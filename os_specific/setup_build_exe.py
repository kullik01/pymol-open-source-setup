"""cx_Freeze configuration of the PyMOL-Open-Source application.

Do not run this file directly, use: automator build app
(it patches the pymol package of the .venv before freezing).

Output:
  Windows/Linux: dist/exe.<platform>-<python version>/
  macOS:         dist/PyMOL-Open-Source-<version>.app
"""
import importlib.metadata
import pathlib
import re
import sys
import sysconfig
import tempfile
import tomllib

from cx_Freeze import setup


PROJECT_ROOT_DIR = pathlib.Path(__file__).resolve().parent.parent
SITE_PACKAGES_DIR = pathlib.Path(sysconfig.get_path("platlib"))
PYMOL_PACKAGE_DIR = SITE_PACKAGES_DIR / "pymol"
# e.g. ".cpython-311-x86_64-linux-gnu.so", ".cpython-311-darwin.so", ".cp311-win_amd64.pyd"
CMD_MODULE_FILENAME = f"_cmd{sysconfig.get_config_var('EXT_SUFFIX')}"

with open(PROJECT_ROOT_DIR / "pyproject.toml", "rb") as tmp_file:
  PROJECT_VERSION = tomllib.load(tmp_file)["project"]["version"]

# --- License texts, shipped in the "licenses" folder of the application
LICENSES_DIR = PROJECT_ROOT_DIR / "licenses"
# Python distributions that end up in the frozen application
RUNTIME_DISTRIBUTIONS = (
  "pymol-open-source-whl", "PySide6-Essentials", "shiboken6", "numpy", "biopython",
  "Pmw", "msgpack", "msgpack-python", "simplejson", "rules",
  "freeze-core",  # the executable's startup code and the native libraries of cx_Freeze
)
# Qt for Python: LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only (texts not in the wheels)
QT_FOR_PYTHON_LICENSES = [LICENSES_DIR / "LGPL-3.0.txt", LICENSES_DIR / "GPL-3.0.txt"]
# License texts of distributions whose metadata contains none
EXTRA_LICENSE_FILES = {
  "PySide6-Essentials": QT_FOR_PYTHON_LICENSES,
  "shiboken6": QT_FOR_PYTHON_LICENSES,
  # Relative to the installed package; a pattern, so a Pmw update keeps working
  "Pmw": ["Pmw/Pmw_*/doc/copyright.html"],
}
LICENSE_FILENAME_PATTERN = re.compile(r"^(LICEN[CS]E|COPYING|NOTICE|AUTHORS)", re.IGNORECASE)


def license_name(a_distribution: importlib.metadata.Distribution) -> str:
  """Returns a short license name from the metadata of a distribution."""
  metadata = a_distribution.metadata
  classifiers = [c.split(" :: ")[-1] for c in metadata.get_all("Classifier") or [] if c.startswith("License ::")]
  name = (metadata.get("License-Expression") or ", ".join(classifiers) or metadata.get("License") or "").strip()
  return name.splitlines()[0][:80] if name else "see license files"


def collect_license_files(an_index_dir: pathlib.Path) -> list:
  """Returns the (source, target) pairs of the licenses folder of the application.

  Stops the build if a bundled distribution has no license text, so new
  dependencies cannot be shipped without one.
  """
  if sys.platform == "win32":
    python_license = pathlib.Path(sys.base_prefix, "LICENSE.txt")
  else:
    python_license = pathlib.Path(sysconfig.get_path("stdlib"), "LICENSE.txt")
  files = [
    (LICENSES_DIR / "THIRD-PARTY-NOTICES.txt", "licenses/THIRD-PARTY-NOTICES.txt"),
    (LICENSES_DIR / "GPL-3.0.txt", "licenses/GPL-3.0.txt"),
    (LICENSES_DIR / "LGPL-3.0.txt", "licenses/LGPL-3.0.txt"),
    (LICENSES_DIR / "Apache-2.0.txt", "licenses/Apache-2.0.txt"),
    (LICENSES_DIR / "Mesa-MIT.txt", "licenses/Mesa-MIT.txt"),
    (LICENSES_DIR / "LLVM-LICENSE.txt", "licenses/LLVM-LICENSE.txt"),
    (PROJECT_ROOT_DIR / "LICENSE", "licenses/PyMOL-Open-Source-setup/LICENSE"),
    (python_license, "licenses/Python/LICENSE.txt"),
  ]
  index = [
    "Licenses of the components of this application",
    "",
    f"PyMOL-Open-Source-setup {PROJECT_VERSION}: BSD-3-Clause (PyMOL-Open-Source-setup/LICENSE)",
    f"Python {sys.version.split()[0]}: PSF License (Python/LICENSE.txt)",
  ]
  for name in RUNTIME_DISTRIBUTIONS:
    distribution = importlib.metadata.distribution(name)
    dist_name = distribution.metadata["Name"]
    sources = [
      pathlib.Path(distribution.locate_file(f)) for f in distribution.files or []
      if ".dist-info" in str(f) and LICENSE_FILENAME_PATTERN.match(f.name)
    ]
    for extra in EXTRA_LICENSE_FILES.get(name, []):
      if pathlib.Path(extra).is_absolute():
        sources.append(extra)
      else:
        sources.extend(pathlib.Path(distribution.locate_file("")).glob(extra))
    if not sources:
      sys.exit(f"No license text found for the bundled package {dist_name}; add one to EXTRA_LICENSE_FILES.")
    files += [(source, f"licenses/{dist_name}/{source.name}") for source in sources]
    index.append(f"{dist_name} {distribution.version}: {license_name(distribution)} ({dist_name}/)")
  index += ["", "Further components (Qt, OpenSSL, system libraries): THIRD-PARTY-NOTICES.txt"]
  for source, _ in files:
    if not pathlib.Path(source).is_file():
      sys.exit(f"License file not found: {source}")
  (an_index_dir / "README.txt").write_text("\n".join(index) + "\n", encoding="utf-8")
  files.append((an_index_dir / "README.txt", "licenses/README.txt"))
  return files


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
      "PySide6.QtUiTools",  # used by pymol.Qt.utils.loadUi
      "pymol.vfont",
      "pymol.povray",
      "pymol.parser",
      "uuid",
    ],
    # pymol.Qt also imports these bindings; keep cx_Freeze from bundling them if they are in the venv
    "excludes": ["PyQt5", "PySide2", "PyQt6"],
    # Qt plugins a desktop PyMOL never loads, which pull in about 18 MB of Qml/Quick and
    # Wayland compositor libraries: the virtual keyboard, the Wayland compositor (server)
    # side and the EGLFS plugins for embedded devices
    "bin_excludes": ["*qtvirtualkeyboardplugin*", "wayland-graphics-integration-server/*", "egldeviceintegrations/*"],
    # Files that are loaded dynamically and therefore not found by cx_Freeze
    "include_files": [
      (PYMOL_PACKAGE_DIR / CMD_MODULE_FILENAME, f"lib/pymol/{CMD_MODULE_FILENAME}"),
      (PYMOL_PACKAGE_DIR / "wizard", "lib/pymol/wizard"),
      (PYMOL_PACKAGE_DIR / "data" / "startup", "lib/pymol/data/startup"),
    ],
  },
}

if sys.platform == "win32":
  # Bundles the Microsoft C++ runtime (vcruntime140.dll, msvcp140.dll, ...), which
  # cx_Freeze leaves out by default, so the app also starts on PCs without the
  # VC++ Redistributable. cx_Freeze downloads the latest runtime of Visual Studio
  # 2022 from Microsoft (cached in %APPDATA%\cxfreeze\vc_redist).
  options["build_exe"]["include_msvcr"] = True
  options["build_exe"]["include_msvcr_version"] = "17"
  # Qt's software OpenGL (Mesa llvmpipe) for PCs, VMs and remote desktops without a usable
  # OpenGL driver (cx_Freeze copies it only for QtWebEngine). PyMOL itself is linked against
  # opengl32.dll, so users copy it to opengl32.dll next to the executable (see the website).
  options["build_exe"]["include_files"].append(
    (SITE_PACKAGES_DIR / "PySide6" / "opengl32sw.dll", "opengl32sw.dll")
  )

if sys.platform == "darwin":
  options["build_exe"]["includes"].append("ssl")
  options["bdist_mac"] = {
    "bundle_name": f"PyMOL-Open-Source-{PROJECT_VERSION}",
    "custom_info_plist": str(OS_SPECIFIC_DIR / "Info.plist"),
    # Keeps the version of the app bundle in sync with pyproject.toml
    "plist_items": [
      ("CFBundleShortVersionString", PROJECT_VERSION),
      ("CFBundleVersion", PROJECT_VERSION),
    ],
  }

with tempfile.TemporaryDirectory() as tmp_index_dir:
  options["build_exe"]["include_files"] += collect_license_files(pathlib.Path(tmp_index_dir))
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
