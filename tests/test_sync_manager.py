#!/usr/bin/env python3
"""
Test script for the sync manager integration.

This script tests the sync manager functionality including Qt integration,
authentication handling, and operation management.
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


def test_sync_manager():
    """Test the sync manager functionality."""
    
    try:
        from PyQt6.QtWidgets import QApplication
        from PyQt6.QtCore import QTimer, QEventLoop
        from client.config import ClientConfiguration
        from client.sync_manager import SyncManager
        from client.qt.application import SyncStatus
        
        logger.info("Testing sync manager integration...")
        
        # Create Qt application
        app = QApplication([])
        
        # Load configuration
        config = ClientConfiguration()
        logger.info(f"Using server URL: {config.get_server_url()}")
        
        # Initialize sync manager
        sync_manager = SyncManager(config)
        
        # Track events
        events = []
        
        def on_status_changed(status):
            events.append(f"status_changed: {status.value}")
            logger.info(f"Status changed to: {status.value}")
        
        def on_authentication_changed(is_authenticated):
            events.append(f"authentication_changed: {is_authenticated}")
            logger.info(f"Authentication changed: {is_authenticated}")
        
        def on_operation_completed(operation_type, success, message):
            events.append(f"operation_completed: {operation_type}, {success}, {message}")
            logger.info(f"Operation completed: {operation_type} -> {success}: {message}")
        
        def on_error_occurred(error_message):
            events.append(f"error_occurred: {error_message}")
            logger.info(f"Error occurred: {error_message}")
        
        # Connect signals
        sync_manager.status_changed.connect(on_status_changed)
        sync_manager.authentication_changed.connect(on_authentication_changed)
        sync_manager.operation_completed.connect(on_operation_completed)
        sync_manager.error_occurred.connect(on_error_occurred)
        
        # Start sync manager
        sync_manager.start()
        
        # Set up test timeout
        test_timeout = QTimer()
        test_timeout.setSingleShot(True)
        test_timeout.timeout.connect(app.quit)
        test_timeout.start(10000)  # 10 second timeout
        
        # Run for a short time to let authentication attempt complete
        logger.info("Running sync manager for 10 seconds...")
        app.exec()
        
        # Stop sync manager
        sync_manager.stop()
        
        # Check results
        logger.info("Events captured:")
        for event in events:
            logger.info(f"  - {event}")
        
        # Verify we got some events
        if events:
            logger.info("Sync manager test completed successfully!")
            return True
        else:
            logger.warning("No events were captured")
            return False
            
    except ImportError as e:
        logger.error(f"Required dependencies not available: {e}")
        logger.info("Please install PyQt6: pip install PyQt6")
        return False
    except Exception as e:
        logger.error(f"Sync manager test error: {e}")
        return False


def test_configuration_integration():
    """Test configuration integration."""
    
    try:
        from client.config import ClientConfiguration
        
        logger.info("Testing configuration integration...")
        
        # Test configuration loading
        config = ClientConfiguration()
        
        # Test all the methods used by sync manager
        server_url = config.get_server_url()
        endpoint_name = config.get_endpoint_name()
        timeout = config.get_server_timeout()
        retry_attempts = config.get_retry_attempts()
        retry_delay = config.get_retry_delay()
        update_interval = config.get_update_interval()
        
        logger.info(f"Server URL: {server_url}")
        logger.info(f"Endpoint name: {endpoint_name}")
        logger.info(f"Timeout: {timeout}")
        logger.info(f"Retry attempts: {retry_attempts}")
        logger.info(f"Retry delay: {retry_delay}")
        logger.info(f"Update interval: {update_interval}")
        
        # Test configuration overrides
        config.set_override('server_url', 'http://test:8080')
        overridden_url = config.get_server_url()
        logger.info(f"Overridden URL: {overridden_url}")
        
        logger.info("Configuration integration test completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"Configuration integration test error: {e}")
        return False


def main():
    """Main test function."""
    logger.info("Starting sync manager integration tests...")
    
    try:
        # Test configuration integration
        config_success = test_configuration_integration()
        
        # Test sync manager
        sync_success = test_sync_manager()
        
        if config_success and sync_success:
            logger.info("All integration tests completed successfully!")
            return 0
        else:
            logger.error("Some integration tests failed")
            return 1
            
    except KeyboardInterrupt:
        logger.info("Tests interrupted by user")
        return 0
    except Exception as e:
        logger.error(f"Integration test error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())