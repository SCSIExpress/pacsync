"""
Comprehensive tests for error handling and logging functionality.

This module tests the enhanced error handling, structured logging,
graceful degradation, and recovery mechanisms implemented in task 11.2.
"""

import pytest
import json
import logging
import tempfile
import os
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

# Import the modules we're testing
from shared.exceptions import (
    PacmanSyncError, ErrorCode, ErrorSeverity, RecoveryAction,
    NetworkError, AuthenticationError, ValidationError,
    create_error_response, handle_exception
)
from shared.logging_config import (
    setup_logging, LogLevel, LogFormat, AuditLogger, OperationLogger,
    StructuredFormatter, log_structured_error
)
from client.error_handling import (
    ClientErrorHandler, ErrorDisplayMode, NetworkState,
    setup_client_error_handling
)


class TestStructuredExceptions:
    """Test structured exception hierarchy and error responses."""
    
    def test_pacman_sync_error_creation(self):
        """Test creating structured PacmanSyncError."""
        error = PacmanSyncError(
            message="Test error message",
            error_code=ErrorCode.NETWORK_CONNECTION_FAILED,
            severity=ErrorSeverity.HIGH,
            context={'test_key': 'test_value'},
            recovery_actions=[RecoveryAction.RETRY, RecoveryAction.RECONNECT]
        )
        
        assert error.message == "Test error message"
        assert error.error_code == ErrorCode.NETWORK_CONNECTION_FAILED
        assert error.severity == ErrorSeverity.HIGH
        assert error.context['test_key'] == 'test_value'
        assert RecoveryAction.RETRY in error.recovery_actions
        assert RecoveryAction.RECONNECT in error.recovery_actions
        assert isinstance(error.timestamp, datetime)
    
    def test_error_to_dict_conversion(self):
        """Test converting error to dictionary format."""
        error = NetworkError(
            message="Connection failed",
            error_code=ErrorCode.NETWORK_CONNECTION_FAILED,
            context={'host': 'example.com', 'port': 8080}
        )
        
        error_dict = error.to_dict()
        
        assert 'error' in error_dict
        assert error_dict['error']['code'] == ErrorCode.NETWORK_CONNECTION_FAILED.value
        assert error_dict['error']['message'] == "Connection failed"
        assert error_dict['error']['severity'] == ErrorSeverity.MEDIUM.value
        assert error_dict['error']['context']['host'] == 'example.com'
        assert error_dict['error']['context']['port'] == 8080
        assert 'timestamp' in error_dict['error']
    
    def test_http_status_code_mapping(self):
        """Test HTTP status code mapping for different error types."""
        auth_error = AuthenticationError(
            message="Invalid token",
            error_code=ErrorCode.AUTH_INVALID_TOKEN
        )
        assert auth_error.get_http_status_code() == 401
        
        validation_error = ValidationError(
            message="Invalid input",
            field_name="test_field"
        )
        assert validation_error.get_http_status_code() == 400
        
        network_error = NetworkError(
            message="Connection timeout",
            error_code=ErrorCode.NETWORK_TIMEOUT
        )
        assert network_error.get_http_status_code() == 408
    
    def test_create_error_response(self):
        """Test creating standardized error response."""
        error = ValidationError(
            message="Field validation failed",
            field_name="endpoint_name",
            context={'provided_value': 'invalid@name', 'expected_pattern': r'^[a-zA-Z0-9._-]+$'}
        )
        
        response = create_error_response(error)
        
        assert 'error' in response
        assert response['error']['code'] == ErrorCode.VALIDATION_INVALID_INPUT.value
        assert response['error']['message'] == "Field validation failed"
        assert 'context' in response['error']
        assert response['error']['context']['field_name'] == 'endpoint_name'
    
    def test_handle_generic_exception(self):
        """Test converting generic exceptions to structured errors."""
        generic_error = ValueError("Invalid value provided")
        
        structured_error = handle_exception(
            generic_error,
            context={'operation': 'test_operation'},
            default_error_code=ErrorCode.VALIDATION_INVALID_INPUT
        )
        
        assert isinstance(structured_error, PacmanSyncError)
        assert structured_error.error_code == ErrorCode.VALIDATION_INVALID_INPUT
        assert structured_error.message == "Invalid value provided"
        assert structured_error.context['operation'] == 'test_operation'
        assert structured_error.cause == generic_error


class TestStructuredLogging:
    """Test structured logging functionality."""
    
    def test_structured_formatter(self):
        """Test structured JSON formatter."""
        formatter = StructuredFormatter()
        
        # Create a log record
        record = logging.LogRecord(
            name='test_logger',
            level=logging.ERROR,
            pathname='/test/path.py',
            lineno=42,
            msg='Test message',
            args=(),
            exc_info=None
        )
        
        # Add structured error info
        error = NetworkError(
            message="Test network error",
            error_code=ErrorCode.NETWORK_CONNECTION_FAILED
        )
        record.error_info = error
        
        formatted = formatter.format(record)
        log_data = json.loads(formatted)
        
        assert log_data['level'] == 'ERROR'
        assert log_data['logger'] == 'test_logger'
        assert log_data['message'] == 'Test message'
        assert log_data['line'] == 42
        assert 'error' in log_data
        assert log_data['error']['code'] == ErrorCode.NETWORK_CONNECTION_FAILED.value
    
    def test_audit_logger(self):
        """Test audit logging functionality."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Set up logging with temporary directory
            audit_file = os.path.join(temp_dir, 'audit.log')
            
            loggers = setup_logging(
                log_level=LogLevel.INFO,
                log_format=LogFormat.JSON,
                enable_console=False,
                enable_audit=True,
                audit_file=audit_file
            )
            
            audit_logger = AuditLogger()
            
            # Log authentication event
            audit_logger.log_authentication(
                endpoint_name="test-endpoint",
                endpoint_id="test-123",
                success=True
            )
            
            # Log sync operation
            audit_logger.log_sync_operation(
                operation_type="sync",
                endpoint_id="test-123",
                operation_id="op-456",
                pool_id="pool-789",
                result="completed",
                packages_affected=5
            )
            
            # Verify audit log was written
            assert os.path.exists(audit_file)
            
            with open(audit_file, 'r') as f:
                lines = f.readlines()
                assert len(lines) >= 2
                
                # Parse first log entry
                log_entry = json.loads(lines[0])
                assert 'audit' in log_entry
                assert log_entry['audit']['event_type'] == 'authentication'
                assert log_entry['audit']['endpoint_id'] == 'test-123'
    
    def test_operation_logger(self):
        """Test operation logging functionality."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = os.path.join(temp_dir, 'operations.log')
            
            setup_logging(
                log_level=LogLevel.INFO,
                log_format=LogFormat.JSON,
                log_file=log_file,
                enable_console=False
            )
            
            operation_logger = OperationLogger()
            
            # Log operation lifecycle
            operation_logger.log_operation_start(
                operation_type="sync",
                operation_id="op-123",
                endpoint_id="endpoint-456",
                context={'pool_id': 'pool-789'}
            )
            
            operation_logger.log_operation_progress(
                operation_id="op-123",
                stage="downloading",
                progress_percentage=50,
                current_action="Downloading package updates"
            )
            
            operation_logger.log_operation_complete(
                operation_id="op-123",
                success=True,
                duration_seconds=45.2,
                result_summary="5 packages updated"
            )
            
            # Verify operation log was written
            assert os.path.exists(log_file)
            
            with open(log_file, 'r') as f:
                lines = f.readlines()
                assert len(lines) >= 3
                
                # Parse operation start entry
                start_entry = json.loads(lines[0])
                assert 'operation' in start_entry
                assert start_entry['operation']['operation_id'] == 'op-123'
                assert start_entry['operation']['stage'] == 'started'


class TestClientErrorHandler:
    """Test client-side error handling functionality."""
    
    @pytest.fixture
    def error_handler(self):
        """Create a ClientErrorHandler instance for testing."""
        with patch('client.error_handling.QObject'):
            handler = ClientErrorHandler()
            handler.set_system_tray_available(False)  # Disable tray for testing
            return handler
    
    def test_error_handler_initialization(self, error_handler):
        """Test error handler initialization."""
        assert error_handler._network_state == NetworkState.UNKNOWN
        assert error_handler._display_mode == ErrorDisplayMode.BOTH
        assert len(error_handler._error_history) == 0
    
    def test_handle_network_error(self, error_handler):
        """Test handling network errors with graceful degradation."""
        # Mock the signals
        error_handler.error_occurred = Mock()
        error_handler.network_state_changed = Mock()
        
        # Create a network error
        network_error = ConnectionError("Connection refused")
        
        # Handle the error
        success = error_handler.handle_error(network_error, auto_recover=False)
        
        assert success
        assert error_handler._network_state == NetworkState.OFFLINE
        assert len(error_handler._error_history) == 1
        
        # Verify error was logged to history
        history_entry = error_handler._error_history[0]
        assert history_entry['error_code'] == ErrorCode.NETWORK_CONNECTION_FAILED.value
        assert 'Connection refused' in history_entry['message']
    
    def test_recovery_callback_registration(self, error_handler):
        """Test registering and using recovery callbacks."""
        # Register a mock recovery callback
        mock_callback = Mock(return_value=True)
        error_handler.register_recovery_callback(RecoveryAction.RETRY, mock_callback)
        
        # Create an error with retry recovery action
        error = NetworkError(
            message="Connection failed",
            error_code=ErrorCode.NETWORK_CONNECTION_FAILED,
            recovery_actions=[RecoveryAction.RETRY]
        )
        
        # Handle the error with auto-recovery
        error_handler.handle_error(error, auto_recover=True)
        
        # Verify callback was called
        mock_callback.assert_called_once()
    
    def test_error_display_modes(self, error_handler):
        """Test different error display modes."""
        # Test silent mode
        error_handler.set_display_mode(ErrorDisplayMode.SILENT)
        
        with patch.object(error_handler, '_show_error_notification') as mock_notification:
            error = ValidationError("Test error", field_name="test")
            error_handler._display_error_to_user(error)
            mock_notification.assert_not_called()
        
        # Test notification mode
        error_handler.set_display_mode(ErrorDisplayMode.NOTIFICATION)
        error_handler.set_system_tray_available(True)
        
        with patch.object(error_handler, '_show_error_notification') as mock_notification:
            error_handler._display_error_to_user(error)
            mock_notification.assert_called_once()
    
    def test_network_state_monitoring(self, error_handler):
        """Test network state monitoring and updates."""
        error_handler.network_state_changed = Mock()
        
        # Test state change
        error_handler._update_network_state(NetworkState.OFFLINE)
        
        assert error_handler._network_state == NetworkState.OFFLINE
        error_handler.network_state_changed.emit.assert_called_once_with(NetworkState.OFFLINE)
        
        # Test no change (should not emit signal)
        error_handler.network_state_changed.reset_mock()
        error_handler._update_network_state(NetworkState.OFFLINE)
        error_handler.network_state_changed.emit.assert_not_called()
    
    def test_error_history_management(self, error_handler):
        """Test error history tracking and management."""
        # Add multiple errors
        for i in range(5):
            error = ValidationError(f"Error {i}", field_name=f"field_{i}")
            error_handler.handle_error(error, auto_recover=False)
        
        assert len(error_handler._error_history) == 5
        
        # Test history retrieval
        history = error_handler.get_error_history()
        assert len(history) == 5
        assert history[0]['message'] == "Error 0"
        assert history[4]['message'] == "Error 4"
        
        # Test history clearing
        error_handler.clear_error_history()
        assert len(error_handler._error_history) == 0


class TestGracefulDegradation:
    """Test graceful degradation functionality."""
    
    def test_system_tray_unavailable_handling(self):
        """Test handling when system tray is unavailable."""
        with patch('client.error_handling.QObject'):
            error_handler = ClientErrorHandler()
            
            # Simulate system tray unavailable
            error_handler.handle_system_tray_unavailable()
            
            assert not error_handler._system_tray_available
            assert len(error_handler._error_history) == 1
            
            history_entry = error_handler._error_history[0]
            assert history_entry['error_code'] == ErrorCode.SYSTEM_TRAY_UNAVAILABLE.value
    
    @patch('client.qt.application.QSystemTrayIcon.isSystemTrayAvailable')
    def test_qt_application_fallback_mode(self, mock_tray_available):
        """Test Qt application fallback mode when system tray is unavailable."""
        mock_tray_available.return_value = False
        
        with patch('client.qt.application.QApplication'):
            with patch('client.qt.application.QMessageBox'):
                from client.qt.application import PacmanSyncApplication
                
                app = PacmanSyncApplication([])
                
                # Verify fallback mode was set up
                assert app._status_indicator is None
                assert hasattr(app, '_status_file')
    
    def test_network_error_graceful_degradation(self):
        """Test graceful degradation for network errors."""
        with patch('client.error_handling.QObject'):
            error_handler = ClientErrorHandler()
            error_handler.network_state_changed = Mock()
            
            # Simulate network error
            network_error = ConnectionError("Network unreachable")
            
            # Handle with graceful degradation
            error_handler.handle_network_error(
                network_error,
                retry_callback=Mock(),
                context={'operation': 'sync'}
            )
            
            # Verify network state was updated
            assert error_handler._network_state == NetworkState.OFFLINE
            error_handler.network_state_changed.emit.assert_called_with(NetworkState.OFFLINE)


class TestIntegration:
    """Integration tests for error handling components."""
    
    def test_end_to_end_error_handling(self):
        """Test complete error handling flow from exception to user notification."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = os.path.join(temp_dir, 'test.log')
            audit_file = os.path.join(temp_dir, 'audit.log')
            
            # Set up logging
            setup_logging(
                log_level=LogLevel.INFO,
                log_format=LogFormat.JSON,
                log_file=log_file,
                enable_console=False,
                enable_audit=True,
                audit_file=audit_file
            )
            
            # Set up error handler
            with patch('client.error_handling.QObject'):
                error_handler = ClientErrorHandler()
                error_handler.set_system_tray_available(False)
                
                # Create and handle an error
                original_error = ConnectionError("Database connection failed")
                
                success = error_handler.handle_error(
                    original_error,
                    context={'database': 'postgresql', 'host': 'localhost'},
                    endpoint_id='test-endpoint-123',
                    operation_id='op-456'
                )
                
                assert success
                
                # Verify error was logged
                assert os.path.exists(log_file)
                assert os.path.exists(audit_file)
                
                # Verify error history
                history = error_handler.get_error_history()
                assert len(history) == 1
                assert 'Database connection failed' in history[0]['message']
                assert history[0]['additional_context']['database'] == 'postgresql'
    
    def test_server_api_error_response_format(self):
        """Test that server API returns properly formatted error responses."""
        # Create a structured error
        error = ValidationError(
            message="Invalid endpoint name format",
            field_name="endpoint_name",
            context={
                'provided_value': 'invalid@name',
                'expected_pattern': r'^[a-zA-Z0-9._-]+$'
            }
        )
        
        # Create error response
        response = create_error_response(error)
        
        # Verify response structure
        assert 'error' in response
        assert 'code' in response['error']
        assert 'message' in response['error']
        assert 'timestamp' in response['error']
        assert 'context' in response['error']
        assert 'recovery_actions' in response['error']
        
        # Verify content
        assert response['error']['code'] == ErrorCode.VALIDATION_INVALID_INPUT.value
        assert response['error']['message'] == "Invalid endpoint name format"
        assert response['error']['context']['field_name'] == 'endpoint_name'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])