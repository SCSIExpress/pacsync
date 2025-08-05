#!/bin/bash

# Build script for the web UI

set -e

echo "Building Pacman Sync Utility Web UI..."

# Check if we're in the correct directory
if [ ! -f "package.json" ]; then
    echo "Error: package.json not found. Please run this script from the server/web directory."
    exit 1
fi

# Install dependencies
echo "Installing dependencies..."
npm install

# Build the application
echo "Building application..."
npm run build

echo "Build complete! Files are in the dist/ directory."
echo "The server will automatically serve these files when running."