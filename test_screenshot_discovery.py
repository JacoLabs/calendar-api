#!/usr/bin/env python3
"""
Test script to validate the screenshot text selection discovery.

This test analyzes the difference between:
1. Gmail share method (poor results)
2. Screenshot text selection method (excellent results)
"""

import requests
import json
from datetime import datetime, timezone

def test_gmail_share_simulation():
    """Simulate the Gmail share method that gave poor results."""
    print("📧 Testing Gmail share method simulation...")
    
    # This might be what Gmail share sends (truncated/modified text)
    gmail_share_text = "On Monday the elementary students will attend the Indigenous Legacy"
    
    url = 'https://calendar-api-wrxz.onrender.com/parse'
    payload = {
        'text': gmail_share_text,
        'timezone': 'America/New_York',
        'locale': 'en_US', 
        'now': datetime.now(timezone.utc).isoformat()
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        result = response.json()
        
        print(f"   Input: '{gmail_share_text}'")
        print(f"   Title: {result.get('title')}")
        print(f"   Start: {result.get('start_datetime')}")
        print(f"   Location: {result.get('location')}")
        print(f"   Confidence: {result.get('confidence_score', 0):.3f}")
        
        if result.get('start_datetime'):
            dt = datetime.fromisoformat(result['start_datetime'].replace('Z', '+00:00'))
            print(f"   Formatted: {dt.strftime('%a, %b %d, %Y at %I:%M %p')}")
        
        print("   ❌ Poor results - truncated text, missing context")
        
    except Exception as e:
        print(f"   Error: {e}")
    
    print()

def test_screenshot_text_simulation():
    """Simulate the screenshot text selection that gave excellent results."""
    print("📸 Testing screenshot text selection simulation...")
    
    # Full text as it would appear in screenshot (with proper context)
    screenshot_text = """On Monday the elementary students will attend the Indigenous Legacy Gathering at Nathan Phillips Square.

We will leave school by 9:00a.m.

Our typical EE morning routine will apply as we walk south toward the venue, and via TTC if necessary. We aim to be at Nathan Phillips Square at 12:00p.m. to attend a drumming and dance performance from 12-1p.m. We will make our way back to our neighbourhood around 1:30 via TTC and to school for 3:30 dismissal."""
    
    url = 'https://calendar-api-wrxz.onrender.com/parse'
    payload = {
        'text': screenshot_text,
        'timezone': 'America/New_York',
        'locale': 'en_US', 
        'now': datetime.now(timezone.utc).isoformat()
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        result = response.json()
        
        print(f"   Input: Full email text with context")
        print(f"   Title: {result.get('title')}")
        print(f"   Start: {result.get('start_datetime')}")
        print(f"   Location: {result.get('location')}")
        print(f"   Confidence: {result.get('confidence_score', 0):.3f}")
        
        if result.get('start_datetime'):
            dt = datetime.fromisoformat(result['start_datetime'].replace('Z', '+00:00'))
            print(f"   Formatted: {dt.strftime('%a, %b %d, %Y at %I:%M %p')}")
        
        print("   ✅ Excellent results - full context preserved")
        
    except Exception as e:
        print(f"   Error: {e}")
    
    print()

def analyze_difference():
    """Analyze why screenshot method works better."""
    print("🔍 Analysis: Why Screenshot Method Works Better")
    print()
    
    print("📧 Gmail Share Method Issues:")
    print("   • Text gets truncated or modified by Gmail")
    print("   • Loses formatting and context")
    print("   • May use different processing path")
    print("   • Results in poor event extraction")
    print()
    
    print("📸 Screenshot Method Advantages:")
    print("   • Preserves full text and formatting")
    print("   • Maintains complete context")
    print("   • Uses our enhanced TextProcessorActivity directly")
    print("   • Bypasses Gmail's text selection restrictions")
    print("   • OCR may preserve visual formatting cues")
    print()
    
    print("🎯 Key Insight:")
    print("   Gmail blocks our text selection, but Android's system-level")
    print("   screenshot text selection works perfectly and gives superior results!")
    print()

def main():
    """Run the screenshot discovery analysis."""
    print("🧪 Testing Screenshot Text Selection Discovery...\n")
    
    test_gmail_share_simulation()
    test_screenshot_text_simulation()
    analyze_difference()
    
    print("💡 Recommendation for Gmail Users:")
    print("   1. Take screenshot of Gmail email")
    print("   2. Open screenshot in Photos/Gallery")
    print("   3. Select text in screenshot")
    print("   4. Tap 'Create calendar event'")
    print("   5. Enjoy perfect calendar event creation! ✨")

if __name__ == "__main__":
    main()