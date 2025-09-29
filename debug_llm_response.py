#!/usr/bin/env python3
"""
Debug LLM response to see what's actually being returned.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import requests
import json

def debug_raw_llm_response():
    """Test raw LLM response to see what's happening."""
    
    test_cases = [
        'Due Date: Oct 15, 2025',
        'Item ID: 37131076518125 Title: COWA Due Date: Oct 15, 2025'
    ]
    
    system_prompt = """You are an expert calendar event extraction system. Your job is to extract structured event information from natural language text.

Extract the following information when present:
- title: The event name or description
- start_datetime: Date and time when the event starts (ISO format: YYYY-MM-DDTHH:MM:SS)
- end_datetime: Date and time when the event ends (if specified or can be inferred)
- location: Where the event takes place (optional)
- description: Additional details about the event
- all_day: Whether this is an all-day event (boolean)

IMPORTANT RULES:
1. Always respond with valid JSON
2. Use null for missing information
3. For dates without year, assume current year (2025)
4. For times without date, look for date context in the text
5. If only start time is given, estimate reasonable end time based on event type
6. Provide confidence scores (0.0-1.0) for each extracted field
7. Handle typos and variations in date/time formats (9a.m, 9am, 9:00 A M)
8. When text contains "Title: [NAME]", use [NAME] as the event title, not "Due Date"

CRITICAL ALL-DAY EVENT RULES:
8. If text contains "due date", "deadline", "expires", "ends on" with ONLY a date (no time), create an ALL-DAY event on that date
9. If text has a date but NO time context, default to ALL-DAY event rather than assuming a time
10. For all-day events, ALWAYS extract the actual date and set start_datetime to the date at 00:00:00 and end_datetime to the next day at 00:00:00
11. Set all_day: true for events that should be all-day
12. NEVER leave start_datetime as null if a date is mentioned - always extract and format the date as ISO datetime

Response format:
{
  "title": "string or null",
  "start_datetime": "ISO datetime string or null", 
  "end_datetime": "ISO datetime string or null",
  "location": "string or null",
  "description": "string or null",
  "all_day": true/false,
  "confidence": {
    "title": 0.0-1.0,
    "start_datetime": 0.0-1.0,
    "end_datetime": 0.0-1.0,
    "location": 0.0-1.0,
    "overall": 0.0-1.0
  },
  "extraction_notes": "brief explanation of extraction decisions"
}"""
    
    for i, text in enumerate(test_cases, 1):
        print(f"\n{'='*60}")
        print(f"Test {i}: {text}")
        print('='*60)
        
        user_prompt = f"""Extract calendar event information from this text:

"{text}"

Current date context: 2025-01-01
Additional context: No additional context

EXAMPLES:
- For "Due Date: Oct 15, 2025" return: {{"title": "Due Date", "start_datetime": "2025-10-15T00:00:00", "end_datetime": "2025-10-16T00:00:00", "all_day": true}}
- For "Title: COWA Due Date: Oct 15, 2025" return: {{"title": "COWA", "start_datetime": "2025-10-15T00:00:00", "end_datetime": "2025-10-16T00:00:00", "all_day": true}}"""
        
        full_prompt = f"{system_prompt}\n\n{user_prompt}\n\nResponse:"
        
        try:
            response = requests.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": "llama3.2:3b",
                    "prompt": full_prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.1,
                        "num_predict": 800,
                        "top_p": 0.9
                    }
                },
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                raw_response = result['response']
                
                print("Raw LLM Response:")
                print("-" * 40)
                print(raw_response)
                print("-" * 40)
                
                # Try to parse as JSON
                try:
                    parsed_json = json.loads(raw_response)
                    print("\n✅ Successfully parsed as JSON:")
                    print(json.dumps(parsed_json, indent=2))
                    
                    # Check specific fields
                    print(f"\nField Analysis:")
                    print(f"Title: {parsed_json.get('title')}")
                    print(f"Start DateTime: {parsed_json.get('start_datetime')}")
                    print(f"All Day: {parsed_json.get('all_day')}")
                    print(f"Overall Confidence: {parsed_json.get('confidence', {}).get('overall')}")
                    
                except json.JSONDecodeError as e:
                    print(f"\n❌ JSON Parse Error: {e}")
                    
                    # Try to extract JSON from the response
                    import re
                    json_pattern = r'\{.*\}'
                    matches = re.findall(json_pattern, raw_response, re.DOTALL)
                    
                    if matches:
                        print(f"\nFound {len(matches)} potential JSON blocks:")
                        for j, match in enumerate(matches):
                            print(f"\nJSON Block {j+1}:")
                            print(match)
                            try:
                                parsed = json.loads(match)
                                print("✅ This block parses successfully!")
                                print(json.dumps(parsed, indent=2))
                            except:
                                print("❌ This block doesn't parse")
                    else:
                        print("No JSON blocks found in response")
                        
            else:
                print(f"❌ API Error: {response.status_code}")
                print(response.text)
                
        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    debug_raw_llm_response()