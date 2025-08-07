"""
Tests for health check endpoints and container orchestration features.

This module tests the health check endpoints, graceful shutdown handling,
and database connection pooling functionality.
"""

import pytest
import asyncio
import json
import time
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient
from httpx import AsyncClient

from server.api.main import create_app
from server.api.health import (
    check_database_health,
    check_service_dependencies,
    update_service_status,
    mark_service_ready,
    mark_service_shutting_down
)
from server.core.shutdown_handler import GracefulShutdownHandler
from server.database.connection import DatabaseManager


class TestHealthEndpoints:
    """Test health check endpoints."""
    
    @pytest.fixture
    def app(self):
        """Create test FastAPI app."""
        return create_app()
    
    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return TestClient(app)
    
    def test_basic_health_check(self, client):
        """Test basic health check endpoint."""
        response = client.get("/health")
        assert response.status_code in [200, 503]  # May be 503 if database not ready
        
        data = response.json()
        assert "status" in data
        assert "service" in data
        assert "version" in data
        assert "uptime_seconds" in data
        assert "timestamp" in data
        
        assert data["service"] == "pacman-sync-utility"
        assert data["version"] == "1.0.0"
        assert isinstance(data["uptime_seconds"], (int, float))
    
    def test_detailed_health_check(self, client):
        """Test detailed health check endpoint."""
        response = client.get("/health/detailed")
        assert response.status_code in [200, 503]
        
        data = response.json()
        assert "status" in data
        assert "service" in data
        assert "components" in data
        assert "configuration" in data
        
        # Check components
        components = data["components"]
        assert "database" in components
        assert "dependencies" in components
        
        # Check configuration
        config = data["configuration"]
        assert "database_type" in config
        assert "pool_size" in config
        assert "features" in config
    
    def test_readiness_check(self, client):
        """Test readiness check endpoint."""
        response = client.get("/health/ready")
        assert response.status_code in [200, 503]
        
        data = response.json()
        assert "status" in data
        assert "timestamp" in data
        
        if response.status_code == 200:
            assert data["status"] == "ready"
            assert "uptime_seconds" in data
        else:
            assert data["status"] == "not_ready"
            assert "reason" in data
    
    def test_liveness_check(self, client):
        """Test liveness check endpoint."""
        response = client.get("/health/live")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "alive"
        assert "uptime_seconds" in data
        assert "timestamp" in data
        assert isinstance(data["uptime_seconds"], (int, float))


class TestDatabaseHealthCheck:
    """Test database health check functionality."""
    
    @pytest.mark.asyncio
    async def test_postgresql_health_check(self):
        """Test PostgreSQL health check."""
        # Mock database manager
        db_manager = Mock(spec=DatabaseManager)
        db_manager.database_type = "postgresql"
        db_manager.execute = AsyncMock()
        db_manager.fetchval = AsyncMock(return_value=5)
        
        result = await check_database_health(db_manager)
        
        assert result["status"] == "healthy"
        assert result["type"] == "postgresql"
        assert "response_time_ms" in result
        assert "last_check" in result
        
        # Verify database calls were made
        db_manager.execute.assert_called_once_with("SELECT 1")
        db_manager.fetchval.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_sqlite_health_check(self):
        """Test SQLite health check."""
        # Mock database manager
        db_manager = Mock(spec=DatabaseManager)
        db_manager.database_type = "internal"
        db_manager.execute = AsyncMock()
        db_manager.fetchval = AsyncMock(return_value=3)
        
        result = await check_database_health(db_manager)
        
        assert result["status"] == "healthy"
        assert result["type"] == "internal"
        assert "response_time_ms" in result
        assert "last_check" in result
    
    @pytest.mark.asyncio
    async def test_database_health_check_failure(self):
        """Test database health check failure handling."""
        # Mock database manager with failure
        db_manager = Mock(spec=DatabaseManager)
        db_manager.database_type = "postgresql"
        db_manager.execute = AsyncMock(side_effect=Exception("Connection failed"))
        
        result = await check_database_health(db_manager)
        
        assert result["status"] == "unhealthy"
        assert result["type"] == "postgresql"
        assert "error" in result
        assert "Connection failed" in result["error"]


class TestServiceDependencies:
    """Test service dependency checking."""
    
    @pytest.mark.asyncio
    async def test_service_dependencies_healthy(self):
        """Test service dependencies when all are healthy."""
        with patch('server.api.health.app') as mock_app:
            # Mock app state with all services
            mock_app.state.pool_manager = Mock()
            mock_app.state.sync_coordinator = Mock()
            mock_app.state.endpoint_manager = Mock()
            
            result = await check_service_dependencies()
            
            assert result["pool_manager"] == "healthy"
            assert result["sync_coordinator"] == "healthy"
            assert result["endpoint_manager"] == "healthy"
    
    @pytest.mark.asyncio
    async def test_service_dependencies_missing(self):
        """Test service dependencies when some are missing."""
        with patch('server.api.health.app') as mock_app:
            # Mock app state with missing services
            mock_app.state = Mock()
            del mock_app.state.pool_manager  # Simulate missing attribute
            
            result = await check_service_dependencies()
            
            assert "pool_manager" in result
            # Should handle missing attributes gracefully


class TestGracefulShutdown:
    """Test graceful shutdown functionality."""
    
    def test_shutdown_handler_initialization(self):
        """Test shutdown handler initialization."""
        handler = GracefulShutdownHandler(shutdown_timeout=30)
        
        assert handler.shutdown_timeout == 30
        assert not handler.is_shutting_down
        assert len(handler.cleanup_tasks) == 0
        assert len(handler.active_operations) == 0
    
    def test_register_cleanup_task(self):
        """Test registering cleanup tasks."""
        handler = GracefulShutdownHandler()
        
        def cleanup_func():
            pass
        
        handler.register_cleanup_task(cleanup_func)
        
        assert len(handler.cleanup_tasks) == 1
        assert cleanup_func in handler.cleanup_tasks
    
    @pytest.mark.asyncio
    async def test_operation_context_normal(self):
        """Test operation context under normal conditions."""
        handler = GracefulShutdownHandler()
        
        async with handler.operation_context("test_operation"):
            # Should not raise any exceptions
            await asyncio.sleep(0.01)
        
        # Should complete successfully
        assert True
    
    @pytest.mark.asyncio
    async def test_operation_context_during_shutdown(self):
        """Test operation context during shutdown."""
        handler = GracefulShutdownHandler()
        handler.shutdown_event.set()  # Simulate shutdown
        
        with pytest.raises(RuntimeError, match="Service is shutting down"):
            async with handler.operation_context("test_operation"):
                await asyncio.sleep(0.01)
    
    def test_shutdown_status_running(self):
        """Test shutdown status when running."""
        handler = GracefulShutdownHandler()
        
        status = handler.get_shutdown_status()
        
        assert status["status"] == "running"
        assert "active_operations" in status
        assert "cleanup_tasks" in status
    
    def test_shutdown_status_shutting_down(self):
        """Test shutdown status when shutting down."""
        handler = GracefulShutdownHandler()
        handler.is_shutting_down = True
        handler._shutdown_start_time = time.time()
        
        status = handler.get_shutdown_status()
        
        assert status["status"] == "shutting_down"
        assert "elapsed_time" in status
        assert "timeout" in status
        assert "active_operations" in status
        assert "cleanup_tasks" in status


class TestDatabaseConnectionPooling:
    """Test database connection pooling functionality."""
    
    @pytest.mark.asyncio
    async def test_postgresql_pool_stats(self):
        """Test PostgreSQL connection pool statistics."""
        # Mock asyncpg pool
        mock_pool = Mock()
        mock_pool.get_size.return_value = 5
        mock_pool.get_min_size.return_value = 2
        mock_pool.get_max_size.return_value = 10
        mock_pool.get_idle_size.return_value = 3
        
        db_manager = DatabaseManager("postgresql", "postgresql://test")
        db_manager._pool = mock_pool
        
        stats = await db_manager.get_pool_stats()
        
        assert stats["type"] == "postgresql"
        assert stats["size"] == 5
        assert stats["min_size"] == 2
        assert stats["max_size"] == 10
        assert stats["idle_connections"] == 3
        assert stats["active_connections"] == 2  # size - idle
    
    @pytest.mark.asyncio
    async def test_sqlite_pool_stats(self):
        """Test SQLite connection statistics."""
        db_manager = DatabaseManager("internal")
        db_manager._connection = Mock()
        
        stats = await db_manager.get_pool_stats()
        
        assert stats["type"] == "sqlite"
        assert stats["connection_status"] == "connected"
    
    @pytest.mark.asyncio
    async def test_database_health_check_method(self):
        """Test database health check method."""
        # Mock PostgreSQL database manager
        mock_pool = Mock()
        mock_conn = AsyncMock()
        mock_conn.fetchval = AsyncMock(return_value=1)
        mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)
        
        db_manager = DatabaseManager("postgresql", "postgresql://test")
        db_manager._pool = mock_pool
        
        result = await db_manager.health_check()
        
        assert result is True
        mock_conn.fetchval.assert_called_once_with("SELECT 1")
    
    @pytest.mark.asyncio
    async def test_database_health_check_failure(self):
        """Test database health check failure."""
        db_manager = DatabaseManager("postgresql", "postgresql://test")
        db_manager._pool = None  # Simulate no pool
        
        result = await db_manager.health_check()
        
        assert result is False


class TestHealthStatusTracking:
    """Test health status tracking functionality."""
    
    def test_update_service_status(self):
        """Test updating service status."""
        update_service_status("starting")
        # Should not raise any exceptions
        assert True
    
    def test_mark_service_ready(self):
        """Test marking service as ready."""
        mark_service_ready()
        # Should not raise any exceptions
        assert True
    
    def test_mark_service_shutting_down(self):
        """Test marking service as shutting down."""
        mark_service_shutting_down()
        # Should not raise any exceptions
        assert True


@pytest.mark.integration
class TestHealthEndpointsIntegration:
    """Integration tests for health endpoints."""
    
    @pytest.mark.asyncio
    async def test_health_endpoints_with_real_app(self):
        """Test health endpoints with real application."""
        app = create_app()
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Test basic health
            response = await client.get("/health")
            assert response.status_code in [200, 503]
            
            # Test liveness (should always work)
            response = await client.get("/health/live")
            assert response.status_code == 200
            
            # Test readiness (may fail if database not available)
            response = await client.get("/health/ready")
            assert response.status_code in [200, 503]
            
            # Test detailed health
            response = await client.get("/health/detailed")
            assert response.status_code in [200, 503]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])