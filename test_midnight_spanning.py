#!/usr/bin/env python3
"""
Test events that span across midnight to verify duration calculations.
"""

from datetime import datetime, timedelta
from models.event_models import Event
from services.calendar_service import CalendarService


def test_midnight_spanning_events():
    """Test various events that cross midnight boundaries."""
    service = CalendarService(storage_path="test_midnight.json")
    
    print("🌙 Testing Midnight-Spanning Events")
    print("=" * 50)
    
    # Base date for testing
    base_date = datetime(2024, 12, 15)  # Use a fixed date for consistency
    
    test_cases = [
        {
            "name": "2-hour meeting crossing midnight",
            "start": base_date.replace(hour=23, minute=0),  # 11:00 PM
            "end": base_date.replace(hour=23, minute=0) + timedelta(hours=2),  # 1:00 AM next day
            "expected_hours": 2.0
        },
        {
            "name": "4-hour event crossing midnight", 
            "start": base_date.replace(hour=22, minute=0),  # 10:00 PM
            "end": base_date.replace(hour=22, minute=0) + timedelta(hours=4),  # 2:00 AM next day
            "expected_hours": 4.0
        },
        {
            "name": "24-hour event (full day)",
            "start": base_date.replace(hour=0, minute=0),  # Midnight
            "end": base_date.replace(hour=0, minute=0) + timedelta(hours=24),  # Midnight next day
            "expected_hours": 24.0
        },
        {
            "name": "25-hour event crossing midnight",
            "start": base_date.replace(hour=23, minute=0),  # 11:00 PM
            "end": base_date.replace(hour=23, minute=0) + timedelta(hours=25),  # Midnight + 1 hour (day after next)
            "expected_hours": 25.0
        },
        {
            "name": "Same day event (no midnight crossing)",
            "start": base_date.replace(hour=14, minute=0),  # 2:00 PM
            "end": base_date.replace(hour=16, minute=0),    # 4:00 PM same day
            "expected_hours": 2.0
        },
        {
            "name": "Multi-day event (48 hours)",
            "start": base_date.replace(hour=12, minute=0),  # Noon
            "end": base_date.replace(hour=12, minute=0) + timedelta(hours=48),  # Noon 2 days later
            "expected_hours": 48.0
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{i}. {test_case['name']}")
        print("-" * 40)
        
        event = Event(
            title=f"Test Event {i}",
            start_datetime=test_case['start'],
            end_datetime=test_case['end'],
            description=f"Testing midnight spanning: {test_case['name']}"
        )
        
        # Show the actual dates and times
        print(f"Start: {event.start_datetime.strftime('%Y-%m-%d %H:%M:%S (%A)')}")
        print(f"End:   {event.end_datetime.strftime('%Y-%m-%d %H:%M:%S (%A)')}")
        
        # Calculate duration using our method
        duration_delta = event.end_datetime - event.start_datetime
        duration_hours = duration_delta.total_seconds() / 3600
        
        print(f"Duration Delta: {duration_delta}")
        print(f"Calculated Hours: {duration_hours:.2f}")
        print(f"Expected Hours: {test_case['expected_hours']:.2f}")
        
        # Check if calculation is correct
        if abs(duration_hours - test_case['expected_hours']) < 0.01:
            print("✅ Duration calculation correct")
        else:
            print(f"❌ Duration calculation incorrect! Difference: {duration_hours - test_case['expected_hours']:.2f} hours")
        
        # Test validation
        result = service.validate_event(event)
        duration_warnings = [w for w in result.warnings if "duration" in w.lower()]
        
        should_warn = duration_hours > 24.0
        has_warning = len(duration_warnings) > 0
        
        print(f"Should warn (>24h): {should_warn}")
        print(f"Has warning: {has_warning}")
        
        if duration_warnings:
            print(f"Warning message: {duration_warnings[0]}")
        
        if should_warn == has_warning:
            print("✅ Warning logic correct")
        else:
            print("❌ Warning logic incorrect")
        
        # Also test the Event model's duration_minutes method
        event_duration_minutes = event.duration_minutes()
        expected_minutes = test_case['expected_hours'] * 60
        print(f"Event.duration_minutes(): {event_duration_minutes}")
        print(f"Expected minutes: {expected_minutes}")
        
        if abs(event_duration_minutes - expected_minutes) < 1:  # Allow 1 minute tolerance
            print("✅ Event.duration_minutes() correct")
        else:
            print("❌ Event.duration_minutes() incorrect")


if __name__ == "__main__":
    test_midnight_spanning_events()