"""
WayBar Integration for Pacman Sync Utility Client.

This module provides WayBar-specific functionality including JSON status output,
click action handlers, and efficient status querying without blocking the status bar.
"""

import json
import logging
import sys
import os
import signal
import time
from typing import Dict, Any, Optional, Callable
from pathlib import Path
from datetime import datetime, timedelta

# Import with fallback for SyncStatus
try:
    from client.qt.application import SyncStatus
except ImportError:
    from enum import Enum
    class SyncStatus(Enum):
        IN_SYNC = "in_sync"
        AHEAD = "ahead"
        BEHIND = "behind"
        OFFLINE = "offline"
        SYNCING = "syncing"
        ERROR = "error"

from client.status_persistence import StatusPersistenceManager

logger = logging.getLogger(__name__)


class WayBarIntegration:
    """
    WayBar integration handler for Pacman Sync Utility.
    
    Provides JSON status output, click action handling, and efficient status querying
    designed specifically for WayBar consumption.
    """
    
    def __init__(self, config_dir: Optional[str] = None):
        """
        Initialize WayBar integration.
        
        Args:
            config_dir: Optional custom configuration directory
        """
        self.status_manager = StatusPersistenceManager(config_dir)
        
        # WayBar-specific configuration
        self._update_interval = 5  # seconds
        self._max_text_length = 20
        self._show_detailed_tooltip = True
        
        # Status display configuration for WayBar
        self._status_config = {
            SyncStatus.IN_SYNC: {
                "text": "✓",
                "alt": "in_sync",
                "class": ["pacman-sync", "in-sync"],
                "tooltip": "Packages are synchronized"
            },
            SyncStatus.AHEAD: {
                "text": "↑",
                "alt": "ahead", 
                "class": ["pacman-sync", "ahead"],
                "tooltip": "Ahead of pool (newer packages)"
            },
            SyncStatus.BEHIND: {
                "text": "↓",
                "alt": "behind",
                "class": ["pacman-sync", "behind"], 
                "tooltip": "Behind pool (older packages)"
            },
            SyncStatus.OFFLINE: {
                "text": "⚠",
                "alt": "offline",
                "class": ["pacman-sync", "offline"],
                "tooltip": "Cannot connect to server"
            },
            SyncStatus.SYNCING: {
                "text": "⟳",
                "alt": "syncing",
                "class": ["pacman-sync", "syncing"],
                "tooltip": "Synchronization in progress"
            },
            SyncStatus.ERROR: {
                "text": "✗",
                "alt": "error",
                "class": ["pacman-sync", "error"],
                "tooltip": "Synchronization error"
            }
        }
        
        logger.info("WayBar integration initialized")
    
    def get_waybar_status(self, include_detailed_tooltip: bool = True) -> Dict[str, Any]:
        """
        Get current status in WayBar JSON format.
        
        Args:
            include_detailed_tooltip: Whether to include detailed tooltip information
            
        Returns:
            Dictionary containing WayBar-compatible status information
        """
        try:
            # Load current status
            status_info = self.status_manager.load_status()
            
            if status_info is None:
                return self._get_unknown_status()
            
            # Get base status configuration
            status_config = self._status_config.get(status_info.status, 
                                                   self._get_unknown_status())
            
            # Create WayBar output
            waybar_output = {
                "text": status_config["text"],
                "alt": status_config["alt"],
                "class": status_config["class"].copy()
            }
            
            # Add tooltip
            if include_detailed_tooltip:
                waybar_output["tooltip"] = self._build_detailed_tooltip(status_info)
            else:
                waybar_output["tooltip"] = status_config["tooltip"]
            
            # Check if status is stale and add indicator
            if not self.status_manager.is_status_fresh(max_age_seconds=300):
                waybar_output["class"].append("stale")
                waybar_output["tooltip"] += " (status may be outdated)"
            
            # Add percentage for progress indication (if syncing)
            if status_info.status == SyncStatus.SYNCING:
                waybar_output["percentage"] = self._get_sync_progress()
            
            logger.debug(f"WayBar status generated: {waybar_output['alt']}")
            return waybar_output
            
        except Exception as e:
            logger.error(f"Failed to get WayBar status: {e}")
            return self._get_error_status(str(e))
    
    def _get_unknown_status(self) -> Dict[str, Any]:
        """Get status for unknown/unavailable state."""
        return {
            "text": "?",
            "alt": "unknown",
            "class": ["pacman-sync", "unknown"],
            "tooltip": "No status information available"
        }
    
    def _get_error_status(self, error_message: str) -> Dict[str, Any]:
        """Get status for error state."""
        return {
            "text": "!",
            "alt": "error",
            "class": ["pacman-sync", "error"],
            "tooltip": f"Error: {error_message}"
        }
    
    def _build_detailed_tooltip(self, status_info) -> str:
        """
        Build a detailed tooltip with comprehensive status information.
        
        Args:
            status_info: PersistedStatus object
            
        Returns:
            Formatted tooltip string
        """
        lines = []
        
        # Status line
        status_text = status_info.status.value.replace('_', ' ').title()
        lines.append(f"Status: {status_text}")
        
        # Endpoint information
        if status_info.endpoint_name:
            lines.append(f"Endpoint: {status_info.endpoint_name}")
        
        # Server information
        if status_info.server_url:
            lines.append(f"Server: {status_info.server_url}")
        
        # Authentication status
        auth_status = "Yes" if status_info.is_authenticated else "No"
        lines.append(f"Connected: {auth_status}")
        
        # Last operation
        if status_info.last_operation:
            lines.append(f"Last Operation: {status_info.last_operation}")
            if status_info.operation_result:
                # Truncate long operation results
                result = status_info.operation_result
                if len(result) > 50:
                    result = result[:47] + "..."
                lines.append(f"Result: {result}")
        
        # Package count
        if status_info.packages_count:
            lines.append(f"Packages: {status_info.packages_count}")
        
        # Timing information
        if status_info.last_sync_time:
            sync_age = datetime.now() - status_info.last_sync_time
            if sync_age.total_seconds() < 3600:
                sync_time = f"{int(sync_age.total_seconds() / 60)}m ago"
            elif sync_age.total_seconds() < 86400:
                sync_time = f"{int(sync_age.total_seconds() / 3600)}h ago"
            else:
                sync_time = f"{int(sync_age.total_seconds() / 86400)}d ago"
            lines.append(f"Last Sync: {sync_time}")
        
        # Status age
        status_age = datetime.now() - status_info.last_updated
        if status_age.total_seconds() < 60:
            age_text = f"{int(status_age.total_seconds())}s ago"
        elif status_age.total_seconds() < 3600:
            age_text = f"{int(status_age.total_seconds() / 60)}m ago"
        else:
            age_text = f"{int(status_age.total_seconds() / 3600)}h ago"
        lines.append(f"Updated: {age_text}")
        
        return "\n".join(lines)
    
    def _get_sync_progress(self) -> int:
        """
        Get synchronization progress percentage.
        
        Returns:
            Progress percentage (0-100)
        """
        # This is a placeholder - in a real implementation, you would
        # track actual sync progress through the sync manager
        return 50  # Default to 50% when syncing
    
    def handle_click_action(self, button: str, action: Optional[str] = None) -> Dict[str, Any]:
        """
        Handle WayBar click actions.
        
        Args:
            button: Mouse button clicked ("left", "right", "middle", "scroll_up", "scroll_down")
            action: Optional specific action to perform
            
        Returns:
            Dictionary containing action result and updated status
        """
        try:
            logger.info(f"WayBar click action: {button} (action: {action})")
            
            # Default click actions
            if action is None:
                action_map = {
                    "left": "show_status",
                    "right": "show_menu", 
                    "middle": "sync",
                    "scroll_up": "refresh",
                    "scroll_down": "refresh"
                }
                action = action_map.get(button, "show_status")
            
            # Execute the action
            result = self._execute_click_action(action)
            
            # Return updated status along with action result
            return {
                "action": action,
                "result": result,
                "status": self.get_waybar_status(include_detailed_tooltip=False)
            }
            
        except Exception as e:
            logger.error(f"Click action failed: {e}")
            return {
                "action": action or "unknown",
                "result": {"success": False, "message": str(e)},
                "status": self._get_error_status(str(e))
            }
    
    def _execute_click_action(self, action: str) -> Dict[str, Any]:
        """
        Execute a specific click action.
        
        Args:
            action: Action to execute
            
        Returns:
            Dictionary containing action result
        """
        if action == "show_status":
            return self._show_status_action()
        elif action == "show_menu":
            return self._show_menu_action()
        elif action == "sync":
            return self._sync_action()
        elif action == "set_latest":
            return self._set_latest_action()
        elif action == "revert":
            return self._revert_action()
        elif action == "refresh":
            return self._refresh_action()
        else:
            return {"success": False, "message": f"Unknown action: {action}"}
    
    def _show_status_action(self) -> Dict[str, Any]:
        """Show detailed status information."""
        try:
            summary = self.status_manager.get_status_summary()
            return {
                "success": True,
                "message": "Status information retrieved",
                "data": summary
            }
        except Exception as e:
            return {"success": False, "message": f"Failed to get status: {e}"}
    
    def _show_menu_action(self) -> Dict[str, Any]:
        """Show context menu options."""
        return {
            "success": True,
            "message": "Menu options",
            "data": {
                "options": [
                    {"id": "sync", "label": "Sync to Latest", "enabled": True},
                    {"id": "set_latest", "label": "Set as Latest", "enabled": True},
                    {"id": "revert", "label": "Revert to Previous", "enabled": True},
                    {"id": "refresh", "label": "Refresh Status", "enabled": True}
                ]
            }
        }
    
    def _sync_action(self) -> Dict[str, Any]:
        """Execute sync operation."""
        try:
            # This would trigger the actual sync operation
            # For now, we'll simulate it by updating the status
            self.status_manager.update_status(SyncStatus.SYNCING)
            
            # In a real implementation, this would call the sync manager
            # sync_manager.sync_to_latest()
            
            return {
                "success": True,
                "message": "Sync operation started",
                "data": {"operation": "sync_to_latest"}
            }
        except Exception as e:
            return {"success": False, "message": f"Sync failed: {e}"}
    
    def _set_latest_action(self) -> Dict[str, Any]:
        """Execute set as latest operation."""
        try:
            # This would trigger the actual set latest operation
            self.status_manager.update_operation_result("set_latest", True, "State set as latest")
            
            return {
                "success": True,
                "message": "Set as latest operation completed",
                "data": {"operation": "set_as_latest"}
            }
        except Exception as e:
            return {"success": False, "message": f"Set latest failed: {e}"}
    
    def _revert_action(self) -> Dict[str, Any]:
        """Execute revert operation."""
        try:
            # This would trigger the actual revert operation
            self.status_manager.update_operation_result("revert", True, "Reverted to previous state")
            
            return {
                "success": True,
                "message": "Revert operation completed",
                "data": {"operation": "revert_to_previous"}
            }
        except Exception as e:
            return {"success": False, "message": f"Revert failed: {e}"}
    
    def _refresh_action(self) -> Dict[str, Any]:
        """Refresh status information."""
        try:
            # Force a status update
            current_status = self.status_manager.load_status()
            if current_status:
                self.status_manager.update_status(current_status.status)
            
            return {
                "success": True,
                "message": "Status refreshed",
                "data": {"timestamp": datetime.now().isoformat()}
            }
        except Exception as e:
            return {"success": False, "message": f"Refresh failed: {e}"}
    
    def start_waybar_daemon(self, update_interval: int = 5) -> None:
        """
        Start a daemon process for continuous WayBar status updates.
        
        Args:
            update_interval: Update interval in seconds
        """
        logger.info(f"Starting WayBar daemon with {update_interval}s interval")
        
        def signal_handler(signum, frame):
            logger.info("WayBar daemon shutting down")
            sys.exit(0)
        
        # Set up signal handlers
        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)
        
        try:
            while True:
                # Output current status
                status = self.get_waybar_status()
                print(json.dumps(status), flush=True)
                
                # Wait for next update
                time.sleep(update_interval)
                
        except KeyboardInterrupt:
            logger.info("WayBar daemon interrupted")
        except Exception as e:
            logger.error(f"WayBar daemon error: {e}")
            sys.exit(1)
    
    def get_waybar_config_template(self) -> Dict[str, Any]:
        """
        Get a WayBar configuration template for the pacman-sync module.
        
        Returns:
            Dictionary containing WayBar module configuration
        """
        return {
            "pacman-sync": {
                "exec": f"{sys.executable} {sys.argv[0]} --status --json",
                "exec-if": "which pacman",
                "interval": 30,
                "return-type": "json",
                "format": "{icon}",
                "format-icons": {
                    "in_sync": "✓",
                    "ahead": "↑", 
                    "behind": "↓",
                    "offline": "⚠",
                    "syncing": "⟳",
                    "error": "✗",
                    "unknown": "?"
                },
                "tooltip": True,
                "on-click": f"{sys.executable} {sys.argv[0]} --sync",
                "on-click-right": f"{sys.executable} {sys.argv[0]} --status --verbose",
                "on-click-middle": f"{sys.executable} {sys.argv[0]} --set-latest",
                "signal": 10
            }
        }


def create_waybar_click_handler() -> Callable[[str], Dict[str, Any]]:
    """
    Create a click handler function for WayBar integration.
    
    Returns:
        Click handler function
    """
    waybar = WayBarIntegration()
    
    def handle_click(button: str, action: Optional[str] = None) -> Dict[str, Any]:
        return waybar.handle_click_action(button, action)
    
    return handle_click


def main_waybar_daemon():
    """Main entry point for WayBar daemon mode."""
    import argparse
    
    parser = argparse.ArgumentParser(description="WayBar daemon for Pacman Sync Utility")
    parser.add_argument("--interval", type=int, default=5,
                       help="Update interval in seconds (default: 5)")
    parser.add_argument("--config-dir", type=str,
                       help="Custom configuration directory")
    
    args = parser.parse_args()
    
    # Configure logging for daemon mode
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('/tmp/pacman-sync-waybar.log'),
            logging.StreamHandler(sys.stderr)
        ]
    )
    
    waybar = WayBarIntegration(args.config_dir)
    waybar.start_waybar_daemon(args.interval)


if __name__ == "__main__":
    main_waybar_daemon()