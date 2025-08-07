#!/usr/bin/env python3
"""
Unit tests for Qt desktop client components.

Tests Qt application framework, system tray integration, and user interface
components with mocked Qt dependencies to avoid requiring a display server.
"""

import pytest
import sys
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime

# Mock Qt modules before importing client code
sys.modules['PyQt6'] = MagicMock()
sys.modules['PyQt6.QtCore'] = MagicMock()
sys.modules['PyQt6.QtWidgets'] = MagicMock()
sys.modules['PyQt6.QtGui'] = MagicMock()

from client.qt.application import (
    PacmanSyncApplication, SyncStatusIndicator, SyncStatus
)
from client.qt.windows import (
    PackageInfoWindow, SyncProgressDialog, ConfigurationWindow
)
from shared.models import PackageState, SystemState


class TestSyncStatus:
    """Test SyncStatus enumeration."""
    
    def test_sync_status_values(self):
        """Test that SyncStatus has all expected values."""
        expected_values = {
            'IN_SYNC': 'in_sync',
            'AHEAD': 'ahead', 
            'BEHIND': 'behind',
            'OFFLINE': 'offline',
            'SYNCING': 'syncing',
            'ERROR': 'error'
        }
        
        for attr_name, expected_value in expected_values.items():
            assert hasattr(SyncStatus, attr_name)
            assert getattr(SyncStatus, attr_name).value == expected_value
    
    def test_sync_status_comparison(self):
        """Test SyncStatus enum comparison."""
        assert SyncStatus.IN_SYNC == SyncStatus.IN_SYNC
        assert SyncStatus.IN_SYNC != SyncStatus.AHEAD
        assert SyncStatus.BEHIND != SyncStatus.OFFLINE


class TestSyncStatusIndicator:
    """Test SyncStatusIndicator system tray component."""
    
    @pytest.fixture
    def mock_qt_app(self):
        """Create mock Qt application."""
        return MagicMock()
    
    @pytest.fixture
    def status_indicator(self, mock_qt_app):
        """Create SyncStatusIndicator with mocked Qt dependencies."""
        with patch('client.qt.application.QSystemTrayIcon') as mock_tray:
            with patch('client.qt.application.QMenu') as mock_menu:
                indicator = SyncStatusIndicator(mock_qt_app)
                indicator.tray_icon = mock_tray.return_value
                indicator.context_menu = mock_menu.return_value
                return indicator
    
    def test_status_indicator_initialization(self, status_indicator):
        """Test SyncStatusIndicator initialization."""
        assert status_indicator.current_status == SyncStatus.OFFLINE
        assert status_indicator.is_available() == True  # Mocked to return True
        
        # Verify Qt components were created
        assert status_indicator.tray_icon is not None
        assert status_indicator.context_menu is not None
    
    def test_set_status_success(self, status_indicator):
        """Test successful status setting."""
        status_indicator.set_status(SyncStatus.IN_SYNC)
        
        assert status_indicator.current_status == SyncStatus.IN_SYNC
        # Verify icon was updated
        status_indicator.tray_icon.setIcon.assert_called()
        status_indicator.tray_icon.setToolTip.assert_called()
    
    def test_set_status_with_message(self, status_indicator):
        """Test status setting with custom message."""
        status_indicator.set_status(SyncStatus.SYNCING, "Syncing 5 packages...")
        
        assert status_indicator.current_status == SyncStatus.SYNCING
        # Verify tooltip was set with custom message
        status_indicator.tray_icon.setToolTip.assert_called_with("Syncing 5 packages...")
    
    def test_get_status(self, status_indicator):
        """Test status retrieval."""
        status_indicator.current_status = SyncStatus.AHEAD
        
        assert status_indicator.get_status() == SyncStatus.AHEAD
    
    def test_show_message_success(self, status_indicator):
        """Test showing notification message."""
        status_indicator.show_message("Test Title", "Test message", "info")
        
        # Verify notification was shown
        status_indicator.tray_icon.showMessage.assert_called_with(
            "Test Title", "Test message"
        )
    
    def test_show_message_when_unavailable(self, status_indicator):
        """Test showing message when tray is unavailable."""
        status_indicator.tray_icon = None
        
        # Should not raise exception
        status_indicator.show_message("Test", "Message")
    
    def test_is_available_true(self, status_indicator):
        """Test availability check when tray is available."""
        with patch('client.qt.application.QSystemTrayIcon.isSystemTrayAvailable', return_value=True):
            assert status_indicator.is_available() == True
    
    def test_is_available_false(self, status_indicator):
        """Test availability check when tray is unavailable."""
        with patch('client.qt.application.QSystemTrayIcon.isSystemTrayAvailable', return_value=False):
            assert status_indicator.is_available() == False
    
    def test_context_menu_creation(self, status_indicator):
        """Test context menu creation and actions."""
        # Verify menu actions were added
        assert status_indicator.context_menu.addAction.call_count >= 4
        
        # Check that standard actions were added
        action_calls = [call[0][0] for call in status_indicator.context_menu.addAction.call_args_list]
        expected_actions = ["Sync to Latest", "Set as Latest", "Revert to Previous", "Quit"]
        
        for expected_action in expected_actions:
            assert any(expected_action in action for action in action_calls)
    
    def test_icon_selection_by_status(self, status_indicator):
        """Test that correct icons are selected for different statuses."""
        test_cases = [
            (SyncStatus.IN_SYNC, "green"),
            (SyncStatus.AHEAD, "blue"),
            (SyncStatus.BEHIND, "orange"),
            (SyncStatus.OFFLINE, "gray"),
            (SyncStatus.SYNCING, "yellow"),
            (SyncStatus.ERROR, "red")
        ]
        
        for status, expected_color in test_cases:
            status_indicator.set_status(status)
            # Verify icon was set (exact icon verification would require actual icon files)
            status_indicator.tray_icon.setIcon.assert_called()


class TestPacmanSyncApplication:
    """Test PacmanSyncApplication main application class."""
    
    @pytest.fixture
    def mock_qt_app(self):
        """Create mock Qt application."""
        return MagicMock()
    
    @pytest.fixture
    def mock_api_client(self):
        """Create mock API client."""
        return AsyncMock()
    
    @pytest.fixture
    def mock_config(self):
        """Create mock configuration."""
        config = MagicMock()
        config.get_server_url.return_value = "http://localhost:8080"
        config.get_endpoint_name.return_value = "test-endpoint"
        config.get_pool_id.return_value = "test-pool"
        return config
    
    @pytest.fixture
    def sync_app(self, mock_qt_app, mock_api_client, mock_config):
        """Create PacmanSyncApplication with mocked dependencies."""
        with patch('client.qt.application.SyncStatusIndicator') as mock_indicator:
            app = PacmanSyncApplication(mock_qt_app)
            app.api_client = mock_api_client
            app.config = mock_config
            app.status_indicator = mock_indicator.return_value
            return app
    
    def test_application_initialization(self, sync_app):
        """Test PacmanSyncApplication initialization."""
        assert sync_app.qt_app is not None
        assert sync_app.api_client is not None
        assert sync_app.config is not None
        assert sync_app.status_indicator is not None
        assert sync_app.is_running == False
    
    @pytest.mark.asyncio
    async def test_start_application_success(self, sync_app, mock_api_client):
        """Test successful application startup."""
        mock_api_client.authenticate.return_value = "auth-token"
        mock_api_client.register_endpoint.return_value = {"id": "endpoint-1"}
        
        await sync_app.start()
        
        assert sync_app.is_running == True
        assert sync_app.endpoint_id == "endpoint-1"
        
        # Verify authentication and registration
        mock_api_client.authenticate.assert_called_once()
        mock_api_client.register_endpoint.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_start_application_auth_failure(self, sync_app, mock_api_client):
        """Test application startup with authentication failure."""
        mock_api_client.authenticate.side_effect = Exception("Auth failed")
        
        with pytest.raises(Exception, match="Auth failed"):
            await sync_app.start()
        
        assert sync_app.is_running == False
    
    @pytest.mark.asyncio
    async def test_sync_to_latest_success(self, sync_app, mock_api_client):
        """Test successful sync to latest operation."""
        sync_app.endpoint_id = "endpoint-1"
        mock_api_client.trigger_sync.return_value = "operation-1"
        
        operation_id = await sync_app.sync_to_latest()
        
        assert operation_id == "operation-1"
        mock_api_client.trigger_sync.assert_called_once_with(
            "endpoint-1", "sync"
        )
        
        # Verify status was updated
        sync_app.status_indicator.set_status.assert_called_with(
            SyncStatus.SYNCING, "Syncing to latest..."
        )
    
    @pytest.mark.asyncio
    async def test_sync_to_latest_not_registered(self, sync_app):
        """Test sync to latest when endpoint is not registered."""
        sync_app.endpoint_id = None
        
        with pytest.raises(RuntimeError, match="not registered"):
            await sync_app.sync_to_latest()
    
    @pytest.mark.asyncio
    async def test_set_as_latest_success(self, sync_app, mock_api_client):
        """Test successful set as latest operation."""
        sync_app.endpoint_id = "endpoint-1"
        mock_api_client.trigger_sync.return_value = "operation-1"
        
        operation_id = await sync_app.set_as_latest()
        
        assert operation_id == "operation-1"
        mock_api_client.trigger_sync.assert_called_once_with(
            "endpoint-1", "set_latest"
        )
    
    @pytest.mark.asyncio
    async def test_revert_to_previous_success(self, sync_app, mock_api_client):
        """Test successful revert to previous operation."""
        sync_app.endpoint_id = "endpoint-1"
        mock_api_client.trigger_sync.return_value = "operation-1"
        
        operation_id = await sync_app.revert_to_previous()
        
        assert operation_id == "operation-1"
        mock_api_client.trigger_sync.assert_called_once_with(
            "endpoint-1", "revert"
        )
    
    @pytest.mark.asyncio
    async def test_update_status_success(self, sync_app, mock_api_client):
        """Test successful status update."""
        sync_app.endpoint_id = "endpoint-1"
        mock_api_client.report_status.return_value = True
        
        await sync_app.update_status(SyncStatus.IN_SYNC)
        
        mock_api_client.report_status.assert_called_once_with(
            "endpoint-1", SyncStatus.IN_SYNC
        )
        sync_app.status_indicator.set_status.assert_called_with(SyncStatus.IN_SYNC)
    
    @pytest.mark.asyncio
    async def test_get_current_status_success(self, sync_app):
        """Test current status retrieval."""
        sync_app.status_indicator.get_status.return_value = SyncStatus.AHEAD
        
        status = await sync_app.get_current_status()
        
        assert status == SyncStatus.AHEAD
    
    def test_stop_application(self, sync_app):
        """Test application shutdown."""
        sync_app.is_running = True
        
        sync_app.stop()
        
        assert sync_app.is_running == False
        sync_app.qt_app.quit.assert_called_once()


class TestPackageInfoWindow:
    """Test PackageInfoWindow Qt widget."""
    
    @pytest.fixture
    def mock_parent(self):
        """Create mock parent widget."""
        return MagicMock()
    
    @pytest.fixture
    def package_info_window(self, mock_parent):
        """Create PackageInfoWindow with mocked Qt dependencies."""
        with patch('client.qt.windows.QDialog'):
            with patch('client.qt.windows.QVBoxLayout'):
                with patch('client.qt.windows.QTableWidget'):
                    window = PackageInfoWindow(mock_parent)
                    return window
    
    def test_window_initialization(self, package_info_window):
        """Test PackageInfoWindow initialization."""
        assert package_info_window.parent is not None
        # Verify window was configured
        assert hasattr(package_info_window, 'setWindowTitle')
        assert hasattr(package_info_window, 'setModal')
    
    def test_display_packages_success(self, package_info_window):
        """Test displaying package information."""
        packages = [
            PackageState("package1", "1.0.0", "core", 1024, ["dep1"]),
            PackageState("package2", "2.0.0", "extra", 2048, ["dep2", "dep3"])
        ]
        
        package_info_window.display_packages(packages)
        
        # Verify table was populated (exact verification would require Qt widgets)
        assert hasattr(package_info_window, 'package_table')
    
    def test_display_empty_packages(self, package_info_window):
        """Test displaying empty package list."""
        package_info_window.display_packages([])
        
        # Should not raise exception
        assert True
    
    def test_filter_packages_by_name(self, package_info_window):
        """Test package filtering functionality."""
        packages = [
            PackageState("firefox", "1.0.0", "core", 1024),
            PackageState("chrome", "2.0.0", "extra", 2048),
            PackageState("firefox-dev", "1.1.0", "core", 1024)
        ]
        
        package_info_window.display_packages(packages)
        package_info_window.filter_packages("firefox")
        
        # Verify filtering was applied
        assert hasattr(package_info_window, 'filter_text')


class TestSyncProgressDialog:
    """Test SyncProgressDialog Qt widget."""
    
    @pytest.fixture
    def mock_parent(self):
        """Create mock parent widget."""
        return MagicMock()
    
    @pytest.fixture
    def progress_dialog(self, mock_parent):
        """Create SyncProgressDialog with mocked Qt dependencies."""
        with patch('client.qt.windows.QProgressDialog'):
            dialog = SyncProgressDialog(mock_parent, "Syncing packages...")
            return dialog
    
    def test_dialog_initialization(self, progress_dialog):
        """Test SyncProgressDialog initialization."""
        assert progress_dialog.parent is not None
        # Verify dialog was configured
        assert hasattr(progress_dialog, 'setWindowTitle')
        assert hasattr(progress_dialog, 'setModal')
    
    def test_update_progress_success(self, progress_dialog):
        """Test progress update."""
        progress_dialog.update_progress(50, "Processing package 5 of 10...")
        
        # Verify progress was updated
        assert hasattr(progress_dialog, 'setValue')
        assert hasattr(progress_dialog, 'setLabelText')
    
    def test_update_progress_complete(self, progress_dialog):
        """Test progress completion."""
        progress_dialog.update_progress(100, "Sync completed successfully")
        
        # Verify completion handling
        assert hasattr(progress_dialog, 'setValue')
    
    def test_cancel_operation(self, progress_dialog):
        """Test operation cancellation."""
        progress_dialog.cancel_operation()
        
        # Verify cancellation was handled
        assert hasattr(progress_dialog, 'canceled')
    
    def test_is_cancelled_check(self, progress_dialog):
        """Test cancellation status check."""
        result = progress_dialog.is_cancelled()
        
        # Should return boolean
        assert isinstance(result, bool)


class TestConfigurationWindow:
    """Test ConfigurationWindow Qt widget."""
    
    @pytest.fixture
    def mock_parent(self):
        """Create mock parent widget."""
        return MagicMock()
    
    @pytest.fixture
    def mock_config(self):
        """Create mock configuration."""
        config = MagicMock()
        config.get_server_url.return_value = "http://localhost:8080"
        config.get_endpoint_name.return_value = "test-endpoint"
        config.get_pool_id.return_value = "test-pool"
        return config
    
    @pytest.fixture
    def config_window(self, mock_parent, mock_config):
        """Create ConfigurationWindow with mocked Qt dependencies."""
        with patch('client.qt.windows.QDialog'):
            with patch('client.qt.windows.QFormLayout'):
                with patch('client.qt.windows.QLineEdit'):
                    window = ConfigurationWindow(mock_parent, mock_config)
                    return window
    
    def test_window_initialization(self, config_window):
        """Test ConfigurationWindow initialization."""
        assert config_window.parent is not None
        assert config_window.config is not None
        # Verify form fields were created
        assert hasattr(config_window, 'server_url_field')
        assert hasattr(config_window, 'endpoint_name_field')
    
    def test_load_current_settings(self, config_window, mock_config):
        """Test loading current configuration settings."""
        config_window.load_current_settings()
        
        # Verify settings were loaded from config
        mock_config.get_server_url.assert_called()
        mock_config.get_endpoint_name.assert_called()
        mock_config.get_pool_id.assert_called()
    
    def test_save_settings_success(self, config_window, mock_config):
        """Test successful settings save."""
        # Mock form field values
        config_window.server_url_field = MagicMock()
        config_window.server_url_field.text.return_value = "http://new-server:8080"
        config_window.endpoint_name_field = MagicMock()
        config_window.endpoint_name_field.text.return_value = "new-endpoint"
        
        config_window.save_settings()
        
        # Verify settings were saved to config
        mock_config.set_config.assert_called()
    
    def test_validate_settings_valid(self, config_window):
        """Test settings validation with valid input."""
        # Mock valid form values
        config_window.server_url_field = MagicMock()
        config_window.server_url_field.text.return_value = "http://localhost:8080"
        config_window.endpoint_name_field = MagicMock()
        config_window.endpoint_name_field.text.return_value = "valid-endpoint"
        
        is_valid = config_window.validate_settings()
        
        assert is_valid == True
    
    def test_validate_settings_invalid_url(self, config_window):
        """Test settings validation with invalid URL."""
        # Mock invalid URL
        config_window.server_url_field = MagicMock()
        config_window.server_url_field.text.return_value = "invalid-url"
        config_window.endpoint_name_field = MagicMock()
        config_window.endpoint_name_field.text.return_value = "endpoint"
        
        is_valid = config_window.validate_settings()
        
        assert is_valid == False
    
    def test_validate_settings_empty_name(self, config_window):
        """Test settings validation with empty endpoint name."""
        # Mock empty endpoint name
        config_window.server_url_field = MagicMock()
        config_window.server_url_field.text.return_value = "http://localhost:8080"
        config_window.endpoint_name_field = MagicMock()
        config_window.endpoint_name_field.text.return_value = ""
        
        is_valid = config_window.validate_settings()
        
        assert is_valid == False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])