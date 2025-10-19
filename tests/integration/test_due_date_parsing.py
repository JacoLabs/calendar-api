#!/usr/bin/env python3
"""
Test script for due date parsing enhancement.
Tests that "Due Date: Oct 15, 2025" creates an all-day event on the correct date.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.llm_service import LLMService
from datetime import datetime

def test_due_date_parsing():
    """Test that due dates are parsed as all-day events on the correct date."""
    
    # Initialize LLM service
    llm_service = LLMService()
    
    # Test cases for due date parsing
    test_cases = [
        {
            'text': 'Due Date: Oct 15, 2025',
            'expected_date': '2025-10-15',
            'expected_all_day': True,
            'description': 'Simple due date format'
        },
        {
            'text': 'Item ID: 37131076518125 Title: COWA Due Date: Oct 15, 2025',
            'expected_date': '2025-10-15', 
            'expected_all_day': True,
            'description': 'Due date with additional context (like the screenshot)'
        },
        {
            'text': 'Project deadline: December 1, 2025',
            'expected_date': '2025-12-01',
            'expected_all_day': True,
            'description': 'Deadline format'
        },
        {
            'text': 'Meeting tomorrow at 2pm',
            'expected_all_day': False,
            'description': 'Regular meeting with time (should not be all-day)'
        }
    ]
    
    print("Testing Due Date Parsing Enhancement")
    print("=" * 50)
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\nTest {i}: {test_case['description']}")
        print(f"Input: '{test_case['text']}'")
        
        try:
            # Parse the text
            parsed_event = llm_service.llm_extract_event(
                test_case['text'], 
                current_date="2025-01-01"
            )
            
            print(f"Title: {parsed_event.title}")
            print(f"Start: {parsed_event.start_datetime}")
            print(f"End: {parsed_event.end_datetime}")
            print(f"All Day: {parsed_event.all_day}")
            print(f"Confidence: {parsed_event.confidence_score:.2f}")
            
            # Check results
            if 'expected_date' in test_case:
                if parsed_event.start_datetime:
                    actual_date = parsed_event.start_datetime.date().isoformat()
                    expected_date = test_case['expected_date']
                    
                    if actual_date == expected_date:
                        print("✅ Date matches expected")
                    else:
                        print(f"❌ Date mismatch: expected {expected_date}, got {actual_date}")
                else:
                    print("❌ No start date extracted")
            
            if 'expected_all_day' in test_case:
                expected_all_day = test_case['expected_all_day']
                if parsed_event.all_day == expected_all_day:
                    print(f"✅ All-day setting correct: {parsed_event.all_day}")
                else:
                    print(f"❌ All-day mismatch: expected {expected_all_day}, got {parsed_event.all_day}")
            
            # Show extraction metadata
            if parsed_event.extraction_metadata:
                provider = parsed_event.extraction_metadata.get('llm_provider', 'unknown')
                print(f"Provider: {provider}")
                
                if 'extraction_notes' in parsed_event.extraction_metadata.get('raw_llm_response', {}):
                    notes = parsed_event.extraction_metadata['raw_llm_response']['extraction_notes']
                    print(f"Notes: {notes}")
            
        except Exception as e:
            print(f"❌ Error: {e}")
    
    print("\n" + "=" * 50)
    print("Due date parsing test completed!")

if __name__ == "__main__":
    test_due_date_parsing()