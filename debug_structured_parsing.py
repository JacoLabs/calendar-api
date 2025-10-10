#!/usr/bin/env python3
"""
Debug structured text parsing issues
"""

from services.title_extractor import TitleExtractor
from services.advanced_location_extractor import AdvancedLocationExtractor
from services.regex_date_extractor import RegexDateExtractor
from datetime import datetime

def debug_structured_parsing():
    test_text = "Koji's Birthday Party DATE Sun, Oct 26 2:00 PM EDT LOCATION 1980 St Clair Ave W, Toronto, ON M6N 5H3 CA. Inside Nations Experience"
    
    print(f"Input: {test_text}")
    print("=" * 80)
    
    # Test title extraction
    title_extractor = TitleExtractor()
    title_result = title_extractor.extract_title(test_text)
    print(f"Title: '{title_result.title}'")
    print(f"Title Confidence: {title_result.confidence}")
    print(f"Title Method: {title_result.generation_method}")
    print()
    
    # Test location extraction
    location_extractor = AdvancedLocationExtractor()
    location_results = location_extractor.extract_locations(test_text)
    print(f"Location Results: {len(location_results)}")
    for i, loc in enumerate(location_results):
        print(f"  {i+1}. '{loc.location}' (confidence: {loc.confidence}, method: {loc.extraction_method})")
    print()
    
    # Test date extraction
    current_time = datetime(2025, 10, 10, 14, 0, 0)
    date_extractor = RegexDateExtractor(current_time=current_time)
    date_result = date_extractor.extract_datetime(test_text)
    print(f"Date Start: {date_result.start_datetime}")
    print(f"Date End: {date_result.end_datetime}")
    print(f"Date Confidence: {date_result.confidence}")
    print(f"Date Method: {date_result.extraction_method}")
    print(f"Date Pattern: {date_result.pattern_type}")

if __name__ == "__main__":
    debug_structured_parsing()