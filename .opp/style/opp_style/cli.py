"""The checker's command line: ``python3 .opp/style/check.py``.

::

    python3 .opp/style/check.py                    # changes since origin/main
    python3 .opp/style/check.py --committed        # HEAD alone, as a push check
    python3 .opp/style/check.py --base main src/x.py
    python3 .opp/style/check.py --all              # whole files, a catch-up
    python3 .opp/style/check.py --fix              # fix what needs no words

It judges the Python and C++ lines a change added or modified since the
merge base with ``--base`` -- in the working tree, untracked files included,
or with ``--committed`` in ``HEAD`` alone -- or with ``--all`` every line of
the tracked files, and prints each finding as ``path:line: rule message``.
It exits 0 when no rule is broken, 1 when one is, and 2 when it cannot
judge: the installed copy differs from its ``MANIFEST.json``, git fails,
the settings cannot be read, a changed file is not UTF-8
or does not parse with the running Python, or a C++ file changed and no
pinned clang-format can be found. It never skips a check it cannot run.
The import-cycle rule reads the import graph from the working tree, which
a push check's clean tree makes the same as ``HEAD``.
"""

from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Sequence

from opp_style import changes
from opp_style import clang_format
from opp_style import cpp_rules
from opp_style import findings
from opp_style import fixer
from opp_style import hygiene
from opp_style import imports
from opp_style import manifest
from opp_style import python_rules
from opp_style import settings

ALWAYS_EXCLUDED = (".opp/style/**",)
"""The paths never judged: the installed checker itself, which the kit judges."""

DEFAULT_BASE = "origin/main"
"""The reference a change is judged against when none is given."""


class CannotJudge(Exception):
    """The checker cannot judge the change; it exits 2."""


def main(arguments: Sequence[str]) -> int:
    """Run the checker.

    Args:
        arguments: The command line after the script's name.

    Returns:
        0 when no rule is broken, 1 when one is, 2 when the checker cannot
        judge.
    """
    tmp_options = _parser().parse_args(list(arguments))
    try:
        _verify_self()
        tmp_root = changes.repository_root(os.getcwd())
        tmp_settings = settings.load(tmp_root)
        tmp_judged = _judged(tmp_root, tmp_settings, tmp_options)
        if tmp_options.fix:
            return _fix(tmp_root, tmp_settings, tmp_judged)
        tmp_found = judge(tmp_root, tmp_settings, tmp_judged, tmp_options.committed)
    except (
        CannotJudge,
        changes.ChangesError,
        settings.SettingsError,
        clang_format.ToolMissing,
        imports.ImportsError,
    ) as exception:
        sys.stderr.write(f"style check cannot run: {exception}\n")
        return 2
    for tmp_finding in tmp_found:
        print(tmp_finding.render())
    if tmp_found:
        print(
            f"{len(tmp_found)} findings; `python3 .opp/style/check.py --fix` fixes the tmp_ names, "
            "exception names, one name per import and #: comments; the rest needs words."
        )
        return 1
    return 0


def _verify_self() -> None:
    """Refuse to judge with an installed copy that differs from its manifest.

    The kit's own source carries no manifest and is not verified; a copy that
    ``style-install`` wrote must hold exactly the files it recorded.

    Raises:
        CannotJudge: The manifest cannot be read, or a file was edited,
            removed or added by hand.
    """
    tmp_folder = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    try:
        tmp_record = manifest.read(tmp_folder)
    except manifest.ManifestError as exception:
        raise CannotJudge(f"the installed checker's {exception}") from exception
    if tmp_record is None:
        return
    tmp_edited = manifest.edited(tmp_folder, tmp_record)
    if tmp_edited:
        raise CannotJudge(
            f"the installed checker differs from its {manifest.NAME} ({', '.join(tmp_edited)}); restore it "
            "with git, or change the rule in opp-agent-kit and run `opp-workflow style-install`"
        )


def _parser() -> argparse.ArgumentParser:
    """Describe the command line.

    Returns:
        The parser.
    """
    tmp_parser = argparse.ArgumentParser(
        prog="check.py", description="Judge a change's Python and C++ lines by the OPP family's style rules."
    )
    tmp_parser.add_argument("--base", default=DEFAULT_BASE, help="the reference the change is judged against")
    tmp_parser.add_argument("--committed", action="store_true", help="judge HEAD alone, without uncommitted edits")
    tmp_parser.add_argument("--all", action="store_true", help="judge every line of the tracked files")
    tmp_parser.add_argument("--fix", action="store_true", help="fix what needs no words, then stop")
    tmp_parser.add_argument("paths", nargs="*", help="limit the run to these files and folders")
    return tmp_parser


def _judged(root: str, rules: settings.Settings, options: argparse.Namespace) -> changes.Change:
    """Decide which files and lines the run judges.

    Args:
        root: The repository's root folder.
        rules: The repository's settings.
        options: The parsed command line.

    Returns:
        The judged files with their judged lines, and which are new.
    """
    tmp_wanted = {_repository_path(root, tmp_path) for tmp_path in options.paths}
    if options.all:
        tmp_lines = {}
        for tmp_path in changes.tracked_files(root):
            tmp_text = changes.read(root, tmp_path, options.committed)
            if tmp_text is not None:
                tmp_lines[tmp_path] = frozenset(range(1, tmp_text.count("\n") + 2))
        tmp_change = changes.Change(tmp_lines, frozenset(tmp_lines))
    else:
        tmp_change = changes.changed(root, changes.merge_base(root, options.base), options.committed)
    tmp_kept = {
        tmp_path: tmp_value
        for tmp_path, tmp_value in tmp_change.lines.items()
        if _judgeable(tmp_path, rules) and _wanted(tmp_path, tmp_wanted)
    }
    for tmp_named in sorted(tmp_wanted):
        if not any(_wanted(tmp_path, {tmp_named}) for tmp_path in tmp_kept):
            sys.stderr.write(f"note: {tmp_named} names no changed Python or C++ file this run judges\n")
    return changes.Change(tmp_kept, tmp_change.new & frozenset(tmp_kept))


def _wanted(path: str, wanted: set[str]) -> bool:
    """Whether the command line's paths include a file.

    Args:
        path: The file's repository path.
        wanted: The paths named on the command line, files or folders; none,
            or the root ``.``, names every file.

    Returns:
        Whether no path was named, or one names the file or a folder above it.
    """
    if not wanted or "." in wanted:
        return True
    return any(path == tmp_wanted or path.startswith(tmp_wanted.rstrip("/") + "/") for tmp_wanted in wanted)


def _repository_path(root: str, path: str) -> str:
    """Turn a path on the command line into a repository path.

    Args:
        root: The repository's root folder.
        path: The path, relative to the working folder or absolute.

    Returns:
        The path relative to the root, with forward slashes; ``.`` for the
        root itself.

    Raises:
        CannotJudge: The path is outside the repository.
    """
    tmp_relative = os.path.relpath(os.path.abspath(path), root)
    if tmp_relative == os.pardir or tmp_relative.startswith(os.pardir + os.sep):
        raise CannotJudge(f"{path} is outside the repository")
    return tmp_relative.replace(os.sep, "/")


def _judgeable(path: str, rules: settings.Settings) -> bool:
    """Whether a file is Python or C++ that the run judges.

    Args:
        path: The file's repository path.
        rules: The repository's settings.

    Returns:
        Whether a rule judges it.
    """
    if not path.endswith(settings.PYTHON_SUFFIXES + settings.CPP_SUFFIXES):
        return False
    if rules.excluded(path) or settings.Settings(root="", exclude=ALWAYS_EXCLUDED).excluded(path):
        return False
    return not (path.endswith(settings.CPP_SUFFIXES) and rules.legacy(path))


def judge(root: str, rules: settings.Settings, judged: changes.Change, committed: bool) -> list[findings.Finding]:
    """Judge the files and lines of a run.

    Args:
        root: The repository's root folder.
        rules: The repository's settings.
        judged: The judged files, lines and new files.
        committed: Whether to read the files from ``HEAD``.

    Returns:
        Every finding, sorted.
    """
    tmp_found: list[findings.Finding] = []
    tmp_python: dict[str, frozenset[int]] = {}
    tmp_cpp: dict[str, frozenset[int]] = {}
    for tmp_path, tmp_lines in sorted(judged.lines.items()):
        if not tmp_lines:
            continue
        tmp_text = changes.read(root, tmp_path, committed)
        if tmp_text is None:
            raise CannotJudge(f"{tmp_path} cannot be read as UTF-8 text")
        if tmp_path.endswith(settings.PYTHON_SUFFIXES):
            tmp_python[tmp_path] = tmp_lines
            tmp_rules_found = python_rules.judge(tmp_path, tmp_text, tmp_lines, rules)
            for tmp_finding in tmp_rules_found:
                if tmp_finding.rule == "syntax":
                    raise CannotJudge(
                        f"{tmp_path}:{tmp_finding.line} does not parse with Python "
                        f"{sys.version_info[0]}.{sys.version_info[1]} ({tmp_finding.message}); run the checker "
                        "with the Python the repository targets, or fix the syntax"
                    )
            tmp_found.extend(tmp_rules_found)
            tmp_found.extend(hygiene.judge(tmp_path, tmp_text, tmp_lines, rules))
            tmp_found.extend(imports.judge(tmp_path, tmp_text, tmp_lines, rules))
        else:
            tmp_cpp[tmp_path] = tmp_lines
            tmp_found.extend(cpp_rules.judge(tmp_path, tmp_text, tmp_lines, rules, tmp_path in judged.new))
    if tmp_python:
        tmp_found.extend(imports.judge_cycles(tmp_python, rules))
    if tmp_cpp:
        tmp_found.extend(clang_format.judge(tmp_cpp, rules, committed))
    return sorted(
        tmp_finding for tmp_finding in set(tmp_found) if not rules.off(tmp_finding.rule, tmp_finding.path)
    )


def _fix(root: str, rules: settings.Settings, judged: changes.Change) -> int:
    """Fix the changed Python lines' findings that need no words.

    Args:
        root: The repository's root folder.
        rules: The repository's settings.
        judged: The judged files and lines.

    Returns:
        0 when every fix applied, 1 when some were left, with each printed.
    """
    tmp_left = 0
    for tmp_path, tmp_lines in sorted(judged.lines.items()):
        if not tmp_path.endswith(settings.PYTHON_SUFFIXES) or not tmp_lines:
            continue
        tmp_full = os.path.join(root, tmp_path)
        try:
            # newline="" keeps the file's own line endings through the fix.
            with open(tmp_full, encoding="utf-8", newline="") as tmp_file:
                tmp_text = tmp_file.read()
        except (OSError, UnicodeDecodeError) as exception:
            raise CannotJudge(f"{tmp_path} cannot be read as UTF-8 text: {exception}") from exception
        tmp_fixed, tmp_problems = fixer.fix(tmp_path, tmp_text, tmp_lines, rules)
        if tmp_fixed != tmp_text:
            try:
                with open(tmp_full, "w", encoding="utf-8", newline="") as tmp_file:
                    tmp_file.write(tmp_fixed)
            except OSError as exception:
                raise CannotJudge(f"{tmp_path} cannot be written: {exception}") from exception
            print(f"fixed {tmp_path}")
        for tmp_problem in tmp_problems:
            print(tmp_problem)
        tmp_left += len(tmp_problems)
    if tmp_left:
        print(f"{tmp_left} fixes left to the author")
    print("Run the repository's formatter on the fixed files, since a renamed line may grow past the limit.")
    return 1 if tmp_left else 0
