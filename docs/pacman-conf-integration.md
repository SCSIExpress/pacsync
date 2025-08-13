# Pacman-conf Integration

The Pacman Sync Utility client now uses `pacman-conf` to retrieve repository configuration and mirror information. This provides several advantages over manual parsing of `/etc/pacman.conf`.

## Benefits of pacman-conf Integration

### 1. No sudo Required
- `pacman-conf` runs without elevated privileges
- Safer and more secure than parsing system files directly
- Works in restricted environments

### 2. Accurate Mirror Information
- Gets the actual mirror URLs that pacman uses
- Handles Include directives and mirrorlist files automatically
- Provides all configured mirrors, not just the first one

### 3. Complete Repository Data
- Extracts all repository configuration options
- Handles complex configurations with multiple mirrors per repository
- Provides architecture-specific information

## Implementation Details

### Repository Information Retrieval

The client now provides two methods for getting repository information:

#### Lightweight Repository Info
```python
# Get repository info with mirrors for server analysis
repo_info = pacman.get_repository_info_for_server(endpoint_id)
```

This method provides:
- Repository names
- All mirror URLs
- Primary mirror URL
- Architecture information
- No package lists (faster)

#### Full Repository Info
```python
# Get complete repository information including packages
repositories = pacman.get_full_repository_information(endpoint_id)
```

This method provides:
- All repository metadata
- Complete package lists
- Mirror information
- More expensive operation

### Server Integration

The server has been updated to support mirror information with the following changes:

### Database Schema Updates
- Added `mirrors` column to `repositories` table
- Supports both PostgreSQL (JSONB) and SQLite (TEXT) storage
- Automatic migration for existing databases

### API Endpoints
- **New lightweight endpoint**: `POST /api/endpoints/{id}/repository-info`
- **Enhanced repository data**: All endpoints now return mirror information
- **Backward compatibility**: Old repository submission format still supported

### Server Capabilities
The server can now use the mirror information to:

1. **Analyze Package Overlap**: Compare packages across different mirrors of the same repository
2. **Repository Compatibility**: Determine which repositories are compatible across endpoints
3. **Mirror Selection**: Choose optimal mirrors for package synchronization
4. **Redundancy Planning**: Use multiple mirrors for reliability
5. **Geographic Optimization**: Select mirrors based on location and performance

## Configuration Structure

### Repository Info Format
```python
{
    "repo_name": {
        "name": "core",
        "mirrors": [
            "http://mirror1.example.com/core/os/x86_64",
            "http://mirror2.example.com/core/os/x86_64",
            "https://mirror3.example.com/core/os/x86_64"
        ],
        "primary_url": "http://mirror1.example.com/core/os/x86_64",
        "architecture": "x86_64",
        "endpoint_id": "endpoint-123"
    }
}
```

### Repository Model Updates
The `Repository` model now includes:
- `mirrors: List[str]` - Additional mirror URLs
- `get_all_urls()` method - Returns all available URLs

## Fallback Behavior

If `pacman-conf` is not available or fails, the client automatically falls back to:

1. **Manual pacman.conf parsing** - Reads `/etc/pacman.conf` directly
2. **Mirrorlist parsing** - Attempts to parse Include directives
3. **Default repositories** - Uses common Arch Linux repositories as last resort

## Testing

Run the integration test to verify functionality:

```bash
python3 tests/test_pacman_conf_integration.py
```

The test verifies:
- `pacman-conf` availability
- Repository configuration parsing
- Mirror extraction
- Server info formatting
- Direct command execution

## Usage Examples

### Client Integration
```python
from client.pacman_integration_example import PacmanSyncIntegration

integration = PacmanSyncIntegration(config)

# Get lightweight repo info for server
repo_info = integration.get_repository_information("my-endpoint")

# Get full repo info with packages (expensive)
full_repos = integration.get_full_repository_information("my-endpoint")
```

### Server Analysis
The server can use the mirror information to:

```python
# Analyze repository compatibility
for repo_name, info in repo_info.items():
    primary_url = info['primary_url']
    all_mirrors = info['mirrors']
    
    # Check package overlap across mirrors
    # Select optimal mirrors for sync operations
    # Plan redundancy strategies
```

### API Usage

#### Lightweight Repository Submission
```python
# Client submits lightweight repository info
repo_info = pacman.get_repository_info_for_server(endpoint_id)
success = await api_client.submit_repository_info_lightweight(endpoint_id, repo_info)
```

#### Server Response Format
```json
{
    "repositories": [
        {
            "id": "repo-uuid",
            "repo_name": "core",
            "repo_url": "http://primary-mirror.com/core/os/x86_64",
            "mirrors": [
                "http://mirror1.com/core/os/x86_64",
                "http://mirror2.com/core/os/x86_64",
                "https://secure-mirror.com/core/os/x86_64"
            ],
            "packages": [...],
            "last_updated": "2024-12-08T10:30:00Z"
        }
    ]
}
```

## Performance Considerations

- **Lightweight method**: Fast, suitable for frequent updates
- **Full method**: Expensive, use sparingly or cache results
- **Mirror count**: Some repositories have 50+ mirrors
- **Network impact**: Server can choose geographically optimal mirrors

## Security Benefits

- No file system access required
- Uses official pacman utilities
- Respects pacman configuration exactly
- No parsing of system configuration files
- Works in sandboxed environments