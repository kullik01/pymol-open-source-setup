#!/usr/bin/env bash
# Packages the frozen Linux application (dist/exe.linux-*) as .tar.gz, .deb and .rpm
# into os_specific/dist. Run "./automator.sh build app" first.
#
# Usage: os_specific/linux/build_packages.sh
# Requires fpm (https://fpm.readthedocs.io) and rpmbuild for the .deb/.rpm packages.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT_DIR"

APP_NAME="PyMOL-Open-Source"
VERSION="$(sed -n 's/^version = "\(.*\)"/\1/p' pyproject.toml)"
INSTALL_DIR="/opt/${APP_NAME}-${VERSION}"
OUT_DIR="os_specific/dist"

shopt -s nullglob
FROZEN_APP_DIRS=(dist/exe.linux-*)
if [ ${#FROZEN_APP_DIRS[@]} -ne 1 ]; then
  echo "Expected exactly one dist/exe.linux-* directory. Run './automator.sh build app' first." >&2
  exit 1
fi
FROZEN_APP_DIR="${FROZEN_APP_DIRS[0]}"

STAGING_DIR="$(mktemp -d)"
trap 'rm -rf "$STAGING_DIR"' EXIT
mkdir -p "$OUT_DIR"

# --- Files for the .deb/.rpm packages besides the application itself
sed "s|/opt/open-source-pymol|${INSTALL_DIR}|g" \
  os_specific/linux/open-source-pymol.desktop > "$STAGING_DIR/open-source-pymol.desktop"
ln -s "${INSTALL_DIR}/Open-Source-PyMOL" "$STAGING_DIR/Open-Source-PyMOL"
METAINFO="io.github.kullik01.pymol-open-source.metainfo.xml"
sed -e "s|@VERSION@|${VERSION}|" -e "s|@DATE@|$(date -u +%F)|" \
  "os_specific/linux/${METAINFO}" > "$STAGING_DIR/${METAINFO}"

# System libraries that are not bundled: OpenGL, GLib, D-Bus, fonts and the
# X11/XCB/Wayland libraries of the Qt platform plugins, plus the CA certificates
# for HTTPS (e.g. fetching structures from the PDB).
DEB_DEPENDS=(
  ca-certificates
  libdbus-1-3 libegl1 libfontconfig1 libfreetype6 libgl1 libglib2.0-0
  libwayland-client0 libwayland-cursor0 libwayland-egl1
  libx11-6 libx11-xcb1 libxext6 libxrender1 libxkbcommon0 libxkbcommon-x11-0
  libxcb1 libxcb-glx0 libxcb-icccm4 libxcb-image0 libxcb-keysyms1 libxcb-randr0
  libxcb-render0 libxcb-render-util0 libxcb-shape0 libxcb-shm0 libxcb-sync1
  libxcb-util1 libxcb-xfixes0 libxcb-xinerama0 libxcb-xkb1
)
# RPM dependencies use library names, so they work on Fedora, RHEL/Rocky/Alma
# and openSUSE although the package names differ between these distributions.
RPM_SONAMES=(
  libdbus-1.so.3 libEGL.so.1 libfontconfig.so.1 libfreetype.so.6 libGL.so.1
  libglib-2.0.so.0 libgthread-2.0.so.0
  libwayland-client.so.0 libwayland-cursor.so.0 libwayland-egl.so.1
  libX11.so.6 libX11-xcb.so.1 libXext.so.6 libXrender.so.1 libxkbcommon.so.0 libxkbcommon-x11.so.0
  libxcb.so.1 libxcb-glx.so.0 libxcb-icccm.so.4 libxcb-image.so.0 libxcb-keysyms.so.1 libxcb-randr.so.0
  libxcb-render.so.0 libxcb-render-util.so.0 libxcb-shape.so.0 libxcb-shm.so.0 libxcb-sync.so.1
  libxcb-util.so.1 libxcb-xfixes.so.0 libxcb-xinerama.so.0 libxcb-xkb.so.1
)
RPM_SONAMES=("${RPM_SONAMES[@]/%/()(64bit)}")

FPM_ARGS=(
  -s dir
  --version "$VERSION"
  # This project's code (BSD-3-Clause), the bundled Qt/PySide6 (LGPL-3.0) and PyMOL (its own license)
  --license "BSD-3-Clause AND LGPL-3.0-only AND LicenseRef-PyMOL"
  --maintainer "Hannah Kullik <hannah.kullik@studmail.w-hs.de>, Martin Urban <martin.urban@studmail.w-hs.de>"
  --vendor "Hannah Kullik, Martin Urban"
  --url "https://kullik01.github.io/pymol-open-source-setup"
  --category science
  --description "Open-Source PyMOL - molecular visualization system (unofficial build)"
  --force
)
PACKAGE_CONTENTS=(
  "${FROZEN_APP_DIR}/=${INSTALL_DIR}/"
  "$STAGING_DIR/Open-Source-PyMOL=/usr/bin/Open-Source-PyMOL"
  "$STAGING_DIR/open-source-pymol.desktop=/usr/share/applications/open-source-pymol.desktop"
  "os_specific/linux/logo.png=/usr/share/pixmaps/open-source-pymol.png"
  "$STAGING_DIR/${METAINFO}=/usr/share/metainfo/${METAINFO}"
  "os_specific/linux/open-source-pymol-mime.xml=/usr/share/mime/packages/open-source-pymol.xml"
)

# Portable archive: extracts into a single PyMOL-Open-Source-<version>/ directory
build_tarball() {
  tar -C dist -czf "$OUT_DIR/${APP_NAME}_v${VERSION}.tar.gz" \
    --transform "s|^${FROZEN_APP_DIR#dist/}|${APP_NAME}-${VERSION}|" \
    "${FROZEN_APP_DIR#dist/}"
}

build_deb() {
  # Debian package names must be lowercase
  fpm "${FPM_ARGS[@]}" -t deb --name "${APP_NAME,,}" --architecture amd64 \
    --package "$OUT_DIR/${APP_NAME}_v${VERSION}_amd64.deb" \
    "${DEB_DEPENDS[@]/#/--depends=}" \
    "${PACKAGE_CONTENTS[@]}"
}

build_rpm() {
  # No /usr/lib/.build-id links: they would conflict with other packages that
  # contain the same (bundled) libraries.
  fpm "${FPM_ARGS[@]}" -t rpm --name "$APP_NAME" --architecture x86_64 \
    --rpm-rpmbuild-define "_build_id_links none" \
    --package "$OUT_DIR/${APP_NAME}_v${VERSION}_x86_64.rpm" \
    --depends=ca-certificates \
    "${RPM_SONAMES[@]/#/--depends=}" \
    "${PACKAGE_CONTENTS[@]}"
}

# Each package compresses the whole application on a single CPU core, so the
# three packages are built in parallel. Their output is shown one after another.
PACKAGE_BUILDS=(build_tarball build_deb build_rpm)
PIDS=()
for BUILD in "${PACKAGE_BUILDS[@]}"; do
  "$BUILD" > "$STAGING_DIR/$BUILD.log" 2>&1 &
  PIDS+=("$!")
done
FAILED=0
for INDEX in "${!PACKAGE_BUILDS[@]}"; do
  BUILD="${PACKAGE_BUILDS[$INDEX]}"
  if wait "${PIDS[$INDEX]}"; then
    echo "--- ${BUILD}: done"
  else
    echo "--- ${BUILD}: FAILED" >&2
    FAILED=1
  fi
  cat "$STAGING_DIR/$BUILD.log"
done
if [ "$FAILED" -ne 0 ]; then
  exit 1
fi

ls -l "$OUT_DIR"
