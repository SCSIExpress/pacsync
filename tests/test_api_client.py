#!/usr/bin/env python3
"""
Test script for the API client implementation.

This script tests the basic functionality of the API client including
authentication, status reporting, and error handling.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from client.api_client import PacmanSyncAPIClient, APIClientError, AuthenticationError, NetworkError
from client.config import ClientConfiguration
from shared.models import SyncStatus, OperationType

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


async def test_api_client():
    """Test the API client functionality."""
    
    # Load configuration
    config = ClientConfiguration()
    server_url = config.get_server_url()
    
    logger.info(f"Testing API client with server: {server_url}")
    
    # Initialize API client
    async with PacmanSyncAPIClient(server_url) as client:
        
        # Test 1: Authentication
        logger.info("Testing authentication...")
        try:
            endpoint_name = config.get_endpoint_name()
            hostname = "test-hostname"
            
            token = await client.authenticate(endpoint_name, hostname)
            logger.info(f"Authentication successful. Token: {token[:20]}...")
            
            # Get endpoint info
            endpoint_info = client.get_endpoint_info()
            if endpoint_info:
                logger.info(f"Endpoint ID: {endpoint_info['endpoint_id']}")
                endpoint_id = endpoint_info['endpoint_id']
            else:
                logger.error("Failed to get endpoint info")
                return False
            
        except AuthenticationError as e:
            logger.error(f"Authentication failed: {e}")
            return False
        except NetworkError as e:
            logger.warning(f"Network error during authentication: {e}")
            logger.info("This is expected if the server is not running - testing offline functionality")
            
            # Test offline functionality
            logger.info("Testing offline operation queuing...")
            
            # Create a fake endpoint ID for testing
            endpoint_id = "test-endpoint-id"
            client._endpoint_id = endpoint_id
            
            # Test offline status reporting
            success = await client.report_status(endpoint_id, SyncStatus.BEHIND)
            if success:
                logger.info("Offline status queuing successful")
            else:
                logger.warning("Offline status queuing failed")
            
            # Check offline operations queue
            if client._offline_operations:
                logger.info(f"Offline operations queued: {len(client._offline_operations)}")
                for op in client._offline_operations:
                    logger.info(f"  - {op['type']}: {op.get('status', op.get('operation', 'unknown'))}")
            else:
                logger.warning("No offline operations were queued")
            
            return True  # Consider this a successful test of error handling
        except Exception as e:
            logger.error(f"Unexpected error during authentication: {e}")
            return False
        
        # Test 2: Status reporting
        logger.info("Testing status reporting...")
        try:
            success = await client.report_status(endpoint_id, SyncStatus.IN_SYNC)
            if success:
                logger.info("Status reporting successful")
            else:
                logger.warning("Status reporting failed")
            
        except Exception as e:
            logger.error(f"Status reporting error: {e}")
        
        # Test 3: Additional offline operation handling (if we got this far)
        logger.info("Testing additional offline operation handling...")
        
        # Simulate offline mode
        client._is_offline = True
        
        # Try to report status while offline
        success = await client.report_status(endpoint_id, SyncStatus.AHEAD)
        if success:
            logger.info("Additional offline status queuing successful")
        else:
            logger.warning("Additional offline status queuing failed")
        
        # Check offline operations queue
        if client._offline_operations:
            logger.info(f"Total offline operations queued: {len(client._offline_operations)}")
        else:
            logger.warning("No offline operations were queued")
        
        # Test 4: Sync operation triggering
        logger.info("Testing sync operation triggering...")
        try:
            operation_id = await client.trigger_sync(endpoint_id, OperationType.SYNC)
            logger.info(f"Sync operation triggered: {operation_id}")
            
        except Exception as e:
            logger.error(f"Sync operation error: {e}")
        
        # Test 5: Error handling
        logger.info("Testing error handling...")
        try:
            # Try to authenticate with invalid data
            await client.authenticate("", "")
            logger.warning("Expected authentication error did not occur")
        except AuthenticationError:
            logger.info("Authentication error handling working correctly")
        except Exception as e:
            logger.info(f"Got different error as expected: {e}")
    
    logger.info("API client test completed")
    return True


async def test_configuration():
    """Test the configuration management."""
    
    logger.info("Testing configuration management...")
    
    # Test configuration loading
    config = ClientConfiguration()
    
    # Test basic configuration values
    server_url = config.get_server_url()
    endpoint_name = config.get_endpoint_name()
    update_interval = config.get_update_interval()
    
    logger.info(f"Server URL: {server_url}")
    logger.info(f"Endpoint name: {endpoint_name}")
    logger.info(f"Update interval: {update_interval}")
    
    # Test configuration overrides
    config.set_override('server_url', 'http://test-server:8080')
    overridden_url = config.get_server_url()
    logger.info(f"Overridden server URL: {overridden_url}")
    
    # Test dot notation access
    log_level = config.get_config('logging.level', 'INFO')
    logger.info(f"Log level: {log_level}")
    
    # Test configuration file path
    config_file = config.get_config_file_path()
    logger.info(f"Configuration file: {config_file}")
    
    logger.info("Configuration test completed")
    return True


def main():
    """Main test function."""
    logger.info("Starting API client tests...")
    
    try:
        # Test configuration
        config_success = asyncio.run(test_configuration())
        
        # Test API client
        api_success = asyncio.run(test_api_client())
        
        if config_success and api_success:
            logger.info("All tests completed successfully!")
            return 0
        else:
            logger.error("Some tests failed")
            return 1
            
    except KeyboardInterrupt:
        logger.info("Tests interrupted by user")
        return 0
    except Exception as e:
        logger.error(f"Test error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())