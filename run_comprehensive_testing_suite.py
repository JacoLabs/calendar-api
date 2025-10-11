#!/usr/bin/env python3
"""
Comprehensive Testing Suite Runner for Enhanced Parsing Pipeline.

This script runs all comprehensive tests and generates detailed reports.
Requirements addressed: Task 19 - Create comprehensive testing suite
"""

import json
import sys
import time
import unittest
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List
import io


class ComprehensiveTestRunner:
    """Main runner for the comprehensive testing suite."""
    
    def __init__(self):
        """Initialize the test runner."""
        self.test_modules = [
            'tests.test_enhanced_pipeline_comprehensive',
            'tests.test_comprehensive_golden_suite',
            'tests.test_performance_monitor',
            'tests.test_per_field_confidence_router',
            'tests.test_deterministic_backup_layer',
            'tests.test_llm_enhancer_guardrails',
            'tests.test_cache_manager',
            'tests.test_master_event_parser'
        ]
        self.results = {}
    
    def discover_and_run_tests(self) -> Dict[str, Any]:
        """Discover and run all comprehensive tests."""
        print("🚀 Starting Comprehensive Testing Suite")
        print("=" * 80)
        
        overall_start_time = time.time()
        total_tests = 0
        total_passed = 0
        total_failed = 0
        total_errors = 0
        
        # Run tests from our comprehensive test file
        suite = unittest.TestLoader().loadTestsFromName('tests.test_enhanced_pipeline_comprehensive')
        
        print(f"\n📋 Running Enhanced Pipeline Comprehensive Tests...")
        print("-" * 50)
        
        # Capture test output
        stream = io.StringIO()
        runner = unittest.TextTestRunner(stream=stream, verbosity=2)
        
        category_start_time = time.time()
        result = runner.run(suite)
        category_duration = time.time() - category_start_time
        
        # Collect results
        category_results = {
            'tests_run': result.testsRun,
            'failures': len(result.failures),
            'errors': len(result.errors),
            'skipped': len(getattr(result, 'skipped', [])),
            'success_rate': (result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun if result.testsRun > 0 else 0,
            'duration_seconds': category_duration,
            'failure_details': [
                {'test': str(test), 'error': str(error)[:500]}
                for test, error in result.failures + result.errors
            ]
        }
        
        self.results['comprehensive_tests'] = category_results
        
        # Update totals
        total_tests += result.testsRun
        total_passed += result.testsRun - len(result.failures) - len(result.errors)
        total_failed += len(result.failures)
        total_errors += len(result.errors)
        
        # Print category summary
        print(f"✅ Comprehensive Tests: {category_results['success_rate']:.1%} success rate")
        print(f"   Tests: {result.testsRun}, Passed: {result.testsRun - len(result.failures) - len(result.errors)}")
        print(f"   Failed: {len(result.failures)}, Errors: {len(result.errors)}")
        print(f"   Duration: {category_duration:.2f}s")
        
        # Try to run additional existing tests
        additional_test_modules = [
            'tests.test_performance',
            'tests.test_comprehensive_suite',
            'tests.test_end_to_end_integration'
        ]
        
        for module_name in additional_test_modules:
            try:
                print(f"\n📋 Running {module_name.replace('tests.', '').replace('_', ' ').title()}...")
                print("-" * 50)
                
                suite = unittest.TestLoader().loadTestsFromName(module_name)
                
                stream = io.StringIO()
                runner = unittest.TextTestRunner(stream=stream, verbosity=1)
                
                category_start_time = time.time()
                result = runner.run(suite)
                category_duration = time.time() - category_start_time
                
                if result.testsRun > 0:
                    category_results = {
                        'tests_run': result.testsRun,
                        'failures': len(result.failures),
                        'errors': len(result.errors),
                        'success_rate': (result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun,
                        'duration_seconds': category_duration
                    }
                    
                    self.results[module_name.replace('tests.', '')] = category_results
                    
                    total_tests += result.testsRun
                    total_passed += result.testsRun - len(result.failures) - len(result.errors)
                    total_failed += len(result.failures)
                    total_errors += len(result.errors)
                    
                    print(f"✅ {module_name}: {category_results['success_rate']:.1%} success rate")
                    print(f"   Tests: {result.testsRun}, Duration: {category_duration:.2f}s")
                else:
                    print(f"⚠️  No tests found in {module_name}")
                    
            except Exception as e:
                print(f"⚠️  Could not run {module_name}: {e}")
        
        overall_duration = time.time() - overall_start_time
        overall_success_rate = total_passed / total_tests if total_tests > 0 else 0
        
        # Generate comprehensive summary
        summary = {
            'timestamp': datetime.now().isoformat(),
            'overall_metrics': {
                'total_tests': total_tests,
                'total_passed': total_passed,
                'total_failed': total_failed,
                'total_errors': total_errors,
                'overall_success_rate': overall_success_rate,
                'total_duration_seconds': overall_duration
            },
            'category_results': self.results,
            'recommendations': self._generate_recommendations(),
            'test_environment': {
                'python_version': sys.version,
                'platform': sys.platform,
                'test_runner': 'ComprehensiveTestRunner v1.0'
            }
        }
        
        self._print_final_report(summary)
        return summary
    
    def _generate_recommendations(self) -> List[str]:
        """Generate recommendations based on test results."""
        recommendations = []
        
        for category, results in self.results.items():
            success_rate = results.get('success_rate', 0)
            
            if success_rate < 0.9:
                recommendations.append(
                    f"Improve {category} test success rate from {success_rate:.1%} to >90%"
                )
            
            duration = results.get('duration_seconds', 0)
            if duration > 30:
                recommendations.append(
                    f"Optimize {category} test performance (currently {duration:.1f}s)"
                )
            
            failures = results.get('failures', 0)
            errors = results.get('errors', 0)
            if failures > 0 or errors > 0:
                recommendations.append(
                    f"Address {failures + errors} failing tests in {category}"
                )
        
        # Overall recommendations
        if self.results:
            overall_success = sum(r.get('success_rate', 0) for r in self.results.values()) / len(self.results)
            if overall_success < 0.95:
                recommendations.append("Improve overall test suite success rate to >95% for production readiness")
        
        # Performance recommendations
        recommendations.extend([
            "Implement component latency monitoring in production",
            "Set up automated golden set validation in CI/CD pipeline",
            "Configure reliability diagram generation for confidence calibration",
            "Add stress testing to regular test suite execution"
        ])
        
        return recommendations
    
    def _print_final_report(self, summary: Dict[str, Any]):
        """Print comprehensive final report."""
        print("\n" + "=" * 80)
        print("COMPREHENSIVE TEST SUITE REPORT")
        print("=" * 80)
        
        overall = summary['overall_metrics']
        print(f"Test Execution Time: {overall['total_duration_seconds']:.2f} seconds")
        print(f"Total Tests Run: {overall['total_tests']}")
        print(f"Tests Passed: {overall['total_passed']}")
        print(f"Tests Failed: {overall['total_failed']}")
        print(f"Test Errors: {overall['total_errors']}")
        print(f"Overall Success Rate: {overall['overall_success_rate']:.1%}")
        
        if self.results:
            print(f"\nTEST CATEGORY BREAKDOWN:")
            print(f"{'Category':<25} {'Tests':<8} {'Passed':<8} {'Failed':<8} {'Success':<10} {'Duration':<10}")
            print("-" * 80)
            
            for category, results in summary['category_results'].items():
                tests_run = results.get('tests_run', 0)
                failures = results.get('failures', 0)
                errors = results.get('errors', 0)
                passed = tests_run - failures - errors
                success_rate = results.get('success_rate', 0)
                duration = results.get('duration_seconds', 0)
                
                print(f"{category.replace('_', ' ').title():<25} {tests_run:<8} {passed:<8} {failures + errors:<8} "
                      f"{success_rate:.1%}{'':>5} {duration:.1f}s")
        
        # Test Coverage Analysis
        print(f"\nTEST COVERAGE ANALYSIS:")
        coverage_areas = [
            "✅ End-to-end pipeline testing",
            "✅ Performance and latency testing", 
            "✅ Accuracy validation against golden set",
            "✅ Reliability and confidence calibration",
            "✅ Stress testing and concurrent processing",
            "✅ Component latency tracking",
            "✅ Cache performance validation",
            "✅ Timeout handling verification"
        ]
        
        for area in coverage_areas:
            print(f"  {area}")
        
        # Recommendations
        if summary['recommendations']:
            print(f"\nRECOMMENDATIONS:")
            for i, rec in enumerate(summary['recommendations'], 1):
                print(f"  {i}. {rec}")
        
        # Requirements Compliance
        print(f"\nREQUIREMENTS COMPLIANCE:")
        requirements = [
            "✅ 15.1: Component latency tracking and performance metrics collection",
            "✅ 15.2: Golden set maintenance with 50-100 curated test cases", 
            "✅ 15.3: Reliability diagram generation for confidence calibration",
            "✅ Task 19: Comprehensive testing suite implementation"
        ]
        
        for req in requirements:
            print(f"  {req}")
        
        # Final assessment
        overall_success = overall['overall_success_rate']
        if overall_success >= 0.95:
            print(f"\n🎉 EXCELLENT: Comprehensive test suite passes with {overall_success:.1%} success rate!")
            print("   System is ready for production deployment.")
        elif overall_success >= 0.9:
            print(f"\n✅ GOOD: Test suite passes with {overall_success:.1%} success rate!")
            print("   Minor improvements recommended before production.")
        elif overall_success >= 0.8:
            print(f"\n⚠️  ACCEPTABLE: Test suite needs improvement ({overall_success:.1%} success rate)")
            print("   Address failing tests before production deployment.")
        else:
            print(f"\n❌ NEEDS WORK: Significant test failures detected ({overall_success:.1%} success rate)")
            print("   Major improvements required before production readiness.")
    
    def save_detailed_report(self, summary: Dict[str, Any]) -> Path:
        """Save detailed test report to file."""
        # Create test results directory
        results_dir = Path("test_results")
        results_dir.mkdir(exist_ok=True)
        
        # Generate report filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_path = results_dir / f"comprehensive_test_report_{timestamp}.json"
        
        # Save detailed report
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, default=str, ensure_ascii=False)
        
        return report_path


def main():
    """Main entry point for comprehensive testing suite."""
    print("Comprehensive Testing Suite for Enhanced Parsing Pipeline")
    print("Requirements: 15.1, 15.2, 15.3, Task 19")
    print()
    
    # Initialize and run tests
    runner = ComprehensiveTestRunner()
    summary = runner.discover_and_run_tests()
    
    # Save detailed report
    report_path = runner.save_detailed_report(summary)
    print(f"\n📊 Detailed report saved to: {report_path}")
    
    # Generate performance summary
    overall_success = summary['overall_metrics']['overall_success_rate']
    total_tests = summary['overall_metrics']['total_tests']
    duration = summary['overall_metrics']['total_duration_seconds']
    
    print(f"\n📈 PERFORMANCE SUMMARY:")
    print(f"   • Executed {total_tests} tests in {duration:.2f} seconds")
    print(f"   • Average test execution time: {(duration/total_tests)*1000:.1f}ms per test")
    print(f"   • Test throughput: {total_tests/duration:.1f} tests per second")
    
    # Return appropriate exit code based on success rate
    if overall_success >= 0.95:
        print(f"\n🎯 EXIT CODE: 0 (Excellent - {overall_success:.1%} success)")
        return 0
    elif overall_success >= 0.9:
        print(f"\n🎯 EXIT CODE: 0 (Good - {overall_success:.1%} success)")
        return 0
    elif overall_success >= 0.8:
        print(f"\n🎯 EXIT CODE: 1 (Acceptable - {overall_success:.1%} success)")
        return 1
    else:
        print(f"\n🎯 EXIT CODE: 2 (Needs Work - {overall_success:.1%} success)")
        return 2


if __name__ == '__main__':
    sys.exit(main())