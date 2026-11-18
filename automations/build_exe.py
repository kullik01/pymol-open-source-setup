"""
#A* -------------------------------------------------------------------
#B* This file contains source code for running automation tasks related
#-* to the build process of the PyMOL computer program
#C* Copyright 2025 by Martin Urban.
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
import os
import shutil

import const
import utils


# Project files that replace or extend files of the installed pymol package
# before it gets frozen: (source, destination)
PATCHED_FILES = [
  (
    const.PROJECT_ROOT_DIR / "edited" / "pmg_qt" / "pymol_qt_gui.py",
    const.SITE_PACKAGES_DIR / "pmg_qt" / "pymol_qt_gui.py",
  ),
  (
    const.PROJECT_ROOT_DIR / "alternative_design" / "alt_logo.png",
    const.PYMOL_PACKAGE_DIR / "data" / "pymol" / "icons" / "alt_logo.png",
  ),
  (
    const.OS_SPECIFIC_DIR / "splash.png",
    const.PYMOL_PACKAGE_DIR / "data" / "pymol" / "splash.png",
  ),
]


def build() -> None:
  """Builds the frozen application with cx_Freeze into the dist directory.

  Windows/Linux: dist/exe.<platform>-<python version>/
  macOS: dist/PyMOL-Open-Source-<version>.app
  """
  for tmp_source, tmp_destination in PATCHED_FILES:
    shutil.copyfile(tmp_source, tmp_destination)

  # Start from a clean output directory so no stale files get shipped
  shutil.rmtree(const.DIST_DIR, ignore_errors=True)

  # cx_Freeze needs tools from the venv (e.g. patchelf on Linux) on the PATH,
  # even if the venv is not activated.
  tmp_env = os.environ.copy()
  tmp_env["PATH"] = os.pathsep.join([str(const.VENV_SCRIPTS_DIR), tmp_env.get("PATH", "")])
  tmp_command = "bdist_mac" if const.MACOS else "build_exe"
  utils.run(
    [const.PYTHON_EXECUTABLE, const.SETUP_BUILD_EXE_FILEPATH, tmp_command],
    cwd=const.PROJECT_ROOT_DIR,
    env=tmp_env,
  )
