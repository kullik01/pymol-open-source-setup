import sys
import pathlib

import toml
from cx_Freeze import setup


# <editor-fold desc="Module constants">
PROJECT_ROOT_DIR = pathlib.Path(__file__).parent.parent.parent
PYTHON_VERSION = f"{sys.version_info.major}.{sys.version_info.minor}"
PYMOL_PACKAGE_DIR = pathlib.Path(PROJECT_ROOT_DIR / f".venv/lib/python{PYTHON_VERSION}/site-packages/pymol")

tmp_pyproject_toml = toml.load(
  str(pathlib.Path(PROJECT_ROOT_DIR / "pyproject.toml"))
)
PROJECT_NAME = tmp_pyproject_toml["project"]["name"]
PROJECT_VERSION = tmp_pyproject_toml["project"]["version"]

SHARED_SUFFIX = f".cpython-{PYTHON_VERSION.replace('.', '')}-x86_64-linux-gnu.so"
# </editor-fold>


build_exe_options = {
  "includes": [
    "copy",
    "encodings",
    "PyQt5.uic",
    "pymol.povray",
    "pymol.parser",
    "uuid"
  ],
  "include_files": [
    (
      pathlib.Path(PYMOL_PACKAGE_DIR / f"_cmd{SHARED_SUFFIX}"),
      f"./lib/pymol/_cmd{SHARED_SUFFIX}"
     )
  ]
}


setup(
  name="Open-Source-PyMOL",
  version=PROJECT_VERSION,
  options={
    "build_exe": build_exe_options
  },
  executables=[
    {
      "target_name": "Open-Source-PyMOL",
      "script": pathlib.Path(PYMOL_PACKAGE_DIR / "startup_wrapper.py"),
      "base": "gui",
      "icon": pathlib.Path(PROJECT_ROOT_DIR / "os_specific/linux" / "logo.png"),
    }
  ],
)
