"""
Unit tests for SmartTitleExtractor LLM Fallback Service functionality.
Tests LLM title validation, regex fallback, user prompts, and title quality assessment.
"""

import unittest
from unittest.mock import patch, MagicMock
from services.smart_title_extractor import SmartTitleExtractor
from models.event_models import TitleResult


class TestSmartTitleExtractorLLMFallback(unittest.TestCase):
    """Test cases for SmartTitleExtractor LLM Fallback Service functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.extractor = SmartTitleExtractor()
    
    def test_validate_llm_title_success(self):
        """Test successful validation of high-quality LLM titles."""
        test_cases = [
            {
                'llm_title': 'Annual Board Meeting',
                'text': 'Annual Board Meeting tomorrow at 2pm',
                'llm_confidence': 0.9,
                'expected_method': 'llm_validated',
                'min_confidence': 0.6
            },
            {
                'llm_title': 'Team Standup Session',
                'text': 'Daily standup with the development team',
                'llm_confidence': 0.8,
                'expected_method': 'llm_validated',
                'min_confidence': 0.6
            }
        ]
        
        for case in test_cases:
            with self.subTest(llm_title=case['llm_title']):
                result = self.extractor.validate_llm_title(
                    case['llm_title'], 
                    case['text'], 
                    case['llm_confidence']
                )
                
                self.assertEqual(result.title, case['llm_title'])
                self.assertEqual(result.generation_method, case['expected_method'])
                self.assertGreaterEqual(result.confidence, case['min_confidence'])
                self.assertTrue(result.extraction_metadata['validation_passed'])
    
    def test_validate_llm_title_empty_fallback(self):
        """Test fallback when LLM returns empty title."""
        result = self.extractor.validate_llm_title(
            None, 
            'Meeting with John tomorrow at 2pm', 
            0.0
        )
        
        # Should fall back to regex extraction
        self.assertIsNotNone(result.title)
        self.assertIn('regex_fallback', result.generation_method)
        self.assertEqual(result.extraction_metadata['fallback_reason'], 'llm_empty_title')
    
    def test_validate_llm_title_invalid_fallback(self):
        """Test fallback when LLM returns invalid title."""
        # Test empty/whitespace titles (should be 'llm_empty_title')
        empty_titles = ['', '   ']
        for empty_title in empty_titles:
            with self.subTest(empty_title=repr(empty_title)):
                result = self.extractor.validate_llm_title(
                    empty_title,
                    'Meeting with Sarah at the office',
                    0.8
                )
                
                # Should fall back to regex extraction
                self.assertNotEqual(result.title, empty_title)
                self.assertIn('regex_fallback', result.generation_method)
                self.assertEqual(result.extraction_metadata['fallback_reason'], 'llm_empty_title')
        
        # Test invalid but non-empty titles (should be 'llm_invalid_title')
        invalid_titles = ['a', '123', 'the and or but']
        for invalid_title in invalid_titles:
            with self.subTest(invalid_title=invalid_title):
                result = self.extractor.validate_llm_title(
                    invalid_title,
                    'Meeting with Sarah at the office',
                    0.8
                )
                
                # Should fall back to regex extraction
                self.assertNotEqual(result.title, invalid_title)
                self.assertIn('regex_fallback', result.generation_method)
                self.assertEqual(result.extraction_metadata['fallback_reason'], 'llm_invalid_title')
    
    def test_validate_llm_title_low_quality_enhancement(self):
        """Test enhancement of low-quality LLM titles with regex alternatives."""
        result = self.extractor.validate_llm_title(
            'Meet',  # Low quality title
            'Meeting with John Smith about project review',
            0.2  # Low confidence
        )
        
        # Should enhance with regex alternatives
        self.assertIn(result.generation_method, ['llm_enhanced', 'regex_preferred', 'regex_preferred_over_llm'])
        self.assertTrue(result.extraction_metadata['enhancement_applied'])
        
        # Should have alternatives
        if result.generation_method == 'llm_enhanced':
            self.assertGreater(len(result.alternatives), 0)
    
    def test_extract_title_fallback(self):
        """Test regex-based fallback extraction."""
        test_cases = [
            {
                'text': 'Annual Board Meeting tomorrow',
                'reason': 'llm_unavailable',
                'expected_method_contains': 'regex_fallback'
            },
            {
                'text': 'Meeting with John at 2pm',
                'reason': 'llm_failed',
                'expected_method_contains': 'regex_fallback'
            }
        ]
        
        for case in test_cases:
            with self.subTest(text=case['text']):
                result = self.extractor.extract_title_fallback(case['text'], case['reason'])
                
                self.assertIsNotNone(result.title)
                self.assertIn(case['expected_method_contains'], result.generation_method)
                self.assertEqual(result.extraction_metadata['fallback_reason'], case['reason'])
                self.assertFalse(result.extraction_metadata['llm_available'])
    
    def test_generate_title_suggestions(self):
        """Test generation of title suggestions for user selection."""
        test_cases = [
            {
                'text': 'Meeting with John Smith about budget review tomorrow',
                'min_suggestions': 2,
                'expected_contains': ['Meeting', 'Budget', 'Review']
            },
            {
                'text': 'Call with the development team at 3pm',
                'min_suggestions': 2,
                'expected_contains': ['Call', 'Team']
            },
            {
                'text': 'Lunch at the downtown cafe',
                'min_suggestions': 2,
                'expected_contains': ['Lunch']
            }
        ]
        
        for case in test_cases:
            with self.subTest(text=case['text'][:30] + '...'):
                suggestions = self.extractor.generate_title_suggestions(case['text'])
                
                self.assertIsInstance(suggestions, list)
                self.assertGreaterEqual(len(suggestions), case['min_suggestions'])
                self.assertLessEqual(len(suggestions), 5)  # Should limit to 5
                
                # Check that suggestions contain expected elements
                suggestions_text = ' '.join(suggestions).lower()
                for expected in case['expected_contains']:
                    self.assertIn(expected.lower(), suggestions_text)
    
    def test_generate_title_suggestions_with_context(self):
        """Test title suggestions with additional context."""
        from datetime import datetime
        
        context = {
            'location': 'Conference Room A',
            'datetime': datetime(2025, 1, 15, 14, 30)
        }
        
        suggestions = self.extractor.generate_title_suggestions(
            'Discussion about project status',
            context
        )
        
        self.assertIsInstance(suggestions, list)
        self.assertGreater(len(suggestions), 0)
        
        # Should include context-based suggestions
        suggestions_text = ' '.join(suggestions)
        self.assertTrue(
            'Conference Room A' in suggestions_text or 
            '2:30 PM' in suggestions_text or
            'Meeting at' in suggestions_text
        )
    
    @patch('ui.safe_input.is_non_interactive')
    @patch('ui.safe_input.get_choice')
    @patch('builtins.print')
    def test_prompt_user_for_title_suggestion_selection(self, mock_print, mock_get_choice, mock_is_non_interactive):
        """Test user prompt with suggestion selection."""
        mock_is_non_interactive.return_value = False
        mock_get_choice.return_value = 0  # Select first suggestion
        
        suggestions = ['Team Meeting', 'Project Discussion', 'Status Update']
        
        result = self.extractor.prompt_user_for_title(
            'Meeting with team about project',
            suggestions
        )
        
        self.assertEqual(result.title, 'Team Meeting')
        self.assertEqual(result.generation_method, 'user_selected')
        self.assertEqual(result.confidence, 0.9)
        self.assertTrue(result.extraction_metadata['user_selected'])
        self.assertTrue(result.extraction_metadata['selected_from_suggestions'])
    
    @patch('ui.safe_input.is_non_interactive')
    @patch('ui.safe_input.get_choice')
    @patch('ui.safe_input.safe_input')
    @patch('builtins.print')
    def test_prompt_user_for_title_custom_input(self, mock_print, mock_safe_input, mock_get_choice, mock_is_non_interactive):
        """Test user prompt with custom title input."""
        mock_is_non_interactive.return_value = False
        mock_get_choice.return_value = 3  # Select "Enter custom title" (assuming 3 suggestions)
        mock_safe_input.return_value = 'Custom Event Title'
        
        suggestions = ['Meeting', 'Discussion', 'Session']
        
        result = self.extractor.prompt_user_for_title(
            'Some event text',
            suggestions
        )
        
        self.assertEqual(result.title, 'Custom Event Title')
        self.assertEqual(result.generation_method, 'user_custom')
        self.assertEqual(result.confidence, 0.95)
        self.assertTrue(result.extraction_metadata['user_selected'])
        self.assertTrue(result.extraction_metadata['custom_input'])
    
    @patch('ui.safe_input.is_non_interactive')
    def test_prompt_user_for_title_non_interactive(self, mock_is_non_interactive):
        """Test user prompt in non-interactive mode."""
        mock_is_non_interactive.return_value = True
        
        result = self.extractor.prompt_user_for_title('Some event text')
        
        # Should return empty result in non-interactive mode
        self.assertIsNone(result.title)
        self.assertEqual(result.confidence, 0.0)
    
    def test_extract_with_llm_fallback_with_llm_result(self):
        """Test main LLM fallback method with LLM result provided."""
        llm_result = {
            'title': 'Project Review Meeting',
            'confidence': {'title': 0.8}
        }
        
        result = self.extractor.extract_with_llm_fallback(
            'Project review meeting tomorrow at 2pm',
            llm_result
        )
        
        self.assertEqual(result.title, 'Project Review Meeting')
        self.assertEqual(result.generation_method, 'llm_validated')
        self.assertGreaterEqual(result.confidence, 0.6)
    
    def test_extract_with_llm_fallback_no_llm_result(self):
        """Test main LLM fallback method without LLM result."""
        result = self.extractor.extract_with_llm_fallback(
            'Annual Board Meeting tomorrow at 2pm'
        )
        
        self.assertIsNotNone(result.title)
        self.assertIn('regex_fallback', result.generation_method)
        self.assertEqual(result.extraction_metadata['fallback_reason'], 'no_llm_result')
    
    def test_extract_with_llm_fallback_low_quality_suggestions(self):
        """Test LLM fallback method with low quality results suggesting user prompts."""
        result = self.extractor.extract_with_llm_fallback(
            'Something unclear happening sometime'  # Intentionally vague
        )
        
        # Should detect low quality and suggest user prompts
        if result.confidence < 0.4 or result.quality_score < 0.3:
            self.assertTrue(result.extraction_metadata.get('low_quality_extraction', False))
            self.assertTrue(result.extraction_metadata.get('user_prompt_suggested', False))
            self.assertIn('title_suggestions', result.extraction_metadata)
    
    def test_assess_title_completeness(self):
        """Test title completeness assessment."""
        test_cases = [
            {
                'title': 'Annual Board Meeting',
                'text': 'Annual Board Meeting tomorrow',
                'expected_complete': True,
                'min_score': 0.7
            },
            {
                'title': 'Meeting with',
                'text': 'Meeting with John tomorrow',
                'expected_complete': False,
                'max_score': 0.8,
                'expected_issues': ['Title appears truncated']
            },
            {
                'title': 'A',
                'text': 'A meeting tomorrow',
                'expected_complete': False,
                'expected_issues': ['Title is too short']
            },
            {
                'title': '',
                'text': 'Some event',
                'expected_complete': False,
                'expected_issues': ['Title is empty']
            },
            {
                'title': 'the and or but in on at',
                'text': 'Some event text',
                'expected_complete': False,
                'expected_issues': ['Title contains no meaningful words']
            }
        ]
        
        for case in test_cases:
            with self.subTest(title=case['title']):
                assessment = self.extractor.assess_title_completeness(case['title'], case['text'])
                
                self.assertEqual(assessment['is_complete'], case['expected_complete'])
                
                if 'min_score' in case:
                    self.assertGreaterEqual(assessment['completeness_score'], case['min_score'])
                
                if 'max_score' in case:
                    self.assertLessEqual(assessment['completeness_score'], case['max_score'])
                
                if 'expected_issues' in case:
                    for expected_issue in case['expected_issues']:
                        self.assertTrue(
                            any(expected_issue in issue for issue in assessment['issues']),
                            f"Expected issue '{expected_issue}' not found in {assessment['issues']}"
                        )
    
    def test_llm_fallback_integration_workflow(self):
        """Test complete LLM fallback workflow integration."""
        # Simulate LLM failure scenario
        text = 'Team standup meeting tomorrow at 9am in conference room'
        
        # Test 1: LLM returns good result
        llm_result_good = {
            'title': 'Team Standup Meeting',
            'confidence': {'title': 0.9}
        }
        
        result1 = self.extractor.extract_with_llm_fallback(text, llm_result_good)
        self.assertEqual(result1.title, 'Team Standup Meeting')
        self.assertEqual(result1.generation_method, 'llm_validated')
        
        # Test 2: LLM returns poor result
        llm_result_poor = {
            'title': 'Meet',
            'confidence': {'title': 0.2}
        }
        
        result2 = self.extractor.extract_with_llm_fallback(text, llm_result_poor)
        self.assertIsNotNone(result2.title)
        self.assertIn(result2.generation_method, ['llm_enhanced', 'regex_preferred'])
        
        # Test 3: No LLM result
        result3 = self.extractor.extract_with_llm_fallback(text, None)
        self.assertIsNotNone(result3.title)
        self.assertIn('regex_fallback', result3.generation_method)
    
    def test_title_validation_edge_cases(self):
        """Test edge cases in title validation."""
        edge_cases = [
            {
                'llm_title': None,
                'text': 'Meeting tomorrow',
                'llm_confidence': 0.8,
                'description': 'None title'
            },
            {
                'llm_title': '   ',
                'text': 'Meeting tomorrow',
                'llm_confidence': 0.8,
                'description': 'Whitespace only title'
            },
            {
                'llm_title': 'Very long title that goes on and on and probably should not be this long because it becomes unwieldy and hard to read',
                'text': 'Meeting tomorrow',
                'llm_confidence': 0.8,
                'description': 'Overly long title'
            }
        ]
        
        for case in edge_cases:
            with self.subTest(description=case['description']):
                result = self.extractor.validate_llm_title(
                    case['llm_title'],
                    case['text'],
                    case['llm_confidence']
                )
                
                # Should handle gracefully and provide fallback
                self.assertIsInstance(result, TitleResult)
                if case['llm_title'] in [None, '   ']:
                    # Should fall back to regex
                    self.assertIn('regex_fallback', result.generation_method)
                else:
                    # Should either validate or enhance
                    self.assertIsNotNone(result.title)


if __name__ == '__main__':
    unittest.main()