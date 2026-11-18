"""Smoke test for a frozen PyMOL-Open-Source application.

Run it with the frozen executable, use tests/run_smoke_test.sh:
  headless:          tests/run_smoke_test.sh <executable>
  with the Qt GUI:   tests/run_smoke_test.sh --gui <executable>   (needs a display, e.g. Xvfb)

Prints "SMOKE TEST OK" on success, otherwise exits with status 1.
"""
import os
import sys
import tempfile
import traceback

import pymol
from pymol import cmd


def check_bundled_modules_and_data() -> None:
  # Modules that must be bundled explicitly or are loaded dynamically
  import ssl  # noqa: F401
  import uuid  # noqa: F401
  import pymol.parser  # noqa: F401
  import pymol.povray  # noqa: F401
  import pymol.vfont  # noqa: F401
  import pymol.wizard.mutagenesis  # noqa: F401
  import Bio  # noqa: F401  (used by pymol.seqalign)

  for tmp_path in ("data/startup", "data/pymol/splash.png", "data/pymol/icons/alt_logo.png"):
    tmp_full_path = os.path.join(os.environ["PYMOL_PATH"], tmp_path)
    assert os.path.exists(tmp_full_path), f"missing {tmp_full_path}"


def check_commands(a_tmp_dir: str) -> None:
  cmd.fragment("ala")
  assert cmd.count_atoms() == 10, cmd.count_atoms()
  cmd.wizard("mutagenesis")
  cmd.set_wizard()
  tmp_png = os.path.join(a_tmp_dir, "ray.png")
  cmd.png(tmp_png, width=200, height=150, ray=1)
  assert os.path.getsize(tmp_png) > 1000, "ray-traced image is empty"


def check_gui(a_tmp_dir: str) -> str:
  """Checks the Qt GUI and OpenGL rendering. Returns a description of the mode."""
  if pymol.invocation.options.no_gui:
    return "headless"
  from pymol.Qt import QtWidgets
  tmp_app = QtWidgets.QApplication.instance()
  assert tmp_app is not None, "Qt GUI is not running"
  assert not tmp_app.windowIcon().isNull(), "window icon is missing"
  tmp_png = os.path.join(a_tmp_dir, "opengl.png")
  cmd.png(tmp_png, width=200, height=150, ray=0)
  assert os.path.getsize(tmp_png) > 1000, "OpenGL rendered image is empty"
  return f"GUI, Qt platform {tmp_app.platformName()}"


try:
  check_bundled_modules_and_data()
  with tempfile.TemporaryDirectory() as tmp_dir:
    check_commands(tmp_dir)
    tmp_mode = check_gui(tmp_dir)
except Exception:
  traceback.print_exc()
  print("SMOKE TEST FAILED", flush=True)
  cmd.quit(1)
else:
  print(
    f"SMOKE TEST OK ({tmp_mode}, PyMOL {cmd.get_version()[0]}, Python {sys.version.split()[0]})",
    flush=True,
  )
  cmd.quit(0)
