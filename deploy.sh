#!/bin/bash

# Pacman Sync Utility - Docker Deployment Script
# This script provides easy deployment options for the Pacman Sync Utility server

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
ENVIRONMENT="production"
DATABASE_TYPE="internal"
HTTP_PORT="8080"
BUILD_TARGET="production"

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

# Function to show usage
show_usage() {
    cat << EOF
Usage: $0 [OPTIONS] COMMAND

Commands:
    build       Build Docker images
    start       Start the services
    stop        Stop the services
    restart     Restart the services
    logs        Show service logs
    status      Show service status
    clean       Clean up containers and images
    dev         Start development environment
    prod        Start production environment

Options:
    -e, --env ENV           Environment (development|production) [default: production]
    -d, --database TYPE     Database type (internal|postgresql) [default: internal]
    -p, --port PORT         HTTP port [default: 8080]
    -h, --help              Show this help message

Examples:
    $0 build                    # Build production images
    $0 start --env development  # Start development environment
    $0 prod --database postgresql --port 8080  # Start production with PostgreSQL
    $0 logs                     # Show logs
    $0 clean                    # Clean up everything

EOF
}

# Function to check prerequisites
check_prerequisites() {
    print_info "Checking prerequisites..."
    
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed or not in PATH"
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose is not installed or not in PATH"
        exit 1
    fi
    
    print_success "Prerequisites check passed"
}

# Function to create .env file if it doesn't exist
setup_env_file() {
    if [ ! -f .env ]; then
        print_info "Creating .env file from template..."
        cp .env.example .env
        print_warning "Please review and customize the .env file before deployment"
    fi
}

# Function to build images
build_images() {
    print_info "Building Docker images for $BUILD_TARGET environment..."
    
    docker-compose build --build-arg BUILDKIT_INLINE_CACHE=1 $BUILD_TARGET
    
    print_success "Docker images built successfully"
}

# Function to start services
start_services() {
    print_info "Starting Pacman Sync Utility services..."
    
    setup_env_file
    
    if [ "$ENVIRONMENT" = "development" ]; then
        docker-compose --profile dev up -d pacman-sync-dev
    else
        if [ "$DATABASE_TYPE" = "postgresql" ]; then
            docker-compose --profile postgres up -d postgres
            print_info "Waiting for PostgreSQL to be ready..."
            sleep 10
        fi
        docker-compose up -d pacman-sync-server
    fi
    
    print_success "Services started successfully"
    print_info "Server will be available at http://localhost:$HTTP_PORT"
}

# Function to stop services
stop_services() {
    print_info "Stopping Pacman Sync Utility services..."
    
    docker-compose down
    
    print_success "Services stopped successfully"
}

# Function to restart services
restart_services() {
    print_info "Restarting Pacman Sync Utility services..."
    
    stop_services
    start_services
    
    print_success "Services restarted successfully"
}

# Function to show logs
show_logs() {
    print_info "Showing service logs..."
    
    if [ "$ENVIRONMENT" = "development" ]; then
        docker-compose logs -f pacman-sync-dev
    else
        docker-compose logs -f pacman-sync-server
    fi
}

# Function to show status
show_status() {
    print_info "Service status:"
    
    docker-compose ps
    
    print_info "Container health status:"
    docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
}

# Function to clean up
clean_up() {
    print_warning "This will remove all containers, images, and volumes. Are you sure? (y/N)"
    read -r response
    
    if [[ "$response" =~ ^[Yy]$ ]]; then
        print_info "Cleaning up Docker resources..."
        
        docker-compose down -v --remove-orphans
        docker system prune -f
        docker volume prune -f
        
        print_success "Cleanup completed"
    else
        print_info "Cleanup cancelled"
    fi
}

# Function to start development environment
start_dev() {
    ENVIRONMENT="development"
    BUILD_TARGET="development"
    
    print_info "Starting development environment..."
    
    build_images
    start_services
}

# Function to start production environment
start_prod() {
    ENVIRONMENT="production"
    BUILD_TARGET="production"
    
    print_info "Starting production environment..."
    
    build_images
    start_services
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -e|--env)
            ENVIRONMENT="$2"
            shift 2
            ;;
        -d|--database)
            DATABASE_TYPE="$2"
            shift 2
            ;;
        -p|--port)
            HTTP_PORT="$2"
            shift 2
            ;;
        -h|--help)
            show_usage
            exit 0
            ;;
        build)
            COMMAND="build"
            shift
            ;;
        start)
            COMMAND="start"
            shift
            ;;
        stop)
            COMMAND="stop"
            shift
            ;;
        restart)
            COMMAND="restart"
            shift
            ;;
        logs)
            COMMAND="logs"
            shift
            ;;
        status)
            COMMAND="status"
            shift
            ;;
        clean)
            COMMAND="clean"
            shift
            ;;
        dev)
            COMMAND="dev"
            shift
            ;;
        prod)
            COMMAND="prod"
            shift
            ;;
        *)
            print_error "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
done

# Set build target based on environment
if [ "$ENVIRONMENT" = "development" ]; then
    BUILD_TARGET="development"
else
    BUILD_TARGET="production"
fi

# Export environment variables for docker-compose
export ENVIRONMENT
export DATABASE_TYPE
export HTTP_PORT

# Check prerequisites
check_prerequisites

# Execute command
case $COMMAND in
    build)
        build_images
        ;;
    start)
        start_services
        ;;
    stop)
        stop_services
        ;;
    restart)
        restart_services
        ;;
    logs)
        show_logs
        ;;
    status)
        show_status
        ;;
    clean)
        clean_up
        ;;
    dev)
        start_dev
        ;;
    prod)
        start_prod
        ;;
    *)
        print_error "No command specified"
        show_usage
        exit 1
        ;;
esac