"""
Comprehensive unit tests for ComprehensiveDateTimeParser class.
Tests all date/time parsing scenarios including typos, natural phrases, and edge cases.
"""

import pytest
from datetime import datetime, date, time, timedelta
from services.comprehensive_datetime_parser import ComprehensiveDateTimeParser, DateTimeResult


class TestComprehensiveDateTimeParser:
    """Test suite for ComprehensiveDateTimeParser."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.parser = ComprehensiveDateTimeParser()
    
    # Test explicit date parsing
    def test_explicit_date_parsing_with_weekday(self):
        """Test parsing explicit dates with weekday validation."""
        text = "Meeting on Monday, Sep 29, 2025"
        result = self.parser.parse_datetime(text)
        
        assert result.start_datetime is not None
        assert result.start_datetime.date() == date(2025, 9, 29)
        assert result.field_confidence['date'] > 0.9  # Date confidence should be high
        assert result.extraction_method == "inferred"  # Overall method is inferred due to assumed time
    
    def test_explicit_date_parsing_month_day_year(self):
        """Test parsing Month DD, YYYY format."""
        text = "Event on September 29th, 2025"
        result = self.parser.parse_datetime(text)
        
        assert result.start_datetime is not None
        assert result.start_datetime.date() == date(2025, 9, 29)
        assert result.field_confidence['date'] > 0.9  # Date confidence should be high
    
    def test_explicit_date_parsing_numeric_formats(self):
        """Test parsing numeric date formats."""
        # MM/DD/YYYY format
        text = "Meeting on 09/29/2025"
        result = self.parser.parse_datetime(text)
        
        assert result.start_datetime is not None
        assert result.start_datetime.date() == date(2025, 9, 29)
        
        # DD/MM/YYYY format with preference
        text = "Meeting on 29/09/2025"
        result = self.parser.parse_datetime(text, prefer_dd_mm=True)
        
        assert result.start_datetime is not None
        assert result.start_datetime.date() == date(2025, 9, 29)
    
    def test_inline_date_current_year(self):
        """Test parsing inline dates that assume current year."""
        text = "Meeting on Sep 29"
        result = self.parser.parse_datetime(text)
        
        assert result.start_datetime is not None
        assert result.start_datetime.month == 9
        assert result.start_datetime.day == 29
        assert result.start_datetime.year == datetime.now().year
    
    # Test relative date parsing
    def test_relative_date_today_tomorrow(self):
        """Test parsing today and tomorrow."""
        # Today
        text = "Meeting today"
        result = self.parser.parse_datetime(text)
        
        assert result.start_datetime is not None
        assert result.start_datetime.date() == date.today()
        assert result.field_confidence['date'] > 0.9  # Date confidence should be high
        
        # Tomorrow
        text = "Meeting tomorrow"
        result = self.parser.parse_datetime(text)
        
        assert result.start_datetime is not None
        assert result.start_datetime.date() == date.today() + timedelta(days=1)
        assert result.field_confidence['date'] > 0.9  # Date confidence should be high
    
    def test_relative_date_weekdays(self):
        """Test parsing relative weekday references."""
        text = "Meeting next Monday"
        result = self.parser.parse_datetime(text)
        
        assert result.start_datetime is not None
        assert result.start_datetime.weekday() == 0  # Monday
        assert result.confidence > 0.6  # Lower confidence due to inferred time
        
        text = "Meeting this Friday"
        result = self.parser.parse_datetime(text)
        
        assert result.start_datetime is not None
        assert result.start_datetime.weekday() == 4  # Friday
    
    def test_relative_date_in_days_weeks(self):
        """Test parsing 'in X days/weeks' format."""
        text = "Meeting in 3 days"
        result = self.parser.parse_datetime(text)
        
        assert result.start_datetime is not None
        assert result.start_datetime.date() == date.today() + timedelta(days=3)
        
        text = "Meeting in two weeks"
        result = self.parser.parse_datetime(text)
        
        assert result.start_datetime is not None
        assert result.start_datetime.date() == date.today() + timedelta(weeks=2)
    
    def test_natural_phrases(self):
        """Test parsing natural date phrases."""
        text = "Meeting at the end of month"
        result = self.parser.parse_datetime(text)
        
        assert result.start_datetime is not None
        assert result.extraction_method in ["inferred", "relative"]
        
        text = "Meeting the first day back after break"
        result = self.parser.parse_datetime(text)
        
        assert result.start_datetime is not None
        assert len(result.parsing_issues) > 0  # Should note context dependency
        assert len(result.suggestions) > 0
    
    # Test typo-tolerant time parsing
    def test_typo_tolerant_time_parsing(self):
        """Test parsing times with various typos and formats."""
        test_cases = [
            ("Meeting at 9a.m", time(9, 0)),
            ("Meeting at 9am", time(9, 0)),
            ("Meeting at 9:00 A M", time(9, 0)),
            ("Meeting at 9 AM", time(9, 0)),
            ("Meeting at 2p.m", time(14, 0)),
            ("Meeting at 2pm", time(14, 0)),
            ("Meeting at 2:30 P M", time(14, 30)),
        ]
        
        for text, expected_time in test_cases:
            result = self.parser.parse_datetime(text)
            assert result.start_datetime is not None
            assert result.start_datetime.time() == expected_time
    
    def test_special_time_words(self):
        """Test parsing special time words."""
        # Noon
        text = "Meeting at noon"
        result = self.parser.parse_datetime(text)
        
        assert result.start_datetime is not None
        assert result.start_datetime.time() == time(12, 0)
        assert result.confidence > 0.5  # Lower confidence due to inferred date
        
        # Midnight
        text = "Meeting at midnight"
        result = self.parser.parse_datetime(text)
        
        assert result.start_datetime is not None
        assert result.start_datetime.time() == time(0, 0)
        assert result.confidence > 0.5  # Lower confidence due to inferred date
    
    def test_relative_time_conversion(self):
        """Test conversion of relative time phrases."""
        test_cases = [
            ("Meeting after lunch", time(13, 0)),
            ("Meeting before school", time(8, 0)),
            ("Meeting at end of day", time(17, 0)),
        ]
        
        for text, expected_time in test_cases:
            result = self.parser.parse_datetime(text)
            assert result.start_datetime is not None
            assert result.start_datetime.time() == expected_time
            assert result.extraction_method == "inferred"
    
    # Test time range extraction
    def test_time_range_12hour(self):
        """Test parsing 12-hour time ranges."""
        text = "Meeting from 9:00 AM to 11:30 AM"
        result = self.parser.parse_datetime(text)
        
        assert result.start_datetime is not None
        assert result.end_datetime is not None
        assert result.start_datetime.time() == time(9, 0)
        assert result.end_datetime.time() == time(11, 30)
        assert result.field_confidence['start_time'] > 0.9  # Time confidence should be high
        assert result.field_confidence['end_time'] > 0.9
    
    def test_time_range_24hour(self):
        """Test parsing 24-hour time ranges."""
        text = "Meeting from 14:00 to 16:30"
        result = self.parser.parse_datetime(text)
        
        assert result.start_datetime is not None
        assert result.end_datetime is not None
        assert result.start_datetime.time() == time(14, 0)
        assert result.end_datetime.time() == time(16, 30)
    
    def test_time_range_with_dashes(self):
        """Test parsing time ranges with various dash types."""
        test_cases = [
            "Meeting 9–10 a.m.",
            "Meeting 9-10 a.m.",
            "Meeting 9−10 a.m.",  # Unicode minus
            "Meeting 9~10 a.m.",
        ]
        
        for text in test_cases:
            result = self.parser.parse_datetime(text)
            assert result.start_datetime is not None
            assert result.end_datetime is not None
            assert result.start_datetime.time() == time(9, 0)
            assert result.end_datetime.time() == time(10, 0)
    
    # Test duration calculation
    def test_duration_parsing(self):
        """Test parsing duration information."""
        text = "Meeting tomorrow at 2pm for 2 hours"
        result = self.parser.parse_datetime(text)
        
        assert result.start_datetime is not None
        assert result.end_datetime is not None
        assert result.start_datetime.time() == time(14, 0)
        assert result.end_datetime == result.start_datetime + timedelta(hours=2)
    
    def test_duration_minutes(self):
        """Test parsing minute durations."""
        text = "Meeting at 3pm for 30 minutes"
        result = self.parser.parse_datetime(text)
        
        assert result.start_datetime is not None
        assert result.end_datetime is not None
        assert result.end_datetime == result.start_datetime + timedelta(minutes=30)
    
    def test_duration_long_format(self):
        """Test parsing 'X minutes long' format."""
        text = "Meeting at 2pm, 45 minutes long"
        result = self.parser.parse_datetime(text)
        
        assert result.start_datetime is not None
        assert result.end_datetime is not None
        assert result.end_datetime == result.start_datetime + timedelta(minutes=45)
    
    # Test combined scenarios
    def test_complete_datetime_with_weekday(self):
        """Test parsing complete datetime with weekday validation."""
        text = "Meeting on Monday, September 29, 2025 at 2:30 PM"
        result = self.parser.parse_datetime(text)
        
        assert result.start_datetime is not None
        assert result.start_datetime == datetime(2025, 9, 29, 14, 30)
        assert result.confidence > 0.9
        assert result.extraction_method == "explicit"
    
    def test_date_with_time_range(self):
        """Test parsing date with time range."""
        text = "Meeting on Sep 29 from 2:00 PM to 4:00 PM"
        result = self.parser.parse_datetime(text)
        
        assert result.start_datetime is not None
        assert result.end_datetime is not None
        assert result.start_datetime.month == 9
        assert result.start_datetime.day == 29
        assert result.start_datetime.time() == time(14, 0)
        assert result.end_datetime.time() == time(16, 0)
    
    # Test ambiguity detection
    def test_ambiguous_date_detection(self):
        """Test detection of ambiguous date formats."""
        text = "Meeting on 03/05/2025"  # Could be March 5 or May 3
        result = self.parser.parse_datetime(text)
        
        assert result.start_datetime is not None
        assert len(result.ambiguities) > 0
        assert result.confidence < 0.9  # Lower confidence due to ambiguity
    
    def test_weekday_mismatch_detection(self):
        """Test detection of weekday mismatches."""
        # September 29, 2025 is actually a Monday, not Tuesday
        text = "Meeting on Tuesday, Sep 29, 2025"
        result = self.parser.parse_datetime(text)
        
        assert result.start_datetime is not None
        assert len(result.parsing_issues) > 0
        assert result.confidence < 0.9  # Lower confidence due to mismatch
    
    # Test error handling and edge cases
    def test_no_datetime_found(self):
        """Test handling when no datetime information is found."""
        text = "This is just regular text with no dates or times"
        result = self.parser.parse_datetime(text)
        
        assert result.start_datetime is None
        assert result.confidence == 0.0
        assert result.extraction_method == "none"
    
    def test_invalid_date_handling(self):
        """Test handling of invalid dates."""
        text = "Meeting on February 30, 2025"  # Invalid date
        result = self.parser.parse_datetime(text)
        
        # Should either find no date or handle gracefully
        if result.start_datetime:
            assert result.confidence < 0.8
    
    def test_past_date_detection(self):
        """Test validation of past dates."""
        # Use a date that's definitely in the past
        text = "Meeting on January 1, 2020"
        result = self.parser.parse_datetime(text)
        
        validation = self.parser.validate_extraction(result)
        assert "past" in str(validation['warnings']).lower()
    
    # Test confidence scoring
    def test_confidence_scoring_explicit_vs_inferred(self):
        """Test that explicit information has higher confidence than inferred."""
        explicit_text = "Meeting on September 29, 2025 at 2:30 PM"
        explicit_result = self.parser.parse_datetime(explicit_text)
        
        inferred_text = "Meeting tomorrow"  # Date inferred, time assumed
        inferred_result = self.parser.parse_datetime(inferred_text)
        
        assert explicit_result.confidence > inferred_result.confidence
    
    def test_field_confidence_tracking(self):
        """Test individual field confidence tracking."""
        text = "Meeting on Sep 29 at 2pm"  # Date missing year, explicit time
        result = self.parser.parse_datetime(text)
        
        assert result.field_confidence is not None
        assert 'date' in result.field_confidence
        assert 'start_time' in result.field_confidence
    
    # Test validation and suggestions
    def test_validation_missing_fields(self):
        """Test validation identifies missing fields."""
        text = "Meeting on Sep 29"  # Missing time
        result = self.parser.parse_datetime(text)
        
        validation = self.parser.validate_extraction(result)
        assert 'end_time' in validation['missing_fields']
        assert len(validation['recommendations']) > 0
    
    def test_parsing_suggestions(self):
        """Test generation of parsing suggestions."""
        text = "Meeting sometime next week"  # Vague information
        result = self.parser.parse_datetime(text)
        
        suggestions = self.parser.get_parsing_suggestions(text, result)
        assert len(suggestions) > 0
        assert any('explicit' in suggestion.lower() for suggestion in suggestions)
    
    def test_low_confidence_warnings(self):
        """Test warnings for low confidence results."""
        text = "Meeting maybe around 3ish"  # Very vague
        result = self.parser.parse_datetime(text)
        
        if result.start_datetime and result.confidence < 0.7:
            validation = self.parser.validate_extraction(result)
            assert any('confidence' in warning.lower() for warning in validation['warnings'])
    
    # Test comprehensive real-world scenarios
    def test_email_style_parsing(self):
        """Test parsing email-style event information."""
        text = """
        Hi everyone,
        
        Let's meet on Monday, Sep 29th at 2:30 PM for our weekly standup.
        The meeting should last about 30 minutes.
        
        Thanks!
        """
        result = self.parser.parse_datetime(text)
        
        assert result.start_datetime is not None
        assert result.start_datetime.month == 9
        assert result.start_datetime.day == 29
        assert result.start_datetime.time() == time(14, 30)
        # Should also detect duration if implemented
    
    def test_multiple_datetime_references(self):
        """Test handling text with multiple datetime references."""
        text = "Meeting on Sep 29 at 2pm, but if that doesn't work, how about Oct 1 at 3pm?"
        result = self.parser.parse_datetime(text)
        
        # Should pick the first/most confident datetime
        assert result.start_datetime is not None
        assert result.start_datetime.month == 9
        assert result.start_datetime.day == 29
    
    def test_typo_normalization(self):
        """Test comprehensive typo handling and normalization."""
        test_cases = [
            ("Meeting Sep29th", 9, 29),  # Missing space
            ("Meeting Sep. 29", 9, 29),  # Period after month
            ("Meeting 2 p.m.", time(14, 0)),  # Spaced AM/PM
            ("Meeting 14:30hrs", time(14, 30)),  # Hours suffix
        ]
        
        for text, *expected in test_cases:
            result = self.parser.parse_datetime(text)
            assert result.start_datetime is not None
            
            if len(expected) == 2:  # Date test
                month, day = expected
                assert result.start_datetime.month == month
                assert result.start_datetime.day == day
            else:  # Time test
                expected_time = expected[0]
                assert result.start_datetime.time() == expected_time


if __name__ == "__main__":
    pytest.main([__file__])