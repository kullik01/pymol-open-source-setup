#!/usr/bin/env bash
# Packages the macOS app bundle (dist/PyMOL-Open-Source-<version>.app) as a DMG
# into os_specific/dist. Run "./automator.sh build app" first.
#
# Usage: os_specific/macos/build_dmg.sh
# Requires create-dmg (brew install create-dmg); CREATE_DMG can point to another copy.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT_DIR"

APP_NAME="PyMOL-Open-Source"
VERSION="$(sed -n 's/^version = "\(.*\)"/\1/p' pyproject.toml)"
APP_PATH="dist/${APP_NAME}-${VERSION}.app"
OUT_DIR="os_specific/dist"

if [ ! -d "$APP_PATH" ]; then
  echo "$APP_PATH does not exist. Run './automator.sh build app' first." >&2
  exit 1
fi

# The DMG name tells which Macs the app runs on, based on the built app itself:
# PyMOL, Qt and numpy must all be built for the same single architecture
LIB_DIR="$APP_PATH/Contents/Resources/lib"
ARCHS="$(for MODULE in "$LIB_DIR"/pymol/_cmd.*.so "$LIB_DIR"/PyQt5/QtCore.abi3.so \
    "$LIB_DIR"/numpy/core/_multiarray_umath.*.so; do
  lipo -archs "$MODULE" || exit 1
done | sort -u)"
case "$ARCHS" in
  arm64) ARCH_LABEL="AppleSilicon" ;;
  x86_64) ARCH_LABEL="Intel" ;;
  *)
    echo "PyMOL, Qt and numpy in ${APP_PATH} are built for '${ARCHS//$'\n'/, }'" \
      "(expected all arm64 or all x86_64)" >&2
    exit 1
    ;;
esac
DMG_NAME="${APP_NAME}_v${VERSION}_macOS_${ARCH_LABEL}"
CREATE_DMG="${CREATE_DMG:-create-dmg}"
if ! command -v "$CREATE_DMG" > /dev/null; then
  echo "create-dmg not found. Install it with: brew install create-dmg" >&2
  exit 1
fi
mkdir -p "$OUT_DIR"

# create-dmg sometimes fails on CI runners ("Resource busy"), so retry
for ATTEMPT in 1 2 3; do
  hdiutil detach "/Volumes/${DMG_NAME}" > /dev/null 2>&1 || true
  rm -f "${OUT_DIR}/${DMG_NAME}.dmg" "${OUT_DIR}"/rw.*.dmg
  if "$CREATE_DMG" \
      --volname "$DMG_NAME" \
      --background os_specific/macos/dmg/dmg_background.svg \
      --window-pos 200 120 \
      --window-size 660 400 \
      --icon-size 100 \
      --icon "$(basename "$APP_PATH")" 160 185 \
      --app-drop-link 500 185 \
      "${OUT_DIR}/${DMG_NAME}.dmg" \
      "$APP_PATH"; then
    ls -l "${OUT_DIR}/${DMG_NAME}.dmg"
    exit 0
  fi
  echo "create-dmg attempt ${ATTEMPT} failed" >&2
  [ "$ATTEMPT" -lt 3 ] && sleep 10
done
echo "Creating the DMG failed." >&2
exit 1
