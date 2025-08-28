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
    
    # Use import string format for multi-worker setup
    uvicorn.run(
        "server.api.main:app",
        host="0.0.0.0",
        port=4444,
        workers=4
    )