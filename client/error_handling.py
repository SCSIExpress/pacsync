"""
Comprehensive error handling for Pacman Sync Utility Client.

This module provides graceful error handling, recovery mechanisms,
and user-friendly error reporting for the Qt client application.
"""

import logging
import traceback
from datetime import datetime
from typing import Optional, Dict, Any, Callable, List
from enum import Enum
from PyQt6.QtCore import QObject, pyqtSignal, QTimer
from PyQt6.QtWidgets import QMessageBox, QSystemTrayIcon

from shared.exceptions import (
    PacmanSyncError, ErrorCode, ErrorSeverity, RecoveryAction,
    NetworkError, AuthenticationError, SystemIntegrationError,
    handle_exception
)
from shared.logging_config import log_structured_error, AuditLogger

logger = logging.getLogger(__name__)


class ErrorDisplayMode(Enum):
    """How errors should be displayed to the user."""
    SILENT = "silent"
    NOTIFICATION = "notification"
    DIALOG = "dialog"
    BOTH = "both"


class NetworkState(Enum):
    """Network connectivity states."""
    ONLINE = "online"
    OFFLINE = "offline"
    DEGRADED = "degraded"
    UNKNOWN = "unknown"


class ClientErrorHandler(QObject):
    """
    Centralized error handling for the Qt client application.
    
    Provides graceful error handling, user notifications, recovery mechanisms,
    and graceful degradation for network failures and system integration issues.
    """
    
    # Signals for error events
    error_occurred = pyqtSignal(object)  # PacmanSyncError
    network_state_changed = pyqtSignal(object)  # NetworkState
    recovery_attempted = pyqtSignal(str, bool)  # action, success
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self._network_state = NetworkState.UNKNOWN
        self._system_tray_available = True
        self._error_history: List[Dict[str, Any]] = []
        self._recovery_callbacks: Dict[RecoveryAction, Callable] = {}
        self._audit_logger = AuditLogger("client_audit")
        
        # Error display preferences
        self._display_mode = ErrorDisplayMode.BOTH
        self._show_technical_details = False
        
        # Recovery timers
        self._reconnect_timer = QTimer(self)
        self._reconnect_timer.timeout.connect(self._attempt_reconnection)
        self._reconnect_timer.setSingleShot(True)
        
        # Network monitoring
        self._network_check_timer = QTimer(self)
        self._network_check_timer.timeout.connect(self._check_network_connectivity)
        self._network_check_timer.start(30000)  # Check every 30 seconds
        
        logger.info("Client error handler initialized")
    
    def set_display_mode(self, mode: ErrorDisplayMode):
        """Set how errors should be displayed to the user."""
        self._display_mode = mode
        logger.info(f"Error display mode set to: {mode.value}")
    
    def set_show_technical_details(self, show: bool):
        """Set whether to show technical details in error messages."""
        self._show_technical_details = show
    
    def set_system_tray_available(self, available: bool):
        """Set whether system tray is available for notifications."""
        self._system_tray_available = available
        if not available:
            logger.warning("System tray not available - notifications will be limited")
    
    def register_recovery_callback(self, action: RecoveryAction, callback: Callable):
        """Register a callback function for a specific recovery action."""
        self._recovery_callbacks[action] = callback
        logger.debug(f"Recovery callback registered for action: {action.value}")
    
    def handle_error(
        self,
        error: Exception,
        context: Optional[Dict[str, Any]] = None,
        endpoint_id: Optional[str] = None,
        operation_id: Optional[str] = None,
        auto_recover: bool = True
    ) -> bool:
        """
        Handle an error with appropriate logging, user notification, and recovery.
        
        Args:
            error: The error that occurred
            context: Additional context information
            endpoint_id: Optional endpoint ID for audit logging
            operation_id: Optional operation ID for audit logging
            auto_recover: Whether to attempt automatic recovery
            
        Returns:
            True if error was handled successfully, False otherwise
        """
        try:
            # Convert to structured error if needed
            if not isinstance(error, PacmanSyncError):
                structured_error = handle_exception(error, context)
            else:
                structured_error = error
            
            # Add to error history
            self._add_to_error_history(structured_error, context)
            
            # Log the error
            log_structured_error(logger, structured_error, endpoint_id, operation_id)
            
            # Audit log the error
            self._audit_logger.log_error(structured_error, endpoint_id, operation_id)
            
            # Update network state if it's a network error
            if isinstance(structured_error, NetworkError):
                self._update_network_state(NetworkState.OFFLINE)
            
            # Display error to user
            self._display_error_to_user(structured_error)
            
            # Emit signal for external handlers
            self.error_occurred.emit(structured_error)
            
            # Attempt recovery if enabled
            if auto_recover:
                self._attempt_recovery(structured_error)
            
            return True
            
        except Exception as e:
            # Fallback error handling
            logger.critical(f"Error in error handler: {str(e)}", exc_info=True)
            self._display_critical_error(f"Critical error in error handler: {str(e)}")
            return False
    
    def handle_network_error(
        self,
        error: Exception,
        retry_callback: Optional[Callable] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        """
        Handle network-specific errors with graceful degradation.
        
        Args:
            error: The network error
            retry_callback: Optional callback to retry the operation
            context: Additional context information
        """
        # Convert to NetworkError if needed
        if not isinstance(error, NetworkError):
            network_error = NetworkError(
                message=str(error),
                error_code=ErrorCode.NETWORK_CONNECTION_FAILED,
                context=context,
                cause=error
            )
        else:
            network_error = error
        
        # Update network state
        self._update_network_state(NetworkState.OFFLINE)
        
        # Handle the error
        self.handle_error(network_error, context, auto_recover=True)
        
        # Schedule retry if callback provided
        if retry_callback:
            self._schedule_retry(retry_callback, delay_seconds=30)
    
    def handle_authentication_error(
        self,
        error: Exception,
        refresh_callback: Optional[Callable] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        """
        Handle authentication errors with token refresh attempts.
        
        Args:
            error: The authentication error
            refresh_callback: Optional callback to refresh authentication
            context: Additional context information
        """
        # Convert to AuthenticationError if needed
        if not isinstance(error, AuthenticationError):
            auth_error = AuthenticationError(
                message=str(error),
                error_code=ErrorCode.AUTH_INVALID_TOKEN,
                context=context,
                cause=error
            )
        else:
            auth_error = error
        
        # Handle the error
        self.handle_error(auth_error, context, auto_recover=False)
        
        # Attempt token refresh if callback provided
        if refresh_callback:
            try:
                success = refresh_callback()
                if success:
                    logger.info("Authentication refreshed successfully")
                    self._show_notification("Authentication Restored", "Connection to server restored")
                else:
                    logger.warning("Authentication refresh failed")
            except Exception as e:
                logger.error(f"Error during authentication refresh: {e}")
    
    def handle_system_tray_unavailable(self):
        """Handle system tray unavailability with graceful degradation."""
        error = SystemIntegrationError(
            message="System tray is not available on this system",
            error_code=ErrorCode.SYSTEM_TRAY_UNAVAILABLE,
            context={'desktop_environment': self._get_desktop_environment()},
            user_message="System tray integration is not available. The application will continue to run but notifications may be limited."
        )
        
        self.set_system_tray_available(False)
        self.handle_error(error, auto_recover=False)
        
        # Show alternative notification method
        self._show_fallback_notification(
            "System Tray Unavailable",
            "System tray integration is not available. The application is running in limited mode."
        )
    
    def _add_to_error_history(self, error: PacmanSyncError, context: Optional[Dict[str, Any]]):
        """Add error to history for analysis and debugging."""
        history_entry = {
            'timestamp': datetime.now().isoformat(),
            'error_code': error.error_code.value,
            'message': error.message,
            'severity': error.severity.value,
            'context': error.context,
            'additional_context': context or {},
            'recovery_actions': [action.value for action in error.recovery_actions]
        }
        
        self._error_history.append(history_entry)
        
        # Keep only last 100 errors
        if len(self._error_history) > 100:
            self._error_history = self._error_history[-100:]
    
    def _display_error_to_user(self, error: PacmanSyncError):
        """Display error to user based on display mode and severity."""
        if self._display_mode == ErrorDisplayMode.SILENT:
            return
        
        # Determine display method based on severity and mode
        show_notification = (
            self._display_mode in [ErrorDisplayMode.NOTIFICATION, ErrorDisplayMode.BOTH] and
            self._system_tray_available
        )
        
        show_dialog = (
            self._display_mode in [ErrorDisplayMode.DIALOG, ErrorDisplayMode.BOTH] and
            error.severity in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL]
        )
        
        # Show notification
        if show_notification:
            self._show_error_notification(error)
        
        # Show dialog for critical errors
        if show_dialog:
            self._show_error_dialog(error)
    
    def _show_error_notification(self, error: PacmanSyncError):
        """Show error notification in system tray."""
        if not self._system_tray_available:
            return
        
        title = self._get_error_title(error)
        message = error.user_message
        
        # Determine icon based on severity
        icon = QSystemTrayIcon.MessageIcon.Critical
        if error.severity == ErrorSeverity.LOW:
            icon = QSystemTrayIcon.MessageIcon.Information
        elif error.severity == ErrorSeverity.MEDIUM:
            icon = QSystemTrayIcon.MessageIcon.Warning
        
        # Show notification (this would be called on the system tray icon)
        logger.info(f"Showing notification: {title} - {message}")
    
    def _show_error_dialog(self, error: PacmanSyncError):
        """Show error dialog for critical errors."""
        title = self._get_error_title(error)
        message = error.user_message
        
        if self._show_technical_details:
            message += f"\n\nTechnical Details:\nError Code: {error.error_code.value}"
            if error.context:
                message += f"\nContext: {error.context}"
        
        # Show message box
        msg_box = QMessageBox()
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        
        if error.severity == ErrorSeverity.CRITICAL:
            msg_box.setIcon(QMessageBox.Icon.Critical)
        else:
            msg_box.setIcon(QMessageBox.Icon.Warning)
        
        # Add recovery actions as buttons if available
        if error.recovery_actions:
            for action in error.recovery_actions[:3]:  # Limit to 3 actions
                if action in self._recovery_callbacks:
                    button_text = self._get_recovery_action_text(action)
                    msg_box.addButton(button_text, QMessageBox.ButtonRole.ActionRole)
        
        msg_box.addButton(QMessageBox.StandardButton.Ok)
        
        # Show dialog (in a real implementation, this would be shown properly)
        logger.info(f"Would show error dialog: {title} - {message}")
    
    def _show_notification(self, title: str, message: str):
        """Show a general notification."""
        if self._system_tray_available:
            logger.info(f"Notification: {title} - {message}")
        else:
            self._show_fallback_notification(title, message)
    
    def _show_fallback_notification(self, title: str, message: str):
        """Show notification when system tray is not available."""
        # In a real implementation, this might use desktop notifications
        # or write to a log file that the user can monitor
        logger.info(f"Fallback notification: {title} - {message}")
        print(f"NOTIFICATION: {title} - {message}")
    
    def _display_critical_error(self, message: str):
        """Display critical error that bypasses normal error handling."""
        logger.critical(message)
        print(f"CRITICAL ERROR: {message}")
        
        if self._system_tray_available:
            # Show critical notification
            pass
        else:
            # Fallback display
            self._show_fallback_notification("Critical Error", message)
    
    def _attempt_recovery(self, error: PacmanSyncError):
        """Attempt automatic recovery based on error type and recovery actions."""
        for action in error.recovery_actions:
            if action in self._recovery_callbacks:
                try:
                    logger.info(f"Attempting recovery action: {action.value}")
                    callback = self._recovery_callbacks[action]
                    success = callback()
                    
                    self.recovery_attempted.emit(action.value, success)
                    
                    if success:
                        logger.info(f"Recovery action {action.value} succeeded")
                        self._show_notification("Recovery Successful", f"Automatically recovered from error using {action.value}")
                        return
                    else:
                        logger.warning(f"Recovery action {action.value} failed")
                        
                except Exception as e:
                    logger.error(f"Error during recovery action {action.value}: {e}")
            
            elif action == RecoveryAction.RETRY_WITH_BACKOFF:
                # Schedule retry with exponential backoff
                self._schedule_retry_with_backoff(error)
            
            elif action == RecoveryAction.RECONNECT:
                # Schedule reconnection attempt
                self._schedule_reconnection()
    
    def _schedule_retry(self, callback: Callable, delay_seconds: int = 30):
        """Schedule a retry operation."""
        timer = QTimer(self)
        timer.setSingleShot(True)
        timer.timeout.connect(lambda: self._execute_retry(callback, timer))
        timer.start(delay_seconds * 1000)
        
        logger.info(f"Retry scheduled in {delay_seconds} seconds")
    
    def _execute_retry(self, callback: Callable, timer: QTimer):
        """Execute a retry operation."""
        try:
            callback()
            logger.info("Retry operation executed successfully")
        except Exception as e:
            logger.error(f"Retry operation failed: {e}")
        finally:
            timer.deleteLater()
    
    def _schedule_retry_with_backoff(self, error: PacmanSyncError):
        """Schedule retry with exponential backoff."""
        # Calculate backoff delay based on error history
        recent_errors = [
            e for e in self._error_history[-10:]
            if e['error_code'] == error.error_code.value
        ]
        
        delay = min(30 * (2 ** len(recent_errors)), 300)  # Max 5 minutes
        
        logger.info(f"Scheduling retry with backoff: {delay} seconds")
        # In a real implementation, this would schedule the actual retry
    
    def _schedule_reconnection(self):
        """Schedule a reconnection attempt."""
        if not self._reconnect_timer.isActive():
            self._reconnect_timer.start(30000)  # 30 seconds
            logger.info("Reconnection attempt scheduled")
    
    def _attempt_reconnection(self):
        """Attempt to reconnect to the server."""
        if RecoveryAction.RECONNECT in self._recovery_callbacks:
            try:
                callback = self._recovery_callbacks[RecoveryAction.RECONNECT]
                success = callback()
                
                if success:
                    logger.info("Reconnection successful")
                    self._update_network_state(NetworkState.ONLINE)
                    self._show_notification("Reconnected", "Connection to server restored")
                else:
                    logger.warning("Reconnection failed, will retry")
                    self._schedule_reconnection()
                    
            except Exception as e:
                logger.error(f"Error during reconnection: {e}")
                self._schedule_reconnection()
    
    def _check_network_connectivity(self):
        """Check network connectivity and update state."""
        try:
            import socket
            
            # Try to connect to a reliable host
            socket.create_connection(("8.8.8.8", 53), timeout=3)
            
            if self._network_state != NetworkState.ONLINE:
                self._update_network_state(NetworkState.ONLINE)
                
        except (socket.error, OSError):
            if self._network_state != NetworkState.OFFLINE:
                self._update_network_state(NetworkState.OFFLINE)
    
    def _update_network_state(self, new_state: NetworkState):
        """Update network state and emit signal if changed."""
        if self._network_state != new_state:
            old_state = self._network_state
            self._network_state = new_state
            
            logger.info(f"Network state changed: {old_state.value} -> {new_state.value}")
            self.network_state_changed.emit(new_state)
            
            # Handle state transitions
            if new_state == NetworkState.OFFLINE:
                self._show_notification("Network Offline", "Lost connection to network")
            elif new_state == NetworkState.ONLINE and old_state == NetworkState.OFFLINE:
                self._show_notification("Network Online", "Network connection restored")
    
    def _get_error_title(self, error: PacmanSyncError) -> str:
        """Get user-friendly error title."""
        title_map = {
            ErrorSeverity.LOW: "Information",
            ErrorSeverity.MEDIUM: "Warning",
            ErrorSeverity.HIGH: "Error",
            ErrorSeverity.CRITICAL: "Critical Error"
        }
        return title_map.get(error.severity, "Error")
    
    def _get_recovery_action_text(self, action: RecoveryAction) -> str:
        """Get user-friendly text for recovery actions."""
        text_map = {
            RecoveryAction.RETRY: "Retry",
            RecoveryAction.RETRY_WITH_BACKOFF: "Retry Later",
            RecoveryAction.RECONNECT: "Reconnect",
            RecoveryAction.REFRESH_TOKEN: "Refresh Authentication",
            RecoveryAction.USER_INTERVENTION: "Manual Fix Required",
            RecoveryAction.RESTART_SERVICE: "Restart Service",
            RecoveryAction.CONTACT_ADMIN: "Contact Administrator",
            RecoveryAction.IGNORE: "Ignore"
        }
        return text_map.get(action, action.value.replace('_', ' ').title())
    
    def _get_desktop_environment(self) -> str:
        """Get the current desktop environment."""
        import os
        
        desktop_env = os.environ.get('XDG_CURRENT_DESKTOP', '')
        if not desktop_env:
            desktop_env = os.environ.get('DESKTOP_SESSION', '')
        if not desktop_env:
            desktop_env = 'unknown'
        
        return desktop_env.lower()
    
    def get_error_history(self) -> List[Dict[str, Any]]:
        """Get the error history for debugging."""
        return self._error_history.copy()
    
    def get_network_state(self) -> NetworkState:
        """Get the current network state."""
        return self._network_state
    
    def clear_error_history(self):
        """Clear the error history."""
        self._error_history.clear()
        logger.info("Error history cleared")


def setup_client_error_handling(
    app,
    system_tray_icon=None,
    display_mode: ErrorDisplayMode = ErrorDisplayMode.BOTH,
    show_technical_details: bool = False
) -> ClientErrorHandler:
    """
    Set up comprehensive error handling for the client application.
    
    Args:
        app: The Qt application instance
        system_tray_icon: Optional system tray icon for notifications
        display_mode: How errors should be displayed
        show_technical_details: Whether to show technical details
        
    Returns:
        Configured ClientErrorHandler instance
    """
    error_handler = ClientErrorHandler(app)
    error_handler.set_display_mode(display_mode)
    error_handler.set_show_technical_details(show_technical_details)
    
    if system_tray_icon:
        error_handler.set_system_tray_available(True)
        # Connect system tray icon to error handler for notifications
    else:
        error_handler.set_system_tray_available(False)
    
    # Set up global exception handler
    def handle_exception(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        
        logger.critical(
            "Uncaught exception",
            exc_info=(exc_type, exc_value, exc_traceback)
        )
        
        error_handler.handle_error(
            exc_value,
            context={
                'exception_type': exc_type.__name__,
                'traceback': ''.join(traceback.format_tb(exc_traceback))
            }
        )
    
    import sys
    sys.excepthook = handle_exception
    
    logger.info("Client error handling configured")
    return error_handler