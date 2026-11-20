import os
import sys

# System certificate files (CA bundles), in the order they are tried
CA_BUNDLE_FILEPATHS = {
  "darwin": ("/etc/ssl/cert.pem",),
  "linux": (
    "/etc/ssl/certs/ca-certificates.crt",                 # Debian, Ubuntu, Arch, Fedora
    "/etc/pki/tls/certs/ca-bundle.crt",                   # Fedora, RHEL, Rocky, Alma
    "/etc/ssl/ca-bundle.pem",                             # openSUSE
    "/etc/pki/ca-trust/extracted/pem/tls-ca-bundle.pem",  # RHEL, CentOS
    "/etc/ssl/cert.pem",                                  # Alpine, others
  ),
}


def _use_system_ca_certificates() -> None:
  """Lets HTTPS (e.g. fetching structures from the PDB) use the system's certificates.

  The OpenSSL bundled by cx_Freeze on Linux looks for certificates in paths of
  its build environment that exist on no real system, so every HTTPS
  connection fails with CERTIFICATE_VERIFY_FAILED. On macOS the frozen app has
  the same problem. Windows uses the Windows certificate store instead.

  Nothing is changed if the user already set SSL_CERT_FILE or SSL_CERT_DIR.
  Must run before ssl is imported: cx_Freeze's ssl hook then keeps this file
  instead of the certificate file it copied from the build machine.
  """
  if os.environ.get("SSL_CERT_FILE") or os.environ.get("SSL_CERT_DIR"):
    return
  for tmp_filepath in CA_BUNDLE_FILEPATHS.get(sys.platform, ()):
    if os.path.isfile(tmp_filepath):
      os.environ["SSL_CERT_FILE"] = tmp_filepath
      os.environ.setdefault("REQUESTS_CA_BUNDLE", tmp_filepath)
      return


def _use_pyside6() -> None:
  """Selects PySide6 for PyMOL's Qt layer (pymol.Qt), the only Qt binding of the app.

  Overrides a QT_API the user set for another binding (e.g. pyqt5), which
  the app does not contain and pymol.Qt would then fail to import.
  """
  os.environ["QT_API"] = "pyside6"


def _use_whole_scale_on_wayland() -> None:
  """Gives the window a whole-number scale on native Wayland (e.g. 2 at 150 %).

  With fractional scaling, Qt first gives a Wayland window the screen's scale
  (2) and switches to the fractional one (1.5) after it is shown. PyMOL then
  discards the splash screen (black view), and at fractional scales it draws
  its own panel text smaller. Rounding up keeps one scale from the start; the
  compositor scales the window down sharply. X11, Windows and macOS keep
  their scales. Nothing is changed if the user set the rounding policy.
  """
  if (not sys.platform.startswith("linux") or not os.environ.get("WAYLAND_DISPLAY")
      or os.environ.get("QT_SCALE_FACTOR_ROUNDING_POLICY")):
    return
  if os.environ.get("QT_QPA_PLATFORM", "wayland").startswith("wayland"):
    os.environ["QT_SCALE_FACTOR_ROUNDING_POLICY"] = "Ceil"


if __name__ == '__main__':
  _use_system_ca_certificates()
  _use_pyside6()
  _use_whole_scale_on_wayland()

  import pymol  # only after the environment is set up (imports ssl)
  pymol.launch(sys.argv)
