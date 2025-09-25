#!/usr/bin/env python3
"""
Recreate the exact demo scenario to verify the 25-hour warning.
"""

from datetime import datetime, timedelta
from models.event_models import Event
from services.calendar_service import CalendarService


def test_demo_scenario():
    """Recreate the exact scenario from the demo."""
    service = CalendarService(storage_path="test_demo.json")
    
    print("🎬 Recreating Demo Scenario")
    print("=" * 50)
    
    # This is the exact event from the demo
    test_event = Event(
        title="Very Long Meeting",
        start_datetime=datetime.now() + timedelta(days=1),
        end_datetime=datetime.now() + timedelta(days=2, hours=1),  # 25 hours long
        description="This is a very long meeting for demonstration"
    )
    
    print(f"Event: {test_event.title}")
    print(f"Start: {test_event.start_datetime.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"End: {test_event.end_datetime.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Calculate duration manually
    duration = test_event.end_datetime - test_event.start_datetime
    duration_hours = duration.total_seconds() / 3600
    print(f"Duration: {duration_hours} hours ({duration})")
    
    # Validate the event
    validation_result = service.validate_event(test_event)
    
    print(f"\nValidation Results:")
    print(f"Valid: {validation_result.is_valid}")
    
    if validation_result.warnings:
        print("Warnings:")
        for warning in validation_result.warnings:
            print(f"  ⚠️  {warning}")
    else:
        print("Warnings: None")
    
    if validation_result.suggestions:
        print("Suggestions:")
        for suggestion in validation_result.suggestions:
            print(f"  💡 {suggestion}")
    
    # Verify this matches what we expect
    expected_duration = 25.0  # 1 day + 1 hour = 25 hours
    if abs(duration_hours - expected_duration) < 0.01:  # Allow for small floating point differences
        print(f"\n✅ Duration calculation correct: {duration_hours} hours")
    else:
        print(f"\n❌ Duration calculation incorrect: Expected ~{expected_duration}, got {duration_hours}")
    
    # Check if warning is present
    duration_warnings = [w for w in validation_result.warnings if "duration" in w.lower()]
    if duration_warnings:
        print(f"✅ Duration warning correctly triggered: {duration_warnings[0]}")
    else:
        print("❌ Duration warning missing!")


if __name__ == "__main__":
    test_demo_scenario()