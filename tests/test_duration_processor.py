"""
Unit tests for DurationProcessor class.

Tests duration calculations, all-day detection, and conflict resolution.
Requirements: 13.2, 13.3, 13.4, 13.6
"""

import pytest
from datetime import datetime, timedelta
from services.duration_processor import DurationProcessor
from models.event_models import DurationResult


class TestDurationProcessor:
    """Test cases for DurationProcessor functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.processor = DurationProcessor()
        self.test_start_time = datetime(2025, 10, 8, 14, 0)  # 2:00 PM
    
    def test_calculate_duration_end_time_hours(self):
        """Test duration calculation with hour expressions."""
        # Test "for 2 hours"
        result = self.processor.calculate_duration_end_time(
            self.test_start_time, "Meeting for 2 hours"
        )
        assert result.duration_minutes == 120
        assert result.confidence == 0.8
        
        # Test "for 1.5 hours"
        result = self.processor.calculate_duration_end_time(
            self.test_start_time, "Workshop for 1.5 hours"
        )
        assert result.duration_minutes == 90
        assert result.confidence == 0.8
        
        # Test "2 hour meeting"
        result = self.processor.calculate_duration_end_time(
            self.test_start_time, "2 hour meeting with team"
        )
        assert result.duration_minutes == 120
        assert result.confidence == 0.8
    
    def test_calculate_duration_end_time_minutes(self):
        """Test duration calculation with minute expressions."""
        # Test "for 30 minutes"
        result = self.processor.calculate_duration_end_time(
            self.test_start_time, "Call for 30 minutes"
        )
        assert result.duration_minutes == 30
        assert result.confidence == 0.8
        
        # Test "45 minute session"
        result = self.processor.calculate_duration_end_time(
            self.test_start_time, "45 minute training session"
        )
        assert result.duration_minutes == 45
        assert result.confidence == 0.8
        
        # Test "lasting 90 minutes"
        result = self.processor.calculate_duration_end_time(
            self.test_start_time, "Event lasting 90 minutes"
        )
        assert result.duration_minutes == 90
        assert result.confidence == 0.8
    
    def test_calculate_duration_end_time_edge_cases(self):
        """Test duration calculation edge cases."""
        # Test very short duration (should lower confidence)
        result = self.processor.calculate_duration_end_time(
            self.test_start_time, "Quick 2 minute call"
        )
        assert result.duration_minutes == 2
        assert result.confidence < 0.8  # Lowered confidence for unusual duration
        
        # Test very long duration (should lower confidence)
        result = self.processor.calculate_duration_end_time(
            self.test_start_time, "All day 25 hour marathon"
        )
        assert result.duration_minutes == 1500  # 25 hours
        assert result.confidence < 0.8  # Lowered confidence for unusual duration
        
        # Test no duration found
        result = self.processor.calculate_duration_end_time(
            self.test_start_time, "Meeting tomorrow"
        )
        assert result.duration_minutes is None
        assert result.confidence == 0.0
        
        # Test invalid start time
        result = self.processor.calculate_duration_end_time(
            None, "Meeting for 1 hour"
        )
        assert result.confidence == 0.0
    
    def test_parse_until_time_noon_midnight(self):
        """Test parsing 'until noon' and 'until midnight' expressions."""
        # Test "until noon" with morning start time
        morning_start = datetime(2025, 10, 8, 10, 0)  # 10:00 AM
        result = self.processor.parse_until_time(
            "Meeting until noon", morning_start
        )
        expected_end = morning_start.replace(hour=12, minute=0, second=0, microsecond=0)
        assert result.end_time_override == expected_end
        assert result.confidence == 0.9
        
        # Test "until midnight"
        result = self.processor.parse_until_time(
            "Party until midnight", self.test_start_time
        )
        expected_end = self.test_start_time.replace(hour=23, minute=59, second=59, microsecond=0)
        assert result.end_time_override == expected_end
        assert result.confidence == 0.9
    
    def test_parse_until_time_specific_times(self):
        """Test parsing specific time expressions with 'until'."""
        # Test "until 5pm"
        result = self.processor.parse_until_time(
            "Work until 5pm", self.test_start_time
        )
        expected_end = self.test_start_time.replace(hour=17, minute=0, second=0, microsecond=0)
        assert result.end_time_override == expected_end
        assert result.confidence == 0.8
        
        # Test "until 10:30 AM"
        result = self.processor.parse_until_time(
            "Available until 10:30 AM", self.test_start_time
        )
        # Should be next day since 10:30 AM is before 2:00 PM start
        expected_end = (self.test_start_time + timedelta(days=1)).replace(
            hour=10, minute=30, second=0, microsecond=0
        )
        assert result.end_time_override == expected_end
        assert result.confidence < 0.8  # Lowered for next-day assumption
        
        # Test "until 17:30" (24-hour format)
        result = self.processor.parse_until_time(
            "Meeting until 17:30", self.test_start_time
        )
        expected_end = self.test_start_time.replace(hour=17, minute=30, second=0, microsecond=0)
        assert result.end_time_override == expected_end
        assert result.confidence == 0.8
    
    def test_parse_until_time_word_numbers(self):
        """Test parsing word numbers in 'until' expressions."""
        # Test "until five"
        result = self.processor.parse_until_time(
            "Open until five", self.test_start_time
        )
        expected_end = self.test_start_time.replace(hour=17, minute=0, second=0, microsecond=0)
        assert result.end_time_override == expected_end
        assert result.confidence == 0.8
        
        # Test "until twelve" (should be midnight, not noon)
        result = self.processor.parse_until_time(
            "Party until twelve", self.test_start_time
        )
        expected_end = (self.test_start_time + timedelta(days=1)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        assert result.end_time_override == expected_end
    
    def test_parse_until_time_edge_cases(self):
        """Test edge cases for until time parsing."""
        # Test no until expression
        result = self.processor.parse_until_time(
            "Regular meeting", self.test_start_time
        )
        assert result.end_time_override is None
        assert result.confidence == 0.0
        
        # Test invalid start time
        result = self.processor.parse_until_time(
            "Meeting until 5pm", None
        )
        assert result.confidence == 0.0
        
        # Test invalid time format
        result = self.processor.parse_until_time(
            "Meeting until 25:00", self.test_start_time
        )
        assert result.end_time_override is None
        assert result.confidence == 0.0
    
    def test_detect_all_day_indicators_explicit(self):
        """Test detection of explicit all-day indicators."""
        # Test "all-day"
        result = self.processor.detect_all_day_indicators("All-day conference")
        assert result.all_day is True
        assert result.confidence == 0.9
        
        # Test "full day"
        result = self.processor.detect_all_day_indicators("Full day workshop")
        assert result.all_day is True
        assert result.confidence == 0.9
        
        # Test "entire day"
        result = self.processor.detect_all_day_indicators("Entire day event")
        assert result.all_day is True
        assert result.confidence == 0.9
        
        # Test "whole day"
        result = self.processor.detect_all_day_indicators("Whole day meeting")
        assert result.all_day is True
        assert result.confidence == 0.9
        
        # Test "throughout the day"
        result = self.processor.detect_all_day_indicators("Activities throughout the day")
        assert result.all_day is True
        assert result.confidence == 0.9
    
    def test_detect_all_day_indicators_implicit(self):
        """Test detection of implicit all-day indicators."""
        # Test conference without specific time
        result = self.processor.detect_all_day_indicators("Tech conference on Monday")
        assert result.all_day is True
        assert result.confidence == 0.6
        
        # Test vacation
        result = self.processor.detect_all_day_indicators("Vacation to Hawaii")
        assert result.all_day is True
        assert result.confidence == 0.6
        
        # Test birthday
        result = self.processor.detect_all_day_indicators("John's birthday party")
        assert result.all_day is True
        assert result.confidence == 0.6
        
        # Test with specific time (should not be all-day)
        result = self.processor.detect_all_day_indicators("Conference at 2:00 PM")
        assert result.all_day is False
        assert result.confidence == 0.0
    
    def test_detect_all_day_indicators_negative_cases(self):
        """Test cases that should not be detected as all-day."""
        # Test regular meeting
        result = self.processor.detect_all_day_indicators("Team meeting")
        assert result.all_day is False
        assert result.confidence == 0.0
        
        # Test with specific time
        result = self.processor.detect_all_day_indicators("Meeting at 3pm")
        assert result.all_day is False
        assert result.confidence == 0.0
        
        # Test with time range
        result = self.processor.detect_all_day_indicators("Workshop from 9am to 5pm")
        assert result.all_day is False
        assert result.confidence == 0.0
    
    def test_resolve_duration_conflicts_explicit_end_time(self):
        """Test conflict resolution when explicit end time exists."""
        # Explicit end time should take priority
        explicit_end = self.test_start_time + timedelta(hours=3)
        duration_result = DurationResult(duration_minutes=120, confidence=0.8)  # 2 hours
        
        resolved_end, resolved_result = self.processor.resolve_duration_conflicts(
            self.test_start_time, explicit_end, duration_result
        )
        
        assert resolved_end == explicit_end
        assert resolved_result.duration_minutes == 180  # 3 hours (actual duration)
        assert resolved_result.end_time_override == explicit_end
        assert resolved_result.confidence >= 0.9  # High confidence for explicit times
    
    def test_resolve_duration_conflicts_until_override(self):
        """Test conflict resolution with 'until' time override."""
        until_end = self.test_start_time.replace(hour=17, minute=0)  # 5 PM
        duration_result = DurationResult(
            end_time_override=until_end,
            confidence=0.8
        )
        
        resolved_end, resolved_result = self.processor.resolve_duration_conflicts(
            self.test_start_time, None, duration_result
        )
        
        assert resolved_end == until_end
        assert resolved_result.duration_minutes == 180  # 3 hours (14:00 to 17:00)
        assert resolved_result.end_time_override == until_end
        assert resolved_result.confidence == 0.8
    
    def test_resolve_duration_conflicts_duration_minutes(self):
        """Test conflict resolution with duration minutes."""
        duration_result = DurationResult(duration_minutes=90, confidence=0.8)  # 1.5 hours
        
        resolved_end, resolved_result = self.processor.resolve_duration_conflicts(
            self.test_start_time, None, duration_result
        )
        
        expected_end = self.test_start_time + timedelta(minutes=90)
        assert resolved_end == expected_end
        assert resolved_result.duration_minutes == 90
        assert resolved_result.end_time_override == expected_end
        assert resolved_result.confidence == 0.8
    
    def test_resolve_duration_conflicts_all_day(self):
        """Test conflict resolution for all-day events."""
        duration_result = DurationResult(all_day=True, confidence=0.9)
        
        resolved_end, resolved_result = self.processor.resolve_duration_conflicts(
            self.test_start_time, None, duration_result
        )
        
        expected_end = self.test_start_time.replace(hour=23, minute=59, second=59, microsecond=0)
        assert resolved_end == expected_end
        assert resolved_result.all_day is True
        assert resolved_result.duration_minutes == 1439  # Almost 24 hours
        assert resolved_result.confidence == 0.9
    
    def test_resolve_duration_conflicts_no_duration(self):
        """Test conflict resolution when no duration information is found."""
        duration_result = DurationResult(confidence=0.0)
        
        resolved_end, resolved_result = self.processor.resolve_duration_conflicts(
            self.test_start_time, None, duration_result
        )
        
        assert resolved_end is None
        assert resolved_result.confidence == 0.0
    
    def test_resolve_duration_conflicts_invalid_start(self):
        """Test conflict resolution with invalid start time."""
        duration_result = DurationResult(duration_minutes=60, confidence=0.8)
        
        resolved_end, resolved_result = self.processor.resolve_duration_conflicts(
            None, None, duration_result
        )
        
        assert resolved_end is None
        assert resolved_result == duration_result  # Unchanged
    
    def test_process_duration_and_all_day_comprehensive(self):
        """Test the main processing method with various scenarios."""
        # Test all-day event
        end_time, result = self.processor.process_duration_and_all_day(
            "All-day conference", self.test_start_time, None
        )
        assert result.all_day is True
        assert end_time is not None
        
        # Test duration expression
        end_time, result = self.processor.process_duration_and_all_day(
            "Meeting for 2 hours", self.test_start_time, None
        )
        assert result.duration_minutes == 120
        assert end_time == self.test_start_time + timedelta(hours=2)
        
        # Test until expression
        end_time, result = self.processor.process_duration_and_all_day(
            "Work until 5pm", self.test_start_time, None
        )
        expected_end = self.test_start_time.replace(hour=17, minute=0, second=0, microsecond=0)
        assert end_time == expected_end
        
        # Test with explicit end time (should take priority)
        explicit_end = self.test_start_time + timedelta(hours=1)
        end_time, result = self.processor.process_duration_and_all_day(
            "Meeting for 2 hours", self.test_start_time, explicit_end
        )
        assert end_time == explicit_end
        assert result.duration_minutes == 60  # Actual duration from explicit times
        
        # Test no duration information
        end_time, result = self.processor.process_duration_and_all_day(
            "Regular meeting", self.test_start_time, None
        )
        assert end_time is None
        assert result.confidence == 0.0
    
    def test_process_duration_and_all_day_invalid_start(self):
        """Test main processing method with invalid start time."""
        end_time, result = self.processor.process_duration_and_all_day(
            "Meeting for 1 hour", None, None
        )
        assert end_time is None
        assert result.confidence == 0.0
    
    def test_regex_patterns_case_insensitive(self):
        """Test that regex patterns work case-insensitively."""
        # Test uppercase
        result = self.processor.calculate_duration_end_time(
            self.test_start_time, "MEETING FOR 2 HOURS"
        )
        assert result.duration_minutes == 120
        
        # Test mixed case
        result = self.processor.detect_all_day_indicators("All-Day Conference")
        assert result.all_day is True
        
        # Test until expressions
        morning_start = datetime(2025, 10, 8, 10, 0)  # 10:00 AM
        result = self.processor.parse_until_time(
            "WORK UNTIL NOON", morning_start
        )
        expected_end = morning_start.replace(hour=12, minute=0, second=0, microsecond=0)
        assert result.end_time_override == expected_end
    
    def test_multiple_patterns_in_text(self):
        """Test handling of multiple duration patterns in the same text."""
        # Should pick the first valid pattern
        result = self.processor.calculate_duration_end_time(
            self.test_start_time, "Meeting for 1 hour, lasting 2 hours total"
        )
        assert result.duration_minutes == 60  # First pattern wins
        
        # Test conflicting until and duration
        end_time, result = self.processor.process_duration_and_all_day(
            "Meeting for 1 hour until 5pm", self.test_start_time, None
        )
        # Until expression should take priority (higher confidence)
        expected_end = self.test_start_time.replace(hour=17, minute=0, second=0, microsecond=0)
        assert end_time == expected_end


if __name__ == "__main__":
    pytest.main([__file__])