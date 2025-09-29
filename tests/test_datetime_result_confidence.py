"""
Unit tests for DateTimeResult data model and confidence scoring functionality.
Tests confidence scoring accuracy, validation, and quality assessment.
"""

import pytest
from datetime import datetime, date, time, timedelta
from services.comprehensive_datetime_parser import ComprehensiveDateTimeParser, DateTimeResult


class TestDateTimeResultConfidence:
    """Test suite for DateTimeResult confidence scoring and validation."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.parser = ComprehensiveDateTimeParser()
    
    # Test confidence scoring accuracy
    def test_explicit_datetime_high_confidence(self):
        """Test that explicit date and time information gets high confidence."""
        text = "Meeting on September 29, 2025 at 2:30 PM"
        result = self.parser.parse_datetime(text)
        
        assert result.start_datetime is not None
        assert result.confidence > 0.8
        assert result.extraction_method == "explicit"
        assert result.field_confidence['date'] > 0.9
        assert result.field_confidence['start_time'] > 0.9
    
    def test_relative_datetime_medium_confidence(self):
        """Test that relative dates have medium confidence."""
        text = "Meeting tomorrow at 3pm"
        result = self.parser.parse_datetime(text)
        
        assert result.start_datetime is not None
        assert 0.7 <= result.confidence <= 0.95
        assert result.extraction_method in ["explicit", "relative"]
        assert result.field_confidence['date'] > 0.8  # Tomorrow is very clear
        assert result.field_confidence['start_time'] > 0.9  # 3pm is explicit
    
    def test_inferred_datetime_lower_confidence(self):
        """Test that inferred information has lower confidence."""
        text = "Meeting on Sep 29"  # Missing year and time
        result = self.parser.parse_datetime(text)
        
        assert result.start_datetime is not None
        assert result.confidence < 0.8
        assert result.extraction_method == "inferred"
        assert result.field_confidence['date'] > 0.8  # Date is explicit except year
        assert result.field_confidence['start_time'] < 0.6  # Time is assumed
    
    def test_ambiguous_date_reduced_confidence(self):
        """Test that ambiguous dates reduce confidence."""
        text = "Meeting on 03/05/2025"  # Could be March 5 or May 3
        result = self.parser.parse_datetime(text)
        
        assert result.start_datetime is not None
        assert len(result.ambiguities) > 0
        assert result.confidence < 0.9  # Reduced due to ambiguity
    
    def test_weekday_mismatch_reduced_confidence(self):
        """Test that weekday mismatches reduce confidence."""
        # September 29, 2025 is actually a Monday, not Tuesday
        text = "Meeting on Tuesday, Sep 29, 2025"
        result = self.parser.parse_datetime(text)
        
        assert result.start_datetime is not None
        assert len(result.parsing_issues) > 0
        assert result.confidence < 0.9
        assert any("mismatch" in issue.lower() for issue in result.parsing_issues)
    
    def test_typo_tolerance_confidence(self):
        """Test that typo-tolerant parsing maintains reasonable confidence."""
        text = "Meeting at 2:30 P M"  # Spaced AM/PM
        result = self.parser.parse_datetime(text)
        
        assert result.start_datetime is not None
        assert result.start_datetime.time() == time(14, 30)
        assert result.field_confidence['start_time'] > 0.8  # Should still be confident
    
    # Test extraction method tracking
    def test_extraction_method_explicit(self):
        """Test explicit extraction method tracking."""
        text = "Meeting on Monday, September 29, 2025 at 2:30 PM"
        result = self.parser.parse_datetime(text)
        
        assert result.extraction_method == "explicit"
        assert result.confidence > 0.9
    
    def test_extraction_method_relative(self):
        """Test relative extraction method tracking."""
        text = "Meeting tomorrow at noon"
        result = self.parser.parse_datetime(text)
        
        assert result.extraction_method in ["explicit", "relative"]
        assert result.field_confidence['date'] > 0.9  # Tomorrow is clear
    
    def test_extraction_method_inferred(self):
        """Test inferred extraction method tracking."""
        text = "Meeting at 3pm"  # Date inferred as today
        result = self.parser.parse_datetime(text)
        
        assert result.extraction_method == "inferred"
        assert "Date assumed" in str(result.parsing_issues)
    
    # Test ambiguity detection
    def test_multiple_interpretations_tracking(self):
        """Test tracking of multiple possible interpretations."""
        text = "Meeting on 01/02/2025"  # Jan 2 vs Feb 1
        result = self.parser.parse_datetime(text)
        
        assert result.start_datetime is not None
        if len(result.ambiguities) > 0:
            assert any("Could also be" in ambiguity for ambiguity in result.ambiguities)
    
    def test_no_ambiguity_for_clear_dates(self):
        """Test that clear dates don't generate ambiguities."""
        text = "Meeting on September 29, 2025"
        result = self.parser.parse_datetime(text)
        
        assert result.start_datetime is not None
        assert len(result.ambiguities) == 0
    
    # Test raw text preservation
    def test_raw_text_preservation(self):
        """Test that original text is preserved for debugging."""
        text = "Meeting on Sep 29 at 2:30 PM"
        result = self.parser.parse_datetime(text)
        
        assert result.raw_text == text
    
    # Test validation and quality assessment
    def test_validation_complete_datetime(self):
        """Test validation of complete datetime information."""
        text = "Meeting on Sep 29, 2025 from 2:00 PM to 4:00 PM"
        result = self.parser.parse_datetime(text)
        
        validation = self.parser.validate_extraction(result)
        
        assert validation['is_valid'] is True
        assert validation['quality_score'] > 0.8
        assert len(validation['missing_fields']) == 0
    
    def test_validation_missing_end_time(self):
        """Test validation identifies missing end time."""
        text = "Meeting on Sep 29 at 2pm"
        result = self.parser.parse_datetime(text)
        
        validation = self.parser.validate_extraction(result)
        
        assert validation['is_valid'] is True
        assert 'end_time' in validation['missing_fields']
        assert any('end time' in rec.lower() for rec in validation['recommendations'])
    
    def test_validation_low_confidence_warning(self):
        """Test validation warns about low confidence."""
        text = "Meeting sometime next week"  # Very vague
        result = self.parser.parse_datetime(text)
        
        if result.start_datetime and result.confidence < 0.7:
            validation = self.parser.validate_extraction(result)
            assert any('confidence' in warning.lower() for warning in validation['warnings'])
    
    def test_validation_past_date_warning(self):
        """Test validation warns about past dates."""
        text = "Meeting on January 1, 2020"  # Definitely in the past
        result = self.parser.parse_datetime(text)
        
        validation = self.parser.validate_extraction(result)
        assert any('past' in warning.lower() for warning in validation['warnings'])
    
    def test_validation_no_datetime_found(self):
        """Test validation handles no datetime found."""
        text = "This is just regular text with no dates"
        result = self.parser.parse_datetime(text)
        
        validation = self.parser.validate_extraction(result)
        
        assert validation['is_valid'] is False
        assert validation['quality_score'] == 0.0
        assert 'date' in validation['missing_fields']
        assert 'time' in validation['missing_fields']
    
    # Test field-level confidence scoring
    def test_field_confidence_date_explicit(self):
        """Test field confidence for explicit dates."""
        text = "Meeting on September 29, 2025"
        result = self.parser.parse_datetime(text)
        
        assert 'date' in result.field_confidence
        assert result.field_confidence['date'] > 0.9
    
    def test_field_confidence_date_assumed_year(self):
        """Test field confidence for dates with assumed year."""
        text = "Meeting on Sep 29"
        result = self.parser.parse_datetime(text)
        
        assert 'date' in result.field_confidence
        assert 0.8 <= result.field_confidence['date'] <= 0.9  # Lower due to assumed year
    
    def test_field_confidence_time_explicit(self):
        """Test field confidence for explicit times."""
        text = "Meeting at 2:30 PM"
        result = self.parser.parse_datetime(text)
        
        assert 'start_time' in result.field_confidence
        assert result.field_confidence['start_time'] > 0.9
    
    def test_field_confidence_time_assumed(self):
        """Test field confidence for assumed times."""
        text = "Meeting on Sep 29"  # Time will be assumed
        result = self.parser.parse_datetime(text)
        
        assert 'start_time' in result.field_confidence
        assert result.field_confidence['start_time'] < 0.6  # Low confidence for assumed time
    
    def test_field_confidence_time_range(self):
        """Test field confidence for time ranges."""
        text = "Meeting from 2:00 PM to 4:00 PM"
        result = self.parser.parse_datetime(text)
        
        if result.end_datetime:
            assert 'start_time' in result.field_confidence
            assert 'end_time' in result.field_confidence
            assert result.field_confidence['start_time'] > 0.9
            assert result.field_confidence['end_time'] > 0.9
    
    # Test parsing issues tracking
    def test_parsing_issues_weekday_mismatch(self):
        """Test tracking of weekday mismatch issues."""
        text = "Meeting on Tuesday, Sep 29, 2025"  # Monday, not Tuesday
        result = self.parser.parse_datetime(text)
        
        assert len(result.parsing_issues) > 0
        assert any("mismatch" in issue.lower() for issue in result.parsing_issues)
    
    def test_parsing_issues_assumed_date(self):
        """Test tracking of assumed date issues."""
        text = "Meeting at 3pm"  # Date assumed as today
        result = self.parser.parse_datetime(text)
        
        assert len(result.parsing_issues) > 0
        assert any("assumed" in issue.lower() for issue in result.parsing_issues)
    
    def test_parsing_issues_assumed_time(self):
        """Test tracking of assumed time issues."""
        text = "Meeting on Sep 29"  # Time assumed as 9:00 AM
        result = self.parser.parse_datetime(text)
        
        assert len(result.parsing_issues) > 0
        assert any("assumed" in issue.lower() for issue in result.parsing_issues)
    
    # Test suggestions generation
    def test_suggestions_for_missing_time(self):
        """Test suggestions when time is missing."""
        text = "Meeting on Sep 29"
        result = self.parser.parse_datetime(text)
        
        assert len(result.suggestions) > 0
        assert any("time" in suggestion.lower() for suggestion in result.suggestions)
    
    def test_suggestions_for_missing_date(self):
        """Test suggestions when date is missing."""
        text = "Meeting at 3pm"
        result = self.parser.parse_datetime(text)
        
        suggestions = self.parser.get_parsing_suggestions(text, result)
        assert len(suggestions) > 0
        assert any("date" in suggestion.lower() for suggestion in suggestions)
    
    def test_suggestions_for_low_confidence(self):
        """Test suggestions for low confidence results."""
        text = "Meeting sometime around 3ish"  # Very vague
        result = self.parser.parse_datetime(text)
        
        suggestions = self.parser.get_parsing_suggestions(text, result)
        assert len(suggestions) > 0
        if result.confidence < 0.8:
            assert any("explicit" in suggestion.lower() for suggestion in suggestions)
    
    def test_suggestions_for_ambiguous_dates(self):
        """Test suggestions for ambiguous date formats."""
        text = "Meeting on 03/05/2025"
        result = self.parser.parse_datetime(text)
        
        suggestions = self.parser.get_parsing_suggestions(text, result)
        if result.ambiguities:
            assert any("unambiguous" in suggestion.lower() for suggestion in suggestions)
    
    # Test confidence scoring edge cases
    def test_confidence_scoring_natural_phrases(self):
        """Test confidence scoring for natural phrases."""
        text = "Meeting the first day back after break"
        result = self.parser.parse_datetime(text)
        
        if result.start_datetime:
            assert result.confidence < 0.8  # Should be lower due to context dependency
            assert len(result.parsing_issues) > 0
            assert len(result.suggestions) > 0
    
    def test_confidence_scoring_relative_times(self):
        """Test confidence scoring for relative time phrases."""
        text = "Meeting after lunch"
        result = self.parser.parse_datetime(text)
        
        if result.start_datetime:
            assert result.extraction_method == "inferred"
            assert result.field_confidence['start_time'] < 0.8  # Relative time is less certain
    
    def test_confidence_scoring_duration_calculation(self):
        """Test confidence scoring when duration is calculated."""
        text = "Meeting at 2pm for 2 hours"
        result = self.parser.parse_datetime(text)
        
        if result.end_datetime:
            assert 'duration' in result.field_confidence
            assert result.field_confidence['duration'] > 0.9  # Explicit duration


if __name__ == "__main__":
    pytest.main([__file__])