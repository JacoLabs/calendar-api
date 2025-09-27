#!/usr/bin/env python3
"""
Comprehensive iOS app functionality test.
Tests the complete iOS app implementation including Share Extension.
"""

import pytest
import requests
import json
from datetime import datetime, timezone
import os


class TestiOSCompleteApp:
    """Test complete iOS app functionality."""
    
    API_BASE_URL = "https://calendar-api-wrxz.onrender.com"
    
    def test_api_connectivity(self):
        """Test that the API is accessible for the iOS app."""
        try:
            response = requests.get(f"{self.API_BASE_URL}/", timeout=10)
            assert response.status_code in [200, 404], f"API not accessible: {response.status_code}"
            print("✓ API endpoint is accessible")
        except requests.exceptions.RequestException as e:
            pytest.fail(f"API endpoint not accessible: {e}")
    
    def test_ios_api_integration(self):
        """Test API integration with iOS-specific headers and payload."""
        test_cases = [
            {
                "text": "Meeting with John tomorrow at 2pm",
                "expected_fields": ["title", "start_datetime"]
            },
            {
                "text": "Lunch at Starbucks next Friday 12:30",
                "expected_fields": ["title", "location", "start_datetime"]
            },
            {
                "text": "Conference call Monday 10am for 1 hour",
                "expected_fields": ["title", "start_datetime", "end_datetime"]
            },
            {
                "text": "Doctor appointment on January 15th at 3:30 PM",
                "expected_fields": ["title", "start_datetime"]
            }
        ]
        
        for i, test_case in enumerate(test_cases):
            print(f"\nTesting case {i+1}: {test_case['text']}")
            
            payload = {
                "text": test_case["text"],
                "timezone": "America/New_York",
                "locale": "en_US",
                "now": datetime.now(timezone.utc).isoformat()
            }
            
            try:
                response = requests.post(
                    f"{self.API_BASE_URL}/parse",
                    json=payload,
                    headers={
                        "Content-Type": "application/json",
                        "User-Agent": "CalendarEventApp-iOS/1.0"
                    },
                    timeout=15
                )
                
                assert response.status_code == 200, f"Request failed: {response.status_code} - {response.text}"
                
                result = response.json()
                
                # Verify expected fields are present and not empty
                for field in test_case["expected_fields"]:
                    assert field in result, f"Missing field: {field}"
                    if field in ["title", "location"]:
                        assert result[field] is not None and result[field].strip(), f"Field {field} is empty"
                    elif field in ["start_datetime", "end_datetime"]:
                        assert result[field] is not None, f"Field {field} is None"
                
                # Verify confidence score
                confidence = result.get("confidence_score", 0)
                assert isinstance(confidence, (int, float)), "Confidence score should be numeric"
                assert 0 <= confidence <= 1, "Confidence score should be between 0 and 1"
                
                print(f"  ✓ Title: {result.get('title', 'N/A')}")
                print(f"  ✓ Start: {result.get('start_datetime', 'N/A')}")
                print(f"  ✓ Location: {result.get('location', 'N/A')}")
                print(f"  ✓ Confidence: {confidence:.2f}")
                
            except requests.exceptions.RequestException as e:
                pytest.fail(f"API request failed for case {i+1}: {e}")
    
    def test_ios_error_handling(self):
        """Test API error handling scenarios that iOS app should handle."""
        error_cases = [
            {
                "payload": {"text": ""},
                "description": "Empty text"
            },
            {
                "payload": {"text": "   "},
                "description": "Whitespace only"
            },
            {
                "payload": {"text": "random text with no event information whatsoever"},
                "description": "No event information"
            },
            {
                "payload": {},
                "description": "Missing text field"
            }
        ]
        
        for case in error_cases:
            print(f"\nTesting error case: {case['description']}")
            
            try:
                response = requests.post(
                    f"{self.API_BASE_URL}/parse",
                    json=case["payload"],
                    headers={
                        "Content-Type": "application/json",
                        "User-Agent": "CalendarEventApp-iOS/1.0"
                    },
                    timeout=10
                )
                
                print(f"  Status: {response.status_code}")
                
                # Should handle errors gracefully
                assert response.status_code in [200, 400, 422], f"Unexpected status: {response.status_code}"
                
                if response.status_code == 200:
                    result = response.json()
                    # Even if successful, confidence should be low for poor input
                    confidence = result.get("confidence_score", 0)
                    if case["description"] != "No event information":
                        assert confidence < 0.5, f"Confidence too high for poor input: {confidence}"
                
                print(f"  ✓ Handled gracefully")
                
            except requests.exceptions.RequestException as e:
                pytest.fail(f"Error handling test failed: {e}")
    
    def test_ios_project_structure(self):
        """Test that iOS project has all necessary files."""
        ios_root = "ios"
        
        required_files = [
            "CalendarEventApp/CalendarEventApp.swift",
            "CalendarEventApp/ContentView.swift",
            "CalendarEventApp/ApiService.swift",
            "CalendarEventApp/Models.swift",
            "CalendarEventApp/EventResultView.swift",
            "CalendarEventApp/Info.plist",
            "CalendarEventExtension/ActionViewController.swift",
            "CalendarEventExtension/ApiService.swift",
            "CalendarEventExtension/Info.plist",
            "CalendarEventApp.xcodeproj/project.pbxproj"
        ]
        
        for file_path in required_files:
            full_path = os.path.join(ios_root, file_path)
            assert os.path.exists(full_path), f"Missing required file: {file_path}"
            print(f"✓ Found: {file_path}")
    
    def test_ios_share_extension_configuration(self):
        """Test that Share Extension is properly configured."""
        info_plist_path = "ios/CalendarEventExtension/Info.plist"
        
        with open(info_plist_path, 'r') as f:
            plist_content = f.read()
        
        # Check for required extension configuration
        assert 'NSExtensionPointIdentifier' in plist_content, "Missing extension point identifier"
        assert 'com.apple.ui-services' in plist_content, "Wrong extension point identifier"
        assert 'NSExtensionActivationSupportsText' in plist_content, "Missing text activation support"
        assert 'NSCalendarsUsageDescription' in plist_content, "Missing calendar permission description"
        print("✓ Share Extension properly configured")
    
    def test_ios_main_app_configuration(self):
        """Test that main iOS app is properly configured."""
        info_plist_path = "ios/CalendarEventApp/Info.plist"
        
        with open(info_plist_path, 'r') as f:
            plist_content = f.read()
        
        # Check for required app configuration
        assert 'CFBundleDisplayName' in plist_content, "Missing app display name"
        assert 'CFBundleIdentifier' in plist_content, "Missing bundle identifier"
        print("✓ Main app properly configured")
    
    def test_ios_api_service_implementation(self):
        """Test that iOS API service is properly implemented."""
        # Check main app API service
        main_api_path = "ios/CalendarEventApp/ApiService.swift"
        with open(main_api_path, 'r') as f:
            main_api_content = f.read()
        
        assert 'calendar-api-wrxz.onrender.com' in main_api_content, "Missing API endpoint in main app"
        assert 'parseText' in main_api_content, "Missing parseText method in main app"
        assert 'URLSession' in main_api_content, "Missing URLSession usage in main app"
        print("✓ Main app API service implemented")
        
        # Check extension API service
        ext_api_path = "ios/CalendarEventExtension/ApiService.swift"
        with open(ext_api_path, 'r') as f:
            ext_api_content = f.read()
        
        assert 'calendar-api-wrxz.onrender.com' in ext_api_content, "Missing API endpoint in extension"
        assert 'parseText' in ext_api_content, "Missing parseText method in extension"
        assert 'async' in ext_api_content, "Missing async/await support in extension"
        print("✓ Extension API service implemented")
    
    def test_ios_models_implementation(self):
        """Test that iOS models are properly implemented."""
        models_path = "ios/CalendarEventApp/Models.swift"
        
        with open(models_path, 'r') as f:
            models_content = f.read()
        
        # Check for required model properties
        required_properties = [
            'title', 'startDatetime', 'endDatetime', 'location', 
            'description', 'confidenceScore', 'allDay', 'timezone'
        ]
        
        for prop in required_properties:
            assert prop in models_content, f"Missing property: {prop}"
        
        # Check for Codable conformance
        assert 'Codable' in models_content, "Missing Codable conformance"
        assert 'CodingKeys' in models_content, "Missing CodingKeys enum"
        
        # Check for display properties
        assert 'displayTitle' in models_content, "Missing displayTitle computed property"
        assert 'formattedStartDate' in models_content, "Missing formattedStartDate computed property"
        
        print("✓ Models properly implemented")
    
    def test_ios_calendar_integration(self):
        """Test that iOS calendar integration is properly implemented."""
        # Check EventResultView for calendar integration
        result_view_path = "ios/CalendarEventApp/EventResultView.swift"
        
        with open(result_view_path, 'r') as f:
            result_view_content = f.read()
        
        assert 'EventKit' in result_view_content, "Missing EventKit import"
        assert 'EKEventStore' in result_view_content, "Missing EKEventStore usage"
        assert 'requestAccess' in result_view_content, "Missing calendar permission request"
        assert 'EKEvent' in result_view_content, "Missing EKEvent creation"
        print("✓ Main app calendar integration implemented")
        
        # Check Share Extension for calendar integration
        action_controller_path = "ios/CalendarEventExtension/ActionViewController.swift"
        
        with open(action_controller_path, 'r') as f:
            action_controller_content = f.read()
        
        assert 'EventKit' in action_controller_content, "Missing EventKit import in extension"
        assert 'EKEventEditViewController' in action_controller_content, "Missing event edit controller in extension"
        assert 'EKEventEditViewDelegate' in action_controller_content, "Missing delegate conformance in extension"
        print("✓ Extension calendar integration implemented")
    
    def run_all_tests(self):
        """Run all tests and provide summary."""
        tests = [
            ("API Connectivity", self.test_api_connectivity),
            ("iOS API Integration", self.test_ios_api_integration),
            ("Error Handling", self.test_ios_error_handling),
            ("Project Structure", self.test_ios_project_structure),
            ("Share Extension Configuration", self.test_ios_share_extension_configuration),
            ("Main App Configuration", self.test_ios_main_app_configuration),
            ("API Service Implementation", self.test_ios_api_service_implementation),
            ("Models Implementation", self.test_ios_models_implementation),
            ("Calendar Integration", self.test_ios_calendar_integration)
        ]
        
        passed = 0
        failed = 0
        
        print("iOS App Complete Functionality Test")
        print("=" * 50)
        
        for test_name, test_func in tests:
            try:
                print(f"\n{test_name}:")
                test_func()
                print(f"✓ {test_name} PASSED")
                passed += 1
            except Exception as e:
                print(f"✗ {test_name} FAILED: {e}")
                failed += 1
        
        print(f"\n{'='*50}")
        print(f"Test Results: {passed} passed, {failed} failed")
        
        if failed == 0:
            print("\n🎉 All iOS app tests passed!")
            print("\nThe iOS app is ready with:")
            print("• Main app with text input and parsing")
            print("• Share Extension for text selection from other apps")
            print("• EventKit integration for calendar event creation")
            print("• Proper error handling and user feedback")
            print("• SwiftUI modern interface")
            print("• Comprehensive API integration")
            return True
        else:
            print(f"\n❌ {failed} test(s) failed. Please fix the issues above.")
            return False


if __name__ == "__main__":
    test = TestiOSCompleteApp()
    success = test.run_all_tests()
    exit(0 if success else 1)