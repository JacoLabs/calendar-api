"""
Unit tests for NormalizedEvent class.
Tests standardized output format, confidence scoring, and quality assessment.
"""

import unittest
from datetime import datetime, timedelta
from typing import Dict, Any

from models.event_models import NormalizedEvent, ParsedEvent, Event


class TestNormalizedEvent(unittest.TestCase):
    """Test cases for NormalizedEvent class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.base_datetime = datetime(2025, 1, 15, 14, 0)
        self.end_datetime = datetime(2025, 1, 15, 15, 0)
        
        # Sample normalized event with good quality
        self.good_event = NormalizedEvent(
            title="Team Meeting",
            start_datetime=self.base_datetime,
            end_datetime=self.end_datetime,
            location="Conference Room A",
            description="Weekly team sync meeting",
            confidence_score=0.8,
            field_confidence={
                'title': 0.9,
                'start_datetime': 0.8,
                'end_datetime': 0.8,
                'location': 0.7
            }
        )
        
        # Sample normalized event with quality issues
        self.poor_event = NormalizedEvent(
            title="A",  # Too short
            start_datetime=self.base_datetime,
            end_datetime=self.base_datetime + timedelta(minutes=5),  # Too short duration
            confidence_score=0.3,
            field_confidence={
                'title': 0.2,
                'start_datetime': 0.4,
                'end_datetime': 0.4
            }
        )
        
        # Sample parsed event for conversion testing
        self.sample_parsed_event = ParsedEvent(
            title="Project Review",
            start_datetime=self.base_datetime,
            end_datetime=self.end_datetime,
            location="Room 101",
            description="Monthly project review meeting",
            confidence_score=0.7,
            extraction_metadata={
                'title_confidence': 0.8,
                'datetime_confidence': 0.7,
                'location_confidence': 0.6,
                'multiple_datetime_matches': 2,
                'used_default_duration': False,
                'extraction_method': 'llm'
            }
        )
    
    def test_normalized_event_creation(self):
        """Test basic NormalizedEvent creation."""
        event = NormalizedEvent(
            title="Test Event",
            start_datetime=self.base_datetime,
            end_datetime=self.end_datetime,
            confidence_score=0.8
        )
        
        self.assertEqual(event.title, "Test Event")
        self.assertEqual(event.start_datetime, self.base_datetime)
        self.assertEqual(event.end_datetime, self.end_datetime)
        self.assertEqual(event.confidence_score, 0.8)
        self.assertIsNone(event.location)
        self.assertEqual(event.description, "")
    
    def test_normalized_event_validation_empty_title(self):
        """Test validation fails for empty title."""
        with self.assertRaises(ValueError) as context:
            NormalizedEvent(
                title="",
                start_datetime=self.base_datetime,
                end_datetime=self.end_datetime
            )
        
        self.assertIn("title cannot be empty", str(context.exception))
    
    def test_normalized_event_validation_invalid_datetime(self):
        """Test validation fails for invalid datetime order."""
        with self.assertRaises(ValueError) as context:
            NormalizedEvent(
                title="Test Event",
                start_datetime=self.end_datetime,  # After end time
                end_datetime=self.base_datetime
            )
        
        self.assertIn("start_datetime must be before end_datetime", str(context.exception))
    
    def test_confidence_score_normalization(self):
        """Test confidence scores are normalized to 0.0-1.0 range."""
        event = NormalizedEvent(
            title="Test Event",
            start_datetime=self.base_datetime,
            end_datetime=self.end_datetime,
            confidence_score=1.5,  # Above 1.0
            field_confidence={'title': -0.1, 'start_datetime': 2.0}  # Out of range
        )
        
        self.assertEqual(event.confidence_score, 1.0)
        self.assertEqual(event.field_confidence['title'], 0.0)
        self.assertEqual(event.field_confidence['start_datetime'], 1.0)
    
    def test_field_confidence_methods(self):
        """Test field confidence getter and setter methods."""
        event = self.good_event
        
        # Test getter
        self.assertEqual(event.get_field_confidence('title'), 0.9)
        self.assertEqual(event.get_field_confidence('nonexistent'), 0.8)  # Falls back to overall confidence
        
        # Test setter
        event.set_field_confidence('description', 0.6)
        self.assertEqual(event.get_field_confidence('description'), 0.6)
        
        # Test setter with out-of-range value
        event.set_field_confidence('title', 1.5)
        self.assertEqual(event.get_field_confidence('title'), 1.0)
    
    def test_parsing_issue_methods(self):
        """Test parsing issue and suggestion management."""
        event = self.good_event
        
        # Test adding issues
        event.add_parsing_issue("Test issue 1")
        event.add_parsing_issue("Test issue 2")
        event.add_parsing_issue("Test issue 1")  # Duplicate
        
        self.assertEqual(len(event.parsing_issues), 2)
        self.assertIn("Test issue 1", event.parsing_issues)
        self.assertIn("Test issue 2", event.parsing_issues)
        
        # Test adding suggestions
        event.add_parsing_suggestion("Test suggestion 1")
        event.add_parsing_suggestion("Test suggestion 2")
        event.add_parsing_suggestion("Test suggestion 1")  # Duplicate
        
        self.assertEqual(len(event.parsing_suggestions), 2)
        self.assertIn("Test suggestion 1", event.parsing_suggestions)
        self.assertIn("Test suggestion 2", event.parsing_suggestions)
    
    def test_calculate_quality_score_good_event(self):
        """Test quality score calculation for good event."""
        quality = self.good_event.calculate_quality_score()
        
        self.assertGreater(quality, 0.7)  # Should be high quality
        self.assertEqual(self.good_event.quality_score, quality)
    
    def test_calculate_quality_score_poor_event(self):
        """Test quality score calculation for poor event."""
        quality = self.poor_event.calculate_quality_score()
        
        self.assertLess(quality, 0.5)  # Should be low quality
        self.assertEqual(self.poor_event.quality_score, quality)
    
    def test_calculate_quality_score_with_issues(self):
        """Test quality score calculation with parsing issues."""
        event = self.good_event
        
        # Calculate baseline quality
        baseline_quality = event.calculate_quality_score()
        
        # Add parsing issues
        event.add_parsing_issue("Issue 1")
        event.add_parsing_issue("Issue 2")
        
        # Recalculate quality
        quality_with_issues = event.calculate_quality_score()
        
        # Quality should be lower due to issues
        self.assertLess(quality_with_issues, baseline_quality)
    
    def test_meets_minimum_quality(self):
        """Test minimum quality threshold checking."""
        # Good event should meet default threshold
        self.assertTrue(self.good_event.meets_minimum_quality())
        self.assertTrue(self.good_event.meets_quality_threshold)
        
        # Poor event should not meet default threshold
        self.assertFalse(self.poor_event.meets_minimum_quality())
        self.assertFalse(self.poor_event.meets_quality_threshold)
        
        # Test custom threshold
        self.assertTrue(self.poor_event.meets_minimum_quality(threshold=0.2))
        self.assertFalse(self.poor_event.meets_minimum_quality(threshold=0.8))
    
    def test_get_quality_report(self):
        """Test quality report generation."""
        report = self.good_event.get_quality_report()
        
        # Check report structure
        self.assertIn('overall_quality', report)
        self.assertIn('overall_confidence', report)
        self.assertIn('meets_threshold', report)
        self.assertIn('field_scores', report)
        self.assertIn('recommendations', report)
        self.assertIn('parsing_issues', report)
        self.assertIn('parsing_suggestions', report)
        
        # Check field scores
        self.assertIn('title', report['field_scores'])
        self.assertIn('datetime', report['field_scores'])
        self.assertIn('location', report['field_scores'])
        
        # Check field score structure
        title_score = report['field_scores']['title']
        self.assertIn('confidence', title_score)
        self.assertIn('length', title_score)
        self.assertIn('word_count', title_score)
        self.assertIn('assessment', title_score)
    
    def test_get_quality_report_poor_event(self):
        """Test quality report for poor event includes recommendations."""
        report = self.poor_event.get_quality_report()
        
        # Should have recommendations for improvement
        self.assertGreater(len(report['recommendations']), 0)
        
        # Should have poor assessments
        title_assessment = report['field_scores']['title']['assessment']
        self.assertEqual(title_assessment, 'poor')
    
    def test_to_dict_serialization(self):
        """Test dictionary serialization."""
        event_dict = self.good_event.to_dict()
        
        # Check all required fields are present
        required_fields = [
            'title', 'start_datetime', 'end_datetime', 'location', 'description',
            'confidence_score', 'field_confidence', 'parsing_issues', 'parsing_suggestions',
            'extraction_metadata', 'quality_score', 'meets_quality_threshold'
        ]
        
        for field in required_fields:
            self.assertIn(field, event_dict)
        
        # Check datetime serialization
        self.assertEqual(event_dict['start_datetime'], self.base_datetime.isoformat())
        self.assertEqual(event_dict['end_datetime'], self.end_datetime.isoformat())
    
    def test_from_dict_deserialization(self):
        """Test dictionary deserialization."""
        event_dict = self.good_event.to_dict()
        reconstructed = NormalizedEvent.from_dict(event_dict)
        
        self.assertEqual(reconstructed.title, self.good_event.title)
        self.assertEqual(reconstructed.start_datetime, self.good_event.start_datetime)
        self.assertEqual(reconstructed.end_datetime, self.good_event.end_datetime)
        self.assertEqual(reconstructed.location, self.good_event.location)
        self.assertEqual(reconstructed.confidence_score, self.good_event.confidence_score)
        self.assertEqual(reconstructed.field_confidence, self.good_event.field_confidence)
    
    def test_from_parsed_event_conversion(self):
        """Test conversion from ParsedEvent."""
        normalized = NormalizedEvent.from_parsed_event(self.sample_parsed_event)
        
        self.assertEqual(normalized.title, self.sample_parsed_event.title)
        self.assertEqual(normalized.start_datetime, self.sample_parsed_event.start_datetime)
        self.assertEqual(normalized.end_datetime, self.sample_parsed_event.end_datetime)
        self.assertEqual(normalized.location, self.sample_parsed_event.location)
        self.assertEqual(normalized.confidence_score, self.sample_parsed_event.confidence_score)
        
        # Check field confidence extraction
        self.assertEqual(normalized.get_field_confidence('title'), 0.8)
        self.assertEqual(normalized.get_field_confidence('start_datetime'), 0.7)
        self.assertEqual(normalized.get_field_confidence('location'), 0.6)
        
        # Check parsing issues from metadata
        self.assertIn("Multiple possible dates/times found (2)", normalized.parsing_issues)
    
    def test_from_parsed_event_missing_title(self):
        """Test conversion fails when ParsedEvent lacks title."""
        parsed_event = ParsedEvent(
            start_datetime=self.base_datetime,
            end_datetime=self.end_datetime,
            confidence_score=0.5
        )
        
        with self.assertRaises(ValueError) as context:
            NormalizedEvent.from_parsed_event(parsed_event)
        
        self.assertIn("title is required", str(context.exception))
    
    def test_from_parsed_event_missing_datetime(self):
        """Test conversion fails when ParsedEvent lacks start_datetime."""
        parsed_event = ParsedEvent(
            title="Test Event",
            end_datetime=self.end_datetime,
            confidence_score=0.5
        )
        
        with self.assertRaises(ValueError) as context:
            NormalizedEvent.from_parsed_event(parsed_event)
        
        self.assertIn("start_datetime is required", str(context.exception))
    
    def test_from_parsed_event_default_end_time(self):
        """Test conversion creates default end time when missing."""
        parsed_event = ParsedEvent(
            title="Test Event",
            start_datetime=self.base_datetime,
            confidence_score=0.5
        )
        
        normalized = NormalizedEvent.from_parsed_event(parsed_event)
        
        expected_end = self.base_datetime + timedelta(hours=1)
        self.assertEqual(normalized.end_datetime, expected_end)
    
    def test_from_parsed_event_with_metadata_issues(self):
        """Test conversion handles various metadata issues."""
        parsed_event = ParsedEvent(
            title="Test Event",
            start_datetime=self.base_datetime,
            end_datetime=self.end_datetime,
            confidence_score=0.5,
            extraction_metadata={
                'has_ambiguous_datetime': True,
                'multiple_title_matches': 3,
                'used_default_duration': True,
                'extraction_method': 'regex_fallback'
            }
        )
        
        normalized = NormalizedEvent.from_parsed_event(parsed_event)
        
        # Check that issues were added
        self.assertIn("Date/time information was ambiguous", normalized.parsing_issues)
        self.assertIn("Multiple possible titles found (3)", normalized.parsing_issues)
        self.assertIn("LLM extraction failed, used regex fallback", normalized.parsing_issues)
        self.assertIn("Used default 1-hour duration - consider specifying end time", normalized.parsing_suggestions)
    
    def test_from_event_conversion(self):
        """Test conversion from finalized Event."""
        event = Event(
            title="Finalized Event",
            start_datetime=self.base_datetime,
            end_datetime=self.end_datetime,
            location="Final Location",
            description="Final description"
        )
        
        normalized = NormalizedEvent.from_event(event, confidence_score=0.95)
        
        self.assertEqual(normalized.title, event.title)
        self.assertEqual(normalized.start_datetime, event.start_datetime)
        self.assertEqual(normalized.end_datetime, event.end_datetime)
        self.assertEqual(normalized.location, event.location)
        self.assertEqual(normalized.confidence_score, 0.95)
        
        # All field confidences should be high
        self.assertEqual(normalized.get_field_confidence('title'), 0.95)
        self.assertEqual(normalized.get_field_confidence('start_datetime'), 0.95)
        self.assertEqual(normalized.get_field_confidence('location'), 0.95)
        
        # Quality should be high for finalized events
        quality = normalized.calculate_quality_score()
        self.assertGreater(quality, 0.8)
    
    def test_quality_score_title_factors(self):
        """Test quality score calculation for different title characteristics."""
        base_event_data = {
            'start_datetime': self.base_datetime,
            'end_datetime': self.end_datetime,
            'confidence_score': 0.8
        }
        
        # Test optimal title length and word count
        good_title_event = NormalizedEvent(title="Weekly Team Meeting", **base_event_data)
        good_quality = good_title_event.calculate_quality_score()
        
        # Test very short title
        short_title_event = NormalizedEvent(title="A", **base_event_data)
        short_quality = short_title_event.calculate_quality_score()
        
        # Test very long title
        long_title = "This is an extremely long title that goes on and on and probably contains way too much information for a simple event title"
        long_title_event = NormalizedEvent(title=long_title, **base_event_data)
        long_quality = long_title_event.calculate_quality_score()
        
        # Test truncated title
        truncated_title_event = NormalizedEvent(title="Meeting with...", **base_event_data)
        truncated_quality = truncated_title_event.calculate_quality_score()
        
        # Good title should have highest quality
        self.assertGreater(good_quality, short_quality)
        self.assertGreater(good_quality, long_quality)
        self.assertGreater(good_quality, truncated_quality)
    
    def test_quality_score_duration_factors(self):
        """Test quality score calculation for different event durations."""
        base_event_data = {
            'title': 'Test Meeting',
            'start_datetime': self.base_datetime,
            'confidence_score': 0.8
        }
        
        # Test optimal duration (1 hour)
        optimal_event = NormalizedEvent(
            end_datetime=self.base_datetime + timedelta(hours=1),
            **base_event_data
        )
        optimal_quality = optimal_event.calculate_quality_score()
        
        # Test very short duration (5 minutes)
        short_event = NormalizedEvent(
            end_datetime=self.base_datetime + timedelta(minutes=5),
            **base_event_data
        )
        short_quality = short_event.calculate_quality_score()
        
        # Test very long duration (12 hours)
        long_event = NormalizedEvent(
            end_datetime=self.base_datetime + timedelta(hours=12),
            **base_event_data
        )
        long_quality = long_event.calculate_quality_score()
        
        # Optimal duration should have highest quality
        self.assertGreater(optimal_quality, short_quality)
        self.assertGreater(optimal_quality, long_quality)
    
    def test_string_field_normalization(self):
        """Test that string fields are properly normalized."""
        event = NormalizedEvent(
            title="  Test Event  ",  # Extra whitespace
            start_datetime=self.base_datetime,
            end_datetime=self.end_datetime,
            location="  Conference Room  ",  # Extra whitespace
            description="  Event description  "  # Extra whitespace
        )
        
        self.assertEqual(event.title, "Test Event")
        self.assertEqual(event.location, "Conference Room")
        self.assertEqual(event.description, "Event description")
    
    def test_empty_location_normalization(self):
        """Test that empty location strings are converted to None."""
        event = NormalizedEvent(
            title="Test Event",
            start_datetime=self.base_datetime,
            end_datetime=self.end_datetime,
            location="   "  # Only whitespace
        )
        
        self.assertIsNone(event.location)


if __name__ == '__main__':
    unittest.main()