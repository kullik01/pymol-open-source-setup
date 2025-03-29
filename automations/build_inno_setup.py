import pathlib
import shutil
import subprocess
import sys

import const


class BuildInnoSetup:
  """Contains the logic for building the inno setup EXE file."""

  def __init__(self) -> None:
    """Constructor."""
    self.inno_build_path = pathlib.Path(const.PROJECT_ROOT_DIR / "inno-build-release")
    self.inno_build_src_path = pathlib.Path(self.inno_build_path / "inno-sources")
    self.inno_build_assets_path = pathlib.Path(self.inno_build_path / "inno-assets")
    self.inno_setup_compiler_filepath = pathlib.Path(r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe")
    self.inno_setup_script_filepath = pathlib.Path(const.OS_SPECIFIC_DIR / "inno_setup" / "setup.iss")

  def setup_build_environment(self) -> None:
    """Sets up a temporary build environment."""
    # <editor-fold desc="Path/Filepath definitions">
    tmp_pymol_win_build_files_path = pathlib.Path(const.PROJECT_ROOT_DIR / f"dist/exe.win-amd64-{const.PYTHON_VERSION}")
    tmp_pymol_win_build_logo_filepath = pathlib.Path(const.OS_SPECIFIC_DIR / "logo.ico")
    tmp_vc_redist_setup_filepath = pathlib.Path(const.PROJECT_ROOT_DIR / "vendor/microsoft" / "VC_redist.x64.exe")
    # </editor-fold>
    """IMPORTANT
    Use the python interpreter of the venv of pymol windows build because
    that interpreter gets also used in the build script of the 
    pymol windows build repo!
    """
    # <editor-fold desc="Copy operations">
    if self.inno_build_path.exists():
      shutil.rmtree(self.inno_build_path)
      self.inno_build_path.mkdir()
    if not tmp_pymol_win_build_files_path.exists():
      print("Please run: automator build app")
    shutil.copytree(tmp_pymol_win_build_files_path, self.inno_build_src_path, dirs_exist_ok=True)
    shutil.copy(tmp_vc_redist_setup_filepath, self.inno_build_src_path)
    if not self.inno_build_assets_path.exists():
      self.inno_build_assets_path.mkdir()
    shutil.copy(tmp_pymol_win_build_logo_filepath, pathlib.Path(self.inno_build_assets_path / "logo.ico"))
    # </editor-fold>

  def build_inno_setup(self) -> None:
    """Builds the PyMOL Windows EXE file."""
    self.setup_build_environment()
    subprocess.run(
      [self.inno_setup_compiler_filepath, self.inno_setup_script_filepath],
      stdout=sys.stdout, stderr=sys.stderr, text=True
    )


def build() -> None:
  """Builds the inno setup EXE file."""
  tmp_builder = BuildInnoSetup()
  tmp_builder.build_inno_setup()
