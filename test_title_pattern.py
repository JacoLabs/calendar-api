#!/usr/bin/env python3
"""
Test the title pattern matching
"""

import re

def test_title_patterns():
    text = "Koji's Birthday Party DATE Sun, Oct 26 2:00 PM EDT LOCATION 1980 St Clair Ave W, Toronto, ON M6N 5H3 CA. Inside Nations Experience"
    
    # Test the structured_event pattern
    structured_pattern = re.compile(
        r'^([^,\n\r\.]+?)(?:\s+(?:DATE|TIME|LOCATION|WHEN|WHERE|AT)\s)',
        re.IGNORECASE
    )
    
    match = structured_pattern.search(text)
    if match:
        print(f"Structured pattern matched: '{match.group(1)}'")
    else:
        print("Structured pattern did not match")
    
    # Test the party_celebration pattern
    party_pattern = re.compile(
        r'\b([^,\n\r\.]*(?:party|celebration|birthday|anniversary|wedding)[^,\n\r\.]*?)(?:\s+(?:DATE|TIME|LOCATION|WHEN|WHERE|AT)\s|[,\n\r\.]|$)',
        re.IGNORECASE
    )
    
    match = party_pattern.search(text)
    if match:
        print(f"Party pattern matched: '{match.group(1)}'")
    else:
        print("Party pattern did not match")

if __name__ == "__main__":
    test_title_patterns()