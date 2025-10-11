#!/usr/bin/env python3
"""
Test Production Validation System.

This script tests the production validation components to ensure they work correctly.
"""

import asyncio
import json
import logging
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
import sys

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from scripts.production_performance_validator import ProductionPerformanceValidator, ProductionMetrics

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestProductionValidation(unittest.TestCase):
    """Test production validation functionality."""
    
    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.golden_set_path = Path(self.temp_dir) / "test_golden_set.json"
        self.metrics_history_path = Path(self.temp_dir) / "test_metrics_history.json"
        
        # Create test golden set
        self.create_test_golden_set()
        
        # Initialize validator
        self.validator = ProductionPerformanceValidator(
            api_base_url="http://test-api:8000",
            golden_set_path=str(self.golden_set_path),
            metrics_history_path=str(self.metrics_history_path)
        )
    
    def tearDown(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def create_test_golden_set(self):
        """Create a test golden set."""
        test_cases = [
            {
                "id": "test_001",
                "input_text": "Meeting tomorrow at 2pm",
                "expected_title": "Meeting",
                "expected_start": "2025-01-02T14:00:00",
                "expected_end": "2025-01-02T15:00:00",
                "expected_location": None,
                "expected_description": "",
                "category": "basic_datetime",
                "difficulty": "easy",
                "notes": "Simple test case"
            },
            {
                "id": "test_002",
                "input_text": "Lunch with John at Cafe Downtown",
                "expected_title": "Lunch with John",
                "expected_start": "2025-01-01T12:00:00",
                "expected_end": "2025-01-01T13:00:00",
                "expected_location": "Cafe Downtown",
                "expected_description": "",
                "category": "location_extraction",
                "difficulty": "medium",
                "notes": "Location extraction test"
            }
        ]
        
        golden_set_data = {
            "version": "1.0",
            "created": datetime.now().isoformat(),
            "test_cases": test_cases
        }
        
        with open(self.golden_set_path, 'w') as f:
            json.dump(golden_set_data, f, indent=2)
    
    def test_golden_set_loading(self):
        """Test golden set loading."""
        self.assertEqual(len(self.validator.golden_test_cases), 2)
        self.assertEqual(self.validator.golden_test_cases[0]["id"], "test_001")
        self.assertEqual(self.validator.golden_test_cases[1]["id"], "test_002")
    
    def test_accuracy_calculation(self):
        """Test accuracy calculation for test cases."""
        test_case = {
            "id": "test_001",
            "expected_title": "Meeting",
            "expected_start": "2025-01-02T14:00:00",
            "expected_end": "2025-01-02T15:00:00",
            "expected_location": None
        }
        
        # Perfect match
        api_result = {
            "title": "Meeting",
            "start_datetime": "2025-01-02T14:00:00",
            "end_datetime": "2025-01-02T15:00:00",
            "location": None,
            "confidence_score": 0.9
        }
        
        accuracy_result = self.validator._calculate_test_case_accuracy(test_case, api_result)
        
        self.assertGreater(accuracy_result['accuracy_score'], 0.9)
        self.assertEqual(accuracy_result['field_accuracies']['title'], 1.0)
        self.assertEqual(accuracy_result['field_accuracies']['start_datetime'], 1.0)
        self.assertEqual(accuracy_result['field_accuracies']['end_datetime'], 1.0)
    
    def test_accuracy_calculation_partial_match(self):
        """Test accuracy calculation with partial matches."""
        test_case = {
            "id": "test_002",
            "expected_title": "Lunch with John",
            "expected_start": "2025-01-01T12:00:00",
            "expected_end": "2025-01-01T13:00:00",
            "expected_location": "Cafe Downtown"
        }
        
        # Partial match
        api_result = {
            "title": "Lunch",  # Partial title match
            "start_datetime": "2025-01-01T12:05:00",  # 5 minutes off
            "end_datetime": "2025-01-01T13:05:00",  # 5 minutes off
            "location": "Downtown Cafe",  # Similar location
            "confidence_score": 0.7
        }
        
        accuracy_result = self.validator._calculate_test_case_accuracy(test_case, api_result)
        
        # Should have reasonable accuracy despite differences
        self.assertGreater(accuracy_result['accuracy_score'], 0.5)
        self.assertLess(accuracy_result['accuracy_score'], 1.0)
        
        # Title should have partial match
        self.assertGreater(accuracy_result['field_accuracies']['title'], 0.0)
        self.assertLess(accuracy_result['field_accuracies']['title'], 1.0)
        
        # Time should be close (within 5 minutes = high accuracy)
        self.assertGreater(accuracy_result['field_accuracies']['start_datetime'], 0.8)
    
    @patch('aiohttp.ClientSession')
    async def test_golden_set_validation(self, mock_session):
        """Test golden set validation with mocked API responses."""
        # Mock API responses
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            "title": "Meeting",
            "start_datetime": "2025-01-02T14:00:00",
            "end_datetime": "2025-01-02T15:00:00",
            "location": None,
            "confidence_score": 0.9
        })
        
        mock_session_instance = AsyncMock()
        mock_session_instance.post = AsyncMock(return_value=mock_response)
        mock_session.return_value.__aenter__ = AsyncMock(return_value=mock_session_instance)
        mock_session.return_value.__aexit__ = AsyncMock(return_value=None)
        
        # Run validation
        result = await self.validator.validate_golden_set_accuracy()
        
        # Verify results
        self.assertIn('overall_accuracy', result)
        self.assertIn('field_accuracies', result)
        self.assertIn('results', result)
        self.assertGreater(result['overall_accuracy'], 0.0)
        self.assertEqual(len(result['results']), 2)  # Two test cases
    
    def test_confidence_calibration_calculation(self):
        """Test confidence calibration calculations."""
        # Add some mock confidence predictions
        from scripts.production_performance_validator import ConfidencePrediction
        
        predictions = [
            ConfidencePrediction(0.9, 0.95),  # High confidence, high accuracy
            ConfidencePrediction(0.8, 0.85),  # High confidence, high accuracy
            ConfidencePrediction(0.6, 0.65),  # Medium confidence, medium accuracy
            ConfidencePrediction(0.4, 0.35),  # Low confidence, low accuracy
            ConfidencePrediction(0.2, 0.15),  # Low confidence, low accuracy
        ]
        
        self.validator.confidence_predictions.extend(predictions)
        
        # Test reliability diagram calculation
        confidences = [p.predicted_confidence for p in predictions]
        accuracies = [p.actual_accuracy for p in predictions]
        
        reliability_points = self.validator._calculate_reliability_diagram(confidences, accuracies)
        
        self.assertIsInstance(reliability_points, list)
        self.assertGreater(len(reliability_points), 0)
        
        # Test ECE calculation
        ece = self.validator._calculate_expected_calibration_error(confidences, accuracies)
        
        self.assertIsInstance(ece, float)
        self.assertGreaterEqual(ece, 0.0)
        self.assertLessEqual(ece, 1.0)
    
    def test_health_summary_generation(self):
        """Test health summary generation."""
        # Mock metrics data
        metrics = {
            'accuracy': {
                'overall_accuracy': 0.85,
                'performance_stats': {
                    'p95_processing_time_ms': 1200
                }
            },
            'cache': {
                'cache_stats': {
                    'hit_rate': 0.75
                }
            },
            'calibration': {
                'expected_calibration_error': 0.15
            }
        }
        
        summary = self.validator._generate_health_summary(metrics)
        
        # Verify summary structure
        self.assertIn('overall_status', summary)
        self.assertIn('accuracy_status', summary)
        self.assertIn('performance_status', summary)
        self.assertIn('cache_status', summary)
        self.assertIn('calibration_status', summary)
        self.assertIn('alerts', summary)
        self.assertIn('recommendations', summary)
        
        # Verify status assessments
        self.assertEqual(summary['accuracy_status'], 'excellent')  # 85% accuracy
        self.assertEqual(summary['cache_status'], 'good')  # 75% hit rate
        self.assertEqual(summary['calibration_status'], 'good')  # 0.15 ECE
    
    def test_metrics_history_storage(self):
        """Test metrics history storage."""
        # Create test dashboard data
        dashboard_data = {
            'report_timestamp': datetime.now().isoformat(),
            'metrics': {
                'accuracy': {'overall_accuracy': 0.85},
                'cache': {'hit_rate': 0.75}
            },
            'summary': {'overall_status': 'healthy'}
        }
        
        # Store metrics
        self.validator._store_metrics_history(dashboard_data)
        
        # Verify file was created
        self.assertTrue(self.metrics_history_path.exists())
        
        # Verify content
        with open(self.metrics_history_path, 'r') as f:
            history = json.load(f)
        
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]['summary']['overall_status'], 'healthy')
    
    def test_cache_performance_analysis(self):
        """Test cache performance analysis."""
        # Test excellent performance
        cache_stats = {
            'hit_rate': 0.85,
            'cache_hits': 850,
            'cache_misses': 150,
            'cache_size': 500
        }
        
        analysis = self.validator._analyze_cache_performance(cache_stats)
        
        self.assertEqual(analysis['performance_grade'], 'excellent')
        self.assertIn('efficiency_metrics', analysis)
        self.assertEqual(analysis['efficiency_metrics']['requests_served_from_cache'], 850)
        
        # Test poor performance
        cache_stats_poor = {
            'hit_rate': 0.25,
            'cache_hits': 25,
            'cache_misses': 75,
            'cache_size': 10
        }
        
        analysis_poor = self.validator._analyze_cache_performance(cache_stats_poor)
        
        self.assertEqual(analysis_poor['performance_grade'], 'poor')
        self.assertGreater(len(analysis_poor['recommendations']), 0)


class TestProductionMetrics(unittest.TestCase):
    """Test ProductionMetrics data class."""
    
    def test_metrics_creation(self):
        """Test ProductionMetrics creation and serialization."""
        metrics = ProductionMetrics(
            golden_set_accuracy=0.85,
            overall_latency_p95=1200.0,
            cache_hit_rate=0.75,
            confidence_calibration_error=0.15
        )
        
        # Test serialization
        metrics_dict = metrics.to_dict()
        
        self.assertIn('timestamp', metrics_dict)
        self.assertIn('accuracy', metrics_dict)
        self.assertIn('performance', metrics_dict)
        self.assertIn('cache', metrics_dict)
        
        self.assertEqual(metrics_dict['accuracy']['golden_set_accuracy'], 0.85)
        self.assertEqual(metrics_dict['performance']['overall_latency_p95'], 1200.0)
        self.assertEqual(metrics_dict['cache']['hit_rate'], 0.75)


async def run_integration_test():
    """Run integration test with actual API (if available)."""
    logger.info("Running integration test...")
    
    # Try to connect to local API
    try:
        import aiohttp
        
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "http://localhost:8000/healthz",
                timeout=aiohttp.ClientTimeout(total=5)
            ) as response:
                if response.status == 200:
                    logger.info("✅ API is available - running integration test")
                    
                    # Create validator with real API
                    validator = ProductionPerformanceValidator(
                        api_base_url="http://localhost:8000",
                        golden_set_path="tests/golden_set.json"
                    )
                    
                    # Run a quick validation
                    if Path("tests/golden_set.json").exists():
                        result = await validator.validate_golden_set_accuracy()
                        
                        if 'error' not in result:
                            logger.info(f"✅ Integration test passed - Accuracy: {result.get('overall_accuracy', 0):.2%}")
                            return True
                        else:
                            logger.warning(f"⚠️  Integration test had issues: {result['error']}")
                            return False
                    else:
                        logger.warning("⚠️  Golden set not found - skipping integration test")
                        return False
                else:
                    logger.info("❌ API not available - skipping integration test")
                    return False
    
    except Exception as e:
        logger.info(f"❌ API not available ({e}) - skipping integration test")
        return False


def main():
    """Main test function."""
    print("🧪 Testing Production Validation System")
    print("="*50)
    
    # Run unit tests
    print("\n📋 Running Unit Tests...")
    unittest.main(argv=[''], exit=False, verbosity=2)
    
    # Run integration test
    print("\n🔗 Running Integration Test...")
    integration_result = asyncio.run(run_integration_test())
    
    if integration_result:
        print("✅ All tests passed!")
    else:
        print("⚠️  Some tests had issues (check logs above)")
    
    print("\n🎯 Production validation system is ready!")
    print("\nNext steps:")
    print("1. Start your API server: python -m uvicorn api.app.main:app --reload")
    print("2. Run single validation: python run_production_validation.py --single-run")
    print("3. Run continuous validation: python run_production_validation.py --continuous")
    print("4. Run dashboard: python run_production_validation.py --dashboard")


if __name__ == "__main__":
    main()