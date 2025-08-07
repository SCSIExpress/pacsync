"""
FastAPI application for the Pacman Sync Utility Server.

This module sets up the FastAPI application with all API routes,
middleware, error handling, and configuration.
"""

import logging
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

from server.database.connection import DatabaseManager
from server.database.schema import create_tables, verify_schema
from server.core.pool_manager import PackagePoolManager
from server.core.sync_coordinator import SyncCoordinator
from server.api.pools import router as pools_router
from server.api.endpoints import router as endpoints_router
from server.api.sync import router as sync_router
from server.api.repositories import router as repositories_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    logger.info("Starting Pacman Sync Utility Server...")
    
    # Initialize database
    db_manager = DatabaseManager()
    await db_manager.initialize()
    
    # Create tables if they don't exist
    if not await verify_schema(db_manager):
        logger.info("Creating database schema...")
        await create_tables(db_manager)
    
    # Initialize core services
    pool_manager = PackagePoolManager(db_manager)
    sync_coordinator = SyncCoordinator(db_manager)
    
    # Import and initialize endpoint manager
    from server.core.endpoint_manager import EndpointManager
    endpoint_manager = EndpointManager(db_manager)
    
    # Store in app state for access in routes
    app.state.db_manager = db_manager
    app.state.pool_manager = pool_manager
    app.state.sync_coordinator = sync_coordinator
    app.state.endpoint_manager = endpoint_manager
    
    logger.info("Server initialization complete")
    
    yield
    
    # Cleanup
    logger.info("Shutting down server...")
    await db_manager.close()


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
    
    # Add custom exception handlers
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": f"HTTP_{exc.status_code}",
                    "message": exc.detail,
                    "timestamp": "2025-01-15T10:30:00Z"  # In real app, use datetime.now()
                }
            }
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        logger.error(f"Unhandled exception: {exc}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": "An internal server error occurred",
                    "timestamp": "2025-01-15T10:30:00Z"
                }
            }
        )
    
    # Health check endpoint
    @app.get("/health")
    async def health_check():
        """Health check endpoint for Docker and monitoring."""
        try:
            from server.database.connection import get_database_manager
            db_manager = get_database_manager()
            
            # Test database connection
            await db_manager.execute("SELECT 1")
            
            return {
                "status": "healthy",
                "timestamp": "2025-01-15T10:30:00Z",
                "database": "connected",
                "version": "1.0.0"
            }
        except Exception as e:
            from fastapi import HTTPException
            raise HTTPException(status_code=503, detail=f"Database connection failed: {str(e)}")
    
    # Include API routers
    app.include_router(pools_router, prefix="/api", tags=["pools"])
    app.include_router(endpoints_router, prefix="/api", tags=["endpoints"])
    app.include_router(sync_router, prefix="/api", tags=["sync"])
    app.include_router(repositories_router, prefix="/api", tags=["repositories"])
    
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
    
    # Health check endpoint
    @app.get("/health")
    async def health_check():
        return {"status": "healthy", "service": "pacman-sync-utility"}
    
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