#!/usr/bin/env python3
"""
Debug script to help understand Render deployment issues.
"""

import os
import sys
import importlib.util

def debug_render_environment():
    """Debug the Render environment and module paths."""
    print("="*60)
    print("RENDER DEPLOYMENT DEBUG")
    print("="*60)
    
    print(f"Python version: {sys.version}")
    print(f"Python executable: {sys.executable}")
    print(f"Current working directory: {os.getcwd()}")
    print(f"PYTHONPATH: {os.environ.get('PYTHONPATH', 'Not set')}")
    print(f"PORT: {os.environ.get('PORT', 'Not set')}")
    
    print("\nPython sys.path:")
    for i, path in enumerate(sys.path):
        print(f"  {i}: {path}")
    
    print("\nFiles in current directory:")
    try:
        files = os.listdir('.')
        for file in sorted(files):
            if os.path.isfile(file):
                print(f"  📄 {file}")
            else:
                print(f"  📁 {file}/")
    except Exception as e:
        print(f"  Error listing files: {e}")
    
    print("\nTesting imports:")
    
    # Test 1: Direct wsgi import
    try:
        import wsgi
        print("  ✅ import wsgi - SUCCESS")
        print(f"     wsgi.app: {wsgi.app}")
    except Exception as e:
        print(f"  ❌ import wsgi - FAILED: {e}")
    
    # Test 2: api.app.main import
    try:
        from api.app.main import app
        print("  ✅ from api.app.main import app - SUCCESS")
        print(f"     app: {app}")
    except Exception as e:
        print(f"  ❌ from api.app.main import app - FAILED: {e}")
    
    # Test 3: Check if api directory exists
    if os.path.exists('api'):
        print("  ✅ api/ directory exists")
        if os.path.exists('api/__init__.py'):
            print("  ✅ api/__init__.py exists")
        else:
            print("  ❌ api/__init__.py missing")
            
        if os.path.exists('api/app'):
            print("  ✅ api/app/ directory exists")
            if os.path.exists('api/app/__init__.py'):
                print("  ✅ api/app/__init__.py exists")
            else:
                print("  ❌ api/app/__init__.py missing")
                
            if os.path.exists('api/app/main.py'):
                print("  ✅ api/app/main.py exists")
            else:
                print("  ❌ api/app/main.py missing")
        else:
            print("  ❌ api/app/ directory missing")
    else:
        print("  ❌ api/ directory missing")
    
    # Test 4: Check for conflicting files
    conflicting_files = ['main.py', 'app.py', 'application.py']
    for file in conflicting_files:
        if os.path.exists(file):
            print(f"  ⚠️  Conflicting file found: {file}")
        else:
            print(f"  ✅ No conflicting file: {file}")
    
    print("\nConfiguration files:")
    config_files = ['Procfile', 'render.yaml', '.render.yaml', 'start.sh', 'wsgi.py']
    for file in config_files:
        if os.path.exists(file):
            print(f"  ✅ {file} exists")
            try:
                with open(file, 'r') as f:
                    content = f.read().strip()
                    if 'uvicorn' in content:
                        lines = [line.strip() for line in content.split('\n') if 'uvicorn' in line]
                        for line in lines:
                            print(f"     Command: {line}")
            except Exception as e:
                print(f"     Error reading {file}: {e}")
        else:
            print(f"  ❌ {file} missing")
    
    print("="*60)

if __name__ == "__main__":
    debug_render_environment()