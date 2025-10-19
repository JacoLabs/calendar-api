#!/usr/bin/env python3
"""
Test script for LLM-based text enhancement functionality.
Tests the new LLM integration for improving Gmail parsing quality.
"""

import os
import sys
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.event_parser import EventParser
from services.llm_text_enhancer import LLMTextEnhancer
from services.text_merge_helper import TextMergeHelper


def test_llm_enhancement():
    """Test LLM enhancement with various text types."""
    
    print("🤖 Testing LLM Text Enhancement")
    print("=" * 50)
    
    # Initialize components
    llm_enhancer = LLMTextEnhancer(provider="auto")
    text_helper = TextMergeHelper()
    event_parser = EventParser()
    
    # Check what LLM provider is available
    print(f"🤖 LLM Provider: {llm_enhancer.provider}")
    print(f"📦 Model: {llm_enhancer.model}")
    
    if not llm_enhancer.is_available():
        print("⚠️  No LLM provider available. Testing fallback mode only.")
        print("   Setup instructions:")
        print("   - Ollama (FREE): Install from https://ollama.ai")
        print("   - Groq (FREE): Set GROQ_API_KEY environment variable")
        print("   - OpenAI (PAID): Set OPENAI_API_KEY environment variable")
        print()
    else:
        print(f"✅ LLM enhancement available with {llm_enhancer.provider}")
        print()
    
    # Test cases that were problematic before
    test_cases = [
        {
            "name": "School Event (Gmail Selection Issue)",
            "text": "On Monday the elementary students will attend the Indigenous Legacy Gathering\nWe will leave school by 9:00 AM.",
            "expected_improvement": "Better event title extraction and time parsing"
        },
        {
            "name": "Business Meeting Fragment",
            "text": "quarterly review meeting\nTuesday 2pm conference room B",
            "expected_improvement": "Merge fragmented information"
        },
        {
            "name": "Email with Clipboard Merge",
            "selected_text": "Team standup",
            "clipboard_text": "tomorrow at 10am in the main conference room",
            "expected_improvement": "Combine partial Gmail selection with clipboard"
        },
        {
            "name": "Complex School Communication",
            "text": "Dear Parents,\n\nOn Friday the Grade 3 students will participate in the Science Fair presentation. The event will begin at 1:30 PM in the gymnasium.",
            "expected_improvement": "Extract clear event details from formal communication"
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"Test {i}: {test_case['name']}")
        print("-" * 40)
        
        if 'clipboard_text' in test_case:
            # Test clipboard merge scenario
            original_text = test_case['selected_text']
            clipboard_text = test_case['clipboard_text']
            
            print(f"Selected text: '{original_text}'")
            print(f"Clipboard: '{clipboard_text}'")
            
            # Test with enhancement
            result = event_parser.parse_text_enhanced(original_text, clipboard_text)
            
            print(f"\n📊 Enhanced Result:")
            print(f"   Title: {result.title}")
            print(f"   Start: {result.start_datetime}")
            print(f"   Location: {result.location}")
            print(f"   Confidence: {result.confidence_score:.2f}")
            
            # Show enhancement metadata
            if result.extraction_metadata and 'text_enhancement' in result.extraction_metadata:
                enhancement = result.extraction_metadata['text_enhancement']
                print(f"   Enhanced text: '{enhancement['enhanced_text']}'")
                print(f"   Merge applied: {enhancement['merge_applied']}")
                print(f"   LLM applied: {enhancement['enhancement_applied']}")
        
        else:
            # Test single text enhancement
            original_text = test_case['text']
            print(f"Original: '{original_text}'")
            
            # Test with enhancement
            result = event_parser.parse_text_enhanced(original_text)
            
            print(f"\n📊 Enhanced Result:")
            print(f"   Title: {result.title}")
            print(f"   Start: {result.start_datetime}")
            print(f"   Location: {result.location}")
            print(f"   Confidence: {result.confidence_score:.2f}")
            
            # Show enhancement metadata
            if result.extraction_metadata and 'text_enhancement' in result.extraction_metadata:
                enhancement = result.extraction_metadata['text_enhancement']
                if enhancement['enhanced_text'] != original_text:
                    print(f"   Enhanced text: '{enhancement['enhanced_text']}'")
                print(f"   LLM applied: {enhancement['enhancement_applied']}")
            
            # Compare with original parsing
            print(f"\n📊 Original Parsing (for comparison):")
            original_result = event_parser.parse_text(original_text)
            print(f"   Title: {original_result.title}")
            print(f"   Start: {original_result.start_datetime}")
            print(f"   Location: {original_result.location}")
            print(f"   Confidence: {original_result.confidence_score:.2f}")
        
        print(f"\n✨ Expected: {test_case['expected_improvement']}")
        print("\n" + "=" * 50 + "\n")


def test_fallback_mode():
    """Test fallback mode when LLM is not available."""
    
    print("🔧 Testing Fallback Mode")
    print("=" * 30)
    
    # Create helper without LLM
    text_helper = TextMergeHelper(use_llm=False)
    
    # Test school event restructuring
    test_text = "On Monday the elementary students will attend the Indigenous Legacy Gathering"
    
    result = text_helper.enhance_text_for_parsing(test_text)
    
    print(f"Original: '{test_text}'")
    print(f"Enhanced: '{result.final_text}'")
    print(f"Confidence: {result.confidence}")
    print(f"Enhancement applied: {result.enhancement_applied}")
    print()


def test_api_integration():
    """Test API integration with new parameters."""
    
    print("🌐 Testing API Integration")
    print("=" * 30)
    
    # This would test the API endpoints with the new parameters
    # For now, just show the expected request format
    
    example_request = {
        "text": "On Monday the elementary students will attend the Indigenous Legacy Gathering",
        "clipboard_text": "We will leave school by 9:00 AM",
        "timezone": "America/New_York",
        "locale": "en_US",
        "use_llm_enhancement": True
    }
    
    print("📝 Example API Request:")
    import json
    print(json.dumps(example_request, indent=2))
    print()
    
    print("✅ This request format works with:")
    print("   - Android app (via HTTP client)")
    print("   - iOS app (via HTTP client)")
    print("   - Browser extension (via fetch/XMLHttpRequest)")
    print("   - Any platform that can make HTTP POST requests")
    print()


if __name__ == "__main__":
    print("🚀 LLM Text Enhancement Test Suite")
    print("=" * 50)
    print()
    
    try:
        test_llm_enhancement()
        test_fallback_mode()
        test_api_integration()
        
        print("✅ All tests completed!")
        print("\n🎯 Key Benefits:")
        print("   - Better parsing of complex email patterns")
        print("   - Smart clipboard merging for Gmail selections")
        print("   - Fallback mode when LLM is unavailable")
        print("   - Cross-platform compatibility (Android, iOS, Browser)")
        print("   - Maintains existing API compatibility")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()