#!/usr/bin/env python3
"""Supplemental, dependency-free checks for Google Python Style audits."""

from __future__ import annotations

import argparse
import ast
import dataclasses
import json
import pathlib
import re
import sys
import tokenize


@dataclasses.dataclass(frozen=True)
class Finding:
    """One supplemental audit finding."""

    level: str
    rule: str
    file: str
    line: int
    column: int
    message: str


_EXCLUDED_DIRECTORIES = frozenset(
    {
        ".git",
        ".agents",
        ".mypy_cache",
        ".pytest_cache",
        ".pyrefly",
        ".ruff_cache",
        ".venv",
        "__pycache__",
        "build",
        "dist",
        "generated",
        "gen",
        "node_modules",
        "site-packages",
        "vendor",
    }
)
_TYPE_COMMENT_PATTERN = re.compile(r"#\s*type:\s*(?!ignore\b)")
_TODO_PATTERN = re.compile(r"#\s*TODO(?!\s*:\s*\S+\s+-\s+\S+)", re.IGNORECASE)
_PYLINT_PATTERN = re.compile(r"#\s*pylint\s*:", re.IGNORECASE)


def _relative_file(file_path: pathlib.Path, root: pathlib.Path) -> str:
    """Return a stable slash-separated path for a finding."""
    return file_path.relative_to(root).as_posix()


def _add(
    findings: list[Finding],
    *,
    level: str,
    rule: str,
    file_path: pathlib.Path,
    root: pathlib.Path,
    line: int,
    column: int,
    message: str,
) -> None:
    """Append a finding with a normalized location."""
    findings.append(
        Finding(
            level=level,
            rule=rule,
            file=_relative_file(file_path, root),
            line=line,
            column=column,
            message=message,
        )
    )


def _is_test_file(file_path: pathlib.Path) -> bool:
    """Return whether the path conventionally identifies a test module."""
    return file_path.name.startswith("test_") or file_path.name.endswith("_test.py")


def _is_mutable_value(node: ast.AST) -> bool:
    """Return whether an expression likely creates mutable state."""
    if isinstance(node, (ast.List, ast.Dict, ast.Set, ast.ListComp, ast.DictComp, ast.SetComp)):
        return True
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
        return node.func.id in {"dict", "list", "set"}
    return False


def _docstring(node: ast.AST) -> str | None:
    """Return a symbol's raw docstring without discarding its first line."""
    return ast.get_docstring(node, clean=False)


def _has_docstring_section(docstring: str, section: str) -> bool:
    """Return whether a Google-style docstring contains a section heading."""
    return re.search(rf"(?m)^\s*{re.escape(section)}:\s*$", docstring) is not None


def _meaningful_parameters(node: ast.FunctionDef | ast.AsyncFunctionDef) -> list[str]:
    """Return parameters that should be described in an Args section."""
    arguments = node.args
    parameters = [*getattr(arguments, "posonlyargs", []), *arguments.args, *arguments.kwonlyargs]
    names = [argument.arg for argument in parameters if argument.arg not in {"self", "cls"}]
    if arguments.vararg is not None:
        names.append(arguments.vararg.arg)
    if arguments.kwarg is not None:
        names.append(arguments.kwarg.arg)
    return names


def _contains_yield(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    """Return whether a function directly contains a yield expression."""
    return any(isinstance(item, (ast.Yield, ast.YieldFrom)) for item in ast.walk(node))


def _returns_value(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    """Return whether a function has a documented return value."""
    if node.returns is not None and not (isinstance(node.returns, ast.Constant) and node.returns.value is None):
        return True
    return any(isinstance(item, ast.Return) and item.value is not None for item in ast.walk(node))


def _missing_summary(docstring: str | None) -> bool:
    """Return whether a docstring lacks a complete first-line summary."""
    if docstring is None:
        return True
    lines = docstring.splitlines()
    if not lines or not lines[0].strip():
        return True
    return lines[0].rstrip()[-1:] not in ".!?"


class _StyleVisitor(ast.NodeVisitor):
    """Collect syntax-level and review-level findings from one module."""

    def __init__(self, source: str, file_path: pathlib.Path, root: pathlib.Path) -> None:
        self._source = source
        self._file_path = file_path
        self._root = root
        self.findings: list[Finding] = []
        self._scope: list[str] = ["module"]

    def _add_node(self, node: ast.AST, rule: str, level: str, message: str) -> None:
        """Add a finding at an AST node's source location."""
        _add(
            self.findings,
            level=level,
            rule=rule,
            file_path=self._file_path,
            root=self._root,
            line=getattr(node, "lineno", 1),
            column=getattr(node, "col_offset", 0) + 1,
            message=message,
        )

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        """Check import forms that are mechanically identifiable."""
        if node.level:
            self._add_node(
                node,
                "absolute-imports",
                "violation",
                "Use the full package path instead of a relative import.",
            )
        if any(alias.name == "*" for alias in node.names):
            self._add_node(
                node,
                "no-wildcard-imports",
                "violation",
                "Do not use wildcard imports.",
            )
        if node.module == "typing" and any(alias.name == "Text" for alias in node.names):
            self._add_node(
                node,
                "no-typing-text",
                "violation",
                "Use str instead of typing.Text in new code.",
            )
        if node.module in {"typing", "typing_extensions"} and any(
            alias.name in {"List", "Dict", "Set", "Tuple"} for alias in node.names
        ):
            self._add_node(
                node,
                "legacy-typing-alias",
                "review",
                "Prefer built-in collection types when the project supports them.",
            )
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        """Check qualified legacy typing names."""
        if isinstance(node.value, ast.Name) and node.value.id == "typing" and node.attr == "Text":
            self._add_node(node, "no-typing-text", "violation", "Use str instead of typing.Text in new code.")
        self.generic_visit(node)

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        """Flag exception handlers requiring a human control-flow review."""
        if node.type is None:
            self._add_node(node, "broad-exception", "review", "Review the catch-all except block.")
        elif isinstance(node.type, ast.Name) and node.type.id in {"Exception", "BaseException"}:
            self._add_node(node, "broad-exception", "review", "Confirm that catching a broad exception is justified.")
        self.generic_visit(node)

    def visit_Assert(self, node: ast.Assert) -> None:
        """Flag assertions outside conventional tests for a safety review."""
        if not _is_test_file(self._file_path):
            self._add_node(node, "assertion-control-flow", "review", "Confirm that assert is not required for application logic.")
        self.generic_visit(node)

    def visit_Lambda(self, node: ast.Lambda) -> None:
        """Flag lambdas for the guide's readability review."""
        self._add_node(node, "lambda-expression", "review", "Confirm that a lambda is clearer than a named function.")
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Check function documentation, nesting, and approximate length."""
        self._visit_function(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """Check async function documentation, nesting, and length."""
        self._visit_function(node)

    def _visit_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        docstring = _docstring(node)
        if docstring is None:
            self._add_node(node, "function-docstring", "review", "Add a docstring for this public or private function or method.")
        if docstring is not None and _missing_summary(docstring):
            self._add_node(node, "docstring-summary", "review", "Add a complete summary sentence as the first docstring line.")
        if _meaningful_parameters(node) and (docstring is None or not _has_docstring_section(docstring, "Args")):
            self._add_node(node, "docstring-args", "review", "Document the function parameters in an Args section.")
        if _contains_yield(node) and (docstring is None or not _has_docstring_section(docstring, "Yields")):
            self._add_node(node, "docstring-yields", "review", "Document yielded values in a Yields section.")
        elif _returns_value(node) and (docstring is None or not _has_docstring_section(docstring, "Returns")):
            self._add_node(node, "docstring-returns", "review", "Document returned values in a Returns section.")
        if self._scope[-1] != "module":
            self._add_node(node, "nested-function", "review", "Confirm that this nested function is necessary and readable.")
        if node.end_lineno is not None and node.end_lineno - node.lineno + 1 > 40:
            self._add_node(node, "function-length", "review", "Review whether this function can be kept focused below about 40 lines.")
        self._scope.append("function")
        self.generic_visit(node)
        self._scope.pop()

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Check class documentation, nesting, and mutable class state."""
        docstring = _docstring(node)
        if docstring is None:
            self._add_node(node, "class-docstring", "review", "Add a docstring for this public or private class.")
        if docstring is not None and _missing_summary(docstring):
            self._add_node(node, "docstring-summary", "review", "Add a complete summary sentence as the first docstring line.")
        if self._scope[-1] != "module":
            self._add_node(node, "nested-class", "review", "Confirm that this nested class is necessary and readable.")
        self._scope.append("class")
        self.generic_visit(node)
        self._scope.pop()

    def visit_Assign(self, node: ast.Assign) -> None:
        """Flag likely mutable module and class state unless constant-named."""
        if self._scope[-1] in {"module", "class"} and _is_mutable_value(node.value):
            names = [target.id for target in node.targets if isinstance(target, ast.Name)]
            if not names or any(not name.isupper() for name in names):
                self._add_node(node, "mutable-global-state", "review", "Review mutable module or class state and document its justification.")
        self.generic_visit(node)


def _token_findings(source: str, file_path: pathlib.Path, root: pathlib.Path) -> list[Finding]:
    """Collect lexical rules that are independent of AST structure."""
    findings: list[Finding] = []
    for line_number, line in enumerate(source.splitlines(), start=1):
        if len(line) > 80:
            _add(findings, level="review", rule="line-length", file_path=file_path, root=root, line=line_number, column=81, message="Review this line over the Google 80-character limit and its documented exceptions.")
        if _TYPE_COMMENT_PATTERN.search(line):
            _add(findings, level="violation", rule="type-comments", file_path=file_path, root=root, line=line_number, column=1, message="Do not add type comments; use annotations instead.")
        if _TODO_PATTERN.search(line):
            _add(findings, level="review", rule="todo-format", file_path=file_path, root=root, line=line_number, column=1, message="Use TODO: context - explanation with a traceable context link.")
        if _PYLINT_PATTERN.search(line):
            _add(findings, level="review", rule="ruff-suppression", file_path=file_path, root=root, line=line_number, column=1, message="This repository uses Ruff; review whether this Pylint suppression should be replaced with a scoped Ruff suppression.")
        if re.search(r"\\\s*$", line) and not line.lstrip().startswith("#"):
            _add(findings, level="review", rule="explicit-line-continuation", file_path=file_path, root=root, line=line_number, column=len(line.rstrip()) + 1, message="Prefer implicit line joining; confirm that this backslash is only a string escape if applicable.")
    try:
        tokens = list(tokenize.generate_tokens(iter(source.splitlines(keepends=True)).__next__))
    except (IndentationError, tokenize.TokenError) as error:
        _add(findings, level="violation", rule="tokenization", file_path=file_path, root=root, line=1, column=1, message=f"Tokenization failed: {error}.")
    else:
        for token in tokens:
            if token.type == tokenize.OP and token.string == ";":
                _add(findings, level="violation", rule="semicolons", file_path=file_path, root=root, line=token.start[0], column=token.start[1] + 1, message="Do not terminate statements with semicolons or put multiple statements on one line.")
    return findings


def _source_files(root: pathlib.Path) -> list[pathlib.Path]:
    """Find Python files while applying the default audit exclusions."""
    return sorted(
        file_path
        for file_path in root.rglob("*.py")
        if not any(part.lower() in _EXCLUDED_DIRECTORIES for part in file_path.relative_to(root).parts)
    )


def _audit_file(file_path: pathlib.Path, root: pathlib.Path) -> list[Finding]:
    """Audit one Python source file."""
    try:
        with tokenize.open(file_path) as source_file:
            source = source_file.read()
    except (OSError, SyntaxError, UnicodeError) as error:
        return [Finding("violation", "source-read", _relative_file(file_path, root), 1, 1, f"Could not read source: {error}.")]
    findings = _token_findings(source, file_path, root)
    try:
        tree = ast.parse(source, filename=str(file_path))
    except SyntaxError as error:
        findings.append(Finding("violation", "syntax", _relative_file(file_path, root), error.lineno or 1, error.offset or 1, error.msg))
    else:
        visitor = _StyleVisitor(source, file_path, root)
        visitor.visit(tree)
        findings.extend(visitor.findings)
        if not _is_test_file(file_path) and ast.get_docstring(tree) is None:
            findings.append(Finding("review", "module-docstring", _relative_file(file_path, root), 1, 1, "Review the missing module docstring and license/header requirements."))
    return findings


def main() -> int:
    """Run the supplemental audit and emit JSON-lines findings."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=pathlib.Path, default=pathlib.Path.cwd())
    args = parser.parse_args()
    root = args.root.resolve()
    findings = [finding for file_path in _source_files(root) for finding in _audit_file(file_path, root)]
    for finding in findings:
        print(json.dumps(dataclasses.asdict(finding), sort_keys=True))
    violations = sum(finding.level == "violation" for finding in findings)
    reviews = sum(finding.level == "review" for finding in findings)
    print(f"Checked {len(_source_files(root))} Python files: {violations} violations, {reviews} review items.", file=sys.stderr)
    return 1 if violations else 0


if __name__ == "__main__":
    raise SystemExit(main())
