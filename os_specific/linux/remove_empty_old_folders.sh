#!/bin/sh
# Runs after installing or updating the .deb/.rpm. Versions up to 3.1.0.4+4 did not
# own their folder in /opt, so an update left their (empty) folders behind. Removes
# only empty folders, never files, and needs no tools beyond the shell and rmdir.
remove_empty_folders() {
  for entry in "$1"/* "$1"/.[!.]*; do
    if [ -d "$entry" ] && [ ! -L "$entry" ]; then
      remove_empty_folders "$entry"
    fi
  done
  rmdir "$1" 2> /dev/null || true
}

for folder in /opt/PyMOL-Open-Source-*; do
  if [ -d "$folder" ]; then
    remove_empty_folders "$folder"
  fi
done
exit 0
