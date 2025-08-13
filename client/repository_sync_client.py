#!/usr/bin/env python3
"""
Repository Sync Client for Pacman Sync Utility.

This client uses the pacman-conf integration to get real repository information
from the system and submit it to the central server for analysis.
"""

import asyncio
import logging
import sys
import os
from datetime import datetime
from typing import Optional, Dict, Any
import argparse

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from client.pacman_interface import PacmanInterface
from client.api_client import PacmanSyncAPIClient
from client.config import ClientConfiguration
from shared.models import SyncStatus

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class RepositorySyncClient:
    """
    Client for synchronizing repository information with the central server.
    
    This client:
    1. Uses pacman-conf to get real repository configuration
    2. Extracts repository mirrors and metadata
    3. Submits repository information to the server
    4. Handles authentication and error recovery
    """
    
    def __init__(self, server_url: str, endpoint_name: str, hostname: Optional[str] = None):
        self.server_url = server_url
        self.endpoint_name = endpoint_name
        self.hostname = hostname or self._get_hostname()
        
        # Initialize components
        self.pacman = PacmanInterface()
        self.api_client = PacmanSyncAPIClient(server_url)
        
        # State tracking
        self.endpoint_id: Optional[str] = None
        self.is_authenticated = False
        self.last_sync_time: Optional[datetime] = None
        
        logger.info(f"Repository sync client initialized for {endpoint_name}@{self.hostname}")
    
    def _get_hostname(self) -> str:
        """Get system hostname."""
        import socket
        return socket.gethostname()
    
    async def authenticate(self) -> bool:
        """
        Authenticate with the server and get endpoint ID.
        
        Returns:
            True if authentication successful
        """
        try:
            logger.info("Authenticating with server...")
            
            # Try to authenticate (this will register if needed)
            token = await self.api_client.authenticate(self.endpoint_name, self.hostname)
            
            if token:
                # Get endpoint ID from token manager
                self.endpoint_id = self.api_client.token_manager.get_current_endpoint_id()
                self.is_authenticated = True
                
                logger.info(f"Authentication successful. Endpoint ID: {self.endpoint_id}")
                return True
            else:
                logger.error("Authentication failed - no token received")
                return False
                
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            return False
    
    async def sync_repository_info(self, force: bool = False) -> bool:
        """
        Sync repository information with the server.
        
        Args:
            force: Force sync even if recently synced
            
        Returns:
            True if sync successful
        """
        if not self.is_authenticated:
            logger.error("Not authenticated. Call authenticate() first.")
            return False
        
        # Check if we need to sync (unless forced)
        if not force and self.last_sync_time:
            time_since_sync = datetime.now() - self.last_sync_time
            if time_since_sync.total_seconds() < 300:  # 5 minutes
                logger.info("Repository info synced recently, skipping (use --force to override)")
                return True
        
        try:
            logger.info("Getting repository information from pacman...")
            
            # Get repository information using pacman-conf
            repo_info = self.pacman.get_repository_info_for_server(self.endpoint_id)
            
            if not repo_info:
                logger.warning("No repository information found")
                return False
            
            logger.info(f"Found {len(repo_info)} repositories:")
            for repo_name, info in repo_info.items():
                mirror_count = len(info.get('mirrors', []))
                primary_url = info.get('primary_url', 'none')
                logger.info(f"  {repo_name}: {mirror_count} mirrors, primary: {primary_url}")
            
            # Submit to server using lightweight API
            logger.info("Submitting repository information to server...")
            success = await self.api_client.submit_repository_info_lightweight(
                self.endpoint_id, repo_info
            )
            
            if success:
                self.last_sync_time = datetime.now()
                logger.info("Repository information submitted successfully")
                return True
            else:
                logger.error("Failed to submit repository information")
                return False
                
        except Exception as e:
            logger.error(f"Failed to sync repository info: {e}")
            return False
    
    async def sync_full_repository_data(self) -> bool:
        """
        Sync full repository data including package lists.
        
        This is more expensive as it queries all packages from each repository.
        Use sync_repository_info() for lightweight mirror info only.
        
        Returns:
            True if sync successful
        """
        if not self.is_authenticated:
            logger.error("Not authenticated. Call authenticate() first.")
            return False
        
        try:
            logger.info("Getting full repository data from pacman...")
            
            # Get full repository information including packages
            repositories = self.pacman.get_all_repositories(self.endpoint_id)
            
            if not repositories:
                logger.warning("No repository data found")
                return False
            
            logger.info(f"Found {len(repositories)} repositories:")
            total_packages = 0
            for repo in repositories:
                package_count = len(repo.packages)
                total_packages += package_count
                logger.info(f"  {repo.repo_name}: {package_count} packages")
            
            logger.info(f"Total packages across all repositories: {total_packages}")
            
            # Submit to server using full API
            logger.info("Submitting full repository data to server...")
            success = await self.api_client.submit_repository_info(
                self.endpoint_id, repositories
            )
            
            if success:
                self.last_sync_time = datetime.now()
                logger.info("Full repository data submitted successfully")
                return True
            else:
                logger.error("Failed to submit full repository data")
                return False
                
        except Exception as e:
            logger.error(f"Failed to sync full repository data: {e}")
            return False
    
    async def get_repository_status(self) -> Dict[str, Any]:
        """
        Get current repository status information.
        
        Returns:
            Dictionary with repository status
        """
        try:
            # Get repository mirrors
            mirrors = self.pacman.get_repository_mirrors()
            
            # Get pacman configuration
            config = self.pacman.config
            
            status = {
                'endpoint_name': self.endpoint_name,
                'hostname': self.hostname,
                'endpoint_id': self.endpoint_id,
                'architecture': config.architecture,
                'repositories': {},
                'total_mirrors': 0,
                'last_sync': self.last_sync_time.isoformat() if self.last_sync_time else None,
                'authenticated': self.is_authenticated
            }
            
            for repo_name, mirror_urls in mirrors.items():
                status['repositories'][repo_name] = {
                    'mirror_count': len(mirror_urls),
                    'mirrors': mirror_urls
                }
                status['total_mirrors'] += len(mirror_urls)
            
            return status
            
        except Exception as e:
            logger.error(f"Failed to get repository status: {e}")
            return {'error': str(e)}
    
    async def perform_pool_assignment_sync(self, api_client: PacmanSyncAPIClient, endpoint_id: str) -> bool:
        """
        Perform a full repository and package sync when assigned to a pool.
        
        This method is designed to be called programmatically when an endpoint
        is assigned to a pool to ensure the server has complete data.
        
        Args:
            api_client: Authenticated API client to use
            endpoint_id: ID of the endpoint
            
        Returns:
            True if sync successful
        """
        try:
            logger.info(f"Performing pool assignment sync for endpoint {endpoint_id}")
            
            # Use the provided API client instead of creating a new one
            self.api_client = api_client
            self.endpoint_id = endpoint_id
            self.is_authenticated = True
            
            # Perform full repository sync (includes packages and mirrors)
            success = await self.sync_full_repository_data()
            
            if success:
                logger.info("Pool assignment sync completed successfully")
                return True
            else:
                logger.error("Pool assignment sync failed")
                return False
                
        except Exception as e:
            logger.error(f"Failed to perform pool assignment sync: {e}")
            return False
    
    async def close(self):
        """Close the client and cleanup resources."""
        if hasattr(self, 'api_client'):
            await self.api_client.close()
        logger.info("Repository sync client closed")


async def main():
    """Main entry point for the repository sync client."""
    parser = argparse.ArgumentParser(
        description="Repository Sync Client for Pacman Sync Utility"
    )
    parser.add_argument(
        '--server-url',
        default='http://localhost:4444',
        help='Server URL (default: http://localhost:4444)'
    )
    parser.add_argument(
        '--endpoint-name',
        required=True,
        help='Name for this endpoint'
    )
    parser.add_argument(
        '--hostname',
        help='Hostname (default: system hostname)'
    )
    parser.add_argument(
        '--full',
        action='store_true',
        help='Sync full repository data including packages (slower)'
    )
    parser.add_argument(
        '--force',
        action='store_true',
        help='Force sync even if recently synced'
    )
    parser.add_argument(
        '--status',
        action='store_true',
        help='Show repository status and exit'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )
    
    args = parser.parse_args()
    
    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Create client
    client = RepositorySyncClient(
        server_url=args.server_url,
        endpoint_name=args.endpoint_name,
        hostname=args.hostname
    )
    
    try:
        # Show status if requested
        if args.status:
            status = await client.get_repository_status()
            print("\n" + "=" * 60)
            print("Repository Status")
            print("=" * 60)
            print(f"Endpoint: {status.get('endpoint_name', 'unknown')}@{status.get('hostname', 'unknown')}")
            print(f"Endpoint ID: {status.get('endpoint_id', 'not authenticated')}")
            print(f"Architecture: {status.get('architecture', 'unknown')}")
            print(f"Authenticated: {status.get('authenticated', False)}")
            print(f"Last Sync: {status.get('last_sync', 'never')}")
            print(f"Total Mirrors: {status.get('total_mirrors', 0)}")
            
            repositories = status.get('repositories', {})
            if repositories:
                print(f"\nRepositories ({len(repositories)}):")
                for repo_name, repo_info in repositories.items():
                    mirror_count = repo_info.get('mirror_count', 0)
                    print(f"  {repo_name}: {mirror_count} mirrors")
            else:
                print("\nNo repositories found")
            
            print("=" * 60)
            return
        
        # Authenticate
        print("Authenticating with server...")
        if not await client.authenticate():
            print("❌ Authentication failed")
            return 1
        
        print("✅ Authentication successful")
        
        # Sync repository information
        if args.full:
            print("Syncing full repository data (including packages)...")
            success = await client.sync_full_repository_data()
        else:
            print("Syncing repository information (mirrors only)...")
            success = await client.sync_repository_info(force=args.force)
        
        if success:
            print("✅ Repository sync completed successfully")
            
            # Show final status
            status = await client.get_repository_status()
            print(f"\nSynced {len(status.get('repositories', {}))} repositories with {status.get('total_mirrors', 0)} total mirrors")
            
            return 0
        else:
            print("❌ Repository sync failed")
            return 1
            
    except KeyboardInterrupt:
        print("\n⚠️  Interrupted by user")
        return 1
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        print(f"❌ Error: {e}")
        return 1
    finally:
        await client.close()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))