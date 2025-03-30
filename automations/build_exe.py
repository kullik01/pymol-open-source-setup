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
import sys
import pathlib
import shutil
import subprocess

import const


class BuildExe:
  """Contains the logic for building the macOS EXE file."""

  def __init__(self) -> None:
    """Constructor."""
    self.pymol_data_path = pathlib.Path(const.PROJECT_ROOT_DIR / "pymol/pymol/data")
    self.build_script_filepath = pathlib.Path(
      const.OS_SPECIFIC_DIR / "setup_build_exe.py"
    )
    self.build_dir = pathlib.Path(const.OS_SPECIFIC_DIR / "build")

  def setup_build_environment(self) -> None:
    """Sets up a temporary build environment."""
    # <editor-fold desc="Path/Filepath definitions">
    tmp_edited_pmg_qt_filepath = pathlib.Path(
      const.PROJECT_ROOT_DIR / "edited/pmg_qt" / "pymol_qt_gui.py"
    )
    tmp_edited_base_css_filepath = pathlib.Path(
      const.PROJECT_ROOT_DIR / "edited/pymol/data/pymol", "base.css"
    )
    tmp_edited_init_py_filepath = pathlib.Path(
      const.PROJECT_ROOT_DIR / "edited/pymol", "__init__.py"
    )
    tmp_alternative_logo_filepath = pathlib.Path(
      const.PROJECT_ROOT_DIR / "alternative_design" / "alt_logo.png"
    )
    tmp_alternative_splash_screen_filepath = pathlib.Path(
      const.OS_SPECIFIC_DIR / "splash.png"
    )
    # </editor-fold>
    # <editor-fold desc="Custom file replacements">
    shutil.copy(
      tmp_edited_base_css_filepath,
      pathlib.Path(const.PYMOL_PACKAGE_DIR / "base.css")
    )
    shutil.copy(
      tmp_edited_pmg_qt_filepath,
      pathlib.Path(const.PYMOL_PACKAGE_DIR.parent / "pmg_qt", "pymol_qt_gui.py")
    )
    shutil.copy(
      tmp_edited_init_py_filepath,
      pathlib.Path(const.PYMOL_PACKAGE_DIR / "__init__.py")
    )
    shutil.copy(
      tmp_alternative_logo_filepath,
      pathlib.Path(const.PYMOL_PACKAGE_DIR / "data/pymol/icons", "alt_logo.png")
    )
    shutil.copy(
      tmp_alternative_splash_screen_filepath,
      pathlib.Path(const.PYMOL_PACKAGE_DIR / "data/pymol", "splash.png")
    )
    # </editor-fold>

  def setup_based_build(self) -> None:
    """Uses the cx_freeze setup.py for the build process."""
    self.setup_build_environment()
    if const.WIN32 or const.__linux__:
      subprocess.run(
        [const.PYTHON_EXECUTABLE, self.build_script_filepath, "build_exe"],
        stdout=sys.stdout, stderr=sys.stderr, text=True, cwd=const.OS_SPECIFIC_DIR
      )
    elif const.__APPLE__:
      subprocess.run(
        [const.PYTHON_EXECUTABLE, self.build_script_filepath, "bdist_mac"],
        stdout=sys.stdout, stderr=sys.stderr, text=True, cwd=const.OS_SPECIFIC_DIR
      )
    else:
      const.invalid_platform()
    shutil.copytree(self.build_dir, pathlib.Path(const.PROJECT_ROOT_DIR / "dist"),
                    dirs_exist_ok=True)


def build() -> None:
  """Builds the EXE file but based on the setup.py for cx_freeze."""
  tmp_builder = BuildExe()
  tmp_builder.setup_based_build()
