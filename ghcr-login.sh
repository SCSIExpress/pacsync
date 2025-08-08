#!/bin/bash

# GitHub Container Registry Login Helper
# This script helps you authenticate with GitHub Container Registry (GHCR)

set -e

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

print_header "GitHub Container Registry Login"

echo "This script will help you login to GitHub Container Registry (ghcr.io)"
echo "You'll need a GitHub Personal Access Token with 'packages:write' permission."
echo ""

# Check if GitHub CLI is available
if command -v gh &> /dev/null; then
    print_status "GitHub CLI detected. You can use it for authentication."
    echo ""
    echo "Option 1: Use GitHub CLI (Recommended)"
    echo "  gh auth token | docker login ghcr.io -u \$(gh api user --jq .login) --password-stdin"
    echo ""
fi

echo "Option 2: Use Personal Access Token"
echo "  1. Go to https://github.com/settings/tokens"
echo "  2. Click 'Generate new token' -> 'Generate new token (classic)'"
echo "  3. Give it a name like 'Docker Registry Access'"
echo "  4. Select scopes: 'write:packages', 'read:packages', 'delete:packages'"
echo "  5. Click 'Generate token' and copy the token"
echo ""

read -p "Do you want to login now? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo ""
    print_status "Choose login method:"
    echo "1) GitHub CLI (automatic)"
    echo "2) Personal Access Token (manual)"
    echo ""
    read -p "Enter choice (1 or 2): " -n 1 -r choice
    echo ""
    
    case $choice in
        1)
            if command -v gh &> /dev/null; then
                print_status "Using GitHub CLI for authentication..."
                if gh auth status &> /dev/null; then
                    USERNAME=$(gh api user --jq .login)
                    print_status "Logging in as: $USERNAME"
                    gh auth token | docker login ghcr.io -u "$USERNAME" --password-stdin
                    print_success "Successfully logged in to ghcr.io"
                else
                    print_error "GitHub CLI is not authenticated. Run 'gh auth login' first."
                    exit 1
                fi
            else
                print_error "GitHub CLI is not installed. Please use option 2."
                exit 1
            fi
            ;;
        2)
            print_status "Manual login with Personal Access Token"
            read -p "Enter your GitHub username: " username
            echo "Enter your Personal Access Token (input will be hidden):"
            read -s token
            echo ""
            
            if [ -z "$username" ] || [ -z "$token" ]; then
                print_error "Username and token are required"
                exit 1
            fi
            
            print_status "Logging in to ghcr.io..."
            echo "$token" | docker login ghcr.io -u "$username" --password-stdin
            print_success "Successfully logged in to ghcr.io"
            ;;
        *)
            print_error "Invalid choice"
            exit 1
            ;;
    esac
    
    echo ""
    print_success "You can now run the build and push script:"
    echo "  ./build-and-push.sh"
    
else
    echo ""
    print_status "Login skipped. When you're ready to login, you can:"
    echo ""
    if command -v gh &> /dev/null; then
        echo "Use GitHub CLI:"
        echo "  gh auth token | docker login ghcr.io -u \$(gh api user --jq .login) --password-stdin"
        echo ""
    fi
    echo "Or use Personal Access Token:"
    echo "  echo YOUR_TOKEN | docker login ghcr.io -u YOUR_USERNAME --password-stdin"
    echo ""
    echo "Then run: ./build-and-push.sh"
fi