# Contributing Guide

Thank you for your interest in contributing to the Pacman Sync Utility! This guide will help you get started with contributing to the project.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Process](#development-process)
- [Coding Standards](#coding-standards)
- [Testing Guidelines](#testing-guidelines)
- [Documentation Standards](#documentation-standards)
- [Submitting Changes](#submitting-changes)
- [Review Process](#review-process)
- [Community](#community)

## Code of Conduct

### Our Pledge

We pledge to make participation in our project a harassment-free experience for everyone, regardless of age, body size, disability, ethnicity, gender identity and expression, level of experience, nationality, personal appearance, race, religion, or sexual identity and orientation.

### Our Standards

Examples of behavior that contributes to creating a positive environment include:

- Using welcoming and inclusive language
- Being respectful of differing viewpoints and experiences
- Gracefully accepting constructive criticism
- Focusing on what is best for the community
- Showing empathy towards other community members

### Enforcement

Instances of abusive, harassing, or otherwise unacceptable behavior may be reported by contacting the project team. All complaints will be reviewed and investigated promptly and fairly.

## Getting Started

### Prerequisites

Before contributing, ensure you have:

1. **Development Environment**: Set up according to [Development Setup Guide](development-setup.md)
2. **Git Knowledge**: Basic understanding of Git workflows
3. **Python Experience**: Familiarity with Python 3.8+ development
4. **Arch Linux**: Access to Arch Linux system for client testing

### First Contribution

For your first contribution, consider:

1. **Good First Issues**: Look for issues labeled `good-first-issue`
2. **Documentation**: Improve documentation or fix typos
3. **Tests**: Add missing test cases
4. **Bug Fixes**: Fix small, well-defined bugs

### Setting Up Your Fork

```bash
# Fork the repository on GitHub
# Clone your fork
git clone https://github.com/your-username/pacman-sync-utility.git
cd pacman-sync-utility

# Add upstream remote
git remote add upstream https://github.com/original-org/pacman-sync-utility.git

# Create development branch
git checkout -b feature/your-feature-name
```

## Development Process

### Workflow Overview

1. **Issue Creation**: Create or find an issue to work on
2. **Branch Creation**: Create a feature branch from main
3. **Development**: Implement changes with tests
4. **Testing**: Run all tests and ensure they pass
5. **Documentation**: Update relevant documentation
6. **Pull Request**: Submit PR for review
7. **Review**: Address feedback and iterate
8. **Merge**: Maintainer merges approved PR

### Branch Naming Convention

Use descriptive branch names with prefixes:

```bash
# Feature branches
feature/add-pool-templates
feature/improve-sync-performance

# Bug fix branches
fix/system-tray-icon-missing
fix/database-connection-timeout

# Documentation branches
docs/update-api-documentation
docs/add-troubleshooting-guide

# Refactoring branches
refactor/simplify-auth-logic
refactor/extract-common-utilities
```

### Commit Message Format

Follow the [Conventional Commits](https://www.conventionalcommits.org/) specification:

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

#### Types

- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

#### Examples

```bash
feat(server): add pool template functionality

Add support for creating pools from predefined templates.
Templates include common configurations for different use cases.

Closes #123

fix(client): resolve system tray icon not appearing on KDE

The system tray icon was not visible on KDE Plasma due to missing
AppIndicator support. Added fallback to QSystemTrayIcon.

Fixes #456

docs(api): update endpoint documentation

- Add examples for all endpoints
- Document error responses
- Update authentication section

test(integration): add multi-endpoint sync tests

Add comprehensive tests for synchronization across multiple
endpoints in the same pool.
```

## Coding Standards

### Python Code Style

We follow [PEP 8](https://pep8.org/) with some modifications:

#### Formatting

- **Line Length**: 88 characters (Black default)
- **Indentation**: 4 spaces
- **Quotes**: Double quotes for strings
- **Imports**: Organized with isort

#### Code Quality Tools

```bash
# Format code
black .

# Sort imports
isort .

# Check style
flake8 .

# Type checking
mypy server/ client/ shared/

# Run all checks
pre-commit run --all-files
```

#### Configuration Files

**.flake8**
```ini
[flake8]
max-line-length = 88
extend-ignore = E203, W503
exclude = 
    .git,
    __pycache__,
    venv,
    .venv,
    build,
    dist
```

**pyproject.toml**
```toml
[tool.black]
line-length = 88
target-version = ['py38']
include = '\.pyi?$'

[tool.isort]
profile = "black"
multi_line_output = 3
line_length = 88

[tool.mypy]
python_version = "3.8"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
```

### Code Organization

#### Project Structure

```
pacman-sync-utility/
├── server/                 # Server application
│   ├── api/               # REST API endpoints
│   ├── core/              # Business logic
│   ├── database/          # Database layer
│   └── web/               # Web UI
├── client/                # Desktop client
│   ├── qt/                # Qt GUI components
│   ├── auth/              # Authentication
│   └── ...
├── shared/                # Shared utilities
├── tests/                 # Test suite
├── docs/                  # Documentation
└── scripts/               # Utility scripts
```

#### Module Organization

```python
# server/core/pool_manager.py
"""Pool management business logic."""

from typing import List, Optional
from uuid import UUID

from shared.models import Pool, PoolSettings
from server.database.orm import PoolRepository


class PoolManager:
    """Manages package pools and their configuration."""
    
    def __init__(self, repository: PoolRepository):
        self._repository = repository
    
    def create_pool(self, name: str, description: str, 
                   settings: Optional[PoolSettings] = None) -> Pool:
        """Create a new package pool.
        
        Args:
            name: Unique pool name
            description: Pool description
            settings: Optional pool settings
            
        Returns:
            Created pool instance
            
        Raises:
            ValueError: If pool name already exists
        """
        # Implementation here
        pass
```

### Error Handling

#### Exception Hierarchy

```python
# shared/exceptions.py
"""Custom exception hierarchy."""

class PacmanSyncError(Exception):
    """Base exception for all Pacman Sync errors."""
    pass

class ConfigurationError(PacmanSyncError):
    """Configuration-related errors."""
    pass

class DatabaseError(PacmanSyncError):
    """Database operation errors."""
    pass

class SyncError(PacmanSyncError):
    """Synchronization operation errors."""
    pass

class AuthenticationError(PacmanSyncError):
    """Authentication and authorization errors."""
    pass
```

#### Error Handling Patterns

```python
# Good: Specific exception handling
try:
    pool = pool_manager.create_pool(name, description)
except ValueError as e:
    logger.error(f"Invalid pool configuration: {e}")
    return {"error": "Invalid pool name", "details": str(e)}
except DatabaseError as e:
    logger.error(f"Database error creating pool: {e}")
    return {"error": "Database operation failed"}

# Good: Context managers for resource management
from contextlib import contextmanager

@contextmanager
def database_transaction():
    """Database transaction context manager."""
    transaction = db.begin()
    try:
        yield transaction
        transaction.commit()
    except Exception:
        transaction.rollback()
        raise
    finally:
        transaction.close()
```

### Logging Standards

```python
import logging
from typing import Any, Dict

# Configure logging
logger = logging.getLogger(__name__)

class PoolManager:
    def create_pool(self, name: str, description: str) -> Pool:
        """Create a new package pool."""
        logger.info(f"Creating pool: {name}")
        
        try:
            # Validate input
            if not name or len(name) < 3:
                raise ValueError("Pool name must be at least 3 characters")
            
            # Create pool
            pool = self._repository.create(name, description)
            logger.info(f"Pool created successfully: {pool.id}")
            
            # Log structured data
            logger.info(
                "Pool creation completed",
                extra={
                    "pool_id": str(pool.id),
                    "pool_name": name,
                    "operation": "create_pool"
                }
            )
            
            return pool
            
        except Exception as e:
            logger.error(
                f"Failed to create pool '{name}': {e}",
                extra={
                    "pool_name": name,
                    "error_type": type(e).__name__,
                    "operation": "create_pool"
                }
            )
            raise
```

## Testing Guidelines

### Testing Philosophy

- **Test-Driven Development**: Write tests before implementation when possible
- **Comprehensive Coverage**: Aim for >90% code coverage
- **Fast Feedback**: Unit tests should run quickly
- **Realistic Integration**: Integration tests should use real dependencies
- **End-to-End Validation**: E2E tests should cover critical user journeys

### Test Organization

```
tests/
├── unit/                  # Unit tests
│   ├── server/
│   ├── client/
│   └── shared/
├── integration/           # Integration tests
│   ├── api/
│   ├── database/
│   └── client_server/
├── e2e/                   # End-to-end tests
├── fixtures/              # Test data and fixtures
└── conftest.py           # Pytest configuration
```

### Unit Testing

```python
# tests/unit/server/test_pool_manager.py
import pytest
from unittest.mock import Mock, patch

from server.core.pool_manager import PoolManager
from shared.models import Pool
from shared.exceptions import DatabaseError


class TestPoolManager:
    """Test cases for PoolManager."""
    
    @pytest.fixture
    def mock_repository(self):
        """Mock repository for testing."""
        return Mock()
    
    @pytest.fixture
    def pool_manager(self, mock_repository):
        """PoolManager instance with mocked dependencies."""
        return PoolManager(mock_repository)
    
    def test_create_pool_success(self, pool_manager, mock_repository):
        """Test successful pool creation."""
        # Arrange
        expected_pool = Pool(id="123", name="test-pool", description="Test")
        mock_repository.create.return_value = expected_pool
        
        # Act
        result = pool_manager.create_pool("test-pool", "Test description")
        
        # Assert
        assert result == expected_pool
        mock_repository.create.assert_called_once_with("test-pool", "Test description")
    
    def test_create_pool_invalid_name(self, pool_manager):
        """Test pool creation with invalid name."""
        with pytest.raises(ValueError, match="Pool name must be at least 3 characters"):
            pool_manager.create_pool("ab", "Description")
    
    def test_create_pool_database_error(self, pool_manager, mock_repository):
        """Test pool creation with database error."""
        # Arrange
        mock_repository.create.side_effect = DatabaseError("Connection failed")
        
        # Act & Assert
        with pytest.raises(DatabaseError):
            pool_manager.create_pool("test-pool", "Description")
```

### Integration Testing

```python
# tests/integration/test_api_endpoints.py
import pytest
from fastapi.testclient import TestClient

from server.main import app
from server.database.connection import get_test_db


@pytest.fixture
def client():
    """Test client with test database."""
    app.dependency_overrides[get_db] = get_test_db
    with TestClient(app) as client:
        yield client


class TestPoolAPI:
    """Integration tests for pool API endpoints."""
    
    def test_create_pool_endpoint(self, client):
        """Test pool creation via API."""
        # Arrange
        pool_data = {
            "name": "integration-test-pool",
            "description": "Integration test pool",
            "settings": {"auto_sync": False}
        }
        
        # Act
        response = client.post("/api/v1/pools", json=pool_data)
        
        # Assert
        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True
        assert data["data"]["name"] == pool_data["name"]
    
    def test_get_pools_endpoint(self, client):
        """Test retrieving pools via API."""
        # Act
        response = client.get("/api/v1/pools")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "pools" in data["data"]
```

### End-to-End Testing

```python
# tests/e2e/test_sync_workflow.py
import pytest
import subprocess
import time
from pathlib import Path


class TestSyncWorkflow:
    """End-to-end tests for sync workflow."""
    
    @pytest.fixture(scope="class")
    def server_process(self):
        """Start server for E2E tests."""
        process = subprocess.Popen([
            "python", "-m", "server.main",
            "--config", "config/test-server.conf"
        ])
        time.sleep(5)  # Wait for server to start
        yield process
        process.terminate()
        process.wait()
    
    def test_complete_sync_workflow(self, server_process):
        """Test complete sync workflow from client to server."""
        # Create pool via API
        result = subprocess.run([
            "curl", "-X", "POST",
            "http://localhost:8080/api/v1/pools",
            "-H", "Content-Type: application/json",
            "-d", '{"name": "e2e-test-pool", "description": "E2E test"}'
        ], capture_output=True, text=True)
        
        assert "success" in result.stdout
        
        # Register client endpoint
        result = subprocess.run([
            "python", "-m", "client.main",
            "--config", "config/test-client.conf",
            "--register"
        ], capture_output=True, text=True)
        
        assert result.returncode == 0
        
        # Perform sync operation
        result = subprocess.run([
            "python", "-m", "client.main",
            "--config", "config/test-client.conf",
            "--sync", "--dry-run"
        ], capture_output=True, text=True)
        
        assert result.returncode == 0
        assert "sync completed" in result.stdout.lower()
```

### Test Data and Fixtures

```python
# tests/fixtures/pool_fixtures.py
import pytest
from shared.models import Pool, PoolSettings


@pytest.fixture
def sample_pool():
    """Sample pool for testing."""
    return Pool(
        id="test-pool-123",
        name="test-pool",
        description="Test pool for unit tests",
        settings=PoolSettings(
            auto_sync=False,
            conflict_resolution="manual",
            excluded_packages=["linux", "nvidia"]
        )
    )

@pytest.fixture
def pool_data():
    """Sample pool data for API tests."""
    return {
        "name": "api-test-pool",
        "description": "Pool for API testing",
        "settings": {
            "auto_sync": True,
            "conflict_resolution": "newest",
            "max_history": 25
        }
    }
```

## Documentation Standards

### Documentation Types

1. **Code Documentation**: Docstrings and inline comments
2. **API Documentation**: OpenAPI/Swagger specifications
3. **User Documentation**: Installation, configuration, usage guides
4. **Developer Documentation**: Architecture, contributing guidelines

### Docstring Format

Use Google-style docstrings:

```python
def create_pool(self, name: str, description: str, 
               settings: Optional[PoolSettings] = None) -> Pool:
    """Create a new package pool.
    
    Creates a new pool with the specified configuration. The pool name
    must be unique across the system.
    
    Args:
        name: Unique identifier for the pool. Must be 3-50 characters.
        description: Human-readable description of the pool's purpose.
        settings: Optional pool configuration. Uses defaults if not provided.
        
    Returns:
        The newly created pool instance with generated ID.
        
    Raises:
        ValueError: If the pool name is invalid or already exists.
        DatabaseError: If the database operation fails.
        
    Example:
        >>> manager = PoolManager(repository)
        >>> pool = manager.create_pool("dev-pool", "Development workstations")
        >>> print(pool.id)
        'pool-abc123'
    """
```

### API Documentation

Use OpenAPI annotations:

```python
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()

class PoolCreateRequest(BaseModel):
    """Request model for pool creation."""
    name: str = Field(..., min_length=3, max_length=50, description="Pool name")
    description: str = Field(..., description="Pool description")
    settings: Optional[PoolSettings] = Field(None, description="Pool settings")

@router.post("/pools", response_model=PoolResponse, status_code=201)
async def create_pool(request: PoolCreateRequest):
    """Create a new package pool.
    
    Creates a new pool with the specified configuration. Pool names must be
    unique across the system.
    
    - **name**: Unique pool identifier (3-50 characters)
    - **description**: Human-readable description
    - **settings**: Optional configuration (uses defaults if omitted)
    
    Returns the created pool with generated ID and timestamps.
    """
    try:
        pool = pool_manager.create_pool(
            request.name, 
            request.description, 
            request.settings
        )
        return PoolResponse.from_pool(pool)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
```

### User Documentation

Follow these guidelines for user-facing documentation:

1. **Clear Structure**: Use headings, lists, and code blocks
2. **Step-by-Step Instructions**: Break complex tasks into steps
3. **Examples**: Provide working examples for all procedures
4. **Troubleshooting**: Include common issues and solutions
5. **Cross-References**: Link to related documentation

## Submitting Changes

### Pre-Submission Checklist

Before submitting a pull request:

- [ ] Code follows style guidelines
- [ ] All tests pass locally
- [ ] New features have tests
- [ ] Documentation is updated
- [ ] Commit messages follow convention
- [ ] Branch is up to date with main
- [ ] No merge conflicts exist

### Pull Request Process

1. **Create Pull Request**
   ```bash
   # Push your branch
   git push origin feature/your-feature-name
   
   # Create PR on GitHub with descriptive title and description
   ```

2. **PR Description Template**
   ```markdown
   ## Description
   Brief description of changes and motivation.
   
   ## Type of Change
   - [ ] Bug fix (non-breaking change which fixes an issue)
   - [ ] New feature (non-breaking change which adds functionality)
   - [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
   - [ ] Documentation update
   
   ## Testing
   - [ ] Unit tests pass
   - [ ] Integration tests pass
   - [ ] Manual testing completed
   
   ## Checklist
   - [ ] Code follows style guidelines
   - [ ] Self-review completed
   - [ ] Documentation updated
   - [ ] No new warnings introduced
   
   ## Related Issues
   Closes #123
   Related to #456
   ```

3. **Automated Checks**
   - CI/CD pipeline runs automatically
   - Code quality checks must pass
   - Test coverage must be maintained
   - Security scans must pass

### Pull Request Guidelines

#### Title Format
```
<type>(<scope>): <description>

Examples:
feat(server): add pool template functionality
fix(client): resolve system tray icon issue
docs(api): update authentication examples
```

#### Description Requirements
- Clear explanation of changes
- Motivation and context
- Testing approach
- Breaking changes (if any)
- Screenshots (for UI changes)

## Review Process

### Review Criteria

Reviewers will evaluate:

1. **Functionality**: Does the code work as intended?
2. **Code Quality**: Is the code clean, readable, and maintainable?
3. **Testing**: Are there adequate tests with good coverage?
4. **Documentation**: Is documentation updated and accurate?
5. **Performance**: Are there any performance implications?
6. **Security**: Are there any security concerns?

### Review Timeline

- **Initial Review**: Within 2-3 business days
- **Follow-up Reviews**: Within 1-2 business days
- **Merge Decision**: After all feedback is addressed

### Addressing Feedback

1. **Respond Promptly**: Address feedback within a few days
2. **Ask Questions**: Clarify unclear feedback
3. **Make Changes**: Implement requested changes
4. **Update Tests**: Ensure tests still pass
5. **Request Re-review**: Ask for re-review when ready

### Review Etiquette

#### For Authors
- Be open to feedback
- Explain design decisions
- Keep PRs focused and small
- Respond to all comments

#### For Reviewers
- Be constructive and specific
- Explain the "why" behind suggestions
- Acknowledge good practices
- Be timely with reviews

## Community

### Communication Channels

- **GitHub Issues**: Bug reports and feature requests
- **GitHub Discussions**: General questions and ideas
- **Pull Requests**: Code review and collaboration
- **Documentation**: In-code and repository documentation

### Getting Help

1. **Search Existing Issues**: Check if your question has been asked
2. **Read Documentation**: Review relevant documentation first
3. **Create Detailed Issues**: Provide context and examples
4. **Be Patient**: Maintainers are volunteers with limited time

### Recognition

Contributors are recognized through:

- **Contributors File**: Listed in CONTRIBUTORS.md
- **Release Notes**: Mentioned in release announcements
- **GitHub Recognition**: Contributor badges and statistics

### Becoming a Maintainer

Regular contributors may be invited to become maintainers based on:

- **Consistent Contributions**: Regular, high-quality contributions
- **Community Involvement**: Helping other contributors
- **Technical Expertise**: Deep understanding of the codebase
- **Reliability**: Dependable and responsive participation

## Resources

### Development Resources

- [Development Setup Guide](development-setup.md)
- [Architecture Overview](architecture.md)
- [API Documentation](api-documentation.md)
- [Database Schema](database-schema.md)

### External Resources

- [Python PEP 8 Style Guide](https://pep8.org/)
- [Conventional Commits](https://www.conventionalcommits.org/)
- [Semantic Versioning](https://semver.org/)
- [Keep a Changelog](https://keepachangelog.com/)

### Tools and Libraries

- **Code Formatting**: Black, isort
- **Linting**: flake8, pylint
- **Type Checking**: mypy
- **Testing**: pytest, coverage
- **Documentation**: Sphinx, MkDocs

## Questions?

If you have questions about contributing:

1. Check the [FAQ section](#faq) below
2. Search existing GitHub issues and discussions
3. Create a new discussion with the "question" label
4. Reach out to maintainers through GitHub

## FAQ

### Q: How do I set up the development environment?
A: Follow the [Development Setup Guide](development-setup.md) for detailed instructions.

### Q: What should I work on as a first contribution?
A: Look for issues labeled `good-first-issue` or `help-wanted`. Documentation improvements are also great first contributions.

### Q: How do I run the tests?
A: Use `pytest` to run all tests, or `pytest tests/unit/` for just unit tests. See the testing section for more details.

### Q: My PR is failing CI checks. What should I do?
A: Check the CI logs for specific errors. Common issues are code style violations or failing tests. Run the checks locally first.

### Q: How long does it take for PRs to be reviewed?
A: Initial reviews typically happen within 2-3 business days. Complex changes may take longer.

### Q: Can I work on multiple issues at once?
A: It's better to focus on one issue at a time to ensure quality and avoid conflicts.

Thank you for contributing to the Pacman Sync Utility! Your contributions help make package management better for the Arch Linux community.