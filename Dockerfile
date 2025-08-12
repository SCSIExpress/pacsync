# Multi-stage Dockerfile for Pacman Sync Utility Server
# Based on Ubuntu for familiarity and compatibility

# Base stage with common dependencies
FROM ubuntu:22.04 as base

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PIP_NO_CACHE_DIR=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1
ENV PYTHONPATH=/app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    curl \
    wget \
    git \
    build-essential \
    pkg-config \
    libssl-dev \
    libffi-dev \
    libpq-dev \
    sqlite3 \
    && rm -rf /var/lib/apt/lists/*

# Create application user and directory
RUN useradd --create-home --shell /bin/bash --uid 1000 pacman-sync
WORKDIR /app
RUN chown -R pacman-sync:pacman-sync /app

# Create virtual environment
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Upgrade pip and install wheel
RUN pip install --upgrade pip setuptools wheel

# Development stage
FROM base as development

# Install development dependencies
RUN apt-get update && apt-get install -y \
    vim \
    less \
    htop \
    strace \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt server-requirements.txt ./

# Install Python dependencies including development tools
RUN pip install -r requirements.txt -r server-requirements.txt && \
    pip install pytest pytest-asyncio pytest-mock black flake8 mypy

# Copy source code
COPY --chown=pacman-sync:pacman-sync . .

# Create necessary directories
RUN mkdir -p /app/data /app/logs /app/config && \
    chown -R pacman-sync:pacman-sync /app/data /app/logs /app/config

# Switch to application user
USER pacman-sync

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8080/health/ready || exit 1

# Development command with hot reload
CMD ["python3", "start-dev.py"]

# Production build stage
FROM base as builder

# Copy requirements
COPY requirements.txt server-requirements.txt ./

# Install production dependencies only
RUN pip install -r server-requirements.txt

# Copy source code
COPY . .

# Remove development files and clean up
RUN find . -type d -name "__pycache__" -exec rm -rf {} + && \
    find . -type f -name "*.pyc" -delete && \
    rm -rf .git .pytest_cache tests/ *.md

# Production stage
FROM ubuntu:22.04 as production

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PATH="/opt/venv/bin:$PATH"
ENV PYTHONPATH=/app

# Install minimal runtime dependencies
RUN apt-get update && apt-get install -y \
    python3 \
    curl \
    libpq5 \
    sqlite3 \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create application user
RUN useradd --create-home --shell /bin/bash --uid 1000 pacman-sync

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Copy application code from builder
COPY --from=builder --chown=pacman-sync:pacman-sync /app /app

# Set working directory
WORKDIR /app

# Create necessary directories with proper permissions
RUN mkdir -p /app/data /app/logs /app/config && \
    chown -R pacman-sync:pacman-sync /app

# Switch to application user
USER pacman-sync

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8080/health/ready || exit 1

# Production command
CMD ["python3", "start-prod.py"]