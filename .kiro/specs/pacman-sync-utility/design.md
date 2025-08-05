# Design Document

## Overview

The Pacman Sync Utility is designed as a distributed client-server architecture that enables synchronized package management across multiple Arch-based systems. The system consists of three main components:

1. **Central Server**: A web-based management interface with REST API for coordinating package synchronization
2. **Desktop Client**: A Qt-based application providing system tray integration and user interaction
3. **Database Layer**: Flexible storage supporting both PostgreSQL and embedded database options

The architecture emphasizes scalability, reliability, and user experience while handling the complexities of package repository compatibility across different Arch distributions.

## Architecture

### System Architecture

```mermaid
graph TB
    subgraph "Central Server"
        WEB[Web UI]
        API[REST API]
        CORE[Core Service]
        DB[(Database)]
    end
    
    subgraph "Client Machines"
        CLIENT1[Desktop Client 1]
        CLIENT2[Desktop Client 2]
        CLIENTN[Desktop Client N]
    end
    
    subgraph "External Integrations"
        WAYBAR[WayBar]
        TRAY[System Tray]
        PACMAN[Pacman]
    end
    
    CLIENT1 <--> API
    CLIENT2 <--> API
    CLIENTN <--> API
    
    WEB --> CORE
    API --> CORE
    CORE --> DB
    
    CLIENT1 --> TRAY
    CLIENT1 --> WAYBAR
    CLIENT1 --> PACMAN
    
    CLIENT2 --> TRAY
    CLIENT2 --> PACMAN
```

### Component Communication

- **HTTP/REST**: All client-server communication uses HTTP REST API
- **WebSocket**: Real-time status updates and notifications (optional enhancement)
- **D-Bus**: System tray integration using AppIndicator/KStatusNotifierItem protocols
- **Command Line**: Direct pacman integration and CLI argument processing

### Deployment Architecture

```mermaid
graph LR
    subgraph "Docker Container"
        SERVER[Central Server]
        INTERNAL_DB[(Internal DB)]
    end
    
    subgraph "External"
        POSTGRES[(PostgreSQL)]
        PROXY[Reverse Proxy]
        SSL[SSL Termination]
    end
    
    PROXY --> SSL
    SSL --> SERVER
    SERVER -.-> POSTGRES
    SERVER -.-> INTERNAL_DB
```

## Components and Interfaces

### Central Server Components

#### Web UI Module
- **Technology**: Modern web framework (React/Vue.js recommended)
- **Responsibilities**:
  - Package pool management interface
  - Endpoint grouping and configuration
  - Real-time status dashboard
  - Repository compatibility analysis display
- **API Integration**: Consumes REST API endpoints

#### REST API Module
- **Technology**: Python (FastAPI/Flask) or Go (Gin/Echo)
- **Endpoints**:
  ```
  GET    /api/pools                    # List all package pools
  POST   /api/pools                    # Create new pool
  GET    /api/pools/{id}               # Get pool details
  PUT    /api/pools/{id}               # Update pool
  DELETE /api/pools/{id}               # Delete pool
  
  GET    /api/endpoints                # List all endpoints
  POST   /api/endpoints                # Register new endpoint
  GET    /api/endpoints/{id}           # Get endpoint details
  PUT    /api/endpoints/{id}           # Update endpoint
  DELETE /api/endpoints/{id}           # Remove endpoint
  
  POST   /api/endpoints/{id}/sync      # Trigger sync operation
  POST   /api/endpoints/{id}/set-latest # Set as latest state
  POST   /api/endpoints/{id}/revert    # Revert to previous state
  
  GET    /api/repositories             # Get repository analysis
  POST   /api/repositories/analyze     # Trigger repository analysis
  ```

#### Core Service Module
- **Responsibilities**:
  - Package state management and synchronization logic
  - Repository compatibility analysis
  - Endpoint coordination and communication
  - Database operations and data persistence
- **Key Classes**:
  - `PackagePoolManager`: Manages pool operations and endpoint assignments
  - `SyncCoordinator`: Handles synchronization operations across endpoints
  - `RepositoryAnalyzer`: Analyzes package availability across repositories
  - `StateManager`: Manages package state snapshots and history

### Desktop Client Components

#### Qt Application Framework
- **Main Application**: `QApplication` with system tray integration
- **System Tray**: `QSystemTrayIcon` with AppIndicator/KStatusNotifierItem support
- **UI Windows**: Qt widgets for detailed views and configuration
- **Key Classes**:
  - `MainApplication`: Application lifecycle and tray management
  - `SyncStatusIndicator`: System tray icon and status management
  - `SyncActionHandler`: Handles user actions and API communication
  - `PackageStateDisplay`: Qt windows for detailed package information

#### Command Line Interface
- **Argument Parser**: Handles CLI arguments for automation integration
- **Operation Modes**:
  - GUI mode (default): Runs with system tray integration
  - CLI mode: Executes single operations and exits
  - WayBar mode: Outputs JSON status for WayBar consumption

#### API Client Module
- **HTTP Client**: Handles communication with central server
- **Authentication**: Token-based authentication for endpoint identification
- **Retry Logic**: Handles network failures and reconnection
- **State Synchronization**: Maintains local cache of sync status

### Database Schema

#### Core Tables

```sql
-- Package Pools
CREATE TABLE pools (
    id UUID PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Endpoints
CREATE TABLE endpoints (
    id UUID PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    hostname VARCHAR(255) NOT NULL,
    pool_id UUID REFERENCES pools(id),
    last_seen TIMESTAMP,
    sync_status VARCHAR(50), -- 'in_sync', 'ahead', 'behind', 'offline'
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Package States (snapshots)
CREATE TABLE package_states (
    id UUID PRIMARY KEY,
    pool_id UUID REFERENCES pools(id),
    endpoint_id UUID REFERENCES endpoints(id),
    state_data JSONB, -- Package list with versions
    is_target BOOLEAN DEFAULT FALSE, -- Is this the target state for the pool
    created_at TIMESTAMP DEFAULT NOW()
);

-- Repository Information
CREATE TABLE repositories (
    id UUID PRIMARY KEY,
    endpoint_id UUID REFERENCES endpoints(id),
    repo_name VARCHAR(255) NOT NULL,
    repo_url VARCHAR(500),
    packages JSONB, -- Available packages in this repo
    last_updated TIMESTAMP DEFAULT NOW()
);

-- Sync Operations Log
CREATE TABLE sync_operations (
    id UUID PRIMARY KEY,
    pool_id UUID REFERENCES pools(id),
    endpoint_id UUID REFERENCES endpoints(id),
    operation_type VARCHAR(50), -- 'sync', 'set_latest', 'revert'
    status VARCHAR(50), -- 'pending', 'in_progress', 'completed', 'failed'
    details JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP
);
```

## Data Models

### Package State Model
```python
@dataclass
class PackageState:
    package_name: str
    version: str
    repository: str
    installed_size: int
    dependencies: List[str]
    
@dataclass
class SystemState:
    endpoint_id: str
    timestamp: datetime
    packages: List[PackageState]
    pacman_version: str
    architecture: str
```

### Pool Configuration Model
```python
@dataclass
class PackagePool:
    id: str
    name: str
    description: str
    endpoints: List[str]  # endpoint IDs
    target_state_id: Optional[str]
    sync_policy: SyncPolicy
    
@dataclass
class SyncPolicy:
    auto_sync: bool
    exclude_packages: List[str]
    include_aur: bool
    conflict_resolution: str  # 'manual', 'newest', 'oldest'
```

### Repository Analysis Model
```python
@dataclass
class RepositoryPackage:
    name: str
    version: str
    repository: str
    architecture: str
    
@dataclass
class CompatibilityAnalysis:
    pool_id: str
    common_packages: List[RepositoryPackage]
    excluded_packages: List[RepositoryPackage]
    conflicts: List[PackageConflict]
    last_analyzed: datetime
```

## Error Handling

### Client-Side Error Handling
- **Network Failures**: Implement exponential backoff retry logic
- **Authentication Errors**: Handle token refresh and re-authentication
- **Pacman Errors**: Parse pacman output and provide user-friendly error messages
- **Qt Exceptions**: Graceful degradation when system tray is unavailable

### Server-Side Error Handling
- **Database Errors**: Connection pooling and automatic reconnection
- **API Errors**: Structured error responses with appropriate HTTP status codes
- **Validation Errors**: Input validation with detailed error messages
- **Concurrency Errors**: Handle simultaneous operations on the same pool/endpoint

### Error Response Format
```json
{
    "error": {
        "code": "SYNC_CONFLICT",
        "message": "Cannot sync: package conflicts detected",
        "details": {
            "conflicting_packages": ["package1", "package2"],
            "suggested_action": "resolve_manually"
        },
        "timestamp": "2025-01-15T10:30:00Z"
    }
}
```

## Testing Strategy

### Unit Testing
- **Server Components**: Test API endpoints, core service logic, and database operations
- **Client Components**: Test Qt widgets, API client, and command-line interface
- **Data Models**: Validate serialization, validation, and business logic

### Integration Testing
- **API Integration**: Test complete client-server communication flows
- **Database Integration**: Test with both PostgreSQL and internal database
- **Pacman Integration**: Test package operations in controlled environments

### End-to-End Testing
- **Sync Workflows**: Test complete synchronization scenarios across multiple endpoints
- **UI Testing**: Automated testing of Qt interface and system tray interactions
- **Docker Testing**: Validate containerized deployment and scaling

### Testing Infrastructure
- **Test Databases**: Separate test database instances for isolation
- **Mock Services**: Mock pacman operations for consistent testing
- **CI/CD Pipeline**: Automated testing on multiple Arch-based distributions

### Performance Testing
- **Load Testing**: Test server performance with multiple concurrent endpoints
- **Database Performance**: Optimize queries for large package datasets
- **Memory Usage**: Monitor client memory usage during long-running operations

## Security Considerations

### Authentication and Authorization
- **API Authentication**: JWT tokens for endpoint authentication
- **Role-Based Access**: Different permissions for read-only vs. admin users
- **Token Management**: Secure token storage and automatic refresh

### Network Security
- **HTTP Security**: Designed for reverse proxy with SSL termination
- **Input Validation**: Sanitize all user inputs and API parameters
- **Rate Limiting**: Prevent abuse of API endpoints

### System Security
- **Privilege Separation**: Run with minimal required permissions
- **Package Verification**: Verify package integrity before installation
- **Audit Logging**: Log all package operations and administrative actions

## Deployment Configuration

### Docker Configuration
```dockerfile
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Application setup
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# Configuration
ENV DATABASE_TYPE=internal
ENV HTTP_PORT=8080
ENV LOG_LEVEL=INFO

EXPOSE 8080
CMD ["python", "server.py"]
```

### Environment Variables
```bash
# Database Configuration
DATABASE_TYPE=postgresql  # or 'internal'
DATABASE_URL=postgresql://user:pass@host:5432/dbname

# Server Configuration
HTTP_PORT=8080
HTTP_HOST=0.0.0.0
LOG_LEVEL=INFO

# Security
JWT_SECRET_KEY=your-secret-key
API_RATE_LIMIT=100

# Features
ENABLE_REPOSITORY_ANALYSIS=true
AUTO_CLEANUP_OLD_STATES=true
```

### Client Configuration
```ini
[server]
url = http://your-server:8080
api_key = your-api-key

[client]
endpoint_name = my-desktop
pool_id = default-pool
auto_sync = false

[ui]
show_notifications = true
minimize_to_tray = true
update_interval = 300
```