#!/bin/zsh

INPUT_FILE="logo.png"
OUTPUT_DIR="./icon.iconset"

mkdir -p "$OUTPUT_DIR"

SIZES=(16 32 128 256 512)

for size in $SIZES; do
  sips -z $size $size "$INPUT_FILE" --out "$OUTPUT_DIR/icon_${size}x${size}.png"
  sips -z $((size * 2)) $((size * 2)) "$INPUT_FILE" --out "$OUTPUT_DIR/icon_${size}x${size}@2x.png"
done

iconutil -c icns icon.iconset
