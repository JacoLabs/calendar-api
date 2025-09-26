"""
Contract tests for the FastAPI backend.
Tests with fixed datetime and timezone to ensure consistent behavior.
"""

import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient
import pytz

from app.main import app

client = TestClient(app)

# Fixed test datetime: March 15, 2024, 10:00 AM EST
FIXED_NOW = datetime(2024, 3, 15, 15, 0, 0, tzinfo=timezone.utc)  # 10 AM EST = 3 PM UTC
EST_TZ = "America/New_York"
UTC_TZ = "UTC"


class TestHealthEndpoint:
    """Test health check endpoint."""
    
    def test_health_check(self):
        """Test health endpoint returns correct status."""
        response = client.get("/healthz")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert data["version"] == "1.0.0"


class TestParseEndpoint:
    """Test text parsing endpoint with contract validation."""
    
    def test_parse_simple_meeting(self):
        """Test parsing a simple meeting with fixed datetime."""
        request_data = {
            "text": "Meeting with John tomorrow at 2pm",
            "timezone": EST_TZ,
            "locale": "en_US",
            "now": FIXED_NOW.isoformat()
        }
        
        response = client.post("/parse", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        
        # Contract validation
        assert "title" in data
        assert "start_datetime" in data
        assert "end_datetime" in data
        assert "location" in data
        assert "description" in data
        assert "confidence_score" in data
        assert "all_day" in data
        assert "timezone" in data
        
        # Content validation
        assert data["title"] is not None
        assert "john" in data["title"].lower() or "meeting" in data["title"].lower()
        assert data["start_datetime"] is not None
        assert data["end_datetime"] is not None
        assert data["confidence_score"] > 0.0
        assert data["timezone"] == EST_TZ
        
        # Datetime format validation (ISO 8601 with timezone)
        start_dt = data["start_datetime"]
        assert "T" in start_dt  # ISO 8601 format
        assert ("+" in start_dt or "-" in start_dt or start_dt.endswith("Z"))  # Timezone offset
    
    def test_parse_with_location(self):
        """Test parsing text with location information."""
        request_data = {
            "text": "Team meeting tomorrow at 3pm in Conference Room A",
            "timezone": EST_TZ,
            "locale": "en_US", 
            "now": FIXED_NOW.isoformat()
        }
        
        response = client.post("/parse", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["location"] is not None
        assert "conference room a" in data["location"].lower()
        assert data["confidence_score"] > 0.5
    
    def test_parse_with_duration(self):
        """Test parsing text with duration information."""
        request_data = {
            "text": "Project review meeting tomorrow at 10am for 2 hours",
            "timezone": EST_TZ,
            "locale": "en_US",
            "now": FIXED_NOW.isoformat()
        }
        
        response = client.post("/parse", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        
        # Should have both start and end times
        assert data["start_datetime"] is not None
        assert data["end_datetime"] is not None
        
        # Parse the datetimes to verify duration
        from datetime import datetime as dt
        start = dt.fromisoformat(data["start_datetime"].replace('Z', '+00:00'))
        end = dt.fromisoformat(data["end_datetime"].replace('Z', '+00:00'))
        duration = end - start
        
        # Should be approximately 2 hours (allow some tolerance)
        assert 1.5 <= duration.total_seconds() / 3600 <= 2.5
    
    def test_parse_dd_mm_format(self):
        """Test parsing with DD/MM date format preference."""
        request_data = {
            "text": "Meeting on 15/03/2024 at 2pm",  # March 15th in DD/MM format
            "timezone": UTC_TZ,
            "locale": "en_GB",  # British locale prefers DD/MM
            "now": FIXED_NOW.isoformat()
        }
        
        response = client.post("/parse", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["start_datetime"] is not None
        # Should parse as March 15th, not May 3rd
        start_dt = data["start_datetime"]
        assert "2024-03-15" in start_dt
    
    def test_parse_timezone_handling(self):
        """Test timezone handling in responses."""
        request_data = {
            "text": "Meeting tomorrow at 2pm",
            "timezone": "America/Los_Angeles",  # PST/PDT
            "locale": "en_US",
            "now": FIXED_NOW.isoformat()
        }
        
        response = client.post("/parse", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["timezone"] == "America/Los_Angeles"
        assert data["start_datetime"] is not None
        
        # Should include timezone offset
        start_dt = data["start_datetime"]
        assert ("+" in start_dt or "-" in start_dt or start_dt.endswith("Z"))
    
    def test_parse_low_confidence_text(self):
        """Test parsing text with low confidence."""
        request_data = {
            "text": "maybe meet sometime next week",
            "timezone": EST_TZ,
            "locale": "en_US",
            "now": FIXED_NOW.isoformat()
        }
        
        response = client.post("/parse", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        
        # Should return response but with low confidence
        assert data["confidence_score"] < 0.7
        assert data["description"] == "maybe meet sometime next week"
    
    def test_parse_no_event_information(self):
        """Test parsing text with no event information."""
        request_data = {
            "text": "This is just regular text with no event information",
            "timezone": EST_TZ,
            "locale": "en_US",
            "now": FIXED_NOW.isoformat()
        }
        
        response = client.post("/parse", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        
        # Should return response but with very low confidence
        assert data["confidence_score"] < 0.3
        assert data["start_datetime"] is None or data["confidence_score"] < 0.1
    
    def test_parse_all_day_event(self):
        """Test parsing all-day event."""
        request_data = {
            "text": "Conference all day tomorrow",
            "timezone": EST_TZ,
            "locale": "en_US",
            "now": FIXED_NOW.isoformat()
        }
        
        response = client.post("/parse", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        
        # May be detected as all-day event
        if data["all_day"]:
            assert data["start_datetime"] is not None
    
    def test_parse_invalid_input(self):
        """Test parsing with invalid input."""
        # Empty text
        response = client.post("/parse", json={
            "text": "",
            "timezone": EST_TZ,
            "locale": "en_US",
            "now": FIXED_NOW.isoformat()
        })
        
        assert response.status_code == 422  # Validation error
        
        # Text too long
        response = client.post("/parse", json={
            "text": "x" * 20000,  # Exceeds max length
            "timezone": EST_TZ,
            "locale": "en_US",
            "now": FIXED_NOW.isoformat()
        })
        
        assert response.status_code == 422  # Validation error
    
    def test_parse_default_values(self):
        """Test parsing with default timezone and locale."""
        request_data = {
            "text": "Meeting tomorrow at 2pm"
            # No timezone, locale, or now specified
        }
        
        response = client.post("/parse", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        
        # Should use defaults
        assert data["timezone"] == "UTC"
        assert data["confidence_score"] >= 0.0


class TestContractCompliance:
    """Test API contract compliance."""
    
    def test_response_schema_compliance(self):
        """Test that all responses match the expected schema."""
        request_data = {
            "text": "Meeting tomorrow at 2pm in Room 101",
            "timezone": EST_TZ,
            "locale": "en_US",
            "now": FIXED_NOW.isoformat()
        }
        
        response = client.post("/parse", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        
        # Required fields
        required_fields = [
            "title", "start_datetime", "end_datetime", "location", 
            "description", "confidence_score", "all_day", "timezone"
        ]
        
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"
        
        # Type validation
        assert isinstance(data["confidence_score"], (int, float))
        assert 0.0 <= data["confidence_score"] <= 1.0
        assert isinstance(data["all_day"], bool)
        assert isinstance(data["timezone"], str)
        
        # Optional string fields can be None or string
        for field in ["title", "start_datetime", "end_datetime", "location"]:
            assert data[field] is None or isinstance(data[field], str)
        
        # Description should always be a string (fallback to original text)
        assert isinstance(data["description"], str)
    
    def test_iso_8601_datetime_format(self):
        """Test that datetime fields are in ISO 8601 format with timezone."""
        request_data = {
            "text": "Meeting on March 20, 2024 at 3:30 PM",
            "timezone": EST_TZ,
            "locale": "en_US",
            "now": FIXED_NOW.isoformat()
        }
        
        response = client.post("/parse", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        
        if data["start_datetime"]:
            start_dt = data["start_datetime"]
            # Should be ISO 8601 format
            assert "T" in start_dt
            assert len(start_dt) >= 19  # YYYY-MM-DDTHH:MM:SS minimum
            
            # Should have timezone information
            assert ("+" in start_dt or "-" in start_dt or start_dt.endswith("Z"))
            
            # Should be parseable as datetime
            from datetime import datetime as dt
            parsed_dt = dt.fromisoformat(start_dt.replace('Z', '+00:00'))
            assert isinstance(parsed_dt, dt)
        
        if data["end_datetime"]:
            end_dt = data["end_datetime"]
            # Same validation for end datetime
            assert "T" in end_dt
            assert ("+" in end_dt or "-" in end_dt or end_dt.endswith("Z"))
            
            parsed_dt = dt.fromisoformat(end_dt.replace('Z', '+00:00'))
            assert isinstance(parsed_dt, dt)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])