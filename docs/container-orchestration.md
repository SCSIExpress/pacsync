# Container Orchestration and Scaling Support

This document describes the container orchestration and scaling features implemented in Task 9.2 of the Pacman Sync Utility.

## Overview

The Pacman Sync Utility now includes comprehensive support for container orchestration and horizontal scaling, including:

1. **Enhanced Health Check Endpoints** - Multiple health check endpoints for different monitoring needs
2. **Graceful Shutdown Handling** - Proper lifecycle management for container environments
3. **Database Connection Pooling** - Optimized database connections for horizontal scaling

## Health Check Endpoints

### Available Endpoints

#### `/health` - Basic Health Check
- **Purpose**: Simple liveness check for basic monitoring
- **Response**: 200 OK if service is healthy, 503 if critical issues
- **Use Case**: Basic container health checks, simple monitoring systems

```json
{
  "status": "healthy",
  "service": "pacman-sync-utility",
  "version": "1.0.0",
  "uptime_seconds": 123.45,
  "timestamp": "2025-01-15T10:30:00Z"
}
```

#### `/health/detailed` - Comprehensive Health Check
- **Purpose**: Detailed health information for monitoring dashboards
- **Response**: Includes database status, service dependencies, and configuration
- **Use Case**: Monitoring dashboards, troubleshooting, operational visibility

```json
{
  "status": "healthy",
  "service": "pacman-sync-utility",
  "version": "1.0.0",
  "timestamp": "2025-01-15T10:30:00Z",
  "uptime_seconds": 123.45,
  "environment": "production",
  "components": {
    "database": {
      "status": "healthy",
      "type": "postgresql",
      "response_time_ms": 2.34,
      "last_check": "2025-01-15T10:30:00Z"
    },
    "dependencies": {
      "pool_manager": "healthy",
      "sync_coordinator": "healthy",
      "endpoint_manager": "healthy"
    }
  },
  "configuration": {
    "database_type": "postgresql",
    "pool_size": "2-10",
    "cors_enabled": true,
    "features": {
      "repository_analysis": true,
      "auto_cleanup": true
    }
  }
}
```

#### `/health/ready` - Readiness Check
- **Purpose**: Kubernetes readiness probe - indicates when service is ready to accept traffic
- **Response**: 200 when ready, 503 when starting up or has issues
- **Use Case**: Kubernetes readiness probes, load balancer health checks

```json
{
  "status": "ready",
  "uptime_seconds": 123.45,
  "timestamp": "2025-01-15T10:30:00Z"
}
```

#### `/health/live` - Liveness Check
- **Purpose**: Kubernetes liveness probe - indicates if the process is alive
- **Response**: Always 200 if the process is responsive
- **Use Case**: Kubernetes liveness probes, process monitoring

```json
{
  "status": "alive",
  "uptime_seconds": 123.45,
  "timestamp": "2025-01-15T10:30:00Z"
}
```

### Container Integration

#### Docker Health Checks
The Dockerfile includes built-in health checks using the readiness endpoint:

```dockerfile
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:${HTTP_PORT:-8080}/health/ready || exit 1
```

#### Kubernetes Probes
The Kubernetes deployment includes all three probe types:

```yaml
# Liveness probe - checks if container is alive
livenessProbe:
  httpGet:
    path: /health/live
    port: 8080
  initialDelaySeconds: 30
  periodSeconds: 30

# Readiness probe - checks if container is ready for traffic
readinessProbe:
  httpGet:
    path: /health/ready
    port: 8080
  initialDelaySeconds: 10
  periodSeconds: 10

# Startup probe - gives container time to start
startupProbe:
  httpGet:
    path: /health/live
    port: 8080
  initialDelaySeconds: 10
  periodSeconds: 5
  failureThreshold: 12
```

## Graceful Shutdown Handling

### Features

The graceful shutdown system provides:

- **Signal Handling**: Catches SIGTERM and SIGINT signals
- **Active Operation Tracking**: Waits for ongoing operations to complete
- **Cleanup Tasks**: Runs registered cleanup functions
- **Timeout Management**: Enforces shutdown timeout to prevent hanging
- **Status Tracking**: Provides shutdown status information

### Usage

#### Automatic Integration
The shutdown handler is automatically integrated into the FastAPI application:

```python
from server.core.shutdown_handler import setup_graceful_shutdown

# Set up graceful shutdown with 30-second timeout
shutdown_handler = setup_graceful_shutdown(shutdown_timeout=30)
```

#### Operation Context
Use the operation context to track long-running operations:

```python
async with shutdown_handler.operation_context("sync_operation"):
    # Your long-running operation here
    await perform_sync_operation()
```

#### Cleanup Tasks
Register cleanup functions to run during shutdown:

```python
shutdown_handler.register_cleanup_task(cleanup_database_connections)
shutdown_handler.register_cleanup_task(save_application_state)
```

### Container Lifecycle

#### Docker Compose
```yaml
services:
  pacman-sync-server:
    # Graceful shutdown configuration
    stop_grace_period: 45s
```

#### Kubernetes
```yaml
spec:
  template:
    spec:
      # Graceful shutdown configuration
      terminationGracePeriodSeconds: 45
      containers:
      - name: pacman-sync-utility
        lifecycle:
          preStop:
            exec:
              command: ["/bin/sh", "-c", "sleep 15"]
```

## Database Connection Pooling

### Enhanced PostgreSQL Pooling

The database connection pooling has been enhanced for horizontal scaling:

#### Configuration Options
```bash
# Environment variables for pool configuration
DB_POOL_MIN_SIZE=2          # Minimum connections per instance
DB_POOL_MAX_SIZE=10         # Maximum connections per instance
```

#### Pool Features
- **Connection Lifecycle Management**: Automatic connection recycling
- **Health Monitoring**: Built-in connection health checks
- **Performance Optimization**: TCP keepalive settings
- **Graceful Shutdown**: Proper connection cleanup during shutdown

#### Pool Statistics
Monitor connection pool health via the detailed health endpoint:

```json
{
  "components": {
    "database": {
      "type": "postgresql",
      "size": 5,
      "min_size": 2,
      "max_size": 10,
      "idle_connections": 3,
      "active_connections": 2
    }
  }
}
```

### SQLite Support
For development and single-instance deployments:

```json
{
  "components": {
    "database": {
      "type": "sqlite",
      "connection_status": "connected"
    }
  }
}
```

## Horizontal Scaling

### Docker Compose Scaling

#### Basic Scaling
```bash
# Scale to 3 instances
docker-compose up --scale pacman-sync-server=3
```

#### Advanced Scaling with Load Balancer
```bash
# Use the scaling configuration with HAProxy
docker-compose -f docker-compose.yml -f docker-compose.scale.yml up
```

### Kubernetes Horizontal Pod Autoscaler

The Kubernetes deployment includes HPA configuration:

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: pacman-sync-utility-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: pacman-sync-utility
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

### Load Balancing

#### HAProxy Configuration
The included HAProxy configuration provides:

- **Health Check Integration**: Uses the health endpoints for backend monitoring
- **Session Affinity**: Sticky sessions for sync operations
- **Statistics Interface**: Available at `:8404/stats`
- **Monitoring Interface**: Available at `:8405`

#### Load Balancer Health Checks
```haproxy
backend pacman_sync_api
    balance roundrobin
    option httpchk GET /health/ready
    http-check expect status 200
    
    server server1 pacman-sync-server_1:8080 check inter 10s fall 3 rise 2
    server server2 pacman-sync-server_2:8080 check inter 10s fall 3 rise 2
    server server3 pacman-sync-server_3:8080 check inter 10s fall 3 rise 2
```

## Monitoring and Observability

### Prometheus Integration

The Prometheus configuration scrapes health endpoints:

```yaml
scrape_configs:
  - job_name: 'pacman-sync-health'
    static_configs:
      - targets: ['haproxy:8080']
    metrics_path: '/health/detailed'
    scrape_interval: 30s
```

### Monitoring Endpoints

#### HAProxy Stats
- **URL**: `http://localhost:8404/stats`
- **Purpose**: Load balancer statistics and backend health

#### Detailed Health Monitoring
- **URL**: `http://localhost:8405/health/detailed`
- **Purpose**: Comprehensive service health information

## Deployment Examples

### Development
```bash
# Single instance with internal database
docker-compose up pacman-sync-dev
```

### Production with PostgreSQL
```bash
# Single instance with PostgreSQL
docker-compose --profile postgres up
```

### Scaled Production
```bash
# Multiple instances with load balancer
docker-compose -f docker-compose.yml -f docker-compose.scale.yml up --scale pacman-sync-server=3
```

### Kubernetes
```bash
# Deploy to Kubernetes
kubectl apply -f deploy/kubernetes/deployment.yaml
```

## Configuration Reference

### Environment Variables

#### Database Pool Configuration
- `DB_POOL_MIN_SIZE`: Minimum database connections (default: 2)
- `DB_POOL_MAX_SIZE`: Maximum database connections (default: 10)

#### Health Check Configuration
- `HEALTH_CHECK_INTERVAL`: Health check interval in seconds (default: 30)
- `STRUCTURED_LOGGING`: Enable structured JSON logging (default: true)

#### Shutdown Configuration
- `SHUTDOWN_TIMEOUT`: Graceful shutdown timeout in seconds (default: 30)

### Docker Compose Variables
```bash
# Database pool sizing for scaling
DB_POOL_MIN_SIZE=1
DB_POOL_MAX_SIZE=5

# Health check optimization
HEALTH_CHECK_INTERVAL=15

# Monitoring
STRUCTURED_LOGGING=true
```

## Troubleshooting

### Health Check Issues

#### Service Not Ready
```json
{
  "status": "not_ready",
  "reason": "database_unhealthy",
  "timestamp": "2025-01-15T10:30:00Z"
}
```
**Solution**: Check database connectivity and configuration.

#### Dependencies Not Ready
```json
{
  "status": "not_ready",
  "reason": "dependencies_not_ready",
  "dependencies": {
    "pool_manager": "not_initialized"
  }
}
```
**Solution**: Check application startup logs for initialization errors.

### Scaling Issues

#### Database Connection Exhaustion
**Symptoms**: High response times, connection errors
**Solution**: Increase `DB_POOL_MAX_SIZE` or reduce number of instances

#### Load Balancer Health Check Failures
**Symptoms**: Instances marked as down in HAProxy stats
**Solution**: Check health endpoint responses and adjust health check intervals

### Shutdown Issues

#### Hanging Shutdown
**Symptoms**: Container takes full termination grace period
**Solution**: Check for long-running operations, adjust `SHUTDOWN_TIMEOUT`

#### Incomplete Cleanup
**Symptoms**: Resources not properly cleaned up
**Solution**: Verify cleanup tasks are registered and functioning

## Best Practices

### Health Checks
1. Use `/health/ready` for readiness probes
2. Use `/health/live` for liveness probes
3. Monitor `/health/detailed` for operational insights
4. Set appropriate timeouts and retry counts

### Scaling
1. Start with 2-3 instances minimum
2. Monitor database connection usage
3. Use session affinity for stateful operations
4. Implement proper load balancer health checks

### Shutdown
1. Set graceful shutdown timeout appropriately
2. Register all cleanup tasks
3. Use operation contexts for long-running tasks
4. Monitor shutdown metrics

### Monitoring
1. Scrape health endpoints with Prometheus
2. Set up alerts for health check failures
3. Monitor database pool statistics
4. Track shutdown and startup times