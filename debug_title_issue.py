#!/usr/bin/env python3
"""
Debug the specific title extraction issue that's still happening.
"""

import requests
import json
from datetime import datetime, timezone
import re

def simulate_android_preprocessing(text):
    """Simulate the exact preprocessing that happens in Android ApiService."""
    processed = text
    
    # Fix time formats
    processed = re.sub(r'(\d{1,2}:\d{2})a\.m', r'\1 AM', processed)
    processed = re.sub(r'(\d{1,2}:\d{2})p\.m', r'\1 PM', processed)
    processed = re.sub(r'(\d{1,2})a\.m', r'\1:00 AM', processed)
    processed = re.sub(r'(\d{1,2})p\.m', r'\1:00 PM', processed)
    processed = re.sub(r'(\d{1,2}:\d{2})am', r'\1 AM', processed)
    processed = re.sub(r'(\d{1,2}:\d{2})pm', r'\1 PM', processed)
    processed = re.sub(r'(\d{1,2})am', r'\1:00 AM', processed)
    processed = re.sub(r'(\d{1,2})pm', r'\1:00 PM', processed)
    
    # Common phrasing improvements
    processed = re.sub(r'^We will (.+?) by (.+)', r'\1 at \2', processed)
    processed = re.sub(r'^I will (.+?) by (.+)', r'\1 at \2', processed)
    processed = re.sub(r'^We need to (.+?) by (.+)', r'\1 at \2', processed)
    
    # Enhanced title extraction
    processed = enhance_title_extraction(processed)
    
    return processed

def enhance_title_extraction(text):
    """Simulate the enhanceTitleExtraction function."""
    enhanced = text
    
    # Pattern 1: "On [day] the [people] will attend [EVENT]" -> "[EVENT] on [day]"
    enhanced = re.sub(
        r'^On (\w+day) the .+? will attend (.+?)(?:\s+at\s+(.+?))?(?:\.|$)',
        r'\2 on \1',
        enhanced,
        flags=re.IGNORECASE
    )
    
    # Pattern 2: "On [day] the [people] will [action] the [EVENT]" -> "[EVENT] on [day]"
    enhanced = re.sub(
        r'^On (\w+day) the .+? will \w+ the (.+?)(?:\s+at\s+(.+?))?(?:\.|$)',
        r'\2 on \1',
        enhanced,
        flags=re.IGNORECASE
    )
    
    # Pattern 3: Extract event name from "attend [EVENT] at [LOCATION]"
    enhanced = re.sub(
        r'attend (.+?) at (.+?)(?:\.|$)',
        r'\1 at \2',
        enhanced,
        flags=re.IGNORECASE
    )
    
    # Pattern 4: Extract event name from "will attend [EVENT]"
    def replace_will_attend(match):
        event = match.group(1)
        location = match.group(2) if len(match.groups()) > 1 and match.group(2) else ""
        return f"{event} at {location}" if location else event
    
    enhanced = re.sub(
        r'will attend (.+?)(?:\s+at\s+(.+?))?(?:\.|$)',
        replace_will_attend,
        enhanced,
        flags=re.IGNORECASE
    )
    
    # Pattern 5: Clean up common prefixes
    enhanced = re.sub(r'^(On \w+day )?the (students?|children|kids) will ', '', enhanced, flags=re.IGNORECASE)
    enhanced = re.sub(r'^(We|I) will ', '', enhanced, flags=re.IGNORECASE)
    
    # Pattern 6: Capitalize and clean up
    enhanced = enhanced.strip()
    if enhanced:
        enhanced = enhanced[0].upper() + enhanced[1:]
    
    return enhanced

def debug_title_extraction():
    """Debug the exact issue with title extraction."""
    print("🐛 Debugging Title Extraction Issue")
    print("=" * 50)
    
    # The problematic text combinations
    test_cases = [
        {
            "name": "Single Gmail selection (problematic)",
            "text": "On Monday the elementary students will attend the Indigenous Legacy Gathering"
        },
        {
            "name": "Merged text (still problematic?)",
            "text": "On Monday the elementary students will attend the Indigenous Legacy Gathering\nWe will leave school by 9:00 AM."
        },
        {
            "name": "Preprocessed single selection",
            "text": None  # Will be set by preprocessing
        },
        {
            "name": "Preprocessed merged text",
            "text": None  # Will be set by preprocessing
        }
    ]
    
    # Set preprocessed versions
    test_cases[2]["text"] = simulate_android_preprocessing(test_cases[0]["text"])
    test_cases[3]["text"] = simulate_android_preprocessing(test_cases[1]["text"])
    
    for case in test_cases:
        print(f"\n📝 {case['name']}:")
        print(f"   Input: '{case['text']}'")
        
        # Test with API
        result = parse_text(case['text'])
        title = result.get('title', '')
        
        print(f"   API Result:")
        print(f"      Title: '{title}'")
        print(f"      Start: {result.get('start_datetime')}")
        print(f"      Confidence: {result.get('confidence_score', 0):.3f}")
        
        # Check if title is good
        is_good_title = (
            'Indigenous Legacy Gathering' in title and
            not title.startswith('On Monday the elementary')
        )
        
        print(f"   {'✅' if is_good_title else '❌'} Title quality: {'GOOD' if is_good_title else 'POOR'}")
        
        if not is_good_title and 'On Monday the elementary' in title:
            print(f"   🔍 Issue: API is still returning truncated title despite preprocessing")
    
    # Test individual preprocessing steps
    print(f"\n🔧 Step-by-step preprocessing debug:")
    original = "On Monday the elementary students will attend the Indigenous Legacy Gathering"
    
    print(f"   Original: '{original}'")
    
    # Test each pattern individually
    patterns = [
        (r'^On (\w+day) the .+? will attend (.+?)(?:\s+at\s+(.+?))?(?:\.|$)', r'\2 on \1', "Pattern 1"),
        (r'^On (\w+day) the .+? will \w+ the (.+?)(?:\s+at\s+(.+?))?(?:\.|$)', r'\2 on \1', "Pattern 2"),
        (r'^(On \w+day )?the (students?|children|kids) will ', '', "Pattern 5a"),
        (r'^(We|I) will ', '', "Pattern 5b")
    ]
    
    current = original
    for pattern, replacement, name in patterns:
        before = current
        current = re.sub(pattern, replacement, current, flags=re.IGNORECASE)
        if before != current:
            print(f"   {name}: '{before}' → '{current}'")
        else:
            print(f"   {name}: No match")
    
    print(f"   Final preprocessed: '{current}'")
    
    # Test the final preprocessed version
    final_result = parse_text(current)
    final_title = final_result.get('title', '')
    print(f"   Final API result: '{final_title}'")
    
    if 'Indigenous Legacy Gathering' in final_title:
        print(f"   ✅ Preprocessing IS working - the issue might be elsewhere")
    else:
        print(f"   ❌ Preprocessing NOT working - need to fix the patterns")

def parse_text(text):
    """Parse text using the API."""
    url = 'https://calendar-api-wrxz.onrender.com/parse'
    payload = {
        'text': text,
        'timezone': 'America/New_York',
        'locale': 'en_US', 
        'now': datetime.now(timezone.utc).isoformat()
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        return response.json()
    except Exception as e:
        return {'error': str(e), 'confidence_score': 0}

if __name__ == "__main__":
    debug_title_extraction()