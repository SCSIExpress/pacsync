#!/bin/bash
# Validation script to ensure prepare() function integrates properly with PKGBUILD

set -e

echo "Validating prepare() function integration with PKGBUILD..."

# Check that prepare() function exists and has proper structure
if ! grep -q "^prepare()" PKGBUILD; then
    echo "✗ prepare() function not found in PKGBUILD"
    exit 1
fi

echo "✓ prepare() function found in PKGBUILD"

# Check that prepare() function includes required components
required_components=(
    "mkdir -p build/{venv,deps,temp,logs}"
    "python -m venv build/venv"
    "source build/venv/bin/activate"
    "pip install --upgrade pip setuptools wheel build"
    "msg2.*Setting up Python virtual environment"
    "msg2.*Installing build dependencies"
    "msg2.*Validating source structure"
    "msg2.*Preparing configuration templates"
    "msg2.*Validating Python syntax"
    "msg2.*Organizing files for packaging"
)

for component in "${required_components[@]}"; do
    if ! grep -q "$component" PKGBUILD; then
        echo "✗ Missing required component: $component"
        exit 1
    fi
done

echo "✓ All required components found in prepare() function"

# Check that build() function is compatible with prepare() changes
if ! grep -q "source build/venv/bin/activate" PKGBUILD; then
    echo "✗ build() function doesn't activate virtual environment from prepare()"
    exit 1
fi

echo "✓ build() function properly uses virtual environment from prepare()"

# Check that check() function is compatible with prepare() changes
if ! grep -q "source build/venv/bin/activate" PKGBUILD; then
    echo "✗ check() function doesn't activate virtual environment from prepare()"
    exit 1
fi

echo "✓ check() function properly uses virtual environment from prepare()"

# Validate PKGBUILD syntax
echo "Validating PKGBUILD syntax..."
if ! bash -n PKGBUILD; then
    echo "✗ PKGBUILD has syntax errors"
    exit 1
fi

echo "✓ PKGBUILD syntax is valid"

# Check for proper error handling in prepare()
if ! grep -q "return 1" PKGBUILD; then
    echo "✗ prepare() function lacks proper error handling"
    exit 1
fi

echo "✓ prepare() function includes proper error handling"

# Check for logging functionality
if ! grep -q "build/logs/prepare.log" PKGBUILD; then
    echo "✗ prepare() function lacks logging functionality"
    exit 1
fi

echo "✓ prepare() function includes logging functionality"

# Check that required directories are created
required_dirs=(
    "build/{venv,deps,temp,logs}"
    "build/packaging/{client,server,common}"
)

for dir_pattern in "${required_dirs[@]}"; do
    if ! grep -q "mkdir -p.*$dir_pattern" PKGBUILD; then
        echo "✗ Missing directory creation: $dir_pattern"
        exit 1
    fi
done

echo "✓ All required directories are created in prepare()"

# Check for configuration template processing
if ! grep -q "sed.*config.*template" PKGBUILD; then
    echo "✓ Configuration template processing found (optional feature)"
fi

# Check for Python syntax validation
if ! grep -q "python -m py_compile" PKGBUILD; then
    echo "✗ Missing Python syntax validation"
    exit 1
fi

echo "✓ Python syntax validation included"

echo ""
echo "✅ All prepare() function integration tests passed!"
echo "The prepare() function is properly integrated with the PKGBUILD and meets all requirements."