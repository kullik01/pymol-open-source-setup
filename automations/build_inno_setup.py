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
import pathlib
import shutil
import sys
import sysconfig

import const
import utils


DEFAULT_ISCC_FILEPATH = pathlib.Path(r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe")
INNO_SETUP_SCRIPT_FILEPATH = const.PROJECT_ROOT_DIR / "os_specific" / "windows" / "inno_setup" / "setup.iss"


def build() -> None:
  """Builds the Windows installer from the frozen application in dist/."""
  if not const.WIN32:
    sys.exit("The Inno Setup installer can only be built on Windows.")
  if sysconfig.get_platform() != "win-amd64":
    sys.exit("The Inno Setup installer requires a 64-bit (x64) Python interpreter.")

  tmp_frozen_app_dir = const.DIST_DIR / f"exe.{sysconfig.get_platform()}-{const.PYTHON_VERSION}"
  if not tmp_frozen_app_dir.exists():
    sys.exit(f"{tmp_frozen_app_dir} does not exist. Run 'build app' first.")

  tmp_iscc_filepath = shutil.which("ISCC") or DEFAULT_ISCC_FILEPATH
  if not pathlib.Path(tmp_iscc_filepath).exists():
    sys.exit("Inno Setup 6 compiler (ISCC.exe) not found. Install Inno Setup 6 or add it to the PATH.")

  utils.run([
    tmp_iscc_filepath,
    f"/DMyAppVersion={const.PROJECT_VERSION}",
    f"/DAppSourceDir={tmp_frozen_app_dir}",
    INNO_SETUP_SCRIPT_FILEPATH,
  ])
