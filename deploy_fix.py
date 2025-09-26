#!/usr/bin/env python3
"""
Quick deployment fix test
"""

def test_imports():
    try:
        from app.main import app
        print("✅ app.main import works")
        
        # Test that the app has routes
        routes = [route.path for route in app.routes]
        print(f"✅ Routes found: {routes}")
        
        return True
    except Exception as e:
        print(f"❌ Import failed: {e}")
        return False

if __name__ == "__main__":
    test_imports()