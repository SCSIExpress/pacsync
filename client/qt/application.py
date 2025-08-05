"""
Qt Application Framework for Pacman Sync Utility Client.

This module provides the main Qt application class with system tray integration,
supporting AppIndicator and KStatusNotifierItem protocols for cross-desktop compatibility.
"""

import sys
import logging
from enum import Enum
from typing import Optional, Callable
from PyQt6.QtWidgets import (
    QApplication, QSystemTrayIcon, QMenu, QMessageBox, 
    QWidget, QVBoxLayout, QLabel, QPushButton
)
from PyQt6.QtCore import QTimer, pyqtSignal, QObject, QThread
from PyQt6.QtGui import QIcon, QPixmap, QAction, QColor

logger = logging.getLogger(__name__)


class SyncStatus(Enum):
    """Enumeration of possible sync states."""
    IN_SYNC = "in_sync"
    AHEAD = "ahead"
    BEHIND = "behind"
    OFFLINE = "offline"
    SYNCING = "syncing"
    ERROR = "error"


class SyncStatusIndicator(QObject):
    """
    System tray icon manager with dynamic status indication.
    
    Provides cross-desktop system tray integration using QSystemTrayIcon
    with fallback support for AppIndicator and KStatusNotifierItem protocols.
    """
    
    # Signals for status changes
    status_changed = pyqtSignal(SyncStatus)
    sync_requested = pyqtSignal()
    set_latest_requested = pyqtSignal()
    revert_requested = pyqtSignal()
    show_details_requested = pyqtSignal()
    config_requested = pyqtSignal()
    quit_requested = pyqtSignal()
    
    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._current_status = SyncStatus.OFFLINE
        self._tray_icon: Optional[QSystemTrayIcon] = None
        self._context_menu: Optional[QMenu] = None
        self._status_action: Optional[QAction] = None
        
        # Status display strings
        self._status_texts = {
            SyncStatus.IN_SYNC: "In Sync",
            SyncStatus.AHEAD: "Ahead of Pool",
            SyncStatus.BEHIND: "Behind Pool", 
            SyncStatus.OFFLINE: "Offline",
            SyncStatus.SYNCING: "Syncing...",
            SyncStatus.ERROR: "Error"
        }
        
        # Status tooltips
        self._status_tooltips = {
            SyncStatus.IN_SYNC: "All packages are synchronized with the pool",
            SyncStatus.AHEAD: "This endpoint has newer packages than the pool",
            SyncStatus.BEHIND: "This endpoint has older packages than the pool",
            SyncStatus.OFFLINE: "Cannot connect to the central server",
            SyncStatus.SYNCING: "Synchronization operation in progress",
            SyncStatus.ERROR: "An error occurred during synchronization"
        }
        
        self._initialize_tray_icon()
    
    def _initialize_tray_icon(self) -> None:
        """Initialize the system tray icon and context menu."""
        if not QSystemTrayIcon.isSystemTrayAvailable():
            logger.warning("System tray is not available on this system")
            return
        
        # Create system tray icon
        self._tray_icon = QSystemTrayIcon(self)
        self._tray_icon.activated.connect(self._on_tray_activated)
        
        # Create context menu
        self._create_context_menu()
        
        # Set initial status
        self._update_tray_appearance()
        
        # Show the tray icon
        self._tray_icon.show()
        
        logger.info("System tray icon initialized")
    
    def _create_context_menu(self) -> None:
        """Create the context menu for the system tray icon."""
        self._context_menu = QMenu()
        
        # Status display (non-clickable)
        self._status_action = QAction("Status: Offline", self)
        self._status_action.setEnabled(False)
        self._context_menu.addAction(self._status_action)
        
        self._context_menu.addSeparator()
        
        # Sync actions
        sync_action = QAction("Sync to Latest", self)
        sync_action.setToolTip("Update all packages to match the latest pool state")
        sync_action.triggered.connect(self.sync_requested.emit)
        self._context_menu.addAction(sync_action)
        
        set_latest_action = QAction("Set as Current Latest", self)
        set_latest_action.setToolTip("Mark current package state as the new pool target")
        set_latest_action.triggered.connect(self.set_latest_requested.emit)
        self._context_menu.addAction(set_latest_action)
        
        revert_action = QAction("Revert to Previous", self)
        revert_action.setToolTip("Restore packages to the previous synchronized state")
        revert_action.triggered.connect(self.revert_requested.emit)
        self._context_menu.addAction(revert_action)
        
        self._context_menu.addSeparator()
        
        # Information and settings
        details_action = QAction("Show Details", self)
        details_action.triggered.connect(self.show_details_requested.emit)
        self._context_menu.addAction(details_action)
        
        config_action = QAction("Configuration...", self)
        config_action.triggered.connect(self.config_requested.emit)
        self._context_menu.addAction(config_action)
        
        self._context_menu.addSeparator()
        
        # Quit action
        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(self.quit_requested.emit)
        self._context_menu.addAction(quit_action)
        
        # Set context menu on tray icon
        if self._tray_icon:
            self._tray_icon.setContextMenu(self._context_menu)
    
    def _create_status_icon(self, status: SyncStatus) -> QIcon:
        """Create an icon representing the given sync status."""
        # Create a simple colored square icon for each status
        # In a real implementation, you'd use proper icon files
        pixmap = QPixmap(16, 16)
        
        color_map = {
            SyncStatus.IN_SYNC: "#00AA00",      # Green
            SyncStatus.AHEAD: "#FF8800",        # Orange  
            SyncStatus.BEHIND: "#0088FF",       # Blue
            SyncStatus.OFFLINE: "#888888",      # Gray
            SyncStatus.SYNCING: "#FFFF00",      # Yellow
            SyncStatus.ERROR: "#FF0000"         # Red
        }
        
        color = color_map.get(status, "#888888")
        pixmap.fill(QColor(color))
        
        return QIcon(pixmap)
    
    def _update_tray_appearance(self) -> None:
        """Update the tray icon appearance based on current status."""
        if not self._tray_icon:
            return
        
        # Update icon
        icon = self._create_status_icon(self._current_status)
        self._tray_icon.setIcon(icon)
        
        # Update tooltip
        tooltip = self._status_tooltips.get(self._current_status, "Unknown status")
        self._tray_icon.setToolTip(f"Pacman Sync Utility - {tooltip}")
        
        # Update status action text
        if self._status_action:
            status_text = self._status_texts.get(self._current_status, "Unknown")
            self._status_action.setText(f"Status: {status_text}")
    
    def _on_tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        """Handle tray icon activation (clicks)."""
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            # Double-click shows details
            self.show_details_requested.emit()
        elif reason == QSystemTrayIcon.ActivationReason.MiddleClick:
            # Middle-click triggers sync
            self.sync_requested.emit()
    
    def set_status(self, status: SyncStatus) -> None:
        """Update the sync status and refresh the tray icon."""
        if self._current_status != status:
            old_status = self._current_status
            self._current_status = status
            self._update_tray_appearance()
            self.status_changed.emit(status)
            logger.info(f"Status changed from {old_status.value} to {status.value}")
    
    def get_status(self) -> SyncStatus:
        """Get the current sync status."""
        return self._current_status
    
    def show_message(self, title: str, message: str, 
                    icon: QSystemTrayIcon.MessageIcon = QSystemTrayIcon.MessageIcon.Information,
                    timeout: int = 5000) -> None:
        """Show a system tray notification message."""
        if self._tray_icon and self._tray_icon.supportsMessages():
            self._tray_icon.showMessage(title, message, icon, timeout)
        else:
            logger.info(f"Notification: {title} - {message}")
    
    def is_available(self) -> bool:
        """Check if system tray is available."""
        return self._tray_icon is not None and QSystemTrayIcon.isSystemTrayAvailable()


class PacmanSyncApplication(QApplication):
    """
    Main Qt application class for the Pacman Sync Utility client.
    
    Provides system tray integration with AppIndicator and KStatusNotifierItem support
    for cross-desktop environment compatibility.
    """
    
    def __init__(self, argv: list[str]):
        super().__init__(argv)
        
        # Application metadata
        self.setApplicationName("Pacman Sync Utility")
        self.setApplicationVersion("1.0.0")
        self.setOrganizationName("Pacman Sync")
        self.setQuitOnLastWindowClosed(False)  # Keep running when windows are closed
        
        # Components
        self._status_indicator: Optional[SyncStatusIndicator] = None
        self._status_update_timer: Optional[QTimer] = None
        
        # Callbacks for external integration
        self._sync_callback: Optional[Callable] = None
        self._set_latest_callback: Optional[Callable] = None
        self._revert_callback: Optional[Callable] = None
        self._status_update_callback: Optional[Callable] = None
        
        self._initialize_application()
    
    def _initialize_application(self) -> None:
        """Initialize the Qt application components."""
        # Check system tray availability
        if not QSystemTrayIcon.isSystemTrayAvailable():
            QMessageBox.critical(
                None, 
                "System Tray",
                "System tray is not available on this system. "
                "The application will run in command-line mode only."
            )
            logger.error("System tray not available")
            return
        
        # Initialize status indicator
        self._status_indicator = SyncStatusIndicator(self)
        self._connect_status_indicator_signals()
        
        # Set up periodic status updates
        self._status_update_timer = QTimer(self)
        self._status_update_timer.timeout.connect(self._update_status)
        self._status_update_timer.start(30000)  # Update every 30 seconds
        
        logger.info("Qt application initialized successfully")
    
    def _connect_status_indicator_signals(self) -> None:
        """Connect status indicator signals to application handlers."""
        if not self._status_indicator:
            return
        
        self._status_indicator.sync_requested.connect(self._handle_sync_request)
        self._status_indicator.set_latest_requested.connect(self._handle_set_latest_request)
        self._status_indicator.revert_requested.connect(self._handle_revert_request)
        self._status_indicator.show_details_requested.connect(self._handle_show_details_request)
        self._status_indicator.config_requested.connect(self._handle_config_request)
        self._status_indicator.quit_requested.connect(self._handle_quit_request)
    
    def _handle_sync_request(self) -> None:
        """Handle sync to latest request from tray menu."""
        logger.info("Sync request received from system tray")
        if self._sync_callback:
            try:
                self._sync_callback()
                if self._status_indicator:
                    self._status_indicator.show_message(
                        "Sync Started", 
                        "Synchronizing packages to latest pool state..."
                    )
            except Exception as e:
                logger.error(f"Sync operation failed: {e}")
                if self._status_indicator:
                    self._status_indicator.show_message(
                        "Sync Failed", 
                        f"Synchronization failed: {str(e)}",
                        QSystemTrayIcon.MessageIcon.Critical
                    )
    
    def _handle_set_latest_request(self) -> None:
        """Handle set as latest request from tray menu."""
        logger.info("Set latest request received from system tray")
        if self._set_latest_callback:
            try:
                self._set_latest_callback()
                if self._status_indicator:
                    self._status_indicator.show_message(
                        "State Updated", 
                        "Current package state set as pool latest"
                    )
            except Exception as e:
                logger.error(f"Set latest operation failed: {e}")
                if self._status_indicator:
                    self._status_indicator.show_message(
                        "Operation Failed", 
                        f"Failed to set latest state: {str(e)}",
                        QSystemTrayIcon.MessageIcon.Critical
                    )
    
    def _handle_revert_request(self) -> None:
        """Handle revert to previous request from tray menu."""
        logger.info("Revert request received from system tray")
        if self._revert_callback:
            try:
                self._revert_callback()
                if self._status_indicator:
                    self._status_indicator.show_message(
                        "Reverted", 
                        "Packages reverted to previous state"
                    )
            except Exception as e:
                logger.error(f"Revert operation failed: {e}")
                if self._status_indicator:
                    self._status_indicator.show_message(
                        "Revert Failed", 
                        f"Failed to revert: {str(e)}",
                        QSystemTrayIcon.MessageIcon.Critical
                    )
    
    def _handle_show_details_request(self) -> None:
        """Handle show details request from tray menu."""
        logger.info("Show details request received from system tray")
        
        # Import the windows module
        try:
            from client.qt.windows import PackageDetailsWindow, PackageInfo
            
            # Create sample package data (in real implementation, this would come from the system)
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
                )
            ]
            
            # Show package details window
            details_window = PackageDetailsWindow(sample_packages)
            details_window.show()
            
        except ImportError as e:
            logger.error(f"Failed to import windows module: {e}")
            # Fallback to simple message box
            if self._status_indicator:
                current_status = self._status_indicator.get_status()
                status_text = self._status_indicator._status_texts.get(current_status, "Unknown")
                QMessageBox.information(
                    None,
                    "Sync Status Details",
                    f"Current Status: {status_text}\n\n"
                    f"Detailed package information is not available."
                )
    
    def _handle_config_request(self) -> None:
        """Handle configuration request from tray menu."""
        logger.info("Configuration request received from system tray")
        
        try:
            from client.qt.windows import ConfigurationWindow
            
            # Sample configuration (in real implementation, this would come from config file)
            current_config = {
                'server_url': 'http://localhost:8080',
                'api_key': '',
                'timeout': 30,
                'retry_attempts': 3,
                'verify_ssl': True,
                'ssl_cert_path': '',
                'endpoint_name': 'my-desktop',
                'pool_id': 'default-pool',
                'update_interval': 300,
                'auto_register': True,
                'log_level': 'INFO',
                'log_file': '',
                'auto_sync': False,
                'sync_on_startup': False,
                'confirm_operations': True,
                'exclude_packages': ['linux', 'linux-headers'],
                'conflict_resolution': 'manual',
                'show_notifications': True,
                'minimize_to_tray': True,
                'start_minimized': False,
                'theme': 'System Default',
                'font_size': 10,
                'enable_waybar': False,
                'waybar_format': ''
            }
            
            # Show configuration window
            config_window = ConfigurationWindow(current_config)
            config_window.settings_changed.connect(self._handle_settings_changed)
            config_window.exec()
            
        except ImportError as e:
            logger.error(f"Failed to import configuration window: {e}")
            QMessageBox.information(
                None,
                "Configuration",
                "Configuration window is not available."
            )
    
    def _handle_settings_changed(self, settings: dict) -> None:
        """Handle configuration settings changes."""
        logger.info("Configuration settings changed")
        # In a real implementation, this would save the settings to a config file
        # and apply them to the running application
        logger.debug(f"New settings: {settings}")
    
    def _handle_quit_request(self) -> None:
        """Handle quit request from tray menu."""
        logger.info("Quit request received from system tray")
        self.quit()
    
    def _update_status(self) -> None:
        """Periodic status update from external source."""
        if self._status_update_callback:
            try:
                self._status_update_callback()
            except Exception as e:
                logger.error(f"Status update failed: {e}")
    
    def set_sync_callback(self, callback: Callable) -> None:
        """Set callback function for sync operations."""
        self._sync_callback = callback
    
    def set_set_latest_callback(self, callback: Callable) -> None:
        """Set callback function for set latest operations."""
        self._set_latest_callback = callback
    
    def set_revert_callback(self, callback: Callable) -> None:
        """Set callback function for revert operations."""
        self._revert_callback = callback
    
    def set_status_update_callback(self, callback: Callable) -> None:
        """Set callback function for periodic status updates."""
        self._status_update_callback = callback
    
    def update_sync_status(self, status: SyncStatus) -> None:
        """Update the sync status display."""
        if self._status_indicator:
            self._status_indicator.set_status(status)
    
    def get_sync_status(self) -> Optional[SyncStatus]:
        """Get the current sync status."""
        if self._status_indicator:
            return self._status_indicator.get_status()
        return None
    
    def show_notification(self, title: str, message: str, 
                         is_error: bool = False) -> None:
        """Show a system notification."""
        if self._status_indicator:
            icon = (QSystemTrayIcon.MessageIcon.Critical if is_error 
                   else QSystemTrayIcon.MessageIcon.Information)
            self._status_indicator.show_message(title, message, icon)
    
    def is_system_tray_available(self) -> bool:
        """Check if system tray functionality is available."""
        return (self._status_indicator is not None and 
                self._status_indicator.is_available())