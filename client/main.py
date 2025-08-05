"""
Main entry point for the Pacman Sync Utility Client.

This module initializes and runs the desktop client with Qt UI and system tray integration.
It also provides command-line interface for automation and WayBar integration.
"""

import os
import sys
import argparse
import logging
import json
from pathlib import Path
from typing import Optional

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def parse_arguments():
    """Parse command line arguments with comprehensive CLI support."""
    parser = argparse.ArgumentParser(
        description="Pacman Sync Utility Client",
        epilog="""
Examples:
  %(prog)s                    # Run in GUI mode with system tray
  %(prog)s --status           # Show current sync status
  %(prog)s --status --json    # Show status in JSON format (for WayBar)
  %(prog)s --sync             # Sync to latest pool state
  %(prog)s --set-latest       # Set current state as pool latest
  %(prog)s --revert           # Revert to previous state
  
  WayBar Integration:
  %(prog)s --waybar-config    # Output WayBar configuration template
  %(prog)s --waybar-daemon    # Run as WayBar daemon
  %(prog)s --waybar-click left --waybar-action sync  # Handle WayBar click
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    # Operation modes (mutually exclusive)
    operation_group = parser.add_mutually_exclusive_group()
    operation_group.add_argument("--sync", action="store_true", 
                                help="Sync to latest pool state and exit")
    operation_group.add_argument("--set-latest", action="store_true",
                                help="Set current state as pool latest and exit")
    operation_group.add_argument("--revert", action="store_true",
                                help="Revert to previous state and exit")
    operation_group.add_argument("--status", action="store_true",
                                help="Show current sync status and exit")
    
    # Configuration options
    config_group = parser.add_argument_group('Configuration')
    config_group.add_argument("--config", type=str, metavar="FILE",
                             help="Path to configuration file")
    config_group.add_argument("--server-url", type=str, metavar="URL",
                             help="Override server URL")
    config_group.add_argument("--endpoint-name", type=str, metavar="NAME",
                             help="Override endpoint name")
    config_group.add_argument("--pool-id", type=str, metavar="ID",
                             help="Override pool ID")
    
    # Output format options
    output_group = parser.add_argument_group('Output')
    output_group.add_argument("--json", action="store_true",
                             help="Output status in JSON format (for WayBar)")
    output_group.add_argument("--verbose", "-v", action="store_true",
                             help="Enable verbose output")
    output_group.add_argument("--quiet", "-q", action="store_true",
                             help="Suppress non-error output")
    
    # WayBar integration options
    waybar_group = parser.add_argument_group('WayBar Integration')
    waybar_group.add_argument("--waybar-click", type=str, metavar="BUTTON",
                             choices=["left", "right", "middle", "scroll_up", "scroll_down"],
                             help="Handle WayBar click action")
    waybar_group.add_argument("--waybar-action", type=str, metavar="ACTION",
                             choices=["sync", "set_latest", "revert", "show_status", "show_menu", "refresh"],
                             help="Specific action to perform for WayBar click")
    waybar_group.add_argument("--waybar-daemon", action="store_true",
                             help="Run as WayBar daemon with continuous status updates")
    waybar_group.add_argument("--waybar-config", action="store_true",
                             help="Output WayBar configuration template")
    
    # Advanced options
    advanced_group = parser.add_argument_group('Advanced')
    advanced_group.add_argument("--timeout", type=int, metavar="SECONDS",
                               help="Operation timeout in seconds (default: 60)")
    advanced_group.add_argument("--force", action="store_true",
                               help="Force operation even if status is stale")
    advanced_group.add_argument("--no-persist", action="store_true",
                               help="Don't update persistent status")
    
    # Debug options
    debug_group = parser.add_argument_group('Debug')
    debug_group.add_argument("--debug", action="store_true",
                            help="Enable debug logging")
    debug_group.add_argument("--log-file", type=str, metavar="FILE",
                            help="Log to file instead of console")
    
    args = parser.parse_args()
    
    # Validate argument combinations
    if args.quiet and args.verbose:
        parser.error("--quiet and --verbose are mutually exclusive")
    
    if args.json and not (args.status or args.waybar_click):
        parser.error("--json can only be used with --status or --waybar-click")
    
    if args.waybar_action and not args.waybar_click:
        parser.error("--waybar-action requires --waybar-click")
    
    # WayBar operations are mutually exclusive with other operations
    waybar_ops = [args.waybar_click, args.waybar_daemon, args.waybar_config]
    regular_ops = [args.sync, args.set_latest, args.revert, args.status]
    
    if any(waybar_ops) and any(regular_ops):
        parser.error("WayBar operations cannot be combined with regular operations")
    
    return args


def run_cli_mode(args):
    """Run in command-line mode for single operations with status persistence."""
    if not args.quiet:
        logger.info("Running in CLI mode")
    
    try:
        # Import status persistence first (doesn't require heavy dependencies)
        from client.status_persistence import StatusPersistenceManager
        
        # Initialize status persistence
        status_manager = StatusPersistenceManager()
        
        # Handle status command first (can work offline without dependencies)
        if args.status:
            return handle_status_command(args, status_manager)
        
        # For other operations, import required modules
        from client.config import ClientConfiguration
        from client.sync_manager import SyncManager
        from client.qt.application import SyncStatus
        import asyncio
        
        # Load configuration
        config = ClientConfiguration(args.config)
        
        # Override configuration with command line arguments
        if args.server_url:
            config.set_override('server_url', args.server_url)
        if args.endpoint_name:
            config.set_override('endpoint_name', args.endpoint_name)
        if args.pool_id:
            config.set_override('pool_id', args.pool_id)
        
        # Set timeout if specified
        timeout = args.timeout or 60
        
        # Create a minimal Qt application for CLI mode
        from PyQt6.QtWidgets import QApplication
        from PyQt6.QtCore import QTimer, QEventLoop
        
        app = QApplication([])
        
        # Initialize sync manager
        sync_manager = SyncManager(config)
        
        # Set up event loop for async operations
        loop = QEventLoop()
        result = [1]  # Default to error
        operation_started = [False]
        
        def on_operation_completed(operation_type: str, success: bool, message: str):
            """Handle completed operations with status persistence."""
            if not args.quiet:
                if success:
                    print(f"✓ {message}")
                else:
                    print(f"✗ {message}", file=sys.stderr)
            
            # Update persistent status
            if not args.no_persist:
                operation_name = {
                    'execute_sync_to_latest': 'sync',
                    'execute_set_as_latest': 'set_latest', 
                    'execute_revert_to_previous': 'revert',
                    'sync_operation': 'sync',
                    'authenticate': 'authenticate'
                }.get(operation_type, operation_type)
                
                status_manager.update_operation_result(operation_name, success, message)
                
                # Update status based on operation result
                if success and operation_type.startswith('execute_'):
                    status_manager.update_status(SyncStatus.IN_SYNC)
                elif not success:
                    status_manager.update_status(SyncStatus.ERROR)
            
            result[0] = 0 if success else 1
            loop.quit()
        
        def on_authentication_changed(is_authenticated: bool):
            """Handle authentication state changes."""
            if is_authenticated:
                # Update persistent authentication status
                if not args.no_persist:
                    endpoint_info = sync_manager._api_client.get_endpoint_info()
                    status_manager.update_authentication(
                        is_authenticated=True,
                        endpoint_id=endpoint_info.get('endpoint_id') if endpoint_info else None,
                        endpoint_name=endpoint_info.get('endpoint_name') if endpoint_info else None,
                        server_url=config.get_server_url()
                    )
                
                # Authentication successful, proceed with operation
                if args.sync:
                    if not args.quiet:
                        print("Syncing to latest pool state...")
                    sync_manager.sync_to_latest()
                    operation_started[0] = True
                elif args.set_latest:
                    if not args.quiet:
                        print("Setting current state as latest...")
                    sync_manager.set_as_latest()
                    operation_started[0] = True
                elif args.revert:
                    if not args.quiet:
                        print("Reverting to previous state...")
                    sync_manager.revert_to_previous()
                    operation_started[0] = True
            else:
                # Update persistent authentication status
                if not args.no_persist:
                    status_manager.update_authentication(is_authenticated=False)
                    status_manager.update_status(SyncStatus.OFFLINE)
                
                if not args.quiet:
                    print("Authentication failed", file=sys.stderr)
                result[0] = 2  # Authentication error
                loop.quit()
        
        def on_status_changed(status: SyncStatus):
            """Handle status changes."""
            if not args.no_persist:
                status_manager.update_status(status)
        
        def on_error_occurred(error_message: str):
            """Handle errors."""
            if not args.quiet:
                print(f"Error: {error_message}", file=sys.stderr)
            
            if not args.no_persist:
                status_manager.update_status(SyncStatus.ERROR)
            
            result[0] = 3  # General error
            loop.quit()
        
        # Connect signals
        sync_manager.operation_completed.connect(on_operation_completed)
        sync_manager.authentication_changed.connect(on_authentication_changed)
        sync_manager.status_changed.connect(on_status_changed)
        sync_manager.error_occurred.connect(on_error_occurred)
        
        # Set timeout for CLI operations
        timeout_timer = QTimer()
        timeout_timer.setSingleShot(True)
        def on_timeout():
            if not args.quiet:
                print(f"Operation timed out after {timeout} seconds", file=sys.stderr)
            if not operation_started[0]:
                result[0] = 4  # Timeout during authentication
            else:
                result[0] = 5  # Timeout during operation
            loop.quit()
        
        timeout_timer.timeout.connect(on_timeout)
        timeout_timer.start(timeout * 1000)  # Convert to milliseconds
        
        # Start sync manager
        sync_manager.start()
        
        # Run event loop
        loop.exec()
        
        # Cleanup
        sync_manager.stop()
        
        return result[0]
        
    except ImportError as e:
        logger.error(f"Required dependencies not available: {e}")
        if not args.quiet:
            print("Error: Required dependencies are not installed.", file=sys.stderr)
            print("Please install PyQt6 and aiohttp: pip install PyQt6 aiohttp", file=sys.stderr)
        return 6  # Dependency error
    except KeyboardInterrupt:
        if not args.quiet:
            print("\nOperation cancelled by user", file=sys.stderr)
        return 130  # Standard exit code for SIGINT
    except Exception as e:
        logger.error(f"CLI mode error: {e}")
        if not args.quiet:
            print(f"Error: {str(e)}", file=sys.stderr)
        return 7  # General error


def handle_status_command(args, status_manager: 'StatusPersistenceManager') -> int:
    """
    Handle the --status command with support for JSON output and offline operation.
    
    Args:
        args: Parsed command line arguments
        status_manager: Status persistence manager
        
    Returns:
        Exit code (0 for success, non-zero for error)
    """
    try:
        if args.json:
            # Suppress logging for JSON output to avoid contaminating the output
            logging.getLogger().setLevel(logging.CRITICAL)
            
            # Use WayBar integration for JSON output
            from client.waybar_integration import WayBarIntegration
            
            waybar = WayBarIntegration()
            status_json = waybar.get_waybar_status(include_detailed_tooltip=args.verbose)
            print(json.dumps(status_json))
            return 0
        
        # Import SyncStatus enum - define locally if import fails
        try:
            from client.qt.application import SyncStatus
        except ImportError:
            # Define SyncStatus locally if Qt is not available
            from enum import Enum
            class SyncStatus(Enum):
                IN_SYNC = "in_sync"
                AHEAD = "ahead"
                BEHIND = "behind"
                OFFLINE = "offline"
                SYNCING = "syncing"
                ERROR = "error"
        
        # Load persisted status
        status_info = status_manager.load_status()
        
        if status_info is None:
            if not args.quiet:
                print("Status: Unknown (no status information available)")
            return 8  # No status available
        
        # Check if status is stale
        is_fresh = status_manager.is_status_fresh(max_age_seconds=300)  # 5 minutes
        
        # Human-readable format
        summary = status_manager.get_status_summary()
        
        if args.verbose:
            # Detailed status output
            print(f"Status: {summary['status'].upper()}")
            print(f"Endpoint: {summary['endpoint_name']}")
            print(f"Server: {summary['server_url']}")
            print(f"Authenticated: {'Yes' if summary['is_authenticated'] else 'No'}")
            print(f"Last Updated: {summary['last_updated']}")
            
            if summary['last_operation']:
                print(f"Last Operation: {summary['last_operation']}")
            if summary['operation_result']:
                print(f"Result: {summary['operation_result']}")
            if summary['packages_count']:
                print(f"Packages: {summary['packages_count']}")
            if summary['last_sync_time']:
                print(f"Last Sync: {summary['last_sync_time']}")
            
            if not is_fresh:
                print("⚠ Status information may be outdated")
        else:
            # Simple status output
            status_text = summary['status'].upper()
            if not is_fresh:
                status_text += " (stale)"
            print(f"Status: {status_text}")
        
        return 0
        
    except Exception as e:
        logger.error(f"Status command error: {e}")
        if not args.quiet:
            print(f"Error retrieving status: {str(e)}", file=sys.stderr)
        return 9  # Status retrieval error


def run_gui_mode(args):
    """Run in GUI mode with system tray integration and status persistence."""
    logger.info("Starting GUI mode with system tray integration")
    
    try:
        # Import Qt components
        from client.qt.application import PacmanSyncApplication, SyncStatus
        from client.config import ClientConfiguration
        from client.sync_manager import SyncManager
        from client.status_persistence import StatusPersistenceManager
        
        # Initialize status persistence
        status_manager = StatusPersistenceManager()
        
        # Load configuration
        config = ClientConfiguration(args.config)
        
        # Override configuration with command line arguments
        if args.server_url:
            config.set_override('server_url', args.server_url)
        if args.endpoint_name:
            config.set_override('endpoint_name', args.endpoint_name)
        if args.pool_id:
            config.set_override('pool_id', args.pool_id)
        
        # Initialize Qt application
        app = PacmanSyncApplication(sys.argv)
        
        # Check if system tray is available
        if not app.is_system_tray_available():
            logger.error("System tray is not available. Cannot run in GUI mode.")
            if not args.quiet:
                print("Error: System tray is not available on this system.")
                print("Please run in command-line mode using --status, --sync, etc.")
            return 1
        
        # Initialize sync manager
        sync_manager = SyncManager(config)
        
        # Connect sync manager signals to Qt application and status persistence
        def on_status_changed(status: SyncStatus):
            app.update_sync_status(status)
            # Update persistent status
            status_manager.update_status(status)
        
        def on_authentication_changed(is_authenticated: bool):
            # Update persistent authentication status
            endpoint_info = sync_manager._api_client.get_endpoint_info()
            status_manager.update_authentication(
                is_authenticated=is_authenticated,
                endpoint_id=endpoint_info.get('endpoint_id') if endpoint_info else None,
                endpoint_name=endpoint_info.get('endpoint_name') if endpoint_info else None,
                server_url=config.get_server_url()
            )
            
            if is_authenticated:
                logger.info("Successfully authenticated with server")
                app.show_notification("Connected", "Successfully connected to sync server")
            else:
                logger.warning("Authentication failed or lost")
                app.show_notification("Disconnected", "Lost connection to sync server", is_error=True)
        
        def on_operation_completed(operation_type: str, success: bool, message: str):
            # Update persistent operation result
            operation_name = {
                'execute_sync_to_latest': 'sync',
                'execute_set_as_latest': 'set_latest',
                'execute_revert_to_previous': 'revert',
                'sync_operation': 'sync'
            }.get(operation_type, operation_type)
            
            status_manager.update_operation_result(operation_name, success, message)
            
            if operation_type in ['execute_sync_to_latest', 'execute_set_as_latest', 'execute_revert_to_previous']:
                if success:
                    app.show_notification("Operation Complete", message)
                    # Status will be updated by periodic status checks
                else:
                    app.show_notification("Operation Failed", message, is_error=True)
                    app.update_sync_status(SyncStatus.ERROR)
        
        def on_error_occurred(error_message: str):
            logger.error(f"Sync manager error: {error_message}")
            app.show_notification("Error", error_message, is_error=True)
            status_manager.update_status(SyncStatus.ERROR)
        
        # Connect signals
        sync_manager.status_changed.connect(on_status_changed)
        sync_manager.authentication_changed.connect(on_authentication_changed)
        sync_manager.operation_completed.connect(on_operation_completed)
        sync_manager.error_occurred.connect(on_error_occurred)
        
        # Set up operation callbacks
        def handle_sync():
            logger.info("Sync operation requested from tray")
            sync_manager.sync_to_latest()
        
        def handle_set_latest():
            logger.info("Set latest operation requested from tray")
            sync_manager.set_as_latest()
        
        def handle_revert():
            logger.info("Revert operation requested from tray")
            sync_manager.revert_to_previous()
        
        def handle_status_update():
            logger.debug("Periodic status update requested")
            sync_manager.force_status_update()
        
        # Register callbacks with Qt application
        app.set_sync_callback(handle_sync)
        app.set_set_latest_callback(handle_set_latest)
        app.set_revert_callback(handle_revert)
        app.set_status_update_callback(handle_status_update)
        
        # Load initial status from persistence or set default
        persisted_status = status_manager.load_status()
        if persisted_status and status_manager.is_status_fresh():
            app.update_sync_status(persisted_status.status)
        else:
            app.update_sync_status(SyncStatus.OFFLINE)
        
        # Start sync manager
        sync_manager.start()
        
        logger.info("Qt application initialized successfully")
        if not args.quiet:
            print("Pacman Sync Utility client started with system tray integration")
            print("Check your system tray for the sync status icon")
            print("Right-click the icon for sync options, or press Ctrl+C to quit")
        
        try:
            # Start Qt event loop
            result = app.exec()
        finally:
            # Cleanup sync manager
            sync_manager.stop()
        
        return result
        
    except ImportError as e:
        logger.error(f"Qt dependencies not available: {e}")
        if not args.quiet:
            print("Error: Qt dependencies are not installed.")
            print("Please install PyQt6 and aiohttp: pip install PyQt6 aiohttp")
        return 6  # Dependency error
    except KeyboardInterrupt:
        logger.info("Client shutdown requested")
        return 0
    except Exception as e:
        logger.error(f"Client error: {e}")
        if not args.quiet:
            print(f"Error: {str(e)}")
        return 1


def configure_logging(args):
    """Configure logging based on command line arguments."""
    # Determine log level
    if args.debug:
        log_level = logging.DEBUG
    elif args.verbose:
        log_level = logging.INFO
    elif args.quiet or args.json:  # Quiet logging for JSON output
        log_level = logging.ERROR
    else:
        log_level = logging.WARNING
    
    # Configure logging format
    if args.debug:
        log_format = '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
    else:
        log_format = '%(asctime)s - %(levelname)s - %(message)s'
    
    # Configure logging output
    if args.log_file:
        logging.basicConfig(
            level=log_level,
            format=log_format,
            filename=args.log_file,
            filemode='a'
        )
    else:
        logging.basicConfig(
            level=log_level,
            format=log_format
        )
    
    # Suppress Qt logging unless in debug mode
    if not args.debug:
        logging.getLogger('PyQt6').setLevel(logging.WARNING)


def print_exit_code_help():
    """Print information about exit codes."""
    print("""
Exit Codes:
  0   - Success
  1   - Operation failed
  2   - Authentication failed
  3   - General error
  4   - Timeout during authentication
  5   - Timeout during operation
  6   - Missing dependencies
  7   - Unexpected error
  8   - No status information available
  9   - Status retrieval error
  130 - Cancelled by user (Ctrl+C)
    """)


def handle_waybar_operations(args) -> int:
    """
    Handle WayBar-specific operations.
    
    Args:
        args: Parsed command line arguments
        
    Returns:
        Exit code (0 for success, non-zero for error)
    """
    try:
        # Suppress logging for JSON output to avoid contaminating the output
        if args.json:
            logging.getLogger().setLevel(logging.CRITICAL)
        
        from client.waybar_integration import WayBarIntegration
        
        waybar = WayBarIntegration()
        
        if args.waybar_config:
            # Output WayBar configuration template
            config = waybar.get_waybar_config_template()
            print(json.dumps(config, indent=2))
            return 0
        
        elif args.waybar_daemon:
            # Run as WayBar daemon
            update_interval = getattr(args, 'waybar_interval', 5)
            waybar.start_waybar_daemon(update_interval)
            return 0
        
        elif args.waybar_click:
            # Handle click action
            result = waybar.handle_click_action(args.waybar_click, args.waybar_action)
            
            # Output updated status for WayBar
            if args.json:
                print(json.dumps(result["status"]))
            elif not args.quiet:
                if result["result"]["success"]:
                    print(f"Action completed: {result['result']['message']}")
                else:
                    print(f"Action failed: {result['result']['message']}", file=sys.stderr)
            
            return 0 if result["result"]["success"] else 1
        
        else:
            if not args.quiet:
                print("Error: No WayBar operation specified", file=sys.stderr)
            return 1
            
    except ImportError as e:
        if not args.quiet:
            print("Error: WayBar integration dependencies not available", file=sys.stderr)
        return 6
    except Exception as e:
        if not args.quiet:
            print(f"Error: {str(e)}", file=sys.stderr)
        return 1


def main():
    """Main entry point for the client."""
    try:
        args = parse_arguments()
        
        # Suppress logging for JSON output early to avoid contaminating output
        if args.json:
            logging.getLogger().setLevel(logging.CRITICAL)
        
        # Configure logging based on arguments
        configure_logging(args)
        
        # Handle WayBar operations first
        waybar_operations = [args.waybar_click, args.waybar_daemon, args.waybar_config]
        if any(waybar_operations):
            return handle_waybar_operations(args)
        
        # Determine run mode for regular operations
        cli_operations = [args.sync, args.set_latest, args.revert, args.status]
        is_cli_mode = any(cli_operations)
        
        if is_cli_mode:
            return run_cli_mode(args)
        else:
            return run_gui_mode(args)
            
    except KeyboardInterrupt:
        print("\nInterrupted by user", file=sys.stderr)
        return 130
    except Exception as e:
        print(f"Fatal error: {str(e)}", file=sys.stderr)
        if not getattr(args, 'json', False):
            logger.exception("Fatal error in main")
        return 1


if __name__ == "__main__":
    sys.exit(main())