#!/usr/bin/env python3
"""
Test script for Qt user interface windows.

This script demonstrates the Qt windows created for task 6.3:
- PackageDetailsWindow for detailed package information display
- SyncProgressDialog for sync operations with cancellation support
- ConfigurationWindow for endpoint settings and preferences
"""

import sys
import logging
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def test_package_details_window():
    """Test the PackageDetailsWindow."""
    from PyQt6.QtWidgets import QApplication
    from client.qt.windows import PackageDetailsWindow, PackageInfo
    
    app = QApplication(sys.argv)
    
    # Create sample package data
    sample_packages = [
        PackageInfo(
            name="python",
            version="3.11.6-1",
            repository="core",
            installed_size=52428800,  # 50MB
            description="Next generation of the python high-level scripting language",
            dependencies=["expat", "bzip2", "gdbm", "openssl", "libffi", "zlib"],
            conflicts=[],
            provides=["python3"],
            install_date="2024-01-15 10:30:00",
            build_date="2024-01-10 08:15:00",
            packager="Felix Yan <felixonmars@archlinux.org>",
            url="https://www.python.org/",
            licenses=["PSF"]
        ),
        PackageInfo(
            name="gcc",
            version="13.2.1-3",
            repository="core",
            installed_size=157286400,  # 150MB
            description="The GNU Compiler Collection - C and C++ frontends",
            dependencies=["gcc-libs", "binutils", "libmpc"],
            conflicts=["gcc-multilib"],
            provides=["gcc-multilib"],
            install_date="2024-01-12 14:20:00",
            build_date="2024-01-08 12:45:00",
            packager="Allan McRae <allan@archlinux.org>",
            url="https://gcc.gnu.org/",
            licenses=["GPL", "LGPL", "FDL", "custom"]
        ),
        PackageInfo(
            name="linux",
            version="6.6.8.arch1-1",
            repository="core",
            installed_size=134217728,  # 128MB
            description="The Linux kernel and modules",
            dependencies=["coreutils", "kmod", "initramfs"],
            conflicts=["linux-lts"],
            provides=["VIRTUALBOX-GUEST-MODULES", "WIREGUARD-MODULE"],
            install_date="2024-01-10 09:15:00",
            build_date="2024-01-08 06:30:00",
            packager="Jan Alexander Steffens <heftig@archlinux.org>",
            url="https://www.kernel.org/",
            licenses=["GPL2"]
        )
    ]
    
    # Create and show the window
    window = PackageDetailsWindow(sample_packages)
    window.show()
    
    logger.info("PackageDetailsWindow test started - close the window to continue")
    app.exec()

def test_sync_progress_dialog():
    """Test the SyncProgressDialog."""
    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtCore import QTimer
    from client.qt.windows import SyncProgressDialog, SyncOperation
    from datetime import datetime
    
    app = QApplication(sys.argv)
    
    # Create sample sync operation
    operation = SyncOperation(
        operation_id="sync_001",
        operation_type="sync",
        total_packages=100,
        processed_packages=0,
        current_package=None,
        status="pending",
        start_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )
    
    # Create and show the dialog
    dialog = SyncProgressDialog(operation)
    
    # Simulate progress updates
    def update_progress():
        if operation.processed_packages < operation.total_packages:
            operation.processed_packages += 1
            operation.current_package = f"package-{operation.processed_packages}"
            operation.status = "running"
            
            if operation.processed_packages == operation.total_packages:
                operation.status = "completed"
                operation.end_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                operation.current_package = None
            
            dialog.update_operation(operation)
    
    # Update progress every 100ms for demonstration
    timer = QTimer()
    timer.timeout.connect(update_progress)
    timer.start(100)
    
    logger.info("SyncProgressDialog test started - watch the progress or cancel to continue")
    dialog.exec()

def test_configuration_window():
    """Test the ConfigurationWindow."""
    from PyQt6.QtWidgets import QApplication
    from client.qt.windows import ConfigurationWindow
    
    app = QApplication(sys.argv)
    
    # Sample configuration
    current_config = {
        'server_url': 'http://localhost:8080',
        'api_key': 'test-api-key-12345',
        'timeout': 30,
        'retry_attempts': 3,
        'verify_ssl': True,
        'ssl_cert_path': '/path/to/cert.pem',
        'endpoint_name': 'test-desktop',
        'pool_id': 'test-pool',
        'update_interval': 300,
        'auto_register': True,
        'log_level': 'INFO',
        'log_file': '/var/log/pacman_sync.log',
        'auto_sync': False,
        'sync_on_startup': True,
        'confirm_operations': True,
        'exclude_packages': ['linux', 'linux-headers', 'grub'],
        'conflict_resolution': 'manual',
        'show_notifications': True,
        'minimize_to_tray': True,
        'start_minimized': False,
        'theme': 'System Default',
        'font_size': 12,
        'enable_waybar': True,
        'waybar_format': '{"text": "{status}", "class": "{class}"}'
    }
    
    def on_settings_changed(settings):
        logger.info("Settings changed:")
        for key, value in settings.items():
            logger.info(f"  {key}: {value}")
    
    # Create and show the window
    window = ConfigurationWindow(current_config)
    window.settings_changed.connect(on_settings_changed)
    
    logger.info("ConfigurationWindow test started - modify settings and apply/ok to continue")
    result = window.exec()
    
    if result == window.DialogCode.Accepted:
        logger.info("Configuration accepted")
        final_config = window.get_modified_config()
        logger.info(f"Final configuration: {final_config}")
    else:
        logger.info("Configuration cancelled")

def main():
    """Main test function."""
    if len(sys.argv) > 1:
        test_type = sys.argv[1].lower()
    else:
        print("Usage: python test_qt_windows.py [package|progress|config|all]")
        print("  package - Test PackageDetailsWindow")
        print("  progress - Test SyncProgressDialog")  
        print("  config - Test ConfigurationWindow")
        print("  all - Test all windows sequentially")
        return
    
    try:
        if test_type == "package":
            test_package_details_window()
        elif test_type == "progress":
            test_sync_progress_dialog()
        elif test_type == "config":
            test_configuration_window()
        elif test_type == "all":
            logger.info("Testing all Qt windows sequentially...")
            test_package_details_window()
            test_sync_progress_dialog()
            test_configuration_window()
            logger.info("All tests completed!")
        else:
            print(f"Unknown test type: {test_type}")
            return 1
            
    except ImportError as e:
        logger.error(f"Import error: {e}")
        print("Error: PyQt6 is required to run these tests.")
        print("Install with: pip install PyQt6")
        return 1
    except Exception as e:
        logger.error(f"Test error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())