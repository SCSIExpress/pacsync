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

### Server Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Configure database (PostgreSQL recommended for production):
```bash
export DATABASE_URL="postgresql://user:pass@localhost/pacman_sync"
```

3. Run database migrations:
```bash
python -m server.database.migrations
```

4. Start the server:
```bash
python -m server.main
```

### Client Setup

1. Install the client:
```bash
python -m client.main --install
```

2. Configure server connection:
```bash
python -m client.main --configure
```

3. Register endpoint with server:
```bash
python -m client.main --register
```

### Docker Deployment

```bash
docker build -t pacman-sync-server .
docker run -d -p 8000:8000 -e DATABASE_URL="..." pacman-sync-server
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

[Add your license here]

## Support

For issues and questions:
- Check the documentation in `docs/`
- Review existing issues on GitHub
- Create a new issue with detailed information

## Roadmap

See `.kiro/specs/pacman-sync-utility/tasks.md` for detailed implementation progress and planned features.