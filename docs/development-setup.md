# Development Setup Guide

This guide covers setting up a development environment for contributing to the Pacman Sync Utility project.

## Prerequisites

### System Requirements

- **Operating System**: Linux (Arch Linux recommended for client development)
- **Python**: 3.8 or higher
- **Git**: For version control
- **Docker**: For containerized development (optional)
- **Node.js**: 16+ for web UI development
- **PostgreSQL**: For database development (optional, can use SQLite)

### Development Tools

```bash
# Essential development tools
sudo pacman -S base-devel git python python-pip nodejs npm

# Qt development (for client GUI)
sudo pacman -S qt6-base python-pyqt6 python-pyqt6-tools

# Database tools
sudo pacman -S postgresql sqlite

# Optional: Docker for containerized development
sudo pacman -S docker docker-compose
sudo systemctl enable --now docker
sudo usermod -aG docker $USER
```

## Project Setup

### 1. Clone Repository

```bash
# Clone the main repository
git clone https://github.com/your-org/pacman-sync-utility.git
cd pacman-sync-utility

# Set up upstream remote (for contributors)
git remote add upstream https://github.com/original-org/pacman-sync-utility.git
```

### 2. Python Environment Setup

#### Using Virtual Environment (Recommended)

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
source venv/bin/activate

# Install development dependencies
pip install -r requirements.txt
pip install -r server-requirements.txt
pip install -r dev-requirements.txt
```

#### Using Poetry (Alternative)

```bash
# Install Poetry
curl -sSL https://install.python-poetry.org | python3 -

# Install dependencies
poetry install --with dev

# Activate environment
poetry shell
```

### 3. Database Setup

#### SQLite (Quick Start)

```bash
# SQLite requires no additional setup
# Database file will be created automatically
export DATABASE_TYPE=internal
export DATABASE_FILE=./dev-database.db
```

#### PostgreSQL (Recommended for Development)

```bash
# Start PostgreSQL service
sudo systemctl start postgresql

# Create development database
sudo -u postgres createuser -P pacman_sync_dev
sudo -u postgres createdb -O pacman_sync_dev pacman_sync_dev

# Set environment variables
export DATABASE_TYPE=postgresql
export DATABASE_URL="postgresql://pacman_sync_dev:password@localhost:5432/pacman_sync_dev"
```

### 4. Configuration Files

#### Server Configuration

```bash
# Create development server config
cp config/server.conf.template config/server-dev.conf

# Edit configuration
nano config/server-dev.conf
```

```ini
# config/server-dev.conf
[database]
type = postgresql
url = postgresql://pacman_sync_dev:password@localhost:5432/pacman_sync_dev

[server]
host = 127.0.0.1
port = 8080
debug = true
workers = 1

[security]
jwt_secret_key = dev-secret-key-not-for-production
api_rate_limit = 1000

[logging]
level = DEBUG
file = 
```

#### Client Configuration

```bash
# Create development client config
mkdir -p ~/.config/pacman-sync
cp config/client.conf.template ~/.config/pacman-sync/client-dev.conf

# Edit configuration
nano ~/.config/pacman-sync/client-dev.conf
```

```ini
# ~/.config/pacman-sync/client-dev.conf
[server]
url = http://127.0.0.1:8080
api_key = dev-api-key

[client]
endpoint_name = dev-client
pool_id = dev-pool
auto_sync = false

[logging]
level = DEBUG
file = ./client-dev.log
```

## Development Workflow

### 1. Database Initialization

```bash
# Run database migrations
python -m server.database.migrations --apply-all

# Verify database setup
python -m server.database.connection --test

# Create initial data (optional)
python -m server.database.seed --dev-data
```

### 2. Start Development Server

```bash
# Start server with development config
python -m server.main --config config/server-dev.conf --reload

# Or with environment variables
export SERVER_CONFIG=config/server-dev.conf
python -m server.main --reload
```

### 3. Start Development Client

```bash
# Start client with development config
python -m client.main --config ~/.config/pacman-sync/client-dev.conf --debug

# Or run without system tray for debugging
python -m client.main --config ~/.config/pacman-sync/client-dev.conf --no-tray --debug
```

### 4. Web UI Development

```bash
# Navigate to web UI directory
cd server/web

# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build
```

## Development Tools

### Code Quality Tools

#### Pre-commit Hooks

```bash
# Install pre-commit
pip install pre-commit

# Install hooks
pre-commit install

# Run hooks manually
pre-commit run --all-files
```

#### Linting and Formatting

```bash
# Install development tools
pip install black flake8 mypy isort

# Format code
black .

# Check code style
flake8 .

# Type checking
mypy server/ client/ shared/

# Sort imports
isort .
```

#### Configuration Files

Create `.pre-commit-config.yaml`:
```yaml
repos:
  - repo: https://github.com/psf/black
    rev: 23.1.0
    hooks:
      - id: black
        language_version: python3

  - repo: https://github.com/pycqa/flake8
    rev: 6.0.0
    hooks:
      - id: flake8
        args: [--max-line-length=88, --extend-ignore=E203]

  - repo: https://github.com/pycqa/isort
    rev: 5.12.0
    hooks:
      - id: isort
        args: [--profile=black]

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.0.1
    hooks:
      - id: mypy
        additional_dependencies: [types-requests]
```

### Testing Framework

#### Running Tests

```bash
# Run all tests
pytest

# Run specific test categories
pytest tests/unit/
pytest tests/integration/
pytest tests/e2e/

# Run with coverage
pytest --cov=server --cov=client --cov=shared

# Run specific test file
pytest tests/test_api_endpoints.py

# Run with verbose output
pytest -v

# Run tests matching pattern
pytest -k "test_pool"
```

#### Test Configuration

Create `pytest.ini`:
```ini
[tool:pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = 
    --strict-markers
    --disable-warnings
    --tb=short
markers =
    unit: Unit tests
    integration: Integration tests
    e2e: End-to-end tests
    slow: Slow tests
```

#### Writing Tests

```python
# tests/unit/test_pool_manager.py
import pytest
from server.core.pool_manager import PoolManager
from server.database.connection import get_test_db

@pytest.fixture
def pool_manager():
    db = get_test_db()
    return PoolManager(db)

def test_create_pool(pool_manager):
    pool_data = {
        "name": "test-pool",
        "description": "Test pool",
        "settings": {"auto_sync": False}
    }
    
    pool = pool_manager.create_pool(pool_data)
    
    assert pool.name == "test-pool"
    assert pool.settings["auto_sync"] is False

def test_pool_name_uniqueness(pool_manager):
    pool_data = {"name": "duplicate-pool", "description": "Test"}
    
    pool_manager.create_pool(pool_data)
    
    with pytest.raises(ValueError, match="Pool name already exists"):
        pool_manager.create_pool(pool_data)
```

### Debugging

#### Server Debugging

```bash
# Run server with debugger
python -m pdb -m server.main --config config/server-dev.conf

# Or with IDE debugging
# Set breakpoints in your IDE and run:
python -m server.main --config config/server-dev.conf --debug
```

#### Client Debugging

```bash
# Run client with debugger
python -m pdb -m client.main --config ~/.config/pacman-sync/client-dev.conf

# Debug Qt application
QT_DEBUG_PLUGINS=1 python -m client.main --debug --no-tray
```

#### Database Debugging

```bash
# Connect to development database
psql -h localhost -U pacman_sync_dev -d pacman_sync_dev

# Enable query logging
export SQLALCHEMY_ECHO=true
python -m server.main --config config/server-dev.conf
```

## Docker Development

### Development Container

```bash
# Build development image
docker build -f Dockerfile.dev -t pacman-sync-dev .

# Run development container
docker run -it --rm \
  -v $(pwd):/app \
  -p 8080:8080 \
  -e DATABASE_TYPE=internal \
  pacman-sync-dev bash

# Or use docker-compose
docker-compose -f docker-compose.dev.yml up -d
```

### Dockerfile.dev

```dockerfile
FROM python:3.11-slim

# Install development dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt server-requirements.txt dev-requirements.txt ./
RUN pip install -r dev-requirements.txt

# Install development tools
RUN pip install black flake8 mypy isort pytest

# Set up development environment
ENV PYTHONPATH=/app
ENV DATABASE_TYPE=internal
ENV LOG_LEVEL=DEBUG

# Development command
CMD ["python", "-m", "server.main", "--reload"]
```

## IDE Configuration

### Visual Studio Code

#### Extensions

Install recommended extensions:
```json
{
    "recommendations": [
        "ms-python.python",
        "ms-python.black-formatter",
        "ms-python.flake8",
        "ms-python.mypy-type-checker",
        "ms-vscode.vscode-json",
        "bradlc.vscode-tailwindcss",
        "esbenp.prettier-vscode"
    ]
}
```

#### Settings

Create `.vscode/settings.json`:
```json
{
    "python.defaultInterpreterPath": "./venv/bin/python",
    "python.linting.enabled": true,
    "python.linting.flake8Enabled": true,
    "python.formatting.provider": "black",
    "python.testing.pytestEnabled": true,
    "python.testing.pytestArgs": ["tests"],
    "files.exclude": {
        "**/__pycache__": true,
        "**/*.pyc": true,
        ".pytest_cache": true,
        ".mypy_cache": true
    }
}
```

#### Launch Configuration

Create `.vscode/launch.json`:
```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Debug Server",
            "type": "python",
            "request": "launch",
            "module": "server.main",
            "args": ["--config", "config/server-dev.conf", "--debug"],
            "console": "integratedTerminal",
            "env": {
                "PYTHONPATH": "${workspaceFolder}"
            }
        },
        {
            "name": "Debug Client",
            "type": "python",
            "request": "launch",
            "module": "client.main",
            "args": ["--config", "~/.config/pacman-sync/client-dev.conf", "--debug", "--no-tray"],
            "console": "integratedTerminal",
            "env": {
                "PYTHONPATH": "${workspaceFolder}"
            }
        },
        {
            "name": "Run Tests",
            "type": "python",
            "request": "launch",
            "module": "pytest",
            "args": ["tests/", "-v"],
            "console": "integratedTerminal"
        }
    ]
}
```

### PyCharm

#### Project Configuration

1. **Interpreter Setup**:
   - File → Settings → Project → Python Interpreter
   - Add interpreter from virtual environment: `./venv/bin/python`

2. **Run Configurations**:
   - Run → Edit Configurations
   - Add Python configuration for server and client modules

3. **Code Style**:
   - File → Settings → Editor → Code Style → Python
   - Import settings from `.editorconfig`

## Contributing Guidelines

### Git Workflow

#### Branch Naming

```bash
# Feature branches
git checkout -b feature/add-pool-templates

# Bug fix branches
git checkout -b fix/sync-operation-timeout

# Documentation branches
git checkout -b docs/update-api-documentation
```

#### Commit Messages

Follow conventional commit format:
```
type(scope): description

[optional body]

[optional footer]
```

Examples:
```
feat(server): add pool template functionality
fix(client): resolve system tray icon not appearing
docs(api): update endpoint documentation
test(integration): add multi-endpoint sync tests
```

#### Pull Request Process

1. **Create Feature Branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make Changes and Test**
   ```bash
   # Make your changes
   # Run tests
   pytest
   
   # Run linting
   black .
   flake8 .
   ```

3. **Commit Changes**
   ```bash
   git add .
   git commit -m "feat(component): add new feature"
   ```

4. **Push and Create PR**
   ```bash
   git push origin feature/your-feature-name
   # Create pull request on GitHub
   ```

### Code Review Checklist

- [ ] Code follows project style guidelines
- [ ] All tests pass
- [ ] New features have tests
- [ ] Documentation is updated
- [ ] No security vulnerabilities introduced
- [ ] Performance impact considered
- [ ] Backward compatibility maintained

## Troubleshooting Development Issues

### Common Problems

#### Import Errors

```bash
# Fix Python path issues
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Or add to your shell profile
echo 'export PYTHONPATH="${PYTHONPATH}:$(pwd)"' >> ~/.bashrc
```

#### Database Connection Issues

```bash
# Check PostgreSQL service
sudo systemctl status postgresql

# Test database connection
psql -h localhost -U pacman_sync_dev -d pacman_sync_dev -c "SELECT 1;"

# Reset database
python -m server.database.migrations --reset --confirm
python -m server.database.migrations --apply-all
```

#### Qt/GUI Issues

```bash
# Check Qt installation
python -c "from PyQt6.QtWidgets import QApplication; print('Qt OK')"

# Run with Qt debug
QT_DEBUG_PLUGINS=1 python -m client.main --debug

# Test without GUI
python -m client.main --no-tray --debug
```

#### Web UI Development Issues

```bash
# Clear npm cache
npm cache clean --force

# Reinstall dependencies
rm -rf node_modules package-lock.json
npm install

# Check for port conflicts
lsof -i :3000
```

### Performance Profiling

#### Python Profiling

```bash
# Profile server startup
python -m cProfile -o server_profile.prof -m server.main --config config/server-dev.conf

# Analyze profile
python -c "
import pstats
p = pstats.Stats('server_profile.prof')
p.sort_stats('cumulative').print_stats(20)
"
```

#### Memory Profiling

```bash
# Install memory profiler
pip install memory-profiler

# Profile memory usage
python -m memory_profiler -m server.main --config config/server-dev.conf
```

## Documentation Development

### Building Documentation

```bash
# Install documentation dependencies
pip install sphinx sphinx-rtd-theme

# Build documentation
cd docs
make html

# Serve documentation locally
python -m http.server 8000 -d _build/html
```

### Writing Documentation

- Use clear, concise language
- Include code examples
- Add screenshots for UI features
- Update API documentation for changes
- Test all examples and commands

## Release Process

### Version Management

```bash
# Update version in setup.py
# Update CHANGELOG.md
# Create version tag
git tag -a v1.0.0 -m "Release version 1.0.0"
git push origin v1.0.0
```

### Testing Release

```bash
# Build distribution packages
python setup.py sdist bdist_wheel

# Test installation
pip install dist/pacman-sync-utility-1.0.0.tar.gz

# Test Docker build
docker build -t pacman-sync-server:1.0.0 .
```

## Getting Help

### Development Resources

- **Project Documentation**: Check `docs/` directory
- **Code Examples**: Review `examples/` directory
- **Test Cases**: Study existing tests for patterns
- **Issue Tracker**: GitHub issues for bugs and features

### Community Support

- **GitHub Discussions**: For development questions
- **Code Reviews**: Request reviews from maintainers
- **Development Chat**: Join development discussions

### Debugging Resources

```bash
# Generate development diagnostic report
python -m server.main --diagnose --dev --report dev-diagnostic.txt

# Check development environment
python -m server.main --check-dev-env

# Validate development setup
python scripts/validate-dev-setup.py
```

## Next Steps

After setting up your development environment:

1. Read the [Architecture Overview](architecture.md) to understand the system design
2. Review [Contributing Guidelines](contributing.md) for code standards
3. Check [API Documentation](api-documentation.md) for integration details
4. Explore existing tests to understand testing patterns
5. Start with small bug fixes or documentation improvements