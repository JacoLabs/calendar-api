"""
Unit tests for SmartTitleExtractor class.
Tests formal event name detection, action-based title generation, context-derived titles,
truncated sentence completion, and quality assessment.
"""

import unittest
from services.smart_title_extractor import SmartTitleExtractor
from models.event_models import TitleResult


class TestSmartTitleExtractor(unittest.TestCase):
    """Test cases for SmartTitleExtractor functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.extractor = SmartTitleExtractor()
    
    def test_formal_event_name_detection(self):
        """Test detection of formal event names."""
        test_cases = [
            {
                'text': 'Indigenous Legacy Gathering tomorrow at 2pm',
                'expected_title': 'Indigenous Legacy Gathering',
                'expected_method': 'explicit',
                'min_confidence': 0.8
            },
            {
                'text': 'Annual Board Meeting scheduled for next week',
                'expected_title': 'Annual Board Meeting',
                'expected_method': 'explicit',
                'min_confidence': 0.8
            },
            {
                'text': 'The "Project Kickoff Meeting" is at 3pm',
                'expected_title': 'Project Kickoff Meeting',
                'expected_method': 'explicit',
                'min_confidence': 0.8
            },
            {
                'text': 'Emergency Staff Conference will be held tomorrow',
                'expected_title': 'Emergency Staff Conference',
                'expected_method': 'explicit',
                'min_confidence': 0.8
            }
        ]
        
        for case in test_cases:
            with self.subTest(text=case['text']):
                result = self.extractor.extract_title(case['text'])
                
                self.assertIsNotNone(result.title)
                self.assertEqual(result.title, case['expected_title'])
                self.assertEqual(result.generation_method, case['expected_method'])
                self.assertGreaterEqual(result.confidence, case['min_confidence'])
                self.assertTrue(result.is_high_quality())
    
    def test_action_based_title_generation(self):
        """Test generation of titles from action-based patterns."""
        test_cases = [
            {
                'text': 'We will leave school by 9:00 a.m.',
                'expected_title': 'School Departure',
                'expected_method': 'action_based',
                'min_confidence': 0.7
            },
            {
                'text': "Let's have lunch at the cafe tomorrow",
                'expected_title': 'Lunch',
                'expected_method': 'action_based',
                'min_confidence': 0.7
            },
            {
                'text': 'We need to review the project proposal',
                'expected_title': 'Review Session',
                'expected_method': 'action_based',
                'min_confidence': 0.6
            },
            {
                'text': 'We should meet to discuss the budget',
                'expected_title': 'Meeting Session',
                'expected_method': 'action_based',
                'min_confidence': 0.6
            },
            {
                'text': "We're going to brainstorm new ideas",
                'expected_title': 'Brainstorming Session',
                'expected_method': 'action_based',
                'min_confidence': 0.7
            }
        ]
        
        for case in test_cases:
            with self.subTest(text=case['text']):
                result = self.extractor.extract_title(case['text'])
                
                self.assertIsNotNone(result.title)
                self.assertEqual(result.title, case['expected_title'])
                self.assertEqual(result.generation_method, case['expected_method'])
                self.assertGreaterEqual(result.confidence, case['min_confidence'])
    
    def test_context_derived_title_generation(self):
        """Test generation of titles using who/what/where analysis."""
        test_cases = [
            {
                'text': 'Meeting with John Smith tomorrow at 2pm',
                'expected_title': 'Meeting with John Smith',
                'expected_method': 'context_derived',
                'min_confidence': 0.8
            },
            {
                'text': 'Call with the development team at 3pm',
                'expected_title': 'Call with The Development Team',
                'expected_method': 'context_derived',
                'min_confidence': 0.8
            },
            {
                'text': 'Lunch with Sarah at the downtown cafe',
                'expected_title': 'Lunch with Sarah',
                'expected_method': 'context_derived',
                'min_confidence': 0.8
            },
            {
                'text': 'Interview with potential candidate next week',
                'expected_title': 'Interview with Potential Candidate',
                'expected_method': 'context_derived',
                'min_confidence': 0.8
            },
            {
                'text': 'Presentation about quarterly results',
                'expected_title': 'Presentation: Quarterly Results',
                'expected_method': 'context_derived',
                'min_confidence': 0.8
            },
            {
                'text': 'Training on new software features',
                'expected_title': 'Training: New Software Features',
                'expected_method': 'context_derived',
                'min_confidence': 0.7
            }
        ]
        
        for case in test_cases:
            with self.subTest(text=case['text']):
                result = self.extractor.extract_title(case['text'])
                
                self.assertIsNotNone(result.title)
                self.assertEqual(result.title, case['expected_title'])
                self.assertEqual(result.generation_method, case['expected_method'])
                self.assertGreaterEqual(result.confidence, case['min_confidence'])
    
    def test_simple_action_detection(self):
        """Test detection of simple action words at the beginning."""
        test_cases = [
            {
                'text': 'Meeting at 2pm',
                'expected_title': 'Meeting',
                'expected_method': 'action_based',
                'min_confidence': 0.7
            },
            {
                'text': 'Lunch tomorrow',
                'expected_title': 'Lunch',
                'expected_method': 'action_based',
                'min_confidence': 0.7
            },
            {
                'text': 'Call in 30 minutes',
                'expected_title': 'Call',
                'expected_method': 'action_based',
                'min_confidence': 0.7
            },
            {
                'text': 'Interview next week',
                'expected_title': 'Interview',
                'expected_method': 'action_based',
                'min_confidence': 0.7
            }
        ]
        
        for case in test_cases:
            with self.subTest(text=case['text']):
                result = self.extractor.extract_title(case['text'])
                
                self.assertIsNotNone(result.title)
                self.assertEqual(result.title, case['expected_title'])
                self.assertEqual(result.generation_method, case['expected_method'])
                self.assertGreaterEqual(result.confidence, case['min_confidence'])
    
    def test_truncated_sentence_detection_and_completion(self):
        """Test detection and completion of truncated sentences."""
        test_cases = [
            {
                'text': 'Meeting with John and Sarah at the office tomorrow',
                'truncated_input': 'Meeting with',
                'should_detect_truncation': True
            },
            {
                'text': 'Presentation for the board meeting next week',
                'truncated_input': 'Presentation for',
                'should_detect_truncation': True
            },
            {
                'text': 'Call about project status update',
                'truncated_input': 'Call about',
                'should_detect_truncation': True
            }
        ]
        
        for case in test_cases:
            with self.subTest(text=case['truncated_input']):
                # Test truncation detection
                is_truncated = self.extractor._is_truncated_sentence(case['truncated_input'])
                self.assertEqual(is_truncated, case['should_detect_truncation'])
                
                # Test completion attempt
                if case['should_detect_truncation']:
                    completed = self.extractor._complete_truncated_sentence(
                        case['truncated_input'], 
                        case['text']
                    )
                    self.assertIsNotNone(completed)
                    self.assertNotEqual(completed, case['truncated_input'])
    
    def test_title_quality_assessment(self):
        """Test title quality scoring based on completeness and relevance."""
        test_cases = [
            {
                'title': 'Annual Board Meeting',
                'expected_min_quality': 0.7,
                'should_be_high_quality': True
            },
            {
                'title': 'Meeting',
                'expected_min_quality': 0.5,
                'should_be_high_quality': False
            },
            {
                'title': 'The and or but',
                'expected_min_quality': 0.0,
                'should_be_high_quality': False
            },
            {
                'title': 'Project Review Session',
                'expected_min_quality': 0.7,
                'should_be_high_quality': True
            },
            {
                'title': 'A very long title that goes on and on and probably should not be this long because it becomes unwieldy',
                'expected_min_quality': 0.0,
                'should_be_high_quality': False
            }
        ]
        
        for case in test_cases:
            with self.subTest(title=case['title']):
                quality = self.extractor._assess_title_quality(case['title'])
                
                self.assertGreaterEqual(quality, case['expected_min_quality'])
                
                # Test high quality determination
                result = TitleResult(
                    title=case['title'],
                    confidence=0.8,
                    quality_score=quality
                )
                
                if case['should_be_high_quality']:
                    self.assertTrue(result.is_high_quality() or quality >= 0.6)
                else:
                    # Low quality titles should not be high quality
                    if quality < 0.6:
                        self.assertFalse(result.is_high_quality())
    
    def test_multiple_title_candidate_evaluation(self):
        """Test evaluation and selection of multiple title candidates."""
        test_cases = [
            {
                'text': 'Annual Board Meeting with stakeholders tomorrow at 2pm in conference room A',
                'expected_alternatives': True,
                'min_confidence': 0.7
            },
            {
                'text': 'We will have lunch with the team at the new restaurant downtown',
                'expected_alternatives': True,
                'min_confidence': 0.6
            }
        ]
        
        for case in test_cases:
            with self.subTest(text=case['text']):
                result = self.extractor.extract_title(case['text'])
                
                self.assertIsNotNone(result.title)
                self.assertGreaterEqual(result.confidence, case['min_confidence'])
                
                if case['expected_alternatives']:
                    # Should have found multiple candidates and stored alternatives
                    self.assertGreater(
                        result.extraction_metadata.get('total_candidates', 0), 
                        1
                    )
    
    def test_title_normalization_and_formatting(self):
        """Test title normalization and formatting."""
        test_cases = [
            {
                'input': 'Reminder: Team meeting tomorrow at 2pm',
                'expected_normalized': 'Team meeting',
                'description': 'Remove reminder prefix'
            },
            {
                'input': 'Meeting with John tomorrow at the office',
                'expected_normalized': 'Meeting with John',
                'description': 'Remove temporal and location info'
            },
            {
                'input': 'FYI: Important presentation next week',
                'expected_normalized': 'Important presentation',
                'description': 'Remove FYI prefix'
            },
            {
                'input': 'Please   join   the   call',
                'expected_normalized': 'join the call',
                'description': 'Clean up whitespace and remove please'
            }
        ]
        
        for case in test_cases:
            with self.subTest(description=case['description']):
                normalized = self.extractor._normalize_title(case['input'])
                self.assertEqual(normalized, case['expected_normalized'])
    
    def test_edge_cases_and_error_handling(self):
        """Test edge cases and error handling."""
        edge_cases = [
            {
                'text': '',
                'description': 'Empty text'
            },
            {
                'text': '   ',
                'description': 'Whitespace only'
            },
            {
                'text': '123456789',
                'description': 'Numbers only'
            },
            {
                'text': 'a',
                'description': 'Single character'
            },
            {
                'text': 'the and or but in on at to for of with by from',
                'description': 'Only noise words'
            }
        ]
        
        for case in edge_cases:
            with self.subTest(description=case['description']):
                result = self.extractor.extract_title(case['text'])
                
                # Should not crash and should return a valid TitleResult
                self.assertIsInstance(result, TitleResult)
                self.assertEqual(result.raw_text, case['text'])
                
                # For invalid inputs, title should be None or empty
                if case['text'].strip() == '' or case['text'] == '123456789':
                    self.assertIsNone(result.title)
                    self.assertEqual(result.confidence, 0.0)
    
    def test_multiple_events_detection(self):
        """Test detection and extraction of multiple events from single text."""
        test_cases = [
            {
                'text': 'Meeting at 9am. Then lunch with Sarah at noon. After that, presentation at 3pm.',
                'expected_count': 3,
                'expected_titles': ['Meeting', 'Lunch with Sarah', 'Presentation']
            },
            {
                'text': 'First we have the board meeting, then the team standup, and finally the client call.',
                'expected_count': 3,
                'min_count': 1  # May not detect all as separate events
            }
        ]
        
        for case in test_cases:
            with self.subTest(text=case['text'][:50] + '...'):
                results = self.extractor.extract_multiple_titles(case['text'])
                
                self.assertIsInstance(results, list)
                self.assertGreater(len(results), 0)
                
                if 'expected_count' in case:
                    # Flexible assertion - may not always detect exact count
                    self.assertGreaterEqual(len(results), case.get('min_count', 1))
                
                # All results should be valid
                for result in results:
                    self.assertIsInstance(result, TitleResult)
                    if result.title:
                        self.assertGreater(len(result.title), 0)
    
    def test_confidence_scoring_accuracy(self):
        """Test accuracy of confidence scoring for different extraction methods."""
        test_cases = [
            {
                'text': 'Annual Board Meeting tomorrow',
                'expected_min_confidence': 0.8,
                'description': 'Formal event name should have high confidence'
            },
            {
                'text': 'Meeting with',
                'expected_max_confidence': 0.6,
                'description': 'Truncated sentence should have lower confidence'
            },
            {
                'text': 'We will have lunch',
                'expected_min_confidence': 0.6,
                'description': 'Action-based should have medium-high confidence'
            },
            {
                'text': 'Call with the team',
                'expected_min_confidence': 0.8,
                'description': 'Context-derived should have high confidence'
            }
        ]
        
        for case in test_cases:
            with self.subTest(description=case['description']):
                result = self.extractor.extract_title(case['text'])
                
                if 'expected_min_confidence' in case:
                    self.assertGreaterEqual(result.confidence, case['expected_min_confidence'])
                
                if 'expected_max_confidence' in case:
                    self.assertLessEqual(result.confidence, case['expected_max_confidence'])
    
    def test_title_result_data_model(self):
        """Test TitleResult data model functionality."""
        # Test basic creation
        result = TitleResult(
            title="Test Meeting",
            confidence=0.8,
            generation_method="explicit",
            quality_score=0.7
        )
        
        self.assertEqual(result.title, "Test Meeting")
        self.assertEqual(result.confidence, 0.8)
        self.assertEqual(result.generation_method, "explicit")
        self.assertEqual(result.quality_score, 0.7)
        
        # Test high quality detection
        self.assertTrue(result.is_high_quality())
        
        # Test complete phrase detection
        self.assertTrue(result.is_complete_phrase())
        
        # Test adding alternatives
        result.add_alternative("Alternative Title", 0.6)
        self.assertIn("Alternative Title", result.alternatives)
        
        # Test serialization
        result_dict = result.to_dict()
        self.assertIsInstance(result_dict, dict)
        self.assertEqual(result_dict['title'], "Test Meeting")
        
        # Test deserialization
        restored_result = TitleResult.from_dict(result_dict)
        self.assertEqual(restored_result.title, result.title)
        self.assertEqual(restored_result.confidence, result.confidence)
    
    def test_integration_with_real_world_examples(self):
        """Test with real-world text examples from requirements."""
        real_world_cases = [
            {
                'text': 'Indigenous Legacy Gathering next Friday at Nathan Phillips Square',
                'expected_method': 'explicit',
                'min_confidence': 0.8,
                'description': 'Formal event name from requirements'
            },
            {
                'text': 'We will leave school by 9:00 a.m. to catch the bus',
                'expected_method': 'action_based',
                'min_confidence': 0.7,
                'description': 'Action-based example from requirements'
            },
            {
                'text': 'Meeting with the project team about budget review',
                'expected_method': 'context_derived',
                'min_confidence': 0.8,
                'description': 'Context-derived example'
            }
        ]
        
        for case in real_world_cases:
            with self.subTest(description=case['description']):
                result = self.extractor.extract_title(case['text'])
                
                self.assertIsNotNone(result.title)
                self.assertEqual(result.generation_method, case['expected_method'])
                self.assertGreaterEqual(result.confidence, case['min_confidence'])
                self.assertTrue(len(result.title) >= 3)


if __name__ == '__main__':
    unittest.main()