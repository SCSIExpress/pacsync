"""
Sync Manager for Pacman Sync Utility Client.

This module integrates the API client with the Qt application, handling
authentication, status updates, and sync operations with proper error handling.
"""

import asyncio
import logging
import socket
from datetime import datetime, timedelta
from typing import Optional, Callable, Dict, Any
from PyQt6.QtCore import QObject, QTimer, pyqtSignal, QThread, pyqtSlot

from client.api_client import PacmanSyncAPIClient, APIClientError, AuthenticationError, NetworkError, RetryConfig
from client.config import ClientConfiguration
from client.qt.application import SyncStatus
from client.package_operations import PackageSynchronizer, StateManager, PackageOperationError
from client.pacman_interface import PacmanInterface
from client.status_persistence import StatusPersistenceManager
from client.error_handling import ClientErrorHandler, ErrorDisplayMode, setup_client_error_handling
from shared.models import OperationType, SystemState, Repository
from shared.exceptions import (
    PacmanSyncError, ErrorCode, NetworkError as SharedNetworkError,
    AuthenticationError as SharedAuthError, RecoveryAction
)
from shared.logging_config import setup_logging, LogLevel, LogFormat, log_structured_error

logger = logging.getLogger(__name__)


class AsyncWorker(QThread):
    """Worker thread for async operations."""
    
    # Signals for communication with main thread
    operation_completed = pyqtSignal(str, bool, str)  # operation_type, success, message
    status_updated = pyqtSignal(object)  # SyncStatus
    error_occurred = pyqtSignal(str, str)  # error_type, message
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._operations_queue = None
        self._running = False
        self._loop = None
    
    def run(self):
        """Run the async event loop in the worker thread."""
        self._running = True
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        
        try:
            self._loop.run_until_complete(self._process_operations())
        except Exception as e:
            logger.error(f"Worker thread error: {e}")
        finally:
            self._loop.close()
            self._loop = None
    
    async def _process_operations(self):
        """Process operations from the queue."""
        # Initialize the queue in the async context
        self._operations_queue = asyncio.Queue()
        
        while self._running:
            try:
                # Wait for operations with timeout
                operation = await asyncio.wait_for(
                    self._operations_queue.get(), 
                    timeout=1.0
                )
                
                # Process the operation
                await self._execute_operation(operation)
                
            except asyncio.TimeoutError:
                # Continue loop to check if still running
                continue
            except Exception as e:
                logger.error(f"Error processing operation: {e}")
    
    async def _execute_operation(self, operation: Dict[str, Any]):
        """Execute a single operation."""
        op_type = operation.get('type')
        
        try:
            if op_type == 'authenticate':
                await self._handle_authenticate(operation)
            elif op_type == 'report_status':
                await self._handle_report_status(operation)
            elif op_type == 'sync_operation':
                await self._handle_sync_operation(operation)
            elif op_type == 'submit_repository_info':
                await self._handle_submit_repository_info(operation)
            elif op_type == 'process_offline_operations':
                await self._handle_process_offline_operations(operation)
            elif op_type == 'execute_sync_to_latest':
                await self._handle_execute_sync_to_latest(operation)
            elif op_type == 'execute_set_as_latest':
                await self._handle_execute_set_as_latest(operation)
            elif op_type == 'execute_revert_to_previous':
                await self._handle_execute_revert_to_previous(operation)
            else:
                logger.warning(f"Unknown operation type: {op_type}")
                
        except Exception as e:
            logger.error(f"Operation {op_type} failed: {e}")
            self.error_occurred.emit(op_type, str(e))
    
    async def _handle_authenticate(self, operation: Dict[str, Any]):
        """Handle authentication operation."""
        api_client = operation['api_client']
        endpoint_name = operation['endpoint_name']
        hostname = operation['hostname']
        
        try:
            await api_client.authenticate(endpoint_name, hostname)
            self.operation_completed.emit('authenticate', True, 'Authentication successful')
        except Exception as e:
            self.operation_completed.emit('authenticate', False, str(e))
    
    async def _handle_report_status(self, operation: Dict[str, Any]):
        """Handle status reporting operation."""
        api_client = operation['api_client']
        endpoint_id = operation['endpoint_id']
        status = operation['status']
        
        try:
            success = await api_client.report_status(endpoint_id, status)
            self.operation_completed.emit('report_status', success, 'Status reported')
        except Exception as e:
            self.operation_completed.emit('report_status', False, str(e))
    
    async def _handle_sync_operation(self, operation: Dict[str, Any]):
        """Handle sync operation."""
        api_client = operation['api_client']
        endpoint_id = operation['endpoint_id']
        operation_type = operation['operation_type']
        
        try:
            operation_id = await api_client.trigger_sync(endpoint_id, operation_type)
            self.operation_completed.emit('sync_operation', True, f'Operation started: {operation_id}')
        except Exception as e:
            self.operation_completed.emit('sync_operation', False, str(e))
    
    async def _handle_submit_repository_info(self, operation: Dict[str, Any]):
        """Handle repository info submission."""
        api_client = operation['api_client']
        endpoint_id = operation['endpoint_id']
        repositories = operation['repositories']
        
        try:
            success = await api_client.submit_repository_info(endpoint_id, repositories)
            self.operation_completed.emit('submit_repository_info', success, 'Repository info submitted')
        except Exception as e:
            self.operation_completed.emit('submit_repository_info', False, str(e))
    
    async def _handle_process_offline_operations(self, operation: Dict[str, Any]):
        """Handle processing of offline operations."""
        api_client = operation['api_client']
        
        try:
            processed = await api_client.process_offline_operations()
            self.operation_completed.emit('process_offline_operations', True, f'Processed {processed} operations')
        except Exception as e:
            self.operation_completed.emit('process_offline_operations', False, str(e))
    
    async def _handle_execute_sync_to_latest(self, operation: Dict[str, Any]):
        """Handle sync to latest package operation."""
        synchronizer = operation['synchronizer']
        target_state = operation['target_state']
        
        try:
            # Execute sync operation in thread pool to avoid blocking
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(synchronizer.sync_to_latest, target_state)
                result = future.result()
            
            if result.success:
                message = f'Sync completed: {result.packages_changed} packages changed'
                self.operation_completed.emit('execute_sync_to_latest', True, message)
            else:
                error_msg = '; '.join(result.errors) if result.errors else 'Unknown error'
                self.operation_completed.emit('execute_sync_to_latest', False, error_msg)
                
        except Exception as e:
            self.operation_completed.emit('execute_sync_to_latest', False, str(e))
    
    async def _handle_execute_set_as_latest(self, operation: Dict[str, Any]):
        """Handle set as latest package operation."""
        synchronizer = operation['synchronizer']
        endpoint_id = operation['endpoint_id']
        api_client = operation['api_client']
        state_manager = operation['state_manager']
        
        try:
            # Execute set as latest operation in thread pool
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(synchronizer.set_as_latest, endpoint_id)
                system_state, result = future.result()
            
            if result.success and system_state:
                # Save state locally
                state_id = state_manager.save_state(system_state, is_target=True)
                
                # Submit state to server
                state_id = await api_client.submit_state(endpoint_id, system_state)
                success = bool(state_id)
                
                if success:
                    message = f'Set as latest completed: {len(system_state.packages)} packages captured'
                    self.operation_completed.emit('execute_set_as_latest', True, message)
                else:
                    self.operation_completed.emit('execute_set_as_latest', False, 'Failed to submit state to server')
            else:
                error_msg = '; '.join(result.errors) if result.errors else 'Failed to capture system state'
                self.operation_completed.emit('execute_set_as_latest', False, error_msg)
                
        except Exception as e:
            self.operation_completed.emit('execute_set_as_latest', False, str(e))
    
    async def _handle_execute_revert_to_previous(self, operation: Dict[str, Any]):
        """Handle revert to previous package operation."""
        synchronizer = operation['synchronizer']
        state_manager = operation['state_manager']
        endpoint_id = operation['endpoint_id']
        
        try:
            # Get previous state
            previous_state = state_manager.get_previous_state(endpoint_id)
            if not previous_state:
                self.operation_completed.emit('execute_revert_to_previous', False, 'No previous state found')
                return
            
            # Execute revert operation in thread pool
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(synchronizer.revert_to_previous, previous_state)
                result = future.result()
            
            if result.success:
                message = f'Revert completed: {result.packages_changed} packages changed'
                self.operation_completed.emit('execute_revert_to_previous', True, message)
            else:
                error_msg = '; '.join(result.errors) if result.errors else 'Unknown error'
                self.operation_completed.emit('execute_revert_to_previous', False, error_msg)
                
        except Exception as e:
            self.operation_completed.emit('execute_revert_to_previous', False, str(e))
    
    def queue_operation(self, operation: Dict[str, Any]):
        """Queue an operation for processing."""
        if self._running and hasattr(self, '_loop') and self._loop:
            try:
                asyncio.run_coroutine_threadsafe(
                    self._operations_queue.put(operation),
                    self._loop
                )
            except Exception as e:
                logger.error(f"Failed to queue operation: {e}")
        else:
            logger.warning("Cannot queue operation: worker not running or loop not available")
    
    def stop(self):
        """Stop the worker thread."""
        self._running = False


class SyncManager(QObject):
    """
    Manages synchronization operations and API communication.
    
    This class integrates the API client with the Qt application, handling
    authentication, periodic status updates, and sync operations.
    """
    
    # Signals for Qt integration
    status_changed = pyqtSignal(object)  # SyncStatus
    authentication_changed = pyqtSignal(bool)  # is_authenticated
    operation_completed = pyqtSignal(str, bool, str)  # operation, success, message
    error_occurred = pyqtSignal(str)  # error_message
    
    def __init__(self, config: ClientConfiguration, parent=None):
        super().__init__(parent)
        
        self.config = config
        self._current_status = SyncStatus.OFFLINE
        self._is_authenticated = False
        self._endpoint_id: Optional[str] = None
        
        # Set up enhanced logging
        self._setup_logging(config)
        
        # Initialize error handler
        self._error_handler = ClientErrorHandler(self)
        self._error_handler.set_display_mode(ErrorDisplayMode.BOTH)
        self._error_handler.set_show_technical_details(config.get_debug_mode())
        
        # Register recovery callbacks
        self._setup_recovery_callbacks()
        
        # Initialize status persistence
        self._status_persistence = StatusPersistenceManager()
        
        # Initialize API client
        retry_config = RetryConfig(
            max_retries=config.get_retry_attempts(),
            base_delay=config.get_retry_delay(),
            max_delay=60.0
        )
        
        self._api_client = PacmanSyncAPIClient(
            server_url=config.get_server_url(),
            timeout=config.get_server_timeout(),
            retry_config=retry_config
        )
        
        # Initialize package operations
        self._pacman_interface = PacmanInterface()
        self._package_synchronizer = PackageSynchronizer(self._pacman_interface)
        self._state_manager = StateManager()
        
        # Initialize worker thread
        self._worker = AsyncWorker(self)
        self._worker.operation_completed.connect(self._on_operation_completed)
        self._worker.status_updated.connect(self._on_status_updated)
        self._worker.error_occurred.connect(self._on_error_occurred)
        self._worker.start()
        
        # Set up periodic status updates
        self._status_timer = QTimer(self)
        self._status_timer.timeout.connect(self._periodic_status_update)
        self._status_timer.start(config.get_update_interval() * 1000)  # Convert to milliseconds
        
        # Set up connection retry timer
        self._retry_timer = QTimer(self)
        self._retry_timer.timeout.connect(self._retry_connection)
        self._retry_timer.setSingleShot(True)
        
        logger.info("Sync manager initialized with enhanced error handling")
    
    def _setup_logging(self, config: ClientConfiguration):
        """Set up comprehensive logging for the client."""
        try:
            # Determine log level and format
            log_level = LogLevel.DEBUG if config.get_debug_mode() else LogLevel.INFO
            log_format = LogFormat.JSON if config.get_structured_logging() else LogFormat.STANDARD
            
            # Set up log files
            log_file = config.get_log_file() if config.get_log_file() else None
            audit_file = None
            
            if log_file:
                # Create audit file path based on log file
                import os
                log_dir = os.path.dirname(log_file)
                audit_file = os.path.join(log_dir, "client-audit.log")
            
            # Set up comprehensive logging
            setup_logging(
                log_level=log_level,
                log_format=log_format,
                log_file=log_file,
                enable_console=not config.get_quiet_mode(),
                enable_audit=True,
                audit_file=audit_file
            )
            
            logger.info("Enhanced logging configured")
            
        except Exception as e:
            # Fallback to basic logging if enhanced setup fails
            logging.basicConfig(level=logging.INFO)
            logger.warning(f"Failed to set up enhanced logging, using basic logging: {e}")
    
    def _setup_recovery_callbacks(self):
        """Set up recovery callbacks for error handling."""
        self._error_handler.register_recovery_callback(
            RecoveryAction.RECONNECT, 
            self._recovery_reconnect
        )
        
        self._error_handler.register_recovery_callback(
            RecoveryAction.REFRESH_TOKEN,
            self._recovery_refresh_token
        )
        
        self._error_handler.register_recovery_callback(
            RecoveryAction.RETRY,
            self._recovery_retry_last_operation
        )
        
        logger.debug("Recovery callbacks registered")
    
    def _recovery_reconnect(self) -> bool:
        """Recovery callback for reconnection."""
        try:
            self._authenticate()
            return True
        except Exception as e:
            logger.error(f"Recovery reconnection failed: {e}")
            return False
    
    def _recovery_refresh_token(self) -> bool:
        """Recovery callback for token refresh."""
        try:
            # Clear current authentication
            self._api_client.clear_authentication()
            self._is_authenticated = False
            self._endpoint_id = None
            
            # Attempt re-authentication
            self._authenticate()
            return True
        except Exception as e:
            logger.error(f"Recovery token refresh failed: {e}")
            return False
    
    def _recovery_retry_last_operation(self) -> bool:
        """Recovery callback for retrying the last operation."""
        # This would retry the last failed operation
        # For now, just return True as a placeholder
        logger.info("Retry recovery action triggered")
        return True
    
    def start(self):
        """Start the sync manager and attempt initial authentication."""
        logger.info("Starting sync manager")
        self._authenticate()
    
    def stop(self):
        """Stop the sync manager and cleanup resources."""
        logger.info("Stopping sync manager")
        
        self._status_timer.stop()
        self._retry_timer.stop()
        
        if self._worker.isRunning():
            self._worker.stop()
            self._worker.wait(5000)  # Wait up to 5 seconds
        
        # Close API client
        asyncio.run(self._api_client.close())
    
    def _authenticate(self):
        """Attempt to authenticate with the server."""
        endpoint_name = self.config.get_endpoint_name()
        hostname = socket.gethostname()
        
        logger.info(f"Attempting authentication: {endpoint_name}@{hostname}")
        
        self._worker.queue_operation({
            'type': 'authenticate',
            'api_client': self._api_client,
            'endpoint_name': endpoint_name,
            'hostname': hostname
        })
    
    def _retry_connection(self):
        """Retry connection after failure."""
        logger.info("Retrying connection...")
        self._authenticate()
    
    def _periodic_status_update(self):
        """Perform periodic status update."""
        if not self._is_authenticated:
            # Try to authenticate if not authenticated
            self._authenticate()
            return
        
        # Check if we need to process offline operations
        if not self._api_client.is_offline():
            self._worker.queue_operation({
                'type': 'process_offline_operations',
                'api_client': self._api_client
            })
        
        # Report current status
        if self._endpoint_id:
            self._worker.queue_operation({
                'type': 'report_status',
                'api_client': self._api_client,
                'endpoint_id': self._endpoint_id,
                'status': self._current_status
            })
    
    @pyqtSlot(str, bool, str)
    def _on_operation_completed(self, operation_type: str, success: bool, message: str):
        """Handle completed operations."""
        logger.info(f"Operation {operation_type} completed: success={success}, message={message}")
        
        if operation_type == 'authenticate':
            if success:
                self._is_authenticated = True
                endpoint_info = self._api_client.get_endpoint_info()
                if endpoint_info:
                    self._endpoint_id = endpoint_info['endpoint_id']
                
                # Update status to indicate we're connected
                self._update_status(SyncStatus.IN_SYNC)  # Default to in_sync, will be updated by status checks
                
                self.authentication_changed.emit(True)
                logger.info(f"Authentication successful. Endpoint ID: {self._endpoint_id}")
            else:
                self._is_authenticated = False
                self._endpoint_id = None
                self._update_status(SyncStatus.OFFLINE)
                self.authentication_changed.emit(False)
                
                # Schedule retry
                self._retry_timer.start(30000)  # Retry in 30 seconds
                logger.warning(f"Authentication failed: {message}")
        
        elif operation_type == 'report_status':
            if not success and 'authentication' in message.lower():
                # Authentication expired, clear state and retry
                self._is_authenticated = False
                self._endpoint_id = None
                self._api_client.clear_authentication()
                self._authenticate()
        
        # Emit signal for external handlers
        self.operation_completed.emit(operation_type, success, message)
    
    @pyqtSlot(object)
    def _on_status_updated(self, status: SyncStatus):
        """Handle status updates from worker."""
        self._update_status(status)
    
    @pyqtSlot(str, str)
    def _on_error_occurred(self, error_type: str, message: str):
        """Handle errors from worker with enhanced error handling."""
        logger.error(f"Worker error ({error_type}): {message}")
        
        # Create appropriate structured error
        if 'network' in error_type.lower() or 'connection' in message.lower():
            error = SharedNetworkError(
                message=message,
                error_code=ErrorCode.NETWORK_CONNECTION_FAILED,
                context={'error_type': error_type, 'source': 'worker_thread'}
            )
            self._update_status(SyncStatus.OFFLINE)
        elif 'auth' in error_type.lower():
            error = SharedAuthError(
                message=message,
                error_code=ErrorCode.AUTH_INVALID_TOKEN,
                context={'error_type': error_type, 'source': 'worker_thread'}
            )
        else:
            error = PacmanSyncError(
                message=message,
                error_code=ErrorCode.INTERNAL_UNEXPECTED_ERROR,
                context={'error_type': error_type, 'source': 'worker_thread'}
            )
        
        # Handle error through error handler
        self._error_handler.handle_error(
            error,
            endpoint_id=self._endpoint_id,
            auto_recover=True
        )
        
        self.error_occurred.emit(f"{error_type}: {message}")
    
    def _update_status(self, new_status: SyncStatus):
        """Update the current sync status."""
        if self._current_status != new_status:
            old_status = self._current_status
            self._current_status = new_status
            
            logger.info(f"Status changed: {old_status.value} -> {new_status.value}")
            self.status_changed.emit(new_status)
    
    # Public interface methods
    
    def get_current_status(self) -> SyncStatus:
        """Get the current sync status."""
        return self._current_status
    
    def is_authenticated(self) -> bool:
        """Check if client is authenticated."""
        return self._is_authenticated
    
    def is_offline(self) -> bool:
        """Check if client is offline."""
        return self._api_client.is_offline()
    
    def get_endpoint_id(self) -> Optional[str]:
        """Get the current endpoint ID."""
        return self._endpoint_id
    
    def sync_to_latest(self, target_state: SystemState = None):
        """
        Trigger sync to latest operation.
        
        Args:
            target_state: Target system state to sync to. If None, will fetch from server.
        """
        if not self._is_authenticated or not self._endpoint_id:
            self.error_occurred.emit("Not authenticated or endpoint ID not available")
            return
        
        logger.info("Triggering sync to latest")
        self._update_status(SyncStatus.SYNCING)
        
        if target_state:
            # Execute sync operation directly with provided target state
            self._worker.queue_operation({
                'type': 'execute_sync_to_latest',
                'synchronizer': self._package_synchronizer,
                'target_state': target_state
            })
        else:
            # First trigger server sync operation to get target state
            self._worker.queue_operation({
                'type': 'sync_operation',
                'api_client': self._api_client,
                'endpoint_id': self._endpoint_id,
                'operation_type': OperationType.SYNC
            })
    
    def set_as_latest(self):
        """Trigger set as latest operation."""
        if not self._is_authenticated or not self._endpoint_id:
            self.error_occurred.emit("Not authenticated or endpoint ID not available")
            return
        
        logger.info("Triggering set as latest")
        
        # Save current state before setting as latest
        try:
            current_state = self._pacman_interface.get_system_state(self._endpoint_id)
            self._state_manager.save_state(current_state, is_target=False)
        except Exception as e:
            logger.warning(f"Failed to save current state before set as latest: {e}")
        
        self._worker.queue_operation({
            'type': 'execute_set_as_latest',
            'synchronizer': self._package_synchronizer,
            'endpoint_id': self._endpoint_id,
            'api_client': self._api_client,
            'state_manager': self._state_manager
        })
    
    def revert_to_previous(self):
        """Trigger revert to previous operation."""
        if not self._is_authenticated or not self._endpoint_id:
            self.error_occurred.emit("Not authenticated or endpoint ID not available")
            return
        
        logger.info("Triggering revert to previous")
        
        # Save current state before reverting
        try:
            current_state = self._pacman_interface.get_system_state(self._endpoint_id)
            self._state_manager.save_state(current_state, is_target=False)
        except Exception as e:
            logger.warning(f"Failed to save current state before revert: {e}")
        
        self._worker.queue_operation({
            'type': 'execute_revert_to_previous',
            'synchronizer': self._package_synchronizer,
            'state_manager': self._state_manager,
            'endpoint_id': self._endpoint_id
        })
    
    def submit_repository_info(self, repositories: list):
        """Submit repository information to server."""
        if not self._is_authenticated or not self._endpoint_id:
            self.error_occurred.emit("Not authenticated or endpoint ID not available")
            return
        
        logger.info("Submitting repository information")
        
        self._worker.queue_operation({
            'type': 'submit_repository_info',
            'api_client': self._api_client,
            'endpoint_id': self._endpoint_id,
            'repositories': repositories
        })
    
    def force_status_update(self):
        """Force an immediate status update."""
        logger.info("Forcing status update")
        self._periodic_status_update()
    
    def reconnect(self):
        """Force reconnection to server."""
        logger.info("Forcing reconnection")
        self._is_authenticated = False
        self._endpoint_id = None
        self._api_client.clear_authentication()
        self._authenticate()