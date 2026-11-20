"""
#A* -------------------------------------------------------------------
#B* This file contains source code for running automation tasks related
#-* to the build process of the PyMOL computer program
#C* Copyright 2026 by Martin Urban.
#D* -------------------------------------------------------------------
#E* It is unlawful to modify or remove this copyright notice.
#F* -------------------------------------------------------------------
#G* Please see the accompanying LICENSE file for further information.
#H* -------------------------------------------------------------------
#I* Additional authors of this source file include:
#-* Hannah Kullik
#-*
#-*
#Z* -------------------------------------------------------------------
"""
import importlib.metadata
import os
import pathlib
import platform
import shutil
import sys

import const
import utils


# Version of pymol-open-source-whl that the files in edited/ were made for.
# They are copies of the wheel's files with a few edits ("BEGIN EDITED CODE
# SEGMENT"), so a newer wheel needs them ported before they may replace its files.
EDITED_FOR_PYMOL_WHL_VERSION = "3.1.0.4"

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


def bundle_libxcb_cursor() -> None:
  """Copies libxcb-cursor next to the Qt libraries of the frozen app (Linux).

  Qt 6.5+ needs it for X11, but RHEL/Alma 8 only have it in EPEL. cx_Freeze
  leaves system libraries out, so it is copied after freezing.
  """
  tmp_multiarch = f"{platform.machine()}-linux-gnu"
  for tmp_dir in (f"/usr/lib/{tmp_multiarch}", f"/lib/{tmp_multiarch}", "/usr/lib64", "/lib64", "/usr/lib"):
    tmp_source = pathlib.Path(tmp_dir, "libxcb-cursor.so.0")
    if tmp_source.exists():
      break
  else:
    sys.exit("libxcb-cursor.so.0 not found. Install it (Debian/Ubuntu and openSUSE: libxcb-cursor0, Fedora: xcb-util-cursor).")
  tmp_qt_lib_dirs = list(const.DIST_DIR.glob("exe.linux-*/lib/PySide6/Qt/lib"))
  if not tmp_qt_lib_dirs:
    sys.exit(f"No PySide6/Qt/lib folder found in {const.DIST_DIR}; cannot bundle libxcb-cursor.so.0.")
  for tmp_qt_lib_dir in tmp_qt_lib_dirs:
    shutil.copy2(tmp_source.resolve(), tmp_qt_lib_dir / "libxcb-cursor.so.0")


def build() -> None:
  """Builds the frozen application with cx_Freeze into the dist directory.

  Windows/Linux: dist/exe.<platform>-<python version>/
  macOS: dist/PyMOL-Open-Source-<version>.app
  """
  tmp_installed_version = importlib.metadata.version("pymol-open-source-whl")
  if tmp_installed_version != EDITED_FOR_PYMOL_WHL_VERSION:
    sys.exit(
      f"pymol-open-source-whl {tmp_installed_version} is installed, but the files in edited/ were "
      f"made for {EDITED_FOR_PYMOL_WHL_VERSION}. Port their 'BEGIN EDITED CODE SEGMENT' blocks into "
      f"the new versions of the files, then update EDITED_FOR_PYMOL_WHL_VERSION in {__file__}."
    )
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
  if const.LINUX:
    bundle_libxcb_cursor()
