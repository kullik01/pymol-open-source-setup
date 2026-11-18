#!/usr/bin/env bash
# Runs tests/smoke_test.py with a frozen PyMOL-Open-Source executable.
# Usage: tests/run_smoke_test.sh [--gui] <path to executable>
#   --gui  start the Qt GUI as well (needs a display, e.g. Xvfb); default is headless
set -uo pipefail

PYMOL_FLAGS="-cq"
if [ "${1:-}" = "--gui" ]; then
  PYMOL_FLAGS="-q"
  shift
fi
if [ $# -ne 1 ]; then
  echo "Usage: $0 [--gui] <path to executable>" >&2
  exit 2
fi

SMOKE_TEST="$(cd "$(dirname "$0")" && pwd)/smoke_test.py"
LOG_FILE="$(mktemp)"
trap 'rm -f "$LOG_FILE"' EXIT

"$1" "$PYMOL_FLAGS" "$SMOKE_TEST" 2>&1 | tee "$LOG_FILE"
EXIT_CODE=${PIPESTATUS[0]}

# Checking the output as well ensures the test script was really executed
if [ "$EXIT_CODE" -ne 0 ] || ! grep -q "SMOKE TEST OK" "$LOG_FILE"; then
  echo "Smoke test failed (exit code $EXIT_CODE)" >&2
  exit 1
fi
