# Docker Registry Guide

This guide covers building, pushing, and using Docker images from GitHub Container Registry (GHCR).

## Overview

The Pacman Sync Utility provides pre-built Docker images hosted on GitHub Container Registry:

- **Registry**: `ghcr.io`
- **Repository**: `scsiexpress/pacman-sync-server`
- **Images**: Production and Development variants
- **Platforms**: `linux/amd64`, `linux/arm64`

## Available Images

### Production Images
- `ghcr.io/scsiexpress/pacman-sync-server:latest` - Latest stable release
- `ghcr.io/scsiexpress/pacman-sync-server:prod` - Production build
- `ghcr.io/scsiexpress/pacman-sync-server:v1.0.0` - Specific version tags

### Development Images
- `ghcr.io/scsiexpress/pacman-sync-server:dev` - Latest development build
- `ghcr.io/scsiexpress/pacman-sync-server:dev-{commit}` - Specific commit builds

## Using Pre-built Images

### Quick Start with Production Image

```bash
# Pull the latest production image
docker pull ghcr.io/scsiexpress/pacman-sync-server:latest

# Run the container
docker run -d \
  --name pacman-sync-server \
  -p 8080:8080 \
  -e DATABASE_TYPE=internal \
  -e JWT_SECRET_KEY="$(openssl rand -hex 32)" \
  -v pacman-sync-data:/app/data \
  --restart unless-stopped \
  ghcr.io/scsiexpress/pacman-sync-server:latest
```

### Development with Pre-built Image

```bash
# Pull the development image
docker pull ghcr.io/scsiexpress/pacman-sync-server:dev

# Run with source code mounting for development
docker run -d \
  --name pacman-sync-dev \
  -p 8080:8080 \
  -e DATABASE_TYPE=internal \
  -e JWT_SECRET_KEY=dev-key \
  -e LOG_LEVEL=DEBUG \
  -v $(pwd)/server:/app/server \
  -v $(pwd)/shared:/app/shared \
  ghcr.io/scsiexpress/pacman-sync-server:dev
```

### Docker Compose with Registry Images

```yaml
services:
  pacman-sync-server:
    image: ghcr.io/scsiexpress/pacman-sync-server:latest
    ports:
      - "8080:8080"
    environment:
      DATABASE_TYPE: internal
      JWT_SECRET_KEY: "your-secret-key"
    volumes:
      - pacman-sync-data:/app/data
      - pacman-sync-logs:/app/logs
    restart: unless-stopped

volumes:
  pacman-sync-data:
  pacman-sync-logs:
```

## Building and Pushing Images (Maintainers)

### Prerequisites

1. **Docker installed and running**
2. **Git repository access**
3. **GitHub account with package write permissions**

### Authentication

#### Option 1: GitHub CLI (Recommended)
```bash
# Install GitHub CLI if not already installed
# Then authenticate
gh auth login

# Login to container registry
./ghcr-login.sh
```

#### Option 2: Personal Access Token
```bash
# Create token at https://github.com/settings/tokens
# Select scopes: write:packages, read:packages, delete:packages

# Login manually
echo YOUR_TOKEN | docker login ghcr.io -u YOUR_USERNAME --password-stdin
```

### Building and Pushing

#### Automated Build and Push
```bash
# Build and push both production and development images
./build-and-push.sh

# View help and options
./build-and-push.sh --help
```

#### Manual Build and Push
```bash
# Build production image
docker build --target production -t ghcr.io/scsiexpress/pacman-sync-server:latest .

# Build development image
docker build --target development -t ghcr.io/scsiexpress/pacman-sync-server:dev .

# Push images
docker push ghcr.io/scsiexpress/pacman-sync-server:latest
docker push ghcr.io/scsiexpress/pacman-sync-server:dev
```

### Build Script Options

```bash
# Build only (don't push)
./build-and-push.sh --skip-push

# Push only (don't build)
./build-and-push.sh --skip-build

# Clean up local images after pushing
./build-and-push.sh --cleanup

# Show help
./build-and-push.sh --help
```

## Automated Builds (GitHub Actions)

The repository includes GitHub Actions workflow that automatically:

- **Builds images** on push to main/develop branches
- **Pushes to GHCR** with appropriate tags
- **Supports multi-platform** builds (amd64, arm64)
- **Creates releases** on git tags

### Workflow Triggers
- Push to `main` or `develop` branches
- Git tags starting with `v` (e.g., `v1.0.0`)
- Manual workflow dispatch
- Pull requests (build only, no push)

### Generated Tags
- `latest` - Latest main branch build
- `prod` - Production build
- `dev` - Development build
- `v1.0.0` - Version tags from git tags
- `main-{commit}` - Branch-specific builds

## Image Information

### Labels and Metadata

All images include OCI-compliant labels:
- `org.opencontainers.image.source` - GitHub repository URL
- `org.opencontainers.image.description` - Image description
- `org.opencontainers.image.licenses` - License information
- `org.opencontainers.image.version` - Version/tag information
- `org.opencontainers.image.revision` - Git commit hash

### Image Sizes

Typical image sizes:
- **Production**: ~200-300MB (optimized, minimal dependencies)
- **Development**: ~400-500MB (includes dev tools, debugging utilities)

### Security

- Images run as **non-root user** (`pacman-sync`, UID 1000)
- **Minimal attack surface** in production images
- **Regular base image updates** via automated builds
- **Vulnerability scanning** via GitHub security features

## Registry Management

### Viewing Packages

Visit the GitHub Container Registry page:
https://github.com/SCSIExpress/pacsync/pkgs/container/pacman-sync-server

### Package Permissions

- **Public packages** - Anyone can pull
- **Private packages** - Require authentication
- **Write access** - Limited to repository maintainers

### Retention Policies

- **Latest tags** - Kept indefinitely
- **Development builds** - Cleaned up periodically
- **Version tags** - Kept permanently

## Troubleshooting

### Authentication Issues

```bash
# Check if logged in
docker info | grep -i registry

# Re-authenticate
./ghcr-login.sh

# Manual login test
echo "test" | docker login ghcr.io -u USERNAME --password-stdin
```

### Build Issues

```bash
# Clear Docker cache
docker builder prune -af

# Check Docker daemon
docker version
docker info

# Rebuild without cache
docker build --no-cache --target production -t test-image .
```

### Push Issues

```bash
# Check image exists locally
docker images ghcr.io/scsiexpress/pacman-sync-server

# Test push with verbose output
docker push ghcr.io/scsiexpress/pacman-sync-server:latest --verbose

# Check registry connectivity
curl -I https://ghcr.io/v2/
```

### Pull Issues

```bash
# Check if image exists
docker manifest inspect ghcr.io/scsiexpress/pacman-sync-server:latest

# Pull with specific platform
docker pull --platform linux/amd64 ghcr.io/scsiexpress/pacman-sync-server:latest

# Clear local cache
docker system prune -af
```

## Best Practices

### For Users
1. **Use specific tags** in production (not `latest`)
2. **Pin to versions** for reproducible deployments
3. **Update regularly** to get security fixes
4. **Use health checks** in container orchestration

### For Maintainers
1. **Tag releases** properly with semantic versioning
2. **Test images** before pushing to production
3. **Document changes** in release notes
4. **Monitor image sizes** and optimize when needed
5. **Keep base images updated** for security

### Security
1. **Scan images** for vulnerabilities regularly
2. **Use minimal base images** when possible
3. **Don't include secrets** in images
4. **Run as non-root** user
5. **Use read-only filesystems** when possible

## Integration Examples

### Kubernetes Deployment
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: pacman-sync-server
spec:
  replicas: 3
  selector:
    matchLabels:
      app: pacman-sync-server
  template:
    metadata:
      labels:
        app: pacman-sync-server
    spec:
      containers:
      - name: server
        image: ghcr.io/scsiexpress/pacman-sync-server:v1.0.0
        ports:
        - containerPort: 8080
        env:
        - name: DATABASE_TYPE
          value: "postgresql"
        - name: JWT_SECRET_KEY
          valueFrom:
            secretKeyRef:
              name: pacman-sync-secrets
              key: jwt-secret
```

### Docker Swarm Service
```bash
docker service create \
  --name pacman-sync-server \
  --replicas 3 \
  --publish 8080:8080 \
  --env DATABASE_TYPE=internal \
  --env JWT_SECRET_KEY="$(openssl rand -hex 32)" \
  --mount type=volume,source=pacman-sync-data,target=/app/data \
  ghcr.io/scsiexpress/pacman-sync-server:latest
```

### Podman Usage
```bash
# Pull and run with Podman
podman pull ghcr.io/scsiexpress/pacman-sync-server:latest
podman run -d \
  --name pacman-sync-server \
  -p 8080:8080 \
  -e DATABASE_TYPE=internal \
  -e JWT_SECRET_KEY="$(openssl rand -hex 32)" \
  -v pacman-sync-data:/app/data \
  ghcr.io/scsiexpress/pacman-sync-server:latest
```