"""
Rate limiting middleware for the Pacman Sync Utility Server.

This module provides rate limiting functionality to prevent abuse of API endpoints,
with support for different rate limits per endpoint type and client identification.
"""

import logging
import time
from typing import Dict, Optional, Tuple
from collections import defaultdict, deque
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Token bucket rate limiter with sliding window.
    
    Supports different rate limits for different endpoint types and tracks
    usage per client IP address or authenticated endpoint.
    """
    
    def __init__(self, requests_per_minute: int = 60, burst_size: Optional[int] = None):
        self.requests_per_minute = requests_per_minute
        self.burst_size = burst_size or requests_per_minute
        self.window_size = 60  # 1 minute window
        
        # Storage for rate limiting data
        # Format: {client_id: deque([(timestamp, request_count), ...])}
        self._request_history: Dict[str, deque] = defaultdict(lambda: deque())
        self._last_cleanup = time.time()
        
    def _cleanup_old_entries(self, current_time: float) -> None:
        """Remove old entries from request history."""
        cutoff_time = current_time - self.window_size
        
        for client_id in list(self._request_history.keys()):
            history = self._request_history[client_id]
            
            # Remove old entries
            while history and history[0][0] < cutoff_time:
                history.popleft()
            
            # Remove empty histories
            if not history:
                del self._request_history[client_id]
    
    def _get_client_id(self, request: Request) -> str:
        """
        Get client identifier for rate limiting.
        
        Uses authenticated endpoint ID if available, otherwise falls back to IP address.
        """
        # Try to get endpoint ID from authentication
        if hasattr(request.state, 'endpoint') and request.state.endpoint:
            return f"endpoint:{request.state.endpoint.id}"
        
        # Fall back to IP address
        client_ip = request.client.host if request.client else "unknown"
        
        # Check for forwarded IP headers (for reverse proxy setups)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            client_ip = forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            client_ip = real_ip.strip()
        
        return f"ip:{client_ip}"
    
    def is_allowed(self, request: Request) -> Tuple[bool, Dict[str, any]]:
        """
        Check if request is allowed based on rate limits.
        
        Args:
            request: FastAPI request object
            
        Returns:
            Tuple of (is_allowed, rate_limit_info)
        """
        current_time = time.time()
        client_id = self._get_client_id(request)
        
        # Periodic cleanup of old entries
        if current_time - self._last_cleanup > 60:  # Cleanup every minute
            self._cleanup_old_entries(current_time)
            self._last_cleanup = current_time
        
        # Get request history for this client
        history = self._request_history[client_id]
        
        # Remove old entries for this client
        cutoff_time = current_time - self.window_size
        while history and history[0][0] < cutoff_time:
            history.popleft()
        
        # Count requests in current window
        current_requests = sum(count for _, count in history)
        
        # Check if request is allowed
        is_allowed = current_requests < self.requests_per_minute
        
        if is_allowed:
            # Add current request to history
            history.append((current_time, 1))
            current_requests += 1
        
        # Calculate rate limit info
        remaining = max(0, self.requests_per_minute - current_requests)
        reset_time = int(current_time + self.window_size)
        
        rate_limit_info = {
            'limit': self.requests_per_minute,
            'remaining': remaining,
            'reset': reset_time,
            'retry_after': self.window_size if not is_allowed else None
        }
        
        return is_allowed, rate_limit_info
    
    def get_rate_limit_headers(self, rate_limit_info: Dict[str, any]) -> Dict[str, str]:
        """Get rate limit headers for response."""
        headers = {
            'X-RateLimit-Limit': str(rate_limit_info['limit']),
            'X-RateLimit-Remaining': str(rate_limit_info['remaining']),
            'X-RateLimit-Reset': str(rate_limit_info['reset'])
        }
        
        if rate_limit_info['retry_after']:
            headers['Retry-After'] = str(int(rate_limit_info['retry_after']))
        
        return headers


class RateLimitMiddleware:
    """
    FastAPI middleware for rate limiting.
    
    Applies different rate limits based on endpoint patterns and client type.
    """
    
    def __init__(self, default_limit: int = 60):
        self.default_limiter = RateLimiter(default_limit)
        
        # Different rate limits for different endpoint types
        self.endpoint_limiters = {
            # Authentication endpoints - more restrictive
            '/api/endpoints/register': RateLimiter(10),  # 10 registrations per minute
            
            # Status update endpoints - moderate
            '/api/endpoints/*/status': RateLimiter(120),  # 2 per second
            
            # Sync operation endpoints - more restrictive
            '/api/sync/*/sync-to-latest': RateLimiter(30),  # 30 per minute
            '/api/sync/*/set-as-latest': RateLimiter(30),
            '/api/sync/*/revert': RateLimiter(30),
            
            # Repository submission - moderate
            '/api/endpoints/*/repositories': RateLimiter(60),  # 1 per second
            
            # Admin operations - restrictive
            '/api/pools': RateLimiter(30),  # Pool management
            '/api/repositories/analyze': RateLimiter(10),  # Analysis operations
        }
    
    def _get_limiter_for_path(self, path: str) -> RateLimiter:
        """Get appropriate rate limiter for request path."""
        # Check for exact matches first
        if path in self.endpoint_limiters:
            return self.endpoint_limiters[path]
        
        # Check for pattern matches
        for pattern, limiter in self.endpoint_limiters.items():
            if '*' in pattern:
                # Simple wildcard matching
                pattern_parts = pattern.split('*')
                if len(pattern_parts) == 2:
                    prefix, suffix = pattern_parts
                    if path.startswith(prefix) and path.endswith(suffix):
                        return limiter
        
        return self.default_limiter
    
    async def __call__(self, request: Request, call_next):
        """Process request with rate limiting."""
        # Get appropriate rate limiter
        limiter = self._get_limiter_for_path(request.url.path)
        
        # Check rate limit
        is_allowed, rate_limit_info = limiter.is_allowed(request)
        
        if not is_allowed:
            # Rate limit exceeded
            logger.warning(f"Rate limit exceeded for {limiter._get_client_id(request)} on {request.url.path}")
            
            headers = limiter.get_rate_limit_headers(rate_limit_info)
            
            return JSONResponse(
                status_code=429,
                content={
                    "error": {
                        "code": "RATE_LIMIT_EXCEEDED",
                        "message": "Too many requests. Please try again later.",
                        "details": {
                            "limit": rate_limit_info['limit'],
                            "window": "1 minute",
                            "retry_after": rate_limit_info['retry_after']
                        },
                        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                    }
                },
                headers=headers
            )
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers to response
        headers = limiter.get_rate_limit_headers(rate_limit_info)
        for key, value in headers.items():
            response.headers[key] = value
        
        return response


def create_rate_limit_middleware(
    default_limit: int = 60,
    endpoint_limits: Optional[Dict[str, int]] = None
) -> RateLimitMiddleware:
    """
    Create rate limiting middleware with custom configuration.
    
    Args:
        default_limit: Default requests per minute
        endpoint_limits: Custom limits for specific endpoints
        
    Returns:
        Configured rate limiting middleware
    """
    middleware = RateLimitMiddleware(default_limit)
    
    if endpoint_limits:
        for endpoint, limit in endpoint_limits.items():
            middleware.endpoint_limiters[endpoint] = RateLimiter(limit)
    
    return middleware