"""
Unit tests for LLM service functionality.
Tests the LLM-based event extraction with various scenarios and providers.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import json
from datetime import datetime, timedelta

from services.llm_service import LLMService, LLMResponse
from services.llm_prompts import get_prompt_templates
from models.event_models import ParsedEvent


class TestLLMService(unittest.TestCase):
    """Test cases for LLM service functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.llm_service = LLMService(provider="heuristic")  # Start with heuristic to avoid external deps
        self.prompt_templates = get_prompt_templates()
    
    def test_initialization(self):
        """Test LLM service initialization."""
        service = LLMService(provider="heuristic")
        self.assertEqual(service.provider, "heuristic")
        self.assertIsNotNone(service.prompt_templates)
    
    def test_provider_detection(self):
        """Test automatic provider detection."""
        with patch('services.llm_service.LLMService._check_ollama_available', return_value=True), \
             patch('services.llm_service.LLMService._initialize_ollama'):
            service = LLMService(provider="auto")
            self.assertEqual(service.provider, "ollama")
        
        with patch('services.llm_service.LLMService._check_ollama_available', return_value=False), \
             patch('services.llm_service.LLMService._check_openai_available', return_value=True), \
             patch('services.llm_service.LLMService._initialize_openai'):
            service = LLMService(provider="auto")
            self.assertEqual(service.provider, "openai")
    
    def test_heuristic_fallback_extraction(self):
        """Test heuristic fallback when LLM is not available."""
        text = "Team meeting tomorrow at 2pm in conference room A"
        response = self.llm_service.extract_event(text)
        
        self.assertTrue(response.success)
        self.assertIsNotNone(response.data)
        self.assertEqual(response.provider, "heuristic")
        self.assertGreater(response.confidence, 0.0)
    
    def test_llm_extract_event_method(self):
        """Test the llm_extract_event method that returns ParsedEvent."""
        text = "Birthday party on Friday at 7pm at John's house"
        parsed_event = self.llm_service.llm_extract_event(text)
        
        self.assertIsInstance(parsed_event, ParsedEvent)
        self.assertEqual(parsed_event.description, text)
        self.assertIsNotNone(parsed_event.extraction_metadata)
        self.assertIn('llm_provider', parsed_event.extraction_metadata)
    
    def test_basic_event_extraction_patterns(self):
        """Test extraction of basic event patterns."""
        test_cases = [
            {
                'text': "Meeting tomorrow at 2pm",
                'expected_title': True,
                'expected_datetime': True,
                'expected_location': False
            },
            {
                'text': "Lunch with Sarah on Friday at noon at Cafe Central",
                'expected_title': True,
                'expected_datetime': True,
                'expected_location': True
            },
            {
                'text': "Doctor appointment next Tuesday 3:30pm",
                'expected_title': True,
                'expected_datetime': True,
                'expected_location': False
            }
        ]
        
        for case in test_cases:
            with self.subTest(text=case['text']):
                response = self.llm_service.extract_event(case['text'])
                
                self.assertTrue(response.success)
                data = response.data
                
                if case['expected_title']:
                    self.assertIsNotNone(data.get('title'))
                
                if case['expected_datetime']:
                    self.assertIsNotNone(data.get('start_datetime'))
                
                if case['expected_location']:
                    self.assertIsNotNone(data.get('location'))
    
    def test_confidence_scoring(self):
        """Test confidence scoring in extraction results."""
        text = "Clear meeting tomorrow at 2pm in room 101"
        response = self.llm_service.extract_event(text)
        
        self.assertTrue(response.success)
        confidence = response.data.get('confidence', {})
        
        self.assertIn('overall', confidence)
        self.assertIsInstance(confidence['overall'], (int, float))
        self.assertGreaterEqual(confidence['overall'], 0.0)
        self.assertLessEqual(confidence['overall'], 1.0)
    
    def test_error_handling(self):
        """Test error handling for invalid inputs."""
        # Empty text
        response = self.llm_service.extract_event("")
        self.assertTrue(response.success)  # Should handle gracefully
        
        # Very long text
        long_text = "Meeting " * 1000
        response = self.llm_service.extract_event(long_text)
        self.assertTrue(response.success)
    
    def test_template_selection(self):
        """Test automatic template selection based on text characteristics."""
        # Multi-paragraph text
        multi_para_text = """First paragraph about the event.
        
        Second paragraph with more details.
        
        Third paragraph with timing information."""
        
        template_name = self.prompt_templates.get_template_for_text_type(multi_para_text)
        self.assertEqual(template_name, 'multi_paragraph')
        
        # Ambiguous text
        ambiguous_text = "Maybe we could meet sometime next week?"
        template_name = self.prompt_templates.get_template_for_text_type(ambiguous_text)
        self.assertEqual(template_name, 'ambiguous_handling')
        
        # Incomplete text
        incomplete_text = "Meeting"
        template_name = self.prompt_templates.get_template_for_text_type(incomplete_text)
        self.assertEqual(template_name, 'fallback_extraction')
    
    def test_json_extraction_from_text(self):
        """Test JSON extraction from malformed LLM responses."""
        # Test with valid JSON embedded in text
        text_with_json = '''Here is the extracted information:
        {"title": "Test Meeting", "start_datetime": "2025-01-15T14:00:00", "confidence": {"overall": 0.8}}
        That's the result.'''
        
        result = self.llm_service._extract_json_from_text(text_with_json)
        self.assertIsInstance(result, dict)
        self.assertEqual(result['title'], "Test Meeting")
        
        # Test with no JSON
        text_no_json = "This is just plain text with no JSON"
        result = self.llm_service._extract_json_from_text(text_no_json)
        self.assertIsInstance(result, dict)
        self.assertIn('extraction_notes', result)
    
    def test_service_status(self):
        """Test service status reporting."""
        status = self.llm_service.get_status()
        
        self.assertIn('provider', status)
        self.assertIn('available', status)
        self.assertIn('model', status)
        self.assertIsInstance(status['available'], bool)
    
    def test_is_available(self):
        """Test availability checking."""
        # Heuristic mode should not be considered "available"
        heuristic_service = LLMService(provider="heuristic")
        self.assertFalse(heuristic_service.is_available())


class TestLLMServiceWithMockedOllama(unittest.TestCase):
    """Test LLM service with mocked Ollama responses."""
    
    def setUp(self):
        """Set up test fixtures with mocked Ollama."""
        self.mock_response_data = {
            "title": "Team Meeting",
            "start_datetime": "2025-01-15T14:00:00",
            "end_datetime": "2025-01-15T15:00:00",
            "location": "Conference Room A",
            "description": "Weekly team sync",
            "confidence": {
                "title": 0.9,
                "start_datetime": 0.8,
                "end_datetime": 0.7,
                "location": 0.8,
                "overall": 0.8
            },
            "extraction_notes": "Clear event information extracted"
        }
    
    @patch('services.llm_service.requests')
    def test_ollama_extraction(self, mock_requests):
        """Test extraction using mocked Ollama."""
        # Mock Ollama availability check
        mock_requests.get.return_value.status_code = 200
        mock_requests.get.return_value.json.return_value = {'models': [{'name': 'llama3.2:3b'}]}
        
        # Mock Ollama generation response
        mock_requests.post.return_value.status_code = 200
        mock_requests.post.return_value.json.return_value = {
            'response': json.dumps(self.mock_response_data)
        }
        
        service = LLMService(provider="ollama")
        response = service.extract_event("Team meeting tomorrow at 2pm in conference room A")
        
        self.assertTrue(response.success)
        self.assertEqual(response.provider, "ollama")
        self.assertIsNotNone(response.data)
        self.assertEqual(response.data['title'], "Team Meeting")
    
    @patch('services.llm_service.requests')
    def test_ollama_error_handling(self, mock_requests):
        """Test Ollama error handling."""
        # Mock Ollama availability
        mock_requests.get.return_value.status_code = 200
        mock_requests.get.return_value.json.return_value = {'models': [{'name': 'llama3.2:3b'}]}
        
        # Mock Ollama error response
        mock_requests.post.return_value.status_code = 500
        mock_requests.post.return_value.text = "Internal server error"
        
        service = LLMService(provider="ollama")
        response = service.extract_event("Test text")
        
        self.assertFalse(response.success)
        self.assertIsNotNone(response.error)
    
    @patch('services.llm_service.requests')
    def test_ollama_malformed_json_response(self, mock_requests):
        """Test handling of malformed JSON from Ollama."""
        # Mock Ollama availability
        mock_requests.get.return_value.status_code = 200
        mock_requests.get.return_value.json.return_value = {'models': [{'name': 'llama3.2:3b'}]}
        
        # Mock malformed JSON response
        mock_requests.post.return_value.status_code = 200
        mock_requests.post.return_value.json.return_value = {
            'response': 'This is not valid JSON but contains {"title": "Meeting"} somewhere'
        }
        
        service = LLMService(provider="ollama")
        response = service.extract_event("Test meeting")
        
        self.assertTrue(response.success)
        self.assertEqual(response.data['title'], "Meeting")


class TestLLMServiceWithMockedOpenAI(unittest.TestCase):
    """Test LLM service with mocked OpenAI responses."""
    
    @patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'})
    @patch('services.llm_service.OpenAI')
    def test_openai_extraction(self, mock_openai_class):
        """Test extraction using mocked OpenAI."""
        # Mock OpenAI client
        mock_client = Mock()
        mock_openai_class.return_value = mock_client
        
        # Mock response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = json.dumps({
            "title": "OpenAI Meeting",
            "start_datetime": "2025-01-15T14:00:00",
            "confidence": {"overall": 0.9}
        })
        mock_client.chat.completions.create.return_value = mock_response
        
        service = LLMService(provider="openai")
        response = service.extract_event("Meeting tomorrow")
        
        self.assertTrue(response.success)
        self.assertEqual(response.provider, "openai")
        self.assertEqual(response.data['title'], "OpenAI Meeting")


class TestLLMPromptTemplates(unittest.TestCase):
    """Test LLM prompt templates."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.templates = get_prompt_templates()
    
    def test_template_availability(self):
        """Test that all required templates are available."""
        required_templates = [
            'primary_extraction',
            'multi_paragraph',
            'ambiguous_handling',
            'fallback_extraction',
            'confidence_scoring',
            'incomplete_info'
        ]
        
        for template_name in required_templates:
            template = self.templates.get_template(template_name)
            self.assertIsNotNone(template, f"Template {template_name} not found")
            self.assertIsNotNone(template.system_prompt)
            self.assertIsNotNone(template.user_prompt_template)
    
    def test_prompt_formatting(self):
        """Test prompt formatting with variables."""
        text = "Meeting tomorrow at 2pm"
        system_prompt, user_prompt = self.templates.format_prompt(
            'primary_extraction',
            text,
            current_date='2025-01-01',
            context='Test context'
        )
        
        self.assertIn(text, user_prompt)
        self.assertIn('2025-01-01', user_prompt)
        self.assertIn('Test context', user_prompt)
    
    def test_template_selection_logic(self):
        """Test automatic template selection logic."""
        # Test multi-paragraph detection
        multi_para = "First paragraph.\n\nSecond paragraph.\n\nThird paragraph."
        template_name = self.templates.get_template_for_text_type(multi_para)
        self.assertEqual(template_name, 'multi_paragraph')
        
        # Test ambiguous text detection
        ambiguous = "Maybe we could meet sometime?"
        template_name = self.templates.get_template_for_text_type(ambiguous)
        self.assertEqual(template_name, 'ambiguous_handling')
        
        # Test incomplete info detection (single word -> fallback)
        incomplete = "Meeting"
        template_name = self.templates.get_template_for_text_type(incomplete)
        self.assertEqual(template_name, 'fallback_extraction')
        
        # Test normal text
        normal = "Team meeting tomorrow at 2pm in room 101"
        template_name = self.templates.get_template_for_text_type(normal)
        self.assertEqual(template_name, 'primary_extraction')
    
    def test_template_list(self):
        """Test template listing functionality."""
        template_list = self.templates.list_templates()
        self.assertIsInstance(template_list, dict)
        self.assertGreater(len(template_list), 0)
        
        for name, use_case in template_list.items():
            self.assertIsInstance(name, str)
            self.assertIsInstance(use_case, str)


class TestLLMServiceIntegration(unittest.TestCase):
    """Integration tests for LLM service with real-world scenarios."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.llm_service = LLMService(provider="heuristic")
    
    def test_real_world_scenarios(self):
        """Test extraction with real-world text scenarios."""
        scenarios = [
            {
                'name': 'School event email',
                'text': 'On Monday the elementary students will attend the Indigenous Legacy Gathering',
                'expected_elements': ['title', 'start_datetime']
            },
            {
                'name': 'Business meeting',
                'text': 'Quarterly review meeting on Friday, January 15th at 2:00 PM in the boardroom',
                'expected_elements': ['title', 'start_datetime', 'location']
            },
            {
                'name': 'Personal appointment',
                'text': 'Dentist appointment next Tuesday at 3:30pm',
                'expected_elements': ['title', 'start_datetime']
            },
            {
                'name': 'Multi-paragraph event',
                'text': '''The annual company picnic is coming up.
                
                It will be held on Saturday, June 15th starting at noon.
                
                Location is Central Park pavilion. Bring your families!''',
                'expected_elements': ['title', 'start_datetime', 'location']
            }
        ]
        
        for scenario in scenarios:
            with self.subTest(scenario=scenario['name']):
                parsed_event = self.llm_service.llm_extract_event(scenario['text'])
                
                self.assertIsInstance(parsed_event, ParsedEvent)
                self.assertGreater(parsed_event.confidence_score, 0.0)
                
                # Check that expected elements are present
                for element in scenario['expected_elements']:
                    if element == 'title':
                        self.assertIsNotNone(parsed_event.title, 
                                           f"Title missing for scenario: {scenario['name']}")
                    elif element == 'start_datetime':
                        self.assertIsNotNone(parsed_event.start_datetime,
                                           f"Start datetime missing for scenario: {scenario['name']}")
                    elif element == 'location':
                        self.assertIsNotNone(parsed_event.location,
                                           f"Location missing for scenario: {scenario['name']}")
    
    def test_edge_cases(self):
        """Test edge cases and error conditions."""
        edge_cases = [
            "",  # Empty string
            "   ",  # Whitespace only
            "a",  # Single character
            "Meeting",  # Single word
            "This is just random text with no event information whatsoever",  # No event info
            "Meeting tomorrow at 25:00",  # Invalid time
            "Event on February 30th",  # Invalid date
        ]
        
        for text in edge_cases:
            with self.subTest(text=text):
                parsed_event = self.llm_service.llm_extract_event(text)
                
                # Should not crash and should return a ParsedEvent
                self.assertIsInstance(parsed_event, ParsedEvent)
                self.assertIsNotNone(parsed_event.extraction_metadata)
    
    def test_performance_timing(self):
        """Test that extraction completes within reasonable time."""
        text = "Team meeting tomorrow at 2pm in conference room A"
        
        start_time = datetime.now()
        response = self.llm_service.extract_event(text)
        end_time = datetime.now()
        
        processing_time = (end_time - start_time).total_seconds()
        
        # Should complete within 5 seconds for heuristic mode
        self.assertLess(processing_time, 5.0)
        self.assertGreater(response.processing_time, 0.0)


if __name__ == '__main__':
    unittest.main()