#!/usr/bin/env python3
"""
Test the multiline preprocessing fix.
"""

import requests
import json
from datetime import datetime, timezone
import re

def enhance_single_line_title(text):
    """Simulate the enhanceSingleLineTitle function."""
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

def enhance_title_extraction_multiline(text):
    """Simulate the new multiline-aware title extraction."""
    enhanced = text
    
    # For multi-line text, process each line separately then recombine
    if '\n' in enhanced:
        lines = enhanced.split('\n')
        processed_lines = []
        for line in lines:
            processed_line = enhance_single_line_title(line.strip())
            if processed_line:
                processed_lines.append(processed_line)
        enhanced = '\n'.join(processed_lines)
    else:
        enhanced = enhance_single_line_title(enhanced)
    
    return enhanced

def test_multiline_fix():
    """Test the multiline preprocessing fix."""
    print("🔧 Testing Multiline Preprocessing Fix")
    print("=" * 50)
    
    test_cases = [
        {
            "name": "Single line (should work)",
            "text": "On Monday the elementary students will attend the Indigenous Legacy Gathering"
        },
        {
            "name": "Multi-line merged text (the problem case)",
            "text": "On Monday the elementary students will attend the Indigenous Legacy Gathering\nWe will leave school by 9:00 AM."
        },
        {
            "name": "Multi-line with location",
            "text": "On Monday the elementary students will attend the Indigenous Legacy Gathering\nNathan Phillips Square\nWe will leave school by 9:00 AM."
        }
    ]
    
    for case in test_cases:
        print(f"\n📝 {case['name']}:")
        print(f"   Original: '{case['text']}'")
        
        # Apply new multiline preprocessing
        processed = enhance_title_extraction_multiline(case['text'])
        print(f"   Processed: '{processed}'")
        
        # Test with API
        result = parse_text(processed)
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
        
        if is_good_title:
            print(f"   🎉 SUCCESS: Multiline preprocessing fixed the title!")

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
    test_multiline_fix()