"""
Unit tests for ComprehensiveErrorHandler class.
Tests error handling scenarios, fallback mechanisms, and user interaction flows.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from typing import List, Dict, Any

from services.comprehensive_error_handler import (
    ComprehensiveErrorHandler, 
    ErrorHandlingResult, 
    InterpretationOption
)
from models.event_models import ParsedEvent, ValidationResult, TitleResult


class TestComprehensiveErrorHandler(unittest.TestCase):
    """Test cases for ComprehensiveErrorHandler class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.handler = ComprehensiveErrorHandler()
        self.sample_text = "Meeting tomorrow at 2pm in Conference Room A"
        
        # Sample parsed event with good confidence
        self.good_event = ParsedEvent(
            title="Meeting",  # Use a title that matches the sample text
            start_datetime=datetime(2025, 1, 15, 14, 0),  # Use future date to avoid consistency issues
            end_datetime=datetime(2025, 1, 15, 15, 0),
            location="Conference Room A",
            description=self.sample_text,
            confidence_score=0.8,
            extraction_metadata={
                'datetime_confidence': 0.9,
                'title_confidence': 0.8,
                'location_confidence': 0.7
            }
        )
        
        # Sample parsed event with low confidence
        self.low_confidence_event = ParsedEvent(
            title="Meeting",
            start_datetime=datetime(2024, 1, 15, 14, 0),
            end_datetime=datetime(2024, 1, 15, 15, 0),
            confidence_score=0.2,
            extraction_metadata={
                'datetime_confidence': 0.3,
                'title_confidence': 0.2
            }
        )
        
        # Sample parsed event with missing critical fields
        self.incomplete_event = ParsedEvent(
            location="Conference Room A",
            description=self.sample_text,
            confidence_score=0.5,
            extraction_metadata={}
        )
        
        # Sample parsed event with multiple interpretations
        self.ambiguous_event = ParsedEvent(
            title="Meeting",
            start_datetime=datetime(2024, 1, 15, 14, 0),
            end_datetime=datetime(2024, 1, 15, 15, 0),
            confidence_score=0.6,
            extraction_metadata={
                'multiple_datetime_matches': 2,
                'multiple_title_matches': 2,
                'all_datetime_matches': [
                    {
                        'datetime': '2024-01-15T14:00:00',
                        'confidence': 0.8,
                        'pattern_type': 'relative_time',
                        'matched_text': 'tomorrow at 2pm'
                    },
                    {
                        'datetime': '2024-01-16T14:00:00',
                        'confidence': 0.6,
                        'pattern_type': 'relative_date',
                        'matched_text': 'next day at 2pm'
                    }
                ],
                'all_title_matches': [
                    {
                        'title': 'Team Meeting',
                        'confidence': 0.7,
                        'extraction_type': 'explicit',
                        'matched_text': 'Team Meeting'
                    },
                    {
                        'title': 'Meeting',
                        'confidence': 0.5,
                        'extraction_type': 'generic',
                        'matched_text': 'Meeting'
                    }
                ]
            }
        )
    
    def test_handle_parsing_errors_no_errors(self):
        """Test handling when no errors are detected."""
        result = self.handler.handle_parsing_errors(self.good_event, self.sample_text)
        
        self.assertTrue(result.success)
        self.assertEqual(result.error_type, "none")
        self.assertEqual(result.resolved_event, self.good_event)
        self.assertEqual(result.error_message, "No errors detected")
    
    def test_handle_parsing_errors_none_event(self):
        """Test handling when parsed_event is None."""
        with patch.object(self.handler, '_handle_no_event_found') as mock_handle:
            mock_handle.return_value = ErrorHandlingResult(
                success=False,
                error_type="no_event_found",
                error_message="No event information detected"
            )
            
            result = self.handler.handle_parsing_errors(None, self.sample_text)
            
            mock_handle.assert_called_once_with(self.sample_text, True)
            self.assertFalse(result.success)
            self.assertEqual(result.error_type, "no_event_found")
    
    def test_handle_parsing_errors_low_confidence(self):
        """Test handling low confidence extraction."""
        with patch.object(self.handler, '_handle_low_confidence') as mock_handle:
            mock_handle.return_value = ErrorHandlingResult(
                success=True,
                resolved_event=self.low_confidence_event,
                error_type="low_confidence"
            )
            
            result = self.handler.handle_parsing_errors(self.low_confidence_event, self.sample_text)
            
            mock_handle.assert_called_once_with(self.low_confidence_event, self.sample_text, True)
            self.assertTrue(result.success)
            self.assertEqual(result.error_type, "low_confidence")
    
    def test_handle_parsing_errors_multiple_interpretations(self):
        """Test handling multiple interpretations."""
        with patch.object(self.handler, '_handle_multiple_interpretations') as mock_handle:
            mock_handle.return_value = ErrorHandlingResult(
                success=True,
                resolved_event=self.ambiguous_event,
                error_type="multiple_interpretations"
            )
            
            result = self.handler.handle_parsing_errors(self.ambiguous_event, self.sample_text)
            
            mock_handle.assert_called_once_with(self.ambiguous_event, self.sample_text)
            self.assertTrue(result.success)
            self.assertEqual(result.error_type, "multiple_interpretations")
    
    def test_handle_parsing_errors_missing_critical_fields(self):
        """Test handling missing critical fields."""
        with patch.object(self.handler, '_handle_missing_critical_fields') as mock_handle:
            mock_handle.return_value = ErrorHandlingResult(
                success=True,
                resolved_event=self.incomplete_event,
                error_type="missing_critical_fields"
            )
            
            result = self.handler.handle_parsing_errors(self.incomplete_event, self.sample_text)
            
            mock_handle.assert_called_once()
            self.assertTrue(result.success)
            self.assertEqual(result.error_type, "missing_critical_fields")
    
    def test_handle_llm_failure_with_regex_fallback(self):
        """Test LLM failure handling with successful regex fallback."""
        fallback_event = ParsedEvent(
            title="Fallback Meeting",
            start_datetime=datetime(2024, 1, 15, 14, 0),
            confidence_score=0.6
        )
        
        with patch.object(self.handler, '_regex_fallback_extraction') as mock_fallback:
            mock_fallback.return_value = fallback_event
            
            result = self.handler.handle_llm_failure(self.sample_text, "LLM service unavailable")
            
            self.assertTrue(result.success)
            self.assertEqual(result.error_type, "llm_failure")
            self.assertEqual(result.fallback_used, "regex")
            self.assertIn("LLM service unavailable", result.error_message)
            
            # Check that confidence was reduced
            self.assertEqual(result.resolved_event.confidence_score, 0.48)  # 0.6 * 0.8
            
            # Check metadata
            metadata = result.resolved_event.extraction_metadata
            self.assertTrue(metadata['llm_failure'])
            self.assertEqual(metadata['llm_error'], "LLM service unavailable")
    
    def test_handle_llm_failure_no_fallback_config(self):
        """Test LLM failure when regex fallback is disabled."""
        self.handler.set_config(fallback_to_regex=False)
        
        result = self.handler.handle_llm_failure(self.sample_text, "LLM error")
        
        self.assertFalse(result.success)
        self.assertEqual(result.error_type, "llm_failure")
        self.assertEqual(result.fallback_used, "none")
    
    def test_handle_llm_failure_fallback_fails(self):
        """Test LLM failure when regex fallback also fails."""
        with patch.object(self.handler, '_regex_fallback_extraction') as mock_fallback:
            mock_fallback.return_value = None
            
            with patch.object(self.handler, '_handle_no_event_found') as mock_no_event:
                mock_no_event.return_value = ErrorHandlingResult(
                    success=False,
                    error_type="no_event_found"
                )
                
                result = self.handler.handle_llm_failure(self.sample_text, "LLM error")
                
                mock_no_event.assert_called_once_with(self.sample_text, llm_available=False)
                self.assertFalse(result.success)
    
    @patch('services.comprehensive_error_handler.is_non_interactive')
    def test_resolve_ambiguous_field_single_option(self, mock_non_interactive):
        """Test resolving ambiguous field with single option."""
        options = [
            InterpretationOption(
                field_name='title',
                value='Team Meeting',
                confidence=0.8,
                source='llm'
            )
        ]
        
        value, method = self.handler.resolve_ambiguous_field('title', options)
        
        self.assertEqual(value, 'Team Meeting')
        self.assertEqual(method, 'single_option')
    
    @patch('services.comprehensive_error_handler.is_non_interactive')
    def test_resolve_ambiguous_field_non_interactive(self, mock_non_interactive):
        """Test resolving ambiguous field in non-interactive mode."""
        mock_non_interactive.return_value = True
        
        options = [
            InterpretationOption(
                field_name='title',
                value='Team Meeting',
                confidence=0.8,
                source='llm'
            ),
            InterpretationOption(
                field_name='title',
                value='Meeting',
                confidence=0.6,
                source='regex'
            )
        ]
        
        value, method = self.handler.resolve_ambiguous_field('title', options)
        
        self.assertEqual(value, 'Team Meeting')  # Highest confidence
        self.assertEqual(method, 'auto_selected_llm')
    
    @patch('services.comprehensive_error_handler.get_choice')
    @patch('services.comprehensive_error_handler.is_non_interactive')
    def test_resolve_ambiguous_field_interactive(self, mock_non_interactive, mock_get_choice):
        """Test resolving ambiguous field with user interaction."""
        mock_non_interactive.return_value = False
        mock_get_choice.return_value = 1  # Select second option
        
        options = [
            InterpretationOption(
                field_name='title',
                value='Team Meeting',
                confidence=0.8,
                source='llm'
            ),
            InterpretationOption(
                field_name='title',
                value='Project Meeting',
                confidence=0.7,
                source='regex'
            )
        ]
        
        value, method = self.handler.resolve_ambiguous_field('title', options)
        
        self.assertEqual(value, 'Project Meeting')  # User selected second option
        self.assertEqual(method, 'user_selected_regex')
    
    @patch('services.comprehensive_error_handler.safe_input')
    @patch('services.comprehensive_error_handler.get_choice')
    @patch('services.comprehensive_error_handler.is_non_interactive')
    def test_resolve_ambiguous_field_custom_input(self, mock_non_interactive, mock_get_choice, mock_safe_input):
        """Test resolving ambiguous field with custom user input."""
        mock_non_interactive.return_value = False
        mock_get_choice.return_value = 2  # Select custom input option
        mock_safe_input.return_value = "Custom Meeting Title"
        
        options = [
            InterpretationOption(
                field_name='title',
                value='Team Meeting',
                confidence=0.8,
                source='llm'
            ),
            InterpretationOption(
                field_name='title',
                value='Project Meeting',
                confidence=0.7,
                source='regex'
            )
        ]
        
        value, method = self.handler.resolve_ambiguous_field('title', options)
        
        self.assertEqual(value, "Custom Meeting Title")
        self.assertEqual(method, 'user_custom')
    
    def test_validate_field_consistency_title_mismatch(self):
        """Test consistency validation for title that doesn't match text."""
        event = ParsedEvent(
            title="Completely Different Title",
            start_datetime=datetime(2024, 1, 15, 14, 0)
        )
        
        issues = self.handler.validate_field_consistency(event, "Meeting tomorrow at 2pm")
        
        self.assertGreater(len(issues), 0)
        self.assertTrue(any("Title" in issue for issue in issues))
    
    def test_validate_field_consistency_location_no_context(self):
        """Test consistency validation for location without context."""
        event = ParsedEvent(
            title="Meeting",
            start_datetime=datetime(2025, 1, 15, 14, 0),  # Use future date
            location="Random Place That Definitely Does Not Appear In Text"
        )
        
        # Use text without location indicators
        issues = self.handler.validate_field_consistency(event, "Meeting tomorrow 2pm")
        
        self.assertTrue(any("Location" in issue for issue in issues))
    
    def test_validate_field_consistency_datetime_past(self):
        """Test consistency validation for dates too far in the past."""
        event = ParsedEvent(
            title="Meeting",
            start_datetime=datetime(2020, 1, 15, 14, 0),  # More than 1 year ago
            end_datetime=datetime(2020, 1, 15, 15, 0)
        )
        
        issues = self.handler.validate_field_consistency(event, "Meeting")
        
        self.assertTrue(any("past" in issue.lower() for issue in issues))
    
    def test_validate_field_consistency_datetime_future(self):
        """Test consistency validation for dates too far in the future."""
        event = ParsedEvent(
            title="Meeting",
            start_datetime=datetime(2040, 1, 15, 14, 0),  # More than 10 years in future
            end_datetime=datetime(2040, 1, 15, 15, 0)
        )
        
        issues = self.handler.validate_field_consistency(event, "Meeting")
        
        self.assertTrue(any("future" in issue.lower() for issue in issues))
    
    def test_validate_field_consistency_end_before_start(self):
        """Test consistency validation for end time before start time."""
        event = ParsedEvent(
            title="Meeting",
            start_datetime=datetime(2024, 1, 15, 15, 0),
            end_datetime=datetime(2024, 1, 15, 14, 0)  # End before start
        )
        
        issues = self.handler.validate_field_consistency(event, "Meeting")
        
        self.assertTrue(any("End time" in issue for issue in issues))
    
    def test_get_completion_prompts_missing_title(self):
        """Test completion prompts for missing title."""
        event = ParsedEvent(
            start_datetime=datetime(2024, 1, 15, 14, 0)
        )
        
        prompts = self.handler.get_completion_prompts(event)
        
        self.assertIn('title', prompts)
        self.assertIn('name or title', prompts['title'])
    
    def test_get_completion_prompts_missing_datetime(self):
        """Test completion prompts for missing datetime."""
        event = ParsedEvent(
            title="Meeting"
        )
        
        prompts = self.handler.get_completion_prompts(event)
        
        self.assertIn('start_datetime', prompts)
        self.assertIn('When does', prompts['start_datetime'])
    
    def test_get_completion_prompts_missing_end_datetime(self):
        """Test completion prompts for missing end datetime."""
        event = ParsedEvent(
            title="Meeting",
            start_datetime=datetime(2024, 1, 15, 14, 0)
        )
        
        prompts = self.handler.get_completion_prompts(event)
        
        self.assertIn('end_datetime', prompts)
        self.assertIn('end', prompts['end_datetime'].lower())
    
    def test_get_completion_prompts_missing_location(self):
        """Test completion prompts for missing location."""
        event = ParsedEvent(
            title="Meeting",
            start_datetime=datetime(2024, 1, 15, 14, 0),
            end_datetime=datetime(2024, 1, 15, 15, 0)
        )
        
        prompts = self.handler.get_completion_prompts(event)
        
        self.assertIn('location', prompts)
        self.assertIn('optional', prompts['location'])
    
    def test_has_multiple_interpretations_true(self):
        """Test detection of multiple interpretations."""
        result = self.handler._has_multiple_interpretations(self.ambiguous_event)
        self.assertTrue(result)
    
    def test_has_multiple_interpretations_false(self):
        """Test detection when no multiple interpretations."""
        result = self.handler._has_multiple_interpretations(self.good_event)
        self.assertFalse(result)
    
    def test_get_missing_critical_fields(self):
        """Test identification of missing critical fields."""
        missing = self.handler._get_missing_critical_fields(self.incomplete_event)
        
        self.assertIn('title', missing)
        self.assertIn('start_datetime', missing)
    
    def test_get_missing_critical_fields_short_title(self):
        """Test identification of too-short title as missing."""
        event = ParsedEvent(
            title="A",  # Too short
            start_datetime=datetime(2024, 1, 15, 14, 0)
        )
        
        missing = self.handler._get_missing_critical_fields(event)
        
        self.assertIn('title', missing)
    
    def test_get_missing_optional_fields(self):
        """Test identification of missing optional fields."""
        event = ParsedEvent(
            title="Meeting",
            start_datetime=datetime(2024, 1, 15, 14, 0)
        )
        
        missing = self.handler._get_missing_optional_fields(event)
        
        self.assertIn('location', missing)
        self.assertIn('description', missing)
    
    def test_extract_datetime_options(self):
        """Test extraction of datetime interpretation options."""
        metadata = self.ambiguous_event.extraction_metadata
        options = self.handler._extract_datetime_options(metadata)
        
        self.assertEqual(len(options), 2)
        self.assertEqual(options[0].field_name, 'start_datetime')
        self.assertEqual(options[0].confidence, 0.8)
        self.assertEqual(options[0].source, 'relative_time')
    
    def test_extract_title_options(self):
        """Test extraction of title interpretation options."""
        metadata = self.ambiguous_event.extraction_metadata
        options = self.handler._extract_title_options(metadata)
        
        self.assertEqual(len(options), 2)
        self.assertEqual(options[0].value, 'Team Meeting')
        self.assertEqual(options[0].confidence, 0.7)
        self.assertEqual(options[0].source, 'explicit')
    
    @patch('services.event_parser.EventParser')
    def test_regex_fallback_extraction(self, mock_parser_class):
        """Test regex fallback extraction."""
        mock_parser = Mock()
        mock_parser_class.return_value = mock_parser
        
        fallback_event = ParsedEvent(
            title="Fallback Title",
            start_datetime=datetime(2024, 1, 15, 14, 0),
            confidence_score=0.5
        )
        mock_parser.parse_text.return_value = fallback_event
        
        result = self.handler._regex_fallback_extraction(self.sample_text)
        
        self.assertEqual(result, fallback_event)
        self.assertEqual(result.extraction_metadata['extraction_method'], 'regex_fallback')
        mock_parser.parse_text.assert_called_once_with(self.sample_text)
    
    @patch('services.event_parser.EventParser')
    def test_regex_fallback_extraction_failure(self, mock_parser_class):
        """Test regex fallback extraction when it fails."""
        mock_parser_class.side_effect = Exception("Parser error")
        
        result = self.handler._regex_fallback_extraction(self.sample_text)
        
        self.assertIsNone(result)
    
    def test_set_and_get_config(self):
        """Test configuration management."""
        original_config = self.handler.get_config()
        
        self.handler.set_config(
            low_confidence_threshold=0.5,
            enable_user_interaction=False
        )
        
        new_config = self.handler.get_config()
        
        self.assertEqual(new_config['low_confidence_threshold'], 0.5)
        self.assertEqual(new_config['enable_user_interaction'], False)
        self.assertNotEqual(original_config['low_confidence_threshold'], 0.5)
    
    @patch('services.comprehensive_error_handler.confirm_action')
    @patch('services.comprehensive_error_handler.is_non_interactive')
    def test_handle_no_event_found_manual_creation(self, mock_non_interactive, mock_confirm):
        """Test handling no event found with manual creation."""
        mock_non_interactive.return_value = False
        mock_confirm.return_value = True
        
        with patch.object(self.handler, '_regex_fallback_extraction') as mock_fallback:
            mock_fallback.return_value = None  # Fallback fails
            
            with patch.object(self.handler, '_create_manual_event') as mock_create:
                manual_event = ParsedEvent(
                    title="Manual Event",
                    start_datetime=datetime(2024, 1, 15, 14, 0),
                    confidence_score=1.0
                )
                mock_create.return_value = manual_event
                
                result = self.handler._handle_no_event_found(self.sample_text, llm_available=True)
                
                self.assertTrue(result.success)
                self.assertEqual(result.error_type, "no_event_found")
                self.assertEqual(result.user_action_taken, "manual_creation")
                self.assertEqual(result.resolved_event, manual_event)
    
    @patch('services.comprehensive_error_handler.is_non_interactive')
    def test_handle_no_event_found_non_interactive(self, mock_non_interactive):
        """Test handling no event found in non-interactive mode."""
        mock_non_interactive.return_value = True
        
        with patch.object(self.handler, '_regex_fallback_extraction') as mock_fallback:
            mock_fallback.return_value = None
            
            result = self.handler._handle_no_event_found(self.sample_text, llm_available=True)
            
            self.assertFalse(result.success)
            self.assertEqual(result.error_type, "no_event_found")
            self.assertIn("No event information detected", result.error_message)


class TestErrorHandlingResult(unittest.TestCase):
    """Test cases for ErrorHandlingResult dataclass."""
    
    def test_error_handling_result_creation(self):
        """Test creating ErrorHandlingResult."""
        result = ErrorHandlingResult(
            success=True,
            error_type="test_error",
            error_message="Test message"
        )
        
        self.assertTrue(result.success)
        self.assertEqual(result.error_type, "test_error")
        self.assertEqual(result.error_message, "Test message")
        self.assertEqual(result.confidence_improvement, 0.0)
        self.assertEqual(result.metadata, {})


class TestInterpretationOption(unittest.TestCase):
    """Test cases for InterpretationOption dataclass."""
    
    def test_interpretation_option_creation(self):
        """Test creating InterpretationOption."""
        option = InterpretationOption(
            field_name='title',
            value='Test Title',
            confidence=0.8,
            source='llm',
            description='From LLM extraction'
        )
        
        self.assertEqual(option.field_name, 'title')
        self.assertEqual(option.value, 'Test Title')
        self.assertEqual(option.confidence, 0.8)
        self.assertEqual(option.source, 'llm')
        self.assertEqual(option.description, 'From LLM extraction')
        self.assertEqual(option.metadata, {})


if __name__ == '__main__':
    unittest.main()