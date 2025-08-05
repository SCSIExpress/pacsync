#!/usr/bin/env python3
"""
Test script for endpoint management API endpoints.

This script tests the endpoint registration, status updates, repository submission,
and authentication functionality.
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Any

import httpx
from server.database.connection import DatabaseManager
from server.database.schema import create_tables, verify_schema
from server.core.endpoint_manager import EndpointManager
from shared.models import SyncStatus

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASE_URL = "http://localhost:8080"


async def test_endpoint_registration():
    """Test endpoint registration."""
    logger.info("Testing endpoint registration...")
    
    async with httpx.AsyncClient() as client:
        # Test endpoint registration
        registration_data = {
            "name": "test-endpoint",
            "hostname": "test-host.local"
        }
        
        response = await client.post(
            f"{BASE_URL}/api/endpoints/register",
            json=registration_data
        )
        
        assert response.status_code == 200, f"Registration failed: {response.text}"
        
        data = response.json()
        assert "endpoint" in data
        assert "auth_token" in data
        
        endpoint = data["endpoint"]
        auth_token = data["auth_token"]
        
        logger.info(f"Successfully registered endpoint: {endpoint['id']}")
        logger.info(f"Auth token: {auth_token[:20]}...")
        
        return endpoint, auth_token


async def test_endpoint_listing():
    """Test endpoint listing."""
    logger.info("Testing endpoint listing...")
    
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/api/endpoints")
        
        assert response.status_code == 200, f"Listing failed: {response.text}"
        
        endpoints = response.json()
        assert isinstance(endpoints, list)
        
        logger.info(f"Found {len(endpoints)} endpoints")
        
        return endpoints


async def test_endpoint_details(endpoint_id: str):
    """Test getting endpoint details."""
    logger.info(f"Testing endpoint details for {endpoint_id}...")
    
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/api/endpoints/{endpoint_id}")
        
        assert response.status_code == 200, f"Get endpoint failed: {response.text}"
        
        endpoint = response.json()
        assert endpoint["id"] == endpoint_id
        
        logger.info(f"Successfully retrieved endpoint details")
        
        return endpoint


async def test_status_update(endpoint_id: str, auth_token: str):
    """Test endpoint status update."""
    logger.info(f"Testing status update for {endpoint_id}...")
    
    async with httpx.AsyncClient() as client:
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        # Test status update
        status_data = {"status": "ahead"}
        
        response = await client.put(
            f"{BASE_URL}/api/endpoints/{endpoint_id}/status",
            json=status_data,
            headers=headers
        )
        
        assert response.status_code == 200, f"Status update failed: {response.text}"
        
        result = response.json()
        assert "message" in result
        
        logger.info("Successfully updated endpoint status")


async def test_repository_submission(endpoint_id: str, auth_token: str):
    """Test repository information submission."""
    logger.info(f"Testing repository submission for {endpoint_id}...")
    
    async with httpx.AsyncClient() as client:
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        # Test repository submission
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
                        },
                        {
                            "name": "coreutils",
                            "version": "9.1-3",
                            "repository": "core",
                            "architecture": "x86_64",
                            "description": "The basic file, shell and text manipulation utilities"
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
                            "description": "Standalone web browser from mozilla.org"
                        }
                    ]
                }
            ]
        }
        
        response = await client.post(
            f"{BASE_URL}/api/endpoints/{endpoint_id}/repositories",
            json=repo_data,
            headers=headers
        )
        
        assert response.status_code == 200, f"Repository submission failed: {response.text}"
        
        result = response.json()
        assert "message" in result
        
        logger.info("Successfully submitted repository information")


async def test_repository_retrieval(endpoint_id: str):
    """Test repository information retrieval."""
    logger.info(f"Testing repository retrieval for {endpoint_id}...")
    
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/api/endpoints/{endpoint_id}/repositories")
        
        assert response.status_code == 200, f"Repository retrieval failed: {response.text}"
        
        data = response.json()
        assert "repositories" in data
        
        repositories = data["repositories"]
        assert len(repositories) == 2  # core and extra
        
        # Verify repository structure
        for repo in repositories:
            assert "repo_name" in repo
            assert "packages" in repo
            assert len(repo["packages"]) > 0
        
        logger.info(f"Successfully retrieved {len(repositories)} repositories")
        
        return repositories


async def test_authentication_failure(endpoint_id: str):
    """Test authentication failure scenarios."""
    logger.info("Testing authentication failures...")
    
    async with httpx.AsyncClient() as client:
        # Test without authorization header
        response = await client.put(
            f"{BASE_URL}/api/endpoints/{endpoint_id}/status",
            json={"status": "in_sync"}
        )
        assert response.status_code == 401
        
        # Test with invalid token
        headers = {"Authorization": "Bearer invalid-token"}
        response = await client.put(
            f"{BASE_URL}/api/endpoints/{endpoint_id}/status",
            json={"status": "in_sync"},
            headers=headers
        )
        assert response.status_code == 401
        
        logger.info("Authentication failure tests passed")


async def test_authorization_failure(endpoint_id: str, auth_token: str):
    """Test authorization failure scenarios."""
    logger.info("Testing authorization failures...")
    
    # Register another endpoint to test cross-endpoint access
    async with httpx.AsyncClient() as client:
        registration_data = {
            "name": "other-endpoint",
            "hostname": "other-host.local"
        }
        
        response = await client.post(
            f"{BASE_URL}/api/endpoints/register",
            json=registration_data
        )
        assert response.status_code == 200
        
        other_endpoint = response.json()["endpoint"]
        other_endpoint_id = other_endpoint["id"]
        
        # Try to update other endpoint's status with first endpoint's token
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = await client.put(
            f"{BASE_URL}/api/endpoints/{other_endpoint_id}/status",
            json={"status": "in_sync"},
            headers=headers
        )
        assert response.status_code == 403
        
        logger.info("Authorization failure tests passed")
        
        return other_endpoint_id


async def test_endpoint_removal(endpoint_id: str, auth_token: str):
    """Test endpoint removal."""
    logger.info(f"Testing endpoint removal for {endpoint_id}...")
    
    async with httpx.AsyncClient() as client:
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        response = await client.delete(
            f"{BASE_URL}/api/endpoints/{endpoint_id}",
            headers=headers
        )
        
        assert response.status_code == 200, f"Endpoint removal failed: {response.text}"
        
        result = response.json()
        assert "message" in result
        
        # Verify endpoint is gone
        response = await client.get(f"{BASE_URL}/api/endpoints/{endpoint_id}")
        assert response.status_code == 404
        
        logger.info("Successfully removed endpoint")


async def run_tests():
    """Run all endpoint API tests."""
    logger.info("Starting endpoint API tests...")
    
    try:
        # Test endpoint registration
        endpoint, auth_token = await test_endpoint_registration()
        endpoint_id = endpoint["id"]
        
        # Test endpoint listing
        await test_endpoint_listing()
        
        # Test endpoint details
        await test_endpoint_details(endpoint_id)
        
        # Test status update
        await test_status_update(endpoint_id, auth_token)
        
        # Test repository submission
        await test_repository_submission(endpoint_id, auth_token)
        
        # Test repository retrieval
        await test_repository_retrieval(endpoint_id)
        
        # Test authentication failures
        await test_authentication_failure(endpoint_id)
        
        # Test authorization failures
        other_endpoint_id = await test_authorization_failure(endpoint_id, auth_token)
        
        # Test endpoint removal
        await test_endpoint_removal(endpoint_id, auth_token)
        
        # Clean up other endpoint
        async with httpx.AsyncClient() as client:
            # We need to get the other endpoint's token first
            registration_data = {
                "name": "cleanup-endpoint",
                "hostname": "cleanup-host.local"
            }
            response = await client.post(
                f"{BASE_URL}/api/endpoints/register",
                json=registration_data
            )
            cleanup_token = response.json()["auth_token"]
            cleanup_id = response.json()["endpoint"]["id"]
            
            # Remove cleanup endpoint
            headers = {"Authorization": f"Bearer {cleanup_token}"}
            await client.delete(f"{BASE_URL}/api/endpoints/{cleanup_id}", headers=headers)
        
        logger.info("All endpoint API tests passed!")
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(run_tests())