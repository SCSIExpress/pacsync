#!/usr/bin/env python3
"""
Unit tests for REST API endpoints.

Tests all API endpoint functionality including pool management,
endpoint management, and synchronization operations.
"""

import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from server.api.endpoints import app
from shared.models import (
    PackagePool, Endpoint, SyncOperation, CompatibilityAnalysis,
    SyncStatus, OperationType, OperationStatus, SyncPolicy, ConflictResolution
)
from server.database.orm import ValidationError, NotFoundError


class TestPoolEndpoints:
    """Test pool management API endpoints."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        app.config['TESTING'] = True
        with app.test_client() as client:
            yield client
    
    @pytest.fixture
    def mock_pool_manager(self):
        """Create mock pool manager."""
        return AsyncMock()
    
    def test_create_pool_success(self, client, mock_pool_manager):
        """Test successful pool creation."""
        # Setup mock
        expected_pool = PackagePool(
            id="pool-1",
            name="Test Pool",
            description="Test description"
        )
        mock_pool_manager.create_pool.return_value = expected_pool
        
        # Mock the pool manager in the app
        with patch('server.api.endpoints.pool_manager', mock_pool_manager):
            response = client.post('/api/pools', 
                                 json={
                                     'name': 'Test Pool',
                                     'description': 'Test description'
                                 })
        
        assert response.status_code == 201
        data = json.loads(response.data)
        assert data['id'] == 'pool-1'
        assert data['name'] == 'Test Pool'
        assert data['description'] == 'Test description'
        
        mock_pool_manager.create_pool.assert_called_once_with(
            'Test Pool', 'Test description', None
        )
    
    def test_create_pool_with_sync_policy(self, client, mock_pool_manager):
        """Test pool creation with custom sync policy."""
        expected_pool = PackagePool(
            id="pool-1",
            name="Test Pool",
            description="Test description",
            sync_policy=SyncPolicy(auto_sync=True, conflict_resolution=ConflictResolution.NEWEST)
        )
        mock_pool_manager.create_pool.return_value = expected_pool
        
        with patch('server.api.endpoints.pool_manager', mock_pool_manager):
            response = client.post('/api/pools', 
                                 json={
                                     'name': 'Test Pool',
                                     'description': 'Test description',
                                     'sync_policy': {
                                         'auto_sync': True,
                                         'exclude_packages': [],
                                         'include_aur': False,
                                         'conflict_resolution': 'newest'
                                     }
                                 })
        
        assert response.status_code == 201
        
        # Verify sync policy was passed correctly
        call_args = mock_pool_manager.create_pool.call_args
        sync_policy = call_args[0][2]  # Third argument
        assert sync_policy.auto_sync == True
        assert sync_policy.conflict_resolution == ConflictResolution.NEWEST
    
    def test_create_pool_missing_name(self, client):
        """Test pool creation with missing name."""
        response = client.post('/api/pools', json={'description': 'Test description'})
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data
        assert 'name' in data['error'].lower()
    
    def test_create_pool_validation_error(self, client, mock_pool_manager):
        """Test pool creation with validation error."""
        mock_pool_manager.create_pool.side_effect = ValidationError("Pool name already exists")
        
        with patch('server.api.endpoints.pool_manager', mock_pool_manager):
            response = client.post('/api/pools', 
                                 json={'name': 'Duplicate Pool', 'description': 'Test'})
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data
        assert 'already exists' in data['error']
    
    def test_get_pool_success(self, client, mock_pool_manager):
        """Test successful pool retrieval."""
        expected_pool = PackagePool(
            id="pool-1",
            name="Test Pool",
            description="Test description",
            endpoints=["endpoint-1", "endpoint-2"]
        )
        mock_pool_manager.get_pool.return_value = expected_pool
        
        with patch('server.api.endpoints.pool_manager', mock_pool_manager):
            response = client.get('/api/pools/pool-1')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['id'] == 'pool-1'
        assert data['name'] == 'Test Pool'
        assert len(data['endpoints']) == 2
    
    def test_get_pool_not_found(self, client, mock_pool_manager):
        """Test pool retrieval when pool doesn't exist."""
        mock_pool_manager.get_pool.return_value = None
        
        with patch('server.api.endpoints.pool_manager', mock_pool_manager):
            response = client.get('/api/pools/non-existent')
        
        assert response.status_code == 404
        data = json.loads(response.data)
        assert 'error' in data
        assert 'not found' in data['error'].lower()
    
    def test_list_pools_success(self, client, mock_pool_manager):
        """Test successful pool listing."""
        pools = [
            PackagePool("pool-1", "Pool 1", "Description 1"),
            PackagePool("pool-2", "Pool 2", "Description 2")
        ]
        mock_pool_manager.list_pools.return_value = pools
        
        with patch('server.api.endpoints.pool_manager', mock_pool_manager):
            response = client.get('/api/pools')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert len(data) == 2
        assert data[0]['name'] == 'Pool 1'
        assert data[1]['name'] == 'Pool 2'
    
    def test_update_pool_success(self, client, mock_pool_manager):
        """Test successful pool update."""
        updated_pool = PackagePool(
            id="pool-1",
            name="Updated Pool",
            description="Updated description"
        )
        mock_pool_manager.update_pool.return_value = updated_pool
        
        with patch('server.api.endpoints.pool_manager', mock_pool_manager):
            response = client.put('/api/pools/pool-1', 
                                json={
                                    'name': 'Updated Pool',
                                    'description': 'Updated description'
                                })
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['name'] == 'Updated Pool'
        assert data['description'] == 'Updated description'
        
        mock_pool_manager.update_pool.assert_called_once_with(
            'pool-1', name='Updated Pool', description='Updated description'
        )
    
    def test_update_pool_not_found(self, client, mock_pool_manager):
        """Test pool update when pool doesn't exist."""
        mock_pool_manager.update_pool.side_effect = NotFoundError("Pool not found")
        
        with patch('server.api.endpoints.pool_manager', mock_pool_manager):
            response = client.put('/api/pools/non-existent', 
                                json={'name': 'Updated Pool'})
        
        assert response.status_code == 404
        data = json.loads(response.data)
        assert 'error' in data
        assert 'not found' in data['error'].lower()
    
    def test_delete_pool_success(self, client, mock_pool_manager):
        """Test successful pool deletion."""
        mock_pool_manager.delete_pool.return_value = True
        
        with patch('server.api.endpoints.pool_manager', mock_pool_manager):
            response = client.delete('/api/pools/pool-1')
        
        assert response.status_code == 204
        mock_pool_manager.delete_pool.assert_called_once_with('pool-1')
    
    def test_delete_pool_not_found(self, client, mock_pool_manager):
        """Test pool deletion when pool doesn't exist."""
        mock_pool_manager.delete_pool.return_value = False
        
        with patch('server.api.endpoints.pool_manager', mock_pool_manager):
            response = client.delete('/api/pools/non-existent')
        
        assert response.status_code == 404
        data = json.loads(response.data)
        assert 'error' in data
        assert 'not found' in data['error'].lower()


class TestEndpointEndpoints:
    """Test endpoint management API endpoints."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        app.config['TESTING'] = True
        with app.test_client() as client:
            yield client
    
    @pytest.fixture
    def mock_endpoint_manager(self):
        """Create mock endpoint manager."""
        return AsyncMock()
    
    def test_register_endpoint_success(self, client, mock_endpoint_manager):
        """Test successful endpoint registration."""
        expected_endpoint = Endpoint(
            id="endpoint-1",
            name="Test Endpoint",
            hostname="test-host"
        )
        mock_endpoint_manager.register_endpoint.return_value = expected_endpoint
        
        with patch('server.api.endpoints.endpoint_manager', mock_endpoint_manager):
            response = client.post('/api/endpoints', 
                                 json={
                                     'name': 'Test Endpoint',
                                     'hostname': 'test-host'
                                 })
        
        assert response.status_code == 201
        data = json.loads(response.data)
        assert data['id'] == 'endpoint-1'
        assert data['name'] == 'Test Endpoint'
        assert data['hostname'] == 'test-host'
        
        mock_endpoint_manager.register_endpoint.assert_called_once_with(
            'Test Endpoint', 'test-host'
        )
    
    def test_register_endpoint_missing_fields(self, client):
        """Test endpoint registration with missing required fields."""
        response = client.post('/api/endpoints', json={'name': 'Test Endpoint'})
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data
        assert 'hostname' in data['error'].lower()
    
    def test_get_endpoint_success(self, client, mock_endpoint_manager):
        """Test successful endpoint retrieval."""
        expected_endpoint = Endpoint(
            id="endpoint-1",
            name="Test Endpoint",
            hostname="test-host",
            pool_id="pool-1",
            sync_status=SyncStatus.IN_SYNC
        )
        mock_endpoint_manager.get_endpoint.return_value = expected_endpoint
        
        with patch('server.api.endpoints.endpoint_manager', mock_endpoint_manager):
            response = client.get('/api/endpoints/endpoint-1')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['id'] == 'endpoint-1'
        assert data['name'] == 'Test Endpoint'
        assert data['pool_id'] == 'pool-1'
        assert data['sync_status'] == 'in_sync'
    
    def test_get_endpoint_not_found(self, client, mock_endpoint_manager):
        """Test endpoint retrieval when endpoint doesn't exist."""
        mock_endpoint_manager.get_endpoint.return_value = None
        
        with patch('server.api.endpoints.endpoint_manager', mock_endpoint_manager):
            response = client.get('/api/endpoints/non-existent')
        
        assert response.status_code == 404
        data = json.loads(response.data)
        assert 'error' in data
        assert 'not found' in data['error'].lower()
    
    def test_list_endpoints_success(self, client, mock_endpoint_manager):
        """Test successful endpoint listing."""
        endpoints = [
            Endpoint("endpoint-1", "Endpoint 1", "host1"),
            Endpoint("endpoint-2", "Endpoint 2", "host2")
        ]
        mock_endpoint_manager.list_endpoints.return_value = endpoints
        
        with patch('server.api.endpoints.endpoint_manager', mock_endpoint_manager):
            response = client.get('/api/endpoints')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert len(data) == 2
        assert data[0]['name'] == 'Endpoint 1'
        assert data[1]['name'] == 'Endpoint 2'
    
    def test_list_endpoints_by_pool(self, client, mock_endpoint_manager):
        """Test endpoint listing filtered by pool."""
        endpoints = [
            Endpoint("endpoint-1", "Endpoint 1", "host1", pool_id="pool-1")
        ]
        mock_endpoint_manager.list_endpoints.return_value = endpoints
        
        with patch('server.api.endpoints.endpoint_manager', mock_endpoint_manager):
            response = client.get('/api/endpoints?pool_id=pool-1')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert len(data) == 1
        assert data[0]['pool_id'] == 'pool-1'
        
        mock_endpoint_manager.list_endpoints.assert_called_once_with(pool_id='pool-1')
    
    def test_update_endpoint_status_success(self, client, mock_endpoint_manager):
        """Test successful endpoint status update."""
        mock_endpoint_manager.update_endpoint_status.return_value = True
        
        with patch('server.api.endpoints.endpoint_manager', mock_endpoint_manager):
            response = client.put('/api/endpoints/endpoint-1', 
                                json={'sync_status': 'in_sync'})
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] == True
        
        mock_endpoint_manager.update_endpoint_status.assert_called_once_with(
            'endpoint-1', SyncStatus.IN_SYNC
        )
    
    def test_update_endpoint_invalid_status(self, client):
        """Test endpoint status update with invalid status."""
        response = client.put('/api/endpoints/endpoint-1', 
                            json={'sync_status': 'invalid_status'})
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data
        assert 'invalid' in data['error'].lower()
    
    def test_remove_endpoint_success(self, client, mock_endpoint_manager):
        """Test successful endpoint removal."""
        mock_endpoint_manager.remove_endpoint.return_value = True
        
        with patch('server.api.endpoints.endpoint_manager', mock_endpoint_manager):
            response = client.delete('/api/endpoints/endpoint-1')
        
        assert response.status_code == 204
        mock_endpoint_manager.remove_endpoint.assert_called_once_with('endpoint-1')
    
    def test_remove_endpoint_not_found(self, client, mock_endpoint_manager):
        """Test endpoint removal when endpoint doesn't exist."""
        mock_endpoint_manager.remove_endpoint.return_value = False
        
        with patch('server.api.endpoints.endpoint_manager', mock_endpoint_manager):
            response = client.delete('/api/endpoints/non-existent')
        
        assert response.status_code == 404
        data = json.loads(response.data)
        assert 'error' in data
        assert 'not found' in data['error'].lower()


class TestSyncEndpoints:
    """Test synchronization operation API endpoints."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        app.config['TESTING'] = True
        with app.test_client() as client:
            yield client
    
    @pytest.fixture
    def mock_sync_coordinator(self):
        """Create mock sync coordinator."""
        return AsyncMock()
    
    def test_sync_endpoint_success(self, client, mock_sync_coordinator):
        """Test successful endpoint sync operation."""
        expected_operation = SyncOperation(
            id="op-1",
            pool_id="pool-1",
            endpoint_id="endpoint-1",
            operation_type=OperationType.SYNC,
            status=OperationStatus.PENDING
        )
        mock_sync_coordinator.sync_to_latest.return_value = expected_operation
        
        with patch('server.api.endpoints.sync_coordinator', mock_sync_coordinator):
            response = client.post('/api/endpoints/endpoint-1/sync')
        
        assert response.status_code == 202
        data = json.loads(response.data)
        assert data['id'] == 'op-1'
        assert data['operation_type'] == 'sync'
        assert data['status'] == 'pending'
        
        mock_sync_coordinator.sync_to_latest.assert_called_once_with('endpoint-1')
    
    def test_sync_endpoint_validation_error(self, client, mock_sync_coordinator):
        """Test endpoint sync with validation error."""
        mock_sync_coordinator.sync_to_latest.side_effect = ValidationError(
            "Endpoint not assigned to a pool"
        )
        
        with patch('server.api.endpoints.sync_coordinator', mock_sync_coordinator):
            response = client.post('/api/endpoints/endpoint-1/sync')
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data
        assert 'not assigned' in data['error']
    
    def test_set_latest_endpoint_success(self, client, mock_sync_coordinator):
        """Test successful set-latest operation."""
        expected_operation = SyncOperation(
            id="op-1",
            pool_id="pool-1",
            endpoint_id="endpoint-1",
            operation_type=OperationType.SET_LATEST,
            status=OperationStatus.PENDING
        )
        mock_sync_coordinator.set_as_latest.return_value = expected_operation
        
        with patch('server.api.endpoints.sync_coordinator', mock_sync_coordinator):
            response = client.post('/api/endpoints/endpoint-1/set-latest')
        
        assert response.status_code == 202
        data = json.loads(response.data)
        assert data['operation_type'] == 'set_latest'
        
        mock_sync_coordinator.set_as_latest.assert_called_once_with('endpoint-1')
    
    def test_revert_endpoint_success(self, client, mock_sync_coordinator):
        """Test successful revert operation."""
        expected_operation = SyncOperation(
            id="op-1",
            pool_id="pool-1",
            endpoint_id="endpoint-1",
            operation_type=OperationType.REVERT,
            status=OperationStatus.PENDING
        )
        mock_sync_coordinator.revert_to_previous.return_value = expected_operation
        
        with patch('server.api.endpoints.sync_coordinator', mock_sync_coordinator):
            response = client.post('/api/endpoints/endpoint-1/revert')
        
        assert response.status_code == 202
        data = json.loads(response.data)
        assert data['operation_type'] == 'revert'
        
        mock_sync_coordinator.revert_to_previous.assert_called_once_with('endpoint-1')
    
    def test_get_operation_status_success(self, client, mock_sync_coordinator):
        """Test successful operation status retrieval."""
        expected_operation = SyncOperation(
            id="op-1",
            pool_id="pool-1",
            endpoint_id="endpoint-1",
            operation_type=OperationType.SYNC,
            status=OperationStatus.COMPLETED,
            completed_at=datetime.now()
        )
        mock_sync_coordinator.get_operation_status.return_value = expected_operation
        
        with patch('server.api.endpoints.sync_coordinator', mock_sync_coordinator):
            response = client.get('/api/operations/op-1')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['id'] == 'op-1'
        assert data['status'] == 'completed'
        assert 'completed_at' in data
    
    def test_get_operation_status_not_found(self, client, mock_sync_coordinator):
        """Test operation status retrieval when operation doesn't exist."""
        mock_sync_coordinator.get_operation_status.return_value = None
        
        with patch('server.api.endpoints.sync_coordinator', mock_sync_coordinator):
            response = client.get('/api/operations/non-existent')
        
        assert response.status_code == 404
        data = json.loads(response.data)
        assert 'error' in data
        assert 'not found' in data['error'].lower()
    
    def test_cancel_operation_success(self, client, mock_sync_coordinator):
        """Test successful operation cancellation."""
        mock_sync_coordinator.cancel_operation.return_value = True
        
        with patch('server.api.endpoints.sync_coordinator', mock_sync_coordinator):
            response = client.delete('/api/operations/op-1')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] == True
        
        mock_sync_coordinator.cancel_operation.assert_called_once_with('op-1')
    
    def test_cancel_operation_failed(self, client, mock_sync_coordinator):
        """Test operation cancellation failure."""
        mock_sync_coordinator.cancel_operation.return_value = False
        
        with patch('server.api.endpoints.sync_coordinator', mock_sync_coordinator):
            response = client.delete('/api/operations/op-1')
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data


class TestRepositoryEndpoints:
    """Test repository analysis API endpoints."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        app.config['TESTING'] = True
        with app.test_client() as client:
            yield client
    
    @pytest.fixture
    def mock_repository_analyzer(self):
        """Create mock repository analyzer."""
        return AsyncMock()
    
    def test_get_repository_analysis_success(self, client, mock_repository_analyzer):
        """Test successful repository analysis retrieval."""
        expected_analysis = CompatibilityAnalysis(
            pool_id="pool-1",
            common_packages=[],
            excluded_packages=[],
            conflicts=[]
        )
        mock_repository_analyzer.analyze_pool_compatibility.return_value = expected_analysis
        
        with patch('server.api.endpoints.repository_analyzer', mock_repository_analyzer):
            response = client.get('/api/repositories?pool_id=pool-1')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['pool_id'] == 'pool-1'
        assert 'common_packages' in data
        assert 'excluded_packages' in data
        assert 'conflicts' in data
        
        mock_repository_analyzer.analyze_pool_compatibility.assert_called_once_with('pool-1')
    
    def test_get_repository_analysis_missing_pool_id(self, client):
        """Test repository analysis without pool_id parameter."""
        response = client.get('/api/repositories')
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data
        assert 'pool_id' in data['error'].lower()
    
    def test_trigger_repository_analysis_success(self, client, mock_repository_analyzer):
        """Test successful repository analysis trigger."""
        expected_analysis = CompatibilityAnalysis(
            pool_id="pool-1",
            common_packages=[],
            excluded_packages=[],
            conflicts=[]
        )
        mock_repository_analyzer.analyze_pool_compatibility.return_value = expected_analysis
        
        with patch('server.api.endpoints.repository_analyzer', mock_repository_analyzer):
            response = client.post('/api/repositories/analyze', 
                                 json={'pool_id': 'pool-1'})
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['pool_id'] == 'pool-1'
        
        mock_repository_analyzer.analyze_pool_compatibility.assert_called_once_with('pool-1')


class TestHealthEndpoints:
    """Test health check API endpoints."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        app.config['TESTING'] = True
        with app.test_client() as client:
            yield client
    
    def test_health_check_success(self, client):
        """Test successful health check."""
        with patch('server.api.endpoints.db_manager') as mock_db:
            mock_db.is_connected.return_value = True
            
            response = client.get('/api/health')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'healthy'
        assert data['database'] == 'connected'
        assert 'timestamp' in data
    
    def test_health_check_database_disconnected(self, client):
        """Test health check with database disconnected."""
        with patch('server.api.endpoints.db_manager') as mock_db:
            mock_db.is_connected.return_value = False
            
            response = client.get('/api/health')
        
        assert response.status_code == 503
        data = json.loads(response.data)
        assert data['status'] == 'unhealthy'
        assert data['database'] == 'disconnected'


class TestErrorHandling:
    """Test API error handling."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        app.config['TESTING'] = True
        with app.test_client() as client:
            yield client
    
    def test_invalid_json_request(self, client):
        """Test handling of invalid JSON in request."""
        response = client.post('/api/pools', 
                             data='invalid json',
                             content_type='application/json')
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data
        assert 'json' in data['error'].lower()
    
    def test_method_not_allowed(self, client):
        """Test handling of unsupported HTTP methods."""
        response = client.patch('/api/pools/pool-1')
        
        assert response.status_code == 405
        data = json.loads(response.data)
        assert 'error' in data
        assert 'method not allowed' in data['error'].lower()
    
    def test_internal_server_error(self, client):
        """Test handling of internal server errors."""
        with patch('server.api.endpoints.pool_manager') as mock_pool_manager:
            mock_pool_manager.list_pools.side_effect = Exception("Database connection failed")
            
            response = client.get('/api/pools')
        
        assert response.status_code == 500
        data = json.loads(response.data)
        assert 'error' in data
        assert 'internal server error' in data['error'].lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])