#!/usr/bin/env python3
"""
Development startup script for Pacman Sync Utility Server.
"""

import sys
import os
from pathlib import Path

print("=== Startup Debug ===")
print(f"Current working directory: {os.getcwd()}")
print(f"Script location: {__file__}")

# Add project root to Python path
project_root = Path(__file__).parent.absolute()
print(f"Project root: {project_root}")
sys.path.insert(0, str(project_root))

# Set working directory
os.chdir(project_root)

# Check if server directory exists and has content
server_dir = project_root / "server"
print(f"Server directory exists: {server_dir.exists()}")
if server_dir.exists():
    print(f"Server directory contents: {list(server_dir.iterdir())}")
    api_dir = server_dir / "api"
    print(f"API directory exists: {api_dir.exists()}")
    if api_dir.exists():
        print(f"API directory contents: {list(api_dir.iterdir())}")

print("=== Starting Server ===")

if __name__ == "__main__":
    # Check if we can import the modules
    try:
        print("Attempting to import server.api.main...")
        from server.api.main import app
        print("✓ Successfully imported app")
        
        import uvicorn
        print("Starting uvicorn with hot reload...")
        
        # Use import string format to enable proper hot reload
        uvicorn.run(
            "server.api.main:app",
            host="0.0.0.0",
            port=4444,
            reload=True,
            reload_dirs=[str(project_root / "server"), str(project_root / "shared")]
        )
    except ImportError as e:
        print(f"✗ Import error: {e}")
        print("Falling back to direct execution...")
        
        # Try to run the main.py directly
        try:
            sys.path.insert(0, str(project_root / "server"))
            from main import main
            main()
        except Exception as e2:
            print(f"✗ Fallback failed: {e2}")
            sys.exit(1)