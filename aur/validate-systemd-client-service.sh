#!/bin/bash
# Validation script for pacman-sync-client systemd user service

set -euo pipefail

SERVICE_FILE="pacman-sync-client.service"
TRAY_SERVICE_FILE="pacman-sync-client-tray.service"
TEMPLATE_SERVICE_FILE="pacman-sync-client@.service"

echo "Validating systemd client service files..."

# Check if service files exist
for service in "$SERVICE_FILE" "$TRAY_SERVICE_FILE" "$TEMPLATE_SERVICE_FILE"; do
    if [[ ! -f "$service" ]]; then
        echo "ERROR: Service file $service not found"
        exit 1
    fi
    echo "✓ Found $service"
done

# Validate service file syntax using systemd-analyze
if command -v systemd-analyze >/dev/null 2>&1; then
    echo "Validating service file syntax..."
    
    for service in "$SERVICE_FILE" "$TRAY_SERVICE_FILE" "$TEMPLATE_SERVICE_FILE"; do
        if systemd-analyze verify "$service" 2>/dev/null; then
            echo "✓ $service syntax is valid"
        else
            echo "⚠ $service syntax validation failed (may be due to missing dependencies)"
        fi
    done
else
    echo "⚠ systemd-analyze not available, skipping syntax validation"
fi

# Check required sections and keys
check_service_structure() {
    local service_file="$1"
    echo "Checking structure of $service_file..."
    
    # Check for required sections
    if ! grep -q "^\[Unit\]" "$service_file"; then
        echo "ERROR: Missing [Unit] section in $service_file"
        return 1
    fi
    
    if ! grep -q "^\[Service\]" "$service_file"; then
        echo "ERROR: Missing [Service] section in $service_file"
        return 1
    fi
    
    if ! grep -q "^\[Install\]" "$service_file"; then
        echo "ERROR: Missing [Install] section in $service_file"
        return 1
    fi
    
    # Check for required keys
    if ! grep -q "^Description=" "$service_file"; then
        echo "ERROR: Missing Description in $service_file"
        return 1
    fi
    
    if ! grep -q "^ExecStart=" "$service_file"; then
        echo "ERROR: Missing ExecStart in $service_file"
        return 1
    fi
    
    if ! grep -q "^WantedBy=" "$service_file"; then
        echo "ERROR: Missing WantedBy in $service_file"
        return 1
    fi
    
    echo "✓ $service_file structure is valid"
}

# Validate each service file structure
for service in "$SERVICE_FILE" "$TRAY_SERVICE_FILE" "$TEMPLATE_SERVICE_FILE"; do
    check_service_structure "$service"
done

# Check for graphical session dependencies
echo "Checking graphical session integration..."
if grep -q "graphical-session.target" "$SERVICE_FILE"; then
    echo "✓ Main service has graphical session dependencies"
else
    echo "ERROR: Main service missing graphical session dependencies"
    exit 1
fi

# Check for environment variables
echo "Checking environment variables..."
if grep -q "Environment=DISPLAY" "$SERVICE_FILE"; then
    echo "✓ Display environment variable configured"
else
    echo "ERROR: Missing DISPLAY environment variable"
    exit 1
fi

if grep -q "Environment=QT_QPA_PLATFORM" "$SERVICE_FILE"; then
    echo "✓ Qt platform environment variable configured"
else
    echo "ERROR: Missing Qt platform environment variable"
    exit 1
fi

# Check for restart policies
echo "Checking restart policies..."
if grep -q "Restart=always" "$SERVICE_FILE"; then
    echo "✓ Restart policy configured"
else
    echo "ERROR: Missing or incorrect restart policy"
    exit 1
fi

if grep -q "RestartSec=" "$SERVICE_FILE"; then
    echo "✓ Restart delay configured"
else
    echo "ERROR: Missing restart delay configuration"
    exit 1
fi

# Check for security settings
echo "Checking security settings..."
if grep -q "NoNewPrivileges=yes" "$SERVICE_FILE"; then
    echo "✓ NoNewPrivileges security setting enabled"
else
    echo "⚠ NoNewPrivileges security setting not found"
fi

if grep -q "PrivateTmp=yes" "$SERVICE_FILE"; then
    echo "✓ PrivateTmp security setting enabled"
else
    echo "⚠ PrivateTmp security setting not found"
fi

# Check for resource limits
echo "Checking resource limits..."
if grep -q "MemoryMax=" "$SERVICE_FILE"; then
    echo "✓ Memory limit configured"
else
    echo "⚠ Memory limit not configured"
fi

if grep -q "TasksMax=" "$SERVICE_FILE"; then
    echo "✓ Task limit configured"
else
    echo "⚠ Task limit not configured"
fi

echo "✅ All systemd client service validations completed successfully!"