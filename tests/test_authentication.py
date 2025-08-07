"""
Tests for authentication and authorization functionality.

This module tests JWT token authentication, rate limiting, input validation,
and secure token storage for the Pacman Sync Utility.
"""

import pytest
import asyncio
import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock

# Test JWT authentication
def test_jwt_token_generation():
    """Test JWT token generation and verification."""
    from server.core.endpoint_manager import EndpointManager
    from server.database.connection import DatabaseManager
    
    # Mock database manager
    db_manager = Mock(spec=DatabaseManager)
    
    # Create endpoint manager with test secret
    endpoint_manager = EndpointManager(
        db_manager, 
        jwt_secret="test-secret-key",
        jwt_expiration_hours=24
    )
    
    # Generate token
    endpoint_id = "test-endpoint-123"
    endpoint_name = "test-endpoint"
    
    token = endpoint_manager.generate_auth_token(endpoint_id, endpoint_name)
    
    # Verify token
    payload = endpoint_manager.verify_auth_token(token)
    
    assert payload['endpoint_id'] == endpoint_id
    assert payload['endpoint_name'] == endpoint_name
    assert 'issued_at' in payload
    assert 'expires_at' in payload


def test_jwt_token_expiration():
    """Test JWT token expiration handling."""
    from server.core.endpoint_manager import EndpointManager, EndpointAuthenticationError
    from server.database.connection import DatabaseManager
    
    # Mock database manager
    db_manager = Mock(spec=DatabaseManager)
    
    # Create endpoint manager with very short expiration
    endpoint_manager = EndpointManager(
        db_manager, 
        jwt_secret="test-secret-key",
        jwt_expiration_hours=0  # Immediate expiration
    )
    
    # Generate token
    token = endpoint_manager.generate_auth_token("test-id", "test-name")
    
    # Token should be expired immediately
    with pytest.raises(EndpointAuthenticationError, match="Token expired"):
        endpoint_manager.verify_auth_token(token)


def test_invalid_jwt_token():
    """Test handling of invalid JWT tokens."""
    from server.core.endpoint_manager import EndpointManager, EndpointAuthenticationError
    from server.database.connection import DatabaseManager
    
    # Mock database manager
    db_manager = Mock(spec=DatabaseManager)
    endpoint_manager = EndpointManager(db_manager, jwt_secret="test-secret-key")
    
    # Test invalid token
    with pytest.raises(EndpointAuthenticationError, match="Invalid token"):
        endpoint_manager.verify_auth_token("invalid-token")
    
    # Test token with wrong secret
    other_manager = EndpointManager(db_manager, jwt_secret="different-secret")
    token = other_manager.generate_auth_token("test-id", "test-name")
    
    with pytest.raises(EndpointAuthenticationError, match="Invalid token"):
        endpoint_manager.verify_auth_token(token)


def test_rate_limiting():
    """Test rate limiting middleware."""
    from server.middleware.rate_limiting import RateLimiter
    from fastapi import Request
    from unittest.mock import Mock
    
    # Create rate limiter with low limit for testing
    limiter = RateLimiter(requests_per_minute=2)
    
    # Mock request
    request = Mock(spec=Request)
    request.client.host = "127.0.0.1"
    request.headers = {}
    request.state = Mock()
    request.state.endpoint = None
    
    # First request should be allowed
    is_allowed, info = limiter.is_allowed(request)
    assert is_allowed is True
    assert info['remaining'] == 1
    
    # Second request should be allowed
    is_allowed, info = limiter.is_allowed(request)
    assert is_allowed is True
    assert info['remaining'] == 0
    
    # Third request should be blocked
    is_allowed, info = limiter.is_allowed(request)
    assert is_allowed is False
    assert info['remaining'] == 0
    assert info['retry_after'] is not None


def test_input_validation():
    """Test input validation middleware."""
    from server.middleware.validation import ValidationMiddleware
    from fastapi import HTTPException
    
    validator = ValidationMiddleware()
    
    # Test valid inputs
    valid_name = validator.validate_identifier("valid-name_123", "test_field")
    assert valid_name == "valid-name_123"
    
    valid_hostname = validator.validate_hostname("example.com", "hostname")
    assert valid_hostname == "example.com"
    
    # Test invalid inputs
    with pytest.raises(HTTPException, match="invalid characters"):
        validator.validate_identifier("invalid@name", "test_field")
    
    with pytest.raises(HTTPException, match="not a valid hostname"):
        validator.validate_hostname("invalid hostname with spaces", "hostname")
    
    # Test SQL injection detection
    with pytest.raises(HTTPException, match="Invalid characters detected"):
        validator.validate_string_field("'; DROP TABLE users; --", "test_field")
    
    # Test XSS detection
    with pytest.raises(HTTPException, match="Invalid content detected"):
        validator.validate_string_field("<script>alert('xss')</script>", "test_field")


def test_secure_token_storage():
    """Test secure token storage functionality."""
    from client.auth.token_storage import SecureTokenStorage
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create token storage with custom path
        storage = SecureTokenStorage()
        storage.storage_path = Path(temp_dir) / "test_tokens.enc"
        storage.keyring_available = False  # Force file storage for testing
        
        # Store token
        endpoint_id = "test-endpoint-123"
        token = "test-jwt-token"
        endpoint_name = "test@hostname"
        server_url = "http://localhost:8080"
        expires_at = datetime.now() + timedelta(hours=24)
        
        storage.store_token(endpoint_id, token, endpoint_name, server_url, expires_at)
        
        # Retrieve token
        token_data = storage.get_token(endpoint_id)
        assert token_data is not None
        assert token_data['token'] == token
        assert token_data['endpoint_name'] == endpoint_name
        assert token_data['server_url'] == server_url
        
        # Check token validity
        assert storage.is_token_valid(endpoint_id) is True
        
        # Get valid token
        retrieved_token = storage.get_valid_token(endpoint_id)
        assert retrieved_token == token
        
        # Remove token
        success = storage.remove_token(endpoint_id)
        assert success is True
        
        # Verify token is gone
        assert storage.get_token(endpoint_id) is None


def test_token_storage_expiration():
    """Test token storage expiration handling."""
    from client.auth.token_storage import SecureTokenStorage
    
    with tempfile.TemporaryDirectory() as temp_dir:
        storage = SecureTokenStorage()
        storage.storage_path = Path(temp_dir) / "test_tokens.enc"
        storage.keyring_available = False
        
        # Store expired token
        endpoint_id = "test-endpoint-123"
        token = "expired-token"
        expires_at = datetime.now() - timedelta(hours=1)  # Expired 1 hour ago
        
        storage.store_token(endpoint_id, token, "test@host", "http://localhost", expires_at)
        
        # Check token validity
        assert storage.is_token_valid(endpoint_id) is False
        
        # Get valid token should return None
        assert storage.get_valid_token(endpoint_id) is None


@pytest.mark.asyncio
async def test_token_manager():
    """Test token manager functionality."""
    from client.auth.token_manager import TokenManager
    
    # Mock API client
    api_client = AsyncMock()
    api_client.register_endpoint.return_value = {
        'endpoint_id': 'test-endpoint-123',
        'auth_token': 'test-jwt-token'
    }
    
    # Create token manager
    token_manager = TokenManager(api_client=api_client)
    token_manager.token_storage.keyring_available = False  # Force file storage
    
    # Test authentication
    success = await token_manager.authenticate("test@hostname", "hostname", "http://localhost:8080")
    assert success is True
    assert token_manager.is_authenticated() is True
    assert token_manager.get_current_endpoint_id() == 'test-endpoint-123'
    assert token_manager.get_current_token() == 'test-jwt-token'
    
    # Test logout
    token_manager.logout()
    assert token_manager.is_authenticated() is False
    assert token_manager.get_current_token() is None


@pytest.mark.asyncio
async def test_authentication_middleware():
    """Test authentication middleware integration."""
    from server.middleware.auth import AuthenticationMiddleware
    from server.core.endpoint_manager import EndpointManager
    from shared.models import Endpoint, SyncStatus
    from fastapi.security import HTTPAuthorizationCredentials
    from fastapi import HTTPException
    
    # Create test endpoint
    test_endpoint = Endpoint(
        id="test-endpoint-123",
        name="test-endpoint",
        hostname="test-host",
        sync_status=SyncStatus.OFFLINE
    )
    
    # Mock endpoint manager
    endpoint_manager = Mock(spec=EndpointManager)
    endpoint_manager.get_endpoint.return_value = test_endpoint
    endpoint_manager.update_last_seen.return_value = True
    
    # Create auth middleware
    auth_middleware = AuthenticationMiddleware("test-secret-key")
    
    # Generate valid token
    from server.core.endpoint_manager import EndpointManager as RealEndpointManager
    real_manager = RealEndpointManager(Mock(), jwt_secret="test-secret-key")
    valid_token = real_manager.generate_auth_token("test-endpoint-123", "test-endpoint")
    
    # Test valid authentication
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=valid_token)
    authenticated_endpoint = await auth_middleware.authenticate_endpoint(credentials, endpoint_manager)
    
    assert authenticated_endpoint.id == "test-endpoint-123"
    endpoint_manager.get_endpoint.assert_called_once_with("test-endpoint-123")
    endpoint_manager.update_last_seen.assert_called_once()
    
    # Test invalid token
    invalid_credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="invalid-token")
    
    with pytest.raises(HTTPException, match="Invalid authentication token"):
        await auth_middleware.authenticate_endpoint(invalid_credentials, endpoint_manager)


def test_pydantic_validation():
    """Test Pydantic model validation with custom validators."""
    from server.api.endpoints import EndpointRegistrationRequest, RepositoryPackageData
    from pydantic import ValidationError
    from fastapi import HTTPException
    
    # Test valid endpoint registration
    valid_request = EndpointRegistrationRequest(
        name="valid-endpoint",
        hostname="example.com"
    )
    assert valid_request.name == "valid-endpoint"
    assert valid_request.hostname == "example.com"
    
    # Test invalid endpoint name - our validators raise HTTPException, not ValidationError
    with pytest.raises(HTTPException, match="invalid characters"):
        EndpointRegistrationRequest(
            name="invalid@name",  # Contains invalid character
            hostname="example.com"
        )
    
    # Test invalid hostname
    with pytest.raises(HTTPException, match="not a valid hostname"):
        EndpointRegistrationRequest(
            name="valid-name",
            hostname="invalid hostname"  # Contains spaces
        )
    
    # Test valid package data
    valid_package = RepositoryPackageData(
        name="valid-package",
        version="1.0.0-1",
        repository="core",
        architecture="x86_64"
    )
    assert valid_package.name == "valid-package"
    
    # Test invalid package name
    with pytest.raises(HTTPException, match="not a valid package name"):
        RepositoryPackageData(
            name="invalid package name",  # Contains spaces
            version="1.0.0",
            repository="core",
            architecture="x86_64"
        )


if __name__ == "__main__":
    pytest.main([__file__])