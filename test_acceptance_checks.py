#!/usr/bin/env python3
"""
Test script for acceptance checks with Canadian context focus.
"""

from services.event_extractor import EventInformationExtractor

def test_acceptance_checks():
    extractor = EventInformationExtractor()
    
    # Acceptance check test cases
    test_cases = [
        {
            'text': 'Dinner at 7pm @ Starbucks',
            'expected_title': 'Dinner',
            'expected_location': 'Starbucks',
            'description': 'Free-form place name with @ symbol'
        },
        {
            'text': 'Meet at 123 Main St, Toronto, M5V 3L9',
            'expected_title': 'Meet',
            'expected_location': '123 Main St, Toronto, M5V 3L9',
            'description': 'Full Canadian address with postal code'
        },
        {
            'text': 'Coordinates 43.6532, -79.3832 at 7pm',
            'expected_title': None,  # Should extract something, but not coordinates
            'expected_location': None,  # Should NOT extract coordinates
            'description': 'Coordinates should be ignored'
        }
    ]
    
    print("Acceptance Check Results:")
    print("=" * 60)
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{i}. {test_case['description']}")
        print(f"   Input: '{test_case['text']}'")
        
        result = extractor.extract_all_information(test_case['text'])
        
        print(f"   Title: '{result['best_title']}' (confidence: {result['title_confidence']:.2f})")
        print(f"   Location: '{result['best_location']}' (confidence: {result['location_confidence']:.2f})")
        
        # Check expectations
        title_ok = True
        location_ok = True
        
        if test_case['expected_title']:
            title_ok = result['best_title'] and test_case['expected_title'].lower() in result['best_title'].lower()
            print(f"   Title Check: {'✅ PASS' if title_ok else '❌ FAIL'}")
        
        if test_case['expected_location']:
            location_ok = result['best_location'] and test_case['expected_location'].lower() in result['best_location'].lower()
            print(f"   Location Check: {'✅ PASS' if location_ok else '❌ FAIL'}")
        elif test_case['expected_location'] is None:
            location_ok = result['best_location'] is None
            print(f"   Location Check (should be None): {'✅ PASS' if location_ok else '❌ FAIL'}")
        
        overall = title_ok and location_ok
        print(f"   Overall: {'✅ PASS' if overall else '❌ FAIL'}")
    
    # Additional Canadian context tests
    print("\n\nAdditional Canadian Context Tests:")
    print("=" * 60)
    
    canadian_tests = [
        "Meeting at Kensington Market tomorrow",
        "Lunch at Tim Hortons downtown",
        "Conference at CN Tower, Toronto",
        "Event in Vancouver, BC V6B 2W9",
        "Workshop at 100 University Ave, Toronto, ON M5J 1V6",
        "Appointment at Shoppers Drug Mart",
        "Call at Second Cup on Queen Street"
    ]
    
    for test_text in canadian_tests:
        print(f"\nTesting: {test_text}")
        result = extractor.extract_all_information(test_text)
        print(f"  Title: '{result['best_title']}' (conf: {result['title_confidence']:.2f})")
        print(f"  Location: '{result['best_location']}' (conf: {result['location_confidence']:.2f})")
        
        # Show all location matches to verify no coordinates are extracted
        if result['locations']:
            print(f"  All locations: {[loc['value'] for loc in result['locations']]}")

if __name__ == "__main__":
    test_acceptance_checks()