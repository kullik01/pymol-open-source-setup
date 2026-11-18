#!/usr/bin/env python3
"""Validate the structure and acceptance state of a project specification."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


REQUIRED_METADATA = (
    "Status",
    "Product frame",
    "Technical design",
    "Product owner",
    "Technical owner",
    "Required reviewers",
    "Last reviewed",
)

REQUIRED_SECTIONS = (
    "Executive summary",
    "Problem, users, and evidence",
    "Product vision and desired outcomes",
    "Success measures and guardrails",
    "Essential scenarios",
    "V1 scope",
    "Non-goals",
    "Constraints",
    "Assumptions and unresolved questions",
    "Architectural context",
    "System architecture",
    "Components and ownership",
    "Domain model and state transitions",
    "Data lifecycle and retention",
    "APIs, protocols, and contracts",
    "Supported clients and interfaces",
    "Component orchestration rules",
    "Security, privacy, and abuse controls",
    "Failure modes and resilience",
    "Concurrency, capacity, performance, and cost",
    "Configuration and deployment topology",
    "Observability and operations",
    "Test and evaluation strategy",
    "Compatibility and migration",
    "Rollout, rollback, and cleanup",
    "Alternatives and trade-offs",
    "Risks and open decisions",
    "Source references",
    "Acceptance",
)

ALLOWED_STATES = {"Draft", "Accepted", "Superseded"}
PLACEHOLDER = re.compile(
    r"\b(?:TODO|TBD)\b|<!--|"
    r"\[(?:Project Name|name or team|technical and specialist reviewers|"
    r"YYYY-MM-DD|measure|baseline|target|window|source|owner|item|"
    r"assumption/open|yes/no|evidence|point|component|responsibility|inputs|"
    r"outputs|dependencies|contract|consumers|shape|guarantees|behavior|policy|"
    r"failure|effect|signal|recovery|option|benefits|costs|"
    r"chosen/rejected and why|risk|impact|action)\](?!\()",
    re.IGNORECASE,
)


def metadata(text: str, field: str) -> str | None:
    match = re.search(
        rf"^\*\*{re.escape(field)}:\*\*\s*(.*?)\s*$",
        text,
        re.MULTILINE,
    )
    return match.group(1) if match else None


def validate(path: Path) -> list[str]:
    errors: list[str] = []
    if not path.is_file():
        return [f"{path}: file does not exist"]

    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    if not lines or not re.fullmatch(r"#\s+.+\s+Specification", lines[0]):
        errors.append("first line must be '# <Project Name> Specification'")

    values: dict[str, str] = {}
    for field in REQUIRED_METADATA:
        value = metadata(text, field)
        if value is None:
            errors.append(f"missing metadata field: {field}")
        else:
            values[field] = value

    for field in ("Status", "Product frame", "Technical design"):
        value = values.get(field)
        if value is not None and value not in ALLOWED_STATES:
            errors.append(f"{field} must be Draft, Accepted, or Superseded")

    headings = {
        match.group(1).strip()
        for match in re.finditer(r"^##\s+(.+?)\s*$", text, re.MULTILINE)
    }
    for section in REQUIRED_SECTIONS:
        if section not in headings:
            errors.append(f"missing section: {section}")

    if values.get("Status") == "Accepted":
        if values.get("Product frame") != "Accepted":
            errors.append("accepted document requires an accepted product frame")
        if values.get("Technical design") != "Accepted":
            errors.append("accepted document requires an accepted technical design")
        if PLACEHOLDER.search(text):
            errors.append("accepted document contains a placeholder or HTML comment")
        unchecked = re.findall(r"^- \[ \]", text, re.MULTILINE)
        if unchecked:
            errors.append("accepted document contains unchecked acceptance criteria")
        for field in ("Product owner", "Technical owner", "Required reviewers"):
            value = values.get(field, "")
            if not value or value.casefold() in {"none", "n/a", "unknown"}:
                errors.append(f"accepted document requires {field}")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("specification", type=Path)
    args = parser.parse_args()

    errors = validate(args.specification)
    if errors:
        print(f"Specification validation failed: {args.specification}")
        for error in errors:
            print(f"- {error}")
        return 1

    state = metadata(args.specification.read_text(encoding="utf-8"), "Status")
    print(f"Specification validation passed ({state}): {args.specification}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
