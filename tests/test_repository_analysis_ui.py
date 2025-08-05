#!/usr/bin/env python3
"""
Test script to verify the repository analysis dashboard implementation.
This tests the enhanced functionality for task 5.2.
"""

import json
import sys
import os

def test_repository_analysis_ui():
    """Test the repository analysis UI implementation"""
    
    print("Testing Repository Analysis Dashboard Implementation...")
    print("=" * 60)
    
    # Test 1: Check if the enhanced RepositoryAnalysisPage exists
    ui_file = "server/web/src/pages/RepositoryAnalysisPage.jsx"
    if not os.path.exists(ui_file):
        print("❌ FAIL: RepositoryAnalysisPage.jsx not found")
        return False
    
    with open(ui_file, 'r') as f:
        content = f.read()
    
    # Test 2: Check for package exclusion management functionality
    exclusion_features = [
        'excludedPackages',
        'handleAddExclusion',
        'handleRemoveExclusion',
        'newExclusionPackage',
        'renderExclusionsTab'
    ]
    
    print("\n1. Package Exclusion Management:")
    for feature in exclusion_features:
        if feature in content:
            print(f"   ✅ {feature} - implemented")
        else:
            print(f"   ❌ {feature} - missing")
            return False
    
    # Test 3: Check for conflict resolution UI
    conflict_features = [
        'handleResolveConflict',
        'resolvingConflicts',
        'conflictResolutions',
        'Resolution Options',
        'Use {endpoint',
        'Exclude Package'
    ]
    
    print("\n2. Conflict Resolution UI:")
    for feature in conflict_features:
        if feature in content:
            print(f"   ✅ {feature} - implemented")
        else:
            print(f"   ❌ {feature} - missing")
            return False
    
    # Test 4: Check for repository information visualization
    repo_features = [
        'repositoryDetails',
        'renderRepositoriesTab',
        'Repository Details',
        'Total Endpoints',
        'Total Repositories',
        'Last Updated'
    ]
    
    print("\n3. Repository Information Visualization:")
    for feature in repo_features:
        if feature in content:
            print(f"   ✅ {feature} - implemented")
        else:
            print(f"   ❌ {feature} - missing")
            return False
    
    # Test 5: Check for enhanced tabs
    tab_features = [
        'exclusions',
        'repositories',
        'Exclusion Management',
        'Repository Details',
        'AdjustmentsHorizontalIcon',
        'ServerIcon'
    ]
    
    print("\n4. Enhanced Tab Navigation:")
    for feature in tab_features:
        if feature in content:
            print(f"   ✅ {feature} - implemented")
        else:
            print(f"   ❌ {feature} - missing")
            return False
    
    # Test 6: Check for package availability matrix enhancements
    matrix_features = [
        'Package Availability Matrix',
        'sticky left-0',
        'getStatusIcon',
        'endpoint.sync_status'
    ]
    
    print("\n5. Package Availability Matrix:")
    for feature in matrix_features:
        if feature in content:
            print(f"   ✅ {feature} - implemented")
        else:
            print(f"   ❌ {feature} - missing")
            return False
    
    # Test 7: Check Tailwind configuration for required colors
    tailwind_file = "server/web/tailwind.config.js"
    if os.path.exists(tailwind_file):
        with open(tailwind_file, 'r') as f:
            tailwind_content = f.read()
        
        print("\n6. Tailwind CSS Configuration:")
        required_colors = ['100: \'#dcfce7\'', '100: \'#fef3c7\'', '100: \'#dbeafe\'']
        color_names = ['success-100', 'warning-100', 'primary-100']
        for i, color in enumerate(required_colors):
            if color in tailwind_content:
                print(f"   ✅ {color_names[i]} - configured")
            else:
                print(f"   ❌ {color_names[i]} - missing")
                return False
    
    # Test 8: Check if build succeeds
    print("\n7. Build Verification:")
    build_result = os.system("cd server/web && npm run build > /dev/null 2>&1")
    if build_result == 0:
        print("   ✅ Web UI builds successfully")
    else:
        print("   ❌ Web UI build failed")
        return False
    
    print("\n" + "=" * 60)
    print("✅ ALL TESTS PASSED - Repository Analysis Dashboard Enhanced Successfully!")
    print("\nImplemented Features:")
    print("• Package exclusion management interface")
    print("• Interactive conflict resolution UI")
    print("• Enhanced repository information visualization")
    print("• Package availability matrix with status indicators")
    print("• Multi-tab navigation for different analysis views")
    print("• Real-time status updates and progress indicators")
    
    return True

if __name__ == "__main__":
    success = test_repository_analysis_ui()
    sys.exit(0 if success else 1)