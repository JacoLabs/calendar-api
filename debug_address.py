#!/usr/bin/env python3
"""
Debug script for address extraction issue.
"""

import re

def debug_address():
    text = "Meet at 123 Main St, Toronto, M5V 3L9"
    
    # Test the street address pattern
    street_pattern = re.compile(r'\b(\d+\s+[A-Za-z\s]+(?:street|st|avenue|ave|road|rd|drive|dr|lane|ln|boulevard|blvd|way|place|pl|court|ct|crescent|cres|circle|circ)(?:,\s*[A-Za-z\s]+)*(?:,\s*[A-Za-z]\d[A-Za-z]\s+\d[A-Za-z]\d)?)', re.IGNORECASE)
    
    print(f"Text: {text}")
    print(f"Pattern: {street_pattern.pattern}")
    
    matches = street_pattern.finditer(text)
    for match in matches:
        print(f"Found: '{match.group(1)}' at position {match.start(1)}-{match.end(1)}")
        print(f"Full match: '{match.group(0)}'")

if __name__ == "__main__":
    debug_address()