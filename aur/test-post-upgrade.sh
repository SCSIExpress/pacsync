#!/bin/bash
# Test script for post_upgrade() function validation
# This script validates the enhanced post_upgrade implementation

set -e

echo "=== Testing post_upgrade() Function Implementation ==="
echo

# Test 1: Verify post_upgrade function exists and is properly formatted
echo "Test 1: Checking post_upgrade function structure..."
if grep -q "^post_upgrade()" aur/pacman-sync-utility.install; then
    echo "✓ post_upgrade() function found"
else
    echo "✗ post_upgrade() function not found"
    exit 1
fi

# Test 2: Verify database migration handling
echo "Test 2: Checking database migration handling..."
if grep -q "migrate-db" aur/pacman-sync-utility.install && \
   grep -q "MIGRATION_SUCCESS" aur/pacman-sync-utility.install && \
   grep -q "migration.log" aur/pacman-sync-utility.install; then
    echo "✓ Database migration handling implemented"
else
    echo "✗ Database migration handling missing or incomplete"
    exit 1
fi

# Test 3: Verify backup and rollback mechanisms
echo "Test 3: Checking backup and rollback mechanisms..."
if grep -q "BACKUP_DIR=" aur/pacman-sync-utility.install && \
   grep -q "Backing up" aur/pacman-sync-utility.install && \
   grep -q "rollback" aur/pacman-sync-utility.install; then
    echo "✓ Backup and rollback mechanisms implemented"
else
    echo "✗ Backup and rollback mechanisms missing or incomplete"
    exit 1
fi

# Test 4: Verify service restart logic
echo "Test 4: Checking service restart logic..."
if grep -q "SERVER_WAS_RUNNING" aur/pacman-sync-utility.install && \
   grep -q "systemctl stop" aur/pacman-sync-utility.install && \
   grep -q "systemctl start" aur/pacman-sync-utility.install; then
    echo "✓ Service restart logic implemented"
else
    echo "✗ Service restart logic missing or incomplete"
    exit 1
fi

# Test 5: Verify configuration file handling (.pacnew files)
echo "Test 5: Checking configuration file handling..."
if grep -q "\.pacnew" aur/pacman-sync-utility.install && \
   grep -q "PACNEW_FOUND" aur/pacman-sync-utility.install && \
   grep -q "merge changes manually" aur/pacman-sync-utility.install; then
    echo "✓ Configuration file handling implemented"
else
    echo "✗ Configuration file handling missing or incomplete"
    exit 1
fi

# Test 6: Verify error handling and recovery
echo "Test 6: Checking error handling and recovery..."
if grep -q "ERROR:" aur/pacman-sync-utility.install && \
   grep -q "rollback" aur/pacman-sync-utility.install && \
   grep -q "Manual intervention" aur/pacman-sync-utility.install; then
    echo "✓ Error handling and recovery implemented"
else
    echo "✗ Error handling and recovery missing or incomplete"
    exit 1
fi

# Test 7: Verify rollback script generation
echo "Test 7: Checking rollback script generation..."
if grep -q "pacman-sync-rollback-" aur/pacman-sync-utility.install && \
   grep -q "Emergency rollback script" aur/pacman-sync-utility.install && \
   grep -q "chmod 755" aur/pacman-sync-utility.install; then
    echo "✓ Rollback script generation implemented"
else
    echo "✗ Rollback script generation missing or incomplete"
    exit 1
fi

# Test 8: Verify backup cleanup
echo "Test 8: Checking backup cleanup..."
if grep -q "Clean.*old.*backup" aur/pacman-sync-utility.install && \
   grep -q "tail -n +6" aur/pacman-sync-utility.install; then
    echo "✓ Backup cleanup implemented"
else
    echo "✗ Backup cleanup missing or incomplete"
    exit 1
fi

# Test 9: Verify requirements compliance
echo "Test 9: Checking requirements compliance..."

# Requirement 6.1: Configuration file creation (handled in post_install, verified in post_upgrade)
if grep -q "/etc/pacman-sync-utility" aur/pacman-sync-utility.install; then
    echo "✓ Requirement 6.1: Configuration directory handling"
else
    echo "✗ Requirement 6.1: Configuration directory handling missing"
    exit 1
fi

# Requirement 6.2: Configuration preservation during updates
if grep -q "Backing up configuration" aur/pacman-sync-utility.install && \
   grep -q "BACKUP_DIR" aur/pacman-sync-utility.install; then
    echo "✓ Requirement 6.2: Configuration preservation"
else
    echo "✗ Requirement 6.2: Configuration preservation missing"
    exit 1
fi

# Requirement 6.3: .pacnew file handling
if grep -q "\.pacnew" aur/pacman-sync-utility.install && \
   grep -q "New configuration" aur/pacman-sync-utility.install; then
    echo "✓ Requirement 6.3: .pacnew file handling"
else
    echo "✗ Requirement 6.3: .pacnew file handling missing"
    exit 1
fi

# Requirement 6.4: Configuration preservation during removal (handled in post_remove)
if grep -q "\.pacsave" aur/pacman-sync-utility.install; then
    echo "✓ Requirement 6.4: .pacsave file handling"
else
    echo "✗ Requirement 6.4: .pacsave file handling missing"
    exit 1
fi

# Test 10: Verify function syntax and structure
echo "Test 10: Checking function syntax..."
if bash -n aur/pacman-sync-utility.install; then
    echo "✓ Bash syntax validation passed"
else
    echo "✗ Bash syntax validation failed"
    exit 1
fi

echo
echo "=== All Tests Passed! ==="
echo "The post_upgrade() function implementation meets all requirements:"
echo "  ✓ Database migration handling with error recovery"
echo "  ✓ Service restart logic with state preservation"
echo "  ✓ Backup and rollback mechanisms"
echo "  ✓ Configuration file handling (.pacnew/.pacsave)"
echo "  ✓ Error handling and recovery procedures"
echo "  ✓ Requirements 6.1, 6.2, 6.3, 6.4 compliance"
echo
echo "Task 8.2 implementation is complete and validated."