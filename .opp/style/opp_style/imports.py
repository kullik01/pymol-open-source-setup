"""The import rules: modules, never symbols, and no import cycle.

``from X import Y`` must import a module ``X.Y``, except from
``__future__``, ``typing`` and ``collections.abc``. First-party names are
resolved against the files under the Python roots; third-party names are
resolved by the repository's own interpreter. No module may import, directly
or through others, a module that imports it.
"""

from __future__ import annotations

import ast
import dataclasses
import json
import os
import shutil
import subprocess
import sys
from collections.abc import Iterator
from collections.abc import Mapping

from opp_style import findings
from opp_style import settings

RULE_MODULE = "module-import"
"""The rule's short name for an import of a symbol."""

RULE_CYCLE = "import-cycle"
"""The rule's short name for an import on a cycle."""

SYMBOL_MODULES = frozenset({"__future__", "typing", "collections.abc"})
"""The modules whose symbols may be imported."""

MODULE_SUFFIXES = (".py", ".pyi")
"""The file suffixes of a module."""

SKIPPED_FOLDERS = frozenset({"__pycache__", "node_modules", "site-packages"})
"""The folders no import graph looks into."""

PROBE_TIMEOUT = 60
"""The longest an interpreter may take to resolve a batch of names, in seconds."""

PROBE = """
import importlib.util
import json
import sys

result = {}
for name in json.loads(sys.argv[1]):
    try:
        if importlib.util.find_spec(name.split(".")[0]) is None:
            result[name] = "missing"
            continue
        result[name] = "symbol" if importlib.util.find_spec(name) is None else "module"
    except ModuleNotFoundError as exception:
        missing = exception.name or ""
        symbol = name == missing or name.startswith(missing + ".")
        result[name] = "symbol" if symbol else "missing"
    except Exception:
        result[name] = "missing"
print(json.dumps(result))
"""
"""The program an interpreter runs to tell modules from symbols."""

_RESOLVED: dict[tuple[str, str], str] = {}
"""What each interpreter found for each dotted name: module, symbol or missing."""

_NOTED: set[tuple[str, str]] = set()
"""The interpreter and package pairs already reported as not importable."""


class ImportsError(Exception):
    """The interpreter that resolves third-party imports cannot be run."""


@dataclasses.dataclass(frozen=True)
class _Location:
    """Where a file sits among the Python roots.

    Attributes:
        module: The dotted name of the module, as parts.
        package: The dotted name of the package the file's relative imports
            start from, as parts.
    """

    module: tuple[str, ...]
    package: tuple[str, ...]


@dataclasses.dataclass(frozen=True)
class _Statement:
    """One import statement and the first-party modules it may import.

    Attributes:
        first: The statement's first line.
        last: The statement's last line.
        targets: The modules the statement's edges lead to.
    """

    first: int
    last: int
    targets: tuple[tuple[str, ...], ...]


def _roots(rules: settings.Settings) -> list[str]:
    """Normalize the Python roots.

    Args:
        rules: The repository's settings.

    Returns:
        Each root relative to the repository root, with forward slashes and
        no trailing slash; the repository root itself is an empty string.
    """
    tmp_roots = []
    for tmp_root in rules.python_roots:
        tmp_normal = os.path.normpath(tmp_root).replace(os.sep, "/")
        tmp_roots.append("" if tmp_normal == "." else tmp_normal.strip("/"))
    return tmp_roots


def _locate(path: str, rules: settings.Settings) -> _Location | None:
    """Find a file's module name below the Python roots.

    Args:
        path: The file's repository path.
        rules: The repository's settings.

    Returns:
        The location below the deepest root that holds the file, or None
        when no root holds it.
    """
    tmp_best: str | None = None
    for tmp_root in _roots(rules):
        tmp_prefix = tmp_root + "/" if tmp_root else ""
        if path.startswith(tmp_prefix) and (tmp_best is None or len(tmp_root) > len(tmp_best)):
            tmp_best = tmp_root
    if tmp_best is None:
        return None
    tmp_relative = path[len(tmp_best) + 1 :] if tmp_best else path
    tmp_stem, tmp_suffix = os.path.splitext(tmp_relative)
    if tmp_suffix not in MODULE_SUFFIXES:
        return None
    tmp_parts = tuple(tmp_stem.split("/"))
    if tmp_parts[-1] == "__init__":
        tmp_module = tmp_parts[:-1]
        return _Location(tmp_module, tmp_module)
    return _Location(tmp_parts, tmp_parts[:-1])


def _is_module(parts: tuple[str, ...], rules: settings.Settings) -> bool:
    """Whether dotted parts name a module file under a Python root.

    Args:
        parts: The dotted name, split at the dots.
        rules: The repository's settings.

    Returns:
        Whether ``X/Y.py`` or ``X/Y/__init__.py``, or a ``.pyi`` stub of
        either, exists.
    """
    if not parts:
        return False
    for tmp_root in _roots(rules):
        tmp_base = os.path.join(rules.root, tmp_root, *parts)
        for tmp_suffix in MODULE_SUFFIXES:
            if os.path.isfile(tmp_base + tmp_suffix) or os.path.isfile(os.path.join(tmp_base, "__init__" + tmp_suffix)):
                return True
    return False


def _is_first_party(top: str, rules: settings.Settings) -> bool:
    """Whether a top-level name is a folder or file under a Python root.

    Args:
        top: The name's first part.
        rules: The repository's settings.

    Returns:
        Whether the repository holds it.
    """
    for tmp_root in _roots(rules):
        tmp_base = os.path.join(rules.root, tmp_root, top)
        if os.path.isdir(tmp_base) or any(os.path.isfile(tmp_base + tmp_suffix) for tmp_suffix in MODULE_SUFFIXES):
            return True
    return False


def _resolve_from(node: ast.ImportFrom, location: _Location | None) -> tuple[str, ...] | None:
    """Work out the module a ``from`` statement imports from.

    Args:
        node: The statement.
        location: Where its file sits, for relative imports.

    Returns:
        The dotted module as parts, or None when a relative import cannot be
        resolved.
    """
    tmp_name = tuple(node.module.split(".")) if node.module else ()
    if node.level == 0:
        return tmp_name
    if location is None or node.level - 1 > len(location.package):
        return None
    tmp_keep = len(location.package) - (node.level - 1)
    return location.package[:tmp_keep] + tmp_name


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


def _touches(node: ast.stmt, lines: frozenset[int]) -> bool:
    """Whether a statement spans a judged line.

    Args:
        node: The statement.
        lines: The judged lines.

    Returns:
        Whether any line of the statement is judged.
    """
    return any(tmp_line in lines for tmp_line in range(node.lineno, (node.end_lineno or node.lineno) + 1))


def _symbol_module(module: str, rules: settings.Settings) -> bool:
    """Whether ``from module import Y`` may import symbols.

    Args:
        module: The dotted module name.
        rules: The repository's settings, which may name more such modules.

    Returns:
        Whether the module is one of :data:`SYMBOL_MODULES` or of the
        repository's ``symbol_modules``, or a submodule of one of the latter.
    """
    if module in SYMBOL_MODULES:
        return True
    return any(module == tmp_name or module.startswith(tmp_name + ".") for tmp_name in rules.symbol_modules)


def judge(path: str, text: str, lines: frozenset[int], rules: settings.Settings) -> list[findings.Finding]:
    """Find imported symbols on judged lines.

    Args:
        path: The file's repository path.
        text: The file's text.
        lines: The judged lines, counted from 1.
        rules: The repository's settings.

    Returns:
        One finding per imported name that is a symbol, not a module.

    Raises:
        ImportsError: The interpreter for third-party names cannot run.
    """
    tmp_tree = _parse(text)
    if tmp_tree is None:
        return []
    tmp_location = _locate(path, rules)
    tmp_checks: list[tuple[int, tuple[str, ...], str]] = []
    for tmp_node in ast.walk(tmp_tree):
        if isinstance(tmp_node, ast.ImportFrom) and _touches(tmp_node, lines):
            tmp_source = _resolve_from(tmp_node, tmp_location)
            if tmp_source is None or _symbol_module(".".join(tmp_source), rules):
                continue
            tmp_checks.extend((tmp_node.lineno, tmp_source, tmp_alias.name) for tmp_alias in tmp_node.names)
    tmp_third = {
        ".".join(tmp_source + (tmp_name,))
        for _, tmp_source, tmp_name in tmp_checks
        if tmp_name != "*" and _is_third_party(tmp_source, rules)
    }
    tmp_status = _resolve_third_party(sorted(tmp_third), rules)
    tmp_found = []
    for tmp_line, tmp_source, tmp_name in tmp_checks:
        if tmp_name == "*" or not tmp_source:
            continue
        tmp_dotted = ".".join(tmp_source + (tmp_name,))
        if _is_third_party(tmp_source, rules):
            tmp_symbol = tmp_status.get(tmp_dotted) == "symbol"
        else:
            tmp_symbol = not _is_module(tmp_source + (tmp_name,), rules)
        if tmp_symbol:
            tmp_found.append(
                findings.Finding(
                    path,
                    tmp_line,
                    RULE_MODULE,
                    f"{tmp_name} is a symbol of {'.'.join(tmp_source)}; import the module and use {tmp_name} "
                    "through it",
                )
            )
    return sorted(set(tmp_found))


def _is_third_party(source: tuple[str, ...], rules: settings.Settings) -> bool:
    """Whether an absolute module is not part of the repository.

    Args:
        source: The module the statement imports from, as parts.
        rules: The repository's settings.

    Returns:
        Whether the module's top-level name is not under a Python root.
        A relative import is always first-party; it reaches here already
        resolved to parts under a root.
    """
    return bool(source) and not _is_first_party(source[0], rules)


def _interpreter(rules: settings.Settings) -> str:
    """Find the interpreter that resolves third-party imports.

    Args:
        rules: The repository's settings.

    Returns:
        The interpreter's path or command: the running one, a path relative
        to the repository root, or a command found on the search path.

    Raises:
        ImportsError: The configured command is not on the search path.
    """
    if rules.python_interpreter is None:
        return sys.executable
    if "/" in rules.python_interpreter or os.sep in rules.python_interpreter:
        return os.path.join(rules.root, rules.python_interpreter)
    tmp_found = shutil.which(rules.python_interpreter)
    if tmp_found is None:
        raise ImportsError(f"the interpreter {rules.python_interpreter} is not on the search path")
    return tmp_found


def _resolve_third_party(names: list[str], rules: settings.Settings) -> dict[str, str]:
    """Ask the interpreter whether dotted names are modules or symbols.

    Args:
        names: The dotted names, each ``X.Y`` of ``from X import Y``.
        rules: The repository's settings.

    Returns:
        The status of each name: ``module``, ``symbol`` or ``missing``,
        where ``missing`` means the top-level package cannot be imported.

    Raises:
        ImportsError: The interpreter cannot be started or answers badly.
    """
    if not names:
        return {}
    tmp_interpreter = _interpreter(rules)
    tmp_unknown = [tmp_name for tmp_name in names if (tmp_interpreter, tmp_name) not in _RESOLVED]
    if tmp_unknown:
        for tmp_name, tmp_state in _probe(tmp_interpreter, tmp_unknown, rules.root).items():
            _RESOLVED[(tmp_interpreter, tmp_name)] = tmp_state
    tmp_status = {tmp_name: _RESOLVED[(tmp_interpreter, tmp_name)] for tmp_name in names}
    for tmp_name, tmp_state in tmp_status.items():
        tmp_package = tmp_name.split(".")[0]
        if tmp_state == "missing" and (tmp_interpreter, tmp_package) not in _NOTED:
            _NOTED.add((tmp_interpreter, tmp_package))
            sys.stderr.write(
                f"note: {tmp_package} is not importable by {tmp_interpreter}; its from-imports were not judged\n"
            )
    return tmp_status


def _probe(interpreter: str, names: list[str], root: str) -> dict[str, str]:
    """Run one interpreter once over a batch of names.

    Args:
        interpreter: The interpreter's path.
        names: The dotted names.
        root: The repository's root folder, where the interpreter runs.

    Returns:
        The status of each name.

    Raises:
        ImportsError: The interpreter cannot be started, times out, fails
            or prints something that is not the expected answer.
    """
    try:
        tmp_done = subprocess.run(
            [interpreter, "-c", PROBE, json.dumps(names)],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=PROBE_TIMEOUT,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exception:
        raise ImportsError(f"the interpreter {interpreter} cannot be run: {exception}") from exception
    if tmp_done.returncode != 0:
        raise ImportsError(f"the interpreter {interpreter} failed: {tmp_done.stderr.strip()}")
    try:
        tmp_answer = json.loads(tmp_done.stdout)
    except ValueError as exception:
        raise ImportsError(f"the interpreter {interpreter} gave no answer: {tmp_done.stdout.strip()}") from exception
    if not isinstance(tmp_answer, dict) or not all(tmp_name in tmp_answer for tmp_name in names):
        raise ImportsError(f"the interpreter {interpreter} gave an incomplete answer")
    return {tmp_name: str(tmp_answer[tmp_name]) for tmp_name in names}


def _python_files(rules: settings.Settings) -> list[str]:
    """List the Python files below every Python root.

    Args:
        rules: The repository's settings.

    Returns:
        The repository paths of the files that are not excluded, sorted,
        each listed once.
    """
    tmp_found: set[str] = set()
    for tmp_root in _roots(rules):
        for tmp_folder, tmp_names, tmp_files in os.walk(os.path.join(rules.root, tmp_root)):
            tmp_names[:] = [
                tmp_name for tmp_name in tmp_names if not tmp_name.startswith(".") and tmp_name not in SKIPPED_FOLDERS
            ]
            for tmp_file in tmp_files:
                if not tmp_file.endswith(".py"):
                    continue
                tmp_path = os.path.relpath(os.path.join(tmp_folder, tmp_file), rules.root).replace(os.sep, "/")
                if not rules.excluded(tmp_path) and not tmp_path.startswith(".opp/style/"):
                    tmp_found.add(tmp_path)
    return sorted(tmp_found)


def _read(rules: settings.Settings, path: str) -> str | None:
    """Read a file of the repository.

    Args:
        rules: The repository's settings.
        path: The file's repository path.

    Returns:
        The text, or None when the file cannot be read.
    """
    try:
        with open(os.path.join(rules.root, path), encoding="utf-8", errors="replace") as tmp_file:
            return tmp_file.read()
    except OSError:
        return None


def _statements(
    tree: ast.Module, location: _Location, modules: Mapping[tuple[str, ...], str], rules: settings.Settings
) -> list[_Statement]:
    """Collect the import statements of one module with their targets.

    Args:
        tree: The module's syntax tree.
        location: Where the module sits.
        modules: The first-party modules, each with its file.
        rules: The repository's settings.

    Returns:
        Every import statement of the module, anywhere in it, with the
        first-party modules it leads to.
    """
    tmp_found = []
    for tmp_node in ast.walk(tree):
        tmp_targets: list[tuple[str, ...]] = []
        if isinstance(tmp_node, ast.Import):
            tmp_targets = [tuple(tmp_alias.name.split(".")) for tmp_alias in tmp_node.names]
        elif isinstance(tmp_node, ast.ImportFrom):
            tmp_source = _resolve_from(tmp_node, location)
            if tmp_source is not None:
                tmp_targets = [_from_target(tmp_source, tmp_alias.name, modules) for tmp_alias in tmp_node.names]
        else:
            continue
        tmp_kept = tuple(
            tmp_target for tmp_target in tmp_targets if tmp_target in modules and tmp_target != location.module
        )
        if tmp_kept:
            tmp_found.append(_Statement(tmp_node.lineno, tmp_node.end_lineno or tmp_node.lineno, tmp_kept))
    return tmp_found


def _from_target(
    source: tuple[str, ...], name: str, modules: Mapping[tuple[str, ...], str]
) -> tuple[str, ...]:
    """Pick the module a name of a ``from`` statement leads to.

    Args:
        source: The module the statement imports from.
        name: The imported name.
        modules: The first-party modules.

    Returns:
        ``source.name`` when that is a module, else ``source``.
    """
    tmp_deeper = source + (name,)
    return tmp_deeper if tmp_deeper in modules else source


def _components(graph: Mapping[tuple[str, ...], set[tuple[str, ...]]]) -> dict[tuple[str, ...], int]:
    """Number the strongly connected components of the import graph.

    Args:
        graph: Each module with the modules it imports.

    Returns:
        Each module's component number; two modules on one cycle share one.
    """
    tmp_index: dict[tuple[str, ...], int] = {}
    tmp_low: dict[tuple[str, ...], int] = {}
    tmp_stack: list[tuple[str, ...]] = []
    tmp_on_stack: set[tuple[str, ...]] = set()
    tmp_number: dict[tuple[str, ...], int] = {}
    for tmp_start in sorted(graph):
        if tmp_start in tmp_index:
            continue
        tmp_work: list[tuple[tuple[str, ...], Iterator[tuple[str, ...]]]] = []
        tmp_index[tmp_start] = tmp_low[tmp_start] = len(tmp_index)
        tmp_stack.append(tmp_start)
        tmp_on_stack.add(tmp_start)
        tmp_work.append((tmp_start, iter(sorted(graph[tmp_start]))))
        while tmp_work:
            tmp_node, tmp_children = tmp_work[-1]
            tmp_descended = False
            for tmp_child in tmp_children:
                if tmp_child not in tmp_index:
                    tmp_index[tmp_child] = tmp_low[tmp_child] = len(tmp_index)
                    tmp_stack.append(tmp_child)
                    tmp_on_stack.add(tmp_child)
                    tmp_work.append((tmp_child, iter(sorted(graph[tmp_child]))))
                    tmp_descended = True
                    break
                if tmp_child in tmp_on_stack:
                    tmp_low[tmp_node] = min(tmp_low[tmp_node], tmp_index[tmp_child])
            if tmp_descended:
                continue
            tmp_work.pop()
            if tmp_work:
                tmp_parent = tmp_work[-1][0]
                tmp_low[tmp_parent] = min(tmp_low[tmp_parent], tmp_low[tmp_node])
            if tmp_low[tmp_node] == tmp_index[tmp_node]:
                tmp_id = len(set(tmp_number.values()))
                while True:
                    tmp_member = tmp_stack.pop()
                    tmp_on_stack.discard(tmp_member)
                    tmp_number[tmp_member] = tmp_id
                    if tmp_member == tmp_node:
                        break
    return tmp_number


def _cycle(
    graph: Mapping[tuple[str, ...], set[tuple[str, ...]]],
    components: Mapping[tuple[str, ...], int],
    importer: tuple[str, ...],
    target: tuple[str, ...],
) -> list[tuple[str, ...]]:
    """Find the shortest way back from an import's target to its importer.

    Args:
        graph: Each module with the modules it imports.
        components: Each module's component number.
        importer: The module that holds the import.
        target: The module the import leads to.

    Returns:
        The cycle as modules: the importer, the target, and the way back,
        ending at the importer.
    """
    tmp_before: dict[tuple[str, ...], tuple[str, ...]] = {}
    tmp_queue = [target]
    tmp_seen = {target}
    while tmp_queue and importer not in tmp_before:
        tmp_next = []
        for tmp_module in tmp_queue:
            for tmp_child in sorted(graph[tmp_module]):
                if tmp_child in tmp_seen or components[tmp_child] != components[importer]:
                    continue
                tmp_seen.add(tmp_child)
                tmp_before[tmp_child] = tmp_module
                tmp_next.append(tmp_child)
        tmp_queue = tmp_next
    tmp_way = [importer]
    while tmp_way[-1] != target:
        tmp_way.append(tmp_before[tmp_way[-1]])
    return [importer, *reversed(tmp_way)]


def judge_cycles(changed: Mapping[str, frozenset[int]], rules: settings.Settings) -> list[findings.Finding]:
    """Find imports on judged lines that lie on an import cycle.

    A module that imports itself is not a cycle between modules and is not
    reported.

    Args:
        changed: Each changed file's repository path with its judged lines.
        rules: The repository's settings.

    Returns:
        One finding per import statement and target on a cycle, naming the
        cycle as ``a.b -> a.c -> a.b``.
    """
    tmp_files = _python_files(rules)
    tmp_locations = {tmp_path: _locate(tmp_path, rules) for tmp_path in tmp_files}
    tmp_modules = {
        tmp_location.module: tmp_path for tmp_path, tmp_location in tmp_locations.items() if tmp_location is not None
    }
    tmp_statements: dict[str, list[_Statement]] = {}
    tmp_graph: dict[tuple[str, ...], set[tuple[str, ...]]] = {tmp_module: set() for tmp_module in tmp_modules}
    for tmp_path, tmp_location in tmp_locations.items():
        tmp_text = _read(rules, tmp_path)
        tmp_tree = _parse(tmp_text) if tmp_text is not None else None
        if tmp_location is None or tmp_tree is None or tmp_modules.get(tmp_location.module) != tmp_path:
            continue
        tmp_statements[tmp_path] = _statements(tmp_tree, tmp_location, tmp_modules, rules)
        for tmp_statement in tmp_statements[tmp_path]:
            tmp_graph[tmp_location.module].update(tmp_statement.targets)
    tmp_components = _components(tmp_graph)
    tmp_found = []
    for tmp_path, tmp_lines in sorted(changed.items()):
        tmp_location = tmp_locations.get(tmp_path)
        if tmp_location is None:
            continue
        for tmp_statement in tmp_statements.get(tmp_path, []):
            if not any(tmp_line in tmp_lines for tmp_line in range(tmp_statement.first, tmp_statement.last + 1)):
                continue
            for tmp_target in tmp_statement.targets:
                if tmp_components[tmp_target] != tmp_components[tmp_location.module]:
                    continue
                tmp_way = _cycle(tmp_graph, tmp_components, tmp_location.module, tmp_target)
                tmp_found.append(
                    findings.Finding(
                        tmp_path,
                        tmp_statement.first,
                        RULE_CYCLE,
                        "the import closes a cycle, " + " -> ".join(".".join(tmp_part) for tmp_part in tmp_way)
                        + "; move what the modules share into a lower module",
                    )
                )
    return sorted(set(tmp_found))
