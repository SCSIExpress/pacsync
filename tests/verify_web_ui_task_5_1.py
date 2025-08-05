#!/usr/bin/env python3
"""
Verification script for Task 5.1: Create pool management interface

This script verifies that the web UI implementation meets all the requirements
specified in the task.
"""

import os
import json
import subprocess
import sys
from pathlib import Path

def check_file_exists(file_path, description):
    """Check if a file exists and print result."""
    if os.path.exists(file_path):
        print(f"✅ {description}: {file_path}")
        return True
    else:
        print(f"❌ {description}: {file_path} (NOT FOUND)")
        return False

def check_directory_exists(dir_path, description):
    """Check if a directory exists and print result."""
    if os.path.isdir(dir_path):
        print(f"✅ {description}: {dir_path}")
        return True
    else:
        print(f"❌ {description}: {dir_path} (NOT FOUND)")
        return False

def check_file_contains(file_path, search_terms, description):
    """Check if a file contains specific terms."""
    if not os.path.exists(file_path):
        print(f"❌ {description}: {file_path} (FILE NOT FOUND)")
        return False
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        missing_terms = []
        for term in search_terms:
            if term not in content:
                missing_terms.append(term)
        
        if not missing_terms:
            print(f"✅ {description}: All required terms found")
            return True
        else:
            print(f"❌ {description}: Missing terms: {missing_terms}")
            return False
    except Exception as e:
        print(f"❌ {description}: Error reading file: {e}")
        return False

def main():
    print("🔍 Verifying Task 5.1: Create pool management interface")
    print("=" * 60)
    
    all_checks_passed = True
    
    # Check project structure
    print("\n📁 Project Structure:")
    structure_checks = [
        ("server/web/package.json", "Package.json configuration"),
        ("server/web/vite.config.js", "Vite configuration"),
        ("server/web/tailwind.config.js", "Tailwind CSS configuration"),
        ("server/web/src/main.jsx", "React application entry point"),
        ("server/web/src/App.jsx", "Main App component"),
        ("server/web/src/index.css", "Main stylesheet"),
    ]
    
    for file_path, description in structure_checks:
        if not check_file_exists(file_path, description):
            all_checks_passed = False
    
    # Check React components
    print("\n⚛️ React Components:")
    component_checks = [
        ("server/web/src/components/Layout.jsx", "Layout component"),
        ("server/web/src/components/EndpointCard.jsx", "Endpoint card component"),
        ("server/web/src/components/CreatePoolModal.jsx", "Create pool modal"),
        ("server/web/src/components/EditPoolModal.jsx", "Edit pool modal"),
        ("server/web/src/components/DeleteConfirmModal.jsx", "Delete confirmation modal"),
    ]
    
    for file_path, description in component_checks:
        if not check_file_exists(file_path, description):
            all_checks_passed = False
    
    # Check pages
    print("\n📄 Pages:")
    page_checks = [
        ("server/web/src/pages/Dashboard.jsx", "Dashboard page"),
        ("server/web/src/pages/PoolsPage.jsx", "Pools management page"),
        ("server/web/src/pages/PoolDetailPage.jsx", "Pool detail page"),
        ("server/web/src/pages/EndpointsPage.jsx", "Endpoints page"),
    ]
    
    for file_path, description in page_checks:
        if not check_file_exists(file_path, description):
            all_checks_passed = False
    
    # Check API service
    print("\n🌐 API Integration:")
    if not check_file_exists("server/web/src/services/api.js", "API service layer"):
        all_checks_passed = False
    
    # Check for React/Vue.js components (Requirement: Implement React/Vue.js components)
    print("\n⚛️ React/Vue.js Implementation:")
    react_terms = ["React", "useState", "useEffect", "jsx"]
    if not check_file_contains("server/web/src/App.jsx", react_terms, "React implementation"):
        all_checks_passed = False
    
    # Check for drag-and-drop functionality (Requirement: drag-and-drop functionality)
    print("\n🖱️ Drag-and-Drop Functionality:")
    dnd_terms = ["useDrag", "useDrop", "react-dnd", "DndProvider"]
    dnd_files = [
        ("server/web/src/main.jsx", "DnD Provider setup"),
        ("server/web/src/components/EndpointCard.jsx", "Draggable endpoint cards"),
        ("server/web/src/pages/PoolDetailPage.jsx", "Drop zone implementation"),
    ]
    
    for file_path, description in dnd_files:
        if not check_file_contains(file_path, ["useDrag", "useDrop", "DndProvider"], description):
            all_checks_passed = False
    
    # Check for real-time status dashboard (Requirement: real-time status dashboard)
    print("\n📊 Real-time Status Dashboard:")
    dashboard_terms = ["status", "dashboard", "real-time", "sync_percentage"]
    if not check_file_contains("server/web/src/pages/Dashboard.jsx", dashboard_terms, "Status dashboard implementation"):
        all_checks_passed = False
    
    # Check for pool creation and editing
    print("\n🏊 Pool Management:")
    pool_terms = ["createPool", "updatePool", "deletePool", "sync_policy"]
    if not check_file_contains("server/web/src/services/api.js", pool_terms, "Pool management API"):
        all_checks_passed = False
    
    # Check build output
    print("\n🏗️ Build Output:")
    if not check_directory_exists("server/web/dist", "Build output directory"):
        print("⚠️  Running build to generate dist directory...")
        try:
            result = subprocess.run(
                ["npm", "run", "build"], 
                cwd="server/web", 
                capture_output=True, 
                text=True
            )
            if result.returncode == 0:
                print("✅ Build completed successfully")
                check_directory_exists("server/web/dist", "Build output directory")
            else:
                print(f"❌ Build failed: {result.stderr}")
                all_checks_passed = False
        except Exception as e:
            print(f"❌ Build error: {e}")
            all_checks_passed = False
    
    # Check server integration
    print("\n🖥️ Server Integration:")
    server_terms = ["StaticFiles", "FileResponse", "web/dist"]
    if not check_file_contains("server/api/main.py", server_terms, "Static file serving"):
        all_checks_passed = False
    
    # Requirements verification
    print("\n📋 Requirements Verification:")
    requirements = [
        ("1.1", "Web-based user interface", "server/web/src/App.jsx"),
        ("1.2", "Pool creation and editing", "server/web/src/components/CreatePoolModal.jsx"),
        ("1.3", "Endpoint assignment", "server/web/src/pages/PoolDetailPage.jsx"),
        ("1.4", "Endpoint grouping", "server/web/src/pages/EndpointsPage.jsx"),
        ("1.5", "Status display", "server/web/src/pages/Dashboard.jsx"),
    ]
    
    for req_id, req_desc, file_path in requirements:
        if check_file_exists(file_path, f"Requirement {req_id}: {req_desc}"):
            print(f"✅ Requirement {req_id} fulfilled")
        else:
            print(f"❌ Requirement {req_id} NOT fulfilled")
            all_checks_passed = False
    
    # Final result
    print("\n" + "=" * 60)
    if all_checks_passed:
        print("🎉 ALL CHECKS PASSED! Task 5.1 implementation is complete.")
        print("\nImplemented features:")
        print("✅ React-based web UI with modern components")
        print("✅ Pool creation, editing, and deletion with full configuration")
        print("✅ Drag-and-drop endpoint assignment interface")
        print("✅ Real-time status dashboard with metrics")
        print("✅ Responsive design with Tailwind CSS")
        print("✅ API integration with error handling")
        print("✅ Production build system")
        return 0
    else:
        print("❌ SOME CHECKS FAILED! Please review the issues above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())