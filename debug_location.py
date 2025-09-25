#!/usr/bin/env python3
"""
Debug script to test location extraction specifically.
"""

import re

def test_location():
    text = "Hi team, let's schedule our 'Q4 Planning Review' for next Friday at 2:30pm in the main conference room."
    
    # Test the 'in' pattern
    in_pattern = re.compile(r'\bin\s+((?:the\s+)?[^,\n!?;]+?)(?:\s+(?:tomorrow|today|yesterday|on\s+\w+|at\s+\d+:\d+|for\s+\d+)|[.!?]|\s*$)', re.IGNORECASE)
    
    print(f"Text: {text}")
    print(f"Pattern: {in_pattern.pattern}")
    
    matches = in_pattern.finditer(text)
    for match in matches:
        print(f"Found: '{match.group(1)}' at position {match.start(1)}-{match.end(1)}")
        print(f"Full match: '{match.group(0)}'")

if __name__ == "__main__":
    test_location()