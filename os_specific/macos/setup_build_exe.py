"""Configure the macOS cx_Freeze application build."""

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

SHARED_SUFFIX = f".cpython-{PYTHON_VERSION.replace('.', '')}-darwin.so"
# </editor-fold>


BUILD_EXE_OPTIONS = {
  "includes": [
    "copy",
    "encodings",
    "PyQt5.uic",
    "pymol.vfont",
    "pymol.povray",
    "pymol.parser",
    "uuid",
    "ssl"
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

# The custom .plist file needs manual version change!
BDIST_MAC_OPTIONS = {
  "custom_info_plist": Path(
    PROJECT_ROOT_DIR / "os_specific/macos" / "Info.plist"
  )
}

setup(
  name="Open-Source-PyMOL",
  version=PROJECT_VERSION,
  options={
    "build_exe": BUILD_EXE_OPTIONS,
    "bdist_mac": BDIST_MAC_OPTIONS
  },
  executables=[
    {
      "target_name": "PyMOL",
      "script": Path(PYMOL_PACKAGE_DIR / "startup_wrapper.py"),
      "base": "gui",
      "icon": Path(PROJECT_ROOT_DIR / "os_specific/macos" / "icon.icns"),
    }
  ],
)
