#!/usr/bin/env bash
# Fails if a binary in a macOS app bundle needs a newer macOS than the app's
# LSMinimumSystemVersion (e.g. a numpy wheel built for macOS 14).
# Usage: tests/check_macos_min_version.sh <path to .app>
set -euo pipefail

APP="$1"
MIN_MACOS="$(plutil -extract LSMinimumSystemVersion raw "$APP/Contents/Info.plist")"
TOO_NEW=0
COUNT=0
while IFS= read -r -d '' FILE; do
  file -b "$FILE" | grep -q "Mach-O" || continue
  COUNT=$((COUNT + 1))
  # Minimum macOS of the binary (load command LC_BUILD_VERSION); older binaries have none
  MINOS="$(otool -l "$FILE" | awk '/cmd LC_BUILD_VERSION/ { found = 1 } found && $1 == "minos" { print $2; exit }')"
  [ -n "$MINOS" ] || continue
  if awk -v a="$MINOS" -v b="$MIN_MACOS" 'BEGIN { split(a, x, "."); split(b, y, "."); exit !(x[1] > y[1] || (x[1] == y[1] && x[2] > y[2])) }'; then
    echo "Needs macOS ${MINOS}: ${FILE#"$APP"/}" >&2
    TOO_NEW=1
  fi
done < <(find "$APP" -type f -print0)

if [ "$TOO_NEW" -ne 0 ]; then
  echo "These binaries need a newer macOS than the app's minimum (macOS ${MIN_MACOS})." >&2
  exit 1
fi
echo "All ${COUNT} binaries run on macOS ${MIN_MACOS}"
