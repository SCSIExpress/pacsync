#!/usr/bin/env python3
"""
Production startup script for Pacman Sync Utility Server.
"""

import sys
import os
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.absolute()
sys.path.insert(0, str(project_root))

# Set working directory
os.chdir(project_root)

if __name__ == "__main__":
    import uvicorn
    
    # Import the app after setting up the path
    from server.api.main import app
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8080,
        workers=4
    )