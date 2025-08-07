# Multi-stage build for Pacman Sync Utility Server
FROM node:18-alpine as web-builder

# Build web UI
WORKDIR /app/web
COPY server/web/package*.json ./
RUN npm ci --only=production

COPY server/web/ ./
RUN npm run build

# Base Python image with common dependencies
FROM python:3.11-slim as base

# Set environment variables for Python
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PIP_NO_CACHE_DIR=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    sqlite3 \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create app user for security
RUN groupadd -r appuser && useradd -r -g appuser -d /app -s /bin/bash appuser

# Set working directory
WORKDIR /app

# Create directories for persistent data with proper permissions
RUN mkdir -p /app/data /app/logs /app/config \
    && chown -R appuser:appuser /app

# Copy server requirements
COPY server-requirements.txt ./requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Development stage
FROM base as development

# Install development dependencies
RUN pip install --no-cache-dir \
    pytest>=7.0.0 \
    pytest-asyncio>=0.21.0 \
    pytest-mock>=3.10.0 \
    black>=23.0.0 \
    flake8>=6.0.0 \
    mypy>=1.0.0 \
    uvicorn[standard]>=0.20.0

# Install additional development tools
RUN apt-get update && apt-get install -y \
    git \
    vim \
    nano \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy application code
COPY server/ ./server/
COPY shared/ ./shared/

# Copy built web UI from web-builder stage
COPY --from=web-builder /app/web/dist ./server/web/dist

# Change ownership to app user
RUN chown -R appuser:appuser /app

# Switch to app user
USER appuser

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${HTTP_PORT:-8080}/health || exit 1

# Default environment variables for development
ENV DATABASE_TYPE=internal
ENV HTTP_PORT=8080
ENV HTTP_HOST=0.0.0.0
ENV LOG_LEVEL=DEBUG
ENV ENVIRONMENT=development

# Volume mounts for persistent data
VOLUME ["/app/data", "/app/logs", "/app/config"]

# Development command with auto-reload
CMD ["python", "-m", "uvicorn", "server.api.main:app", "--host", "0.0.0.0", "--port", "8080", "--reload"]

# Production stage
FROM base as production

# Production-specific optimizations
ENV PYTHONOPTIMIZE=1
ENV ENVIRONMENT=production

# Install production WSGI server
RUN pip install --no-cache-dir \
    gunicorn>=20.1.0 \
    uvicorn[standard]>=0.20.0

# Copy application code
COPY server/ ./server/
COPY shared/ ./shared/

# Copy built web UI from web-builder stage
COPY --from=web-builder /app/web/dist ./server/web/dist

# Change ownership to app user
RUN chown -R appuser:appuser /app

# Switch to app user
USER appuser

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${HTTP_PORT:-8080}/health || exit 1

# Default environment variables for production
ENV DATABASE_TYPE=internal
ENV HTTP_PORT=8080
ENV HTTP_HOST=0.0.0.0
ENV LOG_LEVEL=INFO
ENV ENVIRONMENT=production

# Volume mounts for persistent data
VOLUME ["/app/data", "/app/logs", "/app/config"]

# Production command with gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "4", "--worker-class", "uvicorn.workers.UvicornWorker", "--access-logfile", "/app/logs/access.log", "--error-logfile", "/app/logs/error.log", "server.api.main:app"]