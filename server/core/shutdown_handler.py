"""
Graceful shutdown handler for container lifecycle management.

This module provides graceful shutdown capabilities for the Pacman Sync Utility
server, ensuring that ongoing operations are completed and resources are
properly cleaned up before the process terminates.
"""

import asyncio
import logging
import signal
import time
from typing import List, Callable, Optional, Any
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)


class GracefulShutdownHandler:
    """
    Handles graceful shutdown of the application.
    
    This class manages the shutdown process by:
    1. Catching shutdown signals (SIGTERM, SIGINT)
    2. Stopping new request acceptance
    3. Waiting for ongoing operations to complete
    4. Cleaning up resources
    5. Exiting gracefully
    """
    
    def __init__(self, shutdown_timeout: int = 30):
        self.shutdown_timeout = shutdown_timeout
        self.shutdown_event = asyncio.Event()
        self.cleanup_tasks: List[Callable] = []
        self.active_operations: List[asyncio.Task] = []
        self.is_shutting_down = False
        self._shutdown_start_time: Optional[float] = None
    
    def register_cleanup_task(self, cleanup_func: Callable):
        """Register a cleanup function to be called during shutdown."""
        self.cleanup_tasks.append(cleanup_func)
        logger.debug(f"Registered cleanup task: {cleanup_func.__name__}")
    
    def register_active_operation(self, task: asyncio.Task):
        """Register an active operation that should complete before shutdown."""
        self.active_operations.append(task)
        
        # Clean up completed tasks
        self.active_operations = [t for t in self.active_operations if not t.done()]
    
    def setup_signal_handlers(self):
        """Set up signal handlers for graceful shutdown."""
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, initiating graceful shutdown...")
            asyncio.create_task(self.initiate_shutdown())
        
        # Handle SIGTERM (Docker stop, Kubernetes termination)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Handle SIGINT (Ctrl+C)
        signal.signal(signal.SIGINT, signal_handler)
        
        logger.info("Signal handlers registered for graceful shutdown")
    
    async def initiate_shutdown(self):
        """Initiate the graceful shutdown process."""
        if self.is_shutting_down:
            logger.warning("Shutdown already in progress")
            return
        
        self.is_shutting_down = True
        self._shutdown_start_time = time.time()
        
        logger.info("Starting graceful shutdown process...")
        
        # Update health check status
        try:
            from server.api.health import mark_service_shutting_down
            mark_service_shutting_down()
        except ImportError:
            logger.warning("Could not update health check status")
        
        # Set shutdown event to signal other components
        self.shutdown_event.set()
        
        # Wait for active operations to complete
        await self._wait_for_active_operations()
        
        # Run cleanup tasks
        await self._run_cleanup_tasks()
        
        shutdown_duration = time.time() - self._shutdown_start_time
        logger.info(f"Graceful shutdown completed in {shutdown_duration:.2f} seconds")
    
    async def _wait_for_active_operations(self):
        """Wait for active operations to complete with timeout."""
        if not self.active_operations:
            logger.info("No active operations to wait for")
            return
        
        logger.info(f"Waiting for {len(self.active_operations)} active operations to complete...")
        
        try:
            # Wait for all active operations with timeout
            await asyncio.wait_for(
                asyncio.gather(*self.active_operations, return_exceptions=True),
                timeout=self.shutdown_timeout - 5  # Reserve 5 seconds for cleanup
            )
            logger.info("All active operations completed successfully")
        except asyncio.TimeoutError:
            logger.warning(f"Timeout waiting for active operations, cancelling remaining tasks")
            
            # Cancel remaining tasks
            for task in self.active_operations:
                if not task.done():
                    task.cancel()
                    logger.debug(f"Cancelled task: {task}")
            
            # Wait a bit for cancellations to take effect
            await asyncio.sleep(1)
        except Exception as e:
            logger.error(f"Error waiting for active operations: {e}")
    
    async def _run_cleanup_tasks(self):
        """Run all registered cleanup tasks."""
        if not self.cleanup_tasks:
            logger.info("No cleanup tasks to run")
            return
        
        logger.info(f"Running {len(self.cleanup_tasks)} cleanup tasks...")
        
        for cleanup_func in self.cleanup_tasks:
            try:
                if asyncio.iscoroutinefunction(cleanup_func):
                    await cleanup_func()
                else:
                    cleanup_func()
                logger.debug(f"Completed cleanup task: {cleanup_func.__name__}")
            except Exception as e:
                logger.error(f"Error in cleanup task {cleanup_func.__name__}: {e}")
    
    async def wait_for_shutdown(self):
        """Wait for shutdown signal."""
        await self.shutdown_event.wait()
    
    def is_shutdown_requested(self) -> bool:
        """Check if shutdown has been requested."""
        return self.shutdown_event.is_set()
    
    @asynccontextmanager
    async def operation_context(self, operation_name: str = "operation"):
        """
        Context manager for tracking active operations.
        
        Usage:
            async with shutdown_handler.operation_context("sync_operation"):
                # Your operation code here
                await some_long_running_task()
        """
        if self.is_shutdown_requested():
            logger.warning(f"Refusing to start {operation_name} during shutdown")
            raise RuntimeError("Service is shutting down")
        
        # Create a task for this operation
        current_task = asyncio.current_task()
        if current_task:
            self.register_active_operation(current_task)
        
        logger.debug(f"Started operation: {operation_name}")
        
        try:
            yield
        finally:
            logger.debug(f"Completed operation: {operation_name}")
    
    def get_shutdown_status(self) -> dict:
        """Get current shutdown status information."""
        if not self.is_shutting_down:
            return {
                "status": "running",
                "active_operations": len(self.active_operations),
                "cleanup_tasks": len(self.cleanup_tasks)
            }
        
        elapsed_time = 0
        if self._shutdown_start_time:
            elapsed_time = time.time() - self._shutdown_start_time
        
        return {
            "status": "shutting_down",
            "elapsed_time": elapsed_time,
            "timeout": self.shutdown_timeout,
            "active_operations": len([t for t in self.active_operations if not t.done()]),
            "cleanup_tasks": len(self.cleanup_tasks)
        }


# Global shutdown handler instance
_shutdown_handler: Optional[GracefulShutdownHandler] = None


def get_shutdown_handler(shutdown_timeout: int = 30) -> GracefulShutdownHandler:
    """Get the global shutdown handler instance."""
    global _shutdown_handler
    if _shutdown_handler is None:
        _shutdown_handler = GracefulShutdownHandler(shutdown_timeout)
    return _shutdown_handler


def setup_graceful_shutdown(shutdown_timeout: int = 30) -> GracefulShutdownHandler:
    """Set up graceful shutdown handling."""
    handler = get_shutdown_handler(shutdown_timeout)
    handler.setup_signal_handlers()
    return handler


async def shutdown_cleanup():
    """Cleanup function to be called during shutdown."""
    logger.info("Running application shutdown cleanup...")
    
    try:
        # Close database connections
        from server.database.connection import close_database
        await close_database()
        logger.info("Database connections closed")
    except Exception as e:
        logger.error(f"Error closing database connections: {e}")
    
    try:
        # Additional cleanup can be added here
        logger.info("Application cleanup completed")
    except Exception as e:
        logger.error(f"Error during application cleanup: {e}")