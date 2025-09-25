#!/usr/bin/env python3
"""
Debug script for address combination issue.
"""

from services.event_extractor import EventInformationExtractor

def debug_combination():
    extractor = EventInformationExtractor()
    text = "Meet at 123 Main St, Toronto, M5V 3L9"
    
    print(f"Testing: {text}")
    print("=" * 50)
    
    # Test location extraction
    location_matches = extractor.extract_location(text)
    print("Final location matches:")
    for i, match in enumerate(location_matches):
        print(f"  {i+1}. '{match.value}' (conf: {match.confidence:.2f}, type: {match.extraction_type})")
        print(f"      Position: {match.start_pos}-{match.end_pos}")
        print(f"      Keywords: {match.keywords_used}")
    
    print()
    
    # Test individual patterns
    import re
    street_pattern = re.compile(r'\b(\d+\s+[A-Za-z\s]+(?:street|st|avenue|ave|road|rd|drive|dr|lane|ln|boulevard|blvd|way|place|pl|court|ct|crescent|cres|circle|circ)(?:,\s*[A-Za-z\s]+)*(?:,\s*[A-Za-z]\d[A-Za-z]\s*\d[A-Za-z]\d)?)', re.IGNORECASE)
    postal_pattern = re.compile(r'\b([A-Za-z]\d[A-Za-z]\s*\d[A-Za-z]\d)\b')
    
    print("Street pattern matches:")
    for match in street_pattern.finditer(text):
        print(f"  '{match.group(1)}' at {match.start(1)}-{match.end(1)}")
    
    print("Postal pattern matches:")
    for match in postal_pattern.finditer(text):
        print(f"  '{match.group(1)}' at {match.start(1)}-{match.end(1)}")

if __name__ == "__main__":
    debug_combination()