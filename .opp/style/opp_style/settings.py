"""The repository's style settings: the ``style`` key of ``.opp/config.json``.

Every key is optional; a repository without one is judged by the family
defaults::

    "style": {
      "include": ["src/python/**", "test/**"],
      "exclude": ["third_party/**"],
      "python": {
        "roots": ["src/python"],
        "interpreter": ".venv/bin/python",
        "abbreviations": ["dat"],
        "citation_exceptions": [],
        "line_length": 80,
        "suppression_issue": "https://github\\\\.com/owner/repo/issues/\\\\d+",
        "symbol_modules": ["pymol.Qt"]
      },
      "cpp": {
        "legacy": ["src/cpp/layer*/**"],
        "licence": ["@copyright", "SPDX-License-Identifier:"]
      },
      "rules_off": {"suppression": ["python/pymol_plugin/**"]}
    }

A path glob is matched against the repository path with :func:`fnmatch`,
whose ``*`` also matches ``/``, so ``src/cpp/**`` names everything below
``src/cpp``.
"""

from __future__ import annotations

import dataclasses
import fnmatch
import json
import os
import re
from collections.abc import Mapping

CONFIG_FILE = os.path.join(".opp", "config.json")
"""The repository's opp-workflow settings, relative to its root."""

ABBREVIATIONS = frozenset(
    {
        "args",
        "attr",
        "btn",
        "buf",
        "cb",
        "cfg",
        "cnt",
        "ctx",
        "dct",
        "dst",
        "el",
        "elem",
        "err",
        "ev",
        "evt",
        "exc",
        "fh",
        "fn",
        "fp",
        "func",
        "idx",
        "img",
        "info",
        "kwargs",
        "lbl",
        "lst",
        "msg",
        "num",
        "obj",
        "param",
        "params",
        "pos",
        "ptr",
        "rect",
        "res",
        "ret",
        "src",
        "str",
        "val",
    }
)
"""The names after ``tmp_`` that are abbreviations, not whole words."""

LINE_LENGTH = 80
"""The longest changed Python line, in characters."""

SUPPRESSION_ISSUE = r"https://github\.com/[\w.-]+/[\w.-]+/issues/\d+"
"""The link a suppression needs: any GitHub issue."""

CPP_LICENCE = ("@copyright", "SPDX-License-Identifier:")
"""The texts a new C++ file's ``@file`` block holds."""

PYTHON_SUFFIXES = (".py",)
"""The suffixes of the Python files the checker judges."""

CPP_SUFFIXES = (".h", ".hh", ".hpp", ".hxx", ".c", ".cc", ".cpp", ".cxx")
"""The suffixes of the C and C++ files the checker judges."""


class SettingsError(Exception):
    """The ``style`` settings cannot be read; the checker cannot run."""


@dataclasses.dataclass(frozen=True)
class Settings:
    """What the rules take from the repository.

    Attributes:
        root: The repository's root folder, absolute.
        include: Path globs the rules judge; empty means every path.
        exclude: Path globs no rule judges, even when included.
        python_roots: The folders, relative to the root, that hold the
            repository's own Python packages; imports resolve against them.
        python_interpreter: The interpreter third-party imports resolve
            with, or None for the one running the checker.
        abbreviations: The names after ``tmp_`` that are abbreviations.
        citation_exceptions: The short ids that are not record ids.
        line_length: The longest changed Python line, in characters.
        suppression_issue: The regular expression of the link a suppression
            needs.
        cpp_legacy: Path globs of C++ sources that keep their own style.
        cpp_licence: The texts a new C++ file's ``@file`` block holds.
        symbol_modules: Modules besides ``__future__``, ``typing`` and
            ``collections.abc`` that ``from X import Y`` may import symbols
            from, with their submodules.
        rules_off: Each rule a repository turns off for some paths, with
            those paths' globs.
    """

    root: str
    include: tuple[str, ...] = ()
    exclude: tuple[str, ...] = ()
    python_roots: tuple[str, ...] = (".",)
    python_interpreter: str | None = None
    abbreviations: frozenset[str] = ABBREVIATIONS
    citation_exceptions: frozenset[str] = frozenset()
    line_length: int = LINE_LENGTH
    suppression_issue: str = SUPPRESSION_ISSUE
    cpp_legacy: tuple[str, ...] = ()
    cpp_licence: tuple[str, ...] = CPP_LICENCE
    symbol_modules: frozenset[str] = frozenset()
    rules_off: tuple[tuple[str, tuple[str, ...]], ...] = ()

    def off(self, rule: str, path: str) -> bool:
        """Whether the repository turned a rule off for a file.

        Args:
            rule: The rule's short name.
            path: The file's repository path.

        Returns:
            Whether :attr:`rules_off` names the rule with a glob matching the
            path.
        """
        return any(tmp_rule == rule and _matches(path, tmp_globs) for tmp_rule, tmp_globs in self.rules_off)

    def excluded(self, path: str) -> bool:
        """Whether no rule judges a file.

        Args:
            path: The file's repository path.

        Returns:
            Whether :attr:`include` names globs and none matches the path,
            or one of :attr:`exclude` matches it.
        """
        if self.include and not _matches(path, self.include):
            return True
        return _matches(path, self.exclude)

    def legacy(self, path: str) -> bool:
        """Whether a C++ file keeps its own style.

        Args:
            path: The file's repository path.

        Returns:
            Whether the path matches one of :attr:`cpp_legacy`.
        """
        return _matches(path, self.cpp_legacy)


def _matches(path: str, globs: tuple[str, ...]) -> bool:
    """Whether a path matches one of some globs.

    Args:
        path: The repository path.
        globs: The globs.

    Returns:
        Whether one glob matches.
    """
    return any(fnmatch.fnmatchcase(path, tmp_glob) for tmp_glob in globs)


def load(root: str) -> Settings:
    """Read the repository's settings.

    Args:
        root: The repository's root folder.

    Returns:
        The settings, with the family defaults where the file names none.

    Raises:
        SettingsError: The file is not JSON, or a key has the wrong type.
    """
    tmp_root = os.path.abspath(root)
    tmp_path = os.path.join(tmp_root, CONFIG_FILE)
    try:
        with open(tmp_path, encoding="utf-8") as tmp_file:
            tmp_config = json.load(tmp_file)
    except FileNotFoundError:
        return Settings(root=tmp_root)
    except (OSError, ValueError) as exception:
        raise SettingsError(f"{CONFIG_FILE} cannot be read: {exception}") from exception
    tmp_style = _mapping(tmp_config, "style", "")
    tmp_python = _mapping(tmp_style, "python", "style.")
    tmp_cpp = _mapping(tmp_style, "cpp", "style.")
    tmp_interpreter = tmp_python.get("interpreter")
    if tmp_interpreter is not None and not isinstance(tmp_interpreter, str):
        raise SettingsError("style.python.interpreter must be a string")
    tmp_line_length = tmp_python.get("line_length", LINE_LENGTH)
    if not isinstance(tmp_line_length, int) or isinstance(tmp_line_length, bool):
        raise SettingsError("style.python.line_length must be a whole number")
    tmp_issue = tmp_python.get("suppression_issue", SUPPRESSION_ISSUE)
    if not isinstance(tmp_issue, str):
        raise SettingsError("style.python.suppression_issue must be a string")
    try:
        re.compile(tmp_issue)
    except re.error as exception:
        raise SettingsError(f"style.python.suppression_issue is no regular expression: {exception}") from exception
    tmp_off = _mapping(tmp_style, "rules_off", "style.")
    tmp_rules_off = tuple(
        (tmp_rule, _strings(tmp_off, tmp_rule, "style.rules_off.")) for tmp_rule in sorted(tmp_off)
    )
    tmp_roots = _strings(tmp_python, "roots", "style.python.") or (".",)
    tmp_licence = _strings(tmp_cpp, "licence", "style.cpp.") or CPP_LICENCE
    return Settings(
        root=tmp_root,
        include=_strings(tmp_style, "include", "style."),
        exclude=_strings(tmp_style, "exclude", "style."),
        python_roots=tmp_roots,
        python_interpreter=tmp_interpreter,
        abbreviations=ABBREVIATIONS | frozenset(_strings(tmp_python, "abbreviations", "style.python.")),
        citation_exceptions=frozenset(_strings(tmp_python, "citation_exceptions", "style.python.")),
        line_length=tmp_line_length,
        suppression_issue=tmp_issue,
        cpp_legacy=_strings(tmp_cpp, "legacy", "style.cpp."),
        cpp_licence=tmp_licence,
        symbol_modules=frozenset(_strings(tmp_python, "symbol_modules", "style.python.")),
        rules_off=tmp_rules_off,
    )


def _mapping(parent: object, key: str, prefix: str) -> Mapping[str, object]:
    """Read an optional object from the settings.

    Args:
        parent: The object that may hold it.
        key: Its key.
        prefix: The keys above it, for the message.

    Returns:
        The object, or an empty one when it is absent.

    Raises:
        SettingsError: It is not an object.
    """
    if not isinstance(parent, Mapping):
        raise SettingsError(f"{prefix.rstrip('.') or 'the settings'} must be an object")
    tmp_value = parent.get(key, {})
    if not isinstance(tmp_value, Mapping):
        raise SettingsError(f"{prefix}{key} must be an object")
    return tmp_value


def _strings(parent: Mapping[str, object], key: str, prefix: str) -> tuple[str, ...]:
    """Read an optional list of strings from the settings.

    Args:
        parent: The object that may hold it.
        key: Its key.
        prefix: The keys above it, for the message.

    Returns:
        The strings, or none when the key is absent.

    Raises:
        SettingsError: It is not a list of strings.
    """
    tmp_value = parent.get(key, [])
    if not isinstance(tmp_value, list) or not all(isinstance(tmp_item, str) for tmp_item in tmp_value):
        raise SettingsError(f"{prefix}{key} must be a list of strings")
    return tuple(tmp_value)
