"""
Main entry point for the Pacman Sync Utility Server.

This module initializes and runs the central server with web UI and REST API.
"""

import os
import sys
import logging
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def main():
    """Main entry point for the server."""
    logger.info("Starting Pacman Sync Utility Server...")
    
    # Configuration from environment variables
    database_type = os.getenv("DATABASE_TYPE", "internal")
    http_port = int(os.getenv("HTTP_PORT", "8080"))
    http_host = os.getenv("HTTP_HOST", "0.0.0.0")
    log_level = os.getenv("LOG_LEVEL", "INFO")
    
    logger.info(f"Configuration: database={database_type}, host={http_host}, port={http_port}")
    
    # Start the FastAPI server
    try:
        import uvicorn
        from server.api.main import app
        
        logger.info("Starting FastAPI server...")
        uvicorn.run(
            app,
            host=http_host,
            port=http_port,
            log_level=log_level.lower()
        )
    except KeyboardInterrupt:
        logger.info("Server shutdown requested")
    except Exception as e:
        logger.error(f"Server error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()