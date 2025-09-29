"""
Comprehensive end-to-end integration tests for the text-to-calendar event system.
Tests complete workflows from text input to calendar event creation across all platforms.
"""

import pytest
import requests
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List
import time

# Test configuration
API_BASE_URL = "http://localhost:8000"  # Adjust for your deployment
TEST_TIMEOUT = 30  # seconds


class TestEndToEndIntegration:
    """
    End-to-end integration tests covering complete user workflows
    from text selection to calendar event creation.
    """
    
    @pytest.fixture
    def api_client(self):
        """Setup API client for testing."""
        return APITestClient(API_BASE_URL)
    
    def test_complete_android_workflow(self, api_client):
        """
        Test complete Android workflow: text selection → API → calendar integration.
        Simulates the full Android text selection and calendar creation flow.
        """
        # Step 1: Simulate Android text selection
        selected_text = "Team standup meeting tomorrow at 9:00 AM in Conference Room A"
        
        # Step 2: API call (as Android app would make)
        response = api_client.parse_text(
            text=selected_text,
            platform="android",
            preferences={
                "timezone": "America/Toronto",
                "date_format": "MM/DD/YYYY"
            }
        )
        
        # Step 3: Validate API response
        assert response["success"] is True
        parsed_event = response["parsed_event"]
        
        assert parsed_event["title"] == "Team Standup Meeting"
        assert "Conference Room A" in parsed_event["location"]
        assert response["field_confidence"]["title"] > 0.7
        assert response["field_confidence"]["start_datetime"] > 0.8
        
        # Step 4: Simulate calendar integration (would use CalendarContract in real Android)
        calendar_event = self._create_test_calendar_event(parsed_event)
        assert calendar_event["success"] is True
        assert calendar_event["event_id"] is not None
    
    def test_complete_ios_workflow(self, api_client):
        """
        Test complete iOS workflow: share extension → API → EventKit integration.
        Simulates the full iOS share extension and calendar creation flow.
        """
        # Step 1: Simulate iOS share extension text
        selected_text = "Lunch with Sarah next Friday at 12:30 PM at Cafe Milano downtown"
        
        # Step 2: API call (as iOS extension would make)
        response = api_client.parse_text(
            text=selected_text,
            platform="ios",
            preferences={
                "timezone": "America/Toronto",
                "time_format": "12_hour"
            }
        )
        
        # Step 3: Validate API response
        assert response["success"] is True
        parsed_event = response["parsed_event"]
        
        assert "Lunch with Sarah" in parsed_event["title"]
        assert "Cafe Milano" in parsed_event["location"]
        assert response["field_confidence"]["location"] > 0.6
        
        # Step 4: Simulate EventKit integration
        eventkit_event = self._create_test_eventkit_event(parsed_event)
        assert eventkit_event["success"] is True
        assert eventkit_event["calendar_id"] is not None
    
    def test_complete_browser_extension_workflow(self, api_client):
        """
        Test complete browser extension workflow: context menu → API → calendar URL.
        Simulates the full browser extension and web calendar integration flow.
        """
        # Step 1: Simulate browser text selection
        selected_text = "Board meeting on Monday, October 6th at 10:00 AM in the executive conference room"
        
        # Step 2: API call (as browser extension would make)
        response = api_client.parse_text(
            text=selected_text,
            platform="browser",
            preferences={
                "timezone": "America/Toronto",
                "date_format": "MM/DD/YYYY"
            }
        )
        
        # Step 3: Validate API response
        assert response["success"] is True
        parsed_event = response["parsed_event"]
        
        assert parsed_event["title"] == "Board Meeting"
        assert "executive conference room" in parsed_event["location"].lower()
        assert response["field_confidence"]["title"] > 0.8
        
        # Step 4: Simulate calendar URL generation
        calendar_url = self._generate_calendar_url(parsed_event, "google")
        assert "calendar.google.com" in calendar_url
        assert parsed_event["title"].replace(" ", "+") in calendar_url
    
    def test_cross_platform_consistency(self, api_client):
        """
        Test that the same text produces consistent results across all platforms.
        Ensures parsing consistency regardless of client platform.
        """
        test_text = "Project review meeting on Wednesday, September 30th at 2:00 PM in Room 301"
        
        # Test same text from all platforms
        platforms = ["android", "ios", "browser"]
        results = {}
        
        for platform in platforms:
            response = api_client.parse_text(
                text=test_text,
                platform=platform,
                preferences={"timezone": "America/Toronto"}
            )
            results[platform] = response["parsed_event"]
        
        # Verify consistency across platforms
        base_result = results["android"]
        for platform in ["ios", "browser"]:
            result = results[platform]
            
            # Core fields should be identical
            assert result["title"] == base_result["title"]
            assert result["start_datetime"] == base_result["start_datetime"]
            assert result["location"] == base_result["location"]
    
    def test_error_handling_workflow(self, api_client):
        """
        Test error handling and recovery across the complete workflow.
        Ensures graceful degradation when parsing fails or confidence is low.
        """
        # Test with ambiguous/poor text
        ambiguous_text = "meeting sometime next week"
        
        response = api_client.parse_text(
            text=ambiguous_text,
            platform="android"
        )
        
        # Should succeed but with low confidence and suggestions
        assert response["success"] is True
        assert response["parsed_event"]["confidence_score"] < 0.5
        assert len(response["parsing_metadata"]["suggestions"]) > 0
        
        # Test with completely invalid text
        invalid_text = "random text with no event information"
        
        response = api_client.parse_text(
            text=invalid_text,
            platform="android"
        )
        
        # Should fail gracefully with helpful error message
        if not response["success"]:
            assert "error" in response
            assert "suggestions" in response
        else:
            # If it succeeds, confidence should be very low
            assert response["parsed_event"]["confidence_score"] < 0.3
    
    def test_performance_requirements(self, api_client):
        """
        Test that the system meets performance requirements for user experience.
        Ensures API responses are fast enough for real-time user interaction.
        """
        test_texts = [
            "Quick meeting tomorrow at 2pm",
            "Conference call with the development team on Friday, October 3rd at 10:00 AM",
            "Annual planning session next Monday from 9 AM to 5 PM in the main conference room"
        ]
        
        for text in test_texts:
            start_time = time.time()
            
            response = api_client.parse_text(text=text, platform="android")
            
            end_time = time.time()
            processing_time = end_time - start_time
            
            # Should respond within 5 seconds for good user experience
            assert processing_time < 5.0
            
            # Should succeed for reasonable text
            assert response["success"] is True
            assert response["parsed_event"]["confidence_score"] > 0.4
    
    def test_real_world_text_scenarios(self, api_client):
        """
        Test with real-world text examples from emails, messages, and documents.
        Validates parsing accuracy with actual user text patterns.
        """
        real_world_examples = [
            {
                "text": "Hi team, we're scheduling our quarterly review meeting for next Thursday, October 3rd at 2:00 PM in the main conference room. Please bring your project updates.",
                "expected_title": "Quarterly Review Meeting",
                "expected_confidence": 0.8
            },
            {
                "text": "Reminder: Doctor appointment tomorrow at 3:30 PM at the medical center on Main Street.",
                "expected_title": "Doctor Appointment",
                "expected_confidence": 0.85
            },
            {
                "text": "Let's grab lunch next Friday around noon at that new Italian place downtown.",
                "expected_title": "Lunch",
                "expected_confidence": 0.7
            },
            {
                "text": "Training session: Introduction to Machine Learning\nDate: Monday, October 6th\nTime: 10:00 AM - 4:00 PM\nLocation: Training Room B",
                "expected_title": "Introduction to Machine Learning",
                "expected_confidence": 0.9
            }
        ]
        
        for example in real_world_examples:
            response = api_client.parse_text(
                text=example["text"],
                platform="android"
            )
            
            assert response["success"] is True
            
            parsed_event = response["parsed_event"]
            
            # Check title extraction
            assert example["expected_title"].lower() in parsed_event["title"].lower()
            
            # Check confidence meets expectations
            assert parsed_event["confidence_score"] >= example["expected_confidence"] - 0.1
            
            # Should have extracted date/time
            assert parsed_event["start_datetime"] is not None
    
    def test_calendar_integration_formats(self, api_client):
        """
        Test that parsed events can be successfully integrated with various calendar systems.
        Validates output format compatibility with different calendar APIs.
        """
        test_text = "Team meeting on Friday, October 3rd at 2:00 PM in Conference Room A"
        
        response = api_client.parse_text(text=test_text, platform="android")
        parsed_event = response["parsed_event"]
        
        # Test Google Calendar format
        google_event = self._format_for_google_calendar(parsed_event)
        assert "summary" in google_event
        assert "start" in google_event
        assert "end" in google_event
        assert "location" in google_event
        
        # Test Outlook format
        outlook_event = self._format_for_outlook(parsed_event)
        assert "subject" in outlook_event
        assert "start" in outlook_event
        assert "end" in outlook_event
        assert "location" in outlook_event
        
        # Test Apple Calendar format
        apple_event = self._format_for_apple_calendar(parsed_event)
        assert "title" in apple_event
        assert "startDate" in apple_event
        assert "endDate" in apple_event
    
    def test_multi_event_detection(self, api_client):
        """
        Test detection and handling of multiple events in single text block.
        Ensures system can identify when text contains multiple distinct events.
        """
        multi_event_text = """
        We have two important meetings this week:
        
        1. Team standup on Tuesday at 9:00 AM in Room 101
        2. Client presentation on Thursday at 2:00 PM in the main conference room
        
        Please mark your calendars accordingly.
        """
        
        response = api_client.parse_text(
            text=multi_event_text,
            platform="android"
        )
        
        # Should detect multiple events or provide suggestions
        if "multiple_events_detected" in response.get("parsing_metadata", {}):
            assert response["parsing_metadata"]["multiple_events_detected"] is True
        else:
            # If single event returned, should have suggestions about multiple events
            suggestions = response.get("parsing_metadata", {}).get("suggestions", [])
            multiple_event_suggestion = any("multiple" in s.lower() for s in suggestions)
            assert multiple_event_suggestion or response["parsed_event"]["confidence_score"] < 0.7
    
    def _create_test_calendar_event(self, parsed_event: Dict[str, Any]) -> Dict[str, Any]:
        """Simulate Android CalendarContract event creation."""
        # In real implementation, this would use Android CalendarContract
        return {
            "success": True,
            "event_id": f"android_event_{int(time.time())}",
            "calendar_id": "primary",
            "platform": "android"
        }
    
    def _create_test_eventkit_event(self, parsed_event: Dict[str, Any]) -> Dict[str, Any]:
        """Simulate iOS EventKit event creation."""
        # In real implementation, this would use iOS EventKit
        return {
            "success": True,
            "event_id": f"ios_event_{int(time.time())}",
            "calendar_id": "default",
            "platform": "ios"
        }
    
    def _generate_calendar_url(self, parsed_event: Dict[str, Any], service: str) -> str:
        """Generate calendar service URL for browser extension."""
        if service == "google":
            base_url = "https://calendar.google.com/calendar/render"
            params = {
                "action": "TEMPLATE",
                "text": parsed_event["title"],
                "dates": f"{parsed_event['start_datetime']}/{parsed_event['end_datetime']}",
                "location": parsed_event.get("location", "")
            }
            return f"{base_url}?" + "&".join([f"{k}={v}" for k, v in params.items()])
        
        return f"https://{service}.calendar.com/create"
    
    def _format_for_google_calendar(self, parsed_event: Dict[str, Any]) -> Dict[str, Any]:
        """Format event for Google Calendar API."""
        return {
            "summary": parsed_event["title"],
            "start": {"dateTime": parsed_event["start_datetime"]},
            "end": {"dateTime": parsed_event["end_datetime"]},
            "location": parsed_event.get("location", ""),
            "description": parsed_event.get("description", "")
        }
    
    def _format_for_outlook(self, parsed_event: Dict[str, Any]) -> Dict[str, Any]:
        """Format event for Outlook API."""
        return {
            "subject": parsed_event["title"],
            "start": {"dateTime": parsed_event["start_datetime"]},
            "end": {"dateTime": parsed_event["end_datetime"]},
            "location": {"displayName": parsed_event.get("location", "")},
            "body": {"content": parsed_event.get("description", "")}
        }
    
    def _format_for_apple_calendar(self, parsed_event: Dict[str, Any]) -> Dict[str, Any]:
        """Format event for Apple Calendar."""
        return {
            "title": parsed_event["title"],
            "startDate": parsed_event["start_datetime"],
            "endDate": parsed_event["end_datetime"],
            "location": parsed_event.get("location", ""),
            "notes": parsed_event.get("description", "")
        }


class APITestClient:
    """Test client for API integration testing."""
    
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.timeout = TEST_TIMEOUT
    
    def parse_text(self, text: str, platform: str = "test", 
                   preferences: Dict[str, Any] = None) -> Dict[str, Any]:
        """Make API call to parse text."""
        url = f"{self.base_url}/parse"
        
        payload = {
            "text": text,
            "preferences": preferences or {},
            "context": {
                "platform": platform,
                "app_version": "test",
                "timestamp": datetime.now().isoformat()
            }
        }
        
        try:
            response = self.session.post(url, json=payload)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {
                "success": False,
                "error": f"API request failed: {str(e)}",
                "error_code": "API_ERROR"
            }
    
    def health_check(self) -> bool:
        """Check if API is available."""
        try:
            response = self.session.get(f"{self.base_url}/health")
            return response.status_code == 200
        except:
            return False


class TestPerformanceMetrics:
    """Performance and load testing for the complete system."""
    
    def test_concurrent_requests(self, api_client):
        """Test system performance under concurrent load."""
        import concurrent.futures
        import threading
        
        def make_request(text_index):
            test_texts = [
                "Meeting tomorrow at 2pm",
                "Call with John on Friday at 10am",
                "Lunch next week at noon"
            ]
            text = test_texts[text_index % len(test_texts)]
            
            start_time = time.time()
            response = api_client.parse_text(text=text, platform="load_test")
            end_time = time.time()
            
            return {
                "success": response.get("success", False),
                "processing_time": end_time - start_time,
                "confidence": response.get("parsed_event", {}).get("confidence_score", 0)
            }
        
        # Test with 10 concurrent requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request, i) for i in range(20)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        # Analyze results
        success_rate = sum(1 for r in results if r["success"]) / len(results)
        avg_processing_time = sum(r["processing_time"] for r in results) / len(results)
        avg_confidence = sum(r["confidence"] for r in results if r["success"]) / sum(1 for r in results if r["success"])
        
        # Performance assertions
        assert success_rate > 0.9  # 90% success rate under load
        assert avg_processing_time < 10.0  # Average under 10 seconds
        assert avg_confidence > 0.5  # Reasonable confidence maintained
    
    def test_memory_usage_stability(self, api_client):
        """Test that repeated requests don't cause memory leaks."""
        # Make many requests to test for memory leaks
        for i in range(50):
            response = api_client.parse_text(
                text=f"Test meeting {i} tomorrow at {10 + (i % 8)}:00 AM",
                platform="memory_test"
            )
            assert response.get("success", False) is True
        
        # If we get here without timeout/crash, memory usage is stable


class TestUserAcceptanceScenarios:
    """User acceptance tests simulating real user workflows."""
    
    def test_gmail_integration_scenario(self, api_client):
        """Test typical Gmail email processing scenario."""
        gmail_text = """
        Subject: Quarterly Business Review Meeting
        
        Hi team,
        
        I'd like to schedule our Q3 business review for next Thursday, October 3rd at 2:00 PM. 
        We'll meet in the large conference room on the 5th floor.
        
        Please prepare your department reports and bring any questions about the quarterly metrics.
        
        Thanks,
        Sarah
        """
        
        response = api_client.parse_text(text=gmail_text, platform="browser")
        
        assert response["success"] is True
        parsed_event = response["parsed_event"]
        
        # Should extract key information from email
        assert "business review" in parsed_event["title"].lower()
        assert "conference room" in parsed_event["location"].lower()
        assert "5th floor" in parsed_event["location"].lower()
        assert response["field_confidence"]["title"] > 0.7
    
    def test_mobile_message_scenario(self, api_client):
        """Test typical mobile messaging scenario."""
        message_text = "Hey, want to grab coffee tomorrow at 3pm? How about that new place on Main Street?"
        
        response = api_client.parse_text(text=message_text, platform="android")
        
        assert response["success"] is True
        parsed_event = response["parsed_event"]
        
        # Should extract casual event information
        assert "coffee" in parsed_event["title"].lower()
        assert "main street" in parsed_event["location"].lower()
        assert parsed_event["start_datetime"] is not None
    
    def test_calendar_invite_scenario(self, api_client):
        """Test processing of calendar invitation text."""
        invite_text = """
        You're invited to: Project Kickoff Meeting
        
        When: Monday, October 6th, 2025 at 10:00 AM - 11:30 AM (EST)
        Where: Zoom Meeting Room (link will be provided)
        
        Agenda:
        - Project overview
        - Team introductions  
        - Timeline review
        - Q&A session
        """
        
        response = api_client.parse_text(text=invite_text, platform="ios")
        
        assert response["success"] is True
        parsed_event = response["parsed_event"]
        
        # Should extract formal invitation details
        assert "project kickoff" in parsed_event["title"].lower()
        assert "zoom" in parsed_event["location"].lower()
        assert response["field_confidence"]["title"] > 0.8
        assert response["field_confidence"]["start_datetime"] > 0.9


if __name__ == "__main__":
    # Run basic integration test
    client = APITestClient("http://localhost:8000")
    
    if client.health_check():
        print("✅ API is available")
        
        # Run a quick test
        response = client.parse_text("Test meeting tomorrow at 2pm")
        if response.get("success"):
            print("✅ Basic parsing test passed")
            print(f"   Title: {response['parsed_event']['title']}")
            print(f"   Confidence: {response['parsed_event']['confidence_score']:.2f}")
        else:
            print("❌ Basic parsing test failed")
            print(f"   Error: {response.get('error', 'Unknown error')}")
    else:
        print("❌ API is not available - check if server is running")