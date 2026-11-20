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
import os
import shutil
import sys
import sysconfig

import const
import utils


INNO_SETUP_SCRIPT_FILEPATH = const.PROJECT_ROOT_DIR / "os_specific" / "windows" / "inno_setup" / "setup.iss"


def build() -> None:
  """Builds the Windows installer from the frozen application in dist/."""
  if not const.WIN32:
    sys.exit("The Inno Setup installer can only be built on Windows.")
  if sysconfig.get_platform() != "win-amd64":
    sys.exit("The Inno Setup installer requires a 64-bit (x64) Python interpreter.")

  if not const.FROZEN_APP_DIR.exists():
    sys.exit(f"{const.FROZEN_APP_DIR} does not exist. Run 'build app' first.")

  # Inno Setup 7's install folders (64-bit and 32-bit edition for all users, per-user install)
  # come before the PATH, which may contain an older Inno Setup (e.g. on the GitHub runners)
  tmp_search_path = os.pathsep.join([
    r"C:\Program Files\Inno Setup 7",
    r"C:\Program Files (x86)\Inno Setup 7",
    os.path.join(os.environ["LOCALAPPDATA"], "Programs", "Inno Setup 7"),
    os.environ.get("PATH", ""),
  ])
  tmp_iscc_filepath = shutil.which("ISCC", path=tmp_search_path)
  if tmp_iscc_filepath is None:
    sys.exit("Inno Setup 7 compiler (ISCC.exe) not found. Install Inno Setup 7 or add it to the PATH.")

  utils.run([
    tmp_iscc_filepath,
    f"/DMyAppVersion={const.PROJECT_VERSION}",
    f"/DAppSourceDir={const.FROZEN_APP_DIR}",
    INNO_SETUP_SCRIPT_FILEPATH,
  ])
