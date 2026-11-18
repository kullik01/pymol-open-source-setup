#!/usr/bin/env bash
# Checks that the download links of the built website and the release files
# match: every link points to a release file and every release file is linked.
#
# Usage: <release file names, one per line> | tests/check_release_assets.sh <built website directory>
# e.g.   ls os_specific/dist | tests/check_release_assets.sh site
set -euo pipefail

if [ $# -ne 1 ]; then
  echo "Usage: <release file names> | $0 <built website directory>" >&2
  exit 2
fi
SITE_DIR="$1"

# grep fails without a match, which the check below reports
LINKED_FILES="$( { grep -rhoE 'releases/download/[^"]+' "$SITE_DIR" --include='*.html' || true; } \
  | sed 's|.*/||; s|%2B|+|g' | sort -u)"
RELEASE_FILES="$( { grep -v '^$' || true; } | sort -u)"

if [ -z "$LINKED_FILES" ] || [ -z "$RELEASE_FILES" ]; then
  echo "No download links or no release files found." >&2
  exit 1
fi
if [ "$LINKED_FILES" != "$RELEASE_FILES" ]; then
  echo "Website download links and release files differ ('<' only linked on the website, '>' only a release file):" >&2
  diff <(echo "$LINKED_FILES") <(echo "$RELEASE_FILES") | grep '^[<>]' >&2
  exit 1
fi
echo "All $(echo "$RELEASE_FILES" | wc -l) release files are linked on the website:"
echo "$RELEASE_FILES"
