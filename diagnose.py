#!/usr/bin/env python3
"""
Diagnostic script to help debug Render deployment issues.
"""

import os
import sys

def diagnose_deployment():
    """Diagnose the current deployment setup."""
    print("🔍 DEPLOYMENT DIAGNOSTICS")
    print("=" * 50)
    
    print(f"Python version: {sys.version}")
    print(f"Current directory: {os.getcwd()}")
    print(f"PORT environment: {os.environ.get('PORT', 'Not set')}")
    
    print("\n📁 Directory structure:")
    if os.path.exists('api'):
        print("  ✅ api/ exists")
        if os.path.exists('api/__init__.py'):
            print("  ✅ api/__init__.py exists")
        else:
            print("  ❌ api/__init__.py missing")
            
        if os.path.exists('api/app'):
            print("  ✅ api/app/ exists")
            if os.path.exists('api/app/__init__.py'):
                print("  ✅ api/app/__init__.py exists")
            else:
                print("  ❌ api/app/__init__.py missing")
                
            if os.path.exists('api/app/main.py'):
                print("  ✅ api/app/main.py exists")
            else:
                print("  ❌ api/app/main.py missing")
        else:
            print("  ❌ api/app/ missing")
    else:
        print("  ❌ api/ missing")
    
    print("\n🧪 Import tests:")
    try:
        import api
        print("  ✅ import api - SUCCESS")
    except Exception as e:
        print(f"  ❌ import api - FAILED: {e}")
    
    try:
        import api.app
        print("  ✅ import api.app - SUCCESS")
    except Exception as e:
        print(f"  ❌ import api.app - FAILED: {e}")
    
    try:
        from api.app import main
        print("  ✅ from api.app import main - SUCCESS")
    except Exception as e:
        print(f"  ❌ from api.app import main - FAILED: {e}")
    
    try:
        from api.app.main import app
        print("  ✅ from api.app.main import app - SUCCESS")
        print(f"     App type: {type(app)}")
        print(f"     App title: {getattr(app, 'title', 'No title')}")
    except Exception as e:
        print(f"  ❌ from api.app.main import app - FAILED: {e}")
    
    print("\n⚙️  Configuration files:")
    config_files = ['Procfile', 'render.yaml', '.render.yaml', 'start.sh']
    for file in config_files:
        if os.path.exists(file):
            print(f"  ✅ {file} exists")
            try:
                with open(file, 'r') as f:
                    content = f.read()
                    if 'uvicorn' in content:
                        for line in content.split('\n'):
                            if 'uvicorn' in line and line.strip():
                                print(f"     Command: {line.strip()}")
            except Exception as e:
                print(f"     Error reading: {e}")
        else:
            print(f"  ❌ {file} missing")
    
    print("\n🚫 Ignored files (.renderignore):")
    if os.path.exists('.renderignore'):
        print("  ✅ .renderignore exists")
        try:
            with open('.renderignore', 'r') as f:
                ignored = [line.strip() for line in f if line.strip() and not line.startswith('#')]
                for pattern in ignored[:10]:  # Show first 10
                    print(f"     Ignoring: {pattern}")
                if len(ignored) > 10:
                    print(f"     ... and {len(ignored) - 10} more patterns")
        except Exception as e:
            print(f"     Error reading: {e}")
    else:
        print("  ❌ .renderignore missing")
    
    print("\n🔧 Recommended command:")
    print("  uvicorn api.app.main:app --host 0.0.0.0 --port $PORT")
    
    print("\n" + "=" * 50)

if __name__ == "__main__":
    diagnose_deployment()