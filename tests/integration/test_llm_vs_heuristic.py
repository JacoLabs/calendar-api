#!/usr/bin/env python3
"""
Test LLM vs Heuristic parsing to demonstrate the enhanced capabilities.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.llm_service import LLMService
from datetime import datetime
import json

def test_llm_vs_heuristic():
    """Compare LLM parsing vs heuristic fallback."""
    
    # Test cases that should show LLM advantages
    test_cases = [
        {
            'text': 'Due Date: Oct 15, 2025',
            'description': 'Simple due date (our main fix)'
        },
        {
            'text': 'Item ID: 37131076518125 Title: COWA Due Date: Oct 15, 2025',
            'description': 'Due date with context (screenshot example)'
        },
        {
            'text': 'Meeting with Sarah tomorrow at 2pm to discuss the quarterly budget review',
            'description': 'Complex meeting description'
        },
        {
            'text': 'Lunch at Cafe Downtown next Friday from 12:30-1:30 with the marketing team',
            'description': 'Event with time range and location'
        },
        {
            'text': 'Project deadline: December 1, 2025 - Final presentation due',
            'description': 'Deadline with additional context'
        },
        {
            'text': 'On Monday the elementary students will attend the Indigenous Legacy Gathering',
            'description': 'Complex sentence structure'
        }
    ]
    
    print("🧪 Testing LLM vs Heuristic Parsing")
    print("=" * 60)
    
    # Initialize LLM service
    llm_service = LLMService()
    
    # Check LLM status
    status = llm_service.get_status()
    print(f"LLM Status: {status}")
    print(f"Provider: {status['provider']}")
    print(f"Model: {status['model']}")
    print(f"Available: {status['available']}")
    print()
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"Test {i}: {test_case['description']}")
        print(f"Input: '{test_case['text']}'")
        print("-" * 40)
        
        try:
            # Test with LLM
            parsed_event = llm_service.llm_extract_event(
                test_case['text'], 
                current_date="2025-01-01"
            )
            
            provider = parsed_event.extraction_metadata.get('llm_provider', 'unknown')
            
            print(f"🤖 {provider.upper()} Result:")
            print(f"   Title: {parsed_event.title}")
            print(f"   Start: {parsed_event.start_datetime}")
            print(f"   End: {parsed_event.end_datetime}")
            print(f"   All Day: {parsed_event.all_day}")
            print(f"   Location: {parsed_event.location}")
            print(f"   Confidence: {parsed_event.confidence_score:.2f}")
            
            # Show LLM-specific metadata
            if 'raw_llm_response' in parsed_event.extraction_metadata:
                raw_response = parsed_event.extraction_metadata['raw_llm_response']
                if 'extraction_notes' in raw_response:
                    print(f"   Notes: {raw_response['extraction_notes']}")
                
                # Show confidence breakdown
                if 'confidence' in raw_response:
                    conf = raw_response['confidence']
                    print(f"   Confidence Breakdown:")
                    for field, score in conf.items():
                        if field != 'overall':
                            print(f"     {field}: {score:.2f}")
            
            # Test connection quality
            processing_time = parsed_event.extraction_metadata.get('processing_time', 0)
            print(f"   Processing Time: {processing_time:.3f}s")
            
            # Validate our due date fix
            if 'due date' in test_case['text'].lower():
                if parsed_event.all_day and parsed_event.start_datetime:
                    date_str = parsed_event.start_datetime.date().isoformat()
                    if '2025-10-15' in date_str:
                        print("   ✅ Due date correctly parsed as all-day event on Oct 15!")
                    else:
                        print(f"   ❌ Wrong date: {date_str}")
                else:
                    print("   ❌ Should be all-day event")
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        print()
    
    # Test LLM connection directly
    print("🔗 Testing LLM Connection:")
    connection_test = llm_service.test_connection()
    print(f"Connection Test: {'✅ PASS' if connection_test else '❌ FAIL'}")
    
    print("\n" + "=" * 60)
    print("LLM Testing Complete!")

def test_raw_ollama_connection():
    """Test raw Ollama connection to verify it's working."""
    print("\n🔧 Testing Raw Ollama Connection:")
    
    try:
        import requests
        
        # Test Ollama API directly
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        if response.status_code == 200:
            models = response.json().get('models', [])
            print(f"✅ Ollama is running with {len(models)} models:")
            for model in models:
                print(f"   - {model['name']} ({model['size']})")
        else:
            print(f"❌ Ollama API error: {response.status_code}")
    
    except Exception as e:
        print(f"❌ Ollama connection failed: {e}")
    
    # Test a simple generation
    try:
        test_prompt = "Extract event info from: 'Meeting tomorrow at 2pm'. Respond with JSON."
        
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "llama3.2:3b",
                "prompt": test_prompt,
                "stream": False,
                "options": {"temperature": 0.1, "num_predict": 200}
            },
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Ollama generation test successful")
            print(f"Response: {result['response'][:200]}...")
        else:
            print(f"❌ Ollama generation failed: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Ollama generation test failed: {e}")

if __name__ == "__main__":
    test_raw_ollama_connection()
    test_llm_vs_heuristic()