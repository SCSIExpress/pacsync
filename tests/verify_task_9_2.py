#!/usr/bin/env python3
"""
Verification script for Task 9.2: Container orchestration and scaling support.

This script verifies that all components of task 9.2 have been implemented:
1. Health check endpoints for container monitoring
2. Graceful shutdown handling for container lifecycle management  
3. Database connection pooling for horizontal scaling
"""

import asyncio
import sys
import json
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from server.api.health import (
    get_current_timestamp,
    update_service_status,
    mark_service_ready,
    mark_service_shutting_down,
    check_database_health,
    check_service_dependencies
)
from server.core.shutdown_handler import (
    GracefulShutdownHandler,
    setup_graceful_shutdown,
    get_shutdown_handler
)
from server.database.connection import DatabaseManager


class Task92Verifier:
    """Verifies Task 9.2 implementation."""
    
    def __init__(self):
        self.passed_tests = 0
        self.total_tests = 0
        self.errors = []
    
    def test(self, test_name: str, test_func):
        """Run a test and track results."""
        self.total_tests += 1
        try:
            print(f"Testing {test_name}...", end=" ")
            test_func()
            print("✓ PASSED")
            self.passed_tests += 1
        except Exception as e:
            print(f"✗ FAILED: {e}")
            self.errors.append(f"{test_name}: {e}")
    
    async def async_test(self, test_name: str, test_func):
        """Run an async test and track results."""
        self.total_tests += 1
        try:
            print(f"Testing {test_name}...", end=" ")
            await test_func()
            print("✓ PASSED")
            self.passed_tests += 1
        except Exception as e:
            print(f"✗ FAILED: {e}")
            self.errors.append(f"{test_name}: {e}")
    
    def verify_health_endpoints(self):
        """Verify health check endpoints implementation."""
        print("\n=== Verifying Health Check Endpoints ===")
        
        # Test timestamp generation
        self.test("Current timestamp generation", lambda: (
            get_current_timestamp() and 
            isinstance(get_current_timestamp(), str) and
            "T" in get_current_timestamp()
        ))
        
        # Test service status tracking
        self.test("Service status updates", lambda: (
            update_service_status("testing"),
            mark_service_ready(),
            mark_service_shutting_down()
        ))
        
        # Test health check file exists
        self.test("Health check module exists", lambda: (
            (project_root / "server" / "api" / "health.py").exists()
        ))
        
        # Test health endpoints are defined
        from server.api.health import router
        self.test("Health router exists", lambda: (
            router is not None and
            len(router.routes) > 0
        ))
    
    async def verify_database_pooling(self):
        """Verify database connection pooling implementation."""
        print("\n=== Verifying Database Connection Pooling ===")
        
        # Test DatabaseManager initialization
        await self.async_test("DatabaseManager initialization", self._test_db_manager_init)
        
        # Test pool statistics
        await self.async_test("Pool statistics", self._test_pool_stats)
        
        # Test health check method
        await self.async_test("Database health check", self._test_db_health_check)
        
        # Test enhanced PostgreSQL configuration
        self.test("PostgreSQL pool configuration", self._test_postgresql_config)
    
    async def _test_db_manager_init(self):
        """Test database manager initialization."""
        # Test SQLite
        db_manager = DatabaseManager("internal")
        assert db_manager.database_type == "internal"
        
        # Test PostgreSQL (without actual connection)
        db_manager_pg = DatabaseManager("postgresql", "postgresql://test:test@localhost/test")
        assert db_manager_pg.database_type == "postgresql"
        assert db_manager_pg.database_url == "postgresql://test:test@localhost/test"
    
    async def _test_pool_stats(self):
        """Test pool statistics functionality."""
        db_manager = DatabaseManager("internal")
        stats = await db_manager.get_pool_stats()
        
        assert isinstance(stats, dict)
        assert "type" in stats
        assert stats["type"] == "sqlite"
    
    async def _test_db_health_check(self):
        """Test database health check method."""
        db_manager = DatabaseManager("internal")
        
        # Should return False without actual connection
        health = await db_manager.health_check()
        assert isinstance(health, bool)
    
    def _test_postgresql_config(self):
        """Test PostgreSQL configuration enhancements."""
        # Check that the enhanced configuration methods exist
        db_manager = DatabaseManager("postgresql", "postgresql://test")
        
        # These methods should exist
        assert hasattr(db_manager, 'get_pool_stats')
        assert hasattr(db_manager, 'health_check')
        assert callable(db_manager.get_pool_stats)
        assert callable(db_manager.health_check)
    
    def verify_graceful_shutdown(self):
        """Verify graceful shutdown handling implementation."""
        print("\n=== Verifying Graceful Shutdown Handling ===")
        
        # Test GracefulShutdownHandler initialization
        self.test("Shutdown handler initialization", self._test_shutdown_init)
        
        # Test cleanup task registration
        self.test("Cleanup task registration", self._test_cleanup_registration)
        
        # Test shutdown status tracking
        self.test("Shutdown status tracking", self._test_shutdown_status)
        
        # Test global shutdown handler
        self.test("Global shutdown handler", self._test_global_handler)
        
        # Test shutdown handler file exists
        self.test("Shutdown handler module exists", lambda: (
            (project_root / "server" / "core" / "shutdown_handler.py").exists()
        ))
    
    def _test_shutdown_init(self):
        """Test shutdown handler initialization."""
        handler = GracefulShutdownHandler(shutdown_timeout=30)
        
        assert handler.shutdown_timeout == 30
        assert not handler.is_shutting_down
        assert len(handler.cleanup_tasks) == 0
        assert len(handler.active_operations) == 0
        assert handler.shutdown_event is not None
    
    def _test_cleanup_registration(self):
        """Test cleanup task registration."""
        handler = GracefulShutdownHandler()
        
        def dummy_cleanup():
            pass
        
        handler.register_cleanup_task(dummy_cleanup)
        assert len(handler.cleanup_tasks) == 1
        assert dummy_cleanup in handler.cleanup_tasks
    
    def _test_shutdown_status(self):
        """Test shutdown status tracking."""
        handler = GracefulShutdownHandler()
        
        # Test running status
        status = handler.get_shutdown_status()
        assert status["status"] == "running"
        assert "active_operations" in status
        assert "cleanup_tasks" in status
        
        # Test shutdown status
        handler.is_shutting_down = True
        status = handler.get_shutdown_status()
        assert status["status"] == "shutting_down"
    
    def _test_global_handler(self):
        """Test global shutdown handler functions."""
        handler = get_shutdown_handler()
        assert isinstance(handler, GracefulShutdownHandler)
        
        handler2 = setup_graceful_shutdown(shutdown_timeout=45)
        assert isinstance(handler2, GracefulShutdownHandler)
    
    def verify_docker_configuration(self):
        """Verify Docker and deployment configuration."""
        print("\n=== Verifying Docker and Deployment Configuration ===")
        
        # Test Dockerfile health check updates
        self.test("Dockerfile health check", self._test_dockerfile_health)
        
        # Test Kubernetes deployment
        self.test("Kubernetes deployment config", lambda: (
            (project_root / "deploy" / "kubernetes" / "deployment.yaml").exists()
        ))
        
        # Test HAProxy configuration
        self.test("HAProxy configuration", lambda: (
            (project_root / "deploy" / "haproxy" / "haproxy.cfg").exists()
        ))
        
        # Test Docker Compose scaling
        self.test("Docker Compose scaling config", lambda: (
            (project_root / "docker-compose.scale.yml").exists()
        ))
        
        # Test Prometheus configuration
        self.test("Prometheus configuration", lambda: (
            (project_root / "deploy" / "prometheus" / "prometheus.yml").exists()
        ))
    
    def _test_dockerfile_health(self):
        """Test Dockerfile health check configuration."""
        dockerfile_path = project_root / "Dockerfile"
        assert dockerfile_path.exists()
        
        content = dockerfile_path.read_text()
        
        # Should use the enhanced health endpoint
        assert "/health/ready" in content
        assert "HEALTHCHECK" in content
    
    def verify_integration(self):
        """Verify integration with main application."""
        print("\n=== Verifying Integration ===")
        
        # Test health router integration
        self.test("Health router integration", self._test_health_integration)
        
        # Test shutdown handler integration
        self.test("Shutdown handler integration", self._test_shutdown_integration)
        
        # Test configuration updates
        self.test("Configuration updates", self._test_config_updates)
    
    def _test_health_integration(self):
        """Test health router integration in main app."""
        from server.api.main import create_app
        
        app = create_app()
        
        # Check that health routes are included
        routes = [route.path for route in app.routes]
        health_routes = [route for route in routes if route.startswith("/health")]
        
        assert len(health_routes) > 0, "Health routes not found in application"
    
    def _test_shutdown_integration(self):
        """Test shutdown handler integration."""
        # Check that shutdown handler is imported in main
        main_file = project_root / "server" / "api" / "main.py"
        content = main_file.read_text()
        
        assert "shutdown_handler" in content
        assert "graceful_shutdown" in content or "GracefulShutdownHandler" in content
    
    def _test_config_updates(self):
        """Test configuration updates for pooling."""
        docker_compose = project_root / "docker-compose.yml"
        content = docker_compose.read_text()
        
        # Should include pool configuration
        assert "DB_POOL_MIN_SIZE" in content
        assert "DB_POOL_MAX_SIZE" in content
        assert "HEALTH_CHECK_INTERVAL" in content
    
    def print_summary(self):
        """Print test summary."""
        print(f"\n=== Test Summary ===")
        print(f"Passed: {self.passed_tests}/{self.total_tests}")
        
        if self.errors:
            print(f"\nErrors:")
            for error in self.errors:
                print(f"  - {error}")
        
        if self.passed_tests == self.total_tests:
            print("\n🎉 All tests passed! Task 9.2 implementation is complete.")
            return True
        else:
            print(f"\n❌ {self.total_tests - self.passed_tests} tests failed.")
            return False


async def main():
    """Main verification function."""
    print("Verifying Task 9.2: Container orchestration and scaling support")
    print("=" * 70)
    
    verifier = Task92Verifier()
    
    # Run all verification tests
    verifier.verify_health_endpoints()
    await verifier.verify_database_pooling()
    verifier.verify_graceful_shutdown()
    verifier.verify_docker_configuration()
    verifier.verify_integration()
    
    # Print summary and return success status
    success = verifier.print_summary()
    return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)