#!/usr/bin/env python3
"""
Debug script to test datetime parsing with the pottery camp email text.
"""

import os
import sys
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.datetime_parser import DateTimeParser
from services.event_parser import EventParser


def test_datetime_parsing():
    """Test datetime parsing with the pottery camp email."""
    
    print("🔍 Debugging DateTime Parsing")
    print("=" * 40)
    
    # The actual text from the email
    email_text = """Adult Winter Pottery Camp
Date: January 5th to 9th, 2026
Time: 9am to 12pm
Cost: $470 plus taxes (includes materials and firing)"""
    
    print(f"Email text:\n{email_text}\n")
    
    # Test datetime parser directly
    datetime_parser = DateTimeParser()
    
    print("🔍 Testing DateTimeParser directly:")
    datetime_matches = datetime_parser.extract_datetime(email_text)
    
    if datetime_matches:
        print(f"Found {len(datetime_matches)} datetime matches:")
        for i, match in enumerate(datetime_matches):
            print(f"  {i+1}. {match.value} (confidence: {match.confidence:.2f})")
            print(f"      Pattern: {match.pattern_type}")
            print(f"      Matched text: '{match.matched_text}'")
            print(f"      Position: {match.start_pos}-{match.end_pos}")
    else:
        print("❌ No datetime matches found!")
    
    print("\n" + "=" * 40)
    
    # Test duration extraction
    print("🔍 Testing Duration extraction:")
    duration_matches = datetime_parser.extract_durations(email_text)
    
    if duration_matches:
        print(f"Found {len(duration_matches)} duration matches:")
        for i, match in enumerate(duration_matches):
            print(f"  {i+1}. {match.duration} (confidence: {match.confidence:.2f})")
            print(f"      Pattern: {match.pattern_type}")
            print(f"      Matched text: '{match.matched_text}'")
    else:
        print("❌ No duration matches found!")
    
    print("\n" + "=" * 40)
    
    # Test full event parser
    print("🔍 Testing EventParser:")
    event_parser = EventParser()
    parsed_event = event_parser.parse_text(email_text)
    
    print(f"Title: {parsed_event.title}")
    print(f"Start: {parsed_event.start_datetime}")
    print(f"End: {parsed_event.end_datetime}")
    print(f"Location: {parsed_event.location}")
    print(f"Confidence: {parsed_event.confidence_score:.2f}")
    
    # Show metadata
    if parsed_event.extraction_metadata:
        metadata = parsed_event.extraction_metadata
        print(f"\nMetadata:")
        print(f"  DateTime matches found: {metadata.get('datetime_matches_found', 0)}")
        print(f"  DateTime confidence: {metadata.get('datetime_confidence', 0):.2f}")
        print(f"  DateTime pattern: {metadata.get('datetime_pattern_type', 'None')}")
        print(f"  DateTime matched text: '{metadata.get('datetime_matched_text', 'None')}'")
    
    print("\n" + "=" * 40)
    
    # Test individual components
    print("🔍 Testing individual date/time components:")
    
    test_strings = [
        "January 5th to 9th, 2026",
        "January 5th, 2026",
        "9am to 12pm",
        "9am",
        "12pm",
        "Date: January 5th to 9th, 2026",
        "Time: 9am to 12pm"
    ]
    
    for test_str in test_strings:
        print(f"\nTesting: '{test_str}'")
        matches = datetime_parser.extract_datetime(test_str)
        if matches:
            for match in matches:
                print(f"  → {match.value} ({match.pattern_type}, {match.confidence:.2f})")
        else:
            print("  → No matches")


if __name__ == "__main__":
    test_datetime_parsing()