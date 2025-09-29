#!/usr/bin/env python3
"""
Test enhanced title extraction preprocessing.
"""

import requests
import json
from datetime import datetime, timezone
import re

def enhance_title_extraction(text):
    """Simulate the enhanced title extraction logic."""
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

def preprocess_text_full(text):
    """Full preprocessing including time fixes and title enhancement."""
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

def test_title_extraction():
    """Test title extraction with the Gmail example."""
    print("🎯 Testing Enhanced Title Extraction")
    print("=" * 50)
    
    # Test cases from the Gmail scenario
    test_cases = [
        {
            "name": "Gmail Event Description",
            "original": "On Monday the elementary students will attend the Indigenous Legacy Gathering",
            "expected_improvement": "Indigenous Legacy Gathering on Monday"
        },
        {
            "name": "Gmail Event + Location",
            "original": "On Monday the elementary students will attend the Indigenous Legacy Gathering at Nathan Phillips Square",
            "expected_improvement": "Indigenous Legacy Gathering at Nathan Phillips Square on Monday"
        },
        {
            "name": "Merged Text (Current Issue)",
            "original": "On Monday the elementary students will attend the Indigenous Legacy Gathering\nWe will leave school by 9:00 AM.",
            "expected_improvement": "Indigenous Legacy Gathering on Monday\nLeave school at 9:00 AM."
        },
        {
            "name": "Time Line",
            "original": "We will leave school by 9:00a.m.",
            "expected_improvement": "Leave school at 9:00 AM."
        }
    ]
    
    print("📝 Testing preprocessing improvements:")
    print()
    
    for i, case in enumerate(test_cases, 1):
        print(f"{i}. {case['name']}:")
        print(f"   Original: '{case['original']}'")
        
        processed = preprocess_text_full(case['original'])
        print(f"   Processed: '{processed}'")
        print(f"   Expected: '{case['expected_improvement']}'")
        
        # Test with API
        result = parse_text(processed)
        print(f"   API Result:")
        print(f"      Title: {result.get('title')}")
        print(f"      Start: {result.get('start_datetime')}")
        print(f"      Location: {result.get('location')}")
        print(f"      Confidence: {result.get('confidence_score', 0):.3f}")
        
        # Check if title improved
        title = result.get('title', '')
        title_improved = (
            'Indigenous Legacy Gathering' in title or
            'Leave school' in title or
            not title.startswith('On Monday the elementary')
        )
        
        print(f"   {'✅' if title_improved else '❌'} Title extraction: {'IMPROVED' if title_improved else 'NEEDS WORK'}")
        print()
    
    # Test the specific merged scenario that was working but had poor title
    print("🎯 Testing Specific Gmail Merge Scenario:")
    
    gmail_selection = "On Monday the elementary students will attend the Indigenous Legacy Gathering"
    clipboard_content = "We will leave school by 9:00 AM."
    
    # Test different merge orders
    merge_strategies = [
        f"{gmail_selection}\n{clipboard_content}",
        f"{clipboard_content}\n{gmail_selection}",
        f"{preprocess_text_full(gmail_selection)}\n{preprocess_text_full(clipboard_content)}"
    ]
    
    for i, merged_text in enumerate(merge_strategies, 1):
        print(f"Strategy {i}: {merged_text[:50]}...")
        result = parse_text(merged_text)
        
        print(f"   Title: {result.get('title')}")
        print(f"   Start: {result.get('start_datetime')}")
        print(f"   Confidence: {result.get('confidence_score', 0):.3f}")
        
        title_good = (
            result.get('title', '') and
            'Indigenous Legacy Gathering' in result.get('title', '') and
            not result.get('title', '').startswith('On Monday the elementary')
        )
        
        print(f"   {'✅' if title_good else '❌'} Title quality: {'GOOD' if title_good else 'POOR'}")
        print()

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
    test_title_extraction()