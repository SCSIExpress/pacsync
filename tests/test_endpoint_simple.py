#!/usr/bin/env python3
"""
Simple test for endpoint management API.
"""

import requests
import json
import sys

BASE_URL = "http://localhost:8080"

def test_health():
    """Test health endpoint."""
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        print(f"Health check: {response.status_code} - {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"Health check failed: {e}")
        return False

def test_endpoint_registration():
    """Test endpoint registration."""
    try:
        data = {
            "name": "test-endpoint",
            "hostname": "test-host.local"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/endpoints/register",
            json=data,
            timeout=10
        )
        
        print(f"Registration: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"Endpoint ID: {result['endpoint']['id']}")
            print(f"Auth token: {result['auth_token'][:20]}...")
            return result['endpoint']['id'], result['auth_token']
        else:
            print(f"Registration failed: {response.text}")
            return None, None
            
    except Exception as e:
        print(f"Registration test failed: {e}")
        return None, None

def test_endpoint_listing():
    """Test endpoint listing."""
    try:
        response = requests.get(f"{BASE_URL}/api/endpoints", timeout=10)
        print(f"Listing: {response.status_code}")
        if response.status_code == 200:
            endpoints = response.json()
            print(f"Found {len(endpoints)} endpoints")
            return True
        else:
            print(f"Listing failed: {response.text}")
            return False
    except Exception as e:
        print(f"Listing test failed: {e}")
        return False

def main():
    print("Testing endpoint management API...")
    
    # Test health
    if not test_health():
        print("Server not responding")
        sys.exit(1)
    
    # Test registration
    endpoint_id, auth_token = test_endpoint_registration()
    if not endpoint_id:
        print("Registration failed")
        sys.exit(1)
    
    # Test listing
    if not test_endpoint_listing():
        print("Listing failed")
        sys.exit(1)
    
    print("Basic tests passed!")

if __name__ == "__main__":
    main()