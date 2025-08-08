# Project Structure

This document outlines the organization of the Pacman Sync Utility project.

## Root Directory

```
pacman-sync-utility/
├── README.md                    # Main project documentation
├── LICENSE                      # Project license
├── CHANGELOG.md                 # Version history and changes
├── contributing.md              # Contribution guidelines
├── PROJECT_STRUCTURE.md         # This file
├── requirements.txt             # Client Python dependencies
├── server-requirements.txt      # Server Python dependencies
├── setup.py                     # Python package setup
├── CMakeLists.txt              # C++ build configuration
├── Dockerfile                   # Docker container definition
├── docker-compose.yml          # Docker Compose configuration
├── docker-compose.scale.yml    # Scaling configuration
├── .env.example                # Environment variables template
└── .gitignore                  # Git ignore patterns
```

## Core Components

### Server (`server/`)
Central coordination server with REST API and web interface.

```
server/
├── __init__.py
├── main.py                     # Server entry point
├── api/                        # REST API endpoints
│   ├── pools.py               # Pool management API
│   ├── endpoints.py           # Endpoint management API
│   └── sync.py                # Synchronization API
├── core/                       # Business logic
│   ├── pool_manager.py        # Pool management service
│   ├── repository_analyzer.py # Repository analysis
│   └── sync_coordinator.py    # Sync coordination
├── database/                   # Database layer
│   ├── models.py              # Data models
│   ├── migrations/            # Database migrations
│   └── connection.py          # Database connection
└── web/                       # Web UI assets
    ├── static/                # Static files (CSS, JS)
    └── templates/             # HTML templates
```

### Client (`client/`)
Desktop client application with Qt GUI and system integration.

```
client/
├── __init__.py
├── main.py                     # Client entry point
├── api_client.py              # Server communication
├── config.py                  # Configuration management
├── error_handling.py          # Error handling utilities
├── error_recovery.py          # Error recovery mechanisms
├── package_operations.py      # Package management
├── pacman_interface.py        # Pacman integration
├── status_persistence.py      # State persistence
├── sync_manager.py            # Synchronization logic
├── system_tray_handler.py     # System tray integration
├── waybar_integration.py      # WayBar status integration
├── qt/                        # Qt GUI components
│   ├── main_window.py         # Main application window
│   ├── tray_icon.py          # System tray icon
│   └── dialogs/              # Dialog windows
└── auth/                      # Authentication
    └── token_manager.py       # JWT token management
```

### Shared (`shared/`)
Common data models and utilities used by both server and client.

```
shared/
├── __init__.py
├── models.py                   # Data models and interfaces
├── constants.py               # Application constants
├── utils.py                   # Utility functions
└── exceptions.py              # Custom exceptions
```

## Configuration

### Configuration Files (`config/`)
Template configuration files and examples.

```
config/
├── server.conf.template        # Server configuration template
├── client.conf.template        # Client configuration template
└── docker/                    # Docker-specific configs
    ├── production.env         # Production environment
    └── development.env        # Development environment
```

### System Integration (`systemd/`)
Systemd service files for system integration.

```
systemd/
├── pacman-sync-server.service  # Server system service
├── pacman-sync-client.service  # Client user service
└── install-services.sh        # Service installation script
```

## Documentation (`docs/`)

```
docs/
├── README.md                   # Documentation index
├── architecture.md            # System architecture
├── api-documentation.md       # API reference
├── desktop-client-guide.md    # Client user guide
├── web-ui-guide.md            # Web UI guide
├── configuration.md           # Configuration guide
├── development-setup.md       # Development setup
├── troubleshooting.md         # Troubleshooting guide
└── docker-quick-reference.md  # Docker commands
```

## Testing (`tests/`)

```
tests/
├── __init__.py
├── conftest.py                # Pytest configuration
├── unit/                      # Unit tests
│   ├── test_models.py         # Data model tests
│   ├── test_api.py           # API endpoint tests
│   └── test_client.py        # Client functionality tests
├── integration/               # Integration tests
│   ├── test_server_client.py # Server-client communication
│   └── test_sync_operations.py # Sync operation tests
└── fixtures/                  # Test data and fixtures
    ├── sample_configs.py      # Sample configurations
    └── mock_data.py          # Mock data for tests
```

## Deployment

### Docker (`deploy/`)
Docker deployment configurations and scripts.

```
deploy/
├── production/                # Production deployment
│   ├── docker-compose.yml    # Production compose file
│   └── nginx.conf            # Nginx configuration
└── development/               # Development deployment
    └── docker-compose.dev.yml # Development compose file
```

### Scripts (`scripts/`)
Utility scripts for deployment and maintenance.

```
scripts/
├── README.md                  # Scripts documentation
├── validate-deployment.py     # Deployment validation
├── integrate-components.py    # Component integration
└── final-integration-test.py  # Integration testing
```

### Root Level Scripts
- `install.sh` - System installation script
- `deploy.sh` - Docker deployment script
- `build-and-push.sh` - Docker image management
- `test-docker.sh` - Docker testing
- `validate-docker.sh` - Docker validation
- `healthcheck.sh` - Health check script
- `ghcr-login.sh` - Container registry login

## Data Directories

### Runtime Data (`data/`)
Runtime data storage (created during execution).

```
data/
├── database/                  # Database files (SQLite)
├── logs/                     # Application logs
├── cache/                    # Temporary cache files
└── backups/                  # Database backups
```

### Logs (`logs/`)
Application log files (created during execution).

```
logs/
├── server.log                # Server application logs
├── client.log               # Client application logs
├── access.log               # HTTP access logs
└── error.log                # Error logs
```

## Development Files

### IDE Configuration
- `.vscode/` - Visual Studio Code settings
- `.kiro/` - Kiro AI assistant configuration

### Build Artifacts
- `__pycache__/` - Python bytecode cache
- `.pytest_cache/` - Pytest cache
- `build/` - Build artifacts
- `dist/` - Distribution packages
- `venv/` - Python virtual environment

## Key Features by Directory

### Server Features
- REST API for pool and endpoint management
- Web-based management interface
- Repository compatibility analysis
- Synchronization coordination
- Database management (PostgreSQL/SQLite)
- Authentication and authorization

### Client Features
- Qt-based desktop application
- System tray integration
- Pacman package manager integration
- Real-time status updates
- WayBar integration
- Command-line interface
- Automatic error recovery

### Shared Features
- Common data models
- Utility functions
- Exception handling
- Configuration management
- Logging infrastructure

This structure provides clear separation of concerns while maintaining modularity and ease of development.