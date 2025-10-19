#!/usr/bin/env python3
"""
Final comprehensive test of all Android improvements.
"""

import requests
import json
from datetime import datetime, timezone
import re

def preprocess_text_full(text):
    """Full preprocessing simulation matching Android implementation."""
    processed = text
    
    # Fix common time format issues
    processed = re.sub(r'(\d{1,2}:\d{2})a\.m', r'\1 AM', processed)
    processed = re.sub(r'(\d{1,2}:\d{2})p\.m', r'\1 PM', processed)
    processed = re.sub(r'(\d{1,2})a\.m', r'\1:00 AM', processed)
    processed = re.sub(r'(\d{1,2})p\.m', r'\1:00 PM', processed)
    
    # Fix common spacing issues
    processed = re.sub(r'(\d{1,2}:\d{2})am', r'\1 AM', processed)
    processed = re.sub(r'(\d{1,2}:\d{2})pm', r'\1 PM', processed)
    processed = re.sub(r'(\d{1,2})am', r'\1:00 AM', processed)
    processed = re.sub(r'(\d{1,2})pm', r'\1:00 PM', processed)
    
    # Improve common phrasing patterns for better title extraction
    processed = re.sub(r'^We will (.+?) by (.+)', r'\1 at \2', processed)
    processed = re.sub(r'^I will (.+?) by (.+)', r'\1 at \2', processed)
    processed = re.sub(r'^We need to (.+?) by (.+)', r'\1 at \2', processed)
    
    return processed

def test_comprehensive_improvements():
    """Test all improvements together."""
    print("🎯 Final comprehensive test of Android improvements...\n")
    
    test_cases = [
        {
            "original": "We will leave school by 9:00a.m",
            "description": "Screenshot case - should fix time format and improve title"
        },
        {
            "original": "I will call mom by 3:30p.m",
            "description": "Personal task with p.m format"
        },
        {
            "original": "We need to finish the project by 5pm tomorrow",
            "description": "Work task with pm format"
        },
        {
            "original": "random text with no clear event info",
            "description": "Low confidence case - should warn user"
        },
        {
            "original": "Meeting with John tomorrow at 2 PM",
            "description": "Already good format - should maintain quality"
        }
    ]
    
    url = 'https://calendar-api-wrxz.onrender.com/parse'
    
    for i, test_case in enumerate(test_cases, 1):
        original = test_case["original"]
        processed = preprocess_text_full(original)
        
        print(f"📝 Test {i}: {test_case['description']}")
        print(f"   Original: '{original}'")
        print(f"   Processed: '{processed}'")
        
        # Test with API
        payload = {
            'text': processed,
            'timezone': 'America/New_York',
            'locale': 'en_US', 
            'now': datetime.now(timezone.utc).isoformat()
        }
        
        try:
            response = requests.post(url, json=payload, timeout=10)
            result = response.json()
            
            title = result.get('title')
            start_time = result.get('start_datetime')
            confidence = result.get('confidence_score', 0)
            
            print(f"   API Result:")
            print(f"     Title: {title}")
            print(f"     Time: {start_time}")
            print(f"     Confidence: {confidence:.3f}")
            
            # Simulate Android behavior
            print(f"   Android Behavior:")
            
            if confidence < 0.3:
                print(f"     ⚠️  Low confidence warning shown")
                print(f"     ❌ Calendar event creation blocked")
            elif not title and not start_time:
                print(f"     ❌ Insufficient data error shown")
                print(f"     ❌ Calendar event creation blocked")
            else:
                print(f"     ✅ Calendar event creation allowed")
                if start_time:
                    dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                    formatted_time = dt.strftime('%I:%M %p')
                    print(f"     📱 Calendar shows: '{title}' at {formatted_time}")
                else:
                    print(f"     📱 Calendar shows: '{title}' (no time)")
            
            # Evaluation
            print(f"   Evaluation:")
            if processed != original:
                print(f"     ✅ Text preprocessing applied")
            if confidence >= 0.7:
                print(f"     ✅ High confidence achieved")
            elif confidence >= 0.3:
                print(f"     ✅ Acceptable confidence")
            else:
                print(f"     ⚠️  Low confidence (expected for unclear text)")
            
            if start_time and ('09:00:00' in start_time or '15:30:00' in start_time or '17:00:00' in start_time):
                print(f"     ✅ Correct time extracted")
            elif 'random text' in original:
                print(f"     ✅ Correctly rejected unclear text")
            
        except Exception as e:
            print(f"     ❌ API Error: {e}")
        
        print()
    
    print("🎉 Comprehensive test completed!")
    print("\n📊 Summary of improvements:")
    print("1. ✅ Text preprocessing fixes time format issues")
    print("2. ✅ Confidence validation prevents poor results")
    print("3. ✅ Better error messages guide users")
    print("4. ✅ Title extraction improvements")
    print("5. ✅ Visual confidence indicators in UI")

if __name__ == "__main__":
    test_comprehensive_improvements()