"""The C++ layout rule: the lines a change touched are formatted by clang-format.

The checker asks the pinned clang-format, with the family style file that
sits beside the ``opp_style`` package, which of the judged lines it would
change. The tool comes from ``uvx`` when uv is installed, otherwise from the
``PATH`` when it is the pinned version.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import xml.etree.ElementTree as element_tree
from collections.abc import Mapping

from opp_style import changes
from opp_style import findings
from opp_style import settings

VERSION = "21.1.8"
"""The clang-format version the family pins."""

RULE = "clang-format"
"""The rule's short name."""

STYLE_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "clang-format")
"""The family style file, beside the ``opp_style`` package."""

INSTALLED_STYLE_FILE = ".opp/style/clang-format"
"""Where a repository keeps the style file, for the fix the message names."""

TIMEOUT = 300.0
"""Seconds to wait for one clang-format run, a first ``uvx`` download included."""

_TOOL: list[list[str]] = []
"""The command found for this process: empty before the first search."""


class ToolMissing(Exception):
    """No clang-format of the pinned version is available."""


class ToolFailed(ToolMissing):
    """clang-format ran and failed, so the layout cannot be judged."""


def _reports_version(command: list[str]) -> bool:
    """Whether a command is clang-format of the pinned version.

    Args:
        command: The command and its leading arguments.

    Returns:
        Whether ``--version`` ran and named :data:`VERSION`.
    """
    try:
        tmp_result = subprocess.run(
            [*command, "--version"],
            capture_output=True,
            text=True,
            timeout=TIMEOUT,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return tmp_result.returncode == 0 and f"version {VERSION}" in tmp_result.stdout


def tool() -> list[str]:
    """Find the pinned clang-format, once per process.

    ``uvx`` is tried first, then ``clang-format`` on the ``PATH``.

    Returns:
        The command to run, without its arguments.

    Raises:
        ToolMissing: Neither is available at the pinned version.
    """
    if _TOOL:
        return _TOOL[0]
    tmp_candidates: list[list[str]] = []
    if shutil.which("uvx"):
        tmp_candidates.append(["uvx", "--from", f"clang-format=={VERSION}", "clang-format"])
    if shutil.which("clang-format"):
        tmp_candidates.append(["clang-format"])
    for tmp_candidate in tmp_candidates:
        if _reports_version(tmp_candidate):
            _TOOL.append(tmp_candidate)
            return tmp_candidate
    raise ToolMissing(
        f"clang-format {VERSION} is not available: install uv (https://docs.astral.sh/uv/), "
        f"which runs it with uvx, or install clang-format {VERSION} on the PATH"
    )


def forget() -> None:
    """Forget the tool found, so that the next :func:`tool` call searches again."""
    _TOOL.clear()


def _ranges(lines: frozenset[int], count: int) -> list[tuple[int, int]]:
    """Group line numbers into contiguous ranges.

    Args:
        lines: The judged lines.
        count: The number of lines in the file; later lines are dropped.

    Returns:
        The ``(first, last)`` of each run of consecutive lines, in order.
    """
    tmp_ranges: list[tuple[int, int]] = []
    for tmp_line in sorted(tmp_value for tmp_value in lines if 1 <= tmp_value <= count):
        if tmp_ranges and tmp_ranges[-1][1] == tmp_line - 1:
            tmp_ranges[-1] = (tmp_ranges[-1][0], tmp_line)
        else:
            tmp_ranges.append((tmp_line, tmp_line))
    return tmp_ranges


def _replacements(path: str, text: str, ranges: list[tuple[int, int]]) -> list[tuple[int, int]]:
    """Ask clang-format what it would change in the ranges.

    Args:
        path: The file's repository path, for the language it implies.
        text: The file's text.
        ranges: The line ranges to format; none formats the whole file.

    Returns:
        The byte offset and length of each replacement.

    Raises:
        ToolMissing: clang-format is unavailable or fails.
    """
    tmp_command = [
        *tool(),
        f"--style=file:{STYLE_FILE}",
        "--output-replacements-xml",
        f"--assume-filename={path}",
        *[f"--lines={tmp_first}:{tmp_last}" for tmp_first, tmp_last in ranges],
    ]
    try:
        tmp_result = subprocess.run(
            tmp_command,
            input=text.encode("utf-8"),
            capture_output=True,
            timeout=TIMEOUT,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exception:
        raise ToolFailed(f"clang-format could not run on {path}: {exception}") from exception
    if tmp_result.returncode != 0:
        raise ToolFailed(f"clang-format failed on {path}: {tmp_result.stderr.decode('utf-8', 'replace').strip()}")
    try:
        tmp_root = element_tree.fromstring(tmp_result.stdout)
    except element_tree.ParseError as exception:
        raise ToolFailed(f"clang-format printed unreadable replacements for {path}: {exception}") from exception
    return [
        (int(tmp_node.get("offset", "0")), int(tmp_node.get("length", "0")))
        for tmp_node in tmp_root.iter("replacement")
    ]


def _changed_lines(text: str, replacements: list[tuple[int, int]]) -> set[int]:
    """Find the lines that replacements change.

    A replacement of the white space before a token starts at the line break
    that ends the line before, so a leading line break does not count as part
    of the changed span.

    Args:
        text: The file's text.
        replacements: The byte offset and length of each replacement.

    Returns:
        The numbers of the lines the replacements touch.
    """
    tmp_bytes = text.encode("utf-8")
    tmp_changed: set[int] = set()
    for tmp_offset, tmp_length in replacements:
        tmp_start = tmp_offset
        if tmp_length and tmp_bytes[tmp_start : tmp_start + 1] == b"\n":
            tmp_start += 1
        tmp_first = tmp_bytes.count(b"\n", 0, tmp_start) + 1
        tmp_last = tmp_bytes.count(b"\n", 0, tmp_offset + tmp_length) + 1
        tmp_changed.update(range(tmp_first, max(tmp_first, tmp_last) + 1))
    return tmp_changed


def judge(
    changed: Mapping[str, frozenset[int]],
    rules: settings.Settings,
    committed: bool,
) -> list[findings.Finding]:
    """Judge the layout of the changed C++ lines.

    Args:
        changed: Each C++ file's repository path with its judged lines.
        rules: The repository's settings.
        committed: Whether to read the files from ``HEAD``.

    Returns:
        A finding on each judged line that clang-format would change.

    Raises:
        ToolMissing: clang-format of the pinned version is unavailable, or it
            fails.
    """
    tmp_found: list[findings.Finding] = []
    for tmp_path, tmp_lines in sorted(changed.items()):
        tmp_text = changes.read(rules.root, tmp_path, committed)
        if tmp_text is None:
            continue
        tmp_ranges = _ranges(tmp_lines, tmp_text.count("\n") + 1)
        if not tmp_ranges:
            continue
        # The whole file is formatted and only the judged lines' changes are
        # kept: formatting only the judged ranges can change a line at a
        # range's edge that the whole file's formatting leaves alone.
        tmp_touched = _changed_lines(tmp_text, _replacements(tmp_path, tmp_text, []))
        tmp_arguments = " ".join(f"--lines={tmp_first}:{tmp_last}" for tmp_first, tmp_last in tmp_ranges)
        tmp_message = (
            "clang-format would change this line; run "
            f"clang-format --style=file:{INSTALLED_STYLE_FILE} -i {tmp_arguments} {tmp_path}"
        )
        tmp_found.extend(
            findings.Finding(tmp_path, tmp_line, RULE, tmp_message)
            for tmp_line in sorted(tmp_touched & tmp_lines)
        )
    return tmp_found
