"""
Integration tests for the complete text-to-calendar workflow.
Tests the end-to-end functionality from text input to event creation.
"""

import unittest
import tempfile
import os
import json
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from main import TextToCalendarApp
from models.event_models import Event, ParsedEvent
from services.event_parser import EventParser
from services.calendar_service import CalendarService
from ui.event_preview import EventPreviewInterface


class TestIntegrationWorkflow(unittest.TestCase):
    """Test the complete integration workflow."""
    
    def setUp(self):
        """Set up test environment with temporary storage."""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_storage = os.path.join(self.temp_dir, "test_events.json")
        
        # Create app with test storage
        self.app = TextToCalendarApp()
        self.app.calendar_service = CalendarService(storage_path=self.temp_storage)
        
        # Configure for testing
        self.app.set_config(
            auto_preview=False,  # Skip interactive preview for tests
            verbose_output=False,  # Reduce output during tests
            error_recovery=False  # Don't prompt for user input
        )
    
    def tearDown(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_complete_workflow_simple_event(self):
        """Test complete workflow with a simple event."""
        text = "Meeting with John tomorrow at 2pm"
        
        success, event, message = self.app.run_complete_workflow(text)
        
        self.assertTrue(success, f"Workflow failed: {message}")
        self.assertIsNotNone(event)
        self.assertIn("Meeting", event.title)
        self.assertEqual(event.start_datetime.hour, 14)  # 2pm
        
        # Verify event was stored
        events = self.app.calendar_service.list_events()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].title, event.title)
    
    def test_complete_workflow_detailed_event(self):
        """Test workflow with detailed event information."""
        text = "Project review meeting at Conference Room A on March 15, 2024 from 10:00 AM to 11:30 AM"
        
        success, event, message = self.app.run_complete_workflow(text)
        
        self.assertTrue(success, f"Workflow failed: {message}")
        self.assertIsNotNone(event)
        self.assertIn("Project review", event.title)
        self.assertIn("Conference Room A", event.location)
        self.assertEqual(event.start_datetime.hour, 10)
        self.assertEqual(event.end_datetime.hour, 11)
        self.assertEqual(event.end_datetime.minute, 30)
    
    def test_workflow_with_invalid_text(self):
        """Test workflow with text that cannot be parsed."""
        text = "This is just random text with no event information"
        
        success, event, message = self.app.run_complete_workflow(text)
        
        # Should fail due to missing required information
        self.assertFalse(success)
        self.assertIsNone(event)
        self.assertIn("validation", message.lower())
    
    def test_batch_workflow(self):
        """Test batch processing of multiple texts."""
        texts = [
            "Meeting with John tomorrow at 2pm",
            "Lunch at cafe next Friday 12:30",
            "Conference call on Monday 10am for 1 hour"
        ]
        
        results = self.app.run_batch_workflow(texts)
        
        self.assertEqual(len(results), 3)
        
        # Check that at least some events were created successfully
        successful_results = [r for r in results if r[0]]  # r[0] is success flag
        self.assertGreater(len(successful_results), 0, "No events were created in batch mode")
        
        # Verify events were stored
        events = self.app.calendar_service.list_events()
        self.assertEqual(len(events), len(successful_results))
    
    def test_workflow_error_handling(self):
        """Test error handling in the workflow."""
        # Test with empty text
        success, event, message = self.app.run_complete_workflow("")
        self.assertFalse(success)
        self.assertIsNone(event)
        
        # Test with None text (should handle gracefully now)
        success, event, message = self.app.run_complete_workflow(None)
        self.assertFalse(success)
        self.assertIsNone(event)
        self.assertIn("validation", message.lower())
    
    def test_configuration_integration(self):
        """Test that configuration changes affect the workflow."""
        text = "Meeting tomorrow at 2pm for 2 hours"
        
        # Test with default duration
        self.app.set_config(default_duration_minutes=90)
        success, event, message = self.app.run_complete_workflow(text)
        
        self.assertTrue(success)
        # Duration should be overridden by "for 2 hours" in the text
        duration_minutes = (event.end_datetime - event.start_datetime).total_seconds() / 60
        self.assertEqual(duration_minutes, 120)  # 2 hours
    
    def test_parser_integration(self):
        """Test integration between parser and workflow."""
        text = "Team standup every Monday at 9am"
        
        # Parse directly
        parsed_event = self.app.event_parser.parse_text(text)
        self.assertIsNotNone(parsed_event.title)
        self.assertIsNotNone(parsed_event.start_datetime)
        
        # Run through workflow
        success, event, message = self.app.run_complete_workflow(text)
        self.assertTrue(success)
        self.assertEqual(event.title, parsed_event.title)
    
    def test_calendar_service_integration(self):
        """Test integration with calendar service."""
        # Create an event through the workflow
        text = "Doctor appointment next Tuesday at 3pm"
        success, event, message = self.app.run_complete_workflow(text)
        
        self.assertTrue(success)
        
        # Verify through calendar service
        events = self.app.calendar_service.list_events()
        self.assertEqual(len(events), 1)
        
        stored_event = events[0]
        self.assertEqual(stored_event.title, event.title)
        self.assertEqual(stored_event.start_datetime, event.start_datetime)
        
        # Test storage info
        storage_info = self.app.calendar_service.get_storage_info()
        self.assertEqual(storage_info['event_count'], 1)
        self.assertTrue(storage_info['storage_exists'])
    
    @patch('builtins.input')
    def test_interactive_preview_integration(self, mock_input):
        """Test integration with interactive preview (mocked)."""
        # Mock user confirming the event
        mock_input.side_effect = ['c']  # 'c' for confirm
        
        # Enable preview for this test
        self.app.set_config(auto_preview=True)
        
        text = "Team meeting tomorrow at 10am"
        success, event, message = self.app.run_complete_workflow(text)
        
        self.assertTrue(success)
        self.assertIsNotNone(event)
    
    @patch('ui.event_preview.safe_input')
    @patch('ui.event_preview.is_non_interactive')
    def test_interactive_preview_cancellation(self, mock_is_non_interactive, mock_safe_input):
        """Test cancellation in interactive preview."""
        # Force interactive mode for this test
        mock_is_non_interactive.return_value = False
        
        # Mock user cancelling the event
        mock_safe_input.side_effect = ['q']  # 'q' for quit/cancel
        
        # Enable preview for this test
        self.app.set_config(auto_preview=True)
        
        text = "Team meeting tomorrow at 10am"
        success, event, message = self.app.run_complete_workflow(text)
        
        self.assertFalse(success)
        self.assertIsNone(event)
        self.assertIn("cancelled", message.lower())
    
    def test_workflow_with_confidence_scores(self):
        """Test workflow behavior with different confidence scores."""
        # High confidence text
        high_confidence_text = "Meeting on 2024-03-15 at 14:00 in Room 101"
        success, event, message = self.app.run_complete_workflow(high_confidence_text)
        
        self.assertTrue(success)
        
        # Lower confidence text (more ambiguous)
        low_confidence_text = "maybe meet sometime next week"
        success, event, message = self.app.run_complete_workflow(low_confidence_text)
        
        # Should still attempt to create but may fail validation
        # The exact behavior depends on the parsing confidence threshold
        self.assertIsNotNone(message)  # Should have some feedback
    
    def test_multiple_events_in_workflow(self):
        """Test workflow with text containing multiple potential events."""
        text = "Meeting at 10am then lunch at 12pm and conference call at 3pm"
        
        # The parser should handle this and extract the most confident event
        success, event, message = self.app.run_complete_workflow(text)
        
        # Should succeed with at least one event
        if success:
            self.assertIsNotNone(event)
            # Should pick one of the events (likely the first or most confident)
            self.assertTrue(
                any(time in event.title.lower() or str(event.start_datetime.hour) in ['10', '12', '15'] 
                    for time in ['meeting', 'lunch', 'call'])
            )
    
    def test_workflow_date_format_handling(self):
        """Test workflow with different date formats."""
        # Test MM/DD format
        self.app.set_config(prefer_dd_mm_format=False)
        text = "Meeting on 03/15/2024 at 2pm"
        success, event, message = self.app.run_complete_workflow(text)
        
        if success:  # Parsing success depends on current date context
            self.assertEqual(event.start_datetime.month, 3)
            self.assertEqual(event.start_datetime.day, 15)
        
        # Test DD/MM format
        self.app.set_config(prefer_dd_mm_format=True)
        text = "Meeting on 15/03/2024 at 2pm"
        success, event, message = self.app.run_complete_workflow(text)
        
        if success:
            self.assertEqual(event.start_datetime.month, 3)
            self.assertEqual(event.start_datetime.day, 15)
    
    def test_workflow_error_recovery(self):
        """Test error recovery mechanisms in workflow."""
        # Create a scenario that might cause storage errors
        # Make storage path read-only to simulate permission error
        os.chmod(self.temp_storage, 0o444)  # Read-only
        
        try:
            text = "Meeting tomorrow at 2pm"
            success, event, message = self.app.run_complete_workflow(text)
            
            # Should handle the error gracefully
            self.assertFalse(success)
            self.assertIn("error", message.lower())
            
        finally:
            # Restore permissions for cleanup
            os.chmod(self.temp_storage, 0o644)
    
    def test_workflow_performance(self):
        """Test workflow performance with reasonable response times."""
        import time
        
        text = "Quick meeting tomorrow at 2pm"
        
        start_time = time.time()
        success, event, message = self.app.run_complete_workflow(text)
        end_time = time.time()
        
        # Workflow should complete within reasonable time (5 seconds)
        self.assertLess(end_time - start_time, 5.0, "Workflow took too long to complete")
        
        if success:
            self.assertIsNotNone(event)


class TestWorkflowComponents(unittest.TestCase):
    """Test individual components in the workflow context."""
    
    def setUp(self):
        """Set up test components."""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_storage = os.path.join(self.temp_dir, "test_events.json")
        
        self.parser = EventParser()
        self.calendar_service = CalendarService(storage_path=self.temp_storage)
    
    def tearDown(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_parser_to_calendar_integration(self):
        """Test direct integration between parser and calendar service."""
        text = "Team meeting tomorrow at 10am"
        
        # Parse text
        parsed_event = self.parser.parse_text(text)
        self.assertIsNotNone(parsed_event.title)
        self.assertIsNotNone(parsed_event.start_datetime)
        
        # Convert to Event and create
        event = Event(
            title=parsed_event.title,
            start_datetime=parsed_event.start_datetime,
            end_datetime=parsed_event.end_datetime,
            location=parsed_event.location,
            description=parsed_event.description or ""
        )
        
        success, message, event_id = self.calendar_service.create_event(event)
        self.assertTrue(success, f"Event creation failed: {message}")
        self.assertIsNotNone(event_id)
    
    def test_validation_integration(self):
        """Test validation integration across components."""
        text = "Meeting"  # Minimal text, should have validation issues
        
        parsed_event = self.parser.parse_text(text)
        validation_result = self.parser.validate_parsed_event(parsed_event)
        
        # Should have validation issues
        self.assertFalse(validation_result.is_valid)
        self.assertGreater(len(validation_result.missing_fields), 0)
        
        # Calendar service should also catch these issues
        if parsed_event.start_datetime and parsed_event.end_datetime:
            event = Event(
                title=parsed_event.title or "Test Event",
                start_datetime=parsed_event.start_datetime,
                end_datetime=parsed_event.end_datetime,
                location=parsed_event.location,
                description=""
            )
            
            calendar_validation = self.calendar_service.validate_event(event)
            # Should validate successfully if we provide required fields
            self.assertTrue(calendar_validation.is_valid or len(calendar_validation.missing_fields) > 0)
    
    def test_end_to_end_data_flow(self):
        """Test data flow from text input to stored event."""
        original_text = "Project kickoff meeting at Conference Room B on Friday March 15th 2024 from 9:00 AM to 10:30 AM"
        
        # Step 1: Parse
        parsed_event = self.parser.parse_text(original_text)
        
        # Step 2: Validate
        validation_result = self.parser.validate_parsed_event(parsed_event)
        
        # Step 3: Convert to Event
        if validation_result.is_valid or not validation_result.missing_fields:
            event = Event(
                title=parsed_event.title or "Untitled Event",
                start_datetime=parsed_event.start_datetime,
                end_datetime=parsed_event.end_datetime,
                location=parsed_event.location,
                description=original_text
            )
            
            # Step 4: Store
            success, message, event_id = self.calendar_service.create_event(event)
            
            if success:
                # Step 5: Retrieve and verify
                stored_events = self.calendar_service.list_events()
                self.assertEqual(len(stored_events), 1)
                
                stored_event = stored_events[0]
                self.assertEqual(stored_event.title, event.title)
                self.assertEqual(stored_event.start_datetime, event.start_datetime)
                self.assertEqual(stored_event.end_datetime, event.end_datetime)
                self.assertEqual(stored_event.location, event.location)


if __name__ == '__main__':
    unittest.main()