#!/usr/bin/env python3
"""
Test script to verify the live API is working correctly.
"""

import requests
import json
from datetime import datetime

API_BASE_URL = "https://calendar-api-wrxz.onrender.com"

def test_health_endpoint():
    """Test the health endpoint."""
    print("🔍 Testing health endpoint...")
    try:
        response = requests.get(f"{API_BASE_URL}/healthz", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Health check: {data['status']}")
            return True
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Health check error: {e}")
        return False

def test_parse_endpoint():
    """Test the parse endpoint with sample text."""
    print("\n🔍 Testing parse endpoint...")
    
    test_data = {
        "text": "Meeting with John tomorrow at 2pm in Conference Room A",
        "timezone": "America/New_York",
        "locale": "en_US"
    }
    
    try:
        response = requests.post(
            f"{API_BASE_URL}/parse",
            json=test_data,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Parse endpoint working!")
            print(f"   Title: {data.get('title')}")
            print(f"   Start: {data.get('start_datetime')}")
            print(f"   Location: {data.get('location')}")
            print(f"   Confidence: {data.get('confidence_score', 0):.2f}")
            return True
        else:
            print(f"❌ Parse failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Parse error: {e}")
        return False

def test_mobile_app_scenarios():
    """Test scenarios that mobile apps will use."""
    print("\n🔍 Testing mobile app scenarios...")
    
    scenarios = [
        {
            "name": "Android text selection",
            "text": "Lunch at The Keg next Friday 12:30pm",
            "timezone": "America/Toronto",
            "locale": "en_CA"
        },
        {
            "name": "iOS share extension",
            "text": "Conference call Monday 10am for 1 hour",
            "timezone": "America/Los_Angeles", 
            "locale": "en_US"
        },
        {
            "name": "Browser extension",
            "text": "Team building event this Saturday 2pm at the park",
            "timezone": "UTC",
            "locale": "en_US"
        }
    ]
    
    success_count = 0
    for scenario in scenarios:
        try:
            response = requests.post(
                f"{API_BASE_URL}/parse",
                json=scenario,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ {scenario['name']}: {data.get('title', 'No title')}")
                success_count += 1
            else:
                print(f"❌ {scenario['name']}: HTTP {response.status_code}")
                
        except Exception as e:
            print(f"❌ {scenario['name']}: {e}")
    
    print(f"\n📊 Mobile scenarios: {success_count}/{len(scenarios)} successful")
    return success_count == len(scenarios)

def main():
    """Run all API tests."""
    print("🧪 Testing Live API at", API_BASE_URL)
    print("=" * 60)
    
    health_ok = test_health_endpoint()
    parse_ok = test_parse_endpoint()
    mobile_ok = test_mobile_app_scenarios()
    
    print("\n" + "=" * 60)
    print("📋 TEST SUMMARY")
    print("=" * 60)
    
    if health_ok and parse_ok and mobile_ok:
        print("🎉 ALL TESTS PASSED! Your API is ready for mobile apps!")
        print("\n🚀 Next steps:")
        print("1. Build Android app and test text selection")
        print("2. Build iOS app and test share extension")
        print("3. Load browser extension and test context menu")
        return True
    else:
        print("⚠️  Some tests failed. Check the API deployment.")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)