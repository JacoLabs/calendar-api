#!/usr/bin/env python3
"""
Quick deployment test to verify all imports work.
"""

def test_imports():
    """Test that all required modules can be imported."""
    try:
        print("Testing imports...")
        
        # Test FastAPI imports
        from fastapi import FastAPI
        print("✅ FastAPI imported")
        
        from pydantic import BaseModel
        print("✅ Pydantic imported")
        
        import uvicorn
        print("✅ Uvicorn imported")
        
        # Test our app import
        from app import app
        print("✅ App imported successfully")
        
        # Test that the app has the expected endpoints
        routes = [route.path for route in app.routes]
        expected_routes = ["/", "/healthz", "/parse"]
        
        for route in expected_routes:
            if route in routes:
                print(f"✅ Route {route} found")
            else:
                print(f"❌ Route {route} missing")
        
        print("\n🎉 All imports successful! Ready for deployment.")
        return True
        
    except Exception as e:
        print(f"❌ Import error: {e}")
        return False

if __name__ == "__main__":
    success = test_imports()
    exit(0 if success else 1)