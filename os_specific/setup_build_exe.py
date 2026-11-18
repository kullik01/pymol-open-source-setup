"""cx_Freeze configuration of the PyMOL-Open-Source application.

Do not run this file directly, use: automator build app
(it patches the pymol package of the .venv before freezing).

Output:
  Windows/Linux: dist/exe.<platform>-<python version>/
  macOS:         dist/PyMOL-Open-Source-<version>.app
"""
import pathlib
import sys
import sysconfig
import tomllib

from cx_Freeze import setup


PROJECT_ROOT_DIR = pathlib.Path(__file__).resolve().parent.parent
PYMOL_PACKAGE_DIR = pathlib.Path(sysconfig.get_path("platlib"), "pymol")
# e.g. ".cpython-311-x86_64-linux-gnu.so", ".cpython-311-darwin.so", ".cp311-win_amd64.pyd"
CMD_MODULE_FILENAME = f"_cmd{sysconfig.get_config_var('EXT_SUFFIX')}"

with open(PROJECT_ROOT_DIR / "pyproject.toml", "rb") as tmp_file:
  PROJECT_VERSION = tomllib.load(tmp_file)["project"]["version"]

if sys.platform == "win32":
  OS_SPECIFIC_DIR = PROJECT_ROOT_DIR / "os_specific" / "windows"
  ICON_FILEPATH = OS_SPECIFIC_DIR / "logo.ico"
elif sys.platform == "darwin":
  OS_SPECIFIC_DIR = PROJECT_ROOT_DIR / "os_specific" / "macos"
  ICON_FILEPATH = OS_SPECIFIC_DIR / "icon.icns"
else:
  OS_SPECIFIC_DIR = PROJECT_ROOT_DIR / "os_specific" / "linux"
  ICON_FILEPATH = OS_SPECIFIC_DIR / "logo.png"

options = {
  "build": {
    "build_base": str(PROJECT_ROOT_DIR / "dist"),
  },
  "build_exe": {
    "includes": [
      "copy",
      "encodings",
      "PyQt5.uic",
      "pymol.vfont",
      "pymol.povray",
      "pymol.parser",
      "uuid",
    ],
    # Files that are loaded dynamically and therefore not found by cx_Freeze
    "include_files": [
      (PYMOL_PACKAGE_DIR / CMD_MODULE_FILENAME, f"lib/pymol/{CMD_MODULE_FILENAME}"),
      (PYMOL_PACKAGE_DIR / "wizard", "lib/pymol/wizard"),
      (PYMOL_PACKAGE_DIR / "data" / "startup", "lib/pymol/data/startup"),
    ],
  },
}

if sys.platform == "darwin":
  options["build_exe"]["includes"].append("ssl")
  options["bdist_mac"] = {
    "bundle_name": f"PyMOL-Open-Source-{PROJECT_VERSION}",
    "custom_info_plist": str(OS_SPECIFIC_DIR / "Info.plist"),
    # Keeps the version of the app bundle in sync with pyproject.toml
    "plist_items": [
      ("CFBundleIdentifier", f"Open-Source-PyMOL-{PROJECT_VERSION}"),
      ("CFBundleShortVersionString", PROJECT_VERSION),
      ("CFBundleVersion", PROJECT_VERSION),
    ],
  }

setup(
  name="Open-Source-PyMOL",
  version=PROJECT_VERSION,
  options=options,
  executables=[
    {
      "target_name": "PyMOL" if sys.platform == "darwin" else "Open-Source-PyMOL",
      "script": PROJECT_ROOT_DIR / "edited" / "pymol" / "startup_wrapper.py",
      "base": "gui",
      "icon": ICON_FILEPATH,
    }
  ],
)
