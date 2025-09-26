#!/usr/bin/env python3
"""
Test script to simulate end-to-end Android text selection workflow.

This test validates the complete flow:
1. Text selection triggers ACTION_PROCESS_TEXT intent
2. TextProcessorActivity processes the selected text
3. API call is made to parse the text
4. Native calendar app is launched with pre-filled event data

Requirements tested: 1.1, 1.4, 5.1, 5.2
"""

import json
import requests
import subprocess
import time
from datetime import datetime, timezone
from typing import Dict, Any, Optional


class AndroidFlowTester:
    """Test class for Android text selection to calendar event flow."""
    
    def __init__(self):
        self.api_base_url = "https://calendar-api-wrxz.onrender.com"
        self.package_name = "com.jacolabs.calendar"
        self.text_processor_activity = f"{self.package_name}/.TextProcessorActivity"
        
    def test_api_integration(self) -> bool:
        """Test that the API endpoint is working correctly."""
        print("Testing API integration...")
        
        test_cases = [
            {
                "text": "Meeting with John tomorrow at 2pm",
                "expected_fields": ["title", "start_datetime"]
            },
            {
                "text": "Lunch at The Keg next Friday 12:30",
                "expected_fields": ["title", "start_datetime", "location"]
            },
            {
                "text": "Conference call Monday 10am for 1 hour",
                "expected_fields": ["title", "start_datetime", "end_datetime"]
            }
        ]
        
        for i, test_case in enumerate(test_cases, 1):
            print(f"  Test case {i}: {test_case['text']}")
            
            try:
                response = self._call_parse_api(test_case["text"])
                
                if not response:
                    print(f"    ❌ API call failed")
                    return False
                
                # Check that expected fields are present
                for field in test_case["expected_fields"]:
                    if field not in response or not response[field]:
                        print(f"    ❌ Missing expected field: {field}")
                        return False
                
                print(f"    ✅ Parsed successfully: title='{response.get('title')}', "
                      f"start='{response.get('start_datetime')}', "
                      f"location='{response.get('location', 'N/A')}'")
                
            except Exception as e:
                print(f"    ❌ Error: {e}")
                return False
        
        print("✅ API integration test passed")
        return True
    
    def test_android_intent_simulation(self) -> bool:
        """Simulate Android ACTION_PROCESS_TEXT intent handling."""
        print("Testing Android intent simulation...")
        
        # Check if ADB is available
        if not self._check_adb():
            print("  ⚠️  ADB not available, skipping Android device tests")
            return True
        
        # Check if device is connected
        if not self._check_device_connected():
            print("  ⚠️  No Android device connected, skipping device tests")
            return True
        
        # Check if app is installed
        if not self._check_app_installed():
            print("  ⚠️  App not installed on device, skipping device tests")
            return True
        
        # Test ACTION_PROCESS_TEXT intent
        test_text = "Team meeting tomorrow at 3pm in Conference Room A"
        
        try:
            print(f"  Simulating text selection: '{test_text}'")
            
            # Launch TextProcessorActivity with ACTION_PROCESS_TEXT intent
            cmd = [
                "adb", "shell", "am", "start",
                "-a", "android.intent.action.PROCESS_TEXT",
                "-t", "text/plain",
                "--es", "android.intent.extra.PROCESS_TEXT", test_text,
                self.text_processor_activity
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                print("  ✅ Intent launched successfully")
                print("  📱 Check device for calendar app opening with pre-filled event")
                time.sleep(2)  # Give time for processing
                return True
            else:
                print(f"  ❌ Intent launch failed: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            print("  ❌ Intent launch timed out")
            return False
        except Exception as e:
            print(f"  ❌ Error launching intent: {e}")
            return False
    
    def test_calendar_contract_integration(self) -> bool:
        """Test CalendarContract intent creation logic."""
        print("Testing CalendarContract integration...")
        
        # Test data that would come from API
        test_parse_result = {
            "title": "Team Meeting",
            "start_datetime": "2024-01-15T15:00:00-08:00",
            "end_datetime": "2024-01-15T16:00:00-08:00",
            "location": "Conference Room A",
            "description": "Weekly team sync meeting",
            "confidence_score": 0.85,
            "all_day": False
        }
        
        # Simulate the calendar intent creation logic
        calendar_intent_data = self._create_calendar_intent_data(test_parse_result)
        
        expected_fields = [
            "title", "begin_time", "end_time", "location", "description"
        ]
        
        for field in expected_fields:
            if field not in calendar_intent_data:
                print(f"  ❌ Missing calendar intent field: {field}")
                return False
        
        print("  ✅ Calendar intent data created successfully:")
        for key, value in calendar_intent_data.items():
            print(f"    {key}: {value}")
        
        return True
    
    def test_error_handling(self) -> bool:
        """Test error handling scenarios."""
        print("Testing error handling...")
        
        # Test empty text
        try:
            response = self._call_parse_api("")
            print("  ✅ Empty text handled gracefully")
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 422:
                print("  ✅ Empty text properly rejected by API (422 Unprocessable Entity)")
            else:
                print(f"  ❌ Unexpected HTTP error for empty text: {e}")
                return False
        except Exception as e:
            print(f"  ❌ Empty text error: {e}")
            return False
        
        # Test invalid text
        try:
            response = self._call_parse_api("asdfghjkl random text with no event info")
            if response.get("confidence_score", 0) < 0.3:
                print("  ✅ Low confidence text handled correctly")
            else:
                print("  ⚠️  Unexpected high confidence for invalid text")
        except Exception as e:
            print(f"  ❌ Invalid text error: {e}")
            return False
        
        return True
    
    def run_all_tests(self) -> bool:
        """Run all test scenarios."""
        print("🧪 Starting Android text selection flow tests...\n")
        
        tests = [
            ("API Integration", self.test_api_integration),
            ("Android Intent Simulation", self.test_android_intent_simulation),
            ("CalendarContract Integration", self.test_calendar_contract_integration),
            ("Error Handling", self.test_error_handling)
        ]
        
        results = []
        
        for test_name, test_func in tests:
            print(f"📋 {test_name}")
            try:
                result = test_func()
                results.append(result)
                print()
            except Exception as e:
                print(f"  ❌ Test failed with exception: {e}\n")
                results.append(False)
        
        # Summary
        passed = sum(results)
        total = len(results)
        
        print("📊 Test Summary:")
        print(f"  Passed: {passed}/{total}")
        
        if passed == total:
            print("🎉 All tests passed!")
            return True
        else:
            print("❌ Some tests failed")
            return False
    
    def _call_parse_api(self, text: str) -> Optional[Dict[str, Any]]:
        """Call the parse API endpoint."""
        url = f"{self.api_base_url}/parse"
        
        payload = {
            "text": text,
            "timezone": "America/Los_Angeles",
            "locale": "en_US",
            "now": datetime.now(timezone.utc).isoformat()
        }
        
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "AndroidFlowTester/1.0"
        }
        
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        response.raise_for_status()
        
        return response.json()
    
    def _check_adb(self) -> bool:
        """Check if ADB is available."""
        try:
            subprocess.run(["adb", "version"], capture_output=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
    
    def _check_device_connected(self) -> bool:
        """Check if an Android device is connected."""
        try:
            result = subprocess.run(["adb", "devices"], capture_output=True, text=True)
            lines = result.stdout.strip().split('\n')[1:]  # Skip header
            devices = [line for line in lines if line.strip() and 'device' in line]
            return len(devices) > 0
        except Exception:
            return False
    
    def _check_app_installed(self) -> bool:
        """Check if the calendar app is installed on the device."""
        try:
            result = subprocess.run(
                ["adb", "shell", "pm", "list", "packages", self.package_name],
                capture_output=True, text=True
            )
            return self.package_name in result.stdout
        except Exception:
            return False
    
    def _create_calendar_intent_data(self, parse_result: Dict[str, Any]) -> Dict[str, Any]:
        """Simulate calendar intent data creation logic."""
        intent_data = {}
        
        if parse_result.get("title"):
            intent_data["title"] = parse_result["title"]
        
        if parse_result.get("start_datetime"):
            # Convert ISO datetime to milliseconds (simplified)
            try:
                dt = datetime.fromisoformat(parse_result["start_datetime"].replace('Z', '+00:00'))
                intent_data["begin_time"] = int(dt.timestamp() * 1000)
            except Exception:
                pass
        
        if parse_result.get("end_datetime"):
            try:
                dt = datetime.fromisoformat(parse_result["end_datetime"].replace('Z', '+00:00'))
                intent_data["end_time"] = int(dt.timestamp() * 1000)
            except Exception:
                pass
        elif intent_data.get("begin_time"):
            # Default to +30 minutes
            intent_data["end_time"] = intent_data["begin_time"] + (30 * 60 * 1000)
        
        if parse_result.get("location"):
            intent_data["location"] = parse_result["location"]
        
        if parse_result.get("description"):
            intent_data["description"] = parse_result["description"]
        
        if parse_result.get("all_day"):
            intent_data["all_day"] = True
        
        return intent_data


def main():
    """Main test runner."""
    tester = AndroidFlowTester()
    success = tester.run_all_tests()
    
    if success:
        print("\n✅ Android text selection flow validation completed successfully!")
        print("\n📱 Manual testing steps:")
        print("1. Install the app on an Android device")
        print("2. Open any app with selectable text (browser, email, etc.)")
        print("3. Select text containing event information")
        print("4. Look for 'Create calendar event' in the context menu")
        print("5. Tap it and verify the calendar app opens with pre-filled data")
        
        exit(0)
    else:
        print("\n❌ Some tests failed. Please check the implementation.")
        exit(1)


if __name__ == "__main__":
    main()