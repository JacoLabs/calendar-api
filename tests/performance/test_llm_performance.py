#!/usr/bin/env python3
"""
Quick test to check LLM performance and optimize settings.
"""

import time
import requests
import json
from datetime import datetime

def test_api_performance():
    """Test the API server performance with different text inputs."""
    
    test_cases = [
        "Meeting tomorrow at 2pm",
        "Koji's Birthday Party DATE Sun, Oct 26 2:00 PM EDT LOCATION 1980 St Clair Ave W, Toronto, ON M6N 5H3 CA. Inside Nations Experience",
        "Lunch with John at noon today",
        "Conference call at 3:30pm in the main office"
    ]
    
    print("🧪 Testing API Performance")
    print("=" * 50)
    
    for i, text in enumerate(test_cases, 1):
        print(f"\nTest {i}: '{text[:50]}{'...' if len(text) > 50 else ''}'")
        
        start_time = time.time()
        
        try:
            response = requests.post('http://localhost:5000/parse', 
                json={
                    'text': text,
                    'timezone': 'America/Toronto',
                    'now': datetime.now().isoformat()
                },
                timeout=15
            )
            
            end_time = time.time()
            duration = end_time - start_time
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Success - {duration:.2f}s")
                print(f"   Title: {result.get('title', 'N/A')}")
                print(f"   Confidence: {result.get('confidence_score', 0):.2f}")
                print(f"   Path: {result.get('parsing_path', 'unknown')}")
            else:
                print(f"❌ Error {response.status_code} - {duration:.2f}s")
                
        except requests.exceptions.Timeout:
            print(f"⏰ Timeout after 15s")
        except Exception as e:
            print(f"❌ Exception: {e}")

def test_ollama_direct():
    """Test Ollama directly to see raw performance."""
    print("\n🦙 Testing Ollama Direct Performance")
    print("=" * 50)
    
    try:
        # Check if Ollama is running
        response = requests.get("http://localhost:11434/api/tags", timeout=3)
        if response.status_code != 200:
            print("❌ Ollama not running")
            return
            
        models = response.json().get('models', [])
        print(f"Available models: {[m['name'] for m in models]}")
        
        # Test a simple prompt
        prompt = """Extract event information from: "Meeting tomorrow at 2pm"
Return JSON: {"title": "...", "confidence": 0.8}"""
        
        start_time = time.time()
        
        response = requests.post("http://localhost:11434/api/generate",
            json={
                "model": "llama3.2:3b",
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.1,
                    "num_predict": 100
                }
            },
            timeout=10
        )
        
        end_time = time.time()
        duration = end_time - start_time
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Ollama direct - {duration:.2f}s")
            print(f"   Response: {result.get('response', '')[:100]}...")
        else:
            print(f"❌ Ollama error {response.status_code}")
            
    except Exception as e:
        print(f"❌ Ollama test failed: {e}")

if __name__ == '__main__':
    test_api_performance()
    test_ollama_direct()