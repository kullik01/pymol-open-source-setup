import sys
import pathlib

import toml
from cx_Freeze import setup

# <editor-fold desc="Module constants">
PROJECT_ROOT_DIR = pathlib.Path(__file__).parent.parent.parent
PYMOL_PACKAGE_DIR = pathlib.Path(PROJECT_ROOT_DIR / ".venv/Lib/site-packages/pymol")

tmp_pyproject_toml = toml.load(
  str(pathlib.Path(PROJECT_ROOT_DIR / "pyproject.toml"))
)
PROJECT_NAME = tmp_pyproject_toml["project"]["name"]
PROJECT_VERSION = tmp_pyproject_toml["project"]["version"]

PYTHON_VERSION = f"{sys.version_info.major}.{sys.version_info.minor}"
SHARED_SUFFIX = f".cp{PYTHON_VERSION.replace('.', '')}-win_amd64.pyd"
# </editor-fold>


build_exe_options = {
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
      pathlib.Path(PYMOL_PACKAGE_DIR / f"_cmd{SHARED_SUFFIX}"),
      f"./lib/pymol/_cmd{SHARED_SUFFIX}"
     )
  ]
}


setup(
  name="Open-Source-PyMOL",
  version=PROJECT_VERSION,
  options={
    "build_exe": build_exe_options,
  },
  executables=[
    {
      "target_name": "Open-Source-PyMOL",
      "script": pathlib.Path(PYMOL_PACKAGE_DIR / "startup_wrapper.py"),
      "base": "gui",
      "icon": pathlib.Path(PROJECT_ROOT_DIR / "os_specific/windows" / "logo.ico"),
    }
  ],
)

# <editor-fold desc="Coping Windows build script into the application package">
# Definition
tmp_os_specific_build_exe_filepath = pathlib.Path(
  const.OS_SPECIFIC_SETUP_BUILD_EXE
)

# Copy
shutil.copy(
  tmp_os_specific_build_exe_filepath,
  pathlib.Path(const.PYMOL_PACKAGE_DIR / "setup_build_exe.py")
)
# </editor-fold>
