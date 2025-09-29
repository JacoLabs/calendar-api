#!/usr/bin/env python3
"""
Debug the time parsing issue seen in the Android screenshot.
"""

import requests
import json
from datetime import datetime, timezone

def debug_time_parsing():
    url = 'https://calendar-api-wrxz.onrender.com/parse'
    
    # Test cases that might explain the 9:30 PM issue
    test_cases = [
        'We will leave school by 9:00a.m',
        'We will leave school by 9:30a.m',  # Maybe they typed 9:30?
        'We will leave school by 9:00 pm',  # Maybe AM/PM got confused?
        'We will leave school by 21:00',    # 24-hour format?
        'We will leave school by 9:30 PM',  # Direct PM test
        'We will leave school by 21:30',    # 9:30 PM in 24-hour
    ]
    
    print("🔍 Debugging time parsing issue...\n")
    
    for text in test_cases:
        payload = {
            'text': text,
            'timezone': 'America/New_York',  # Eastern time like in screenshot
            'locale': 'en_US', 
            'now': datetime.now(timezone.utc).isoformat()
        }
        
        try:
            response = requests.post(url, json=payload, timeout=10)
            result = response.json()
            
            print(f'📝 Text: "{text}"')
            print(f'   Start: {result.get("start_datetime")}')
            print(f'   End: {result.get("end_datetime")}')
            print(f'   Confidence: {result.get("confidence_score", 0):.3f}')
            
            # If we got a time, let's see what it converts to
            if result.get("start_datetime"):
                try:
                    dt = datetime.fromisoformat(result["start_datetime"].replace('Z', '+00:00'))
                    print(f'   Converted: {dt.strftime("%a, %b %d, %Y at %I:%M %p")}')
                except:
                    print(f'   Conversion failed')
            print()
            
        except Exception as e:
            print(f'❌ Error with "{text}": {e}')
            print()

    # Also test the current time to see if there's a timezone issue
    print("🕐 Current time info:")
    now = datetime.now(timezone.utc)
    print(f"   UTC: {now}")
    print(f"   Eastern: {now.astimezone(timezone.utc).replace(tzinfo=timezone.utc).astimezone()}")

if __name__ == "__main__":
    debug_time_parsing()