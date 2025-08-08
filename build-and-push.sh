#!/bin/bash

# Build and Push Docker Images to GitHub Container Registry
# This script builds both production and development images and pushes them to GHCR

set -e

# Configuration
REPO_OWNER="scsiexpress"  # Must be lowercase for Docker registry
REPO_NAME="pacsync"
IMAGE_NAME="pacman-sync-server"
REGISTRY="ghcr.io"
FULL_IMAGE_NAME="${REGISTRY}/${REPO_OWNER}/${IMAGE_NAME}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_header() {
    echo -e "${BLUE}================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}================================${NC}"
}

print_status() {
    echo -e "${YELLOW}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check prerequisites
check_prerequisites() {
    print_status "Checking prerequisites..."
    
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed or not in PATH"
        exit 1
    fi
    
    if ! command -v git &> /dev/null; then
        print_error "Git is not installed or not in PATH"
        exit 1
    fi
    
    # Check if logged into GitHub Container Registry (only if we're going to push)
    if [ "$SKIP_PUSH" = false ]; then
        if [ ! -f ~/.docker/config.json ] || ! grep -q "ghcr.io" ~/.docker/config.json; then
            print_status "Please login to GitHub Container Registry first:"
            echo "  echo \$GITHUB_TOKEN | docker login ghcr.io -u USERNAME --password-stdin"
            echo ""
            echo "Or use GitHub CLI:"
            echo "  gh auth token | docker login ghcr.io -u USERNAME --password-stdin"
            echo ""
            echo "Or run with --skip-push to build without pushing"
            exit 1
        fi
    fi
    
    print_success "Prerequisites check passed"
}

# Function to get version information
get_version_info() {
    print_status "Getting version information..."
    
    # Get git commit hash
    GIT_COMMIT=$(git rev-parse --short HEAD)
    
    # Get git tag if available
    GIT_TAG=$(git describe --tags --exact-match 2>/dev/null || echo "")
    
    # Get branch name
    GIT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
    
    # Determine version tag
    if [ -n "$GIT_TAG" ]; then
        VERSION_TAG="$GIT_TAG"
        print_status "Using git tag: $VERSION_TAG"
    else
        VERSION_TAG="$GIT_BRANCH-$GIT_COMMIT"
        print_status "Using branch-commit: $VERSION_TAG"
    fi
    
    # Set image tags
    PROD_TAGS=(
        "${FULL_IMAGE_NAME}:latest"
        "${FULL_IMAGE_NAME}:${VERSION_TAG}"
        "${FULL_IMAGE_NAME}:prod"
    )
    
    DEV_TAGS=(
        "${FULL_IMAGE_NAME}:dev"
        "${FULL_IMAGE_NAME}:dev-${VERSION_TAG}"
    )
    
    print_success "Version info collected"
    echo "  Git commit: $GIT_COMMIT"
    echo "  Git branch: $GIT_BRANCH"
    echo "  Version tag: $VERSION_TAG"
    if [ -n "$GIT_TAG" ]; then
        echo "  Git tag: $GIT_TAG"
    fi
}

# Function to build production image
build_production() {
    print_header "Building Production Image"
    
    print_status "Building production image with multiple tags..."
    
    # Build the image
    docker build \
        --target production \
        --build-arg BUILDKIT_INLINE_CACHE=1 \
        --label "org.opencontainers.image.source=https://github.com/${REPO_OWNER}/${REPO_NAME}" \
        --label "org.opencontainers.image.description=Pacman Sync Utility Server - Production" \
        --label "org.opencontainers.image.licenses=MIT" \
        --label "org.opencontainers.image.version=${VERSION_TAG}" \
        --label "org.opencontainers.image.revision=${GIT_COMMIT}" \
        -t "${PROD_TAGS[0]}" \
        .
    
    # Tag with additional tags
    for tag in "${PROD_TAGS[@]:1}"; do
        print_status "Tagging as: $tag"
        docker tag "${PROD_TAGS[0]}" "$tag"
    done
    
    print_success "Production image built successfully"
}

# Function to build development image
build_development() {
    print_header "Building Development Image"
    
    print_status "Building development image with multiple tags..."
    
    # Build the image
    docker build \
        --target development \
        --build-arg BUILDKIT_INLINE_CACHE=1 \
        --label "org.opencontainers.image.source=https://github.com/${REPO_OWNER}/${REPO_NAME}" \
        --label "org.opencontainers.image.description=Pacman Sync Utility Server - Development" \
        --label "org.opencontainers.image.licenses=MIT" \
        --label "org.opencontainers.image.version=${VERSION_TAG}" \
        --label "org.opencontainers.image.revision=${GIT_COMMIT}" \
        -t "${DEV_TAGS[0]}" \
        .
    
    # Tag with additional tags
    for tag in "${DEV_TAGS[@]:1}"; do
        print_status "Tagging as: $tag"
        docker tag "${DEV_TAGS[0]}" "$tag"
    done
    
    print_success "Development image built successfully"
}

# Function to push images
push_images() {
    print_header "Pushing Images to GitHub Container Registry"
    
    print_status "Pushing production images..."
    for tag in "${PROD_TAGS[@]}"; do
        print_status "Pushing: $tag"
        docker push "$tag"
    done
    
    print_status "Pushing development images..."
    for tag in "${DEV_TAGS[@]}"; do
        print_status "Pushing: $tag"
        docker push "$tag"
    done
    
    print_success "All images pushed successfully"
}

# Function to display image information
show_image_info() {
    print_header "Image Information"
    
    echo "Production Images:"
    for tag in "${PROD_TAGS[@]}"; do
        echo "  - $tag"
    done
    
    echo ""
    echo "Development Images:"
    for tag in "${DEV_TAGS[@]}"; do
        echo "  - $tag"
    done
    
    echo ""
    echo "Image sizes:"
    docker images "${FULL_IMAGE_NAME}" --format "table {{.Repository}}:{{.Tag}}\t{{.Size}}\t{{.CreatedAt}}"
}

# Function to generate usage examples
generate_usage_examples() {
    print_header "Usage Examples"
    
    cat << EOF
Pull and run production image:
  docker pull ${PROD_TAGS[0]}
  docker run -d --name pacman-sync-server -p 8080:8080 \\
    -e DATABASE_TYPE=internal \\
    -e JWT_SECRET_KEY="\$(openssl rand -hex 32)" \\
    -v pacman-sync-data:/app/data \\
    ${PROD_TAGS[0]}

Pull and run development image:
  docker pull ${DEV_TAGS[0]}
  docker run -d --name pacman-sync-dev -p 8080:8080 \\
    -e DATABASE_TYPE=internal \\
    -e JWT_SECRET_KEY=dev-key \\
    -v \$(pwd)/server:/app/server \\
    ${DEV_TAGS[0]}

Use in Docker Compose:
  services:
    pacman-sync-server:
      image: ${PROD_TAGS[0]}
      ports:
        - "8080:8080"
      environment:
        DATABASE_TYPE: internal
        JWT_SECRET_KEY: your-secret-key
      volumes:
        - pacman-sync-data:/app/data

View on GitHub Container Registry:
  https://github.com/${REPO_OWNER}/${REPO_NAME}/pkgs/container/${IMAGE_NAME}
EOF
}

# Function to cleanup local images (optional)
cleanup_local() {
    if [ "$1" = "--cleanup" ]; then
        print_header "Cleaning Up Local Images"
        
        print_status "Removing local images..."
        for tag in "${PROD_TAGS[@]}" "${DEV_TAGS[@]}"; do
            docker rmi "$tag" 2>/dev/null || true
        done
        
        print_success "Local images cleaned up"
    fi
}

# Main execution
main() {
    # Check if we should skip certain steps
    SKIP_BUILD=false
    SKIP_PUSH=false
    CLEANUP=false
    
    # Parse command line arguments first
    while [[ $# -gt 0 ]]; do
        case $1 in
            --skip-build)
                SKIP_BUILD=true
                shift
                ;;
            --skip-push)
                SKIP_PUSH=true
                shift
                ;;
            --cleanup)
                CLEANUP=true
                shift
                ;;
            --help|-h)
                echo "Usage: $0 [OPTIONS]"
                echo ""
                echo "Options:"
                echo "  --skip-build    Skip building images (only push existing)"
                echo "  --skip-push     Skip pushing images (only build)"
                echo "  --cleanup       Remove local images after pushing"
                echo "  --help, -h      Show this help message"
                exit 0
                ;;
            *)
                print_error "Unknown option: $1"
                echo "Use --help for usage information"
                exit 1
                ;;
        esac
    done
    
    print_header "Pacman Sync Utility - Docker Build & Push"
    
    echo "Repository: ${REPO_OWNER}/${REPO_NAME}"
    echo "Registry: ${REGISTRY}"
    echo "Image: ${FULL_IMAGE_NAME}"
    echo ""
    
    # Execute steps
    check_prerequisites
    get_version_info
    
    if [ "$SKIP_BUILD" = false ]; then
        build_production
        build_development
    else
        print_status "Skipping build step"
    fi
    
    if [ "$SKIP_PUSH" = false ]; then
        push_images
    else
        print_status "Skipping push step"
    fi
    
    show_image_info
    generate_usage_examples
    
    if [ "$CLEANUP" = true ]; then
        cleanup_local --cleanup
    fi
    
    print_success "Build and push completed successfully!"
}

# Run main function with all arguments
main "$@"