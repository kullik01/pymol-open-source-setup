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
import sys
import sysconfig
import tomllib


PROJECT_ROOT_DIR = pathlib.Path(__file__).resolve().parent.parent
DIST_DIR = PROJECT_ROOT_DIR / "dist"
SETUP_BUILD_EXE_FILEPATH = PROJECT_ROOT_DIR / "os_specific" / "setup_build_exe.py"

PYTHON_EXECUTABLE = sys.executable
PYTHON_VERSION = f"{sys.version_info.major}.{sys.version_info.minor}"

# The automations always run with the interpreter of the project's .venv,
# so these paths point into that virtual environment on every platform.
SITE_PACKAGES_DIR = pathlib.Path(sysconfig.get_path("platlib"))
PYMOL_PACKAGE_DIR = SITE_PACKAGES_DIR / "pymol"
VENV_SCRIPTS_DIR = pathlib.Path(sysconfig.get_path("scripts"))

with open(PROJECT_ROOT_DIR / "pyproject.toml", "rb") as tmp_file:
  PROJECT_VERSION = tomllib.load(tmp_file)["project"]["version"]

WIN32 = sys.platform == "win32"
MACOS = sys.platform == "darwin"
LINUX = sys.platform.startswith("linux")

if WIN32:
  OS_SPECIFIC_DIR = PROJECT_ROOT_DIR / "os_specific" / "windows"
elif MACOS:
  OS_SPECIFIC_DIR = PROJECT_ROOT_DIR / "os_specific" / "macos"
elif LINUX:
  OS_SPECIFIC_DIR = PROJECT_ROOT_DIR / "os_specific" / "linux"
else:
  sys.exit(f"Unsupported platform: {sys.platform}")
