#!/usr/bin/env python3
"""
Comprehensive Golden Test Suite Runner.

This script runs the complete golden test suite including:
- Comprehensive test cases covering all parsing scenarios
- Regression testing for parsing accuracy improvements
- Test validation for confidence thresholds and warning flags
- Automated accuracy evaluation against golden set
- Performance benchmarking and latency profiling

Requirements addressed:
- Task 16: Create golden test suite and validation
- 15.2: Golden set maintenance with 50-100 curated test cases
- 15.3: Reliability diagram generation for confidence calibration
"""

import argparse
import json
import logging
import sys
import time
import unittest
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Callable

# Import test modules
from tests.test_comprehensive_golden_suite import (
    ComprehensiveGoldenTestSuite,
    GoldenTestSuiteManager,
    RegressionTestValidator,
    ConfidenceThresholdValidator
)
from tests.performance_benchmarking import PerformanceBenchmarker
from services.performance_monitor import PerformanceMonitor
from services.event_parser import EventParser

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ComprehensiveTestRunner:
    """
    Comprehensive test runner that orchestrates all golden test suite components.
    """
    
    def __init__(self, output_dir: str = "test_results"):
        """Initialize the comprehensive test runner."""
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        # Initialize components
        self.golden_suite_manager = GoldenTestSuiteManager()
        self.regression_validator = RegressionTestValidator()
        self.confidence_validator = ConfidenceThresholdValidator()
        self.performance_benchmarker = PerformanceBenchmarker(str(self.output_dir / "performance"))
        self.performance_monitor = PerformanceMonitor()
        
        # Test results storage
        self.test_results = {
            'timestamp': datetime.now().isoformat(),
            'test_suite_stats': {},
            'accuracy_results': {},
            'regression_analysis': {},
            'confidence_validation': {},
            'performance_benchmarks': {},
            'recommendations': [],
            'overall_status': 'UNKNOWN'
        }
        
        logger.info(f"ComprehensiveTestRunner initialized with output directory: {self.output_dir}")
    
    def run_golden_test_suite(self) -> bool:
        """
        Run the comprehensive golden test suite.
        
        Returns:
            True if all tests pass, False otherwise
        """
        print(f"\n{'='*80}")
        print("RUNNING COMPREHENSIVE GOLDEN TEST SUITE")
        print(f"{'='*80}")
        
        # Get test suite statistics
        test_stats = self.golden_suite_manager.get_test_statistics()
        self.test_results['test_suite_stats'] = test_stats
        
        print(f"Total Test Cases: {test_stats['total_cases']}")
        print(f"Categories: {len(test_stats['categories'])}")
        
        for category, count in test_stats['categories'].items():
            print(f"  {category}: {count} cases")
        
        # Run unittest suite
        suite = unittest.TestLoader().loadTestsFromTestCase(ComprehensiveGoldenTestSuite)
        runner = unittest.TextTestRunner(verbosity=2, stream=sys.stdout)
        
        start_time = time.time()
        result = runner.run(suite)
        end_time = time.time()
        
        # Process results
        test_duration = end_time - start_time
        success_rate = ((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100) if result.testsRun > 0 else 0
        
        self.test_results['golden_suite_results'] = {
            'tests_run': result.testsRun,
            'failures': len(result.failures),
            'errors': len(result.errors),
            'success_rate': success_rate,
            'duration_seconds': test_duration,
            'failure_details': [{'test': str(test), 'error': error} for test, error in result.failures],
            'error_details': [{'test': str(test), 'error': error} for test, error in result.errors]
        }
        
        print(f"\nGolden Test Suite Results:")
        print(f"  Tests Run: {result.testsRun}")
        print(f"  Failures: {len(result.failures)}")
        print(f"  Errors: {len(result.errors)}")
        print(f"  Success Rate: {success_rate:.1f}%")
        print(f"  Duration: {test_duration:.2f}s")
        
        return len(result.failures) == 0 and len(result.errors) == 0
    
    def run_accuracy_evaluation(self) -> Dict[str, Any]:
        """
        Run automated accuracy evaluation against golden set.
        
        Returns:
            Dictionary with accuracy evaluation results
        """
        print(f"\n{'='*60}")
        print("RUNNING ACCURACY EVALUATION")
        print(f"{'='*60}")
        
        # Initialize parser
        event_parser = EventParser()
        
        def parser_func(text: str):
            return event_parser.parse_text(text)
        
        # Run accuracy evaluation
        accuracy_results = self.performance_monitor.evaluate_accuracy(parser_func)
        self.test_results['accuracy_results'] = accuracy_results
        
        print(f"Overall Accuracy: {accuracy_results.get('overall_accuracy', 0.0):.3f}")
        print(f"Total Test Cases: {accuracy_results.get('total_test_cases', 0)}")
        
        # Print field accuracies
        field_accuracies = accuracy_results.get('field_accuracies', {})
        if field_accuracies:
            print("\nField Accuracies:")
            for field, stats in field_accuracies.items():
                print(f"  {field}: {stats.get('mean', 0.0):.3f}")
        
        return accuracy_results
    
    def run_regression_testing(self, accuracy_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run regression testing against baseline.
        
        Args:
            accuracy_results: Results from accuracy evaluation
            
        Returns:
            Dictionary with regression analysis results
        """
        print(f"\n{'='*60}")
        print("RUNNING REGRESSION TESTING")
        print(f"{'='*60}")
        
        regression_analysis = self.regression_validator.validate_regression(accuracy_results)
        self.test_results['regression_analysis'] = regression_analysis
        
        print(f"Has Regression: {regression_analysis.get('has_regression', False)}")
        print(f"Improvements: {len(regression_analysis.get('improvements', []))}")
        print(f"Regressions: {len(regression_analysis.get('regressions', []))}")
        
        if regression_analysis.get('improvements'):
            print("\nImprovements:")
            for improvement in regression_analysis['improvements']:
                print(f"  ✅ {improvement}")
        
        if regression_analysis.get('regressions'):
            print("\nRegressions:")
            for regression in regression_analysis['regressions']:
                print(f"  ❌ {regression}")
        
        return regression_analysis
    
    def run_confidence_validation(self) -> Dict[str, Any]:
        """
        Run confidence threshold and warning flag validation.
        
        Returns:
            Dictionary with confidence validation results
        """
        print(f"\n{'='*60}")
        print("RUNNING CONFIDENCE VALIDATION")
        print(f"{'='*60}")
        
        # Get test results for confidence validation
        event_parser = EventParser()
        test_results = []
        
        # Test confidence threshold cases
        confidence_cases = self.golden_suite_manager.get_test_cases_by_category('confidence_thresholds')
        warning_cases = self.golden_suite_manager.get_test_cases_by_category('warning_flags')
        all_validation_cases = confidence_cases + warning_cases
        
        print(f"Testing {len(all_validation_cases)} validation cases...")
        
        for test_case in all_validation_cases:
            try:
                predicted_event = event_parser.parse_text(test_case.input_text)
                accuracy_result = self.performance_monitor._calculate_accuracy(test_case, predicted_event)
                test_results.append(accuracy_result)
            except Exception as e:
                logger.error(f"Error in confidence validation for {test_case.id}: {e}")
        
        # Validate confidence calibration
        calibration_results = self.confidence_validator.validate_confidence_calibration(test_results)
        
        # Validate warning flags
        warning_results = self.confidence_validator.validate_warning_flags(test_results)
        
        confidence_validation = {
            'calibration_results': calibration_results,
            'warning_results': warning_results,
            'total_validation_cases': len(all_validation_cases)
        }
        
        self.test_results['confidence_validation'] = confidence_validation
        
        print(f"Calibration Error: {calibration_results.get('calibration_error', 0.0):.3f}")
        print(f"Well Calibrated: {calibration_results.get('is_well_calibrated', False)}")
        print(f"Warning Accuracy: {warning_results.get('warning_accuracy', 0.0):.3f}")
        
        return confidence_validation
    
    def run_performance_benchmarking(self) -> Dict[str, Any]:
        """
        Run comprehensive performance benchmarking.
        
        Returns:
            Dictionary with performance benchmark results
        """
        print(f"\n{'='*60}")
        print("RUNNING PERFORMANCE BENCHMARKING")
        print(f"{'='*60}")
        
        # Initialize parsers
        event_parser = EventParser()
        parsers = {
            'EventParser': lambda text: event_parser.parse_text(text)
        }
        
        # Try to add hybrid parser if available
        try:
            from services.hybrid_event_parser import HybridEventParser
            hybrid_parser = HybridEventParser()
            parsers['HybridParser'] = lambda text: hybrid_parser.parse_event_text(text).parsed_event if hybrid_parser.parse_event_text(text) else None
        except Exception as e:
            logger.warning(f"Could not initialize HybridParser for benchmarking: {e}")
        
        benchmark_results = {}
        
        # Run benchmarks for each parser
        for parser_name, parser_func in parsers.items():
            print(f"\nBenchmarking {parser_name}...")
            
            # Comprehensive benchmark
            benchmark_result = self.performance_benchmarker.benchmark_parsing_performance(parser_func, parser_name)
            benchmark_results[f"{parser_name}_comprehensive"] = benchmark_result.to_dict()
            
            # Category-specific benchmarks
            category_results = self.performance_benchmarker.benchmark_category_performance(parser_func, parser_name)
            for category, result in category_results.items():
                benchmark_results[f"{parser_name}_{category}"] = result.to_dict()
        
        # Compare parsers if multiple available
        if len(parsers) > 1:
            comparison_results = self.performance_benchmarker.compare_parser_performance(parsers)
            benchmark_results['parser_comparison'] = comparison_results
        
        # Generate performance report
        performance_report = self.performance_benchmarker.generate_performance_report(
            str(self.output_dir / "performance_report.json")
        )
        
        # Generate performance plots
        self.performance_benchmarker.plot_performance_trends(str(self.output_dir))
        
        self.test_results['performance_benchmarks'] = benchmark_results
        
        return benchmark_results
    
    def generate_recommendations(self) -> List[str]:
        """
        Generate comprehensive recommendations based on all test results.
        
        Returns:
            List of recommendation strings
        """
        recommendations = []
        
        # Accuracy recommendations
        accuracy_results = self.test_results.get('accuracy_results', {})
        overall_accuracy = accuracy_results.get('overall_accuracy', 0.0)
        
        if overall_accuracy < 0.8:
            recommendations.append(f"Overall accuracy ({overall_accuracy:.3f}) is below 80% - review parsing algorithms")
        elif overall_accuracy < 0.9:
            recommendations.append(f"Overall accuracy ({overall_accuracy:.3f}) is good but could be improved")
        else:
            recommendations.append(f"Excellent overall accuracy ({overall_accuracy:.3f})")
        
        # Field-specific recommendations
        field_accuracies = accuracy_results.get('field_accuracies', {})
        for field, stats in field_accuracies.items():
            field_accuracy = stats.get('mean', 0.0)
            if field_accuracy < 0.7:
                recommendations.append(f"Low {field} accuracy ({field_accuracy:.3f}) - needs improvement")
        
        # Regression recommendations
        regression_analysis = self.test_results.get('regression_analysis', {})
        if regression_analysis.get('has_regression'):
            recommendations.append("Regressions detected - review recent changes")
            recommendations.extend(regression_analysis.get('recommendations', []))
        
        # Confidence validation recommendations
        confidence_validation = self.test_results.get('confidence_validation', {})
        calibration_results = confidence_validation.get('calibration_results', {})
        
        if not calibration_results.get('is_well_calibrated', True):
            recommendations.append("Confidence scores are poorly calibrated - review confidence calculation")
        
        warning_results = confidence_validation.get('warning_results', {})
        warning_accuracy = warning_results.get('warning_accuracy', 1.0)
        if warning_accuracy < 0.8:
            recommendations.append(f"Warning flag accuracy ({warning_accuracy:.3f}) is low - improve warning detection")
        
        # Performance recommendations
        performance_benchmarks = self.test_results.get('performance_benchmarks', {})
        
        # Check for slow performance
        slow_benchmarks = []
        for benchmark_name, result in performance_benchmarks.items():
            if isinstance(result, dict) and result.get('avg_time_ms', 0) > 500:
                slow_benchmarks.append(benchmark_name)
        
        if slow_benchmarks:
            recommendations.append(f"Slow performance detected in: {', '.join(slow_benchmarks)}")
        
        # Golden test suite recommendations
        golden_results = self.test_results.get('golden_suite_results', {})
        success_rate = golden_results.get('success_rate', 100.0)
        
        if success_rate < 95:
            recommendations.append(f"Golden test suite success rate ({success_rate:.1f}%) is below 95%")
        
        # General recommendations
        if not recommendations:
            recommendations.append("All tests passed successfully - system is performing well")
        
        recommendations.extend([
            "Continue monitoring performance in production",
            "Update golden test cases as new scenarios are discovered",
            "Run comprehensive tests before major releases"
        ])
        
        return recommendations
    
    def determine_overall_status(self) -> str:
        """
        Determine overall test status based on all results.
        
        Returns:
            Overall status string: EXCELLENT, GOOD, ACCEPTABLE, NEEDS_WORK, or FAILED
        """
        # Check golden test suite results
        golden_results = self.test_results.get('golden_suite_results', {})
        golden_success_rate = golden_results.get('success_rate', 0.0)
        
        if golden_success_rate < 80:
            return 'FAILED'
        
        # Check accuracy results
        accuracy_results = self.test_results.get('accuracy_results', {})
        overall_accuracy = accuracy_results.get('overall_accuracy', 0.0)
        
        # Check for regressions
        regression_analysis = self.test_results.get('regression_analysis', {})
        has_regression = regression_analysis.get('has_regression', False)
        
        # Check confidence validation
        confidence_validation = self.test_results.get('confidence_validation', {})
        calibration_results = confidence_validation.get('calibration_results', {})
        is_well_calibrated = calibration_results.get('is_well_calibrated', True)
        
        # Determine status
        if (golden_success_rate >= 98 and overall_accuracy >= 0.9 and 
            not has_regression and is_well_calibrated):
            return 'EXCELLENT'
        elif (golden_success_rate >= 95 and overall_accuracy >= 0.85 and 
              not has_regression):
            return 'GOOD'
        elif (golden_success_rate >= 90 and overall_accuracy >= 0.8):
            return 'ACCEPTABLE'
        elif golden_success_rate >= 80:
            return 'NEEDS_WORK'
        else:
            return 'FAILED'
    
    def save_comprehensive_report(self) -> str:
        """
        Save comprehensive test report to file.
        
        Returns:
            Path to saved report file
        """
        # Generate final recommendations and status
        self.test_results['recommendations'] = self.generate_recommendations()
        self.test_results['overall_status'] = self.determine_overall_status()
        
        # Save report
        report_path = self.output_dir / f"comprehensive_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        try:
            with open(report_path, 'w') as f:
                json.dump(self.test_results, f, indent=2, default=str)
            
            logger.info(f"Comprehensive test report saved to: {report_path}")
            return str(report_path)
        
        except Exception as e:
            logger.error(f"Could not save comprehensive test report: {e}")
            return ""
    
    def print_final_summary(self):
        """Print final test summary."""
        print(f"\n{'='*80}")
        print("COMPREHENSIVE GOLDEN TEST SUITE - FINAL SUMMARY")
        print(f"{'='*80}")
        
        # Overall status
        overall_status = self.test_results.get('overall_status', 'UNKNOWN')
        status_emoji = {
            'EXCELLENT': '🎉',
            'GOOD': '✅',
            'ACCEPTABLE': '⚠️',
            'NEEDS_WORK': '❌',
            'FAILED': '💥',
            'UNKNOWN': '❓'
        }
        
        print(f"Overall Status: {status_emoji.get(overall_status, '❓')} {overall_status}")
        
        # Key metrics
        accuracy_results = self.test_results.get('accuracy_results', {})
        overall_accuracy = accuracy_results.get('overall_accuracy', 0.0)
        
        golden_results = self.test_results.get('golden_suite_results', {})
        success_rate = golden_results.get('success_rate', 0.0)
        
        regression_analysis = self.test_results.get('regression_analysis', {})
        has_regression = regression_analysis.get('has_regression', False)
        
        print(f"\nKey Metrics:")
        print(f"  Overall Accuracy: {overall_accuracy:.3f}")
        print(f"  Golden Test Success Rate: {success_rate:.1f}%")
        print(f"  Has Regressions: {'Yes' if has_regression else 'No'}")
        
        # Test suite statistics
        test_stats = self.test_results.get('test_suite_stats', {})
        total_cases = test_stats.get('total_cases', 0)
        
        print(f"\nTest Suite Statistics:")
        print(f"  Total Golden Test Cases: {total_cases}")
        print(f"  Test Categories: {len(test_stats.get('categories', {}))}")
        
        # Performance summary
        performance_benchmarks = self.test_results.get('performance_benchmarks', {})
        if performance_benchmarks:
            print(f"  Performance Benchmarks: {len(performance_benchmarks)}")
        
        # Recommendations
        recommendations = self.test_results.get('recommendations', [])
        if recommendations:
            print(f"\nTop Recommendations:")
            for i, rec in enumerate(recommendations[:5], 1):
                print(f"  {i}. {rec}")
        
        print(f"\n{'='*80}")
    
    def run_comprehensive_tests(self, skip_performance: bool = False) -> bool:
        """
        Run all comprehensive tests.
        
        Args:
            skip_performance: Whether to skip performance benchmarking
            
        Returns:
            True if all tests pass acceptably, False otherwise
        """
        start_time = time.time()
        
        try:
            # 1. Run golden test suite
            golden_success = self.run_golden_test_suite()
            
            # 2. Run accuracy evaluation
            accuracy_results = self.run_accuracy_evaluation()
            
            # 3. Run regression testing
            regression_results = self.run_regression_testing(accuracy_results)
            
            # 4. Run confidence validation
            confidence_results = self.run_confidence_validation()
            
            # 5. Run performance benchmarking (optional)
            if not skip_performance:
                performance_results = self.run_performance_benchmarking()
            else:
                print(f"\n{'='*60}")
                print("SKIPPING PERFORMANCE BENCHMARKING")
                print(f"{'='*60}")
            
            # 6. Save comprehensive report
            report_path = self.save_comprehensive_report()
            
            # 7. Print final summary
            self.print_final_summary()
            
            end_time = time.time()
            total_duration = end_time - start_time
            
            print(f"\nTotal Test Duration: {total_duration:.2f} seconds")
            if report_path:
                print(f"Comprehensive Report: {report_path}")
            
            # Determine success
            overall_status = self.test_results.get('overall_status', 'FAILED')
            return overall_status in ['EXCELLENT', 'GOOD', 'ACCEPTABLE']
        
        except Exception as e:
            logger.error(f"Error running comprehensive tests: {e}")
            print(f"\n💥 COMPREHENSIVE TESTS FAILED: {e}")
            return False


def main():
    """Main entry point for comprehensive golden test suite."""
    parser = argparse.ArgumentParser(description='Run comprehensive golden test suite')
    parser.add_argument('--output-dir', default='test_results', 
                       help='Output directory for test results')
    parser.add_argument('--skip-performance', action='store_true',
                       help='Skip performance benchmarking (faster execution)')
    parser.add_argument('--verbose', action='store_true',
                       help='Enable verbose logging')
    
    args = parser.parse_args()
    
    # Configure logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Run comprehensive tests
    test_runner = ComprehensiveTestRunner(args.output_dir)
    success = test_runner.run_comprehensive_tests(skip_performance=args.skip_performance)
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()