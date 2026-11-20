"""The lines a change added or modified, read from git.

The checker judges only these lines. A change is the difference between the
merge base of a reference (``origin/main`` by default) and either the
working tree, which includes edits not yet committed, or ``HEAD`` alone,
which is what a push check judges.
"""

from __future__ import annotations

import os
import re
import subprocess

GIT_TIMEOUT = 120.0
"""Seconds to wait for one git command."""

_HUNK = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@")
"""A hunk header of ``git diff -U0``: where the new lines start, and how many."""


class ChangesError(Exception):
    """git cannot say what changed; the checker cannot run."""


def git(root: str, arguments: list[str]) -> str:
    """Run git in the repository.

    Args:
        root: The repository's root folder.
        arguments: git's arguments.

    Returns:
        What git printed.

    Raises:
        ChangesError: git is missing, timed out or failed.
    """
    try:
        tmp_result = subprocess.run(
            ["git", *arguments],
            cwd=root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=GIT_TIMEOUT,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exception:
        raise ChangesError(f"git {arguments[0]} could not run: {exception}") from exception
    if tmp_result.returncode != 0:
        raise ChangesError(f"git {' '.join(arguments)} failed: {tmp_result.stderr.strip()}")
    return tmp_result.stdout


def repository_root(folder: str) -> str:
    """Find the root of the repository a folder is in.

    Args:
        folder: Any folder inside the repository.

    Returns:
        The repository's root folder, absolute.

    Raises:
        ChangesError: The folder is not inside a git repository.
    """
    return os.path.abspath(git(folder, ["rev-parse", "--show-toplevel"]).strip())


def merge_base(root: str, reference: str) -> str:
    """Find where the change starts.

    Args:
        root: The repository's root folder.
        reference: The reference the change is judged against.

    Returns:
        The hash of the merge base of the reference and ``HEAD``.

    Raises:
        ChangesError: The reference is unknown or has no common history.
    """
    return git(root, ["merge-base", reference, "HEAD"]).strip()


class Change:
    """What a change did: the lines it added or modified, and the files it added.

    Attributes:
        lines: Each added, copied, modified or renamed file's repository
            path, with the numbers of its added or modified lines; a file
            whose change only deleted lines maps to no lines.
        new: The files the change added or copied, as opposed to files it
            modified or renamed.
    """

    def __init__(self, lines: dict[str, frozenset[int]], new: frozenset[str]) -> None:
        """Hold what a change did.

        Args:
            lines: Each file's repository path, with its added or modified
                lines.
            new: The files the change added or copied.
        """
        self.lines = lines
        self.new = new


def changed(root: str, base: str, committed: bool) -> Change:
    """Read what a change did since a commit.

    The prefixes are named, so a repository's ``diff.noprefix`` or
    ``diff.mnemonicPrefix`` setting cannot shift the paths. Without
    ``committed``, files git does not track yet, but does not ignore, count
    as added with every line.

    Args:
        root: The repository's root folder.
        base: The commit the change starts from.
        committed: Whether to judge ``HEAD`` alone, leaving out edits not
            yet committed and untracked files.

    Returns:
        The change's lines and new files; deleted files are left out.
    """
    tmp_range = [base, "HEAD"] if committed else [base]
    tmp_options = ["--no-color", "--no-ext-diff", "--diff-filter=ACMR", "-M", "--src-prefix=a/", "--dst-prefix=b/"]
    tmp_lines = parse_diff(git(root, ["diff", "-U0", *tmp_options, *tmp_range]))
    tmp_new = set(_added(git(root, ["diff", "--name-status", "-z", *tmp_options, *tmp_range])))
    if not committed:
        for tmp_path in git(root, ["ls-files", "--others", "--exclude-standard", "-z"]).split("\0"):
            if tmp_path:
                tmp_text = read(root, tmp_path, False)
                tmp_count = 0 if tmp_text is None else tmp_text.count("\n") + 1
                tmp_lines[tmp_path] = frozenset(range(1, tmp_count + 1))
                tmp_new.add(tmp_path)
    return Change(tmp_lines, frozenset(tmp_new))


def _added(name_status: str) -> list[str]:
    """Read the added and copied files from ``git diff --name-status -z``.

    Args:
        name_status: The output: a status, then one path, or two for a
            rename or copy, each ended by a NUL.

    Returns:
        The new-side path of each added or copied file.
    """
    tmp_fields = name_status.split("\0")
    tmp_added = []
    tmp_index = 0
    while tmp_index < len(tmp_fields) and tmp_fields[tmp_index]:
        tmp_status = tmp_fields[tmp_index]
        tmp_paths = 2 if tmp_status[0] in "RC" else 1
        tmp_new = tmp_fields[tmp_index + tmp_paths]
        if tmp_status[0] in "AC":
            tmp_added.append(tmp_new)
        tmp_index += 1 + tmp_paths
    return tmp_added


def parse_diff(diff: str) -> dict[str, frozenset[int]]:
    """Read the added and modified lines from ``git diff -U0`` output.

    The diff must use git's ``b/`` destination prefix. A path git quotes is
    unquoted; a path with a space ends, unquoted, in a tab, which is
    dropped.

    Args:
        diff: The output.

    Returns:
        Each new-side path with the numbers of its added or modified lines.
    """
    tmp_lines: dict[str, set[int]] = {}
    tmp_path: str | None = None
    tmp_in_header = False
    for tmp_text in diff.split("\n"):
        if tmp_text.startswith("diff --git "):
            tmp_in_header = True
            tmp_path = None
            continue
        if tmp_in_header and tmp_text.startswith("+++ "):
            tmp_target = tmp_text[4:].rstrip("\t")
            tmp_path = None if tmp_target == "/dev/null" else _unquote(tmp_target)[2:]
            if tmp_path is not None:
                tmp_lines.setdefault(tmp_path, set())
            continue
        tmp_match = _HUNK.match(tmp_text)
        if tmp_match and tmp_path is not None:
            tmp_in_header = False
            tmp_start = int(tmp_match.group(1))
            tmp_count = 1 if tmp_match.group(2) is None else int(tmp_match.group(2))
            tmp_lines[tmp_path].update(range(tmp_start, tmp_start + tmp_count))
    return {tmp_key: frozenset(tmp_value) for tmp_key, tmp_value in tmp_lines.items()}


def _unquote(path: str) -> str:
    """Undo git's quoting of a path with unusual characters.

    Args:
        path: The path as ``git diff`` prints it, quoted or not.

    Returns:
        The path itself.
    """
    if not (path.startswith('"') and path.endswith('"')):
        return path
    tmp_escaped = path[1:-1].encode("latin-1", "backslashreplace").decode("unicode_escape")
    return tmp_escaped.encode("latin-1").decode("utf-8", "replace")


def tracked_files(root: str) -> list[str]:
    """Every file git tracks, for a whole-file run.

    Args:
        root: The repository's root folder.

    Returns:
        The repository paths, sorted.
    """
    return sorted(tmp_line for tmp_line in git(root, ["ls-files", "-z"]).split("\0") if tmp_line)


def read(root: str, path: str, committed: bool) -> str | None:
    """Read a file of the change.

    Args:
        root: The repository's root folder.
        path: The file's repository path.
        committed: Whether to read it from ``HEAD`` rather than the working
            tree.

    Returns:
        The file's text, or None when it does not exist there or is not
        UTF-8 text.
    """
    if committed:
        try:
            return git(root, ["show", f"HEAD:{path}"])
        except ChangesError:
            return None
    try:
        with open(os.path.join(root, path), encoding="utf-8") as tmp_file:
            return tmp_file.read()
    except (OSError, UnicodeDecodeError):
        return None
