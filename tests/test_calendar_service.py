"""
Unit tests for the CalendarService class.
Tests event validation, creation, storage, and error handling.
"""

import json
import os
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch, mock_open

from models.event_models import Event, ValidationResult
from services.calendar_service import (
    CalendarService, 
    CalendarServiceError, 
    EventValidationError, 
    EventCreationError
)


class TestCalendarService(unittest.TestCase):
    """Test cases for CalendarService functionality."""
    
    def setUp(self):
        """Set up test fixtures with temporary storage."""
        self.temp_dir = tempfile.mkdtemp()
        self.test_storage_path = os.path.join(self.temp_dir, "test_events.json")
        self.service = CalendarService(storage_path=self.test_storage_path)
        
        # Create test events
        self.valid_event = Event(
            title="Test Meeting",
            start_datetime=datetime(2024, 12, 15, 14, 0),
            end_datetime=datetime(2024, 12, 15, 15, 0),
            location="Conference Room A",
            description="Test meeting description"
        )
        
        self.future_event = Event(
            title="Future Event",
            start_datetime=datetime.now() + timedelta(days=1),
            end_datetime=datetime.now() + timedelta(days=1, hours=1)
        )
    
    def tearDown(self):
        """Clean up test files."""
        if os.path.exists(self.test_storage_path):
            os.remove(self.test_storage_path)
        os.rmdir(self.temp_dir)
    
    def test_service_initialization(self):
        """Test CalendarService initialization and storage setup."""
        # Test that storage file is created
        self.assertTrue(Path(self.test_storage_path).exists())
        
        # Test default calendar ID
        self.assertEqual(self.service.get_default_calendar(), "default")
        
        # Test storage info
        info = self.service.get_storage_info()
        self.assertIn('storage_path', info)
        self.assertIn('event_count', info)
        self.assertEqual(info['event_count'], 0)
    
    def test_validate_event_valid(self):
        """Test validation of a valid event."""
        result = self.service.validate_event(self.valid_event)
        
        self.assertIsInstance(result, ValidationResult)
        self.assertTrue(result.is_valid)
        self.assertEqual(len(result.missing_fields), 0)
    
    def test_validate_event_missing_title(self):
        """Test validation fails for missing title."""
        # Create event with valid data first, then modify title to test validation
        invalid_event = Event(
            title="Valid Title",  # Start with valid title
            start_datetime=datetime(2024, 12, 15, 14, 0),
            end_datetime=datetime(2024, 12, 15, 15, 0)
        )
        # Modify title after creation to bypass __post_init__ validation
        invalid_event.title = ""
        
        result = self.service.validate_event(invalid_event)
        
        self.assertFalse(result.is_valid)
        self.assertIn("title", result.missing_fields)
    
    def test_validate_event_invalid_datetime(self):
        """Test validation fails for invalid datetime logic."""
        # Create event with valid data first, then modify times to test validation
        invalid_event = Event(
            title="Test Event",
            start_datetime=datetime(2024, 12, 15, 14, 0),
            end_datetime=datetime(2024, 12, 15, 15, 0)
        )
        # Modify times after creation to bypass __post_init__ validation
        invalid_event.start_datetime = datetime(2024, 12, 15, 15, 0)  # After end time
        invalid_event.end_datetime = datetime(2024, 12, 15, 14, 0)
        
        result = self.service.validate_event(invalid_event)
        
        self.assertFalse(result.is_valid)
        self.assertTrue(len(result.warnings) > 0)
    
    def test_validate_event_past_datetime(self):
        """Test validation warning for past events."""
        past_event = Event(
            title="Past Event",
            start_datetime=datetime(2020, 1, 1, 10, 0),
            end_datetime=datetime(2020, 1, 1, 11, 0)
        )
        
        result = self.service.validate_event(past_event)
        
        # Should still be valid but with warnings
        self.assertTrue(result.is_valid)
        self.assertTrue(any("past" in warning.lower() for warning in result.warnings))
    
    def test_validate_event_long_duration(self):
        """Test validation warning for very long events."""
        long_event = Event(
            title="Long Event",
            start_datetime=datetime.now() + timedelta(days=1),
            end_datetime=datetime.now() + timedelta(days=2, hours=1)  # 25 hours
        )
        
        result = self.service.validate_event(long_event)
        
        self.assertTrue(result.is_valid)
        self.assertTrue(any("duration" in warning.lower() for warning in result.warnings))
    
    def test_create_event_success(self):
        """Test successful event creation."""
        with patch('builtins.print'):  # Suppress console output
            success = self.service.create_event(self.future_event)
        
        self.assertTrue(success)
        
        # Verify event was stored
        events = self.service.list_events()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].title, self.future_event.title)
    
    def test_create_event_validation_failure(self):
        """Test event creation fails with invalid event."""
        # Create event with valid data first, then modify to test validation
        invalid_event = Event(
            title="Valid Title",
            start_datetime=datetime.now() + timedelta(days=1),
            end_datetime=datetime.now() + timedelta(days=1, hours=1)
        )
        # Modify title after creation to bypass __post_init__ validation
        invalid_event.title = ""
        
        with self.assertRaises(EventValidationError):
            self.service.create_event(invalid_event)
    
    def test_create_multiple_events(self):
        """Test creating multiple events."""
        event1 = Event(
            title="Event 1",
            start_datetime=datetime.now() + timedelta(days=1),
            end_datetime=datetime.now() + timedelta(days=1, hours=1)
        )
        
        event2 = Event(
            title="Event 2",
            start_datetime=datetime.now() + timedelta(days=2),
            end_datetime=datetime.now() + timedelta(days=2, hours=1)
        )
        
        with patch('builtins.print'):  # Suppress console output
            self.service.create_event(event1)
            self.service.create_event(event2)
        
        events = self.service.list_events()
        self.assertEqual(len(events), 2)
        
        # Events should be sorted by start time
        self.assertEqual(events[0].title, "Event 1")
        self.assertEqual(events[1].title, "Event 2")
    
    def test_conflict_detection(self):
        """Test detection of scheduling conflicts."""
        # Create first event
        with patch('builtins.print'):
            self.service.create_event(self.future_event)
        
        # Create overlapping event
        overlapping_event = Event(
            title="Overlapping Event",
            start_datetime=self.future_event.start_datetime + timedelta(minutes=30),
            end_datetime=self.future_event.end_datetime + timedelta(minutes=30)
        )
        
        # Should still create but with warning
        with patch('builtins.print') as mock_print:
            self.service.create_event(overlapping_event)
            
        # Check that conflict warning was printed
        print_calls = [str(call) for call in mock_print.call_args_list]
        conflict_warning = any("conflict" in call.lower() for call in print_calls)
        self.assertTrue(conflict_warning)
    
    def test_list_events_with_date_filter(self):
        """Test listing events with date range filters."""
        # Create events on different dates
        event1 = Event(
            title="Event 1",
            start_datetime=datetime(2024, 12, 15, 10, 0),
            end_datetime=datetime(2024, 12, 15, 11, 0)
        )
        
        event2 = Event(
            title="Event 2",
            start_datetime=datetime(2024, 12, 20, 10, 0),
            end_datetime=datetime(2024, 12, 20, 11, 0)
        )
        
        with patch('builtins.print'):
            self.service.create_event(event1)
            self.service.create_event(event2)
        
        # Test date filtering
        filtered_events = self.service.list_events(
            start_date=datetime(2024, 12, 16),
            end_date=datetime(2024, 12, 25)
        )
        
        self.assertEqual(len(filtered_events), 1)
        self.assertEqual(filtered_events[0].title, "Event 2")
    
    def test_delete_event(self):
        """Test event deletion."""
        with patch('builtins.print'):
            self.service.create_event(self.future_event)
        
        # Get the event ID from storage
        events_data = self.service._load_events()
        event_id = events_data[0]['id']
        
        # Delete the event
        success = self.service.delete_event(event_id)
        self.assertTrue(success)
        
        # Verify event was deleted
        events = self.service.list_events()
        self.assertEqual(len(events), 0)
    
    def test_delete_nonexistent_event(self):
        """Test deleting a non-existent event."""
        success = self.service.delete_event("nonexistent_id")
        self.assertFalse(success)
    
    def test_storage_error_handling(self):
        """Test error handling for storage operations."""
        # Test with invalid storage path (use Windows-style path)
        with self.assertRaises(EventCreationError):
            invalid_service = CalendarService(storage_path="Z:\\nonexistent\\path\\events.json")
    
    def test_malformed_storage_data(self):
        """Test handling of malformed storage data."""
        # Write malformed JSON to storage file
        with open(self.test_storage_path, 'w') as f:
            f.write('{"invalid": json}')
        
        # Service should handle this gracefully
        events = self.service.list_events()
        self.assertEqual(len(events), 0)
    
    def test_event_id_generation(self):
        """Test unique event ID generation."""
        import time
        
        id1 = self.service._generate_event_id()
        time.sleep(0.001)  # Small delay to ensure different microseconds
        id2 = self.service._generate_event_id()
        
        self.assertNotEqual(id1, id2)
        self.assertTrue(id1.startswith("event_"))
        self.assertTrue(id2.startswith("event_"))
    
    def test_storage_info(self):
        """Test storage information retrieval."""
        # Create an event first
        with patch('builtins.print'):
            self.service.create_event(self.future_event)
        
        info = self.service.get_storage_info()
        
        self.assertEqual(info['event_count'], 1)
        self.assertTrue(info['storage_exists'])
        self.assertGreater(info['storage_size_bytes'], 0)
        self.assertTrue(info['storage_path'].endswith('test_events.json'))


class TestCalendarServiceExceptions(unittest.TestCase):
    """Test cases for CalendarService exception handling."""
    
    def test_calendar_service_error_inheritance(self):
        """Test exception class inheritance."""
        self.assertTrue(issubclass(EventValidationError, CalendarServiceError))
        self.assertTrue(issubclass(EventCreationError, CalendarServiceError))
        self.assertTrue(issubclass(CalendarServiceError, Exception))
    
    def test_exception_messages(self):
        """Test exception message handling."""
        validation_error = EventValidationError("Validation failed")
        creation_error = EventCreationError("Creation failed")
        
        self.assertEqual(str(validation_error), "Validation failed")
        self.assertEqual(str(creation_error), "Creation failed")


if __name__ == '__main__':
    unittest.main()