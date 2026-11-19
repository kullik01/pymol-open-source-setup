"""
#A* -------------------------------------------------------------------
#B* This file contains source code for running automation tasks related
#-* to the build process of the PyMOL computer program
#C* Copyright 2026 by Hannah Kullik.
#D* -------------------------------------------------------------------
#E* It is unlawful to modify or remove this copyright notice.
#F* -------------------------------------------------------------------
#G* Please see the accompanying LICENSE file for further information.
#H* -------------------------------------------------------------------
#I* Additional authors of this source file include:
#-*
#-*
#-*
#Z* -------------------------------------------------------------------
"""
import pathlib
import subprocess
import sys
import sysconfig

import build_exe
import build_inno_setup
import const
import utils


SMOKE_TEST_FILEPATH = const.PROJECT_ROOT_DIR / "tests" / "smoke_test.py"


def frozen_executable() -> pathlib.Path:
  """The executable of the frozen application in dist/ (see build_exe.build)."""
  if const.MACOS:
    return const.DIST_DIR / f"PyMOL-Open-Source-{const.PROJECT_VERSION}.app" / "Contents" / "MacOS" / "PyMOL"
  tmp_name = "Open-Source-PyMOL.exe" if const.WIN32 else "Open-Source-PyMOL"
  return const.DIST_DIR / f"exe.{sysconfig.get_platform()}-{const.PYTHON_VERSION}" / tmp_name


def build_packages() -> None:
  """Builds the installer/packages of this platform into os_specific/dist (like the CI)."""
  if const.WIN32:
    build_inno_setup.build()
  elif const.MACOS:
    utils.run(["bash", const.OS_SPECIFIC_DIR / "build_dmg.sh"])
  else:
    utils.run(["bash", const.OS_SPECIFIC_DIR / "build_packages.sh"])


def build_all() -> None:
  """Builds the frozen application, then the installer/packages of this platform."""
  build_exe.build()
  build_packages()


def _run_smoke_test(a_gui: bool) -> None:
  """Runs tests/smoke_test.py with the frozen application (like tests/run_smoke_test.sh)."""
  tmp_executable = frozen_executable()
  if not tmp_executable.exists():
    sys.exit(f"{tmp_executable} does not exist. Run 'build app' first.")
  tmp_result = subprocess.run(
    [str(tmp_executable), "-q" if a_gui else "-cq", str(SMOKE_TEST_FILEPATH)],
    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, errors="replace", check=False,
  )
  print(tmp_result.stdout, end="")
  # Checking the output as well ensures the test script was really executed
  if tmp_result.returncode != 0 or "SMOKE TEST OK" not in tmp_result.stdout:
    sys.exit(f"Smoke test failed (exit code {tmp_result.returncode})")


def test() -> None:
  """Runs the headless smoke test with the frozen application."""
  _run_smoke_test(a_gui=False)


def test_gui() -> None:
  """Runs the smoke test with the Qt GUI (needs a display)."""
  _run_smoke_test(a_gui=True)
