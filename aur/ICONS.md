# Application Icons for AUR Package

This document describes the application icons implementation for the pacman-sync-utility AUR package.

## Overview

The AUR package includes a complete set of application icons that follow XDG standards and integrate properly with desktop environments. The icons are designed to represent the package synchronization functionality of the utility.

## Icon Assets

### Files Included
- **SVG Source**: `icons/pacman-sync-utility.svg` (scalable vector graphics)
- **PNG Icons**: Multiple sizes from 16x16 to 256x256 pixels
- **Generation Script**: `generate-icons.sh` for regenerating PNG files
- **Validation Script**: `validate-icons.sh` for verifying icon compliance

### Icon Sizes
The following PNG icon sizes are provided:
- 16x16 - Menu items, small lists
- 32x32 - Standard application icons
- 48x48 - Desktop shortcuts, medium icons
- 64x64 - Large desktop icons
- 128x128 - High-resolution displays
- 256x256 - Maximum resolution, scaling base

## PKGBUILD Integration

### Source Files
The icons are included in the PKGBUILD source array:
```bash
source=(...
        "icons/pacman-sync-utility.svg"
        "icons/16x16/pacman-sync-utility.png"
        "icons/32x32/pacman-sync-utility.png"
        "icons/48x48/pacman-sync-utility.png"
        "icons/64x64/pacman-sync-utility.png"
        "icons/128x128/pacman-sync-utility.png"
        "icons/256x256/pacman-sync-utility.png")
```

### Installation
Icons are installed to standard XDG locations:
```bash
# Install application icons
for size in 16 32 48 64 128 256; do
    install -Dm644 "$srcdir/icons/${size}x${size}/pacman-sync-utility.png" \
                   "$pkgdir/usr/share/icons/hicolor/${size}x${size}/apps/pacman-sync-utility.png"
done
install -Dm644 "$srcdir/icons/pacman-sync-utility.svg" \
               "$pkgdir/usr/share/icons/hicolor/scalable/apps/pacman-sync-utility.svg"
```

## Desktop Integration

### Desktop Entry
The desktop file references the icon by name:
```ini
[Desktop Entry]
Name=Pacman Sync Utility
Icon=pacman-sync-utility
...
```

### Icon Cache Updates
The package install script automatically updates the icon cache:
```bash
gtk-update-icon-cache -q -t -f /usr/share/icons/hicolor
```

## Design Specifications

### Visual Elements
- **Background**: Blue gradient representing Arch Linux ecosystem
- **Package Boxes**: Two boxes showing different systems/endpoints
- **Sync Arrows**: Bidirectional arrows indicating synchronization
- **Central Symbol**: Circular sync indicator with up/down arrows
- **Arch Accent**: Bottom element inspired by Arch Linux branding

### Color Scheme
- Primary Blue: #1793d1 (Arch Linux blue)
- Dark Blue: #0f5582 (gradient end)
- Green: #4caf50 (sync arrows, success state)
- White: #ffffff (highlights, text)
- Gray: #e0e0e0 (box gradients)

### Technical Specifications
- **Base Size**: 256x256 pixels (SVG viewBox)
- **Format**: SVG for source, PNG for raster versions
- **Transparency**: Full alpha channel support
- **Optimization**: Minimal file sizes while maintaining quality

## Theme Compatibility

The icons are designed to work with:
- **GNOME/GTK**: Full hicolor theme support
- **KDE/Qt**: Proper scaling and theme integration
- **System Tray**: Appropriate sizing for tray icons
- **High-DPI**: SVG scaling for retina displays
- **Dark Themes**: Sufficient contrast for dark backgrounds

## Maintenance

### Regenerating Icons
To regenerate PNG files from the SVG source:
```bash
cd aur
./generate-icons.sh
```

### Validation
To validate all icons meet requirements:
```bash
cd aur
./validate-icons.sh
```

### Requirements
Icon generation requires one of:
- **Inkscape** (preferred): `sudo pacman -S inkscape`
- **ImageMagick**: `sudo pacman -S imagemagick`

## Standards Compliance

### XDG Icon Theme Specification
- ✅ Follows hicolor theme structure
- ✅ Uses standard size directories
- ✅ Proper naming convention (application-name.extension)
- ✅ Includes scalable SVG version
- ✅ Supports transparency

### Arch Linux Packaging Guidelines
- ✅ Icons included in source array
- ✅ Proper installation paths
- ✅ Icon cache updates in install script
- ✅ No unnecessary dependencies for icon display
- ✅ Reasonable file sizes

### Desktop Entry Specification
- ✅ Icon referenced by name (not path)
- ✅ Fallback to generic icons if missing
- ✅ Proper categories and metadata

## Troubleshooting

### Icons Not Appearing
1. Verify icon cache was updated: `gtk-update-icon-cache -f /usr/share/icons/hicolor`
2. Check file permissions: Icons should be readable by all users
3. Restart desktop environment or logout/login
4. Verify files exist in `/usr/share/icons/hicolor/*/apps/`

### Wrong Icon Size
1. Check if high-DPI scaling is affecting display
2. Verify correct size PNG files are installed
3. Clear icon cache and regenerate: `rm -rf ~/.cache/icon-theme.cache`

### Theme Integration Issues
1. Ensure hicolor theme is available
2. Check desktop environment icon theme settings
3. Verify SVG support in desktop environment
4. Test with different icon themes