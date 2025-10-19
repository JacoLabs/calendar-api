#!/usr/bin/env python3
"""
Test preprocessing effectiveness.
"""

import requests
import json
from datetime import datetime, timezone

def test_preprocessing():
    url = 'https://calendar-api-wrxz.onrender.com/parse'
    
    test_cases = [
        {
            "original": "We will leave school by 9:00a.m.",
            "processed": "We will leave school by 9:00 AM."
        },
        {
            "original": "On Monday the elementary students will attend the Indigenous Legacy Gathering",
            "processed": "On Monday the elementary students will attend the Indigenous Legacy Gathering"
        },
        {
            "original": "On Monday the elementary students will attend the Indigenous Legacy Gathering\nWe will leave school by 9:00 AM.",
            "processed": "On Monday the elementary students will attend the Indigenous Legacy Gathering\nWe will leave school by 9:00 AM."
        }
    ]
    
    for i, case in enumerate(test_cases, 1):
        print(f"Test {i}:")
        print(f"  Text: '{case['processed']}'")
        
        payload = {
            'text': case['processed'],
            'timezone': 'America/New_York',
            'locale': 'en_US', 
            'now': datetime.now(timezone.utc).isoformat()
        }
        
        try:
            response = requests.post(url, json=payload, timeout=10)
            result = response.json()
            
            print(f"  Title: {result.get('title')}")
            print(f"  Start: {result.get('start_datetime')}")
            print(f"  Location: {result.get('location')}")
            print(f"  Confidence: {result.get('confidence_score', 0):.3f}")
            
        except Exception as e:
            print(f"  Error: {e}")
        
        print()

if __name__ == "__main__":
    test_preprocessing()