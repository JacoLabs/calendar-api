#!/usr/bin/env python3
"""
Test structured title extraction
"""

from services.title_extractor import TitleExtractor

def test_structured_extraction():
    extractor = TitleExtractor()
    
    test_cases = [
        "Koji's Birthday Party DATE Sun, Oct 26 2:00 PM EDT LOCATION 1980 St Clair Ave W, Toronto, ON M6N 5H3 CA. Inside Nations Experience",
        "Team Meeting DATE Tomorrow TIME 2pm LOCATION Conference Room A",
        "Company Retreat LOCATION Beach Resort DATE Next Friday",
        "Doctor Appointment TIME 9:30am DATE Oct 15",
        "Wedding Celebration DATE Saturday LOCATION Church"
    ]
    
    for text in test_cases:
        result = extractor.extract_title(text)
        print(f"Text: '{text[:60]}...'")
        print(f"Extracted title: '{result.title}'")
        print(f"Confidence: {result.confidence}")
        print(f"Method: {result.generation_method}")
        print("-" * 70)

if __name__ == "__main__":
    test_structured_extraction()