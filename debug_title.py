#!/usr/bin/env python3
"""
Debug script to test title extraction specifically.
"""

import re

def test_title():
    text = "Appointment with Dr. Smith at 3pm"
    
    # Test the appointment pattern
    appointment_pattern = re.compile(r'\b(?:appointment|appt)\s+(?:with|for|at)\s+([^,\n!?]+?)(?:\s+(?:tomorrow|today|yesterday|at\s+\d+(?::\d+)?(?:am|pm)?|on\s+\w+)|\s*$)', re.IGNORECASE)
    
    print(f"Text: {text}")
    print(f"Pattern: {appointment_pattern.pattern}")
    
    matches = appointment_pattern.finditer(text)
    for match in matches:
        print(f"Found: '{match.group(1)}' at position {match.start(1)}-{match.end(1)}")
        print(f"Full match: '{match.group(0)}'")

if __name__ == "__main__":
    test_title()