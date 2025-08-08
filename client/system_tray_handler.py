"""
Enhanced system tray handler with graceful degradation.

This module provides robust system tray integration with fallback mechanisms
when system tray is unavailable, ensuring the application continues to function
in all desktop environments.
"""

import logging
import os
import sys
from typing import Optional, Callable, Dict, Any
from enum import Enum
from PyQt6.QtCore import QObject, pyqtSignal, QTimer
from PyQt6.QtWidgets import QSystemTrayIcon, QMenu, QApplication
from PyQt6.QtGui import QIcon, QPixmap, QAction

from shared.exceptions import SystemIntegrationError, ErrorCode
from client.error_handling import ClientErrorHandler

logger = logging.getLogger(__name__)


class TrayAvailability(Enum):
    """System tray availability states."""
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    UNKNOWN = "unknown"
    DEGRADED = "degraded"  # Available but with limited functionality


class FallbackNotificationMethod(Enum):
    """Alternative notification methods when tray is unavailable."""
    DESKTOP_NOTIFICATION = "desktop_notification"
    CONSOLE_OUTPUT = "console_output"
    LOG_FILE = "log_file"
    STATUS_FILE = "status_file"
    NONE = "none"


class SystemTrayHandler(QObject):
    """
    Enhanced system tray handler with graceful degradation.
    
    Provides robust system tray integration with automatic fallback to
    alternative notification methods when system tray is unavailable.
    """
    
    # Signals
    tray_availability_changed = pyqtSignal(object)  # TrayAvailability
    action_triggered = pyqtSignal(str)  # action_name
    notification_sent = pyqtSignal(str, str)  # title, message
    
    def __init__(self, app: QApplication, error_handler: Optional[ClientErrorHandler] = None):
        super().__init__()
        
        self.app = app
        self.error_handler = error_handler
        
        # Tray state
        self._tray_icon: Optional[QSystemTrayIcon] = None
        self._tray_menu: Optional[QMenu] = None
        self._availability = TrayAvailability.UNKNOWN
        self._fallback_method = FallbackNotificationMethod.DESKTOP_NOTIFICATION
        
        # Icons for different states
        self._icons: Dict[str, QIcon] = {}
        self._current_state = "unknown"
        
        # Fallback mechanisms
        self._status_file_path = os.path.expanduser("~/.pacman-sync-status")
        self._notification_callbacks: Dict[str, Callable] = {}
        
        # Monitoring
        self._availability_check_timer = QTimer(self)
        self._availability_check_timer.timeout.connect(self._check_tray_availability)
        self._availability_check_timer.start(30000)  # Check every 30 seconds
        
        # Initialize
        self._initialize_tray()
        self._setup_fallback_methods()
        
        logger.info("System tray handler initialized")
    
    def _initialize_tray(self):
        """Initialize system tray with availability detection."""
        try:
            # Check if system tray is available
            if not QSystemTrayIcon.isSystemTrayAvailable():
                logger.warning("System tray is not available")
                self._set_availability(TrayAvailability.UNAVAILABLE)
                self._handle_tray_unavailable()
                return
            
            # Create tray icon
            self._tray_icon = QSystemTrayIcon(self)
            
            # Set up default icon
            self._setup_icons()
            self._tray_icon.setIcon(self._icons.get("unknown", QIcon()))
            
            # Create context menu
            self._create_tray_menu()
            
            # Connect signals
            self._tray_icon.activated.connect(self._on_tray_activated)
            self._tray_icon.messageClicked.connect(self._on_message_clicked)
            
            # Show tray icon
            self._tray_icon.show()
            
            # Test tray functionality
            if self._test_tray_functionality():
                self._set_availability(TrayAvailability.AVAILABLE)
                logger.info("System tray initialized successfully")
            else:
                self._set_availability(TrayAvailability.DEGRADED)
                logger.warning("System tray has limited functionality")
            
        except Exception as e:
            logger.error(f"Failed to initialize system tray: {e}")
            self._set_availability(TrayAvailability.UNAVAILABLE)
            self._handle_tray_unavailable()
            
            if self.error_handler:
                self.error_handler.handle_system_tray_unavailable()
    
    def _setup_icons(self):
        """Set up icons for different sync states."""
        try:
            # Create simple colored icons if no icon files are available
            icon_configs = {
                "in_sync": {"color": "green", "symbol": "✓"},
                "ahead": {"color": "blue", "symbol": "↑"},
                "behind": {"color": "orange", "symbol": "↓"},
                "syncing": {"color": "yellow", "symbol": "⟳"},
                "error": {"color": "red", "symbol": "✗"},
                "offline": {"color": "gray", "symbol": "○"},
                "unknown": {"color": "gray", "symbol": "?"}
            }
            
            for state, config in icon_configs.items():
                icon = self._create_simple_icon(config["color"], config["symbol"])
                self._icons[state] = icon
                
        except Exception as e:
            logger.error(f"Failed to set up icons: {e}")
            # Create a basic fallback icon
            self._icons["unknown"] = QIcon()
    
    def _create_simple_icon(self, color: str, symbol: str) -> QIcon:
        """Create a simple colored icon with a symbol."""
        try:
            from PyQt6.QtGui import QPainter, QFont, QColor
            
            # Create a 16x16 pixmap
            pixmap = QPixmap(16, 16)
            pixmap.fill(QColor("transparent"))
            
            # Paint the icon
            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            
            # Set color
            color_map = {
                "green": QColor(0, 150, 0),
                "blue": QColor(0, 100, 200),
                "orange": QColor(255, 150, 0),
                "yellow": QColor(200, 200, 0),
                "red": QColor(200, 0, 0),
                "gray": QColor(128, 128, 128)
            }
            
            painter.setPen(color_map.get(color, QColor(128, 128, 128)))
            painter.setFont(QFont("Arial", 12, QFont.Weight.Bold))
            
            # Draw symbol
            painter.drawText(pixmap.rect(), symbol)
            painter.end()
            
            return QIcon(pixmap)
            
        except Exception as e:
            logger.error(f"Failed to create icon: {e}")
            return QIcon()
    
    def _create_tray_menu(self):
        """Create system tray context menu."""
        try:
            self._tray_menu = QMenu()
            
            # Sync actions
            sync_action = QAction("Sync to Latest", self)
            sync_action.triggered.connect(lambda: self.action_triggered.emit("sync"))
            self._tray_menu.addAction(sync_action)
            
            set_latest_action = QAction("Set as Latest", self)
            set_latest_action.triggered.connect(lambda: self.action_triggered.emit("set_latest"))
            self._tray_menu.addAction(set_latest_action)
            
            revert_action = QAction("Revert to Previous", self)
            revert_action.triggered.connect(lambda: self.action_triggered.emit("revert"))
            self._tray_menu.addAction(revert_action)
            
            self._tray_menu.addSeparator()
            
            # Status action
            status_action = QAction("Show Status", self)
            status_action.triggered.connect(lambda: self.action_triggered.emit("show_status"))
            self._tray_menu.addAction(status_action)
            
            self._tray_menu.addSeparator()
            
            # Settings action
            settings_action = QAction("Settings", self)
            settings_action.triggered.connect(lambda: self.action_triggered.emit("settings"))
            self._tray_menu.addAction(settings_action)
            
            # Quit action
            quit_action = QAction("Quit", self)
            quit_action.triggered.connect(lambda: self.action_triggered.emit("quit"))
            self._tray_menu.addAction(quit_action)
            
            # Set menu on tray icon
            if self._tray_icon:
                self._tray_icon.setContextMenu(self._tray_menu)
                
        except Exception as e:
            logger.error(f"Failed to create tray menu: {e}")
    
    def _test_tray_functionality(self) -> bool:
        """Test if tray functionality works properly."""
        try:
            if not self._tray_icon:
                return False
            
            # Test basic functionality
            self._tray_icon.setToolTip("Pacman Sync Utility - Testing")
            
            # Test if we can show/hide (some systems don't support this)
            try:
                self._tray_icon.hide()
                self._tray_icon.show()
            except:
                logger.warning("Tray show/hide functionality limited")
            
            return True
            
        except Exception as e:
            logger.error(f"Tray functionality test failed: {e}")
            return False
    
    def _setup_fallback_methods(self):
        """Set up fallback notification methods."""
        try:
            # Determine best fallback method
            if self._can_use_desktop_notifications():
                self._fallback_method = FallbackNotificationMethod.DESKTOP_NOTIFICATION
            elif sys.stdout.isatty():
                self._fallback_method = FallbackNotificationMethod.CONSOLE_OUTPUT
            else:
                self._fallback_method = FallbackNotificationMethod.STATUS_FILE
            
            logger.info(f"Fallback notification method: {self._fallback_method.value}")
            
        except Exception as e:
            logger.error(f"Failed to set up fallback methods: {e}")
            self._fallback_method = FallbackNotificationMethod.LOG_FILE
    
    def _can_use_desktop_notifications(self) -> bool:
        """Check if desktop notifications are available."""
        try:
            # Check for common notification systems
            desktop_env = os.environ.get('XDG_CURRENT_DESKTOP', '').lower()
            
            # Check for notify-send command
            import shutil
            if shutil.which('notify-send'):
                return True
            
            # Check for desktop-specific notification systems
            if desktop_env in ['gnome', 'unity', 'cinnamon']:
                return shutil.which('gdbus') is not None
            elif desktop_env in ['kde', 'plasma']:
                return shutil.which('kdialog') is not None
            
            return False
            
        except Exception:
            return False
    
    def _set_availability(self, availability: TrayAvailability):
        """Set tray availability and emit signal if changed."""
        if self._availability != availability:
            old_availability = self._availability
            self._availability = availability
            
            logger.info(f"Tray availability changed: {old_availability.value} -> {availability.value}")
            self.tray_availability_changed.emit(availability)
    
    def _handle_tray_unavailable(self):
        """Handle system tray unavailability with graceful degradation."""
        logger.info("Handling system tray unavailability with graceful degradation")
        
        # Show fallback notification about tray unavailability
        self._send_fallback_notification(
            "System Tray Unavailable",
            "Pacman Sync Utility is running without system tray integration. "
            "Notifications will be shown using alternative methods."
        )
        
        # Set up alternative status reporting
        self._setup_alternative_status_reporting()
    
    def _setup_alternative_status_reporting(self):
        """Set up alternative status reporting when tray is unavailable."""
        try:
            # Create status file for external monitoring
            self._write_status_file({
                "status": "running",
                "tray_available": False,
                "fallback_method": self._fallback_method.value,
                "timestamp": self._get_current_timestamp()
            })
            
            logger.info(f"Alternative status reporting set up: {self._status_file_path}")
            
        except Exception as e:
            logger.error(f"Failed to set up alternative status reporting: {e}")
    
    def _check_tray_availability(self):
        """Periodically check tray availability."""
        try:
            current_available = QSystemTrayIcon.isSystemTrayAvailable()
            
            if current_available and self._availability == TrayAvailability.UNAVAILABLE:
                logger.info("System tray became available - attempting to initialize")
                self._initialize_tray()
            elif not current_available and self._availability == TrayAvailability.AVAILABLE:
                logger.warning("System tray became unavailable")
                self._set_availability(TrayAvailability.UNAVAILABLE)
                self._handle_tray_unavailable()
                
        except Exception as e:
            logger.error(f"Error checking tray availability: {e}")
    
    def _on_tray_activated(self, reason):
        """Handle tray icon activation."""
        try:
            if reason == QSystemTrayIcon.ActivationReason.Trigger:
                # Left click - show status
                self.action_triggered.emit("show_status")
            elif reason == QSystemTrayIcon.ActivationReason.DoubleClick:
                # Double click - sync action
                self.action_triggered.emit("sync")
                
        except Exception as e:
            logger.error(f"Error handling tray activation: {e}")
    
    def _on_message_clicked(self):
        """Handle notification message click."""
        try:
            self.action_triggered.emit("show_status")
        except Exception as e:
            logger.error(f"Error handling message click: {e}")
    
    def set_state(self, state: str, tooltip: Optional[str] = None):
        """
        Set the current sync state and update tray icon.
        
        Args:
            state: Sync state (in_sync, ahead, behind, syncing, error, offline)
            tooltip: Optional tooltip text
        """
        try:
            self._current_state = state
            
            if self._availability == TrayAvailability.AVAILABLE and self._tray_icon:
                # Update tray icon
                icon = self._icons.get(state, self._icons.get("unknown"))
                self._tray_icon.setIcon(icon)
                
                # Update tooltip
                if tooltip:
                    self._tray_icon.setToolTip(f"Pacman Sync Utility - {tooltip}")
                else:
                    state_messages = {
                        "in_sync": "In sync",
                        "ahead": "Ahead of pool",
                        "behind": "Behind pool",
                        "syncing": "Synchronizing...",
                        "error": "Error occurred",
                        "offline": "Offline",
                        "unknown": "Status unknown"
                    }
                    message = state_messages.get(state, "Unknown state")
                    self._tray_icon.setToolTip(f"Pacman Sync Utility - {message}")
            
            # Update status file for fallback monitoring
            self._write_status_file({
                "sync_state": state,
                "tooltip": tooltip,
                "timestamp": self._get_current_timestamp(),
                "tray_available": self._availability == TrayAvailability.AVAILABLE
            })
            
        except Exception as e:
            logger.error(f"Failed to set state: {e}")
    
    def show_notification(self, title: str, message: str, icon_type: str = "information"):
        """
        Show notification with fallback support.
        
        Args:
            title: Notification title
            message: Notification message
            icon_type: Icon type (information, warning, critical)
        """
        try:
            if self._availability == TrayAvailability.AVAILABLE and self._tray_icon:
                # Use system tray notification
                icon_map = {
                    "information": QSystemTrayIcon.MessageIcon.Information,
                    "warning": QSystemTrayIcon.MessageIcon.Warning,
                    "critical": QSystemTrayIcon.MessageIcon.Critical
                }
                
                icon = icon_map.get(icon_type, QSystemTrayIcon.MessageIcon.Information)
                self._tray_icon.showMessage(title, message, icon, 5000)  # 5 second timeout
                
            else:
                # Use fallback notification
                self._send_fallback_notification(title, message)
            
            self.notification_sent.emit(title, message)
            
        except Exception as e:
            logger.error(f"Failed to show notification: {e}")
            # Always try fallback on error
            self._send_fallback_notification(title, message)
    
    def _send_fallback_notification(self, title: str, message: str):
        """Send notification using fallback method."""
        try:
            if self._fallback_method == FallbackNotificationMethod.DESKTOP_NOTIFICATION:
                self._send_desktop_notification(title, message)
            elif self._fallback_method == FallbackNotificationMethod.CONSOLE_OUTPUT:
                self._send_console_notification(title, message)
            elif self._fallback_method == FallbackNotificationMethod.STATUS_FILE:
                self._send_status_file_notification(title, message)
            else:
                # Log as fallback
                logger.info(f"NOTIFICATION: {title} - {message}")
                
        except Exception as e:
            logger.error(f"Fallback notification failed: {e}")
            # Ultimate fallback - just log it
            logger.info(f"NOTIFICATION: {title} - {message}")
    
    def _send_desktop_notification(self, title: str, message: str):
        """Send desktop notification using system commands."""
        try:
            import subprocess
            
            # Try notify-send first
            if os.system("which notify-send > /dev/null 2>&1") == 0:
                subprocess.run([
                    "notify-send", 
                    "-a", "Pacman Sync Utility",
                    "-i", "system-software-update",
                    title, 
                    message
                ], check=False)
                return
            
            # Try desktop-specific methods
            desktop_env = os.environ.get('XDG_CURRENT_DESKTOP', '').lower()
            
            if desktop_env in ['kde', 'plasma'] and os.system("which kdialog > /dev/null 2>&1") == 0:
                subprocess.run([
                    "kdialog", 
                    "--passivepopup", 
                    f"{title}\n{message}", 
                    "5"
                ], check=False)
                return
            
            # Fallback to console
            self._send_console_notification(title, message)
            
        except Exception as e:
            logger.error(f"Desktop notification failed: {e}")
            self._send_console_notification(title, message)
    
    def _send_console_notification(self, title: str, message: str):
        """Send notification to console."""
        print(f"\n=== {title} ===")
        print(message)
        print("=" * (len(title) + 8))
    
    def _send_status_file_notification(self, title: str, message: str):
        """Send notification by writing to status file."""
        try:
            notification_data = {
                "type": "notification",
                "title": title,
                "message": message,
                "timestamp": self._get_current_timestamp()
            }
            
            # Append to status file
            status_file = self._status_file_path + ".notifications"
            with open(status_file, "a", encoding="utf-8") as f:
                import json
                f.write(json.dumps(notification_data) + "\n")
                
        except Exception as e:
            logger.error(f"Status file notification failed: {e}")
    
    def _write_status_file(self, status_data: Dict[str, Any]):
        """Write status information to file."""
        try:
            import json
            with open(self._status_file_path, "w", encoding="utf-8") as f:
                json.dump(status_data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to write status file: {e}")
    
    def _get_current_timestamp(self) -> str:
        """Get current timestamp as ISO string."""
        from datetime import datetime
        return datetime.now().isoformat()
    
    def is_available(self) -> bool:
        """Check if system tray is available."""
        return self._availability == TrayAvailability.AVAILABLE
    
    def get_availability(self) -> TrayAvailability:
        """Get current tray availability status."""
        return self._availability
    
    def get_fallback_method(self) -> FallbackNotificationMethod:
        """Get current fallback notification method."""
        return self._fallback_method
    
    def cleanup(self):
        """Clean up resources."""
        try:
            if self._availability_check_timer:
                self._availability_check_timer.stop()
            
            if self._tray_icon:
                self._tray_icon.hide()
                self._tray_icon = None
            
            if self._tray_menu:
                self._tray_menu.clear()
                self._tray_menu = None
                
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")