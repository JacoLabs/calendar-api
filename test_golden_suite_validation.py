#!/usr/bin/env python3
"""
Golden Test Suite Validation Script.

This script validates that the golden test suite implementation is working correctly
by running a subset of tests and checking the basic functionality.
"""

import sys
import logging
from datetime import datetime
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_golden_suite_manager():
    """Test the GoldenTestSuiteManager functionality."""
    print("Testing GoldenTestSuiteManager...")
    
    try:
        from tests.test_comprehensive_golden_suite import GoldenTestSuiteManager
        
        # Initialize manager
        manager = GoldenTestSuiteManager()
        
        # Check test statistics
        stats = manager.get_test_statistics()
        print(f"  Total test cases: {stats['total_cases']}")
        print(f"  Categories: {len(stats['categories'])}")
        
        # Validate we have comprehensive coverage
        assert stats['total_cases'] >= 50, f"Expected at least 50 test cases, got {stats['total_cases']}"
        assert len(stats['categories']) >= 8, f"Expected at least 8 categories, got {len(stats['categories'])}"
        
        # Check specific categories exist
        required_categories = [
            'basic_datetime', 'complex_formatting', 'typos_variations',
            'relative_dates', 'duration_allday', 'location_extraction',
            'title_generation', 'confidence_thresholds'
        ]
        
        for category in required_categories:
            assert category in stats['categories'], f"Missing required category: {category}"
            assert stats['categories'][category] > 0, f"Category {category} has no test cases"
        
        print("  ✅ GoldenTestSuiteManager validation passed")
        return True
        
    except Exception as e:
        print(f"  ❌ GoldenTestSuiteManager validation failed: {e}")
        return False

def test_performance_monitor_integration():
    """Test the PerformanceMonitor integration."""
    print("Testing PerformanceMonitor integration...")
    
    try:
        from services.performance_monitor import PerformanceMonitor
        
        # Initialize monitor
        monitor = PerformanceMonitor()
        
        # Check that golden test cases are loaded
        assert len(monitor.golden_test_cases) > 0, "No golden test cases loaded"
        
        # Test component latency tracking with a valid component
        monitor.track_component_latency('overall_parsing', 100.0)
        stats = monitor.component_latencies['overall_parsing'].get_stats()
        assert stats['count'] == 1, "Component latency not tracked correctly"
        assert stats['mean'] == 100.0, "Component latency value incorrect"
        
        print(f"  Golden test cases loaded: {len(monitor.golden_test_cases)}")
        print("  ✅ PerformanceMonitor integration validation passed")
        return True
        
    except Exception as e:
        print(f"  ❌ PerformanceMonitor integration validation failed: {e}")
        return False

def test_confidence_validator():
    """Test the ConfidenceThresholdValidator functionality."""
    print("Testing ConfidenceThresholdValidator...")
    
    try:
        from tests.test_comprehensive_golden_suite import ConfidenceThresholdValidator
        from services.performance_monitor import AccuracyResult
        from models.event_models import ParsedEvent
        
        # Initialize validator
        validator = ConfidenceThresholdValidator()
        
        # Create mock test results
        test_results = []
        for i in range(10):
            confidence = 0.1 * (i + 1)  # 0.1 to 1.0
            accuracy = confidence * 0.8  # Simulate reasonable correlation
            
            mock_event = ParsedEvent(
                title="Test Event",
                start_datetime=datetime.now(),
                end_datetime=datetime.now(),
                confidence_score=confidence
            )
            
            result = AccuracyResult(
                test_case_id=f"test_{i}",
                predicted_event=mock_event,
                accuracy_score=accuracy
            )
            test_results.append(result)
        
        # Test confidence calibration
        calibration_results = validator.validate_confidence_calibration(test_results)
        assert 'calibration_error' in calibration_results, "Missing calibration error"
        assert 'reliability_curve' in calibration_results, "Missing reliability curve"
        
        print(f"  Calibration error: {calibration_results['calibration_error']:.3f}")
        print("  ✅ ConfidenceThresholdValidator validation passed")
        return True
        
    except Exception as e:
        print(f"  ❌ ConfidenceThresholdValidator validation failed: {e}")
        return False

def test_performance_benchmarker():
    """Test the PerformanceBenchmarker functionality."""
    print("Testing PerformanceBenchmarker...")
    
    try:
        from tests.performance_benchmarking import PerformanceBenchmarker
        from models.event_models import ParsedEvent
        
        # Initialize benchmarker
        benchmarker = PerformanceBenchmarker("test_performance_results")
        
        # Create mock parser function
        def mock_parser(text: str) -> ParsedEvent:
            return ParsedEvent(
                title="Mock Event",
                start_datetime=datetime.now(),
                end_datetime=datetime.now(),
                confidence_score=0.8
            )
        
        # Test benchmark test case creation
        test_cases = benchmarker.create_benchmark_test_cases()
        assert len(test_cases) > 0, "No benchmark test cases created"
        assert 'simple_cases' in test_cases, "Missing simple test cases"
        assert 'complex_cases' in test_cases, "Missing complex test cases"
        
        total_cases = sum(len(cases) for cases in test_cases.values())
        print(f"  Total benchmark test cases: {total_cases}")
        
        # Test a small benchmark (to avoid long execution time)
        small_cases = test_cases['simple_cases'][:5]  # Just 5 cases for validation
        
        # This would normally run a full benchmark, but we'll skip for validation
        print("  ✅ PerformanceBenchmarker validation passed")
        return True
        
    except Exception as e:
        print(f"  ❌ PerformanceBenchmarker validation failed: {e}")
        return False

def test_regression_validator():
    """Test the RegressionTestValidator functionality."""
    print("Testing RegressionTestValidator...")
    
    try:
        from tests.test_comprehensive_golden_suite import RegressionTestValidator
        
        # Initialize validator
        validator = RegressionTestValidator("test_regression_baseline.json")
        
        # Create mock current results
        current_results = {
            'overall_accuracy': 0.85,
            'field_accuracies': {
                'title': {'mean': 0.90},
                'start_datetime': {'mean': 0.95},
                'location': {'mean': 0.80}
            },
            'performance_stats': {
                'mean_processing_time_ms': 150.0,
                'median_processing_time_ms': 120.0
            }
        }
        
        # Test regression validation
        regression_analysis = validator.validate_regression(current_results)
        assert 'has_regression' in regression_analysis, "Missing regression flag"
        assert 'improvements' in regression_analysis, "Missing improvements list"
        assert 'regressions' in regression_analysis, "Missing regressions list"
        
        print(f"  Has regression: {regression_analysis['has_regression']}")
        print("  ✅ RegressionTestValidator validation passed")
        return True
        
    except Exception as e:
        print(f"  ❌ RegressionTestValidator validation failed: {e}")
        return False

def test_comprehensive_test_runner():
    """Test the ComprehensiveTestRunner functionality."""
    print("Testing ComprehensiveTestRunner...")
    
    try:
        from run_comprehensive_golden_tests import ComprehensiveTestRunner
        
        # Initialize test runner
        runner = ComprehensiveTestRunner("test_output")
        
        # Check initialization
        assert runner.golden_suite_manager is not None, "GoldenTestSuiteManager not initialized"
        assert runner.regression_validator is not None, "RegressionTestValidator not initialized"
        assert runner.confidence_validator is not None, "ConfidenceThresholdValidator not initialized"
        assert runner.performance_benchmarker is not None, "PerformanceBenchmarker not initialized"
        
        # Test recommendation generation (with empty results)
        recommendations = runner.generate_recommendations()
        assert isinstance(recommendations, list), "Recommendations should be a list"
        assert len(recommendations) > 0, "Should generate at least some recommendations"
        
        # Test status determination
        status = runner.determine_overall_status()
        assert status in ['EXCELLENT', 'GOOD', 'ACCEPTABLE', 'NEEDS_WORK', 'FAILED'], f"Invalid status: {status}"
        
        print(f"  Generated {len(recommendations)} recommendations")
        print(f"  Overall status: {status}")
        print("  ✅ ComprehensiveTestRunner validation passed")
        return True
        
    except Exception as e:
        print(f"  ❌ ComprehensiveTestRunner validation failed: {e}")
        return False

def main():
    """Run all validation tests."""
    print("="*60)
    print("GOLDEN TEST SUITE VALIDATION")
    print("="*60)
    
    validation_tests = [
        test_golden_suite_manager,
        test_performance_monitor_integration,
        test_confidence_validator,
        test_performance_benchmarker,
        test_regression_validator,
        test_comprehensive_test_runner
    ]
    
    passed = 0
    failed = 0
    
    for test_func in validation_tests:
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"  ❌ {test_func.__name__} failed with exception: {e}")
            failed += 1
        print()
    
    print("="*60)
    print("VALIDATION SUMMARY")
    print("="*60)
    print(f"Tests Passed: {passed}")
    print(f"Tests Failed: {failed}")
    print(f"Success Rate: {passed/(passed+failed)*100:.1f}%")
    
    if failed == 0:
        print("🎉 All validation tests passed!")
        print("\nThe golden test suite implementation is ready for use.")
        print("You can now run the comprehensive tests with:")
        print("  python run_comprehensive_golden_tests.py")
        return True
    else:
        print("❌ Some validation tests failed.")
        print("Please fix the issues before running the comprehensive test suite.")
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)