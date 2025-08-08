# Docker Deployment Guide

This guide covers deploying the Pacman Sync Utility server using Docker containers for production and development environments.

## Overview

The Pacman Sync Utility server is designed for containerized deployment with:
- **Multi-stage builds** for optimized production images
- **Environment variable configuration** for container orchestration
- **Health checks** for container monitoring
- **Volume mounts** for persistent data storage
- **Horizontal scaling** support with load balancing

## Quick Start

### Using Docker Compose (Recommended)

1. **Clone and Configure**
   ```bash
   git clone https://github.com/your-org/pacman-sync-utility.git
   cd pacman-sync-utility
   
   # Copy and customize docker-compose configuration
   cp docker-compose.yml.example docker-compose.yml
   nano docker-compose.yml
   ```

2. **Start Services**
   ```bash
   # Start with PostgreSQL database
   docker-compose up -d
   
   # Check status
   docker-compose ps
   
   # View logs
   docker-compose logs -f pacman-sync-server
   ```

3. **Verify Deployment**
   ```bash
   # Test health endpoint
   curl http://localhost:8080/health/live
   
   # Access web UI
   open http://localhost:8080
   ```

### Using Docker CLI

```bash
# Build the image
docker build -t pacman-sync-server .

# Run with internal database
docker run -d \
  --name pacman-sync-server \
  -p 8080:8080 \
  -e DATABASE_TYPE=internal \
  -e JWT_SECRET_KEY="$(openssl rand -hex 32)" \
  -v pacman-sync-data:/app/data \
  pacman-sync-server

# Run with PostgreSQL
docker run -d \
  --name pacman-sync-server \
  -p 8080:8080 \
  -e DATABASE_TYPE=postgresql \
  -e DATABASE_URL="postgresql://user:pass@postgres:5432/db" \
  -e JWT_SECRET_KEY="$(openssl rand -hex 32)" \
  --link postgres:postgres \
  pacman-sync-server
```

## Docker Configuration

### Dockerfile

The project includes a multi-stage Dockerfile optimized for production:

```dockerfile
# Build stage
FROM python:3.11-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt server-requirements.txt ./
RUN pip install --no-cache-dir --user -r server-requirements.txt

# Production stage
FROM python:3.11-slim

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create application user
RUN useradd --create-home --shell /bin/bash pacman-sync

# Copy Python packages from builder
COPY --from=builder /root/.local /home/pacman-sync/.local

# Copy application code
WORKDIR /app
COPY server/ ./server/
COPY shared/ ./shared/
COPY config/ ./config/

# Set ownership and permissions
RUN chown -R pacman-sync:pacman-sync /app
USER pacman-sync

# Add local packages to PATH
ENV PATH=/home/pacman-sync/.local/bin:$PATH

# Configuration
ENV DATABASE_TYPE=internal
ENV HTTP_PORT=8080
ENV LOG_LEVEL=INFO

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8080/health/live || exit 1

# Expose port
EXPOSE 8080

# Start server
CMD ["python", "-m", "server.main"]
```

### Environment Variables

#### Database Configuration
```bash
# Database type: 'postgresql' or 'internal'
DATABASE_TYPE=postgresql

# PostgreSQL connection (when DATABASE_TYPE=postgresql)
DATABASE_URL=postgresql://username:password@host:5432/database

# Internal database file path (when DATABASE_TYPE=internal)
DATABASE_FILE=/app/data/database.db

# Connection pool settings
DATABASE_POOL_SIZE=10
DATABASE_MAX_OVERFLOW=20
DATABASE_POOL_TIMEOUT=30
```

#### Server Configuration
```bash
# Server settings
HTTP_HOST=0.0.0.0
HTTP_PORT=8080
SERVER_DEBUG=false
SERVER_WORKERS=4

# Security
JWT_SECRET_KEY=your-secret-key-here
TOKEN_EXPIRY=24
API_RATE_LIMIT=100

# Features
ENABLE_REPOSITORY_ANALYSIS=true
AUTO_CLEANUP_OLD_STATES=true
MAX_STATE_HISTORY=50
```

#### Logging Configuration
```bash
# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json
LOG_FILE=  # Empty for stdout

# Web UI
WEB_UI_ENABLED=true
WEB_UI_TITLE="Pacman Sync Utility"
```

## Docker Compose Configurations

### Production Configuration

```yaml
# docker-compose.yml
version: '3.8'

services:
  pacman-sync-server:
    build: .
    container_name: pacman-sync-server
    restart: unless-stopped
    ports:
      - "8080:8080"
    environment:
      - DATABASE_TYPE=postgresql
      - DATABASE_URL=postgresql://pacman_sync:${DB_PASSWORD}@postgres:5432/pacman_sync_db
      - JWT_SECRET_KEY=${JWT_SECRET_KEY}
      - LOG_LEVEL=INFO
      - ENABLE_REPOSITORY_ANALYSIS=true
      - AUTO_CLEANUP_OLD_STATES=true
    volumes:
      - pacman-sync-logs:/app/logs
    depends_on:
      postgres:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health/live"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    networks:
      - pacman-sync-network

  postgres:
    image: postgres:15-alpine
    container_name: pacman-sync-postgres
    restart: unless-stopped
    environment:
      - POSTGRES_DB=pacman_sync_db
      - POSTGRES_USER=pacman_sync
      - POSTGRES_PASSWORD=${DB_PASSWORD}
    volumes:
      - postgres-data:/var/lib/postgresql/data
      - ./init-db.sql:/docker-entrypoint-initdb.d/init-db.sql:ro
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U pacman_sync -d pacman_sync_db"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - pacman-sync-network

  nginx:
    image: nginx:alpine
    container_name: pacman-sync-nginx
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/nginx/ssl:ro
    depends_on:
      - pacman-sync-server
    networks:
      - pacman-sync-network

volumes:
  postgres-data:
  pacman-sync-logs:

networks:
  pacman-sync-network:
    driver: bridge
```

### Development Configuration

```yaml
# docker-compose.dev.yml
version: '3.8'

services:
  pacman-sync-server:
    build:
      context: .
      target: builder  # Use builder stage for development
    container_name: pacman-sync-server-dev
    ports:
      - "8080:8080"
    environment:
      - DATABASE_TYPE=internal
      - DATABASE_FILE=/app/data/dev-database.db
      - JWT_SECRET_KEY=dev-secret-key-not-for-production
      - LOG_LEVEL=DEBUG
      - SERVER_DEBUG=true
    volumes:
      - .:/app:ro  # Mount source code for development
      - dev-data:/app/data
    command: ["python", "-m", "server.main", "--reload"]
    networks:
      - pacman-sync-dev

volumes:
  dev-data:

networks:
  pacman-sync-dev:
    driver: bridge
```

### Environment File

Create a `.env` file for sensitive configuration:

```bash
# .env
DB_PASSWORD=secure-database-password
JWT_SECRET_KEY=your-jwt-secret-key-32-characters-long
API_RATE_LIMIT=100
LOG_LEVEL=INFO
```

## Production Deployment

### SSL/TLS Configuration

#### Nginx Reverse Proxy

```nginx
# nginx.conf
events {
    worker_connections 1024;
}

http {
    upstream pacman-sync-backend {
        server pacman-sync-server:8080;
        # Add more servers for load balancing
        # server pacman-sync-server-2:8080;
    }

    server {
        listen 80;
        server_name your-domain.com;
        return 301 https://$server_name$request_uri;
    }

    server {
        listen 443 ssl http2;
        server_name your-domain.com;

        ssl_certificate /etc/nginx/ssl/cert.pem;
        ssl_certificate_key /etc/nginx/ssl/key.pem;
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512;

        location / {
            proxy_pass http://pacman-sync-backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            
            # WebSocket support
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
        }

        location /health {
            proxy_pass http://pacman-sync-backend/health;
            access_log off;
        }
    }
}
```

#### Let's Encrypt SSL

```bash
# Install certbot
sudo apt-get install certbot python3-certbot-nginx

# Generate certificate
sudo certbot --nginx -d your-domain.com

# Auto-renewal
sudo crontab -e
# Add: 0 12 * * * /usr/bin/certbot renew --quiet
```

### Database Initialization

```sql
-- init-db.sql
-- Database initialization script

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";

-- Create indexes for performance
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_endpoints_pool_id ON endpoints(pool_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_package_states_pool_id ON package_states(pool_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_sync_operations_created_at ON sync_operations(created_at);

-- Set up monitoring user (optional)
CREATE USER monitoring WITH PASSWORD 'monitoring-password';
GRANT CONNECT ON DATABASE pacman_sync_db TO monitoring;
GRANT USAGE ON SCHEMA public TO monitoring;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO monitoring;
```

### Scaling Configuration

#### Horizontal Scaling

```yaml
# docker-compose.scale.yml
version: '3.8'

services:
  pacman-sync-server:
    build: .
    environment:
      - DATABASE_TYPE=postgresql
      - DATABASE_URL=postgresql://pacman_sync:${DB_PASSWORD}@postgres:5432/pacman_sync_db
      - JWT_SECRET_KEY=${JWT_SECRET_KEY}
    depends_on:
      - postgres
      - redis
    networks:
      - pacman-sync-network

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx-lb.conf:/etc/nginx/nginx.conf:ro
    depends_on:
      - pacman-sync-server
    networks:
      - pacman-sync-network

  postgres:
    image: postgres:15-alpine
    environment:
      - POSTGRES_DB=pacman_sync_db
      - POSTGRES_USER=pacman_sync
      - POSTGRES_PASSWORD=${DB_PASSWORD}
    volumes:
      - postgres-data:/var/lib/postgresql/data
    networks:
      - pacman-sync-network

  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes
    volumes:
      - redis-data:/data
    networks:
      - pacman-sync-network

volumes:
  postgres-data:
  redis-data:

networks:
  pacman-sync-network:
    driver: bridge
```

#### Load Balancer Configuration

```nginx
# nginx-lb.conf
upstream pacman-sync-backend {
    least_conn;
    server pacman-sync-server_1:8080 max_fails=3 fail_timeout=30s;
    server pacman-sync-server_2:8080 max_fails=3 fail_timeout=30s;
    server pacman-sync-server_3:8080 max_fails=3 fail_timeout=30s;
}

server {
    listen 80;
    
    location / {
        proxy_pass http://pacman-sync-backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        
        # Health check
        proxy_next_upstream error timeout invalid_header http_500 http_502 http_503;
        proxy_connect_timeout 5s;
        proxy_send_timeout 10s;
        proxy_read_timeout 10s;
    }
}
```

#### Scaling Commands

```bash
# Scale up to 3 instances
docker-compose -f docker-compose.scale.yml up -d --scale pacman-sync-server=3

# Scale down to 1 instance
docker-compose -f docker-compose.scale.yml up -d --scale pacman-sync-server=1

# Check running instances
docker-compose ps
```

## Kubernetes Deployment

### Basic Deployment

```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: pacman-sync-server
  labels:
    app: pacman-sync-server
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
      - name: pacman-sync-server
        image: pacman-sync-server:latest
        ports:
        - containerPort: 8080
        env:
        - name: DATABASE_TYPE
          value: "postgresql"
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: pacman-sync-secrets
              key: database-url
        - name: JWT_SECRET_KEY
          valueFrom:
            secretKeyRef:
              name: pacman-sync-secrets
              key: jwt-secret
        livenessProbe:
          httpGet:
            path: /health/live
            port: 8080
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health/ready
            port: 8080
          initialDelaySeconds: 5
          periodSeconds: 5
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"

---
apiVersion: v1
kind: Service
metadata:
  name: pacman-sync-service
spec:
  selector:
    app: pacman-sync-server
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8080
  type: LoadBalancer

---
apiVersion: v1
kind: Secret
metadata:
  name: pacman-sync-secrets
type: Opaque
data:
  database-url: <base64-encoded-database-url>
  jwt-secret: <base64-encoded-jwt-secret>
```

### Ingress Configuration

```yaml
# k8s/ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: pacman-sync-ingress
  annotations:
    kubernetes.io/ingress.class: nginx
    cert-manager.io/cluster-issuer: letsencrypt-prod
    nginx.ingress.kubernetes.io/proxy-body-size: "50m"
spec:
  tls:
  - hosts:
    - pacman-sync.your-domain.com
    secretName: pacman-sync-tls
  rules:
  - host: pacman-sync.your-domain.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: pacman-sync-service
            port:
              number: 80
```

## Monitoring and Logging

### Prometheus Monitoring

```yaml
# docker-compose.monitoring.yml
version: '3.8'

services:
  prometheus:
    image: prom/prometheus:latest
    container_name: prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - prometheus-data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--web.console.libraries=/etc/prometheus/console_libraries'
      - '--web.console.templates=/etc/prometheus/consoles'
    networks:
      - monitoring

  grafana:
    image: grafana/grafana:latest
    container_name: grafana
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    volumes:
      - grafana-data:/var/lib/grafana
      - ./grafana/dashboards:/etc/grafana/provisioning/dashboards:ro
      - ./grafana/datasources:/etc/grafana/provisioning/datasources:ro
    networks:
      - monitoring

volumes:
  prometheus-data:
  grafana-data:

networks:
  monitoring:
    driver: bridge
```

### Centralized Logging

```yaml
# docker-compose.logging.yml
version: '3.8'

services:
  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.5.0
    container_name: elasticsearch
    environment:
      - discovery.type=single-node
      - "ES_JAVA_OPTS=-Xms512m -Xmx512m"
      - xpack.security.enabled=false
    volumes:
      - elasticsearch-data:/usr/share/elasticsearch/data
    networks:
      - logging

  logstash:
    image: docker.elastic.co/logstash/logstash:8.5.0
    container_name: logstash
    volumes:
      - ./logstash.conf:/usr/share/logstash/pipeline/logstash.conf:ro
    depends_on:
      - elasticsearch
    networks:
      - logging

  kibana:
    image: docker.elastic.co/kibana/kibana:8.5.0
    container_name: kibana
    ports:
      - "5601:5601"
    environment:
      - ELASTICSEARCH_HOSTS=http://elasticsearch:9200
    depends_on:
      - elasticsearch
    networks:
      - logging

volumes:
  elasticsearch-data:

networks:
  logging:
    driver: bridge
```

## Backup and Recovery

### Database Backup

```bash
#!/bin/bash
# backup-database.sh

BACKUP_DIR="/backup/pacman-sync"
DATE=$(date +%Y%m%d_%H%M%S)
CONTAINER_NAME="pacman-sync-postgres"

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Backup database
docker exec "$CONTAINER_NAME" pg_dump -U pacman_sync pacman_sync_db | gzip > "$BACKUP_DIR/backup_$DATE.sql.gz"

# Clean old backups (keep 30 days)
find "$BACKUP_DIR" -name "backup_*.sql.gz" -mtime +30 -delete

echo "Backup completed: backup_$DATE.sql.gz"
```

### Volume Backup

```bash
#!/bin/bash
# backup-volumes.sh

BACKUP_DIR="/backup/pacman-sync-volumes"
DATE=$(date +%Y%m%d_%H%M%S)

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Backup Docker volumes
docker run --rm \
  -v pacman-sync_postgres-data:/data:ro \
  -v "$BACKUP_DIR":/backup \
  alpine tar czf "/backup/postgres-data_$DATE.tar.gz" -C /data .

docker run --rm \
  -v pacman-sync_pacman-sync-logs:/data:ro \
  -v "$BACKUP_DIR":/backup \
  alpine tar czf "/backup/logs_$DATE.tar.gz" -C /data .

echo "Volume backup completed"
```

### Automated Backup

```bash
# Add to crontab
0 2 * * * /usr/local/bin/backup-database.sh
0 3 * * 0 /usr/local/bin/backup-volumes.sh
```

## Troubleshooting Docker Deployment

### Common Issues

#### Container Won't Start

```bash
# Check container logs
docker logs pacman-sync-server

# Check container status
docker ps -a

# Inspect container configuration
docker inspect pacman-sync-server
```

#### Database Connection Issues

```bash
# Test database connectivity
docker exec pacman-sync-server python -c "
import os
from server.database.connection import test_connection
print('Database connection:', test_connection())
"

# Check database container
docker logs pacman-sync-postgres
docker exec pacman-sync-postgres pg_isready -U pacman_sync
```

#### Performance Issues

```bash
# Monitor resource usage
docker stats

# Check container resource limits
docker inspect pacman-sync-server | grep -A 10 "Resources"

# Scale up resources
docker-compose up -d --scale pacman-sync-server=3
```

### Health Checks

```bash
# Manual health check
curl http://localhost:8080/health/live
curl http://localhost:8080/health/ready

# Docker health check status
docker inspect --format='{{.State.Health.Status}}' pacman-sync-server

# View health check logs
docker inspect --format='{{range .State.Health.Log}}{{.Output}}{{end}}' pacman-sync-server
```

## Security Considerations

### Container Security

```dockerfile
# Security-hardened Dockerfile
FROM python:3.11-slim

# Create non-root user
RUN groupadd -r pacman-sync && useradd -r -g pacman-sync pacman-sync

# Install security updates
RUN apt-get update && apt-get upgrade -y && rm -rf /var/lib/apt/lists/*

# Set secure permissions
COPY --chown=pacman-sync:pacman-sync . /app
WORKDIR /app
USER pacman-sync

# Drop capabilities
USER 1000:1000
```

### Network Security

```yaml
# docker-compose.security.yml
version: '3.8'

services:
  pacman-sync-server:
    build: .
    networks:
      - internal
    # Don't expose ports directly
    # ports:
    #   - "8080:8080"

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    networks:
      - internal
      - external

networks:
  internal:
    driver: bridge
    internal: true
  external:
    driver: bridge
```

### Secrets Management

```bash
# Use Docker secrets
echo "your-jwt-secret" | docker secret create jwt_secret -
echo "postgresql://user:pass@host/db" | docker secret create db_url -

# Reference in compose file
services:
  pacman-sync-server:
    secrets:
      - jwt_secret
      - db_url
    environment:
      - JWT_SECRET_KEY_FILE=/run/secrets/jwt_secret
      - DATABASE_URL_FILE=/run/secrets/db_url

secrets:
  jwt_secret:
    external: true
  db_url:
    external: true
```

## Next Steps

After successful Docker deployment:

1. Set up [Monitoring and Alerting](troubleshooting.md#monitoring)
2. Configure [Client Connections](desktop-client-guide.md)
3. Review [API Documentation](api-documentation.md) for integration
4. Implement [Backup Strategies](#backup-and-recovery)
5. Plan [Scaling Strategy](#scaling-configuration) for growth