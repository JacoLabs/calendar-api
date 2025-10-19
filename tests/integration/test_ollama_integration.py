#!/usr/bin/env python3
"""
Integration test for LLM service with Ollama.
Run this to test if Ollama integration is working properly.
"""

import sys
import json
from datetime import datetime

from services.llm_service import LLMService


def test_ollama_integration():
    """Test LLM service with Ollama if available."""
    print("🧪 Testing LLM Service Integration")
    print("=" * 40)
    
    # Initialize service with auto-detection
    service = LLMService(provider="auto")
    
    print(f"Provider: {service.provider}")
    print(f"Model: {service.model}")
    print(f"Available: {service.is_available()}")
    print()
    
    # Test connection
    print("🔗 Testing connection...")
    if service.test_connection():
        print("✅ Connection test passed")
    else:
        print("❌ Connection test failed")
    
    print()
    
    # Test event extraction
    test_cases = [
        "Meeting tomorrow at 2pm in conference room A",
        "Lunch with Sarah on Friday at noon at Cafe Central", 
        "Doctor appointment next Tuesday 3:30pm",
        "On Monday the elementary students will attend the Indigenous Legacy Gathering"
    ]
    
    print("📝 Testing event extraction...")
    for i, text in enumerate(test_cases, 1):
        print(f"\nTest {i}: {text}")
        
        try:
            response = service.extract_event(text, current_date="2025-01-01")
            
            if response.success:
                print(f"✅ Success (confidence: {response.confidence:.2f})")
                data = response.data
                
                if data.get('title'):
                    print(f"   Title: {data['title']}")
                if data.get('start_datetime'):
                    print(f"   Start: {data['start_datetime']}")
                if data.get('location'):
                    print(f"   Location: {data['location']}")
                
                print(f"   Processing time: {response.processing_time:.3f}s")
            else:
                print(f"❌ Failed: {response.error}")
                
        except Exception as e:
            print(f"❌ Exception: {e}")
    
    # Test ParsedEvent conversion
    print(f"\n🔄 Testing ParsedEvent conversion...")
    text = "Team standup tomorrow at 9am"
    parsed_event = service.llm_extract_event(text)
    
    print(f"Title: {parsed_event.title}")
    print(f"Start: {parsed_event.start_datetime}")
    print(f"Confidence: {parsed_event.confidence_score:.2f}")
    print(f"Provider: {parsed_event.extraction_metadata.get('llm_provider', 'unknown')}")
    
    print(f"\n📊 Service Status:")
    status = service.get_status()
    for key, value in status.items():
        if key != 'config':  # Skip config details
            print(f"   {key}: {value}")


if __name__ == "__main__":
    try:
        test_ollama_integration()
        print(f"\n🎉 Integration test completed!")
    except KeyboardInterrupt:
        print(f"\n👋 Test cancelled by user")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)