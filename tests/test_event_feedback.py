"""
Tests for event creation feedback system.
Tests confirmation flow, error handling, and retry mechanisms.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import tempfile
import os
from pathlib import Path

from services.event_feedback import EventCreationFeedback, FeedbackType, create_event_with_comprehensive_feedback
from services.calendar_service import CalendarService, EventCreationError, EventValidationError
from models.event_models import Event


class TestEventCreationFeedback(unittest.TestCase):
    """Test cases for EventCreationFeedback class."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create temporary storage for testing
        self.temp_dir = tempfile.mkdtemp()
        self.storage_path = os.path.join(self.temp_dir, "test_events.json")
        
        # Create calendar service with test storage
        self.calendar_service = CalendarService(storage_path=self.storage_path)
        self.feedback_system = EventCreationFeedback(self.calendar_service)
        
        # Create test event
        self.test_event = Event(
            title="Test Meeting",
            start_datetime=datetime.now() + timedelta(hours=1),
            end_datetime=datetime.now() + timedelta(hours=2),
            location="Conference Room A",
            description="Test event for feedback system"
        )
    
    def tearDown(self):
        """Clean up test fixtures."""
        # Clean up temporary files
        if os.path.exists(self.storage_path):
            os.remove(self.storage_path)
        os.rmdir(self.temp_dir)
    
    def test_successful_event_creation_feedback(self):
        """Test feedback for successful event creation."""
        # Test non-interactive mode
        success, message = self.feedback_system.create_event_with_feedback(
            self.test_event, interactive=False
        )
        
        self.assertTrue(success)
        self.assertIn("CALENDAR EVENT CREATED SUCCESSFULLY", message)
        self.assertIn(self.test_event.title, message)
        
        # Check feedback history
        self.assertEqual(len(self.feedback_system.feedback_history), 1)
        self.assertEqual(self.feedback_system.feedback_history[0]['type'], FeedbackType.SUCCESS.value)
    
    def test_event_creation_failure_feedback(self):
        """Test feedback for failed event creation."""
        # Create a mock calendar service that fails
        mock_calendar_service = Mock()
        mock_calendar_service.create_event_with_retry.return_value = (False, "Storage error", None)
        
        feedback_system = EventCreationFeedback(mock_calendar_service)
        
        success, message = feedback_system.create_event_with_feedback(
            self.test_event, interactive=False
        )
        
        self.assertFalse(success)
        self.assertIn("Storage error", message)
        
        # Check feedback history
        self.assertEqual(len(feedback_system.feedback_history), 1)
        self.assertEqual(feedback_system.feedback_history[0]['type'], FeedbackType.ERROR.value)
    
    def test_validation_error_feedback(self):
        """Test feedback for validation errors."""
        # Create a mock calendar service that raises validation error
        mock_calendar_service = Mock()
        mock_calendar_service.create_event_with_retry.side_effect = EventValidationError("Title is required")
        
        feedback_system = EventCreationFeedback(mock_calendar_service)
        
        success, message = feedback_system.create_event_with_feedback(
            self.test_event, interactive=False
        )
        
        self.assertFalse(success)
        self.assertIn("validation failed", message.lower())
        
        # Check feedback history (use the correct feedback system instance)
        self.assertEqual(len(feedback_system.feedback_history), 1)
        self.assertEqual(feedback_system.feedback_history[0]['type'], FeedbackType.ERROR.value)
    
    @patch('builtins.input', side_effect=['1'])  # Choose retry option
    @patch('services.event_feedback.EventCreationFeedback._display_success_feedback')
    def test_retry_mechanism_success(self, mock_display, mock_input):
        """Test successful retry after initial failure."""
        # Mock calendar service that fails first, then succeeds
        mock_calendar_service = Mock()
        mock_calendar_service.create_event_with_retry.side_effect = [
            (False, "Temporary error", None),  # First attempt fails
            (True, "Success message", "event_123")  # Second attempt succeeds
        ]
        mock_calendar_service.handle_creation_error.return_value = (True, self.test_event)
        
        feedback_system = EventCreationFeedback(mock_calendar_service)
        
        success, message = feedback_system.create_event_with_feedback(
            self.test_event, interactive=True
        )
        
        self.assertTrue(success)
        self.assertIn("Success message", message)
        
        # Verify retry was attempted
        self.assertEqual(mock_calendar_service.create_event_with_retry.call_count, 2)
    
    @patch('builtins.input', return_value='')  # Just press Enter
    @patch('builtins.print')
    def test_display_success_feedback_interactive(self, mock_print, mock_input):
        """Test interactive success feedback display."""
        event_id = "test_event_123"
        message = "Test success message"
        
        self.feedback_system._display_success_feedback(self.test_event, event_id, message)
        
        # Verify success message was printed
        mock_print.assert_called()
        # Check the actual arguments passed to print
        if mock_print.call_args_list:
            # The message should be in one of the print calls
            found_message = False
            for call_args in mock_print.call_args_list:
                if call_args[0] and "Test success message" in str(call_args[0][0]):
                    found_message = True
                    break
            self.assertTrue(found_message, "Success message not found in print calls")
        else:
            self.fail("No print calls were made")
    
    @patch('builtins.print')
    def test_display_validation_error(self, mock_print):
        """Test validation error display."""
        error_message = "Title is required"
        
        self.feedback_system._display_validation_error(self.test_event, error_message)
        
        # Verify error message was printed
        mock_print.assert_called()
        if mock_print.call_args_list:
            found_error = False
            for call_args in mock_print.call_args_list:
                if call_args[0] and "VALIDATION ERROR" in str(call_args[0][0]):
                    found_error = True
                    break
            self.assertTrue(found_error, "Validation error message not found in print calls")
        else:
            self.fail("No print calls were made")
    
    @patch('builtins.print')
    def test_display_unexpected_error(self, mock_print):
        """Test unexpected error display."""
        error_message = "Database connection failed"
        
        self.feedback_system._display_unexpected_error(self.test_event, error_message)
        
        # Verify error message was printed
        mock_print.assert_called()
        if mock_print.call_args_list:
            found_error = False
            for call_args in mock_print.call_args_list:
                if call_args[0] and "UNEXPECTED ERROR" in str(call_args[0][0]):
                    found_error = True
                    break
            self.assertTrue(found_error, "Unexpected error message not found in print calls")
        else:
            self.fail("No print calls were made")
    
    def test_feedback_logging(self):
        """Test feedback logging functionality."""
        # Create some feedback entries
        self.feedback_system._log_feedback(
            FeedbackType.SUCCESS, "Test success", {'event_id': '123'}
        )
        self.feedback_system._log_feedback(
            FeedbackType.ERROR, "Test error", {'error_type': 'validation'}
        )
        
        self.assertEqual(len(self.feedback_system.feedback_history), 2)
        
        # Check first entry
        first_entry = self.feedback_system.feedback_history[0]
        self.assertEqual(first_entry['type'], FeedbackType.SUCCESS.value)
        self.assertEqual(first_entry['message'], "Test success")
        self.assertEqual(first_entry['metadata']['event_id'], '123')
        
        # Check second entry
        second_entry = self.feedback_system.feedback_history[1]
        self.assertEqual(second_entry['type'], FeedbackType.ERROR.value)
        self.assertEqual(second_entry['message'], "Test error")
    
    def test_feedback_summary(self):
        """Test feedback summary generation."""
        # Add some test feedback entries
        self.feedback_system._log_feedback(
            FeedbackType.SUCCESS, "Success 1", {'event_title': 'Event 1'}
        )
        self.feedback_system._log_feedback(
            FeedbackType.SUCCESS, "Success 2", {'event_title': 'Event 2'}
        )
        self.feedback_system._log_feedback(
            FeedbackType.ERROR, "Error 1", {'event_title': 'Event 3'}
        )
        
        summary = self.feedback_system.get_feedback_summary()
        
        self.assertEqual(summary['total_events'], 3)
        self.assertEqual(summary['successful_events'], 2)
        self.assertEqual(summary['failed_events'], 1)
        self.assertAlmostEqual(summary['success_rate'], 2/3, places=2)
        self.assertEqual(len(summary['recent_activity']), 3)
    
    @patch('builtins.print')
    def test_display_feedback_summary(self, mock_print):
        """Test feedback summary display."""
        # Add some test data
        self.feedback_system._log_feedback(
            FeedbackType.SUCCESS, "Success", {'event_title': 'Test Event'}
        )
        
        self.feedback_system.display_feedback_summary()
        
        # Verify summary was printed
        mock_print.assert_called()
        if mock_print.call_args_list:
            found_summary = False
            for call_args in mock_print.call_args_list:
                if call_args[0] and "EVENT CREATION SUMMARY" in str(call_args[0][0]):
                    found_summary = True
                    break
            self.assertTrue(found_summary, "Summary message not found in print calls")
        else:
            self.fail("No print calls were made")
    
    @patch('services.event_feedback.EventCreationFeedback._copy_event_to_clipboard')
    @patch('builtins.input', return_value='copy')
    @patch('builtins.print')
    def test_copy_event_to_clipboard(self, mock_print, mock_input, mock_copy):
        """Test copying event details to clipboard."""
        event_id = "test_123"
        
        self.feedback_system._display_success_feedback(self.test_event, event_id, "Success")
        
        # Verify copy method was called
        mock_copy.assert_called_once_with(self.test_event, event_id)
    
    @patch('builtins.input', return_value='details')
    @patch('builtins.print')
    def test_show_detailed_event_info(self, mock_print, mock_input):
        """Test showing detailed event information."""
        event_id = "test_123"
        
        self.feedback_system._display_success_feedback(self.test_event, event_id, "Success")
        
        # Verify detailed info was printed
        mock_print.assert_called()
        if mock_print.call_args_list:
            found_details = False
            for call_args in mock_print.call_args_list:
                if call_args[0] and "DETAILED EVENT INFORMATION" in str(call_args[0][0]):
                    found_details = True
                    break
            self.assertTrue(found_details, "Detailed info message not found in print calls")
        else:
            self.fail("No print calls were made")


class TestConvenienceFunction(unittest.TestCase):
    """Test cases for convenience function."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.storage_path = os.path.join(self.temp_dir, "test_events.json")
        
        self.test_event = Event(
            title="Test Event",
            start_datetime=datetime.now() + timedelta(hours=1),
            end_datetime=datetime.now() + timedelta(hours=2)
        )
    
    def tearDown(self):
        """Clean up test fixtures."""
        if os.path.exists(self.storage_path):
            os.remove(self.storage_path)
        os.rmdir(self.temp_dir)
    
    def test_convenience_function_with_default_service(self):
        """Test convenience function with default calendar service."""
        success, message = create_event_with_comprehensive_feedback(
            self.test_event, interactive=False
        )
        
        self.assertTrue(success)
        self.assertIn("CALENDAR EVENT CREATED SUCCESSFULLY", message)
    
    def test_convenience_function_with_custom_service(self):
        """Test convenience function with custom calendar service."""
        calendar_service = CalendarService(storage_path=self.storage_path)
        
        success, message = create_event_with_comprehensive_feedback(
            self.test_event, calendar_service=calendar_service, interactive=False
        )
        
        self.assertTrue(success)
        self.assertIn("CALENDAR EVENT CREATED SUCCESSFULLY", message)


class TestErrorScenarios(unittest.TestCase):
    """Test cases for various error scenarios."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.storage_path = os.path.join(self.temp_dir, "test_events.json")
        
        self.test_event = Event(
            title="Test Event",
            start_datetime=datetime.now() + timedelta(hours=1),
            end_datetime=datetime.now() + timedelta(hours=2)
        )
    
    def tearDown(self):
        """Clean up test fixtures."""
        # Clean up all files in temp directory
        import shutil
        if os.path.exists(self.temp_dir):
            try:
                shutil.rmtree(self.temp_dir)
            except PermissionError:
                # Try to fix permissions and retry
                for root, dirs, files in os.walk(self.temp_dir):
                    for file in files:
                        try:
                            os.chmod(os.path.join(root, file), 0o666)
                        except:
                            pass
                try:
                    shutil.rmtree(self.temp_dir)
                except:
                    pass  # Give up if still can't delete
    
    def test_storage_permission_error(self):
        """Test handling of storage permission errors."""
        # Create a read-only directory to simulate permission error
        readonly_path = os.path.join(self.temp_dir, "readonly_events.json")
        
        # Create the file first
        with open(readonly_path, 'w') as f:
            f.write('[]')
        
        # Make it read-only (on Windows, this might not work as expected)
        try:
            os.chmod(readonly_path, 0o444)
            
            calendar_service = CalendarService(storage_path=readonly_path)
            feedback_system = EventCreationFeedback(calendar_service)
            
            success, message = feedback_system.create_event_with_feedback(
                self.test_event, interactive=False
            )
            
            # Should fail due to permission error
            self.assertFalse(success)
            
        except PermissionError:
            # Expected on some systems
            pass
        finally:
            # Restore permissions for cleanup
            try:
                os.chmod(readonly_path, 0o666)
            except:
                pass
    
    def test_invalid_datetime_event(self):
        """Test handling of events with invalid datetime."""
        # Mock calendar service that raises validation error for invalid datetime
        mock_calendar_service = Mock()
        mock_calendar_service.create_event_with_retry.side_effect = EventValidationError("Start time must be before end time")
        
        feedback_system = EventCreationFeedback(mock_calendar_service)
        
        success, message = feedback_system.create_event_with_feedback(
            self.test_event, interactive=False
        )
        
        self.assertFalse(success)
        self.assertIn("validation failed", message.lower())
    
    def test_storage_write_failure(self):
        """Test handling of storage write failures."""
        # Create calendar service first
        calendar_service = CalendarService(storage_path=self.storage_path)
        
        # Then mock the save method to fail
        with patch.object(calendar_service, '_save_events', side_effect=IOError("Disk full")):
            feedback_system = EventCreationFeedback(calendar_service)
            
            success, message = feedback_system.create_event_with_feedback(
                self.test_event, interactive=False
            )
            
            self.assertFalse(success)
            self.assertIn("Disk full", message)


if __name__ == '__main__':
    unittest.main()