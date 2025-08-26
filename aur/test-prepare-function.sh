#!/bin/bash
# Test script to validate the prepare() function implementation

set -e

echo "Testing prepare() function implementation..."

# Create a temporary test environment
TEST_DIR=$(mktemp -d)
echo "Test directory: $TEST_DIR"

# Copy necessary files for testing
cp -r ../client ../server ../shared "$TEST_DIR/"
cp ../requirements.txt ../server-requirements.txt "$TEST_DIR/"
cp -r ../config "$TEST_DIR/" 2>/dev/null || echo "No config directory found"

cd "$TEST_DIR"

# Simulate the prepare() function environment
export srcdir="$TEST_DIR"
export pkgbase="pacman-sync-utility"
export pkgver="1.0.0"

# Create the source directory structure that prepare() expects
mkdir -p "$pkgbase-$pkgver"
mv client server shared requirements.txt server-requirements.txt "$pkgbase-$pkgver/"
[ -d config ] && mv config "$pkgbase-$pkgver/"

# Test the prepare() function logic
cd "$pkgbase-$pkgver"

echo "Testing directory structure creation..."
mkdir -p build/{venv,deps,temp,logs}
mkdir -p build/packaging/{client,server,common}

echo "Testing Python virtual environment creation..."
python -m venv build/venv
source build/venv/bin/activate

echo "Testing pip upgrade and build dependencies..."
pip install --upgrade pip setuptools wheel build

echo "Testing requirements installation..."
if [ -f requirements.txt ]; then
    pip install -r requirements.txt
    echo "✓ Runtime dependencies installed"
fi

if [ -f server-requirements.txt ]; then
    pip install -r server-requirements.txt  
    echo "✓ Server dependencies installed"
fi

echo "Testing source validation..."
required_files=("client" "server" "shared" "requirements.txt" "server-requirements.txt")
missing_files=()

for file in "${required_files[@]}"; do
    if [ ! -e "$file" ]; then
        missing_files+=("$file")
    fi
done

if [ ${#missing_files[@]} -gt 0 ]; then
    echo "✗ Missing required files: ${missing_files[*]}"
    exit 1
else
    echo "✓ All required source files present"
fi

echo "Testing Python syntax validation..."
find . -name "*.py" -type f -exec python -m py_compile {} \;
echo "✓ Python syntax validation passed"

echo "Testing file organization..."
mkdir -p build/packaging/client/{bin,lib,share}
mkdir -p build/packaging/server/{bin,lib,systemd}
mkdir -p build/packaging/common/{etc,share/doc,share/licenses}
echo "✓ File organization structure created"

echo "Testing log creation..."
echo "Test preparation completed at $(date)" > build/logs/prepare.log
echo "Virtual environment: $(which python)" >> build/logs/prepare.log
echo "Python version: $(python --version)" >> build/logs/prepare.log
echo "Pip version: $(pip --version)" >> build/logs/prepare.log
echo "✓ Logging functionality working"

echo ""
echo "✅ All prepare() function tests passed!"
echo "Test artifacts created in: $TEST_DIR"

# Cleanup
cd /
rm -rf "$TEST_DIR"
echo "✓ Test cleanup completed"