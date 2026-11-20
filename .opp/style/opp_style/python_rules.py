"""The OPP family's Python rules that ruff has no rule for, judged line by line.

ruff checks the formatting and its own rules; this module checks the rest,
over the lines of a change that the caller names:

- ``tmp-prefix``: a variable a function, lambda or comprehension binds
  starts with ``tmp_``; parameters, ``except`` names, imports, nested
  definitions, names starting with ``_``, and module- and class-level names
  keep theirs.
- ``whole-word``: such a variable's name after ``tmp_`` is not a single
  letter (``x``, ``y`` and ``z`` excepted) nor one of the settings'
  abbreviations, unless the docstring of its function or module names it in
  double backticks, as a documented formula's symbol.
- ``exception-name``: an exception an ``except`` clause catches is named
  ``exception``, and no parameter is named ``e``, ``exc`` or ``err``.
- ``logger-name``: a module's logger is ``_LOGGER``.
- ``one-import``: an import statement names one module or symbol.
- ``docstring``: every module, class, function and method has a
  docstring, private ones included.
- ``args``: a function's docstring describes each parameter in its
  ``Args:`` section, but ``self``, ``cls`` and the ones whose name starts
  with ``_``, which marks them unused.
- ``returns``: a function that returns a value says what in a
  ``Returns:`` section, and a generator what it yields in a ``Yields:``
  section. A function returns a value when its return annotation is not
  ``None``, ``NoReturn`` or ``Never``, or when its own body returns one;
  a property is documented as the attribute it is, and needs neither.
- ``attribute-docstring``: a module-level or class-level assignment, and an
  instance attribute's first assignment in ``__init__``, has a docstring
  right after it, unless the class docstring's ``Attributes:`` section
  describes it; ``__all__``, ``__slots__`` and ``__docformat__`` need none.
- ``citation``: a comment or docstring cites no ADR, decision, step,
  question or gap number, nor a short record id: a capital D, Q, S or O
  followed by one to three digits, other than the settings' citation
  exceptions.
- ``inline-comment``: a comment stands on its own line; tool directives
  (``# noqa``, ``# type:``, ``# pyrefly:``, ``# pragma``, ``# fmt:``) are
  exempt, since their tools read them only there.
- ``colon-comment``: a comment starts with ``#`` alone, never with
  Sphinx's ``#:``; an attribute is documented by its docstring.
- ``field-parameters``: a function takes no ``**`` parameter unless it
  passes it on as ``**`` in a call, as forwarding a callable's own
  arguments does.

``python3 .opp/style/check.py --fix`` fixes the ``tmp-prefix``,
``exception-name``, ``one-import`` and ``colon-comment`` findings.
"""

from __future__ import annotations

import ast
import dataclasses
import io
import re
import tokenize
from collections.abc import Iterator

from opp_style import citations
from opp_style import findings
from opp_style import settings

def comments(text: str) -> dict[int, str]:
    """Every comment in a file, by its line.

    Args:
        text: The file's text, which parses.

    Returns:
        Each comment's text, ``#`` included, by the line it is on.
    """
    tmp_found: dict[int, str] = {}
    for tmp_token in tokenize.generate_tokens(io.StringIO(text).readline):
        if tmp_token.type == tokenize.COMMENT:
            tmp_found[tmp_token.start[0]] = tmp_token.string
    return tmp_found


def _parse(path: str, text: str) -> ast.Module | findings.Finding:
    """A file's syntax tree, or the finding that it does not parse.

    Args:
        path: The file's repository path, for the finding.
        text: The file's text.

    Returns:
        The tree, or a ``syntax`` finding.
    """
    try:
        return ast.parse(text, filename=path)
    except SyntaxError as exception:
        return findings.Finding(
            path=path,
            line=exception.lineno or 0,
            rule="syntax",
            message="does not parse: %s" % (exception.msg,),
        )


def _span(node: ast.AST) -> range:
    """The lines a node covers.

    Args:
        node: The node.

    Returns:
        Its first to its last line.
    """
    tmp_first = getattr(node, "lineno", 0)
    tmp_last = getattr(node, "end_lineno", None) or tmp_first
    return range(tmp_first, tmp_last + 1)


def touched(node: ast.AST, lines: frozenset[int]) -> bool:
    """Whether a judged line lies in a node.

    Args:
        node: The node.
        lines: The judged lines.

    Returns:
        Whether one does.
    """
    return any(tmp_line in lines for tmp_line in _span(node))


def _dotted(node: ast.AST) -> str:
    """The dotted name a name or an attribute chain on one spells.

    Args:
        node: The node.

    Returns:
        ``a.b.c``, or empty for any other node.
    """
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        tmp_base = _dotted(node.value)
        return tmp_base + "." + node.attr if tmp_base else ""
    return ""


_COORDINATES = frozenset({"x", "y", "z"})
"""The single letters a variable may be named after ``tmp_``."""

_DOCLESS = frozenset({"__all__", "__slots__", "__docformat__"})
"""The module- and class-level names that need no docstring."""

_DIRECTIVE = re.compile(r"#\s*(noqa|type:|pyrefly:|pragma|fmt:)", re.IGNORECASE)
"""A comment a tool reads only on the line of the code it is about."""

_ARGS_SECTION = re.compile(r"^\s*(Args|Arguments):\s*$", re.MULTILINE)
"""The ``Args:`` heading of a Google-style docstring."""

_ATTRIBUTES_SECTION = re.compile(r"^\s*Attributes:\s*$", re.MULTILINE)
"""The ``Attributes:`` heading of a Google-style class docstring."""

_RETURNS_SECTION = re.compile(r"^\s*Returns?:\s*$", re.MULTILINE)
"""The ``Returns:`` heading of a Google-style docstring."""

_YIELDS_SECTION = re.compile(r"^\s*Yields?:\s*$", re.MULTILINE)
"""The ``Yields:`` heading of a Google-style docstring."""

_NOTHING = frozenset({"None", "NoReturn", "Never"})
"""The return annotations that say a function returns no value."""

_PROPERTIES = ("property", "cached_property")
"""The decorators whose function is documented as an attribute."""

_NEXT_SECTION = re.compile(
    r"^\s*(Returns|Return|Yields|Raises|Attributes|Examples?|Notes?|"
    r"Warnings?|See Also|Todo):\s*$",
    re.MULTILINE,
)
"""A heading that ends the section before it."""

_TYPE_ALIAS = getattr(ast, "TypeAlias", ())
"""The node of a ``type`` statement, which Python before 3.12 lacks."""

_FUNCTIONS = (ast.FunctionDef, ast.AsyncFunctionDef)
"""The nodes that define a function or method."""

_COMPREHENSIONS = (ast.ListComp, ast.SetComp, ast.GeneratorExp, ast.DictComp)
"""The nodes that open a comprehension's scope."""


def judge(path: str, text: str, lines: frozenset[int], rules: settings.Settings) -> list[findings.Finding]:
    """The findings on the judged ``lines`` of one file.

    Args:
        path: The file's repository path.
        text: The file's text.
        lines: The judged lines.
        rules: The repository's settings.

    Returns:
        The findings, sorted; a file that does not parse gives one ``syntax``
        finding.
    """
    tmp_tree = _parse(path, text)
    if isinstance(tmp_tree, findings.Finding):
        return [tmp_tree]
    tmp_found: list[tuple[int, str, str]] = []
    tmp_found.extend(_imports(tmp_tree, lines))
    tmp_found.extend(_definitions(tmp_tree, lines))
    tmp_found.extend(_attribute_docstrings(tmp_tree, lines))
    tmp_found.extend(_variables(tmp_tree, lines, rules))
    tmp_found.extend(_comments(text, lines, rules))
    tmp_found.extend(_docstring_citations(tmp_tree, text, lines, rules))
    return [
        findings.Finding(path=path, line=tmp_line, rule=tmp_rule, message=tmp_message)
        for tmp_line, tmp_rule, tmp_message in sorted(set(tmp_found))
    ]


# <editor-fold desc="Imports and definitions">


def _imports(tree: ast.Module, lines: frozenset[int]) -> list[tuple[int, str, str]]:
    """Import statements on judged lines that name more than one name.

    Args:
        tree: The parsed file.
        lines: The judged lines.

    Returns:
        A ``(line, rule, message)`` per such statement.
    """
    return [
        (
            tmp_node.lineno,
            "one-import",
            "an import statement names one module or symbol; write one "
            "statement per name",
        )
        for tmp_node in ast.walk(tree)
        if isinstance(tmp_node, (ast.Import, ast.ImportFrom))
        and len(tmp_node.names) > 1
        and touched(tmp_node, lines)
    ]


def _definitions(tree: ast.Module, lines: frozenset[int]) -> list[tuple[int, str, str]]:
    """Modules, classes and functions without the documentation due.

    Args:
        tree: The parsed file.
        lines: The judged lines.

    Returns:
        The ``docstring``, ``args``, ``exception-name``, ``logger-name``
        and ``field-parameters`` findings.
    """
    tmp_found: list[tuple[int, str, str]] = []
    if lines and ast.get_docstring(tree) is None:
        tmp_found.append((1, "docstring", "the module needs a docstring"))
    for tmp_node in ast.walk(tree):
        if isinstance(tmp_node, ast.ClassDef):
            if touched(tmp_node, lines) and (ast.get_docstring(tmp_node) is None):
                tmp_found.append(
                    (
                        tmp_node.lineno,
                        "docstring",
                        "class %s needs a docstring" % (tmp_node.name,),
                    )
                )
        elif isinstance(tmp_node, _FUNCTIONS):
            if touched(tmp_node, lines):
                tmp_found.extend(_function(tmp_node))
        elif isinstance(tmp_node, ast.ExceptHandler):
            if (
                tmp_node.name
                and tmp_node.name != "exception"
                and not tmp_node.name.startswith("_")
                and tmp_node.lineno in lines
            ):
                tmp_found.append(
                    (
                        tmp_node.lineno,
                        "exception-name",
                        "name the exception `exception`, not `%s`" % (tmp_node.name,),
                    )
                )
        elif isinstance(tmp_node, (ast.Assign, ast.AnnAssign)):
            tmp_found.extend(_logger(tmp_node, lines))
    return tmp_found


def _function(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> list[tuple[int, str, str]]:
    """What a function's documentation and signature lack.

    Args:
        node: The function.

    Returns:
        Its ``docstring``, ``args``, ``exception-name`` and
        ``field-parameters`` findings.
    """
    if any(
        _dotted(tmp_decorator).endswith("overload")
        for tmp_decorator in node.decorator_list
    ):
        return []
    tmp_found: list[tuple[int, str, str]] = []
    tmp_parameters = parameters(node.args)
    for tmp_name in tmp_parameters:
        if tmp_name in ("e", "exc", "err"):
            tmp_found.append(
                (
                    node.lineno,
                    "exception-name",
                    "name the parameter that holds an exception "
                    "`exception`, not `%s`" % (tmp_name,),
                )
            )
    if node.args.kwarg is not None and not _forwards(node, node.args.kwarg.arg):
        tmp_found.append(
            (
                node.lineno,
                "field-parameters",
                "%s takes **%s; take one mapping parameter instead, unless "
                "it passes the arguments on as **%s"
                % (node.name, node.args.kwarg.arg, node.args.kwarg.arg),
            )
        )
    tmp_docstring = ast.get_docstring(node)
    if tmp_docstring is None:
        tmp_found.append(
            (
                node.lineno,
                "docstring",
                "%s needs a docstring" % (node.name,),
            )
        )
        return tmp_found
    tmp_found.extend(_returned(node, tmp_docstring))
    tmp_documented = _section_names(tmp_docstring, _ARGS_SECTION)
    tmp_missing = [
        tmp_name
        for tmp_name in tmp_parameters
        if tmp_name not in ("self", "cls")
        and not tmp_name.startswith("_")
        and tmp_name not in tmp_documented
    ]
    if tmp_missing:
        tmp_found.append(
            (
                node.lineno,
                "args",
                "%s's docstring describes no %s in its Args: section"
                % (
                    node.name,
                    ", ".join("`%s`" % tmp_name for tmp_name in tmp_missing),
                ),
            )
        )
    return tmp_found


def _returned(
    node: ast.FunctionDef | ast.AsyncFunctionDef, docstring: str
) -> list[tuple[int, str, str]]:
    """A ``Returns:`` or ``Yields:`` section the function's docstring lacks.

    A generator needs ``Yields:``. Any other function needs ``Returns:``
    when its return annotation is not ``None``, ``NoReturn`` or ``Never``,
    or when its own body returns a value. A property is documented as the
    attribute it is, and needs neither.

    Args:
        node: The function.
        docstring: Its docstring.

    Returns:
        A ``returns`` finding, or none.
    """
    if any(
        _dotted(tmp_decorator).split(".")[-1] in _PROPERTIES
        for tmp_decorator in node.decorator_list
    ):
        return []
    tmp_body = list(_own_nodes(node))
    if any(isinstance(tmp_node, (ast.Yield, ast.YieldFrom)) for tmp_node in tmp_body):
        if _YIELDS_SECTION.search(docstring):
            return []
        return [
            (
                node.lineno,
                "returns",
                "%s is a generator; its docstring says what it yields in a "
                "Yields: section" % (node.name,),
            )
        ]
    tmp_annotated = node.returns is not None and (
        _dotted(node.returns).split(".")[-1] not in _NOTHING
        and not (
            isinstance(node.returns, ast.Constant)
            and node.returns.value in (None, *_NOTHING)
        )
    )
    tmp_returns_value = any(
        isinstance(tmp_node, ast.Return)
        and tmp_node.value is not None
        and not (
            isinstance(tmp_node.value, ast.Constant) and tmp_node.value.value is None
        )
        for tmp_node in tmp_body
    )
    if (tmp_annotated or tmp_returns_value) and not _RETURNS_SECTION.search(docstring):
        return [
            (
                node.lineno,
                "returns",
                "%s returns a value; its docstring says what in a Returns: "
                "section" % (node.name,),
            )
        ]
    return []


def _own_nodes(node: ast.AST) -> Iterator[ast.AST]:
    """The nodes of a function's body, not those of functions nested in it.

    Args:
        node: The function.

    Yields:
        Each node of its body, nested classes' and functions' left out.
    """
    tmp_pending = list(ast.iter_child_nodes(node))
    while tmp_pending:
        tmp_node = tmp_pending.pop()
        if isinstance(tmp_node, (*_FUNCTIONS, ast.Lambda, ast.ClassDef)):
            continue
        yield tmp_node
        tmp_pending.extend(ast.iter_child_nodes(tmp_node))


def parameters(arguments: ast.arguments) -> list[str]:
    """Every parameter's name, in order, ``*`` and ``**`` ones included.

    Args:
        arguments: A function's or lambda's arguments.

    Returns:
        The names.
    """
    tmp_names = [
        tmp_argument.arg
        for tmp_argument in (
            *arguments.posonlyargs,
            *arguments.args,
            *arguments.kwonlyargs,
        )
    ]
    for tmp_argument in (arguments.vararg, arguments.kwarg):
        if tmp_argument is not None:
            tmp_names.append(tmp_argument.arg)
    return tmp_names


def _forwards(node: ast.FunctionDef | ast.AsyncFunctionDef, name: str) -> bool:
    """Whether the function passes its ``**name`` on as ``**name`` in a call.

    Args:
        node: The function.
        name: Its ``**`` parameter's name.

    Returns:
        Whether a call in its body spreads that name.
    """
    for tmp_node in ast.walk(node):
        if isinstance(tmp_node, ast.Call):
            for tmp_keyword in tmp_node.keywords:
                if (
                    tmp_keyword.arg is None
                    and isinstance(tmp_keyword.value, ast.Name)
                    and tmp_keyword.value.id == name
                ):
                    return True
    return False


def _section_names(docstring: str, heading: re.Pattern[str]) -> set[str]:
    """The names a Google-style section of ``docstring`` describes.

    Args:
        docstring: The docstring, as ``ast.get_docstring`` cleans it.
        heading: The section's heading.

    Returns:
        Each ``name:`` or ``name (type):`` entry's name, ``*`` and ``**``
        stripped; empty without the section.
    """
    tmp_match = heading.search(docstring)
    if tmp_match is None:
        return set()
    tmp_rest = docstring[tmp_match.end() :]
    tmp_end = _NEXT_SECTION.search(tmp_rest)
    tmp_section = tmp_rest[: tmp_end.start()] if tmp_end else tmp_rest
    return {
        tmp_entry.group(1)
        for tmp_entry in re.finditer(
            r"^\s+\**([A-Za-z_][A-Za-z0-9_]*)\s*(?:\(|:)",
            tmp_section,
            re.MULTILINE,
        )
    }


def _logger(
    node: ast.Assign | ast.AnnAssign, lines: frozenset[int]
) -> list[tuple[int, str, str]]:
    """A logger assigned on a judged line to a name other than ``_LOGGER``.

    Args:
        node: An assignment.
        lines: The judged lines.

    Returns:
        A ``logger-name`` finding per such name.
    """
    if (
        node.lineno not in lines
        or not isinstance(node.value, ast.Call)
        or not _dotted(node.value.func).endswith("getLogger")
    ):
        return []
    tmp_targets = node.targets if isinstance(node, ast.Assign) else [node.target]
    return [
        (
            node.lineno,
            "logger-name",
            "name the module's logger `_LOGGER`, not `%s`" % (tmp_target.id,),
        )
        for tmp_target in tmp_targets
        if isinstance(tmp_target, ast.Name) and tmp_target.id != "_LOGGER"
    ]


# </editor-fold>


# <editor-fold desc="Attribute docstrings">


def _attribute_docstrings(
    tree: ast.Module, lines: frozenset[int]
) -> list[tuple[int, str, str]]:
    """Assignments on judged lines that lack the docstring after them.

    Args:
        tree: The parsed file.
        lines: The judged lines.

    Returns:
        An ``attribute-docstring`` finding per such name.
    """
    tmp_found = _block(tree.body, lines, set(), "module-level")
    for tmp_node in ast.walk(tree):
        if not isinstance(tmp_node, ast.ClassDef):
            continue
        tmp_described = _section_names(
            ast.get_docstring(tmp_node) or "", _ATTRIBUTES_SECTION
        )
        tmp_found.extend(_block(tmp_node.body, lines, tmp_described, "class attribute"))
        for tmp_member in tmp_node.body:
            if isinstance(tmp_member, _FUNCTIONS) and (tmp_member.name == "__init__"):
                tmp_found.extend(
                    _instance_attributes(tmp_member.body, lines, tmp_described, set())
                )
    return tmp_found


def _block(
    body: list[ast.stmt],
    lines: frozenset[int],
    described: set[str],
    kind: str,
) -> list[tuple[int, str, str]]:
    """The undocumented names a module's or class's block assigns.

    Args:
        body: The statements, nested ``if`` and ``try`` blocks included.
        lines: The judged lines.
        described: The names the class docstring's ``Attributes:`` section
            describes.
        kind: How the finding names the variable.

    Returns:
        An ``attribute-docstring`` finding per such name.
    """
    tmp_found: list[tuple[int, str, str]] = []
    for tmp_index, tmp_statement in enumerate(body):
        if isinstance(tmp_statement, ast.If):
            tmp_found.extend(_block(tmp_statement.body, lines, described, kind))
            tmp_found.extend(_block(tmp_statement.orelse, lines, described, kind))
            continue
        if isinstance(tmp_statement, ast.Try):
            tmp_found.extend(_block(tmp_statement.body, lines, described, kind))
            continue
        tmp_names = _assigned_names(tmp_statement)
        if not tmp_names or tmp_statement.lineno not in lines:
            continue
        if _followed_by_docstring(body, tmp_index):
            continue
        tmp_found.extend(
            (
                tmp_statement.lineno,
                "attribute-docstring",
                "the %s `%s` needs a docstring on the line after its "
                "assignment" % (kind, tmp_name),
            )
            for tmp_name in tmp_names
            if tmp_name not in described
        )
    return tmp_found


def _assigned_names(statement: ast.stmt) -> list[str]:
    """The names a module- or class-level statement assigns.

    Args:
        statement: The statement.

    Returns:
        The names that need a docstring; empty for any other statement.
    """
    tmp_targets: list[ast.expr] = []
    if isinstance(statement, ast.Assign):
        tmp_targets = list(statement.targets)
    elif isinstance(statement, ast.AnnAssign):
        tmp_targets = [statement.target]
    elif _TYPE_ALIAS and isinstance(statement, _TYPE_ALIAS):
        tmp_targets = [statement.name]
    return [
        tmp_name.id
        for tmp_target in tmp_targets
        for tmp_name in names(tmp_target)
        if tmp_name.id not in _DOCLESS
    ]


def _instance_attributes(
    body: list[ast.stmt],
    lines: frozenset[int],
    described: set[str],
    seen: set[str],
) -> list[tuple[int, str, str]]:
    """The undocumented instance attributes ``__init__`` assigns first.

    Args:
        body: ``__init__``'s statements, or a block nested in them.
        lines: The judged lines.
        described: The names the class docstring's ``Attributes:`` section
            describes.
        seen: The attributes assigned before, which this call adds to.

    Returns:
        An ``attribute-docstring`` finding per such attribute.
    """
    tmp_found: list[tuple[int, str, str]] = []
    for tmp_index, tmp_statement in enumerate(body):
        for tmp_field in ("body", "orelse", "finalbody"):
            tmp_inner = getattr(tmp_statement, tmp_field, None)
            if isinstance(
                tmp_statement, (ast.If, ast.Try, ast.With, ast.For)
            ) and isinstance(tmp_inner, list):
                tmp_found.extend(
                    _instance_attributes(tmp_inner, lines, described, seen)
                )
        tmp_targets: list[ast.expr] = []
        if isinstance(tmp_statement, ast.Assign):
            tmp_targets = list(tmp_statement.targets)
        elif isinstance(tmp_statement, ast.AnnAssign):
            tmp_targets = [tmp_statement.target]
        for tmp_target in tmp_targets:
            if not (
                isinstance(tmp_target, ast.Attribute)
                and isinstance(tmp_target.value, ast.Name)
                and tmp_target.value.id == "self"
            ) or (tmp_target.attr in seen):
                continue
            seen.add(tmp_target.attr)
            if (
                tmp_statement.lineno in lines
                and tmp_target.attr not in described
                and not _followed_by_docstring(body, tmp_index)
            ):
                tmp_found.append(
                    (
                        tmp_statement.lineno,
                        "attribute-docstring",
                        "the instance attribute `%s` needs a docstring on "
                        "the line after its first assignment in __init__, "
                        "or a line in the class's Attributes: section"
                        % (tmp_target.attr,),
                    )
                )
    return tmp_found


def _followed_by_docstring(body: list[ast.stmt], index: int) -> bool:
    """Whether the statement after ``body[index]`` is a string expression.

    Args:
        body: A block's statements.
        index: The assignment's position in it.

    Returns:
        Whether a docstring follows the assignment.
    """
    if index + 1 >= len(body):
        return False
    tmp_next = body[index + 1]
    return (
        isinstance(tmp_next, ast.Expr)
        and isinstance(tmp_next.value, ast.Constant)
        and isinstance(tmp_next.value.value, str)
    )


def names(target: ast.expr) -> list[ast.Name]:
    """The names an assignment target binds, unpacking included.

    Args:
        target: The target.

    Returns:
        Its names; attributes and subscripts bind none.
    """
    if isinstance(target, ast.Name):
        return [target]
    if isinstance(target, (ast.Tuple, ast.List)):
        return [
            tmp_name for tmp_element in target.elts for tmp_name in names(tmp_element)
        ]
    if isinstance(target, ast.Starred):
        return names(target.value)
    return []


# </editor-fold>


# <editor-fold desc="Variables">


@dataclasses.dataclass
class _Scope:
    """A function, lambda or comprehension, as the variable rules see it.

    Attributes:
        node: The node that opens the scope.
        parameters: Its parameters' names.
        declared: The names it declares ``global`` or ``nonlocal``.
        bindings: The names its statements bind as variables.
        docstring: The docstring that may define a formula's symbols: the
            function's own, else the enclosing one's, else the module's.
    """

    node: ast.AST
    parameters: set[str]
    declared: set[str]
    bindings: list[ast.Name]
    docstring: str


def _variables(
    tree: ast.Module, lines: frozenset[int], rules: settings.Settings
) -> list[tuple[int, str, str]]:
    """Variables bound on judged lines without ``tmp_`` or a whole word.

    Args:
        tree: The parsed file.
        lines: The judged lines.
        rules: The repository's settings.

    Returns:
        The ``tmp-prefix`` and ``whole-word`` findings.
    """
    tmp_found: list[tuple[int, str, str]] = []
    for tmp_scope in scopes(tree):
        for tmp_name in tmp_scope.bindings:
            tmp_identifier = tmp_name.id
            if (
                tmp_name.lineno not in lines
                or tmp_identifier.startswith("_")
                or tmp_identifier in tmp_scope.parameters
                or tmp_identifier in tmp_scope.declared
            ):
                continue
            if not tmp_identifier.startswith("tmp_"):
                tmp_found.append(
                    (
                        tmp_name.lineno,
                        "tmp-prefix",
                        "the variable `%s` starts with tmp_: `tmp_%s`"
                        % (tmp_identifier, tmp_identifier),
                    )
                )
                continue
            tmp_word = tmp_identifier[len("tmp_") :]
            tmp_short = (
                len(tmp_word) == 1 and tmp_word not in _COORDINATES
            ) or tmp_word in rules.abbreviations
            if tmp_short and "``%s``" % (tmp_word,) not in tmp_scope.docstring:
                tmp_found.append(
                    (
                        tmp_name.lineno,
                        "whole-word",
                        "name `%s` with the whole word for what it holds; a "
                        "formula's symbol may stay when the docstring names "
                        "it as ``%s``" % (tmp_identifier, tmp_word),
                    )
                )
    return tmp_found


def scopes(tree: ast.Module) -> list[_Scope]:
    """Every function, lambda and comprehension scope, with its bindings.

    A walrus binds in the nearest enclosing function, as Python does; a
    class body is no function scope, so its names are not variables.

    Args:
        tree: The parsed file.

    Returns:
        The scopes, outermost first.
    """
    tmp_found: list[_Scope] = []
    _collect(tree, [], ast.get_docstring(tree) or "", tmp_found)
    return tmp_found


def _collect(
    node: ast.AST,
    stack: list[_Scope],
    docstring: str,
    found: list[_Scope],
) -> None:
    """Walk ``node``, opening a scope for each function-like node.

    Args:
        node: The node to walk.
        stack: The function-like scopes around it, innermost last.
        docstring: The docstring that defines symbols where ``node`` is.
        found: The scopes found so far, which this call adds to.
    """
    for tmp_child in ast.iter_child_nodes(node):
        if isinstance(tmp_child, (*_FUNCTIONS, ast.Lambda)):
            tmp_own = (
                ast.get_docstring(tmp_child)
                if isinstance(tmp_child, _FUNCTIONS)
                else None
            )
            tmp_scope = _Scope(
                node=tmp_child,
                parameters=set(parameters(tmp_child.args)),
                declared=set(),
                bindings=[],
                docstring=(tmp_own or "") + "\n" + docstring,
            )
            found.append(tmp_scope)
            _collect(tmp_child, [*stack, tmp_scope], tmp_scope.docstring, found)
        elif isinstance(tmp_child, _COMPREHENSIONS):
            tmp_scope = _Scope(
                node=tmp_child,
                parameters=set(),
                declared=set(),
                bindings=[],
                docstring=docstring,
            )
            found.append(tmp_scope)
            for tmp_generator in tmp_child.generators:
                tmp_scope.bindings.extend(names(tmp_generator.target))
            _collect(tmp_child, [*stack, tmp_scope], docstring, found)
        elif isinstance(tmp_child, ast.ClassDef):
            _collect(
                tmp_child,
                [],
                (ast.get_docstring(tmp_child) or "") + "\n" + docstring,
                found,
            )
        else:
            _bind(tmp_child, stack)
            _collect(tmp_child, stack, docstring, found)


def _bind(node: ast.AST, stack: list[_Scope]) -> None:
    """Record the variables ``node`` binds in the innermost scope.

    Args:
        node: A statement or expression.
        stack: The function-like scopes around it, innermost last.
    """
    if not stack:
        return
    tmp_scope = stack[-1]
    if isinstance(node, (ast.Global, ast.Nonlocal)):
        tmp_scope.declared.update(node.names)
    elif isinstance(node, ast.Assign):
        for tmp_target in node.targets:
            tmp_scope.bindings.extend(names(tmp_target))
    elif isinstance(node, (ast.AnnAssign, ast.AugAssign, ast.For, ast.AsyncFor)):
        tmp_scope.bindings.extend(names(node.target))
    elif isinstance(node, (ast.With, ast.AsyncWith)):
        for tmp_item in node.items:
            if tmp_item.optional_vars is not None:
                tmp_scope.bindings.extend(names(tmp_item.optional_vars))
    elif isinstance(node, ast.NamedExpr):
        tmp_function = next(
            (
                tmp_outer
                for tmp_outer in reversed(stack)
                if not isinstance(tmp_outer.node, _COMPREHENSIONS)
            ),
            None,
        )
        if tmp_function is not None:
            tmp_function.bindings.append(node.target)


# </editor-fold>


# <editor-fold desc="Comments and citations">


def _comments(
    text: str, lines: frozenset[int], rules: settings.Settings
) -> list[tuple[int, str, str]]:
    """Comments after code, with ``#:``, or citing records.

    Args:
        text: The file's text, which parses.
        lines: The judged lines.
        rules: The repository's settings.

    Returns:
        The ``inline-comment``, ``colon-comment`` and ``citation``
        findings of comments.
    """
    tmp_source = text.splitlines()
    tmp_found: list[tuple[int, str, str]] = []
    for tmp_line, tmp_comment in comments(text).items():
        if tmp_line not in lines:
            continue
        tmp_before = tmp_source[tmp_line - 1].split(tmp_comment, 1)[0]
        if tmp_before.strip() and not _DIRECTIVE.match(tmp_comment):
            tmp_found.append(
                (
                    tmp_line,
                    "inline-comment",
                    "a comment stands on its own line above the code it explains",
                )
            )
        if tmp_comment.startswith("#:"):
            tmp_found.append(
                (
                    tmp_line,
                    "colon-comment",
                    "a comment starts with # alone, not #:; an attribute "
                    "is documented by a docstring after it",
                )
            )
        tmp_found.extend(_citations(tmp_line, tmp_comment, rules))
    return tmp_found


def _docstring_citations(
    tree: ast.Module, text: str, lines: frozenset[int], rules: settings.Settings
) -> list[tuple[int, str, str]]:
    """Docstring lines that cite records.

    Args:
        tree: The parsed file.
        text: The file's text.
        lines: The judged lines.
        rules: The repository's settings.

    Returns:
        The ``citation`` findings of docstrings, module, class, function
        and attribute docstrings alike.
    """
    tmp_source = text.splitlines()
    tmp_found: list[tuple[int, str, str]] = []
    for tmp_node in ast.walk(tree):
        if not (
            isinstance(tmp_node, ast.Expr)
            and isinstance(tmp_node.value, ast.Constant)
            and isinstance(tmp_node.value.value, str)
        ):
            continue
        for tmp_line in _span(tmp_node):
            if tmp_line in lines and tmp_line <= len(tmp_source):
                tmp_found.extend(_citations(tmp_line, tmp_source[tmp_line - 1], rules))
    return tmp_found


def _citations(line: int, text: str, rules: settings.Settings) -> list[tuple[int, str, str]]:
    """The citation finding for one line of a comment or docstring.

    Args:
        line: The line's number.
        text: The line's text.
        rules: The repository's settings.

    Returns:
        One ``citation`` finding if the line cites a record, else none.
    """
    tmp_cited = citations.cited(text, rules.citation_exceptions)
    if not tmp_cited:
        return []
    return [(line, citations.RULE, citations.message(tmp_cited))]


# </editor-fold>
