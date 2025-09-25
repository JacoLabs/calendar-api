"""
Tests for calendar service confirmation and retry mechanisms.
Tests the enhanced calendar service features for event creation feedback.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import tempfile
import os
import json

from services.calendar_service import CalendarService, EventCreationError, EventValidationError
from models.event_models import Event


class TestCalendarServiceConfirmation(unittest.TestCase):
    """Test cases for calendar service confirmation features."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.storage_path = os.path.join(self.temp_dir, "test_events.json")
        
        self.calendar_service = CalendarService(storage_path=self.storage_path, max_retries=3)
        
        self.test_event = Event(
            title="Test Meeting",
            start_datetime=datetime.now() + timedelta(hours=1),
            end_datetime=datetime.now() + timedelta(hours=2),
            location="Conference Room A",
            description="Test event description"
        )
    
    def tearDown(self):
        """Clean up test fixtures."""
        if os.path.exists(self.storage_path):
            os.remove(self.storage_path)
        os.rmdir(self.temp_dir)
    
    def test_create_event_returns_detailed_response(self):
        """Test that create_event returns detailed success information."""
        success, message, event_id = self.calendar_service.create_event(self.test_event)
        
        self.assertTrue(success)
        self.assertIsNotNone(event_id)
        self.assertIn("CALENDAR EVENT CREATED SUCCESSFULLY", message)
        self.assertIn(self.test_event.title, message)
        self.assertIn(event_id, message)
    
    def test_success_message_formatting(self):
        """Test that success messages are properly formatted."""
        success, message, event_id = self.calendar_service.create_event(self.test_event)
        
        # Check message contains all expected elements
        self.assertIn("📅", message)  # Calendar emoji
        self.assertIn(self.test_event.title, message)
        self.assertIn(self.test_event.location, message)
        self.assertIn(event_id, message)
        
        # Check date formatting
        expected_start = self.test_event.start_datetime.strftime('%A, %B %d, %Y at %H:%M')
        self.assertIn(expected_start, message)
    
    def test_success_message_with_conflicts(self):
        """Test success message includes conflict warnings."""
        # Create an existing event that conflicts
        existing_event = Event(
            title="Existing Meeting",
            start_datetime=self.test_event.start_datetime,
            end_datetime=self.test_event.end_datetime
        )
        
        # Add existing event first
        self.calendar_service.create_event(existing_event)
        
        # Create conflicting event
        success, message, event_id = self.calendar_service.create_event(self.test_event)
        
        self.assertTrue(success)
        self.assertIn("SCHEDULING CONFLICTS DETECTED", message)
        self.assertIn("Existing Meeting", message)
    
    def test_display_event_confirmation(self):
        """Test the display_event_confirmation method."""
        event_id = "test_123"
        
        with patch('builtins.print') as mock_print:
            self.calendar_service.display_event_confirmation(
                self.test_event, event_id, ["Conflict with Meeting A"]
            )
            
            # Verify print was called
            mock_print.assert_called()
            
            # Check the actual arguments passed to print
            if mock_print.call_args_list:
                # Get the first argument of the first call (the message)
                printed_message = mock_print.call_args_list[0][0][0]
                self.assertIn("CALENDAR EVENT CREATED SUCCESSFULLY", printed_message)
                self.assertIn(self.test_event.title, printed_message)
                self.assertIn("SCHEDULING CONFLICTS DETECTED", printed_message)
            else:
                self.fail("No print calls were made")
    
    @patch('builtins.input', side_effect=['y', 'y'])  # Retry twice
    @patch('builtins.print')
    def test_create_event_with_retry_interactive(self, mock_print, mock_input):
        """Test interactive retry mechanism."""
        # Mock the create_event method to fail twice, then succeed
        original_create = self.calendar_service.create_event
        call_count = 0
        
        def mock_create_event(event):
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise EventCreationError("Temporary failure")
            return original_create(event)
        
        with patch.object(self.calendar_service, 'create_event', side_effect=mock_create_event):
            success, message, event_id = self.calendar_service.create_event_with_retry(
                self.test_event, interactive=True
            )
        
        self.assertTrue(success)
        self.assertIn("after 3 attempt(s)", message)
        self.assertEqual(call_count, 3)
    
    @patch('builtins.input', return_value='n')  # Don't retry
    @patch('builtins.print')
    def test_create_event_with_retry_decline(self, mock_print, mock_input):
        """Test declining retry in interactive mode."""
        with patch.object(self.calendar_service, 'create_event', 
                         side_effect=EventCreationError("Persistent failure")):
            success, message, event_id = self.calendar_service.create_event_with_retry(
                self.test_event, interactive=True
            )
        
        self.assertFalse(success)
        self.assertIn("Persistent failure", message)
        self.assertIsNone(event_id)
    
    @patch('builtins.print')
    def test_create_event_with_retry_non_interactive(self, mock_print):
        """Test non-interactive retry mechanism."""
        call_count = 0
        
        def mock_create_event(event):
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                return False, "Temporary failure", None
            return True, "Success", "event_123"
        
        with patch.object(self.calendar_service, 'create_event', side_effect=mock_create_event):
            success, message, event_id = self.calendar_service.create_event_with_retry(
                self.test_event, interactive=False
            )
        
        self.assertTrue(success)
        self.assertEqual(call_count, 3)
    
    @patch('builtins.input', return_value='1')  # Choose retry option
    @patch('builtins.print')
    def test_handle_creation_error_retry(self, mock_print, mock_input):
        """Test error handling with retry option."""
        error_message = "Database connection failed"
        
        retry_requested, modified_event = self.calendar_service.handle_creation_error(
            error_message, self.test_event, interactive=True
        )
        
        self.assertTrue(retry_requested)
        self.assertEqual(modified_event, self.test_event)
    
    @patch('builtins.input', return_value='3')  # Choose cancel option
    @patch('builtins.print')
    def test_handle_creation_error_cancel(self, mock_print, mock_input):
        """Test error handling with cancel option."""
        error_message = "Storage full"
        
        retry_requested, modified_event = self.calendar_service.handle_creation_error(
            error_message, self.test_event, interactive=True
        )
        
        self.assertFalse(retry_requested)
        self.assertIsNone(modified_event)
    
    @patch('ui.event_preview.EventPreviewInterface')
    @patch('builtins.input', return_value='2')  # Choose edit option
    @patch('builtins.print')
    def test_handle_creation_error_edit(self, mock_print, mock_input, mock_interface_class):
        """Test error handling with edit option."""
        # Mock the event preview interface
        mock_interface = Mock()
        mock_interface.run_interactive_editing.return_value = (True, self.test_event)
        mock_interface_class.return_value = mock_interface
        
        error_message = "Validation failed"
        
        retry_requested, modified_event = self.calendar_service.handle_creation_error(
            error_message, self.test_event, interactive=True
        )
        
        self.assertTrue(retry_requested)
        self.assertEqual(modified_event, self.test_event)
        mock_interface.display_event_preview.assert_called_once()
        mock_interface.run_interactive_editing.assert_called_once()
    
    def test_handle_creation_error_non_interactive(self):
        """Test error handling in non-interactive mode."""
        error_message = "Network error"
        
        retry_requested, modified_event = self.calendar_service.handle_creation_error(
            error_message, self.test_event, interactive=False
        )
        
        self.assertFalse(retry_requested)
        self.assertIsNone(modified_event)
    
    def test_validation_error_not_retried(self):
        """Test that validation errors are not retried."""
        # Mock the validate_event method to return invalid result
        with patch.object(self.calendar_service, 'validate_event') as mock_validate:
            from models.event_models import ValidationResult
            invalid_result = ValidationResult(is_valid=False)
            invalid_result.add_missing_field('title', 'Title is required')
            mock_validate.return_value = invalid_result
            
            success, message, event_id = self.calendar_service.create_event_with_retry(
                self.test_event, interactive=False
            )
            
            self.assertFalse(success)
            self.assertIn("Validation Error", message)
            self.assertIsNone(event_id)
    
    def test_event_id_generation(self):
        """Test that unique event IDs are generated."""
        # Create multiple events and check IDs are unique
        event_ids = set()
        
        for i in range(5):
            event = Event(
                title=f"Event {i}",
                start_datetime=datetime.now() + timedelta(hours=i+1),
                end_datetime=datetime.now() + timedelta(hours=i+2)
            )
            
            success, message, event_id = self.calendar_service.create_event(event)
            self.assertTrue(success)
            self.assertIsNotNone(event_id)
            self.assertNotIn(event_id, event_ids)
            event_ids.add(event_id)
        
        # All IDs should be unique
        self.assertEqual(len(event_ids), 5)
    
    def test_conflict_detection_accuracy(self):
        """Test that conflict detection works correctly."""
        # Create base event
        base_event = Event(
            title="Base Event",
            start_datetime=datetime(2024, 3, 15, 14, 0),  # 2:00 PM
            end_datetime=datetime(2024, 3, 15, 15, 0)     # 3:00 PM
        )
        self.calendar_service.create_event(base_event)
        
        # Test overlapping event (should conflict)
        overlapping_event = Event(
            title="Overlapping Event",
            start_datetime=datetime(2024, 3, 15, 14, 30),  # 2:30 PM
            end_datetime=datetime(2024, 3, 15, 15, 30)     # 3:30 PM
        )
        
        success, message, event_id = self.calendar_service.create_event(overlapping_event)
        self.assertTrue(success)  # Should still create but warn
        self.assertIn("SCHEDULING CONFLICTS DETECTED", message)
        
        # Test non-overlapping event (should not conflict)
        non_overlapping_event = Event(
            title="Non-overlapping Event",
            start_datetime=datetime(2024, 3, 15, 16, 0),  # 4:00 PM
            end_datetime=datetime(2024, 3, 15, 17, 0)     # 5:00 PM
        )
        
        success, message, event_id = self.calendar_service.create_event(non_overlapping_event)
        self.assertTrue(success)
        self.assertNotIn("SCHEDULING CONFLICTS DETECTED", message)
    
    def test_storage_info_after_events(self):
        """Test storage info reflects created events."""
        initial_info = self.calendar_service.get_storage_info()
        self.assertEqual(initial_info['event_count'], 0)
        
        # Create some events
        for i in range(3):
            event = Event(
                title=f"Event {i}",
                start_datetime=datetime.now() + timedelta(hours=i+1),
                end_datetime=datetime.now() + timedelta(hours=i+2)
            )
            self.calendar_service.create_event(event)
        
        final_info = self.calendar_service.get_storage_info()
        self.assertEqual(final_info['event_count'], 3)
        self.assertGreater(final_info['storage_size_bytes'], 0)


class TestConfirmationIntegration(unittest.TestCase):
    """Integration tests for confirmation features."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.storage_path = os.path.join(self.temp_dir, "integration_events.json")
        
        self.calendar_service = CalendarService(storage_path=self.storage_path)
        
        self.test_event = Event(
            title="Integration Test Event",
            start_datetime=datetime.now() + timedelta(hours=1),
            end_datetime=datetime.now() + timedelta(hours=2),
            location="Test Location"
        )
    
    def tearDown(self):
        """Clean up test fixtures."""
        if os.path.exists(self.storage_path):
            os.remove(self.storage_path)
        os.rmdir(self.temp_dir)
    
    def test_end_to_end_event_creation_with_confirmation(self):
        """Test complete event creation flow with confirmation."""
        # Create event
        success, message, event_id = self.calendar_service.create_event(self.test_event)
        
        # Verify success
        self.assertTrue(success)
        self.assertIsNotNone(event_id)
        
        # Verify event was actually stored
        events = self.calendar_service.list_events()
        self.assertEqual(len(events), 1)
        
        stored_event = events[0]
        self.assertEqual(stored_event.title, self.test_event.title)
        self.assertEqual(stored_event.location, self.test_event.location)
        
        # Verify storage file exists and contains event
        self.assertTrue(os.path.exists(self.storage_path))
        
        with open(self.storage_path, 'r') as f:
            stored_data = json.load(f)
        
        self.assertEqual(len(stored_data), 1)
        self.assertEqual(stored_data[0]['title'], self.test_event.title)
        self.assertEqual(stored_data[0]['id'], event_id)
    
    @patch('builtins.print')
    def test_confirmation_display_integration(self, mock_print):
        """Test that confirmation is properly displayed."""
        success, message, event_id = self.calendar_service.create_event(self.test_event)
        
        # Display confirmation
        self.calendar_service.display_event_confirmation(self.test_event, event_id)
        
        # Verify confirmation was displayed
        mock_print.assert_called()
        
        # Check printed content
        if mock_print.call_args_list:
            printed_message = mock_print.call_args_list[0][0][0]
            self.assertIn("CALENDAR EVENT CREATED SUCCESSFULLY", printed_message)
            self.assertIn(self.test_event.title, printed_message)
            self.assertIn(event_id, printed_message)
        else:
            self.fail("No print calls were made")


if __name__ == '__main__':
    unittest.main()