import os
import sys

import pymol

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
  """
  if os.environ.get("SSL_CERT_FILE") or os.environ.get("SSL_CERT_DIR"):
    return
  for tmp_filepath in CA_BUNDLE_FILEPATHS.get(sys.platform, ()):
    if os.path.isfile(tmp_filepath):
      os.environ["SSL_CERT_FILE"] = tmp_filepath
      os.environ.setdefault("REQUESTS_CA_BUNDLE", tmp_filepath)
      return


def _prefer_xwayland_on_linux() -> None:
  """Runs PyMOL through XWayland (Qt "xcb") on Linux Wayland sessions.

  The bundled Qt 5 auto-selects its own Wayland platform plugin on Wayland
  sessions (e.g. KDE Plasma 6). PyMOL's legacy QGLWidget does not work with
  it: the viewer turns translucent/black and flickers on resize.

  Nothing is changed if:
    - the OS is not Linux (Windows and macOS are unaffected),
    - the user already chose a platform via QT_QPA_PLATFORM,
    - the session is not Wayland (plain X11 already uses xcb),
    - no X display is available (no XWayland), to avoid a startup crash.
  """
  if not sys.platform.startswith("linux"):
    return
  if os.environ.get("QT_QPA_PLATFORM"):
    return
  is_wayland_session = (
    os.environ.get("XDG_SESSION_TYPE", "").lower() == "wayland"
    or bool(os.environ.get("WAYLAND_DISPLAY"))
  )
  if is_wayland_session and os.environ.get("DISPLAY"):
    os.environ["QT_QPA_PLATFORM"] = "xcb"


if __name__ == '__main__':
  _use_system_ca_certificates()
  _prefer_xwayland_on_linux()

  pymol.launch(sys.argv)
