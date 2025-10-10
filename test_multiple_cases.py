#!/usr/bin/env python3
"""
Test multiple structured text cases
"""

from services.hybrid_event_parser import HybridEventParser
from datetime import datetime

def test_multiple_cases():
    current_time = datetime(2025, 10, 10, 14, 0, 0)
    parser = HybridEventParser(current_time=current_time)
    
    test_cases = [
        "Koji's Birthday Party DATE Sun, Oct 26 2:00 PM EDT LOCATION 1980 St Clair Ave W, Toronto, ON M6N 5H3 CA. Inside Nations Experience",
        "Team Meeting DATE Tomorrow TIME 2pm LOCATION Conference Room A",
        "Company Retreat LOCATION Beach Resort DATE Next Friday",
        "Doctor Appointment TIME 9:30am DATE Oct 15",
        "Wedding Celebration DATE Saturday LOCATION Church"
    ]
    
    for i, text in enumerate(test_cases, 1):
        print(f"\n{i}. Testing: {text}")
        print("-" * 80)
        
        result = parser.parse_event_text(text, mode="hybrid")
        
        print(f"Title: '{result.parsed_event.title}'")
        print(f"Date: {result.parsed_event.start_datetime}")
        print(f"Location: '{result.parsed_event.location}'")
        print(f"Confidence: {result.confidence_score:.2f}")

if __name__ == "__main__":
    test_multiple_cases()