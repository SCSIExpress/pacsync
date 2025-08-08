# Pacman Sync Utility

A comprehensive system for managing package synchronization across multiple Arch Linux endpoints. This utility provides both a centralized server for coordination and desktop clients for individual system management.

## Features

- **Centralized Package Pool Management**: Create and manage groups of endpoints with synchronized package states
- **Multi-Endpoint Synchronization**: Coordinate package installations across multiple Arch Linux systems
- **Desktop Integration**: Qt-based system tray application with real-time status updates
- **Web Management Interface**: Browser-based dashboard for pool and endpoint management
- **WayBar Integration**: Status bar integration for Wayland compositors
- **Command Line Interface**: Full CLI support for automation and scripting
- **Docker Support**: Containerized server deployment with scaling capabilities

## Architecture

The system consists of three main components:

### Server (`server/`)
- **Core Services**: Package pool management, repository analysis, and synchronization coordination
- **REST API**: Comprehensive API for all operations
- **Web UI**: React-based management interface
- **Database**: PostgreSQL/SQLite support with migrations

### Client (`client/`)
- **Qt Desktop App**: System tray integration with status monitoring
- **API Client**: HTTP client for server communication
- **Pacman Integration**: Direct integration with pacman package manager
- **Status Persistence**: Maintains state between GUI and CLI modes

### Shared (`shared/`)
- **Data Models**: Common data structures and interfaces
- **Utilities**: Shared functionality between server and client

## Quick Start

### Automated Installation

The easiest way to install and configure the Pacman Sync Utility is using the setup script:

```bash
# Full installation with both server and client
sudo python3 setup.py install --server --client --systemd

# Configure with default settings
python3 setup.py configure --server --client

# Start services
python3 setup.py start --services server client

# Check status
python3 setup.py status
```

### Manual Installation

#### Server Setup

1. Install using the installation script:
```bash
sudo ./install.sh --server --systemd
```

2. Configure the server:
```bash
sudo cp config/server.conf.template /etc/pacman-sync/server.conf
sudo nano /etc/pacman-sync/server.conf  # Customize settings
```

3. Start the server:
```bash
sudo systemctl enable --now pacman-sync-server
```

4. Verify server is running:
```bash
curl http://localhost:8080/health/live
```

#### Client Setup

1. Install the client:
```bash
sudo ./install.sh --client --systemd
```

2. Configure the client:
```bash
cp config/client.conf.template ~/.config/pacman-sync/client.conf
nano ~/.config/pacman-sync/client.conf  # Set server URL and endpoint name
```

3. Start the client:
```bash
systemctl --user enable --now pacman-sync-client
```

4. Check system tray for the sync status icon

### Docker Deployment

#### Production Deployment

```bash
# Build and start with Docker Compose
./deploy.sh prod --database postgresql --port 8080

# Or manually with Docker
docker build -t pacman-sync-server .
docker run -d -p 8080:8080 \
  -e DATABASE_TYPE=postgresql \
  -e DATABASE_URL="postgresql://user:pass@host:5432/db" \
  -e JWT_SECRET_KEY="$(openssl rand -hex 32)" \
  pacman-sync-server
```

#### Development Environment

```bash
# Start development environment
./deploy.sh dev

# Or with Docker Compose
docker-compose --profile dev up -d
```

### Validation and Integration

After installation, validate the deployment:

```bash
# Validate all components
python3 scripts/validate-deployment.py --components all

# Integrate components
python3 scripts/integrate-components.py --components all

# Run comprehensive setup validation
python3 setup.py validate
```

## Usage

### Desktop Client
- System tray icon shows current sync status
- Right-click for sync operations and configuration
- Automatic status updates and notifications

### Command Line
```bash
# Sync to latest state
python -m client.main --sync

# Set current state as latest
python -m client.main --set-latest

# Revert to previous state
python -m client.main --revert

# Check status
python -m client.main --status
```

### WayBar Integration
Add to your WayBar config:
```json
{
    "custom/pacman-sync": {
        "exec": "python -m client.main --waybar-status",
        "on-click": "python -m client.main --sync",
        "interval": 30
    }
}
```

## Development

### Project Structure
```
├── server/          # Central coordination server
│   ├── api/         # REST API endpoints
│   ├── core/        # Core business logic
│   ├── database/    # Database models and migrations
│   └── web/         # Web UI assets
├── client/          # Desktop client application
│   ├── qt/          # Qt GUI components
│   └── ...          # Client modules
├── shared/          # Shared data models and interfaces
├── tests/           # Test suite
└── docs/            # Documentation
```

### Running Tests
```bash
pytest tests/
```

### Building Documentation
```bash
# Documentation is in docs/ directory
# See docs/README.md for building instructions
```

## Requirements

- **Server**: Python 3.8+, PostgreSQL/SQLite, Docker (optional)
- **Client**: Python 3.8+, Qt6, Arch Linux with pacman
- **Network**: HTTP/HTTPS connectivity between clients and server

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Documentation

For detailed information, see the documentation in the `docs/` directory:

- **[Documentation Index](docs/README.md)** - Complete documentation overview
- **[Desktop Client Guide](docs/desktop-client-guide.md)** - Qt desktop client usage
- **[Web UI Guide](docs/web-ui-guide.md)** - Web interface management  
- **[Architecture Overview](docs/architecture.md)** - System design and components
- **[API Documentation](docs/api-documentation.md)** - REST API reference
- **[Development Setup](docs/development-setup.md)** - Development environment
- **[Docker Deployment](DOCKER.md)** - Container deployment guide
- **[Configuration Guide](docs/configuration.md)** - Configuration options
- **[Troubleshooting Guide](docs/troubleshooting.md)** - Common issues and solutions

### Quick Reference

- **End Users**: Start with [Documentation Index](docs/README.md)
- **Developers**: Begin with [Development Setup](docs/development-setup.md)
- **Deployment**: See [Docker Guide](DOCKER.md) or [Installation Guide](docs/installation.md)

## Support

For issues and questions:
- Check the [Documentation Index](docs/README.md)
- Review the [Troubleshooting Guide](docs/troubleshooting.md)
- Review existing issues on GitHub
- Create a new issue with detailed information

## Roadmap

See `.kiro/specs/pacman-sync-utility/tasks.md` for detailed implementation progress and planned features.