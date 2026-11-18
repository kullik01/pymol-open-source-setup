#!/usr/bin/env bash
# Checks that the download links of the built website and the release files
# match: every link points to an existing file and every file is linked.
#
# Usage: tests/check_release_assets.sh <directory with release files> <built website directory>
set -euo pipefail

if [ $# -ne 2 ]; then
  echo "Usage: $0 <directory with release files> <built website directory>" >&2
  exit 2
fi
ASSETS_DIR="$1"
SITE_DIR="$2"

# grep fails without a match, which the check below reports
LINKED_FILES="$( { grep -rhoE 'releases/download/[^"]+' "$SITE_DIR" --include='*.html' || true; } \
  | sed 's|.*/||; s|%2B|+|g' | sort -u)"
RELEASE_FILES="$(for FILE in "$ASSETS_DIR"/*; do
  if [ -f "$FILE" ]; then echo "${FILE##*/}"; fi
done | sort)"

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
