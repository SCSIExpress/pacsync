#!/bin/bash

# Validate application icons for pacman-sync-utility AUR package
# This script verifies that all required icons exist and meet specifications

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ICONS_DIR="$SCRIPT_DIR/icons"

# Required icon sizes
REQUIRED_SIZES=(16 32 48 64 128 256)
SVG_FILE="$ICONS_DIR/pacman-sync-utility.svg"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "Validating pacman-sync-utility icons..."
echo "========================================"

# Check if icons directory exists
if [ ! -d "$ICONS_DIR" ]; then
    echo -e "${RED}ERROR: Icons directory not found at $ICONS_DIR${NC}"
    exit 1
fi

# Validate SVG file
echo -n "Checking SVG source file... "
if [ -f "$SVG_FILE" ]; then
    # Check if it's a valid SVG
    if file "$SVG_FILE" | grep -q "SVG"; then
        echo -e "${GREEN}OK${NC}"
    else
        echo -e "${RED}INVALID (not a valid SVG file)${NC}"
        exit 1
    fi
else
    echo -e "${RED}MISSING${NC}"
    exit 1
fi

# Validate PNG files
echo "Checking PNG icon files:"
all_valid=true

for size in "${REQUIRED_SIZES[@]}"; do
    png_file="$ICONS_DIR/${size}x${size}/pacman-sync-utility.png"
    echo -n "  ${size}x${size}: "
    
    if [ -f "$png_file" ]; then
        # Check if it's a valid PNG
        if file "$png_file" | grep -q "PNG"; then
            # Check dimensions using identify (ImageMagick)
            if command -v identify >/dev/null 2>&1; then
                dimensions=$(identify -format "%wx%h" "$png_file" 2>/dev/null || echo "unknown")
                expected="${size}x${size}"
                if [ "$dimensions" = "$expected" ]; then
                    echo -e "${GREEN}OK ($dimensions)${NC}"
                else
                    echo -e "${YELLOW}WARNING (dimensions: $dimensions, expected: $expected)${NC}"
                fi
            else
                echo -e "${GREEN}OK (file exists)${NC}"
            fi
        else
            echo -e "${RED}INVALID (not a valid PNG file)${NC}"
            all_valid=false
        fi
    else
        echo -e "${RED}MISSING${NC}"
        all_valid=false
    fi
done

# Check XDG compliance
echo ""
echo "XDG Standards Compliance:"
echo "========================"

# Check naming convention
echo -n "Icon naming convention: "
if [[ "$SVG_FILE" =~ pacman-sync-utility\.svg$ ]]; then
    echo -e "${GREEN}OK (follows application-name.extension format)${NC}"
else
    echo -e "${RED}INVALID (should be pacman-sync-utility.svg)${NC}"
    all_valid=false
fi

# Check directory structure
echo -n "Directory structure: "
structure_valid=true
for size in "${REQUIRED_SIZES[@]}"; do
    if [ ! -d "$ICONS_DIR/${size}x${size}" ]; then
        structure_valid=false
        break
    fi
done

if $structure_valid; then
    echo -e "${GREEN}OK (follows hicolor theme structure)${NC}"
else
    echo -e "${RED}INVALID (missing size directories)${NC}"
    all_valid=false
fi

# Check file sizes (reasonable limits)
echo "File size validation:"
for size in "${REQUIRED_SIZES[@]}"; do
    png_file="$ICONS_DIR/${size}x${size}/pacman-sync-utility.png"
    if [ -f "$png_file" ]; then
        file_size=$(stat -f%z "$png_file" 2>/dev/null || stat -c%s "$png_file" 2>/dev/null || echo "0")
        # Reasonable size limits (in bytes)
        case $size in
            16|32) max_size=5120 ;;    # 5KB for small icons
            48|64) max_size=10240 ;;   # 10KB for medium icons
            128) max_size=20480 ;;     # 20KB for large icons
            256) max_size=40960 ;;     # 40KB for extra large icons
        esac
        
        echo -n "  ${size}x${size} size: "
        if [ "$file_size" -le "$max_size" ]; then
            echo -e "${GREEN}OK (${file_size} bytes)${NC}"
        else
            echo -e "${YELLOW}WARNING (${file_size} bytes, consider optimizing)${NC}"
        fi
    fi
done

# Check SVG file size
if [ -f "$SVG_FILE" ]; then
    svg_size=$(stat -f%z "$SVG_FILE" 2>/dev/null || stat -c%s "$SVG_FILE" 2>/dev/null || echo "0")
    echo -n "SVG size: "
    if [ "$svg_size" -le 51200 ]; then  # 50KB limit for SVG
        echo -e "${GREEN}OK (${svg_size} bytes)${NC}"
    else
        echo -e "${YELLOW}WARNING (${svg_size} bytes, consider optimizing)${NC}"
    fi
fi

echo ""
echo "Installation Path Validation:"
echo "============================"

# Show expected installation paths
echo "Icons will be installed to:"
echo "  /usr/share/icons/hicolor/scalable/apps/pacman-sync-utility.svg"
for size in "${REQUIRED_SIZES[@]}"; do
    echo "  /usr/share/icons/hicolor/${size}x${size}/apps/pacman-sync-utility.png"
done

echo ""
if $all_valid; then
    echo -e "${GREEN}✓ All icon validations passed!${NC}"
    echo ""
    echo "Icons are ready for AUR package inclusion."
    echo "Run './generate-icons.sh' to regenerate PNG files if needed."
    exit 0
else
    echo -e "${RED}✗ Some validations failed!${NC}"
    echo ""
    echo "Please fix the issues above before including icons in the AUR package."
    exit 1
fi