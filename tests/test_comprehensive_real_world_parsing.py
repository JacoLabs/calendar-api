"""
Comprehensive real-world testing suite for the complete LLM-first parsing pipeline.

Tests all enumerated parsing scenarios including dates, times, locations, titles,
various text formats, typo handling, error conditions, and performance benchmarks.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
import time
import json

from services.master_event_parser import MasterEventParser, get_master_parser
from services.llm_service import LLMService
from models.event_models import ParsedEvent, NormalizedEvent
from services.format_aware_text_processor import TextFormat


class TestComprehensiveRealWorldParsing:
    """Comprehensive test suite for real-world parsing scenarios."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Create mock LLM service for controlled testing
        self.mock_llm_service = Mock(spec=LLMService)
        self.mock_llm_service.is_available.return_value = True
        
        # Create parser with mock LLM service
        self.parser = MasterEventParser(llm_service=self.mock_llm_service)
        
        # Test data collections
        self.date_test_cases = self._load_date_test_cases()
        self.time_test_cases = self._load_time_test_cases()
        self.location_test_cases = self._load_location_test_cases()
        self.title_test_cases = self._load_title_test_cases()
        self.format_test_cases = self._load_format_test_cases()
        self.typo_test_cases = self._load_typo_test_cases()
        self.error_test_cases = self._load_error_test_cases()
    
    def _load_date_test_cases(self):
        """Load comprehensive date parsing test cases."""
        return [
            # Explicit dates
            {
                'text': 'Meeting on Monday, September 29, 2025',
                'expected_date': datetime(2025, 9, 29),
                'category': 'explicit_full_date'
            },
            {
                'text': 'Event on 09/29/2025',
                'expected_date': datetime(2025, 9, 29),
                'category': 'explicit_numeric_date'
            },
            {
                'text': 'Conference on Sep 29, 2025',
                'expected_date': datetime(2025, 9, 29),
                'category': 'explicit_abbreviated_date'
            },
            {
                'text': 'Workshop on September 29th',
                'expected_date': datetime.now().replace(month=9, day=29),
                'category': 'explicit_date_no_year'
            },
            
            # Relative dates
            {
                'text': 'Meeting tomorrow at 2pm',
                'expected_date': datetime.now() + timedelta(days=1),
                'category': 'relative_tomorrow'
            },
            {
                'text': 'Call next Friday',
                'expected_date': self._get_next_weekday(4),  # Friday = 4
                'category': 'relative_next_weekday'
            },
            {
                'text': 'Event in two weeks',
                'expected_date': datetime.now() + timedelta(weeks=2),
                'category': 'relative_weeks'
            },
            {
                'text': 'Meeting this Monday',
                'expected_date': self._get_this_weekday(0),  # Monday = 0
                'category': 'relative_this_weekday'
            },
            
            # Natural phrases
            {
                'text': 'First day back after break',
                'expected_date': None,  # Context-dependent
                'category': 'natural_phrase'
            },
            {
                'text': 'End of month meeting',
                'expected_date': None,  # Context-dependent
                'category': 'natural_phrase'
            }
        ]
    
    def _load_time_test_cases(self):
        """Load comprehensive time parsing test cases."""
        return [
            # Explicit times - standard formats
            {
                'text': 'Meeting at 9:00 AM',
                'expected_time': (9, 0),
                'category': 'explicit_12hour_colon'
            },
            {
                'text': 'Call at 14:30',
                'expected_time': (14, 30),
                'category': 'explicit_24hour'
            },
            {
                'text': 'Event at noon',
                'expected_time': (12, 0),
                'category': 'explicit_named_time'
            },
            {
                'text': 'Meeting at midnight',
                'expected_time': (0, 0),
                'category': 'explicit_named_time'
            },
            
            # Typo-tolerant time parsing
            {
                'text': 'Meeting at 9a.m',
                'expected_time': (9, 0),
                'category': 'typo_am_periods'
            },
            {
                'text': 'Call at 9am',
                'expected_time': (9, 0),
                'category': 'typo_am_no_periods'
            },
            {
                'text': 'Event at 9:00 A M',
                'expected_time': (9, 0),
                'category': 'typo_am_spaces'
            },
            {
                'text': 'Meeting at 2 PM',
                'expected_time': (14, 0),
                'category': 'typo_pm_space'
            },
            
            # Relative times
            {
                'text': 'Lunch after lunch',
                'expected_time': (13, 0),  # Approximate
                'category': 'relative_after_lunch'
            },
            {
                'text': 'Meeting before school',
                'expected_time': (8, 0),  # Approximate
                'category': 'relative_before_school'
            },
            {
                'text': 'Call end of day',
                'expected_time': (17, 0),  # Approximate
            },
            
            # Time ranges
            {
                'text': 'Meeting from 9–10 a.m.',
                'expected_start': (9, 0),
                'expected_end': (10, 0),
                'category': 'range_dash_am'
            },
            {
                'text': 'Event from 3 p.m. to 5 p.m.',
                'expected_start': (15, 0),
                'expected_end': (17, 0),
                'category': 'range_to_pm'
            },
            {
                'text': 'Workshop 2:00-3:30',
                'expected_start': (14, 0),
                'expected_end': (15, 30),
                'category': 'range_dash_24hour'
            },
            
            # Duration information
            {
                'text': 'Meeting for 2 hours',
                'duration_hours': 2,
                'category': 'duration_hours'
            },
            {
                'text': 'Call for 30 minutes',
                'duration_minutes': 30,
                'category': 'duration_minutes'
            },
            {
                'text': 'Event 1.5 hours long',
                'duration_hours': 1.5,
                'category': 'duration_decimal'
            }
        ]
    
    def _load_location_test_cases(self):
        """Load comprehensive location parsing test cases."""
        return [
            # Explicit addresses
            {
                'text': 'Meeting at Nathan Phillips Square',
                'expected_location': 'Nathan Phillips Square',
                'location_type': 'address',
                'category': 'explicit_named_location'
            },
            {
                'text': 'Event at 123 Main Street',
                'expected_location': '123 Main Street',
                'location_type': 'address',
                'category': 'explicit_street_address'
            },
            {
                'text': 'Conference at Toronto City Hall, 100 Queen St W, Toronto, ON M5H 2N2',
                'expected_location': 'Toronto City Hall, 100 Queen St W, Toronto, ON M5H 2N2',
                'location_type': 'address',
                'category': 'explicit_full_address'
            },
            
            # Implicit locations
            {
                'text': 'Meeting at school',
                'expected_location': 'school',
                'location_type': 'implicit',
                'category': 'implicit_educational'
            },
            {
                'text': 'Call from the office',
                'expected_location': 'the office',
                'location_type': 'implicit',
                'category': 'implicit_workplace'
            },
            {
                'text': 'Lunch at the gym',
                'expected_location': 'the gym',
                'location_type': 'implicit',
                'category': 'implicit_recreational'
            },
            {
                'text': 'Meeting downtown',
                'expected_location': 'downtown',
                'location_type': 'implicit',
                'category': 'implicit_area'
            },
            
            # Directional locations
            {
                'text': 'Meet at the front doors',
                'expected_location': 'the front doors',
                'location_type': 'directional',
                'category': 'directional_entrance'
            },
            {
                'text': 'Gathering by the entrance',
                'expected_location': 'by the entrance',
                'location_type': 'directional',
                'category': 'directional_relative'
            },
            {
                'text': 'Meeting in the lobby',
                'expected_location': 'the lobby',
                'location_type': 'directional',
                'category': 'directional_area'
            },
            
            # Venue keywords
            {
                'text': 'Conference at Convention Center',
                'expected_location': 'Convention Center',
                'location_type': 'venue',
                'category': 'venue_center'
            },
            {
                'text': 'Event at Memorial Hall',
                'expected_location': 'Memorial Hall',
                'location_type': 'venue',
                'category': 'venue_hall'
            },
            {
                'text': 'Meeting in Conference Room A',
                'expected_location': 'Conference Room A',
                'location_type': 'venue',
                'category': 'venue_room'
            },
            {
                'text': 'Workshop in Building 5',
                'expected_location': 'Building 5',
                'location_type': 'venue',
                'category': 'venue_building'
            },
            
            # Context clues
            {
                'text': 'Meeting @ Central Library',
                'expected_location': 'Central Library',
                'location_type': 'venue',
                'category': 'context_at_symbol'
            },
            {
                'text': 'Event\nVenue: Grand Ballroom',
                'expected_location': 'Grand Ballroom',
                'location_type': 'venue',
                'category': 'context_venue_colon'
            },
            {
                'text': 'Location: Room 204',
                'expected_location': 'Room 204',
                'location_type': 'venue',
                'category': 'context_location_colon'
            }
        ]
    
    def _load_title_test_cases(self):
        """Load comprehensive title parsing test cases."""
        return [
            # Formal event names
            {
                'text': 'Indigenous Legacy Gathering tomorrow at 2pm',
                'expected_title': 'Indigenous Legacy Gathering',
                'title_type': 'formal',
                'category': 'formal_proper_noun'
            },
            {
                'text': '"Annual Board Meeting" scheduled for Friday',
                'expected_title': 'Annual Board Meeting',
                'title_type': 'formal',
                'category': 'formal_quoted'
            },
            {
                'text': 'Monthly Team Standup at 9am',
                'expected_title': 'Monthly Team Standup',
                'title_type': 'formal',
                'category': 'formal_descriptive'
            },
            
            # Context-derived titles
            {
                'text': 'Meeting with John tomorrow at 2pm',
                'expected_title': 'Meeting with John',
                'title_type': 'context_derived',
                'category': 'context_meeting_with'
            },
            {
                'text': 'Call with Sarah on Friday',
                'expected_title': 'Call with Sarah',
                'title_type': 'context_derived',
                'category': 'context_call_with'
            },
            {
                'text': 'Lunch with the team next week',
                'expected_title': 'Lunch with the team',
                'title_type': 'context_derived',
                'category': 'context_meal_with'
            },
            {
                'text': 'Interview with candidate tomorrow',
                'expected_title': 'Interview with candidate',
                'title_type': 'context_derived',
                'category': 'context_interview_with'
            },
            
            # Action-based titles
            {
                'text': 'We will review the quarterly reports tomorrow',
                'expected_title': 'Review the quarterly reports',
                'title_type': 'action_based',
                'category': 'action_we_will'
            },
            {
                'text': "Let's discuss the project timeline",
                'expected_title': 'Discuss the project timeline',
                'title_type': 'action_based',
                'category': 'action_lets'
            },
            {
                'text': 'Need to finalize the budget by Friday',
                'expected_title': 'Finalize the budget',
                'title_type': 'action_based',
                'category': 'action_need_to'
            },
            
            # Generated titles (when no explicit title)
            {
                'text': 'Tomorrow at 2pm in Conference Room A',
                'expected_title': None,  # Should generate or prompt
                'title_type': 'generated',
                'category': 'no_explicit_title'
            },
            {
                'text': 'Meeting at 3pm',
                'expected_title': 'Meeting',
                'title_type': 'simple',
                'category': 'simple_action_word'
            }
        ]
    
    def _load_format_test_cases(self):
        """Load various text format test cases."""
        return [
            # Bullet points
            {
                'text': '''
                • Meeting with John
                • Tomorrow at 2pm
                • Conference Room A
                ''',
                'format_type': TextFormat.BULLET_POINTS,
                'category': 'bullet_points_standard'
            },
            {
                'text': '''
                1. Team standup
                2. Friday at 9am
                3. Main conference room
                ''',
                'format_type': TextFormat.BULLET_POINTS,
                'category': 'bullet_points_numbered'
            },
            
            # Structured email
            {
                'text': '''
                Subject: Quarterly Review
                When: Monday, October 1st at 10:00 AM
                Where: Boardroom
                
                Please join us for the quarterly business review.
                ''',
                'format_type': TextFormat.STRUCTURED_EMAIL,
                'category': 'structured_email_formal'
            },
            {
                'text': '''
                Meeting: Project Kickoff
                Date: Tomorrow
                Time: 2:00 PM
                Location: Room 301
                ''',
                'format_type': TextFormat.STRUCTURED_EMAIL,
                'category': 'structured_meeting_format'
            },
            
            # Paragraphs
            {
                'text': '''
                We need to schedule our weekly team meeting for this Friday. 
                The meeting should start at 10:00 AM and will be held in the 
                main conference room. Please bring your status updates.
                ''',
                'format_type': TextFormat.PARAGRAPHS,
                'category': 'paragraph_embedded_info'
            },
            
            # Mixed format
            {
                'text': '''
                Team Meeting Details:
                • Date: This Friday
                • Time: 10:00 AM - 11:00 AM
                
                We'll be discussing the quarterly goals and reviewing 
                project timelines. Location is the main conference room.
                ''',
                'format_type': TextFormat.MIXED,
                'category': 'mixed_bullets_and_paragraphs'
            },
            
            # Plain text variations
            {
                'text': 'Quick standup tomorrow 9am conference room',
                'format_type': TextFormat.PLAIN_TEXT,
                'category': 'plain_text_compact'
            },
            {
                'text': 'Meeting with John tomorrow at 2pm in Conference Room A to discuss project timeline',
                'format_type': TextFormat.PLAIN_TEXT,
                'category': 'plain_text_sentence'
            }
        ]
    
    def _load_typo_test_cases(self):
        """Load typo handling and normalization test cases."""
        return [
            # Time format typos
            {
                'text': 'Meeting at 9a.m tomorrow',
                'expected_normalized': 'Meeting at 9:00 AM tomorrow',
                'category': 'time_typo_am_periods'
            },
            {
                'text': 'Call at 2 p m',
                'expected_normalized': 'Call at 2:00 PM',
                'category': 'time_typo_pm_spaces'
            },
            {
                'text': 'Event at 14.30',
                'expected_normalized': 'Event at 14:30',
                'category': 'time_typo_period_separator'
            },
            
            # Date format variations
            {
                'text': 'Meeting on 09-29-2025',
                'expected_normalized': 'Meeting on 09/29/2025',
                'category': 'date_typo_dash_separator'
            },
            {
                'text': 'Event on Sep. 29th, 2025',
                'expected_normalized': 'Event on Sep 29, 2025',
                'category': 'date_typo_extra_periods'
            },
            
            # Case normalization
            {
                'text': 'MEETING WITH JOHN TOMORROW AT 2PM',
                'expected_normalized': 'Meeting with John tomorrow at 2:00 PM',
                'category': 'case_all_caps'
            },
            {
                'text': 'meeting with john tomorrow at 2pm',
                'expected_normalized': 'Meeting with John tomorrow at 2:00 PM',
                'category': 'case_all_lowercase'
            },
            
            # Whitespace normalization
            {
                'text': 'Meeting    with   John     tomorrow',
                'expected_normalized': 'Meeting with John tomorrow',
                'category': 'whitespace_multiple_spaces'
            },
            {
                'text': 'Meeting\n\nwith\n\nJohn',
                'expected_normalized': 'Meeting with John',
                'category': 'whitespace_multiple_newlines'
            }
        ]
    
    def _load_error_test_cases(self):
        """Load error condition and edge case test cases."""
        return [
            # Low confidence scenarios
            {
                'text': 'Maybe sometime next week?',
                'expected_confidence': 0.2,
                'category': 'low_confidence_vague'
            },
            {
                'text': 'Meeting at 2',  # Ambiguous AM/PM
                'expected_confidence': 0.4,
                'category': 'low_confidence_ambiguous'
            },
            
            # Missing critical information
            {
                'text': 'In Conference Room A',  # No time or title
                'missing_fields': ['title', 'start_datetime'],
                'category': 'missing_critical_info'
            },
            {
                'text': 'Meeting tomorrow',  # No time
                'missing_fields': ['start_datetime'],
                'category': 'missing_time'
            },
            
            # Multiple interpretations
            {
                'text': 'Meeting Monday at 2pm and Tuesday at 3pm',
                'multiple_events': True,
                'category': 'multiple_events'
            },
            {
                'text': 'Call at 2pm or 3pm tomorrow',
                'ambiguous_time': True,
                'category': 'ambiguous_multiple_times'
            },
            
            # No event information
            {
                'text': 'The weather is nice today',
                'no_event_info': True,
                'category': 'no_event_content'
            },
            {
                'text': 'How are you doing?',
                'no_event_info': True,
                'category': 'question_not_event'
            },
            
            # Edge cases
            {
                'text': '',  # Empty text
                'empty_text': True,
                'category': 'empty_input'
            },
            {
                'text': 'a',  # Single character
                'minimal_text': True,
                'category': 'minimal_input'
            },
            {
                'text': 'Meeting ' * 100,  # Very long text
                'long_text': True,
                'category': 'excessive_length'
            }
        ]
    
    def _get_next_weekday(self, weekday):
        """Get the next occurrence of a weekday (0=Monday, 6=Sunday)."""
        today = datetime.now()
        days_ahead = weekday - today.weekday()
        if days_ahead <= 0:  # Target day already happened this week
            days_ahead += 7
        return today + timedelta(days=days_ahead)
    
    def _get_this_weekday(self, weekday):
        """Get this week's occurrence of a weekday."""
        today = datetime.now()
        days_ahead = weekday - today.weekday()
        return today + timedelta(days=days_ahead)
    
    def create_mock_llm_response(self, text, expected_data=None):
        """Create appropriate mock LLM response based on test case."""
        if expected_data is None:
            expected_data = {}
        
        # Extract expected values from test case
        title = expected_data.get('expected_title', 'Test Event')
        
        # Create datetime from expected data
        start_datetime = expected_data.get('expected_date', datetime.now() + timedelta(days=1))
        if 'expected_time' in expected_data:
            hour, minute = expected_data['expected_time']
            start_datetime = start_datetime.replace(hour=hour, minute=minute)
        
        end_datetime = start_datetime + timedelta(hours=1)
        if 'expected_end' in expected_data:
            end_hour, end_minute = expected_data['expected_end']
            end_datetime = start_datetime.replace(hour=end_hour, minute=end_minute)
        elif 'duration_hours' in expected_data:
            end_datetime = start_datetime + timedelta(hours=expected_data['duration_hours'])
        elif 'duration_minutes' in expected_data:
            end_datetime = start_datetime + timedelta(minutes=expected_data['duration_minutes'])
        
        location = expected_data.get('expected_location')
        confidence = expected_data.get('expected_confidence', 0.8)
        
        return ParsedEvent(
            title=title,
            start_datetime=start_datetime,
            end_datetime=end_datetime,
            location=location,
            description=text,
            confidence_score=confidence,
            extraction_metadata={
                'llm_provider': 'mock',
                'test_case': expected_data.get('category', 'unknown')
            }
        )
    
    # ===== DATE PARSING TESTS =====
    
    def test_explicit_date_parsing(self):
        """Test explicit date parsing scenarios."""
        test_cases = [case for case in self.date_test_cases if case['category'].startswith('explicit')]
        
        for test_case in test_cases:
            mock_event = self.create_mock_llm_response(test_case['text'], test_case)
            self.mock_llm_service.llm_extract_event.return_value = mock_event
            
            result = self.parser.parse_event(test_case['text'])
            
            assert result.success, f"Failed for case: {test_case['category']}"
            assert result.parsed_event.start_datetime is not None
            
            if test_case['expected_date']:
                expected = test_case['expected_date']
                actual = result.parsed_event.start_datetime
                # Compare date parts (ignore time for date-only tests)
                assert actual.year == expected.year
                assert actual.month == expected.month
                assert actual.day == expected.day
    
    def test_relative_date_parsing(self):
        """Test relative date parsing scenarios."""
        test_cases = [case for case in self.date_test_cases if case['category'].startswith('relative')]
        
        for test_case in test_cases:
            mock_event = self.create_mock_llm_response(test_case['text'], test_case)
            self.mock_llm_service.llm_extract_event.return_value = mock_event
            
            result = self.parser.parse_event(test_case['text'])
            
            assert result.success, f"Failed for case: {test_case['category']}"
            assert result.parsed_event.start_datetime is not None
            
            # For relative dates, check that the date is reasonable (within expected range)
            actual = result.parsed_event.start_datetime
            now = datetime.now()
            
            if 'tomorrow' in test_case['text']:
                expected_date = now + timedelta(days=1)
                assert abs((actual.date() - expected_date.date()).days) <= 1
            elif 'next' in test_case['text'] and 'week' in test_case['text']:
                # Should be within next 2 weeks
                assert timedelta(days=7) <= (actual - now) <= timedelta(days=14)
    
    # ===== TIME PARSING TESTS =====
    
    @pytest.mark.parametrize("test_case", [
        case for case in TestComprehensiveRealWorldParsing()._load_time_test_cases()
        if case['category'].startswith('explicit')
    ])
    def test_explicit_time_parsing(self, test_case):
        """Test explicit time parsing scenarios."""
        mock_event = self.create_mock_llm_response(test_case['text'], test_case)
        self.mock_llm_service.llm_extract_event.return_value = mock_event
        
        result = self.parser.parse_event(test_case['text'])
        
        assert result.success
        assert result.parsed_event.start_datetime is not None
        
        if 'expected_time' in test_case:
            expected_hour, expected_minute = test_case['expected_time']
            actual = result.parsed_event.start_datetime
            assert actual.hour == expected_hour
            assert actual.minute == expected_minute
    
    @pytest.mark.parametrize("test_case", [
        case for case in TestComprehensiveRealWorldParsing()._load_time_test_cases()
        if case['category'].startswith('typo')
    ])
    def test_typo_tolerant_time_parsing(self, test_case):
        """Test typo-tolerant time parsing scenarios."""
        mock_event = self.create_mock_llm_response(test_case['text'], test_case)
        self.mock_llm_service.llm_extract_event.return_value = mock_event
        
        result = self.parser.parse_event(test_case['text'])
        
        assert result.success
        assert result.parsed_event.start_datetime is not None
        
        # Check that typos were handled correctly
        if 'expected_time' in test_case:
            expected_hour, expected_minute = test_case['expected_time']
            actual = result.parsed_event.start_datetime
            assert actual.hour == expected_hour
            assert actual.minute == expected_minute
    
    @pytest.mark.parametrize("test_case", [
        case for case in TestComprehensiveRealWorldParsing()._load_time_test_cases()
        if case['category'].startswith('range')
    ])
    def test_time_range_parsing(self, test_case):
        """Test time range parsing scenarios."""
        mock_event = self.create_mock_llm_response(test_case['text'], test_case)
        self.mock_llm_service.llm_extract_event.return_value = mock_event
        
        result = self.parser.parse_event(test_case['text'])
        
        assert result.success
        assert result.parsed_event.start_datetime is not None
        assert result.parsed_event.end_datetime is not None
        
        # Check start and end times
        if 'expected_start' in test_case:
            start_hour, start_minute = test_case['expected_start']
            assert result.parsed_event.start_datetime.hour == start_hour
            assert result.parsed_event.start_datetime.minute == start_minute
        
        if 'expected_end' in test_case:
            end_hour, end_minute = test_case['expected_end']
            assert result.parsed_event.end_datetime.hour == end_hour
            assert result.parsed_event.end_datetime.minute == end_minute
    
    # ===== LOCATION PARSING TESTS =====
    
    @pytest.mark.parametrize("test_case", [
        case for case in TestComprehensiveRealWorldParsing()._load_location_test_cases()
        if case['location_type'] == 'address'
    ])
    def test_explicit_address_parsing(self, test_case):
        """Test explicit address parsing scenarios."""
        mock_event = self.create_mock_llm_response(test_case['text'], test_case)
        self.mock_llm_service.llm_extract_event.return_value = mock_event
        
        result = self.parser.parse_event(test_case['text'])
        
        assert result.success
        if test_case['expected_location']:
            assert result.parsed_event.location is not None
            # Check that key parts of the location are present
            expected_parts = test_case['expected_location'].lower().split()
            actual_location = result.parsed_event.location.lower()
            
            # At least half of the expected location parts should be present
            matching_parts = sum(1 for part in expected_parts if part in actual_location)
            assert matching_parts >= len(expected_parts) * 0.5
    
    @pytest.mark.parametrize("test_case", [
        case for case in TestComprehensiveRealWorldParsing()._load_location_test_cases()
        if case['location_type'] in ['implicit', 'directional', 'venue']
    ])
    def test_contextual_location_parsing(self, test_case):
        """Test contextual location parsing scenarios."""
        mock_event = self.create_mock_llm_response(test_case['text'], test_case)
        self.mock_llm_service.llm_extract_event.return_value = mock_event
        
        result = self.parser.parse_event(test_case['text'])
        
        assert result.success
        if test_case['expected_location']:
            assert result.parsed_event.location is not None
            # For contextual locations, check that the key concept is captured
            expected_key = test_case['expected_location'].lower()
            actual_location = result.parsed_event.location.lower()
            
            # Should contain the main location concept
            key_words = [word for word in expected_key.split() if len(word) > 2]
            if key_words:
                assert any(word in actual_location for word in key_words)
    
    # ===== TITLE PARSING TESTS =====
    
    @pytest.mark.parametrize("test_case", [
        case for case in TestComprehensiveRealWorldParsing()._load_title_test_cases()
        if case['title_type'] == 'formal'
    ])
    def test_formal_title_parsing(self, test_case):
        """Test formal event title parsing scenarios."""
        mock_event = self.create_mock_llm_response(test_case['text'], test_case)
        self.mock_llm_service.llm_extract_event.return_value = mock_event
        
        result = self.parser.parse_event(test_case['text'])
        
        assert result.success
        if test_case['expected_title']:
            assert result.parsed_event.title is not None
            # Check that the title contains key elements
            expected_words = test_case['expected_title'].lower().split()
            actual_title = result.parsed_event.title.lower()
            
            # Most of the expected title words should be present
            matching_words = sum(1 for word in expected_words if word in actual_title)
            assert matching_words >= len(expected_words) * 0.7
    
    @pytest.mark.parametrize("test_case", [
        case for case in TestComprehensiveRealWorldParsing()._load_title_test_cases()
        if case['title_type'] == 'context_derived'
    ])
    def test_context_derived_title_parsing(self, test_case):
        """Test context-derived title parsing scenarios."""
        mock_event = self.create_mock_llm_response(test_case['text'], test_case)
        self.mock_llm_service.llm_extract_event.return_value = mock_event
        
        result = self.parser.parse_event(test_case['text'])
        
        assert result.success
        assert result.parsed_event.title is not None
        
        # For context-derived titles, check that the action and context are captured
        title = result.parsed_event.title.lower()
        text = test_case['text'].lower()
        
        # Should contain the main action word
        if 'meeting' in text:
            assert 'meeting' in title or 'meet' in title
        elif 'call' in text:
            assert 'call' in title
        elif 'lunch' in text:
            assert 'lunch' in title
        elif 'interview' in text:
            assert 'interview' in title
    
    # ===== FORMAT HANDLING TESTS =====
    
    @pytest.mark.parametrize("test_case", [
        case for case in TestComprehensiveRealWorldParsing()._load_format_test_cases()
    ])
    def test_format_aware_processing(self, test_case):
        """Test format-aware text processing scenarios."""
        mock_event = self.create_mock_llm_response(test_case['text'], {})
        self.mock_llm_service.llm_extract_event.return_value = mock_event
        
        result = self.parser.parse_event(test_case['text'])
        
        assert result.success
        assert result.format_result is not None
        
        # Check that format was detected correctly
        detected_format = result.format_result.detected_format
        expected_format = test_case['format_type']
        
        # Allow some flexibility in format detection
        if expected_format == TextFormat.BULLET_POINTS:
            assert detected_format in [TextFormat.BULLET_POINTS, TextFormat.MIXED]
        elif expected_format == TextFormat.STRUCTURED_EMAIL:
            assert detected_format in [TextFormat.STRUCTURED_EMAIL, TextFormat.MIXED]
        else:
            assert detected_format == expected_format
    
    # ===== TYPO HANDLING TESTS =====
    
    @pytest.mark.parametrize("test_case", [
        case for case in TestComprehensiveRealWorldParsing()._load_typo_test_cases()
    ])
    def test_typo_normalization(self, test_case):
        """Test typo handling and text normalization scenarios."""
        mock_event = self.create_mock_llm_response(test_case['text'], {})
        self.mock_llm_service.llm_extract_event.return_value = mock_event
        
        result = self.parser.parse_event(test_case['text'])
        
        assert result.success
        assert result.format_result is not None
        
        # Check that text was normalized
        processed_text = result.format_result.processed_text
        
        # Verify specific normalizations based on category
        if 'time_typo' in test_case['category']:
            # Should have normalized time format
            assert 'AM' in processed_text or 'PM' in processed_text or ':' in processed_text
        elif 'case_' in test_case['category']:
            # Should have proper capitalization
            assert not processed_text.isupper()  # Not all caps
            assert not processed_text.islower()  # Not all lowercase
        elif 'whitespace_' in test_case['category']:
            # Should have normalized whitespace
            assert '  ' not in processed_text  # No double spaces
            assert '\n\n\n' not in processed_text  # No triple newlines
    
    # ===== ERROR CONDITION TESTS =====
    
    @pytest.mark.parametrize("test_case", [
        case for case in TestComprehensiveRealWorldParsing()._load_error_test_cases()
        if case.get('no_event_info')
    ])
    def test_no_event_information_detection(self, test_case):
        """Test detection of text with no event information."""
        # Mock LLM to return None or very low confidence
        self.mock_llm_service.llm_extract_event.return_value = None
        
        result = self.parser.parse_event(test_case['text'])
        
        # Should handle gracefully - either fail cleanly or return very low confidence
        if result.success:
            assert result.confidence_score < 0.3
        else:
            assert 'no' in result.metadata.get('error', '').lower()
    
    @pytest.mark.parametrize("test_case", [
        case for case in TestComprehensiveRealWorldParsing()._load_error_test_cases()
        if case.get('missing_fields')
    ])
    def test_missing_critical_fields_handling(self, test_case):
        """Test handling of missing critical fields."""
        # Create mock event missing specified fields
        mock_event = ParsedEvent(
            title=None if 'title' in test_case['missing_fields'] else 'Test Event',
            start_datetime=None if 'start_datetime' in test_case['missing_fields'] else datetime.now(),
            description=test_case['text'],
            confidence_score=0.6
        )
        self.mock_llm_service.llm_extract_event.return_value = mock_event
        
        result = self.parser.parse_event(test_case['text'])
        
        # Should handle missing fields gracefully
        if result.success:
            # Error handling should have resolved the issues
            assert result.error_handling_result is not None
        else:
            # Or should fail with appropriate error message
            assert any(field in str(result.metadata) for field in test_case['missing_fields'])
    
    @pytest.mark.parametrize("test_case", [
        case for case in TestComprehensiveRealWorldParsing()._load_error_test_cases()
        if case.get('expected_confidence', 1.0) < 0.5
    ])
    def test_low_confidence_handling(self, test_case):
        """Test handling of low confidence extractions."""
        mock_event = self.create_mock_llm_response(test_case['text'], test_case)
        self.mock_llm_service.llm_extract_event.return_value = mock_event
        
        result = self.parser.parse_event(test_case['text'])
        
        # Should handle low confidence appropriately
        if result.success:
            # Should have low confidence score
            assert result.confidence_score < 0.6
            # Should have error handling result
            assert result.error_handling_result is not None
        else:
            # Or should fail with confidence-related error
            assert 'confidence' in str(result.metadata).lower()
    
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
        
        mock_event = ParsedEvent(
            title="Test Event",
            start_datetime=datetime.now() + timedelta(days=1),
            end_datetime=datetime.now() + timedelta(days=1, hours=1),
            confidence_score=0.8
        )
        self.mock_llm_service.llm_extract_event.return_value = mock_event
        
        # Measure parsing time
        start_time = time.time()
        
        for text in test_texts:
            result = self.parser.parse_event(text)
            assert result.success
        
        total_time = time.time() - start_time
        avg_time_per_parse = total_time / len(test_texts)
        
        # Performance benchmark: should parse each event in under 1 second
        assert avg_time_per_parse < 1.0
        
        # Check that processing times are recorded
        for text in test_texts:
            result = self.parser.parse_event(text)
            assert result.processing_time > 0
    
    def test_parsing_accuracy_benchmark(self):
        """Test parsing accuracy across various scenarios."""
        # Use a subset of test cases for accuracy measurement
        test_cases = (
            self.date_test_cases[:3] +
            self.time_test_cases[:3] +
            self.location_test_cases[:3] +
            self.title_test_cases[:3]
        )
        
        successful_parses = 0
        total_cases = len(test_cases)
        
        for test_case in test_cases:
            mock_event = self.create_mock_llm_response(test_case['text'], test_case)
            self.mock_llm_service.llm_extract_event.return_value = mock_event
            
            result = self.parser.parse_event(test_case['text'])
            
            if result.success and result.confidence_score > 0.5:
                successful_parses += 1
        
        accuracy = successful_parses / total_cases
        
        # Accuracy benchmark: should successfully parse at least 80% of test cases
        assert accuracy >= 0.8
    
    def test_memory_usage_benchmark(self):
        """Test memory usage for large text processing."""
        # Create a large text block
        large_text = "Meeting with John tomorrow at 2pm in Conference Room A. " * 1000
        
        mock_event = ParsedEvent(
            title="Large Text Event",
            start_datetime=datetime.now() + timedelta(days=1),
            confidence_score=0.8
        )
        self.mock_llm_service.llm_extract_event.return_value = mock_event
        
        # Should handle large text without issues
        result = self.parser.parse_event(large_text)
        
        assert result.success
        assert result.processing_time < 5.0  # Should complete within 5 seconds
    
    # ===== INTEGRATION TESTS =====
    
    def test_end_to_end_parsing_pipeline(self):
        """Test complete end-to-end parsing pipeline."""
        test_text = "Indigenous Legacy Gathering tomorrow at 2:30 PM in Nathan Phillips Square"
        
        mock_event = ParsedEvent(
            title="Indigenous Legacy Gathering",
            start_datetime=datetime.now() + timedelta(days=1, hours=14, minutes=30),
            end_datetime=datetime.now() + timedelta(days=1, hours=15, minutes=30),
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
        
        # First, test LLM failure scenario
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
        
        Join Microsoft Teams Meeting
        +1 416-555-0123   Conference ID: 123 456 789#
        
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
    
    def test_calendar_app_export(self):
        """Test parsing calendar app export format."""
        calendar_text = """
        Event: Doctor Appointment
        Date: 2024-10-15
        Time: 10:30 AM - 11:00 AM
        Location: Medical Center, 123 Health St
        Description: Annual checkup with Dr. Smith
        Reminder: 15 minutes before
        """
        
        mock_event = ParsedEvent(
            title="Doctor Appointment",
            start_datetime=datetime(2024, 10, 15, 10, 30),
            end_datetime=datetime(2024, 10, 15, 11, 0),
            location="Medical Center, 123 Health St",
            description=calendar_text,
            confidence_score=0.98
        )
        self.mock_llm_service.llm_extract_event.return_value = mock_event
        
        result = self.parser.parse_event(calendar_text)
        
        assert result.success
        assert result.format_result.detected_format == TextFormat.STRUCTURED_EMAIL
        assert result.parsed_event.title == "Doctor Appointment"
        assert "Medical Center" in result.parsed_event.location


if __name__ == "__main__":
    pytest.main([__file__])