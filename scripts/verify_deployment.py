#!/usr/bin/env python3
"""
Deployment verification script for Calendar API.
Validates that all components are working correctly after deployment.
"""

import json
import time
import requests
import sys
from datetime import datetime
from typing import Dict, Any, List, Tuple


class DeploymentVerifier:
    """Verifies deployment health and functionality."""
    
    def __init__(self, api_base_url: str = "http://localhost:8000"):
        self.api_base_url = api_base_url.rstrip('/')
        self.test_results = []
    
    def log_test(self, test_name: str, success: bool, message: str = "", details: Any = None):
        """Log test result."""
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
        if message:
            print(f"    {message}")
        if details and not success:
            print(f"    Details: {details}")
        
        self.test_results.append({
            "test": test_name,
            "success": success,
            "message": message,
            "details": details,
            "timestamp": datetime.now().isoformat()
        })
    
    def test_basic_connectivity(self) -> bool:
        """Test basic API connectivity."""
        try:
            response = requests.get(f"{self.api_base_url}/", timeout=10)
            success = response.status_code == 200
            self.log_test(
                "Basic API Connectivity",
                success,
                f"Status: {response.status_code}" if success else f"Failed with status {response.status_code}"
            )
            return success
        except Exception as e:
            self.log_test("Basic API Connectivity", False, f"Connection failed: {str(e)}")
            return False
    
    def test_health_endpoint(self) -> bool:
        """Test health check endpoint."""
        try:
            response = requests.get(f"{self.api_base_url}/healthz", timeout=10)
            success = response.status_code == 200
            
            if success:
                health_data = response.json()
                overall_status = health_data.get('status', 'unknown')
                services = health_data.get('services', {})
                
                healthy_services = sum(1 for status in services.values() if status == 'healthy')
                total_services = len(services)
                
                self.log_test(
                    "Health Check Endpoint",
                    success,
                    f"Status: {overall_status}, Services: {healthy_services}/{total_services} healthy"
                )
            else:
                self.log_test("Health Check Endpoint", False, f"Status: {response.status_code}")
            
            return success
        except Exception as e:
            self.log_test("Health Check Endpoint", False, f"Request failed: {str(e)}")
            return False
    
    def test_metrics_endpoint(self) -> bool:
        """Test Prometheus metrics endpoint."""
        try:
            response = requests.get(f"{self.api_base_url}/metrics", timeout=10)
            success = response.status_code == 200
            
            if success:
                metrics_text = response.text
                metric_count = len([line for line in metrics_text.split('\n') 
                                  if line and not line.startswith('#')])
                
                self.log_test(
                    "Metrics Endpoint",
                    success,
                    f"Returned {metric_count} metrics"
                )
            else:
                self.log_test("Metrics Endpoint", False, f"Status: {response.status_code}")
            
            return success
        except Exception as e:
            self.log_test("Metrics Endpoint", False, f"Request failed: {str(e)}")
            return False
    
    def test_cache_stats_endpoint(self) -> bool:
        """Test cache statistics endpoint."""
        try:
            response = requests.get(f"{self.api_base_url}/cache/stats", timeout=10)
            success = response.status_code == 200
            
            if success:
                cache_data = response.json()
                status = cache_data.get('status', 'unknown')
                hit_ratio = cache_data.get('hit_ratio', 0)
                
                self.log_test(
                    "Cache Stats Endpoint",
                    success,
                    f"Status: {status}, Hit ratio: {hit_ratio:.2f}"
                )
            else:
                self.log_test("Cache Stats Endpoint", False, f"Status: {response.status_code}")
            
            return success
        except Exception as e:
            self.log_test("Cache Stats Endpoint", False, f"Request failed: {str(e)}")
            return False
    
    def test_parsing_functionality(self) -> bool:
        """Test basic parsing functionality."""
        test_cases = [
            {
                "text": "Meeting tomorrow at 2pm",
                "expected_fields": ["title", "start_datetime"]
            },
            {
                "text": "Lunch with John next Friday from 12:30-1:30 at Cafe Downtown",
                "expected_fields": ["title", "start_datetime", "end_datetime", "location"]
            }
        ]
        
        all_passed = True
        
        for i, test_case in enumerate(test_cases):
            try:
                payload = {
                    "text": test_case["text"],
                    "timezone": "UTC",
                    "locale": "en_US"
                }
                
                response = requests.post(
                    f"{self.api_base_url}/parse",
                    json=payload,
                    timeout=15
                )
                
                success = response.status_code == 200
                
                if success:
                    result = response.json()
                    confidence = result.get('confidence_score', 0)
                    
                    # Check if expected fields are present
                    missing_fields = []
                    for field in test_case["expected_fields"]:
                        if not result.get(field):
                            missing_fields.append(field)
                    
                    field_success = len(missing_fields) == 0
                    success = success and field_success
                    
                    message = f"Confidence: {confidence:.2f}"
                    if missing_fields:
                        message += f", Missing fields: {missing_fields}"
                    
                    self.log_test(
                        f"Parsing Test {i+1}",
                        success,
                        message
                    )
                else:
                    self.log_test(
                        f"Parsing Test {i+1}",
                        False,
                        f"HTTP {response.status_code}: {response.text[:100]}"
                    )
                
                all_passed = all_passed and success
                
            except Exception as e:
                self.log_test(f"Parsing Test {i+1}", False, f"Request failed: {str(e)}")
                all_passed = False
        
        return all_passed
    
    def test_error_handling(self) -> bool:
        """Test error handling."""
        try:
            # Test with invalid JSON
            response = requests.post(
                f"{self.api_base_url}/parse",
                data="invalid json",
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            success = response.status_code == 422  # Validation error expected
            
            self.log_test(
                "Error Handling",
                success,
                f"Invalid JSON handled correctly (status: {response.status_code})"
            )
            
            return success
        except Exception as e:
            self.log_test("Error Handling", False, f"Request failed: {str(e)}")
            return False
    
    def test_rate_limiting(self) -> bool:
        """Test rate limiting (basic check)."""
        try:
            # Make multiple rapid requests
            responses = []
            for i in range(5):
                response = requests.get(f"{self.api_base_url}/healthz", timeout=5)
                responses.append(response.status_code)
            
            # All should succeed for basic health checks
            success = all(status == 200 for status in responses)
            
            self.log_test(
                "Rate Limiting",
                success,
                f"5 rapid requests: {responses}"
            )
            
            return success
        except Exception as e:
            self.log_test("Rate Limiting", False, f"Request failed: {str(e)}")
            return False
    
    def test_documentation_endpoints(self) -> bool:
        """Test API documentation endpoints."""
        endpoints = [
            ("/docs", "Swagger UI"),
            ("/redoc", "ReDoc"),
            ("/openapi.json", "OpenAPI Schema")
        ]
        
        all_passed = True
        
        for endpoint, name in endpoints:
            try:
                response = requests.get(f"{self.api_base_url}{endpoint}", timeout=10)
                success = response.status_code == 200
                
                self.log_test(
                    f"Documentation - {name}",
                    success,
                    f"Status: {response.status_code}"
                )
                
                all_passed = all_passed and success
                
            except Exception as e:
                self.log_test(f"Documentation - {name}", False, f"Request failed: {str(e)}")
                all_passed = False
        
        return all_passed
    
    def run_all_tests(self) -> bool:
        """Run all deployment verification tests."""
        print("=" * 80)
        print(f"Calendar API Deployment Verification - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Testing API at: {self.api_base_url}")
        print("=" * 80)
        
        tests = [
            ("Basic Connectivity", self.test_basic_connectivity),
            ("Health Endpoint", self.test_health_endpoint),
            ("Metrics Endpoint", self.test_metrics_endpoint),
            ("Cache Stats Endpoint", self.test_cache_stats_endpoint),
            ("Parsing Functionality", self.test_parsing_functionality),
            ("Error Handling", self.test_error_handling),
            ("Rate Limiting", self.test_rate_limiting),
            ("Documentation Endpoints", self.test_documentation_endpoints)
        ]
        
        print("\nRunning tests...\n")
        
        all_passed = True
        for test_name, test_func in tests:
            try:
                result = test_func()
                all_passed = all_passed and result
            except Exception as e:
                self.log_test(test_name, False, f"Test execution failed: {str(e)}")
                all_passed = False
            
            print()  # Add spacing between tests
        
        # Summary
        print("=" * 80)
        passed_count = sum(1 for result in self.test_results if result['success'])
        total_count = len(self.test_results)
        
        if all_passed:
            print(f"🎉 ALL TESTS PASSED ({passed_count}/{total_count})")
            print("✅ Deployment verification successful!")
        else:
            print(f"❌ SOME TESTS FAILED ({passed_count}/{total_count})")
            print("⚠️  Please review failed tests before proceeding.")
        
        print("=" * 80)
        
        return all_passed
    
    def save_results(self, filename: str = None):
        """Save test results to file."""
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"deployment_verification_{timestamp}.json"
        
        with open(filename, 'w') as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "api_url": self.api_base_url,
                "summary": {
                    "total_tests": len(self.test_results),
                    "passed_tests": sum(1 for r in self.test_results if r['success']),
                    "failed_tests": sum(1 for r in self.test_results if not r['success']),
                    "success_rate": sum(1 for r in self.test_results if r['success']) / len(self.test_results) if self.test_results else 0
                },
                "test_results": self.test_results
            }, f, indent=2)
        
        print(f"📄 Test results saved to: {filename}")


def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Calendar API Deployment Verification")
    parser.add_argument(
        "--url",
        default="http://localhost:8000",
        help="API base URL (default: http://localhost:8000)"
    )
    parser.add_argument(
        "--save-results",
        action="store_true",
        help="Save test results to JSON file"
    )
    parser.add_argument(
        "--output-file",
        help="Output file for test results (default: auto-generated)"
    )
    
    args = parser.parse_args()
    
    verifier = DeploymentVerifier(args.url)
    success = verifier.run_all_tests()
    
    if args.save_results:
        verifier.save_results(args.output_file)
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()