"""
Operation tracking middleware for comprehensive audit trails.

This module provides middleware to track operations with unique IDs,
context information, and performance metrics for audit and debugging purposes.
"""

import logging
import time
import uuid
from datetime import datetime
from typing import Optional, Dict, Any
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from shared.logging_config import OperationLogger, AuditLogger, AuditEventType

logger = logging.getLogger(__name__)


class OperationTrackingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to track operations with unique IDs and context information.
    
    This middleware:
    - Assigns unique operation IDs to requests
    - Tracks operation start/end times and performance
    - Logs operation context and results
    - Provides audit trail for all API operations
    """
    
    def __init__(self, app, enable_performance_logging: bool = True):
        super().__init__(app)
        self.enable_performance_logging = enable_performance_logging
        self.operation_logger = OperationLogger("api_operations")
        self.audit_logger = AuditLogger("api_audit")
    
    async def dispatch(self, request: Request, call_next):
        """Process request with operation tracking."""
        # Generate unique operation ID
        operation_id = str(uuid.uuid4())
        request.state.operation_id = operation_id
        
        # Extract operation context
        operation_type = self._determine_operation_type(request)
        endpoint_id = self._extract_endpoint_id(request)
        
        # Record operation start
        start_time = time.time()
        
        # Log operation start
        self.operation_logger.log_operation_start(
            operation_type=operation_type,
            operation_id=operation_id,
            endpoint_id=endpoint_id,
            context={
                'method': request.method,
                'path': str(request.url.path),
                'query_params': dict(request.query_params),
                'client_host': request.client.host if request.client else None,
                'user_agent': request.headers.get('user-agent'),
                'content_type': request.headers.get('content-type')
            }
        )
        
        # Audit log for sensitive operations
        if self._is_sensitive_operation(request):
            self.audit_logger.log_event(
                event_type=AuditEventType.SYSTEM_EVENT,
                message=f"API operation started: {operation_type}",
                endpoint_id=endpoint_id,
                operation_id=operation_id,
                resource_type="api_endpoint",
                resource_id=str(request.url.path),
                additional_context={
                    'method': request.method,
                    'client_host': request.client.host if request.client else None
                }
            )
        
        try:
            # Process the request
            response = await call_next(request)
            
            # Calculate duration
            duration = time.time() - start_time
            
            # Determine success based on status code
            success = 200 <= response.status_code < 400
            
            # Create result summary
            result_summary = f"HTTP {response.status_code}"
            if not success:
                result_summary += f" - {self._get_error_category(response.status_code)}"
            
            # Log operation completion
            self.operation_logger.log_operation_complete(
                operation_id=operation_id,
                success=success,
                duration_seconds=duration,
                result_summary=result_summary,
                context={
                    'status_code': response.status_code,
                    'response_size': response.headers.get('content-length'),
                    'content_type': response.headers.get('content-type')
                }
            )
            
            # Audit log for sensitive operations
            if self._is_sensitive_operation(request):
                self.audit_logger.log_event(
                    event_type=AuditEventType.SYSTEM_EVENT,
                    message=f"API operation completed: {operation_type}",
                    endpoint_id=endpoint_id,
                    operation_id=operation_id,
                    resource_type="api_endpoint",
                    resource_id=str(request.url.path),
                    result="success" if success else "failure",
                    additional_context={
                        'status_code': response.status_code,
                        'duration_seconds': duration
                    }
                )
            
            # Add operation ID to response headers
            response.headers['X-Operation-ID'] = operation_id
            
            # Add performance headers if enabled
            if self.enable_performance_logging:
                response.headers['X-Response-Time'] = f"{duration:.3f}s"
            
            return response
            
        except Exception as e:
            # Calculate duration for failed requests
            duration = time.time() - start_time
            
            # Log operation failure
            self.operation_logger.log_operation_complete(
                operation_id=operation_id,
                success=False,
                duration_seconds=duration,
                result_summary=f"Exception: {type(e).__name__}",
                context={
                    'exception_type': type(e).__name__,
                    'exception_message': str(e)
                }
            )
            
            # Audit log for failed sensitive operations
            if self._is_sensitive_operation(request):
                self.audit_logger.log_event(
                    event_type=AuditEventType.ERROR_EVENT,
                    message=f"API operation failed: {operation_type}",
                    endpoint_id=endpoint_id,
                    operation_id=operation_id,
                    resource_type="api_endpoint",
                    resource_id=str(request.url.path),
                    result="error",
                    additional_context={
                        'exception_type': type(e).__name__,
                        'exception_message': str(e),
                        'duration_seconds': duration
                    }
                )
            
            # Re-raise the exception
            raise
    
    def _determine_operation_type(self, request: Request) -> str:
        """Determine operation type from request."""
        path = str(request.url.path)
        method = request.method
        
        # Map common API patterns to operation types
        if '/sync/' in path:
            if 'sync-to-latest' in path:
                return 'sync_to_latest'
            elif 'set-as-latest' in path:
                return 'set_as_latest'
            elif 'revert' in path:
                return 'revert_to_previous'
            else:
                return 'sync_operation'
        
        elif '/pools' in path:
            if method == 'POST':
                return 'create_pool'
            elif method == 'PUT':
                return 'update_pool'
            elif method == 'DELETE':
                return 'delete_pool'
            else:
                return 'pool_management'
        
        elif '/endpoints' in path:
            if 'register' in path:
                return 'endpoint_registration'
            elif method == 'POST':
                return 'create_endpoint'
            elif method == 'PUT':
                return 'update_endpoint'
            elif method == 'DELETE':
                return 'delete_endpoint'
            else:
                return 'endpoint_management'
        
        elif '/repositories' in path:
            return 'repository_analysis'
        
        elif '/health' in path:
            return 'health_check'
        
        else:
            return f"{method.lower()}_{path.replace('/', '_').strip('_')}"
    
    def _extract_endpoint_id(self, request: Request) -> Optional[str]:
        """Extract endpoint ID from request context."""
        # Try to get from authenticated endpoint
        if hasattr(request.state, 'current_endpoint'):
            return request.state.current_endpoint.id
        
        # Try to extract from path parameters
        path_parts = str(request.url.path).split('/')
        for i, part in enumerate(path_parts):
            if part in ['endpoints', 'sync'] and i + 1 < len(path_parts):
                # Next part might be endpoint ID
                potential_id = path_parts[i + 1]
                if self._looks_like_uuid(potential_id):
                    return potential_id
        
        return None
    
    def _looks_like_uuid(self, value: str) -> bool:
        """Check if a string looks like a UUID."""
        try:
            uuid.UUID(value)
            return True
        except ValueError:
            return False
    
    def _is_sensitive_operation(self, request: Request) -> bool:
        """Determine if operation should be audit logged."""
        path = str(request.url.path)
        method = request.method
        
        # Audit log for:
        # - Authentication operations
        # - Sync operations
        # - Pool/endpoint management
        # - Configuration changes
        
        sensitive_patterns = [
            '/auth',
            '/register',
            '/sync/',
            '/pools',
            '/endpoints'
        ]
        
        # Always audit non-GET operations on sensitive endpoints
        if method != 'GET':
            return any(pattern in path for pattern in sensitive_patterns)
        
        # Audit specific GET operations
        if '/sync/' in path or '/auth' in path:
            return True
        
        return False
    
    def _get_error_category(self, status_code: int) -> str:
        """Get error category from HTTP status code."""
        if status_code == 400:
            return "Bad Request"
        elif status_code == 401:
            return "Unauthorized"
        elif status_code == 403:
            return "Forbidden"
        elif status_code == 404:
            return "Not Found"
        elif status_code == 409:
            return "Conflict"
        elif status_code == 422:
            return "Validation Error"
        elif status_code == 429:
            return "Rate Limited"
        elif 400 <= status_code < 500:
            return "Client Error"
        elif status_code == 500:
            return "Internal Server Error"
        elif status_code == 502:
            return "Bad Gateway"
        elif status_code == 503:
            return "Service Unavailable"
        elif status_code == 504:
            return "Gateway Timeout"
        elif 500 <= status_code < 600:
            return "Server Error"
        else:
            return "Unknown Error"


def create_operation_tracking_middleware(
    enable_performance_logging: bool = True
) -> OperationTrackingMiddleware:
    """
    Create operation tracking middleware with configuration.
    
    Args:
        enable_performance_logging: Whether to include performance metrics
        
    Returns:
        Configured middleware instance
    """
    return lambda app: OperationTrackingMiddleware(
        app, 
        enable_performance_logging=enable_performance_logging
    )