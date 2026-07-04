import sys
import os
import pathlib
import pymol


if __name__ == '__main__':
  if sys.platform == "darwin":
    native_mac_cert = "/etc/ssl/cert.pem"
    if os.path.exists(native_mac_cert):
      os.environ["SSL_CERT_FILE"] = native_mac_cert
      os.environ["REQUESTS_CA_BUNDLE"] = native_mac_cert

  pymol.launch(sys.argv)
