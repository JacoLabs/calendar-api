#!/usr/bin/env python3
"""
Quick script to test the local API server health endpoints.
"""

import requests
import json
import sys
from datetime import datetime

def test_fastapi_server():
    """Test FastAPI server endpoints."""
    base_url = "http://localhost:8000"
    
    print("🧪 Testing FastAPI Server (localhost:8000)")
    print("=" * 50)
    
    # Test root endpoint
    try:
        response = requests.get(f"{base_url}/")
        print(f"✅ Root endpoint: {response.status_code}")
        if response.status_code == 200:
            print(f"   Response: {response.json()}")
    except Exception as e:
        print(f"❌ Root endpoint failed: {e}")
    
    # Test lightweight health check
    try:
        response = requests.get(f"{base_url}/healthz")
        print(f"✅ Lightweight health: {response.status_code}")
        if response.status_code == 204:
            print("   ✅ Returns 204 No Content as expected")
    except Exception as e:
        print(f"❌ Lightweight health failed: {e}")
    
    # Test detailed health check
    try:
        response = requests.get(f"{base_url}/health")
        print(f"✅ Detailed health: {response.status_code}")
        if response.status_code == 200:
            health_data = response.json()
            print(f"   Status: {health_data.get('status')}")
            print(f"   Uptime: {health_data.get('uptime_seconds', 0):.1f}s")
            services = health_data.get('services', {})
            for service, status in services.items():
                print(f"   {service}: {status}")
    except Exception as e:
        print(f"❌ Detailed health failed: {e}")
    
    # Test API info
    try:
        response = requests.get(f"{base_url}/api/info")
        print(f"✅ API info: {response.status_code}")
        if response.status_code == 200:
            info = response.json()
            print(f"   Version: {info.get('version')}")
            print(f"   Features: {len(info.get('features', []))} available")
    except Exception as e:
        print(f"❌ API info failed: {e}")
    
    # Test parse endpoint
    try:
        test_data = {"text": "Meeting tomorrow at 2pm"}
        response = requests.post(f"{base_url}/parse", json=test_data)
        print(f"✅ Parse endpoint: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"   Parsed title: {result.get('title')}")
            print(f"   Confidence: {result.get('confidence_score', 0):.2f}")
    except Exception as e:
        print(f"❌ Parse endpoint failed: {e}")

def test_flask_server():
    """Test Flask server endpoints."""
    base_url = "http://localhost:5000"
    
    print("\n🧪 Testing Flask Server (localhost:5000)")
    print("=" * 50)
    
    # Test health endpoint
    try:
        response = requests.get(f"{base_url}/health")
        print(f"✅ Health endpoint: {response.status_code}")
        if response.status_code == 200:
            health_data = response.json()
            print(f"   Status: {health_data.get('status')}")
            print(f"   Parser available: {health_data.get('hybrid_parser_available')}")
    except Exception as e:
        print(f"❌ Health endpoint failed: {e}")
    
    # Test parse endpoint
    try:
        test_data = {"text": "Meeting tomorrow at 2pm"}
        response = requests.post(f"{base_url}/parse", json=test_data)
        print(f"✅ Parse endpoint: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"   Parsed title: {result.get('title')}")
            print(f"   Confidence: {result.get('confidence_score', 0):.2f}")
    except Exception as e:
        print(f"❌ Parse endpoint failed: {e}")

def main():
    """Run all tests."""
    print(f"🚀 API Server Health Check - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Test FastAPI server first
    test_fastapi_server()
    
    # Test Flask server
    test_flask_server()
    
    print("\n" + "=" * 50)
    print("💡 Tips:")
    print("   - FastAPI server should be running on port 8000")
    print("   - Flask server should be running on port 5000")
    print("   - Use 'python app.py' for FastAPI server")
    print("   - Use 'python api_server.py' for Flask server")

if __name__ == "__main__":
    main()