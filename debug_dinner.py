#!/usr/bin/env python3
"""
Debug script for dinner extraction issue.
"""

from services.event_extractor import EventInformationExtractor

def debug_dinner():
    extractor = EventInformationExtractor()
    text = "Dinner at 7pm @ Starbucks"
    
    print(f"Testing: {text}")
    print("=" * 40)
    
    # Test title extraction
    title_matches = extractor.extract_title(text)
    print("Title matches:")
    for i, match in enumerate(title_matches):
        print(f"  {i+1}. '{match.value}' (conf: {match.confidence:.2f}, type: {match.extraction_type})")
    
    print()
    
    # Test location extraction
    location_matches = extractor.extract_location(text)
    print("Location matches:")
    for i, match in enumerate(location_matches):
        print(f"  {i+1}. '{match.value}' (conf: {match.confidence:.2f}, type: {match.extraction_type})")

if __name__ == "__main__":
    debug_dinner()