#!/bin/bash

# Generate application icons from SVG source
# This script creates PNG icons in multiple sizes for the pacman-sync-utility

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ICONS_DIR="$SCRIPT_DIR/icons"
SVG_SOURCE="$ICONS_DIR/pacman-sync-utility.svg"

# Check if SVG source exists
if [ ! -f "$SVG_SOURCE" ]; then
    echo "Error: SVG source file not found at $SVG_SOURCE"
    exit 1
fi

# Check if inkscape or imagemagick is available
if command -v inkscape >/dev/null 2>&1; then
    CONVERTER="inkscape"
    echo "Using Inkscape for icon generation"
elif command -v convert >/dev/null 2>&1; then
    CONVERTER="imagemagick"
    echo "Using ImageMagick for icon generation"
else
    echo "Error: Neither Inkscape nor ImageMagick found. Please install one of them."
    echo "  Arch Linux: sudo pacman -S inkscape"
    echo "  or: sudo pacman -S imagemagick"
    exit 1
fi

# Icon sizes to generate
SIZES=(16 32 48 64 128 256)

echo "Generating PNG icons from $SVG_SOURCE"

# Create output directories if they don't exist
for size in "${SIZES[@]}"; do
    mkdir -p "$ICONS_DIR/${size}x${size}"
done

# Generate PNG icons
for size in "${SIZES[@]}"; do
    output_file="$ICONS_DIR/${size}x${size}/pacman-sync-utility.png"
    
    if [ "$CONVERTER" = "inkscape" ]; then
        inkscape --export-type=png \
                 --export-width="$size" \
                 --export-height="$size" \
                 --export-filename="$output_file" \
                 "$SVG_SOURCE" >/dev/null 2>&1
    else
        magick "$SVG_SOURCE" \
               -resize "${size}x${size}" \
               -background transparent \
               "$output_file"
    fi
    
    if [ -f "$output_file" ]; then
        echo "Generated: ${size}x${size}/pacman-sync-utility.png"
    else
        echo "Error: Failed to generate ${size}x${size}/pacman-sync-utility.png"
        exit 1
    fi
done

echo "Icon generation completed successfully!"
echo ""
echo "Generated files:"
echo "  SVG: icons/pacman-sync-utility.svg"
for size in "${SIZES[@]}"; do
    echo "  PNG: icons/${size}x${size}/pacman-sync-utility.png"
done
echo ""
echo "These icons follow XDG standards and can be installed to:"
echo "  /usr/share/icons/hicolor/scalable/apps/pacman-sync-utility.svg"
for size in "${SIZES[@]}"; do
    echo "  /usr/share/icons/hicolor/${size}x${size}/apps/pacman-sync-utility.png"
done