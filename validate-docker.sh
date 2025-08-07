#!/bin/bash

# Docker Configuration Validation Script for Pacman Sync Utility
# This script validates the Docker container configuration and deployment

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to validate Docker prerequisites
validate_prerequisites() {
    print_info "Validating Docker prerequisites..."
    
    if ! command_exists docker; then
        print_error "Docker is not installed or not in PATH"
        return 1
    fi
    
    if ! command_exists docker-compose; then
        print_error "Docker Compose is not installed or not in PATH"
        return 1
    fi
    
    # Check Docker daemon is running
    if ! docker info >/dev/null 2>&1; then
        print_error "Docker daemon is not running"
        return 1
    fi
    
    print_success "Docker prerequisites validated"
    return 0
}

# Function to validate Dockerfile
validate_dockerfile() {
    print_info "Validating Dockerfile..."
    
    if [ ! -f "Dockerfile" ]; then
        print_error "Dockerfile not found"
        return 1
    fi
    
    # Check for multi-stage build
    if ! grep -q "FROM.*as.*" Dockerfile; then
        print_error "Multi-stage build not found in Dockerfile"
        return 1
    fi
    
    # Check for production and development stages
    if ! grep -q "FROM.*as production" Dockerfile; then
        print_error "Production stage not found in Dockerfile"
        return 1
    fi
    
    if ! grep -q "FROM.*as development" Dockerfile; then
        print_error "Development stage not found in Dockerfile"
        return 1
    fi
    
    # Check for web builder stage
    if ! grep -q "FROM.*as web-builder" Dockerfile; then
        print_error "Web builder stage not found in Dockerfile"
        return 1
    fi
    
    # Check for security best practices
    if ! grep -q "USER appuser" Dockerfile; then
        print_error "Non-root user not configured in Dockerfile"
        return 1
    fi
    
    # Check for health check
    if ! grep -q "HEALTHCHECK" Dockerfile; then
        print_error "Health check not configured in Dockerfile"
        return 1
    fi
    
    # Check for volume mounts
    if ! grep -q "VOLUME" Dockerfile; then
        print_error "Volume mounts not configured in Dockerfile"
        return 1
    fi
    
    print_success "Dockerfile validation passed"
    return 0
}

# Function to validate docker-compose configuration
validate_docker_compose() {
    print_info "Validating docker-compose.yml..."
    
    if [ ! -f "docker-compose.yml" ]; then
        print_error "docker-compose.yml not found"
        return 1
    fi
    
    # Validate docker-compose syntax
    if ! docker-compose config >/dev/null 2>&1; then
        print_error "docker-compose.yml syntax validation failed"
        return 1
    fi
    
    # Check for required services
    if ! docker-compose config | grep -q "pacman-sync-server:"; then
        print_error "pacman-sync-server service not found"
        return 1
    fi
    
    if ! docker-compose config | grep -q "postgres:"; then
        print_error "postgres service not found"
        return 1
    fi
    
    if ! docker-compose config | grep -q "pacman-sync-dev:"; then
        print_error "pacman-sync-dev service not found"
        return 1
    fi
    
    # Check for volume definitions
    if ! docker-compose config | grep -q "volumes:"; then
        print_error "Named volumes not configured"
        return 1
    fi
    
    # Check for network configuration
    if ! docker-compose config | grep -q "networks:"; then
        print_error "Network configuration not found"
        return 1
    fi
    
    print_success "docker-compose.yml validation passed"
    return 0
}

# Function to validate environment configuration
validate_environment() {
    print_info "Validating environment configuration..."
    
    if [ ! -f ".env.example" ]; then
        print_error ".env.example not found"
        return 1
    fi
    
    # Check for required environment variables
    required_vars=(
        "DATABASE_TYPE"
        "HTTP_PORT"
        "HTTP_HOST"
        "LOG_LEVEL"
        "ENVIRONMENT"
        "JWT_SECRET_KEY"
        "API_RATE_LIMIT"
    )
    
    for var in "${required_vars[@]}"; do
        if ! grep -q "^$var=" .env.example; then
            print_error "Required environment variable $var not found in .env.example"
            return 1
        fi
    done
    
    print_success "Environment configuration validation passed"
    return 0
}

# Function to test Docker build
test_docker_build() {
    print_info "Testing Docker build process..."
    
    # Test production build
    print_info "Building production image..."
    if ! docker build --target production -t pacman-sync-test:production . >/dev/null 2>&1; then
        print_error "Production Docker build failed"
        return 1
    fi
    
    # Test development build
    print_info "Building development image..."
    if ! docker build --target development -t pacman-sync-test:development . >/dev/null 2>&1; then
        print_error "Development Docker build failed"
        return 1
    fi
    
    print_success "Docker build tests passed"
    return 0
}

# Function to test container startup
test_container_startup() {
    print_info "Testing container startup..."
    
    # Create temporary .env file for testing
    cat > .env.test << EOF
DATABASE_TYPE=internal
HTTP_PORT=8081
HTTP_HOST=0.0.0.0
LOG_LEVEL=INFO
ENVIRONMENT=production
JWT_SECRET_KEY=test-secret-key
API_RATE_LIMIT=100
EOF
    
    # Start container with test configuration
    print_info "Starting test container..."
    if ! docker run -d --name pacman-sync-test \
        --env-file .env.test \
        -p 8081:8081 \
        pacman-sync-test:production >/dev/null 2>&1; then
        print_error "Container startup failed"
        cleanup_test_resources
        return 1
    fi
    
    # Wait for container to be ready
    print_info "Waiting for container to be ready..."
    sleep 10
    
    # Test health check endpoint
    if ! curl -f -s http://localhost:8081/health >/dev/null 2>&1; then
        print_error "Health check endpoint failed"
        cleanup_test_resources
        return 1
    fi
    
    print_success "Container startup test passed"
    cleanup_test_resources
    return 0
}

# Function to test volume mounts
test_volume_mounts() {
    print_info "Testing volume mounts..."
    
    # Create test directories
    mkdir -p test-data test-logs test-config
    
    # Start container with volume mounts
    if ! docker run -d --name pacman-sync-volume-test \
        -v "$(pwd)/test-data:/app/data" \
        -v "$(pwd)/test-logs:/app/logs" \
        -v "$(pwd)/test-config:/app/config" \
        -e DATABASE_TYPE=internal \
        -e HTTP_PORT=8082 \
        -p 8082:8082 \
        pacman-sync-test:production >/dev/null 2>&1; then
        print_error "Volume mount test failed"
        cleanup_test_resources
        return 1
    fi
    
    sleep 5
    
    # Check if volumes are accessible
    if ! docker exec pacman-sync-volume-test ls /app/data >/dev/null 2>&1; then
        print_error "Data volume not accessible"
        cleanup_test_resources
        return 1
    fi
    
    print_success "Volume mount test passed"
    cleanup_test_resources
    return 0
}

# Function to cleanup test resources
cleanup_test_resources() {
    print_info "Cleaning up test resources..."
    
    # Stop and remove test containers
    docker stop pacman-sync-test >/dev/null 2>&1 || true
    docker rm pacman-sync-test >/dev/null 2>&1 || true
    docker stop pacman-sync-volume-test >/dev/null 2>&1 || true
    docker rm pacman-sync-volume-test >/dev/null 2>&1 || true
    
    # Remove test images
    docker rmi pacman-sync-test:production >/dev/null 2>&1 || true
    docker rmi pacman-sync-test:development >/dev/null 2>&1 || true
    
    # Remove test files and directories
    rm -f .env.test
    rm -rf test-data test-logs test-config
    
    print_info "Test cleanup completed"
}

# Function to validate deployment scripts
validate_deployment_scripts() {
    print_info "Validating deployment scripts..."
    
    if [ ! -f "deploy.sh" ]; then
        print_error "deploy.sh not found"
        return 1
    fi
    
    if [ ! -x "deploy.sh" ]; then
        print_error "deploy.sh is not executable"
        return 1
    fi
    
    if [ ! -f "healthcheck.sh" ]; then
        print_error "healthcheck.sh not found"
        return 1
    fi
    
    if [ ! -x "healthcheck.sh" ]; then
        print_error "healthcheck.sh is not executable"
        return 1
    fi
    
    print_success "Deployment scripts validation passed"
    return 0
}

# Main validation function
main() {
    print_info "Starting Docker configuration validation..."
    
    local exit_code=0
    
    # Run all validation tests
    validate_prerequisites || exit_code=1
    validate_dockerfile || exit_code=1
    validate_docker_compose || exit_code=1
    validate_environment || exit_code=1
    validate_deployment_scripts || exit_code=1
    
    # Run build and runtime tests if basic validation passed
    if [ $exit_code -eq 0 ]; then
        test_docker_build || exit_code=1
        test_container_startup || exit_code=1
        test_volume_mounts || exit_code=1
    fi
    
    # Final cleanup
    cleanup_test_resources
    
    if [ $exit_code -eq 0 ]; then
        print_success "All Docker configuration validations passed!"
        print_info "Docker container configuration is ready for deployment"
    else
        print_error "Docker configuration validation failed"
        print_info "Please fix the issues above before deployment"
    fi
    
    exit $exit_code
}

# Handle script interruption
trap cleanup_test_resources EXIT INT TERM

# Run main function
main "$@"