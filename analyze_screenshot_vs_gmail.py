#!/usr/bin/env python3
"""
Analyze why screenshots work beautifully but Gmail text highlighting doesn't.
"""

import requests
import json
from datetime import datetime, timezone

def analyze_text_sources():
    """Analyze different text sources and their parsing quality."""
    print("🔍 Analyzing Screenshot vs Gmail Text Highlighting")
    print("=" * 60)
    
    # The same email content from different sources
    test_scenarios = [
        {
            "name": "📧 Gmail Text Selection (Poor Results)",
            "description": "What Gmail sends via ACTION_PROCESS_TEXT",
            "text": "On Monday the elementary students will attend the Indigenous Legacy Gathering",
            "source": "Gmail text selection API",
            "expected_quality": "Poor"
        },
        {
            "name": "📧 Gmail Share (Poor Results)", 
            "description": "What Gmail sends via ACTION_SEND",
            "text": "On Monday the elementary students will attend the Indigenous Legacy",
            "source": "Gmail share truncation",
            "expected_quality": "Poor"
        },
        {
            "name": "📸 Screenshot OCR (Excellent Results)",
            "description": "Full email text from screenshot OCR",
            "text": """Dear Elementary Families,

Our apologies for sending this after hours. I hope this reaches you by Monday. 😊

On Monday the elementary students will attend the Indigenous Legacy Gathering at Nathan Phillips Square.

We will leave school by 9:00a.m.

Our typical EE morning routine will apply as we walk south toward the venue, and via TTC if necessary. We aim to be at Nathan Phillips Square at 12:00p.m. to attend a drumming and dance performance from 12-1p.m. We will make our way back to our neighbourhood around 1:30 via TTC and to school for 3:30 dismissal.""",
            "source": "Screenshot OCR with full context",
            "expected_quality": "Excellent"
        },
        {
            "name": "📋 Clipboard Full Context",
            "description": "User manually copies full relevant text",
            "text": """On Monday the elementary students will attend the Indigenous Legacy Gathering at Nathan Phillips Square.

We will leave school by 9:00a.m.

We aim to be at Nathan Phillips Square at 12:00p.m. to attend a drumming and dance performance from 12-1p.m.""",
            "source": "Manual copy with context",
            "expected_quality": "Good"
        },
        {
            "name": "🔧 Our Current Merge Attempt",
            "description": "Gmail selection + clipboard merge",
            "text": "On Monday the elementary students will attend the Indigenous Legacy Gathering\nWe will leave school by 9:00 AM.",
            "source": "Automated merge logic",
            "expected_quality": "Improved but limited"
        }
    ]
    
    results = []
    
    for scenario in test_scenarios:
        print(f"\n{scenario['name']}")
        print(f"   Description: {scenario['description']}")
        print(f"   Source: {scenario['source']}")
        print(f"   Expected: {scenario['expected_quality']}")
        
        # Parse with API
        result = parse_text(scenario['text'])
        
        title = result.get('title', '')
        start_time = result.get('start_datetime')
        location = result.get('location')
        confidence = result.get('confidence_score', 0)
        
        print(f"   Results:")
        print(f"      Title: '{title}'")
        print(f"      Time: {start_time}")
        print(f"      Location: {location}")
        print(f"      Confidence: {confidence:.3f}")
        
        # Assess quality
        has_good_title = bool(title and 'Indigenous Legacy Gathering' in title)
        has_correct_time = bool(start_time and ('09:00:00' in start_time or '12:00:00' in start_time))
        has_location = bool(location and 'Nathan Phillips Square' in location)
        
        quality_score = sum([has_good_title, has_correct_time, has_location, confidence > 0.6])
        quality_rating = ["Poor", "Fair", "Good", "Excellent"][min(quality_score, 3)]
        
        print(f"      Quality: {quality_rating} ({quality_score}/4)")
        print(f"         Good title: {'✅' if has_good_title else '❌'}")
        print(f"         Correct time: {'✅' if has_correct_time else '❌'}")
        print(f"         Has location: {'✅' if has_location else '❌'}")
        print(f"         High confidence: {'✅' if confidence > 0.6 else '❌'}")
        
        results.append({
            'name': scenario['name'],
            'quality_score': quality_score,
            'quality_rating': quality_rating,
            'confidence': confidence,
            'has_good_title': has_good_title,
            'has_correct_time': has_correct_time,
            'has_location': has_location
        })
    
    # Analysis summary
    print(f"\n📊 ANALYSIS SUMMARY")
    print("=" * 60)
    
    best_result = max(results, key=lambda x: x['quality_score'])
    worst_result = min(results, key=lambda x: x['quality_score'])
    
    print(f"🏆 Best: {best_result['name']} - {best_result['quality_rating']} ({best_result['quality_score']}/4)")
    print(f"💔 Worst: {worst_result['name']} - {worst_result['quality_rating']} ({worst_result['quality_score']}/4)")
    
    print(f"\n🔍 KEY INSIGHTS:")
    
    # Find what makes screenshot so good
    screenshot_result = next(r for r in results if 'Screenshot' in r['name'])
    gmail_results = [r for r in results if 'Gmail' in r['name']]
    
    print(f"   📸 Screenshot Success Factors:")
    print(f"      • Full email context preserved")
    print(f"      • Multiple time references (9:00am, 12:00pm, 12-1pm)")
    print(f"      • Complete location information")
    print(f"      • No text truncation by app")
    print(f"      • OCR preserves formatting and structure")
    
    print(f"   📧 Gmail Failure Factors:")
    for gmail_result in gmail_results:
        print(f"      • {gmail_result['name']}: Limited to single selection/truncation")
    
    print(f"   🎯 The Core Problem:")
    print(f"      Gmail's API limitations prevent us from getting the full context")
    print(f"      that makes screenshot parsing so successful.")
    
    return results

def identify_solution_approaches(results):
    """Identify potential solution approaches based on the analysis."""
    print(f"\n💡 SOLUTION APPROACHES")
    print("=" * 60)
    
    approaches = [
        {
            "name": "1. Context Reconstruction",
            "description": "Intelligently reconstruct full context from partial Gmail selections",
            "feasibility": "Medium",
            "impact": "High",
            "details": [
                "Use multiple clipboard snapshots over time",
                "Build context map from repeated selections",
                "Apply NLP to infer missing information",
                "Use email structure patterns"
            ]
        },
        {
            "name": "2. Smart Email Parsing",
            "description": "Detect email patterns and apply email-specific parsing rules",
            "feasibility": "High", 
            "impact": "Medium",
            "details": [
                "Detect email headers/signatures",
                "Apply school/organization communication patterns",
                "Use time sequence analysis (multiple times in email)",
                "Location extraction from common patterns"
            ]
        },
        {
            "name": "3. Multi-Pass Enhancement",
            "description": "Multiple parsing attempts with different strategies",
            "feasibility": "High",
            "impact": "Medium",
            "details": [
                "Parse for events first, then times, then locations",
                "Use confidence-weighted combination",
                "Apply domain-specific rules (school events, meetings, etc.)",
                "Fallback hierarchy of parsing strategies"
            ]
        },
        {
            "name": "4. User-Guided Context",
            "description": "Help users provide better context through UI",
            "feasibility": "High",
            "impact": "High",
            "details": [
                "Smart clipboard monitoring with context suggestions",
                "One-tap 'add more context' button",
                "Template-based event creation for common scenarios",
                "Learning from user corrections"
            ]
        }
    ]
    
    for approach in approaches:
        print(f"\n{approach['name']}")
        print(f"   Description: {approach['description']}")
        print(f"   Feasibility: {approach['feasibility']}")
        print(f"   Impact: {approach['impact']}")
        print(f"   Details:")
        for detail in approach['details']:
            print(f"      • {detail}")
    
    return approaches

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
    """Run the analysis."""
    results = analyze_text_sources()
    approaches = identify_solution_approaches(results)
    
    print(f"\n🎯 RECOMMENDATION")
    print("=" * 60)
    print(f"Focus on approaches 2 & 4 for immediate impact:")
    print(f"• Smart Email Parsing (High feasibility, Medium impact)")
    print(f"• User-Guided Context (High feasibility, High impact)")
    print(f"\nThis combination can bridge the gap between Gmail's limitations")
    print(f"and screenshot-quality results.")

if __name__ == "__main__":
    main()