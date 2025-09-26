"""
Comprehensive test data sets with various text formats and scenarios.
Tests the system with real-world examples and edge cases.
"""

import unittest
from datetime import datetime, timedelta
from services.event_parser import EventParser
from models.event_models import ParsedEvent


class TestRealWorldScenarios(unittest.TestCase):
    """Test with real-world text scenarios from various sources."""
    
    def setUp(self):
        """Set up test environment."""
        self.parser = EventParser()
    
    def test_email_scenarios(self):
        """Test parsing text that might come from emails."""
        email_scenarios = [
            {
                'text': "Hi John, Let's schedule our weekly sync for tomorrow at 2:30 PM in Conference Room B. The meeting should take about an hour. Thanks!",
                'expected_elements': ['sync', 'tomorrow', '2:30', 'conference room b', 'hour']
            },
            {
                'text': "Reminder: Your dentist appointment is scheduled for next Tuesday, March 15th at 10:30 AM at Toronto Dental Clinic (123 Main St).",
                'expected_elements': ['dentist', 'tuesday', 'march 15', '10:30', 'toronto dental clinic']
            },
            {
                'text': "Subject: Project Kickoff Meeting\n\nWhen: Friday, March 22, 2024 9:00 AM - 11:00 AM\nWhere: Boardroom A, 5th Floor\nWho: All team members",
                'expected_elements': ['project kickoff', 'friday', 'march 22', '9:00', 'boardroom a']
            },
            {
                'text': "FYI - The client presentation has been moved to next Wednesday at 3 PM. Location remains the same (Main Conference Room).",
                'expected_elements': ['client presentation', 'wednesday', '3 pm', 'main conference room']
            }
        ]
        
        for scenario in email_scenarios:
            with self.subTest(text=scenario['text'][:50] + "..."):
                result = self.parser.parse_text(scenario['text'])
                
                # Should extract meaningful information
                self.assertGreater(result.confidence_score, 0.3, 
                                 f"Low confidence for email text: {scenario['text'][:100]}")
                
                # Check for expected elements in extracted data
                extracted_text = (
                    (result.title or "") + " " + 
                    (result.location or "") + " " + 
                    (result.description or "")
                ).lower()
                
                found_elements = sum(1 for element in scenario['expected_elements'] 
                                   if element.lower() in extracted_text or 
                                   (result.start_datetime and element.lower() in str(result.start_datetime).lower()))
                
                self.assertGreater(found_elements, 0, 
                                 f"Should find some expected elements in: {scenario['text'][:100]}")
    
    def test_calendar_invite_scenarios(self):
        """Test parsing text from calendar invites."""
        calendar_scenarios = [
            "Meeting: Q1 Planning Session\nTime: Monday, January 15, 2024 2:00 PM - 4:00 PM (EST)\nLocation: Conference Room 301\nDescription: Quarterly planning and goal setting",
            "Event: Team Building Activity\nDate: Friday, February 9, 2024\nTime: 1:00 PM - 5:00 PM\nVenue: Community Center, 456 Oak Street",
            "Appointment: Performance Review\nScheduled: Thursday, March 7, 2024 at 10:30 AM\nDuration: 1 hour\nOffice: Manager's Office (Room 205)",
            "Workshop: Advanced Excel Training\nWhen: Tuesday, April 2, 2024 9:00 AM - 12:00 PM\nWhere: Training Room B, 2nd Floor\nInstructor: Sarah Johnson"
        ]
        
        for text in calendar_scenarios:
            with self.subTest(text=text[:30] + "..."):
                result = self.parser.parse_text(text)
                
                # Should successfully parse structured calendar text
                self.assertIsNotNone(result.title, f"Should extract title from: {text[:50]}")
                self.assertIsNotNone(result.start_datetime, f"Should extract datetime from: {text[:50]}")
                self.assertGreater(result.confidence_score, 0.5, 
                                 f"Should have high confidence for structured text: {text[:50]}")
    
    def test_social_media_scenarios(self):
        """Test parsing text from social media posts."""
        social_scenarios = [
            "Anyone want to join me for coffee tomorrow at 10am? I'll be at Starbucks on King Street ☕",
            "Reminder: Book club meeting this Thursday 7pm at Sarah's place. We're discussing 'The Great Gatsby' 📚",
            "Gym session tomorrow 6am - who's in? 💪 Meet at the front desk",
            "Birthday party for Mike this Saturday 8pm! 🎉 Address: 123 Party Lane. BYOB 🍻",
            "Study group for finals next Tuesday 2pm in the library. Bring your notes! 📖"
        ]
        
        for text in social_scenarios:
            with self.subTest(text=text[:30] + "..."):
                result = self.parser.parse_text(text)
                
                # Should handle informal social media text
                self.assertGreater(result.confidence_score, 0.2, 
                                 f"Should extract some information from social text: {text}")
                
                # Should handle emojis gracefully
                if result.title:
                    # Title should not contain raw emoji characters in a problematic way
                    self.assertIsInstance(result.title, str)
    
    def test_document_scenarios(self):
        """Test parsing text from documents and reports."""
        document_scenarios = [
            "The quarterly board meeting is scheduled for Wednesday, June 12, 2024, at 2:00 PM in the executive boardroom on the 10th floor.",
            "All staff are required to attend the mandatory safety training session on Friday, May 17, 2024, from 9:00 AM to 12:00 PM in the main auditorium.",
            "The annual company picnic will take place on Saturday, July 20, 2024, starting at 11:00 AM at Riverside Park (weather permitting).",
            "Please note that the office will be closed on Monday, February 19, 2024, in observance of Presidents' Day. Normal business hours will resume on Tuesday."
        ]
        
        for text in document_scenarios:
            with self.subTest(text=text[:30] + "..."):
                result = self.parser.parse_text(text)
                
                # Should parse formal document language
                self.assertIsNotNone(result.start_datetime, f"Should extract date from: {text[:50]}")
                self.assertGreater(result.confidence_score, 0.4, 
                                 f"Should have reasonable confidence for formal text: {text[:50]}")


class TestDateTimeFormatVariations(unittest.TestCase):
    """Test various date and time format variations."""
    
    def setUp(self):
        """Set up test environment."""
        self.parser = EventParser()
    
    def test_date_format_variations(self):
        """Test different date format variations."""
        date_formats = [
            # MM/DD/YYYY variations
            "Meeting on 12/25/2024",
            "Event on 3/5/24",
            "Call on 03/05/2024",
            
            # DD/MM/YYYY variations
            "Meeting on 25/12/2024",
            "Event on 5/3/24",
            "Call on 05/03/2024",
            
            # Month name variations
            "Meeting on December 25, 2024",
            "Event on Dec 25 2024",
            "Call on 25 December 2024",
            "Conference on December 25th, 2024",
            
            # ISO format variations
            "Meeting on 2024-12-25",
            "Event on 2024/12/25",
            
            # Relative date variations
            "Meeting today",
            "Event tomorrow",
            "Call yesterday",
            "Conference next Monday",
            "Workshop this Friday",
            "Training next week",
            "Seminar in 2 weeks",
            "Review in 3 days",
        ]
        
        for text in date_formats:
            with self.subTest(text=text):
                result = self.parser.parse_text(text)
                
                # Should extract some date information
                self.assertTrue(
                    result.start_datetime is not None or result.confidence_score > 0.3,
                    f"Should extract date information from: {text}"
                )
    
    def test_time_format_variations(self):
        """Test different time format variations."""
        time_formats = [
            # 12-hour format variations
            "Meeting at 2pm",
            "Event at 2:30pm",
            "Call at 2:30 PM",
            "Conference at 2:30 p.m.",
            "Workshop at 10am",
            "Training at 10:30am",
            "Seminar at 10:30 AM",
            "Review at 10:30 a.m.",
            
            # 24-hour format variations
            "Meeting at 14:00",
            "Event at 14:30",
            "Call at 09:15",
            "Conference at 23:45",
            
            # Hour-only variations
            "Meeting at 2 o'clock",
            "Event at two o'clock",
            "Call at 2",
            "Conference at 14",
            
            # Noon/midnight variations
            "Meeting at noon",
            "Event at midnight",
            "Call at 12 noon",
            "Conference at 12 midnight",
        ]
        
        for text in time_formats:
            with self.subTest(text=text):
                result = self.parser.parse_text(text)
                
                # Should extract time information
                self.assertTrue(
                    result.start_datetime is not None or result.confidence_score > 0.3,
                    f"Should extract time information from: {text}"
                )
    
    def test_duration_format_variations(self):
        """Test different duration format variations."""
        duration_formats = [
            # Hour variations
            "Meeting for 1 hour",
            "Event for 2 hours",
            "Call for one hour",
            "Conference for two hours",
            "Workshop for 1.5 hours",
            "Training for 2.5 hours",
            
            # Minute variations
            "Meeting for 30 minutes",
            "Event for 45 mins",
            "Call for thirty minutes",
            "Conference for 90 minutes",
            
            # Combined variations
            "Meeting for 1 hour and 30 minutes",
            "Event for 2 hours 15 minutes",
            "Call for 1 hr 45 mins",
            "Conference for 2h 30m",
            
            # Time range variations
            "Meeting from 2pm to 3pm",
            "Event from 9:00 AM to 11:30 AM",
            "Call from 14:00 to 15:30",
            "Conference 2-4 PM",
            "Workshop 9am-12pm",
        ]
        
        for text in duration_formats:
            with self.subTest(text=text):
                result = self.parser.parse_text(text)
                
                # Should extract duration or end time
                if result.start_datetime:
                    self.assertTrue(
                        result.end_datetime is not None,
                        f"Should calculate end time for: {text}"
                    )


class TestLocationFormatVariations(unittest.TestCase):
    """Test various location format variations."""
    
    def setUp(self):
        """Set up test environment."""
        self.parser = EventParser()
    
    def test_location_keyword_variations(self):
        """Test different location keyword variations."""
        location_formats = [
            # "at" keyword
            ("Meeting at Starbucks", "starbucks"),
            ("Event at Conference Room A", "conference room a"),
            ("Call at the office", "office"),
            ("Workshop at 123 Main Street", "123 main street"),
            
            # "in" keyword
            ("Meeting in Room 205", "room 205"),
            ("Event in the boardroom", "boardroom"),
            ("Call in Building B", "building b"),
            ("Conference in Toronto", "toronto"),
            
            # "@" symbol
            ("Meeting @ Cafe Downtown", "cafe downtown"),
            ("Event @ The Keg Restaurant", "the keg"),
            ("Call @ client office", "client office"),
            
            # "from" keyword (for remote locations)
            ("Call from home", "home"),
            ("Meeting from the airport", "airport"),
            
            # Address formats
            ("Meeting at 123 King Street West", "123 king street west"),
            ("Event at 456 Bay St, Toronto, ON", "456 bay st"),
            ("Conference at 789 Queen Street, Suite 100", "789 queen street"),
        ]
        
        for text, expected_location in location_formats:
            with self.subTest(text=text):
                result = self.parser.parse_text(text)
                
                if result.location:
                    self.assertIn(expected_location.lower(), result.location.lower(),
                                f"Should extract '{expected_location}' from: {text}")
    
    def test_complex_location_scenarios(self):
        """Test complex location scenarios."""
        complex_locations = [
            "Meeting at the Marriott Hotel, 123 Queen Street West, Toronto, ON M5H 2M9",
            "Conference at University of Toronto, Bahen Centre, Room 1180",
            "Workshop at Toronto Convention Centre, North Building, Hall A",
            "Training at our downtown office (25th floor, Conference Room B)",
            "Lunch at The Keg Restaurant on King Street (near the financial district)",
        ]
        
        for text in complex_locations:
            with self.subTest(text=text[:30] + "..."):
                result = self.parser.parse_text(text)
                
                # Should extract some location information
                self.assertIsNotNone(result.location, f"Should extract location from: {text}")
                self.assertGreater(len(result.location), 3, 
                                 f"Location should be meaningful: {result.location}")


class TestEdgeCasesAndBoundaryConditions(unittest.TestCase):
    """Test edge cases and boundary conditions."""
    
    def setUp(self):
        """Set up test environment."""
        self.parser = EventParser()
    
    def test_minimal_information_scenarios(self):
        """Test scenarios with minimal information."""
        minimal_scenarios = [
            "Meeting",
            "Tomorrow",
            "2pm",
            "Conference Room A",
            "Call John",
            "Lunch",
        ]
        
        for text in minimal_scenarios:
            with self.subTest(text=text):
                result = self.parser.parse_text(text)
                
                # Should handle minimal information gracefully
                self.assertIsNotNone(result)
                self.assertIsInstance(result.confidence_score, (int, float))
                self.assertGreaterEqual(result.confidence_score, 0.0)
                self.assertLessEqual(result.confidence_score, 1.0)
    
    def test_ambiguous_scenarios(self):
        """Test ambiguous scenarios that could be interpreted multiple ways."""
        ambiguous_scenarios = [
            "Meeting at 2",  # 2 AM or 2 PM?
            "Call on 05/03/2024",  # May 3rd or March 5th?
            "Event next Friday",  # This Friday or next Friday?
            "Conference in 2 weeks",  # Exactly 2 weeks or approximately?
            "Workshop for 2 hours",  # Starting when?
            "Lunch with John and Sarah",  # Who is the primary contact?
        ]
        
        for text in ambiguous_scenarios:
            with self.subTest(text=text):
                result = self.parser.parse_text(text)
                validation = self.parser.validate_parsed_event(result)
                
                # Should handle ambiguity with appropriate confidence or warnings
                self.assertTrue(
                    result.confidence_score < 0.9 or 
                    len(validation.warnings) > 0 or
                    len(validation.suggestions) > 0,
                    f"Should indicate uncertainty for ambiguous text: {text}"
                )
    
    def test_invalid_datetime_scenarios(self):
        """Test scenarios with invalid datetime information."""
        invalid_scenarios = [
            "Meeting on February 30th",  # Invalid date
            "Event at 25:00",  # Invalid time
            "Call on 13/45/2024",  # Invalid month/day
            "Conference at 2:70 PM",  # Invalid minutes
            "Workshop on the 32nd",  # Invalid day
        ]
        
        for text in invalid_scenarios:
            with self.subTest(text=text):
                result = self.parser.parse_text(text)
                
                # Should handle invalid datetime gracefully
                self.assertIsNotNone(result)
                # Either should have low confidence or no datetime extracted
                self.assertTrue(
                    result.confidence_score < 0.5 or 
                    result.start_datetime is None,
                    f"Should handle invalid datetime in: {text}"
                )
    
    def test_conflicting_information_scenarios(self):
        """Test scenarios with conflicting information."""
        conflicting_scenarios = [
            "Meeting tomorrow at yesterday's time",
            "Event on Monday next Friday",
            "Call at 2pm in the morning",
            "Conference from 3pm to 2pm",
            "Workshop for -2 hours",
        ]
        
        for text in conflicting_scenarios:
            with self.subTest(text=text):
                result = self.parser.parse_text(text)
                validation = self.parser.validate_parsed_event(result)
                
                # Should detect conflicts
                self.assertTrue(
                    result.confidence_score < 0.7 or
                    len(validation.warnings) > 0 or
                    not validation.is_valid,
                    f"Should detect conflicts in: {text}"
                )
    
    def test_very_long_text_scenarios(self):
        """Test scenarios with very long text."""
        long_text = """
        This is a very long email about our upcoming quarterly business review meeting 
        which is scheduled to take place next Thursday, March 15th, 2024, starting at 
        2:00 PM Eastern Standard Time in the main conference room on the 25th floor of 
        our downtown office building located at 123 Business Avenue in the heart of the 
        financial district. The meeting will cover a comprehensive review of our Q1 
        performance metrics, including sales figures, customer satisfaction scores, 
        operational efficiency improvements, and strategic initiatives for the upcoming 
        quarter. All department heads are required to attend and should come prepared 
        with their quarterly reports and presentations. The meeting is expected to last 
        approximately 3 hours with a 15-minute break at 3:30 PM. Light refreshments 
        will be provided. Please confirm your attendance by replying to this email no 
        later than Monday, March 12th. If you have any questions or concerns, please 
        don't hesitate to reach out to me directly.
        """
        
        result = self.parser.parse_text(long_text)
        
        # Should extract key information despite length
        self.assertIsNotNone(result.title)
        self.assertIsNotNone(result.start_datetime)
        self.assertGreater(result.confidence_score, 0.5)
        
        # Should extract the main meeting details
        self.assertIn("march", str(result.start_datetime).lower())
        self.assertEqual(result.start_datetime.hour, 14)  # 2 PM
    
    def test_multiple_events_in_single_text(self):
        """Test text containing multiple events."""
        multi_event_text = """
        My schedule for tomorrow: 9am team standup in Room A, 11am client call, 
        1pm lunch with Sarah at The Keg, 3pm project review in the boardroom, 
        and 5pm happy hour at Murphy's Pub.
        """
        
        # Test single event extraction (should pick the most confident one)
        result = self.parser.parse_text(multi_event_text)
        self.assertIsNotNone(result.title)
        self.assertIsNotNone(result.start_datetime)
        
        # Test multiple event extraction
        results = self.parser.parse_multiple_events(multi_event_text)
        self.assertGreater(len(results), 1, "Should identify multiple events")
        
        # Each result should have reasonable confidence
        for event_result in results:
            self.assertGreater(event_result.confidence_score, 0.2)


class TestInternationalAndCulturalVariations(unittest.TestCase):
    """Test international date formats and cultural variations."""
    
    def setUp(self):
        """Set up test environment."""
        self.parser = EventParser()
    
    def test_international_date_formats(self):
        """Test international date format preferences."""
        # Test DD/MM format preference
        self.parser.set_config(prefer_dd_mm_format=True)
        
        dd_mm_scenarios = [
            ("Meeting on 15/03/2024", (2024, 3, 15)),  # Unambiguous
            ("Event on 05/03/2024", (2024, 3, 5)),    # Should be March 5th with DD/MM preference
        ]
        
        for text, expected_date in dd_mm_scenarios:
            with self.subTest(text=text):
                result = self.parser.parse_text(text, prefer_dd_mm_format=True)
                
                if result.start_datetime:
                    actual_date = (
                        result.start_datetime.year,
                        result.start_datetime.month,
                        result.start_datetime.day
                    )
                    self.assertEqual(actual_date, expected_date)
        
        # Test MM/DD format preference
        mm_dd_scenarios = [
            ("Meeting on 03/15/2024", (2024, 3, 15)),  # Unambiguous
            ("Event on 05/03/2024", (2024, 5, 3)),    # Should be May 3rd with MM/DD preference
        ]
        
        for text, expected_date in mm_dd_scenarios:
            with self.subTest(text=text):
                result = self.parser.parse_text(text, prefer_dd_mm_format=False)
                
                if result.start_datetime:
                    actual_date = (
                        result.start_datetime.year,
                        result.start_datetime.month,
                        result.start_datetime.day
                    )
                    self.assertEqual(actual_date, expected_date)
    
    def test_cultural_time_references(self):
        """Test cultural variations in time references."""
        cultural_scenarios = [
            # Business hours assumptions
            "Meeting at 9",  # Should assume 9 AM in business context
            "Call at 3",    # Should assume 3 PM in business context
            
            # Cultural event times
            "Dinner at 7",  # Should assume 7 PM
            "Breakfast at 8",  # Should assume 8 AM
            "Lunch at 12",  # Should assume 12 PM (noon)
        ]
        
        for text in cultural_scenarios:
            with self.subTest(text=text):
                result = self.parser.parse_text(text)
                
                if result.start_datetime:
                    # Should make reasonable assumptions about AM/PM
                    hour = result.start_datetime.hour
                    self.assertTrue(0 <= hour <= 23, f"Hour should be valid: {hour}")


if __name__ == '__main__':
    # Run comprehensive test data scenarios
    print("="*60)
    print("COMPREHENSIVE TEST DATA SCENARIOS")
    print("="*60)
    
    # Create test suite
    suite = unittest.TestSuite()
    
    # Add all scenario test classes
    for test_class in [TestRealWorldScenarios, TestDateTimeFormatVariations,
                      TestLocationFormatVariations, TestEdgeCasesAndBoundaryConditions,
                      TestInternationalAndCulturalVariations]:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        suite.addTests(tests)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print(f"\n{'='*60}")
    print(f"TEST DATA SCENARIOS SUMMARY")
    print(f"{'='*60}")
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%")
    
    if result.failures:
        print(f"\nFAILED SCENARIOS:")
        for test, traceback in result.failures:
            print(f"- {test}")
    
    if result.errors:
        print(f"\nERROR SCENARIOS:")
        for test, traceback in result.errors:
            print(f"- {test}")
    
    print(f"\n✅ Comprehensive test data validation complete!")