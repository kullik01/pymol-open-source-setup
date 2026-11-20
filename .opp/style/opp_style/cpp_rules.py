"""The C++ documentation rules, judged on the lines a change added or modified.

Every comment is a standalone ``/** ... */`` block on its own lines, none
stands inside a function body, a new file opens with an ``@file`` block that
holds the licence, a header spells out its default arguments, and no comment
cites a planning or decision record.
"""

from __future__ import annotations

import bisect
import re

from opp_style import citations
from opp_style import findings
from opp_style import settings

COMMENT_RULE = "javadoc-comment"
"""The rule that every comment is a standalone Javadoc block."""

PLACEMENT_RULE = "javadoc-placement"
"""The rule that no Javadoc block stands inside a function body."""

FILE_RULE = "file-block"
"""The rule that a new file opens with an ``@file`` block."""

DEFAULT_RULE = "default-arguments"
"""The rule that a header spells out its default arguments."""

HEADER_SUFFIXES = (".h", ".hh", ".hpp", ".hxx")
"""The suffixes of the files that are headers."""

_RAW_STRING_PREFIX = re.compile(r"\b(?:u8|u|U|L)?R$")
"""The prefix that makes the string literal after it a raw string."""

_HEAD_KIND = re.compile(r"\b(namespace|class|struct|union|enum)\b|extern\s*$")
"""The keywords whose brace opens a namespace or a type, not code."""

_EMPTY_BRACE_DEFAULT = re.compile(r"=\s*\{\s*\}\s*[,)]")
"""A parameter's default written as empty braces, as in ``Options options = {}``."""

_FILE_BLOCK = re.compile(r"\A/\*\*\s*(?:\*\s*)?@file\b")
"""The opening of a file's ``@file`` block."""


def _starts_with_digit(text: str, index: int) -> bool:
    """Whether the token that holds ``text[index]`` starts with a digit.

    The token is the run of letters, digits, underscores, points and quotes
    that ends at the index; a quote inside a number is a digit separator, as
    in ``1'000'000``, while a quote after a prefix such as ``u8`` opens a
    character literal.

    Args:
        text: The C++ source.
        index: The offset of a quote in the text.

    Returns:
        Whether the token before the quote is a number.
    """
    tmp_start = index
    while tmp_start > 0 and (text[tmp_start - 1].isalnum() or text[tmp_start - 1] in "_.'"):
        tmp_start -= 1
    return tmp_start < index and text[tmp_start].isdigit()


def _raw_string_end(text: str, index: int) -> int:
    """Find the end of a raw string literal.

    Args:
        text: The C++ source.
        index: The offset of the opening quote.

    Returns:
        The offset after the closing quote, or the text's length when the
        literal is not closed.
    """
    tmp_open = text.find("(", index)
    tmp_delimiter = text[index + 1 : tmp_open] if tmp_open != -1 else ""
    tmp_close = text.find(")" + tmp_delimiter + '"', tmp_open + 1)
    tmp_end = len(text) if tmp_open == -1 or tmp_close == -1 else tmp_close
    return min(len(text), tmp_end + len(tmp_delimiter) + 2)


def _quoted_end(text: str, index: int) -> int:
    """Find the end of a string or character literal.

    Args:
        text: The C++ source.
        index: The offset of the opening quote.

    Returns:
        The offset after the closing quote.
    """
    tmp_quote = text[index]
    tmp_end = index + 1
    while tmp_end < len(text) and text[tmp_end] != tmp_quote:
        tmp_end += 2 if text[tmp_end] == "\\" else 1
    return tmp_end + 1


def _token_at(text: str, index: int) -> tuple[str, int]:
    """Classify what starts at an offset.

    Args:
        text: The C++ source.
        index: The offset.

    Returns:
        ``("comment", end)`` or ``("literal", end)`` for a comment or a
        literal that starts there, with the offset after it; ``("code", index)``
        for anything else, a digit separator included.
    """
    if text.startswith("/*", index):
        tmp_end = text.find("*/", index + 2)
        return "comment", len(text) if tmp_end == -1 else tmp_end + 2
    if text.startswith("//", index):
        tmp_end = text.find("\n", index)
        return "comment", len(text) if tmp_end == -1 else tmp_end
    if text[index] == '"' and _RAW_STRING_PREFIX.search(text, max(0, index - 3), index):
        return "literal", _raw_string_end(text, index)
    if text[index] == "'" and _starts_with_digit(text, index):
        return "code", index
    if text[index] in "\"'":
        return "literal", _quoted_end(text, index)
    return "code", index


def scan(text: str) -> tuple[str, list[tuple[int, int]]]:
    """Separate a C++ source into its code and its comments.

    Args:
        text: The C++ source.

    Returns:
        The source with every comment and every literal (raw strings
        included) blanked to spaces, line breaks kept, so that offsets still
        match; and the offsets ``(start, end)`` of each comment, in order.
    """
    tmp_code = list(text)
    tmp_comments: list[tuple[int, int]] = []
    tmp_index = 0
    while tmp_index < len(text):
        tmp_kind, tmp_end = _token_at(text, tmp_index)
        if tmp_kind == "code":
            tmp_index += 1
            continue
        if tmp_kind == "comment":
            tmp_comments.append((tmp_index, min(tmp_end, len(text))))
        for tmp_position in range(tmp_index, min(tmp_end, len(text))):
            if tmp_code[tmp_position] != "\n":
                tmp_code[tmp_position] = " "
        tmp_index = tmp_end
    return "".join(tmp_code), tmp_comments


def _line_starts(text: str) -> list[int]:
    """Find where each line of a text starts.

    Args:
        text: The text.

    Returns:
        The offset of the first character of every line.
    """
    return [0] + [tmp_match.end() for tmp_match in re.finditer("\n", text)]


def _line_of(starts: list[int], offset: int) -> int:
    """Find the line of an offset.

    Args:
        starts: The line starts, as :func:`_line_starts` gives them.
        offset: The offset.

    Returns:
        The line, counted from 1.
    """
    return bisect.bisect_right(starts, offset)


def _opens_type(head: str) -> bool:
    """Whether a brace's head opens a namespace, a type or ``extern "C"``.

    The head opens one when a namespace, class, struct, union or enum keyword
    (or extern) stands outside every parenthesis and no parenthesis follows
    it, so constraints, attributes and default arguments before it do not
    matter, while a function with a parameter declared with ``struct`` is
    code.

    Args:
        head: The code between the statement before the brace and the brace.

    Returns:
        Whether the brace opens a namespace, a type or ``extern "C"``.
    """
    for tmp_match in _HEAD_KIND.finditer(head):
        tmp_before = head[: tmp_match.start()]
        if tmp_before.count("(") == tmp_before.count(")") and "(" not in head[tmp_match.end() :]:
            return True
    return False


def _comment_findings(
    path: str,
    text: str,
    comments: list[tuple[int, int]],
    starts: list[int],
    lines: frozenset[int],
) -> list[findings.Finding]:
    """Judge that every comment is a standalone Javadoc block.

    Args:
        path: The file's repository path.
        text: The file's text.
        comments: The comments' offsets, as :func:`scan` gives them.
        starts: The line starts of the text.
        lines: The judged lines.

    Returns:
        A finding for each comment that is not one, on the line that breaks it.
    """
    tmp_found: list[findings.Finding] = []
    for tmp_start, tmp_end in comments:
        tmp_line = _line_of(starts, tmp_start)
        tmp_last = _line_of(starts, max(tmp_start, tmp_end - 1))
        tmp_message = _comment_problem(text, tmp_start, tmp_end, starts)
        if tmp_message is None:
            continue
        tmp_where = tmp_last if tmp_message.startswith("trailing") else tmp_line
        if tmp_where in lines:
            tmp_found.append(findings.Finding(path, tmp_where, COMMENT_RULE, tmp_message))
    return tmp_found


def _comment_problem(text: str, start: int, end: int, starts: list[int]) -> str | None:
    """Say what is wrong with one comment.

    Args:
        text: The file's text.
        start: The offset of the comment's first character.
        end: The offset after its last character.
        starts: The line starts of the text.

    Returns:
        The message, or None when the comment is a standalone Javadoc block.
    """
    tmp_opening = text[start : start + 3]
    if text.startswith("//", start):
        return "disallowed '//' comment; write a standalone /** ... */ block"
    if tmp_opening != "/**" or text.startswith("/**/", start):
        return "comment must start with '/**'; write a standalone /** ... */ block"
    tmp_first = starts[_line_of(starts, start) - 1]
    if text[tmp_first:start].strip():
        return "a comment stands on its own lines, never after code"
    if not text.startswith("*/", end - 2):
        return None
    tmp_line_end = text.find("\n", end)
    tmp_line_end = len(text) if tmp_line_end == -1 else tmp_line_end
    if text[end:tmp_line_end].strip():
        return "trailing code after closing '*/'; the block ends its line"
    return None


def _placement_findings(
    path: str,
    text: str,
    code: str,
    starts: list[int],
    lines: frozenset[int],
) -> list[findings.Finding]:
    """Judge that no Javadoc block stands inside a function body.

    A brace opens a namespace, a type or code, as :func:`_opens_type` decides;
    a block that starts while any code brace is open is inside a function.

    Args:
        path: The file's repository path.
        text: The file's text.
        code: The text with comments and literals blanked.
        starts: The line starts of the text.
        lines: The judged lines.

    Returns:
        A finding for each block inside a code block.
    """
    tmp_found: list[findings.Finding] = []
    tmp_open: list[str] = []
    tmp_statement = 0
    for tmp_index, tmp_character in enumerate(code):
        if text.startswith("/**", tmp_index) and "code" in tmp_open:
            tmp_line = _line_of(starts, tmp_index)
            if tmp_line in lines:
                tmp_found.append(
                    findings.Finding(
                        path,
                        tmp_line,
                        PLACEMENT_RULE,
                        "Javadoc block inside a code block; put it above the function or in a name",
                    )
                )
        if tmp_character not in ";{}":
            continue
        if tmp_character == "{":
            tmp_kind = "type" if _opens_type(code[tmp_statement:tmp_index]) else "code"
            tmp_open.append(tmp_kind)
        elif tmp_open:
            tmp_open.pop()
        tmp_statement = tmp_index + 1
    return tmp_found


def _file_block_findings(path: str, text: str, rules: settings.Settings) -> list[findings.Finding]:
    """Judge a new file's opening block.

    Args:
        path: The file's repository path.
        text: The file's text.
        rules: The repository's settings.

    Returns:
        A finding on line 1 for each way the block falls short: it is missing,
        it lacks a licence text, or the file uses ``@brief``.
    """
    if not _FILE_BLOCK.match(text):
        return [findings.Finding(path, 1, FILE_RULE, "a new file opens with a /** @file ... */ block")]
    tmp_end = text.find("*/")
    tmp_block = text if tmp_end == -1 else text[:tmp_end]
    tmp_found = [
        findings.Finding(path, 1, FILE_RULE, f"the @file block must hold '{tmp_licence}'")
        for tmp_licence in rules.cpp_licence
        if tmp_licence not in tmp_block
    ]
    if "@brief" in text:
        tmp_found.append(findings.Finding(path, 1, FILE_RULE, "Javadoc blocks must not use @brief"))
    return tmp_found


def _default_findings(
    path: str,
    code: str,
    starts: list[int],
    lines: frozenset[int],
) -> list[findings.Finding]:
    """Judge that a header spells out its default arguments.

    Args:
        path: The file's repository path.
        code: The text with comments and literals blanked.
        starts: The line starts of the text.
        lines: The judged lines.

    Returns:
        A finding for each default argument written ``= {}``.
    """
    tmp_found: list[findings.Finding] = []
    for tmp_match in _EMPTY_BRACE_DEFAULT.finditer(code):
        tmp_line = _line_of(starts, tmp_match.start())
        if tmp_line in lines:
            tmp_found.append(
                findings.Finding(
                    path,
                    tmp_line,
                    DEFAULT_RULE,
                    "write the default argument as = Type{} instead of = {}",
                )
            )
    return tmp_found


def _citation_findings(
    path: str,
    text: str,
    comments: list[tuple[int, int]],
    starts: list[int],
    lines: frozenset[int],
    rules: settings.Settings,
) -> list[findings.Finding]:
    """Judge that no comment line cites a record.

    Args:
        path: The file's repository path.
        text: The file's text.
        comments: The comments' offsets, as :func:`scan` gives them.
        starts: The line starts of the text.
        lines: The judged lines.
        rules: The repository's settings.

    Returns:
        A finding for each judged comment line that cites a record.
    """
    tmp_found: list[findings.Finding] = []
    for tmp_start, tmp_end in comments:
        for tmp_line in range(_line_of(starts, tmp_start), _line_of(starts, max(tmp_start, tmp_end - 1)) + 1):
            if tmp_line not in lines:
                continue
            tmp_from = max(tmp_start, starts[tmp_line - 1])
            tmp_to = min(tmp_end, starts[tmp_line] if tmp_line < len(starts) else len(text))
            # Short ids are left out in C++: atom and test names such as O1 or S2 look the same.
            tmp_cited = citations.cited(text[tmp_from:tmp_to], rules.citation_exceptions, short_ids=False)
            if tmp_cited:
                tmp_found.append(findings.Finding(path, tmp_line, citations.RULE, citations.message(tmp_cited)))
    return tmp_found


def judge(
    path: str,
    text: str,
    lines: frozenset[int],
    rules: settings.Settings,
    new_file: bool,
) -> list[findings.Finding]:
    """Judge the changed lines of one C++ file.

    Args:
        path: The file's repository path.
        text: The file's text.
        lines: The numbers of the lines the change added or modified.
        rules: The repository's settings.
        new_file: Whether the change adds the file, which then needs its
            ``@file`` block.

    Returns:
        The findings on the judged lines, in the order the rules run.
    """
    tmp_code, tmp_comments = scan(text)
    tmp_starts = _line_starts(text)
    tmp_found = _comment_findings(path, text, tmp_comments, tmp_starts, lines)
    tmp_found.extend(_placement_findings(path, text, tmp_code, tmp_starts, lines))
    if new_file and 1 in lines:
        tmp_found.extend(_file_block_findings(path, text, rules))
    if path.endswith(HEADER_SUFFIXES):
        tmp_found.extend(_default_findings(path, tmp_code, tmp_starts, lines))
    tmp_found.extend(_citation_findings(path, text, tmp_comments, tmp_starts, lines, rules))
    return tmp_found
