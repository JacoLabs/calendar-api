#!/usr/bin/env python3
"""
Test script to verify the exact 24-hour boundary for duration validation.
"""

from datetime import datetime, timedelta
from models.event_models import Event
from services.calendar_service import CalendarService


def test_boundary_cases():
    """Test edge cases around the 24-hour boundary."""
    service = CalendarService(storage_path="test_boundary.json")
    
    print("🎯 Testing 24-Hour Boundary Cases")
    print("=" * 50)
    
    base_start = datetime.now() + timedelta(days=1)
    
    # Test cases around the 24-hour boundary
    test_durations = [
        23.9,   # Just under 24 hours
        23.99,  # Very close to 24 hours
        24.0,   # Exactly 24 hours
        24.01,  # Just over 24 hours
        24.1    # Clearly over 24 hours
    ]
    
    for i, duration_hours in enumerate(test_durations, 1):
        print(f"\n{i}. Testing {duration_hours} hours")
        print("-" * 30)
        
        start_time = base_start + timedelta(hours=i)
        end_time = start_time + timedelta(hours=duration_hours)
        
        event = Event(
            title=f"Boundary Test {i}",
            start_datetime=start_time,
            end_datetime=end_time
        )
        
        result = service.validate_event(event)
        
        # Calculate actual duration
        actual_duration = (event.end_datetime - event.start_datetime).total_seconds() / 3600
        
        # Check for duration warnings
        duration_warnings = [w for w in result.warnings if "duration" in w.lower()]
        
        print(f"Requested: {duration_hours} hours")
        print(f"Actual: {actual_duration:.6f} hours")
        print(f"Warning: {'Yes' if duration_warnings else 'No'}")
        
        if duration_warnings:
            print(f"Message: {duration_warnings[0]}")
        
        # Determine if this should have a warning (> 24 hours)
        should_warn = actual_duration > 24.0
        has_warning = len(duration_warnings) > 0
        
        if should_warn == has_warning:
            print("✅ Correct behavior")
        else:
            print(f"❌ Incorrect! Should warn: {should_warn}, Has warning: {has_warning}")


if __name__ == "__main__":
    test_boundary_cases()