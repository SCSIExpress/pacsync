"""
Comprehensive logging configuration for Pacman Sync Utility.

This module provides structured logging with audit trails, operation tracking,
and configurable output formats for both server and client components.
"""

import json
import logging
import logging.handlers
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
from enum import Enum

from shared.exceptions import PacmanSyncError, ErrorSeverity


class LogLevel(Enum):
    """Log level enumeration."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class LogFormat(Enum):
    """Log format enumeration."""
    STANDARD = "standard"
    JSON = "json"
    DETAILED = "detailed"


class AuditEventType(Enum):
    """Types of events that should be audited."""
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    SYNC_OPERATION = "sync_operation"
    PACKAGE_OPERATION = "package_operation"
    CONFIGURATION_CHANGE = "configuration_change"
    SYSTEM_EVENT = "system_event"
    ERROR_EVENT = "error_event"


class StructuredFormatter(logging.Formatter):
    """
    Custom formatter that outputs structured JSON logs with consistent fields.
    """
    
    def __init__(self, include_extra_fields: bool = True):
        super().__init__()
        self.include_extra_fields = include_extra_fields
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as structured JSON."""
        # Base log structure
        log_entry = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        # Add process and thread information
        log_entry['process'] = {
            'pid': os.getpid(),
            'name': getattr(record, 'process_name', 'unknown')
        }
        
        log_entry['thread'] = {
            'id': record.thread,
            'name': record.threadName
        }
        
        # Add exception information if present
        if record.exc_info:
            log_entry['exception'] = {
                'type': record.exc_info[0].__name__ if record.exc_info[0] else None,
                'message': str(record.exc_info[1]) if record.exc_info[1] else None,
                'traceback': self.formatException(record.exc_info) if record.exc_info else None
            }
        
        # Add structured error information if available
        if hasattr(record, 'error_info') and isinstance(record.error_info, PacmanSyncError):
            error = record.error_info
            log_entry['error'] = {
                'code': error.error_code.value,
                'severity': error.severity.value,
                'context': error.context,
                'recovery_actions': [action.value for action in error.recovery_actions],
                'user_message': error.user_message
            }
        
        # Add audit information if present
        if hasattr(record, 'audit_info'):
            log_entry['audit'] = record.audit_info
        
        # Add operation context if present
        if hasattr(record, 'operation_context'):
            log_entry['operation'] = record.operation_context
        
        # Add extra fields if enabled
        if self.include_extra_fields:
            extra_fields = {}
            for key, value in record.__dict__.items():
                if key not in ['name', 'msg', 'args', 'levelname', 'levelno', 'pathname',
                              'filename', 'module', 'lineno', 'funcName', 'created', 'msecs',
                              'relativeCreated', 'thread', 'threadName', 'processName', 'process',
                              'getMessage', 'exc_info', 'exc_text', 'stack_info', 'error_info',
                              'audit_info', 'operation_context']:
                    extra_fields[key] = value
            
            if extra_fields:
                log_entry['extra'] = extra_fields
        
        return json.dumps(log_entry, default=str, ensure_ascii=False)


class DetailedFormatter(logging.Formatter):
    """
    Detailed human-readable formatter with comprehensive information.
    """
    
    def __init__(self):
        super().__init__(
            fmt='%(asctime)s | %(levelname)-8s | %(name)-20s | %(funcName)-15s:%(lineno)-4d | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record with detailed information."""
        formatted = super().format(record)
        
        # Add structured error information if available
        if hasattr(record, 'error_info') and isinstance(record.error_info, PacmanSyncError):
            error = record.error_info
            formatted += f"\n  Error Code: {error.error_code.value}"
            formatted += f"\n  Severity: {error.severity.value}"
            if error.context:
                formatted += f"\n  Context: {json.dumps(error.context, indent=2)}"
            if error.recovery_actions:
                actions = [action.value for action in error.recovery_actions]
                formatted += f"\n  Recovery Actions: {', '.join(actions)}"
        
        # Add audit information if present
        if hasattr(record, 'audit_info'):
            formatted += f"\n  Audit: {json.dumps(record.audit_info, indent=2)}"
        
        # Add operation context if present
        if hasattr(record, 'operation_context'):
            formatted += f"\n  Operation: {json.dumps(record.operation_context, indent=2)}"
        
        return formatted


class AuditLogger:
    """
    Specialized logger for audit events with structured information.
    """
    
    def __init__(self, logger_name: str = "audit"):
        self.logger = logging.getLogger(logger_name)
    
    def log_event(
        self,
        event_type: AuditEventType,
        message: str,
        user_id: Optional[str] = None,
        endpoint_id: Optional[str] = None,
        operation_id: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        result: Optional[str] = None,
        additional_context: Optional[Dict[str, Any]] = None
    ):
        """
        Log an audit event with structured information.
        
        Args:
            event_type: Type of audit event
            message: Human-readable message
            user_id: ID of the user performing the action
            endpoint_id: ID of the endpoint involved
            operation_id: ID of the operation being performed
            resource_type: Type of resource being accessed
            resource_id: ID of the resource being accessed
            result: Result of the operation (success, failure, etc.)
            additional_context: Additional context information
        """
        audit_info = {
            'event_type': event_type.value,
            'timestamp': datetime.now().isoformat(),
            'user_id': user_id,
            'endpoint_id': endpoint_id,
            'operation_id': operation_id,
            'resource': {
                'type': resource_type,
                'id': resource_id
            } if resource_type or resource_id else None,
            'result': result,
            'context': additional_context or {}
        }
        
        # Remove None values
        audit_info = {k: v for k, v in audit_info.items() if v is not None}
        
        # Create log record with audit information
        extra = {'audit_info': audit_info}
        self.logger.info(message, extra=extra)
    
    def log_authentication(
        self,
        endpoint_name: str,
        endpoint_id: Optional[str] = None,
        success: bool = True,
        failure_reason: Optional[str] = None
    ):
        """Log authentication events."""
        self.log_event(
            event_type=AuditEventType.AUTHENTICATION,
            message=f"Authentication {'successful' if success else 'failed'} for endpoint: {endpoint_name}",
            endpoint_id=endpoint_id,
            result="success" if success else "failure",
            additional_context={
                'endpoint_name': endpoint_name,
                'failure_reason': failure_reason
            } if failure_reason else {'endpoint_name': endpoint_name}
        )
    
    def log_sync_operation(
        self,
        operation_type: str,
        endpoint_id: str,
        operation_id: str,
        pool_id: Optional[str] = None,
        result: str = "started",
        packages_affected: Optional[int] = None,
        error_message: Optional[str] = None
    ):
        """Log synchronization operations."""
        context = {
            'operation_type': operation_type,
            'pool_id': pool_id,
            'packages_affected': packages_affected,
            'error_message': error_message
        }
        context = {k: v for k, v in context.items() if v is not None}
        
        self.log_event(
            event_type=AuditEventType.SYNC_OPERATION,
            message=f"Sync operation {operation_type} {result} for endpoint {endpoint_id}",
            endpoint_id=endpoint_id,
            operation_id=operation_id,
            resource_type="sync_operation",
            resource_id=operation_id,
            result=result,
            additional_context=context
        )
    
    def log_package_operation(
        self,
        operation_type: str,
        package_name: str,
        endpoint_id: str,
        result: str = "success",
        version: Optional[str] = None,
        error_message: Optional[str] = None
    ):
        """Log package operations."""
        context = {
            'operation_type': operation_type,
            'package_name': package_name,
            'version': version,
            'error_message': error_message
        }
        context = {k: v for k, v in context.items() if v is not None}
        
        self.log_event(
            event_type=AuditEventType.PACKAGE_OPERATION,
            message=f"Package operation {operation_type} {result} for {package_name}",
            endpoint_id=endpoint_id,
            resource_type="package",
            resource_id=package_name,
            result=result,
            additional_context=context
        )
    
    def log_error(
        self,
        error: PacmanSyncError,
        endpoint_id: Optional[str] = None,
        operation_id: Optional[str] = None
    ):
        """Log error events."""
        self.log_event(
            event_type=AuditEventType.ERROR_EVENT,
            message=f"Error occurred: {error.message}",
            endpoint_id=endpoint_id,
            operation_id=operation_id,
            result="error",
            additional_context={
                'error_code': error.error_code.value,
                'severity': error.severity.value,
                'context': error.context,
                'recovery_actions': [action.value for action in error.recovery_actions]
            }
        )


class OperationLogger:
    """
    Logger for tracking operations with context and performance metrics.
    """
    
    def __init__(self, logger_name: str = "operations"):
        self.logger = logging.getLogger(logger_name)
    
    def log_operation_start(
        self,
        operation_type: str,
        operation_id: str,
        endpoint_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        """Log the start of an operation."""
        operation_context = {
            'operation_id': operation_id,
            'operation_type': operation_type,
            'endpoint_id': endpoint_id,
            'stage': 'started',
            'start_time': datetime.now().isoformat(),
            'context': context or {}
        }
        
        extra = {'operation_context': operation_context}
        self.logger.info(f"Operation {operation_type} started: {operation_id}", extra=extra)
    
    def log_operation_progress(
        self,
        operation_id: str,
        stage: str,
        progress_percentage: Optional[int] = None,
        current_action: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        """Log operation progress."""
        operation_context = {
            'operation_id': operation_id,
            'stage': stage,
            'progress_percentage': progress_percentage,
            'current_action': current_action,
            'timestamp': datetime.now().isoformat(),
            'context': context or {}
        }
        
        extra = {'operation_context': operation_context}
        message = f"Operation {operation_id} progress: {stage}"
        if progress_percentage is not None:
            message += f" ({progress_percentage}%)"
        if current_action:
            message += f" - {current_action}"
        
        self.logger.info(message, extra=extra)
    
    def log_operation_complete(
        self,
        operation_id: str,
        success: bool,
        duration_seconds: Optional[float] = None,
        result_summary: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        """Log operation completion."""
        operation_context = {
            'operation_id': operation_id,
            'stage': 'completed',
            'success': success,
            'duration_seconds': duration_seconds,
            'result_summary': result_summary,
            'end_time': datetime.now().isoformat(),
            'context': context or {}
        }
        
        extra = {'operation_context': operation_context}
        status = "completed successfully" if success else "failed"
        message = f"Operation {operation_id} {status}"
        if duration_seconds:
            message += f" (took {duration_seconds:.2f}s)"
        if result_summary:
            message += f": {result_summary}"
        
        level = logging.INFO if success else logging.ERROR
        self.logger.log(level, message, extra=extra)


def setup_logging(
    log_level: LogLevel = LogLevel.INFO,
    log_format: LogFormat = LogFormat.STANDARD,
    log_file: Optional[str] = None,
    max_file_size: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5,
    enable_console: bool = True,
    enable_audit: bool = True,
    audit_file: Optional[str] = None
) -> Dict[str, logging.Logger]:
    """
    Set up comprehensive logging configuration.
    
    Args:
        log_level: Minimum log level to capture
        log_format: Format for log output
        log_file: Path to main log file (optional)
        max_file_size: Maximum size of log files before rotation
        backup_count: Number of backup files to keep
        enable_console: Whether to enable console logging
        enable_audit: Whether to enable audit logging
        audit_file: Path to audit log file (optional)
        
    Returns:
        Dictionary of configured loggers
    """
    # Clear any existing handlers
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Set root log level
    root_logger.setLevel(getattr(logging, log_level.value))
    
    # Create formatters
    if log_format == LogFormat.JSON:
        formatter = StructuredFormatter()
    elif log_format == LogFormat.DETAILED:
        formatter = DetailedFormatter()
    else:  # STANDARD
        formatter = logging.Formatter(
            fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    
    handlers = []
    
    # Console handler
    if enable_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        handlers.append(console_handler)
    
    # File handler with rotation
    if log_file:
        # Ensure log directory exists
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=max_file_size,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setFormatter(formatter)
        handlers.append(file_handler)
    
    # Add handlers to root logger
    for handler in handlers:
        root_logger.addHandler(handler)
    
    # Set up specialized loggers
    loggers = {
        'root': root_logger,
        'main': logging.getLogger('main'),
        'api': logging.getLogger('api'),
        'database': logging.getLogger('database'),
        'sync': logging.getLogger('sync'),
        'package': logging.getLogger('package'),
        'network': logging.getLogger('network')
    }
    
    # Set up audit logging if enabled
    if enable_audit:
        audit_logger = logging.getLogger('audit')
        audit_logger.setLevel(logging.INFO)
        
        # Use JSON format for audit logs
        audit_formatter = StructuredFormatter()
        
        if audit_file:
            # Ensure audit log directory exists
            audit_path = Path(audit_file)
            audit_path.parent.mkdir(parents=True, exist_ok=True)
            
            audit_handler = logging.handlers.RotatingFileHandler(
                audit_file,
                maxBytes=max_file_size,
                backupCount=backup_count,
                encoding='utf-8'
            )
            audit_handler.setFormatter(audit_formatter)
            audit_logger.addHandler(audit_handler)
        else:
            # Use console if no audit file specified
            audit_console_handler = logging.StreamHandler(sys.stdout)
            audit_console_handler.setFormatter(audit_formatter)
            audit_logger.addHandler(audit_console_handler)
        
        loggers['audit'] = audit_logger
    
    return loggers


def log_structured_error(
    logger: logging.Logger,
    error: PacmanSyncError,
    endpoint_id: Optional[str] = None,
    operation_id: Optional[str] = None
):
    """
    Log a structured error with full context information.
    
    Args:
        logger: Logger instance to use
        error: The structured error to log
        endpoint_id: Optional endpoint ID for context
        operation_id: Optional operation ID for context
    """
    extra = {
        'error_info': error,
        'endpoint_id': endpoint_id,
        'operation_id': operation_id
    }
    
    logger.error(error.message, extra=extra)


def create_operation_context(
    operation_type: str,
    operation_id: str,
    endpoint_id: Optional[str] = None,
    additional_context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Create operation context for logging.
    
    Args:
        operation_type: Type of operation
        operation_id: Unique operation identifier
        endpoint_id: Optional endpoint ID
        additional_context: Additional context information
        
    Returns:
        Operation context dictionary
    """
    context = {
        'operation_type': operation_type,
        'operation_id': operation_id,
        'endpoint_id': endpoint_id,
        'timestamp': datetime.now().isoformat()
    }
    
    if additional_context:
        context.update(additional_context)
    
    return {k: v for k, v in context.items() if v is not None}