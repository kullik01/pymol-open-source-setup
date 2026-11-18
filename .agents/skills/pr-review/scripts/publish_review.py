#!/usr/bin/env python3
"""Validate and optionally publish a CoDev GitHub Pull Request review.

The script deliberately has no third-party dependencies and never publishes by
default. The AI review produces the JSON payload; this script handles the
provider-specific commit and diff anchor checks.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


API_ROOT = "https://api.github.com"
FETCH_PARTS = ("metadata", "diff", "files", "commits", "reviews", "comments", "checks")
HUNK_RE = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")


class ReviewError(RuntimeError):
    """Raised for an invalid payload, stale PR, or GitHub API failure."""


def _gh_executable() -> str | None:
    """Resolve gh even when a desktop agent omits machine PATH entries."""
    configured = os.environ.get("CODEV_GH_PATH")
    if configured and Path(configured).is_file():
        return configured
    found = shutil.which("gh")
    if found:
        return found
    if os.name == "nt":
        for candidate in (
            Path(os.environ.get("ProgramFiles", "C:\\Program Files"))
            / "GitHub CLI"
            / "gh.exe",
            Path(os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)"))
            / "GitHub CLI"
            / "gh.exe",
            Path(os.environ.get("LOCALAPPDATA", ""))
            / "Programs"
            / "GitHub CLI"
            / "gh.exe",
        ):
            if candidate.is_file():
                return str(candidate)
    return None


@dataclass(frozen=True)
class DiffLines:
    right: frozenset[int]
    left: frozenset[int]


def _request(
    token: str | None,
    method: str,
    url: str,
    *,
    accept: str,
    body: object | None = None,
    decode_json: bool = True,
    use_gh: bool = False,
) -> object:
    if use_gh:
        gh_executable = _gh_executable()
        if gh_executable is None:
            raise ReviewError(
                "gh CLI was not found; install it or set CODEV_GH_PATH"
            )
        endpoint = url.removeprefix(f"{API_ROOT}/")
        command = [
            gh_executable,
            "api",
            endpoint,
            "--method",
            method,
            "--header",
            f"Accept: {accept}",
        ]
        encoded = None if body is None else json.dumps(body)
        if encoded is not None:
            command.extend(["--input", "-"])
        try:
            completed = subprocess.run(
                command,
                check=False,
                capture_output=True,
                text=True,
                input=encoded,
                timeout=30,
            )
        except (OSError, subprocess.TimeoutExpired) as error:
            raise ReviewError(f"gh CLI request failed: {error}") from error
        if completed.returncode != 0:
            detail = completed.stderr.strip() or "unknown gh CLI error"
            raise ReviewError(f"gh CLI request failed: {detail}")
        raw = completed.stdout
        if not raw:
            return {}
        if not decode_json:
            return raw
        try:
            return json.loads(raw)
        except json.JSONDecodeError as error:
            raise ReviewError("gh CLI returned invalid JSON") from error

    if not token:
        raise ReviewError("a GitHub token is required for direct API authentication")
    data = None if body is None else json.dumps(body).encode("utf-8")
    request = Request(
        url,
        data=data,
        method=method,
        headers={
            "Accept": accept,
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "CoDev-pr-review",
            **({"Content-Type": "application/json"} if data else {}),
        },
    )
    try:
        with urlopen(request, timeout=30) as response:
            raw = response.read().decode("utf-8")
    except (HTTPError, URLError, TimeoutError) as error:
        detail = getattr(error, "reason", error)
        raise ReviewError(f"GitHub API request failed: {detail}") from error
    if not raw:
        return {}
    if not decode_json:
        return raw
    try:
        return json.loads(raw)
    except json.JSONDecodeError as error:
        raise ReviewError("GitHub API returned invalid JSON") from error


def parse_diff(diff: str) -> dict[str, DiffLines]:
    """Return valid old/new line numbers for each file in a unified diff."""
    result: dict[str, DiffLines] = {}
    path: str | None = None
    right: set[int] = set()
    left: set[int] = set()
    old_line = new_line = 0

    def save() -> None:
        if path is not None:
            result[path] = DiffLines(frozenset(right), frozenset(left))

    for raw_line in diff.splitlines():
        if raw_line.startswith("diff --git "):
            save()
            path = None
            right = set()
            left = set()
            continue
        if raw_line.startswith("+++ b/"):
            path = raw_line[6:]
            continue
        match = HUNK_RE.match(raw_line)
        if match:
            old_line = int(match.group(1))
            new_line = int(match.group(3))
            continue
        if path is None or not raw_line:
            continue
        marker = raw_line[0]
        if marker == "+" and not raw_line.startswith("+++"):
            right.add(new_line)
            new_line += 1
        elif marker == "-" and not raw_line.startswith("---"):
            left.add(old_line)
            old_line += 1
        elif marker == " ":
            right.add(new_line)
            left.add(old_line)
            old_line += 1
            new_line += 1
    save()
    return result


def _marker(finding_id: str) -> str:
    return f"<!-- codev:pr-review:{finding_id} -->"


def validate_payload(payload: object, head_sha: str, diff: str) -> list[dict[str, object]]:
    if not isinstance(payload, dict):
        raise ReviewError("review payload must be a JSON object")
    if payload.get("head_sha") != head_sha:
        raise ReviewError("payload head_sha does not match the current PR head")
    comments = payload.get("comments", [])
    if not isinstance(comments, list):
        raise ReviewError("review payload comments must be a list")
    diff_lines = parse_diff(diff)
    validated: list[dict[str, object]] = []
    seen: set[str] = set()
    for index, item in enumerate(comments, 1):
        if not isinstance(item, dict):
            raise ReviewError(f"comment {index} must be an object")
        finding_id = item.get("finding_id")
        body = item.get("body")
        if not isinstance(finding_id, str) or not finding_id:
            raise ReviewError(f"comment {index} needs a non-empty finding_id")
        if finding_id in seen:
            raise ReviewError(f"duplicate finding_id: {finding_id}")
        seen.add(finding_id)
        if not isinstance(body, str) or not body.strip():
            raise ReviewError(f"comment {finding_id} needs a non-empty body")
        path = item.get("path")
        subject_type = item.get("subject_type", "line")
        if not isinstance(path, str) or path not in diff_lines:
            raise ReviewError(f"comment {finding_id} targets a file absent from the PR diff")
        if subject_type == "file":
            if any(key in item for key in ("line", "start_line", "side", "start_side")):
                raise ReviewError(f"file comment {finding_id} must not include line coordinates")
            validated.append({"path": path, "subject_type": "file", "body": f"{_marker(finding_id)}\n{body}"})
            continue
        side = item.get("side")
        line = item.get("line")
        if side not in {"LEFT", "RIGHT"} or not isinstance(line, int):
            raise ReviewError(f"inline comment {finding_id} needs line and LEFT/RIGHT side")
        allowed = diff_lines[path].left if side == "LEFT" else diff_lines[path].right
        if line not in allowed:
            raise ReviewError(f"comment {finding_id} line {line} is not present in the PR diff")
        comment: dict[str, object] = {
            "path": path,
            "line": line,
            "side": side,
            "body": f"{_marker(finding_id)}\n{body}",
        }
        if "start_line" in item:
            start_line = item.get("start_line")
            start_side = item.get("start_side")
            if not isinstance(start_line, int) or start_side not in {"LEFT", "RIGHT"}:
                raise ReviewError(f"multi-line comment {finding_id} has invalid start coordinates")
            start_allowed = diff_lines[path].left if start_side == "LEFT" else diff_lines[path].right
            if start_line not in start_allowed:
                raise ReviewError(f"comment {finding_id} start line is not present in the PR diff")
            comment.update(start_line=start_line, start_side=start_side)
        validated.append(comment)
    return validated


def _authentication(args: argparse.Namespace) -> tuple[str | None, bool]:
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    use_gh = args.auth == "gh" or (args.auth == "auto" and not token)
    if args.auth == "token" and not token:
        raise ReviewError("--auth token requires GITHUB_TOKEN or GH_TOKEN")
    if use_gh and _gh_executable() is None:
        raise ReviewError("GitHub CLI is unavailable; install gh or set CODEV_GH_PATH")
    return token, use_gh


def _fetch_data(
    args: argparse.Namespace,
    token: str | None,
    use_gh: bool,
) -> dict[str, object]:
    root = f"{API_ROOT}/repos/{args.repo}/pulls/{args.pr}"
    selected = tuple(args.include or FETCH_PARTS)
    data: dict[str, object] = {}
    if "metadata" in selected or "checks" in selected:
        data["metadata"] = _request(
            token, "GET", root, accept="application/vnd.github+json", use_gh=use_gh
        )
    metadata = data.get("metadata")
    if not isinstance(metadata, dict):
        metadata = _request(
            token, "GET", root, accept="application/vnd.github+json", use_gh=use_gh
        )
        data["metadata"] = metadata
    head = metadata.get("head") if isinstance(metadata, dict) else None
    head_sha = head.get("sha") if isinstance(head, dict) else None
    if not isinstance(head_sha, str):
        raise ReviewError("GitHub PR response contained no head SHA")
    if "diff" in selected:
        data["diff"] = _request(
            token,
            "GET",
            root,
            accept="application/vnd.github.v3.diff",
            decode_json=False,
            use_gh=use_gh,
        )
    endpoints = {
        "files": f"{root}/files?per_page=100",
        "commits": f"{root}/commits?per_page=100",
        "reviews": f"{root}/reviews?per_page=100",
        "comments": f"{root}/comments?per_page=100",
        "checks": f"{API_ROOT}/repos/{args.repo}/commits/{head_sha}/check-runs?per_page=100",
    }
    for part, endpoint in endpoints.items():
        if part in selected:
            data[part] = _request(
                token,
                "GET",
                endpoint,
                accept="application/vnd.github+json",
                use_gh=use_gh,
            )
    return data


def fetch(args: argparse.Namespace) -> int:
    token, use_gh = _authentication(args)
    data = _fetch_data(args, token, use_gh)
    if args.output_dir:
        args.output_dir.mkdir(parents=True, exist_ok=True)
        for name, value in data.items():
            path = args.output_dir / (
                f"{name}.patch" if name == "diff" else f"{name}.json"
            )
            if name == "diff":
                if not isinstance(value, str):
                    raise ReviewError("GitHub did not return a textual PR diff")
                path.write_text(value, encoding="utf-8")
            else:
                path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
        print(f"Fetched {', '.join(data)} into {args.output_dir}")
    else:
        print(json.dumps(data, indent=2))
    return 0


def publish(args: argparse.Namespace) -> int:
    payload = json.loads(Path(args.review).read_text(encoding="utf-8"))
    token, use_gh = _authentication(args)
    root = f"{API_ROOT}/repos/{args.repo}/pulls/{args.pr}"
    pr = _request(
        token, "GET", root, accept="application/vnd.github+json", use_gh=use_gh
    )
    diff = _request(
        token,
        "GET",
        root,
        accept="application/vnd.github.v3.diff",
        decode_json=False,
        use_gh=use_gh,
    )
    if not isinstance(pr, dict) or not isinstance(pr.get("head"), dict):
        raise ReviewError("GitHub PR response did not contain a head commit")
    head_sha = pr["head"].get("sha")
    if not isinstance(head_sha, str):
        raise ReviewError("GitHub PR response contained no head SHA")
    expected = args.commit or payload.get("head_sha")
    if expected != head_sha:
        raise ReviewError(f"stale PR: expected head {expected}, current head is {head_sha}")
    if not isinstance(diff, str):
        raise ReviewError("GitHub did not return a textual PR diff")
    comments = validate_payload(payload, head_sha, diff)
    summary = payload.get("summary", "CoDev PR review")
    if not isinstance(summary, str):
        raise ReviewError("review summary must be a string")
    existing: set[str] = set()
    if args.publish:
        old = _request(
            token,
            "GET",
            f"{root}/comments?per_page=100",
            accept="application/vnd.github+json",
            use_gh=use_gh,
        )
        if isinstance(old, list):
            existing = {marker for item in old if isinstance(item, dict) for marker in re.findall(r"<!-- codev:pr-review:[^ ]+ -->", str(item.get("body", "")))}
        comments = [item for item in comments if not any(marker in str(item.get("body", "")) for marker in existing)]
    review = {"commit_id": head_sha, "body": summary, "comments": comments}
    if args.submit:
        review["event"] = "COMMENT" if args.submit == "comment" else "REQUEST_CHANGES"
    if args.publish:
        response = _request(
            token,
            "POST",
            f"{root}/reviews",
            accept="application/vnd.github+json",
            body=review,
            use_gh=use_gh,
        )
        print(json.dumps({"published": True, "pending": not args.submit, "response": response}, indent=2))
    else:
        print(json.dumps({"published": False, "pending": True, "request": review}, indent=2))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True, help="GitHub owner/name")
    parser.add_argument("--pr", required=True, type=int, help="Pull Request number")
    parser.add_argument("--review", type=Path, help="Review JSON payload")
    parser.add_argument(
        "--fetch",
        action="store_true",
        help="Fetch PR data instead of publishing a review",
    )
    parser.add_argument(
        "--include",
        action="append",
        choices=FETCH_PARTS,
        help="Fetch part; repeat this option (default: all parts)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="Write fetched data here instead of printing JSON",
    )
    parser.add_argument("--commit", help="Expected PR head SHA")
    parser.add_argument(
        "--auth",
        choices=("auto", "gh", "token"),
        default="auto",
        help="Authentication backend (default: gh when no token environment variable)",
    )
    parser.add_argument("--publish", action="store_true", help="Post the review to GitHub")
    parser.add_argument("--submit", choices=("comment", "request-changes"), help="Submit instead of leaving pending")
    args = parser.parse_args(argv)
    try:
        if args.fetch:
            return fetch(args)
        if args.review is None:
            parser.error("--review is required unless --fetch is used")
        return publish(args)
    except (OSError, json.JSONDecodeError, ReviewError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
