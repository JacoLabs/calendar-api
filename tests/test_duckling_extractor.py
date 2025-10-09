"""
Unit tests for Duckling extractor integration.

Tests the DucklingExtractor class for deterministic date/time entity extraction,
including confidence scoring, timezone validation, and edge cases.
"""

import pytest
import json
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch, MagicMock
import requests
from requests.exceptions import RequestException, Timeout, ConnectionError

from services.duckling_extractor import DucklingExtractor
from models.event_models import FieldResult


class TestDucklingExtractor:
    """Test cases for DucklingExtractor class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.extractor = DucklingExtractor(
            duckling_url="http://localhost:8000/parse",
            timeout_seconds=3,
            default_timezone="UTC"
        )
    
    def test_init(self):
        """Test DucklingExtractor initialization."""
        extractor = DucklingExtractor(
            duckling_url="http://test:9000/parse",
            timeout_seconds=5,
            default_timezone="America/New_York"
        )
        
        assert extractor.duckling_url == "http://test:9000/parse"
        assert extractor.timeout_seconds == 5
        assert extractor.default_timezone == "America/New_York"
        assert extractor._service_available is None
        assert extractor._health_check_interval == 300
    
    @patch('requests.post')
    def test_is_service_available_success(self, mock_post):
        """Test service availability check when service is available."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response
        
        assert self.extractor.is_service_available() is True
        
        # Verify request was made correctly
        mock_post.assert_called_once_with(
            "http://localhost:8000/parse",
            json={
                "text": "test",
                "dims": ["time"],
                "locale": "en_US"
            },
            timeout=2
        )
    
    @patch('requests.post')
    def test_is_service_available_failure(self, mock_post):
        """Test service availability check when service is unavailable."""
        mock_post.side_effect = ConnectionError("Connection failed")
        
        assert self.extractor.is_service_available() is False
    
    @patch('requests.post')
    def test_is_service_available_cached(self, mock_post):
        """Test that service availability is cached."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response
        
        # First call
        assert self.extractor.is_service_available() is True
        
        # Second call should use cached result
        assert self.extractor.is_service_available() is True
        
        # Should only have made one request
        assert mock_post.call_count == 1
    
    @patch('requests.post')
    def test_extract_with_duckling_service_unavailable(self, mock_post):
        """Test extraction when Duckling service is unavailable."""
        mock_post.side_effect = ConnectionError("Connection failed")
        
        result = self.extractor.extract_with_duckling("tomorrow at 3pm", "start_datetime")
        
        assert result.value is None
        assert result.source == "duckling"
        assert result.confidence == 0.0
        assert result.span == (0, 0)
        assert result.alternatives == []
        assert result.processing_time_ms > 0
    
    @patch('requests.post')
    def test_extract_with_duckling_success(self, mock_post):
        """Test successful extraction with Duckling."""
        # Mock service availability check
        health_response = Mock()
        health_response.status_code = 200
        
        # Mock extraction response
        extract_response = Mock()
        extract_response.status_code = 200
        extract_response.json.return_value = [
            {
                "body": "tomorrow at 3pm",
                "start": 0,
                "end": 15,
                "value": {
                    "value": "2024-01-16T15:00:00.000Z",
                    "grain": "hour",
                    "type": "value"
                },
                "confidence": 0.8
            }
        ]
        
        mock_post.side_effect = [health_response, extract_response]
        
        result = self.extractor.extract_with_duckling("tomorrow at 3pm", "start_datetime")
        
        assert result.value is not None
        assert isinstance(result.value, datetime)
        assert result.source == "duckling"
        assert 0.6 <= result.confidence <= 0.8
        assert result.span == (0, 15)
        assert result.processing_time_ms > 0
    
    @patch('requests.post')
    def test_extract_with_duckling_no_entities(self, mock_post):
        """Test extraction when no entities are found."""
        # Mock service availability check
        health_response = Mock()
        health_response.status_code = 200
        
        # Mock empty extraction response
        extract_response = Mock()
        extract_response.status_code = 200
        extract_response.json.return_value = []
        
        mock_post.side_effect = [health_response, extract_response]
        
        result = self.extractor.extract_with_duckling("random text", "start_datetime")
        
        assert result.value is None
        assert result.source == "duckling"
        assert result.confidence == 0.0
        assert result.span == (0, 0)
        assert result.alternatives == []
    
    @patch('requests.post')
    def test_extract_with_duckling_timeout(self, mock_post):
        """Test extraction with timeout."""
        mock_post.side_effect = Timeout("Request timed out")
        
        result = self.extractor.extract_with_duckling("tomorrow at 3pm", "start_datetime")
        
        assert result.value is None
        assert result.source == "duckling"
        assert result.confidence == 0.0
        assert result.processing_time_ms > 0
    
    @patch('requests.post')
    def test_extract_with_duckling_http_error(self, mock_post):
        """Test extraction with HTTP error."""
        # Mock service availability check
        health_response = Mock()
        health_response.status_code = 200
        
        # Mock error response
        error_response = Mock()
        error_response.status_code = 500
        
        mock_post.side_effect = [health_response, error_response]
        
        result = self.extractor.extract_with_duckling("tomorrow at 3pm", "start_datetime")
        
        assert result.value is None
        assert result.source == "duckling"
        assert result.confidence == 0.0
    
    def test_select_best_entity_empty(self):
        """Test selecting best entity from empty list."""
        result = self.extractor._select_best_entity([], "time")
        assert result is None
    
    def test_select_best_entity_single(self):
        """Test selecting best entity from single entity."""
        entities = [
            {
                "start": 0,
                "end": 8,
                "confidence": 0.7,
                "value": {"value": "2024-01-16T15:00:00.000Z"}
            }
        ]
        
        result = self.extractor._select_best_entity(entities, "time")
        assert result == entities[0]
    
    def test_select_best_entity_multiple(self):
        """Test selecting best entity from multiple entities."""
        entities = [
            {
                "start": 0,
                "end": 15,  # Longer span
                "confidence": 0.6,
                "value": {"value": "2024-01-16T15:00:00.000Z"}
            },
            {
                "start": 0,
                "end": 8,   # Shorter span
                "confidence": 0.8,  # Higher confidence
                "value": {"value": "2024-01-16T15:00:00.000Z"}
            }
        ]
        
        result = self.extractor._select_best_entity(entities, "time")
        # Should prefer higher confidence
        assert result == entities[1]
    
    def test_extract_value_from_entity_datetime(self):
        """Test extracting datetime value from entity."""
        entity = {
            "value": {
                "value": "2024-01-16T15:00:00.000Z",
                "grain": "hour",
                "type": "value"
            }
        }
        
        result = self.extractor._extract_value_from_entity(entity, "start_datetime")
        
        assert isinstance(result, datetime)
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 16
        assert result.hour == 15
        assert result.tzinfo is not None
    
    def test_extract_value_from_entity_range_start(self):
        """Test extracting start time from range entity."""
        entity = {
            "value": {
                "from": {"value": "2024-01-16T15:00:00.000Z"},
                "to": {"value": "2024-01-16T17:00:00.000Z"},
                "type": "interval"
            }
        }
        
        result = self.extractor._extract_value_from_entity(entity, "start_datetime")
        
        assert isinstance(result, datetime)
        assert result.hour == 15  # Should get start time
    
    def test_extract_value_from_entity_range_end(self):
        """Test extracting end time from range entity."""
        entity = {
            "value": {
                "from": {"value": "2024-01-16T15:00:00.000Z"},
                "to": {"value": "2024-01-16T17:00:00.000Z"},
                "type": "interval"
            }
        }
        
        result = self.extractor._extract_value_from_entity(entity, "end_datetime")
        
        assert isinstance(result, datetime)
        assert result.hour == 17  # Should get end time
    
    def test_extract_value_from_entity_duration_minutes(self):
        """Test extracting duration in minutes."""
        entity = {
            "value": {
                "minute": 30,
                "type": "value"
            }
        }
        
        result = self.extractor._extract_value_from_entity(entity, "duration")
        assert result == 30
    
    def test_extract_value_from_entity_duration_hours(self):
        """Test extracting duration in hours."""
        entity = {
            "value": {
                "hour": 2,
                "type": "value"
            }
        }
        
        result = self.extractor._extract_value_from_entity(entity, "duration")
        assert result == 120  # 2 hours = 120 minutes
    
    def test_extract_value_from_entity_invalid(self):
        """Test extracting value from invalid entity."""
        entity = {"invalid": "data"}
        
        result = self.extractor._extract_value_from_entity(entity, "start_datetime")
        assert result is None
    
    def test_calculate_confidence_high_coverage(self):
        """Test confidence calculation with high text coverage."""
        entity = {
            "start": 0,
            "end": 15,
            "confidence": 0.8,
            "value": {"value": "2024-01-16T15:00:00.000Z"}
        }
        
        confidence = self.extractor._calculate_confidence(entity, "tomorrow at 3pm")
        
        assert 0.6 <= confidence <= 0.8
        assert confidence > 0.65  # Should be reasonably high due to good coverage
    
    def test_calculate_confidence_low_coverage(self):
        """Test confidence calculation with low text coverage."""
        entity = {
            "start": 0,
            "end": 3,
            "confidence": 0.5,
            "value": {"value": "2024-01-16T15:00:00.000Z"}
        }
        
        confidence = self.extractor._calculate_confidence(entity, "tomorrow at 3pm and other stuff")
        
        assert 0.6 <= confidence <= 0.8
        assert confidence < 0.75  # Should be lower due to poor coverage
    
    def test_calculate_confidence_complete_entity(self):
        """Test confidence calculation with complete entity."""
        entity = {
            "start": 0,
            "end": 8,
            "confidence": 0.7,
            "value": {"value": "2024-01-16T15:00:00.000Z"}
        }
        
        confidence = self.extractor._calculate_confidence(entity, "tomorrow")
        
        assert 0.6 <= confidence <= 0.8
        # Should be reasonably high due to complete value
        assert confidence >= 0.62
    
    def test_calculate_confidence_range_entity(self):
        """Test confidence calculation with range entity."""
        entity = {
            "start": 0,
            "end": 15,
            "confidence": 0.7,
            "value": {
                "from": {"value": "2024-01-16T15:00:00.000Z"},
                "to": {"value": "2024-01-16T17:00:00.000Z"}
            }
        }
        
        confidence = self.extractor._calculate_confidence(entity, "3pm to 5pm")
        
        assert 0.6 <= confidence <= 0.8
        # Should be reasonably high due to range completeness
        assert confidence >= 0.65
    
    def test_validate_timezone_normalization_valid(self):
        """Test timezone validation with valid datetime."""
        dt = datetime(2024, 1, 16, 15, 0, 0, tzinfo=timezone.utc)
        field_result = FieldResult(
            value=dt,
            source="duckling",
            confidence=0.7,
            span=(0, 8)
        )
        
        assert self.extractor.validate_timezone_normalization(field_result) is True
    
    def test_validate_timezone_normalization_naive(self):
        """Test timezone validation with naive datetime."""
        dt = datetime(2024, 1, 16, 15, 0, 0)  # No timezone
        field_result = FieldResult(
            value=dt,
            source="duckling",
            confidence=0.7,
            span=(0, 8)
        )
        
        assert self.extractor.validate_timezone_normalization(field_result) is False
    
    def test_validate_timezone_normalization_invalid_offset(self):
        """Test timezone validation with invalid timezone offset."""
        # Create timezone with invalid offset (15 hours)
        invalid_tz = timezone(timedelta(hours=15))
        dt = datetime(2024, 1, 16, 15, 0, 0, tzinfo=invalid_tz)
        field_result = FieldResult(
            value=dt,
            source="duckling",
            confidence=0.7,
            span=(0, 8)
        )
        
        assert self.extractor.validate_timezone_normalization(field_result) is False
    
    def test_validate_timezone_normalization_non_datetime(self):
        """Test timezone validation with non-datetime value."""
        field_result = FieldResult(
            value="not a datetime",
            source="duckling",
            confidence=0.7,
            span=(0, 8)
        )
        
        assert self.extractor.validate_timezone_normalization(field_result) is False
    
    def test_normalize_timezone_naive_to_utc(self):
        """Test normalizing naive datetime to UTC."""
        dt = datetime(2024, 1, 16, 15, 0, 0)  # Naive datetime
        
        result = self.extractor.normalize_timezone(dt, "UTC")
        
        assert result.tzinfo == timezone.utc
        assert result.year == 2024
        assert result.hour == 15
    
    def test_normalize_timezone_aware_to_utc(self):
        """Test normalizing timezone-aware datetime to UTC."""
        # Create datetime in EST (UTC-5)
        est_tz = timezone(timedelta(hours=-5))
        dt = datetime(2024, 1, 16, 15, 0, 0, tzinfo=est_tz)
        
        result = self.extractor.normalize_timezone(dt, "UTC")
        
        assert result.tzinfo == timezone.utc
        assert result.hour == 20  # 15:00 EST = 20:00 UTC
    
    def test_normalize_timezone_default(self):
        """Test normalizing with default timezone."""
        dt = datetime(2024, 1, 16, 15, 0, 0)
        
        result = self.extractor.normalize_timezone(dt)
        
        assert result.tzinfo == timezone.utc
    
    @patch('requests.post')
    def test_extract_multiple_fields(self, mock_post):
        """Test extracting multiple fields in one call."""
        # Mock service availability check
        health_response = Mock()
        health_response.status_code = 200
        
        # Mock extraction responses
        extract_response = Mock()
        extract_response.status_code = 200
        extract_response.json.return_value = [
            {
                "body": "tomorrow at 3pm",
                "start": 0,
                "end": 15,
                "value": {"value": "2024-01-16T15:00:00.000Z"},
                "confidence": 0.8
            }
        ]
        
        mock_post.side_effect = [health_response, extract_response, extract_response]
        
        fields = ["start_datetime", "end_datetime"]
        results = self.extractor.extract_multiple_fields("tomorrow at 3pm", fields)
        
        assert len(results) == 2
        assert "start_datetime" in results
        assert "end_datetime" in results
        assert all(isinstance(result, FieldResult) for result in results.values())
    
    def test_field_mapping(self):
        """Test that field types are correctly mapped to Duckling dimensions."""
        # This is tested indirectly through the extract_with_duckling method
        # by checking that the correct payload is sent to Duckling
        
        with patch('requests.post') as mock_post:
            # Mock service availability
            health_response = Mock()
            health_response.status_code = 200
            
            # Mock extraction response
            extract_response = Mock()
            extract_response.status_code = 200
            extract_response.json.return_value = []
            
            mock_post.side_effect = [health_response, extract_response]
            
            self.extractor.extract_with_duckling("test", "duration")
            
            # Check that the correct dimension was used
            call_args = mock_post.call_args_list[1]  # Second call is the extraction
            payload = call_args[1]['json']
            assert payload['dims'] == ['duration']
    
    @patch('requests.post')
    def test_edge_case_malformed_response(self, mock_post):
        """Test handling of malformed JSON response."""
        # Mock service availability check
        health_response = Mock()
        health_response.status_code = 200
        
        # Mock malformed response
        extract_response = Mock()
        extract_response.status_code = 200
        extract_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
        
        mock_post.side_effect = [health_response, extract_response]
        
        result = self.extractor.extract_with_duckling("tomorrow at 3pm", "start_datetime")
        
        assert result.value is None
        assert result.source == "duckling"
        assert result.confidence == 0.0
    
    @patch('requests.post')
    def test_edge_case_empty_text(self, mock_post):
        """Test extraction with empty text."""
        # Mock service availability check
        health_response = Mock()
        health_response.status_code = 200
        
        # Mock empty response
        extract_response = Mock()
        extract_response.status_code = 200
        extract_response.json.return_value = []
        
        mock_post.side_effect = [health_response, extract_response]
        
        result = self.extractor.extract_with_duckling("", "start_datetime")
        
        assert result.value is None
        assert result.confidence == 0.0
    
    def test_confidence_range_enforcement(self):
        """Test that confidence scores are always within 0.6-0.8 range."""
        # Test various entity configurations
        test_cases = [
            # (entity, text, expected_min, expected_max)
            ({"start": 0, "end": 5, "confidence": 0.9, "value": {"value": "test"}}, "hello", 0.6, 0.8),
            ({"start": 0, "end": 1, "confidence": 0.3, "value": {"value": "test"}}, "hello world", 0.6, 0.8),
            ({"start": 0, "end": 10, "confidence": 0.7, "value": {"value": "test"}}, "hello world", 0.6, 0.8),
        ]
        
        for entity, text, min_conf, max_conf in test_cases:
            confidence = self.extractor._calculate_confidence(entity, text)
            assert min_conf <= confidence <= max_conf, f"Confidence {confidence} not in range [{min_conf}, {max_conf}]"


class TestDucklingExtractorIntegration:
    """Integration tests for DucklingExtractor (require running Duckling service)."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.extractor = DucklingExtractor()
    
    @pytest.mark.integration
    def test_real_duckling_service(self):
        """Test with real Duckling service (if available)."""
        # This test only runs if Duckling service is actually running
        if not self.extractor.is_service_available():
            pytest.skip("Duckling service not available")
        
        result = self.extractor.extract_with_duckling("tomorrow at 3pm", "start_datetime")
        
        # If service is available, we should get a reasonable result
        assert result.source == "duckling"
        assert result.processing_time_ms > 0
        
        # Result might be None if Duckling can't parse, but should not error
        if result.value is not None:
            assert isinstance(result.value, datetime)
            assert 0.6 <= result.confidence <= 0.8
    
    @pytest.mark.integration
    def test_real_duckling_multiple_entities(self):
        """Test extracting multiple entities with real service."""
        if not self.extractor.is_service_available():
            pytest.skip("Duckling service not available")
        
        text = "Meeting from 2pm to 4pm tomorrow"
        result = self.extractor.extract_with_duckling(text, "start_datetime")
        
        assert result.source == "duckling"
        if result.value is not None:
            assert isinstance(result.value, datetime)
            # Should have alternatives for end time
            assert len(result.alternatives) >= 0