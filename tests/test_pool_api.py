#!/usr/bin/env python3
"""
Test script for Pool Management API endpoints.

This script tests the pool CRUD operations, endpoint assignment,
and status retrieval functionality.
"""

import asyncio
import json
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

import httpx
import pytest
from fastapi.testclient import TestClient

from server.api.main import create_app


class TestPoolAPI:
    """Test class for Pool Management API endpoints."""
    
    def setup_method(self):
        """Set up test client."""
        self.app = create_app()
        self.client = TestClient(self.app)
    
    def test_health_check(self):
        """Test health check endpoint."""
        response = self.client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "pacman-sync-utility"
    
    def test_create_pool_success(self):
        """Test successful pool creation."""
        pool_data = {
            "name": "test-pool",
            "description": "Test pool for API testing",
            "sync_policy": {
                "auto_sync": False,
                "exclude_packages": ["test-package"],
                "include_aur": False,
                "conflict_resolution": "manual"
            }
        }
        
        response = self.client.post("/api/pools", json=pool_data)
        assert response.status_code == 201
        
        data = response.json()
        assert data["name"] == "test-pool"
        assert data["description"] == "Test pool for API testing"
        assert "id" in data
        assert data["sync_policy"]["auto_sync"] is False
        assert data["sync_policy"]["exclude_packages"] == ["test-package"]
        
        return data["id"]  # Return pool ID for other tests
    
    def test_create_pool_validation_error(self):
        """Test pool creation with validation errors."""
        # Empty name
        response = self.client.post("/api/pools", json={"name": ""})
        assert response.status_code == 422
        
        # Invalid conflict resolution
        pool_data = {
            "name": "test-pool",
            "sync_policy": {
                "conflict_resolution": "invalid"
            }
        }
        response = self.client.post("/api/pools", json=pool_data)
        assert response.status_code == 422
    
    def test_list_pools_empty(self):
        """Test listing pools when none exist."""
        response = self.client.get("/api/pools")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_get_pool_not_found(self):
        """Test getting a non-existent pool."""
        response = self.client.get("/api/pools/non-existent-id")
        assert response.status_code == 404
        data = response.json()
        assert "error" in data
    
    def test_pool_crud_workflow(self):
        """Test complete CRUD workflow for pools."""
        # Create pool
        pool_data = {
            "name": "crud-test-pool",
            "description": "Pool for CRUD testing"
        }
        
        create_response = self.client.post("/api/pools", json=pool_data)
        assert create_response.status_code == 201
        created_pool = create_response.json()
        pool_id = created_pool["id"]
        
        # Get pool
        get_response = self.client.get(f"/api/pools/{pool_id}")
        assert get_response.status_code == 200
        retrieved_pool = get_response.json()
        assert retrieved_pool["name"] == "crud-test-pool"
        assert retrieved_pool["id"] == pool_id
        
        # Update pool
        update_data = {
            "name": "updated-crud-test-pool",
            "description": "Updated description",
            "sync_policy": {
                "auto_sync": True,
                "conflict_resolution": "newest"
            }
        }
        
        update_response = self.client.put(f"/api/pools/{pool_id}", json=update_data)
        assert update_response.status_code == 200
        updated_pool = update_response.json()
        assert updated_pool["name"] == "updated-crud-test-pool"
        assert updated_pool["description"] == "Updated description"
        assert updated_pool["sync_policy"]["auto_sync"] is True
        
        # List pools (should contain our pool)
        list_response = self.client.get("/api/pools")
        assert list_response.status_code == 200
        pools = list_response.json()
        assert len(pools) >= 1
        assert any(pool["id"] == pool_id for pool in pools)
        
        # Delete pool
        delete_response = self.client.delete(f"/api/pools/{pool_id}")
        assert delete_response.status_code == 204
        
        # Verify deletion
        get_after_delete = self.client.get(f"/api/pools/{pool_id}")
        assert get_after_delete.status_code == 404
    
    def test_pool_status_endpoints(self):
        """Test pool status endpoints."""
        # Create a pool first
        pool_data = {"name": "status-test-pool"}
        create_response = self.client.post("/api/pools", json=pool_data)
        assert create_response.status_code == 201
        pool_id = create_response.json()["id"]
        
        # Get pool status
        status_response = self.client.get(f"/api/pools/{pool_id}/status")
        assert status_response.status_code == 200
        status_data = status_response.json()
        
        assert status_data["pool_id"] == pool_id
        assert status_data["pool_name"] == "status-test-pool"
        assert status_data["total_endpoints"] == 0
        assert status_data["overall_status"] == "empty"
        
        # List all pool statuses
        list_status_response = self.client.get("/api/pools/status")
        assert list_status_response.status_code == 200
        statuses = list_status_response.json()
        assert isinstance(statuses, list)
        assert any(status["pool_id"] == pool_id for status in statuses)
        
        # Clean up
        self.client.delete(f"/api/pools/{pool_id}")
    
    def test_endpoint_assignment_endpoints(self):
        """Test endpoint assignment endpoints."""
        # Create a pool first
        pool_data = {"name": "assignment-test-pool"}
        create_response = self.client.post("/api/pools", json=pool_data)
        assert create_response.status_code == 201
        pool_id = create_response.json()["id"]
        
        # Test assigning non-existent endpoint (should fail gracefully)
        assignment_data = {"endpoint_id": "non-existent-endpoint"}
        assign_response = self.client.post(f"/api/pools/{pool_id}/endpoints", json=assignment_data)
        assert assign_response.status_code == 400
        
        # Test removing non-existent endpoint (should fail gracefully)
        remove_response = self.client.delete(f"/api/pools/{pool_id}/endpoints/non-existent-endpoint")
        assert remove_response.status_code == 400
        
        # Test moving endpoint between pools (should fail with non-existent endpoints)
        move_response = self.client.put(f"/api/pools/{pool_id}/endpoints/non-existent/move/another-pool")
        assert move_response.status_code == 400
        
        # Clean up
        self.client.delete(f"/api/pools/{pool_id}")


def run_manual_tests():
    """Run manual tests for demonstration."""
    print("Running Pool Management API Tests...")
    
    # Create test instance
    test_instance = TestPoolAPI()
    test_instance.setup_method()
    
    try:
        # Run tests
        print("✓ Testing health check...")
        test_instance.test_health_check()
        
        print("✓ Testing pool creation...")
        test_instance.test_create_pool_success()
        
        print("✓ Testing validation errors...")
        test_instance.test_create_pool_validation_error()
        
        print("✓ Testing empty pool list...")
        test_instance.test_list_pools_empty()
        
        print("✓ Testing not found error...")
        test_instance.test_get_pool_not_found()
        
        print("✓ Testing CRUD workflow...")
        test_instance.test_pool_crud_workflow()
        
        print("✓ Testing status endpoints...")
        test_instance.test_pool_status_endpoints()
        
        print("✓ Testing endpoint assignment...")
        test_instance.test_endpoint_assignment_endpoints()
        
        print("\n🎉 All tests passed!")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


if __name__ == "__main__":
    success = run_manual_tests()
    sys.exit(0 if success else 1)