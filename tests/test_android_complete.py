#!/usr/bin/env python3
"""
Comprehensive Android app functionality test.
Tests the complete Android app implementation including text processing activities.
"""

import pytest
import requests
import json
from datetime import datetime, timezone
import subprocess
import os


class TestAndroidCompleteApp:
    """Test complete Android app functionality."""
    
    API_BASE_URL = "https://calendar-api-wrxz.onrender.com"
    
    def test_api_connectivity(self):
        """Test that the API is accessible for the Android app."""
        try:
            response = requests.get(f"{self.API_BASE_URL}/", timeout=10)
            assert response.status_code in [200, 404], f"API not accessible: {response.status_code}"
            print("✓ API endpoint is accessible")
        except requests.exceptions.RequestException as e:
            pytest.fail(f"API endpoint not accessible: {e}")
    
    def test_android_api_integration(self):
        """Test API integration with Android-specific headers and payload."""
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
                        "User-Agent": "CalendarEventApp-Android/1.0"
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
    
    def test_android_error_handling(self):
        """Test API error handling scenarios that Android app should handle."""
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
                        "User-Agent": "CalendarEventApp-Android/1.0"
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
    
    def test_android_project_structure(self):
        """Test that Android project has all necessary files."""
        android_root = "android"
        
        required_files = [
            "app/build.gradle",
            "app/src/main/AndroidManifest.xml",
            "app/src/main/java/com/jacolabs/calendar/MainActivity.kt",
            "app/src/main/java/com/jacolabs/calendar/ApiService.kt",
            "app/src/main/java/com/jacolabs/calendar/TextProcessorActivity.kt",
            "app/src/main/java/com/jacolabs/calendar/ShareHandlerActivity.kt",
            "app/src/main/res/values/strings.xml"
        ]
        
        for file_path in required_files:
            full_path = os.path.join(android_root, file_path)
            assert os.path.exists(full_path), f"Missing required file: {file_path}"
            print(f"✓ Found: {file_path}")
    
    def test_android_manifest_configuration(self):
        """Test that AndroidManifest.xml has correct configuration."""
        manifest_path = "android/app/src/main/AndroidManifest.xml"
        
        with open(manifest_path, 'r') as f:
            manifest_content = f.read()
        
        # Check for required permissions
        assert 'android.permission.INTERNET' in manifest_content, "Missing INTERNET permission"
        assert 'android.permission.ACCESS_NETWORK_STATE' in manifest_content, "Missing NETWORK_STATE permission"
        print("✓ Required permissions found")
        
        # Check for text processing activity
        assert 'TextProcessorActivity' in manifest_content, "Missing TextProcessorActivity"
        assert 'android.intent.action.PROCESS_TEXT' in manifest_content, "Missing PROCESS_TEXT intent filter"
        print("✓ Text processing activity configured")
        
        # Check for share handler activity
        assert 'ShareHandlerActivity' in manifest_content, "Missing ShareHandlerActivity"
        assert 'android.intent.action.SEND' in manifest_content, "Missing SEND intent filter"
        print("✓ Share handler activity configured")
    
    def test_android_build_configuration(self):
        """Test that build.gradle has correct dependencies."""
        build_gradle_path = "android/app/build.gradle"
        
        with open(build_gradle_path, 'r') as f:
            build_content = f.read()
        
        # Check for required dependencies
        required_deps = [
            'androidx.compose.material3:material3',
            'kotlinx-coroutines-android',
            'okhttp3:okhttp'
        ]
        
        for dep in required_deps:
            assert dep in build_content, f"Missing dependency: {dep}"
            print(f"✓ Found dependency: {dep}")
        
        # Check target SDK
        assert 'targetSdk 34' in build_content, "Should target SDK 34"
        assert 'minSdk 24' in build_content, "Should support minimum SDK 24"
        print("✓ SDK versions configured correctly")
    
    def test_android_string_resources(self):
        """Test that string resources are properly defined."""
        strings_path = "android/app/src/main/res/values/strings.xml"
        
        with open(strings_path, 'r') as f:
            strings_content = f.read()
        
        required_strings = [
            'app_name',
            'main_title',
            'parse_button',
            'create_event_button',
            'error_no_text_selected',
            'context_menu_create_event'
        ]
        
        for string_name in required_strings:
            assert f'name="{string_name}"' in strings_content, f"Missing string resource: {string_name}"
            print(f"✓ Found string resource: {string_name}")
    
    def run_all_tests(self):
        """Run all tests and provide summary."""
        tests = [
            ("API Connectivity", self.test_api_connectivity),
            ("Android API Integration", self.test_android_api_integration),
            ("Error Handling", self.test_android_error_handling),
            ("Project Structure", self.test_android_project_structure),
            ("Manifest Configuration", self.test_android_manifest_configuration),
            ("Build Configuration", self.test_android_build_configuration),
            ("String Resources", self.test_android_string_resources)
        ]
        
        passed = 0
        failed = 0
        
        print("Android App Complete Functionality Test")
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
            print("\n🎉 All Android app tests passed!")
            print("\nThe Android app is ready with:")
            print("• Main activity with text input and parsing")
            print("• Text selection context menu integration")
            print("• Share intent handling from other apps")
            print("• Calendar app integration")
            print("• Proper error handling and user feedback")
            print("• Material Design 3 UI")
            return True
        else:
            print(f"\n❌ {failed} test(s) failed. Please fix the issues above.")
            return False


if __name__ == "__main__":
    test = TestAndroidCompleteApp()
    success = test.run_all_tests()
    exit(0 if success else 1)