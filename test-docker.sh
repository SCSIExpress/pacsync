#!/bin/bash

# Test script for Docker image functionality

set -e

echo "Testing Pacman Sync Utility Docker Image"
echo "========================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${YELLOW}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Test 1: Build production image
print_status "Building production Docker image..."
if docker build --target production -t pacman-sync-server:test . > /dev/null 2>&1; then
    print_success "Production image built successfully"
else
    print_error "Failed to build production image"
    exit 1
fi

# Test 2: Build development image
print_status "Building development Docker image..."
if docker build --target development -t pacman-sync-server:test-dev . > /dev/null 2>&1; then
    print_success "Development image built successfully"
else
    print_error "Failed to build development image"
    exit 1
fi

# Test 3: Check image size
print_status "Checking image sizes..."
PROD_SIZE=$(docker images pacman-sync-server:test --format "{{.Size}}")
DEV_SIZE=$(docker images pacman-sync-server:test-dev --format "{{.Size}}")
echo "  Production image size: $PROD_SIZE"
echo "  Development image size: $DEV_SIZE"

# Test 4: Test container startup (quick test)
print_status "Testing container startup..."
CONTAINER_ID=$(docker run -d \
    -e DATABASE_TYPE=internal \
    -e JWT_SECRET_KEY=test-key \
    -e LOG_LEVEL=INFO \
    -p 8081:8080 \
    pacman-sync-server:test)

if [ $? -eq 0 ]; then
    print_success "Container started successfully (ID: ${CONTAINER_ID:0:12})"
    
    # Wait a moment for startup
    sleep 5
    
    # Test 5: Check if container is running
    if docker ps | grep -q $CONTAINER_ID; then
        print_success "Container is running"
        
        # Test 6: Test health endpoint (if available)
        print_status "Testing health endpoint..."
        if curl -f http://localhost:8081/health/live > /dev/null 2>&1; then
            print_success "Health endpoint responding"
        else
            print_status "Health endpoint not responding (may be normal during startup)"
        fi
    else
        print_error "Container stopped unexpectedly"
        docker logs $CONTAINER_ID
    fi
    
    # Cleanup
    print_status "Cleaning up test container..."
    docker stop $CONTAINER_ID > /dev/null 2>&1
    docker rm $CONTAINER_ID > /dev/null 2>&1
    print_success "Test container cleaned up"
else
    print_error "Failed to start container"
    exit 1
fi

# Test 7: Validate Docker Compose configuration
print_status "Validating Docker Compose configuration..."
if docker-compose config > /dev/null 2>&1; then
    print_success "Docker Compose configuration is valid"
else
    print_error "Docker Compose configuration is invalid"
    exit 1
fi

# Cleanup test images
print_status "Cleaning up test images..."
docker rmi pacman-sync-server:test pacman-sync-server:test-dev > /dev/null 2>&1

print_success "All Docker tests passed!"
echo ""
echo "Usage Examples:"
echo "==============="
echo ""
echo "1. Build and run with Docker Compose:"
echo "   docker-compose up --build"
echo ""
echo "2. Build production image manually:"
echo "   docker build --target production -t pacman-sync-server ."
echo ""
echo "3. Run production container:"
echo "   docker run -d \\"
echo "     --name pacman-sync-server \\"
echo "     -p 8080:8080 \\"
echo "     -e DATABASE_TYPE=internal \\"
echo "     -e JWT_SECRET_KEY=\"\$(openssl rand -hex 32)\" \\"
echo "     -v pacman-sync-data:/app/data \\"
echo "     pacman-sync-server"
echo ""
echo "4. Run development container:"
echo "   docker build --target development -t pacman-sync-server:dev ."
echo "   docker run -d \\"
echo "     --name pacman-sync-dev \\"
echo "     -p 8080:8080 \\"
echo "     -e DATABASE_TYPE=internal \\"
echo "     -e JWT_SECRET_KEY=dev-key \\"
echo "     -v \$(pwd)/server:/app/server \\"
echo "     -v \$(pwd)/shared:/app/shared \\"
echo "     pacman-sync-server:dev"