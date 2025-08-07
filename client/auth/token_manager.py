"""
Token Manager for Pacman Sync Utility Client.

This module provides automatic token refresh, authentication state management,
and integration with the secure token storage system.
"""

import logging
import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Callable, List
from jose import jwt, JWTError

from client.auth.token_storage import SecureTokenStorage, TokenStorageError

logger = logging.getLogger(__name__)


class TokenManager:
    """
    Manages authentication tokens with automatic refresh and validation.
    
    Provides high-level authentication management including token validation,
    automatic refresh, and secure storage integration.
    """
    
    def __init__(self, api_client=None, refresh_threshold_minutes: int = 60):
        self.api_client = api_client
        self.token_storage = SecureTokenStorage()
        self.refresh_threshold = timedelta(minutes=refresh_threshold_minutes)
        
        # Current authentication state
        self._current_endpoint_id: Optional[str] = None
        self._current_token: Optional[str] = None
        self._token_expires_at: Optional[datetime] = None
        
        # Callbacks for authentication events
        self._auth_callbacks: List[Callable[[bool], None]] = []
        self._token_refresh_callbacks: List[Callable[[str], None]] = []
        
        # Automatic refresh task
        self._refresh_task: Optional[asyncio.Task] = None
        self._refresh_enabled = True
        
        logger.info("Token manager initialized")
    
    def add_auth_callback(self, callback: Callable[[bool], None]) -> None:
        """
        Add callback for authentication state changes.
        
        Args:
            callback: Function called with authentication status (bool)
        """
        self._auth_callbacks.append(callback)
    
    def add_token_refresh_callback(self, callback: Callable[[str], None]) -> None:
        """
        Add callback for token refresh events.
        
        Args:
            callback: Function called with new token (str)
        """
        self._token_refresh_callbacks.append(callback)
    
    def _notify_auth_change(self, is_authenticated: bool) -> None:
        """Notify callbacks of authentication state change."""
        for callback in self._auth_callbacks:
            try:
                callback(is_authenticated)
            except Exception as e:
                logger.error(f"Error in auth callback: {e}")
    
    def _notify_token_refresh(self, new_token: str) -> None:
        """Notify callbacks of token refresh."""
        for callback in self._token_refresh_callbacks:
            try:
                callback(new_token)
            except Exception as e:
                logger.error(f"Error in token refresh callback: {e}")
    
    def _parse_token_expiration(self, token: str) -> Optional[datetime]:
        """
        Parse expiration time from JWT token.
        
        Args:
            token: JWT token string
            
        Returns:
            Expiration datetime or None if not available
        """
        try:
            # Decode without verification to get expiration
            payload = jwt.get_unverified_claims(token)
            expires_at_timestamp = payload.get('expires_at')
            
            if expires_at_timestamp:
                return datetime.fromtimestamp(expires_at_timestamp)
                
        except JWTError as e:
            logger.warning(f"Failed to parse token expiration: {e}")
        
        return None
    
    async def authenticate(self, endpoint_name: str, hostname: str, server_url: str) -> bool:
        """
        Authenticate with server and store token.
        
        Args:
            endpoint_name: Name of the endpoint
            hostname: Hostname of the endpoint
            server_url: Server URL
            
        Returns:
            True if authentication successful
        """
        if not self.api_client:
            logger.error("No API client configured for authentication")
            return False
        
        try:
            logger.info(f"Authenticating endpoint: {endpoint_name}@{hostname}")
            
            # Attempt authentication with server
            auth_result = await self.api_client.register_endpoint(endpoint_name, hostname)
            
            endpoint_id = auth_result['endpoint_id']
            token = auth_result['auth_token']
            
            # Parse token expiration
            expires_at = self._parse_token_expiration(token)
            
            # Store token securely
            self.token_storage.store_token(
                endpoint_id=endpoint_id,
                token=token,
                endpoint_name=endpoint_name,
                server_url=server_url,
                expires_at=expires_at
            )
            
            # Update current state
            self._current_endpoint_id = endpoint_id
            self._current_token = token
            self._token_expires_at = expires_at
            
            # Start automatic refresh if enabled
            if self._refresh_enabled:
                await self._start_refresh_task()
            
            # Notify callbacks
            self._notify_auth_change(True)
            
            logger.info(f"Authentication successful for endpoint {endpoint_id}")
            return True
            
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            self._notify_auth_change(False)
            return False
    
    async def load_stored_token(self, endpoint_id: str) -> bool:
        """
        Load and validate stored authentication token.
        
        Args:
            endpoint_id: Endpoint identifier
            
        Returns:
            True if valid token was loaded
        """
        try:
            token_data = self.token_storage.get_token(endpoint_id)
            if not token_data:
                logger.info(f"No stored token found for endpoint {endpoint_id}")
                return False
            
            token = token_data['token']
            expires_at_str = token_data.get('expires_at')
            
            # Parse expiration
            expires_at = None
            if expires_at_str:
                try:
                    expires_at = datetime.fromisoformat(expires_at_str)
                except ValueError:
                    logger.warning(f"Invalid expiration date in stored token")
            
            # Check if token is expired
            if expires_at and datetime.now() >= expires_at:
                logger.info(f"Stored token for {endpoint_id} is expired")
                self.token_storage.remove_token(endpoint_id)
                return False
            
            # Update current state
            self._current_endpoint_id = endpoint_id
            self._current_token = token
            self._token_expires_at = expires_at
            
            # Start automatic refresh if enabled
            if self._refresh_enabled:
                await self._start_refresh_task()
            
            # Notify callbacks
            self._notify_auth_change(True)
            
            logger.info(f"Loaded valid stored token for endpoint {endpoint_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load stored token: {e}")
            return False
    
    def get_current_token(self) -> Optional[str]:
        """
        Get current valid authentication token.
        
        Returns:
            Current token or None if not authenticated
        """
        if not self._current_token:
            return None
        
        # Check expiration
        if self._token_expires_at and datetime.now() >= self._token_expires_at:
            logger.info("Current token is expired")
            self._current_token = None
            self._current_endpoint_id = None
            self._token_expires_at = None
            self._notify_auth_change(False)
            return None
        
        return self._current_token
    
    def get_current_endpoint_id(self) -> Optional[str]:
        """Get current endpoint ID."""
        return self._current_endpoint_id
    
    def is_authenticated(self) -> bool:
        """Check if currently authenticated with valid token."""
        return self.get_current_token() is not None
    
    def needs_refresh(self) -> bool:
        """
        Check if token needs refresh.
        
        Returns:
            True if token should be refreshed soon
        """
        if not self._token_expires_at:
            return False
        
        time_until_expiry = self._token_expires_at - datetime.now()
        return time_until_expiry <= self.refresh_threshold
    
    async def refresh_token(self) -> bool:
        """
        Refresh current authentication token.
        
        Returns:
            True if refresh successful
        """
        if not self._current_endpoint_id or not self.api_client:
            logger.warning("Cannot refresh token: no current endpoint or API client")
            return False
        
        try:
            # Get stored endpoint information
            token_data = self.token_storage.get_token(self._current_endpoint_id)
            if not token_data:
                logger.error("Cannot refresh token: no stored endpoint data")
                return False
            
            endpoint_name = token_data['endpoint_name']
            server_url = token_data['server_url']
            
            # Extract hostname from endpoint name (format: user@hostname)
            if '@' in endpoint_name:
                hostname = endpoint_name.split('@', 1)[1]
            else:
                hostname = endpoint_name
            
            logger.info(f"Refreshing token for endpoint {self._current_endpoint_id}")
            
            # Re-authenticate to get new token
            success = await self.authenticate(endpoint_name, hostname, server_url)
            
            if success:
                self._notify_token_refresh(self._current_token)
                logger.info("Token refresh successful")
            else:
                logger.error("Token refresh failed")
            
            return success
            
        except Exception as e:
            logger.error(f"Token refresh error: {e}")
            return False
    
    async def _start_refresh_task(self) -> None:
        """Start automatic token refresh task."""
        if self._refresh_task and not self._refresh_task.done():
            self._refresh_task.cancel()
        
        self._refresh_task = asyncio.create_task(self._refresh_loop())
    
    async def _refresh_loop(self) -> None:
        """Automatic token refresh loop."""
        try:
            while self._refresh_enabled and self._current_token:
                # Calculate sleep time until refresh needed
                if self._token_expires_at:
                    time_until_refresh = (
                        self._token_expires_at - datetime.now() - self.refresh_threshold
                    )
                    sleep_seconds = max(60, time_until_refresh.total_seconds())  # At least 1 minute
                else:
                    sleep_seconds = 3600  # Check every hour if no expiration
                
                logger.debug(f"Token refresh check in {sleep_seconds} seconds")
                await asyncio.sleep(sleep_seconds)
                
                # Check if refresh is needed
                if self.needs_refresh():
                    logger.info("Automatic token refresh triggered")
                    await self.refresh_token()
                
        except asyncio.CancelledError:
            logger.debug("Token refresh task cancelled")
        except Exception as e:
            logger.error(f"Error in token refresh loop: {e}")
    
    def logout(self) -> None:
        """
        Logout and clear authentication state.
        """
        logger.info("Logging out and clearing authentication state")
        
        # Cancel refresh task
        if self._refresh_task and not self._refresh_task.done():
            self._refresh_task.cancel()
        
        # Remove stored token
        if self._current_endpoint_id:
            self.token_storage.remove_token(self._current_endpoint_id)
        
        # Clear current state
        self._current_endpoint_id = None
        self._current_token = None
        self._token_expires_at = None
        
        # Notify callbacks
        self._notify_auth_change(False)
    
    def cleanup_expired_tokens(self) -> int:
        """
        Clean up expired tokens from storage.
        
        Returns:
            Number of tokens removed
        """
        return self.token_storage.cleanup_expired_tokens()
    
    def get_stored_endpoints(self) -> List[Dict[str, Any]]:
        """
        Get list of stored endpoint information.
        
        Returns:
            List of endpoint information dictionaries
        """
        return self.token_storage.list_stored_endpoints()
    
    def enable_auto_refresh(self, enabled: bool = True) -> None:
        """
        Enable or disable automatic token refresh.
        
        Args:
            enabled: Whether to enable automatic refresh
        """
        self._refresh_enabled = enabled
        
        if enabled and self._current_token:
            asyncio.create_task(self._start_refresh_task())
        elif not enabled and self._refresh_task:
            self._refresh_task.cancel()
    
    async def shutdown(self) -> None:
        """Shutdown token manager and cleanup resources."""
        logger.info("Shutting down token manager")
        
        self._refresh_enabled = False
        
        if self._refresh_task and not self._refresh_task.done():
            self._refresh_task.cancel()
            try:
                await self._refresh_task
            except asyncio.CancelledError:
                pass