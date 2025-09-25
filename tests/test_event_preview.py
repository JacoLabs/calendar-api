"""
Tests for the event preview and editing interface.
"""

import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
from io import StringIO
import sys

from models.event_models import ParsedEvent, Event, ValidationResult
from ui.event_preview import EventPreviewInterface, create_event_from_text


class TestEventPreviewInterface(unittest.TestCase):
    """Test cases for EventPreviewInterface class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.interface = EventPreviewInterface()
        
        # Create a sample parsed event
        self.sample_event = ParsedEvent(
            title="Team Meeting",
            start_datetime=datetime(2024, 3, 15, 14, 0),
            end_datetime=datetime(2024, 3, 15, 15, 0),
            location="Conference Room A",
            description="Weekly team sync meeting",
            confidence_score=0.85
        )
        
        # Create validation result
        self.validation_result = ValidationResult(is_valid=True)
    
    def test_display_event_preview(self):
        """Test displaying event preview."""
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            self.interface.display_event_preview(self.sample_event, self.validation_result)
            output = mock_stdout.getvalue()
            
            # Check that all event details are displayed
            self.assertIn("Team Meeting", output)
            self.assertIn("2024-03-15", output)
            self.assertIn("14:00", output)
            self.assertIn("15:00", output)
            self.assertIn("Conference Room A", output)
            self.assertIn("85.0%", output)  # Confidence score
    
    def test_display_event_preview_with_missing_fields(self):
        """Test displaying event with missing fields."""
        incomplete_event = ParsedEvent(
            title=None,
            start_datetime=None,
            end_datetime=None,
            location=None,
            description="Some text",
            confidence_score=0.3
        )
        
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            self.interface.display_event_preview(incomplete_event)
            output = mock_stdout.getvalue()
            
            # Check that missing fields are indicated
            self.assertIn("(not specified)", output)
            self.assertIn("30.0%", output)  # Low confidence score
    
    def test_display_validation_issues(self):
        """Test displaying validation issues."""
        validation_with_issues = ValidationResult(is_valid=False)
        validation_with_issues.add_missing_field('title', 'Event needs a title')
        validation_with_issues.add_warning('End time should be after start time')
        validation_with_issues.add_suggestion('Consider adding location information')
        
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            self.interface.display_event_preview(self.sample_event, validation_with_issues)
            output = mock_stdout.getvalue()
            
            # Check that validation issues are displayed
            self.assertIn("VALIDATION ISSUES", output)
            self.assertIn("title", output)
            self.assertIn("End time should be after start time", output)
            self.assertIn("SUGGESTIONS", output)
            self.assertIn("Consider adding location information", output)
    
    def test_format_date_and_time(self):
        """Test date and time formatting methods."""
        dt = datetime(2024, 3, 15, 14, 30)
        
        # Test date formatting
        formatted_date = self.interface._format_date(dt)
        self.assertIn("2024-03-15", formatted_date)
        self.assertIn("Friday", formatted_date)  # Day of week
        
        # Test time formatting
        formatted_time = self.interface._format_time(dt)
        self.assertEqual(formatted_time, "14:30")
        
        # Test with None values
        self.assertEqual(self.interface._format_date(None), "(not specified)")
        self.assertEqual(self.interface._format_time(None), "(not specified)")
    
    def test_parse_time_input(self):
        """Test parsing various time input formats."""
        # Test 24-hour format
        time_24h = self.interface._parse_time_input("14:30")
        self.assertEqual(time_24h.hour, 14)
        self.assertEqual(time_24h.minute, 30)
        
        # Test 12-hour format with AM/PM
        time_12h_pm = self.interface._parse_time_input("2:30 PM")
        self.assertEqual(time_12h_pm.hour, 14)
        self.assertEqual(time_12h_pm.minute, 30)
        
        time_12h_am = self.interface._parse_time_input("9:15 AM")
        self.assertEqual(time_12h_am.hour, 9)
        self.assertEqual(time_12h_am.minute, 15)
        
        # Test hour only
        time_hour_only = self.interface._parse_time_input("15")
        self.assertEqual(time_hour_only.hour, 15)
        self.assertEqual(time_hour_only.minute, 0)
        
        # Test invalid formats
        with self.assertRaises(ValueError):
            self.interface._parse_time_input("invalid")
        
        with self.assertRaises(ValueError):
            self.interface._parse_time_input("25:00")  # Invalid hour
    
    def test_validate_current_event(self):
        """Test event validation."""
        self.interface.current_event = self.sample_event
        
        # Test valid event
        result = self.interface._validate_current_event()
        self.assertTrue(result.is_valid)
        self.assertEqual(len(result.missing_fields), 0)
        
        # Test event with missing title
        self.interface.current_event.title = None
        result = self.interface._validate_current_event()
        self.assertFalse(result.is_valid)
        self.assertIn('title', result.missing_fields)
        
        # Test event with invalid time order
        self.interface.current_event.title = "Test Event"
        self.interface.current_event.end_datetime = self.interface.current_event.start_datetime - timedelta(hours=1)
        result = self.interface._validate_current_event()
        self.assertFalse(result.is_valid)
        self.assertTrue(len(result.warnings) > 0)
    
    @patch('builtins.input')
    def test_edit_title(self, mock_input):
        """Test editing event title."""
        self.interface.current_event = self.sample_event
        
        # Test updating title
        mock_input.return_value = "New Meeting Title"
        
        with patch('sys.stdout', new_callable=StringIO):
            self.interface._edit_title()
        
        self.assertEqual(self.interface.current_event.title, "New Meeting Title")
        
        # Test keeping current title (empty input)
        original_title = self.interface.current_event.title
        mock_input.return_value = ""
        
        with patch('sys.stdout', new_callable=StringIO):
            self.interface._edit_title()
        
        self.assertEqual(self.interface.current_event.title, original_title)
    
    @patch('builtins.input')
    def test_edit_start_date(self, mock_input):
        """Test editing start date."""
        self.interface.current_event = self.sample_event
        original_time = self.interface.current_event.start_datetime.time()
        
        # Test updating date
        mock_input.return_value = "2024-04-20"
        
        with patch('sys.stdout', new_callable=StringIO):
            self.interface._edit_start_date()
        
        # Check that date changed but time was preserved
        self.assertEqual(self.interface.current_event.start_datetime.date().year, 2024)
        self.assertEqual(self.interface.current_event.start_datetime.date().month, 4)
        self.assertEqual(self.interface.current_event.start_datetime.date().day, 20)
        self.assertEqual(self.interface.current_event.start_datetime.time(), original_time)
        
        # Test invalid date format
        mock_input.return_value = "invalid-date"
        
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            self.interface._edit_start_date()
            output = mock_stdout.getvalue()
            self.assertIn("Invalid date format", output)
    
    @patch('builtins.input')
    def test_edit_start_time(self, mock_input):
        """Test editing start time."""
        self.interface.current_event = self.sample_event
        original_date = self.interface.current_event.start_datetime.date()
        
        # Test updating time
        mock_input.return_value = "16:30"
        
        with patch('sys.stdout', new_callable=StringIO):
            self.interface._edit_start_time()
        
        # Check that time changed but date was preserved
        self.assertEqual(self.interface.current_event.start_datetime.date(), original_date)
        self.assertEqual(self.interface.current_event.start_datetime.time().hour, 16)
        self.assertEqual(self.interface.current_event.start_datetime.time().minute, 30)
        
        # Check that end time was adjusted to maintain duration
        self.assertEqual(self.interface.current_event.end_datetime.time().hour, 17)
        self.assertEqual(self.interface.current_event.end_datetime.time().minute, 30)
    
    @patch('builtins.input')
    def test_edit_location(self, mock_input):
        """Test editing event location."""
        self.interface.current_event = self.sample_event
        
        # Test updating location
        mock_input.return_value = "New Conference Room"
        
        with patch('sys.stdout', new_callable=StringIO):
            self.interface._edit_location()
        
        self.assertEqual(self.interface.current_event.location, "New Conference Room")
        
        # Test clearing location
        mock_input.side_effect = ["", "y"]  # Empty input, then confirm clear
        
        with patch('sys.stdout', new_callable=StringIO):
            self.interface._edit_location()
        
        self.assertIsNone(self.interface.current_event.location)
    
    @patch('builtins.input')
    def test_handle_confirmation_valid_event(self, mock_input):
        """Test confirming a valid event."""
        self.interface.current_event = self.sample_event
        mock_input.return_value = "y"
        
        with patch('sys.stdout', new_callable=StringIO):
            confirmed, event = self.interface._handle_confirmation()
        
        self.assertTrue(confirmed)
        self.assertIsInstance(event, Event)
        self.assertEqual(event.title, "Team Meeting")
        self.assertEqual(event.start_datetime, self.sample_event.start_datetime)
        self.assertEqual(event.end_datetime, self.sample_event.end_datetime)
    
    @patch('builtins.input')
    def test_handle_confirmation_invalid_event(self, mock_input):
        """Test confirming an invalid event."""
        # Create invalid event (missing title)
        invalid_event = ParsedEvent(
            title=None,
            start_datetime=datetime(2024, 3, 15, 14, 0),
            end_datetime=datetime(2024, 3, 15, 13, 0),  # End before start
            location="Test Location"
        )
        
        self.interface.current_event = invalid_event
        
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            confirmed, event = self.interface._handle_confirmation()
            output = mock_stdout.getvalue()
        
        self.assertFalse(confirmed)
        self.assertIsNone(event)
        self.assertIn("validation issues", output)
    
    @patch('builtins.input')
    def test_handle_confirmation_cancelled(self, mock_input):
        """Test cancelling event confirmation."""
        self.interface.current_event = self.sample_event
        mock_input.return_value = "n"
        
        with patch('sys.stdout', new_callable=StringIO):
            confirmed, event = self.interface._handle_confirmation()
        
        self.assertFalse(confirmed)
        self.assertIsNone(event)
    
    @patch('builtins.input')
    def test_run_interactive_editing_confirm(self, mock_input):
        """Test running interactive editing and confirming."""
        self.interface.current_event = self.sample_event
        mock_input.side_effect = ["c", "y"]  # Confirm, then yes to final confirmation
        
        with patch('sys.stdout', new_callable=StringIO):
            confirmed, event = self.interface.run_interactive_editing()
        
        self.assertTrue(confirmed)
        self.assertIsInstance(event, Event)
    
    @patch('builtins.input')
    def test_run_interactive_editing_cancel(self, mock_input):
        """Test running interactive editing and cancelling."""
        self.interface.current_event = self.sample_event
        mock_input.return_value = "q"  # Cancel
        
        with patch('sys.stdout', new_callable=StringIO):
            confirmed, event = self.interface.run_interactive_editing()
        
        self.assertFalse(confirmed)
        self.assertIsNone(event)
    
    @patch('builtins.input')
    def test_run_interactive_editing_field_edit(self, mock_input):
        """Test editing a field during interactive editing."""
        self.interface.current_event = self.sample_event
        mock_input.side_effect = [
            "1",  # Edit title
            "Updated Meeting Title",  # New title
            "c",  # Confirm
            "y"   # Final confirmation
        ]
        
        with patch('sys.stdout', new_callable=StringIO):
            confirmed, event = self.interface.run_interactive_editing()
        
        self.assertTrue(confirmed)
        self.assertEqual(event.title, "Updated Meeting Title")
    
    @patch('builtins.input')
    def test_run_interactive_editing_help_and_refresh(self, mock_input):
        """Test help and refresh commands during interactive editing."""
        self.interface.current_event = self.sample_event
        mock_input.side_effect = [
            "h",  # Help
            "r",  # Refresh
            "c",  # Confirm
            "y"   # Final confirmation
        ]
        
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            confirmed, event = self.interface.run_interactive_editing()
            output = mock_stdout.getvalue()
        
        self.assertTrue(confirmed)
        self.assertIn("DETAILED HELP", output)
        self.assertIn("EVENT PREVIEW", output)  # From refresh
    
    @patch('builtins.input')
    def test_run_interactive_editing_invalid_input(self, mock_input):
        """Test handling invalid input during interactive editing."""
        self.interface.current_event = self.sample_event
        mock_input.side_effect = [
            "invalid",  # Invalid command
            "99",       # Invalid field number
            "c",        # Confirm
            "y"         # Final confirmation
        ]
        
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            confirmed, event = self.interface.run_interactive_editing()
            output = mock_stdout.getvalue()
        
        self.assertTrue(confirmed)
        self.assertIn("Invalid choice", output)
        self.assertIn("Invalid field number", output)


class TestCreateEventFromText(unittest.TestCase):
    """Test cases for the create_event_from_text convenience function."""
    
    @patch('ui.event_preview.EventPreviewInterface.run_interactive_editing')
    @patch('ui.event_preview.EventPreviewInterface.display_event_preview')
    def test_create_event_from_text_success(self, mock_display, mock_editing):
        """Test successful event creation from text."""
        # Mock the editing interface to return success
        mock_event = Event(
            title="Test Meeting",
            start_datetime=datetime(2024, 3, 15, 14, 0),
            end_datetime=datetime(2024, 3, 15, 15, 0)
        )
        mock_editing.return_value = (True, mock_event)
        
        success, event = create_event_from_text("Meeting tomorrow at 2pm")
        
        self.assertTrue(success)
        self.assertEqual(event, mock_event)
        mock_display.assert_called_once()
        mock_editing.assert_called_once()
    
    @patch('ui.event_preview.EventPreviewInterface.run_interactive_editing')
    @patch('ui.event_preview.EventPreviewInterface.display_event_preview')
    def test_create_event_from_text_cancelled(self, mock_display, mock_editing):
        """Test cancelled event creation from text."""
        # Mock the editing interface to return cancellation
        mock_editing.return_value = (False, None)
        
        success, event = create_event_from_text("Meeting tomorrow at 2pm")
        
        self.assertFalse(success)
        self.assertIsNone(event)
        mock_display.assert_called_once()
        mock_editing.assert_called_once()


if __name__ == '__main__':
    unittest.main()