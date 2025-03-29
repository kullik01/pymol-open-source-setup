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
import os
import pathlib
import shutil
import time
import zipfile
import platform
import subprocess
import sys

from cx_Freeze import Freezer, Executable

FILE_ROOT_PATH = pathlib.Path(__file__).parent
PROJECT_ROOT_DIR = pathlib.Path(FILE_ROOT_PATH).parent


def get_mac_architecture():
  try:
    # Get the hardware architecture using sysctl
    arch = subprocess.check_output(
      ['sysctl', '-n', 'hw.machine'],
      stderr=subprocess.DEVNULL
    ).decode().strip()
    return arch
  except subprocess.CalledProcessError:
    # Fallback to platform.machine() if sysctl isn't available (unlikely on macOS)
    return platform.machine()


def copy_pymol_sources() -> None:
  """Copies the pymol python sources from the vendor directory."""
  tmp_src_path = pathlib.Path(PROJECT_ROOT_DIR / "src/python")
  tmp_pymol_python_src_path = pathlib.Path(PROJECT_ROOT_DIR / "vendor/pymol-open-source/modules")
  if not tmp_src_path.exists():
    print("Copying the pymol python sources ...")
    tmp_src_path.mkdir(parents=True)
    shutil.copytree(
      tmp_pymol_python_src_path,
      tmp_src_path,
      dirs_exist_ok=True
    )


# Define the entry point of your application
executable = Executable(
  script="pymol/__init__.py",  # Replace with your script name
  target_name="Open-Source-PyMOL",  # Optional: Set the name of the .exe file
  # base="gui",  # Uncomment to suppress command window
  icon=pathlib.Path(FILE_ROOT_PATH.parent / "alternative_design" / "logo.ico")
)

# Create a freezer instance
freezer = Freezer(
  executables=[executable],
  includes=[
    "copy", "encodings", "PyQt5.uic", "pymol.povray", "pymol.parser", "uuid"
  ],
  excludes=[],  # Exclude unnecessary modules
  include_files=[],  # Include additional files
  zip_exclude_packages=[]
)


def remove_dist_info_folders(directory: pathlib.Path):
  """
  Remove all folders ending with .dist-info from the specified directory.

  Args:
      directory (str): The path to the directory to search.
  """
  for root, dirs, files in os.walk(str(directory)):
    for dir_name in dirs:
      if dir_name.endswith(".dist-info"):
        dist_info_path = os.path.join(root, dir_name)
        shutil.rmtree(dist_info_path)


if __name__ == '__main__':
  tmp_python_version = f"{sys.version_info.major}.{sys.version_info.minor}"
  tmp_shared_suffix = f".cpython-{tmp_python_version.replace('.', '')}-darwin.so"
  tmp_dist_path = pathlib.Path(f"{FILE_ROOT_PATH}/dist")
  if tmp_dist_path.exists():
    shutil.rmtree(tmp_dist_path)
  freezer.freeze()
  #tmp_build_exe_path = pathlib.Path(f"{PROJECT_ROOT_DIR}/dist/{os.listdir(pathlib.Path(f'{PROJECT_ROOT_DIR}/dist'))[0]}")
  tmp_build_exe_path = freezer.target_dir
  with zipfile.ZipFile(pathlib.Path(f"{tmp_build_exe_path}/lib/library.zip"), 'r') as zip_ref:
    zip_ref.extractall(pathlib.Path(f"{tmp_build_exe_path}/lib"))
  if not pathlib.Path(PROJECT_ROOT_DIR / "src/python/pymol").exists():
    copy_pymol_sources()
    _CMD_FROM_BUILD_DIR = pathlib.Path(PROJECT_ROOT_DIR / "cmake-build-release" / f"_cmd{tmp_shared_suffix}")
    if _CMD_FROM_BUILD_DIR.exists():
      shutil.copy(
        _CMD_FROM_BUILD_DIR,
        pathlib.Path(PROJECT_ROOT_DIR / "src/python/pymol" / f"_cmd{tmp_shared_suffix}")
      )
    else:
      print(f"Could not find _cmd{tmp_shared_suffix} for building the EXE file.")
  else:
    print("The src/python/pymol directory already exists, that might mean a self compiled _cmd module was built.")
  remove_dist_info_folders(pathlib.Path(f"{tmp_build_exe_path}/lib"))
  shutil.copytree(
    str(pathlib.Path(PROJECT_ROOT_DIR / "pymol/pymol/wizard")),
    str(pathlib.Path(f"{tmp_build_exe_path}/lib/pymol/wizard")),
    dirs_exist_ok=True
  )
  shutil.copytree(
    str(pathlib.Path(PROJECT_ROOT_DIR / "pymol/pymol/data/startup")),
    str(pathlib.Path(f"{tmp_build_exe_path}/lib/pymol/data/startup")),
    dirs_exist_ok=True
  )
