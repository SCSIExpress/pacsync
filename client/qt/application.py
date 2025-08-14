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
        self._config: Optional['ClientConfiguration'] = None
        
        # Callbacks for external integration
        self._sync_callback: Optional[Callable] = None
        self._set_latest_callback: Optional[Callable] = None
        self._revert_callback: Optional[Callable] = None
        self._status_update_callback: Optional[Callable] = None
        self._config_changed_callback: Optional[Callable] = None
        
        self._initialize_application()
    
    def _initialize_application(self) -> None:
        """Initialize the Qt application components with graceful degradation."""
        # Check system tray availability
        if not QSystemTrayIcon.isSystemTrayAvailable():
            logger.warning("System tray is not available on this system")
            
            # Set up graceful degradation
            self._setup_fallback_mode()
            
            # Show informational message instead of critical error
            QMessageBox.information(
                None, 
                "System Tray Unavailable",
                "System tray is not available on this system. "
                "The application will continue to run with limited notification capabilities. "
                "You can still use command-line operations and check logs for status updates."
            )
            return
        
        # Initialize status indicator
        self._status_indicator = SyncStatusIndicator(self)
        self._connect_status_indicator_signals()
        
        # Set up periodic status updates
        self._status_update_timer = QTimer(self)
        self._status_update_timer.timeout.connect(self._update_status)
        self._status_update_timer.start(30000)  # Update every 30 seconds
        
        logger.info("Qt application initialized successfully")
    
    def _setup_fallback_mode(self):
        """Set up fallback mode when system tray is unavailable."""
        logger.info("Setting up fallback mode for system tray unavailability")
        
        # Create a minimal status indicator that logs instead of showing tray icons
        self._status_indicator = None
        
        # Set up file-based status reporting
        self._setup_file_status_reporting()
        
        # Set up periodic status updates with console output
        self._status_update_timer = QTimer(self)
        self._status_update_timer.timeout.connect(self._update_status_fallback)
        self._status_update_timer.start(60000)  # Update every minute in fallback mode
    
    def _setup_file_status_reporting(self):
        """Set up file-based status reporting for fallback mode."""
        try:
            import os
            from pathlib import Path
            
            # Create status directory
            status_dir = Path.home() / '.pacman-sync'
            status_dir.mkdir(exist_ok=True)
            
            self._status_file = status_dir / 'status.txt'
            self._write_status_file("OFFLINE", "System tray unavailable - running in fallback mode")
            
            logger.info(f"Status file created at: {self._status_file}")
            
        except Exception as e:
            logger.error(f"Failed to set up file status reporting: {e}")
            self._status_file = None
    
    def _write_status_file(self, status: str, message: str):
        """Write status to file for fallback mode."""
        if not hasattr(self, '_status_file') or not self._status_file:
            return
        
        try:
            from datetime import datetime
            
            status_content = f"""Pacman Sync Utility Status
Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Status: {status}
Message: {message}

Note: System tray is not available. Check this file for status updates.
Use command-line options for operations: --sync, --set-latest, --revert, --status
"""
            
            with open(self._status_file, 'w') as f:
                f.write(status_content)
                
        except Exception as e:
            logger.error(f"Failed to write status file: {e}")
    
    def _update_status_fallback(self):
        """Update status in fallback mode."""
        if self._status_update_callback:
            try:
                self._status_update_callback()
            except Exception as e:
                logger.error(f"Status update failed in fallback mode: {e}")
        
        # Update status file
        current_status = self.get_sync_status()
        if current_status:
            self._write_status_file(
                current_status.value.upper(),
                f"Application running in fallback mode (no system tray)"
            )
    
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
            from client.config import ClientConfiguration
            
            # Use stored configuration or load from file
            config = self._config or ClientConfiguration()
            all_config = config.get_all_config()
            
            # Convert configuration to format expected by ConfigurationWindow
            current_config = {
                # Server settings
                'server_url': config.get_server_url(),
                'api_key': config.get_api_key() or '',
                'timeout': int(config.get_server_timeout()),  # Convert float to int
                'retry_attempts': int(config.get_retry_attempts()),  # Ensure int
                'verify_ssl': self._to_bool(all_config.get('server', {}).get('verify_ssl', True)),
                'ssl_cert_path': all_config.get('server', {}).get('ssl_cert_path', ''),
                
                # Client settings
                'endpoint_name': config.get_endpoint_name(),
                'pool_id': config.get_pool_id() or '',  # Read-only, for display purposes
                'update_interval': int(config.get_update_interval()),  # Convert to int
                'auto_register': self._to_bool(all_config.get('client', {}).get('auto_register', True)),
                'auto_sync': self._to_bool(config.is_auto_sync_enabled()),
                'sync_on_startup': self._to_bool(all_config.get('client', {}).get('sync_on_startup', False)),
                'confirm_operations': self._to_bool(all_config.get('operations', {}).get('confirm_destructive_operations', True)),
                'exclude_packages': all_config.get('operations', {}).get('exclude_packages', []),
                'conflict_resolution': all_config.get('operations', {}).get('conflict_resolution', 'manual'),
                
                # Logging settings
                'log_level': config.get_log_level(),
                'log_file': config.get_log_file() or '',
                
                # UI settings
                'show_notifications': self._to_bool(config.should_show_notifications()),
                'minimize_to_tray': self._to_bool(config.should_minimize_to_tray()),
                'start_minimized': self._to_bool(all_config.get('ui', {}).get('start_minimized', False)),
                'theme': all_config.get('ui', {}).get('theme', 'System Default'),
                'font_size': int(all_config.get('ui', {}).get('font_size', 10)),  # Ensure int
                
                # WayBar settings
                'enable_waybar': self._to_bool(all_config.get('waybar', {}).get('enabled', False)),
                'waybar_format': all_config.get('waybar', {}).get('format', '')
            }
            
            # Show configuration window
            config_window = ConfigurationWindow(current_config)
            config_window.settings_changed.connect(lambda settings: self._handle_settings_changed(settings, config))
            config_window.exec()
            
        except ImportError as e:
            logger.error(f"Failed to import configuration window: {e}")
            QMessageBox.information(
                None,
                "Configuration",
                "Configuration window is not available."
            )
    
    def _handle_settings_changed(self, settings: dict, config: 'ClientConfiguration') -> None:
        """Handle configuration settings changes."""
        logger.info("Configuration settings changed")
        
        try:
            # Update configuration with new settings
            # Server settings
            config.set_config('server.url', settings.get('server_url', ''))
            if settings.get('api_key'):
                config.set_config('server.api_key', settings['api_key'])
            config.set_config('server.timeout', settings.get('timeout', 30))
            config.set_config('server.retry_attempts', settings.get('retry_attempts', 3))
            config.set_config('server.verify_ssl', settings.get('verify_ssl', True))
            if settings.get('ssl_cert_path'):
                config.set_config('server.ssl_cert_path', settings['ssl_cert_path'])
            
            # Client settings
            config.set_config('client.endpoint_name', settings.get('endpoint_name', ''))
            # Note: pool_id is not saved from UI - it's managed by the server
            config.set_config('client.update_interval', settings.get('update_interval', 300))
            config.set_config('client.auto_register', settings.get('auto_register', True))
            config.set_config('client.auto_sync', settings.get('auto_sync', False))
            config.set_config('client.sync_on_startup', settings.get('sync_on_startup', False))
            
            # Operations settings
            config.set_config('operations.confirm_destructive_operations', settings.get('confirm_operations', True))
            config.set_config('operations.exclude_packages', settings.get('exclude_packages', []))
            config.set_config('operations.conflict_resolution', settings.get('conflict_resolution', 'manual'))
            
            # Logging settings
            config.set_config('logging.level', settings.get('log_level', 'INFO'))
            if settings.get('log_file'):
                config.set_config('logging.file', settings['log_file'])
            
            # UI settings
            config.set_config('ui.show_notifications', settings.get('show_notifications', True))
            config.set_config('ui.minimize_to_tray', settings.get('minimize_to_tray', True))
            config.set_config('ui.start_minimized', settings.get('start_minimized', False))
            config.set_config('ui.theme', settings.get('theme', 'System Default'))
            config.set_config('ui.font_size', settings.get('font_size', 10))
            
            # WayBar settings
            config.set_config('waybar.enabled', settings.get('enable_waybar', False))
            config.set_config('waybar.format', settings.get('waybar_format', ''))
            
            # Save configuration to file
            config.save_configuration()
            
            # Save configuration to file
            config.save_configuration()
            
            # Reload and apply configuration changes immediately
            self.reload_configuration()
            
            logger.info(f"Configuration saved and reloaded: {config.get_config_file_path()}")
            
        except Exception as e:
            logger.error(f"Failed to save configuration: {e}")
            if self._status_indicator:
                self._status_indicator.show_message(
                    "Configuration Error",
                    f"Failed to save settings: {str(e)}",
                    QSystemTrayIcon.MessageIcon.Critical
                )
            else:
                # Fallback error display
                QMessageBox.critical(
                    None,
                    "Configuration Error",
                    f"Failed to save configuration:\n{str(e)}"
                )
    
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
    
    def set_configuration(self, config: 'ClientConfiguration') -> None:
        """Set the configuration object for the application."""
        self._config = config
    
    def _to_bool(self, value) -> bool:
        """Convert various value types to boolean."""
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ('true', '1', 'yes', 'on')
        if isinstance(value, (int, float)):
            return bool(value)
        return bool(value)
    
    def reload_configuration(self) -> None:
        """Reload configuration and apply changes to the running application."""
        if not self._config:
            logger.warning("No configuration object available for reload")
            return
        
        try:
            # Reload configuration from file
            self._config.reload_configuration()
            logger.info("Configuration reloaded from file")
            
            # Apply configuration changes to running components
            self._apply_configuration_changes()
            
            # Show notification
            if self._status_indicator:
                self._status_indicator.show_message(
                    "Configuration Reloaded",
                    "Settings have been applied to the running application"
                )
            
        except Exception as e:
            logger.error(f"Failed to reload configuration: {e}")
            if self._status_indicator:
                self._status_indicator.show_message(
                    "Configuration Error",
                    f"Failed to reload configuration: {str(e)}",
                    QSystemTrayIcon.MessageIcon.Critical
                )
    
    def _apply_configuration_changes(self) -> None:
        """Apply configuration changes to running application components."""
        if not self._config:
            return
        
        try:
            # Update status update timer interval
            if self._status_update_timer:
                new_interval = self._config.get_update_interval() * 1000  # Convert to milliseconds
                current_interval = self._status_update_timer.interval()
                if new_interval != current_interval:
                    self._status_update_timer.setInterval(new_interval)
                    logger.info(f"Updated status update interval to {new_interval/1000} seconds")
            
            # Update notification settings (will apply to future notifications)
            show_notifications = self._config.should_show_notifications()
            logger.info(f"Notification setting updated: {show_notifications}")
            
            # Emit signal to notify other components of configuration changes
            # This allows sync manager and other components to update their settings
            if self._config_changed_callback:
                logger.info("Notifying components of configuration changes")
                self._config_changed_callback(self._config)
            else:
                logger.warning("No configuration change callback set")
            
            logger.info("Configuration changes applied to running application")
            
        except Exception as e:
            logger.error(f"Failed to apply configuration changes: {e}")
    
    def set_config_changed_callback(self, callback: Callable) -> None:
        """Set callback function for configuration changes."""
        self._config_changed_callback = callback
    
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
        """Show a system notification with graceful degradation."""
        if self._status_indicator:
            icon = (QSystemTrayIcon.MessageIcon.Critical if is_error 
                   else QSystemTrayIcon.MessageIcon.Information)
            self._status_indicator.show_message(title, message, icon)
        else:
            # Fallback notification methods
            self._show_fallback_notification(title, message, is_error)
    
    def _show_fallback_notification(self, title: str, message: str, is_error: bool = False):
        """Show notification when system tray is unavailable."""
        # Log the notification
        log_level = logging.ERROR if is_error else logging.INFO
        logger.log(log_level, f"NOTIFICATION: {title} - {message}")
        
        # Print to console
        prefix = "ERROR" if is_error else "INFO"
        print(f"[{prefix}] {title}: {message}")
        
        # Update status file if available
        if hasattr(self, '_status_file') and self._status_file:
            try:
                status = "ERROR" if is_error else "INFO"
                self._write_status_file(status, f"{title}: {message}")
            except Exception as e:
                logger.error(f"Failed to update status file with notification: {e}")
        
        # Try desktop notifications as fallback
        self._try_desktop_notification(title, message, is_error)
    
    def _try_desktop_notification(self, title: str, message: str, is_error: bool = False):
        """Try to show desktop notification using system tools."""
        try:
            import subprocess
            import shutil
            
            # Try notify-send (Linux)
            if shutil.which('notify-send'):
                urgency = 'critical' if is_error else 'normal'
                subprocess.run([
                    'notify-send',
                    '--urgency', urgency,
                    '--app-name', 'Pacman Sync Utility',
                    title,
                    message
                ], check=False, timeout=5)
                logger.debug("Desktop notification sent via notify-send")
                return
            
            # Try osascript (macOS)
            if shutil.which('osascript'):
                script = f'display notification "{message}" with title "{title}"'
                subprocess.run(['osascript', '-e', script], check=False, timeout=5)
                logger.debug("Desktop notification sent via osascript")
                return
            
            # Try PowerShell (Windows)
            if shutil.which('powershell'):
                script = f'''
                Add-Type -AssemblyName System.Windows.Forms
                $notification = New-Object System.Windows.Forms.NotifyIcon
                $notification.Icon = [System.Drawing.SystemIcons]::Information
                $notification.BalloonTipTitle = "{title}"
                $notification.BalloonTipText = "{message}"
                $notification.Visible = $true
                $notification.ShowBalloonTip(5000)
                '''
                subprocess.run(['powershell', '-Command', script], check=False, timeout=10)
                logger.debug("Desktop notification sent via PowerShell")
                return
            
            logger.debug("No desktop notification system found")
            
        except Exception as e:
            logger.debug(f"Failed to send desktop notification: {e}")
    
    def is_system_tray_available(self) -> bool:
        """Check if system tray functionality is available."""
        return (self._status_indicator is not None and 
                self._status_indicator.is_available())