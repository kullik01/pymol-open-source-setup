#!/usr/bin/env bash

APP_NAME="Open-Source-PyMOL"
DMG_FILE_NAME="${APP_NAME}Installer.dmg"
VOLUME_NAME="${APP_NAME} Installer"
SOURCE_FOLDER_PATH="tmp/"
VOL_ICON_PATH="./alternative_design/icon.icns"

CREATE_DMG=./vendor/create-dmg/create-dmg

# Since create-dmg does not clobber, be sure to delete previous DMG
[[ -f "${DMG_FILE_NAME}" ]] && rm "${DMG_FILE_NAME}"

# Create the DMG
$CREATE_DMG \
  --volname "${VOLUME_NAME}" \
  --volicon "${VOL_ICON_PATH}" \
  --window-pos 200 120 \
  --window-size 800 400 \
  --icon-size 100 \
  --icon "${APP_NAME}.app" 200 190 \
  --hide-extension "${APP_NAME}.app" \
  --app-drop-link 600 185 \
  "${DMG_FILE_NAME}" \
  "${SOURCE_FOLDER_PATH}"
