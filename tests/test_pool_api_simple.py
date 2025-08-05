#!/usr/bin/env python3
"""
Simple test script for Pool Management API endpoints.

This script tests the pool API endpoints using FastAPI's TestClient
without requiring a running server.
"""

import sys
import os
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Set environment variables for testing
os.environ["DATABASE_TYPE"] = "internal"
os.environ["DATABASE_URL"] = "sqlite:///test.db"

def test_pool_api():
    """Test pool API endpoints."""
    try:
        from fastapi.testclient import TestClient
        from server.api.main import create_app
        
        print("Creating FastAPI test client...")
        app = create_app()
        client = TestClient(app)
        
        print("✓ Testing health check...")
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        print(f"  Health check response: {data}")
        
        print("✓ Testing pool creation...")
        pool_data = {
            "name": "test-pool",
            "description": "Test pool for API testing"
        }
        
        response = client.post("/api/pools", json=pool_data)
        print(f"  Create pool status: {response.status_code}")
        if response.status_code != 201:
            print(f"  Error response: {response.text}")
            return False
        
        created_pool = response.json()
        pool_id = created_pool["id"]
        print(f"  Created pool: {created_pool['name']} (ID: {pool_id})")
        
        print("✓ Testing pool retrieval...")
        response = client.get(f"/api/pools/{pool_id}")
        assert response.status_code == 200
        retrieved_pool = response.json()
        assert retrieved_pool["name"] == "test-pool"
        print(f"  Retrieved pool: {retrieved_pool['name']}")
        
        print("✓ Testing pool listing...")
        response = client.get("/api/pools")
        assert response.status_code == 200
        pools = response.json()
        assert len(pools) >= 1
        print(f"  Found {len(pools)} pools")
        
        print("✓ Testing pool status...")
        response = client.get(f"/api/pools/{pool_id}/status")
        assert response.status_code == 200
        status = response.json()
        assert status["pool_name"] == "test-pool"
        print(f"  Pool status: {status['overall_status']}")
        
        print("✓ Testing pool update...")
        update_data = {
            "name": "updated-test-pool",
            "description": "Updated description"
        }
        response = client.put(f"/api/pools/{pool_id}", json=update_data)
        assert response.status_code == 200
        updated_pool = response.json()
        assert updated_pool["name"] == "updated-test-pool"
        print(f"  Updated pool name: {updated_pool['name']}")
        
        print("✓ Testing pool deletion...")
        response = client.delete(f"/api/pools/{pool_id}")
        assert response.status_code == 204
        print("  Pool deleted successfully")
        
        # Verify deletion
        response = client.get(f"/api/pools/{pool_id}")
        assert response.status_code == 404
        print("  Confirmed pool no longer exists")
        
        print("\n🎉 All pool API tests passed!")
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_pool_api()
    sys.exit(0 if success else 1)