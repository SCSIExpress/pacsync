# Pacman Sync Utility Icons

This directory contains the application icons for the pacman-sync-utility AUR package.

## Icon Files

### SVG Source
- `pacman-sync-utility.svg` - Scalable vector graphics source file (256x256 base size)

### PNG Icons
The following PNG icons are generated from the SVG source:
- `16x16/pacman-sync-utility.png` - Small icon for menus and lists
- `32x32/pacman-sync-utility.png` - Standard small icon
- `48x48/pacman-sync-utility.png` - Medium icon for desktop
- `64x64/pacman-sync-utility.png` - Large icon for desktop
- `128x128/pacman-sync-utility.png` - High-resolution icon
- `256x256/pacman-sync-utility.png` - Maximum resolution icon

## Icon Design

The icon represents the core functionality of the pacman-sync-utility:
- **Blue gradient background**: Represents the Arch Linux ecosystem
- **Package boxes**: Two boxes representing different systems/endpoints
- **Sync arrows**: Bidirectional arrows showing synchronization
- **Central sync symbol**: Circular icon with up/down arrows for sync status
- **Arch accent**: Bottom accent inspired by Arch Linux branding

## Installation Paths

When installed via the AUR package, icons are placed according to XDG standards:

```
/usr/share/icons/hicolor/
├── scalable/apps/pacman-sync-utility.svg
├── 16x16/apps/pacman-sync-utility.png
├── 32x32/apps/pacman-sync-utility.png
├── 48x48/apps/pacman-sync-utility.png
├── 64x64/apps/pacman-sync-utility.png
├── 128x128/apps/pacman-sync-utility.png
└── 256x256/apps/pacman-sync-utility.png
```

## Regenerating Icons

To regenerate the PNG icons from the SVG source, run:

```bash
./generate-icons.sh
```

This script requires either Inkscape or ImageMagick to be installed:
- **Inkscape** (preferred): `sudo pacman -S inkscape`
- **ImageMagick**: `sudo pacman -S imagemagick`

## Theme Integration

The icons follow the hicolor icon theme specification and will integrate properly with:
- GNOME/GTK applications
- KDE/Qt applications  
- System tray implementations
- Application launchers
- File managers

The SVG version ensures proper scaling for high-DPI displays and theme customization.

## Icon Cache Updates

The AUR package automatically updates the icon cache during installation and removal using:
```bash
gtk-update-icon-cache -q -t -f /usr/share/icons/hicolor
```

This ensures icons appear immediately after installation without requiring a logout/login cycle.