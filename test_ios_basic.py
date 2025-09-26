#!/usr/bin/env python3
"""
Test script to verify iOS app API integration with the calendar parsing service.
This test simulates the API calls that the iOS app would make.
"""

import requests
import json
import sys
from datetime import datetime

# API endpoint
API_BASE_URL = "https://calendar-api-wrxz.onrender.com"
PARSE_ENDPOINT = f"{API_BASE_URL}/parse"

def test_api_connection():
    """Test basic API connectivity"""
    print("Testing API connection...")
    try:
        response = requests.get(API_BASE_URL, timeout=10)
        print(f"✓ API is reachable (Status: {response.status_code})")
        return True
    except requests.exceptions.RequestException as e:
        print(f"✗ API connection failed: {e}")
        return False

def test_parse_endpoint(text_input, expected_fields=None):
    """Test the /parse endpoint with given text input"""
    print(f"\nTesting parse endpoint with: '{text_input}'")
    
    try:
        payload = {"text": text_input}
        headers = {"Content-Type": "application/json"}
        
        response = requests.post(PARSE_ENDPOINT, json=payload, headers=headers, timeout=15)
        
        print(f"Response Status: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                print(f"Response Data: {json.dumps(data, indent=2)}")
                
                # Validate response structure
                if isinstance(data, dict):
                    # Check for expected fields
                    required_fields = ['title', 'start_datetime', 'confidence_score']
                    missing_fields = []
                    
                    for field in required_fields:
                        if field not in data:
                            missing_fields.append(field)
                    
                    if missing_fields:
                        print(f"✗ Missing required fields: {missing_fields}")
                        return False
                    
                    # Validate confidence score
                    confidence = data.get('confidence_score', 0)
                    if not isinstance(confidence, (int, float)) or confidence < 0 or confidence > 1:
                        print(f"✗ Invalid confidence score: {confidence}")
                        return False
                    
                    # Check expected fields if provided
                    if expected_fields:
                        for field, expected_value in expected_fields.items():
                            actual_value = data.get(field)
                            if expected_value and not actual_value:
                                print(f"✗ Expected {field} to have value, but got: {actual_value}")
                                return False
                    
                    print("✓ Parse endpoint test passed")
                    return True
                else:
                    print(f"✗ Unexpected response format: {type(data)}")
                    return False
                    
            except json.JSONDecodeError as e:
                print(f"✗ Invalid JSON response: {e}")
                print(f"Raw response: {response.text}")
                return False
        else:
            print(f"✗ API request failed with status {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"✗ Request failed: {e}")
        return False

def test_error_handling():
    """Test API error handling with invalid inputs"""
    print("\nTesting error handling...")
    
    # Test empty text
    test_cases = [
        {"text": ""},
        {"text": "   "},
        {},  # Missing text field
        {"text": "random text with no event information whatsoever"}
    ]
    
    for i, payload in enumerate(test_cases):
        print(f"\nTest case {i+1}: {payload}")
        try:
            response = requests.post(PARSE_ENDPOINT, json=payload, headers={"Content-Type": "application/json"}, timeout=10)
            print(f"Status: {response.status_code}")
            
            if response.status_code in [200, 400]:
                try:
                    data = response.json()
                    print(f"Response: {json.dumps(data, indent=2)}")
                except json.JSONDecodeError:
                    print(f"Non-JSON response: {response.text}")
            else:
                print(f"Unexpected status code: {response.status_code}")
                
        except requests.exceptions.RequestException as e:
            print(f"Request failed: {e}")
    
    print("✓ Error handling tests completed")

def main():
    """Run all iOS API integration tests"""
    print("iOS App API Integration Tests")
    print("=" * 40)
    
    # Test 1: Basic connectivity
    if not test_api_connection():
        print("\n✗ Basic connectivity test failed. Exiting.")
        sys.exit(1)
    
    # Test 2: Valid event parsing
    test_cases = [
        {
            "text": "Meeting with John tomorrow at 2pm",
            "expected": {"title": True, "start_datetime": True}
        },
        {
            "text": "Lunch at Starbucks next Friday 12:30",
            "expected": {"title": True, "location": True, "start_datetime": True}
        },
        {
            "text": "Conference call Monday 10am for 1 hour",
            "expected": {"title": True, "start_datetime": True}
        },
        {
            "text": "Doctor appointment on January 15th at 3:30 PM",
            "expected": {"title": True, "start_datetime": True}
        }
    ]
    
    passed_tests = 0
    total_tests = len(test_cases)
    
    for test_case in test_cases:
        if test_parse_endpoint(test_case["text"], test_case.get("expected")):
            passed_tests += 1
    
    # Test 3: Error handling
    test_error_handling()
    
    # Summary
    print(f"\n{'='*40}")
    print(f"Test Results: {passed_tests}/{total_tests} parsing tests passed")
    
    if passed_tests == total_tests:
        print("✓ All iOS API integration tests passed!")
        print("\nThe iOS app should be able to:")
        print("- Connect to the API endpoint")
        print("- Send POST requests with text data")
        print("- Receive and parse JSON responses")
        print("- Handle various event text formats")
        print("- Display parsed event information")
        sys.exit(0)
    else:
        print("✗ Some tests failed. Check the API implementation.")
        sys.exit(1)

if __name__ == "__main__":
    main()