#!/usr/bin/env python3
# pymake - A zero-dependency, Python-based task runner
# -------------------------------------------------------------------
# This file contains source code for the pymake computer program
# Copyright (C) 2025 Martin Urban (martin.urban@studmail.w-hs.de)
# Source code is available at <https://github.com/urban233/pymake>
# -------------------------------------------------------------------
# It is unlawful to modify or remove this copyright notice.
# -------------------------------------------------------------------
# Please see the accompanying LICENSE file for further information.
# -------------------------------------------------------------------
# Additional authors of this source file include:
#
# ==============================================================================
#
"""Standalone Python task runner.

A zero-dependency, production-ready task runner that replicates the ergonomics
of tools like ``invoke`` or GNU ``make`` using only the Python standard library.
Tasks are plain Python functions decorated with ``@task``; the CLI dispatcher
parses positional and keyword arguments and routes execution accordingly.

Typical usage::

    chmod +x pymake.bat/sh

    ./pymake.bat/sh                   # Print the help menu
    ./pymake.bat/sh test              # Run with defaults
    ./pymake.bat/sh test verbose=true # Pass keyword argument
    ./pymake.bat/sh build env=prod    # Override default keyword argument

Design principles:
    - **Portability**: Only the Python standard library is used (Python ≥ 3.8).
    - **Discoverability**: ``--help`` / ``-h`` renders a formatted task menu
      derived from each task's docstring automatically.
    - **Composability**: Tasks are ordinary functions; calling one task from
      another is idiomatic Python—no special API is required.
    - **Fail-fast**: Shell commands raise immediately on non-zero exit codes
      unless ``check=False`` is explicitly requested.
    - **Style compliance**: Follows the `Google Python Style Guide
      <https://google.github.io/styleguide/pyguide.html>`_ throughout.
"""

import inspect
import os
import pathlib
import platform
import shlex
import shutil
import subprocess
import sys
import sysconfig
import textwrap
from typing import Callable

# <editor-fold desc="pymake">
# <editor-fold desc="Type aliases">
# A task callable as stored in the registry.
_TaskFunc = Callable[..., None]
# </editor-fold>

# Absolute repository root so tasks work regardless of the caller's directory.
_PROJECT_ROOT = pathlib.Path(__file__).resolve().parent

# <editor-fold desc="Module-level task registry">
# Maps task name → registered callable.  Insertion order is preserved (Python
# 3.7+) so the help menu reflects the order tasks are declared in the file.
_TASKS: dict[str, _TaskFunc] = {}
# </editor-fold>

# <editor-fold desc="ANSI color helpers">
# Colour codes used for terminal output.  These are intentionally kept as
# simple constants rather than a third-party library to preserve portability.
_COLOR_GREY = "\033[90m"
_COLOR_RED = "\033[91m"
_COLOR_GREEN = "\033[92m"
_COLOR_YELLOW = "\033[93m"
_COLOR_RESET = "\033[0m"
# </editor-fold>


def _colorize(text: str, color_code: str) -> str:
  """Wraps ``text`` in the given ANSI ``color_code`` and a reset sequence.

  When stdout is not a TTY (e.g. a CI log file or a pipe) the raw text is
  returned unchanged so log output stays human-readable without escape noise.

  Args:
      text: The string to colorise.
      color_code: An ANSI escape sequence string, e.g. ``"\\033[90m"``.

  Returns:
      The colorised string when connected to a TTY; otherwise ``text``
      unchanged.
  """
  if sys.stdout.isatty():
    return f"{color_code}{text}{_COLOR_RESET}"
  return text


def task(func: _TaskFunc) -> _TaskFunc:
  """Registers a callable as a named CLI task.

  The function name becomes the task's CLI name.  Its signature drives
  argument parsing and its docstring populates the ``--help`` output.

  Example:

      @task
      def lint(fix: str = "false") -> None:
          '''Lint the codebase. Pass fix=true to auto-fix issues.'''
          run(f"ruff check {'--fix' if fix == 'true' else ''} .")

  Args:
      func: The function to register.  Must accept only positional and/or
          keyword parameters with default values; ``*args`` / ``**kwargs``
          are unsupported.

  Returns:
      The original ``func`` unmodified (the decorator is transparent).

  Raises:
      ValueError: If a task with the same name has already been registered,
          which typically indicates a copy-paste error in the task file.
  """
  if func.__name__ in _TASKS:
    raise ValueError(
      f"Duplicate task name '{func.__name__}': a task with this name is "
      "already registered.  Rename one of the conflicting functions."
    )
  _TASKS[func.__name__] = func
  return func


def run(
        cmd: str,
        *,
        check: bool = True,
        capture: bool = False,
        env: dict[str, str] | None = None,
        cwd: pathlib.Path | None = None,
) -> str | None:
  """Executes a shell command, printing it to stdout before running.

  This helper is the primary interface for invoking external processes from
  within tasks.  It mirrors the ergonomics of ``invoke.run`` while remaining
  standard-library-only.

  The command is printed in grey before execution so developers can trace
  exactly which shell invocations a composite task triggers.  When ``check``
  is ``True`` (the default) a non-zero exit code raises
  ``subprocess.CalledProcessError``, which propagates up and terminates the
  runner with a non-zero exit status—consistent with GNU Make semantics.

  Args:
      cmd: The shell command string to execute.  Passed to ``/bin/sh -c``
          (or the platform equivalent) via ``shell=True``.
      check: If ``True`` (default), raise ``subprocess.CalledProcessError``
          on non-zero exit code.  Set to ``False`` to tolerate failures.
      capture: If ``True``, capture stdout and return it as a stripped
          string instead of streaming it to the terminal.  Useful when the
          output of a command is needed programmatically.
      env: Optional mapping of environment variables to pass to the child
          process.  When ``None``, the parent environment is inherited.
      cwd: Optional working directory for the child process.  When ``None``,
          the caller's working directory is inherited.

  Returns:
      The captured stdout string (stripped of leading/trailing whitespace)
      when ``capture=True``.  ``None`` otherwise.

  Raises:
      subprocess.CalledProcessError: When ``check=True`` and the command
          exits with a non-zero status code.

  Example:

      # Stream output to terminal (most common usage).
      run("pytest -v")

      # Capture and use programmatically.
      git_hash = run("git rev-parse --short HEAD", capture=True)
      print(f"Current commit: {git_hash}")

      # Tolerate failure (e.g. optional clean-up step).
      run("pkill -f my_server", check=False)
  """
  print(_colorize(f"$ {cmd}", _COLOR_GREY))
  result = subprocess.run(
    cmd,
    shell=True,
    check=check,
    capture_output=capture,
    text=True,
    env=env,
    cwd=cwd,
  )
  if capture:
    return result.stdout.strip()
  return None


def _run_process(args: list[str], *, cwd: pathlib.Path | None = None) -> None:
  """Runs an executable with an argument list and fails on errors."""
  print(_colorize(f"$ {shlex.join(args)}", _COLOR_GREY))
  subprocess.run(args, check=True, cwd=cwd)


def _platform_build_paths() -> tuple[pathlib.Path, pathlib.Path, str]:
  """Returns the platform directory, PyMOL package, and build command."""
  system = platform.system()
  if system == "Windows":
    platform_dir = _PROJECT_ROOT / "os_specific/windows"
    build_command = "build_exe"
  elif system == "Darwin":
    platform_dir = _PROJECT_ROOT / "os_specific/macos"
    build_command = "bdist_mac"
  elif system == "Linux":
    platform_dir = _PROJECT_ROOT / "os_specific/linux"
    build_command = "build_exe"
  else:
    raise RuntimeError(f"Unsupported platform: {system}")

  package_dir = pathlib.Path(sysconfig.get_path("purelib")) / "pymol"
  return platform_dir, package_dir, build_command


def _copy_build_customizations(package_dir: pathlib.Path) -> None:
  """Copies repository-specific files into the installed PyMOL package."""
  project_root = _PROJECT_ROOT
  platform_name = {
    "Windows": "windows",
    "Darwin": "macos",
    "Linux": "linux",
  }[platform.system()]
  copies = {
    project_root / "edited/pmg_qt/pymol_qt_gui.py":
      package_dir.parent / "pmg_qt/pymol_qt_gui.py",
    project_root / "edited/pymol/data/pymol/base.css":
      package_dir / "base.css",
    project_root / "edited/pymol/__init__.py": package_dir / "__init__.py",
    project_root / "edited/pymol/startup_wrapper.py":
      package_dir / "startup_wrapper.py",
    project_root / "alternative_design/alt_logo.png":
      package_dir / "data/pymol/icons/alt_logo.png",
    project_root / "os_specific" / platform_name / "splash.png":
      package_dir / "data/pymol/splash.png",
  }
  for source, destination in copies.items():
    shutil.copy(source, destination)


def _prepare_inno_setup_environment() -> None:
  """Creates the temporary source and asset tree used by Inno Setup."""
  project_root = _PROJECT_ROOT
  build_path = project_root / "inno-build-release"
  build_source_path = build_path / "inno-sources"
  build_assets_path = build_path / "inno-assets"
  python_version = f"{sys.version_info.major}.{sys.version_info.minor}"
  app_build_path = project_root / f"dist/exe.win-amd64-{python_version}"
  logo_path = project_root / "os_specific/windows/logo.ico"
  redistributable_path = project_root / "vendor/microsoft/VC_redist.x64.exe"

  required_paths = (app_build_path, logo_path, redistributable_path)
  missing_paths = [path for path in required_paths if not path.exists()]
  if missing_paths:
    missing = ", ".join(str(path) for path in missing_paths)
    raise FileNotFoundError(
      f"Cannot prepare Inno Setup; missing {missing}. Run build_app first."
    )

  if build_path.exists():
    shutil.rmtree(build_path)
  build_assets_path.mkdir(parents=True)
  shutil.copytree(app_build_path, build_source_path)
  shutil.copy(redistributable_path, build_source_path)
  shutil.copy(logo_path, build_assets_path / "logo.ico")


@task
def build_app() -> None:
  """Build the frozen PyMOL application for the current platform."""
  platform_dir, package_dir, build_command = _platform_build_paths()
  if not package_dir.exists():
    raise FileNotFoundError(
      f"PyMOL is not installed in the active environment: {package_dir}"
    )

  _copy_build_customizations(package_dir)
  build_script = platform_dir / "setup_build_exe.py"
  _run_process(
    [sys.executable, str(build_script), build_command],
    cwd=platform_dir,
  )
  shutil.copytree(
    platform_dir / "build",
    _PROJECT_ROOT / "dist",
    dirs_exist_ok=True,
  )


@task
def prepare_inno_setup() -> None:
  """Prepare the Windows Inno Setup staging tree without compiling it."""
  if platform.system() != "Windows":
    raise RuntimeError("Inno Setup preparation is only supported on Windows.")
  from scripts.python.windows_bundle import BundleConfig, prepare_inno_staging

  bundle = _PROJECT_ROOT / "dist/windows-x86_64-bundle"
  prepare_inno_staging(
    bundle,
    _PROJECT_ROOT / "inno-build-release",
    _PROJECT_ROOT / "os_specific/windows/logo.ico",
    BundleConfig(_PROJECT_ROOT, bundle, _PROJECT_ROOT / "uv.lock"),
  )


@task
def build_inno_setup(architecture: str = "x64") -> None:
  """Build the Windows installer for ``x86`` or ``x64`` architecture."""
  if platform.system() != "Windows":
    raise RuntimeError("Inno Setup is only supported on Windows.")
  if architecture not in ("x86", "x64"):
    raise ValueError("architecture must be 'x86' or 'x64'")
  if architecture == "x86":
    raise RuntimeError(
      "Windows x86 Inno packaging is retired and unsupported; use x64."
    )

  if architecture == "x64":
    from scripts.python.windows_bundle import BundleConfig, prepare_inno_staging

    bundle = _PROJECT_ROOT / "dist/windows-x86_64-bundle"
    prepare_inno_staging(
      bundle,
      _PROJECT_ROOT / "inno-build-release",
      _PROJECT_ROOT / "os_specific/windows/logo.ico",
      BundleConfig(_PROJECT_ROOT, bundle, _PROJECT_ROOT / "uv.lock"),
    )
  project_root = _PROJECT_ROOT
  script_path = project_root / f"os_specific/windows/inno_setup/setup_{architecture}.iss"
  compiler = shutil.which("iscc")
  if compiler is None:
    compiler_path = pathlib.Path(
      r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
    )
    if not compiler_path.exists():
      raise FileNotFoundError(
        "Inno Setup compiler not found. Install ISCC.exe or add iscc to PATH."
      )
    compiler = str(compiler_path)
  compiler_args = [compiler]
  project_version = os.environ.get("PROJECT_VERSION")
  if project_version:
    compiler_args.append(f"/DMyAppVersion={project_version}")
  compiler_args.append(str(script_path))
  _run_process(compiler_args)


def _parse_args(argv: list[str]) -> tuple[list[str], dict[str, str]]:
  """Splits a list of CLI tokens into positional args and keyword args.

  Keyword arguments may be supplied in any of the following formats::

      key=value          # bare assignment
      --key=value        # GNU long-option style

  All other tokens are treated as positional arguments and returned in order.

  Args:
      argv: A list of raw CLI tokens *excluding* the program name and the
          task name (i.e. ``sys.argv[2:]``).

  Returns:
      A two-tuple ``(positional_args, keyword_args)`` where:
          - ``positional_args`` is a ``list[str]`` of values without ``=``.
          - ``keyword_args`` is a ``dict[str, str]`` of stripped key/value
            pairs.

  Example:

      >>> _parse_args(["--env=prod", "extra"])
      (['extra'], {'env': 'prod'})
  """
  positional: list[str] = []
  keyword: dict[str, str] = {}

  for token in argv:
    if "=" in token:
      # Strip any leading dashes to normalise ``--key=value`` → ``key``.
      raw_key, _, value = token.partition("=")
      key = raw_key.lstrip("-")
      keyword[key] = value
    else:
      positional.append(token)

  return positional, keyword


def _build_help_text() -> str:
  """Constructs the formatted help string for the ``--help`` output.

  Iterates over the task registry in insertion order, extracting each task's
  signature and the first non-blank line of its docstring to build a compact
  usage table.

  Returns:
      A multi-line string ready to be printed to stdout.
  """
  lines: list[str] = [
    "",
    _colorize("Available tasks", _COLOR_GREEN),
    _colorize("=" * 60, _COLOR_GREY),
  ]

  for name, func in _TASKS.items():
    sig = inspect.signature(func)
    params = list(sig.parameters.values())

    # Build a compact parameter hint, e.g. ``[env=dev] [verbose=false]``.
    param_hints: list[str] = []
    for param in params:
      if param.default is inspect.Parameter.empty:
        param_hints.append(f"<{param.name}>")
      else:
        param_hints.append(f"[{param.name}={param.default!r}]")

    usage_suffix = (" " + " ".join(param_hints)) if param_hints else ""
    heading = _colorize(f"  {name}{usage_suffix}", _COLOR_YELLOW)
    lines.append(heading)

    # Emit the full docstring (minus the first line already shown in the
    # heading) indented for readability.
    raw_doc = (func.__doc__ or "").strip()
    if raw_doc:
      # ``textwrap.dedent`` normalises inconsistent indentation from
      # triple-quoted strings.
      doc_lines = textwrap.dedent(raw_doc).splitlines()
      for doc_line in doc_lines:
        lines.append(f"      {doc_line}")

    lines.append("")  # Blank line between tasks.

  lines.append(_colorize("=" * 60, _COLOR_GREY))
  lines.append(f"  Usage: {sys.argv[0]} <task> [positional] [key=value ...]")
  lines.append("")
  return "\n".join(lines)


def _main() -> None:
  """CLI entry point: parses ``sys.argv`` and dispatches to the named task.

  Flow:
      1. No arguments, ``-h``, or ``--help`` → print the help menu and exit 0.
      2. Unknown task name → print an error and exit 1.
      3. Valid task with well-formed arguments → invoke the task function.
       4. Argument mismatch (``TypeError``) → print a usage hint and exit 1.
       5. ``subprocess.CalledProcessError`` from a ``run()`` call → print the
          failing command and exit with the command's own exit code.
       6. Task validation or filesystem errors → print the error and exit 1.
       7. ``KeyboardInterrupt`` → exit 130 (SIGINT convention).

  Raises:
      SystemExit: Always; exit code 0 on success, non-zero on any error.
  """
  # ------------------------------------------------------------------
  # Help / no-argument path
  # ------------------------------------------------------------------
  if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
    print(_build_help_text())
    sys.exit(0)

  task_name = sys.argv[1]

  # ------------------------------------------------------------------
  # Task lookup
  # ------------------------------------------------------------------
  if task_name not in _TASKS:
    # Offer a helpful suggestion when the name is close to a known task.
    suggestions = [
      name for name in _TASKS if task_name.lower() in name.lower()
    ]
    msg = _colorize(f"Error: Unknown task '{task_name}'.", _COLOR_RED)
    print(msg, file=sys.stderr)
    if suggestions:
      print(
        _colorize(
          f"  Did you mean: {', '.join(suggestions)}?",
          _COLOR_YELLOW,
        ),
        file=sys.stderr,
      )
    else:
      print(
        f"  Run '{sys.argv[0]} --help' to list available tasks.",
        file=sys.stderr,
      )
    sys.exit(1)

  # ------------------------------------------------------------------
  # Argument parsing and dispatch
  # ------------------------------------------------------------------
  positional, keyword = _parse_args(sys.argv[2:])
  func = _TASKS[task_name]

  try:
    func(*positional, **keyword)
  except TypeError as exc:
    # Likely an arity mismatch; print a context-rich usage hint.
    print(
      _colorize(f"Argument error: {exc}", _COLOR_RED),
      file=sys.stderr,
    )
    sig = inspect.signature(func)
    print(
      _colorize(
        f"  Usage: {sys.argv[0]} {task_name}{sig}",
        _COLOR_YELLOW,
      ),
      file=sys.stderr,
    )
    sys.exit(1)
  except subprocess.CalledProcessError as exc:
    # A shell command failed; exit with its own return code so that CI
    # pipelines receive a meaningful exit status.
    print(
      _colorize(
        f"Command failed (exit {exc.returncode}): {exc.cmd}",
        _COLOR_RED,
      ),
      file=sys.stderr,
    )
    sys.exit(exc.returncode)
  except (OSError, RuntimeError, ValueError) as exc:
    print(_colorize(f"Task failed: {exc}", _COLOR_RED), file=sys.stderr)
    sys.exit(1)
  except KeyboardInterrupt:
    # Conventional exit code for SIGINT.
    print(_colorize("\nInterrupted.", _COLOR_YELLOW), file=sys.stderr)
    sys.exit(130)


# </editor-fold>

# <editor-fold desc="Tasks">
@task
def format(check: str = "false") -> None:
  """Format the codebase with Ruff.

  Runs `Ruff <https://docs.astral.sh/ruff/>`_ in either reformat or
  check-only mode.

  Args:
      check: Pass ``check=true`` to run Ruff format in ``--check`` mode (exit
          non-zero if any file would be reformatted) without modifying files.
          Useful for CI gating.  Defaults to ``"false"`` (reformat in place).

  Example:

      ./pymake.bat/sh format            # Reformat in place.
      ./pymake.bat/sh format check=true # CI dry-run; fail if changes needed.
  """
  flag = "--check" if check.lower() == "true" else ""
  run(f"ruff format {flag} .", cwd=_PROJECT_ROOT)


@task
def lint(fix: str = "false") -> None:
  """Run static analysis with Ruff.

  Executes `Ruff <https://docs.astral.sh/ruff/>`_ across the entire project
  tree using the configuration defined in ``ruff.toml``.

  Args:
      fix: Pass ``fix=true`` to automatically fix lint violations where
          possible.  Defaults to ``"false"``.
  """
  flag = "--fix" if fix.lower() == "true" else ""
  run(f"ruff check {flag} .", cwd=_PROJECT_ROOT)


@task
def check_types() -> None:
  """Run static type checking with mypy.

  Executes `mypy <https://mypy-lang.org/>`_ across the project
  to verify type safety based on the configuration in ``mypy.ini``.
  """
  run("mypy", cwd=_PROJECT_ROOT)


@task
def test(match: str = "", verbose: str = "false") -> None:
  """Execute the test suite with pytest.

  Runs all tests discovered by ``pytest`` from the current directory.
  Optional filters allow targeted execution during development.

  Args:
      match: A ``-k`` expression passed directly to pytest to select tests
          by name substring or marker expression (e.g. ``match=api``).
          Defaults to ``""`` (run all tests).
      verbose: Pass ``verbose=true`` to enable ``-v`` output, which prints
          each test's full node ID and outcome.  Defaults to ``"false"``.

  Example:

      ./pymake.bat/sh test                       # Run all tests.
      ./pymake.bat/sh test match=auth            # Only tests matching 'auth'.
      ./pymake.bat/sh test verbose=true          # Verbose output.
      ./pymake.bat/sh test match=api verbose=true
  """
  cmd_parts: list[str] = ["pytest"]
  if verbose.lower() == "true":
    cmd_parts.append("-v")
  if match:
    # Use shlex.quote to prevent accidental shell injection from the match
    # expression while still allowing pytest expressions like 'api or db'.
    cmd_parts.extend(["-k", shlex.quote(match)])
  run(" ".join(cmd_parts), cwd=_PROJECT_ROOT)


@task
def build_windows_bundle() -> None:
  """Build the approved relocatable Windows x86_64 standalone bundle."""
  if platform.system() != "Windows":
    raise RuntimeError("Windows standalone bundle is only supported on Windows.")
  from scripts.python.windows_bundle import BundleConfig, build

  build(BundleConfig(
      root=_PROJECT_ROOT,
      output=_PROJECT_ROOT / "dist/windows-x86_64-bundle",
      lockfile=_PROJECT_ROOT / "uv.lock",
  ))


@task
def package_windows_bundle() -> None:
  """Create a deterministic ZIP from the existing Windows x86_64 bundle."""
  if platform.system() != "Windows":
    raise RuntimeError("Windows bundle packaging is only supported on Windows.")
  from scripts.python.windows_bundle import (
    ARCHIVE_NAME,
    BundleConfig,
    create_deterministic_archive,
  )

  bundle = _PROJECT_ROOT / "dist/windows-x86_64-bundle"
  create_deterministic_archive(
    bundle,
    _PROJECT_ROOT / "dist" / ARCHIVE_NAME,
    BundleConfig(_PROJECT_ROOT, bundle, _PROJECT_ROOT / "uv.lock"),
  )


@task
def build_windows_artifacts() -> None:
  """Build the Windows x86_64 bundle, ZIP, and x64 installer in order."""
  if platform.system() != "Windows":
    raise RuntimeError("Windows artifact builds are only supported on Windows.")
  build_windows_bundle()
  package_windows_bundle()
  build_inno_setup("x64")

# </editor-fold>

# <editor-fold desc="main">
if __name__ == "__main__":
  _main()
# </editor-fold>
