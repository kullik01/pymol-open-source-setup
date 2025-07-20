import sys
import pymol


if __name__ == '__main__':
  pymol.launch(sys.argv)

# Coping startup_wrapper and OS specific build scripts into the application package
# <editor-fold desc="Definitions">
# startup_wrapper script
tmp_edited_startup_wrapper_py_filepath = pathlib.Path(
  const.PROJECT_ROOT_DIR / "edited/pymol", "startup_wrapper.py"
)

# OS specific build script
tmp_os_specific_build_exe_filepath = pathlib.Path(
  const.OS_SPECIFIC_SETUP_BUILD_EXE
)
# </editor-fold>

# <editor-fold desc="Copy">
# startup_wrapper script
shutil.copy(
  tmp_edited_startup_wrapper_py_filepath,
  pathlib.Path(const.PYMOL_PACKAGE_DIR / "startup_wrapper.py")
)

# OS specific build script
shutil.copy(
  tmp_os_specific_build_exe_filepath,
  pathlib.Path(const.PYMOL_PACKAGE_DIR / "setup_build_exe.py")
)
# </editor-fold>
