"""
Unit tests for Microsoft Recognizers-Text integration.

Tests the RecognizersExtractor class for multi-language entity recognition,
confidence scoring, and span validation.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone, timedelta
import sys
import os

# Add the parent directory to the path to import modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.recognizers_extractor import RecognizersExtractor
from models.event_models import FieldResult


class TestRecognizersExtractor(unittest.TestCase):
    """Test cases for RecognizersExtractor class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.extractor = RecognizersExtractor()
    
    @patch('services.recognizers_extractor.RECOGNIZERS_AVAILABLE', False)
    def test_service_unavailable(self):
        """Test behavior when Microsoft Recognizers-Text is not available."""
        extractor = RecognizersExtractor()
        
        # Service should not be available
        self.assertFalse(extractor.is_service_available())
        
        # Extraction should return empty result
        result = extractor.extract_with_recognizers("tomorrow at 2pm", "datetime")
        
        self.assertIsNone(result.value)
        self.assertEqual(result.source, "recognizers")
        self.assertEqual(result.confidence, 0.0)
        self.assertEqual(result.span, (0, 0))
        self.assertEqual(result.alternatives, [])
        self.assertGreater(result.processing_time_ms, 0)
    
    @patch('services.recognizers_extractor.RECOGNIZERS_AVAILABLE', True)
    @patch('services.recognizers_extractor.DateTimeRecognizer')
    def test_datetime_extraction_success(self, mock_datetime_recognizer_class):
        """Test successful datetime extraction."""
        # Mock the recognizer instance and results
        mock_recognizer = Mock()
        mock_model = Mock()
        mock_recognizer.get_datetime_model.return_value = mock_model
        mock_datetime_recognizer_class.return_value = mock_recognizer
        
        # Create mock recognition result
        mock_result = Mock()
        mock_result.start = 0
        mock_result.end = 16
        mock_result.type_name = "datetimeV2.datetime"
        mock_result.resolution = {
            'values': [{
                'value': '2024-01-15T14:00:00'
            }]
        }
        
        mock_model.parse.return_value = [mock_result]
        
        # Create extractor and test
        extractor = RecognizersExtractor()
        result = extractor.extract_with_recognizers("tomorrow at 2pm", "datetime")
        
        # Verify result
        self.assertIsNotNone(result.value)
        self.assertIsInstance(result.value, datetime)
        self.assertEqual(result.source, "recognizers")
        self.assertGreaterEqual(result.confidence, 0.6)
        self.assertLessEqual(result.confidence, 0.8)
        self.assertEqual(result.span, (0, 16))
        self.assertGreater(result.processing_time_ms, 0)
    
    @patch('services.recognizers_extractor.RECOGNIZERS_AVAILABLE', True)
    @patch('services.recognizers_extractor.DateTimeRecognizer')
    def test_datetime_extraction_time_range(self, mock_datetime_recognizer_class):
        """Test datetime extraction with time range."""
        mock_recognizer = Mock()
        mock_model = Mock()
        mock_recognizer.get_datetime_model.return_value = mock_model
        mock_datetime_recognizer_class.return_value = mock_recognizer
        
        # Mock time range result
        mock_result = Mock()
        mock_result.start = 0
        mock_result.end = 20
        mock_result.type_name = "datetimeV2.datetimerange"
        mock_result.resolution = {
            'values': [{
                'start': '2024-01-15T14:00:00',
                'end': '2024-01-15T16:00:00'
            }]
        }
        
        mock_model.parse.return_value = [mock_result]
        
        extractor = RecognizersExtractor()
        
        # Test start datetime extraction
        result_start = extractor.extract_with_recognizers("2pm to 4pm today", "start_datetime")
        self.assertIsNotNone(result_start.value)
        self.assertEqual(result_start.value.hour, 14)
        
        # Test end datetime extraction
        result_end = extractor.extract_with_recognizers("2pm to 4pm today", "end_datetime")
        self.assertIsNotNone(result_end.value)
        self.assertEqual(result_end.value.hour, 16)
    
    @patch('services.recognizers_extractor.RECOGNIZERS_AVAILABLE', True)
    @patch('services.recognizers_extractor.NumberRecognizer')
    def test_number_extraction_success(self, mock_number_recognizer_class):
        """Test successful number extraction."""
        mock_recognizer = Mock()
        mock_model = Mock()
        mock_recognizer.get_number_model.return_value = mock_model
        mock_number_recognizer_class.return_value = mock_recognizer
        
        # Mock number result
        mock_result = Mock()
        mock_result.start = 4
        mock_result.end = 6
        mock_result.type_name = "number"
        mock_result.resolution = {
            'value': '45'
        }
        
        mock_model.parse.return_value = [mock_result]
        
        extractor = RecognizersExtractor()
        result = extractor.extract_with_recognizers("for 45 minutes", "number")
        
        # Verify result
        self.assertEqual(result.value, 45.0)
        self.assertEqual(result.source, "recognizers")
        self.assertGreaterEqual(result.confidence, 0.6)
        self.assertLessEqual(result.confidence, 0.8)
        self.assertEqual(result.span, (4, 6))
    
    @patch('services.recognizers_extractor.RECOGNIZERS_AVAILABLE', True)
    @patch('services.recognizers_extractor.DateTimeRecognizer')
    def test_datetime_extraction_no_results(self, mock_datetime_recognizer_class):
        """Test datetime extraction when no entities are found."""
        mock_recognizer = Mock()
        mock_model = Mock()
        mock_recognizer.get_datetime_model.return_value = mock_model
        mock_datetime_recognizer_class.return_value = mock_recognizer
        mock_model.parse.return_value = []
        
        extractor = RecognizersExtractor()
        result = extractor.extract_with_recognizers("no date here", "datetime")
        
        # Should return empty result
        self.assertIsNone(result.value)
        self.assertEqual(result.confidence, 0.0)
        self.assertEqual(result.span, (0, 0))
        self.assertEqual(result.alternatives, [])
    
    @patch('services.recognizers_extractor.RECOGNIZERS_AVAILABLE', True)
    @patch('services.recognizers_extractor.DateTimeRecognizer')
    def test_datetime_extraction_with_alternatives(self, mock_datetime_recognizer_class):
        """Test datetime extraction with multiple possible interpretations."""
        mock_recognizer = Mock()
        mock_model = Mock()
        mock_recognizer.get_datetime_model.return_value = mock_model
        mock_datetime_recognizer_class.return_value = mock_recognizer
        
        # Mock multiple results
        mock_result1 = Mock()
        mock_result1.start = 0
        mock_result1.end = 8
        mock_result1.type_name = "datetimeV2.datetime"
        mock_result1.resolution = {
            'values': [{'value': '2024-01-15T14:00:00'}]
        }
        
        mock_result2 = Mock()
        mock_result2.start = 9
        mock_result2.end = 17
        mock_result2.type_name = "datetimeV2.datetime"
        mock_result2.resolution = {
            'values': [{'value': '2024-01-15T16:00:00'}]
        }
        
        mock_model.parse.return_value = [mock_result1, mock_result2]
        
        extractor = RecognizersExtractor()
        result = extractor.extract_with_recognizers("tomorrow at 4pm", "datetime")
        
        # Should have alternatives
        self.assertIsNotNone(result.value)
        self.assertGreater(len(result.alternatives), 0)
    
    def test_confidence_calculation_datetime(self):
        """Test confidence calculation for datetime results."""
        extractor = RecognizersExtractor()
        
        # Mock result with good coverage
        mock_result = Mock()
        mock_result.start = 0
        mock_result.end = 10
        mock_result.type_name = "datetimeV2.datetime"
        mock_result.resolution = {
            'values': [{'value': '2024-01-15T14:00:00'}]
        }
        
        confidence = extractor._calculate_datetime_confidence(mock_result, "tomorrow 2pm")
        
        # Should be in deterministic backup range
        self.assertGreaterEqual(confidence, 0.6)
        self.assertLessEqual(confidence, 0.8)
    
    def test_confidence_calculation_number(self):
        """Test confidence calculation for number results."""
        extractor = RecognizersExtractor()
        
        # Mock number result
        mock_result = Mock()
        mock_result.start = 0
        mock_result.end = 2
        mock_result.resolution = {'value': '45'}
        
        confidence = extractor._calculate_number_confidence(mock_result, "45")
        
        # Should be in deterministic backup range
        self.assertGreaterEqual(confidence, 0.6)
        self.assertLessEqual(confidence, 0.8)
    
    def test_span_validation(self):
        """Test span validation functionality."""
        extractor = RecognizersExtractor()
        text = "Meeting tomorrow at 2pm"
        
        # Valid spans
        self.assertTrue(extractor.validate_span(text, (0, 7)))  # "Meeting"
        self.assertTrue(extractor.validate_span(text, (8, 16)))  # "tomorrow"
        self.assertTrue(extractor.validate_span(text, (0, len(text))))  # Full text
        
        # Invalid spans
        self.assertFalse(extractor.validate_span(text, (-1, 5)))  # Negative start
        self.assertFalse(extractor.validate_span(text, (0, len(text) + 1)))  # Beyond end
        self.assertFalse(extractor.validate_span(text, (10, 5)))  # Start > end
        self.assertFalse(extractor.validate_span(text, (5, 5)))  # Zero length
    
    def test_datetime_string_parsing(self):
        """Test parsing of various datetime string formats."""
        extractor = RecognizersExtractor()
        
        # ISO format with timezone
        dt1 = extractor._parse_datetime_string("2024-01-15T14:00:00Z")
        self.assertIsNotNone(dt1)
        self.assertEqual(dt1.hour, 14)
        self.assertEqual(dt1.tzinfo, timezone.utc)
        
        # ISO format without timezone
        dt2 = extractor._parse_datetime_string("2024-01-15T14:00:00")
        self.assertIsNotNone(dt2)
        self.assertEqual(dt2.hour, 14)
        self.assertEqual(dt2.tzinfo, timezone.utc)
        
        # Date only
        dt3 = extractor._parse_datetime_string("2024-01-15")
        self.assertIsNotNone(dt3)
        self.assertEqual(dt3.year, 2024)
        self.assertEqual(dt3.month, 1)
        self.assertEqual(dt3.day, 15)
        
        # Time only
        dt4 = extractor._parse_datetime_string("14:30")
        self.assertIsNotNone(dt4)
        self.assertEqual(dt4.hour, 14)
        self.assertEqual(dt4.minute, 30)
        
        # Invalid format
        dt5 = extractor._parse_datetime_string("invalid")
        self.assertIsNone(dt5)
    
    def test_best_result_selection(self):
        """Test selection of best result from multiple candidates."""
        extractor = RecognizersExtractor()
        
        # Mock results with different spans
        result1 = Mock()
        result1.start = 0
        result1.end = 20  # Longer span
        result1.type_name = "datetimeV2.datetime"
        
        result2 = Mock()
        result2.start = 5
        result2.end = 10  # Shorter span (should be preferred)
        result2.type_name = "datetimeV2.datetime"
        
        result3 = Mock()
        result3.start = 15
        result3.end = 25  # Later position
        result3.type_name = "datetimeV2.datetime"
        
        results = [result1, result2, result3]
        best = extractor._select_best_datetime_result(results, "datetime")
        
        # Should select result2 (shortest span)
        self.assertEqual(best, result2)
    
    @patch('services.recognizers_extractor.RECOGNIZERS_AVAILABLE', True)
    @patch('services.recognizers_extractor.DateTimeRecognizer')
    @patch('services.recognizers_extractor.NumberRecognizer')
    def test_multiple_fields_extraction(self, mock_number_recognizer_class, mock_datetime_recognizer_class):
        """Test extraction of multiple fields efficiently."""
        # Mock recognizers
        mock_datetime_recognizer = Mock()
        mock_number_recognizer = Mock()
        mock_datetime_recognizer_class.return_value = mock_datetime_recognizer
        mock_number_recognizer_class.return_value = mock_number_recognizer
        
        # Mock datetime model and result
        mock_dt_model = Mock()
        mock_datetime_recognizer.get_datetime_model.return_value = mock_dt_model
        mock_dt_result = Mock()
        mock_dt_result.start = 0
        mock_dt_result.end = 8
        mock_dt_result.type_name = "datetimeV2.datetime"
        mock_dt_result.resolution = {
            'values': [{'value': '2024-01-15T14:00:00'}]
        }
        mock_dt_model.parse.return_value = [mock_dt_result]
        
        # Mock number model and result
        mock_num_model = Mock()
        mock_number_recognizer.get_number_model.return_value = mock_num_model
        mock_num_result = Mock()
        mock_num_result.start = 9
        mock_num_result.end = 11
        mock_num_result.type_name = "number"
        mock_num_result.resolution = {'value': '45'}
        mock_num_model.parse.return_value = [mock_num_result]
        
        extractor = RecognizersExtractor()
        results = extractor.extract_multiple_fields(
            "tomorrow 45 minutes",
            ["datetime", "start_datetime", "number"]
        )
        
        # Should have results for all requested fields
        self.assertIn("datetime", results)
        self.assertIn("start_datetime", results)
        self.assertIn("number", results)
        
        # Datetime fields should have datetime values
        self.assertIsInstance(results["datetime"].value, datetime)
        self.assertIsInstance(results["start_datetime"].value, datetime)
        
        # Number field should have numeric value
        self.assertEqual(results["number"].value, 45.0)
    
    def test_supported_cultures(self):
        """Test getting supported cultures."""
        extractor = RecognizersExtractor()
        cultures = extractor.get_supported_cultures()
        
        # Should return a list of culture codes
        self.assertIsInstance(cultures, list)
        
        # Should include common cultures (if recognizers available)
        if extractor.is_service_available():
            self.assertGreater(len(cultures), 0)
    
    def test_culture_setting(self):
        """Test setting culture for recognition."""
        extractor = RecognizersExtractor()
        
        # Mock supported cultures
        with patch.object(extractor, 'get_supported_cultures', return_value=['en-us', 'es-es', 'fr-fr']):
            # Set valid culture
            extractor.set_culture('es-es')
            self.assertEqual(extractor.default_culture, 'es-es')
            
            # Try to set invalid culture (should not change)
            original_culture = extractor.default_culture
            extractor.set_culture('invalid-culture')
            self.assertEqual(extractor.default_culture, original_culture)
    
    @patch('services.recognizers_extractor.RECOGNIZERS_AVAILABLE', True)
    @patch('services.recognizers_extractor.DateTimeRecognizer')
    def test_extraction_exception_handling(self, mock_datetime_recognizer_class):
        """Test handling of exceptions during extraction."""
        # Mock recognizer that raises exception
        mock_recognizer = Mock()
        mock_model = Mock()
        mock_model.parse.side_effect = Exception("Recognition failed")
        mock_recognizer.get_datetime_model.return_value = mock_model
        mock_datetime_recognizer_class.return_value = mock_recognizer
        
        extractor = RecognizersExtractor()
        result = extractor.extract_with_recognizers("tomorrow at 2pm", "datetime")
        
        # Should handle exception gracefully
        self.assertIsNone(result.value)
        self.assertEqual(result.confidence, 0.0)
        self.assertEqual(result.source, "recognizers")
        self.assertGreater(result.processing_time_ms, 0)
    
    def test_unsupported_field_type(self):
        """Test extraction with unsupported field type."""
        extractor = RecognizersExtractor()
        result = extractor.extract_with_recognizers("some text", "unsupported_field")
        
        # Should return empty result
        self.assertIsNone(result.value)
        self.assertEqual(result.confidence, 0.0)
        self.assertEqual(result.source, "recognizers")
    
    def test_value_extraction_edge_cases(self):
        """Test value extraction with edge cases."""
        extractor = RecognizersExtractor()
        
        # Mock result with no resolution
        mock_result = Mock()
        mock_result.resolution = None
        
        value = extractor._extract_datetime_value(mock_result, "datetime")
        self.assertIsNone(value)
        
        # Mock result with empty values
        mock_result.resolution = {'values': []}
        value = extractor._extract_datetime_value(mock_result, "datetime")
        self.assertIsNone(value)
        
        # Mock result with malformed value
        mock_result.resolution = {'values': [{'value': 'invalid-datetime'}]}
        value = extractor._extract_datetime_value(mock_result, "datetime")
        self.assertIsNone(value)


class TestRecognizersExtractorIntegration(unittest.TestCase):
    """Integration tests for RecognizersExtractor (require actual library)."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.extractor = RecognizersExtractor()
    
    def test_real_datetime_extraction(self):
        """Test real datetime extraction if library is available."""
        if not self.extractor.is_service_available():
            self.skipTest("Microsoft Recognizers-Text not available")
        
        # Test various datetime formats
        test_cases = [
            ("tomorrow at 2pm", "datetime"),
            ("next Friday", "date"),
            ("in 30 minutes", "duration"),
            ("2024-01-15 14:30", "datetime")
        ]
        
        for text, field in test_cases:
            with self.subTest(text=text, field=field):
                result = self.extractor.extract_with_recognizers(text, field)
                
                # Should have reasonable processing time
                self.assertGreater(result.processing_time_ms, 0)
                self.assertLess(result.processing_time_ms, 5000)  # Less than 5 seconds
                
                # Source should be correct
                self.assertEqual(result.source, "recognizers")
                
                # If extraction succeeded, confidence should be in range
                if result.value is not None:
                    self.assertGreaterEqual(result.confidence, 0.6)
                    self.assertLessEqual(result.confidence, 0.8)
    
    def test_real_number_extraction(self):
        """Test real number extraction if library is available."""
        if not self.extractor.is_service_available():
            self.skipTest("Microsoft Recognizers-Text not available")
        
        test_cases = [
            "for 45 minutes",
            "30 people",
            "room 123",
            "first floor"
        ]
        
        for text in test_cases:
            with self.subTest(text=text):
                result = self.extractor.extract_with_recognizers(text, "number")
                
                # Should have reasonable processing time
                self.assertGreater(result.processing_time_ms, 0)
                self.assertLess(result.processing_time_ms, 5000)
                
                # Source should be correct
                self.assertEqual(result.source, "recognizers")
    
    def test_real_multi_language_support(self):
        """Test multi-language support if library is available."""
        if not self.extractor.is_service_available():
            self.skipTest("Microsoft Recognizers-Text not available")
        
        # Test with different cultures (if supported)
        cultures = self.extractor.get_supported_cultures()
        
        if len(cultures) > 1:
            # Test with a different culture
            original_culture = self.extractor.default_culture
            
            try:
                # Try Spanish if available
                if 'es-es' in cultures or any('es' in c.lower() for c in cultures):
                    spanish_culture = next((c for c in cultures if 'es' in c.lower()), cultures[1])
                    self.extractor.set_culture(spanish_culture)
                    
                    result = self.extractor.extract_with_recognizers("mañana a las 2", "datetime")
                    
                    # Should process without error
                    self.assertEqual(result.source, "recognizers")
                    self.assertGreater(result.processing_time_ms, 0)
            
            finally:
                # Restore original culture
                self.extractor.set_culture(original_culture)


if __name__ == '__main__':
    unittest.main()