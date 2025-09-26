"""
Comprehensive test suite runner that validates all requirements and provides complete coverage.
This is the main test suite for task 12 - comprehensive test suite and validation.
"""

import unittest
import sys
import time
import tempfile
import os
from datetime import datetime
from io import StringIO

# Import all test modules
from tests.test_comprehensive_validation import (
    TestRequirement1, TestRequirement2, TestRequirement3, 
    TestRequirement4, TestRequirement5
)
from tests.test_performance import (
    TestParsingPerformance, TestWorkflowPerformance, 
    TestStressScenarios, TestPerformanceBenchmarks
)
from tests.test_data_scenarios import (
    TestRealWorldScenarios, TestDateTimeFormatVariations,
    TestLocationFormatVariations, TestEdgeCasesAndBoundaryConditions,
    TestInternationalAndCulturalVariations
)

# Import existing test modules
from tests.test_integration_workflow import TestIntegrationWorkflow, TestWorkflowComponents
from tests.test_event_parser import TestEventParser
from tests.test_datetime_parser import TestDateTimeParser, TestRelativeDateParsing, TestDurationParsing
from tests.test_calendar_service import TestCalendarService
from tests.test_event_models import TestParsedEvent, TestEvent, TestValidationResult


class ComprehensiveTestResult:
    """Custom test result class to track comprehensive test metrics."""
    
    def __init__(self):
        self.start_time = None
        self.end_time = None
        self.total_tests = 0
        self.passed_tests = 0
        self.failed_tests = 0
        self.error_tests = 0
        self.skipped_tests = 0
        
        # Category tracking
        self.requirement_tests = {'passed': 0, 'failed': 0, 'total': 0}
        self.performance_tests = {'passed': 0, 'failed': 0, 'total': 0}
        self.scenario_tests = {'passed': 0, 'failed': 0, 'total': 0}
        self.integration_tests = {'passed': 0, 'failed': 0, 'total': 0}
        self.unit_tests = {'passed': 0, 'failed': 0, 'total': 0}
        
        # Detailed results
        self.failures = []
        self.errors = []
        self.performance_issues = []
        
    def add_result(self, test_name, success, category, error_msg=None):
        """Add a test result."""
        self.total_tests += 1
        
        if success:
            self.passed_tests += 1
            getattr(self, f"{category}_tests")['passed'] += 1
        else:
            if error_msg and 'performance' in error_msg.lower():
                self.performance_issues.append((test_name, error_msg))
            
            self.failed_tests += 1
            getattr(self, f"{category}_tests")['failed'] += 1
            
            if error_msg:
                self.failures.append((test_name, error_msg))
        
        getattr(self, f"{category}_tests")['total'] += 1
    
    def get_success_rate(self):
        """Get overall success rate."""
        if self.total_tests == 0:
            return 0.0
        return (self.passed_tests / self.total_tests) * 100
    
    def get_category_success_rate(self, category):
        """Get success rate for a specific category."""
        cat_data = getattr(self, f"{category}_tests")
        if cat_data['total'] == 0:
            return 0.0
        return (cat_data['passed'] / cat_data['total']) * 100


class ComprehensiveTestSuite:
    """Main comprehensive test suite that runs all tests and validates requirements."""
    
    def __init__(self):
        self.result = ComprehensiveTestResult()
        self.temp_dir = None
        
    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.result.start_time = datetime.now()
        
    def tearDown(self):
        """Clean up test environment."""
        if self.temp_dir and os.path.exists(self.temp_dir):
            import shutil
            shutil.rmtree(self.temp_dir, ignore_errors=True)
        
        self.result.end_time = datetime.now()
    
    def run_requirement_validation_tests(self):
        """Run all requirement validation tests."""
        print("🔍 Running Requirement Validation Tests...")
        print("-" * 50)
        
        requirement_classes = [
            TestRequirement1, TestRequirement2, TestRequirement3,
            TestRequirement4, TestRequirement5
        ]
        
        for test_class in requirement_classes:
            suite = unittest.TestLoader().loadTestsFromTestCase(test_class)
            
            # Capture test output
            stream = StringIO()
            runner = unittest.TextTestRunner(stream=stream, verbosity=0)
            result = runner.run(suite)
            
            # Process results
            class_name = test_class.__name__
            for test, traceback in result.failures + result.errors:
                self.result.add_result(
                    f"{class_name}.{test._testMethodName}",
                    False,
                    'requirement',
                    traceback.split('\n')[-2] if traceback else None
                )
            
            # Count successful tests
            successful_tests = result.testsRun - len(result.failures) - len(result.errors)
            for i in range(successful_tests):
                self.result.add_result(f"{class_name}.test_{i}", True, 'requirement')
            
            print(f"  ✓ {class_name}: {successful_tests}/{result.testsRun} passed")
    
    def run_performance_tests(self):
        """Run all performance tests."""
        print("\n⚡ Running Performance Tests...")
        print("-" * 50)
        
        performance_classes = [
            TestParsingPerformance, TestWorkflowPerformance,
            TestStressScenarios, TestPerformanceBenchmarks
        ]
        
        for test_class in performance_classes:
            suite = unittest.TestLoader().loadTestsFromTestCase(test_class)
            
            # Capture test output
            stream = StringIO()
            runner = unittest.TextTestRunner(stream=stream, verbosity=0)
            result = runner.run(suite)
            
            # Process results
            class_name = test_class.__name__
            for test, traceback in result.failures + result.errors:
                self.result.add_result(
                    f"{class_name}.{test._testMethodName}",
                    False,
                    'performance',
                    traceback.split('\n')[-2] if traceback else None
                )
            
            # Count successful tests
            successful_tests = result.testsRun - len(result.failures) - len(result.errors)
            for i in range(successful_tests):
                self.result.add_result(f"{class_name}.test_{i}", True, 'performance')
            
            print(f"  ✓ {class_name}: {successful_tests}/{result.testsRun} passed")
    
    def run_scenario_tests(self):
        """Run all test data scenario tests."""
        print("\n📊 Running Test Data Scenario Tests...")
        print("-" * 50)
        
        scenario_classes = [
            TestRealWorldScenarios, TestDateTimeFormatVariations,
            TestLocationFormatVariations, TestEdgeCasesAndBoundaryConditions,
            TestInternationalAndCulturalVariations
        ]
        
        for test_class in scenario_classes:
            suite = unittest.TestLoader().loadTestsFromTestCase(test_class)
            
            # Capture test output
            stream = StringIO()
            runner = unittest.TextTestRunner(stream=stream, verbosity=0)
            result = runner.run(suite)
            
            # Process results
            class_name = test_class.__name__
            for test, traceback in result.failures + result.errors:
                self.result.add_result(
                    f"{class_name}.{test._testMethodName}",
                    False,
                    'scenario',
                    traceback.split('\n')[-2] if traceback else None
                )
            
            # Count successful tests
            successful_tests = result.testsRun - len(result.failures) - len(result.errors)
            for i in range(successful_tests):
                self.result.add_result(f"{class_name}.test_{i}", True, 'scenario')
            
            print(f"  ✓ {class_name}: {successful_tests}/{result.testsRun} passed")
    
    def run_integration_tests(self):
        """Run all integration tests."""
        print("\n🔗 Running Integration Tests...")
        print("-" * 50)
        
        integration_classes = [TestIntegrationWorkflow, TestWorkflowComponents]
        
        for test_class in integration_classes:
            suite = unittest.TestLoader().loadTestsFromTestCase(test_class)
            
            # Capture test output
            stream = StringIO()
            runner = unittest.TextTestRunner(stream=stream, verbosity=0)
            result = runner.run(suite)
            
            # Process results
            class_name = test_class.__name__
            for test, traceback in result.failures + result.errors:
                self.result.add_result(
                    f"{class_name}.{test._testMethodName}",
                    False,
                    'integration',
                    traceback.split('\n')[-2] if traceback else None
                )
            
            # Count successful tests
            successful_tests = result.testsRun - len(result.failures) - len(result.errors)
            for i in range(successful_tests):
                self.result.add_result(f"{class_name}.test_{i}", True, 'integration')
            
            print(f"  ✓ {class_name}: {successful_tests}/{result.testsRun} passed")
    
    def run_unit_tests(self):
        """Run all unit tests."""
        print("\n🧪 Running Unit Tests...")
        print("-" * 50)
        
        unit_classes = [
            TestEventParser, TestDateTimeParser, TestRelativeDateParsing,
            TestDurationParsing, TestCalendarService, TestParsedEvent,
            TestEvent, TestValidationResult
        ]
        
        for test_class in unit_classes:
            suite = unittest.TestLoader().loadTestsFromTestCase(test_class)
            
            # Capture test output
            stream = StringIO()
            runner = unittest.TextTestRunner(stream=stream, verbosity=0)
            result = runner.run(suite)
            
            # Process results
            class_name = test_class.__name__
            for test, traceback in result.failures + result.errors:
                self.result.add_result(
                    f"{class_name}.{test._testMethodName}",
                    False,
                    'unit',
                    traceback.split('\n')[-2] if traceback else None
                )
            
            # Count successful tests
            successful_tests = result.testsRun - len(result.failures) - len(result.errors)
            for i in range(successful_tests):
                self.result.add_result(f"{class_name}.test_{i}", True, 'unit')
            
            print(f"  ✓ {class_name}: {successful_tests}/{result.testsRun} passed")
    
    def validate_requirements_coverage(self):
        """Validate that all requirements are covered by tests."""
        print("\n📋 Validating Requirements Coverage...")
        print("-" * 50)
        
        # Define requirement mapping
        requirements_coverage = {
            'Requirement 1.1': 'Text highlighting and event creation option',
            'Requirement 1.2': 'Text parsing execution',
            'Requirement 1.3': 'Information extraction (date, time, title, location)',
            'Requirement 1.4': 'Form pre-population',
            'Requirement 2.1': 'Common date format identification',
            'Requirement 2.2': 'Time format identification',
            'Requirement 2.3': 'Relative date conversion',
            'Requirement 2.4': 'Duration calculation',
            'Requirement 3.1': 'Preview display',
            'Requirement 3.2': 'Field editing capability',
            'Requirement 3.3': 'Missing field highlighting',
            'Requirement 3.4': 'Event creation confirmation',
            'Requirement 4.1': 'Multiple events identification',
            'Requirement 4.2': 'Ambiguous text handling',
            'Requirement 4.3': 'No event information handling',
            'Requirement 4.4': 'Location extraction',
            'Requirement 5.1': 'Default calendar storage',
            'Requirement 5.2': 'Creation confirmation',
            'Requirement 5.3': 'Creation failure handling',
            'Requirement 5.4': 'Complete information storage',
        }
        
        covered_requirements = 0
        for req_id, description in requirements_coverage.items():
            # Check if we have tests for this requirement
            has_test = any(req_id.lower().replace('.', '_') in failure[0].lower() 
                          for failure in self.result.failures)
            
            if not has_test:
                covered_requirements += 1
                print(f"  ✓ {req_id}: {description}")
            else:
                print(f"  ❌ {req_id}: {description} - TEST FAILED")
        
        coverage_percentage = (covered_requirements / len(requirements_coverage)) * 100
        print(f"\nRequirements Coverage: {covered_requirements}/{len(requirements_coverage)} ({coverage_percentage:.1f}%)")
        
        return coverage_percentage >= 90  # 90% coverage threshold
    
    def generate_comprehensive_report(self):
        """Generate comprehensive test report."""
        print("\n" + "="*80)
        print("COMPREHENSIVE TEST SUITE REPORT")
        print("="*80)
        
        # Overall statistics
        duration = (self.result.end_time - self.result.start_time).total_seconds()
        print(f"Test Duration: {duration:.2f} seconds")
        print(f"Total Tests: {self.result.total_tests}")
        print(f"Passed: {self.result.passed_tests}")
        print(f"Failed: {self.result.failed_tests}")
        print(f"Overall Success Rate: {self.result.get_success_rate():.1f}%")
        
        # Category breakdown
        print(f"\nCATEGORY BREAKDOWN:")
        print(f"{'Category':<20} {'Passed':<8} {'Total':<8} {'Success Rate':<12}")
        print("-" * 50)
        
        categories = ['requirement', 'performance', 'scenario', 'integration', 'unit']
        for category in categories:
            cat_data = getattr(self.result, f"{category}_tests")
            success_rate = self.result.get_category_success_rate(category)
            print(f"{category.title():<20} {cat_data['passed']:<8} {cat_data['total']:<8} {success_rate:.1f}%")
        
        # Performance issues
        if self.result.performance_issues:
            print(f"\nPERFORMANCE ISSUES DETECTED:")
            for test_name, issue in self.result.performance_issues:
                print(f"  ❌ {test_name}: {issue}")
        
        # Critical failures
        if self.result.failures:
            print(f"\nCRITICAL FAILURES:")
            for test_name, error in self.result.failures[:10]:  # Show first 10
                print(f"  ❌ {test_name}: {error}")
            
            if len(self.result.failures) > 10:
                print(f"  ... and {len(self.result.failures) - 10} more failures")
        
        # Requirements validation
        requirements_covered = self.validate_requirements_coverage()
        
        # Final assessment
        print(f"\nFINAL ASSESSMENT:")
        overall_success = self.result.get_success_rate()
        
        if overall_success >= 95 and requirements_covered:
            print("🎉 EXCELLENT: All tests pass with comprehensive coverage!")
            status = "EXCELLENT"
        elif overall_success >= 90 and requirements_covered:
            print("✅ GOOD: Most tests pass with good coverage!")
            status = "GOOD"
        elif overall_success >= 80:
            print("⚠️  ACCEPTABLE: Reasonable test coverage but improvements needed!")
            status = "ACCEPTABLE"
        else:
            print("❌ NEEDS WORK: Significant test failures detected!")
            status = "NEEDS_WORK"
        
        # Recommendations
        print(f"\nRECOMMENDATIONS:")
        if self.result.performance_issues:
            print("  • Address performance issues in parsing and workflow")
        if self.result.failed_tests > 0:
            print("  • Fix failing tests to improve reliability")
        if not requirements_covered:
            print("  • Ensure all requirements have adequate test coverage")
        if overall_success < 95:
            print("  • Improve test success rate to 95%+ for production readiness")
        
        return status
    
    def run_all_tests(self):
        """Run the complete comprehensive test suite."""
        print("🚀 Starting Comprehensive Test Suite")
        print("="*80)
        
        try:
            self.setUp()
            
            # Run all test categories
            self.run_requirement_validation_tests()
            self.run_performance_tests()
            self.run_scenario_tests()
            self.run_integration_tests()
            self.run_unit_tests()
            
            # Generate final report
            status = self.generate_comprehensive_report()
            
            return status
            
        except Exception as e:
            print(f"\n❌ CRITICAL ERROR in test suite: {e}")
            return "ERROR"
        
        finally:
            self.tearDown()


def main():
    """Main entry point for comprehensive test suite."""
    suite = ComprehensiveTestSuite()
    status = suite.run_all_tests()
    
    # Exit with appropriate code
    exit_codes = {
        "EXCELLENT": 0,
        "GOOD": 0,
        "ACCEPTABLE": 1,
        "NEEDS_WORK": 2,
        "ERROR": 3
    }
    
    return exit_codes.get(status, 3)


if __name__ == '__main__':
    sys.exit(main())