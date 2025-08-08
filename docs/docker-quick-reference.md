# Docker Quick Reference

Quick commands for building and running the Pacman Sync Utility server with Docker.

## Build Commands

### Production Image
```bash
# Build production image
docker build --target production -t pacman-sync-server:latest .

# Build with specific tag
docker build --target production -t pacman-sync-server:v1.0.0 .
```

### Development Image
```bash
# Build development image
docker build --target development -t pacman-sync-server:dev .

# Build development with cache
docker build --target development -t pacman-sync-server:dev --build-arg BUILDKIT_INLINE_CACHE=1 .
```

## GitHub Container Registry Images

### Pull Pre-built Images
```bash
# Pull latest production image
docker pull ghcr.io/scsiexpress/pacman-sync-server:latest

# Pull development image
docker pull ghcr.io/scsiexpress/pacman-sync-server:dev

# Pull specific version
docker pull ghcr.io/scsiexpress/pacman-sync-server:v1.0.0
```

### Build and Push (Maintainers)
```bash
# Login to GitHub Container Registry
./ghcr-login.sh

# Build and push both images
./build-and-push.sh

# Build only (skip push)
./build-and-push.sh --skip-push

# Push only (skip build)
./build-and-push.sh --skip-build
```

## Docker Compose Commands

### Start Services
```bash
# Start all services in background
docker-compose up -d

# Start with build (rebuild images)
docker-compose up -d --build

# Start development profile
docker-compose --profile dev up -d

# Start with PostgreSQL
docker-compose --profile postgres up -d
```

### Manage Services
```bash
# Check status
docker-compose ps

# View logs
docker-compose logs -f pacman-sync-server

# Stop services
docker-compose down

# Stop and remove volumes
docker-compose down -v

# Restart specific service
docker-compose restart pacman-sync-server
```

## Manual Container Commands

### Production Container
```bash
# Run production container with internal database (local build)
docker run -d \
  --name pacman-sync-server \
  -p 8080:8080 \
  -e DATABASE_TYPE=internal \
  -e JWT_SECRET_KEY="$(openssl rand -hex 32)" \
  -e LOG_LEVEL=INFO \
  -v pacman-sync-data:/app/data \
  -v pacman-sync-logs:/app/logs \
  --restart unless-stopped \
  pacman-sync-server:latest

# Run production container (GitHub Container Registry)
docker run -d \
  --name pacman-sync-server \
  -p 8080:8080 \
  -e DATABASE_TYPE=internal \
  -e JWT_SECRET_KEY="$(openssl rand -hex 32)" \
  -e LOG_LEVEL=INFO \
  -v pacman-sync-data:/app/data \
  -v pacman-sync-logs:/app/logs \
  --restart unless-stopped \
  ghcr.io/scsiexpress/pacman-sync-server:latest

# Run with PostgreSQL
docker run -d \
  --name pacman-sync-server \
  -p 8080:8080 \
  -e DATABASE_TYPE=postgresql \
  -e DATABASE_URL="postgresql://user:pass@host:5432/db" \
  -e JWT_SECRET_KEY="$(openssl rand -hex 32)" \
  -e LOG_LEVEL=INFO \
  -v pacman-sync-data:/app/data \
  -v pacman-sync-logs:/app/logs \
  --restart unless-stopped \
  pacman-sync-server:latest
```

### Development Container
```bash
# Run development container with hot reload (local build)
docker run -d \
  --name pacman-sync-dev \
  -p 8080:8080 \
  -e DATABASE_TYPE=internal \
  -e JWT_SECRET_KEY=dev-secret-key \
  -e LOG_LEVEL=DEBUG \
  -e ENVIRONMENT=development \
  -v $(pwd)/server:/app/server \
  -v $(pwd)/shared:/app/shared \
  -v pacman-sync-dev-data:/app/data \
  -v pacman-sync-dev-logs:/app/logs \
  pacman-sync-server:dev

# Run development container (GitHub Container Registry)
docker run -d \
  --name pacman-sync-dev \
  -p 8080:8080 \
  -e DATABASE_TYPE=internal \
  -e JWT_SECRET_KEY=dev-secret-key \
  -e LOG_LEVEL=DEBUG \
  -e ENVIRONMENT=development \
  -v $(pwd)/server:/app/server \
  -v $(pwd)/shared:/app/shared \
  -v pacman-sync-dev-data:/app/data \
  -v pacman-sync-dev-logs:/app/logs \
  ghcr.io/scsiexpress/pacman-sync-server:dev
```

## Container Management

### Monitor and Debug
```bash
# Check container status
docker ps

# View container logs
docker logs -f pacman-sync-server

# Access container shell
docker exec -it pacman-sync-server bash

# Check container health
docker inspect --format='{{.State.Health.Status}}' pacman-sync-server

# Monitor resource usage
docker stats pacman-sync-server
```

### Cleanup
```bash
# Stop and remove container
docker stop pacman-sync-server
docker rm pacman-sync-server

# Remove images
docker rmi pacman-sync-server:latest
docker rmi pacman-sync-server:dev

# Clean up unused resources
docker system prune -f

# Remove all volumes (WARNING: deletes data)
docker volume prune -f
```

## Health Checks

### Test Endpoints
```bash
# Health check
curl -f http://localhost:8080/health/live

# Ready check
curl -f http://localhost:8080/health/ready

# API status
curl http://localhost:8080/api/v1/status
```

## Environment Variables Reference

### Required
- `JWT_SECRET_KEY`: Secret key for JWT tokens

### Database
- `DATABASE_TYPE`: `internal` or `postgresql`
- `DATABASE_URL`: Full PostgreSQL connection string
- `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`

### Server
- `HTTP_HOST`: Server bind address (default: 0.0.0.0)
- `HTTP_PORT`: Server port (default: 8080)
- `LOG_LEVEL`: DEBUG, INFO, WARNING, ERROR
- `ENVIRONMENT`: development, production

### Features
- `ENABLE_REPOSITORY_ANALYSIS`: true/false
- `AUTO_CLEANUP_OLD_STATES`: true/false
- `API_RATE_LIMIT`: Requests per minute

## Quick Start Workflows

### 1. Development Setup
```bash
# Build and run development environment
docker build --target development -t pacman-sync-server:dev .
docker run -d --name pacman-sync-dev -p 8080:8080 \
  -e DATABASE_TYPE=internal \
  -e JWT_SECRET_KEY=dev-key \
  -v $(pwd)/server:/app/server \
  pacman-sync-server:dev

# Check logs
docker logs -f pacman-sync-dev
```

### 2. Production Deployment
```bash
# Build and deploy production
docker build --target production -t pacman-sync-server:latest .
docker run -d --name pacman-sync-server -p 8080:8080 \
  -e DATABASE_TYPE=internal \
  -e JWT_SECRET_KEY="$(openssl rand -hex 32)" \
  -v pacman-sync-data:/app/data \
  --restart unless-stopped \
  pacman-sync-server:latest

# Verify deployment
curl http://localhost:8080/health/live
```

### 3. Docker Compose (Recommended)
```bash
# Start everything
docker-compose up -d --build

# Check status
docker-compose ps

# View logs
docker-compose logs -f

# Access web UI
open http://localhost:8080
```

## Troubleshooting

### Common Issues
```bash
# Container won't start
docker logs pacman-sync-server

# Permission issues
docker exec -it pacman-sync-server chown -R pacman-sync:pacman-sync /app/data

# Port conflicts
docker run -p 8081:8080 ...  # Use different host port

# Database connection issues
docker exec -it pacman-sync-server python3 -c "from server.config import get_config; print(get_config().database)"
```

### Reset Everything
```bash
# Nuclear option - removes everything
docker-compose down -v
docker system prune -af
docker volume prune -f
```