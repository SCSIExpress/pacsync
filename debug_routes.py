#!/usr/bin/env python3
"""Debug script to check actual routes."""

import sys
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from server.api.pools import router

print("Routes in pools router:")
for route in router.routes:
    print(f"  Path: {route.path}")
    if hasattr(route, 'methods'):
        print(f"    Methods: {route.methods}")
    if hasattr(route, 'endpoint'):
        print(f"    Endpoint: {route.endpoint.__name__}")
    print()