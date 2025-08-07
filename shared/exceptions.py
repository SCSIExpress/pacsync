"""
Comprehensive exception hierarchy for Pacman Sync Utility.

This module defines structured exceptions with error codes, context information,
and recovery suggestions for consistent error handling across the system.
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum


class ErrorCode(Enum):
    """Standardized error codes for the Pacman Sync Utility."""
    
    # Authentication and Authorization Errors (1000-1099)
    AUTH_INVALID_TOKEN = "AUTH_1001"
    AUTH_TOKEN_EXPIRED = "AUTH_1002"
    AUTH_INSUFFICIENT_PERMISSIONS = "AUTH_1003"
    AUTH_ENDPOINT_NOT_FOUND = "AUTH_1004"
    AUTH_REGISTRATION_FAILED = "AUTH_1005"
    
    # Network and Communication Errors (2000-2099)
    NETWORK_CONNECTION_FAILED = "NETWORK_2001"
    NETWORK_TIMEOUT = "NETWORK_2002"
    NETWORK_DNS_RESOLUTION_FAILED = "NETWORK_2003"
    NETWORK_SSL_ERROR = "NETWORK_2004"
    NETWORK_PROXY_ERROR = "NETWORK_2005"
    
    # Database Errors (3000-3099)
    DATABASE_CONNECTION_FAILED = "DATABASE_3001"
    DATABASE_QUERY_FAILED = "DATABASE_3002"
    DATABASE_CONSTRAINT_VIOLATION = "DATABASE_3003"
    DATABASE_MIGRATION_FAILED = "DATABASE_3004"
    DATABASE_TRANSACTION_FAILED = "DATABASE_3005"
    
    # Validation Errors (4000-4099)
    VALIDATION_INVALID_INPUT = "VALIDATION_4001"
    VALIDATION_MISSING_REQUIRED_FIELD = "VALIDATION_4002"
    VALIDATION_INVALID_FORMAT = "VALIDATION_4003"
    VALIDATION_VALUE_OUT_OF_RANGE = "VALIDATION_4004"
    VALIDATION_DUPLICATE_VALUE = "VALIDATION_4005"
    
    # Package Management Errors (5000-5099)
    PACKAGE_NOT_FOUND = "PACKAGE_5001"
    PACKAGE_DEPENDENCY_CONFLICT = "PACKAGE_5002"
    PACKAGE_INSTALLATION_FAILED = "PACKAGE_5003"
    PACKAGE_REMOVAL_FAILED = "PACKAGE_5004"
    PACKAGE_VERSION_CONFLICT = "PACKAGE_5005"
    PACKAGE_REPOSITORY_UNAVAILABLE = "PACKAGE_5006"
    
    # Synchronization Errors (6000-6099)
    SYNC_OPERATION_FAILED = "SYNC_6001"
    SYNC_STATE_CONFLICT = "SYNC_6002"
    SYNC_TARGET_UNREACHABLE = "SYNC_6003"
    SYNC_POOL_NOT_FOUND = "SYNC_6004"
    SYNC_ENDPOINT_OFFLINE = "SYNC_6005"
    SYNC_OPERATION_CANCELLED = "SYNC_6006"
    
    # System Integration Errors (7000-7099)
    SYSTEM_TRAY_UNAVAILABLE = "SYSTEM_7001"
    SYSTEM_PACMAN_NOT_FOUND = "SYSTEM_7002"
    SYSTEM_PERMISSION_DENIED = "SYSTEM_7003"
    SYSTEM_DISK_SPACE_INSUFFICIENT = "SYSTEM_7004"
    SYSTEM_SERVICE_UNAVAILABLE = "SYSTEM_7005"
    
    # Configuration Errors (8000-8099)
    CONFIG_FILE_NOT_FOUND = "CONFIG_8001"
    CONFIG_INVALID_FORMAT = "CONFIG_8002"
    CONFIG_MISSING_REQUIRED_SETTING = "CONFIG_8003"
    CONFIG_INVALID_VALUE = "CONFIG_8004"
    
    # Internal Server Errors (9000-9099)
    INTERNAL_UNEXPECTED_ERROR = "INTERNAL_9001"
    INTERNAL_SERVICE_UNAVAILABLE = "INTERNAL_9002"
    INTERNAL_RESOURCE_EXHAUSTED = "INTERNAL_9003"
    INTERNAL_OPERATION_TIMEOUT = "INTERNAL_9004"


class ErrorSeverity(Enum):
    """Error severity levels for logging and handling."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RecoveryAction(Enum):
    """Suggested recovery actions for errors."""
    RETRY = "retry"
    RETRY_WITH_BACKOFF = "retry_with_backoff"
    RECONNECT = "reconnect"
    REFRESH_TOKEN = "refresh_token"
    USER_INTERVENTION = "user_intervention"
    RESTART_SERVICE = "restart_service"
    CONTACT_ADMIN = "contact_admin"
    IGNORE = "ignore"


class PacmanSyncError(Exception):
    """
    Base exception class for all Pacman Sync Utility errors.
    
    Provides structured error information including error codes, context,
    and recovery suggestions for consistent error handling.
    """
    
    def __init__(
        self,
        message: str,
        error_code: ErrorCode,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        context: Optional[Dict[str, Any]] = None,
        recovery_actions: Optional[List[RecoveryAction]] = None,
        cause: Optional[Exception] = None,
        user_message: Optional[str] = None
    ):
        super().__init__(message)
        
        self.message = message
        self.error_code = error_code
        self.severity = severity
        self.context = context or {}
        self.recovery_actions = recovery_actions or []
        self.cause = cause
        self.user_message = user_message or message
        self.timestamp = datetime.now()
        
        # Add cause information to context if available
        if cause:
            self.context['cause_type'] = type(cause).__name__
            self.context['cause_message'] = str(cause)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary format for serialization."""
        return {
            'error': {
                'code': self.error_code.value,
                'message': self.message,
                'user_message': self.user_message,
                'severity': self.severity.value,
                'timestamp': self.timestamp.isoformat(),
                'context': self.context,
                'recovery_actions': [action.value for action in self.recovery_actions],
                'cause': {
                    'type': self.context.get('cause_type'),
                    'message': self.context.get('cause_message')
                } if self.cause else None
            }
        }
    
    def get_http_status_code(self) -> int:
        """Get appropriate HTTP status code for this error."""
        code_mapping = {
            # Authentication errors -> 401
            ErrorCode.AUTH_INVALID_TOKEN: 401,
            ErrorCode.AUTH_TOKEN_EXPIRED: 401,
            ErrorCode.AUTH_ENDPOINT_NOT_FOUND: 401,
            ErrorCode.AUTH_REGISTRATION_FAILED: 401,
            
            # Authorization errors -> 403
            ErrorCode.AUTH_INSUFFICIENT_PERMISSIONS: 403,
            
            # Validation errors -> 400
            ErrorCode.VALIDATION_INVALID_INPUT: 400,
            ErrorCode.VALIDATION_MISSING_REQUIRED_FIELD: 400,
            ErrorCode.VALIDATION_INVALID_FORMAT: 400,
            ErrorCode.VALIDATION_VALUE_OUT_OF_RANGE: 400,
            ErrorCode.VALIDATION_DUPLICATE_VALUE: 409,
            
            # Not found errors -> 404
            ErrorCode.PACKAGE_NOT_FOUND: 404,
            ErrorCode.SYNC_POOL_NOT_FOUND: 404,
            
            # Conflict errors -> 409
            ErrorCode.PACKAGE_DEPENDENCY_CONFLICT: 409,
            ErrorCode.PACKAGE_VERSION_CONFLICT: 409,
            ErrorCode.SYNC_STATE_CONFLICT: 409,
            
            # Service unavailable -> 503
            ErrorCode.INTERNAL_SERVICE_UNAVAILABLE: 503,
            ErrorCode.SYSTEM_SERVICE_UNAVAILABLE: 503,
            ErrorCode.PACKAGE_REPOSITORY_UNAVAILABLE: 503,
            
            # Timeout errors -> 408
            ErrorCode.NETWORK_TIMEOUT: 408,
            ErrorCode.INTERNAL_OPERATION_TIMEOUT: 408,
        }
        
        return code_mapping.get(self.error_code, 500)


# Specific exception classes for different error categories

class AuthenticationError(PacmanSyncError):
    """Authentication and authorization related errors."""
    
    def __init__(self, message: str, error_code: ErrorCode, **kwargs):
        super().__init__(
            message=message,
            error_code=error_code,
            severity=ErrorSeverity.HIGH,
            recovery_actions=[RecoveryAction.REFRESH_TOKEN, RecoveryAction.RECONNECT],
            **kwargs
        )


class NetworkError(PacmanSyncError):
    """Network and communication related errors."""
    
    def __init__(self, message: str, error_code: ErrorCode, **kwargs):
        super().__init__(
            message=message,
            error_code=error_code,
            severity=ErrorSeverity.MEDIUM,
            recovery_actions=[RecoveryAction.RETRY_WITH_BACKOFF, RecoveryAction.RECONNECT],
            **kwargs
        )


class DatabaseError(PacmanSyncError):
    """Database operation related errors."""
    
    def __init__(self, message: str, error_code: ErrorCode, **kwargs):
        super().__init__(
            message=message,
            error_code=error_code,
            severity=ErrorSeverity.HIGH,
            recovery_actions=[RecoveryAction.RETRY, RecoveryAction.RESTART_SERVICE],
            **kwargs
        )


class ValidationError(PacmanSyncError):
    """Input validation related errors."""
    
    def __init__(self, message: str, field_name: Optional[str] = None, **kwargs):
        # Extract context from kwargs to avoid duplicate parameter
        context = kwargs.pop('context', {})
        if field_name:
            context['field_name'] = field_name
        
        # Set default values if not provided
        error_code = kwargs.pop('error_code', ErrorCode.VALIDATION_INVALID_INPUT)
        severity = kwargs.pop('severity', ErrorSeverity.LOW)
        recovery_actions = kwargs.pop('recovery_actions', [RecoveryAction.USER_INTERVENTION])
        
        super().__init__(
            message=message,
            error_code=error_code,
            severity=severity,
            recovery_actions=recovery_actions,
            context=context,
            **kwargs
        )


class PackageError(PacmanSyncError):
    """Package management related errors."""
    
    def __init__(self, message: str, error_code: ErrorCode, package_name: Optional[str] = None, **kwargs):
        context = kwargs.get('context', {})
        if package_name:
            context['package_name'] = package_name
        
        super().__init__(
            message=message,
            error_code=error_code,
            severity=ErrorSeverity.MEDIUM,
            recovery_actions=[RecoveryAction.RETRY, RecoveryAction.USER_INTERVENTION],
            context=context,
            **kwargs
        )


class SynchronizationError(PacmanSyncError):
    """Synchronization operation related errors."""
    
    def __init__(self, message: str, error_code: ErrorCode, operation_id: Optional[str] = None, **kwargs):
        context = kwargs.get('context', {})
        if operation_id:
            context['operation_id'] = operation_id
        
        super().__init__(
            message=message,
            error_code=error_code,
            severity=ErrorSeverity.MEDIUM,
            recovery_actions=[RecoveryAction.RETRY, RecoveryAction.USER_INTERVENTION],
            context=context,
            **kwargs
        )


class SystemIntegrationError(PacmanSyncError):
    """System integration related errors."""
    
    def __init__(self, message: str, error_code: ErrorCode, **kwargs):
        super().__init__(
            message=message,
            error_code=error_code,
            severity=ErrorSeverity.MEDIUM,
            recovery_actions=[RecoveryAction.USER_INTERVENTION, RecoveryAction.IGNORE],
            **kwargs
        )


class ConfigurationError(PacmanSyncError):
    """Configuration related errors."""
    
    def __init__(self, message: str, error_code: ErrorCode, config_key: Optional[str] = None, **kwargs):
        context = kwargs.get('context', {})
        if config_key:
            context['config_key'] = config_key
        
        super().__init__(
            message=message,
            error_code=error_code,
            severity=ErrorSeverity.HIGH,
            recovery_actions=[RecoveryAction.USER_INTERVENTION, RecoveryAction.CONTACT_ADMIN],
            context=context,
            **kwargs
        )


def create_error_response(error: PacmanSyncError) -> Dict[str, Any]:
    """
    Create a standardized error response dictionary from an exception.
    
    Args:
        error: The PacmanSyncError exception
        
    Returns:
        Standardized error response dictionary
    """
    return error.to_dict()


def handle_exception(
    exception: Exception,
    context: Optional[Dict[str, Any]] = None,
    default_error_code: ErrorCode = ErrorCode.INTERNAL_UNEXPECTED_ERROR
) -> PacmanSyncError:
    """
    Convert a generic exception to a structured PacmanSyncError.
    
    Args:
        exception: The original exception
        context: Additional context information
        default_error_code: Default error code if specific mapping not found
        
    Returns:
        Structured PacmanSyncError
    """
    if isinstance(exception, PacmanSyncError):
        return exception
    
    # Map common exception types to structured errors
    exception_mapping = {
        ConnectionError: (ErrorCode.NETWORK_CONNECTION_FAILED, NetworkError),
        TimeoutError: (ErrorCode.NETWORK_TIMEOUT, NetworkError),
        PermissionError: (ErrorCode.SYSTEM_PERMISSION_DENIED, SystemIntegrationError),
        FileNotFoundError: (ErrorCode.CONFIG_FILE_NOT_FOUND, ConfigurationError),
        ValueError: (ErrorCode.VALIDATION_INVALID_INPUT, ValidationError),
    }
    
    error_code, error_class = exception_mapping.get(
        type(exception), 
        (default_error_code, PacmanSyncError)
    )
    
    return error_class(
        message=str(exception),
        error_code=error_code,
        context=context,
        cause=exception
    )