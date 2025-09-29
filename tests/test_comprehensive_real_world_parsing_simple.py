"""
Simplified comprehensive real-world testing suite for the complete LLM-first parsing pipeline.

Tests key parsing scenarios without complex parametrization.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock
import time

from services.master_event_parser import MasterEventParser
from services.llm_service import LLMService
from models.event_models import ParsedEvent
from services.format_aware_text_processor import TextFormat


class TestComprehensiveRealWorldParsing:
    """Comprehensive test suite for real-world parsing scenarios."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_llm_service = Mock(spec=LLMService)
        self.mock_llm_service.is_available.return_value = True
        self.parser = MasterEventParser(llm_service=self.mock_llm_service)
    
    def create_mock_llm_response(self, text, title="Test Event", start_time=None, location=None, confidence=0.8):
        """Create mock LLM response."""
        if start_time is None:
            start_time = datetime.now() + timedelta(days=1, hours=14)
        
        return ParsedEvent(
            title=title,
            start_datetime=start_time,
            end_datetime=start_time + timedelta(hours=1),
            location=location,
            description=text,
            confidence_score=confidence,
            extraction_metadata={'llm_provider': 'mock'}
        )
    
    # ===== DATE PARSING TESTS =====
    
    def test_explicit_date_parsing_scenarios(self):
        """Test various explicit date parsing scenarios."""
        test_cases = [
            {
                'text': 'Meeting on Monday, September 29, 2025',
                'expected_date': datetime(2025, 9, 29),
                'title': 'Meeting'
            },
            {
                'text': 'Event on 09/29/2025 at 2pm',
                'expected_date': datetime(2025, 9, 29, 14, 0),
                'title': 'Event'
            },
            {
                'text': 'Conference on Sep 29, 2025',
                'expected_date': datetime(2025, 9, 29),
                'title': 'Conference'
            }
        ]
        
        for case in test_cases:
            mock_event = self.create_mock_llm_response(
                case['text'], 
                title=case['title'],
                start_time=case['expected_date']
            )
            self.mock_llm_service.llm_extract_event.return_value = mock_event
            
            result = self.parser.parse_event(case['text'])
            
            assert result.success, f"Failed for: {case['text']}"
            assert result.parsed_event.start_datetime is not None
            
            expected = case['expected_date']
            actual = result.parsed_event.start_datetime
            assert actual.year == expected.year
            assert actual.month == expected.month
            assert actual.day == expected.day
    
    def test_relative_date_parsing_scenarios(self):
        """Test relative date parsing scenarios."""
        test_cases = [
            {
                'text': 'Meeting tomorrow at 2pm',
                'title': 'Meeting',
                'relative_days': 1
            },
            {
                'text': 'Call next Friday',
                'title': 'Call',
                'relative_days': 7  # Approximate
            }
        ]
        
        for case in test_cases:
            expected_date = datetime.now() + timedelta(days=case['relative_days'])
            mock_event = self.create_mock_llm_response(
                case['text'],
                title=case['title'],
                start_time=expected_date
            )
            self.mock_llm_service.llm_extract_event.return_value = mock_event
            
            result = self.parser.parse_event(case['text'])
            
            assert result.success, f"Failed for: {case['text']}"
            assert result.parsed_event.start_datetime is not None
            
            # Check that date is in reasonable future range
            actual = result.parsed_event.start_datetime
            now = datetime.now()
            assert (actual - now).days >= 0  # Should be in future
            assert (actual - now).days <= 14  # Should be within 2 weeks
    
    # ===== TIME PARSING TESTS =====
    
    def test_explicit_time_parsing_scenarios(self):
        """Test explicit time parsing scenarios."""
        test_cases = [
            {
                'text': 'Meeting at 9:00 AM',
                'expected_hour': 9,
                'expected_minute': 0
            },
            {
                'text': 'Call at 14:30',
                'expected_hour': 14,
                'expected_minute': 30
            },
            {
                'text': 'Event at noon',
                'expected_hour': 12,
                'expected_minute': 0
            }
        ]
        
        for case in test_cases:
            start_time = datetime.now().replace(
                hour=case['expected_hour'], 
                minute=case['expected_minute']
            )
            mock_event = self.create_mock_llm_response(
                case['text'],
                start_time=start_time
            )
            self.mock_llm_service.llm_extract_event.return_value = mock_event
            
            result = self.parser.parse_event(case['text'])
            
            assert result.success, f"Failed for: {case['text']}"
            actual = result.parsed_event.start_datetime
            assert actual.hour == case['expected_hour']
            assert actual.minute == case['expected_minute']
    
    def test_typo_tolerant_time_parsing(self):
        """Test typo-tolerant time parsing."""
        test_cases = [
            'Meeting at 9a.m',
            'Call at 9am',
            'Event at 9:00 A M',
            'Meeting at 2 PM'
        ]
        
        for text in test_cases:
            # All should normalize to reasonable times
            start_time = datetime.now().replace(hour=9 if 'a' in text.lower() else 14, minute=0)
            mock_event = self.create_mock_llm_response(text, start_time=start_time)
            self.mock_llm_service.llm_extract_event.return_value = mock_event
            
            result = self.parser.parse_event(text)
            
            assert result.success, f"Failed for: {text}"
            assert result.parsed_event.start_datetime is not None
    
    # ===== LOCATION PARSING TESTS =====
    
    def test_location_parsing_scenarios(self):
        """Test various location parsing scenarios."""
        test_cases = [
            {
                'text': 'Meeting at Nathan Phillips Square',
                'expected_location': 'Nathan Phillips Square',
                'location_type': 'explicit'
            },
            {
                'text': 'Event at 123 Main Street',
                'expected_location': '123 Main Street',
                'location_type': 'address'
            },
            {
                'text': 'Meeting at school',
                'expected_location': 'school',
                'location_type': 'implicit'
            },
            {
                'text': 'Call from the office',
                'expected_location': 'the office',
                'location_type': 'implicit'
            },
            {
                'text': 'Meeting in Conference Room A',
                'expected_location': 'Conference Room A',
                'location_type': 'venue'
            }
        ]
        
        for case in test_cases:
            mock_event = self.create_mock_llm_response(
                case['text'],
                location=case['expected_location']
            )
            self.mock_llm_service.llm_extract_event.return_value = mock_event
            
            result = self.parser.parse_event(case['text'])
            
            assert result.success, f"Failed for: {case['text']}"
            assert result.parsed_event.location is not None
            
            # Check that key parts of location are present
            expected_lower = case['expected_location'].lower()
            actual_lower = result.parsed_event.location.lower()
            
            # Should contain main location concept
            key_words = [word for word in expected_lower.split() if len(word) > 2]
            if key_words:
                assert any(word in actual_lower for word in key_words), f"Location mismatch for: {case['text']}"
    
    # ===== TITLE PARSING TESTS =====
    
    def test_title_parsing_scenarios(self):
        """Test various title parsing scenarios."""
        test_cases = [
            {
                'text': 'Indigenous Legacy Gathering tomorrow at 2pm',
                'expected_title': 'Indigenous Legacy Gathering',
                'title_type': 'formal'
            },
            {
                'text': 'Meeting with John tomorrow at 2pm',
                'expected_title': 'Meeting with John',
                'title_type': 'context_derived'
            },
            {
                'text': 'Call with Sarah on Friday',
                'expected_title': 'Call with Sarah',
                'title_type': 'context_derived'
            },
            {
                'text': '"Annual Board Meeting" scheduled for Friday',
                'expected_title': 'Annual Board Meeting',
                'title_type': 'formal_quoted'
            }
        ]
        
        for case in test_cases:
            mock_event = self.create_mock_llm_response(
                case['text'],
                title=case['expected_title']
            )
            self.mock_llm_service.llm_extract_event.return_value = mock_event
            
            result = self.parser.parse_event(case['text'])
            
            assert result.success, f"Failed for: {case['text']}"
            assert result.parsed_event.title is not None
            
            # Check that title contains key elements
            expected_words = case['expected_title'].lower().split()
            actual_title = result.parsed_event.title.lower()
            
            # Most expected words should be present
            matching_words = sum(1 for word in expected_words if word in actual_title)
            assert matching_words >= len(expected_words) * 0.7, f"Title mismatch for: {case['text']}"
    
    # ===== FORMAT HANDLING TESTS =====
    
    def test_format_aware_processing(self):
        """Test format-aware text processing."""
        test_cases = [
            {
                'text': '''
                • Meeting with John
                • Tomorrow at 2pm
                • Conference Room A
                ''',
                'expected_format': TextFormat.BULLET_POINTS
            },
            {
                'text': '''
                Subject: Team Standup
                When: Tomorrow at 9:00 AM
                Where: Conference Room B
                ''',
                'expected_format': TextFormat.STRUCTURED_EMAIL
            },
            {
                'text': 'Meeting with John tomorrow at 2pm in Conference Room A',
                'expected_format': TextFormat.PLAIN_TEXT
            }
        ]
        
        for case in test_cases:
            mock_event = self.create_mock_llm_response(case['text'])
            self.mock_llm_service.llm_extract_event.return_value = mock_event
            
            result = self.parser.parse_event(case['text'])
            
            assert result.success, f"Failed for format test"
            assert result.format_result is not None
            
            # Check format detection (allow some flexibility)
            detected = result.format_result.detected_format
            expected = case['expected_format']
            
            if expected == TextFormat.BULLET_POINTS:
                assert detected in [TextFormat.BULLET_POINTS, TextFormat.MIXED]
            elif expected == TextFormat.STRUCTURED_EMAIL:
                assert detected in [TextFormat.STRUCTURED_EMAIL, TextFormat.MIXED]
            else:
                assert detected == expected
    
    # ===== ERROR CONDITION TESTS =====
    
    def test_no_event_information_detection(self):
        """Test detection of text with no event information."""
        test_cases = [
            'The weather is nice today',
            'How are you doing?',
            'This is just a regular sentence'
        ]
        
        for text in test_cases:
            # Mock LLM to return None (no event detected)
            self.mock_llm_service.llm_extract_event.return_value = None
            
            result = self.parser.parse_event(text)
            
            # Should handle gracefully
            if result.success:
                assert result.confidence_score < 0.3, f"Confidence too high for: {text}"
            else:
                assert 'no' in result.metadata.get('error', '').lower()
    
    def test_missing_critical_fields_handling(self):
        """Test handling of missing critical fields."""
        test_cases = [
            {
                'text': 'In Conference Room A',  # No title or time
                'missing_title': True,
                'missing_time': True
            },
            {
                'text': 'Meeting tomorrow',  # No time
                'missing_time': True
            }
        ]
        
        for case in test_cases:
            # Create event missing specified fields
            mock_event = ParsedEvent(
                title=None if case.get('missing_title') else 'Test Event',
                start_datetime=None if case.get('missing_time') else datetime.now(),
                description=case['text'],
                confidence_score=0.6
            )
            self.mock_llm_service.llm_extract_event.return_value = mock_event
            
            result = self.parser.parse_event(case['text'])
            
            # Should handle missing fields gracefully
            if result.success:
                assert result.error_handling_result is not None
            # If it fails, that's also acceptable for missing critical fields
    
    def test_low_confidence_handling(self):
        """Test handling of low confidence extractions."""
        test_cases = [
            'Maybe sometime next week?',
            'Meeting at 2',  # Ambiguous AM/PM
            'Possibly tomorrow'
        ]
        
        for text in test_cases:
            mock_event = self.create_mock_llm_response(text, confidence=0.3)  # Low confidence
            self.mock_llm_service.llm_extract_event.return_value = mock_event
            
            result = self.parser.parse_event(text)
            
            if result.success:
                # Should have low confidence and error handling
                assert result.confidence_score < 0.6, f"Confidence too high for: {text}"
                assert result.error_handling_result is not None
    
    # ===== PERFORMANCE BENCHMARKS =====
    
    def test_parsing_speed_benchmark(self):
        """Test parsing speed for performance benchmarks."""
        test_texts = [
            "Meeting with John tomorrow at 2pm in Conference Room A",
            "Team standup Friday at 9am",
            "Quarterly review next Monday from 10am to 11am in the boardroom",
            "Call with client at 3:30 PM",
            "Lunch meeting downtown at noon"
        ]
        
        mock_event = self.create_mock_llm_response("Test")
        self.mock_llm_service.llm_extract_event.return_value = mock_event
        
        # Measure parsing time
        start_time = time.time()
        
        for text in test_texts:
            result = self.parser.parse_event(text)
            assert result.success
        
        total_time = time.time() - start_time
        avg_time_per_parse = total_time / len(test_texts)
        
        # Performance benchmark: should parse each event in under 2 seconds (generous for mock)
        assert avg_time_per_parse < 2.0
    
    def test_parsing_accuracy_benchmark(self):
        """Test parsing accuracy across various scenarios."""
        test_cases = [
            "Meeting with John tomorrow at 2pm in Conference Room A",
            "Team standup Friday at 9am",
            "Call at 3:30 PM",
            "Lunch at noon downtown",
            "Conference next Monday from 10am to 11am"
        ]
        
        successful_parses = 0
        
        for text in test_cases:
            mock_event = self.create_mock_llm_response(text)
            self.mock_llm_service.llm_extract_event.return_value = mock_event
            
            result = self.parser.parse_event(text)
            
            if result.success and result.confidence_score > 0.5:
                successful_parses += 1
        
        accuracy = successful_parses / len(test_cases)
        
        # Accuracy benchmark: should successfully parse at least 80% of test cases
        assert accuracy >= 0.8
    
    # ===== INTEGRATION TESTS =====
    
    def test_end_to_end_parsing_pipeline(self):
        """Test complete end-to-end parsing pipeline."""
        test_text = "Indigenous Legacy Gathering tomorrow at 2:30 PM in Nathan Phillips Square"
        
        start_time = (datetime.now() + timedelta(days=1)).replace(hour=14, minute=30, second=0, microsecond=0)
        end_time = start_time + timedelta(hours=1)
        
        mock_event = ParsedEvent(
            title="Indigenous Legacy Gathering",
            start_datetime=start_time,
            end_datetime=end_time,
            location="Nathan Phillips Square",
            description=test_text,
            confidence_score=0.9,
            extraction_metadata={'llm_provider': 'mock'}
        )
        self.mock_llm_service.llm_extract_event.return_value = mock_event
        
        result = self.parser.parse_event(test_text)
        
        # Verify complete pipeline
        assert result.success
        assert result.parsing_method == "llm_primary"
        assert result.parsed_event is not None
        assert result.normalized_event is not None
        assert result.format_result is not None
        assert result.confidence_score > 0.8
        
        # Verify event details
        event = result.parsed_event
        assert event.title == "Indigenous Legacy Gathering"
        assert event.location == "Nathan Phillips Square"
        assert event.start_datetime.hour == 14
        assert event.start_datetime.minute == 30
        
        # Verify normalized output
        normalized = result.normalized_event
        assert normalized.title == event.title
        assert normalized.start_datetime == event.start_datetime
        assert normalized.confidence_score > 0.8
    
    def test_fallback_mechanism_integration(self):
        """Test integration of LLM-first with fallback mechanisms."""
        test_text = "Meeting with John tomorrow at 2pm"
        
        # Test LLM failure scenario
        self.mock_llm_service.llm_extract_event.return_value = None
        
        result = self.parser.parse_event(test_text)
        
        # Should fall back to regex and still succeed
        assert result.success
        assert "regex_fallback" in result.parsing_method
        assert result.parsed_event is not None
    
    def test_component_enhancement_integration(self):
        """Test integration of component enhancement services."""
        test_text = "Meeting tomorrow at 2pm in Conference Room A"
        
        # Mock LLM result missing location
        mock_event = ParsedEvent(
            title="Meeting",
            start_datetime=datetime.now() + timedelta(days=1, hours=14),
            location=None,  # Missing location
            description=test_text,
            confidence_score=0.7
        )
        self.mock_llm_service.llm_extract_event.return_value = mock_event
        
        # Enable component enhancement
        self.parser.config['enable_component_enhancement'] = True
        
        result = self.parser.parse_event(test_text)
        
        assert result.success
        assert "enhanced" in result.parsing_method
        # Location should be enhanced by AdvancedLocationExtractor
        assert result.parsed_event.location is not None
        
        # Check enhancement metadata
        metadata = result.parsed_event.extraction_metadata
        assert metadata.get('location_enhanced') is True


class TestRealWorldEmailScenarios:
    """Test real-world email parsing scenarios."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_llm_service = Mock(spec=LLMService)
        self.mock_llm_service.is_available.return_value = True
        self.parser = MasterEventParser(llm_service=self.mock_llm_service)
    
    def test_outlook_meeting_invitation(self):
        """Test parsing Outlook meeting invitation format."""
        email_text = """
        Subject: Team Standup - Weekly
        When: Monday, October 7, 2024 9:00 AM-10:00 AM (UTC-05:00) Eastern Time (US & Canada)
        Where: Microsoft Teams Meeting
        
        Weekly team standup to discuss progress and blockers.
        """
        
        mock_event = ParsedEvent(
            title="Team Standup - Weekly",
            start_datetime=datetime(2024, 10, 7, 9, 0),
            end_datetime=datetime(2024, 10, 7, 10, 0),
            location="Microsoft Teams Meeting",
            description=email_text,
            confidence_score=0.95
        )
        self.mock_llm_service.llm_extract_event.return_value = mock_event
        
        result = self.parser.parse_event(email_text)
        
        assert result.success
        assert result.format_result.detected_format == TextFormat.STRUCTURED_EMAIL
        assert "Team Standup" in result.parsed_event.title
        assert result.parsed_event.location == "Microsoft Teams Meeting"
    
    def test_gmail_event_snippet(self):
        """Test parsing Gmail event snippet format."""
        email_text = """
        Hi team,
        
        Let's schedule our quarterly planning session for next Friday, October 11th 
        from 2:00 PM to 4:00 PM. We'll meet in the large conference room on the 
        3rd floor. Please bring your Q4 goals and current project status.
        
        Thanks,
        Sarah
        """
        
        mock_event = ParsedEvent(
            title="Quarterly planning session",
            start_datetime=datetime(2024, 10, 11, 14, 0),
            end_datetime=datetime(2024, 10, 11, 16, 0),
            location="large conference room on the 3rd floor",
            description=email_text,
            confidence_score=0.85
        )
        self.mock_llm_service.llm_extract_event.return_value = mock_event
        
        result = self.parser.parse_event(email_text)
        
        assert result.success
        assert result.format_result.detected_format == TextFormat.PARAGRAPHS
        assert "planning" in result.parsed_event.title.lower()
        assert "conference room" in result.parsed_event.location.lower()


if __name__ == "__main__":
    pytest.main([__file__])