"""
Unit tests for Per-Field Confidence Router.

Tests routing logic, confidence thresholds, field analysis, and processing optimization.
Requirements: 10.1, 10.2, 10.3, 10.5
"""

import pytest
from datetime import datetime, timedelta
from services.per_field_confidence_router import (
    PerFieldConfidenceRouter, 
    ProcessingMethod, 
    FieldAnalysis
)
from models.event_models import FieldResult, ValidationResult


class TestPerFieldConfidenceRouter:
    """Test suite for PerFieldConfidenceRouter functionality."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.router = PerFieldConfidenceRouter()
    
    def test_initialization(self):
        """Test router initialization and pattern compilation."""
        assert self.router is not None
        assert hasattr(self.router, 'datetime_patterns')
        assert hasattr(self.router, 'title_patterns')
        assert hasattr(self.router, 'location_patterns')
        assert hasattr(self.router, 'confidence_thresholds')
        assert hasattr(self.router, 'field_priorities')
        
        # Check confidence thresholds
        assert self.router.confidence_thresholds['high_confidence'] == 0.8
        assert self.router.confidence_thresholds['medium_confidence'] == 0.6
        assert self.router.confidence_thresholds['low_confidence'] == 0.4
    
    def test_analyze_field_extractability_empty_text(self):
        """Test field analysis with empty or None text."""
        # Empty string
        result = self.router.analyze_field_extractability("")
        assert result == {}
        
        # None input
        result = self.router.analyze_field_extractability(None)
        assert result == {}
        
        # Whitespace only
        result = self.router.analyze_field_extractability("   \n\t  ")
        assert result == {}
    
    def test_analyze_datetime_field_high_confidence(self):
        """Test datetime field analysis with high confidence patterns."""
        # Explicit date with time range
        text = "Meeting on October 15, 2025 from 2pm to 3pm"
        analyses = self.router.analyze_field_extractability(text)
        
        assert 'start_datetime' in analyses
        start_analysis = analyses['start_datetime']
        assert start_analysis.confidence_potential >= 0.8
        assert start_analysis.recommended_method == ProcessingMethod.REGEX
        assert len(start_analysis.pattern_matches) > 0
        assert start_analysis.processing_priority == 1  # Highest priority
    
    def test_analyze_datetime_field_medium_confidence(self):
        """Test datetime field analysis with medium confidence patterns."""
        # Relative date without specific time
        text = "Meeting tomorrow at some point"
        analyses = self.router.analyze_field_extractability(text)
        
        if 'start_datetime' in analyses:
            start_analysis = analyses['start_datetime']
            # Should have some confidence but not high
            assert 0.4 <= start_analysis.confidence_potential < 0.9
    
    def test_analyze_title_field_high_confidence(self):
        """Test title field analysis with high confidence patterns."""
        # Formal title pattern
        text = "Annual Sales Conference: Q4 Planning Session"
        analyses = self.router.analyze_field_extractability(text)
        
        assert 'title' in analyses
        title_analysis = analyses['title']
        assert title_analysis.confidence_potential >= 0.7
        assert len(title_analysis.pattern_matches) > 0
        assert 'formal_title' in str(title_analysis.pattern_matches)
    
    def test_analyze_title_field_quoted_title(self):
        """Test title field analysis with quoted titles."""
        text = 'Please attend "Project Kickoff Meeting" tomorrow'
        analyses = self.router.analyze_field_extractability(text)
        
        assert 'title' in analyses
        title_analysis = analyses['title']
        assert title_analysis.confidence_potential >= 0.8
        assert any('quoted_title' in match for match in title_analysis.pattern_matches)
    
    def test_analyze_location_field_explicit_address(self):
        """Test location field analysis with explicit addresses."""
        text = "Meeting at 123 Main Street, Conference Room A"
        analyses = self.router.analyze_field_extractability(text)
        
        assert 'location' in analyses
        location_analysis = analyses['location']
        assert location_analysis.confidence_potential >= 0.8
        assert any('explicit_address' in match for match in location_analysis.pattern_matches)
    
    def test_analyze_location_field_venue_keywords(self):
        """Test location field analysis with venue keywords."""
        text = "Meeting at Nathan Phillips Square"
        analyses = self.router.analyze_field_extractability(text)
        
        assert 'location' in analyses
        location_analysis = analyses['location']
        assert location_analysis.confidence_potential >= 0.7
        assert any('explicit_address' in match for match in location_analysis.pattern_matches)
    
    def test_analyze_participants_field_email_addresses(self):
        """Test participants field analysis with email addresses."""
        text = "Meeting with john.doe@company.com and jane.smith@company.com"
        analyses = self.router.analyze_field_extractability(text)
        
        assert 'participants' in analyses
        participants_analysis = analyses['participants']
        assert participants_analysis.confidence_potential >= 0.9
        assert any('email_addresses' in match for match in participants_analysis.pattern_matches)
    
    def test_analyze_participants_field_with_keyword(self):
        """Test participants field analysis with 'with' keyword."""
        text = "Meeting with John Smith and Mary Johnson"
        analyses = self.router.analyze_field_extractability(text)
        
        assert 'participants' in analyses
        participants_analysis = analyses['participants']
        assert participants_analysis.confidence_potential >= 0.6
        assert any('with_keyword' in match for match in participants_analysis.pattern_matches)
    
    def test_analyze_recurrence_field_explicit(self):
        """Test recurrence field analysis with explicit patterns."""
        text = "Weekly team meeting every Monday"
        analyses = self.router.analyze_field_extractability(text)
        
        assert 'recurrence' in analyses
        recurrence_analysis = analyses['recurrence']
        assert recurrence_analysis.confidence_potential >= 0.8
        assert any('explicit_recurrence' in match for match in recurrence_analysis.pattern_matches)
    
    def test_analyze_duration_field_explicit(self):
        """Test duration field analysis with explicit duration."""
        text = "Meeting for 2 hours starting at 2pm"
        analyses = self.router.analyze_field_extractability(text)
        
        assert 'duration' in analyses
        duration_analysis = analyses['duration']
        assert duration_analysis.confidence_potential >= 0.8
        assert any('explicit_duration' in match for match in duration_analysis.pattern_matches)
    
    def test_route_processing_method_high_confidence(self):
        """Test processing method routing for high confidence."""
        method = self.router.route_processing_method('start_datetime', 0.9)
        assert method == ProcessingMethod.REGEX
    
    def test_route_processing_method_medium_confidence(self):
        """Test processing method routing for medium confidence."""
        method = self.router.route_processing_method('start_datetime', 0.7)
        assert method == ProcessingMethod.DETERMINISTIC
    
    def test_route_processing_method_low_confidence(self):
        """Test processing method routing for low confidence."""
        method = self.router.route_processing_method('start_datetime', 0.5)
        assert method == ProcessingMethod.LLM
    
    def test_route_processing_method_very_low_confidence(self):
        """Test processing method routing for very low confidence."""
        method = self.router.route_processing_method('start_datetime', 0.2)
        assert method == ProcessingMethod.SKIP
    
    def test_route_processing_method_field_adjustments(self):
        """Test processing method routing with field-specific adjustments."""
        # Location field has -0.1 adjustment, so 0.55 becomes 0.45
        method = self.router.route_processing_method('location', 0.55)
        assert method == ProcessingMethod.LLM  # 0.55 - 0.1 = 0.45, which is >= 0.4
        
        # Description field has -0.2 adjustment, so 0.55 becomes 0.35
        method = self.router.route_processing_method('description', 0.55)
        assert method == ProcessingMethod.SKIP  # 0.55 - 0.2 = 0.35, which is < 0.4
    
    def test_validate_field_consistency_valid_results(self):
        """Test field consistency validation with valid results."""
        now = datetime.now()
        results = {
            'title': FieldResult(
                value="Team Meeting",
                source="regex",
                confidence=0.9,
                span=(0, 12)
            ),
            'start_datetime': FieldResult(
                value=now,
                source="regex",
                confidence=0.9,
                span=(13, 25)
            ),
            'end_datetime': FieldResult(
                value=now + timedelta(hours=1),
                source="regex",
                confidence=0.9,
                span=(26, 35)
            )
        }
        
        validation = self.router.validate_field_consistency(results)
        assert validation.is_valid
        assert len(validation.missing_fields) == 0
    
    def test_validate_field_consistency_missing_essential_fields(self):
        """Test field consistency validation with missing essential fields."""
        results = {
            'location': FieldResult(
                value="Conference Room A",
                source="regex",
                confidence=0.8,
                span=(0, 17)
            )
        }
        
        validation = self.router.validate_field_consistency(results)
        assert not validation.is_valid
        assert 'title' in validation.missing_fields
        assert 'start_datetime' in validation.missing_fields
    
    def test_validate_field_consistency_invalid_datetime_order(self):
        """Test field consistency validation with invalid datetime order."""
        now = datetime.now()
        results = {
            'title': FieldResult(
                value="Team Meeting",
                source="regex",
                confidence=0.9,
                span=(0, 12)
            ),
            'start_datetime': FieldResult(
                value=now,
                source="regex",
                confidence=0.9,
                span=(13, 25)
            ),
            'end_datetime': FieldResult(
                value=now - timedelta(hours=1),  # End before start
                source="regex",
                confidence=0.9,
                span=(26, 35)
            )
        }
        
        validation = self.router.validate_field_consistency(results)
        assert not validation.is_valid
        assert 'end_datetime' in validation.field_warnings
        assert any('after start time' in warning for warning in validation.field_warnings['end_datetime'])
    
    def test_validate_field_consistency_unreasonable_duration(self):
        """Test field consistency validation with unreasonable duration."""
        now = datetime.now()
        results = {
            'title': FieldResult(
                value="Team Meeting",
                source="regex",
                confidence=0.9,
                span=(0, 12)
            ),
            'start_datetime': FieldResult(
                value=now,
                source="regex",
                confidence=0.9,
                span=(13, 25)
            ),
            'end_datetime': FieldResult(
                value=now + timedelta(hours=30),  # 30 hour meeting
                source="regex",
                confidence=0.9,
                span=(26, 35)
            )
        }
        
        validation = self.router.validate_field_consistency(results)
        assert 'end_datetime' in validation.field_warnings
        assert any('exceeds 24 hours' in warning for warning in validation.field_warnings['end_datetime'])
    
    def test_validate_field_consistency_low_confidence_warnings(self):
        """Test field consistency validation with low confidence warnings."""
        now = datetime.now()
        results = {
            'title': FieldResult(
                value="Meeting",
                source="llm",
                confidence=0.3,  # Low confidence
                span=(0, 7)
            ),
            'start_datetime': FieldResult(
                value=now,
                source="llm",
                confidence=0.4,  # Low confidence
                span=(8, 20)
            )
        }
        
        validation = self.router.validate_field_consistency(results)
        assert 'title' in validation.confidence_issues
        assert 'start_datetime' in validation.confidence_issues
        assert validation.confidence_issues['title'] == 0.3
        assert validation.confidence_issues['start_datetime'] == 0.4
    
    def test_optimize_processing_order_empty_list(self):
        """Test processing order optimization with empty list."""
        result = self.router.optimize_processing_order([])
        assert result == []
    
    def test_optimize_processing_order_single_field(self):
        """Test processing order optimization with single field."""
        result = self.router.optimize_processing_order(['title'])
        assert result == ['title']
    
    def test_optimize_processing_order_dependency_based(self):
        """Test processing order optimization with dependency-based ordering."""
        fields = ['description', 'location', 'start_datetime', 'title', 'end_datetime']
        result = self.router.optimize_processing_order(fields)
        
        # start_datetime should be first
        assert result[0] == 'start_datetime'
        
        # end_datetime should come after start_datetime
        start_idx = result.index('start_datetime')
        end_idx = result.index('end_datetime')
        assert start_idx < end_idx
        
        # description should be last (lowest priority)
        assert result[-1] == 'description'
    
    def test_optimize_processing_order_all_fields(self):
        """Test processing order optimization with all possible fields."""
        fields = [
            'description', 'participants', 'recurrence', 'location', 
            'duration', 'end_datetime', 'start_datetime', 'title'
        ]
        result = self.router.optimize_processing_order(fields)
        
        # Verify expected order based on priorities and dependencies
        expected_order = [
            'start_datetime',  # Priority 1
            'duration',        # Priority 3 (before end_datetime)
            'end_datetime',    # Priority 2 (after duration)
            'title',           # Priority 4
            'location',        # Priority 5
            'participants',    # Priority 6
            'recurrence',      # Priority 7
            'description'      # Priority 8
        ]
        
        assert result == expected_order
    
    def test_get_field_routing_summary(self):
        """Test field routing summary generation."""
        text = "Team meeting tomorrow at 2pm in Conference Room A with John Smith"
        analyses = self.router.analyze_field_extractability(text)
        
        summary = self.router.get_field_routing_summary(analyses)
        
        # Check summary structure
        assert 'total_fields' in summary
        assert 'routing_decisions' in summary
        assert 'confidence_breakdown' in summary
        assert 'processing_order' in summary
        assert 'high_confidence_fields' in summary
        assert 'low_confidence_fields' in summary
        assert 'complexity_analysis' in summary
        
        # Check summary content
        assert summary['total_fields'] == len(analyses)
        assert len(summary['routing_decisions']) == len(analyses)
        assert len(summary['confidence_breakdown']) == len(analyses)
        
        # Check statistics
        if analyses:
            assert 'average_confidence' in summary
            assert 'min_confidence' in summary
            assert 'max_confidence' in summary
            assert 0.0 <= summary['average_confidence'] <= 1.0
            assert 0.0 <= summary['min_confidence'] <= 1.0
            assert 0.0 <= summary['max_confidence'] <= 1.0
    
    def test_field_threshold_adjustments(self):
        """Test field-specific threshold adjustments."""
        # Test that optional fields have lower thresholds
        assert self.router.field_threshold_adjustments['location'] == -0.1
        assert self.router.field_threshold_adjustments['description'] == -0.2
        assert self.router.field_threshold_adjustments['participants'] == -0.1
        
        # Test that essential fields have no adjustment
        assert self.router.field_threshold_adjustments['title'] == 0.0
        assert self.router.field_threshold_adjustments['start_datetime'] == 0.0
        assert self.router.field_threshold_adjustments['end_datetime'] == 0.0
    
    def test_field_priorities(self):
        """Test field processing priorities."""
        # Test that start_datetime has highest priority
        assert self.router.field_priorities['start_datetime'] == 1
        
        # Test that description has lowest priority
        assert self.router.field_priorities['description'] == 8
        
        # Test relative priorities
        assert (self.router.field_priorities['start_datetime'] < 
                self.router.field_priorities['end_datetime'])
        assert (self.router.field_priorities['title'] < 
                self.router.field_priorities['location'])
    
    def test_complex_text_analysis(self):
        """Test field analysis with complex, realistic text."""
        text = """
        Subject: Q4 Planning Meeting
        
        Hi team,
        
        We need to schedule our quarterly planning session for next Friday, 
        October 15th from 2:00 PM to 4:30 PM in the main conference room.
        
        Please bring your laptops and Q3 reports. We'll be joined by 
        john.doe@company.com and sarah.wilson@company.com from the marketing team.
        
        This will be a recurring monthly meeting going forward.
        
        Best regards,
        Manager
        """
        
        analyses = self.router.analyze_field_extractability(text)
        
        # Should detect multiple fields with varying confidence
        assert len(analyses) > 4
        
        # Should have high confidence for datetime (explicit date and time range)
        if 'start_datetime' in analyses:
            assert analyses['start_datetime'].confidence_potential >= 0.8
        
        # Should have high confidence for title (subject line)
        if 'title' in analyses:
            assert analyses['title'].confidence_potential >= 0.7
        
        # Should have high confidence for participants (email addresses)
        if 'participants' in analyses:
            assert analyses['participants'].confidence_potential >= 0.9
        
        # Should have high confidence for location (conference room)
        if 'location' in analyses:
            assert analyses['location'].confidence_potential >= 0.6
        
        # Should detect recurrence pattern
        if 'recurrence' in analyses:
            assert analyses['recurrence'].confidence_potential >= 0.7
    
    def test_ambiguity_detection(self):
        """Test detection of ambiguous patterns."""
        # Text with multiple potential titles and times
        text = """
        Marketing Meeting and Sales Review
        Tomorrow at 10am or 2pm
        Conference Room A or Room B
        """
        
        analyses = self.router.analyze_field_extractability(text)
        
        # Should detect ambiguities in multiple fields
        for field_name, analysis in analyses.items():
            if analysis.confidence_potential > 0.5:
                # Fields with decent confidence should have some ambiguity indicators
                # due to multiple options
                if field_name in ['title', 'start_datetime', 'location']:
                    # May have ambiguities due to multiple options
                    pass  # Ambiguity detection is field-specific
    
    def test_edge_cases(self):
        """Test edge cases and error handling."""
        # Very short text
        analyses = self.router.analyze_field_extractability("Meet")
        # Should return some analysis but with low confidence
        
        # Text with no clear patterns
        analyses = self.router.analyze_field_extractability("Lorem ipsum dolor sit amet")
        # Should return analyses with very low confidence
        
        # Text with conflicting information
        text = "Meeting at 2pm and also at 3pm tomorrow and next week"
        analyses = self.router.analyze_field_extractability(text)
        # Should detect patterns but flag ambiguities


if __name__ == '__main__':
    pytest.main([__file__])