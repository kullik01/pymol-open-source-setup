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
import pathlib
import subprocess

import const


def setup_dev_env() -> None:
  """Installs the dependencies needed for building the _cmd extension module."""
  # <editor-fold desc="OS specific code">
  if const.WIN32:
    tmp_pip_exe_filepath = pathlib.Path(const.PROJECT_ROOT_DIR / ".venv/Scripts/pip")
  elif const.__APPLE__ or const.__linux__:
    tmp_pip_exe_filepath = pathlib.Path(const.PROJECT_ROOT_DIR / ".venv/bin/pip")
  else:
    exit(const.invalid_platform())
  # </editor-fold>
  subprocess.run([tmp_pip_exe_filepath, "install", "pymol-open-source-whl"])

  # # <editor-fold desc="Setup pymol-open-source repository">
  # # TODO: use the GitHelper class from the py-automator package
  # if not pathlib.Path(f"{const.PROJECT_ROOT_DIR}/vendor/pymol-open-source").exists():
  #   subprocess.run(["git", "clone", "https://github.com/schrodinger/pymol-open-source.git",
  #                   pathlib.Path(f"{const.PROJECT_ROOT_DIR}/vendor/pymol-open-source")])
  #   subprocess.run(["git", "checkout", "0313aeba9d75f464e4dddccc3bdbee71a5afb049"],
  #                  cwd=pathlib.Path(f"{const.PROJECT_ROOT_DIR}/vendor/pymol-open-source"))
  #   subprocess.run([pathlib.Path(f"{const.PROJECT_ROOT_DIR}/.venv/bin/python"), pathlib.Path(f"{const.PROJECT_ROOT_DIR}/scripts/python/create_generated_files.py")])
  # else:
  #   print("pymol-open-source already setup.")
  # # </editor-fold>
  # # if not pathlib.Path(f"{const.PROJECT_ROOT_DIR}/vendor/vcpkg").exists():
  # #   subprocess.run(["git", "clone", "https://github.com/microsoft/vcpkg.git", pathlib.Path(f"{const.PROJECT_ROOT_DIR}/vendor/vcpkg")])
  # #   subprocess.run(["chmod", "+x", "./bootstrap-vcpkg.sh"], cwd=pathlib.Path(const.PROJECT_ROOT_DIR / "vendor/vcpkg"))
  # #   subprocess.run(["./bootstrap-vcpkg.sh"], shell=True, cwd=pathlib.Path(const.PROJECT_ROOT_DIR / "vendor/vcpkg"))
  # #   subprocess.run([pathlib.Path(const.PROJECT_ROOT_DIR / "vendor/vcpkg" / "vcpkg"), "install"], shell=True)
  # # else:
  # #   print("vcpkg already setup.")
  #
  # if not pathlib.Path(f"{const.PROJECT_ROOT_DIR}/vendor/create-dmg").exists():
  #   subprocess.run(["git", "clone", "https://github.com/create-dmg/create-dmg.git", pathlib.Path(f"{const.PROJECT_ROOT_DIR}/vendor/create-dmg")])
  # else:
  #   print("create-dmg already setup.")
