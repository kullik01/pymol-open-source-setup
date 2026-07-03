import sys
import os
import pathlib
import pymol


if __name__ == '__main__':
  if getattr(sys, 'frozen', False):
    exe_dir = pathlib.Path(sys.executable).parent

    if sys.platform == "darwin":
      # On macOS, cx_Freeze places included files relative to the binary
      cert_file = exe_dir / "cacert.pem"
    # Could become helpful
    # elif sys.platform == "win32":
    #   # On Windows, it's typically in the same root directory as the .exe
    #   cert_file = exe_dir / "cacert.pem"
    # else:
    #   # Linux layout safely handles the fallback
    #   cert_file = exe_dir / "cacert.pem"

      # Apply the fix globally to Python's SSL and requests libraries
      if cert_file.exists():
        os.environ["SSL_CERT_FILE"] = str(cert_file)
        os.environ["REQUESTS_CA_BUNDLE"] = str(cert_file)

  pymol.launch(sys.argv)
