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
import re
import shutil
import sys

import const
import utils


# Version of pymol-open-source-whl that the files in edited/ were made for.
# They are copies of the wheel's files with a few edits ("BEGIN EDITED CODE
# SEGMENT"), so a newer wheel needs them ported before they may replace its files.
EDITED_FOR_PYMOL_WHL_VERSION = "3.2.0.3"

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


MAX_GLIBC_VERSION = (2, 28)
"""Newest glibc the frozen Linux app may need: RHEL/AlmaLinux 8's."""

GLIBC_SYMBOL_PATTERN = re.compile(rb"GLIBC_(\d+)\.(\d+)")
"""Version tag of the glibc symbols a Linux library needs."""


def check_glibc_versions() -> None:
  """Reports libraries of the frozen app that need a newer glibc (Linux).

  A build on a new distribution can bundle that machine's libraries, such
  as libxcb-cursor, which then need a newer glibc than the oldest
  supported distribution has. In CI, which builds the release packages,
  this stops the build; locally it is a warning, because such a build
  still runs on the build machine and on newer distributions.
  """
  tmp_findings = []
  for tmp_path in sorted(const.FROZEN_APP_DIR.rglob("*.so*")):
    if tmp_path.is_symlink() or not tmp_path.is_file():
      continue
    tmp_versions = {
      (int(tmp_major), int(tmp_minor))
      for tmp_major, tmp_minor in GLIBC_SYMBOL_PATTERN.findall(
        tmp_path.read_bytes()
      )
    }
    tmp_newest = max(tmp_versions, default=MAX_GLIBC_VERSION)
    if tmp_newest > MAX_GLIBC_VERSION:
      tmp_name = tmp_path.relative_to(const.FROZEN_APP_DIR)
      tmp_findings.append(
        f"  {tmp_name} needs glibc {tmp_newest[0]}.{tmp_newest[1]}"
      )
  if not tmp_findings:
    return
  tmp_message = "\n".join([
    "These libraries need a newer glibc than RHEL/AlmaLinux 8 has (2.28),",
    "so the app will not start there. Build the release packages in CI",
    "(Ubuntu 22.04) or in an Ubuntu 22.04 container:",
    *tmp_findings,
  ])
  if os.environ.get("CI"):
    sys.exit(tmp_message)
  print(f"Warning: {tmp_message}")


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


def thin_macos_app() -> None:
  """Keeps only this Mac's architecture in the app's universal binaries (macOS).

  The PySide6 wheels contain Qt for Intel and Apple Silicon, while each DMG is
  for one architecture; thinning saves about a third of the DMG size.
  build_dmg.sh checks afterwards that PyMOL, Qt and numpy match.
  """
  # arm64 or x86_64, the architecture of this Python and of the wheels installed for it
  tmp_arch = platform.machine()
  for tmp_app in const.DIST_DIR.glob("*.app"):
    tmp_thin_app = tmp_app.with_name(f"{tmp_app.name}.thin")
    utils.run(["ditto", "--arch", tmp_arch, tmp_app, tmp_thin_app])
    shutil.rmtree(tmp_app)
    tmp_thin_app.rename(tmp_app)
    print(f"Thinned the universal binaries in {tmp_app.name} to {tmp_arch}")


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
    check_glibc_versions()
  if const.MACOS:
    thin_macos_app()
