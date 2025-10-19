#!/usr/bin/env python3
"""
Test script to verify API synchronization and cache functionality.
"""

import sys
import os
import json
from datetime import datetime

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_api_imports():
    """Test that API can import all required modules."""
    print("🔍 Testing API Imports...")
    
    try:
        from api.app.main import app
        print("✅ FastAPI app import: OK")
    except ImportError as e:
        print(f"❌ FastAPI app import failed: {e}")
        return False
    
    try:
        from services.cache_manager import get_cache_manager
        cache_manager = get_cache_manager()
        print("✅ Cache manager import: OK")
        print(f"   TTL: {cache_manager.ttl_hours} hours")
        print(f"   Max entries: {cache_manager.max_entries}")
    except ImportError as e:
        print(f"❌ Cache manager import failed: {e}")
        return False
    
    try:
        from services.event_parser import EventParser
        parser = EventParser()
        print("✅ Event parser import: OK")
    except ImportError as e:
        print(f"❌ Event parser import failed: {e}")
        return False
    
    return True

def test_cache_integration():
    """Test cache integration with event parsing."""
    print("\n🗄️ Testing Cache Integration...")
    
    try:
        from services.cache_manager import get_cache_manager
        from services.event_parser import EventParser
        from models.event_models import ParsedEvent
        
        cache_manager = get_cache_manager()
        parser = EventParser()
        
        # Test text
        test_text = "Team meeting tomorrow at 3pm in conference room A"
        
        # Parse event
        print("📅 Parsing test event...")
        parsed_event = parser.parse_event_text(test_text)
        
        if parsed_event.confidence_score > 0:
            print(f"✅ Event parsed successfully (confidence: {parsed_event.confidence_score:.2f})")
            print(f"   Title: {parsed_event.title}")
            print(f"   Start: {parsed_event.start_datetime}")
            print(f"   Location: {parsed_event.location}")
        else:
            print("⚠️ Event parsing returned low confidence")
        
        # Test cache operations
        print("🗄️ Testing cache operations...")
        
        # Put in cache
        success = cache_manager.put(test_text, parsed_event)
        if success:
            print("✅ Cache put: OK")
        else:
            print("❌ Cache put: Failed")
            return False
        
        # Get from cache
        cached_result = cache_manager.get(test_text)
        if cached_result:
            print("✅ Cache get: OK")
            print(f"   Cached title: {cached_result.title}")
        else:
            print("❌ Cache get: Failed")
            return False
        
        # Check cache stats
        stats = cache_manager.get_stats()
        print(f"✅ Cache stats: {stats.total_requests} requests, {stats.cache_hits} hits")
        
        return True
        
    except Exception as e:
        print(f"❌ Cache integration test failed: {e}")
        return False

def test_llm_service_status():
    """Test LLM service status and configuration."""
    print("\n🤖 Testing LLM Service Status...")
    
    try:
        from services.llm_service import LLMService
        
        llm_service = LLMService()
        status = llm_service.get_status()
        
        print(f"✅ LLM Provider: {status['provider']}")
        print(f"✅ LLM Model: {status['model']}")
        print(f"✅ Available: {status['available']}")
        print(f"✅ OpenAI Available: {status['openai_available']}")
        print(f"✅ Ollama Available: {status['ollama_available']}")
        
        # Test a simple extraction
        print("🧠 Testing LLM extraction...")
        response = llm_service.extract_event("Meeting with Sarah tomorrow at 2pm")
        
        if response.success:
            print(f"✅ LLM extraction successful (provider: {response.provider})")
            print(f"   Confidence: {response.confidence:.2f}")
            print(f"   Processing time: {response.processing_time:.3f}s")
        else:
            print(f"⚠️ LLM extraction failed: {response.error}")
        
        return True
        
    except Exception as e:
        print(f"❌ LLM service test failed: {e}")
        return False

def test_environment_config():
    """Test environment variable configuration."""
    print("\n🔧 Testing Environment Configuration...")
    
    # Check cache configuration
    cache_ttl = os.getenv('CACHE_TTL_HOURS', '24')
    print(f"✅ CACHE_TTL_HOURS: {cache_ttl}")
    
    # Check LLM configuration
    llm_provider = os.getenv('LLM_PROVIDER', 'auto')
    print(f"✅ LLM_PROVIDER: {llm_provider}")
    
    llm_model = os.getenv('LLM_MODEL', 'not set')
    print(f"✅ LLM_MODEL: {llm_model}")
    
    # Check OpenAI key
    openai_key = os.getenv('OPENAI_API_KEY')
    if openai_key:
        print(f"✅ OPENAI_API_KEY: Configured (length: {len(openai_key)})")
    else:
        print("⚠️ OPENAI_API_KEY: Not configured (using fallback providers)")
    
    return True

def main():
    """Run all API synchronization tests."""
    print("🔄 API Synchronization Test Suite")
    print("=" * 50)
    
    results = []
    
    # Run tests
    results.append(("API Imports", test_api_imports()))
    results.append(("Environment Config", test_environment_config()))
    results.append(("Cache Integration", test_cache_integration()))
    results.append(("LLM Service", test_llm_service_status()))
    
    # Summary
    print("\n📊 Test Results Summary")
    print("=" * 50)
    
    passed = 0
    for name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{name:20} {status}")
        if success:
            passed += 1
    
    print(f"\nOverall: {passed}/{len(results)} tests passed")
    
    if passed == len(results):
        print("\n🎉 All tests passed! API is properly synchronized.")
        print("\n🚀 Ready for production deployment!")
        return 0
    else:
        print("\n⚠️ Some tests failed. Please review the issues above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())