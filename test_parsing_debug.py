#!/usr/bin/env python3
"""
Debug the parsing issues with date and location extraction
"""

from services.hybrid_event_parser import HybridEventParser
from datetime import datetime
import json

def test_parsing_debug():
    # Set current time to a known date for testing
    current_time = datetime(2025, 10, 10, 14, 0, 0)  # Oct 10, 2025, 2 PM
    parser = HybridEventParser(current_time=current_time)
    
    test_text = "Koji's Birthday Party DATE Sun, Oct 26 2:00 PM EDT LOCATION 1980 St Clair Ave W, Toronto, ON M6N 5H3 CA. Inside Nations Experience"
    
    print(f"Testing: {test_text}")
    print("=" * 80)
    
    result = parser.parse_event_text(test_text, mode="hybrid")
    
    print(f"Title: {result.parsed_event.title}")
    print(f"Start DateTime: {result.parsed_event.start_datetime}")
    print(f"End DateTime: {result.parsed_event.end_datetime}")
    print(f"Location: {result.parsed_event.location}")
    print(f"All Day: {result.parsed_event.all_day}")
    print(f"Confidence: {result.confidence_score}")
    print(f"Parsing Path: {result.parsing_path}")
    print(f"Warnings: {result.warnings}")
    
    print("\nProcessing Metadata:")
    print(json.dumps(result.processing_metadata, indent=2, default=str))

if __name__ == "__main__":
    test_parsing_debug()