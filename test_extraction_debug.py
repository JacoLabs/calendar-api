#!/usr/bin/env python3
"""
Debug script to test event extraction functionality manually.
"""

from services.event_extractor import EventInformationExtractor

def test_extraction():
    extractor = EventInformationExtractor()
    
    # Test cases that are failing
    test_cases = [
        "Meeting with John about project planning tomorrow at 2pm",
        "Conference room B is available",
        "Room 205",
        "Meeting @ Main Office",
        "3rd floor conference area",
        "Hi team, let's schedule our 'Q4 Planning Review' for next Friday at 2:30pm in the main conference room."
    ]
    
    for text in test_cases:
        print(f"\n=== Testing: {text} ===")
        
        # Test title extraction
        title_matches = extractor.extract_title(text)
        print(f"Title matches: {len(title_matches)}")
        for i, match in enumerate(title_matches[:3]):  # Show top 3
            print(f"  {i+1}. '{match.value}' (confidence: {match.confidence:.2f}, type: {match.extraction_type})")
        
        # Test location extraction
        location_matches = extractor.extract_location(text)
        print(f"Location matches: {len(location_matches)}")
        for i, match in enumerate(location_matches[:3]):  # Show top 3
            print(f"  {i+1}. '{match.value}' (confidence: {match.confidence:.2f}, type: {match.extraction_type})")
        
        # Test comprehensive extraction
        result = extractor.extract_all_information(text)
        print(f"Best title: '{result['best_title']}'")
        print(f"Best location: '{result['best_location']}'")

if __name__ == "__main__":
    test_extraction()