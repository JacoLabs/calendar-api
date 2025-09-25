#!/usr/bin/env python3
"""
Test script to verify duration validation is working correctly.
"""

from datetime import datetime, timedelta
from models.event_models import Event
from services.calendar_service import CalendarService


def test_duration_validation():
    """Test various event durations to ensure validation works correctly."""
    service = CalendarService(storage_path="test_duration.json")
    
    print("🕐 Testing Event Duration Validation")
    print("=" * 50)
    
    # Test cases with different durations
    test_cases = [
        {
            "name": "Normal 1-hour meeting",
            "duration_hours": 1,
            "expected_warning": False
        },
        {
            "name": "Half-day event (4 hours)",
            "duration_hours": 4,
            "expected_warning": False
        },
        {
            "name": "Full day event (8 hours)",
            "duration_hours": 8,
            "expected_warning": False
        },
        {
            "name": "Long day event (12 hours)",
            "duration_hours": 12,
            "expected_warning": False
        },
        {
            "name": "24-hour event (exactly)",
            "duration_hours": 24,
            "expected_warning": False
        },
        {
            "name": "25-hour event (over limit)",
            "duration_hours": 25,
            "expected_warning": True
        },
        {
            "name": "48-hour event (2 days)",
            "duration_hours": 48,
            "expected_warning": True
        },
        {
            "name": "30-minute meeting",
            "duration_hours": 0.5,
            "expected_warning": False
        }
    ]
    
    base_start = datetime.now() + timedelta(days=1)
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{i}. {test_case['name']}")
        print("-" * 30)
        
        # Create event with specified duration
        start_time = base_start + timedelta(hours=i)  # Offset to avoid conflicts
        end_time = start_time + timedelta(hours=test_case['duration_hours'])
        
        event = Event(
            title=f"Test Event {i}",
            start_datetime=start_time,
            end_datetime=end_time,
            description=f"Duration test: {test_case['duration_hours']} hours"
        )
        
        # Validate the event
        result = service.validate_event(event)
        
        # Calculate actual duration
        actual_duration = (event.end_datetime - event.start_datetime).total_seconds() / 3600
        
        print(f"Duration: {actual_duration:.1f} hours")
        print(f"Valid: {result.is_valid}")
        
        # Check for duration warnings
        duration_warnings = [w for w in result.warnings if "duration" in w.lower()]
        has_duration_warning = len(duration_warnings) > 0
        
        if duration_warnings:
            print(f"Duration Warning: {duration_warnings[0]}")
        else:
            print("Duration Warning: None")
        
        # Verify expectation
        if has_duration_warning == test_case['expected_warning']:
            print("✅ Expected result")
        else:
            print(f"❌ Unexpected result! Expected warning: {test_case['expected_warning']}, Got warning: {has_duration_warning}")
        
        # Show all warnings if any
        if result.warnings and not duration_warnings:
            print(f"Other warnings: {', '.join(result.warnings)}")
    
    print("\n" + "=" * 50)
    print("Duration validation test completed!")


if __name__ == "__main__":
    test_duration_validation()