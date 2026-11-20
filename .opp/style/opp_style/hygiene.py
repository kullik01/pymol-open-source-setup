"""Hygiene of the lines a change touched: suppressions, task markers, length.

A suppression hides what a checker would report, so the code it covers is
never judged. Each one needs a link to the issue that tracks removing it.
A comment or docstring holds no task marker, since an unfinished piece of
work belongs in an issue. A changed line stays within the configured length.
Comments and line lengths are judged even in a file that does not parse;
the syntax-dependent parts are skipped there.
"""

from __future__ import annotations

import ast
import contextlib
import io
import re
import tokenize

from opp_style import findings
from opp_style import settings

COMMENT_SUPPRESSIONS = (
    ("noqa", re.compile(r"#\s*noqa\b", re.IGNORECASE), "# noqa"),
    ("type-ignore", re.compile(r"#\s*type:\s*ignore\b"), "# type: ignore"),
    ("pyrefly-ignore", re.compile(r"#\s*pyrefly:\s*ignore\b"), "# pyrefly: ignore"),
)
"""The suppression comments: each one's kind, pattern and display name."""

CAST_MODULES = ("typing", "typing_extensions")
"""The modules whose ``cast`` is a suppression; a function that only shares the name is not."""

MARKER = re.compile(r"\b(?:TOD[O]|FIXM[E]|XX[X]|HAC[K])\b")
"""The upper-case task markers a comment or docstring may not hold."""

URL = re.compile(r"[A-Za-z][A-Za-z0-9+.-]*://\S+")
"""A single URL without spaces."""

RULE_SUPPRESSION = "suppression"
"""The rule's short name for a suppression without an issue link."""

RULE_MARKER = "marker"
"""The rule's short name for a task marker."""

RULE_LINE_LENGTH = "line-length"
"""The rule's short name for a line that is too long."""


def judge(path: str, text: str, lines: frozenset[int], rules: settings.Settings) -> list[findings.Finding]:
    """Judge the hygiene of a file's changed lines.

    Args:
        path: The file's repository path.
        text: The file's text.
        lines: The changed lines, counted from 1.
        rules: The repository's settings.

    Returns:
        The findings, on changed lines only.
    """
    tmp_comments = _comments(text)
    tmp_tree = _parse(text)
    tmp_found = _markers(path, text, lines, tmp_comments, tmp_tree)
    tmp_found.extend(_line_lengths(path, text, lines, rules.line_length))
    if tmp_tree is not None:
        tmp_found.extend(_suppressions(path, lines, tmp_comments, tmp_tree, rules))
    return sorted(tmp_found)


def _parse(text: str) -> ast.Module | None:
    """Parse a file.

    Args:
        text: The file's text.

    Returns:
        The syntax tree, or None when the file does not parse.
    """
    try:
        return ast.parse(text)
    except (SyntaxError, ValueError):
        return None


def _comments(text: str) -> dict[int, str]:
    """Collect the comments of a file.

    Args:
        text: The file's text.

    Returns:
        Each comment's text by its line; a file that stops tokenizing
        yields the comments before the break.
    """
    tmp_found: dict[int, str] = {}
    with contextlib.suppress(tokenize.TokenError, SyntaxError):
        for tmp_token in tokenize.generate_tokens(io.StringIO(text).readline):
            if tmp_token.type == tokenize.COMMENT:
                tmp_found[tmp_token.start[0]] = tmp_token.string
    return tmp_found


def _docstring_lines(tree: ast.Module) -> set[int]:
    """Find the lines of every docstring, including attribute docstrings.

    Args:
        tree: The file's syntax tree.

    Returns:
        The lines of each statement that is only a string.
    """
    tmp_lines: set[int] = set()
    for tmp_node in ast.walk(tree):
        if (
            isinstance(tmp_node, ast.Expr)
            and isinstance(tmp_node.value, ast.Constant)
            and isinstance(tmp_node.value.value, str)
        ):
            tmp_lines.update(range(tmp_node.lineno, (tmp_node.end_lineno or tmp_node.lineno) + 1))
    return tmp_lines


def _markers(
    path: str, text: str, lines: frozenset[int], comments: dict[int, str], tree: ast.Module | None
) -> list[findings.Finding]:
    """Find task markers in changed comments and docstrings.

    Args:
        path: The file's repository path.
        text: The file's text.
        lines: The changed lines.
        comments: The file's comments by line.
        tree: The file's syntax tree, or None.

    Returns:
        One finding per changed line that holds a marker.
    """
    tmp_source = text.split("\n")
    tmp_docstrings = _docstring_lines(tree) if tree is not None else set()
    tmp_found = []
    for tmp_line in sorted(lines):
        if tmp_line in comments:
            tmp_haystack = comments[tmp_line]
        elif tmp_line in tmp_docstrings and tmp_line <= len(tmp_source):
            tmp_haystack = tmp_source[tmp_line - 1]
        else:
            continue
        tmp_match = MARKER.search(tmp_haystack)
        if tmp_match is not None:
            tmp_found.append(
                findings.Finding(
                    path,
                    tmp_line,
                    RULE_MARKER,
                    f"{tmp_match.group(0)} marks unfinished work; finish it, or track it in an issue",
                )
            )
    return tmp_found


def _line_lengths(path: str, text: str, lines: frozenset[int], limit: int) -> list[findings.Finding]:
    """Find changed lines longer than the limit.

    Args:
        path: The file's repository path.
        text: The file's text.
        lines: The changed lines.
        limit: The longest line, in characters.

    Returns:
        One finding per changed line that is too long, is not a lone URL
        and is not part of the file's leading comment block, the licence
        header a repository copies into every file unchanged.
    """
    tmp_source = text.split("\n")
    tmp_header = _header_length(tmp_source)
    tmp_found = []
    for tmp_line in sorted(lines):
        if tmp_line > len(tmp_source) or tmp_line <= tmp_header:
            continue
        tmp_content = tmp_source[tmp_line - 1].rstrip("\r")
        if len(tmp_content) > limit and not _lone_url(tmp_content):
            tmp_found.append(
                findings.Finding(
                    path,
                    tmp_line,
                    RULE_LINE_LENGTH,
                    f"the line has {len(tmp_content)} characters; the limit is {limit}",
                )
            )
    return tmp_found


def _header_length(source: list[str]) -> int:
    """Count the lines of a file's leading comment block.

    Args:
        source: The file's lines.

    Returns:
        How many lines at the top are comments or blank, before the first
        line of code or docstring.
    """
    tmp_count = 0
    for tmp_text in source:
        tmp_stripped = tmp_text.strip()
        if tmp_stripped and not tmp_stripped.startswith("#"):
            break
        tmp_count += 1
    return tmp_count


def _lone_url(line: str) -> bool:
    """Whether a line holds nothing but a URL, possibly in a comment or quotes.

    Args:
        line: The line's text.

    Returns:
        Whether, without its indentation, a leading ``#``, spaces and
        surrounding quotes, the line is one URL.
    """
    tmp_content = line.strip().lstrip("#").strip().strip("\"'")
    return URL.fullmatch(tmp_content) is not None


def _suppressions(
    path: str, lines: frozenset[int], comments: dict[int, str], tree: ast.Module, rules: settings.Settings
) -> list[findings.Finding]:
    """Find suppressions on changed lines that carry no issue link.

    Args:
        path: The file's repository path.
        lines: The changed lines.
        comments: The file's comments by line.
        tree: The file's syntax tree.
        rules: The repository's settings.

    Returns:
        One finding per suppression without a link on its line or the line
        above.
    """
    tmp_link = re.compile(rules.suppression_issue)
    tmp_found: dict[tuple[int, str], str] = {}
    for tmp_line, tmp_comment in comments.items():
        if tmp_line not in lines:
            continue
        for tmp_kind, tmp_pattern, tmp_what in COMMENT_SUPPRESSIONS:
            if tmp_pattern.search(tmp_comment):
                tmp_found[(tmp_line, tmp_kind)] = tmp_what
    tmp_modules, tmp_names = _cast_bindings(tree)
    for tmp_node in ast.walk(tree):
        if (
            isinstance(tmp_node, ast.Call)
            and _is_cast(tmp_node.func, tmp_modules, tmp_names)
            and tmp_node.lineno in lines
        ):
            tmp_found[(tmp_node.lineno, "cast")] = "cast()"
    for tmp_annotation in _annotations(tree):
        for tmp_node in ast.walk(tmp_annotation):
            if _is_any(tmp_node) and getattr(tmp_node, "lineno", 0) in lines:
                tmp_found[(tmp_node.lineno, "any")] = "Any in an annotation"
    return [
        findings.Finding(
            path,
            tmp_line,
            RULE_SUPPRESSION,
            f"{tmp_what} suppresses a check; link the issue that tracks removing it in a comment "
            "on this line or the line above, or fix what it hides",
        )
        for (tmp_line, tmp_kind), tmp_what in sorted(tmp_found.items())
        if not any(tmp_link.search(comments.get(tmp_number, "")) for tmp_number in (tmp_line, tmp_line - 1))
    ]


def _cast_bindings(tree: ast.Module) -> tuple[frozenset[str], frozenset[str]]:
    """Find the names a file binds to ``typing``'s ``cast`` and its modules.

    Imports anywhere in the file count, inside functions and under
    ``if TYPE_CHECKING:`` too.

    Args:
        tree: The file's syntax tree.

    Returns:
        The names bound to the ``typing`` and ``typing_extensions`` modules,
        and the names bound to their ``cast``.
    """
    tmp_modules: set[str] = set()
    tmp_names: set[str] = set()
    for tmp_node in ast.walk(tree):
        if isinstance(tmp_node, ast.Import):
            for tmp_alias in tmp_node.names:
                if tmp_alias.name in CAST_MODULES:
                    tmp_modules.add(tmp_alias.asname or tmp_alias.name)
        elif isinstance(tmp_node, ast.ImportFrom) and tmp_node.level == 0 and tmp_node.module in CAST_MODULES:
            for tmp_alias in tmp_node.names:
                if tmp_alias.name == "cast":
                    tmp_names.add(tmp_alias.asname or tmp_alias.name)
    return frozenset(tmp_modules), frozenset(tmp_names)


def _is_cast(node: ast.expr, modules: frozenset[str], names: frozenset[str]) -> bool:
    """Whether a called expression is ``typing``'s ``cast``.

    Args:
        node: The called expression.
        modules: The names the file binds to ``typing`` and
            ``typing_extensions``.
        names: The names the file binds to their ``cast``.

    Returns:
        Whether it is one of ``names``, or ``cast`` on one of ``modules``;
        a method or function that only shares the name is not.
    """
    if isinstance(node, ast.Name):
        return node.id in names
    return (
        isinstance(node, ast.Attribute)
        and node.attr == "cast"
        and isinstance(node.value, ast.Name)
        and node.value.id in modules
    )


def _is_any(node: ast.AST) -> bool:
    """Whether a node is ``Any``, bare, as an attribute or in a string.

    Args:
        node: A node inside an annotation.

    Returns:
        Whether it names ``Any``.
    """
    if isinstance(node, ast.Name):
        return node.id == "Any"
    if isinstance(node, ast.Attribute):
        return node.attr == "Any"
    return (
        isinstance(node, ast.Constant)
        and isinstance(node.value, str)
        and re.search(r"\bAny\b", node.value) is not None
    )


def _annotations(tree: ast.Module) -> list[ast.expr]:
    """Collect every annotation of a file.

    Args:
        tree: The file's syntax tree.

    Returns:
        The annotations of arguments, returns and annotated assignments.
    """
    tmp_found: list[ast.expr] = []
    for tmp_node in ast.walk(tree):
        if isinstance(tmp_node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            tmp_arguments = tmp_node.args
            tmp_all = [*tmp_arguments.posonlyargs, *tmp_arguments.args, *tmp_arguments.kwonlyargs]
            tmp_all.extend(tmp_extra for tmp_extra in (tmp_arguments.vararg, tmp_arguments.kwarg) if tmp_extra)
            tmp_found.extend(tmp_argument.annotation for tmp_argument in tmp_all if tmp_argument.annotation)
            if tmp_node.returns is not None:
                tmp_found.append(tmp_node.returns)
        elif isinstance(tmp_node, ast.AnnAssign):
            tmp_found.append(tmp_node.annotation)
    return tmp_found
