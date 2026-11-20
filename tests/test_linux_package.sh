#!/usr/bin/env bash
# Installs a PyMOL-Open-Source .deb/.rpm package on a clean Linux distribution
# (e.g. inside a container) and runs the headless and GUI smoke tests.
# The package manager resolves the declared dependencies, so this verifies that
# the package declares everything it needs.
#
# With a second package (the previous release), that one is installed first, so the
# test also checks that the new package replaces it completely (update test).
#
# Usage (as root): tests/test_linux_package.sh <path to .deb or .rpm> [<previous release>]
set -euo pipefail

PACKAGE="$(realpath "$1")"
PREVIOUS="${2:+$(realpath "$2")}"
TESTS_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=/dev/null
source /etc/os-release
echo "=== Testing $(basename "$PACKAGE") on ${PRETTY_NAME}"

# Retries a command, e.g. if a distribution mirror is temporarily out of sync
# Up to 3 attempts of at most 4 minutes each: a stuck package mirror fails the attempt
# instead of the whole CI job (15 minutes)
retry() {
  for ATTEMPT in 1 2 3; do
    timeout 240 "$@" && return 0
    echo "Attempt ${ATTEMPT} failed: $*" >&2
    [ "$ATTEMPT" -lt 3 ] && sleep 30
  done
  return 1
}

# Installs packages with the distribution's package manager
case " ${ID} ${ID_LIKE:-} " in
  *" debian "*|*" ubuntu "*)
    export DEBIAN_FRONTEND=noninteractive
    retry apt-get update -qq
    install_packages() { retry apt-get install -y -qq "$@" > /dev/null; }
    TEST_PACKAGES=(xvfb libgl1-mesa-dri shared-mime-info)
    ;;
  *" fedora "*|*" rhel "*)
    # Leave mirrors slower than 100 kB/s (dnf's default limit is 1 kB/s)
    install_packages() { retry dnf install -y -q --setopt=minrate=100k --setopt=timeout=30 "$@"; }
    TEST_PACKAGES=(xorg-x11-server-Xvfb mesa-dri-drivers shared-mime-info)
    ;;
  *" suse "*|*" opensuse "*)
    install_packages() { retry zypper --non-interactive --quiet install --allow-unsigned-rpm "$@"; }
    TEST_PACKAGES=(xorg-x11-server-Xvfb Mesa-dri shared-mime-info)
    ;;
  *)
    echo "Unsupported distribution: ${ID}" >&2
    exit 1
    ;;
esac

# Update test: install the previous release first, then the new package over it
if [ -n "$PREVIOUS" ]; then
  echo "Installing the previous release $(basename "$PREVIOUS")"
  install_packages "$PREVIOUS"
fi
# For the GUI test also an X server and the Mesa OpenGL drivers (part of every desktop)
install_packages "$PACKAGE" "${TEST_PACKAGES[@]}"

# Only the new version remains: one folder in /opt, the current command
INSTALL_FOLDERS=(/opt/PyMOL-Open-Source-*)
if [ "${#INSTALL_FOLDERS[@]}" -ne 1 ] || [ -e /usr/bin/Open-Source-PyMOL ]; then
  echo "Older versions are left: ${INSTALL_FOLDERS[*]} /usr/bin/Open-Source-PyMOL" >&2
  exit 1
fi
echo "Installed: ${INSTALL_FOLDERS[0]}"

# Desktop integration: menu entry, icon and software center metadata
for FILE in /usr/share/applications/pymol-open-source.desktop /usr/share/icons/hicolor/256x256/apps/pymol-open-source.png \
    /usr/share/metainfo/io.github.kullik01.pymol-open-source.metainfo.xml \
    /usr/share/mime/packages/pymol-open-source.xml; do
  test -s "$FILE" || { echo "Missing: $FILE" >&2; exit 1; }
done
# The package manager's trigger updates the MIME database for the new file types (.cif, .pse)
for MIME_TYPE in chemical/x-cif application/x-pymol-session; do
  grep -qF "$MIME_TYPE" /usr/share/mime/globs2 || { echo "MIME database not updated: $MIME_TYPE" >&2; exit 1; }
done
echo "MIME types registered"

EXECUTABLE=/usr/bin/PyMOL-Open-Source
timeout 300 "$TESTS_DIR/run_smoke_test.sh" "$EXECUTABLE"

Xvfb :99 -screen 0 1280x1024x24 -nolisten tcp > /dev/null 2>&1 &
XVFB_PID=$!
trap 'kill $XVFB_PID 2> /dev/null || true' EXIT
sleep 2
DISPLAY=:99 timeout 300 "$TESTS_DIR/run_smoke_test.sh" --gui "$EXECUTABLE"
