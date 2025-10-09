"""
Unit tests for LLM function calling schema implementation.
Tests schema enforcement, constraint validation, and field enhancement.
"""

import json
import pytest
from unittest.mock import Mock, patch
from datetime import datetime

from services.llm_enhancer import LLMEnhancer, EnhancementResult
from services.llm_service import LLMService, LLMResponse
from models.event_models import FieldResult


class TestLLMFunctionCallingSchema:
    """Test LLM function calling schema implementation."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_llm_service = Mock(spec=LLMService)
        self.mock_llm_service.is_available.return_value = True
        self.mock_llm_service.provider = "test"
        self.mock_llm_service.model = "test-model"
        
        self.enhancer = LLMEnhancer(llm_service=self.mock_llm_service)
    
    def test_function_calling_schema_structure(self):
        """Test that function calling schema has correct structure."""
        schema = self.enhancer.function_calling_schema
        
        # Verify top-level structure
        assert schema["name"] == "enhance_event_fields"
        assert "description" in schema
        assert "parameters" in schema
        
        # Verify parameters structure
        params = schema["parameters"]
        assert params["type"] == "object"
        assert "enhanced_fields" in params["properties"]
        assert "field_confidence" in params["properties"]
        assert "locked_fields_preserved" in params["properties"]
        assert "enhancement_notes" in params["properties"]
        
        # Verify required fields
        required = params["required"]
        assert "enhanced_fields" in required
        assert "field_confidence" in required
        assert "locked_fields_preserved" in required
        assert "enhancement_notes" in required
        
        # Verify no additional properties allowed
        assert params["additionalProperties"] is False
    
    def test_create_field_enhancement_schema(self):
        """Test dynamic schema creation for field enhancement."""
        fields_to_enhance = ["title", "location"]
        locked_fields = {"start_datetime": "2025-10-15T14:00:00", "end_datetime": "2025-10-15T15:00:00"}
        
        schema = self.enhancer._create_field_enhancement_schema(fields_to_enhance, locked_fields)
        
        # Verify enhanced_fields properties
        enhanced_props = schema["properties"]["enhanced_fields"]["properties"]
        assert "title" in enhanced_props
        assert "location" in enhanced_props
        assert "start_datetime" not in enhanced_props  # Should not be in enhancement schema
        
        # Verify field_confidence properties
        confidence_props = schema["properties"]["field_confidence"]["properties"]
        assert "title" in confidence_props
        assert "location" in confidence_props
        
        # Verify locked fields mentioned in description
        locked_desc = schema["properties"]["locked_fields_preserved"]["description"]
        assert "start_datetime" in locked_desc
        assert "end_datetime" in locked_desc
    
    def test_enforce_schema_constraints_removes_locked_fields(self):
        """Test that schema constraints prevent modification of locked fields."""
        llm_output = {
            "enhanced_fields": {
                "title": "Enhanced Title",
                "start_datetime": "2025-10-15T16:00:00"  # Unauthorized modification
            },
            "field_confidence": {
                "title": 0.8,
                "start_datetime": 0.9
            },
            "locked_fields_preserved": True,
            "enhancement_notes": "Enhanced title"
        }
        
        locked_fields = {"start_datetime": "2025-10-15T14:00:00"}
        
        validated = self.enhancer.enforce_schema_constraints(llm_output, locked_fields)
        
        # Verify locked field was removed from enhanced_fields
        assert "start_datetime" not in validated["enhanced_fields"]
        assert "title" in validated["enhanced_fields"]  # Allowed field preserved
        
        # Verify warning added to notes
        assert "WARNING" in validated["enhancement_notes"]
        assert "start_datetime" in validated["enhancement_notes"]
    
    def test_limit_context_to_residual(self):
        """Test context limitation to residual unparsed text."""
        text = "Meeting with John tomorrow at 2pm in Conference Room A about project updates"
        
        field_results = {
            "start_datetime": FieldResult(
                value="2025-10-16T14:00:00",
                source="regex",
                confidence=0.9,
                span=(18, 33),  # "tomorrow at 2pm"
                alternatives=[],
                processing_time_ms=10
            ),
            "location": FieldResult(
                value="Conference Room A",
                source="regex", 
                confidence=0.8,
                span=(37, 54),  # "Conference Room A"
                alternatives=[],
                processing_time_ms=5
            )
        }
        
        residual = self.enhancer.limit_context_to_residual(text, field_results)
        
        # Verify high-confidence spans were removed
        assert "tomorrow at 2pm" not in residual
        assert "Conference Room A" not in residual
        
        # Verify remaining context preserved
        assert "Meeting with John" in residual
        assert "about project updates" in residual
    
    def test_timeout_with_retry_success_first_attempt(self):
        """Test timeout handling with successful first attempt."""
        mock_response = LLMResponse(
            success=True,
            data={"enhanced_fields": {"title": "Test Event"}},
            error=None,
            provider="test",
            model="test-model",
            confidence=0.8,
            processing_time=1.0
        )
        
        with patch.object(self.enhancer, '_call_llm_with_schema', return_value=mock_response):
            result = self.enhancer.timeout_with_retry("system", "user", {}, timeout_seconds=3)
        
        assert result is not None
        assert result.success is True
        assert result.data["enhanced_fields"]["title"] == "Test Event"
    
    def test_timeout_with_retry_success_second_attempt(self):
        """Test timeout handling with successful retry."""
        failed_response = LLMResponse(
            success=False,
            data=None,
            error="First attempt failed",
            provider="test",
            model="test-model",
            confidence=0.0,
            processing_time=0.5
        )
        
        success_response = LLMResponse(
            success=True,
            data={"enhanced_fields": {"title": "Retry Success"}},
            error=None,
            provider="test",
            model="test-model",
            confidence=0.7,
            processing_time=1.2
        )
        
        with patch.object(self.enhancer, '_call_llm_with_schema', side_effect=[failed_response, success_response]):
            result = self.enhancer.timeout_with_retry("system", "user", {}, timeout_seconds=3)
        
        assert result is not None
        assert result.success is True
        assert result.data["enhanced_fields"]["title"] == "Retry Success"
    
    def test_timeout_with_retry_both_attempts_fail(self):
        """Test timeout handling when both attempts fail."""
        failed_response = LLMResponse(
            success=False,
            data=None,
            error="Both attempts failed",
            provider="test",
            model="test-model",
            confidence=0.0,
            processing_time=0.5
        )
        
        with patch.object(self.enhancer, '_call_llm_with_schema', return_value=failed_response):
            result = self.enhancer.timeout_with_retry("system", "user", {}, timeout_seconds=3)
        
        assert result is None  # Should return None for partial results handling
    
    def test_validate_json_schema_function_calling(self):
        """Test JSON schema validation for function calling response."""
        valid_output = json.dumps({
            "enhanced_fields": {
                "title": "Enhanced Event Title",
                "location": "Enhanced Location"
            },
            "field_confidence": {
                "title": 0.8,
                "location": 0.7
            },
            "locked_fields_preserved": True,
            "enhancement_notes": "Enhanced title and location"
        })
        
        schema = self.enhancer.function_calling_schema["parameters"]
        is_valid, result, error = self.enhancer.validate_json_schema(valid_output, schema)
        
        assert is_valid is True
        assert isinstance(result, dict)
        assert "enhanced_fields" in result
        assert "field_confidence" in result
        assert result["locked_fields_preserved"] is True
        assert result["field_confidence"]["title"] == 0.8
    
    def test_validate_json_schema_invalid_confidence(self):
        """Test JSON schema validation with invalid confidence values."""
        invalid_output = json.dumps({
            "enhanced_fields": {"title": "Test"},
            "field_confidence": {"title": 1.5},  # Invalid confidence > 1.0
            "locked_fields_preserved": True,
            "enhancement_notes": "Test"
        })
        
        schema = self.enhancer.function_calling_schema["parameters"]
        is_valid, result, error = self.enhancer.validate_json_schema(invalid_output, schema)
        
        # Should still be valid but with warning about confidence range
        assert is_valid is True
        assert result["field_confidence"]["title"] == 1.5  # Original value preserved
    
    def test_validate_json_schema_malformed_json(self):
        """Test JSON schema validation with malformed JSON."""
        malformed_output = '{"enhanced_fields": {"title": "Test"'  # Missing closing braces
        
        schema = self.enhancer.function_calling_schema["parameters"]
        is_valid, result, error = self.enhancer.validate_json_schema(malformed_output, schema)
        
        # Should return False for malformed JSON
        assert is_valid is False
        assert result is None
        assert "Invalid JSON syntax" in error
    
    def test_enhance_low_confidence_fields_integration(self):
        """Test complete field enhancement with function calling schema."""
        text = "Team meeting tomorrow at 2pm in the main conference room"
        
        field_results = {
            "title": FieldResult(
                value="Team meeting",
                source="regex",
                confidence=0.6,  # Low confidence - needs enhancement
                span=(0, 12),
                alternatives=[],
                processing_time_ms=5
            ),
            "start_datetime": FieldResult(
                value="2025-10-16T14:00:00",
                source="regex",
                confidence=0.9,  # High confidence - locked
                span=(13, 28),
                alternatives=[],
                processing_time_ms=10
            )
        }
        
        locked_fields = {"start_datetime": "2025-10-16T14:00:00"}
        
        # Mock successful LLM response
        mock_response = LLMResponse(
            success=True,
            data={
                "enhanced_fields": {
                    "title": "Team Meeting - Project Updates"
                },
                "field_confidence": {
                    "title": 0.8
                },
                "locked_fields_preserved": True,
                "enhancement_notes": "Enhanced title for clarity"
            },
            error=None,
            provider="test",
            model="test-model",
            confidence=0.8,
            processing_time=1.0
        )
        
        with patch.object(self.enhancer, 'timeout_with_retry', return_value=mock_response):
            result = self.enhancer.enhance_low_confidence_fields(
                text, field_results, locked_fields, confidence_threshold=0.8
            )
        
        # Verify enhancement applied
        assert result["title"].value == "Team Meeting - Project Updates"
        assert result["title"].confidence > field_results["title"].confidence
        assert result["title"].source == "llm_enhancement"
        
        # Verify locked field preserved
        assert result["start_datetime"] == field_results["start_datetime"]
    
    def test_get_field_enhancement_system_prompt(self):
        """Test system prompt generation for field enhancement."""
        locked_fields = {"start_datetime": "2025-10-15T14:00:00", "end_datetime": "2025-10-15T15:00:00"}
        
        prompt = self.enhancer._get_field_enhancement_system_prompt(locked_fields)
        
        # Verify locked fields mentioned
        assert "start_datetime" in prompt
        assert "end_datetime" in prompt
        
        # Verify key constraints mentioned
        assert "Temperature = 0" in prompt
        assert "NEVER modify" in prompt
        assert "JSON matching the provided schema" in prompt
    
    def test_format_field_enhancement_prompt(self):
        """Test prompt formatting for field enhancement."""
        residual_text = "Meeting with John about project updates"
        fields_to_enhance = ["title", "location"]
        
        field_results = {
            "title": FieldResult(
                value="Meeting",
                source="regex",
                confidence=0.5,
                span=(0, 7),
                alternatives=[],
                processing_time_ms=5
            )
        }
        
        locked_fields = {"start_datetime": "2025-10-15T14:00:00"}
        
        prompt = self.enhancer._format_field_enhancement_prompt(
            residual_text, fields_to_enhance, field_results, locked_fields
        )
        
        # Verify prompt structure
        assert residual_text in prompt
        assert "['title', 'location']" in prompt
        assert "title: Meeting (confidence: 0.50)" in prompt
        assert "location: None" in prompt
        assert "start_datetime: 2025-10-15T14:00:00" in prompt
        assert "LOCKED fields" in prompt


if __name__ == "__main__":
    pytest.main([__file__])