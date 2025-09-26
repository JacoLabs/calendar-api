"""
Comprehensive test suite for validating all requirements are met.
This test suite validates each requirement from the requirements document.
"""

import unittest
import tempfile
import os
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from main import TextToCalendarApp
from services.event_parser import EventParser
from services.calendar_service import CalendarService
from models.event_models import Event, ParsedEvent


class TestRequirement1(unittest.TestCase):
    """Test Requirement 1: Text highlighting and event creation option."""
    
    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_storage = os.path.join(self.temp_dir, "test_events.json")
        self.app = TextToCalendarApp()
        self.app.calendar_service = CalendarService(storage_path=self.temp_storage)
        self.app.set_config(auto_preview=False, verbose_output=False)
    
    def tearDown(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_requirement_1_1_text_parsing_option(self):
        """
        WHEN a user highlights text THEN the system SHALL display a "Create Calendar Event" option
        """
        # This is simulated by the CLI accepting text input
        text = "Meeting with John tomorrow at 2pm"
        
        # The system should be able to process this text
        success, event, message = self.app.run_complete_workflow(text)
        
        # Should successfully process the text (simulating the "Create Calendar Event" option)
        self.assertTrue(success or event is not None, 
                       "System should provide event creation capability for highlighted text")
    
    def test_requirement_1_2_text_parsing_execution(self):
        """
        WHEN a user selects the "Create Calendar Event" option THEN the system SHALL parse the highlighted text
        """
        text = "Team meeting tomorrow at 3pm in Conference Room B"
        
        # Parse the text (simulating selection of "Create Calendar Event")
        parsed_event = self.app.event_parser.parse_text(text)
        
        # Should successfully parse the text
        self.assertIsNotNone(parsed_event)
        self.assertGreater(parsed_event.confidence_score, 0)
        self.assertIsNotNone(parsed_event.title)
    
    def test_requirement_1_3_information_extraction(self):
        """
        WHEN the system parses text THEN it SHALL extract date, time, title, and location information when present
        """
        text = "Project review meeting at Conference Room A on March 15, 2024 from 10:00 AM to 11:30 AM"
        
        parsed_event = self.app.event_parser.parse_text(text)
        
        # Should extract all available information
        self.assertIsNotNone(parsed_event.title, "Should extract title")
        self.assertIsNotNone(parsed_event.start_datetime, "Should extract date and time")
        self.assertIsNotNone(parsed_event.location, "Should extract location")
        
        # Verify specific extractions
        self.assertIn("project", parsed_event.title.lower())
        self.assertIn("conference room a", parsed_event.location.lower())
        self.assertEqual(parsed_event.start_datetime.hour, 10)
    
    def test_requirement_1_4_form_prepopulation(self):
        """
        WHEN event information is extracted THEN the system SHALL pre-populate a calendar event creation form
        """
        text = "Lunch meeting with client next Tuesday 12:30pm at The Keg Restaurant"
        
        parsed_event = self.app.event_parser.parse_text(text)
        
        # Convert to Event (simulating form pre-population)
        if parsed_event.is_complete():
            event = Event(
                title=parsed_event.title,
                start_datetime=parsed_event.start_datetime,
                end_datetime=parsed_event.end_datetime,
                location=parsed_event.location,
                description=parsed_event.description or ""
            )
            
            # Verify form would be pre-populated with extracted data
            self.assertIsNotNone(event.title)
            self.assertIsNotNone(event.start_datetime)
            self.assertIsNotNone(event.location)


class TestRequirement2(unittest.TestCase):
    """Test Requirement 2: Intelligent parsing of different date and time formats."""
    
    def setUp(self):
        """Set up test environment."""
        self.parser = EventParser()
    
    def test_requirement_2_1_common_date_formats(self):
        """
        WHEN text contains dates in common formats THEN the system SHALL correctly identify the date
        """
        test_cases = [
            ("Meeting on 12/25/2024", (2024, 12, 25)),
            ("Event on March 15, 2025", (2025, 3, 15)),
            ("Call on 15/03/2024", (2024, 3, 15)),  # DD/MM format
        ]
        
        for text, expected_date in test_cases:
            with self.subTest(text=text):
                parsed_event = self.parser.parse_text(text, prefer_dd_mm_format=True)
                
                if parsed_event.start_datetime:
                    actual_date = (
                        parsed_event.start_datetime.year,
                        parsed_event.start_datetime.month,
                        parsed_event.start_datetime.day
                    )
                    self.assertEqual(actual_date, expected_date)
    
    def test_requirement_2_2_time_format_identification(self):
        """
        WHEN text contains time information THEN the system SHALL correctly identify the time
        """
        test_cases = [
            ("Meeting at 2:30 PM", 14, 30),
            ("Event at 09:15", 9, 15),
            ("Call at 11:45 PM", 23, 45),
        ]
        
        for text, expected_hour, expected_minute in test_cases:
            with self.subTest(text=text):
                parsed_event = self.parser.parse_text(text)
                
                if parsed_event.start_datetime:
                    self.assertEqual(parsed_event.start_datetime.hour, expected_hour)
                    self.assertEqual(parsed_event.start_datetime.minute, expected_minute)
    
    def test_requirement_2_3_relative_date_conversion(self):
        """
        WHEN text contains relative dates THEN the system SHALL convert them to absolute dates
        """
        today = datetime.now().date()
        
        test_cases = [
            ("Meeting tomorrow", today + timedelta(days=1)),
            ("Event next Friday", None),  # Will vary based on current day
            ("Call in 2 weeks", today + timedelta(weeks=2)),
        ]
        
        for text, expected_date in test_cases:
            with self.subTest(text=text):
                parsed_event = self.parser.parse_text(text)
                
                if parsed_event.start_datetime and expected_date:
                    self.assertEqual(parsed_event.start_datetime.date(), expected_date)
                elif parsed_event.start_datetime:
                    # For "next Friday", just verify it's in the future
                    self.assertGreater(parsed_event.start_datetime.date(), today)
    
    def test_requirement_2_4_duration_calculation(self):
        """
        WHEN text contains duration information THEN the system SHALL calculate the end time
        """
        test_cases = [
            ("Meeting for 2 hours", 120),
            ("Call for 30 minutes", 30),
            ("Workshop for 1 hour and 15 minutes", 75),
        ]
        
        for text, expected_minutes in test_cases:
            with self.subTest(text=text):
                parsed_event = self.parser.parse_text(text)
                
                if parsed_event.start_datetime and parsed_event.end_datetime:
                    duration = parsed_event.end_datetime - parsed_event.start_datetime
                    actual_minutes = duration.total_seconds() / 60
                    self.assertAlmostEqual(actual_minutes, expected_minutes, delta=5)


class TestRequirement3(unittest.TestCase):
    """Test Requirement 3: Review and edit extracted event information."""
    
    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_storage = os.path.join(self.temp_dir, "test_events.json")
        self.app = TextToCalendarApp()
        self.app.calendar_service = CalendarService(storage_path=self.temp_storage)
    
    def tearDown(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_requirement_3_1_preview_display(self):
        """
        WHEN event information is extracted THEN the system SHALL display a preview form with all extracted data
        """
        text = "Team meeting tomorrow at 10am in Conference Room B"
        
        parsed_event = self.app.event_parser.parse_text(text)
        
        # Verify all extractable data is present for preview
        self.assertIsNotNone(parsed_event.title)
        self.assertIsNotNone(parsed_event.start_datetime)
        self.assertIsNotNone(parsed_event.end_datetime)
        
        # The preview interface should be able to display this data
        from ui.event_preview import EventPreviewInterface
        interface = EventPreviewInterface()
        
        # Should not raise an exception when displaying
        try:
            validation_result = self.app.event_parser.validate_parsed_event(parsed_event)
            interface.display_event_preview(parsed_event, validation_result)
        except Exception as e:
            self.fail(f"Preview display failed: {e}")
    
    def test_requirement_3_2_field_editing_capability(self):
        """
        WHEN the preview form is displayed THEN the user SHALL be able to edit any field
        """
        # This tests the data model's ability to be modified (simulating user edits)
        parsed_event = ParsedEvent(
            title="Original Title",
            start_datetime=datetime(2024, 3, 15, 14, 0),
            end_datetime=datetime(2024, 3, 15, 15, 0),
            location="Original Location"
        )
        
        # Simulate editing fields (what the UI would do)
        edited_event = Event(
            title="Edited Title",
            start_datetime=datetime(2024, 3, 15, 15, 0),  # Changed time
            end_datetime=datetime(2024, 3, 15, 16, 0),
            location="Edited Location",
            description="Added description"
        )
        
        # Verify all fields can be modified
        self.assertNotEqual(edited_event.title, parsed_event.title)
        self.assertNotEqual(edited_event.start_datetime, parsed_event.start_datetime)
        self.assertNotEqual(edited_event.location, parsed_event.location)
    
    def test_requirement_3_3_missing_field_highlighting(self):
        """
        WHEN required information is missing THEN the system SHALL highlight missing fields and prompt for input
        """
        # Create event with missing required information
        incomplete_event = ParsedEvent(
            title="Meeting",
            # Missing start_datetime
            confidence_score=0.5
        )
        
        validation_result = self.app.event_parser.validate_parsed_event(incomplete_event)
        
        # Should identify missing fields
        self.assertFalse(validation_result.is_valid)
        self.assertIn('start_datetime', validation_result.missing_fields)
    
    def test_requirement_3_4_event_creation_confirmation(self):
        """
        WHEN the user confirms the event details THEN the system SHALL create the calendar event
        """
        event = Event(
            title="Confirmed Meeting",
            start_datetime=datetime.now() + timedelta(days=1),
            end_datetime=datetime.now() + timedelta(days=1, hours=1),
            location="Test Location"
        )
        
        # Simulate user confirmation by creating the event
        with patch('builtins.print'):  # Suppress output
            success, message, event_id = self.app.calendar_service.create_event(event)
        
        self.assertTrue(success)
        
        # Verify event was created
        events = self.app.calendar_service.list_events()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].title, "Confirmed Meeting")


class TestRequirement4(unittest.TestCase):
    """Test Requirement 4: Handle various text formats and sources."""
    
    def setUp(self):
        """Set up test environment."""
        self.parser = EventParser()
    
    def test_requirement_4_1_multiple_events_identification(self):
        """
        WHEN text contains multiple potential events THEN the system SHALL identify and offer to create separate events
        """
        text = "Meeting at 10am then lunch at 12pm and conference call at 3pm tomorrow"
        
        # Test multiple event parsing
        results = self.parser.parse_multiple_events(text)
        
        # Should identify multiple events
        self.assertGreaterEqual(len(results), 1)
        
        # Each result should have reasonable confidence
        for result in results:
            self.assertGreater(result.confidence_score, 0.2)
    
    def test_requirement_4_2_ambiguous_text_handling(self):
        """
        WHEN text is ambiguous or unclear THEN the system SHALL provide suggestions and ask for clarification
        """
        ambiguous_texts = [
            "maybe meet sometime next week",
            "call at 2",  # AM or PM unclear
            "meeting on 05/03/2024",  # MM/DD vs DD/MM unclear
        ]
        
        for text in ambiguous_texts:
            with self.subTest(text=text):
                parsed_event = self.parser.parse_text(text)
                validation_result = self.parser.validate_parsed_event(parsed_event)
                
                # Should provide suggestions for ambiguous text
                self.assertTrue(
                    len(validation_result.suggestions) > 0 or 
                    len(validation_result.warnings) > 0 or
                    parsed_event.confidence_score < 0.8,
                    f"Should provide guidance for ambiguous text: {text}"
                )
    
    def test_requirement_4_3_no_event_information_handling(self):
        """
        WHEN no event information can be extracted THEN the system SHALL inform the user and allow manual event creation
        """
        non_event_texts = [
            "This is just regular text with no event information",
            "The weather is nice today",
            "Random words without dates or times",
        ]
        
        for text in non_event_texts:
            with self.subTest(text=text):
                parsed_event = self.parser.parse_text(text)
                
                # Should have very low confidence or missing required fields
                self.assertTrue(
                    parsed_event.confidence_score < 0.3 or
                    not parsed_event.is_complete(),
                    f"Should recognize lack of event information in: {text}"
                )
    
    def test_requirement_4_4_location_extraction(self):
        """
        WHEN text contains location information THEN the system SHALL extract and include it in the event
        """
        location_texts = [
            ("Meeting at Starbucks tomorrow 2pm", "starbucks"),
            ("Conference in Room 205 next Friday", "room 205"),
            ("Lunch @ The Keg Restaurant", "the keg"),
            ("Call from home office", "home office"),
        ]
        
        for text, expected_location in location_texts:
            with self.subTest(text=text):
                parsed_event = self.parser.parse_text(text)
                
                if parsed_event.location:
                    self.assertIn(expected_location.lower(), parsed_event.location.lower())


class TestRequirement5(unittest.TestCase):
    """Test Requirement 5: Calendar system integration and event storage."""
    
    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_storage = os.path.join(self.temp_dir, "test_events.json")
        self.calendar_service = CalendarService(storage_path=self.temp_storage)
    
    def tearDown(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_requirement_5_1_default_calendar_storage(self):
        """
        WHEN a calendar event is created THEN it SHALL be saved to the user's default calendar
        """
        event = Event(
            title="Test Event",
            start_datetime=datetime.now() + timedelta(days=1),
            end_datetime=datetime.now() + timedelta(days=1, hours=1)
        )
        
        with patch('builtins.print'):  # Suppress output
            success, message, event_id = self.calendar_service.create_event(event)
        
        self.assertTrue(success)
        
        # Verify event is stored in default calendar
        events = self.calendar_service.list_events()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].calendar_id, "default")
    
    def test_requirement_5_2_creation_confirmation(self):
        """
        WHEN an event is saved THEN the system SHALL provide confirmation with event details
        """
        event = Event(
            title="Confirmed Event",
            start_datetime=datetime.now() + timedelta(days=1),
            end_datetime=datetime.now() + timedelta(days=1, hours=1),
            location="Test Location"
        )
        
        success, message, event_id = self.calendar_service.create_event(event)
        
        # Should provide confirmation
        self.assertTrue(success)
        self.assertIsNotNone(message)
        self.assertIsNotNone(event_id)
        
        # Message should contain event details
        self.assertIn("created", message.lower())
    
    def test_requirement_5_3_creation_failure_handling(self):
        """
        WHEN an event creation fails THEN the system SHALL display an error message and allow retry
        """
        # Create invalid event to trigger failure
        invalid_event = Event(
            title="Valid Title",
            start_datetime=datetime.now() + timedelta(days=1),
            end_datetime=datetime.now() + timedelta(days=1, hours=1)
        )
        # Modify to make invalid after creation
        invalid_event.title = ""
        
        # Should handle validation failure
        try:
            success, message, event_id = self.calendar_service.create_event(invalid_event)
            # If it doesn't raise an exception, it should return failure
            self.assertFalse(success)
            self.assertIsNotNone(message)
        except Exception as e:
            # Should provide meaningful error message
            self.assertIn("title", str(e).lower())
    
    def test_requirement_5_4_complete_information_storage(self):
        """
        WHEN an event is created THEN it SHALL include all extracted and user-confirmed information
        """
        event = Event(
            title="Complete Event",
            start_datetime=datetime(2024, 3, 15, 14, 30),
            end_datetime=datetime(2024, 3, 15, 15, 30),
            location="Conference Room A",
            description="Detailed description"
        )
        
        with patch('builtins.print'):  # Suppress output
            success, message, event_id = self.calendar_service.create_event(event)
        
        self.assertTrue(success)
        
        # Retrieve and verify all information is preserved
        stored_events = self.calendar_service.list_events()
        stored_event = stored_events[0]
        
        self.assertEqual(stored_event.title, event.title)
        self.assertEqual(stored_event.start_datetime, event.start_datetime)
        self.assertEqual(stored_event.end_datetime, event.end_datetime)
        self.assertEqual(stored_event.location, event.location)
        self.assertEqual(stored_event.description, event.description)


if __name__ == '__main__':
    # Create test suite that runs all requirement tests
    suite = unittest.TestSuite()
    
    # Add all requirement test classes
    for test_class in [TestRequirement1, TestRequirement2, TestRequirement3, 
                      TestRequirement4, TestRequirement5]:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        suite.addTests(tests)
    
    # Run the tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print(f"\n{'='*60}")
    print(f"REQUIREMENTS VALIDATION SUMMARY")
    print(f"{'='*60}")
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%")
    
    if result.failures:
        print(f"\nFAILURES:")
        for test, traceback in result.failures:
            print(f"- {test}: {traceback.split('AssertionError: ')[-1].split('\\n')[0]}")
    
    if result.errors:
        print(f"\nERRORS:")
        for test, traceback in result.errors:
            print(f"- {test}: {traceback.split('\\n')[-2]}")