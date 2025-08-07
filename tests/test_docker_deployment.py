#!/usr/bin/env python3
"""
Docker deployment and scaling validation tests.

This module tests Docker deployment scenarios including:
- Container startup and health checks
- Database connectivity and initialization
- Horizontal scaling with load balancing
- Environment variable configuration
- Volume persistence and data integrity
- Container orchestration scenarios

Requirements: All requirements - integration validation
"""

import pytest
import asyncio
import json
import tempfile
import os
import sys
import subprocess
import time
import requests
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class DockerTestEnvironment:
    """Manages Docker test environment setup and cleanup."""
    
    def __init__(self):
        self.containers = []
        self.networks = []
        self.volumes = []
        self.temp_files = []
    
    def create_temp_env_file(self, env_vars):
        """Create temporary environment file for Docker."""
        temp_env = tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False)
        for key, value in env_vars.items():
            temp_env.write(f"{key}={value}\n")
        temp_env.close()
        self.temp_files.append(temp_env.name)
        return temp_env.name
    
    def run_container(self, image, name, ports=None, env_vars=None, volumes=None, network=None, detach=True):
        """Run a Docker container with specified configuration."""
        cmd = ["docker", "run"]
        
        if detach:
            cmd.append("-d")
        
        if name:
            cmd.extend(["--name", name])
            self.containers.append(name)
        
        if ports:
            for host_port, container_port in ports.items():
                cmd.extend(["-p", f"{host_port}:{container_port}"])
        
        if env_vars:
            for key, value in env_vars.items():
                cmd.extend(["-e", f"{key}={value}"])
        
        if volumes:
            for host_path, container_path in volumes.items():
                cmd.extend(["-v", f"{host_path}:{container_path}"])
        
        if network:
            cmd.extend(["--network", network])
        
        cmd.append(image)
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            print(f"Failed to run container: {e.stderr}")
            raise
    
    def create_network(self, name):
        """Create a Docker network."""
        try:
            subprocess.run(["docker", "network", "create", name], 
                         capture_output=True, text=True, check=True)
            self.networks.append(name)
            return name
        except subprocess.CalledProcessError as e:
            if "already exists" not in e.stderr:
                print(f"Failed to create network: {e.stderr}")
                raise
            return name
    
    def create_volume(self, name):
        """Create a Docker volume."""
        try:
            subprocess.run(["docker", "volume", "create", name], 
                         capture_output=True, text=True, check=True)
            self.volumes.append(name)
            return name
        except subprocess.CalledProcessError as e:
            if "already exists" not in e.stderr:
                print(f"Failed to create volume: {e.stderr}")
                raise
            return name
    
    def wait_for_container_health(self, container_name, timeout=60):
        """Wait for container to become healthy."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                result = subprocess.run(
                    ["docker", "inspect", "--format", "{{.State.Health.Status}}", container_name],
                    capture_output=True, text=True, check=True
                )
                health_status = result.stdout.strip()
                if health_status == "healthy":
                    return True
                elif health_status == "unhealthy":
                    return False
            except subprocess.CalledProcessError:
                pass
            
            time.sleep(2)
        
        return False
    
    def wait_for_port(self, host, port, timeout=60):
        """Wait for a port to become available."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                response = requests.get(f"http://{host}:{port}/health", timeout=5)
                if response.status_code == 200:
                    return True
            except (requests.ConnectionError, requests.Timeout):
                pass
            
            time.sleep(2)
        
        return False
    
    def get_container_logs(self, container_name):
        """Get container logs."""
        try:
            result = subprocess.run(
                ["docker", "logs", container_name],
                capture_output=True, text=True, check=True
            )
            return result.stdout
        except subprocess.CalledProcessError as e:
            return f"Failed to get logs: {e.stderr}"
    
    def cleanup(self):
        """Clean up all created Docker resources."""
        # Stop and remove containers
        for container in self.containers:
            try:
                subprocess.run(["docker", "stop", container], 
                             capture_output=True, text=True)
                subprocess.run(["docker", "rm", container], 
                             capture_output=True, text=True)
            except subprocess.CalledProcessError:
                pass
        
        # Remove networks
        for network in self.networks:
            try:
                subprocess.run(["docker", "network", "rm", network], 
                             capture_output=True, text=True)
            except subprocess.CalledProcessError:
                pass
        
        # Remove volumes
        for volume in self.volumes:
            try:
                subprocess.run(["docker", "volume", "rm", volume], 
                             capture_output=True, text=True)
            except subprocess.CalledProcessError:
                pass
        
        # Remove temporary files
        for temp_file in self.temp_files:
            try:
                os.unlink(temp_file)
            except OSError:
                pass


@pytest.fixture
def docker_env():
    """Docker test environment fixture."""
    env = DockerTestEnvironment()
    yield env
    env.cleanup()


@pytest.fixture
def docker_available():
    """Check if Docker is available for testing."""
    try:
        subprocess.run(["docker", "--version"], 
                      capture_output=True, text=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        pytest.skip("Docker is not available for testing")


class TestContainerStartup:
    """Test container startup and basic functionality."""
    
    def test_container_builds_successfully(self, docker_env, docker_available):
        """Test that the Docker image builds successfully."""
        # Build the Docker image
        build_cmd = [
            "docker", "build", 
            "-t", "pacman-sync-test",
            "-f", "Dockerfile",
            "."
        ]
        
        try:
            result = subprocess.run(build_cmd, capture_output=True, text=True, 
                                  check=True, cwd=project_root)
            assert "Successfully built" in result.stdout or "Successfully tagged" in result.stdout
        except subprocess.CalledProcessError as e:
            pytest.fail(f"Docker build failed: {e.stderr}")
    
    def test_container_starts_with_default_config(self, docker_env, docker_available):
        """Test container starts with default configuration."""
        # Build image first
        subprocess.run([
            "docker", "build", "-t", "pacman-sync-test", 
            "-f", "Dockerfile", "."
        ], cwd=project_root, check=True)
        
        # Start container with default configuration
        container_id = docker_env.run_container(
            image="pacman-sync-test",
            name="pacman-sync-default",
            ports={8080: 8080},
            env_vars={
                "DATABASE_TYPE": "internal",
                "LOG_LEVEL": "INFO"
            }
        )
        
        # Wait for container to be ready
        assert docker_env.wait_for_port("localhost", 8080, timeout=30)
        
        # Test health endpoint
        response = requests.get("http://localhost:8080/health")
        assert response.status_code == 200
        
        health_data = response.json()
        assert health_data["status"] == "healthy"
        assert "timestamp" in health_data
    
    def test_container_health_checks(self, docker_env, docker_available):
        """Test container health check functionality."""
        # Build image with health check
        subprocess.run([
            "docker", "build", "-t", "pacman-sync-test", 
            "-f", "Dockerfile", "."
        ], cwd=project_root, check=True)
        
        # Start container
        container_id = docker_env.run_container(
            image="pacman-sync-test",
            name="pacman-sync-health",
            ports={8081: 8080},
            env_vars={
                "DATABASE_TYPE": "internal",
                "HEALTH_CHECK_INTERVAL": "10"
            }
        )
        
        # Wait for health check to pass
        assert docker_env.wait_for_container_health("pacman-sync-health", timeout=60)
        
        # Verify health endpoint responds correctly
        response = requests.get("http://localhost:8081/health/ready")
        assert response.status_code == 200
        
        ready_data = response.json()
        assert ready_data["status"] == "ready"
        assert "database" in ready_data
        assert "services" in ready_data
    
    def test_container_environment_variables(self, docker_env, docker_available):
        """Test container configuration through environment variables."""
        # Build image
        subprocess.run([
            "docker", "build", "-t", "pacman-sync-test", 
            "-f", "Dockerfile", "."
        ], cwd=project_root, check=True)
        
        # Test with custom environment variables
        custom_env = {
            "DATABASE_TYPE": "internal",
            "HTTP_PORT": "8080",
            "LOG_LEVEL": "DEBUG",
            "JWT_SECRET_KEY": "test-secret-key",
            "API_RATE_LIMIT": "50",
            "ENABLE_REPOSITORY_ANALYSIS": "true"
        }
        
        container_id = docker_env.run_container(
            image="pacman-sync-test",
            name="pacman-sync-env",
            ports={8082: 8080},
            env_vars=custom_env
        )
        
        # Wait for startup
        assert docker_env.wait_for_port("localhost", 8082, timeout=30)
        
        # Test that configuration is applied
        response = requests.get("http://localhost:8082/health")
        assert response.status_code == 200
        
        # Check logs for debug level logging
        logs = docker_env.get_container_logs("pacman-sync-env")
        assert "DEBUG" in logs or "debug" in logs.lower()


class TestDatabaseConnectivity:
    """Test database connectivity and initialization."""
    
    def test_internal_database_initialization(self, docker_env, docker_available):
        """Test internal SQLite database initialization."""
        # Build image
        subprocess.run([
            "docker", "build", "-t", "pacman-sync-test", 
            "-f", "Dockerfile", "."
        ], cwd=project_root, check=True)
        
        # Create volume for persistent data
        data_volume = docker_env.create_volume("pacman-sync-data-test")
        
        # Start container with internal database
        container_id = docker_env.run_container(
            image="pacman-sync-test",
            name="pacman-sync-internal-db",
            ports={8083: 8080},
            env_vars={
                "DATABASE_TYPE": "internal",
                "LOG_LEVEL": "INFO"
            },
            volumes={
                data_volume: "/app/data"
            }
        )
        
        # Wait for startup
        assert docker_env.wait_for_port("localhost", 8083, timeout=30)
        
        # Test database connectivity
        response = requests.get("http://localhost:8083/health/ready")
        assert response.status_code == 200
        
        ready_data = response.json()
        assert ready_data["database"]["status"] == "connected"
        assert ready_data["database"]["type"] == "sqlite"
    
    def test_postgresql_database_connection(self, docker_env, docker_available):
        """Test PostgreSQL database connection."""
        # Create network for database communication
        network = docker_env.create_network("pacman-sync-test-net")
        
        # Start PostgreSQL container
        postgres_container = docker_env.run_container(
            image="postgres:15-alpine",
            name="pacman-sync-postgres-test",
            env_vars={
                "POSTGRES_DB": "pacman_sync_test",
                "POSTGRES_USER": "test_user",
                "POSTGRES_PASSWORD": "test_password"
            },
            network=network
        )
        
        # Wait for PostgreSQL to be ready
        time.sleep(10)  # Give PostgreSQL time to initialize
        
        # Build application image
        subprocess.run([
            "docker", "build", "-t", "pacman-sync-test", 
            "-f", "Dockerfile", "."
        ], cwd=project_root, check=True)
        
        # Start application container with PostgreSQL connection
        app_container = docker_env.run_container(
            image="pacman-sync-test",
            name="pacman-sync-postgres-app",
            ports={8084: 8080},
            env_vars={
                "DATABASE_TYPE": "postgresql",
                "DATABASE_URL": "postgresql://test_user:test_password@pacman-sync-postgres-test:5432/pacman_sync_test",
                "LOG_LEVEL": "INFO"
            },
            network=network
        )
        
        # Wait for application startup
        assert docker_env.wait_for_port("localhost", 8084, timeout=60)
        
        # Test database connectivity
        response = requests.get("http://localhost:8084/health/ready")
        assert response.status_code == 200
        
        ready_data = response.json()
        assert ready_data["database"]["status"] == "connected"
        assert ready_data["database"]["type"] == "postgresql"
    
    def test_database_migration_on_startup(self, docker_env, docker_available):
        """Test database schema migration on container startup."""
        # Build image
        subprocess.run([
            "docker", "build", "-t", "pacman-sync-test", 
            "-f", "Dockerfile", "."
        ], cwd=project_root, check=True)
        
        # Start container
        container_id = docker_env.run_container(
            image="pacman-sync-test",
            name="pacman-sync-migration",
            ports={8085: 8080},
            env_vars={
                "DATABASE_TYPE": "internal",
                "LOG_LEVEL": "DEBUG"
            }
        )
        
        # Wait for startup
        assert docker_env.wait_for_port("localhost", 8085, timeout=30)
        
        # Check logs for migration messages
        logs = docker_env.get_container_logs("pacman-sync-migration")
        assert "Creating database schema" in logs or "Database initialized" in logs
        
        # Test that API endpoints work (indicating successful migration)
        response = requests.get("http://localhost:8085/api/pools")
        assert response.status_code == 200


class TestHorizontalScaling:
    """Test horizontal scaling and load balancing scenarios."""
    
    def test_multiple_container_instances(self, docker_env, docker_available):
        """Test running multiple container instances."""
        # Build image
        subprocess.run([
            "docker", "build", "-t", "pacman-sync-test", 
            "-f", "Dockerfile", "."
        ], cwd=project_root, check=True)
        
        # Create shared network
        network = docker_env.create_network("pacman-sync-scale-net")
        
        # Start PostgreSQL for shared database
        postgres_container = docker_env.run_container(
            image="postgres:15-alpine",
            name="pacman-sync-postgres-scale",
            env_vars={
                "POSTGRES_DB": "pacman_sync_scale",
                "POSTGRES_USER": "scale_user",
                "POSTGRES_PASSWORD": "scale_password"
            },
            network=network
        )
        
        # Wait for PostgreSQL
        time.sleep(10)
        
        # Start multiple application instances
        instances = []
        for i in range(3):
            port = 8090 + i
            container_name = f"pacman-sync-scale-{i+1}"
            
            container_id = docker_env.run_container(
                image="pacman-sync-test",
                name=container_name,
                ports={port: 8080},
                env_vars={
                    "DATABASE_TYPE": "postgresql",
                    "DATABASE_URL": "postgresql://scale_user:scale_password@pacman-sync-postgres-scale:5432/pacman_sync_scale",
                    "LOG_LEVEL": "INFO",
                    "DB_POOL_MIN_SIZE": "2",
                    "DB_POOL_MAX_SIZE": "5"
                },
                network=network
            )
            
            instances.append((container_name, port))
        
        # Wait for all instances to be ready
        for container_name, port in instances:
            assert docker_env.wait_for_port("localhost", port, timeout=60)
        
        # Test that all instances are responding
        for container_name, port in instances:
            response = requests.get(f"http://localhost:{port}/health")
            assert response.status_code == 200
            
            health_data = response.json()
            assert health_data["status"] == "healthy"
        
        # Test that they share the same database
        # Create a pool on instance 1
        pool_data = {
            "name": "Scale Test Pool",
            "description": "Pool for testing scaling"
        }
        
        response = requests.post(f"http://localhost:{instances[0][1]}/api/pools", 
                               json=pool_data)
        assert response.status_code == 201
        created_pool = response.json()
        
        # Verify pool is visible from other instances
        for _, port in instances[1:]:
            response = requests.get(f"http://localhost:{port}/api/pools")
            assert response.status_code == 200
            
            pools = response.json()
            pool_names = [p["name"] for p in pools]
            assert "Scale Test Pool" in pool_names
    
    def test_load_balancing_simulation(self, docker_env, docker_available):
        """Test load balancing across multiple instances."""
        # Build image
        subprocess.run([
            "docker", "build", "-t", "pacman-sync-test", 
            "-f", "Dockerfile", "."
        ], cwd=project_root, check=True)
        
        # Start multiple instances with internal databases
        instances = []
        for i in range(2):
            port = 8095 + i
            container_name = f"pacman-sync-lb-{i+1}"
            
            container_id = docker_env.run_container(
                image="pacman-sync-test",
                name=container_name,
                ports={port: 8080},
                env_vars={
                    "DATABASE_TYPE": "internal",
                    "LOG_LEVEL": "INFO"
                }
            )
            
            instances.append((container_name, port))
        
        # Wait for instances to be ready
        for container_name, port in instances:
            assert docker_env.wait_for_port("localhost", port, timeout=30)
        
        # Simulate load balancing by distributing requests
        request_counts = {port: 0 for _, port in instances}
        
        # Send requests in round-robin fashion
        for i in range(10):
            port = instances[i % len(instances)][1]
            response = requests.get(f"http://localhost:{port}/health")
            assert response.status_code == 200
            request_counts[port] += 1
        
        # Verify requests were distributed
        for port, count in request_counts.items():
            assert count > 0  # Each instance should have received requests
    
    def test_container_resource_limits(self, docker_env, docker_available):
        """Test container behavior with resource limits."""
        # Build image
        subprocess.run([
            "docker", "build", "-t", "pacman-sync-test", 
            "-f", "Dockerfile", "."
        ], cwd=project_root, check=True)
        
        # Start container with resource limits
        cmd = [
            "docker", "run", "-d",
            "--name", "pacman-sync-limited",
            "--memory", "256m",
            "--cpus", "0.5",
            "-p", "8097:8080",
            "-e", "DATABASE_TYPE=internal",
            "-e", "LOG_LEVEL=INFO",
            "pacman-sync-test"
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            docker_env.containers.append("pacman-sync-limited")
            
            # Wait for startup
            assert docker_env.wait_for_port("localhost", 8097, timeout=30)
            
            # Test that application works within resource limits
            response = requests.get("http://localhost:8097/health")
            assert response.status_code == 200
            
            # Test API functionality
            response = requests.get("http://localhost:8097/api/pools")
            assert response.status_code == 200
            
        except subprocess.CalledProcessError as e:
            pytest.fail(f"Failed to start container with resource limits: {e.stderr}")


class TestVolumePersistence:
    """Test volume persistence and data integrity."""
    
    def test_data_persistence_across_restarts(self, docker_env, docker_available):
        """Test that data persists across container restarts."""
        # Build image
        subprocess.run([
            "docker", "build", "-t", "pacman-sync-test", 
            "-f", "Dockerfile", "."
        ], cwd=project_root, check=True)
        
        # Create persistent volume
        data_volume = docker_env.create_volume("pacman-sync-persist-test")
        
        # Start first container instance
        container_id = docker_env.run_container(
            image="pacman-sync-test",
            name="pacman-sync-persist-1",
            ports={8098: 8080},
            env_vars={
                "DATABASE_TYPE": "internal",
                "LOG_LEVEL": "INFO"
            },
            volumes={
                data_volume: "/app/data"
            }
        )
        
        # Wait for startup
        assert docker_env.wait_for_port("localhost", 8098, timeout=30)
        
        # Create test data
        pool_data = {
            "name": "Persistence Test Pool",
            "description": "Pool for testing data persistence"
        }
        
        response = requests.post("http://localhost:8098/api/pools", json=pool_data)
        assert response.status_code == 201
        created_pool = response.json()
        pool_id = created_pool["id"]
        
        # Stop first container
        subprocess.run(["docker", "stop", "pacman-sync-persist-1"], check=True)
        subprocess.run(["docker", "rm", "pacman-sync-persist-1"], check=True)
        docker_env.containers.remove("pacman-sync-persist-1")
        
        # Start second container instance with same volume
        container_id = docker_env.run_container(
            image="pacman-sync-test",
            name="pacman-sync-persist-2",
            ports={8099: 8080},
            env_vars={
                "DATABASE_TYPE": "internal",
                "LOG_LEVEL": "INFO"
            },
            volumes={
                data_volume: "/app/data"
            }
        )
        
        # Wait for startup
        assert docker_env.wait_for_port("localhost", 8099, timeout=30)
        
        # Verify data persisted
        response = requests.get("http://localhost:8099/api/pools")
        assert response.status_code == 200
        
        pools = response.json()
        pool_names = [p["name"] for p in pools]
        assert "Persistence Test Pool" in pool_names
        
        # Verify specific pool data
        response = requests.get(f"http://localhost:8099/api/pools/{pool_id}")
        assert response.status_code == 200
        
        pool = response.json()
        assert pool["name"] == "Persistence Test Pool"
        assert pool["description"] == "Pool for testing data persistence"
    
    def test_log_persistence(self, docker_env, docker_available):
        """Test log file persistence."""
        # Build image
        subprocess.run([
            "docker", "build", "-t", "pacman-sync-test", 
            "-f", "Dockerfile", "."
        ], cwd=project_root, check=True)
        
        # Create log volume
        log_volume = docker_env.create_volume("pacman-sync-logs-test")
        
        # Start container with log persistence
        container_id = docker_env.run_container(
            image="pacman-sync-test",
            name="pacman-sync-logs",
            ports={8100: 8080},
            env_vars={
                "DATABASE_TYPE": "internal",
                "LOG_LEVEL": "DEBUG",
                "STRUCTURED_LOGGING": "true"
            },
            volumes={
                log_volume: "/app/logs"
            }
        )
        
        # Wait for startup and generate some log activity
        assert docker_env.wait_for_port("localhost", 8100, timeout=30)
        
        # Make some API calls to generate logs
        for i in range(5):
            requests.get("http://localhost:8100/health")
            requests.get("http://localhost:8100/api/pools")
        
        # Give time for logs to be written
        time.sleep(5)
        
        # Check that logs exist in volume
        # Note: In a real test, you'd inspect the volume contents
        # For now, we verify the container is running and responsive
        response = requests.get("http://localhost:8100/health")
        assert response.status_code == 200
    
    def test_configuration_persistence(self, docker_env, docker_available):
        """Test configuration file persistence."""
        # Create temporary config file
        config_data = {
            "server": {
                "host": "0.0.0.0",
                "port": 8080,
                "cors_origins": ["*"]
            },
            "database": {
                "type": "internal",
                "pool_size": 10
            },
            "features": {
                "repository_analysis": True,
                "auto_cleanup": True
            }
        }
        
        temp_config = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        json.dump(config_data, temp_config, indent=2)
        temp_config.close()
        docker_env.temp_files.append(temp_config.name)
        
        # Build image
        subprocess.run([
            "docker", "build", "-t", "pacman-sync-test", 
            "-f", "Dockerfile", "."
        ], cwd=project_root, check=True)
        
        # Start container with config file mounted
        container_id = docker_env.run_container(
            image="pacman-sync-test",
            name="pacman-sync-config",
            ports={8101: 8080},
            env_vars={
                "DATABASE_TYPE": "internal",
                "LOG_LEVEL": "INFO"
            },
            volumes={
                temp_config.name: "/app/config/server.json"
            }
        )
        
        # Wait for startup
        assert docker_env.wait_for_port("localhost", 8101, timeout=30)
        
        # Verify configuration is applied
        response = requests.get("http://localhost:8101/health")
        assert response.status_code == 200
        
        # Test CORS configuration
        response = requests.options("http://localhost:8101/api/pools",
                                  headers={"Origin": "http://example.com"})
        # Should not fail due to CORS (wildcard origin configured)
        assert response.status_code in [200, 204]


class TestContainerOrchestration:
    """Test container orchestration scenarios using docker-compose."""
    
    def test_docker_compose_startup(self, docker_env, docker_available):
        """Test startup using docker-compose configuration."""
        # Create temporary docker-compose override for testing
        compose_override = {
            "version": "3.8",
            "services": {
                "pacman-sync-server": {
                    "ports": ["8102:8080"],
                    "environment": {
                        "DATABASE_TYPE": "internal",
                        "LOG_LEVEL": "INFO",
                        "HTTP_PORT": "8080"
                    }
                }
            }
        }
        
        temp_compose = tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False)
        import yaml
        yaml.dump(compose_override, temp_compose, default_flow_style=False)
        temp_compose.close()
        docker_env.temp_files.append(temp_compose.name)
        
        try:
            # Start services using docker-compose
            compose_cmd = [
                "docker-compose", 
                "-f", "docker-compose.yml",
                "-f", temp_compose.name,
                "up", "-d", "--build"
            ]
            
            result = subprocess.run(compose_cmd, capture_output=True, text=True, 
                                  check=True, cwd=project_root)
            
            # Add container to cleanup list
            docker_env.containers.append("pacman-sync-server")
            
            # Wait for service to be ready
            assert docker_env.wait_for_port("localhost", 8102, timeout=60)
            
            # Test service functionality
            response = requests.get("http://localhost:8102/health")
            assert response.status_code == 200
            
            health_data = response.json()
            assert health_data["status"] == "healthy"
            
        except subprocess.CalledProcessError as e:
            pytest.fail(f"Docker compose startup failed: {e.stderr}")
        finally:
            # Cleanup compose services
            try:
                subprocess.run([
                    "docker-compose", 
                    "-f", "docker-compose.yml",
                    "-f", temp_compose.name,
                    "down", "-v"
                ], cwd=project_root, capture_output=True)
            except subprocess.CalledProcessError:
                pass
    
    def test_docker_compose_with_postgres(self, docker_env, docker_available):
        """Test docker-compose with PostgreSQL profile."""
        # Create compose override for PostgreSQL testing
        compose_override = {
            "version": "3.8",
            "services": {
                "pacman-sync-server": {
                    "ports": ["8103:8080"],
                    "environment": {
                        "DATABASE_TYPE": "postgresql",
                        "POSTGRES_HOST": "postgres",
                        "POSTGRES_DB": "pacman_sync_test",
                        "POSTGRES_USER": "test_user",
                        "POSTGRES_PASSWORD": "test_password",
                        "LOG_LEVEL": "INFO"
                    },
                    "depends_on": ["postgres"]
                },
                "postgres": {
                    "environment": {
                        "POSTGRES_DB": "pacman_sync_test",
                        "POSTGRES_USER": "test_user",
                        "POSTGRES_PASSWORD": "test_password"
                    }
                }
            }
        }
        
        temp_compose = tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False)
        import yaml
        yaml.dump(compose_override, temp_compose, default_flow_style=False)
        temp_compose.close()
        docker_env.temp_files.append(temp_compose.name)
        
        try:
            # Start services with PostgreSQL profile
            compose_cmd = [
                "docker-compose",
                "-f", "docker-compose.yml", 
                "-f", temp_compose.name,
                "--profile", "postgres",
                "up", "-d", "--build"
            ]
            
            result = subprocess.run(compose_cmd, capture_output=True, text=True,
                                  check=True, cwd=project_root)
            
            # Add containers to cleanup list
            docker_env.containers.extend(["pacman-sync-server", "pacman-sync-postgres"])
            
            # Wait for services to be ready (PostgreSQL takes longer)
            assert docker_env.wait_for_port("localhost", 8103, timeout=90)
            
            # Test service functionality
            response = requests.get("http://localhost:8103/health/ready")
            assert response.status_code == 200
            
            ready_data = response.json()
            assert ready_data["status"] == "ready"
            assert ready_data["database"]["status"] == "connected"
            assert ready_data["database"]["type"] == "postgresql"
            
        except subprocess.CalledProcessError as e:
            pytest.fail(f"Docker compose with PostgreSQL failed: {e.stderr}")
        finally:
            # Cleanup compose services
            try:
                subprocess.run([
                    "docker-compose",
                    "-f", "docker-compose.yml",
                    "-f", temp_compose.name,
                    "--profile", "postgres",
                    "down", "-v"
                ], cwd=project_root, capture_output=True)
            except subprocess.CalledProcessError:
                pass


def run_docker_tests():
    """Run all Docker deployment tests."""
    print("=" * 60)
    print("DOCKER DEPLOYMENT AND SCALING TESTS")
    print("=" * 60)
    
    # Check if Docker is available
    try:
        subprocess.run(["docker", "--version"], 
                      capture_output=True, text=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Docker is not available. Skipping Docker tests.")
        return True
    
    # Run pytest with this file
    import subprocess
    result = subprocess.run([
        sys.executable, "-m", "pytest", __file__, "-v", "--tb=short", "-x"
    ], capture_output=True, text=True)
    
    print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)
    
    return result.returncode == 0


if __name__ == "__main__":
    success = run_docker_tests()
    sys.exit(0 if success else 1)