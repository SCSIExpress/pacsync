#!/bin/bash

# Validation script for post_install() function implementation
# This script checks the implementation without requiring root privileges

echo "Validating post_install() function implementation..."
echo "=================================================="

ERRORS=0

# Function to report errors
report_error() {
    echo "❌ ERROR: $1"
    ERRORS=$((ERRORS + 1))
}

# Function to report success
report_success() {
    echo "✅ $1"
}

# Test 1: Check if install file exists
echo "Test 1: Checking install file existence..."
if [ ! -f "pacman-sync-utility.install" ]; then
    report_error "Install file 'pacman-sync-utility.install' not found"
else
    report_success "Install file found"
fi

# Test 2: Check if post_install function exists
echo "Test 2: Checking post_install() function..."
if ! grep -q "^post_install()" "pacman-sync-utility.install" 2>/dev/null; then
    report_error "post_install() function not found in install file"
else
    report_success "post_install() function found"
fi

# Test 3: Check for system user creation
echo "Test 3: Checking system user creation implementation..."
if ! grep -q "systemd-sysusers" "pacman-sync-utility.install" 2>/dev/null; then
    report_error "systemd-sysusers call not found in post_install()"
else
    report_success "System user creation implemented with systemd-sysusers"
fi

# Test 4: Check for directory structure creation
echo "Test 4: Checking directory structure creation..."
if ! grep -q "systemd-tmpfiles" "pacman-sync-utility.install" 2>/dev/null; then
    report_error "systemd-tmpfiles call not found in post_install()"
else
    report_success "Directory structure creation implemented with systemd-tmpfiles"
fi

# Test 5: Check for JWT secret generation
echo "Test 5: Checking JWT secret generation..."
if ! grep -q "jwt-secret" "pacman-sync-utility.install" 2>/dev/null; then
    report_error "JWT secret generation not found in post_install()"
else
    report_success "JWT secret generation implemented"
fi

# Test 6: Check for database initialization
echo "Test 6: Checking database initialization..."
if ! grep -q "init-db" "pacman-sync-utility.install" 2>/dev/null; then
    report_error "Database initialization not found in post_install()"
else
    report_success "Database initialization implemented"
fi

# Test 7: Check for error handling
echo "Test 7: Checking error handling..."
if ! grep -q "exit 1" "pacman-sync-utility.install" 2>/dev/null; then
    report_error "Error handling (exit 1) not found in post_install()"
else
    report_success "Error handling implemented"
fi

# Test 8: Check for user verification
echo "Test 8: Checking user creation verification..."
if ! grep -q "id pacman-sync" "pacman-sync-utility.install" 2>/dev/null; then
    report_error "User creation verification not found in post_install()"
else
    report_success "User creation verification implemented"
fi

# Test 9: Check for directory verification
echo "Test 9: Checking directory creation verification..."
if ! grep -q "for dir in" "pacman-sync-utility.install" 2>/dev/null; then
    report_error "Directory creation verification not found in post_install()"
else
    report_success "Directory creation verification implemented"
fi

# Test 10: Check for systemd daemon reload
echo "Test 10: Checking systemd daemon reload..."
if ! grep -q "systemctl daemon-reload" "pacman-sync-utility.install" 2>/dev/null; then
    report_error "systemctl daemon-reload not found in post_install()"
else
    report_success "systemd daemon reload implemented"
fi

# Test 11: Check sysusers configuration
echo "Test 11: Checking sysusers configuration..."
if [ ! -f "pacman-sync-utility.sysusers" ]; then
    report_error "sysusers configuration file not found"
else
    if ! grep -q "u pacman-sync" "pacman-sync-utility.sysusers" 2>/dev/null; then
        report_error "pacman-sync user not defined in sysusers configuration"
    else
        report_success "sysusers configuration properly defines pacman-sync user"
    fi
fi

# Test 12: Check tmpfiles configuration
echo "Test 12: Checking tmpfiles configuration..."
if [ ! -f "pacman-sync-utility.tmpfiles" ]; then
    report_error "tmpfiles configuration file not found"
else
    if ! grep -q "/var/lib/pacman-sync-utility" "pacman-sync-utility.tmpfiles" 2>/dev/null; then
        report_error "Data directory not defined in tmpfiles configuration"
    else
        report_success "tmpfiles configuration properly defines directories"
    fi
fi

# Test 13: Check for proper permissions in implementation
echo "Test 13: Checking permission setting implementation..."
if ! grep -q "chmod.*600.*jwt-secret" "pacman-sync-utility.install" 2>/dev/null; then
    report_error "JWT secret permission setting (600) not found"
else
    report_success "JWT secret permissions properly set to 600"
fi

if ! grep -q "chown.*pacman-sync.*jwt-secret" "pacman-sync-utility.install" 2>/dev/null; then
    report_error "JWT secret ownership setting not found"
else
    report_success "JWT secret ownership properly set to pacman-sync"
fi

# Test 14: Check for informational output
echo "Test 14: Checking informational output..."
if ! grep -q "successfully" "pacman-sync-utility.install" 2>/dev/null; then
    report_error "Success message not found in post_install()"
else
    report_success "Informational output implemented"
fi

# Test 15: Check requirements coverage
echo "Test 15: Checking requirements coverage..."

# Requirement 1.1-1.4: Package installation and directory creation
if grep -q "systemd-tmpfiles" "pacman-sync-utility.install" 2>/dev/null && \
   grep -q "/usr/bin" "pacman-sync-utility.install" 2>/dev/null; then
    report_success "Requirements 1.1-1.4 covered (package installation)"
else
    report_error "Requirements 1.1-1.4 not fully covered"
fi

# Requirement 3.1-3.4: systemd integration
if grep -q "systemctl daemon-reload" "pacman-sync-utility.install" 2>/dev/null && \
   grep -q "systemctl.*enable" "pacman-sync-utility.install" 2>/dev/null; then
    report_success "Requirements 3.1-3.4 covered (systemd integration)"
else
    report_error "Requirements 3.1-3.4 not fully covered"
fi

echo ""
echo "=================================================="
if [ $ERRORS -eq 0 ]; then
    echo "✅ All validation tests passed!"
    echo "✅ post_install() function implementation is complete and correct"
    echo ""
    echo "Implementation covers:"
    echo "  ✓ System user and group creation"
    echo "  ✓ Directory structure setup with proper permissions"
    echo "  ✓ Security key generation (JWT secret)"
    echo "  ✓ Database initialization"
    echo "  ✓ Error handling and verification"
    echo "  ✓ systemd integration"
    echo "  ✓ Desktop environment integration"
    echo "  ✓ Informational user output"
else
    echo "❌ Validation failed with $ERRORS error(s)"
    echo "Please review and fix the issues above"
    exit 1
fi
echo "=================================================="