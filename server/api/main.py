"""
FastAPI application for the Pacman Sync Utility Server.

This module sets up the FastAPI application with all API routes,
middleware, error handling, and configuration.
"""

import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

from server.database.connection import DatabaseManager
from server.database.schema import create_tables, verify_schema
from server.core.pool_manager import PackagePoolManager
from server.core.sync_coordinator import SyncCoordinator
from server.middleware.auth import create_auth_dependencies, add_security_headers
from server.middleware.rate_limiting import create_rate_limit_middleware
from server.middleware.validation import validation_middleware
from server.middleware.operation_tracking import create_operation_tracking_middleware
from server.api.pools import router as pools_router
from server.api.endpoints import router as endpoints_router
from server.api.sync import router as sync_router
from server.api.repositories import router as repositories_router
from server.api.states import router as states_router
from server.api.health import router as health_router

# Import enhanced error handling
from shared.exceptions import (
    PacmanSyncError, ErrorCode, create_error_response, handle_exception
)
from shared.logging_config import (
    setup_logging, LogLevel, LogFormat, AuditLogger, OperationLogger,
    log_structured_error
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager with graceful shutdown support."""
    logger.info("Starting Pacman Sync Utility Server...")
    
    # Get configuration
    from server.config import get_config
    config = get_config()
    
    # Set up graceful shutdown handler
    from server.core.shutdown_handler import setup_graceful_shutdown, shutdown_cleanup
    shutdown_handler = setup_graceful_shutdown(shutdown_timeout=30)
    shutdown_handler.register_cleanup_task(shutdown_cleanup)
    
    # Initialize database
    db_manager = DatabaseManager(config.database.type, config.database.url)
    await db_manager.initialize()
    
    # Register database cleanup
    shutdown_handler.register_cleanup_task(db_manager.close)
    
    # Create tables if they don't exist
    if not await verify_schema(db_manager):
        logger.info("Creating database schema...")
        await create_tables(db_manager)
    
    # Initialize core services
    pool_manager = PackagePoolManager(db_manager)
    sync_coordinator = SyncCoordinator(db_manager)
    
    # Import and initialize endpoint manager
    from server.core.endpoint_manager import EndpointManager
    endpoint_manager = EndpointManager(
        db_manager, 
        jwt_secret=config.security.jwt_secret_key,
        jwt_expiration_hours=config.security.jwt_expiration_hours
    )
    
    # Store in app state for access in routes
    app.state.db_manager = db_manager
    app.state.pool_manager = pool_manager
    app.state.sync_coordinator = sync_coordinator
    app.state.endpoint_manager = endpoint_manager
    app.state.shutdown_handler = shutdown_handler
    
    # Mark service as ready
    from server.api.health import mark_service_ready
    mark_service_ready()
    
    logger.info("Server initialization complete")
    
    yield
    
    # Graceful shutdown
    logger.info("Initiating graceful shutdown...")
    await shutdown_handler.initiate_shutdown()


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    from server.config import get_config
    config = get_config()
    
    app = FastAPI(
        title="Pacman Sync Utility API",
        description="REST API for managing package synchronization across Arch-based systems",
        version="1.0.0",
        lifespan=lifespan
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.server.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Add operation tracking middleware
    operation_tracking_middleware = create_operation_tracking_middleware(
        enable_performance_logging=config.server.environment != "production"
    )
    app.add_middleware(operation_tracking_middleware)
    
    # Add rate limiting middleware
    if config.security.enable_rate_limiting:
        rate_limit_middleware = create_rate_limit_middleware(
            default_limit=config.security.api_rate_limit
        )
        app.middleware("http")(rate_limit_middleware)
    
    # Create authentication dependencies
    authenticate_endpoint, authenticate_admin = create_auth_dependencies(
        jwt_secret=config.security.jwt_secret_key,
        admin_tokens=config.security.admin_tokens
    )
    
    # Store auth dependencies in app state for use in routers
    app.state.authenticate_endpoint = authenticate_endpoint
    app.state.authenticate_admin = authenticate_admin
    
    # Add security headers middleware
    @app.middleware("http")
    async def security_headers_middleware(request: Request, call_next):
        response = await call_next(request)
        return add_security_headers(response, request)
    
    # Set up audit and operation loggers
    audit_logger = AuditLogger("server_audit")
    operation_logger = OperationLogger("server_operations")
    
    # Store loggers in app state
    app.state.audit_logger = audit_logger
    app.state.operation_logger = operation_logger
    
    # Add enhanced exception handlers
    @app.exception_handler(PacmanSyncError)
    async def pacman_sync_error_handler(request: Request, exc: PacmanSyncError):
        """Handle structured PacmanSyncError exceptions."""
        # Extract endpoint ID from request if available
        endpoint_id = None
        if hasattr(request.state, 'current_endpoint'):
            endpoint_id = request.state.current_endpoint.id
        
        # Extract operation ID from request context if available
        operation_id = getattr(request.state, 'operation_id', None)
        
        # Log the structured error with context
        log_structured_error(logger, exc, endpoint_id, operation_id)
        
        # Audit log the error with full context
        audit_logger.log_error(exc, endpoint_id, operation_id)
        
        # Create enhanced error response with recovery suggestions
        error_response = create_error_response(exc)
        
        # Add request context to error response
        error_response['error']['request_context'] = {
            'method': request.method,
            'path': str(request.url.path),
            'endpoint_id': endpoint_id,
            'operation_id': operation_id,
            'client_host': request.client.host if request.client else None,
            'user_agent': request.headers.get('user-agent')
        }
        
        return JSONResponse(
            status_code=exc.get_http_status_code(),
            content=error_response,
            headers={
                'X-Error-Code': exc.error_code.value,
                'X-Error-Severity': exc.severity.value,
                'X-Request-ID': operation_id or f"req_{datetime.now().timestamp()}"
            }
        )
    
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        """Handle FastAPI HTTP exceptions with structured error format."""
        # Extract context information
        endpoint_id = None
        if hasattr(request.state, 'current_endpoint'):
            endpoint_id = request.state.current_endpoint.id
        
        operation_id = getattr(request.state, 'operation_id', None)
        
        # Convert to structured error
        structured_error = handle_exception(
            exc,
            context={
                'request_method': request.method,
                'request_path': str(request.url.path),
                'status_code': exc.status_code,
                'client_host': request.client.host if request.client else None,
                'endpoint_id': endpoint_id,
                'operation_id': operation_id,
                'user_agent': request.headers.get('user-agent')
            }
        )
        
        # Log the error with context
        log_structured_error(logger, structured_error, endpoint_id, operation_id)
        
        # Audit log for authentication/authorization errors
        if exc.status_code in [401, 403]:
            audit_logger.log_error(structured_error, endpoint_id, operation_id)
        
        # Create enhanced error response
        error_response = create_error_response(structured_error)
        error_response['error']['request_context'] = {
            'method': request.method,
            'path': str(request.url.path),
            'endpoint_id': endpoint_id,
            'operation_id': operation_id
        }
        
        return JSONResponse(
            status_code=exc.status_code,
            content=error_response,
            headers={
                'X-Error-Code': structured_error.error_code.value,
                'X-Request-ID': operation_id or f"req_{datetime.now().timestamp()}"
            }
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """Handle unexpected exceptions with structured error format."""
        # Extract context information
        endpoint_id = None
        if hasattr(request.state, 'current_endpoint'):
            endpoint_id = request.state.current_endpoint.id
        
        operation_id = getattr(request.state, 'operation_id', None)
        
        # Convert to structured error
        structured_error = handle_exception(
            exc,
            context={
                'request_method': request.method,
                'request_path': str(request.url.path),
                'client_host': request.client.host if request.client else None,
                'endpoint_id': endpoint_id,
                'operation_id': operation_id,
                'handler': 'general_exception_handler',
                'user_agent': request.headers.get('user-agent'),
                'exception_type': type(exc).__name__
            },
            default_error_code=ErrorCode.INTERNAL_UNEXPECTED_ERROR
        )
        
        # Log the error with full traceback and context
        logger.error(
            f"Unhandled exception: {exc}",
            exc_info=True,
            extra={
                'endpoint_id': endpoint_id,
                'operation_id': operation_id,
                'request_method': request.method,
                'request_path': str(request.url.path)
            }
        )
        log_structured_error(logger, structured_error, endpoint_id, operation_id)
        
        # Always audit log unexpected errors
        audit_logger.log_error(structured_error, endpoint_id, operation_id)
        
        # Create enhanced error response
        error_response = create_error_response(structured_error)
        error_response['error']['request_context'] = {
            'method': request.method,
            'path': str(request.url.path),
            'endpoint_id': endpoint_id,
            'operation_id': operation_id
        }
        
        # Don't expose internal details in production
        if config.server.environment == "production":
            error_response['error']['context'] = {}
            error_response['error']['message'] = "An internal server error occurred"
        
        return JSONResponse(
            status_code=structured_error.get_http_status_code(),
            content=error_response,
            headers={
                'X-Error-Code': structured_error.error_code.value,
                'X-Error-Severity': structured_error.severity.value,
                'X-Request-ID': operation_id or f"req_{datetime.now().timestamp()}"
            }
        )
    
    # Include API routers
    app.include_router(health_router, tags=["health"])
    app.include_router(pools_router, prefix="/api", tags=["pools"])
    app.include_router(endpoints_router, prefix="/api", tags=["endpoints"])
    app.include_router(sync_router, prefix="/api", tags=["sync"])
    app.include_router(repositories_router, prefix="/api", tags=["repositories"])
    app.include_router(states_router, prefix="/api", tags=["states"])
    
    # Serve static files for web UI
    web_dist_path = os.path.join(os.path.dirname(__file__), "..", "web", "dist")
    if os.path.exists(web_dist_path):
        app.mount("/static", StaticFiles(directory=web_dist_path), name="static")
        
        # Serve index.html for SPA routing
        from fastapi.responses import FileResponse
        
        @app.get("/")
        async def serve_spa():
            return FileResponse(os.path.join(web_dist_path, "index.html"))
        
        @app.get("/{path:path}")
        async def serve_spa_routes(path: str):
            # Check if it's an API route
            if path.startswith("api/") or path.startswith("health"):
                raise HTTPException(status_code=404, detail="Not found")
            
            # Check if file exists in static directory
            file_path = os.path.join(web_dist_path, path)
            if os.path.isfile(file_path):
                return FileResponse(file_path)
            
            # Otherwise serve index.html for SPA routing
            return FileResponse(os.path.join(web_dist_path, "index.html"))
    
    return app


# Create the app instance
app = create_app()


if __name__ == "__main__":
    from server.config import get_config
    
    config = get_config()
    
    uvicorn.run(
        "server.api.main:app",
        host=config.server.host,
        port=config.server.port,
        log_level=config.server.log_level.lower(),
        reload=(config.server.environment == "development")
    )