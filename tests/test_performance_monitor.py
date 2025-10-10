"""
Tests for the PerformanceMonitor class.

Tests comprehensive performance monitoring including:
- Component latency tracking
- Golden set maintenance and accuracy evaluation
- Reliability diagram generation
- Performance metrics collection and reporting
"""

import json
import tempfile
import time
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch

from services.performance_monitor import (
    PerformanceMonitor,
    ComponentLatency,
    GoldenTestCase,
    AccuracyResult,
    ReliabilityPoint,
    PerformanceMetrics
)
from models.event_models import ParsedEvent, FieldResult


class TestComponentLatency(unittest.TestCase):
    """Test ComponentLatency class."""
    
    def test_component_latency_initialization(self):
        """Test ComponentLatency initialization."""
        latency = ComponentLatency("test_component")
        
        self.assertEqual(latency.component_name, "test_component")
        self.assertEqual(len(latency.latencies), 0)
        self.assertEqual(latency.total_calls, 0)
        self.assertEqual(latency.total_time_ms, 0.0)
    
    def test_add_measurement(self):
        """Test adding latency measurements."""
        latency = ComponentLatency("test_component")
        
        # Add measurements
        latency.add_measurement(100.0)
        latency.add_measurement(200.0)
        latency.add_measurement(150.0)
        
        self.assertEqual(len(latency.latencies), 3)
        self.assertEqual(latency.total_calls, 3)
        self.assertEqual(latency.total_time_ms, 450.0)
    
    def test_get_stats(self):
        """Test getting statistical summary."""
        latency = ComponentLatency("test_component")
        
        # Test empty stats
        stats = latency.get_stats()
        self.assertEqual(stats['count'], 0)
        self.assertEqual(stats['mean'], 0.0)
        
        # Add measurements
        measurements = [100, 200, 150, 300, 250]
        for measurement in measurements:
            latency.add_measurement(measurement)
        
        stats = latency.get_stats()
        self.assertEqual(stats['count'], 5)
        self.assertEqual(stats['mean'], 200.0)
        self.assertEqual(stats['median'], 200.0)
        self.assertEqual(stats['min'], 100.0)
        self.assertEqual(stats['max'], 300.0)


class TestGoldenTestCase(unittest.TestCase):
    """Test GoldenTestCase class."""
    
    def test_golden_test_case_creation(self):
        """Test creating a golden test case."""
        test_case = GoldenTestCase(
            id="test_001",
            input_text="Meeting tomorrow at 2pm",
            expected_title="Meeting",
            expected_start=datetime(2025, 1, 2, 14, 0),
            expected_end=datetime(2025, 1, 2, 15, 0),
            expected_location="Conference Room A",
            category="basic",
            difficulty="easy"
        )
        
        self.assertEqual(test_case.id, "test_001")
        self.assertEqual(test_case.input_text, "Meeting tomorrow at 2pm")
        self.assertEqual(test_case.expected_title, "Meeting")
        self.assertEqual(test_case.expected_location, "Conference Room A")
        self.assertEqual(test_case.category, "basic")
        self.assertEqual(test_case.difficulty, "easy")
    
    def test_golden_test_case_serialization(self):
        """Test serialization and deserialization."""
        original = GoldenTestCase(
            id="test_001",
            input_text="Meeting tomorrow at 2pm",
            expected_title="Meeting",
            expected_start=datetime(2025, 1, 2, 14, 0),
            expected_end=datetime(2025, 1, 2, 15, 0)
        )
        
        # Serialize to dict
        data = original.to_dict()
        
        # Deserialize from dict
        restored = GoldenTestCase.from_dict(data)
        
        self.assertEqual(original.id, restored.id)
        self.assertEqual(original.input_text, restored.input_text)
        self.assertEqual(original.expected_title, restored.expected_title)
        self.assertEqual(original.expected_start, restored.expected_start)
        self.assertEqual(original.expected_end, restored.expected_end)


class TestPerformanceMonitor(unittest.TestCase):
    """Test PerformanceMonitor class."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create temporary directory for golden set
        self.temp_dir = tempfile.mkdtemp()
        self.golden_set_path = Path(self.temp_dir) / "golden_set.json"
        
        # Create performance monitor with temporary path
        self.monitor = PerformanceMonitor(str(self.golden_set_path))
    
    def tearDown(self):
        """Clean up test fixtures."""
        # Clean up temporary files
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_initialization(self):
        """Test PerformanceMonitor initialization."""
        self.assertIsInstance(self.monitor, PerformanceMonitor)
        self.assertEqual(len(self.monitor.component_latencies), 9)  # 9 components defined
        self.assertGreater(len(self.monitor.golden_test_cases), 0)  # Default cases created
    
    def test_track_component_latency(self):
        """Test component latency tracking."""
        # Track some latencies
        self.monitor.track_component_latency("regex_extractor", 50.0)
        self.monitor.track_component_latency("regex_extractor", 75.0)
        self.monitor.track_component_latency("llm_enhancer", 1500.0)
        
        # Check that latencies were recorded
        regex_stats = self.monitor.component_latencies["regex_extractor"].get_stats()
        self.assertEqual(regex_stats['count'], 2)
        self.assertEqual(regex_stats['mean'], 62.5)
        
        llm_stats = self.monitor.component_latencies["llm_enhancer"].get_stats()
        self.assertEqual(llm_stats['count'], 1)
        self.assertEqual(llm_stats['mean'], 1500.0)
    
    def test_time_component_context_manager(self):
        """Test timing component with context manager."""
        # Use context manager to time a component
        with self.monitor.time_component("regex_extractor"):
            time.sleep(0.01)  # Sleep for 10ms
        
        # Check that latency was recorded
        stats = self.monitor.component_latencies["regex_extractor"].get_stats()
        self.assertEqual(stats['count'], 1)
        self.assertGreater(stats['mean'], 5.0)  # Should be at least 5ms
    
    def test_golden_set_management(self):
        """Test golden set loading and saving."""
        # Check that default golden set was created
        self.assertGreater(len(self.monitor.golden_test_cases), 5)
        
        # Add a new test case
        new_case = GoldenTestCase(
            id="custom_001",
            input_text="Custom meeting next week",
            expected_title="Custom meeting",
            expected_start=datetime(2025, 1, 8, 10, 0),
            expected_end=datetime(2025, 1, 8, 11, 0)
        )
        
        initial_count = len(self.monitor.golden_test_cases)
        success = self.monitor.add_golden_test_case(new_case)
        
        self.assertTrue(success)
        self.assertEqual(len(self.monitor.golden_test_cases), initial_count + 1)
        
        # Try to add duplicate ID
        duplicate_success = self.monitor.add_golden_test_case(new_case)
        self.assertFalse(duplicate_success)
        self.assertEqual(len(self.monitor.golden_test_cases), initial_count + 1)
    
    def test_accuracy_calculation(self):
        """Test accuracy calculation for individual test cases."""
        # Create a test case
        test_case = GoldenTestCase(
            id="accuracy_test",
            input_text="Meeting tomorrow at 2pm",
            expected_title="Meeting",
            expected_start=datetime(2025, 1, 2, 14, 0),
            expected_end=datetime(2025, 1, 2, 15, 0),
            expected_location="Room A"
        )
        
        # Create a perfect prediction
        perfect_prediction = ParsedEvent(
            title="Meeting",
            start_datetime=datetime(2025, 1, 2, 14, 0),
            end_datetime=datetime(2025, 1, 2, 15, 0),
            location="Room A",
            confidence_score=0.9
        )
        
        result = self.monitor._calculate_accuracy(test_case, perfect_prediction)
        
        self.assertEqual(result.test_case_id, "accuracy_test")
        self.assertGreater(result.accuracy_score, 0.9)  # Should be very high
        self.assertEqual(result.field_accuracies['title'], 1.0)
        self.assertEqual(result.field_accuracies['start_datetime'], 1.0)
        self.assertEqual(result.field_accuracies['end_datetime'], 1.0)
        self.assertEqual(result.field_accuracies['location'], 1.0)
        
        # Test partial match
        partial_prediction = ParsedEvent(
            title="Team Meeting",  # Different title
            start_datetime=datetime(2025, 1, 2, 16, 0),  # 2 hours off - should trigger error
            end_datetime=datetime(2025, 1, 2, 17, 0),
            location="Room A",
            confidence_score=0.7
        )
        
        partial_result = self.monitor._calculate_accuracy(test_case, partial_prediction)
        
        self.assertLess(partial_result.accuracy_score, result.accuracy_score)
        self.assertLess(partial_result.field_accuracies['title'], 1.0)
        self.assertLess(partial_result.field_accuracies['start_datetime'], 1.0)
        self.assertGreater(len(partial_result.errors), 0)
    
    def test_evaluate_accuracy(self):
        """Test accuracy evaluation against golden set."""
        # Create a mock parser function
        def mock_parser(text: str) -> ParsedEvent:
            """Mock parser that returns reasonable predictions."""
            if "meeting" in text.lower():
                return ParsedEvent(
                    title="Meeting",
                    start_datetime=datetime(2025, 1, 2, 14, 0),
                    end_datetime=datetime(2025, 1, 2, 15, 0),
                    confidence_score=0.8
                )
            else:
                return ParsedEvent(
                    title="Event",
                    start_datetime=datetime(2025, 1, 1, 10, 0),
                    end_datetime=datetime(2025, 1, 1, 11, 0),
                    confidence_score=0.6
                )
        
        # Evaluate accuracy
        evaluation = self.monitor.evaluate_accuracy(mock_parser)
        
        self.assertIn('overall_accuracy', evaluation)
        self.assertIn('field_accuracies', evaluation)
        self.assertIn('results', evaluation)
        self.assertIn('performance_stats', evaluation)
        
        self.assertGreater(evaluation['overall_accuracy'], 0.0)
        self.assertEqual(len(evaluation['results']), len(self.monitor.golden_test_cases))
    
    def test_confidence_calibration_tracking(self):
        """Test confidence calibration tracking."""
        # Add some confidence predictions
        predictions = [
            (0.9, True),   # High confidence, correct
            (0.8, True),   # High confidence, correct
            (0.7, False),  # Medium confidence, incorrect
            (0.6, True),   # Medium confidence, correct
            (0.3, False),  # Low confidence, incorrect
            (0.2, False),  # Low confidence, incorrect
        ]
        
        for conf, correct in predictions:
            self.monitor.confidence_predictions.append((conf, correct))
        
        # Generate reliability diagram
        reliability_data = self.monitor.generate_reliability_diagram("test_reliability.png")
        
        self.assertIn('expected_calibration_error', reliability_data)
        self.assertIn('reliability_points', reliability_data)
        self.assertIn('total_predictions', reliability_data)
        
        self.assertEqual(reliability_data['total_predictions'], len(predictions))
        self.assertGreater(len(reliability_data['reliability_points']), 0)
    
    def test_system_metrics_recording(self):
        """Test recording system metrics."""
        # Record some requests
        self.monitor.record_request(success=True, cache_hit=False, quality_score=0.8)
        self.monitor.record_request(success=True, cache_hit=True, quality_score=0.9)
        self.monitor.record_request(success=False, cache_hit=False)
        self.monitor.record_request(success=True, cache_hit=True, quality_score=0.7)
        
        # Get performance metrics
        metrics = self.monitor.get_performance_metrics()
        
        self.assertEqual(metrics.total_requests, 4)
        self.assertEqual(metrics.successful_parses, 3)
        self.assertEqual(metrics.failed_parses, 1)
        self.assertEqual(metrics.cache_hit_rate, 0.5)  # 2 hits out of 4 requests
        self.assertGreater(metrics.average_quality_score, 0.0)
    
    def test_performance_report_generation(self):
        """Test comprehensive performance report generation."""
        # Add some test data
        self.monitor.track_component_latency("regex_extractor", 50.0)
        self.monitor.track_component_latency("llm_enhancer", 1200.0)
        self.monitor.record_request(success=True, quality_score=0.8)
        self.monitor.confidence_predictions.append((0.8, True))
        
        # Generate report
        report_path = Path(self.temp_dir) / "test_report.json"
        report = self.monitor.generate_performance_report(str(report_path))
        
        self.assertIn('report_timestamp', report)
        self.assertIn('system_metrics', report)
        self.assertIn('reliability_analysis', report)
        self.assertIn('golden_set_info', report)
        self.assertIn('recommendations', report)
        
        # Check that report was saved
        self.assertTrue(report_path.exists())
        
        # Load and verify saved report
        with open(report_path, 'r') as f:
            saved_report = json.load(f)
        
        self.assertEqual(saved_report['system_metrics']['total_requests'], 1)
    
    def test_recommendations_generation(self):
        """Test performance recommendations generation."""
        # Create metrics with various issues
        metrics = PerformanceMetrics()
        
        # Add high latency component
        metrics.component_latencies = {
            'slow_component': {
                'count': 10,
                'p95': 6000.0,  # 6 seconds - should trigger recommendation
                'mean': 3000.0
            },
            'fast_component': {
                'count': 10,
                'p95': 100.0,  # 100ms - should be fine
                'mean': 50.0
            }
        }
        
        # Low accuracy
        metrics.overall_accuracy = 0.5  # Should trigger recommendation
        metrics.field_accuracies = {
            'title': 0.4,  # Low - should trigger recommendation
            'start_datetime': 0.8  # Good - should not trigger
        }
        
        # Poor calibration
        metrics.calibration_error = 0.15  # High ECE - should trigger recommendation
        
        # Low cache hit rate
        metrics.cache_hit_rate = 0.2  # Low - should trigger recommendation
        
        # Generate recommendations
        recommendations = self.monitor._generate_recommendations(metrics)
        
        self.assertGreater(len(recommendations), 0)
        
        # Check for specific recommendations
        recommendation_text = ' '.join(recommendations)
        self.assertIn('slow_component', recommendation_text)
        self.assertIn('accuracy', recommendation_text)
        self.assertIn('calibration', recommendation_text)
        self.assertIn('cache', recommendation_text)
    
    @patch('matplotlib.pyplot.savefig')
    @patch('matplotlib.pyplot.figure')
    def test_reliability_diagram_with_no_data(self, mock_figure, mock_savefig):
        """Test reliability diagram generation with no data."""
        # Clear any existing predictions
        self.monitor.confidence_predictions = []
        
        # Try to generate reliability diagram
        result = self.monitor.generate_reliability_diagram()
        
        self.assertIn('error', result)
        self.assertEqual(result['error'], 'No confidence predictions available')
    
    def test_performance_metrics_structure(self):
        """Test that performance metrics have correct structure."""
        metrics = self.monitor.get_performance_metrics()
        
        # Check required fields
        self.assertIsInstance(metrics.timestamp, datetime)
        self.assertIsInstance(metrics.component_latencies, dict)
        self.assertIsInstance(metrics.overall_accuracy, float)
        self.assertIsInstance(metrics.field_accuracies, dict)
        self.assertIsInstance(metrics.calibration_error, float)
        self.assertIsInstance(metrics.total_requests, int)
        self.assertIsInstance(metrics.successful_parses, int)
        self.assertIsInstance(metrics.failed_parses, int)
        self.assertIsInstance(metrics.cache_hit_rate, float)
        self.assertIsInstance(metrics.average_quality_score, float)
        self.assertIsInstance(metrics.quality_distribution, dict)
        
        # Check that metrics can be serialized
        metrics_dict = metrics.to_dict()
        self.assertIsInstance(metrics_dict, dict)
        self.assertIn('timestamp', metrics_dict)


if __name__ == '__main__':
    unittest.main()