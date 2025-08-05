#!/usr/bin/env python3
"""
Demo script for Qt user interface windows.
Shows each window implemented for task 6.3.
"""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def demo_package_details():
    """Demo the PackageDetailsWindow."""
    from PyQt6.QtWidgets import QApplication
    from client.qt.windows import PackageDetailsWindow, PackageInfo
    
    app = QApplication(sys.argv)
    
    # Sample packages
    packages = [
        PackageInfo(
            name="python",
            version="3.11.6-1",
            repository="core",
            installed_size=52428800,
            description="Python programming language",
            dependencies=["expat", "bzip2", "gdbm", "openssl"],
            conflicts=[],
            provides=["python3"],
            install_date="2024-01-15 10:30:00",
            licenses=["PSF"]
        ),
        PackageInfo(
            name="gcc",
            version="13.2.1-3", 
            repository="core",
            installed_size=157286400,
            description="GNU Compiler Collection",
            dependencies=["gcc-libs", "binutils", "libmpc"],
            conflicts=["gcc-multilib"],
            provides=["gcc-multilib"],
            licenses=["GPL", "LGPL"]
        )
    ]
    
    window = PackageDetailsWindow(packages)
    window.show()
    
    print("📦 PackageDetailsWindow demo - Navigate between packages")
    app.exec()

if __name__ == "__main__":
    demo_package_details()