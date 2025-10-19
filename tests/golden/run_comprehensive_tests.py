#!/usr/bin/env python3
"""
Comprehensive test runner for the text-to-calendar event system.
This script runs all tests and validates that all requirements are met.
"""

import sys
import os
import subprocess
import time
from pathlib import Path

def run_test_suite(test_name, test_file):
    """Run a specific test suite and return results."""
    print(f"\n{'='*60}")
    print(f"Running {test_name}")
    print(f"{'='*60}")
    
    try:
        start_time = time.time()
        result = subprocess.run([
            sys.executable, test_file
        ], capture_output=True, text=True, timeout=300)  # 5 minute timeout
        
        end_time = time.time()
        duration = end_time - start_time
        
        success = result.returncode == 0
        
        print(f"Duration: {duration:.2f} seconds")
        print(f"Return Code: {result.returncode}")
        
        if result.stdout:
            print("STDOUT:")
            print(result.stdout)
        
        if result.stderr:
            print("STDERR:")
            print(result.stderr)
        
        return {
            'name': test_name,
            'success': success,
            'duration': duration,
            'return_code': result.returncode,
            'stdout': result.stdout,
            'stderr': result.stderr
        }
        
    except subprocess.TimeoutExpired:
        print(f"❌ {test_name} timed out after 5 minutes")
        return {
            'name': test_name,
            'success': False,
            'duration': 300,
            'return_code': -1,
            'stdout': '',
            'stderr': 'Test timed out'
        }
    except Exception as e:
        print(f"❌ Error running {test_name}: {e}")
        return {
            'name': test_name,
            'success': False,
            'duration': 0,
            'return_code': -1,
            'stdout': '',
            'stderr': str(e)
        }

def main():
    """Main test runner."""
    print("🚀 Text-to-Calendar Event System - Comprehensive Test Suite")
    print("="*80)
    
    # Check if we're in the right directory
    if not os.path.exists('tests') or not os.path.exists('services'):
        print("❌ Error: Please run this script from the project root directory")
        print("   Expected to find 'tests' and 'services' directories")
        return 1
    
    # Define test suites to run
    test_suites = [
        ("Requirements Validation", "tests/test_comprehensive_validation.py"),
        ("Performance Tests", "tests/test_performance.py"),
        ("Test Data Scenarios", "tests/test_data_scenarios.py"),
        ("Integration Tests", "tests/test_integration_workflow.py"),
        ("Event Parser Tests", "tests/test_event_parser.py"),
        ("DateTime Parser Tests", "tests/test_datetime_parser.py"),
        ("Calendar Service Tests", "tests/test_calendar_service.py"),
        ("Event Models Tests", "tests/test_event_models.py"),
    ]
    
    # Run individual test suites
    results = []
    total_start_time = time.time()
    
    for test_name, test_file in test_suites:
        if os.path.exists(test_file):
            result = run_test_suite(test_name, test_file)
            results.append(result)
        else:
            print(f"⚠️  Warning: Test file not found: {test_file}")
            results.append({
                'name': test_name,
                'success': False,
                'duration': 0,
                'return_code': -1,
                'stdout': '',
                'stderr': f'Test file not found: {test_file}'
            })
    
    # Run comprehensive test suite if available
    comprehensive_suite = "tests/test_comprehensive_suite.py"
    if os.path.exists(comprehensive_suite):
        result = run_test_suite("Comprehensive Test Suite", comprehensive_suite)
        results.append(result)
    
    total_end_time = time.time()
    total_duration = total_end_time - total_start_time
    
    # Generate summary report
    print(f"\n{'='*80}")
    print("COMPREHENSIVE TEST SUMMARY")
    print(f"{'='*80}")
    
    successful_tests = sum(1 for r in results if r['success'])
    total_tests = len(results)
    success_rate = (successful_tests / total_tests * 100) if total_tests > 0 else 0
    
    print(f"Total Duration: {total_duration:.2f} seconds")
    print(f"Test Suites Run: {total_tests}")
    print(f"Successful: {successful_tests}")
    print(f"Failed: {total_tests - successful_tests}")
    print(f"Success Rate: {success_rate:.1f}%")
    
    # Detailed results
    print(f"\nDETAILED RESULTS:")
    print(f"{'Test Suite':<30} {'Status':<10} {'Duration':<10} {'Return Code'}")
    print("-" * 70)
    
    for result in results:
        status = "✅ PASS" if result['success'] else "❌ FAIL"
        duration = f"{result['duration']:.2f}s"
        return_code = result['return_code']
        
        print(f"{result['name']:<30} {status:<10} {duration:<10} {return_code}")
    
    # Failed tests details
    failed_tests = [r for r in results if not r['success']]
    if failed_tests:
        print(f"\nFAILED TESTS DETAILS:")
        print("-" * 50)
        for result in failed_tests:
            print(f"\n❌ {result['name']}:")
            if result['stderr']:
                print(f"   Error: {result['stderr'][:200]}...")
            if result['return_code'] != 0:
                print(f"   Return Code: {result['return_code']}")
    
    # Performance summary
    total_test_time = sum(r['duration'] for r in results)
    print(f"\nPERFORMANCE SUMMARY:")
    print(f"Total Test Execution Time: {total_test_time:.2f} seconds")
    print(f"Average Test Suite Duration: {total_test_time / total_tests:.2f} seconds")
    
    slowest_test = max(results, key=lambda r: r['duration'])
    print(f"Slowest Test Suite: {slowest_test['name']} ({slowest_test['duration']:.2f}s)")
    
    # Final assessment
    print(f"\nFINAL ASSESSMENT:")
    if success_rate >= 95:
        print("🎉 EXCELLENT: All test suites pass! System is ready for production.")
        final_status = 0
    elif success_rate >= 90:
        print("✅ GOOD: Most test suites pass. Minor issues to address.")
        final_status = 0
    elif success_rate >= 75:
        print("⚠️  ACCEPTABLE: Some test failures. Review and fix issues.")
        final_status = 1
    else:
        print("❌ NEEDS WORK: Significant test failures. Major issues to resolve.")
        final_status = 2
    
    # Recommendations
    print(f"\nRECOMMENDATIONS:")
    if failed_tests:
        print("• Fix failing test suites to improve system reliability")
    if total_test_time > 60:
        print("• Consider optimizing test performance for faster feedback")
    if success_rate < 100:
        print("• Aim for 100% test success rate before deployment")
    
    print(f"\n{'='*80}")
    print("Test run complete!")
    print(f"{'='*80}")
    
    return final_status

if __name__ == '__main__':
    sys.exit(main())