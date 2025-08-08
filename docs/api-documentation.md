# API Documentation

This document provides comprehensive documentation for the Pacman Sync Utility REST API.

## Overview

The Pacman Sync Utility provides a RESTful API for managing package pools, endpoints, and synchronization operations. The API is designed for:

- **Web UI Integration**: Powers the web management interface
- **Client Communication**: Enables desktop client functionality
- **Third-party Integration**: Allows external tools and automation
- **Monitoring Systems**: Provides metrics and health information

## Base URL and Versioning

```
Base URL: http://your-server:8080/api/v1
```

All API endpoints are prefixed with `/api/v1` for versioning. Future API versions will use different prefixes (e.g., `/api/v2`).

## Authentication

### API Key Authentication

Most endpoints require API key authentication using the `Authorization` header:

```http
Authorization: Bearer your-api-key-here
```

### Generating API Keys

API keys are generated server-side and associated with specific endpoints:

```bash
# Generate API key for an endpoint
curl -X POST http://server:8080/api/v1/auth/generate-key \
  -H "Content-Type: application/json" \
  -d '{"endpoint_name": "my-desktop", "description": "Desktop client key"}'
```

### Public Endpoints

Some endpoints are publicly accessible:
- Health checks (`/health/*`)
- API documentation (`/docs`)
- Server information (`/info`)

## Response Format

### Standard Response Structure

All API responses follow a consistent structure:

```json
{
    "success": true,
    "data": {
        // Response data here
    },
    "message": "Operation completed successfully",
    "timestamp": "2024-01-15T10:30:00Z"
}
```

### Error Response Structure

Error responses include detailed error information:

```json
{
    "success": false,
    "error": {
        "code": "VALIDATION_ERROR",
        "message": "Invalid pool configuration",
        "details": {
            "field": "name",
            "reason": "Pool name already exists"
        }
    },
    "timestamp": "2024-01-15T10:30:00Z"
}
```

### HTTP Status Codes

- `200 OK`: Successful operation
- `201 Created`: Resource created successfully
- `400 Bad Request`: Invalid request data
- `401 Unauthorized`: Authentication required
- `403 Forbidden`: Insufficient permissions
- `404 Not Found`: Resource not found
- `409 Conflict`: Resource conflict (e.g., duplicate name)
- `422 Unprocessable Entity`: Validation error
- `500 Internal Server Error`: Server error

## Pool Management API

### List Pools

Get all package pools with their basic information.

```http
GET /api/v1/pools
```

**Response:**
```json
{
    "success": true,
    "data": {
        "pools": [
            {
                "id": "pool-123",
                "name": "development-pool",
                "description": "Development workstations",
                "endpoint_count": 5,
                "created_at": "2024-01-10T09:00:00Z",
                "updated_at": "2024-01-15T10:30:00Z"
            }
        ],
        "total": 1
    }
}
```

### Get Pool Details

Retrieve detailed information about a specific pool.

```http
GET /api/v1/pools/{pool_id}
```

**Response:**
```json
{
    "success": true,
    "data": {
        "id": "pool-123",
        "name": "development-pool",
        "description": "Development workstations",
        "settings": {
            "auto_sync": false,
            "conflict_resolution": "manual",
            "excluded_packages": ["linux", "nvidia"],
            "max_history": 50
        },
        "endpoints": [
            {
                "id": "endpoint-456",
                "name": "workstation-01",
                "status": "in_sync",
                "last_seen": "2024-01-15T10:25:00Z"
            }
        ],
        "target_state": {
            "id": "state-789",
            "created_at": "2024-01-15T08:00:00Z",
            "created_by": "workstation-02"
        },
        "statistics": {
            "total_packages": 1247,
            "sync_operations": 156,
            "last_sync": "2024-01-15T10:00:00Z"
        }
    }
}
```

### Create Pool

Create a new package pool.

```http
POST /api/v1/pools
```

**Request Body:**
```json
{
    "name": "production-pool",
    "description": "Production servers",
    "settings": {
        "auto_sync": true,
        "conflict_resolution": "newest",
        "excluded_packages": ["linux", "nvidia-dkms"],
        "excluded_repos": ["testing"],
        "max_history": 100
    }
}
```

**Response:**
```json
{
    "success": true,
    "data": {
        "id": "pool-new-123",
        "name": "production-pool",
        "description": "Production servers",
        "created_at": "2024-01-15T10:30:00Z"
    },
    "message": "Pool created successfully"
}
```

### Update Pool

Update an existing pool's configuration.

```http
PUT /api/v1/pools/{pool_id}
```

**Request Body:**
```json
{
    "description": "Updated description",
    "settings": {
        "auto_sync": false,
        "max_history": 75
    }
}
```

### Delete Pool

Delete a pool and remove all endpoint assignments.

```http
DELETE /api/v1/pools/{pool_id}
```

**Query Parameters:**
- `force=true`: Force deletion even if endpoints are assigned

## Endpoint Management API

### List Endpoints

Get all registered endpoints.

```http
GET /api/v1/endpoints
```

**Query Parameters:**
- `pool_id`: Filter by pool ID
- `status`: Filter by status (online, offline, sync_pending, error)
- `limit`: Number of results per page (default: 50)
- `offset`: Pagination offset

**Response:**
```json
{
    "success": true,
    "data": {
        "endpoints": [
            {
                "id": "endpoint-456",
                "name": "workstation-01",
                "hostname": "arch-desktop",
                "pool_id": "pool-123",
                "status": "online",
                "sync_status": "in_sync",
                "last_seen": "2024-01-15T10:25:00Z",
                "system_info": {
                    "architecture": "x86_64",
                    "pacman_version": "6.0.2",
                    "kernel": "6.1.12-arch1-1"
                }
            }
        ],
        "total": 1,
        "pagination": {
            "limit": 50,
            "offset": 0,
            "has_more": false
        }
    }
}
```

### Get Endpoint Details

Retrieve detailed information about a specific endpoint.

```http
GET /api/v1/endpoints/{endpoint_id}
```

**Response:**
```json
{
    "success": true,
    "data": {
        "id": "endpoint-456",
        "name": "workstation-01",
        "hostname": "arch-desktop",
        "pool_id": "pool-123",
        "status": "online",
        "sync_status": "behind",
        "last_seen": "2024-01-15T10:25:00Z",
        "system_info": {
            "architecture": "x86_64",
            "pacman_version": "6.0.2",
            "kernel": "6.1.12-arch1-1",
            "total_packages": 1245,
            "available_repos": ["core", "extra", "community"]
        },
        "package_summary": {
            "total": 1245,
            "behind": 23,
            "ahead": 0,
            "excluded": 15
        },
        "recent_activity": [
            {
                "timestamp": "2024-01-15T09:30:00Z",
                "operation": "sync",
                "status": "completed",
                "packages_changed": 12
            }
        ]
    }
}
```

### Register Endpoint

Register a new endpoint with the server.

```http
POST /api/v1/endpoints
```

**Request Body:**
```json
{
    "name": "new-workstation",
    "hostname": "arch-laptop",
    "pool_id": "pool-123",
    "system_info": {
        "architecture": "x86_64",
        "pacman_version": "6.0.2",
        "kernel": "6.1.12-arch1-1"
    }
}
```

**Response:**
```json
{
    "success": true,
    "data": {
        "id": "endpoint-new-789",
        "name": "new-workstation",
        "api_key": "generated-api-key-here",
        "created_at": "2024-01-15T10:30:00Z"
    },
    "message": "Endpoint registered successfully"
}
```

### Update Endpoint

Update endpoint information and status.

```http
PUT /api/v1/endpoints/{endpoint_id}
```

**Request Body:**
```json
{
    "status": "online",
    "system_info": {
        "total_packages": 1250,
        "kernel": "6.1.13-arch1-1"
    },
    "package_summary": {
        "total": 1250,
        "behind": 18,
        "ahead": 0
    }
}
```

### Remove Endpoint

Unregister an endpoint from the server.

```http
DELETE /api/v1/endpoints/{endpoint_id}
```

## Synchronization API

### Trigger Sync Operation

Start a synchronization operation for an endpoint.

```http
POST /api/v1/endpoints/{endpoint_id}/sync
```

**Request Body:**
```json
{
    "type": "sync_to_latest",
    "options": {
        "dry_run": false,
        "force": false,
        "packages": ["firefox", "chromium"],  // Optional: specific packages
        "exclude": ["linux", "nvidia"]       // Optional: exclude packages
    }
}
```

**Response:**
```json
{
    "success": true,
    "data": {
        "operation_id": "op-sync-123",
        "status": "started",
        "estimated_duration": 300,
        "packages_to_change": 23
    },
    "message": "Sync operation started"
}
```

### Set as Latest

Mark an endpoint's current state as the pool's target state.

```http
POST /api/v1/endpoints/{endpoint_id}/set-latest
```

**Request Body:**
```json
{
    "message": "Updated development tools",
    "packages": {
        // Optional: specific package state to set
        "firefox": "110.0-1",
        "chromium": "109.0.5414.119-1"
    }
}
```

### Revert Operation

Revert an endpoint to a previous state.

```http
POST /api/v1/endpoints/{endpoint_id}/revert
```

**Request Body:**
```json
{
    "target_state_id": "state-456",  // Optional: specific state
    "options": {
        "dry_run": false,
        "confirm": true
    }
}
```

### Get Operation Status

Check the status of a synchronization operation.

```http
GET /api/v1/operations/{operation_id}
```

**Response:**
```json
{
    "success": true,
    "data": {
        "id": "op-sync-123",
        "type": "sync_to_latest",
        "status": "in_progress",
        "progress": {
            "percentage": 65,
            "current_step": "Installing packages",
            "packages_processed": 15,
            "packages_total": 23
        },
        "started_at": "2024-01-15T10:30:00Z",
        "estimated_completion": "2024-01-15T10:35:00Z",
        "logs": [
            {
                "timestamp": "2024-01-15T10:30:15Z",
                "level": "info",
                "message": "Starting package installation"
            }
        ]
    }
}
```

## Repository Analysis API

### Get Repository Analysis

Retrieve repository compatibility analysis for a pool.

```http
GET /api/v1/pools/{pool_id}/analysis
```

**Response:**
```json
{
    "success": true,
    "data": {
        "pool_id": "pool-123",
        "analysis_date": "2024-01-15T10:00:00Z",
        "repositories": [
            {
                "endpoint_id": "endpoint-456",
                "endpoint_name": "workstation-01",
                "repositories": ["core", "extra", "community"],
                "total_packages": 12450
            }
        ],
        "compatibility": {
            "compatible_packages": 12200,
            "incompatible_packages": 250,
            "conflicts": [
                {
                    "package": "example-package",
                    "versions": {
                        "endpoint-456": "1.0.0-1",
                        "endpoint-789": "1.0.1-1"
                    },
                    "resolution": "manual"
                }
            ]
        },
        "exclusions": {
            "automatic": ["linux", "nvidia-dkms"],
            "manual": ["custom-package"],
            "total": 3
        }
    }
}
```

### Trigger Repository Analysis

Force a new repository analysis for a pool.

```http
POST /api/v1/pools/{pool_id}/analyze
```

**Request Body:**
```json
{
    "force": true,
    "include_aur": false
}
```

## Package State API

### Get Package States

Retrieve package state history for a pool.

```http
GET /api/v1/pools/{pool_id}/states
```

**Query Parameters:**
- `limit`: Number of states to return (default: 10)
- `endpoint_id`: Filter by specific endpoint
- `is_target`: Filter target states only

**Response:**
```json
{
    "success": true,
    "data": {
        "states": [
            {
                "id": "state-789",
                "pool_id": "pool-123",
                "endpoint_id": "endpoint-456",
                "is_target": true,
                "created_at": "2024-01-15T08:00:00Z",
                "created_by": "workstation-02",
                "message": "Updated development tools",
                "package_count": 1247,
                "packages": {
                    "firefox": "110.0-1",
                    "chromium": "109.0.5414.119-1",
                    // ... more packages
                }
            }
        ],
        "total": 1
    }
}
```

### Get Specific Package State

Retrieve detailed information about a specific package state.

```http
GET /api/v1/states/{state_id}
```

**Response:**
```json
{
    "success": true,
    "data": {
        "id": "state-789",
        "pool_id": "pool-123",
        "endpoint_id": "endpoint-456",
        "is_target": true,
        "created_at": "2024-01-15T08:00:00Z",
        "created_by": "workstation-02",
        "message": "Updated development tools",
        "packages": {
            "firefox": {
                "version": "110.0-1",
                "repository": "extra",
                "size": 52428800,
                "dependencies": ["gtk3", "libxt"]
            },
            // ... detailed package information
        },
        "statistics": {
            "total_packages": 1247,
            "total_size": 8589934592,
            "repositories": {
                "core": 156,
                "extra": 891,
                "community": 200
            }
        }
    }
}
```

## Health and Monitoring API

### Health Check

Check server health status.

```http
GET /api/v1/health/live
```

**Response:**
```json
{
    "success": true,
    "data": {
        "status": "healthy",
        "timestamp": "2024-01-15T10:30:00Z",
        "uptime": 86400,
        "version": "1.0.0"
    }
}
```

### Detailed Health Check

Get comprehensive health information.

```http
GET /api/v1/health/ready
```

**Response:**
```json
{
    "success": true,
    "data": {
        "status": "healthy",
        "components": {
            "database": {
                "status": "healthy",
                "response_time": 5,
                "connections": {
                    "active": 3,
                    "idle": 7,
                    "max": 20
                }
            },
            "api": {
                "status": "healthy",
                "requests_per_minute": 45,
                "average_response_time": 120
            },
            "background_tasks": {
                "status": "healthy",
                "active_tasks": 2,
                "completed_tasks": 1456,
                "failed_tasks": 3
            }
        },
        "system": {
            "cpu_usage": 15.5,
            "memory_usage": 67.2,
            "disk_usage": 45.8
        }
    }
}
```

### Metrics

Get Prometheus-compatible metrics.

```http
GET /api/v1/metrics
```

**Response:**
```
# HELP pacman_sync_pools_total Total number of pools
# TYPE pacman_sync_pools_total gauge
pacman_sync_pools_total 5

# HELP pacman_sync_endpoints_total Total number of endpoints
# TYPE pacman_sync_endpoints_total gauge
pacman_sync_endpoints_total 23

# HELP pacman_sync_operations_total Total number of sync operations
# TYPE pacman_sync_operations_total counter
pacman_sync_operations_total 1456

# HELP pacman_sync_operation_duration_seconds Duration of sync operations
# TYPE pacman_sync_operation_duration_seconds histogram
pacman_sync_operation_duration_seconds_bucket{le="30"} 145
pacman_sync_operation_duration_seconds_bucket{le="60"} 234
pacman_sync_operation_duration_seconds_bucket{le="120"} 456
```

## WebSocket API (Real-time Updates)

### Connection

Connect to the WebSocket endpoint for real-time updates:

```javascript
const ws = new WebSocket('ws://server:8080/api/v1/ws');

ws.onopen = function() {
    // Subscribe to updates
    ws.send(JSON.stringify({
        type: 'subscribe',
        channels: ['pool.pool-123', 'endpoint.endpoint-456']
    }));
};

ws.onmessage = function(event) {
    const message = JSON.parse(event.data);
    console.log('Received update:', message);
};
```

### Message Types

#### Sync Status Updates
```json
{
    "type": "sync_status",
    "endpoint_id": "endpoint-456",
    "status": "in_progress",
    "progress": 45,
    "timestamp": "2024-01-15T10:30:00Z"
}
```

#### Pool Updates
```json
{
    "type": "pool_update",
    "pool_id": "pool-123",
    "change": "target_state_updated",
    "data": {
        "new_target_state_id": "state-new-123"
    },
    "timestamp": "2024-01-15T10:30:00Z"
}
```

#### Endpoint Status Changes
```json
{
    "type": "endpoint_status",
    "endpoint_id": "endpoint-456",
    "old_status": "offline",
    "new_status": "online",
    "timestamp": "2024-01-15T10:30:00Z"
}
```

## Error Codes

### Common Error Codes

| Code | Description | HTTP Status |
|------|-------------|-------------|
| `VALIDATION_ERROR` | Request validation failed | 400 |
| `AUTHENTICATION_REQUIRED` | API key required | 401 |
| `INSUFFICIENT_PERMISSIONS` | Operation not allowed | 403 |
| `RESOURCE_NOT_FOUND` | Requested resource doesn't exist | 404 |
| `RESOURCE_CONFLICT` | Resource already exists | 409 |
| `SYNC_IN_PROGRESS` | Sync operation already running | 409 |
| `INVALID_STATE` | Invalid operation for current state | 422 |
| `DATABASE_ERROR` | Database operation failed | 500 |
| `INTERNAL_ERROR` | Unexpected server error | 500 |

### Error Response Examples

#### Validation Error
```json
{
    "success": false,
    "error": {
        "code": "VALIDATION_ERROR",
        "message": "Invalid request data",
        "details": {
            "field": "name",
            "reason": "Name must be between 3 and 50 characters"
        }
    }
}
```

#### Resource Conflict
```json
{
    "success": false,
    "error": {
        "code": "RESOURCE_CONFLICT",
        "message": "Pool name already exists",
        "details": {
            "existing_pool_id": "pool-456",
            "suggested_names": ["development-pool-2", "dev-pool"]
        }
    }
}
```

## Rate Limiting

### Rate Limit Headers

All API responses include rate limiting information:

```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1642248600
X-RateLimit-Window: 60
```

### Rate Limit Exceeded

When rate limits are exceeded:

```json
{
    "success": false,
    "error": {
        "code": "RATE_LIMIT_EXCEEDED",
        "message": "Too many requests",
        "details": {
            "limit": 100,
            "window": 60,
            "retry_after": 45
        }
    }
}
```

## SDK and Client Libraries

### Python Client Example

```python
import requests
import json

class PacmanSyncClient:
    def __init__(self, base_url, api_key):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        })
    
    def get_pools(self):
        response = self.session.get(f'{self.base_url}/api/v1/pools')
        response.raise_for_status()
        return response.json()
    
    def create_pool(self, name, description, settings=None):
        data = {
            'name': name,
            'description': description,
            'settings': settings or {}
        }
        response = self.session.post(
            f'{self.base_url}/api/v1/pools',
            json=data
        )
        response.raise_for_status()
        return response.json()
    
    def sync_endpoint(self, endpoint_id, options=None):
        data = {
            'type': 'sync_to_latest',
            'options': options or {}
        }
        response = self.session.post(
            f'{self.base_url}/api/v1/endpoints/{endpoint_id}/sync',
            json=data
        )
        response.raise_for_status()
        return response.json()

# Usage
client = PacmanSyncClient('http://server:8080', 'your-api-key')
pools = client.get_pools()
print(f"Found {len(pools['data']['pools'])} pools")
```

### JavaScript Client Example

```javascript
class PacmanSyncClient {
    constructor(baseUrl, apiKey) {
        this.baseUrl = baseUrl.replace(/\/$/, '');
        this.apiKey = apiKey;
    }
    
    async request(method, endpoint, data = null) {
        const url = `${this.baseUrl}/api/v1${endpoint}`;
        const options = {
            method,
            headers: {
                'Authorization': `Bearer ${this.apiKey}`,
                'Content-Type': 'application/json'
            }
        };
        
        if (data) {
            options.body = JSON.stringify(data);
        }
        
        const response = await fetch(url, options);
        
        if (!response.ok) {
            throw new Error(`API request failed: ${response.statusText}`);
        }
        
        return response.json();
    }
    
    async getPools() {
        return this.request('GET', '/pools');
    }
    
    async createPool(name, description, settings = {}) {
        return this.request('POST', '/pools', {
            name,
            description,
            settings
        });
    }
    
    async syncEndpoint(endpointId, options = {}) {
        return this.request('POST', `/endpoints/${endpointId}/sync`, {
            type: 'sync_to_latest',
            options
        });
    }
}

// Usage
const client = new PacmanSyncClient('http://server:8080', 'your-api-key');
client.getPools().then(pools => {
    console.log(`Found ${pools.data.pools.length} pools`);
});
```

## Testing the API

### Using curl

```bash
# Set variables
SERVER="http://server:8080"
API_KEY="your-api-key"

# Test authentication
curl -H "Authorization: Bearer $API_KEY" \
     "$SERVER/api/v1/pools"

# Create a pool
curl -X POST \
     -H "Authorization: Bearer $API_KEY" \
     -H "Content-Type: application/json" \
     -d '{"name":"test-pool","description":"Test pool"}' \
     "$SERVER/api/v1/pools"

# Trigger sync
curl -X POST \
     -H "Authorization: Bearer $API_KEY" \
     -H "Content-Type: application/json" \
     -d '{"type":"sync_to_latest","options":{"dry_run":true}}' \
     "$SERVER/api/v1/endpoints/endpoint-123/sync"
```

### Using HTTPie

```bash
# Install HTTPie
pip install httpie

# Set up authentication
export API_KEY="your-api-key"

# Test endpoints
http GET server:8080/api/v1/pools Authorization:"Bearer $API_KEY"

http POST server:8080/api/v1/pools \
     Authorization:"Bearer $API_KEY" \
     name="test-pool" \
     description="Test pool"

http POST server:8080/api/v1/endpoints/endpoint-123/sync \
     Authorization:"Bearer $API_KEY" \
     type="sync_to_latest" \
     options:='{"dry_run": true}'
```

## Best Practices

### API Usage
- **Always check response status** before processing data
- **Implement proper error handling** for all error codes
- **Use appropriate HTTP methods** (GET for reading, POST for creation, etc.)
- **Include request timeouts** to handle slow responses
- **Implement retry logic** with exponential backoff

### Security
- **Protect API keys** and rotate them regularly
- **Use HTTPS** in production environments
- **Validate all input data** before sending to API
- **Implement rate limiting** in client applications
- **Log API access** for security auditing

### Performance
- **Use pagination** for large result sets
- **Cache responses** when appropriate
- **Use WebSocket connections** for real-time updates
- **Batch operations** when possible
- **Monitor API response times** and optimize accordingly

## Getting Help

### Interactive API Documentation

The server provides interactive API documentation at:
```
http://your-server:8080/docs
```

This includes:
- Complete endpoint documentation
- Request/response examples
- Interactive testing interface
- Authentication setup

### Support Resources

1. **API Status Page**: Check `GET /api/v1/health/ready` for system status
2. **Error Logs**: Review server logs for detailed error information
3. **Rate Limit Status**: Monitor rate limit headers in responses
4. **Community Support**: Check GitHub issues and discussions

## Next Steps

After mastering the API:

1. Explore [Web UI Integration](web-ui-guide.md) for frontend development
2. Set up [Monitoring Integration](troubleshooting.md#monitoring) using metrics endpoints
3. Review [Advanced Configuration](configuration.md) for API customization
4. Check [CLI Integration](cli-guide.md) for command-line API usage