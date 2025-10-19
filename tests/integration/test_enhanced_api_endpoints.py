#!/usr/bin/env python3
"""
Test script for enhanced API endpoints (Task 12).
Tests the new /parse endpoint features, /healthz enhancements, and /cache/stats endpoint.
"""

import requests
import json
import time
from datetime import datetime

# API base URL
BASE_URL = "http://localhost:8000"

def test_parse_endpoint_basic():
    """Test basic parse endpoint functionality."""
    print("🧪 Testing basic /parse endpoint...")
    
    response = requests.post(f"{BASE_URL}/parse", json={
        "text": "Meeting with John tomorrow at 2pm in Conference Room A",
        "timezone": "America/New_York"
    })
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Basic parsing successful - Confidence: {data.get('confidence_score', 0):.2f}")
        print(f"   Title: {data.get('title')}")
        print(f"   Start: {data.get('start_datetime')}")
        print(f"   Location: {data.get('location')}")
        return True
    else:
        print(f"❌ Basic parsing failed: {response.status_code} - {response.text}")
        return False

def test_parse_endpoint_audit_mode():
    """Test /parse endpoint with audit mode."""
    print("\n🧪 Testing /parse endpoint with audit mode...")
    
    response = requests.post(f"{BASE_URL}/parse?mode=audit", json={
        "text": "Team standup meeting tomorrow at 9am",
        "timezone": "UTC"
    })
    
    if response.status_code == 200:
        data = response.json()
        metadata = data.get('parsing_metadata', {})
        
        # Check for audit information
        if 'routing_decisions' in metadata:
            print("✅ Audit mode working - routing decisions included")
            print(f"   Parsing method: {metadata['routing_decisions'].get('parsing_method')}")
            print(f"   LLM enhanced: {metadata['routing_decisions'].get('llm_enhancement_used')}")
            
            if 'confidence_breakdown' in metadata:
                print(f"   Confidence breakdown: {metadata['confidence_breakdown']}")
            
            return True
        else:
            print("❌ Audit mode missing routing decisions")
            return False
    else:
        print(f"❌ Audit mode failed: {response.status_code} - {response.text}")
        return False

def test_parse_endpoint_partial_parsing():
    """Test /parse endpoint with partial parsing (fields parameter)."""
    print("\n🧪 Testing /parse endpoint with partial parsing...")
    
    response = requests.post(f"{BASE_URL}/parse?fields=title,start", json={
        "text": "Lunch meeting with Sarah next Friday at noon at Cafe Downtown",
        "timezone": "America/Los_Angeles"
    })
    
    if response.status_code == 200:
        data = response.json()
        metadata = data.get('parsing_metadata', {})
        
        if metadata.get('partial_parsing') and metadata.get('requested_fields'):
            print("✅ Partial parsing working")
            print(f"   Requested fields: {metadata['requested_fields']}")
            print(f"   Title: {data.get('title')}")
            print(f"   Start: {data.get('start_datetime')}")
            print(f"   Location (should be None): {data.get('location')}")
            return True
        else:
            print("❌ Partial parsing not working properly")
            return False
    else:
        print(f"❌ Partial parsing failed: {response.status_code} - {response.text}")
        return False

def test_healthz_endpoint():
    """Test enhanced /healthz endpoint."""
    print("\n🧪 Testing enhanced /healthz endpoint...")
    
    response = requests.get(f"{BASE_URL}/healthz")
    
    if response.status_code == 200:
        data = response.json()
        
        required_fields = ['status', 'timestamp', 'version', 'services', 'uptime_seconds']
        missing_fields = [field for field in required_fields if field not in data]
        
        if not missing_fields:
            print("✅ Health check working")
            print(f"   Status: {data['status']}")
            print(f"   Uptime: {data['uptime_seconds']:.1f}s")
            print(f"   Services: {list(data['services'].keys())}")
            
            # Check for performance metrics
            services = data['services']
            if any(key in services for key in ['regex_parser', 'llm_service', 'cache']):
                print("✅ Performance metrics included in health check")
            
            return True
        else:
            print(f"❌ Health check missing fields: {missing_fields}")
            return False
    else:
        print(f"❌ Health check failed: {response.status_code} - {response.text}")
        return False

def test_cache_stats_endpoint():
    """Test /cache/stats endpoint."""
    print("\n🧪 Testing /cache/stats endpoint...")
    
    response = requests.get(f"{BASE_URL}/cache/stats")
    
    if response.status_code == 200:
        data = response.json()
        
        if data.get('success') and 'cache_stats' in data:
            cache_stats = data['cache_stats']
            print("✅ Cache stats endpoint working")
            print(f"   Status: {cache_stats.get('status')}")
            print(f"   Total requests: {cache_stats.get('total_requests', 0)}")
            print(f"   Hit ratio: {cache_stats.get('hit_ratio', 0):.2%}")
            print(f"   Cache size: {cache_stats.get('cache_size_mb', 0):.2f} MB")
            print(f"   TTL: {cache_stats.get('ttl_hours', 0)} hours")
            
            # Check for performance impact metrics
            if 'performance_impact' in data:
                perf = data['performance_impact']
                print(f"   Performance impact: {perf}")
            
            return True
        else:
            print(f"❌ Cache stats malformed response: {data}")
            return False
    else:
        print(f"❌ Cache stats failed: {response.status_code} - {response.text}")
        return False

def test_cache_functionality():
    """Test that caching actually works by making identical requests."""
    print("\n🧪 Testing cache functionality...")
    
    test_request = {
        "text": "Board meeting next Monday at 10am in the main conference room",
        "timezone": "America/New_York"
    }
    
    # First request (should be cache miss)
    start_time = time.time()
    response1 = requests.post(f"{BASE_URL}/parse", json=test_request)
    first_duration = time.time() - start_time
    
    if response1.status_code != 200:
        print(f"❌ First request failed: {response1.status_code}")
        return False
    
    data1 = response1.json()
    cache_hit1 = data1.get('parsing_metadata', {}).get('cache_hit', False)
    
    # Second identical request (should be cache hit)
    start_time = time.time()
    response2 = requests.post(f"{BASE_URL}/parse", json=test_request)
    second_duration = time.time() - start_time
    
    if response2.status_code != 200:
        print(f"❌ Second request failed: {response2.status_code}")
        return False
    
    data2 = response2.json()
    cache_hit2 = data2.get('parsing_metadata', {}).get('cache_hit', False)
    
    print(f"   First request - Cache hit: {cache_hit1}, Duration: {first_duration:.3f}s")
    print(f"   Second request - Cache hit: {cache_hit2}, Duration: {second_duration:.3f}s")
    
    # Verify caching behavior
    if not cache_hit1 and cache_hit2:
        print("✅ Cache functionality working correctly")
        if second_duration < first_duration:
            print(f"   Cache provided speedup: {(first_duration - second_duration) * 1000:.1f}ms")
        return True
    else:
        print("❌ Cache functionality not working as expected")
        return False

def test_invalid_fields_parameter():
    """Test error handling for invalid fields parameter."""
    print("\n🧪 Testing invalid fields parameter handling...")
    
    response = requests.post(f"{BASE_URL}/parse?fields=invalid_field,another_invalid", json={
        "text": "Test meeting tomorrow",
        "timezone": "UTC"
    })
    
    if response.status_code == 400:
        print("✅ Invalid fields parameter properly rejected")
        return True
    else:
        print(f"❌ Invalid fields parameter not handled: {response.status_code}")
        return False

def main():
    """Run all tests for enhanced API endpoints."""
    print("🚀 Testing Enhanced API Endpoints (Task 12)")
    print("=" * 50)
    
    tests = [
        test_parse_endpoint_basic,
        test_parse_endpoint_audit_mode,
        test_parse_endpoint_partial_parsing,
        test_healthz_endpoint,
        test_cache_stats_endpoint,
        test_cache_functionality,
        test_invalid_fields_parameter
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"❌ Test {test.__name__} failed with exception: {e}")
    
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All enhanced API endpoint tests passed!")
        return True
    else:
        print("⚠️  Some tests failed. Check the API server and implementation.")
        return False

if __name__ == "__main__":
    main()