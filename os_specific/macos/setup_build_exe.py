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

SHARED_SUFFIX = f".cpython-{PYTHON_VERSION.replace('.', '')}-darwin.so"
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

# The custom .plist file needs manual version change!
bdist_mac_options = {
  "custom_info_plist": pathlib.Path(PROJECT_ROOT_DIR / "os_specific/macos" / "Info.plist")
}

setup(
  name="Open-Source-PyMOL",
  version=PROJECT_VERSION,
  options={
    "build_exe": build_exe_options,
    "bdist_mac": bdist_mac_options
  },
  executables=[
    {
      "target_name": "PyMOL",
      "script": pathlib.Path(PYMOL_PACKAGE_DIR / "startup_wrapper.py"),
      "base": "gui",
      "icon": pathlib.Path(PROJECT_ROOT_DIR / "os_specific/macos" / "icon.icns"),
    }
  ],
)

# <editor-fold desc="Coping macOS build script into the application package">
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
