# Docker Deployment Guide

This document provides comprehensive instructions for deploying the Pacman Sync Utility using Docker containers.

## Overview

The Pacman Sync Utility supports Docker deployment with the following features:

- **Multi-stage builds** for optimized production and development images
- **Environment variable configuration** for all server settings
- **Volume mount support** for persistent data storage
- **PostgreSQL integration** with optional external database support
- **Health checks** for container monitoring
- **Security best practices** with non-root user execution

## Quick Start

### 1. Basic Production Deployment

```bash
# Clone the repository
git clone <repository-url>
cd pacman-sync-utility

# Copy and customize environment configuration
cp .env.example .env
# Edit .env with your settings

# Start production services
./deploy.sh prod
```

### 2. Development Environment

```bash
# Start development environment with hot reload
./deploy.sh dev
```

## Configuration

### Environment Variables

The application supports comprehensive configuration through environment variables. Copy `.env.example` to `.env` and customize:

#### Database Configuration

```bash
# Database type: 'internal' for SQLite or 'postgresql' for external PostgreSQL
DATABASE_TYPE=internal

# PostgreSQL connection (when DATABASE_TYPE=postgresql)
DATABASE_URL=postgresql://username:password@host:port/database
# OR individual components:
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=pacman_sync
POSTGRES_USER=pacman_sync
POSTGRES_PASSWORD=changeme
```

#### Server Configuration

```bash
# HTTP server settings
HTTP_PORT=8080
HTTP_HOST=0.0.0.0
LOG_LEVEL=INFO
ENVIRONMENT=production

# CORS configuration (comma-separated origins)
CORS_ORIGINS=*
```

#### Security Configuration

```bash
# JWT secret key (CHANGE IN PRODUCTION!)
JWT_SECRET_KEY=your-very-secure-secret-key

# API rate limiting (requests per minute per IP)
API_RATE_LIMIT=100
```

#### Feature Flags

```bash
# Enable repository compatibility analysis
ENABLE_REPOSITORY_ANALYSIS=true

# Automatically clean up old package states
AUTO_CLEANUP_OLD_STATES=true
MAX_STATE_SNAPSHOTS=10
```

#### Performance Tuning

```bash
# Production worker processes
GUNICORN_WORKERS=4

# Database connection pooling (PostgreSQL only)
DB_POOL_MIN_SIZE=1
DB_POOL_MAX_SIZE=10

# Request timeout
REQUEST_TIMEOUT=60
```

## Docker Images

### Multi-Stage Build Architecture

The Dockerfile uses a multi-stage build process:

1. **web-builder**: Builds the React/Vue.js web UI
2. **base**: Common Python dependencies and system setup
3. **development**: Development tools and hot reload support
4. **production**: Optimized production image with Gunicorn

### Image Variants

- **Production**: `pacman-sync-server:production` - Optimized for production deployment
- **Development**: `pacman-sync-server:development` - Includes development tools and hot reload

## Deployment Options

### Option 1: Docker Compose (Recommended)

#### Production with Internal Database

```bash
# Start with internal SQLite database
DATABASE_TYPE=internal ./deploy.sh prod
```

#### Production with PostgreSQL

```bash
# Start with external PostgreSQL database
DATABASE_TYPE=postgresql ./deploy.sh prod --database postgresql
```

#### Development Environment

```bash
# Start development environment
./deploy.sh dev
```

### Option 2: Manual Docker Commands

#### Build Images

```bash
# Build production image
docker build --target production -t pacman-sync:prod .

# Build development image
docker build --target development -t pacman-sync:dev .
```

#### Run Production Container

```bash
docker run -d \
  --name pacman-sync-server \
  -p 8080:8080 \
  -v pacman-sync-data:/app/data \
  -v pacman-sync-logs:/app/logs \
  -v pacman-sync-config:/app/config \
  -e DATABASE_TYPE=internal \
  -e HTTP_PORT=8080 \
  -e LOG_LEVEL=INFO \
  pacman-sync:prod
```

#### Run with PostgreSQL

```bash
# Start PostgreSQL
docker run -d \
  --name pacman-sync-postgres \
  -e POSTGRES_DB=pacman_sync \
  -e POSTGRES_USER=pacman_sync \
  -e POSTGRES_PASSWORD=changeme \
  -v postgres-data:/var/lib/postgresql/data \
  postgres:15-alpine

# Start application
docker run -d \
  --name pacman-sync-server \
  --link pacman-sync-postgres:postgres \
  -p 8080:8080 \
  -v pacman-sync-data:/app/data \
  -v pacman-sync-logs:/app/logs \
  -v pacman-sync-config:/app/config \
  -e DATABASE_TYPE=postgresql \
  -e DATABASE_URL=postgresql://pacman_sync:changeme@postgres:5432/pacman_sync \
  pacman-sync:prod
```

## Volume Mounts

The application uses three main volume mounts for persistent data:

### Data Volume (`/app/data`)

- **Purpose**: Application data and internal SQLite database
- **Contents**: 
  - `pacman_sync.db` (when using internal database)
  - Temporary files and caches
- **Backup**: Critical for data persistence

### Logs Volume (`/app/logs`)

- **Purpose**: Application logs and audit trails
- **Contents**:
  - `access.log` (HTTP access logs)
  - `error.log` (Application error logs)
  - `app.log` (General application logs)
- **Rotation**: Configured via `LOG_MAX_SIZE` and `LOG_BACKUP_COUNT`

### Config Volume (`/app/config`)

- **Purpose**: Runtime configuration and customization
- **Contents**:
  - Custom configuration files
  - SSL certificates (if needed)
  - Plugin configurations
- **Mount**: Can be mounted read-only for security

### Example Volume Configuration

```yaml
# docker-compose.yml
volumes:
  # Named volumes (managed by Docker)
  - pacman-sync-data:/app/data
  - pacman-sync-logs:/app/logs
  - pacman-sync-config:/app/config
  
  # Host bind mounts (for direct access)
  - ./data:/app/data
  - ./logs:/app/logs
  - ./config:/app/config:ro  # Read-only
```

## Health Checks

### Built-in Health Check

The container includes a built-in health check that:

- Tests the `/health` endpoint
- Verifies database connectivity
- Returns service status and version information
- Runs every 30 seconds with 10-second timeout

### Health Check Endpoint

```bash
# Check container health
curl http://localhost:8080/health

# Response format
{
  "status": "healthy",
  "timestamp": "2025-01-15T10:30:00Z",
  "database": "connected",
  "version": "1.0.0"
}
```

### Custom Health Check Script

Use the included `healthcheck.sh` script for custom monitoring:

```bash
# Run health check manually
./healthcheck.sh

# Use in monitoring systems
docker exec pacman-sync-server /app/healthcheck.sh
```

## Security Considerations

### Container Security

- **Non-root user**: Application runs as `appuser` (UID/GID managed by Docker)
- **Read-only filesystem**: Consider using `--read-only` flag with tmpfs mounts
- **Resource limits**: Configure memory and CPU limits in production
- **Network isolation**: Use custom networks to isolate services

### Production Security Checklist

- [ ] Change default `JWT_SECRET_KEY`
- [ ] Use strong PostgreSQL passwords
- [ ] Configure appropriate `CORS_ORIGINS`
- [ ] Enable SSL termination via reverse proxy
- [ ] Set up log rotation and monitoring
- [ ] Configure resource limits
- [ ] Use secrets management for sensitive data

### Example Secure Configuration

```yaml
# docker-compose.override.yml
services:
  pacman-sync-server:
    read_only: true
    tmpfs:
      - /tmp
      - /var/tmp
    deploy:
      resources:
        limits:
          memory: 512M
          cpus: '0.5'
    security_opt:
      - no-new-privileges:true
    cap_drop:
      - ALL
    cap_add:
      - CHOWN
      - SETGID
      - SETUID
```

## Monitoring and Logging

### Log Configuration

```bash
# Structured JSON logging
STRUCTURED_LOGGING=true

# Log levels: DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_LEVEL=INFO

# Log rotation
LOG_MAX_SIZE=10MB
LOG_BACKUP_COUNT=5
```

### Monitoring Integration

The application supports integration with monitoring systems:

- **Prometheus**: Metrics endpoint at `/metrics` (if enabled)
- **Health checks**: Standard Docker health check protocol
- **Structured logging**: JSON format for log aggregation
- **Audit trails**: All operations logged with timestamps

### Log Aggregation Example

```yaml
# docker-compose.yml with log driver
services:
  pacman-sync-server:
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
        labels: "service=pacman-sync"
```

## Scaling and High Availability

### Horizontal Scaling

The application supports horizontal scaling with proper configuration:

```yaml
# docker-compose.yml
services:
  pacman-sync-server:
    deploy:
      replicas: 3
      update_config:
        parallelism: 1
        delay: 10s
      restart_policy:
        condition: on-failure
```

### Load Balancing

Use a reverse proxy for load balancing:

```nginx
# nginx.conf
upstream pacman_sync {
    server pacman-sync-1:8080;
    server pacman-sync-2:8080;
    server pacman-sync-3:8080;
}

server {
    listen 80;
    location / {
        proxy_pass http://pacman_sync;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### Database Considerations

- **PostgreSQL**: Required for multi-instance deployments
- **Connection pooling**: Configure `DB_POOL_MAX_SIZE` appropriately
- **Database migrations**: Run migrations before scaling up

## Troubleshooting

### Common Issues

#### Container Won't Start

```bash
# Check container logs
docker logs pacman-sync-server

# Check configuration
docker-compose config

# Validate environment variables
docker exec pacman-sync-server env | grep -E "(DATABASE|HTTP|LOG)"
```

#### Database Connection Issues

```bash
# Test PostgreSQL connection
docker exec pacman-sync-postgres pg_isready -U pacman_sync

# Check database logs
docker logs pacman-sync-postgres

# Test from application container
docker exec pacman-sync-server curl -f http://localhost:8080/health
```

#### Permission Issues

```bash
# Check volume permissions
docker exec pacman-sync-server ls -la /app/

# Fix volume ownership (if needed)
docker exec --user root pacman-sync-server chown -R appuser:appuser /app/data
```

### Debugging Commands

```bash
# Enter container for debugging
docker exec -it pacman-sync-server bash

# Check application status
docker exec pacman-sync-server ps aux

# View real-time logs
docker logs -f pacman-sync-server

# Check resource usage
docker stats pacman-sync-server
```

### Validation Script

Use the included validation script to test your Docker configuration:

```bash
# Validate Docker configuration
./validate-docker.sh

# This script tests:
# - Dockerfile syntax and best practices
# - docker-compose.yml configuration
# - Environment variable setup
# - Container build process
# - Runtime functionality
# - Volume mounts
# - Health checks
```

## Backup and Recovery

### Data Backup

```bash
# Backup data volume
docker run --rm -v pacman-sync-data:/data -v $(pwd):/backup alpine \
  tar czf /backup/pacman-sync-data-$(date +%Y%m%d).tar.gz -C /data .

# Backup PostgreSQL database
docker exec pacman-sync-postgres pg_dump -U pacman_sync pacman_sync > \
  pacman-sync-db-$(date +%Y%m%d).sql
```

### Data Recovery

```bash
# Restore data volume
docker run --rm -v pacman-sync-data:/data -v $(pwd):/backup alpine \
  tar xzf /backup/pacman-sync-data-20250115.tar.gz -C /data

# Restore PostgreSQL database
docker exec -i pacman-sync-postgres psql -U pacman_sync pacman_sync < \
  pacman-sync-db-20250115.sql
```

## Performance Optimization

### Production Optimizations

```bash
# Gunicorn worker configuration
GUNICORN_WORKERS=4  # CPU cores * 2

# Database connection pooling
DB_POOL_MIN_SIZE=2
DB_POOL_MAX_SIZE=20

# Request timeout
REQUEST_TIMEOUT=30

# Log level for production
LOG_LEVEL=WARNING
```

### Resource Limits

```yaml
# docker-compose.yml
services:
  pacman-sync-server:
    deploy:
      resources:
        limits:
          memory: 1G
          cpus: '1.0'
        reservations:
          memory: 512M
          cpus: '0.5'
```

## Support and Maintenance

### Regular Maintenance Tasks

1. **Log Rotation**: Ensure log files don't consume excessive disk space
2. **Database Cleanup**: Remove old package states based on retention policy
3. **Image Updates**: Regularly update base images for security patches
4. **Backup Verification**: Test backup and recovery procedures
5. **Health Monitoring**: Monitor application health and performance metrics

### Update Procedure

```bash
# Pull latest changes
git pull origin main

# Rebuild images
docker-compose build --no-cache

# Rolling update
docker-compose up -d --force-recreate
```

This completes the comprehensive Docker deployment guide for the Pacman Sync Utility.