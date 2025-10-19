#!/usr/bin/env python3
"""
Test script for Canadian context extraction.
"""

from services.event_extractor import EventInformationExtractor

def test_canadian_extraction():
    extractor = EventInformationExtractor()
    
    # Acceptance check test case
    test_text = "Meet at 123 Main St, Toronto, M5V 3L9 tomorrow at 2pm"
    
    print(f"Testing: {test_text}")
    print("=" * 60)
    
    # Test comprehensive extraction
    result = extractor.extract_all_information(test_text)
    
    print(f"Best title: '{result['best_title']}'")
    print(f"Best location: '{result['best_location']}'")
    print(f"Title confidence: {result['title_confidence']:.2f}")
    print(f"Location confidence: {result['location_confidence']:.2f}")
    print()
    
    # Show all title matches
    print("All title matches:")
    for i, title_info in enumerate(result['titles'][:3]):
        print(f"  {i+1}. '{title_info['value']}' (confidence: {title_info['confidence']:.2f}, type: {title_info['extraction_type']})")
    
    print()
    
    # Show all location matches
    print("All location matches:")
    for i, location_info in enumerate(result['locations'][:3]):
        print(f"  {i+1}. '{location_info['value']}' (confidence: {location_info['confidence']:.2f}, type: {location_info['extraction_type']})")
    
    print()
    
    # Additional Canadian test cases
    canadian_test_cases = [
        "Meeting at Kensington Market tomorrow",
        "Lunch at Starbucks on Queen Street West",
        "Conference at 100 University Ave, Toronto, ON M5J 1V6",
        "Event in Vancouver, BC V6B 2W9",
        "Appointment at Tim Hortons downtown",
        "Workshop at CN Tower, Toronto"
    ]
    
    print("Additional Canadian test cases:")
    print("=" * 60)
    
    for test_case in canadian_test_cases:
        print(f"\nTesting: {test_case}")
        result = extractor.extract_all_information(test_case)
        print(f"  Title: '{result['best_title']}' (conf: {result['title_confidence']:.2f})")
        print(f"  Location: '{result['best_location']}' (conf: {result['location_confidence']:.2f})")

if __name__ == "__main__":
    test_canadian_extraction()