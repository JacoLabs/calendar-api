"""
Unit tests for LLM Enhancer guardrails implementation (Task 6).
Tests the new methods added for per-field confidence routing with strict guardrails.
"""

import unittest
from unittest.mock import Mock, patch
from datetime import datetime

from services.llm_enhancer import LLMEnhancer
from services.llm_service import LLMResponse
from models.event_models import FieldResult


class TestLLMEnhancerGuardrails(unittest.TestCase):
    """Test LLM enhancer guardrails functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.enhancer = LLMEnhancer()
        
        # Mock LLM service
        self.mock_llm_service = Mock()
        self.mock_llm_service.is_available.return_value = True
        self.mock_llm_service.provider = "mock"
        self.mock_llm_service.model = "test-model"
        self.enhancer.llm_service = self.mock_llm_service
    
    def test_enforce_schema_constraints(self):
        """Test schema constraint enforcement prevents locked field modification."""
        llm_output = {
            "title": "Modified Title",
            "start_datetime": "2025-01-15T10:00:00",  # Should be blocked
            "location": "New Location",
            "end_datetime": "2025-01-15T11:00:00"  # Should be blocked
        }
        
        locked_fields = {
            "start_datetime": "2025-01-15T09:00:00",
            "end_datetime": "2025-01-15T10:00:00"
        }
        
        validated = self.enhancer.enforce_schema_constraints(llm_output, locked_fields)
        
        # Locked fields should be removed
        self.assertNotIn("start_datetime", validated)
        self.assertNotIn("end_datetime", validated)
        
        # Non-locked fields should be preserved
        self.assertIn("title", validated)
        self.assertIn("location", validated)
        self.assertEqual(validated["title"], "Modified Title")
        self.assertEqual(validated["location"], "New Location")
    
    def test_enforce_schema_constraints_datetime_protection(self):
        """Test that datetime fields are protected when any fields are locked."""
        llm_output = {
            "title": "Modified Title",
            "start_datetime": "2025-01-15T10:00:00",
            "date": "2025-01-15",
            "time": "10:00"
        }
        
        locked_fields = {"location": "Conference Room"}  # Any locked field triggers datetime protection
        
        validated = self.enhancer.enforce_schema_constraints(llm_output, locked_fields)
        
        # All datetime-related fields should be blocked
        self.assertNotIn("start_datetime", validated)
        self.assertNotIn("date", validated)
        self.assertNotIn("time", validated)
        
        # Non-datetime fields should be preserved
        self.assertIn("title", validated)
    
    def test_limit_context_to_residual(self):
        """Test context limiting to residual unparsed text."""
        original_text = "Meeting with John tomorrow at 2pm in Conference Room A to discuss the project"
        
        # Create field results with actual spans
        datetime_start = original_text.find("tomorrow at 2pm")
        datetime_end = datetime_start + len("tomorrow at 2pm")
        location_start = original_text.find("Conference Room A")
        location_end = location_start + len("Conference Room A")
        
        field_results = {
            "start_datetime": FieldResult(
                value="2025-01-16T14:00:00",
                source="regex",
                confidence=0.9,
                span=(datetime_start, datetime_end)
            ),
            "location": FieldResult(
                value="Conference Room A",
                source="regex",
                confidence=0.8,
                span=(location_start, location_end)
            )
        }
        
        residual = self.enhancer.limit_context_to_residual(original_text, field_results)
        
        # Extracted spans should be removed
        self.assertNotIn("tomorrow at 2pm", residual)
        self.assertNotIn("Conference Room A", residual)
        
        # Remaining text should be preserved
        self.assertIn("Meeting with John", residual)
        self.assertIn("to discuss the project", residual)
    
    def test_limit_context_to_residual_no_spans(self):
        """Test context limiting when no spans are provided."""
        original_text = "Meeting tomorrow at 2pm"
        field_results = {}
        
        residual = self.enhancer.limit_context_to_residual(original_text, field_results)
        
        # Should return original text when no spans
        self.assertEqual(residual, original_text)
    
    def test_limit_context_to_residual_short_result(self):
        """Test context limiting when residual text becomes too short."""
        original_text = "Meeting at 2pm"
        
        field_results = {
            "start_datetime": FieldResult(
                value="2025-01-16T14:00:00",
                source="regex",
                confidence=0.9,
                span=(8, 14)  # "at 2pm"
            )
        }
        
        residual = self.enhancer.limit_context_to_residual(original_text, field_results)
        
        # Should return original text when residual is too short
        self.assertEqual(residual, original_text)
    
    def test_validate_json_schema_valid(self):
        """Test JSON schema validation with valid input."""
        schema = {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "confidence": {"type": "number"}
            },
            "required": ["title"],
            "additionalProperties": False
        }
        
        valid_json = '{"title": "Test Event", "confidence": 0.8}'
        is_valid, data, error = self.enhancer.validate_json_schema(valid_json, schema)
        
        self.assertTrue(is_valid)
        self.assertIsNotNone(data)
        self.assertIsNone(error)
        self.assertEqual(data["title"], "Test Event")
        self.assertEqual(data["confidence"], 0.8)
    
    def test_validate_json_schema_missing_required(self):
        """Test JSON schema validation with missing required field."""
        schema = {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "confidence": {"type": "number"}
            },
            "required": ["title"],
            "additionalProperties": False
        }
        
        invalid_json = '{"confidence": 0.8}'
        is_valid, data, error = self.enhancer.validate_json_schema(invalid_json, schema)
        
        self.assertFalse(is_valid)
        self.assertIsNone(data)
        self.assertIsNotNone(error)
        self.assertIn("title", error)
    
    def test_validate_json_schema_malformed(self):
        """Test JSON schema validation with malformed JSON."""
        schema = {"type": "object"}
        malformed_json = '{"title": "Test Event"'  # Missing closing brace
        
        is_valid, data, error = self.enhancer.validate_json_schema(malformed_json, schema)
        
        self.assertFalse(is_valid)
        self.assertIsNone(data)
        self.assertIsNotNone(error)
        self.assertIn("Invalid JSON", error)
    
    def test_validate_json_schema_wrong_type(self):
        """Test JSON schema validation with wrong field type."""
        schema = {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "confidence": {"type": "number"}
            },
            "required": ["title"]
        }
        
        invalid_json = '{"title": 123, "confidence": "not_a_number"}'
        is_valid, data, error = self.enhancer.validate_json_schema(invalid_json, schema)
        
        self.assertFalse(is_valid)
        self.assertIsNone(data)
        self.assertIsNotNone(error)
    
    def test_validate_json_schema_additional_properties(self):
        """Test JSON schema validation with additional properties not allowed."""
        schema = {
            "type": "object",
            "properties": {
                "title": {"type": "string"}
            },
            "additionalProperties": False
        }
        
        invalid_json = '{"title": "Test", "extra_field": "not_allowed"}'
        is_valid, data, error = self.enhancer.validate_json_schema(invalid_json, schema)
        
        self.assertFalse(is_valid)
        self.assertIsNone(data)
        self.assertIsNotNone(error)
        self.assertIn("Additional properties", error)
    
    def test_create_field_enhancement_schema(self):
        """Test field enhancement schema creation."""
        fields_to_enhance = ["title", "location"]
        locked_fields = {"start_datetime": "2025-01-15T10:00:00"}
        
        schema = self.enhancer._create_field_enhancement_schema(fields_to_enhance, locked_fields)
        
        # Check schema structure
        self.assertIn("properties", schema)
        self.assertIn("required", schema)
        self.assertEqual(schema["type"], "object")
        self.assertFalse(schema["additionalProperties"])
        
        # Check field properties
        self.assertIn("title", schema["properties"])
        self.assertIn("location", schema["properties"])
        self.assertIn("confidence", schema["properties"])
        
        # Check required fields
        self.assertIn("confidence", schema["required"])
        
        # Check confidence sub-schema
        confidence_props = schema["properties"]["confidence"]["properties"]
        self.assertIn("title", confidence_props)
        self.assertIn("location", confidence_props)
    
    @patch('time.sleep')  # Mock sleep to speed up tests
    def test_timeout_with_retry_success(self, mock_sleep):
        """Test timeout with retry on successful call."""
        # Mock successful LLM response
        mock_response = LLMResponse(
            success=True,
            data={"title": "Test"},
            error=None,
            provider="mock",
            model="test",
            confidence=0.8,
            processing_time=0.1
        )
        
        self.enhancer._call_llm_with_schema = Mock(return_value=mock_response)
        
        response = self.enhancer.timeout_with_retry("system", "user", {}, timeout_seconds=1)
        
        self.assertIsNotNone(response)
        self.assertTrue(response.success)
        self.assertEqual(response.data["title"], "Test")
        
        # Should only call once on success
        self.enhancer._call_llm_with_schema.assert_called_once()
    
    @patch('time.sleep')  # Mock sleep to speed up tests
    def test_timeout_with_retry_failure_then_success(self, mock_sleep):
        """Test timeout with retry on failure then success."""
        # Mock first call failure, second call success
        mock_responses = [
            LLMResponse(success=False, data=None, error="First attempt failed", provider="mock", model="test", confidence=0.0, processing_time=0.1),
            LLMResponse(success=True, data={"title": "Test"}, error=None, provider="mock", model="test", confidence=0.8, processing_time=0.1)
        ]
        
        self.enhancer._call_llm_with_schema = Mock(side_effect=mock_responses)
        
        response = self.enhancer.timeout_with_retry("system", "user", {}, timeout_seconds=1)
        
        self.assertIsNotNone(response)
        self.assertTrue(response.success)
        self.assertEqual(response.data["title"], "Test")
        
        # Should call twice (initial + retry)
        self.assertEqual(self.enhancer._call_llm_with_schema.call_count, 2)
    
    @patch('time.sleep')  # Mock sleep to speed up tests
    def test_timeout_with_retry_both_fail(self, mock_sleep):
        """Test timeout with retry when both attempts fail."""
        # Mock both calls failing
        mock_response = LLMResponse(
            success=False,
            data=None,
            error="Both attempts failed",
            provider="mock",
            model="test",
            confidence=0.0,
            processing_time=0.1
        )
        
        self.enhancer._call_llm_with_schema = Mock(return_value=mock_response)
        
        response = self.enhancer.timeout_with_retry("system", "user", {}, timeout_seconds=1)
        
        self.assertIsNone(response)
        
        # Should call twice (initial + retry)
        self.assertEqual(self.enhancer._call_llm_with_schema.call_count, 2)
    
    def test_enhance_low_confidence_fields_llm_unavailable(self):
        """Test field enhancement when LLM service is unavailable."""
        self.mock_llm_service.is_available.return_value = False
        
        text = "Meeting tomorrow"
        field_results = {
            "title": FieldResult(value="Meeting", source="regex", confidence=0.3, span=(0, 7))
        }
        locked_fields = {}
        
        enhanced_results = self.enhancer.enhance_low_confidence_fields(
            text, field_results, locked_fields
        )
        
        # Should return original results when LLM unavailable
        self.assertEqual(enhanced_results, field_results)
    
    def test_enhance_low_confidence_fields_no_enhancement_needed(self):
        """Test field enhancement when all fields have high confidence."""
        text = "Meeting tomorrow at 2pm"
        
        # All fields have high confidence
        field_results = {
            "title": FieldResult(value="Meeting", source="regex", confidence=0.9, span=(0, 7)),
            "start_datetime": FieldResult(value="2025-01-16T14:00:00", source="regex", confidence=0.9, span=(8, 23))
        }
        locked_fields = {}
        
        enhanced_results = self.enhancer.enhance_low_confidence_fields(
            text, field_results, locked_fields, confidence_threshold=0.8
        )
        
        # Should return original results unchanged
        self.assertEqual(enhanced_results, field_results)
    
    def test_enhance_low_confidence_fields_success(self):
        """Test successful field enhancement."""
        # Mock successful timeout_with_retry
        mock_response = LLMResponse(
            success=True,
            data={
                "title": "Enhanced Meeting Title",
                "location": "Enhanced Location",
                "confidence": {"title": 0.8, "location": 0.7}
            },
            error=None,
            provider="mock",
            model="test-model",
            confidence=0.75,
            processing_time=0.5
        )
        
        self.enhancer.timeout_with_retry = Mock(return_value=mock_response)
        
        text = "Meeting with John tomorrow at 2pm in Conference Room A"
        
        field_results = {
            "title": FieldResult(value="Meeting", source="regex", confidence=0.4, span=(0, 7)),
            "start_datetime": FieldResult(value="2025-01-16T14:00:00", source="regex", confidence=0.9, span=(18, 33)),
            "location": FieldResult(value="Conference Room A", source="regex", confidence=0.5, span=(37, 54))
        }
        
        locked_fields = {"start_datetime": "2025-01-16T14:00:00"}
        
        enhanced_results = self.enhancer.enhance_low_confidence_fields(
            text, field_results, locked_fields, confidence_threshold=0.8
        )
        
        # Check that low-confidence fields were enhanced
        self.assertEqual(enhanced_results["title"].value, "Enhanced Meeting Title")
        self.assertEqual(enhanced_results["title"].source, "llm_enhancement")
        self.assertGreater(enhanced_results["title"].confidence, field_results["title"].confidence)
        
        self.assertEqual(enhanced_results["location"].value, "Enhanced Location")
        self.assertEqual(enhanced_results["location"].source, "llm_enhancement")
        
        # Check that high-confidence fields were preserved
        self.assertEqual(enhanced_results["start_datetime"].value, field_results["start_datetime"].value)
        self.assertEqual(enhanced_results["start_datetime"].source, "regex")


if __name__ == '__main__':
    unittest.main()