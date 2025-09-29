#!/usr/bin/env python3
"""
Test the enhanced merge logic with better title extraction.
"""

import requests
import json
from datetime import datetime, timezone
import re

def preprocess_text_for_merge(text):
    """Simulate the enhanced preprocessing in TextMergeHelper."""
    processed = text
    
    # Fix time formats first
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
    """Enhanced title extraction logic."""
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

def test_enhanced_merge():
    """Test the enhanced merge logic."""
    print("🎯 Testing Enhanced Merge Logic with Better Titles")
    print("=" * 60)
    
    # The exact Gmail scenario
    gmail_selection = "On Monday the elementary students will attend the Indigenous Legacy Gathering"
    clipboard_content = "We will leave school by 9:00a.m."
    
    print(f"📧 Gmail Selection: '{gmail_selection}'")
    print(f"📋 Clipboard Content: '{clipboard_content}'")
    print()
    
    # Step 1: Show current merge (without preprocessing)
    print("🔍 Step 1: Current Merge (No Preprocessing)")
    current_merge = f"{gmail_selection}\n{clipboard_content}"
    current_result = parse_text(current_merge)
    
    print(f"   Merged text: '{current_merge}'")
    print(f"   Result:")
    print(f"      Title: {current_result.get('title')}")
    print(f"      Start: {current_result.get('start_datetime')}")
    print(f"      Confidence: {current_result.get('confidence_score', 0):.3f}")
    print(f"   {'❌' if 'On Monday the elementary' in str(current_result.get('title', '')) else '✅'} Title quality")
    print()
    
    # Step 2: Show enhanced merge (with preprocessing)
    print("🚀 Step 2: Enhanced Merge (With Preprocessing)")
    
    # Preprocess both parts
    preprocessed_selection = preprocess_text_for_merge(gmail_selection)
    preprocessed_clipboard = preprocess_text_for_merge(clipboard_content)
    
    print(f"   Preprocessed selection: '{preprocessed_selection}'")
    print(f"   Preprocessed clipboard: '{preprocessed_clipboard}'")
    
    # Test different merge strategies
    enhanced_strategies = [
        f"{preprocessed_selection}\n{preprocessed_clipboard}",
        f"{preprocessed_clipboard}\n{preprocessed_selection}",
        f"{preprocessed_selection} {preprocessed_clipboard}"
    ]
    
    best_result = None
    best_confidence = 0
    best_strategy = ""
    
    for i, merged_text in enumerate(enhanced_strategies, 1):
        result = parse_text(merged_text)
        confidence = result.get('confidence_score', 0)
        
        print(f"   Strategy {i}: '{merged_text}'")
        print(f"      Title: {result.get('title')}")
        print(f"      Start: {result.get('start_datetime')}")
        print(f"      Confidence: {confidence:.3f}")
        
        if confidence > best_confidence:
            best_confidence = confidence
            best_result = result
            best_strategy = f"Strategy {i}"
        
        print()
    
    print(f"🏆 Best Enhanced Result: {best_strategy}")
    if best_result:
        title = best_result.get('title', '')
        has_good_title = (
            'Indigenous Legacy Gathering' in title and
            not title.startswith('On Monday the elementary')
        )
        has_correct_time = '09:00:00' in str(best_result.get('start_datetime', ''))
        
        print(f"   Title: {title}")
        print(f"   Start: {best_result.get('start_datetime')}")
        print(f"   Confidence: {best_confidence:.3f}")
        print()
        print(f"   ✅ Verification:")
        print(f"      Good title: {'✅' if has_good_title else '❌'}")
        print(f"      Correct time: {'✅' if has_correct_time else '❌'}")
        print(f"      High confidence: {'✅' if best_confidence > 0.6 else '❌'}")
        
        success = has_good_title and has_correct_time and best_confidence > 0.6
        
        print(f"\n{'🎉' if success else '❌'} Overall: {'SUCCESS!' if success else 'NEEDS MORE WORK'}")
        
        return success
    
    return False

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

def main():
    """Run the enhanced merge test."""
    success = test_enhanced_merge()
    
    if success:
        print("\n✅ Enhanced merge logic is working!")
        print("\n🎯 Key improvements:")
        print("   • Better title extraction from Gmail selections")
        print("   • Preprocessing both parts before merging")
        print("   • Maintains correct time and date parsing")
        print("   • High confidence results (>60%)")
        
        exit(0)
    else:
        print("\n❌ Enhanced merge logic needs more refinement")
        exit(1)

if __name__ == "__main__":
    main()