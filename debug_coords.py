#!/usr/bin/env python3
"""
Debug script to test coordinates pattern specifically.
"""

import re

def test_coords():
    text = "Coordinates: 40.7128, -74.0060"
    
    # Test both patterns
    coord_keyword_pattern = re.compile(r'\bcoordinates:?\s*([^,\n.!?;]+)', re.IGNORECASE)
    coord_pattern = re.compile(r'(-?\d+\.\d+,\s*-?\d+\.\d+)')
    coord_keyword_pattern2 = re.compile(r'\bcoordinates:?\s*(-?\d+\.\d+,\s*-?\d+\.\d+)', re.IGNORECASE)
    
    print(f"Text: {text}")
    print()
    
    print("Keyword pattern:")
    matches = coord_keyword_pattern.finditer(text)
    for match in matches:
        print(f"  Found: '{match.group(1)}' at position {match.start(1)}-{match.end(1)}")
    
    print("Number pattern:")
    matches = coord_pattern.finditer(text)
    for match in matches:
        print(f"  Found: '{match.group(1)}' at position {match.start(1)}-{match.end(1)}")

if __name__ == "__main__":
    test_coords()