#!/usr/bin/env python3
"""
Test endpoint authentication and authorization.
"""

import requests
import json
import sys

BASE_URL = "http://localhost:8080"

def test_status_update_with_auth():
    """Test status update with authentication."""
    print("Testing status update with authentication...")
    
    # First register an endpoint
    data = {
        "name": "auth-test-endpoint",
        "hostname": "auth-test-host.local"
    }
    
    response = requests.post(f"{BASE_URL}/api/endpoints/register", json=data)
    if response.status_code != 200:
        print(f"Registration failed: {response.text}")
        return False
    
    result = response.json()
    endpoint_id = result['endpoint']['id']
    auth_token = result['auth_token']
    
    print(f"Registered endpoint: {endpoint_id}")
    
    # Test status update with valid token
    headers = {"Authorization": f"Bearer {auth_token}"}
    status_data = {"status": "ahead"}
    
    response = requests.put(
        f"{BASE_URL}/api/endpoints/{endpoint_id}/status",
        json=status_data,
        headers=headers
    )
    
    if response.status_code == 200:
        print("✓ Status update with valid token succeeded")
    else:
        print(f"✗ Status update failed: {response.text}")
        return False
    
    # Test status update without token
    response = requests.put(
        f"{BASE_URL}/api/endpoints/{endpoint_id}/status",
        json=status_data
    )
    
    if response.status_code == 401:
        print("✓ Status update without token correctly rejected")
    else:
        print(f"✗ Status update without token should have been rejected: {response.status_code}")
        return False
    
    # Test status update with invalid token
    headers = {"Authorization": "Bearer invalid-token"}
    response = requests.put(
        f"{BASE_URL}/api/endpoints/{endpoint_id}/status",
        json=status_data,
        headers=headers
    )
    
    if response.status_code == 401:
        print("✓ Status update with invalid token correctly rejected")
    else:
        print(f"✗ Status update with invalid token should have been rejected: {response.status_code}")
        return False
    
    return True

def test_repository_submission():
    """Test repository information submission."""
    print("Testing repository submission...")
    
    # Register an endpoint
    data = {
        "name": "repo-test-endpoint",
        "hostname": "repo-test-host.local"
    }
    
    response = requests.post(f"{BASE_URL}/api/endpoints/register", json=data)
    if response.status_code != 200:
        print(f"Registration failed: {response.text}")
        return False
    
    result = response.json()
    endpoint_id = result['endpoint']['id']
    auth_token = result['auth_token']
    
    # Submit repository information
    headers = {"Authorization": f"Bearer {auth_token}"}
    repo_data = {
        "repositories": [
            {
                "repo_name": "core",
                "repo_url": "https://mirror.example.com/archlinux/core/os/x86_64",
                "packages": [
                    {
                        "name": "bash",
                        "version": "5.1.016-1",
                        "repository": "core",
                        "architecture": "x86_64",
                        "description": "The GNU Bourne Again shell"
                    }
                ]
            }
        ]
    }
    
    response = requests.post(
        f"{BASE_URL}/api/endpoints/{endpoint_id}/repositories",
        json=repo_data,
        headers=headers
    )
    
    if response.status_code == 200:
        print("✓ Repository submission succeeded")
    else:
        print(f"✗ Repository submission failed: {response.text}")
        return False
    
    # Retrieve repository information
    response = requests.get(f"{BASE_URL}/api/endpoints/{endpoint_id}/repositories")
    
    if response.status_code == 200:
        data = response.json()
        repositories = data.get('repositories', [])
        if len(repositories) == 1 and repositories[0]['repo_name'] == 'core':
            print("✓ Repository retrieval succeeded")
        else:
            print(f"✗ Repository retrieval returned unexpected data: {data}")
            return False
    else:
        print(f"✗ Repository retrieval failed: {response.text}")
        return False
    
    return True

def main():
    print("Testing endpoint authentication and authorization...")
    
    if not test_status_update_with_auth():
        print("Authentication tests failed")
        sys.exit(1)
    
    if not test_repository_submission():
        print("Repository submission tests failed")
        sys.exit(1)
    
    print("All authentication tests passed!")

if __name__ == "__main__":
    main()