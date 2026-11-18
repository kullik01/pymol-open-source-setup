import os
import sys

import pymol


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
  if sys.platform == "darwin":
    native_mac_cert = "/etc/ssl/cert.pem"
    if os.path.exists(native_mac_cert):
      os.environ["SSL_CERT_FILE"] = native_mac_cert
      os.environ["REQUESTS_CA_BUNDLE"] = native_mac_cert

  _prefer_xwayland_on_linux()

  pymol.launch(sys.argv)
