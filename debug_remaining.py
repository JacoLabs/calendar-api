#!/usr/bin/env python3
"""
Debug script to test remaining failing cases.
"""

from services.event_extractor import EventInformationExtractor

def test_remaining():
    extractor = EventInformationExtractor()
    
    test_cases = [
        "Meeting in Building C",
        "Coordinates: 40.7128, -74.0060"
    ]
    
    for text in test_cases:
        print(f"\n=== Testing: {text} ===")
        
        # Test location extraction
        location_matches = extractor.extract_location(text)
        print(f"Location matches: {len(location_matches)}")
        for i, match in enumerate(location_matches):
            print(f"  {i+1}. '{match.value}' (confidence: {match.confidence:.2f}, type: {match.extraction_type}, keywords: {match.keywords_used})")

if __name__ == "__main__":
    test_remaining()