#!/usr/bin/env python3
"""
Verification script for Task 4.2: Implement endpoint management API endpoints.

This script verifies that all requirements for task 4.2 are implemented:
- Create endpoints for endpoint registration, status updates, and removal
- Implement repository information submission and processing
- Add endpoint authentication and authorization
- Requirements: 3.1, 5.1, 5.2, 5.3, 5.4, 5.5
"""

import asyncio
import sys
import subprocess
import time
import requests
import json
from typing import Dict, Any, Optional

BASE_URL = "http://localhost:8080"

class Task42Verifier:
    def __init__(self):
        self.server_process = None
        self.test_results = []
    
    def start_server(self):
        """Start the server for testing."""
        print("Starting server...")
        import os
        env = os.environ.copy()
        env["PYTHONPATH"] = "."
        self.server_process = subprocess.Popen(
            ["python", "server/api/main.py"],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # Wait for server to start and check if it's responding
        max_attempts = 10
        for attempt in range(max_attempts):
            time.sleep(1)
            try:
                response = requests.get(f"{BASE_URL}/health", timeout=2)
                if response.status_code == 200:
                    print("Server started successfully")
                    return
            except:
                continue
        
        # If we get here, server didn't start properly
        stdout, stderr = self.server_process.communicate(timeout=5)
        print(f"Server failed to start. STDOUT: {stdout.decode()}")
        print(f"STDERR: {stderr.decode()}")
        raise Exception("Server failed to start")
    
    def stop_server(self):
        """Stop the server."""
        if self.server_process:
            self.server_process.terminate()
            self.server_process.wait()
    
    def test_result(self, test_name: str, success: bool, details: str = ""):
        """Record test result."""
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"{status}: {test_name}")
        if details:
            print(f"    {details}")
        self.test_results.append((test_name, success, details))
        return success
    
    def test_server_health(self) -> bool:
        """Test that server is running."""
        try:
            response = requests.get(f"{BASE_URL}/health", timeout=5)
            return self.test_result(
                "Server Health Check",
                response.status_code == 200,
                f"Status: {response.status_code}"
            )
        except Exception as e:
            return self.test_result("Server Health Check", False, str(e))
    
    def test_endpoint_registration(self) -> Optional[Dict[str, Any]]:
        """Test endpoint registration functionality."""
        try:
            data = {
                "name": "test-endpoint-reg",
                "hostname": "test-host-reg.local"
            }
            
            response = requests.post(f"{BASE_URL}/api/endpoints/register", json=data)
            
            if response.status_code == 200:
                result = response.json()
                has_endpoint = "endpoint" in result
                has_token = "auth_token" in result
                has_id = has_endpoint and "id" in result["endpoint"]
                
                success = has_endpoint and has_token and has_id
                details = f"Has endpoint: {has_endpoint}, Has token: {has_token}, Has ID: {has_id}"
                
                self.test_result("Endpoint Registration", success, details)
                return result if success else None
            else:
                self.test_result("Endpoint Registration", False, f"HTTP {response.status_code}: {response.text}")
                return None
                
        except Exception as e:
            self.test_result("Endpoint Registration", False, str(e))
            return None
    
    def test_endpoint_listing(self) -> bool:
        """Test endpoint listing functionality."""
        try:
            response = requests.get(f"{BASE_URL}/api/endpoints")
            
            if response.status_code == 200:
                endpoints = response.json()
                is_list = isinstance(endpoints, list)
                has_endpoints = len(endpoints) > 0
                
                success = is_list and has_endpoints
                details = f"Is list: {is_list}, Count: {len(endpoints) if is_list else 'N/A'}"
                
                return self.test_result("Endpoint Listing", success, details)
            else:
                return self.test_result("Endpoint Listing", False, f"HTTP {response.status_code}")
                
        except Exception as e:
            return self.test_result("Endpoint Listing", False, str(e))
    
    def test_endpoint_details(self, endpoint_id: str) -> bool:
        """Test getting endpoint details."""
        try:
            response = requests.get(f"{BASE_URL}/api/endpoints/{endpoint_id}")
            
            if response.status_code == 200:
                endpoint = response.json()
                has_required_fields = all(field in endpoint for field in 
                                        ["id", "name", "hostname", "sync_status"])
                correct_id = endpoint.get("id") == endpoint_id
                
                success = has_required_fields and correct_id
                details = f"Has required fields: {has_required_fields}, Correct ID: {correct_id}"
                
                return self.test_result("Endpoint Details", success, details)
            else:
                return self.test_result("Endpoint Details", False, f"HTTP {response.status_code}")
                
        except Exception as e:
            return self.test_result("Endpoint Details", False, str(e))
    
    def test_authentication_required(self, endpoint_id: str) -> bool:
        """Test that authentication is required for protected endpoints."""
        try:
            # Test status update without auth
            response = requests.put(
                f"{BASE_URL}/api/endpoints/{endpoint_id}/status",
                json={"status": "in_sync"}
            )
            
            auth_required = response.status_code == 401
            
            return self.test_result(
                "Authentication Required",
                auth_required,
                f"Status update without auth returned: {response.status_code}"
            )
            
        except Exception as e:
            return self.test_result("Authentication Required", False, str(e))
    
    def test_status_update(self, endpoint_id: str, auth_token: str) -> bool:
        """Test endpoint status update with authentication."""
        try:
            headers = {"Authorization": f"Bearer {auth_token}"}
            data = {"status": "ahead"}
            
            response = requests.put(
                f"{BASE_URL}/api/endpoints/{endpoint_id}/status",
                json=data,
                headers=headers
            )
            
            success = response.status_code == 200
            
            return self.test_result(
                "Status Update with Auth",
                success,
                f"HTTP {response.status_code}"
            )
            
        except Exception as e:
            return self.test_result("Status Update with Auth", False, str(e))
    
    def test_repository_submission(self, endpoint_id: str, auth_token: str) -> bool:
        """Test repository information submission."""
        try:
            headers = {"Authorization": f"Bearer {auth_token}"}
            data = {
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
                            },
                            {
                                "name": "coreutils",
                                "version": "9.1-3",
                                "repository": "core",
                                "architecture": "x86_64",
                                "description": "Basic file utilities"
                            }
                        ]
                    },
                    {
                        "repo_name": "extra",
                        "repo_url": "https://mirror.example.com/archlinux/extra/os/x86_64",
                        "packages": [
                            {
                                "name": "firefox",
                                "version": "109.0-1",
                                "repository": "extra",
                                "architecture": "x86_64",
                                "description": "Web browser"
                            }
                        ]
                    }
                ]
            }
            
            response = requests.post(
                f"{BASE_URL}/api/endpoints/{endpoint_id}/repositories",
                json=data,
                headers=headers
            )
            
            success = response.status_code == 200
            
            return self.test_result(
                "Repository Submission",
                success,
                f"HTTP {response.status_code}"
            )
            
        except Exception as e:
            return self.test_result("Repository Submission", False, str(e))
    
    def test_repository_retrieval(self, endpoint_id: str) -> bool:
        """Test repository information retrieval."""
        try:
            response = requests.get(f"{BASE_URL}/api/endpoints/{endpoint_id}/repositories")
            
            if response.status_code == 200:
                data = response.json()
                has_repositories = "repositories" in data
                repositories = data.get("repositories", [])
                has_expected_repos = len(repositories) == 2  # core and extra
                
                # Check repository structure
                valid_structure = True
                if has_repositories and repositories:
                    for repo in repositories:
                        if not all(field in repo for field in ["repo_name", "packages"]):
                            valid_structure = False
                            break
                        if not isinstance(repo["packages"], list) or len(repo["packages"]) == 0:
                            valid_structure = False
                            break
                
                success = has_repositories and has_expected_repos and valid_structure
                details = f"Has repos: {has_repositories}, Count: {len(repositories)}, Valid structure: {valid_structure}"
                
                return self.test_result("Repository Retrieval", success, details)
            else:
                return self.test_result("Repository Retrieval", False, f"HTTP {response.status_code}")
                
        except Exception as e:
            return self.test_result("Repository Retrieval", False, str(e))
    
    def test_authorization_enforcement(self, endpoint_id: str, auth_token: str) -> bool:
        """Test that endpoints can only modify their own data."""
        try:
            # Register another endpoint
            data = {
                "name": "other-endpoint",
                "hostname": "other-host.local"
            }
            
            response = requests.post(f"{BASE_URL}/api/endpoints/register", json=data)
            if response.status_code != 200:
                return self.test_result("Authorization Enforcement", False, "Failed to register second endpoint")
            
            other_endpoint_id = response.json()["endpoint"]["id"]
            
            # Try to update other endpoint's status with first endpoint's token
            headers = {"Authorization": f"Bearer {auth_token}"}
            response = requests.put(
                f"{BASE_URL}/api/endpoints/{other_endpoint_id}/status",
                json={"status": "in_sync"},
                headers=headers
            )
            
            forbidden = response.status_code == 403
            
            return self.test_result(
                "Authorization Enforcement",
                forbidden,
                f"Cross-endpoint access returned: {response.status_code}"
            )
            
        except Exception as e:
            return self.test_result("Authorization Enforcement", False, str(e))
    
    def test_endpoint_removal(self, endpoint_id: str, auth_token: str) -> bool:
        """Test endpoint removal."""
        try:
            headers = {"Authorization": f"Bearer {auth_token}"}
            
            response = requests.delete(
                f"{BASE_URL}/api/endpoints/{endpoint_id}",
                headers=headers
            )
            
            if response.status_code == 200:
                # Verify endpoint is gone
                response = requests.get(f"{BASE_URL}/api/endpoints/{endpoint_id}")
                endpoint_gone = response.status_code == 404
                
                success = endpoint_gone
                details = f"Removal HTTP: 200, Verification HTTP: {response.status_code}"
                
                return self.test_result("Endpoint Removal", success, details)
            else:
                return self.test_result("Endpoint Removal", False, f"HTTP {response.status_code}")
                
        except Exception as e:
            return self.test_result("Endpoint Removal", False, str(e))
    
    def run_all_tests(self) -> bool:
        """Run all verification tests."""
        print("=" * 60)
        print("TASK 4.2 VERIFICATION: Endpoint Management API Endpoints")
        print("=" * 60)
        
        try:
            self.start_server()
            
            # Basic server health
            if not self.test_server_health():
                return False
            
            # Test endpoint registration
            registration_result = self.test_endpoint_registration()
            if not registration_result:
                return False
            
            endpoint_id = registration_result["endpoint"]["id"]
            auth_token = registration_result["auth_token"]
            
            # Test endpoint listing
            if not self.test_endpoint_listing():
                return False
            
            # Test endpoint details
            if not self.test_endpoint_details(endpoint_id):
                return False
            
            # Test authentication requirement
            if not self.test_authentication_required(endpoint_id):
                return False
            
            # Test status update with authentication
            if not self.test_status_update(endpoint_id, auth_token):
                return False
            
            # Test repository submission
            if not self.test_repository_submission(endpoint_id, auth_token):
                return False
            
            # Test repository retrieval
            if not self.test_repository_retrieval(endpoint_id):
                return False
            
            # Test authorization enforcement
            if not self.test_authorization_enforcement(endpoint_id, auth_token):
                return False
            
            # Test endpoint removal (do this last)
            if not self.test_endpoint_removal(endpoint_id, auth_token):
                return False
            
            return True
            
        finally:
            self.stop_server()
    
    def print_summary(self):
        """Print test summary."""
        print("\n" + "=" * 60)
        print("TEST SUMMARY")
        print("=" * 60)
        
        passed = sum(1 for _, success, _ in self.test_results if success)
        total = len(self.test_results)
        
        print(f"Tests passed: {passed}/{total}")
        
        if passed == total:
            print("\n🎉 ALL TESTS PASSED! Task 4.2 is complete.")
            print("\nImplemented features:")
            print("✓ Endpoint registration with authentication token generation")
            print("✓ Endpoint listing and details retrieval")
            print("✓ Endpoint status updates with authentication")
            print("✓ Repository information submission and processing")
            print("✓ JWT-based authentication and authorization")
            print("✓ Endpoint removal functionality")
            print("✓ Cross-endpoint access protection")
        else:
            print(f"\n❌ {total - passed} tests failed. Task 4.2 needs fixes.")
            print("\nFailed tests:")
            for name, success, details in self.test_results:
                if not success:
                    print(f"  - {name}: {details}")

def main():
    verifier = Task42Verifier()
    
    try:
        success = verifier.run_all_tests()
        verifier.print_summary()
        
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nTest failed with error: {e}")
        sys.exit(1)
    finally:
        verifier.stop_server()

if __name__ == "__main__":
    main()