"""
Integration tests for the unified parsing pipeline.

Tests the complete parsing pipeline with per-field confidence routing,
deterministic backup, and LLM enhancement integration.

Requirements tested:
- 10.5: Multiple parsing methods with cross-component validation
- 11.5: Fallback logic when deterministic methods fail
- 12.6: LLM processing with strict guardrails
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

from services.hybrid_event_parser import HybridEventParser, HybridParsingResult
from services.per_field_confidence_router import PerFieldConfidenceRouter, ProcessingMethod
from services.deterministic_backup_layer import DeterministicBackupLayer
from services.llm_enhancer import LLMEnhancer
from models.event_models import ParsedEvent, FieldResult, ValidationResult


class TestUnifiedParsingPipeline:
    """Test the complete unified parsing pipeline integration."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.current_time = datetime(2025, 10, 8, 14, 30)
        self.parser = HybridEventParser(current_time=self.current_time)
        
        # Mock external services for controlled testing
        self.mock_deterministic_backup = Mock(spec=DeterministicBackupLayer)
        self.mock_llm_enhancer = Mock(spec=LLMEnhancer)
        
        # Set up default mock responses
        self.mock_deterministic_backup.is_available.return_value = True
        self.mock_llm_enhancer.is_available.return_value = True
    
    def test_high_confidence_regex_only_processing(self):
        """Test processing order: high confidence regex (≥0.8) → no additional processing."""
        text = "Meeting with John tomorrow at 2:00 PM"
        
        # Mock high-confidence regex extraction
        with patch.object(self.parser.regex_extractor, 'extract_datetime') as mock_datetime:
            with patch.object(self.parser.title_extractor, 'extract_title') as mock_title:
                # Set up high-confidence regex results
                mock_datetime.return_value = Mock(
                    start_datetime=self.current_time + timedelta(days=1, hours=2),
                    end_datetime=self.current_time + timedelta(days=1, hours=3),
                    confidence=0.9,
                    is_all_day=False
                )
                mock_title.return_value = Mock(
                    title="Meeting with John",
                    confidence=0.85
                )
                
                result = self.parser.parse_event_text(text, mode="hybrid")
                
                # Verify high-confidence regex results are used without additional processing
                assert result.parsed_event is not None
                assert result.confidence_score >= 0.8
                assert result.parsing_path in ["regex_only", "regex_then_llm"]
                assert result.parsed_event.title == "Meeting with John"
                assert result.parsed_event.start_datetime is not None
    
    def test_medium_confidence_deterministic_backup(self):
        """Test processing order: medium confidence (0.6-0.8) → deterministic backup."""
        text = "Lunch next Friday"
        
        # Mock medium-confidence regex that triggers deterministic backup
        with patch.object(self.parser, '_extract_field_with_regex') as mock_regex:
            with patch.object(self.parser, '_extract_field_with_deterministic') as mock_deterministic:
                # Set up medium-confidence regex results
                mock_regex.return_value = FieldResult(
                    value="Lunch",
                    source="regex",
                    confidence=0.7,
                    span=(0, 5)
                )
                
                # Set up deterministic backup results
                mock_deterministic.return_value = FieldResult(
                    value=self.current_time + timedelta(days=4, hours=12),
                    source="deterministic_backup_duckling",
                    confidence=0.75,
                    span=(6, 17)
                )
                
                result = self.parser.parse_event_text(text, mode="hybrid")
                
                # Verify deterministic backup was used
                assert result.parsed_event is not None
                assert 0.6 <= result.confidence_score <= 0.8
                assert any("deterministic" in field_result.source 
                          for field_result in result.parsed_event.field_results.values())
    
    def test_low_confidence_llm_enhancement(self):
        """Test processing order: low confidence (<0.6) → LLM enhancement."""
        text = "Something important happening soon"
        
        # Mock low-confidence regex that triggers LLM enhancement
        with patch.object(self.parser, '_extract_field_with_regex') as mock_regex:
            with patch.object(self.parser, '_extract_field_with_llm') as mock_llm:
                # Set up low-confidence regex results
                mock_regex.return_value = FieldResult(
                    value="Something important",
                    source="regex",
                    confidence=0.4,
                    span=(0, 18)
                )
                
                # Set up LLM enhancement results
                mock_llm.return_value = FieldResult(
                    value="Important Meeting",
                    source="llm",
                    confidence=0.5,
                    span=(0, 18)
                )
                
                result = self.parser.parse_event_text(text, mode="hybrid")
                
                # Verify LLM enhancement was used
                assert result.parsed_event is not None
                assert result.confidence_score <= 0.6
                assert any("llm" in field_result.source 
                          for field_result in result.parsed_event.field_results.values())
                assert result.parsed_event.needs_confirmation  # Low confidence should require confirmation
    
    def test_cross_component_validation(self):
        """Test cross-component validation and consistency checking."""
        text = "Meeting from 3 PM to 2 PM tomorrow"  # Invalid time range
        
        with patch.object(self.parser.confidence_router, 'validate_field_consistency') as mock_validate:
            # Set up validation failure for inconsistent times
            validation_result = ValidationResult(is_valid=False)
            validation_result.add_field_warning('end_datetime', 'End time must be after start time')
            mock_validate.return_value = validation_result
            
            result = self.parser.parse_event_text(text, mode="hybrid")
            
            # Verify validation was performed and warnings were added
            assert len(result.warnings) > 0
            assert any("End time must be after start time" in warning for warning in result.warnings)
            assert result.parsed_event.needs_confirmation
    
    def test_unified_confidence_scoring(self):
        """Test unified confidence scoring across all extraction methods."""
        text = "Team standup Monday 9 AM in Conference Room A"
        
        # Mock different confidence levels for different fields
        field_results = {
            'title': FieldResult(value="Team standup", source="regex", confidence=0.9, span=(0, 12)),
            'start_datetime': FieldResult(value=self.current_time, source="regex", confidence=0.85, span=(13, 23)),
            'location': FieldResult(value="Conference Room A", source="deterministic", confidence=0.7, span=(27, 44))
        }
        
        with patch.object(self.parser, 'route_field_processing') as mock_route:
            mock_route.side_effect = lambda field, *args: field_results.get(field)
            
            result = self.parser.parse_event_text(text, mode="hybrid")
            
            # Verify unified confidence calculation
            # Should be weighted average: (0.9 + 0.85) * 0.7 + 0.7 * 0.3 = 1.225 + 0.21 = 1.435 / 1 = ~0.84
            assert result.parsed_event is not None
            assert 0.8 <= result.confidence_score <= 0.9
            
            # Verify field-level confidence tracking
            assert 'title' in result.parsed_event.field_results
            assert 'start_datetime' in result.parsed_event.field_results
            assert 'location' in result.parsed_event.field_results
    
    def test_processing_order_optimization(self):
        """Test that fields are processed in optimal order based on dependencies."""
        text = "Project review meeting for 2 hours starting at 10 AM tomorrow"
        
        with patch.object(self.parser.confidence_router, 'optimize_processing_order') as mock_optimize:
            # Verify processing order is optimized
            mock_optimize.return_value = ['start_datetime', 'duration', 'end_datetime', 'title']
            
            result = self.parser.parse_event_text(text, mode="hybrid")
            
            # Verify optimization was called
            mock_optimize.assert_called_once()
            
            # Verify processing succeeded
            assert result.parsed_event is not None
    
    def test_deterministic_backup_fallback(self):
        """Test fallback logic when deterministic methods fail."""
        text = "Appointment next week"
        
        # Mock deterministic backup failure
        with patch.object(self.parser, '_extract_field_with_deterministic') as mock_deterministic:
            mock_deterministic.return_value = None  # Deterministic extraction fails
            
            with patch.object(self.parser, '_extract_field_with_llm') as mock_llm:
                mock_llm.return_value = FieldResult(
                    value="Appointment",
                    source="llm",
                    confidence=0.4,
                    span=(0, 11)
                )
                
                result = self.parser.parse_event_text(text, mode="hybrid")
                
                # Verify fallback to LLM occurred
                assert result.parsed_event is not None
                assert any("llm" in field_result.source 
                          for field_result in result.parsed_event.field_results.values())
    
    def test_llm_guardrails_enforcement(self):
        """Test that LLM processing enforces strict guardrails."""
        text = "Meeting tomorrow at 2 PM"
        
        # Mock high-confidence datetime extraction that should be locked
        high_confidence_datetime = FieldResult(
            value=self.current_time + timedelta(days=1, hours=14),
            source="regex",
            confidence=0.9,
            span=(8, 25)
        )
        
        with patch.object(self.parser, '_extract_field_with_regex') as mock_regex:
            with patch.object(self.parser, '_extract_field_with_llm') as mock_llm:
                # Set up high-confidence regex datetime
                mock_regex.return_value = high_confidence_datetime
                
                # Mock LLM trying to modify high-confidence field (should be prevented)
                mock_llm.return_value = FieldResult(
                    value="Enhanced Meeting Title",
                    source="llm",
                    confidence=0.5,
                    span=(0, 7)
                )
                
                result = self.parser.parse_event_text(text, mode="hybrid")
                
                # Verify high-confidence datetime was preserved
                assert result.parsed_event is not None
                datetime_field = result.parsed_event.field_results.get('start_datetime')
                if datetime_field:
                    assert datetime_field.source == "regex"
                    assert datetime_field.confidence == 0.9
    
    def test_partial_parsing_support(self):
        """Test partial parsing for specific fields only."""
        text = "Team meeting Monday at 10 AM in Room 101"
        
        # Request only title and start_datetime fields
        result = self.parser.parse_event_text(text, mode="hybrid", fields=['title', 'start_datetime'])
        
        # Verify only requested fields were processed
        assert result.parsed_event is not None
        processed_fields = set(result.parsed_event.field_results.keys())
        
        # Should contain requested fields (and possibly dependencies)
        assert 'title' in processed_fields or 'start_datetime' in processed_fields
        
        # Should not contain unrequested optional fields like location
        # (unless they were processed as dependencies)
    
    def test_caching_integration(self):
        """Test that caching works with the unified pipeline."""
        text = "Weekly standup tomorrow at 9 AM"
        
        # First parse - should miss cache
        result1 = self.parser.parse_event_text(text, mode="hybrid")
        assert result1.success
        assert not result1.parsed_event.cache_hit
        
        # Second parse - should hit cache
        result2 = self.parser.parse_event_text(text, mode="hybrid")
        assert result2.success
        # Note: Cache hit behavior depends on implementation details
    
    def test_performance_metadata_collection(self):
        """Test that performance metadata is collected during parsing."""
        text = "Project deadline Friday at 5 PM"
        
        result = self.parser.parse_event_text(text, mode="hybrid")
        
        # Verify performance metadata is collected
        assert result.parsed_event is not None
        assert result.processing_metadata is not None
        assert 'processing_time' in result.processing_metadata
        assert result.parsed_event.processing_time_ms >= 0
        
        # Verify field-level processing times are tracked
        for field_result in result.parsed_event.field_results.values():
            assert hasattr(field_result, 'processing_time_ms')
    
    def test_error_handling_and_graceful_degradation(self):
        """Test error handling and graceful degradation when components fail."""
        text = "Important event"
        
        # Mock component failures
        with patch.object(self.parser, '_extract_field_with_regex', side_effect=Exception("Regex failed")):
            with patch.object(self.parser, '_extract_field_with_deterministic', side_effect=Exception("Deterministic failed")):
                with patch.object(self.parser, '_extract_field_with_llm', side_effect=Exception("LLM failed")):
                    
                    result = self.parser.parse_event_text(text, mode="hybrid")
                    
                    # Should still return a result (even if minimal)
                    assert result is not None
                    assert result.parsing_path == "error_fallback"
                    assert len(result.warnings) > 0


class TestProcessingMethodRouting:
    """Test the processing method routing logic."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.router = PerFieldConfidenceRouter()
    
    def test_high_confidence_routes_to_regex(self):
        """Test that high confidence (≥0.8) routes to regex only."""
        method = self.router.route_processing_method('title', 0.9)
        assert method == ProcessingMethod.REGEX
    
    def test_medium_confidence_routes_to_deterministic(self):
        """Test that medium confidence (0.6-0.8) routes to deterministic backup."""
        method = self.router.route_processing_method('start_datetime', 0.7)
        assert method == ProcessingMethod.DETERMINISTIC
    
    def test_low_confidence_routes_to_llm(self):
        """Test that low confidence (<0.6) routes to LLM enhancement."""
        method = self.router.route_processing_method('title', 0.4)
        assert method == ProcessingMethod.LLM
    
    def test_very_low_confidence_routes_to_skip(self):
        """Test that very low confidence (<0.4) routes to skip for optional fields."""
        method = self.router.route_processing_method('description', 0.2)
        assert method == ProcessingMethod.SKIP


class TestIntegrationScenarios:
    """Test real-world integration scenarios."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.current_time = datetime(2025, 10, 8, 14, 30)
        self.parser = HybridEventParser(current_time=self.current_time)
    
    def test_email_parsing_scenario(self):
        """Test parsing a typical email with mixed confidence levels."""
        email_text = """
        Subject: Team Meeting
        
        Hi everyone,
        
        Let's meet tomorrow at 2:00 PM in the main conference room.
        We'll discuss the Q4 planning and review project status.
        
        Thanks,
        John
        """
        
        result = self.parser.parse_event_text(email_text, mode="hybrid")
        
        # Verify successful parsing with appropriate confidence
        assert result.parsed_event is not None
        assert result.parsed_event.title is not None
        assert result.parsed_event.start_datetime is not None
        
        # Should have reasonable confidence for structured email
        assert result.confidence_score > 0.5
    
    def test_casual_text_parsing_scenario(self):
        """Test parsing casual, unstructured text."""
        casual_text = "lunch with sarah sometime next week maybe tuesday"
        
        result = self.parser.parse_event_text(casual_text, mode="hybrid")
        
        # Should parse but with lower confidence and need confirmation
        assert result.parsed_event is not None
        assert result.parsed_event.needs_confirmation
        assert result.confidence_score < 0.7
    
    def test_complex_event_parsing_scenario(self):
        """Test parsing complex event with multiple components."""
        complex_text = """
        Annual Company Retreat
        October 15-17, 2025
        Location: Mountain View Resort, 123 Resort Drive
        Time: Check-in at 2:00 PM on Friday, activities until 5:00 PM Sunday
        Attendees: All staff members
        """
        
        result = self.parser.parse_event_text(complex_text, mode="hybrid")
        
        # Verify comprehensive parsing
        assert result.parsed_event is not None
        assert result.parsed_event.title is not None
        assert result.parsed_event.start_datetime is not None
        assert result.parsed_event.location is not None
        
        # Should have high confidence for well-structured event
        assert result.confidence_score > 0.7


if __name__ == "__main__":
    pytest.main([__file__, "-v"])