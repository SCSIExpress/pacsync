"""
Configuration module for Pacman Sync Utility Server.

This module centralizes all configuration management using environment variables
with appropriate defaults and validation.
"""

import os
import logging
from typing import Optional, List
from dataclasses import dataclass


@dataclass
class DatabaseConfig:
    """Database configuration settings."""
    type: str
    url: Optional[str]
    host: Optional[str]
    port: Optional[int]
    name: Optional[str]
    user: Optional[str]
    password: Optional[str]
    pool_min_size: int
    pool_max_size: int


@dataclass
class ServerConfig:
    """HTTP server configuration settings."""
    host: str
    port: int
    environment: str
    log_level: str
    request_timeout: int
    cors_origins: List[str]
    structured_logging: bool


@dataclass
class SecurityConfig:
    """Security-related configuration settings."""
    jwt_secret_key: str
    api_rate_limit: int


@dataclass
class FeatureConfig:
    """Feature flag configuration settings."""
    enable_repository_analysis: bool
    auto_cleanup_old_states: bool
    max_state_snapshots: int


@dataclass
class MonitoringConfig:
    """Monitoring and logging configuration settings."""
    health_check_interval: int
    log_max_size: str
    log_backup_count: int


@dataclass
class AppConfig:
    """Complete application configuration."""
    database: DatabaseConfig
    server: ServerConfig
    security: SecurityConfig
    features: FeatureConfig
    monitoring: MonitoringConfig


def get_env_bool(key: str, default: bool = False) -> bool:
    """Get boolean value from environment variable."""
    value = os.getenv(key, str(default)).lower()
    return value in ('true', '1', 'yes', 'on')


def get_env_int(key: str, default: int) -> int:
    """Get integer value from environment variable."""
    try:
        return int(os.getenv(key, str(default)))
    except ValueError:
        return default


def get_env_list(key: str, default: List[str] = None, separator: str = ',') -> List[str]:
    """Get list value from environment variable."""
    if default is None:
        default = []
    
    value = os.getenv(key, '')
    if not value:
        return default
    
    return [item.strip() for item in value.split(separator) if item.strip()]


def load_config() -> AppConfig:
    """Load configuration from environment variables."""
    
    # Database configuration
    database_type = os.getenv("DATABASE_TYPE", "internal")
    database_url = os.getenv("DATABASE_URL")
    
    # Parse PostgreSQL connection details if URL not provided
    postgres_host = os.getenv("POSTGRES_HOST", "postgres")
    postgres_port = get_env_int("POSTGRES_PORT", 5432)
    postgres_db = os.getenv("POSTGRES_DB", "pacman_sync")
    postgres_user = os.getenv("POSTGRES_USER", "pacman_sync")
    postgres_password = os.getenv("POSTGRES_PASSWORD", "")
    
    # If no DATABASE_URL provided but using PostgreSQL, construct it
    if database_type == "postgresql" and not database_url and postgres_password:
        database_url = f"postgresql://{postgres_user}:{postgres_password}@{postgres_host}:{postgres_port}/{postgres_db}"
    
    database_config = DatabaseConfig(
        type=database_type,
        url=database_url,
        host=postgres_host,
        port=postgres_port,
        name=postgres_db,
        user=postgres_user,
        password=postgres_password,
        pool_min_size=get_env_int("DB_POOL_MIN_SIZE", 1),
        pool_max_size=get_env_int("DB_POOL_MAX_SIZE", 10)
    )
    
    # Server configuration
    server_config = ServerConfig(
        host=os.getenv("HTTP_HOST", "0.0.0.0"),
        port=get_env_int("HTTP_PORT", 8080),
        environment=os.getenv("ENVIRONMENT", "production"),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        request_timeout=get_env_int("REQUEST_TIMEOUT", 60),
        cors_origins=get_env_list("CORS_ORIGINS", ["*"]),
        structured_logging=get_env_bool("STRUCTURED_LOGGING", False)
    )
    
    # Security configuration
    security_config = SecurityConfig(
        jwt_secret_key=os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production"),
        api_rate_limit=get_env_int("API_RATE_LIMIT", 100)
    )
    
    # Feature configuration
    features_config = FeatureConfig(
        enable_repository_analysis=get_env_bool("ENABLE_REPOSITORY_ANALYSIS", True),
        auto_cleanup_old_states=get_env_bool("AUTO_CLEANUP_OLD_STATES", True),
        max_state_snapshots=get_env_int("MAX_STATE_SNAPSHOTS", 10)
    )
    
    # Monitoring configuration
    monitoring_config = MonitoringConfig(
        health_check_interval=get_env_int("HEALTH_CHECK_INTERVAL", 30),
        log_max_size=os.getenv("LOG_MAX_SIZE", "10MB"),
        log_backup_count=get_env_int("LOG_BACKUP_COUNT", 5)
    )
    
    return AppConfig(
        database=database_config,
        server=server_config,
        security=security_config,
        features=features_config,
        monitoring=monitoring_config
    )


def setup_logging(config: AppConfig) -> None:
    """Setup logging configuration based on config."""
    log_level = getattr(logging, config.server.log_level.upper(), logging.INFO)
    
    if config.server.structured_logging:
        # JSON structured logging format
        log_format = '{"timestamp": "%(asctime)s", "level": "%(levelname)s", "logger": "%(name)s", "message": "%(message)s"}'
    else:
        # Standard logging format
        log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    logging.basicConfig(
        level=log_level,
        format=log_format,
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Set specific logger levels
    if config.server.environment == "development":
        logging.getLogger("uvicorn").setLevel(logging.DEBUG)
        logging.getLogger("uvicorn.access").setLevel(logging.DEBUG)
    else:
        logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


# Global configuration instance
_config: Optional[AppConfig] = None


def get_config() -> AppConfig:
    """Get the global configuration instance."""
    global _config
    if _config is None:
        _config = load_config()
    return _config


def reload_config() -> AppConfig:
    """Reload configuration from environment variables."""
    global _config
    _config = load_config()
    return _config