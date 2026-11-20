"""Fix what the style checker finds that needs no words, on the changed lines.

:func:`fix` edits one file's text and touches only what the judged lines
reach:

- **tmp_ prefixes.** In every function whose span holds a judged line, and
  in the lambdas and comprehensions in it, each variable without the prefix
  gets it, with every use, in nested functions, lambdas and comprehensions
  too. A rename whose new name is taken there, or whose name an inner scope
  declares ``nonlocal`` or ``global``, or that a ``match`` pattern binds, or
  that an f-string uses where a rename would break it (any f-string before
  Python 3.12, a ``{name=}`` field after), is left and reported.
- **Exception names.** ``except ... as e`` on a judged line becomes
  ``exception`` in the handler, unless the function already uses that name
  or the handler nests with another one of that name; each handler left is
  reported.
- **One name per import.** An import statement on a judged line that names
  several names and owns its whole lines becomes one statement per name,
  its trailing comment on the last; any other is left and reported.
- **Comment markers.** A comment on a judged line that starts with
  Sphinx's ``#:`` starts with ``#`` alone.

Docstrings, ``Args:`` and ``Returns:`` sections and whole-word names need
words, so they stay the author's. The text keeps its line endings, and
:func:`fix` never raises: a text whose fixes would not parse comes back
unchanged. A renamed line may grow past the line
length, so the repository's formatter runs on the fixed files afterwards.
"""

from __future__ import annotations

import ast
import dataclasses
import re
import sys

from opp_style import python_rules
from opp_style import settings

_PREFIX = "tmp_"
"""The prefix every variable takes."""

_FUNCTIONS = (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)
"""The nodes that open a function's scope."""


@dataclasses.dataclass
class _Scope:
    """A scope of one file, as the rename sees it.

    Attributes:
        node: The node that opens it.
        kind: ``module``, ``class``, ``function`` or ``comprehension``.
        parent: The scope around it, or None for the module.
        bound: Every name it binds, parameters and imports included.
        variables: The names it binds as variables.
        parameters: Its parameters' names.
        declared: The names it declares ``global`` or ``nonlocal``.
        blocked: The names a ``match`` pattern binds in it.
        names: The ``Name`` nodes that appear in it.
        children: The scopes inside it.
    """

    node: ast.AST
    kind: str
    parent: _Scope | None
    bound: set[str] = dataclasses.field(default_factory=set)
    variables: set[str] = dataclasses.field(default_factory=set)
    parameters: set[str] = dataclasses.field(default_factory=set)
    declared: set[str] = dataclasses.field(default_factory=set)
    blocked: set[str] = dataclasses.field(default_factory=set)
    names: list[ast.Name] = dataclasses.field(default_factory=list)
    children: list[_Scope] = dataclasses.field(default_factory=list)


class _Builder(ast.NodeVisitor):
    """Builds a file's scopes, the names each binds and the names it uses."""

    def __init__(self) -> None:
        """Start with no scope."""
        self.scope: _Scope | None = None
        """The scope being visited."""
        self.root: _Scope | None = None
        """The module's scope, once visited."""

    def _push(self, node: ast.AST, kind: str) -> _Scope:
        """Open a scope inside the current one.

        Args:
            node: The node that opens it.
            kind: Its kind.

        Returns:
            The new scope, now the current one.
        """
        tmp_scope = _Scope(node, kind, self.scope)
        if self.scope is None:
            self.root = tmp_scope
        else:
            self.scope.children.append(tmp_scope)
        self.scope = tmp_scope
        return tmp_scope

    def _pop(self) -> None:
        """Return to the scope around the current one."""
        assert self.scope is not None
        self.scope = self.scope.parent

    def _current(self) -> _Scope:
        """The current scope.

        Returns:
            It; a node outside every scope is a defect of the walk.
        """
        assert self.scope is not None
        return self.scope

    def _variable(self, name: ast.Name, scope: _Scope | None = None) -> None:
        """Record that a scope binds ``name`` as a variable.

        Args:
            name: The name.
            scope: The scope; the current one by default.
        """
        tmp_scope = scope or self._current()
        tmp_scope.bound.add(name.id)
        tmp_scope.variables.add(name.id)
        self._current().names.append(name)

    def _targets(self, targets: list[ast.expr]) -> None:
        """Record the variables assignment targets bind, and visit the rest.

        Args:
            targets: The targets.
        """
        for tmp_target in targets:
            for tmp_name in python_rules.names(tmp_target):
                self._variable(tmp_name)
            for tmp_inner in _attribute_targets(tmp_target):
                self.visit(tmp_inner)

    def visit_Module(self, node: ast.Module) -> None:
        """Open the module's scope.

        Args:
            node: The module.
        """
        self._push(node, "module")
        self.generic_visit(node)
        self._pop()

    def _function(self, node: ast.AST, arguments: ast.arguments) -> _Scope:
        """Open a function's or lambda's scope, after what runs outside it.

        Args:
            node: The function or lambda.
            arguments: Its arguments.

        Returns:
            The new scope.
        """
        for tmp_default in [
            *arguments.defaults,
            *(
                tmp_value
                for tmp_value in arguments.kw_defaults
                if tmp_value is not None
            ),
        ]:
            self.visit(tmp_default)
        tmp_scope = self._push(node, "function")
        tmp_scope.parameters.update(python_rules.parameters(arguments))
        tmp_scope.bound.update(tmp_scope.parameters)
        return tmp_scope

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Bind the function's name outside and open its scope.

        Args:
            node: The function.
        """
        self._definition(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """Bind the function's name outside and open its scope.

        Args:
            node: The function.
        """
        self._definition(node)

    def _definition(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        """Visit a ``def``: decorators and annotations outside, body inside.

        Args:
            node: The function.
        """
        self._current().bound.add(node.name)
        for tmp_decorator in node.decorator_list:
            self.visit(tmp_decorator)
        for tmp_argument in [
            *node.args.posonlyargs,
            *node.args.args,
            *node.args.kwonlyargs,
            *(tmp_star for tmp_star in (node.args.vararg, node.args.kwarg) if tmp_star),
        ]:
            if tmp_argument.annotation is not None:
                self.visit(tmp_argument.annotation)
        if node.returns is not None:
            self.visit(node.returns)
        self._function(node, node.args)
        for tmp_statement in node.body:
            self.visit(tmp_statement)
        self._pop()

    def visit_Lambda(self, node: ast.Lambda) -> None:
        """Open a lambda's scope.

        Args:
            node: The lambda.
        """
        self._function(node, node.args)
        self.visit(node.body)
        self._pop()

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Bind the class's name outside and open its scope.

        Args:
            node: The class.
        """
        self._current().bound.add(node.name)
        for tmp_expression in [
            *node.decorator_list,
            *node.bases,
            *(tmp_keyword.value for tmp_keyword in node.keywords),
        ]:
            self.visit(tmp_expression)
        self._push(node, "class")
        for tmp_statement in node.body:
            self.visit(tmp_statement)
        self._pop()

    def _comprehension(
        self,
        node: ast.ListComp | ast.SetComp | ast.GeneratorExp | ast.DictComp,
    ) -> None:
        """Open a comprehension's scope; its first iterable runs outside.

        Args:
            node: The comprehension.
        """
        self.visit(node.generators[0].iter)
        tmp_scope = self._push(node, "comprehension")
        for tmp_index, tmp_generator in enumerate(node.generators):
            for tmp_name in python_rules.names(tmp_generator.target):
                self._variable(tmp_name, tmp_scope)
            for tmp_inner in _attribute_targets(tmp_generator.target):
                self.visit(tmp_inner)
            if tmp_index > 0:
                self.visit(tmp_generator.iter)
            for tmp_condition in tmp_generator.ifs:
                self.visit(tmp_condition)
        if isinstance(node, ast.DictComp):
            self.visit(node.key)
            self.visit(node.value)
        else:
            self.visit(node.elt)
        self._pop()

    def visit_ListComp(self, node: ast.ListComp) -> None:
        """Open the comprehension's scope.

        Args:
            node: The comprehension.
        """
        self._comprehension(node)

    def visit_SetComp(self, node: ast.SetComp) -> None:
        """Open the comprehension's scope.

        Args:
            node: The comprehension.
        """
        self._comprehension(node)

    def visit_GeneratorExp(self, node: ast.GeneratorExp) -> None:
        """Open the comprehension's scope.

        Args:
            node: The comprehension.
        """
        self._comprehension(node)

    def visit_DictComp(self, node: ast.DictComp) -> None:
        """Open the comprehension's scope.

        Args:
            node: The comprehension.
        """
        self._comprehension(node)

    def visit_Global(self, node: ast.Global) -> None:
        """Record the names the scope declares global.

        Args:
            node: The statement.
        """
        self._current().declared.update(node.names)

    def visit_Nonlocal(self, node: ast.Nonlocal) -> None:
        """Record the names the scope declares nonlocal.

        Args:
            node: The statement.
        """
        self._current().declared.update(node.names)

    def visit_Import(self, node: ast.Import) -> None:
        """Bind the imported names; they are no variables.

        Args:
            node: The statement.
        """
        for tmp_alias in node.names:
            self._current().bound.add(
                (tmp_alias.asname or tmp_alias.name).split(".")[0]
            )

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        """Bind the imported names; they are no variables.

        Args:
            node: The statement.
        """
        for tmp_alias in node.names:
            self._current().bound.add(tmp_alias.asname or tmp_alias.name)

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        """Bind the handler's name; it is renamed apart, to ``exception``.

        Args:
            node: The handler.
        """
        if node.name:
            self._current().bound.add(node.name)
        self.generic_visit(node)

    def visit_MatchAs(self, node: ast.MatchAs) -> None:
        """Bind a capture pattern's name, which the rename leaves.

        Args:
            node: The pattern.
        """
        if node.name:
            self._current().bound.add(node.name)
            self._current().blocked.add(node.name)
        self.generic_visit(node)

    def visit_MatchStar(self, node: ast.MatchStar) -> None:
        """Bind a star pattern's name, which the rename leaves.

        Args:
            node: The pattern.
        """
        if node.name:
            self._current().bound.add(node.name)
            self._current().blocked.add(node.name)

    def visit_MatchMapping(self, node: ast.MatchMapping) -> None:
        """Bind a mapping pattern's rest, which the rename leaves.

        Args:
            node: The pattern.
        """
        if node.rest:
            self._current().bound.add(node.rest)
            self._current().blocked.add(node.rest)
        self.generic_visit(node)

    def visit_NamedExpr(self, node: ast.NamedExpr) -> None:
        """Bind a walrus's target in the nearest function, as Python does.

        Args:
            node: The expression.
        """
        tmp_scope = self.scope
        while tmp_scope is not None and tmp_scope.kind == "comprehension":
            tmp_scope = tmp_scope.parent
        self._variable(node.target, tmp_scope)
        self.visit(node.value)

    def visit_Assign(self, node: ast.Assign) -> None:
        """Visit the value, then bind the targets.

        Args:
            node: The statement.
        """
        self.visit(node.value)
        self._targets(node.targets)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        """Visit the value and annotation, then bind the target.

        Args:
            node: The statement.
        """
        if node.value is not None:
            self.visit(node.value)
        self.visit(node.annotation)
        self._targets([node.target])

    def visit_AugAssign(self, node: ast.AugAssign) -> None:
        """Visit the value, then bind the target.

        Args:
            node: The statement.
        """
        self.visit(node.value)
        self._targets([node.target])

    def visit_For(self, node: ast.For) -> None:
        """Visit the iterable, bind the target, then visit the body.

        Args:
            node: The loop.
        """
        self._loop(node)

    def visit_AsyncFor(self, node: ast.AsyncFor) -> None:
        """Visit the iterable, bind the target, then visit the body.

        Args:
            node: The loop.
        """
        self._loop(node)

    def _loop(self, node: ast.For | ast.AsyncFor) -> None:
        """Visit a ``for`` loop.

        Args:
            node: The loop.
        """
        self.visit(node.iter)
        self._targets([node.target])
        for tmp_statement in [*node.body, *node.orelse]:
            self.visit(tmp_statement)

    def visit_With(self, node: ast.With) -> None:
        """Visit each context, bind its target, then visit the body.

        Args:
            node: The statement.
        """
        self._with(node)

    def visit_AsyncWith(self, node: ast.AsyncWith) -> None:
        """Visit each context, bind its target, then visit the body.

        Args:
            node: The statement.
        """
        self._with(node)

    def _with(self, node: ast.With | ast.AsyncWith) -> None:
        """Visit a ``with`` statement.

        Args:
            node: The statement.
        """
        for tmp_item in node.items:
            self.visit(tmp_item.context_expr)
            if tmp_item.optional_vars is not None:
                self._targets([tmp_item.optional_vars])
        for tmp_statement in node.body:
            self.visit(tmp_statement)

    def visit_Name(self, node: ast.Name) -> None:
        """Record a use of a name.

        Args:
            node: The name.
        """
        self._current().names.append(node)


def _attribute_targets(target: ast.expr) -> list[ast.expr]:
    """The attributes and subscripts among a target, which bind no name.

    Args:
        target: The target.

    Returns:
        Them, to be visited as uses.
    """
    if isinstance(target, (ast.Attribute, ast.Subscript)):
        return [target]
    if isinstance(target, (ast.Tuple, ast.List)):
        return [
            tmp_inner
            for tmp_element in target.elts
            for tmp_inner in _attribute_targets(tmp_element)
        ]
    if isinstance(target, ast.Starred):
        return _attribute_targets(target.value)
    return []


def _identifiers(scope: _Scope) -> set[str]:
    """Every name a scope and the scopes inside it bind or use.

    Args:
        scope: The scope.

    Returns:
        The names.
    """
    tmp_found = set(scope.bound) | {tmp_name.id for tmp_name in scope.names}
    for tmp_child in scope.children:
        tmp_found |= _identifiers(tmp_child)
    return tmp_found


def _declared_below(scope: _Scope, name: str) -> bool:
    """Whether a scope inside ``scope`` declares ``name`` global or nonlocal.

    Args:
        scope: The scope.
        name: The name.

    Returns:
        Whether one does.
    """
    return any(
        name in tmp_child.declared or _declared_below(tmp_child, name)
        for tmp_child in scope.children
    )


def _owner(scope: _Scope, name: str) -> _Scope | None:
    """The scope a use of ``name`` in ``scope`` refers to.

    Args:
        scope: Where the name is used.
        name: The name.

    Returns:
        The nearest scope binding it, skipping classes but the first, or
        None for a global or nonlocal declaration or a name bound nowhere.
    """
    tmp_scope: _Scope | None = scope
    tmp_first = True
    while tmp_scope is not None:
        if tmp_scope.kind == "class" and not tmp_first:
            tmp_scope = tmp_scope.parent
            continue
        if name in tmp_scope.declared:
            return None
        if name in tmp_scope.bound:
            return tmp_scope
        tmp_first = False
        tmp_scope = tmp_scope.parent
    return None


def fix(path: str, text: str, lines: frozenset[int], rules: settings.Settings) -> tuple[str, list[str]]:
    """Fix one file's prefixes, exception names, comments and imports.

    Args:
        path: The file's repository path, for messages.
        text: The file's text.
        lines: The lines the change added or modified; only what touches
            them is fixed.
        rules: The repository's settings; no fix needs one today.

    Returns:
        The fixed text, which parses whenever the input does, and one
        ``path:line: why`` sentence per fix that was left. A text that does
        not parse comes back unchanged with one such sentence.
    """
    try:
        ast.parse(text, filename=path)
    except SyntaxError as exception:
        return text, ["%s:%d: does not parse: %s" % (path, exception.lineno or 0, exception.msg)]
    tmp_refused: list[str] = []
    try:
        tmp_text = _fix_prefixes(path, text, lines, tmp_refused)
        tmp_text = _fix_exceptions(path, tmp_text, lines, tmp_refused)
        tmp_text = _fix_comments(tmp_text, lines)
        # Splitting imports adds lines, so it comes after every fix that
        # finds its lines by number.
        tmp_text = _fix_imports(path, tmp_text, lines, tmp_refused)
        ast.parse(tmp_text, filename=path)
    except SyntaxError as exception:
        return text, ["%s:%d: the fixes would not parse; nothing changed" % (path, exception.lineno or 0)]
    return tmp_text, tmp_refused


def _fix_prefixes(path: str, text: str, lines: frozenset[int], refused: list[str]) -> str:
    """Give the variables of every touched scope the prefix, with their uses.

    Args:
        path: The file's path, for messages.
        text: Its text.
        lines: The lines to fix.
        refused: A sentence per rename that was left, which this call adds to.

    Returns:
        The text with the renames.
    """
    tmp_builder = _Builder()
    tmp_tree = ast.parse(text, filename=path)
    tmp_builder.visit(tmp_tree)
    assert tmp_builder.root is not None
    tmp_renames: dict[int, set[str]] = {}
    tmp_in_fstring = _fstring_blocked(tmp_tree)
    tmp_fstring_names: set[tuple[int, str]] = set()

    def find_fstring_uses(scope: _Scope) -> None:
        """Note the variables that an f-string uses in a way a rename breaks.

        Args:
            scope: The scope.
        """
        for tmp_name in scope.names:
            tmp_owner = _owner(scope, tmp_name.id)
            if tmp_owner is not None and id(tmp_name) in tmp_in_fstring:
                tmp_fstring_names.add((id(tmp_owner), tmp_name.id))
        for tmp_child in scope.children:
            find_fstring_uses(tmp_child)

    def plan(scope: _Scope, enclosing_touched: bool) -> None:
        """Choose the variables of ``scope`` and the scopes inside it.

        A comprehension or lambda is part of the text of the function it is
        in, so it counts as touched when that function does; a nested
        ``def`` counts on its own.

        Args:
            scope: The scope.
            enclosing_touched: Whether the scope around it was touched.
        """
        tmp_expression = scope.kind == "comprehension" or isinstance(
            scope.node, ast.Lambda
        )
        tmp_touched = python_rules.touched(scope.node, lines) or (
            tmp_expression and enclosing_touched
        )
        if scope.kind in ("function", "comprehension") and tmp_touched:
            tmp_taken = _identifiers(scope)
            tmp_chosen: set[str] = set()
            for tmp_name in sorted(scope.variables):
                if (
                    tmp_name.startswith(("_", _PREFIX))
                    or tmp_name in scope.declared
                    or tmp_name in scope.parameters
                ):
                    continue
                tmp_reason = ""
                if tmp_name in scope.blocked:
                    tmp_reason = "a match pattern binds it"
                elif _PREFIX + tmp_name in tmp_taken:
                    tmp_reason = "%s%s is taken there" % (_PREFIX, tmp_name)
                elif _declared_below(scope, tmp_name):
                    tmp_reason = "an inner scope declares it nonlocal"
                elif (id(scope), tmp_name) in tmp_fstring_names:
                    tmp_reason = "used in an f-string; rename it by hand"
                if tmp_reason:
                    refused.append(
                        "%s:%d: %s left: %s"
                        % (
                            path,
                            getattr(scope.node, "lineno", 0),
                            tmp_name,
                            tmp_reason,
                        )
                    )
                    continue
                tmp_chosen.add(tmp_name)
            tmp_renames[id(scope)] = tmp_chosen
        for tmp_child in scope.children:
            plan(tmp_child, tmp_touched and scope.kind != "module")

    find_fstring_uses(tmp_builder.root)
    plan(tmp_builder.root, False)
    tmp_edits: set[tuple[int, int, int, str]] = set()

    def collect(scope: _Scope) -> None:
        """Gather the edits for the uses in ``scope`` and the scopes inside.

        Args:
            scope: The scope.
        """
        for tmp_name in scope.names:
            tmp_owner = _owner(scope, tmp_name.id)
            if tmp_owner is not None and tmp_name.id in tmp_renames.get(
                id(tmp_owner), set()
            ):
                tmp_edits.add(
                    (
                        tmp_name.lineno,
                        tmp_name.col_offset,
                        tmp_name.end_col_offset or tmp_name.col_offset,
                        _PREFIX + tmp_name.id,
                    )
                )
        for tmp_child in scope.children:
            collect(tmp_child)

    collect(tmp_builder.root)
    return _apply(text, tmp_edits)


def _fstring_blocked(tree: ast.Module) -> set[int]:
    """The names in f-strings that a rename would break.

    Before Python 3.12 the positions of names inside an f-string are
    unreliable, so every name in one is blocked. From 3.12 on only a name in
    a self-documenting ``{name=}`` field is, since renaming it changes the
    text the f-string prints.

    Args:
        tree: The parsed file.

    Returns:
        The ``id`` of each blocked ``Name`` node.
    """
    tmp_blocked: set[int] = set()
    for tmp_string in ast.walk(tree):
        if not isinstance(tmp_string, ast.JoinedStr):
            continue
        for tmp_index, tmp_part in enumerate(tmp_string.values):
            if not isinstance(tmp_part, ast.FormattedValue):
                continue
            tmp_before = tmp_string.values[tmp_index - 1] if tmp_index else None
            for tmp_name in ast.walk(tmp_part.value):
                if not isinstance(tmp_name, ast.Name):
                    continue
                if sys.version_info < (3, 12) or _self_documenting(tmp_before, tmp_name.id):
                    tmp_blocked.add(id(tmp_name))
    return tmp_blocked


def _self_documenting(before: ast.AST | None, name: str) -> bool:
    """Whether the text before a replacement field spells ``name=``.

    Args:
        before: The part of the f-string before the field.
        name: A name used in the field.

    Returns:
        Whether the field is the self-documenting form of that name.
    """
    return (
        isinstance(before, ast.Constant)
        and isinstance(before.value, str)
        and re.search(r"\b%s\s*=\s*$" % re.escape(name), before.value) is not None
    )


def _apply(text: str, edits: set[tuple[int, int, int, str]]) -> str:
    """Replace byte ranges of lines, last first.

    Args:
        text: The text.
        edits: ``(line, start, end, new)``, the columns in UTF-8 bytes, as
            ``ast`` gives them.

    Returns:
        The edited text.
    """
    tmp_lines = text.encode("utf-8").split(b"\n")
    for tmp_line, tmp_start, tmp_end, tmp_new in sorted(edits, reverse=True):
        tmp_raw = tmp_lines[tmp_line - 1]
        tmp_lines[tmp_line - 1] = (
            tmp_raw[:tmp_start] + tmp_new.encode("utf-8") + tmp_raw[tmp_end:]
        )
    return b"\n".join(tmp_lines).decode("utf-8")


def _fix_exceptions(path: str, text: str, lines: frozenset[int], refused: list[str]) -> str:
    """Name the exception of each handler on a line to fix ``exception``.

    Sibling handlers are all renamed, since Python deletes a handler's name
    after it. A handler is left when the function already uses the name for
    something else, or when it nests with another handler of that name.

    Args:
        path: The file's path, for messages.
        text: The text.
        lines: The lines to fix.
        refused: A sentence per handler that was left, which this call adds to.

    Returns:
        The text with the handlers renamed.
    """
    tmp_tree = ast.parse(text)
    tmp_source = text.encode("utf-8").split(b"\n")
    tmp_edits: set[tuple[int, int, int, str]] = set()
    for tmp_function in ast.walk(tmp_tree):
        if not isinstance(tmp_function, (*_FUNCTIONS, ast.Module)):
            continue
        tmp_handlers = sorted(_own_handlers(tmp_function), key=lambda tmp_item: tmp_item.lineno)
        tmp_foreign = _uses_exception(tmp_function)
        tmp_active = [tmp_item for tmp_item in tmp_handlers if tmp_item.name == "exception"]
        for tmp_handler in tmp_handlers:
            tmp_old = tmp_handler.name
            if (
                not tmp_old
                or tmp_old == "exception"
                or tmp_old.startswith("_")
                or tmp_handler.lineno not in lines
            ):
                continue
            tmp_reason = ""
            tmp_line = tmp_source[tmp_handler.lineno - 1]
            tmp_at = tmp_line.rfind(b" as " + tmp_old.encode("utf-8"))
            if tmp_foreign:
                tmp_reason = "the function already uses the name exception"
            elif any(_nested(tmp_handler, tmp_other) for tmp_other in tmp_active):
                tmp_reason = "it nests with another handler named exception"
            elif tmp_at < 0:
                tmp_reason = "its name is not on the line of its except"
            if tmp_reason:
                refused.append("%s:%d: handler %s left: %s" % (path, tmp_handler.lineno, tmp_old, tmp_reason))
                continue
            tmp_start = tmp_at + len(b" as ")
            tmp_edits.add((tmp_handler.lineno, tmp_start, tmp_start + len(tmp_old.encode("utf-8")), "exception"))
            for tmp_node in ast.walk(ast.Module(tmp_handler.body, [])):
                if isinstance(tmp_node, ast.Name) and tmp_node.id == tmp_old:
                    tmp_edits.add(
                        (
                            tmp_node.lineno,
                            tmp_node.col_offset,
                            tmp_node.end_col_offset or tmp_node.col_offset,
                            "exception",
                        )
                    )
            tmp_active.append(tmp_handler)
    return _apply(text, tmp_edits)


def _uses_exception(scope: ast.AST) -> bool:
    """Whether a function or module uses the name ``exception`` for anything but handlers.

    Args:
        scope: The function or module.

    Returns:
        Whether a name, a parameter or the body of a handler not named
        ``exception`` uses it.
    """
    tmp_inside: set[int] = set()
    for tmp_node in ast.walk(scope):
        if isinstance(tmp_node, ast.ExceptHandler) and tmp_node.name == "exception":
            tmp_inside.update(id(tmp_inner) for tmp_inner in ast.walk(ast.Module(tmp_node.body, [])))
    return any(
        (isinstance(tmp_node, ast.Name) and tmp_node.id == "exception" and id(tmp_node) not in tmp_inside)
        or (isinstance(tmp_node, ast.arg) and tmp_node.arg == "exception")
        for tmp_node in ast.walk(scope)
    )


def _nested(first: ast.ExceptHandler, second: ast.ExceptHandler) -> bool:
    """Whether one handler lies in the body of the other.

    Args:
        first: A handler.
        second: Another handler.

    Returns:
        Whether either contains the other.
    """
    return any(
        tmp_outer is not tmp_inner and tmp_inner in list(ast.walk(ast.Module(tmp_outer.body, [])))
        for tmp_outer, tmp_inner in ((first, second), (second, first))
    )


def _own_handlers(scope: ast.AST) -> list[ast.ExceptHandler]:
    """The handlers directly in a function or module, not in nested ones.

    Args:
        scope: The function or module.

    Returns:
        The handlers.
    """
    tmp_found: list[ast.ExceptHandler] = []
    tmp_pending = list(ast.iter_child_nodes(scope))
    while tmp_pending:
        tmp_node = tmp_pending.pop()
        if isinstance(tmp_node, (*_FUNCTIONS, ast.ClassDef)):
            continue
        if isinstance(tmp_node, ast.ExceptHandler):
            tmp_found.append(tmp_node)
        tmp_pending.extend(ast.iter_child_nodes(tmp_node))
    return tmp_found


def _fix_comments(text: str, lines: frozenset[int]) -> str:
    """Start each comment on a line to fix that starts with ``#:`` with ``#``.

    Args:
        text: The text.
        lines: The lines to fix.

    Returns:
        The text with ``#: words`` as ``# words``.
    """
    tmp_lines = text.split("\n")
    for tmp_line, tmp_comment in python_rules.comments(text).items():
        if tmp_line not in lines or not tmp_comment.startswith("#:"):
            continue
        # A comment runs to the end of its line, so its last occurrence there
        # is the comment, whatever a string before it holds.
        tmp_source = tmp_lines[tmp_line - 1]
        tmp_start = tmp_source.rindex(tmp_comment)
        tmp_words = tmp_comment[2:].strip()
        tmp_lines[tmp_line - 1] = (
            tmp_source[:tmp_start]
            + ("# " + tmp_words if tmp_words else "#")
            + tmp_source[tmp_start + len(tmp_comment) :]
        )
    return "\n".join(tmp_lines)


def _fix_imports(path: str, text: str, lines: frozenset[int], refused: list[str]) -> str:
    """Split each import statement on a line to fix into one per name.

    Only a statement that owns its whole lines is split: nothing before it
    but indentation, nothing after it but a comment, which moves to the
    last new line. Any other is left and reported.

    Args:
        path: The file's path, for messages.
        text: The text.
        lines: The lines to fix.
        refused: A sentence per import that was left, which this call adds to.

    Returns:
        The text with the imports split.
    """
    tmp_lines = text.split("\n")
    tmp_statements = sorted(
        (
            tmp_node
            for tmp_node in ast.walk(ast.parse(text))
            if isinstance(tmp_node, (ast.Import, ast.ImportFrom))
            and len(tmp_node.names) > 1
            and python_rules.touched(tmp_node, lines)
        ),
        key=lambda tmp_node: tmp_node.lineno,
        reverse=True,
    )
    for tmp_statement in tmp_statements:
        tmp_first = tmp_statement.lineno - 1
        tmp_last = (tmp_statement.end_lineno or tmp_statement.lineno) - 1
        tmp_before = tmp_lines[tmp_first].encode("utf-8")[: tmp_statement.col_offset]
        tmp_last_line = tmp_lines[tmp_last]
        tmp_after = tmp_last_line.encode("utf-8")[tmp_statement.end_col_offset or 0 :].decode("utf-8")
        tmp_ending = "\r" if tmp_last_line.endswith("\r") else ""
        tmp_comment = tmp_after.rstrip("\r")
        if tmp_before.strip() or (tmp_comment.strip() and not tmp_comment.strip().startswith("#")):
            refused.append(
                "%s:%d: import left: it shares its line with other code; split it by hand"
                % (path, tmp_statement.lineno)
            )
            continue
        tmp_indent = tmp_before.decode("utf-8")
        tmp_prefix = (
            "from %s%s import " % ("." * tmp_statement.level, tmp_statement.module or "")
            if isinstance(tmp_statement, ast.ImportFrom)
            else "import "
        )
        tmp_split = [
            tmp_indent
            + tmp_prefix
            + tmp_alias.name
            + (" as " + tmp_alias.asname if tmp_alias.asname else "")
            + tmp_ending
            for tmp_alias in tmp_statement.names
        ]
        tmp_split[-1] = tmp_split[-1][: len(tmp_split[-1]) - len(tmp_ending)] + tmp_comment + tmp_ending
        tmp_lines[tmp_first : tmp_last + 1] = tmp_split
    return "\n".join(tmp_lines)
