#!/usr/bin/env python3
"""
Debug script to check Python path and module availability.
"""

import sys
import os
from pathlib import Path

print("=== Debug Information ===")
print(f"Current working directory: {os.getcwd()}")
print(f"Python executable: {sys.executable}")
print(f"Python version: {sys.version}")
print()

print("=== Python Path ===")
for i, path in enumerate(sys.path):
    print(f"{i}: {path}")
print()

# Add project root to Python path
project_root = Path(__file__).parent.absolute()
print(f"Project root: {project_root}")
sys.path.insert(0, str(project_root))

print("=== Updated Python Path ===")
for i, path in enumerate(sys.path):
    print(f"{i}: {path}")
print()

print("=== Directory Contents ===")
print("Root directory contents:")
for item in sorted(os.listdir(".")):
    item_path = Path(item)
    if item_path.is_dir():
        print(f"  [DIR]  {item}")
    else:
        print(f"  [FILE] {item}")
print()

print("Server directory contents:")
if os.path.exists("server"):
    try:
        items = os.listdir("server")
        if not items:
            print("  server directory is EMPTY!")
        else:
            for item in sorted(items):
                item_path = Path("server") / item
                if item_path.is_dir():
                    print(f"  [DIR]  server/{item}")
                    # Show subdirectory contents too
                    try:
                        subitems = os.listdir(item_path)
                        if not subitems:
                            print(f"    (empty directory)")
                        else:
                            for subitem in sorted(subitems):
                                subitem_path = item_path / subitem
                                if subitem_path.is_dir():
                                    print(f"    [DIR]  server/{item}/{subitem}")
                                else:
                                    print(f"    [FILE] server/{item}/{subitem}")
                    except PermissionError:
                        print(f"    [PERM] Cannot read server/{item}")
                    except Exception as e:
                        print(f"    [ERROR] {e}")
                else:
                    print(f"  [FILE] server/{item}")
    except Exception as e:
        print(f"  Error reading server directory: {e}")
else:
    print("  server directory does not exist!")
print()

print("Server/api directory contents:")
if os.path.exists("server/api"):
    for item in sorted(os.listdir("server/api")):
        item_path = Path("server/api") / item
        if item_path.is_dir():
            print(f"  [DIR]  server/api/{item}")
        else:
            print(f"  [FILE] server/api/{item}")
else:
    print("  server/api directory does not exist!")
print()

print("=== Import Tests ===")
try:
    import server
    print("✓ Successfully imported 'server'")
    print(f"  server.__file__: {server.__file__}")
except ImportError as e:
    print(f"✗ Failed to import 'server': {e}")

try:
    import server.api
    print("✓ Successfully imported 'server.api'")
    print(f"  server.api.__file__: {server.api.__file__}")
except ImportError as e:
    print(f"✗ Failed to import 'server.api': {e}")

try:
    from server.api import main
    print("✓ Successfully imported 'server.api.main'")
    print(f"  server.api.main.__file__: {main.__file__}")
except ImportError as e:
    print(f"✗ Failed to import 'server.api.main': {e}")

try:
    from server.api.main import app
    print("✓ Successfully imported 'app' from 'server.api.main'")
    print(f"  app type: {type(app)}")
except ImportError as e:
    print(f"✗ Failed to import 'app' from 'server.api.main': {e}")