#!/bin/bash

# Validation script for pacman-sync-utility PKGBUILD
# This script performs basic validation checks on the PKGBUILD

set -e

echo "=== Pacman Sync Utility PKGBUILD Validation ==="
echo

# Check if we're in the right directory
if [ ! -f "PKGBUILD" ]; then
    echo "ERROR: PKGBUILD not found in current directory"
    exit 1
fi

echo "✓ PKGBUILD found"

# Check if required files exist
required_files=(
    "PKGBUILD"
    "pacman-sync-server.service"
    "pacman-sync-client.service"
    "pacman-sync-utility.desktop"
    "pacman-sync-utility.sysusers"
    "pacman-sync-utility.tmpfiles"
    "pacman-sync-utility.install"
    ".SRCINFO"
)

echo "Checking required files..."
for file in "${required_files[@]}"; do
    if [ -f "$file" ]; then
        echo "✓ $file"
    else
        echo "✗ $file (missing)"
        exit 1
    fi
done

echo

# Validate PKGBUILD syntax
echo "Validating PKGBUILD syntax..."
if bash -n PKGBUILD; then
    echo "✓ PKGBUILD syntax is valid"
else
    echo "✗ PKGBUILD syntax errors found"
    exit 1
fi

echo

# Check if namcap is available for additional validation
if command -v namcap >/dev/null 2>&1; then
    echo "Running namcap validation..."
    if namcap PKGBUILD; then
        echo "✓ namcap validation passed"
    else
        echo "⚠ namcap found issues (review above)"
    fi
else
    echo "⚠ namcap not available - install 'namcap' for additional validation"
fi

echo

# Validate .SRCINFO is up to date
echo "Checking .SRCINFO..."
if command -v makepkg >/dev/null 2>&1; then
    temp_srcinfo=$(mktemp)
    makepkg --printsrcinfo > "$temp_srcinfo"
    
    if diff -q .SRCINFO "$temp_srcinfo" >/dev/null; then
        echo "✓ .SRCINFO is up to date"
    else
        echo "✗ .SRCINFO is outdated"
        echo "Run: makepkg --printsrcinfo > .SRCINFO"
        rm "$temp_srcinfo"
        exit 1
    fi
    
    rm "$temp_srcinfo"
else
    echo "⚠ makepkg not available - cannot validate .SRCINFO"
fi

echo

# Check systemd service files
echo "Validating systemd service files..."

# Check server service
if systemd-analyze verify pacman-sync-server.service 2>/dev/null; then
    echo "✓ pacman-sync-server.service is valid"
else
    echo "⚠ pacman-sync-server.service may have issues"
fi

# Check client service
if systemd-analyze verify pacman-sync-client.service 2>/dev/null; then
    echo "✓ pacman-sync-client.service is valid"
else
    echo "⚠ pacman-sync-client.service may have issues"
fi

echo

# Validate desktop file
echo "Validating desktop file..."
if command -v desktop-file-validate >/dev/null 2>&1; then
    if desktop-file-validate pacman-sync-utility.desktop; then
        echo "✓ Desktop file is valid"
    else
        echo "✗ Desktop file validation failed"
        exit 1
    fi
else
    echo "⚠ desktop-file-validate not available"
fi

echo

# Check for common PKGBUILD issues
echo "Checking for common issues..."

# Check for proper split package structure
if grep -q "pkgname=(" PKGBUILD && grep -q "package_.*(" PKGBUILD; then
    echo "✓ Split package structure detected"
else
    echo "✗ Split package structure not found"
    exit 1
fi

# Check for proper dependency declarations
if grep -q "depends=(" PKGBUILD && grep -q "makedepends=(" PKGBUILD; then
    echo "✓ Dependencies declared"
else
    echo "✗ Missing dependency declarations"
    exit 1
fi

# Check for backup files declaration
if grep -q "backup=(" PKGBUILD; then
    echo "✓ Backup files declared"
else
    echo "⚠ No backup files declared"
fi

# Check for install script
if grep -q "install=" PKGBUILD; then
    echo "✓ Install script referenced"
else
    echo "⚠ No install script referenced"
fi

echo

echo "=== Validation Summary ==="
echo "✓ All critical validations passed"
echo "⚠ Review any warnings above"
echo
echo "To build the package:"
echo "  makepkg -s"
echo
echo "To install the built package:"
echo "  makepkg -si"
echo
echo "To test in a clean chroot:"
echo "  extra-x86_64-build"
echo