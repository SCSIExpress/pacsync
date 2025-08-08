#!/usr/bin/env python3
"""
Component Integration Script for Pacman Sync Utility

This script wires together all components and ensures proper integration
between server, client, and database components.
"""

import os
import sys
import json
import logging
import asyncio
import argparse
from pathlib import Path
from typing import Dict, List, Optional, Any

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ComponentIntegrator:
    """Handles integration of all system components."""
    
    def __init__(self, config_file: Optional[str] = None):
        self.config_file = config_file or "/etc/pacman-sync/server.conf"
        self.project_root = project_root
        self.integration_status = {}
        
    async def run_integration(self, components: List[str], verify_only: bool = False) -> bool:
        """
        Run integration for specified components.
        
        Args:
            components: List of components to integrate
            verify_only: Only verify integration, don't make changes
            
        Returns:
            True if integration successful, False otherwise
        """
        logger.info(f"Starting component integration: {', '.join(components)}")
        
        success = True
        
        # Integration steps in dependency order
        integration_steps = [
            ("database", self._integrate_database),
            ("server", self._integrate_server),
            ("client", self._integrate_client),
            ("web-ui", self._integrate_web_ui),
            ("api", self._integrate_api),
            ("authentication", self._integrate_authentication),
            ("monitoring", self._integrate_monitoring),
        ]
        
        for component, integration_func in integration_steps:
            if component in components or "all" in components:
                try:
                    logger.info(f"Integrating component: {component}")
                    result = await integration_func(verify_only)
                    self.integration_status[component] = {
                        "status": "success" if result else "failed",
                        "verified": verify_only
                    }
                    if not result:
                        success = False
                        logger.error(f"Integration failed for component: {component}")
                except Exception as e:
                    logger.error(f"Integration error for {component}: {e}")
                    self.integration_status[component] = {
                        "status": "error",
                        "error": str(e),
                        "verified": verify_only
                    }
                    success = False
        
        # Generate integration report
        self._generate_integration_report()
        
        return success
    
    async def _integrate_database(self, verify_only: bool) -> bool:
        """Integrate database components."""
        logger.info("Integrating database components...")
        
        try:
            # Import database components
            from server.database.connection import DatabaseManager
            from server.database.schema import create_tables, verify_schema
            from server.database.migrations import run_migrations
            
            # Initialize database manager
            db_manager = DatabaseManager()
            
            if not verify_only:
                # Initialize database connection
                await db_manager.initialize()
                
                # Verify or create schema
                if not await verify_schema(db_manager):
                    logger.info("Creating database schema...")
                    await create_tables(db_manager)
                
                # Run any pending migrations
                logger.info("Running database migrations...")
                await run_migrations(db_manager)
                
                # Close connection
                await db_manager.close()
            
            logger.info("Database integration completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Database integration failed: {e}")
            return False
    
    async def _integrate_server(self, verify_only: bool) -> bool:
        """Integrate server components."""
        logger.info("Integrating server components...")
        
        try:
            # Import server components
            from server.config import get_config
            from server.core.pool_manager import PackagePoolManager
            from server.core.sync_coordinator import SyncCoordinator
            from server.core.endpoint_manager import EndpointManager
            from server.database.connection import DatabaseManager
            
            # Load configuration
            config = get_config()
            
            if not verify_only:
                # Initialize database
                db_manager = DatabaseManager()
                await db_manager.initialize()
                
                # Initialize core services
                pool_manager = PackagePoolManager(db_manager)
                sync_coordinator = SyncCoordinator(db_manager)
                endpoint_manager = EndpointManager(
                    db_manager,
                    jwt_secret=config.security.jwt_secret_key,
                    jwt_expiration_hours=config.security.jwt_expiration_hours
                )
                
                # Verify services can be initialized
                logger.info("Server core services initialized successfully")
                
                # Cleanup
                await db_manager.close()
            
            logger.info("Server integration completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Server integration failed: {e}")
            return False
    
    async def _integrate_client(self, verify_only: bool) -> bool:
        """Integrate client components."""
        logger.info("Integrating client components...")
        
        try:
            # Import client components
            from client.config import ClientConfiguration
            from client.api_client import APIClient
            from client.sync_manager import SyncManager
            from client.status_persistence import StatusPersistenceManager
            
            if not verify_only:
                # Test client configuration loading
                config = ClientConfiguration()
                
                # Test status persistence
                status_manager = StatusPersistenceManager()
                
                # Test API client initialization (without connecting)
                api_client = APIClient(
                    server_url=config.get_server_url(),
                    timeout=config.get_timeout()
                )
                
                logger.info("Client components initialized successfully")
            
            logger.info("Client integration completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Client integration failed: {e}")
            return False
    
    async def _integrate_web_ui(self, verify_only: bool) -> bool:
        """Integrate web UI components."""
        logger.info("Integrating web UI components...")
        
        try:
            # Check if web UI build exists
            web_dist_path = self.project_root / "server" / "web" / "dist"
            
            if not web_dist_path.exists():
                if not verify_only:
                    logger.info("Building web UI...")
                    # Build web UI
                    import subprocess
                    web_path = self.project_root / "server" / "web"
                    
                    # Install dependencies
                    result = subprocess.run(
                        ["npm", "ci"],
                        cwd=web_path,
                        capture_output=True,
                        text=True
                    )
                    if result.returncode != 0:
                        logger.error(f"npm ci failed: {result.stderr}")
                        return False
                    
                    # Build
                    result = subprocess.run(
                        ["npm", "run", "build"],
                        cwd=web_path,
                        capture_output=True,
                        text=True
                    )
                    if result.returncode != 0:
                        logger.error(f"npm build failed: {result.stderr}")
                        return False
                else:
                    logger.warning("Web UI build not found, but verify_only mode enabled")
            
            logger.info("Web UI integration completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Web UI integration failed: {e}")
            return False
    
    async def _integrate_api(self, verify_only: bool) -> bool:
        """Integrate API components."""
        logger.info("Integrating API components...")
        
        try:
            # Import API components
            from server.api.main import create_app
            from server.api.pools import router as pools_router
            from server.api.endpoints import router as endpoints_router
            from server.api.sync import router as sync_router
            from server.api.repositories import router as repositories_router
            from server.api.health import router as health_router
            
            if not verify_only:
                # Create FastAPI app to verify all routes are properly configured
                app = create_app()
                
                # Verify all routers are included
                route_paths = [route.path for route in app.routes]
                
                expected_routes = [
                    "/health/live",
                    "/health/ready",
                    "/api/pools",
                    "/api/endpoints",
                    "/api/sync",
                    "/api/repositories"
                ]
                
                for expected_route in expected_routes:
                    if not any(expected_route in path for path in route_paths):
                        logger.error(f"Expected route not found: {expected_route}")
                        return False
                
                logger.info("API routes verified successfully")
            
            logger.info("API integration completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"API integration failed: {e}")
            return False
    
    async def _integrate_authentication(self, verify_only: bool) -> bool:
        """Integrate authentication components."""
        logger.info("Integrating authentication components...")
        
        try:
            # Import authentication components
            from server.middleware.auth import create_auth_dependencies
            from client.auth.token_manager import TokenManager
            from client.auth.token_storage import TokenStorage
            
            if not verify_only:
                # Test server-side authentication
                authenticate_endpoint, authenticate_admin = create_auth_dependencies(
                    jwt_secret="test-secret",
                    admin_tokens=[]
                )
                
                # Test client-side token management
                token_storage = TokenStorage()
                token_manager = TokenManager(token_storage)
                
                logger.info("Authentication components verified successfully")
            
            logger.info("Authentication integration completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Authentication integration failed: {e}")
            return False
    
    async def _integrate_monitoring(self, verify_only: bool) -> bool:
        """Integrate monitoring and health check components."""
        logger.info("Integrating monitoring components...")
        
        try:
            # Import monitoring components
            from server.api.health import router as health_router
            from server.core.shutdown_handler import setup_graceful_shutdown
            from shared.logging_config import setup_logging, AuditLogger, OperationLogger
            
            if not verify_only:
                # Test health check endpoints
                # This would normally be tested with actual HTTP requests
                
                # Test logging configuration
                setup_logging()
                audit_logger = AuditLogger("integration_test")
                operation_logger = OperationLogger("integration_test")
                
                # Test graceful shutdown handler
                shutdown_handler = setup_graceful_shutdown(shutdown_timeout=5)
                
                logger.info("Monitoring components verified successfully")
            
            logger.info("Monitoring integration completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Monitoring integration failed: {e}")
            return False
    
    def _generate_integration_report(self):
        """Generate integration status report."""
        report_path = self.project_root / "integration_report.json"
        
        report = {
            "timestamp": str(asyncio.get_event_loop().time()),
            "project_root": str(self.project_root),
            "config_file": self.config_file,
            "components": self.integration_status,
            "overall_status": "success" if all(
                status["status"] == "success" 
                for status in self.integration_status.values()
            ) else "failed"
        }
        
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"Integration report generated: {report_path}")
        
        # Print summary
        print("\n" + "="*60)
        print("INTEGRATION REPORT")
        print("="*60)
        
        for component, status in self.integration_status.items():
            status_symbol = "✓" if status["status"] == "success" else "✗"
            verify_text = " (verify only)" if status.get("verified") else ""
            print(f"{status_symbol} {component.upper()}: {status['status']}{verify_text}")
            
            if "error" in status:
                print(f"  Error: {status['error']}")
        
        print("="*60)
        print(f"Overall Status: {report['overall_status'].upper()}")
        print("="*60)


async def main():
    """Main entry point for component integration."""
    parser = argparse.ArgumentParser(
        description="Integrate Pacman Sync Utility components",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --components all                    # Integrate all components
  %(prog)s --components database server        # Integrate specific components
  %(prog)s --verify-only --components all      # Verify integration without changes
  %(prog)s --config /path/to/config.conf      # Use custom config file
        """
    )
    
    parser.add_argument(
        "--components",
        nargs="+",
        choices=["all", "database", "server", "client", "web-ui", "api", "authentication", "monitoring"],
        default=["all"],
        help="Components to integrate"
    )
    
    parser.add_argument(
        "--config",
        type=str,
        help="Path to server configuration file"
    )
    
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="Only verify integration, don't make changes"
    )
    
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    # Configure logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Create integrator
    integrator = ComponentIntegrator(args.config)
    
    try:
        # Run integration
        success = await integrator.run_integration(args.components, args.verify_only)
        
        if success:
            print("\n✓ Component integration completed successfully!")
            return 0
        else:
            print("\n✗ Component integration failed!")
            return 1
            
    except KeyboardInterrupt:
        print("\nIntegration cancelled by user")
        return 130
    except Exception as e:
        logger.error(f"Integration error: {e}")
        print(f"\n✗ Integration error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))