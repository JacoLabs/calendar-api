#!/usr/bin/env python3
"""
Simple integration test to verify the unified parsing pipeline works.
"""

from datetime import datetime
from services.hybrid_event_parser import HybridEventParser

def test_basic_integration():
    """Test basic integration without external dependencies."""
    
    # Create parser with fixed current time
    current_time = datetime(2025, 10, 8, 14, 30)
    parser = HybridEventParser(current_time=current_time)
    
    # Test simple text parsing
    text = "Meeting with John tomorrow at 2:00 PM"
    
    try:
        # Use regex-only mode to avoid external dependencies
        result = parser.parse_event_text(text, mode="regex_only")
        
        print(f"✓ Parsing successful: {result.parsed_event is not None}")
        print(f"✓ Parsing path: {result.parsing_path}")
        print(f"✓ Confidence: {result.confidence_score:.2f}")
        
        if result.parsed_event:
            print(f"✓ Title: {result.parsed_event.title}")
            print(f"✓ Start time: {result.parsed_event.start_datetime}")
            print(f"✓ Field results: {len(result.parsed_event.field_results)} fields")
            
            # Test field-level confidence tracking
            for field_name, field_result in result.parsed_event.field_results.items():
                print(f"  - {field_name}: {field_result.source} (confidence: {field_result.confidence:.2f})")
        
        print("\n✓ Basic integration test PASSED!")
        return True
        
    except Exception as e:
        print(f"✗ Integration test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_per_field_routing():
    """Test per-field confidence routing."""
    
    current_time = datetime(2025, 10, 8, 14, 30)
    parser = HybridEventParser(current_time=current_time)
    
    try:
        # Test field analysis
        text = "Team meeting Monday at 10 AM in Conference Room A"
        field_analyses = parser.analyze_field_confidence(text)
        
        print(f"✓ Field analysis successful: {len(field_analyses)} fields analyzed")
        
        for field_name, analysis in field_analyses.items():
            print(f"  - {field_name}: confidence={analysis.confidence_potential:.2f}, method={analysis.recommended_method.value}")
        
        print("\n✓ Per-field routing test PASSED!")
        return True
        
    except Exception as e:
        print(f"✗ Per-field routing test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_processing_order():
    """Test processing order optimization."""
    
    current_time = datetime(2025, 10, 8, 14, 30)
    parser = HybridEventParser(current_time=current_time)
    
    try:
        # Test processing order optimization
        fields = ['title', 'location', 'start_datetime', 'end_datetime', 'duration']
        optimized_order = parser.confidence_router.optimize_processing_order(fields)
        
        print(f"✓ Processing order optimization successful")
        print(f"  Original: {fields}")
        print(f"  Optimized: {optimized_order}")
        
        # Verify start_datetime comes first (highest priority)
        assert optimized_order[0] == 'start_datetime', f"Expected start_datetime first, got {optimized_order[0]}"
        
        print("\n✓ Processing order test PASSED!")
        return True
        
    except Exception as e:
        print(f"✗ Processing order test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=== Unified Parsing Pipeline Integration Tests ===\n")
    
    tests = [
        test_basic_integration,
        test_per_field_routing,
        test_processing_order
    ]
    
    passed = 0
    total = len(tests)
    
    for test_func in tests:
        print(f"Running {test_func.__name__}...")
        if test_func():
            passed += 1
        print()
    
    print(f"=== Results: {passed}/{total} tests passed ===")
    
    if passed == total:
        print("🎉 All integration tests PASSED!")
        exit(0)
    else:
        print("❌ Some integration tests FAILED!")
        exit(1)