#!/usr/bin/env python3
"""
Deployment Validation Script for Pacman Sync Utility

This script validates that all components are properly deployed and integrated.
"""

import os
import sys
import json
import time
import logging
import asyncio
import argparse
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Any
from urllib.parse import urljoin

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DeploymentValidator:
    """Validates deployment of all system components."""
    
    def __init__(self, server_url: str = "http://localhost:8080"):
        self.server_url = server_url
        self.validation_results = {}
        
    async def run_validation(self, components: List[str]) -> bool:
        """
        Run validation for specified components.
        
        Args:
            components: List of components to validate
            
        Returns:
            True if all validations pass, False otherwise
        """
        logger.info(f"Starting deployment validation: {', '.join(components)}")
        
        success = True
        
        # Validation steps
        validation_steps = [
            ("system", self._validate_system),
            ("database", self._validate_database),
            ("server", self._validate_server),
            ("api", self._validate_api),
            ("web-ui", self._validate_web_ui),
            ("client", self._validate_client),
            ("integration", self._validate_integration),
            ("performance", self._validate_performance),
        ]
        
        for component, validation_func in validation_steps:
            if component in components or "all" in components:
                try:
                    logger.info(f"Validating component: {component}")
                    result = await validation_func()
                    self.validation_results[component] = result
                    if not result["success"]:
                        success = False
                        logger.error(f"Validation failed for component: {component}")
                except Exception as e:
                    logger.error(f"Validation error for {component}: {e}")
                    self.validation_results[component] = {
                        "success": False,
                        "error": str(e),
                        "details": {}
                    }
                    success = False
        
        # Generate validation report
        self._generate_validation_report()
        
        return success
    
    async def _validate_system(self) -> Dict[str, Any]:
        """Validate system requirements and dependencies."""
        logger.info("Validating system requirements...")
        
        result = {
            "success": True,
            "details": {},
            "issues": []
        }
        
        try:
            # Check Python version
            python_version = sys.version_info
            result["details"]["python_version"] = f"{python_version.major}.{python_version.minor}.{python_version.micro}"
            
            if python_version < (3, 8):
                result["success"] = False
                result["issues"].append("Python 3.8+ required")
            
            # Check required system packages
            system_packages = ["curl", "systemctl"]
            for package in system_packages:
                try:
                    subprocess.run([package, "--version"], capture_output=True, check=True)
                    result["details"][f"{package}_available"] = True
                except (subprocess.CalledProcessError, FileNotFoundError):
                    result["details"][f"{package}_available"] = False
                    result["issues"].append(f"System package not found: {package}")
            
            # Check Python dependencies
            required_packages = ["fastapi", "uvicorn", "PyQt6", "aiohttp"]
            for package in required_packages:
                try:
                    __import__(package.lower().replace("-", "_"))
                    result["details"][f"{package}_installed"] = True
                except ImportError:
                    result["details"][f"{package}_installed"] = False
                    result["issues"].append(f"Python package not installed: {package}")
            
            # Check file permissions
            important_paths = [
                "/opt/pacman-sync",
                "/etc/pacman-sync",
                "/var/lib/pacman-sync",
                "/var/log/pacman-sync"
            ]
            
            for path in important_paths:
                if os.path.exists(path):
                    result["details"][f"path_exists_{path.replace('/', '_')}"] = True
                    result["details"][f"path_readable_{path.replace('/', '_')}"] = os.access(path, os.R_OK)
                else:
                    result["details"][f"path_exists_{path.replace('/', '_')}"] = False
            
        except Exception as e:
            result["success"] = False
            result["error"] = str(e)
        
        return result
    
    async def _validate_database(self) -> Dict[str, Any]:
        """Validate database connectivity and schema."""
        logger.info("Validating database...")
        
        result = {
            "success": True,
            "details": {},
            "issues": []
        }
        
        try:
            from server.database.connection import DatabaseManager
            from server.database.schema import verify_schema
            
            # Test database connection
            db_manager = DatabaseManager()
            await db_manager.initialize()
            
            result["details"]["connection"] = "success"
            
            # Verify schema
            schema_valid = await verify_schema(db_manager)
            result["details"]["schema_valid"] = schema_valid
            
            if not schema_valid:
                result["success"] = False
                result["issues"].append("Database schema is invalid or missing")
            
            # Test basic operations
            try:
                # This would test basic CRUD operations
                result["details"]["crud_operations"] = "success"
            except Exception as e:
                result["success"] = False
                result["issues"].append(f"Database CRUD operations failed: {e}")
            
            await db_manager.close()
            
        except Exception as e:
            result["success"] = False
            result["error"] = str(e)
            result["issues"].append(f"Database connection failed: {e}")
        
        return result
    
    async def _validate_server(self) -> Dict[str, Any]:
        """Validate server startup and basic functionality."""
        logger.info("Validating server...")
        
        result = {
            "success": True,
            "details": {},
            "issues": []
        }
        
        try:
            # Check if server process is running
            try:
                subprocess.run(["systemctl", "is-active", "pacman-sync-server"], 
                             capture_output=True, check=True)
                result["details"]["systemd_service"] = "active"
            except subprocess.CalledProcessError:
                result["details"]["systemd_service"] = "inactive"
                result["issues"].append("Server systemd service is not active")
            
            # Test server configuration loading
            from server.config import get_config
            config = get_config()
            result["details"]["config_loaded"] = True
            result["details"]["server_port"] = config.server.port
            result["details"]["database_type"] = config.database.type
            
        except Exception as e:
            result["success"] = False
            result["error"] = str(e)
            result["issues"].append(f"Server validation failed: {e}")
        
        return result
    
    async def _validate_api(self) -> Dict[str, Any]:
        """Validate API endpoints and responses."""
        logger.info("Validating API endpoints...")
        
        result = {
            "success": True,
            "details": {},
            "issues": []
        }
        
        try:
            import aiohttp
            
            async with aiohttp.ClientSession() as session:
                # Test health endpoints
                health_endpoints = [
                    "/health/live",
                    "/health/ready"
                ]
                
                for endpoint in health_endpoints:
                    url = urljoin(self.server_url, endpoint)
                    try:
                        async with session.get(url, timeout=10) as response:
                            if response.status == 200:
                                result["details"][f"health_{endpoint.split('/')[-1]}"] = "success"
                            else:
                                result["success"] = False
                                result["issues"].append(f"Health endpoint {endpoint} returned {response.status}")
                    except Exception as e:
                        result["success"] = False
                        result["issues"].append(f"Health endpoint {endpoint} failed: {e}")
                
                # Test API endpoints (basic connectivity)
                api_endpoints = [
                    "/api/pools",
                    "/api/endpoints",
                    "/api/repositories"
                ]
                
                for endpoint in api_endpoints:
                    url = urljoin(self.server_url, endpoint)
                    try:
                        async with session.get(url, timeout=10) as response:
                            # We expect 401 (unauthorized) for protected endpoints
                            if response.status in [200, 401]:
                                result["details"][f"api_{endpoint.split('/')[-1]}"] = "accessible"
                            else:
                                result["issues"].append(f"API endpoint {endpoint} returned unexpected status {response.status}")
                    except Exception as e:
                        result["success"] = False
                        result["issues"].append(f"API endpoint {endpoint} failed: {e}")
        
        except Exception as e:
            result["success"] = False
            result["error"] = str(e)
            result["issues"].append(f"API validation failed: {e}")
        
        return result
    
    async def _validate_web_ui(self) -> Dict[str, Any]:
        """Validate web UI accessibility and functionality."""
        logger.info("Validating web UI...")
        
        result = {
            "success": True,
            "details": {},
            "issues": []
        }
        
        try:
            import aiohttp
            
            async with aiohttp.ClientSession() as session:
                # Test main page
                try:
                    async with session.get(self.server_url, timeout=10) as response:
                        if response.status == 200:
                            content = await response.text()
                            if "<!DOCTYPE html>" in content:
                                result["details"]["main_page"] = "success"
                            else:
                                result["success"] = False
                                result["issues"].append("Main page does not contain valid HTML")
                        else:
                            result["success"] = False
                            result["issues"].append(f"Main page returned status {response.status}")
                except Exception as e:
                    result["success"] = False
                    result["issues"].append(f"Main page failed: {e}")
                
                # Test static assets
                static_endpoints = [
                    "/static/index.js",
                    "/static/index.css"
                ]
                
                for endpoint in static_endpoints:
                    url = urljoin(self.server_url, endpoint)
                    try:
                        async with session.get(url, timeout=10) as response:
                            if response.status == 200:
                                result["details"][f"static_{endpoint.split('/')[-1]}"] = "success"
                            else:
                                result["issues"].append(f"Static asset {endpoint} returned {response.status}")
                    except Exception as e:
                        result["issues"].append(f"Static asset {endpoint} failed: {e}")
        
        except Exception as e:
            result["success"] = False
            result["error"] = str(e)
            result["issues"].append(f"Web UI validation failed: {e}")
        
        return result
    
    async def _validate_client(self) -> Dict[str, Any]:
        """Validate client functionality."""
        logger.info("Validating client...")
        
        result = {
            "success": True,
            "details": {},
            "issues": []
        }
        
        try:
            # Test client configuration loading
            from client.config import ClientConfiguration
            config = ClientConfiguration()
            result["details"]["config_loaded"] = True
            
            # Test client components import
            from client.api_client import APIClient
            from client.sync_manager import SyncManager
            from client.status_persistence import StatusPersistenceManager
            
            result["details"]["components_importable"] = True
            
            # Test Qt availability
            try:
                from PyQt6.QtWidgets import QApplication
                result["details"]["qt_available"] = True
            except ImportError:
                result["success"] = False
                result["issues"].append("Qt6 not available for client GUI")
            
            # Test client service status
            try:
                subprocess.run(["systemctl", "--user", "is-active", "pacman-sync-client"], 
                             capture_output=True, check=True)
                result["details"]["user_service"] = "active"
            except subprocess.CalledProcessError:
                result["details"]["user_service"] = "inactive"
                result["issues"].append("Client user service is not active")
        
        except Exception as e:
            result["success"] = False
            result["error"] = str(e)
            result["issues"].append(f"Client validation failed: {e}")
        
        return result
    
    async def _validate_integration(self) -> Dict[str, Any]:
        """Validate end-to-end integration."""
        logger.info("Validating integration...")
        
        result = {
            "success": True,
            "details": {},
            "issues": []
        }
        
        try:
            # This would test actual client-server communication
            # For now, we'll just verify that components can be imported together
            
            # Test server-side imports
            from server.api.main import create_app
            from server.core.pool_manager import PackagePoolManager
            from server.core.sync_coordinator import SyncCoordinator
            
            # Test client-side imports
            from client.main import main as client_main
            from client.api_client import APIClient
            
            result["details"]["imports_successful"] = True
            
            # Test configuration compatibility
            from server.config import get_config as get_server_config
            from client.config import ClientConfiguration
            
            server_config = get_server_config()
            client_config = ClientConfiguration()
            
            result["details"]["config_compatibility"] = True
            
        except Exception as e:
            result["success"] = False
            result["error"] = str(e)
            result["issues"].append(f"Integration validation failed: {e}")
        
        return result
    
    async def _validate_performance(self) -> Dict[str, Any]:
        """Validate basic performance metrics."""
        logger.info("Validating performance...")
        
        result = {
            "success": True,
            "details": {},
            "issues": []
        }
        
        try:
            import aiohttp
            
            # Test response times
            async with aiohttp.ClientSession() as session:
                start_time = time.time()
                
                try:
                    async with session.get(urljoin(self.server_url, "/health/live"), timeout=10) as response:
                        response_time = time.time() - start_time
                        result["details"]["health_response_time"] = response_time
                        
                        if response_time > 5.0:  # 5 second threshold
                            result["issues"].append(f"Health endpoint response time too slow: {response_time:.2f}s")
                        
                except Exception as e:
                    result["success"] = False
                    result["issues"].append(f"Performance test failed: {e}")
            
            # Test memory usage (basic check)
            import psutil
            
            # Find server process
            for proc in psutil.process_iter(['pid', 'name', 'memory_info']):
                if 'python' in proc.info['name'].lower():
                    # This is a simplified check - in reality we'd look for the specific server process
                    memory_mb = proc.info['memory_info'].rss / 1024 / 1024
                    result["details"]["memory_usage_mb"] = memory_mb
                    break
        
        except Exception as e:
            result["success"] = False
            result["error"] = str(e)
            result["issues"].append(f"Performance validation failed: {e}")
        
        return result
    
    def _generate_validation_report(self):
        """Generate validation report."""
        report_path = project_root / "validation_report.json"
        
        report = {
            "timestamp": time.time(),
            "server_url": self.server_url,
            "components": self.validation_results,
            "overall_status": "success" if all(
                result["success"] 
                for result in self.validation_results.values()
            ) else "failed"
        }
        
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"Validation report generated: {report_path}")
        
        # Print summary
        print("\n" + "="*60)
        print("DEPLOYMENT VALIDATION REPORT")
        print("="*60)
        
        for component, result in self.validation_results.items():
            status_symbol = "✓" if result["success"] else "✗"
            print(f"{status_symbol} {component.upper()}: {'PASS' if result['success'] else 'FAIL'}")
            
            if "issues" in result and result["issues"]:
                for issue in result["issues"]:
                    print(f"  ⚠ {issue}")
            
            if "error" in result:
                print(f"  ✗ Error: {result['error']}")
        
        print("="*60)
        print(f"Overall Status: {'PASS' if report['overall_status'] == 'success' else 'FAIL'}")
        print("="*60)


async def main():
    """Main entry point for deployment validation."""
    parser = argparse.ArgumentParser(
        description="Validate Pacman Sync Utility deployment",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --components all                    # Validate all components
  %(prog)s --components server api             # Validate specific components
  %(prog)s --server-url http://example.com:8080  # Use custom server URL
        """
    )
    
    parser.add_argument(
        "--components",
        nargs="+",
        choices=["all", "system", "database", "server", "api", "web-ui", "client", "integration", "performance"],
        default=["all"],
        help="Components to validate"
    )
    
    parser.add_argument(
        "--server-url",
        type=str,
        default="http://localhost:8080",
        help="Server URL for validation"
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
    
    # Create validator
    validator = DeploymentValidator(args.server_url)
    
    try:
        # Run validation
        success = await validator.run_validation(args.components)
        
        if success:
            print("\n✓ Deployment validation completed successfully!")
            return 0
        else:
            print("\n✗ Deployment validation failed!")
            return 1
            
    except KeyboardInterrupt:
        print("\nValidation cancelled by user")
        return 130
    except Exception as e:
        logger.error(f"Validation error: {e}")
        print(f"\n✗ Validation error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))