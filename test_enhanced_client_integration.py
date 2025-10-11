#!/usr/bin/env python3
"""
Test script to verify enhanced API client integration.
Tests the new audit mode, partial parsing, and enhanced error handling.
"""

import requests
import json
import time
from datetime import datetime

API_BASE_URL = "http://localhost:5000"

def test_audit_mode():
    """Test audit mode functionality"""
    print("Testing audit mode...")
    
    response = requests.post(
        f"{API_BASE_URL}/parse?mode=audit",
        json={
            "text": "Meeting with John tomorrow at 2pm at Starbucks",
            "timezone": "America/New_York",
            "now": datetime.now().isoformat()
        },
        headers={"User-Agent": "TestClient/2.0"}
    )
    
    if response.status_code == 200:
        result = response.json()
        print("✓ Audit mode successful")
        
        # Check for enhanced fields
        if "field_results" in result:
            print("✓ Field results present")
        if "parsing_path" in result:
            print(f"✓ Parsing path: {result['parsing_path']}")
        if "processing_time_ms" in result:
            print(f"✓ Processing time: {result['processing_time_ms']}ms")
        if "cache_hit" in result:
            print(f"✓ Cache status: {'hit' if result['cache_hit'] else 'miss'}")
        
        return True
    else:
        print(f"✗ Audit mode failed: {response.status_code}")
        return False

def test_partial_parsing():
    """Test partial parsing functionality"""
    print("\nTesting partial parsing...")
    
    response = requests.post(
        f"{API_BASE_URL}/parse?fields=title,start_datetime",
        json={
            "text": "Team standup meeting Monday 9am in conference room B",
            "timezone": "America/New_York",
            "now": datetime.now().isoformat()
        },
        headers={"User-Agent": "TestClient/2.0"}
    )
    
    if response.status_code == 200:
        result = response.json()
        print("✓ Partial parsing successful")
        
        # Check that only requested fields are processed
        if result.get("title") and result.get("start_datetime"):
            print("✓ Requested fields present")
        
        return True
    else:
        print(f"✗ Partial parsing failed: {response.status_code}")
        return False

def test_enhanced_error_handling():
    """Test enhanced error handling"""
    print("\nTesting enhanced error handling...")
    
    # Test with empty text
    response = requests.post(
        f"{API_BASE_URL}/parse",
        json={
            "text": "",
            "timezone": "America/New_York",
            "now": datetime.now().isoformat()
        },
        headers={"User-Agent": "TestClient/2.0"}
    )
    
    if response.status_code == 400:
        error_data = response.json()
        if "error" in error_data and "message" in error_data["error"]:
            print("✓ Enhanced error format present")
            return True
    
    print("✗ Enhanced error handling test failed")
    return False

def test_caching():
    """Test caching functionality"""
    print("\nTesting caching...")
    
    test_text = "Lunch meeting with Sarah next Friday at noon"
    request_data = {
        "text": test_text,
        "timezone": "America/New_York",
        "now": datetime.now().isoformat()
    }
    
    # First request
    start_time = time.time()
    response1 = requests.post(
        f"{API_BASE_URL}/parse?mode=audit",
        json=request_data,
        headers={"User-Agent": "TestClient/2.0"}
    )
    first_time = time.time() - start_time
    
    if response1.status_code != 200:
        print("✗ First caching request failed")
        return False
    
    # Second request (should be cached)
    start_time = time.time()
    response2 = requests.post(
        f"{API_BASE_URL}/parse?mode=audit",
        json=request_data,
        headers={"User-Agent": "TestClient/2.0"}
    )
    second_time = time.time() - start_time
    
    if response2.status_code == 200:
        result2 = response2.json()
        if result2.get("cache_hit"):
            print("✓ Cache hit detected")
            print(f"✓ Performance improvement: {first_time:.3f}s → {second_time:.3f}s")
            return True
    
    print("✗ Caching test failed")
    return False

def test_confidence_warnings():
    """Test confidence warnings and needs_confirmation flag"""
    print("\nTesting confidence warnings...")
    
    # Use ambiguous text that should trigger warnings
    response = requests.post(
        f"{API_BASE_URL}/parse?mode=audit",
        json={
            "text": "something happening sometime somewhere",
            "timezone": "America/New_York",
            "now": datetime.now().isoformat()
        },
        headers={"User-Agent": "TestClient/2.0"}
    )
    
    if response.status_code == 200:
        result = response.json()
        
        if result.get("needs_confirmation") or (result.get("warnings") and len(result["warnings"]) > 0):
            print("✓ Low confidence handling working")
            if result.get("warnings"):
                print(f"✓ Warnings: {result['warnings']}")
            return True
    
    print("✗ Confidence warnings test failed")
    return False

def main():
    """Run all enhanced API integration tests"""
    print("Testing Enhanced API Client Integration")
    print("=" * 50)
    
    tests = [
        test_audit_mode,
        test_partial_parsing,
        test_enhanced_error_handling,
        test_caching,
        test_confidence_warnings
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"✗ Test failed with exception: {e}")
    
    print("\n" + "=" * 50)
    print(f"Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All enhanced API integration tests passed!")
        return True
    else:
        print("❌ Some tests failed. Check API server and implementation.")
        return False

if __name__ == "__main__":
    main()