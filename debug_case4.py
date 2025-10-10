#!/usr/bin/env python3
"""
Debug case 4 title extraction
"""

from services.title_extractor import TitleExtractor

def debug_case4():
    text = "Doctor Appointment TIME 9:30am DATE Oct 15"
    
    extractor = TitleExtractor()
    
    print(f"Input: {text}")
    print("=" * 80)
    
    result = extractor.extract_title(text)
    print(f"Title: '{result.title}'")
    print(f"Confidence: {result.confidence}")
    print(f"Method: {result.generation_method}")
    print(f"Pattern: {result.extraction_metadata.get('pattern_type', 'N/A')}")

if __name__ == "__main__":
    debug_case4()