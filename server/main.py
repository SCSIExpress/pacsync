"""
Main entry point for the Pacman Sync Utility Server.

This module initializes and runs the central server with web UI and REST API.
"""

import sys
import logging
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from server.config import get_config, setup_logging

logger = logging.getLogger(__name__)


def main():
    """Main entry point for the server."""
    # Load configuration
    config = get_config()
    
    # Setup logging
    setup_logging(config)
    
    logger.info("Starting Pacman Sync Utility Server...")
    logger.info(f"Configuration: database={config.database.type}, host={config.server.host}, port={config.server.port}")
    logger.info(f"Environment: {config.server.environment}")
    
    # Start the FastAPI server with graceful shutdown support
    try:
        import uvicorn
        from server.api.main import app
        
        logger.info("Starting FastAPI server with graceful shutdown support...")
        
        # Configure uvicorn for graceful shutdown
        uvicorn_config = uvicorn.Config(
            app,
            host=config.server.host,
            port=config.server.port,
            log_level=config.server.log_level.lower(),
            reload=(config.server.environment == "development"),
            # Graceful shutdown configuration
            timeout_keep_alive=5,
            timeout_graceful_shutdown=30,
        )
        
        server = uvicorn.Server(uvicorn_config)
        server.run()
        
    except KeyboardInterrupt:
        logger.info("Server shutdown requested via keyboard interrupt")
    except Exception as e:
        logger.error(f"Server error: {e}")
        sys.exit(1)
    
    logger.info("Server shutdown complete")


if __name__ == "__main__":
    main()