"""
HTTP API Client for Pacman Sync Utility Client.

This module provides HTTP client functionality for communicating with the central server,
including authentication, endpoint registration, status reporting, and retry logic.
"""

import asyncio
import json
import logging
import socket
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from urllib.parse import urljoin
import aiohttp
from aiohttp import ClientSession, ClientTimeout, ClientError
from dataclasses import asdict

from shared.models import (
    Endpoint, SystemState, SyncStatus, OperationType, 
    SyncOperation, Repository, RepositoryPackage, PackageState
)
from shared.interfaces import IAPIClient

logger = logging.getLogger(__name__)


class APIClientError(Exception):
    """Base exception for API client errors."""
    pass


class AuthenticationError(APIClientError):
    """Authentication-related errors."""
    pass


class NetworkError(APIClientError):
    """Network-related errors."""
    pass


class ServerError(APIClientError):
    """Server-side errors."""
    pass


class RetryConfig:
    """Configuration for retry logic."""
    
    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True
    ):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter


class PacmanSyncAPIClient(IAPIClient):
    """
    HTTP API client for communicating with the Pacman Sync Utility server.
    
    Provides authentication, endpoint management, status reporting, and sync operations
    with automatic retry logic and offline operation handling.
    """
    
    def __init__(
        self,
        server_url: str,
        timeout: float = 30.0,
        retry_config: Optional[RetryConfig] = None
    ):
        self.server_url = server_url.rstrip('/')
        self.timeout = ClientTimeout(total=timeout)
        self.retry_config = retry_config or RetryConfig()
        
        # Authentication state
        self._auth_token: Optional[str] = None
        self._endpoint_id: Optional[str] = None
        self._endpoint_name: Optional[str] = None
        self._token_expires_at: Optional[datetime] = None
        
        # Session management
        self._session: Optional[ClientSession] = None
        self._is_offline = False
        self._last_connection_attempt: Optional[datetime] = None
        
        # Offline operation queue
        self._offline_operations: List[Dict[str, Any]] = []
        
        logger.info(f"API client initialized for server: {server_url}")
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self._ensure_session()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
    
    async def _ensure_session(self) -> None:
        """Ensure HTTP session is available."""
        if self._session is None or self._session.closed:
            connector = aiohttp.TCPConnector(
                limit=10,
                limit_per_host=5,
                keepalive_timeout=30,
                enable_cleanup_closed=True
            )
            self._session = ClientSession(
                connector=connector,
                timeout=self.timeout,
                headers={
                    'User-Agent': 'PacmanSyncClient/1.0',
                    'Content-Type': 'application/json'
                }
            )
    
    async def close(self) -> None:
        """Close the HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None
    
    def _get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers."""
        headers = {}
        if self._auth_token:
            headers['Authorization'] = f'Bearer {self._auth_token}'
        return headers
    
    async def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        authenticated: bool = True,
        retry: bool = True
    ) -> Dict[str, Any]:
        """
        Make HTTP request with retry logic and error handling.
        
        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint path
            data: Request body data
            params: Query parameters
            authenticated: Whether to include authentication headers
            retry: Whether to retry on failure
            
        Returns:
            Response data as dictionary
            
        Raises:
            APIClientError: On request failure
        """
        await self._ensure_session()
        
        url = urljoin(self.server_url, endpoint.lstrip('/'))
        headers = self._get_auth_headers() if authenticated else {}
        
        # Add any additional headers
        if data is not None:
            headers['Content-Type'] = 'application/json'
        
        attempt = 0
        last_exception = None
        
        while attempt <= (self.retry_config.max_retries if retry else 0):
            try:
                logger.debug(f"Making {method} request to {url} (attempt {attempt + 1})")
                
                async with self._session.request(
                    method=method,
                    url=url,
                    json=data,
                    params=params,
                    headers=headers
                ) as response:
                    
                    # Handle different response status codes
                    if response.status == 200:
                        self._is_offline = False
                        self._last_connection_attempt = datetime.now()
                        
                        try:
                            return await response.json()
                        except json.JSONDecodeError:
                            # Handle empty responses
                            return {}
                    
                    elif response.status == 401:
                        # Authentication error - clear token and raise
                        self._auth_token = None
                        self._token_expires_at = None
                        error_data = await self._get_error_response(response)
                        raise AuthenticationError(f"Authentication failed: {error_data.get('detail', 'Unauthorized')}")
                    
                    elif response.status == 403:
                        error_data = await self._get_error_response(response)
                        raise APIClientError(f"Forbidden: {error_data.get('detail', 'Access denied')}")
                    
                    elif response.status == 404:
                        error_data = await self._get_error_response(response)
                        raise APIClientError(f"Not found: {error_data.get('detail', 'Resource not found')}")
                    
                    elif response.status >= 500:
                        error_data = await self._get_error_response(response)
                        raise ServerError(f"Server error ({response.status}): {error_data.get('detail', 'Internal server error')}")
                    
                    else:
                        error_data = await self._get_error_response(response)
                        raise APIClientError(f"Request failed ({response.status}): {error_data.get('detail', 'Unknown error')}")
            
            except (ClientError, asyncio.TimeoutError, OSError) as e:
                last_exception = e
                logger.warning(f"Network error on attempt {attempt + 1}: {e}")
                
                # Mark as offline on network errors
                self._is_offline = True
                self._last_connection_attempt = datetime.now()
                
                if not retry or attempt >= self.retry_config.max_retries:
                    break
                
                # Calculate delay with exponential backoff
                delay = min(
                    self.retry_config.base_delay * (self.retry_config.exponential_base ** attempt),
                    self.retry_config.max_delay
                )
                
                if self.retry_config.jitter:
                    import random
                    delay *= (0.5 + random.random() * 0.5)  # Add jitter
                
                logger.info(f"Retrying in {delay:.1f} seconds...")
                await asyncio.sleep(delay)
                attempt += 1
            
            except Exception as e:
                logger.error(f"Unexpected error in request: {e}")
                raise APIClientError(f"Request failed: {str(e)}")
        
        # All retries exhausted
        if last_exception:
            raise NetworkError(f"Network request failed after {self.retry_config.max_retries + 1} attempts: {last_exception}")
        else:
            raise APIClientError("Request failed for unknown reason")
    
    async def _get_error_response(self, response) -> Dict[str, Any]:
        """Extract error information from response."""
        try:
            return await response.json()
        except:
            return {"detail": await response.text() or "Unknown error"}
    
    def is_offline(self) -> bool:
        """Check if client is currently offline."""
        return self._is_offline
    
    def get_last_connection_attempt(self) -> Optional[datetime]:
        """Get timestamp of last connection attempt."""
        return self._last_connection_attempt
    
    async def authenticate(self, endpoint_name: str, hostname: str) -> str:
        """
        Authenticate with server and get access token.
        
        Args:
            endpoint_name: Name of the endpoint
            hostname: Hostname of the endpoint
            
        Returns:
            Authentication token
            
        Raises:
            AuthenticationError: On authentication failure
        """
        try:
            logger.info(f"Authenticating endpoint: {endpoint_name}@{hostname}")
            
            response = await self._make_request(
                method='POST',
                endpoint='/api/endpoints/register',
                data={
                    'name': endpoint_name,
                    'hostname': hostname
                },
                authenticated=False
            )
            
            self._auth_token = response['auth_token']
            self._endpoint_id = response['endpoint']['id']
            self._endpoint_name = endpoint_name
            
            # Set token expiration (assume 24 hours if not specified)
            self._token_expires_at = datetime.now() + timedelta(hours=24)
            
            logger.info(f"Authentication successful. Endpoint ID: {self._endpoint_id}")
            return self._auth_token
            
        except NetworkError as e:
            logger.error(f"Network error during authentication: {e}")
            raise  # Re-raise NetworkError as-is
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            raise AuthenticationError(f"Failed to authenticate: {str(e)}")
    
    async def register_endpoint(self, name: str, hostname: str) -> Dict[str, Any]:
        """
        Register endpoint with server.
        
        Args:
            name: Endpoint name
            hostname: Endpoint hostname
            
        Returns:
            Endpoint registration data
        """
        # This is the same as authenticate for this implementation
        await self.authenticate(name, hostname)
        
        return {
            'endpoint_id': self._endpoint_id,
            'name': name,
            'hostname': hostname,
            'auth_token': self._auth_token
        }
    
    async def report_status(self, endpoint_id: str, status: SyncStatus) -> bool:
        """
        Report endpoint status to server.
        
        Args:
            endpoint_id: ID of the endpoint
            status: Current sync status
            
        Returns:
            True if successful
        """
        try:
            if self.is_offline():
                # Queue operation for later
                self._offline_operations.append({
                    'type': 'status_update',
                    'endpoint_id': endpoint_id,
                    'status': status.value,
                    'timestamp': datetime.now().isoformat()
                })
                logger.info(f"Queued status update for offline processing: {status.value}")
                return True
            
            await self._make_request(
                method='PUT',
                endpoint=f'/api/endpoints/{endpoint_id}/status',
                data={'status': status.value}
            )
            
            logger.debug(f"Status reported successfully: {status.value}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to report status: {e}")
            
            # Queue for retry if it's a network error
            if isinstance(e, NetworkError):
                self._offline_operations.append({
                    'type': 'status_update',
                    'endpoint_id': endpoint_id,
                    'status': status.value,
                    'timestamp': datetime.now().isoformat()
                })
            
            return False
    
    async def submit_state(self, endpoint_id: str, state: SystemState) -> str:
        """
        Submit system state to server.
        
        Args:
            endpoint_id: ID of the endpoint
            state: System state to submit
            
        Returns:
            State ID
        """
        try:
            # Convert SystemState to API format
            state_data = {
                'endpoint_id': state.endpoint_id,
                'timestamp': state.timestamp.isoformat(),
                'packages': [
                    {
                        'package_name': pkg.package_name,
                        'version': pkg.version,
                        'repository': pkg.repository,
                        'installed_size': pkg.installed_size,
                        'dependencies': pkg.dependencies
                    }
                    for pkg in state.packages
                ],
                'pacman_version': state.pacman_version,
                'architecture': state.architecture
            }
            
            if self.is_offline():
                # Queue operation for later
                self._offline_operations.append({
                    'type': 'state_submission',
                    'endpoint_id': endpoint_id,
                    'state_data': state_data,
                    'timestamp': datetime.now().isoformat()
                })
                logger.info("Queued state submission for offline processing")
                return f"offline_{datetime.now().timestamp()}"
            
            response = await self._make_request(
                method='POST',
                endpoint=f'/api/states/{endpoint_id}',
                data=state_data
            )
            
            state_id = response.get('state_id', '')
            logger.info(f"State submitted successfully: {state_id}")
            return state_id
            
        except Exception as e:
            logger.error(f"Failed to submit state: {e}")
            
            # Queue for retry if it's a network error
            if isinstance(e, NetworkError):
                state_data = {
                    'endpoint_id': state.endpoint_id,
                    'timestamp': state.timestamp.isoformat(),
                    'packages': [asdict(pkg) for pkg in state.packages],
                    'pacman_version': state.pacman_version,
                    'architecture': state.architecture
                }
                
                self._offline_operations.append({
                    'type': 'state_submission',
                    'endpoint_id': endpoint_id,
                    'state_data': state_data,
                    'timestamp': datetime.now().isoformat()
                })
            
            raise APIClientError(f"Failed to submit state: {str(e)}")
    
    async def get_target_state(self, pool_id: str) -> Optional[SystemState]:
        """
        Get target state for pool.
        
        Args:
            pool_id: ID of the pool
            
        Returns:
            Target system state or None if not available
        """
        try:
            if self.is_offline():
                logger.warning("Cannot get target state while offline")
                return None
            
            response = await self._make_request(
                method='GET',
                endpoint=f'/api/pools/{pool_id}/target-state'
            )
            
            if not response or 'state' not in response:
                return None
            
            state_data = response['state']
            
            # Convert API response to SystemState
            packages = []
            for pkg_data in state_data.get('packages', []):
                packages.append(PackageState(
                    package_name=pkg_data['package_name'],
                    version=pkg_data['version'],
                    repository=pkg_data['repository'],
                    installed_size=pkg_data['installed_size'],
                    dependencies=pkg_data.get('dependencies', [])
                ))
            
            return SystemState(
                endpoint_id=state_data['endpoint_id'],
                timestamp=datetime.fromisoformat(state_data['timestamp']),
                packages=packages,
                pacman_version=state_data['pacman_version'],
                architecture=state_data['architecture']
            )
            
        except Exception as e:
            logger.error(f"Failed to get target state: {e}")
            return None
    
    async def trigger_sync(self, endpoint_id: str, operation: OperationType) -> str:
        """
        Trigger sync operation.
        
        Args:
            endpoint_id: ID of the endpoint
            operation: Type of operation to trigger
            
        Returns:
            Operation ID
        """
        try:
            if self.is_offline():
                # Queue operation for later
                operation_id = f"offline_{datetime.now().timestamp()}"
                self._offline_operations.append({
                    'type': 'sync_operation',
                    'endpoint_id': endpoint_id,
                    'operation': operation.value,
                    'operation_id': operation_id,
                    'timestamp': datetime.now().isoformat()
                })
                logger.info(f"Queued sync operation for offline processing: {operation.value}")
                return operation_id
            
            # Map operation types to API endpoints
            endpoint_map = {
                OperationType.SYNC: f'/api/sync/{endpoint_id}/sync-to-latest',
                OperationType.SET_LATEST: f'/api/sync/{endpoint_id}/set-as-latest',
                OperationType.REVERT: f'/api/sync/{endpoint_id}/revert'
            }
            
            api_endpoint = endpoint_map.get(operation)
            if not api_endpoint:
                raise APIClientError(f"Unknown operation type: {operation}")
            
            response = await self._make_request(
                method='POST',
                endpoint=api_endpoint,
                data={}
            )
            
            operation_id = response.get('operation_id', '')
            logger.info(f"Sync operation triggered: {operation.value} -> {operation_id}")
            return operation_id
            
        except Exception as e:
            logger.error(f"Failed to trigger sync operation: {e}")
            raise APIClientError(f"Failed to trigger sync: {str(e)}")
    
    async def submit_repository_info(self, endpoint_id: str, repositories: List[Repository]) -> bool:
        """
        Submit repository information to server.
        
        Args:
            endpoint_id: ID of the endpoint
            repositories: List of repository information
            
        Returns:
            True if successful
        """
        try:
            # Convert repositories to API format
            repo_data = []
            for repo in repositories:
                packages_data = []
                for pkg in repo.packages:
                    packages_data.append({
                        'name': pkg.name,
                        'version': pkg.version,
                        'repository': pkg.repository,
                        'architecture': pkg.architecture,
                        'description': pkg.description
                    })
                
                repo_data.append({
                    'repo_name': repo.repo_name,
                    'repo_url': repo.repo_url,
                    'packages': packages_data
                })
            
            if self.is_offline():
                # Queue operation for later
                self._offline_operations.append({
                    'type': 'repository_submission',
                    'endpoint_id': endpoint_id,
                    'repositories': repo_data,
                    'timestamp': datetime.now().isoformat()
                })
                logger.info("Queued repository info submission for offline processing")
                return True
            
            await self._make_request(
                method='POST',
                endpoint=f'/api/endpoints/{endpoint_id}/repositories',
                data={'repositories': repo_data}
            )
            
            logger.info("Repository information submitted successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to submit repository info: {e}")
            
            # Queue for retry if it's a network error
            if isinstance(e, NetworkError):
                repo_data = []
                for repo in repositories:
                    packages_data = [asdict(pkg) for pkg in repo.packages]
                    repo_data.append({
                        'repo_name': repo.repo_name,
                        'repo_url': repo.repo_url,
                        'packages': packages_data
                    })
                
                self._offline_operations.append({
                    'type': 'repository_submission',
                    'endpoint_id': endpoint_id,
                    'repositories': repo_data,
                    'timestamp': datetime.now().isoformat()
                })
            
            return False
    
    async def get_operation_status(self, operation_id: str) -> Optional[Dict[str, Any]]:
        """
        Get status of a sync operation.
        
        Args:
            operation_id: ID of the operation
            
        Returns:
            Operation status data or None if not available
        """
        try:
            if self.is_offline():
                logger.warning("Cannot get operation status while offline")
                return None
            
            response = await self._make_request(
                method='GET',
                endpoint=f'/api/sync/operations/{operation_id}'
            )
            
            return response
            
        except Exception as e:
            logger.error(f"Failed to get operation status: {e}")
            return None
    
    async def process_offline_operations(self) -> int:
        """
        Process queued offline operations when connection is restored.
        
        Returns:
            Number of operations processed successfully
        """
        if self.is_offline() or not self._offline_operations:
            return 0
        
        processed = 0
        failed_operations = []
        
        logger.info(f"Processing {len(self._offline_operations)} offline operations")
        
        for operation in self._offline_operations:
            try:
                op_type = operation['type']
                
                if op_type == 'status_update':
                    status = SyncStatus(operation['status'])
                    success = await self.report_status(operation['endpoint_id'], status)
                    if success:
                        processed += 1
                    else:
                        failed_operations.append(operation)
                
                elif op_type == 'repository_submission':
                    # Reconstruct Repository objects
                    repositories = []
                    for repo_data in operation['repositories']:
                        packages = []
                        for pkg_data in repo_data['packages']:
                            packages.append(RepositoryPackage(**pkg_data))
                        
                        repositories.append(Repository(
                            id="",  # Will be generated
                            endpoint_id=operation['endpoint_id'],
                            repo_name=repo_data['repo_name'],
                            repo_url=repo_data['repo_url'],
                            packages=packages
                        ))
                    
                    success = await self.submit_repository_info(operation['endpoint_id'], repositories)
                    if success:
                        processed += 1
                    else:
                        failed_operations.append(operation)
                
                elif op_type == 'sync_operation':
                    # Re-trigger sync operation
                    operation_type = OperationType(operation['operation'])
                    await self.trigger_sync(operation['endpoint_id'], operation_type)
                    processed += 1
                
                # Add other operation types as needed
                
            except Exception as e:
                logger.error(f"Failed to process offline operation: {e}")
                failed_operations.append(operation)
        
        # Update offline operations list with failed operations
        self._offline_operations = failed_operations
        
        logger.info(f"Processed {processed} offline operations, {len(failed_operations)} failed")
        return processed
    
    def get_endpoint_info(self) -> Optional[Dict[str, str]]:
        """Get current endpoint information."""
        if self._endpoint_id and self._endpoint_name:
            return {
                'endpoint_id': self._endpoint_id,
                'endpoint_name': self._endpoint_name,
                'auth_token': self._auth_token or '',
                'is_authenticated': bool(self._auth_token)
            }
        return None
    
    def clear_authentication(self) -> None:
        """Clear authentication state."""
        self._auth_token = None
        self._endpoint_id = None
        self._endpoint_name = None
        self._token_expires_at = None
        logger.info("Authentication state cleared")