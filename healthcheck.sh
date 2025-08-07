#!/bin/bash

# Health check script for Pacman Sync Utility Server
# This script is used by Docker to check if the server is healthy

set -e

# Configuration
HEALTH_ENDPOINT="http://localhost:${HTTP_PORT:-8080}/health"
TIMEOUT=10
MAX_RETRIES=3

# Function to check server health
check_health() {
    local retry_count=0
    
    while [ $retry_count -lt $MAX_RETRIES ]; do
        if curl -f -s --max-time $TIMEOUT "$HEALTH_ENDPOINT" > /dev/null 2>&1; then
            echo "Health check passed"
            return 0
        fi
        
        retry_count=$((retry_count + 1))
        echo "Health check attempt $retry_count failed, retrying..."
        sleep 2
    done
    
    echo "Health check failed after $MAX_RETRIES attempts"
    return 1
}

# Run health check
check_health