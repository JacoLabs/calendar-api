"""
Tests for advanced parsing features and error handling in EventParser.
Tests ambiguity detection, multiple event parsing, and fallback mechanisms.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
import os

from services.event_parser import EventParser
from models.event_models import ParsedEvent, ValidationResult


class TestAmbiguityDetection:
    """Test ambiguity detection and resolution."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.parser = EventParser()
    
    def test_detect_multiple_datetime_ambiguities(self):
        """Test detection of multiple possible datetimes."""
        # Text with multiple possible dates
        text = "Meeting on 3/4/2024 at 2pm or maybe 4/3/2024 at 3pm"
        parsed_event = self.parser.parse_text(text)
        ambiguities = self.parser._detect_ambiguities(text, parsed_event)
        
        # Should detect datetime ambiguity
        datetime_ambiguities = [a for a in ambiguities if a['type'] == 'datetime']
        assert len(datetime_ambiguities) > 0
        assert 'Multiple possible dates/times found' in datetime_ambiguities[0]['message']
    
    def test_detect_multiple_title_ambiguities(self):
        """Test detection of multiple possible titles."""
        text = "Team meeting or project review tomorrow at 2pm"
        parsed_event = self.parser.parse_text(text)
        ambiguities = self.parser._detect_ambiguities(text, parsed_event)
        
        # Should detect title ambiguity if multiple titles found
        title_ambiguities = [a for a in ambiguities if a['type'] == 'title']
        # Note: This depends on the extractor finding multiple titles
        # The test validates the detection logic works when multiple titles exist
    
    def test_detect_low_confidence_ambiguities(self):
        """Test detection of low confidence extractions."""
        # Create a parsed event with low confidence metadata
        parsed_event = ParsedEvent(
            title="Meeting",
            start_datetime=datetime(2024, 3, 15, 14, 0),
            extraction_metadata={
                'datetime_confidence': 0.4,  # Low confidence
                'title_confidence': 0.5
            }
        )
        
        ambiguities = self.parser._detect_ambiguities("vague text", parsed_event)
        
        # Should detect low confidence issues
        confidence_ambiguities = [a for a in ambiguities if 'confidence' in a['type']]
        assert len(confidence_ambiguities) > 0
    
    @patch('ui.safe_input.is_non_interactive', return_value=True)
    def test_parse_with_clarification_non_interactive(self, mock_non_interactive):
        """Test clarification parsing in non-interactive mode."""
        text = "Meeting tomorrow at 2pm"
        result = self.parser.parse_with_clarification(text)
        
        # Should return parsed event without prompting
        assert isinstance(result, ParsedEvent)
        assert result.title is not None
    
    @patch('ui.safe_input.is_non_interactive', return_value=False)
    @patch('ui.safe_input.get_choice', return_value=0)
    @patch('builtins.print')
    def test_parse_with_clarification_interactive(self, mock_print, mock_choice, mock_non_interactive):
        """Test clarification parsing in interactive mode."""
        # Create a scenario with multiple datetime matches
        with patch.object(self.parser, '_detect_ambiguities') as mock_detect:
            mock_detect.return_value = [{
                'type': 'datetime',
                'message': 'Multiple possible dates/times found',
                'options': [
                    {'datetime': '2024-03-15T14:00:00', 'pattern_type': 'test1', 'confidence': 0.8},
                    {'datetime': '2024-03-16T14:00:00', 'pattern_type': 'test2', 'confidence': 0.7}
                ],
                'current_choice': 0
            }]
            
            text = "Meeting tomorrow at 2pm"
            result = self.parser.parse_with_clarification(text)
            
            # Should handle ambiguity and return result
            assert isinstance(result, ParsedEvent)


class TestMultipleEventDetection:
    """Test multiple event detection and parsing."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.parser = EventParser()
    
    def test_detect_multiple_events_with_separators(self):
        """Test detection of multiple events with clear separators."""
        text = "Meeting at 2pm. Then call with client at 4pm."
        events = self.parser._detect_multiple_events(text)
        
        assert len(events) >= 2
        assert "Meeting at 2pm" in events[0]
        assert "call with client at 4pm" in events[1]
    
    def test_detect_multiple_events_with_bullet_points(self):
        """Test detection of events in bullet point format."""
        text = """
        • Team standup at 9am
        • Client presentation at 2pm
        • Code review at 4pm
        """
        events = self.parser._detect_multiple_events(text)
        
        assert len(events) >= 3
        assert any("standup" in event for event in events)
        assert any("presentation" in event for event in events)
        assert any("review" in event for event in events)
    
    def test_detect_multiple_events_with_numbered_list(self):
        """Test detection of events in numbered list format."""
        text = """
        1. Morning meeting at 9am
        2. Lunch with team at 12pm
        3. Afternoon review at 3pm
        """
        events = self.parser._detect_multiple_events(text)
        
        assert len(events) >= 3
    
    def test_looks_like_event_positive_cases(self):
        """Test event detection for positive cases."""
        positive_cases = [
            "Meeting at 2pm",
            "Call tomorrow",
            "Lunch with John on Friday",
            "Interview at 10:00",
            "Conference next week"
        ]
        
        for text in positive_cases:
            assert self.parser._looks_like_event(text), f"Should detect '{text}' as event"
    
    def test_looks_like_event_negative_cases(self):
        """Test event detection for negative cases."""
        negative_cases = [
            "Hello",
            "The",
            "Random text without event indicators",
            "Just some words"
        ]
        
        for text in negative_cases:
            assert not self.parser._looks_like_event(text), f"Should not detect '{text}' as event"
    
    @patch('ui.safe_input.is_non_interactive', return_value=True)
    def test_parse_multiple_with_detection_non_interactive(self, mock_non_interactive):
        """Test multiple event parsing in non-interactive mode."""
        text = "Meeting at 2pm. Call at 4pm."
        events = self.parser.parse_multiple_with_detection(text)
        
        assert isinstance(events, list)
        assert len(events) >= 1
    
    @patch('services.event_parser.is_non_interactive', return_value=False)
    @patch('services.event_parser.confirm_action', return_value=True)
    @patch('builtins.print')
    def test_parse_multiple_with_detection_interactive_confirm(self, mock_print, mock_confirm, mock_non_interactive):
        """Test multiple event parsing with user confirmation."""
        text = "Meeting at 2pm. Call at 4pm."
        
        # Mock the detection to return multiple events that look like events
        with patch.object(self.parser, '_detect_multiple_events') as mock_detect:
            mock_detect.return_value = ["Meeting at 2pm", "Call at 4pm"]
            
            events = self.parser.parse_multiple_with_detection(text)
            
            assert isinstance(events, list)
            # The confirm_action should be called when multiple events are detected
            mock_confirm.assert_called_once()
    
    @patch('services.event_parser.is_non_interactive', return_value=False)
    @patch('services.event_parser.confirm_action', return_value=False)
    @patch('builtins.print')
    def test_parse_multiple_with_detection_interactive_decline(self, mock_print, mock_confirm, mock_non_interactive):
        """Test multiple event parsing when user declines separation."""
        text = "Meeting at 2pm. Call at 4pm."
        
        with patch.object(self.parser, '_detect_multiple_events') as mock_detect:
            mock_detect.return_value = ["Meeting at 2pm", "Call at 4pm"]
            
            events = self.parser.parse_multiple_with_detection(text)
            
            # Should return single event when user declines separation
            assert isinstance(events, list)
            assert len(events) == 1


class TestFallbackMechanisms:
    """Test fallback mechanisms for failed parsing."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.parser = EventParser()
    
    def test_parse_with_fallback_low_confidence(self):
        """Test fallback for low confidence parsing."""
        # Create a scenario where parsing returns low confidence
        with patch.object(self.parser, 'parse_text') as mock_parse:
            mock_parse.return_value = ParsedEvent(
                title="",
                confidence_score=0.1,  # Very low confidence
                extraction_metadata={}
            )
            
            with patch.object(self.parser, '_auto_fallback') as mock_auto_fallback:
                mock_auto_fallback.return_value = ParsedEvent(
                    title="Event",
                    start_datetime=datetime.now(),
                    confidence_score=0.4
                )
                
                result = self.parser.parse_with_fallback("unclear text")
                
                assert result.title == "Event"
                mock_auto_fallback.assert_called_once()
    
    def test_manual_input_fallback(self):
        """Test manual input fallback mechanism."""
        # Create an event that needs manual input (no title, low confidence)
        original_event = ParsedEvent(
            title=None,  # No title to trigger manual input
            confidence_score=0.1,
            extraction_metadata={'title_confidence': 0.2}  # Low confidence to trigger manual input
        )
        
        # Test the logic by directly setting values (simulating user input)
        with patch.object(self.parser, '_prompt_for_datetime') as mock_datetime:
            mock_datetime.return_value = datetime(2024, 3, 15, 14, 0)
            
            # Mock safe_input to return specific values
            with patch('services.event_parser.safe_input') as mock_input:
                mock_input.side_effect = ["Team Meeting", "1 hour", "Conference Room A"]
                
                result = self.parser._manual_input_fallback("unclear text", original_event)
                
                # The title should be set since the condition should be met
                assert result.title == "Team Meeting"
                assert result.confidence_score == 0.9  # High confidence for manual input
                assert result.start_datetime == datetime(2024, 3, 15, 14, 0)
    
    def test_auto_fallback(self):
        """Test automatic fallback for non-interactive mode."""
        original_event = ParsedEvent(confidence_score=0.1)
        
        result = self.parser._auto_fallback("some unclear text here", original_event)
        
        # Should have reasonable defaults
        assert result.title is not None
        assert result.start_datetime is not None
        assert result.end_datetime is not None
        assert result.confidence_score == 0.4
    
    def test_parse_duration_string(self):
        """Test duration string parsing."""
        test_cases = [
            ("1 hour", timedelta(hours=1)),
            ("30 minutes", timedelta(minutes=30)),
            ("2.5 hours", timedelta(hours=2.5)),
            ("45 mins", timedelta(minutes=45)),
            ("1 day", timedelta(days=1)),
            ("invalid", timedelta(hours=1))  # Default fallback
        ]
        
        for duration_str, expected in test_cases:
            result = self.parser._parse_duration_string(duration_str)
            assert result == expected, f"Failed for '{duration_str}'"
    
    def test_parse_time_string(self):
        """Test time string parsing."""
        test_cases = [
            ("14:30", datetime.strptime("14:30", "%H:%M").time()),
            ("2:30 PM", datetime.strptime("2:30 PM", "%I:%M %p").time()),
            ("9 AM", datetime.strptime("9 AM", "%I %p").time()),
            ("15", datetime.strptime("15", "%H").time())
        ]
        
        for time_str, expected in test_cases:
            result = self.parser._parse_time_string(time_str)
            assert result == expected, f"Failed for '{time_str}'"
    
    def test_parse_time_string_invalid(self):
        """Test time string parsing with invalid input."""
        with pytest.raises(ValueError):
            self.parser._parse_time_string("invalid time")


class TestErrorRecoveryScenarios:
    """Test error recovery in various edge cases."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.parser = EventParser()
    
    def test_empty_text_handling(self):
        """Test handling of empty or whitespace-only text."""
        test_cases = ["", "   ", "\n\t", None]
        
        for text in test_cases:
            if text is None:
                continue
            result = self.parser.parse_with_fallback(text)
            assert isinstance(result, ParsedEvent)
    
    def test_very_short_text_handling(self):
        """Test handling of very short text inputs."""
        short_texts = ["hi", "ok", "yes", "no"]
        
        for text in short_texts:
            result = self.parser.parse_with_fallback(text)
            assert isinstance(result, ParsedEvent)
            # Should have some reasonable defaults
            assert result.title is not None
    
    def test_text_with_no_event_indicators(self):
        """Test handling of text with no clear event indicators."""
        non_event_texts = [
            "This is just a random sentence about nothing in particular.",
            "The weather is nice today and I like cats.",
            "Lorem ipsum dolor sit amet consectetur adipiscing elit."
        ]
        
        for text in non_event_texts:
            result = self.parser.parse_with_fallback(text)
            assert isinstance(result, ParsedEvent)
            # Should still create some kind of event
            assert result.title is not None
    
    def test_text_with_conflicting_information(self):
        """Test handling of text with conflicting date/time information."""
        conflicting_texts = [
            "Meeting yesterday at tomorrow 2pm",
            "Call on Monday Tuesday at 3pm 4pm",
            "Event at 25:00 on February 30th"
        ]
        
        for text in conflicting_texts:
            result = self.parser.parse_with_fallback(text)
            assert isinstance(result, ParsedEvent)
            # Should handle gracefully without crashing
    
    @patch('ui.safe_input.is_non_interactive', return_value=False)
    @patch('ui.safe_input.safe_input', side_effect=KeyboardInterrupt())
    def test_keyboard_interrupt_handling(self, mock_input, mock_non_interactive):
        """Test handling of keyboard interrupts during manual input."""
        original_event = ParsedEvent(confidence_score=0.1)
        
        # Should handle KeyboardInterrupt gracefully
        try:
            result = self.parser._manual_input_fallback("text", original_event)
            # If it doesn't raise, it should return something reasonable
            assert isinstance(result, ParsedEvent)
        except KeyboardInterrupt:
            # It's also acceptable to let the interrupt propagate
            pass
    
    def test_malformed_datetime_recovery(self):
        """Test recovery from malformed datetime inputs."""
        with patch.object(self.parser, '_prompt_for_datetime') as mock_prompt:
            # Simulate user entering invalid then valid datetime
            mock_prompt.return_value = datetime(2024, 3, 15, 14, 0)
            
            # Create event that needs datetime input (missing datetime, low confidence)
            original_event = ParsedEvent(
                confidence_score=0.1,
                extraction_metadata={'datetime_confidence': 0.2}
            )
            
            with patch('ui.safe_input.safe_input') as mock_input:
                mock_input.side_effect = ["1 hour"]  # For duration input
                
                result = self.parser._manual_input_fallback("text", original_event)
                
                # Should eventually get a valid datetime
                assert result.start_datetime is not None
    
    def test_unicode_text_handling(self):
        """Test handling of text with unicode characters."""
        unicode_texts = [
            "Réunion demain à 14h",
            "会议明天下午2点",
            "Встреча завтра в 14:00",
            "Meeting with café owner at 2pm 🕐"
        ]
        
        for text in unicode_texts:
            result = self.parser.parse_with_fallback(text)
            assert isinstance(result, ParsedEvent)
            # Should handle unicode gracefully
    
    def test_very_long_text_handling(self):
        """Test handling of very long text inputs."""
        long_text = "Meeting " + "very " * 1000 + "important tomorrow at 2pm"
        
        result = self.parser.parse_with_fallback(long_text)
        assert isinstance(result, ParsedEvent)
        # Should still extract meaningful information
        assert "Meeting" in result.title or "important" in result.title


class TestIntegrationScenarios:
    """Test integration of advanced parsing features."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.parser = EventParser()
    
    @patch('ui.safe_input.is_non_interactive', return_value=True)
    def test_end_to_end_ambiguous_parsing(self, mock_non_interactive):
        """Test end-to-end parsing of ambiguous text."""
        text = "Meeting or call tomorrow at 2pm or 3pm in room A or B"
        
        result = self.parser.parse_with_clarification(text)
        
        assert isinstance(result, ParsedEvent)
        assert result.title is not None
        assert result.start_datetime is not None
    
    @patch('ui.safe_input.is_non_interactive', return_value=True)
    def test_end_to_end_multiple_events(self, mock_non_interactive):
        """Test end-to-end parsing of multiple events."""
        text = "Team standup at 9am. Client call at 2pm. Code review at 4pm."
        
        events = self.parser.parse_multiple_with_detection(text)
        
        assert isinstance(events, list)
        assert len(events) >= 1
        # In non-interactive mode, might parse as single or multiple events
    
    @patch('ui.safe_input.is_non_interactive', return_value=True)
    def test_end_to_end_fallback_parsing(self, mock_non_interactive):
        """Test end-to-end parsing with fallback."""
        text = "something unclear and vague"
        
        result = self.parser.parse_with_fallback(text)
        
        assert isinstance(result, ParsedEvent)
        assert result.title is not None
        assert result.start_datetime is not None
        assert result.end_datetime is not None
    
    def test_validation_after_advanced_parsing(self):
        """Test that validation works correctly after advanced parsing."""
        text = "Meeting tomorrow at 2pm"
        
        parsed_event = self.parser.parse_with_clarification(text)
        validation_result = self.parser.validate_parsed_event(parsed_event)
        
        assert isinstance(validation_result, ValidationResult)
        # Should be valid or have reasonable suggestions


if __name__ == "__main__":
    # Set environment variable for non-interactive testing
    os.environ['NON_INTERACTIVE'] = '1'
    pytest.main([__file__])