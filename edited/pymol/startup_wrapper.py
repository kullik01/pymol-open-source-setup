import sys
import pymol


if __name__ == '__main__':
  pymol.launch(sys.argv)

# <editor-fold desc="Coping startup_wrapper script into the application package">
# Definition
tmp_edited_startup_wrapper_py_filepath = pathlib.Path(
  const.PROJECT_ROOT_DIR / "edited/pymol", "startup_wrapper.py"
)

# Copy
shutil.copy(
  tmp_edited_startup_wrapper_py_filepath,
  pathlib.Path(const.PYMOL_PACKAGE_DIR / "startup_wrapper.py")
)
# </editor-fold>
