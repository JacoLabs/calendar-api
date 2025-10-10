#!/usr/bin/env python3
"""
Debug case 5 location extraction
"""

from services.advanced_location_extractor import AdvancedLocationExtractor

def debug_case5():
    text = "Wedding Celebration DATE Saturday LOCATION Church"
    
    extractor = AdvancedLocationExtractor()
    
    print(f"Input: {text}")
    print("=" * 80)
    
    # Test context locations
    context_results = extractor._extract_context_locations(text)
    print("Context locations:")
    for i, result in enumerate(context_results):
        print(f"   {i+1}. '{result.location}' (confidence: {result.confidence}, method: {result.extraction_method})")
    
    # Test all locations
    all_results = extractor.extract_locations(text)
    print("\nAll locations:")
    for i, result in enumerate(all_results):
        print(f"   {i+1}. '{result.location}' (confidence: {result.confidence}, method: {result.extraction_method})")

if __name__ == "__main__":
    debug_case5()