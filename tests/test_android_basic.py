"""
Test Android basic functionality - API integration verification.

This test verifies that the Android app can successfully integrate with the 
text-to-calendar API at https://calendar-api-wrxz.onrender.com.

Requirements tested:
- 1.1: Text input interface functionality
- 1.2: API integration for parsing text
- 1.3: Display of parsed event results
"""

import pytest
import requests
import json
from datetime import datetime, timezone


class TestAndroidBasicIntegration:
    """Test basic Android app API integration."""
    
    API_BASE_URL = "https://calendar-api-wrxz.onrender.com"
    
    def test_api_endpoint_available(self):
        """Test that the API endpoint is accessible."""
        try:
            # Test the root endpoint instead of /health
            response = requests.get(f"{self.API_BASE_URL}/", timeout=10)
            assert response.status_code in [200, 404], f"API not accessible: {response.status_code}"
        except requests.exceptions.RequestException as e:
            pytest.fail(f"API endpoint not accessible: {e}")
    
    def test_parse_endpoint_basic_functionality(self):
        """Test the /parse endpoint with basic text input."""
        test_text = "Meeting with John tomorrow at 2pm"
        
        payload = {
            "text": test_text,
            "timezone": "America/New_York",
            "locale": "en_US",
            "now": datetime.now(timezone.utc).isoformat()
        }
        
        try:
            response = requests.post(
                f"{self.API_BASE_URL}/parse",
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=15
            )
            
            assert response.status_code == 200, f"Parse request failed: {response.status_code} - {response.text}"
            
            result = response.json()
            
            # Verify response structure matches Android ParseResult data class
            assert "title" in result, "Response missing 'title' field"
            assert "start_datetime" in result, "Response missing 'start_datetime' field"
            assert "confidence_score" in result, "Response missing 'confidence_score' field"
            
            # Verify confidence score is a valid number
            confidence = result.get("confidence_score", 0)
            assert isinstance(confidence, (int, float)), "Confidence score should be numeric"
            assert 0 <= confidence <= 1, "Confidence score should be between 0 and 1"
            
        except requests.exceptions.RequestException as e:
            pytest.fail(f"API request failed: {e}")
    
    def test_parse_endpoint_with_location(self):
        """Test parsing text with location information."""
        test_text = "Lunch at The Keg next Friday 12:30"
        
        payload = {
            "text": test_text,
            "timezone": "America/New_York", 
            "locale": "en_US",
            "now": datetime.now(timezone.utc).isoformat()
        }
        
        try:
            response = requests.post(
                f"{self.API_BASE_URL}/parse",
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=15
            )
            
            assert response.status_code == 200, f"Parse request failed: {response.status_code}"
            
            result = response.json()
            
            # Should extract location information
            assert result.get("location") is not None, "Should extract location from text"
            
        except requests.exceptions.RequestException as e:
            pytest.fail(f"API request failed: {e}")
    
    def test_parse_endpoint_error_handling(self):
        """Test API error handling with invalid input."""
        # Test with empty text
        payload = {
            "text": "",
            "timezone": "America/New_York",
            "locale": "en_US", 
            "now": datetime.now(timezone.utc).isoformat()
        }
        
        try:
            response = requests.post(
                f"{self.API_BASE_URL}/parse",
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=15
            )
            
            # Should handle empty text gracefully (422 is validation error, which is expected)
            assert response.status_code in [200, 400, 422], f"Unexpected status code: {response.status_code}"
            
        except requests.exceptions.RequestException as e:
            pytest.fail(f"API request failed: {e}")
    
    def test_cors_headers_for_android(self):
        """Test that CORS headers allow Android app requests."""
        try:
            # Simulate preflight request
            response = requests.options(
                f"{self.API_BASE_URL}/parse",
                headers={
                    "Origin": "http://localhost",
                    "Access-Control-Request-Method": "POST",
                    "Access-Control-Request-Headers": "Content-Type"
                },
                timeout=10
            )
            
            # Should allow cross-origin requests
            assert response.status_code in [200, 204], f"CORS preflight failed: {response.status_code}"
            
        except requests.exceptions.RequestException as e:
            pytest.fail(f"CORS test failed: {e}")
    
    def test_android_user_agent_accepted(self):
        """Test that Android user agent is accepted."""
        test_text = "Meeting tomorrow at 3pm"
        
        payload = {
            "text": test_text,
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
            
            assert response.status_code == 200, f"Android user agent rejected: {response.status_code}"
            
        except requests.exceptions.RequestException as e:
            pytest.fail(f"Android user agent test failed: {e}")


if __name__ == "__main__":
    # Run basic connectivity test
    test = TestAndroidBasicIntegration()
    
    print("Testing Android API integration...")
    
    try:
        test.test_api_endpoint_available()
        print("✓ API endpoint is accessible")
        
        test.test_parse_endpoint_basic_functionality()
        print("✓ Basic parsing functionality works")
        
        test.test_parse_endpoint_with_location()
        print("✓ Location parsing works")
        
        test.test_android_user_agent_accepted()
        print("✓ Android user agent accepted")
        
        print("\nAll Android basic integration tests passed!")
        
    except Exception as e:
        print(f"✗ Test failed: {e}")