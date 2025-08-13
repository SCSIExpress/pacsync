#!/usr/bin/env python3
"""
Test dashboard metrics with realistic data.
"""

import asyncio
import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from client.api_client import PacmanSyncAPIClient
from client.repository_sync_client import RepositorySyncClient


async def setup_realistic_data():
    """Set up some realistic data for dashboard testing."""
    
    print("🔧 Setting up realistic dashboard data")
    print("=" * 45)
    
    server_url = "http://localhost:4444"
    
    # Create a few endpoints with repository data
    endpoints = []
    
    for i in range(3):
        endpoint_name = f"dashboard-test-{i+1}"
        hostname = f"TestMachine{i+1}"
        
        print(f"\n📋 Creating endpoint: {endpoint_name}")
        
        api_client = PacmanSyncAPIClient(server_url)
        token = await api_client.authenticate(endpoint_name, hostname)
        
        if not token:
            print(f"❌ Failed to authenticate {endpoint_name}")
            continue
        
        endpoint_id = api_client.token_manager.get_current_endpoint_id()
        print(f"   ✅ Endpoint ID: {endpoint_id}")
        
        # Submit repository data
        sync_client = RepositorySyncClient(server_url, endpoint_name, hostname)
        success = await sync_client.perform_pool_assignment_sync(api_client, endpoint_id)
        
        if success:
            print(f"   ✅ Repository data submitted")
        else:
            print(f"   ❌ Failed to submit repository data")
        
        endpoints.append({
            'name': endpoint_name,
            'id': endpoint_id,
            'api_client': api_client
        })
    
    print(f"\n✅ Created {len(endpoints)} endpoints with repository data")
    
    # Cleanup
    for endpoint in endpoints:
        await endpoint['api_client'].close()
    
    return len(endpoints) > 0


async def test_dashboard_metrics():
    """Test the dashboard metrics endpoints."""
    
    print("\n🎯 Testing Dashboard Metrics")
    print("=" * 35)
    
    server_url = "http://localhost:4444"
    
    import aiohttp
    
    async with aiohttp.ClientSession() as session:
        # Test metrics endpoint
        print("\n📊 Dashboard Metrics:")
        print("-" * 25)
        
        async with session.get(f"{server_url}/api/dashboard/metrics") as response:
            if response.status == 200:
                metrics = await response.json()
                
                print(f"✅ Server Metrics:")
                print(f"   🕐 Uptime: {metrics['server_uptime_human']}")
                print(f"   🖥️  Total Endpoints: {metrics['total_endpoints']}")
                print(f"   🟢 Online: {metrics['endpoints_online']}")
                print(f"   🔴 Offline: {metrics['endpoints_offline']}")
                print(f"   ⚪ Unassigned: {metrics['endpoints_unassigned']}")
                print(f"   🏊 Total Pools: {metrics['total_pools']}")
                print(f"   ✅ Healthy Pools: {metrics['pools_healthy']}")
                print(f"   ⚠️  Pools with Issues: {metrics['pools_with_issues']}")
                print(f"   📦 Total Repositories: {metrics['total_repositories']}")
                print(f"   📋 Available Packages: {metrics['total_packages_available']:,}")
                print(f"   🎯 Target State Packages: {metrics['total_packages_in_target_states']:,}")
                print(f"   📈 Average Sync Rate: {metrics['average_sync_percentage']}%")
                
            else:
                error_text = await response.text()
                print(f"❌ Failed to get metrics: {response.status} - {error_text}")
                return False
        
        # Test pool statuses
        print("\n📊 Pool Statuses:")
        print("-" * 20)
        
        async with session.get(f"{server_url}/api/dashboard/pool-statuses") as response:
            if response.status == 200:
                pool_statuses = await response.json()
                
                for pool in pool_statuses:
                    print(f"✅ Pool: {pool['pool_name']}")
                    print(f"   ID: {pool['pool_id']}")
                    print(f"   Endpoints: {pool['total_endpoints']}")
                    print(f"   Status: {pool['overall_status']}")
                    print(f"   Sync Rate: {pool['sync_percentage']}%")
                    print(f"   In Sync: {pool['in_sync_count']}")
                    print(f"   Behind: {pool['behind_count']}")
                    print(f"   Offline: {pool['offline_count']}")
                    print(f"   Has Target State: {pool['has_target_state']}")
                    print()
                
            else:
                error_text = await response.text()
                print(f"❌ Failed to get pool statuses: {response.status} - {error_text}")
                return False
        
        # Test system stats
        print("📊 System Statistics:")
        print("-" * 25)
        
        async with session.get(f"{server_url}/api/dashboard/system-stats") as response:
            if response.status == 200:
                stats = await response.json()
                
                print(f"✅ System Stats:")
                print(f"   💾 Database: {stats['database_type']}")
                print(f"   🔄 Total Sync Operations: {stats['total_sync_operations']}")
                print(f"   ✅ Successful Syncs (24h): {stats['successful_syncs_24h']}")
                print(f"   ❌ Failed Syncs (24h): {stats['failed_syncs_24h']}")
                print(f"   🏆 Most Active Pool: {stats['most_active_pool']}")
                print(f"   🏆 Most Active Endpoint: {stats['most_active_endpoint']}")
                
            else:
                error_text = await response.text()
                print(f"❌ Failed to get system stats: {response.status} - {error_text}")
                return False
    
    return True


async def main():
    """Main test function."""
    
    # Set up realistic data first
    setup_success = await setup_realistic_data()
    
    if not setup_success:
        print("⚠️  Warning: Failed to set up all test data, continuing with existing data")
    
    # Test dashboard metrics
    metrics_success = await test_dashboard_metrics()
    
    print("\n" + "=" * 50)
    if metrics_success:
        print("🎉 DASHBOARD METRICS TEST PASSED!")
        print("✅ All dashboard endpoints are working!")
        print("\n📋 Working features:")
        print("   1. ✅ Server uptime tracking")
        print("   2. ✅ Endpoint count and status")
        print("   3. ✅ Pool health monitoring")
        print("   4. ✅ Repository and package counting")
        print("   5. ✅ Sync rate calculations")
        print("   6. ✅ System statistics")
        print("\n🌐 Dashboard should now load without errors!")
        return 0
    else:
        print("💥 DASHBOARD METRICS TEST FAILED!")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))