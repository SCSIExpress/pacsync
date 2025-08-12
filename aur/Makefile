# Makefile for pacman-sync-utility AUR package

PKGNAME = pacman-sync-utility
PKGVER = 1.0.0

.PHONY: all validate build install clean srcinfo help

# Default target
all: validate

# Validate PKGBUILD and related files
validate:
	@echo "Validating PKGBUILD..."
	@./validate-pkgbuild.sh

# Generate .SRCINFO from PKGBUILD
srcinfo:
	@echo "Generating .SRCINFO..."
	@makepkg --printsrcinfo > .SRCINFO
	@echo "✓ .SRCINFO updated"

# Build the package
build: validate
	@echo "Building package..."
	@makepkg -s

# Build and install the package
install: build
	@echo "Installing package..."
	@makepkg -si

# Clean build artifacts
clean:
	@echo "Cleaning build artifacts..."
	@rm -f *.pkg.tar.xz *.pkg.tar.zst
	@rm -rf pkg/ src/
	@echo "✓ Clean complete"

# Test build in clean chroot (requires devtools)
chroot-build:
	@echo "Building in clean chroot..."
	@extra-x86_64-build

# Check for updates to dependencies
check-deps:
	@echo "Checking dependency versions..."
	@pacman -Si python python-aiohttp python-fastapi python-pyqt6 | grep -E "^(Name|Version)"

# Lint PKGBUILD with namcap
lint:
	@echo "Linting PKGBUILD with namcap..."
	@namcap PKGBUILD || echo "namcap not available"

# Show package information
info:
	@echo "Package: $(PKGNAME)"
	@echo "Version: $(PKGVER)"
	@echo "Files:"
	@ls -la

# Prepare for AUR submission
prepare-aur: clean validate srcinfo
	@echo "Preparing for AUR submission..."
	@echo "✓ Package is ready for AUR submission"
	@echo ""
	@echo "Next steps:"
	@echo "1. Test build: make build"
	@echo "2. Test install: make install"
	@echo "3. Commit to AUR repository"

# Help target
help:
	@echo "Available targets:"
	@echo "  validate      - Validate PKGBUILD and related files"
	@echo "  srcinfo       - Generate .SRCINFO from PKGBUILD"
	@echo "  build         - Build the package"
	@echo "  install       - Build and install the package"
	@echo "  clean         - Clean build artifacts"
	@echo "  chroot-build  - Build in clean chroot (requires devtools)"
	@echo "  check-deps    - Check dependency versions"
	@echo "  lint          - Lint PKGBUILD with namcap"
	@echo "  info          - Show package information"
	@echo "  prepare-aur   - Prepare package for AUR submission"
	@echo "  help          - Show this help message"