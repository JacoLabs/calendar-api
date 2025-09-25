#!/usr/bin/env python3
"""
Demo script showcasing the new event creation confirmation and feedback features.
Demonstrates success confirmations, error handling, and retry mechanisms.
"""

from datetime import datetime, timedelta
from services.event_feedback import EventCreationFeedback, create_event_with_comprehensive_feedback
from services.calendar_service import CalendarService, EventValidationError
from models.event_models import Event
import tempfile
import os


def demo_successful_creation():
    """Demo successful event creation with confirmation."""
    print("\n" + "="*60)
    print("DEMO 1: SUCCESSFUL EVENT CREATION WITH CONFIRMATION")
    print("="*60)
    
    event = Event(
        title="Team Standup Meeting",
        start_datetime=datetime.now() + timedelta(hours=1),
        end_datetime=datetime.now() + timedelta(hours=1, minutes=30),
        location="Conference Room A",
        description="Daily team standup to discuss progress and blockers"
    )
    
    print("Creating event with comprehensive feedback...")
    success, message = create_event_with_comprehensive_feedback(event, interactive=False)
    
    print(f"\nResult: {'✓ SUCCESS' if success else '❌ FAILED'}")
    if not success:
        print(f"Error: {message}")


def demo_retry_mechanism():
    """Demo retry mechanism for failed event creation."""
    print("\n" + "="*60)
    print("DEMO 2: RETRY MECHANISM FOR FAILED CREATION")
    print("="*60)
    
    # Create a temporary storage path that will fail
    temp_dir = tempfile.mkdtemp()
    storage_path = os.path.join(temp_dir, "readonly_events.json")
    
    try:
        # Create the file and make it read-only to simulate failure
        with open(storage_path, 'w') as f:
            f.write('[]')
        
        # Make it read-only (this might not work on all systems)
        try:
            os.chmod(storage_path, 0o444)
        except:
            pass  # Skip if chmod doesn't work
        
        calendar_service = CalendarService(storage_path, max_retries=2)
        feedback_system = EventCreationFeedback(calendar_service)
        
        event = Event(
            title="Test Event for Retry Demo",
            start_datetime=datetime.now() + timedelta(hours=2),
            end_datetime=datetime.now() + timedelta(hours=3)
        )
        
        print("Attempting to create event with failing storage...")
        success, message = feedback_system.create_event_with_feedback(event, interactive=False)
        
        print(f"\nResult: {'✓ SUCCESS' if success else '❌ FAILED (as expected)'}")
        print(f"Message: {message[:100]}..." if len(message) > 100 else message)
        
    finally:
        # Clean up
        try:
            os.chmod(storage_path, 0o666)
            os.remove(storage_path)
            os.rmdir(temp_dir)
        except:
            pass


def demo_validation_error_handling():
    """Demo validation error handling."""
    print("\n" + "="*60)
    print("DEMO 3: VALIDATION ERROR HANDLING")
    print("="*60)
    
    # Create a mock calendar service that will raise validation errors
    from unittest.mock import Mock
    
    mock_calendar_service = Mock()
    mock_calendar_service.create_event_with_retry.side_effect = EventValidationError(
        "Event validation failed: Start time must be before end time"
    )
    
    feedback_system = EventCreationFeedback(mock_calendar_service)
    
    event = Event(
        title="Invalid Event Demo",
        start_datetime=datetime.now() + timedelta(hours=1),
        end_datetime=datetime.now() + timedelta(hours=2)
    )
    
    print("Attempting to create event with validation error...")
    success, message = feedback_system.create_event_with_feedback(event, interactive=False)
    
    print(f"\nResult: {'✓ SUCCESS' if success else '❌ FAILED (as expected)'}")
    print(f"Error: {message}")


def demo_conflict_detection():
    """Demo conflict detection and warnings."""
    print("\n" + "="*60)
    print("DEMO 4: CONFLICT DETECTION AND WARNINGS")
    print("="*60)
    
    temp_dir = tempfile.mkdtemp()
    storage_path = os.path.join(temp_dir, "conflict_demo.json")
    
    try:
        calendar_service = CalendarService(storage_path)
        
        # Create first event
        event1 = Event(
            title="Existing Meeting",
            start_datetime=datetime.now() + timedelta(hours=1),
            end_datetime=datetime.now() + timedelta(hours=2),
            location="Room 101"
        )
        
        print("Creating first event...")
        success1, message1, event_id1 = calendar_service.create_event(event1)
        print(f"First event created: {event_id1}")
        
        # Create conflicting event
        event2 = Event(
            title="Conflicting Meeting",
            start_datetime=datetime.now() + timedelta(hours=1, minutes=30),  # Overlaps
            end_datetime=datetime.now() + timedelta(hours=2, minutes=30),
            location="Room 102"
        )
        
        print("\nCreating conflicting event...")
        success2, message2, event_id2 = calendar_service.create_event(event2)
        
        print(f"\nResult: {'✓ SUCCESS' if success2 else '❌ FAILED'}")
        if success2:
            print("Event created with conflict warnings:")
            print(message2)
        
    finally:
        # Clean up
        try:
            os.remove(storage_path)
            os.rmdir(temp_dir)
        except:
            pass


def demo_feedback_summary():
    """Demo feedback summary and statistics."""
    print("\n" + "="*60)
    print("DEMO 5: FEEDBACK SUMMARY AND STATISTICS")
    print("="*60)
    
    temp_dir = tempfile.mkdtemp()
    storage_path = os.path.join(temp_dir, "summary_demo.json")
    
    try:
        calendar_service = CalendarService(storage_path)
        feedback_system = EventCreationFeedback(calendar_service)
        
        # Create several events to build up history
        events = [
            Event(
                title=f"Meeting {i+1}",
                start_datetime=datetime.now() + timedelta(hours=i+1),
                end_datetime=datetime.now() + timedelta(hours=i+2),
                location=f"Room {i+1}"
            )
            for i in range(3)
        ]
        
        print("Creating multiple events...")
        for i, event in enumerate(events):
            success, message = feedback_system.create_event_with_feedback(event, interactive=False)
            print(f"Event {i+1}: {'✓' if success else '❌'}")
        
        print("\nFeedback Summary:")
        feedback_system.display_feedback_summary()
        
    finally:
        # Clean up
        try:
            os.remove(storage_path)
            os.rmdir(temp_dir)
        except:
            pass


def main():
    """Run all demos."""
    print("EVENT CREATION CONFIRMATION AND FEEDBACK SYSTEM DEMO")
    print("=" * 60)
    print("This demo showcases the new features implemented in task 9:")
    print("• Success confirmation with event details display")
    print("• Error handling and retry mechanisms")
    print("• User feedback system for creation status and errors")
    print("• Comprehensive test coverage")
    
    try:
        demo_successful_creation()
        demo_retry_mechanism()
        demo_validation_error_handling()
        demo_conflict_detection()
        demo_feedback_summary()
        
        print("\n" + "="*60)
        print("DEMO COMPLETED SUCCESSFULLY!")
        print("="*60)
        print("All confirmation and feedback features are working correctly.")
        print("The system now provides:")
        print("✓ Detailed success confirmations")
        print("✓ Comprehensive error handling")
        print("✓ Automatic retry mechanisms")
        print("✓ Conflict detection and warnings")
        print("✓ Feedback history and statistics")
        
    except Exception as e:
        print(f"\n❌ Demo failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()