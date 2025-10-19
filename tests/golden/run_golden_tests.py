#!/usr/bin/env python3
"""
Golden test runner for hybrid parsing pipeline (Task 26.5).
Validates the 5 comprehensive test cases and logs parsing paths and confidence.
"""

import sys
import logging
from datetime import datetime
from services.hybrid_event_parser import HybridEventParser
from services.event_parser import EventParser

# Configure detailed logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def run_golden_tests():
    """Run the 5 golden test cases with detailed logging."""
    
    print("=" * 80)
    print("HYBRID PARSING PIPELINE - GOLDEN TEST SUITE (Task 26.5)")
    print("=" * 80)
    
    # Fixed current time for consistent testing
    current_time = datetime(2025, 9, 29, 17, 0, 0)  # Sept 29, 2025 5:00 PM
    
    # Initialize parsers
    hybrid_parser = HybridEventParser(current_time=current_time)
    event_parser = EventParser()
    
    # Enable hybrid parsing and telemetry
    hybrid_parser.update_config(enable_telemetry=True)
    event_parser.set_config(use_hybrid_parsing=True, hybrid_mode="hybrid")
    
    # Golden test cases
    golden_cases = [
        {
            "name": "Golden Case 1: Title with Due Date (All-day)",
            "text": "Title: COWA! Due Date: Oct 15, 2025",
            "expected_confidence": 0.8,
            "expected_path": ["regex_then_llm", "regex_only"],
            "expected_all_day": True
        },
        {
            "name": "Golden Case 2: Lunch with Person (Timed)",
            "text": "Lunch with Sarah Friday at 12pm",
            "expected_confidence": 0.7,
            "expected_path": ["regex_then_llm", "regex_only"],
            "expected_all_day": False
        },
        {
            "name": "Golden Case 3: Dentist Appointment (Timed)",
            "text": "Dentist Oct 1 @ 9:30",
            "expected_confidence": 0.8,
            "expected_path": ["regex_then_llm", "regex_only"],
            "expected_all_day": False
        },
        {
            "name": "Golden Case 4: Pick up Passport (All-day, current year)",
            "text": "Pick up passport on 10/02",
            "expected_confidence": 0.7,
            "expected_path": ["regex_then_llm", "regex_only"],
            "expected_all_day": None  # Could be all-day or default time
        },
        {
            "name": "Golden Case 5: Tomorrow Relative Time",
            "text": "Tomorrow 7am",
            "expected_confidence": 0.8,
            "expected_path": ["regex_then_llm", "regex_only"],
            "expected_all_day": False
        }
    ]
    
    results = []
    
    for i, case in enumerate(golden_cases, 1):
        print(f"\n{'-' * 60}")
        print(f"TEST {i}: {case['name']}")
        print(f"Text: '{case['text']}'")
        print(f"{'-' * 60}")
        
        try:
            # Run hybrid parsing
            result = hybrid_parser.parse_event_text(
                text=case['text'],
                mode="hybrid",
                current_time=current_time
            )
            
            # Log results
            print(f"✓ Parsing Path: {result.parsing_path}")
            print(f"✓ Confidence Score: {result.confidence_score:.3f}")
            print(f"✓ Warnings: {len(result.warnings)}")
            
            if result.warnings:
                for warning in result.warnings:
                    print(f"  ⚠️  {warning}")
            
            # Event details
            event = result.parsed_event
            print(f"✓ Title: '{event.title}'")
            print(f"✓ Start DateTime: {event.start_datetime}")
            print(f"✓ End DateTime: {event.end_datetime}")
            print(f"✓ All Day: {event.all_day}")
            print(f"✓ Location: {event.location}")
            
            # Collect telemetry
            telemetry = hybrid_parser.collect_telemetry(case['text'], result)
            print(f"✓ Telemetry:")
            for key, value in telemetry.items():
                print(f"  - {key}: {value}")
            
            # Validate expectations
            validation_results = []
            
            # Check confidence
            if result.confidence_score >= case['expected_confidence']:
                validation_results.append("✅ Confidence meets threshold")
            else:
                validation_results.append(f"❌ Confidence below threshold: {result.confidence_score:.3f} < {case['expected_confidence']}")
            
            # Check parsing path
            if result.parsing_path in case['expected_path']:
                validation_results.append("✅ Parsing path as expected")
            else:
                validation_results.append(f"❌ Unexpected parsing path: {result.parsing_path} not in {case['expected_path']}")
            
            # Check all-day if specified
            if case['expected_all_day'] is not None:
                if event.all_day == case['expected_all_day']:
                    validation_results.append("✅ All-day setting correct")
                else:
                    validation_results.append(f"❌ All-day mismatch: {event.all_day} != {case['expected_all_day']}")
            
            # Check basic extraction
            if event.start_datetime:
                validation_results.append("✅ DateTime extracted")
            else:
                validation_results.append("❌ No DateTime extracted")
            
            if event.title:
                validation_results.append("✅ Title extracted")
            else:
                validation_results.append("❌ No title extracted")
            
            print(f"\n📊 Validation Results:")
            for validation in validation_results:
                print(f"  {validation}")
            
            # Overall result
            passed = all("✅" in v for v in validation_results)
            results.append({
                'case': case['name'],
                'passed': passed,
                'confidence': result.confidence_score,
                'path': result.parsing_path,
                'validations': validation_results
            })
            
            if passed:
                print(f"\n🎉 TEST {i} PASSED")
            else:
                print(f"\n💥 TEST {i} FAILED")
        
        except Exception as e:
            print(f"\n💥 TEST {i} ERROR: {e}")
            results.append({
                'case': case['name'],
                'passed': False,
                'error': str(e)
            })
    
    # Summary
    print(f"\n{'=' * 80}")
    print("GOLDEN TEST SUITE SUMMARY")
    print(f"{'=' * 80}")
    
    passed_count = sum(1 for r in results if r['passed'])
    total_count = len(results)
    
    print(f"Tests Passed: {passed_count}/{total_count}")
    print(f"Success Rate: {passed_count/total_count*100:.1f}%")
    
    for i, result in enumerate(results, 1):
        status = "✅ PASS" if result['passed'] else "❌ FAIL"
        print(f"  {i}. {status} - {result['case']}")
        if not result['passed'] and 'error' in result:
            print(f"     Error: {result['error']}")
    
    # Test EventParser integration
    print(f"\n{'-' * 60}")
    print("TESTING EVENTPARSER INTEGRATION")
    print(f"{'-' * 60}")
    
    try:
        test_text = "Meeting tomorrow at 2pm"
        parsed_event = event_parser.parse_event_text(test_text, current_time=current_time)
        
        print(f"✓ Integration test text: '{test_text}'")
        print(f"✓ Hybrid parsing used: {parsed_event.extraction_metadata.get('hybrid_parsing_used')}")
        print(f"✓ Parsing path: {parsed_event.extraction_metadata.get('parsing_path')}")
        print(f"✓ Confidence: {parsed_event.confidence_score:.3f}")
        print(f"✓ Title: '{parsed_event.title}'")
        print(f"✓ DateTime: {parsed_event.start_datetime}")
        
        if parsed_event.extraction_metadata.get('hybrid_parsing_used'):
            print("🎉 EVENTPARSER INTEGRATION PASSED")
        else:
            print("💥 EVENTPARSER INTEGRATION FAILED")
    
    except Exception as e:
        print(f"💥 EVENTPARSER INTEGRATION ERROR: {e}")
    
    # Final status
    if passed_count == total_count:
        print(f"\n🎉 ALL GOLDEN TESTS PASSED! Hybrid parsing pipeline is working correctly.")
        return True
    else:
        print(f"\n💥 {total_count - passed_count} GOLDEN TESTS FAILED. Please review the implementation.")
        return False


if __name__ == "__main__":
    success = run_golden_tests()
    sys.exit(0 if success else 1)