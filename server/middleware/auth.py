"""
Authentication middleware for the Pacman Sync Utility Server.

This module provides JWT-based authentication middleware for FastAPI endpoints,
including token validation, endpoint authentication, and security headers.
"""

import logging
from datetime import datetime
from typing import Optional, Dict, Any
from fastapi import HTTPException, Request, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError

from shared.models import Endpoint
from server.core.endpoint_manager import EndpointManager, EndpointAuthenticationError

logger = logging.getLogger(__name__)

# HTTP Bearer token scheme
security = HTTPBearer(auto_error=False)


class AuthenticationMiddleware:
    """JWT authentication middleware for endpoint authentication."""
    
    def __init__(self, jwt_secret: str):
        self.jwt_secret = jwt_secret
    
    def verify_token(self, token: str) -> Dict[str, Any]:
        """
        Verify JWT token and return payload.
        
        Args:
            token: JWT token string
            
        Returns:
            Token payload dictionary
            
        Raises:
            HTTPException: On authentication failure
        """
        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=['HS256'])
            
            # Check expiration
            expires_at = payload.get('expires_at', 0)
            if expires_at < datetime.now().timestamp():
                raise HTTPException(
                    status_code=401,
                    detail="Token expired",
                    headers={"WWW-Authenticate": "Bearer"}
                )
            
            return payload
            
        except JWTError as e:
            logger.warning(f"JWT verification failed: {e}")
            raise HTTPException(
                status_code=401,
                detail="Invalid authentication token",
                headers={"WWW-Authenticate": "Bearer"}
            )
    
    async def authenticate_endpoint(
        self,
        credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
        endpoint_manager: EndpointManager = None
    ) -> Endpoint:
        """
        Authenticate endpoint using Bearer token.
        
        Args:
            credentials: HTTP authorization credentials
            endpoint_manager: Endpoint manager instance
            
        Returns:
            Authenticated endpoint
            
        Raises:
            HTTPException: On authentication failure
        """
        if not credentials:
            raise HTTPException(
                status_code=401,
                detail="Authentication required",
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        if not endpoint_manager:
            raise HTTPException(
                status_code=500,
                detail="Authentication service unavailable"
            )
        
        try:
            # Verify token
            payload = self.verify_token(credentials.credentials)
            endpoint_id = payload.get('endpoint_id')
            
            if not endpoint_id:
                raise HTTPException(
                    status_code=401,
                    detail="Invalid token: missing endpoint_id",
                    headers={"WWW-Authenticate": "Bearer"}
                )
            
            # Get endpoint from database
            endpoint = await endpoint_manager.get_endpoint(endpoint_id)
            if not endpoint:
                raise HTTPException(
                    status_code=401,
                    detail="Endpoint not found",
                    headers={"WWW-Authenticate": "Bearer"}
                )
            
            # Update last seen timestamp
            await endpoint_manager.update_last_seen(endpoint_id, datetime.now())
            
            return endpoint
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            raise HTTPException(
                status_code=401,
                detail="Authentication failed",
                headers={"WWW-Authenticate": "Bearer"}
            )


class AdminAuthenticationMiddleware:
    """Authentication middleware for admin operations."""
    
    def __init__(self, jwt_secret: str, admin_tokens: Optional[list] = None):
        self.jwt_secret = jwt_secret
        self.admin_tokens = admin_tokens or []
    
    async def authenticate_admin(
        self,
        credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
    ) -> Dict[str, Any]:
        """
        Authenticate admin user.
        
        Args:
            credentials: HTTP authorization credentials
            
        Returns:
            Admin user information
            
        Raises:
            HTTPException: On authentication failure
        """
        if not credentials:
            raise HTTPException(
                status_code=401,
                detail="Admin authentication required",
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        token = credentials.credentials
        
        # Check if it's a static admin token
        if token in self.admin_tokens:
            return {
                'user_type': 'admin',
                'token_type': 'static',
                'authenticated_at': datetime.now().timestamp()
            }
        
        # Try to verify as JWT token
        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=['HS256'])
            
            # Check if it's an admin token
            if payload.get('user_type') != 'admin':
                raise HTTPException(
                    status_code=403,
                    detail="Admin privileges required"
                )
            
            # Check expiration
            expires_at = payload.get('expires_at', 0)
            if expires_at < datetime.now().timestamp():
                raise HTTPException(
                    status_code=401,
                    detail="Admin token expired",
                    headers={"WWW-Authenticate": "Bearer"}
                )
            
            return payload
            
        except JWTError as e:
            logger.warning(f"Admin JWT verification failed: {e}")
            raise HTTPException(
                status_code=401,
                detail="Invalid admin authentication token",
                headers={"WWW-Authenticate": "Bearer"}
            )


def create_auth_dependencies(jwt_secret: str, admin_tokens: Optional[list] = None):
    """
    Create authentication dependency functions.
    
    Args:
        jwt_secret: JWT secret key
        admin_tokens: List of static admin tokens
        
    Returns:
        Tuple of (endpoint_auth, admin_auth) dependency functions
    """
    auth_middleware = AuthenticationMiddleware(jwt_secret)
    admin_middleware = AdminAuthenticationMiddleware(jwt_secret, admin_tokens)
    
    async def authenticate_endpoint(
        request: Request,
        credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
    ) -> Endpoint:
        """Dependency for endpoint authentication."""
        endpoint_manager = getattr(request.app.state, 'endpoint_manager', None)
        return await auth_middleware.authenticate_endpoint(credentials, endpoint_manager)
    
    async def authenticate_admin(
        credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
    ) -> Dict[str, Any]:
        """Dependency for admin authentication."""
        return await admin_middleware.authenticate_admin(credentials)
    
    return authenticate_endpoint, authenticate_admin


def add_security_headers(response, request: Request):
    """Add security headers to response."""
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    
    # Add HSTS header for HTTPS
    if request.url.scheme == "https":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    
    return response