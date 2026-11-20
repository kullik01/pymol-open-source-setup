"""Smoke test for a frozen PyMOL-Open-Source application.

Run it with the frozen executable, use tests/run_smoke_test.sh:
  headless:          tests/run_smoke_test.sh <executable>
  with the Qt GUI:   tests/run_smoke_test.sh --gui <executable>   (needs a display, e.g. Xvfb)

With PYMOL_SMOKE_TEST_ONLINE=1 it also downloads a structure from the PDB (HTTPS).
Note: the certificate check fails if only SSL_CERT_DIR is set (lazily loaded).

Prints "SMOKE TEST OK" on success, otherwise exits with status 1.
"""
import faulthandler
import os
import pathlib
import sys
import ssl
import tempfile
import time
import traceback
import urllib.error
import urllib.request

# On a crash (e.g. in the OpenGL driver) print the Python stacks of all threads.
# Enable it before importing PyMOL, which replaces sys.stderr with an object without fileno().
try:
  faulthandler.enable(file=sys.__stderr__)
except (AttributeError, ValueError, OSError):
  pass  # no usable stderr (e.g. a GUI executable without console)

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


def check_licenses() -> None:
  """The license texts must be shipped next to the executable (macOS: in Resources)."""
  exe_dir = pathlib.Path(os.path.realpath(sys.executable)).parent
  candidates = (exe_dir / "licenses", exe_dir.parent / "Resources" / "licenses")
  licenses_dir = next((d for d in candidates if d.is_dir()), None)
  assert licenses_dir is not None, f"licenses folder missing next to {exe_dir}"
  for tmp_name in ("README.txt", "THIRD-PARTY-NOTICES.txt", "pymol-open-source-whl/LICENSE",
                   "LGPL-3.0.txt", "PySide6_Essentials/LGPL-3.0.txt", "Python/LICENSE.txt"):
    assert (licenses_dir / tmp_name).is_file(), f"license file missing: {tmp_name}"
  if sys.platform == "win32":
    assert (exe_dir / "share" / "licenses" / "vc_redist").is_dir(), "license of the C++ runtime missing"


def check_certificates() -> None:
  """HTTPS needs CA certificates: on Windows from the Windows store, otherwise from the file
  that startup_wrapper.py sets as SSL_CERT_FILE."""
  tmp_count = ssl.create_default_context().cert_store_stats()["x509_ca"]
  assert tmp_count > 0, f"no CA certificates loaded (SSL_CERT_FILE={os.environ.get('SSL_CERT_FILE')})"


def check_online(a_tmp_dir: str) -> bool:
  """Downloads a structure from the PDB. Returns False if the online check is switched off."""
  if os.environ.get("PYMOL_SMOKE_TEST_ONLINE") != "1":
    return False
  # cmd.fetch reports every error the same way, so check the HTTPS connection first:
  # a certificate error fails at once, network problems get retried
  for tmp_attempt in range(1, 4):
    try:
      with urllib.request.urlopen("https://files.rcsb.org/header/1UBQ.cif", timeout=30) as tmp_response:
        tmp_response.read(64)
      break
    except OSError as tmp_error:
      # URLError wraps the cause in "reason"; timeouts and resets while
      # reading arrive unwrapped
      tmp_reason = getattr(tmp_error, "reason", tmp_error)
      if isinstance(tmp_reason, ssl.SSLCertVerificationError) or tmp_attempt == 3:
        raise
      time.sleep(10)
  cmd.fetch("1ubq", path=a_tmp_dir, type="cif", quiet=1)
  assert cmd.count_atoms("1ubq") > 0, "fetch 1ubq loaded no atoms"
  return True


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
  from pymol.Qt import PYQT_NAME, QtWidgets, utils
  tmp_app = QtWidgets.QApplication.instance()
  assert tmp_app is not None, "Qt GUI is not running"
  assert not tmp_app.windowIcon().isNull(), "window icon is missing"
  tmp_png = os.path.join(a_tmp_dir, "opengl.png")
  cmd.png(tmp_png, width=200, height=150, ray=0)
  assert os.path.getsize(tmp_png) > 1000, "OpenGL rendered image is empty"
  # PyMOL's dialogs are .ui forms, loaded like in pmg_qt/pymol_qt_gui.py
  import pmg_qt.pymol_qt_gui
  tmp_form = os.path.join(os.path.dirname(pmg_qt.pymol_qt_gui.__file__), "forms", "fetch.ui")
  tmp_widget = QtWidgets.QWidget()
  assert utils.loadUi(tmp_form, tmp_widget) is not None, "loading a .ui form failed"
  return f"GUI, {PYQT_NAME}, Qt platform {tmp_app.platformName()}"


try:
  check_bundled_modules_and_data()
  check_licenses()
  check_certificates()
  with tempfile.TemporaryDirectory() as tmp_dir:
    check_commands(tmp_dir)
    tmp_mode = check_gui(tmp_dir)
    if check_online(tmp_dir):
      tmp_mode += ", online"
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
