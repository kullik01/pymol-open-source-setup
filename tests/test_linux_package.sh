#!/usr/bin/env bash
# Installs a PyMOL-Open-Source .deb/.rpm package on a clean Linux distribution
# (e.g. inside a container) and runs the headless and GUI smoke tests.
# The package manager resolves the declared dependencies, so this verifies that
# the package declares everything it needs.
#
# Usage (as root): tests/test_linux_package.sh <path to .deb or .rpm>
set -euo pipefail

PACKAGE="$(realpath "$1")"
TESTS_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=/dev/null
source /etc/os-release
echo "=== Testing $(basename "$PACKAGE") on ${PRETTY_NAME}"

# Retries a command, e.g. if a distribution mirror is temporarily out of sync
retry() {
  for ATTEMPT in 1 2 3; do
    "$@" && return 0
    echo "Attempt ${ATTEMPT} failed: $*" >&2
    [ "$ATTEMPT" -lt 3 ] && sleep 30
  done
  return 1
}

# Install the package and, for the GUI test, an X server and the Mesa
# OpenGL drivers (both are part of every desktop installation)
case " ${ID} ${ID_LIKE:-} " in
  *" debian "*|*" ubuntu "*)
    export DEBIAN_FRONTEND=noninteractive
    retry apt-get update -qq
    retry apt-get install -y -qq "$PACKAGE" xvfb libgl1-mesa-dri > /dev/null
    ;;
  *" fedora "*|*" rhel "*)
    retry dnf install -y -q "$PACKAGE" xorg-x11-server-Xvfb mesa-dri-drivers
    ;;
  *" suse "*|*" opensuse "*)
    retry zypper --non-interactive --quiet install --allow-unsigned-rpm "$PACKAGE" xorg-x11-server-Xvfb Mesa-dri
    ;;
  *)
    echo "Unsupported distribution: ${ID}" >&2
    exit 1
    ;;
esac

# Desktop integration: menu entry, icon and software center metadata
for FILE in /usr/share/applications/open-source-pymol.desktop /usr/share/pixmaps/open-source-pymol.png \
    /usr/share/metainfo/io.github.kullik01.pymol-open-source.metainfo.xml \
    /usr/share/mime/packages/open-source-pymol.xml; do
  test -s "$FILE" || { echo "Missing: $FILE" >&2; exit 1; }
done
# The package manager updates the MIME database for the new file types (.cif, .pse),
# if the shared MIME database is installed
if [ -f /usr/share/mime/globs2 ]; then
  grep -q "application/x-pymol-session" /usr/share/mime/globs2 || { echo "MIME database not updated" >&2; exit 1; }
  echo "MIME types registered"
fi

EXECUTABLE=/usr/bin/Open-Source-PyMOL
timeout 300 "$TESTS_DIR/run_smoke_test.sh" "$EXECUTABLE"

Xvfb :99 -screen 0 1280x1024x24 -nolisten tcp > /dev/null 2>&1 &
XVFB_PID=$!
trap 'kill $XVFB_PID 2> /dev/null || true' EXIT
sleep 2
DISPLAY=:99 timeout 300 "$TESTS_DIR/run_smoke_test.sh" --gui "$EXECUTABLE"
