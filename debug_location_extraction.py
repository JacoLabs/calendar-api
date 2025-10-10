#!/usr/bin/env python3
"""
Debug location extraction in detail
"""

from services.advanced_location_extractor import AdvancedLocationExtractor

def debug_location_extraction():
    text = "Koji's Birthday Party DATE Sun, Oct 26 2:00 PM EDT LOCATION 1980 St Clair Ave W, Toronto, ON M6N 5H3 CA. Inside Nations Experience"
    
    extractor = AdvancedLocationExtractor()
    
    print(f"Input: {text}")
    print("=" * 80)
    
    # Test each extraction method separately
    print("1. Explicit addresses:")
    explicit_results = extractor._extract_explicit_addresses(text)
    for i, result in enumerate(explicit_results):
        print(f"   {i+1}. '{result.location}' (confidence: {result.confidence}, method: {result.extraction_method})")
    
    print("\n2. Context locations:")
    context_results = extractor._extract_context_locations(text)
    for i, result in enumerate(context_results):
        print(f"   {i+1}. '{result.location}' (confidence: {result.confidence}, method: {result.extraction_method})")
    
    print("\n3. All locations (combined):")
    all_results = extractor.extract_locations(text)
    for i, result in enumerate(all_results):
        print(f"   {i+1}. '{result.location}' (confidence: {result.confidence}, method: {result.extraction_method})")

if __name__ == "__main__":
    debug_location_extraction()