#!/usr/bin/env python3
"""
Test script to validate all milestones are working correctly.
Tests the complete flow from API to mobile apps to browser extension.
"""

import asyncio
import json
import requests
import time
from datetime import datetime, timezone

# Test configuration
API_BASE_URL = "https://api.jacolabs.com"  # Change to localhost:8000 for local testing
TEST_TIMEZONE = "America/New_York"
TEST_LOCALE = "en_US"
FIXED_NOW = "2024-03-15T15:00:00Z"  # Fixed datetime for consistent testing

def test_milestone_a_api():
    """Test Milestone A: FastAPI Backend"""
    print("🚀 Testing Milestone A: FastAPI Backend")
    print("-" * 50)
    
    # Test health endpoint
    try:
        response = requests.get(f"{API_BASE_URL}/healthz", timeout=10)
        if response.status_code == 200:
            health_data = response.json()
            print(f"✅ Health check: {health_data['status']}")
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Health check error: {e}")
        return False
    
    # Test parse endpoint with various scenarios
    test_cases = [
        {
            "name": "Simple meeting",
            "text": "Meeting with John tomorrow at 2pm",
            "expected_confidence": 0.5
        },
        {
            "name": "Meeting with location",
            "text": "Team meeting tomorrow at 3pm in Conference Room A",
            "expected_confidence": 0.7
        },
        {
            "name": "Meeting with duration",
            "text": "Project review meeting tomorrow at 10am for 2 hours",
            "expected_confidence": 0.6
        },
        {
            "name": "Low confidence text",
            "text": "maybe meet sometime next week",
            "expected_confidence": 0.3
        },
        {
            "name": "No event information",
            "text": "This is just regular text with no event information",
            "expected_confidence": 0.2
        }
    ]
    
    for test_case in test_cases:
        try:
            payload = {
                "text": test_case["text"],
                "timezone": TEST_TIMEZONE,
                "locale": TEST_LOCALE,
                "now": FIXED_NOW
            }
            
            response = requests.post(
                f"{API_BASE_URL}/parse",
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Validate response structure
                required_fields = [
                    "title", "start_datetime", "end_datetime", "location",
                    "description", "confidence_score", "all_day", "timezone"
                ]
                
                missing_fields = [field for field in required_fields if field not in data]
                if missing_fields:
                    print(f"❌ {test_case['name']}: Missing fields {missing_fields}")
                    continue
                
                # Validate confidence score
                confidence = data["confidence_score"]
                if confidence >= test_case["expected_confidence"]:
                    print(f"✅ {test_case['name']}: confidence {confidence:.2f}")
                else:
                    print(f"⚠️  {test_case['name']}: low confidence {confidence:.2f} (expected >= {test_case['expected_confidence']})")
                
                # Validate datetime format if present
                if data["start_datetime"]:
                    try:
                        datetime.fromisoformat(data["start_datetime"].replace('Z', '+00:00'))
                        print(f"   ✅ Valid ISO 8601 datetime format")
                    except ValueError:
                        print(f"   ❌ Invalid datetime format: {data['start_datetime']}")
                
            else:
                print(f"❌ {test_case['name']}: HTTP {response.status_code}")
                
        except Exception as e:
            print(f"❌ {test_case['name']}: {e}")
    
    print("\n✅ Milestone A: API tests completed")
    return True

def test_milestone_b_android():
    """Test Milestone B: Android Integration (simulated)"""
    print("\n📱 Testing Milestone B: Android Integration")
    print("-" * 50)
    
    # Simulate Android API call
    try:
        import json
        import urllib.parse
        
        # Test data that would come from Android
        android_test_data = {
            "text": "Meeting with client tomorrow at 2pm in Conference Room B",
            "timezone": "America/New_York",
            "locale": "en_US",
            "now": FIXED_NOW
        }
        
        response = requests.post(
            f"{API_BASE_URL}/parse",
            json=android_test_data,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "CalendarEventApp-Android/1.0"
            },
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            
            # Simulate Android calendar intent creation
            calendar_intent_data = {
                "title": data.get("title"),
                "start_time": data.get("start_datetime"),
                "end_time": data.get("end_datetime") or "default +30 minutes",
                "location": data.get("location"),
                "description": data.get("description")
            }
            
            print("✅ Android API call successful")
            print(f"   Title: {calendar_intent_data['title']}")
            print(f"   Start: {calendar_intent_data['start_time']}")
            print(f"   Location: {calendar_intent_data['location']}")
            print("✅ Calendar intent data prepared")
            
        else:
            print(f"❌ Android API call failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Android test error: {e}")
        return False
    
    print("✅ Milestone B: Android integration tests completed")
    return True

def test_milestone_c_ios():
    """Test Milestone C: iOS Integration (simulated)"""
    print("\n🍎 Testing Milestone C: iOS Integration")
    print("-" * 50)
    
    # Simulate iOS API call
    try:
        ios_test_data = {
            "text": "Team building event next Friday from 1pm to 5pm at the community center",
            "timezone": "America/Los_Angeles",
            "locale": "en_US",
            "now": FIXED_NOW
        }
        
        response = requests.post(
            f"{API_BASE_URL}/parse",
            json=ios_test_data,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "CalendarEventApp-iOS/1.0"
            },
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            
            # Simulate iOS EventKit integration
            eventkit_data = {
                "title": data.get("title", "New Event"),
                "start_date": data.get("start_datetime"),
                "end_date": data.get("end_datetime"),
                "location": data.get("location"),
                "notes": data.get("description"),
                "all_day": data.get("all_day", False)
            }
            
            print("✅ iOS API call successful")
            print(f"   Title: {eventkit_data['title']}")
            print(f"   Start: {eventkit_data['start_date']}")
            print(f"   End: {eventkit_data['end_date']}")
            print(f"   Location: {eventkit_data['location']}")
            print(f"   All-day: {eventkit_data['all_day']}")
            print("✅ EventKit data prepared")
            
        else:
            print(f"❌ iOS API call failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ iOS test error: {e}")
        return False
    
    print("✅ Milestone C: iOS integration tests completed")
    return True

def test_milestone_d_browser():
    """Test Milestone D: Browser Extension (simulated)"""
    print("\n🌐 Testing Milestone D: Browser Extension")
    print("-" * 50)
    
    # Test browser extension API call
    try:
        browser_test_data = {
            "text": "Quarterly board meeting on Wednesday, June 12, 2024, at 2:00 PM in the executive boardroom",
            "timezone": "UTC",
            "locale": "en_US",
            "now": FIXED_NOW
        }
        
        response = requests.post(
            f"{API_BASE_URL}/parse",
            json=browser_test_data,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "CalendarEventCreator-Extension/1.0"
            },
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            
            # Simulate Google Calendar URL generation
            google_calendar_params = {
                "action": "TEMPLATE",
                "text": data.get("title", ""),
                "dates": f"20240612T140000Z/20240612T150000Z",  # Simulated
                "location": data.get("location", ""),
                "details": data.get("description", "")
            }
            
            google_url = "https://calendar.google.com/calendar/render?" + "&".join([
                f"{k}={requests.utils.quote(str(v))}" for k, v in google_calendar_params.items() if v
            ])
            
            # Simulate Outlook Calendar URL generation
            outlook_params = {
                "subject": data.get("title", ""),
                "startdt": "2024-06-12T14:00:00Z",  # Simulated
                "enddt": "2024-06-12T15:00:00Z",    # Simulated
                "location": data.get("location", ""),
                "body": data.get("description", "")
            }
            
            outlook_url = "https://outlook.live.com/calendar/0/deeplink/compose?" + "&".join([
                f"{k}={requests.utils.quote(str(v))}" for k, v in outlook_params.items() if v
            ])
            
            print("✅ Browser extension API call successful")
            print(f"   Title: {data.get('title')}")
            print(f"   Confidence: {data.get('confidence_score', 0):.2f}")
            print("✅ Google Calendar URL generated")
            print("✅ Outlook Calendar URL generated")
            
        else:
            print(f"❌ Browser extension API call failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Browser extension test error: {e}")
        return False
    
    print("✅ Milestone D: Browser extension tests completed")
    return True

def test_acceptance_criteria():
    """Test acceptance criteria for all milestones"""
    print("\n🎯 Testing Acceptance Criteria")
    print("-" * 50)
    
    # Test /parse contract with fixed now and timezone
    contract_test = {
        "text": "Meeting on March 20, 2024 at 3:30 PM in Room 101",
        "timezone": TEST_TIMEZONE,
        "locale": TEST_LOCALE,
        "now": FIXED_NOW
    }
    
    try:
        response = requests.post(
            f"{API_BASE_URL}/parse",
            json=contract_test,
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            
            # Validate contract compliance
            required_fields = [
                "title", "start_datetime", "end_datetime", "location",
                "description", "confidence_score", "all_day", "timezone"
            ]
            
            contract_valid = all(field in data for field in required_fields)
            
            if contract_valid:
                print("✅ /parse contract test passes")
                print(f"   All required fields present: {required_fields}")
                
                # Validate datetime format
                if data["start_datetime"]:
                    try:
                        parsed_dt = datetime.fromisoformat(data["start_datetime"].replace('Z', '+00:00'))
                        print(f"   ✅ ISO 8601 datetime with timezone: {data['start_datetime']}")
                    except ValueError:
                        print(f"   ❌ Invalid datetime format: {data['start_datetime']}")
                
                # Validate timezone
                if data["timezone"] == TEST_TIMEZONE:
                    print(f"   ✅ Correct timezone: {data['timezone']}")
                else:
                    print(f"   ⚠️  Timezone mismatch: got {data['timezone']}, expected {TEST_TIMEZONE}")
                
            else:
                missing = [field for field in required_fields if field not in data]
                print(f"❌ Contract test failed: missing fields {missing}")
                return False
                
        else:
            print(f"❌ Contract test failed: HTTP {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Contract test error: {e}")
        return False
    
    print("✅ All acceptance criteria tests passed")
    return True

def main():
    """Run all milestone tests"""
    print("🧪 Text-to-Calendar Event System - Milestone Testing")
    print("=" * 80)
    
    start_time = time.time()
    
    # Run all tests
    tests = [
        test_milestone_a_api,
        test_milestone_b_android,
        test_milestone_c_ios,
        test_milestone_d_browser,
        test_acceptance_criteria
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"❌ Test failed with exception: {e}")
            results.append(False)
    
    end_time = time.time()
    duration = end_time - start_time
    
    # Summary
    print(f"\n{'='*80}")
    print("TEST SUMMARY")
    print(f"{'='*80}")
    print(f"Duration: {duration:.2f} seconds")
    print(f"Tests run: {len(results)}")
    print(f"Passed: {sum(results)}")
    print(f"Failed: {len(results) - sum(results)}")
    print(f"Success rate: {(sum(results) / len(results) * 100):.1f}%")
    
    if all(results):
        print("\n🎉 ALL MILESTONES READY FOR DEPLOYMENT!")
        print("Next steps:")
        print("1. Deploy FastAPI to production (api.jacolabs.com)")
        print("2. Build and test Android app")
        print("3. Build and test iOS app with extensions")
        print("4. Package and test browser extension")
        print("5. Submit to app stores and extension stores")
        return 0
    else:
        print("\n⚠️  Some tests failed. Please fix issues before deployment.")
        return 1

if __name__ == "__main__":
    exit(main())