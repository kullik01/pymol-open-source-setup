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
import platform
import sys
import pathlib
import toml


PROJECT_ROOT_DIR = pathlib.Path(__file__).parent.parent
PYTHON_EXECUTABLE = sys.executable

tmp_pyproject_toml = toml.load(
  pathlib.Path(PROJECT_ROOT_DIR / "pyproject.toml")
)
PROJECT_NAME = tmp_pyproject_toml["project"]["name"]
PROJECT_VERSION = tmp_pyproject_toml["project"]["version"]
PYTHON_VERSION = f"{sys.version_info.major}.{sys.version_info.minor}"


def invalid_platform() -> int:
  """Function that reports that the platform is invalid and returns 1.

  Note:
    This function does not automatically crash the program because this
    creates problems with pythons static type checker. Therefore, the
    function needs to be nested inside exit().
  """
  print(f"Invalid platform: {platform.system()}")
  return 1


# <editor-fold desc="Check running OS">
if platform.system() == "Windows":
  WIN32 = True
  __APPLE__ = False
  __linux__ = False
elif platform.system() == "Darwin":
  WIN32 = False
  __APPLE__ = True
  __linux__ = False
elif platform.system() == "Linux":
  WIN32 = False
  __APPLE__ = False
  __linux__ = True
else:
  exit(invalid_platform())
# </editor-fold>

if WIN32:
  PYMOL_PACKAGE_DIR = pathlib.Path(
    PROJECT_ROOT_DIR / ".venv/Lib/site-packages/pymol"
  )
  OS_SPECIFIC_DIR = pathlib.Path(
    PROJECT_ROOT_DIR / "os_specific/windows"
  )
elif __APPLE__:
  PYMOL_PACKAGE_DIR = pathlib.Path(
    PROJECT_ROOT_DIR / f".venv/lib/python{PYTHON_VERSION}/site-packages/pymol"
  )
  OS_SPECIFIC_DIR = pathlib.Path(
    PROJECT_ROOT_DIR / "os_specific/macos"
  )
elif __linux__:
  PYMOL_PACKAGE_DIR = pathlib.Path(
    PROJECT_ROOT_DIR / f".venv/lib/python{PYTHON_VERSION}/site-packages/pymol"
  )
  OS_SPECIFIC_DIR = pathlib.Path(
    PROJECT_ROOT_DIR / "os_specific/linux"
  )
