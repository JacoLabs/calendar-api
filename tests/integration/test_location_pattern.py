#!/usr/bin/env python3
"""
Test the location pattern matching
"""

import re

def test_location_patterns():
    text = "Koji's Birthday Party DATE Sun, Oct 26 2:00 PM EDT LOCATION 1980 St Clair Ave W, Toronto, ON M6N 5H3 CA. Inside Nations Experience"
    
    # Test the location_colon pattern
    location_pattern = re.compile(r'\blocation:?\s*([^,\n.!?;]+)', re.IGNORECASE)
    
    match = location_pattern.search(text)
    if match:
        print(f"Location pattern matched: '{match.group(1)}'")
        print(f"Full match: '{match.group(0)}'")
    else:
        print("Location pattern did not match")
    
    # Test a better pattern that captures more
    better_pattern = re.compile(r'\blocation:?\s*([^,\n]+(?:,[^,\n]+)*(?:\.[^,\n]+)*)', re.IGNORECASE)
    
    match = better_pattern.search(text)
    if match:
        print(f"Better pattern matched: '{match.group(1)}'")
    else:
        print("Better pattern did not match")
    
    # Test an even better pattern
    full_pattern = re.compile(r'\blocation:?\s*(.+?)(?=\s*$)', re.IGNORECASE)
    
    match = full_pattern.search(text)
    if match:
        print(f"Full pattern matched: '{match.group(1)}'")
    else:
        print("Full pattern did not match")

if __name__ == "__main__":
    test_location_patterns()