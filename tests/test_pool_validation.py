#!/usr/bin/env python3
"""
Test script for Pool Management API validation and models.

This script tests the Pydantic models and validation logic
without requiring database connections.
"""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_pool_models():
    """Test pool-related Pydantic models."""
    try:
        from server.api.pools import (
            CreatePoolRequest, UpdatePoolRequest, SyncPolicyRequest,
            PoolResponse, PoolStatusResponse
        )
        from shared.models import PackagePool, SyncPolicy, ConflictResolution
        from datetime import datetime
        
        print("✓ Testing SyncPolicyRequest validation...")
        
        # Valid sync policy
        valid_policy = SyncPolicyRequest(
            auto_sync=True,
            exclude_packages=["test-pkg", "another-pkg"],
            include_aur=False,
            conflict_resolution="newest"
        )
        assert valid_policy.auto_sync is True
        assert len(valid_policy.exclude_packages) == 2
        assert valid_policy.conflict_resolution == "newest"
        print("  Valid sync policy created successfully")
        
        # Test validation errors
        try:
            invalid_policy = SyncPolicyRequest(conflict_resolution="invalid")
            assert False, "Should have raised validation error"
        except Exception as e:
            print(f"  Correctly caught validation error: {type(e).__name__}")
        
        print("✓ Testing CreatePoolRequest validation...")
        
        # Valid pool creation request
        valid_request = CreatePoolRequest(
            name="test-pool",
            description="Test description",
            sync_policy=valid_policy
        )
        assert valid_request.name == "test-pool"
        assert valid_request.description == "Test description"
        print("  Valid pool creation request created successfully")
        
        # Test empty name validation
        try:
            invalid_request = CreatePoolRequest(name="")
            assert False, "Should have raised validation error"
        except Exception as e:
            print(f"  Correctly caught empty name validation error: {type(e).__name__}")
        
        print("✓ Testing UpdatePoolRequest validation...")
        
        # Valid update request
        update_request = UpdatePoolRequest(
            name="updated-name",
            description="Updated description"
        )
        assert update_request.name == "updated-name"
        print("  Valid pool update request created successfully")
        
        print("✓ Testing PoolResponse model...")
        
        # Create a PackagePool to convert
        pool = PackagePool(
            id="test-id",
            name="test-pool",
            description="Test pool",
            endpoints=["endpoint1", "endpoint2"],
            sync_policy=SyncPolicy(auto_sync=True, conflict_resolution=ConflictResolution.NEWEST)
        )
        
        # Convert to response model
        response = PoolResponse.from_pool(pool)
        assert response.id == "test-id"
        assert response.name == "test-pool"
        assert len(response.endpoints) == 2
        assert response.sync_policy["auto_sync"] is True
        print("  Pool response model conversion successful")
        
        print("✓ Testing model serialization...")
        
        # Test JSON serialization
        response_dict = response.model_dump()
        assert "id" in response_dict
        assert "name" in response_dict
        assert "sync_policy" in response_dict
        print("  Model serialization successful")
        
        print("\n🎉 All model validation tests passed!")
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_pool_manager_logic():
    """Test pool manager business logic without database."""
    try:
        from server.core.pool_manager import PoolStatusInfo
        from shared.models import PackagePool, Endpoint, SyncStatus
        from datetime import datetime
        
        print("✓ Testing PoolStatusInfo logic...")
        
        # Create test pool and endpoints
        pool = PackagePool(
            id="test-pool-id",
            name="test-pool",
            description="Test pool"
        )
        
        endpoints = [
            Endpoint(id="ep1", name="endpoint1", hostname="host1", sync_status=SyncStatus.IN_SYNC),
            Endpoint(id="ep2", name="endpoint2", hostname="host2", sync_status=SyncStatus.AHEAD),
            Endpoint(id="ep3", name="endpoint3", hostname="host3", sync_status=SyncStatus.BEHIND),
            Endpoint(id="ep4", name="endpoint4", hostname="host4", sync_status=SyncStatus.OFFLINE),
        ]
        
        # Create status info
        status_info = PoolStatusInfo(pool, endpoints)
        
        # Test calculations
        assert status_info.total_endpoints == 4
        assert status_info.in_sync_count == 1
        assert status_info.ahead_count == 1
        assert status_info.behind_count == 1
        assert status_info.offline_count == 1
        assert status_info.sync_percentage == 25.0  # 1/4 * 100
        assert status_info.overall_status == "partially_synced"
        
        print("  Pool status calculations correct")
        
        # Test with all in sync
        all_sync_endpoints = [
            Endpoint(id="ep1", name="endpoint1", hostname="host1", sync_status=SyncStatus.IN_SYNC),
            Endpoint(id="ep2", name="endpoint2", hostname="host2", sync_status=SyncStatus.IN_SYNC),
        ]
        
        all_sync_status = PoolStatusInfo(pool, all_sync_endpoints)
        assert all_sync_status.overall_status == "fully_synced"
        assert all_sync_status.sync_percentage == 100.0
        
        print("  All-sync status calculations correct")
        
        # Test with empty pool
        empty_status = PoolStatusInfo(pool, [])
        assert empty_status.overall_status == "empty"
        assert empty_status.sync_percentage == 100.0
        
        print("  Empty pool status calculations correct")
        
        # Test dictionary conversion
        status_dict = status_info.to_dict()
        assert "pool_id" in status_dict
        assert "total_endpoints" in status_dict
        assert "sync_percentage" in status_dict
        
        print("  Status info dictionary conversion successful")
        
        print("\n🎉 All pool manager logic tests passed!")
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("Running Pool Management Validation Tests...")
    
    success1 = test_pool_models()
    success2 = test_pool_manager_logic()
    
    if success1 and success2:
        print("\n🎉 All validation tests passed!")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed!")
        sys.exit(1)