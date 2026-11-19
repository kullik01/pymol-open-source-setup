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
import shutil
import subprocess
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
  for tmp_dir in ("/usr/lib/x86_64-linux-gnu", "/lib/x86_64-linux-gnu", "/usr/lib64", "/lib64", "/usr/lib"):
    tmp_source = pathlib.Path(tmp_dir, "libxcb-cursor.so.0")
    if tmp_source.exists():
      break
  else:
    sys.exit("libxcb-cursor.so.0 not found. Install it (Debian/Ubuntu and openSUSE: libxcb-cursor0, Fedora: xcb-util-cursor).")
  for tmp_qt_lib_dir in const.DIST_DIR.glob("exe.linux-*/lib/PySide6/Qt/lib"):
    shutil.copy2(tmp_source.resolve(), tmp_qt_lib_dir / "libxcb-cursor.so.0")


def is_universal_binary(a_path: pathlib.Path) -> bool:
  """True for a macOS universal (fat) Mach-O file."""
  with open(a_path, "rb") as tmp_file:
    header = tmp_file.read(8)
  # 0xcafebabe is also the magic of Java class files, which have a large second field
  return len(header) == 8 and header[:4] == b"\xca\xfe\xba\xbe" and int.from_bytes(header[4:], "big") < 10


def thin_macos_app() -> None:
  """Keeps only the architecture of PyMOL's _cmd module in universal binaries (macOS).

  The PySide6 wheels contain Qt for Intel and Apple Silicon, while each DMG is
  for one architecture; thinning saves about a third of the DMG size.
  """
  for tmp_app in const.DIST_DIR.glob("*.app"):
    tmp_cmd_module = next(tmp_app.glob("Contents/Resources/lib/pymol/_cmd.*.so"))
    tmp_arch = subprocess.run(
      ["lipo", "-archs", str(tmp_cmd_module)], capture_output=True, text=True, check=True
    ).stdout.strip()
    if " " in tmp_arch:
      sys.exit(f"PyMOL's _cmd module is built for several architectures ({tmp_arch}).")
    tmp_count = 0
    for tmp_path in tmp_app.rglob("*"):
      if tmp_path.is_symlink() or not tmp_path.is_file() or not is_universal_binary(tmp_path):
        continue
      utils.run(["lipo", tmp_path, "-thin", tmp_arch, "-output", tmp_path])
      tmp_count += 1
    print(f"Thinned {tmp_count} universal binaries in {tmp_app.name} to {tmp_arch}")


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
  if const.MACOS:
    thin_macos_app()
