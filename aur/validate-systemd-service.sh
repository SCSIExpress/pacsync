#!/bin/bash
# Validation script for systemd service files

set -e

echo "Validating systemd service files..."

# Basic syntax validation without requiring executables to exist
echo "Validating pacman-sync-server.service..."

# Check for required sections
echo "Checking required sections..."
if grep -q "^\[Unit\]" aur/pacman-sync-server.service && \
   grep -q "^\[Service\]" aur/pacman-sync-server.service && \
   grep -q "^\[Install\]" aur/pacman-sync-server.service; then
    echo "✓ All required sections present"
else
    echo "✗ Missing required sections"
    exit 1
fi

# Check for security settings
echo "Checking security hardening..."
security_settings=(
    "NoNewPrivileges=true"
    "PrivateTmp=true"
    "ProtectSystem=strict"
    "ProtectHome=true"
    "RestrictSUIDSGID=true"
    "PrivateDevices=true"
)

for setting in "${security_settings[@]}"; do
    if grep -q "$setting" aur/pacman-sync-server.service; then
        echo "✓ $setting found"
    else
        echo "✗ $setting missing"
        exit 1
    fi
done

echo "All validations passed!"