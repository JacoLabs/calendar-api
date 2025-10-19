#!/usr/bin/env python3
"""
Test script to debug API parsing issues.
"""

import requests
import json
from datetime import datetime, timezone

def test_api_parsing():
    url = 'https://calendar-api-wrxz.onrender.com/parse'
    
    test_cases = [
        'We will leave school by 9:00a.m',
        'We will leave school by 9:00 AM',
        'We will leave school at 9:00 AM',
        'Leave school at 9:00 AM',
        'School departure at 9:00 AM',
        'Meeting tomorrow at 2pm',  # Known working case
        'Lunch at The Keg next Friday 12:30'  # Another known case
    ]
    
    print("🧪 Testing API parsing with various text formats...\n")
    
    for text in test_cases:
        payload = {
            'text': text,
            'timezone': 'America/New_York',
            'locale': 'en_US', 
            'now': datetime.now(timezone.utc).isoformat()
        }
        
        try:
            response = requests.post(url, json=payload, timeout=10)
            result = response.json()
            
            print(f'📝 Text: "{text}"')
            print(f'   Title: {result.get("title")}')
            print(f'   Start: {result.get("start_datetime")}')
            print(f'   End: {result.get("end_datetime")}')
            print(f'   Location: {result.get("location")}')
            print(f'   Confidence: {result.get("confidence_score", 0):.3f}')
            print(f'   All Day: {result.get("all_day")}')
            print()
            
        except Exception as e:
            print(f'❌ Error with "{text}": {e}')
            print()

if __name__ == "__main__":
    test_api_parsing()