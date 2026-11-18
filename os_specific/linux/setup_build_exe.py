"""Configure the Linux cx_Freeze application build."""

import sys
from pathlib import Path

import toml
from cx_Freeze import setup


# <editor-fold desc="Module constants">
PROJECT_ROOT_DIR = Path(__file__).parent.parent.parent
PYTHON_VERSION = f"{sys.version_info.major}.{sys.version_info.minor}"
PYMOL_PACKAGE_DIR = Path(
  PROJECT_ROOT_DIR
  / f".venv/lib/python{PYTHON_VERSION}/site-packages/pymol"
)

tmp_pyproject_toml = toml.load(str(Path(PROJECT_ROOT_DIR / "pyproject.toml")))
PROJECT_NAME = tmp_pyproject_toml["project"]["name"]
PROJECT_VERSION = tmp_pyproject_toml["project"]["version"]

SHARED_SUFFIX = f".cpython-{PYTHON_VERSION.replace('.', '')}-x86_64-linux-gnu.so"
# </editor-fold>


BUILD_EXE_OPTIONS = {
  "includes": [
    "copy",
    "encodings",
    "PyQt5.uic",
    "pymol.vfont",
    "pymol.povray",
    "pymol.parser",
    "uuid"
  ],
  "include_files": [
    (
      Path(PYMOL_PACKAGE_DIR / f"_cmd{SHARED_SUFFIX}"),
      f"./lib/pymol/_cmd{SHARED_SUFFIX}"
    ),
    (
      Path(PYMOL_PACKAGE_DIR / "wizard"),
      "./lib/pymol/wizard"
    ),
    (
      Path(PYMOL_PACKAGE_DIR / "data/startup"),
      "./lib/pymol/data/startup"
    ),
  ]
}


setup(
  name="Open-Source-PyMOL",
  version=PROJECT_VERSION,
  options={
    "build_exe": BUILD_EXE_OPTIONS
  },
  executables=[
    {
      "target_name": "Open-Source-PyMOL",
      "script": Path(PYMOL_PACKAGE_DIR / "startup_wrapper.py"),
      "base": "gui",
      "icon": Path(PROJECT_ROOT_DIR / "os_specific/linux" / "logo.png"),
    }
  ],
)
