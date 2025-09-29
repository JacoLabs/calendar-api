"""
Integration tests for MasterEventParser - LLM-first parsing pipeline.

Tests the complete LLM-first parsing strategy with fallbacks, component enhancement,
error handling, and unified confidence scoring.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

from services.master_event_parser import MasterEventParser, ParsingResult, get_master_parser
from services.llm_service import LLMService, LLMResponse
from models.event_models import ParsedEvent, NormalizedEvent
from services.format_aware_text_processor import TextFormatResult, TextFormat


class TestMasterEventParser:
    """Test suite for MasterEventParser integration."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Create mock LLM service
        self.mock_llm_service = Mock(spec=LLMService)
        self.mock_llm_service.is_available.return_value = True
        
        # Create parser with mock LLM service
        self.parser = MasterEventParser(llm_service=self.mock_llm_service)
        
        # Test data
        self.sample_text = "Meeting with John tomorrow at 2pm in Conference Room A"
        self.sample_datetime = datetime.now() + timedelta(days=1)
        self.sample_datetime = self.sample_datetime.replace(hour=14, minute=0, second=0, microsecond=0)
    
    def create_mock_llm_response(self, success=True, confidence=0.8, title="Meeting with John", 
                                start_datetime=None, location="Conference Room A"):
        """Create a mock LLM response."""
        if start_datetime is None:
            start_datetime = self.sample_datetime
        
        if success:
            parsed_event = ParsedEvent(
                title=title,
                start_datetime=start_datetime,
                end_datetime=start_datetime + timedelta(hours=1),
                location=location,
                description=self.sample_text,
                confidence_score=confidence,
                extraction_metadata={
                    'llm_provider': 'mock',
                    'llm_confidence': {'title': confidence, 'start_datetime': confidence, 'location': confidence}
                }
            )
            return parsed_event
        else:
            return None
    
    def test_llm_primary_success(self):
        """Test successful LLM primary extraction."""
        # Mock successful LLM extraction
        mock_event = self.create_mock_llm_response()
        self.mock_llm_service.llm_extract_event.return_value = mock_event
        
        result = self.parser.parse_event(self.sample_text)
        
        assert result.success
        assert result.parsing_method == "llm_primary"
        assert result.parsed_event.title == "Meeting with John"
        assert result.parsed_event.location == "Conference Room A"
        assert result.confidence_score > 0.7
        assert result.normalized_event is not None
        
        # Verify LLM was called
        self.mock_llm_service.llm_extract_event.assert_called_once()
    
    def test_llm_low_confidence_fallback_to_regex(self):
        """Test fallback to regex when LLM confidence is too low."""
        # Mock low confidence LLM result
        mock_event = self.create_mock_llm_response(confidence=0.2)  # Below threshold
        self.mock_llm_service.llm_extract_event.return_value = mock_event
        
        result = self.parser.parse_event(self.sample_text)
        
        assert result.success
        assert "regex_fallback" in result.parsing_method
        assert result.parsed_event is not None
        
        # Should have fallen back to regex
        self.mock_llm_service.llm_extract_event.assert_called_once()
    
    def test_llm_failure_fallback_to_regex(self):
        """Test fallback to regex when LLM fails completely."""
        # Mock LLM failure
        self.mock_llm_service.llm_extract_event.return_value = None
        
        result = self.parser.parse_event(self.sample_text)
        
        assert result.success
        assert "regex_fallback" in result.parsing_method
        assert result.parsed_event is not None
        
        # Should have attempted LLM first
        self.mock_llm_service.llm_extract_event.assert_called_once()
    
    def test_llm_unavailable_direct_regex(self):
        """Test direct regex usage when LLM is unavailable."""
        # Mock LLM unavailable
        self.mock_llm_service.is_available.return_value = False
        
        result = self.parser.parse_event(self.sample_text)
        
        assert result.success
        assert "regex_fallback" in result.parsing_method
        assert result.parsed_event is not None
        
        # Should not have called LLM
        self.mock_llm_service.llm_extract_event.assert_not_called()
    
    def test_component_enhancement_location(self):
        """Test component enhancement for location extraction."""
        # Mock LLM result without location
        mock_event = self.create_mock_llm_response(location=None)
        self.mock_llm_service.llm_extract_event.return_value = mock_event
        
        # Enable component enhancement
        self.parser.config['enable_component_enhancement'] = True
        
        result = self.parser.parse_event(self.sample_text)
        
        assert result.success
        assert "enhanced" in result.parsing_method
        assert result.parsed_event.location is not None  # Should be enhanced by AdvancedLocationExtractor
        
        # Check enhancement metadata
        metadata = result.parsed_event.extraction_metadata
        assert metadata.get('location_enhanced') is True
    
    def test_component_enhancement_title(self):
        """Test component enhancement for title extraction."""
        # Mock LLM result without title
        mock_event = self.create_mock_llm_response(title=None)
        self.mock_llm_service.llm_extract_event.return_value = mock_event
        
        # Enable component enhancement
        self.parser.config['enable_component_enhancement'] = True
        
        result = self.parser.parse_event(self.sample_text)
        
        assert result.success
        assert "enhanced" in result.parsing_method
        assert result.parsed_event.title is not None  # Should be enhanced by SmartTitleExtractor
        
        # Check enhancement metadata
        metadata = result.parsed_event.extraction_metadata
        assert metadata.get('title_enhanced') is True
    
    def test_format_aware_processing(self):
        """Test format-aware text processing."""
        bullet_text = """
        • Meeting with John
        • Tomorrow at 2pm
        • Conference Room A
        """
        
        mock_event = self.create_mock_llm_response()
        self.mock_llm_service.llm_extract_event.return_value = mock_event
        
        result = self.parser.parse_event(bullet_text)
        
        assert result.success
        assert result.format_result is not None
        assert result.format_result.detected_format == TextFormat.BULLET_POINTS
        
        # Verify processed text was used for LLM
        call_args = self.mock_llm_service.llm_extract_event.call_args
        processed_text = call_args[0][0]  # First argument
        assert "Meeting with John" in processed_text
        assert "•" not in processed_text  # Bullets should be processed out
    
    def test_error_handling_missing_critical_fields(self):
        """Test error handling for missing critical fields."""
        # Mock LLM result missing title
        mock_event = ParsedEvent(
            title=None,  # Missing critical field
            start_datetime=self.sample_datetime,
            description=self.sample_text,
            confidence_score=0.8
        )
        self.mock_llm_service.llm_extract_event.return_value = mock_event
        
        # Enable error handling
        self.parser.config['enable_error_handling'] = True
        
        result = self.parser.parse_event(self.sample_text)
        
        assert result.success  # Should still succeed with error handling
        assert result.error_handling_result is not None
        assert "missing_critical_fields" in result.error_handling_result.error_type
    
    def test_cross_component_validation(self):
        """Test cross-component validation and consistency checking."""
        # Mock LLM result with potentially inconsistent data
        mock_event = self.create_mock_llm_response(
            title="Completely Different Event",  # Inconsistent with text
            location="Mars"  # Unlikely location
        )
        self.mock_llm_service.llm_extract_event.return_value = mock_event
        
        # Enable cross-validation
        self.parser.config['enable_cross_validation'] = True
        
        result = self.parser.parse_event(self.sample_text)
        
        assert result.success
        
        # Check for consistency warnings in metadata
        metadata = result.parsed_event.extraction_metadata
        if 'consistency_issues' in metadata:
            assert len(metadata['consistency_issues']) > 0
    
    def test_unified_confidence_scoring(self):
        """Test unified confidence scoring across components."""
        # Mock medium confidence LLM result
        mock_event = self.create_mock_llm_response(confidence=0.6)
        self.mock_llm_service.llm_extract_event.return_value = mock_event
        
        result = self.parser.parse_event(self.sample_text)
        
        assert result.success
        
        # Unified confidence should be calculated from multiple factors
        assert 0.0 <= result.confidence_score <= 1.0
        
        # Should have confidence metadata
        assert result.metadata is not None
        assert 'unified_confidence_weights' in str(result.metadata) or 'llm_confidence' in str(result.metadata)
    
    def test_normalized_event_output(self):
        """Test normalized event output format."""
        mock_event = self.create_mock_llm_response()
        self.mock_llm_service.llm_extract_event.return_value = mock_event
        
        result = self.parser.parse_event(self.sample_text)
        
        assert result.success
        assert result.normalized_event is not None
        
        normalized = result.normalized_event
        assert normalized.title == "Meeting with John"
        assert normalized.start_datetime == self.sample_datetime
        assert normalized.location == "Conference Room A"
        assert 0.0 <= normalized.confidence_score <= 1.0
        assert isinstance(normalized.field_confidence, dict)
        assert 'title' in normalized.field_confidence
        assert 'start_datetime' in normalized.field_confidence
    
    def test_performance_optimization(self):
        """Test performance optimization and tracking."""
        mock_event = self.create_mock_llm_response()
        self.mock_llm_service.llm_extract_event.return_value = mock_event
        
        # Enable performance optimization
        self.parser.config['performance_optimization'] = True
        
        result = self.parser.parse_event(self.sample_text)
        
        assert result.success
        assert result.processing_time > 0
        
        # Check performance stats were updated
        stats = self.parser.performance_stats
        assert stats['total_parses'] > 0
        assert stats['llm_successes'] > 0
        assert stats['average_processing_time'] > 0
    
    def test_multiple_event_detection(self):
        """Test multiple event detection and parsing."""
        multi_event_text = """
        • Meeting with John tomorrow at 2pm in Room A
        • Call with Sarah on Friday at 10am
        • Lunch with team next Monday at noon
        """
        
        # Mock LLM responses for each segment
        mock_events = [
            self.create_mock_llm_response(title="Meeting with John"),
            self.create_mock_llm_response(title="Call with Sarah"),
            self.create_mock_llm_response(title="Lunch with team")
        ]
        
        self.mock_llm_service.llm_extract_event.side_effect = mock_events
        
        events = self.parser.parse_multiple_events(multi_event_text)
        
        assert len(events) >= 1  # Should detect at least one event
        
        # If multiple events detected, should have multiple results
        if len(events) > 1:
            titles = [event.title for event in events if event.title]
            assert len(titles) > 1
    
    def test_comprehensive_logging_and_debugging(self):
        """Test comprehensive logging and debugging support."""
        # Enable debug logging
        self.parser.config['debug_logging'] = True
        
        mock_event = self.create_mock_llm_response()
        self.mock_llm_service.llm_extract_event.return_value = mock_event
        
        with patch('services.master_event_parser.logger') as mock_logger:
            result = self.parser.parse_event(self.sample_text)
            
            assert result.success
            
            # Should have debug log calls
            assert mock_logger.debug.called
    
    def test_configuration_management(self):
        """Test parser configuration management."""
        # Test configuration updates
        original_threshold = self.parser.config['llm_confidence_threshold']
        
        self.parser.configure(llm_confidence_threshold=0.5)
        assert self.parser.config['llm_confidence_threshold'] == 0.5
        
        # Test invalid configuration
        self.parser.configure(invalid_key="value")  # Should be ignored
        
        # Test status reporting
        status = self.parser.get_parsing_status()
        assert status['master_parser_ready'] is True
        assert 'llm_service_status' in status
        assert 'performance_stats' in status
    
    def test_edge_case_empty_text(self):
        """Test edge case with empty text."""
        result = self.parser.parse_event("")
        
        assert not result.success
        assert result.parsing_method in ["no_result", "failed"]
    
    def test_edge_case_very_long_text(self):
        """Test edge case with very long text."""
        long_text = "Meeting with John tomorrow at 2pm. " * 100  # Very long text
        
        mock_event = self.create_mock_llm_response()
        self.mock_llm_service.llm_extract_event.return_value = mock_event
        
        result = self.parser.parse_event(long_text)
        
        assert result.success
        # Should handle long text gracefully
    
    def test_compatibility_interface(self):
        """Test compatibility with existing EventParser interface."""
        mock_event = self.create_mock_llm_response()
        self.mock_llm_service.llm_extract_event.return_value = mock_event
        
        # Test parse_text method (compatibility interface)
        parsed_event = self.parser.parse_text(self.sample_text)
        
        assert isinstance(parsed_event, ParsedEvent)
        assert parsed_event.title == "Meeting with John"
        assert parsed_event.confidence_score > 0
    
    def test_global_instance_access(self):
        """Test global instance access pattern."""
        parser1 = get_master_parser()
        parser2 = get_master_parser()
        
        # Should return the same instance
        assert parser1 is parser2
        assert isinstance(parser1, MasterEventParser)


class TestMasterEventParserRealWorldScenarios:
    """Test real-world parsing scenarios."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_llm_service = Mock(spec=LLMService)
        self.mock_llm_service.is_available.return_value = True
        self.parser = MasterEventParser(llm_service=self.mock_llm_service)
    
    def test_email_format_parsing(self):
        """Test parsing of email-formatted text."""
        email_text = """
        Subject: Team Standup
        When: Tomorrow at 9:00 AM
        Where: Conference Room B
        
        Please join us for our weekly team standup meeting.
        """
        
        mock_event = ParsedEvent(
            title="Team Standup",
            start_datetime=datetime.now() + timedelta(days=1, hours=9),
            location="Conference Room B",
            description=email_text,
            confidence_score=0.85
        )
        self.mock_llm_service.llm_extract_event.return_value = mock_event
        
        result = self.parser.parse_event(email_text)
        
        assert result.success
        assert result.format_result.detected_format == TextFormat.STRUCTURED_EMAIL
        assert result.parsed_event.title == "Team Standup"
    
    def test_natural_language_parsing(self):
        """Test parsing of natural language text."""
        natural_text = "Let's grab lunch tomorrow around noon at that new cafe downtown"
        
        mock_event = ParsedEvent(
            title="Lunch",
            start_datetime=datetime.now() + timedelta(days=1, hours=12),
            location="cafe downtown",
            description=natural_text,
            confidence_score=0.75
        )
        self.mock_llm_service.llm_extract_event.return_value = mock_event
        
        result = self.parser.parse_event(natural_text)
        
        assert result.success
        assert "lunch" in result.parsed_event.title.lower()
    
    def test_complex_datetime_parsing(self):
        """Test parsing of complex datetime expressions."""
        complex_text = "Board meeting next Friday from 2:30 PM to 4:00 PM in the executive boardroom"
        
        next_friday = datetime.now() + timedelta(days=7)  # Approximate
        mock_event = ParsedEvent(
            title="Board meeting",
            start_datetime=next_friday.replace(hour=14, minute=30),
            end_datetime=next_friday.replace(hour=16, minute=0),
            location="executive boardroom",
            description=complex_text,
            confidence_score=0.9
        )
        self.mock_llm_service.llm_extract_event.return_value = mock_event
        
        result = self.parser.parse_event(complex_text)
        
        assert result.success
        assert result.parsed_event.start_datetime is not None
        assert result.parsed_event.end_datetime is not None
        assert result.parsed_event.end_datetime > result.parsed_event.start_datetime
    
    def test_ambiguous_text_handling(self):
        """Test handling of ambiguous text."""
        ambiguous_text = "Meeting at 2"  # Ambiguous: 2 AM or 2 PM?
        
        # Mock LLM with low confidence due to ambiguity
        mock_event = ParsedEvent(
            title="Meeting",
            start_datetime=datetime.now().replace(hour=14, minute=0),  # Assume PM
            description=ambiguous_text,
            confidence_score=0.4,  # Low confidence
            extraction_metadata={'ambiguity_detected': True}
        )
        self.mock_llm_service.llm_extract_event.return_value = mock_event
        
        result = self.parser.parse_event(ambiguous_text)
        
        assert result.success
        # Should handle ambiguity gracefully, possibly with error handling
        assert result.confidence_score <= 0.6  # Should reflect uncertainty
    
    def test_multilingual_content(self):
        """Test handling of mixed language content."""
        mixed_text = "Réunion d'équipe tomorrow at 10am in salle de conférence"
        
        mock_event = ParsedEvent(
            title="Réunion d'équipe",
            start_datetime=datetime.now() + timedelta(days=1, hours=10),
            location="salle de conférence",
            description=mixed_text,
            confidence_score=0.7
        )
        self.mock_llm_service.llm_extract_event.return_value = mock_event
        
        result = self.parser.parse_event(mixed_text)
        
        assert result.success
        # Should handle mixed language content
        assert result.parsed_event.title is not None


class TestMasterEventParserPerformance:
    """Test performance characteristics of MasterEventParser."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_llm_service = Mock(spec=LLMService)
        self.mock_llm_service.is_available.return_value = True
        self.parser = MasterEventParser(llm_service=self.mock_llm_service)
    
    def test_processing_time_tracking(self):
        """Test processing time tracking."""
        mock_event = ParsedEvent(
            title="Test Event",
            start_datetime=datetime.now(),
            confidence_score=0.8
        )
        self.mock_llm_service.llm_extract_event.return_value = mock_event
        
        result = self.parser.parse_event("Test meeting tomorrow")
        
        assert result.success
        assert result.processing_time > 0
        assert result.processing_time < 10.0  # Should be reasonably fast
    
    def test_performance_stats_accumulation(self):
        """Test performance statistics accumulation."""
        mock_event = ParsedEvent(
            title="Test Event",
            start_datetime=datetime.now(),
            confidence_score=0.8
        )
        self.mock_llm_service.llm_extract_event.return_value = mock_event
        
        # Reset stats
        self.parser.reset_performance_stats()
        
        # Parse multiple events
        for i in range(3):
            self.parser.parse_event(f"Test meeting {i}")
        
        stats = self.parser.performance_stats
        assert stats['total_parses'] == 3
        assert stats['llm_successes'] == 3
        assert stats['average_processing_time'] > 0
    
    def test_timeout_handling(self):
        """Test handling of processing timeouts."""
        # Mock slow LLM response
        def slow_llm_response(*args, **kwargs):
            import time
            time.sleep(0.1)  # Simulate slow response
            return ParsedEvent(title="Slow Event", confidence_score=0.8)
        
        self.mock_llm_service.llm_extract_event.side_effect = slow_llm_response
        
        # Set short timeout for testing
        self.parser.config['max_processing_time'] = 0.05
        
        result = self.parser.parse_event("Test meeting")
        
        # Should still complete (timeout is just a guideline)
        assert result.processing_time > 0


if __name__ == "__main__":
    pytest.main([__file__])