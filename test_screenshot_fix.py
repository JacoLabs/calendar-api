#!/usr/bin/env python3
"""
Test the specific case from the screenshot to verify it's fixed.
"""

import requests
import json
from datetime import datetime, timezone
import re

def preprocess_text(text):
    """Simulate the Android preprocessing."""
    processed = text
    processed = re.sub(r'(\d{1,2}:\d{2})a\.m', r'\1 AM', processed)
    processed = re.sub(r'(\d{1,2}:\d{2})p\.m', r'\1 PM', processed)
    processed = re.sub(r'(\d{1,2})a\.m', r'\1:00 AM', processed)
    processed = re.sub(r'(\d{1,2})p\.m', r'\1:00 PM', processed)
    processed = re.sub(r'(\d{1,2}:\d{2})am', r'\1 AM', processed)
    processed = re.sub(r'(\d{1,2}:\d{2})pm', r'\1 PM', processed)
    processed = re.sub(r'(\d{1,2})am', r'\1:00 AM', processed)
    processed = re.sub(r'(\d{1,2})pm', r'\1:00 PM', processed)
    return processed

def main():
    print("🔍 Testing the specific screenshot case...\n")
    
    # Test the exact text from the screenshot
    original_text = 'We will leave school by 9:00a.m'
    processed_text = preprocess_text(original_text)
    
    print(f'📝 Original text: "{original_text}"')
    print(f'🔧 Processed text: "{processed_text}"')
    print()
    
    url = 'https://calendar-api-wrxz.onrender.com/parse'
    payload = {
        'text': processed_text,
        'timezone': 'America/New_York',
        'locale': 'en_US', 
        'now': datetime.now(timezone.utc).isoformat()
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        result = response.json()
        
        print("📊 API Response:")
        print(f"   Title: {result.get('title')}")
        print(f"   Start: {result.get('start_datetime')}")
        print(f"   End: {result.get('end_datetime')}")
        print(f"   Confidence: {result.get('confidence_score', 0):.3f}")
        print()
        
        if result.get('start_datetime'):
            dt = datetime.fromisoformat(result['start_datetime'].replace('Z', '+00:00'))
            print(f"📅 Formatted time: {dt.strftime('%a, %b %d, %Y at %I:%M %p')}")
            print()
        
        # Simulate Android validation
        confidence = result.get('confidence_score', 0)
        title = result.get('title')
        start_time = result.get('start_datetime')
        
        print("🤖 Android App Behavior:")
        
        if confidence < 0.3:
            print("   ⚠️  Would show low confidence warning")
            print("   ❌ Would NOT create calendar event")
        elif not title and not start_time:
            print("   ❌ Would show insufficient data error")
            print("   ❌ Would NOT create calendar event")
        else:
            print("   ✅ Would allow creating calendar event")
            print(f"   📱 Calendar would show: '{title}' at {dt.strftime('%I:%M %p') if start_time else 'No time'}")
        
        print()
        print("🎯 Summary:")
        if processed_text != original_text:
            print("   ✅ Text preprocessing FIXED the format issue")
        if confidence >= 0.7:
            print("   ✅ High confidence parsing achieved")
        if start_time and '09:00:00' in start_time:
            print("   ✅ Correct time (9:00 AM) extracted")
        else:
            print("   ❌ Time extraction issue")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()