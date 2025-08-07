"""
Input validation middleware for the Pacman Sync Utility Server.

This module provides comprehensive input validation functions and middleware
for API endpoints with detailed error messages and security considerations.
"""

import re
import ipaddress
import logging
from typing import Any, Optional
from urllib.parse import urlparse
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse

from shared.exceptions import (
    ValidationError, ErrorCode, create_error_response, handle_exception
)
from shared.logging_config import log_structured_error

logger = logging.getLogger(__name__)


def validate_endpoint_name(name: str) -> str:
    """
    Validate endpoint name format.
    
    Args:
        name: Endpoint name to validate
        
    Returns:
        Validated and normalized name
        
    Raises:
        ValidationError: If name is invalid
    """
    if not name or not isinstance(name, str):
        raise ValidationError(
            "Endpoint name must be a non-empty string",
            field_name="endpoint_name",
            context={'provided_value': name, 'expected_type': 'string'}
        )
    
    name = name.strip()
    
    if len(name) < 1 or len(name) > 255:
        raise ValidationError(
            "Endpoint name must be between 1 and 255 characters",
            field_name="endpoint_name",
            context={'provided_length': len(name), 'min_length': 1, 'max_length': 255}
        )
    
    # Allow alphanumeric, hyphens, underscores, and dots
    if not re.match(r'^[a-zA-Z0-9._-]+$', name):
        raise ValidationError(
            "Endpoint name can only contain letters, numbers, dots, hyphens, and underscores",
            field_name="endpoint_name",
            context={'provided_value': name, 'allowed_pattern': r'^[a-zA-Z0-9._-]+$'}
        )
    
    return name


def validate_hostname(hostname: str) -> str:
    """
    Validate hostname format.
    
    Args:
        hostname: Hostname to validate
        
    Returns:
        Validated and normalized hostname
        
    Raises:
        ValidationError: If hostname is invalid
    """
    if not hostname or not isinstance(hostname, str):
        raise ValidationError(
            "Hostname must be a non-empty string",
            field_name="hostname",
            context={'provided_value': hostname, 'expected_type': 'string'}
        )
    
    hostname = hostname.strip().lower()
    
    if len(hostname) > 253:
        raise ValidationError(
            "Hostname must be 253 characters or less",
            field_name="hostname",
            context={'provided_length': len(hostname), 'max_length': 253}
        )
    
    # Basic hostname validation
    if not re.match(r'^[a-zA-Z0-9.-]+$', hostname):
        raise ValidationError(
            "Hostname contains invalid characters",
            field_name="hostname",
            context={'provided_value': hostname, 'allowed_pattern': r'^[a-zA-Z0-9.-]+$'}
        )
    
    # Check for valid hostname format
    parts = hostname.split('.')
    for part in parts:
        if not part or len(part) > 63:
            raise ValidationError(
                "Invalid hostname format - parts must be 1-63 characters",
                field_name="hostname",
                context={'invalid_part': part, 'max_part_length': 63}
            )
        if not re.match(r'^[a-zA-Z0-9-]+$', part):
            raise ValidationError(
                "Invalid hostname format - parts contain invalid characters",
                field_name="hostname",
                context={'invalid_part': part, 'allowed_pattern': r'^[a-zA-Z0-9-]+$'}
            )
        if part.startswith('-') or part.endswith('-'):
            raise ValidationError(
                "Hostname parts cannot start or end with hyphens",
                field_name="hostname",
                context={'invalid_part': part}
            )
    
    return hostname


def validate_package_name(name: str) -> str:
    """
    Validate package name format.
    
    Args:
        name: Package name to validate
        
    Returns:
        Validated package name
        
    Raises:
        ValidationError: If package name is invalid
    """
    if not name or not isinstance(name, str):
        raise ValidationError(
            "Package name must be a non-empty string",
            field_name="package_name",
            context={'provided_value': name, 'expected_type': 'string'}
        )
    
    name = name.strip()
    
    if len(name) < 1 or len(name) > 255:
        raise ValidationError(
            "Package name must be between 1 and 255 characters",
            field_name="package_name",
            context={'provided_length': len(name), 'min_length': 1, 'max_length': 255}
        )
    
    # Arch Linux package naming conventions
    if not re.match(r'^[a-z0-9@._+-]+$', name):
        raise ValidationError(
            "Package name contains invalid characters",
            field_name="package_name",
            context={'provided_value': name, 'allowed_pattern': r'^[a-z0-9@._+-]+$'}
        )
    
    return name


def validate_version(version: str) -> str:
    """
    Validate package version format.
    
    Args:
        version: Version string to validate
        
    Returns:
        Validated version string
        
    Raises:
        ValidationError: If version is invalid
    """
    if not version or not isinstance(version, str):
        raise ValidationError(
            "Version must be a non-empty string",
            field_name="version",
            context={'provided_value': version, 'expected_type': 'string'}
        )
    
    version = version.strip()
    
    if len(version) > 255:
        raise ValidationError(
            "Version string must be 255 characters or less",
            field_name="version",
            context={'provided_length': len(version), 'max_length': 255}
        )
    
    # Basic version format validation
    if not re.match(r'^[a-zA-Z0-9.:_+-]+$', version):
        raise ValidationError(
            "Version contains invalid characters",
            field_name="version",
            context={'provided_value': version, 'allowed_pattern': r'^[a-zA-Z0-9.:_+-]+$'}
        )
    
    return version


def validate_repository_name(name: str) -> str:
    """
    Validate repository name format.
    
    Args:
        name: Repository name to validate
        
    Returns:
        Validated repository name
        
    Raises:
        ValidationError: If repository name is invalid
    """
    if not name or not isinstance(name, str):
        raise ValidationError(
            "Repository name must be a non-empty string",
            field_name="repository_name",
            context={'provided_value': name, 'expected_type': 'string'}
        )
    
    name = name.strip()
    
    if len(name) < 1 or len(name) > 255:
        raise ValidationError(
            "Repository name must be between 1 and 255 characters",
            field_name="repository_name",
            context={'provided_length': len(name), 'min_length': 1, 'max_length': 255}
        )
    
    # Allow alphanumeric, hyphens, and underscores
    if not re.match(r'^[a-zA-Z0-9_-]+$', name):
        raise ValidationError(
            "Repository name can only contain letters, numbers, hyphens, and underscores",
            field_name="repository_name",
            context={'provided_value': name, 'allowed_pattern': r'^[a-zA-Z0-9_-]+$'}
        )
    
    return name


def validate_url(url: str) -> str:
    """
    Validate URL format.
    
    Args:
        url: URL to validate
        
    Returns:
        Validated URL
        
    Raises:
        ValidationError: If URL is invalid
    """
    if not url or not isinstance(url, str):
        raise ValidationError(
            "URL must be a non-empty string",
            field_name="url",
            context={'provided_value': url, 'expected_type': 'string'}
        )
    
    url = url.strip()
    
    if len(url) > 2048:
        raise ValidationError(
            "URL must be 2048 characters or less",
            field_name="url",
            context={'provided_length': len(url), 'max_length': 2048}
        )
    
    try:
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            raise ValidationError(
                "URL must include scheme and network location",
                field_name="url",
                context={'provided_url': url, 'parsed_scheme': parsed.scheme, 'parsed_netloc': parsed.netloc}
            )
        
        if parsed.scheme not in ['http', 'https', 'ftp', 'ftps']:
            raise ValidationError(
                "URL scheme must be http, https, ftp, or ftps",
                field_name="url",
                context={'provided_scheme': parsed.scheme, 'allowed_schemes': ['http', 'https', 'ftp', 'ftps']}
            )
        
    except Exception as e:
        if isinstance(e, ValidationError):
            raise
        raise ValidationError(
            f"Invalid URL format: {str(e)}",
            field_name="url",
            context={'provided_url': url, 'parse_error': str(e)}
        )
    
    return url


def validate_ip_address(ip: str) -> str:
    """
    Validate IP address format.
    
    Args:
        ip: IP address to validate
        
    Returns:
        Validated IP address
        
    Raises:
        ValidationError: If IP address is invalid
    """
    if not ip or not isinstance(ip, str):
        raise ValidationError(
            "IP address must be a non-empty string",
            field_name="ip_address",
            context={'provided_value': ip, 'expected_type': 'string'}
        )
    
    ip = ip.strip()
    
    try:
        # This will raise ValueError if invalid
        ipaddress.ip_address(ip)
        return ip
    except ValueError as e:
        raise ValidationError(
            f"Invalid IP address: {str(e)}",
            field_name="ip_address",
            context={'provided_value': ip, 'validation_error': str(e)}
        )


def validate_port(port: Any) -> int:
    """
    Validate port number.
    
    Args:
        port: Port number to validate
        
    Returns:
        Validated port number
        
    Raises:
        ValidationError: If port is invalid
    """
    try:
        port_int = int(port)
    except (ValueError, TypeError):
        raise ValidationError(
            "Port must be a valid integer",
            field_name="port",
            context={'provided_value': port, 'expected_type': 'integer'}
        )
    
    if port_int < 1 or port_int > 65535:
        raise ValidationError(
            "Port must be between 1 and 65535",
            field_name="port",
            context={'provided_value': port_int, 'min_value': 1, 'max_value': 65535}
        )
    
    return port_int


def validate_uuid(uuid_str: str) -> str:
    """
    Validate UUID format.
    
    Args:
        uuid_str: UUID string to validate
        
    Returns:
        Validated UUID string
        
    Raises:
        ValidationError: If UUID is invalid
    """
    if not uuid_str or not isinstance(uuid_str, str):
        raise ValidationError(
            "UUID must be a non-empty string",
            field_name="uuid",
            context={'provided_value': uuid_str, 'expected_type': 'string'}
        )
    
    uuid_str = uuid_str.strip()
    
    # UUID format validation
    uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
    if not re.match(uuid_pattern, uuid_str, re.IGNORECASE):
        raise ValidationError(
            "Invalid UUID format",
            field_name="uuid",
            context={'provided_value': uuid_str, 'expected_pattern': uuid_pattern}
        )
    
    return uuid_str.lower()


async def validation_middleware(request: Request, call_next):
    """
    Middleware for request validation and error handling.
    
    This middleware performs basic request validation, handles exceptions,
    and adds security headers to responses.
    """
    try:
        # Log incoming request
        logger.debug(
            f"Incoming request: {request.method} {request.url.path}",
            extra={
                'request_method': request.method,
                'request_path': request.url.path,
                'request_query': str(request.url.query) if request.url.query else None,
                'client_host': request.client.host if request.client else None,
                'user_agent': request.headers.get('user-agent')
            }
        )
        
        # Process the request
        response = await call_next(request)
        
        # Log successful response
        logger.debug(
            f"Response: {response.status_code} for {request.method} {request.url.path}",
            extra={
                'response_status': response.status_code,
                'request_method': request.method,
                'request_path': request.url.path
            }
        )
        
        return response
        
    except ValidationError as e:
        # Log validation error
        log_structured_error(logger, e)
        
        # Return structured error response
        return JSONResponse(
            status_code=e.get_http_status_code(),
            content=create_error_response(e)
        )
        
    except HTTPException as e:
        # Log HTTP exception
        logger.warning(
            f"HTTP exception: {e.status_code} - {e.detail}",
            extra={
                'status_code': e.status_code,
                'detail': e.detail,
                'request_method': request.method,
                'request_path': request.url.path
            }
        )
        
        # Convert to structured error if possible
        if hasattr(e, 'detail') and isinstance(e.detail, dict):
            return JSONResponse(
                status_code=e.status_code,
                content=e.detail
            )
        else:
            # Create structured error response
            structured_error = handle_exception(
                e,
                context={
                    'request_method': request.method,
                    'request_path': request.url.path,
                    'status_code': e.status_code
                }
            )
            return JSONResponse(
                status_code=e.status_code,
                content=create_error_response(structured_error)
            )
    
    except Exception as e:
        # Log unexpected error
        logger.error(
            f"Unexpected error in validation middleware: {str(e)}",
            exc_info=True,
            extra={
                'request_method': request.method,
                'request_path': request.url.path,
                'error_type': type(e).__name__
            }
        )
        
        # Convert to structured error
        structured_error = handle_exception(
            e,
            context={
                'request_method': request.method,
                'request_path': request.url.path,
                'middleware': 'validation'
            }
        )
        
        log_structured_error(logger, structured_error)
        
        return JSONResponse(
            status_code=structured_error.get_http_status_code(),
            content=create_error_response(structured_error)
        )