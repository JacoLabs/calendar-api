#!/usr/bin/env python3
"""
Test if LLM is actually working when needed in production.
"""

import requests
import json
from datetime import datetime
import time

def test_llm_scenarios():
    """Test scenarios that should trigger LLM usage."""
    
    print("🧪 TESTING LLM FUNCTIONALITY IN PRODUCTION")
    print("=" * 60)
    
    # Test cases designed to trigger different parsing paths
    test_cases = [
        {
            "name": "Simple regex case (should NOT need LLM)",
            "text": "Meeting tomorrow at 2pm",
            "expected_path": "regex",
            "should_use_llm": False
        },
        {
            "name": "Complex natural language (should trigger LLM)",
            "text": "I need to remember to call mom sometime next week, maybe Tuesday afternoon",
            "expected_path": "llm",
            "should_use_llm": True
        },
        {
            "name": "Ambiguous time reference (should trigger LLM)",
            "text": "lunch with sarah sometime next week",
            "expected_path": "llm", 
            "should_use_llm": True
        },
        {
            "name": "Complex event description (should trigger LLM)",
            "text": "Team retrospective meeting to discuss Q4 goals and planning for next quarter",
            "expected_path": "llm",
            "should_use_llm": True
        },
        {
            "name": "Due date format (regex should handle)",
            "text": "Project report due October 20, 2025",
            "expected_path": "regex",
            "should_use_llm": False
        },
        {
            "name": "Very ambiguous text (should definitely need LLM)",
            "text": "maybe something important happening soon",
            "expected_path": "llm",
            "should_use_llm": True
        }
    ]
    
    api_url = "https://calendar-api-wrxz.onrender.com"
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n🔬 Test {i}: {test_case['name']}")
        print(f"   Text: \"{test_case['text']}\"")
        print(f"   Expected to use LLM: {test_case['should_use_llm']}")
        
        try:
            start_time = time.time()
            response = requests.post(
                f"{api_url}/parse",
                json={
                    "text": test_case['text'],
                    "now": datetime.now().isoformat(),
                    "timezone_offset": -480
                },
                timeout=20  # Longer timeout for LLM processing
            )
            response_time = (time.time() - start_time) * 1000
            
            if response.status_code == 200:
                result = response.json()
                
                # Analyze the result
                confidence = result.get('confidence_score', 0)
                parsing_path = result.get('parsing_path', 'unknown')
                title = result.get('title', 'N/A')
                start_datetime = result.get('start_datetime')
                warnings = result.get('warnings', [])
                
                print(f"   ✅ Success:")
                print(f"      Confidence: {confidence:.2f}")
                print(f"      Parsing Path: {parsing_path}")
                print(f"      Title: {title}")
                print(f"      Start DateTime: {start_datetime}")
                print(f"      Response Time: {response_time:.0f}ms")
                
                if warnings:
                    print(f"      Warnings: {warnings}")
                
                # Analyze if LLM was likely used
                llm_indicators = [
                    confidence < 0.6,  # Low confidence suggests LLM fallback
                    parsing_path in ['llm_only', 'llm_fallback'],
                    response_time > 2000,  # Slow response suggests LLM processing
                    'llm' in parsing_path.lower()
                ]
                
                likely_used_llm = any(llm_indicators)
                
                print(f"      LLM Likely Used: {likely_used_llm}")
                
                # Check if expectation matches reality
                if test_case['should_use_llm'] == likely_used_llm:
                    print(f"      ✅ EXPECTATION MET")
                else:
                    print(f"      ⚠️  EXPECTATION MISMATCH")
                    if test_case['should_use_llm'] and not likely_used_llm:
                        print(f"         Expected LLM but got regex/deterministic")
                    else:
                        print(f"         Expected regex but got LLM")
                
            else:
                print(f"   ❌ Failed: HTTP {response.status_code}")
                print(f"      Response: {response.text}")
        
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    print("\n" + "=" * 60)
    print("🔍 LLM AVAILABILITY TEST")
    
    # Test LLM service directly through health endpoint
    try:
        health_response = requests.get(f"{api_url}/health", timeout=10)
        if health_response.status_code == 200:
            health_data = health_response.json()
            llm_status = health_data.get('services', {}).get('llm', 'unknown')
            
            print(f"   LLM Service Status: {llm_status}")
            
            if llm_status == "unavailable":
                print("   ❌ LLM service is marked as unavailable")
                print("   📝 This means:")
                print("      - Health check fails due to method name mismatch")
                print("      - But LLM might still work for actual parsing")
                print("      - System falls back to heuristic/regex methods")
            elif llm_status == "healthy":
                print("   ✅ LLM service is healthy")
            else:
                print(f"   ⚠️  LLM service status unclear: {llm_status}")
    
    except Exception as e:
        print(f"   ❌ Health check error: {e}")
    
    print("\n" + "=" * 60)
    print("💡 ANALYSIS SUMMARY:")
    
    print("\n🔧 Based on the tests above:")
    print("   1. If most complex cases show low confidence + fast response times:")
    print("      → LLM is likely NOT working, falling back to heuristics")
    print("   2. If complex cases show reasonable confidence + slow response times:")
    print("      → LLM is working but may have issues")
    print("   3. If simple cases work well but complex ones fail:")
    print("      → Regex works fine, LLM fallback may be broken")
    
    print("\n🎯 KEY INDICATORS:")
    print("   • LLM Working: Complex text → reasonable confidence + slow response")
    print("   • LLM Broken: Complex text → very low confidence + fast response")
    print("   • Health Check Issue: LLM status 'unavailable' but parsing works")

if __name__ == "__main__":
    test_llm_scenarios()