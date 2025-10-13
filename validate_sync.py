#!/usr/bin/env python3
"""
Validation script to check if codebase is properly synced with OpenAI API configuration.
"""

import os
import sys
import logging
from datetime import datetime

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def check_environment_variables():
    """Check if required environment variables are set."""
    print("🔍 Checking Environment Variables...")
    
    # Check OpenAI API key
    openai_key = os.getenv('OPENAI_API_KEY')
    if openai_key:
        print(f"✅ OPENAI_API_KEY: Configured (length: {len(openai_key)})")
    else:
        print("❌ OPENAI_API_KEY: Not configured")
    
    # Check cache configuration
    cache_ttl = os.getenv('CACHE_TTL_HOURS', '24')
    print(f"✅ CACHE_TTL_HOURS: {cache_ttl}")
    
    # Check LLM provider
    llm_provider = os.getenv('LLM_PROVIDER', 'auto')
    print(f"✅ LLM_PROVIDER: {llm_provider}")
    
    return bool(openai_key)

def check_imports():
    """Check if all required modules can be imported."""
    print("\n📦 Checking Imports...")
    
    try:
        from services.cache_manager import get_cache_manager
        print("✅ Cache Manager: OK")
    except ImportError as e:
        print(f"❌ Cache Manager: {e}")
        return False
    
    try:
        from services.llm_service import LLMService
        print("✅ LLM Service: OK")
    except ImportError as e:
        print(f"❌ LLM Service: {e}")
        return False
    
    try:
        from services.event_parser import EventParser
        print("✅ Event Parser: OK")
    except ImportError as e:
        print(f"❌ Event Parser: {e}")
        return False
    
    return True

def test_cache_manager():
    """Test cache manager functionality."""
    print("\n🗄️ Testing Cache Manager...")
    
    try:
        from services.cache_manager import get_cache_manager
        from models.event_models import ParsedEvent
        
        cache_manager = get_cache_manager()
        
        # Test basic functionality
        test_text = "Meeting tomorrow at 2pm"
        test_event = ParsedEvent()
        test_event.title = "Test Meeting"
        test_event.confidence_score = 0.8
        
        # Test put/get
        success = cache_manager.put(test_text, test_event)
        if success:
            print("✅ Cache Put: OK")
        else:
            print("❌ Cache Put: Failed")
            return False
        
        cached_result = cache_manager.get(test_text)
        if cached_result and cached_result.title == "Test Meeting":
            print("✅ Cache Get: OK")
        else:
            print("❌ Cache Get: Failed")
            return False
        
        # Test statistics
        stats = cache_manager.get_stats()
        print(f"✅ Cache Stats: {stats.total_requests} requests, {stats.cache_hits} hits")
        
        return True
        
    except Exception as e:
        print(f"❌ Cache Manager Test: {e}")
        return False

def test_llm_service():
    """Test LLM service initialization."""
    print("\n🤖 Testing LLM Service...")
    
    try:
        from services.llm_service import LLMService
        
        # Test initialization
        llm_service = LLMService()
        print(f"✅ LLM Service Provider: {llm_service.provider}")
        print(f"✅ LLM Service Model: {llm_service.model}")
        
        # Test availability
        if llm_service.is_available():
            print("✅ LLM Service: Available")
        else:
            print("⚠️ LLM Service: Using fallback mode")
        
        # Test status
        status = llm_service.get_status()
        print(f"✅ OpenAI Available: {status.get('openai_available', False)}")
        print(f"✅ Ollama Available: {status.get('ollama_available', False)}")
        
        return True
        
    except Exception as e:
        print(f"❌ LLM Service Test: {e}")
        return False

def test_event_parser():
    """Test event parser functionality."""
    print("\n📅 Testing Event Parser...")
    
    try:
        from services.event_parser import EventParser
        
        parser = EventParser()
        
        # Test basic parsing
        test_text = "Meeting with John tomorrow at 2pm"
        result = parser.parse_event_text(test_text)
        
        if result and result.confidence_score > 0:
            print(f"✅ Event Parser: OK (confidence: {result.confidence_score:.2f})")
            print(f"   Title: {result.title}")
            print(f"   Start: {result.start_datetime}")
            return True
        else:
            print("❌ Event Parser: Low confidence or failed")
            return False
        
    except Exception as e:
        print(f"❌ Event Parser Test: {e}")
        return False

def main():
    """Run all validation checks."""
    print("🔄 Codebase Synchronization Validation")
    print("=" * 50)
    
    # Track results
    results = []
    
    # Run checks
    results.append(("Environment Variables", check_environment_variables()))
    results.append(("Imports", check_imports()))
    results.append(("Cache Manager", test_cache_manager()))
    results.append(("LLM Service", test_llm_service()))
    results.append(("Event Parser", test_event_parser()))
    
    # Summary
    print("\n📊 Validation Summary")
    print("=" * 50)
    
    passed = 0
    for name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{name:20} {status}")
        if success:
            passed += 1
    
    print(f"\nOverall: {passed}/{len(results)} checks passed")
    
    if passed == len(results):
        print("\n🎉 All checks passed! Codebase is properly synced.")
        return 0
    else:
        print("\n⚠️ Some checks failed. Please review the issues above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())