"""
Secure Token Storage for Pacman Sync Utility Client.

This module provides secure storage and management of authentication tokens
using the system keyring or encrypted file storage as fallback.
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from pathlib import Path
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

logger = logging.getLogger(__name__)


class TokenStorageError(Exception):
    """Base exception for token storage errors."""
    pass


class SecureTokenStorage:
    """
    Secure storage for authentication tokens.
    
    Uses system keyring when available, falls back to encrypted file storage.
    Provides automatic token refresh and expiration handling.
    """
    
    def __init__(self, service_name: str = "pacman-sync-client"):
        self.service_name = service_name
        self.keyring_available = self._check_keyring_availability()
        self.storage_path = self._get_storage_path()
        
        # Encryption key for file storage
        self._encryption_key: Optional[bytes] = None
        
        logger.info(f"Token storage initialized (keyring: {self.keyring_available})")
    
    def _check_keyring_availability(self) -> bool:
        """Check if system keyring is available."""
        try:
            import keyring
            # Test keyring functionality
            test_key = f"{self.service_name}_test"
            keyring.set_password(self.service_name, test_key, "test")
            result = keyring.get_password(self.service_name, test_key)
            keyring.delete_password(self.service_name, test_key)
            return result == "test"
        except Exception as e:
            logger.debug(f"Keyring not available: {e}")
            return False
    
    def _get_storage_path(self) -> Path:
        """Get path for encrypted file storage."""
        # Use XDG config directory
        xdg_config = os.environ.get('XDG_CONFIG_HOME')
        if xdg_config:
            config_dir = Path(xdg_config) / 'pacman-sync'
        else:
            config_dir = Path.home() / '.config' / 'pacman-sync'
        
        config_dir.mkdir(parents=True, exist_ok=True)
        return config_dir / 'auth_tokens.enc'
    
    def _get_encryption_key(self) -> bytes:
        """Get or create encryption key for file storage."""
        if self._encryption_key:
            return self._encryption_key
        
        # Try to get key from keyring first
        if self.keyring_available:
            try:
                import keyring
                stored_key = keyring.get_password(self.service_name, "encryption_key")
                if stored_key:
                    self._encryption_key = base64.b64decode(stored_key.encode())
                    return self._encryption_key
            except Exception as e:
                logger.warning(f"Failed to get encryption key from keyring: {e}")
        
        # Generate new key
        password = os.urandom(32)  # Random password
        salt = os.urandom(16)
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password))
        
        # Store key in keyring if available
        if self.keyring_available:
            try:
                import keyring
                key_data = base64.b64encode(key).decode()
                keyring.set_password(self.service_name, "encryption_key", key_data)
            except Exception as e:
                logger.warning(f"Failed to store encryption key in keyring: {e}")
        
        self._encryption_key = key
        return key
    
    def _encrypt_data(self, data: str) -> bytes:
        """Encrypt data for file storage."""
        key = self._get_encryption_key()
        fernet = Fernet(key)
        return fernet.encrypt(data.encode())
    
    def _decrypt_data(self, encrypted_data: bytes) -> str:
        """Decrypt data from file storage."""
        key = self._get_encryption_key()
        fernet = Fernet(key)
        return fernet.decrypt(encrypted_data).decode()
    
    def store_token(
        self,
        endpoint_id: str,
        token: str,
        endpoint_name: str,
        server_url: str,
        expires_at: Optional[datetime] = None
    ) -> None:
        """
        Store authentication token securely.
        
        Args:
            endpoint_id: Endpoint identifier
            token: JWT authentication token
            endpoint_name: Human-readable endpoint name
            server_url: Server URL
            expires_at: Token expiration time
        """
        token_data = {
            'endpoint_id': endpoint_id,
            'token': token,
            'endpoint_name': endpoint_name,
            'server_url': server_url,
            'expires_at': expires_at.isoformat() if expires_at else None,
            'stored_at': datetime.now().isoformat()
        }
        
        try:
            if self.keyring_available:
                self._store_token_keyring(endpoint_id, token_data)
            else:
                self._store_token_file(endpoint_id, token_data)
            
            logger.info(f"Token stored securely for endpoint {endpoint_id}")
            
        except Exception as e:
            logger.error(f"Failed to store token: {e}")
            raise TokenStorageError(f"Failed to store token: {e}")
    
    def _store_token_keyring(self, endpoint_id: str, token_data: Dict[str, Any]) -> None:
        """Store token using system keyring."""
        import keyring
        
        key = f"token_{endpoint_id}"
        value = json.dumps(token_data)
        keyring.set_password(self.service_name, key, value)
    
    def _store_token_file(self, endpoint_id: str, token_data: Dict[str, Any]) -> None:
        """Store token in encrypted file."""
        # Load existing tokens
        all_tokens = {}
        if self.storage_path.exists():
            try:
                encrypted_data = self.storage_path.read_bytes()
                decrypted_data = self._decrypt_data(encrypted_data)
                all_tokens = json.loads(decrypted_data)
            except Exception as e:
                logger.warning(f"Failed to load existing tokens: {e}")
        
        # Add/update token
        all_tokens[endpoint_id] = token_data
        
        # Save tokens
        data_json = json.dumps(all_tokens)
        encrypted_data = self._encrypt_data(data_json)
        self.storage_path.write_bytes(encrypted_data)
        
        # Set restrictive permissions
        os.chmod(self.storage_path, 0o600)
    
    def get_token(self, endpoint_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve authentication token.
        
        Args:
            endpoint_id: Endpoint identifier
            
        Returns:
            Token data dictionary or None if not found
        """
        try:
            if self.keyring_available:
                return self._get_token_keyring(endpoint_id)
            else:
                return self._get_token_file(endpoint_id)
                
        except Exception as e:
            logger.error(f"Failed to retrieve token: {e}")
            return None
    
    def _get_token_keyring(self, endpoint_id: str) -> Optional[Dict[str, Any]]:
        """Get token from system keyring."""
        import keyring
        
        key = f"token_{endpoint_id}"
        value = keyring.get_password(self.service_name, key)
        
        if value:
            return json.loads(value)
        return None
    
    def _get_token_file(self, endpoint_id: str) -> Optional[Dict[str, Any]]:
        """Get token from encrypted file."""
        if not self.storage_path.exists():
            return None
        
        try:
            encrypted_data = self.storage_path.read_bytes()
            decrypted_data = self._decrypt_data(encrypted_data)
            all_tokens = json.loads(decrypted_data)
            return all_tokens.get(endpoint_id)
        except Exception as e:
            logger.warning(f"Failed to read token file: {e}")
            return None
    
    def is_token_valid(self, endpoint_id: str) -> bool:
        """
        Check if stored token is valid (not expired).
        
        Args:
            endpoint_id: Endpoint identifier
            
        Returns:
            True if token exists and is not expired
        """
        token_data = self.get_token(endpoint_id)
        if not token_data:
            return False
        
        expires_at_str = token_data.get('expires_at')
        if not expires_at_str:
            # No expiration set, assume valid
            return True
        
        try:
            expires_at = datetime.fromisoformat(expires_at_str)
            return datetime.now() < expires_at
        except (ValueError, TypeError):
            logger.warning(f"Invalid expiration date in token for {endpoint_id}")
            return False
    
    def get_valid_token(self, endpoint_id: str) -> Optional[str]:
        """
        Get valid authentication token.
        
        Args:
            endpoint_id: Endpoint identifier
            
        Returns:
            Valid token string or None if not available/expired
        """
        if not self.is_token_valid(endpoint_id):
            return None
        
        token_data = self.get_token(endpoint_id)
        return token_data.get('token') if token_data else None
    
    def remove_token(self, endpoint_id: str) -> bool:
        """
        Remove stored token.
        
        Args:
            endpoint_id: Endpoint identifier
            
        Returns:
            True if token was removed successfully
        """
        try:
            if self.keyring_available:
                return self._remove_token_keyring(endpoint_id)
            else:
                return self._remove_token_file(endpoint_id)
                
        except Exception as e:
            logger.error(f"Failed to remove token: {e}")
            return False
    
    def _remove_token_keyring(self, endpoint_id: str) -> bool:
        """Remove token from system keyring."""
        import keyring
        
        try:
            key = f"token_{endpoint_id}"
            keyring.delete_password(self.service_name, key)
            return True
        except Exception:
            return False
    
    def _remove_token_file(self, endpoint_id: str) -> bool:
        """Remove token from encrypted file."""
        if not self.storage_path.exists():
            return True
        
        try:
            encrypted_data = self.storage_path.read_bytes()
            decrypted_data = self._decrypt_data(encrypted_data)
            all_tokens = json.loads(decrypted_data)
            
            if endpoint_id in all_tokens:
                del all_tokens[endpoint_id]
                
                if all_tokens:
                    # Save remaining tokens
                    data_json = json.dumps(all_tokens)
                    encrypted_data = self._encrypt_data(data_json)
                    self.storage_path.write_bytes(encrypted_data)
                else:
                    # Remove file if no tokens left
                    self.storage_path.unlink()
                
                return True
            
        except Exception as e:
            logger.warning(f"Failed to remove token from file: {e}")
        
        return False
    
    def list_stored_endpoints(self) -> List[Dict[str, Any]]:
        """
        List all stored endpoint information.
        
        Returns:
            List of endpoint information dictionaries
        """
        endpoints = []
        
        try:
            if self.keyring_available:
                endpoints = self._list_endpoints_keyring()
            else:
                endpoints = self._list_endpoints_file()
                
        except Exception as e:
            logger.error(f"Failed to list endpoints: {e}")
        
        return endpoints
    
    def _list_endpoints_keyring(self) -> List[Dict[str, Any]]:
        """List endpoints from keyring storage."""
        # Keyring doesn't provide a way to list all keys
        # This would require maintaining a separate index
        # For now, return empty list
        return []
    
    def _list_endpoints_file(self) -> List[Dict[str, Any]]:
        """List endpoints from file storage."""
        if not self.storage_path.exists():
            return []
        
        try:
            encrypted_data = self.storage_path.read_bytes()
            decrypted_data = self._decrypt_data(encrypted_data)
            all_tokens = json.loads(decrypted_data)
            
            endpoints = []
            for endpoint_id, token_data in all_tokens.items():
                endpoints.append({
                    'endpoint_id': endpoint_id,
                    'endpoint_name': token_data.get('endpoint_name'),
                    'server_url': token_data.get('server_url'),
                    'stored_at': token_data.get('stored_at'),
                    'expires_at': token_data.get('expires_at'),
                    'is_valid': self.is_token_valid(endpoint_id)
                })
            
            return endpoints
            
        except Exception as e:
            logger.warning(f"Failed to list endpoints from file: {e}")
            return []
    
    def cleanup_expired_tokens(self) -> int:
        """
        Remove expired tokens from storage.
        
        Returns:
            Number of tokens removed
        """
        removed_count = 0
        
        try:
            endpoints = self.list_stored_endpoints()
            for endpoint in endpoints:
                if not endpoint['is_valid']:
                    if self.remove_token(endpoint['endpoint_id']):
                        removed_count += 1
                        logger.info(f"Removed expired token for {endpoint['endpoint_id']}")
            
        except Exception as e:
            logger.error(f"Failed to cleanup expired tokens: {e}")
        
        return removed_count