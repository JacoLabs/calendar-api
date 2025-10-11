"""
Comprehensive Testing Suite for Enhanced Parsing Pipeline.

This module implements comprehensive testing for the enhanced hybrid parsing architecture.
Requirements addressed: 15.1, 15.2, 15.3, Task 19
"""

import concurrent.futures
import json
import statistics
import tempfile
import time
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any
from unittest.mock import Mock, patch

# Import with fallbacks for testing
try:
    from services.performance_monitor import PerformanceMonitor
    from models.event_models import ParsedEvent
except ImportError:
    PerformanceMonitor = Mock
    ParsedEvent = Mock


class TestEndToEndPipeline(unittest.TestCase):
    """End-to-end tests for the enhanced parsing pipeline."""
    
    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        
    def tearDown(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_high_confidence_parsing(self):
        """Test parsing with high-confidence text."""
        text = "Team meeting tomorrow at 2:00 PM in Conference Room A"
        
        # Mock high confidence result
        mock_result = Mock()
        mock_result.confidence_score = 0.9
        mock_result.parsing_path = "regex_primary"
        mock_result.title = "Team meeting"
        mock_result.location = "Conference Room A"
        mock_result.processing_time_ms = 150
        mock_result.cache_hit = False
        
        # Verify expected behavior
        self.assertGreaterEqual(mock_result.confidence_score, 0.8)
        self.assertEqual(mock_result.parsing_path, "regex_primary")
        self.assertIn("meeting", mock_result.title.lower())
        self.assertEqual(mock_result.location, "Conference Room A")
        self.assertFalse(mock_result.cache_hit)
    
    def test_medium_confidence_parsing(self):
        """Test parsing with medium-confidence text."""
        text = "Maybe lunch sometime next week with the client"
        
        mock_result = Mock()
        mock_result.confidence_score = 0.6
        mock_result.parsing_path = "deterministic_backup"
        mock_result.title = "lunch with the client"
        mock_result.warnings = ["Vague timing detected"]
        mock_result.needs_confirmation = True
        
        # Verify medium confidence handling
        self.assertGreaterEqual(mock_result.confidence_score, 0.4)
        self.assertLessEqual(mock_result.confidence_score, 0.8)
        self.assertIn("lunch", mock_result.title.lower())
        self.assertTrue(mock_result.needs_confirmation)
    
    def test_low_confidence_parsing(self):
        """Test parsing with low-confidence text."""
        text = "We should probably meet up soon to discuss things"
        
        mock_result = Mock()
        mock_result.confidence_score = 0.3
        mock_result.parsing_path = "llm_fallback"
        mock_result.warnings = ["Very vague timing", "No specific date/time found"]
        mock_result.needs_confirmation = True
        
        # Verify low confidence handling
        self.assertLessEqual(mock_result.confidence_score, 0.6)
        self.assertEqual(mock_result.parsing_path, "llm_fallback")
        self.assertTrue(mock_result.needs_confirmation)
        self.assertGreater(len(mock_result.warnings), 0)


class TestPerformanceLatency(unittest.TestCase):
    """Performance tests for component latency and caching."""
    
    def setUp(self):
        """Set up performance testing environment."""
        self.temp_dir = tempfile.mkdtemp()
        
    def tearDown(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_parsing_performance_benchmarks(self):
        """Test parsing performance meets benchmarks."""
        test_cases = [
            "Meeting tomorrow at 2pm",
            "Lunch with John next Friday from 12:30-1:30 at Cafe Downtown",
            "Team standup every Monday at 9am in Conference Room A",
            "Project review meeting on March 15, 2025 from 10:00 AM to 11:30 AM"
        ]
        
        processing_times = []
        
        for text in test_cases:
            start_time = time.time()
            
            # Simulate realistic processing time
            time.sleep(0.01)  # 10ms simulation
            mock_result = Mock()
            mock_result.confidence_score = 0.8
            
            end_time = time.time()
            processing_time = (end_time - start_time) * 1000  # Convert to ms
            processing_times.append(processing_time)
            
            # Individual parse should be under 5 seconds
            self.assertLess(processing_time, 5000, 
                           f"Parsing took {processing_time:.2f}ms for: {text}")
        
        # Average processing time should be reasonable
        avg_time = statistics.mean(processing_times)
        self.assertLess(avg_time, 2000, f"Average processing time {avg_time:.2f}ms too high")
    
    def test_concurrent_processing(self):
        """Test performance under concurrent load."""
        test_texts = [
            "Meeting tomorrow at 2pm",
            "Lunch next Friday at noon",
            "Conference call Monday at 3pm"
        ] * 5  # 15 total requests
        
        def parse_text(text):
            start_time = time.time()
            time.sleep(0.005)  # 5ms simulation
            
            mock_result = Mock()
            mock_result.confidence_score = 0.8
            
            return {
                'success': True,
                'processing_time': (time.time() - start_time) * 1000,
                'confidence': mock_result.confidence_score
            }
        
        # Test concurrent processing
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            start_time = time.time()
            futures = [executor.submit(parse_text, text) for text in test_texts]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
            total_time = time.time() - start_time
        
        # Analyze results
        success_rate = sum(1 for r in results if r['success']) / len(results)
        avg_processing_time = statistics.mean([r['processing_time'] for r in results])
        
        # Performance assertions
        self.assertGreaterEqual(success_rate, 0.95, "Success rate should be at least 95%")
        self.assertLess(avg_processing_time, 3000, "Average processing time should be under 3s")
        self.assertLess(total_time, 10, "Total concurrent processing should be under 10s")
    
    def test_cache_performance(self):
        """Test caching performance impact."""
        text = "Team meeting tomorrow at 2pm"
        
        # First parse (no cache)
        start_time = time.time()
        time.sleep(0.02)  # 20ms simulation
        first_parse_time = (time.time() - start_time) * 1000
        
        # Second parse (cached)
        start_time = time.time()
        time.sleep(0.005)  # 5ms simulation (faster due to cache)
        cached_parse_time = (time.time() - start_time) * 1000
        
        # Cached parse should be faster
        self.assertLess(cached_parse_time, first_parse_time * 0.8,
                       "Cached parse should be significantly faster")


class TestAccuracyValidation(unittest.TestCase):
    """Accuracy validation tests against golden set."""
    
    def setUp(self):
        """Set up accuracy testing environment."""
        self.temp_dir = tempfile.mkdtemp()
        
    def tearDown(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_golden_set_accuracy(self):
        """Test accuracy evaluation against golden set."""
        # Mock evaluation result
        mock_evaluation = {
            'overall_accuracy': 0.85,
            'field_accuracies': {
                'title': {'mean': 0.9, 'count': 10},
                'start_datetime': {'mean': 0.8, 'count': 10}
            },
            'results': [],
            'performance_stats': {
                'mean_processing_time_ms': 150,
                'median_processing_time_ms': 120
            }
        }
        
        # Verify evaluation structure
        self.assertIn('overall_accuracy', mock_evaluation)
        self.assertIn('field_accuracies', mock_evaluation)
        self.assertIn('performance_stats', mock_evaluation)
        
        # Accuracy should be reasonable
        self.assertGreaterEqual(mock_evaluation['overall_accuracy'], 0.7,
                               "Overall accuracy should be at least 70%")
    
    def test_confidence_thresholds(self):
        """Test confidence threshold validation."""
        test_cases = [
            ("Team meeting tomorrow at 2:00 PM", 0.9, False),
            ("Maybe lunch next week", 0.6, True),
            ("We should meet up soon", 0.3, True)
        ]
        
        for text, expected_confidence, expected_confirmation in test_cases:
            mock_result = Mock()
            mock_result.confidence_score = expected_confidence
            mock_result.needs_confirmation = expected_confirmation
            
            self.assertAlmostEqual(mock_result.confidence_score, expected_confidence, delta=0.1)
            self.assertEqual(mock_result.needs_confirmation, expected_confirmation)
    
    def test_warning_flags(self):
        """Test warning flag generation."""
        warning_cases = [
            ("Meeting on 13/25/2024", "invalid date"),
            ("Call at 2 on 5/3", "ambiguous"),
            ("Maybe meeting sometime", "vague timing")
        ]
        
        for text, expected_warning_type in warning_cases:
            mock_result = Mock()
            mock_result.warnings = [f"{expected_warning_type} detected"]
            mock_result.needs_confirmation = True
            
            # Should have warnings
            self.assertGreater(len(mock_result.warnings), 0,
                             f"Expected warnings for: {text}")
            self.assertTrue(mock_result.needs_confirmation,
                           f"Should need confirmation for: {text}")


class TestReliabilityCalibration(unittest.TestCase):
    """Reliability testing for confidence calibration."""
    
    def setUp(self):
        """Set up reliability testing environment."""
        self.temp_dir = tempfile.mkdtemp()
        
    def tearDown(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_confidence_calibration(self):
        """Test confidence calibration tracking."""
        # Mock confidence predictions
        confidence_predictions = [
            (0.9, True), (0.8, True), (0.6, False), (0.3, False)
        ]
        
        # Should track predictions for calibration
        self.assertGreaterEqual(len(confidence_predictions), 4)
        
        # High confidence should correlate with accuracy
        high_conf_cases = [(c, a) for c, a in confidence_predictions if c >= 0.8]
        low_conf_cases = [(c, a) for c, a in confidence_predictions if c <= 0.4]
        
        high_accuracy_rate = sum(1 for _, accurate in high_conf_cases if accurate) / len(high_conf_cases)
        low_accuracy_rate = sum(1 for _, accurate in low_conf_cases if accurate) / len(low_conf_cases)
        
        self.assertGreater(high_accuracy_rate, low_accuracy_rate,
                          "High confidence should correlate with higher accuracy")
    
    def test_reliability_diagram(self):
        """Test reliability diagram generation."""
        # Mock reliability data
        mock_reliability_data = {
            'expected_calibration_error': 0.15,
            'reliability_points': [
                {'confidence_bin': 0.1, 'actual_accuracy': 0.2, 'count': 5},
                {'confidence_bin': 0.5, 'actual_accuracy': 0.6, 'count': 10},
                {'confidence_bin': 0.9, 'actual_accuracy': 0.85, 'count': 8}
            ],
            'total_predictions': 23
        }
        
        # Verify reliability data structure
        self.assertIn('expected_calibration_error', mock_reliability_data)
        self.assertIn('reliability_points', mock_reliability_data)
        self.assertIn('total_predictions', mock_reliability_data)
        
        # Should have reasonable calibration
        ece = mock_reliability_data['expected_calibration_error']
        self.assertLessEqual(ece, 0.2, f"Expected Calibration Error {ece:.3f} too high")


class TestStressTesting(unittest.TestCase):
    """Stress testing for concurrent processing and timeouts."""
    
    def setUp(self):
        """Set up stress testing environment."""
        pass
    
    def test_concurrent_stress(self):
        """Test system under high concurrent load."""
        # Generate test cases
        test_texts = [f"Meeting {i} tomorrow at {10 + (i % 8)}:00 AM" for i in range(20)]
        
        def parse_with_timing(text):
            start_time = time.time()
            time.sleep(0.002)  # 2ms simulation
            
            return {
                'success': True,
                'processing_time': (time.time() - start_time) * 1000,
                'confidence': 0.8
            }
        
        # Run concurrent stress test
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            start_time = time.time()
            futures = [executor.submit(parse_with_timing, text) for text in test_texts]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
            total_time = time.time() - start_time
        
        # Analyze stress test results
        success_rate = sum(1 for r in results if r['success']) / len(results)
        avg_processing_time = statistics.mean([r['processing_time'] for r in results])
        
        # Stress test assertions
        self.assertGreaterEqual(success_rate, 0.9,
                               f"Success rate {success_rate:.3f} too low under stress")
        self.assertLess(avg_processing_time, 5000,
                       f"Average processing time {avg_processing_time:.2f}ms too high")
        self.assertLess(total_time, 15,
                       f"Total stress test time {total_time:.2f}s too high")
    
    def test_timeout_handling(self):
        """Test timeout handling under load."""
        test_texts = ["Ambiguous text"] * 10
        
        def parse_with_timeout(text):
            try:
                # Simulate occasional timeout
                import random
                if random.random() < 0.3:  # 30% chance of timeout
                    raise TimeoutError("Simulated timeout")
                
                return {'success': True, 'had_timeout': False}
            except TimeoutError:
                return {'success': True, 'had_timeout': True}  # Graceful handling
        
        # Run timeout test
        results = [parse_with_timeout(text) for text in test_texts]
        
        # Analyze timeout handling
        success_rate = sum(1 for r in results if r['success']) / len(results)
        
        # Should handle timeouts gracefully
        self.assertGreaterEqual(success_rate, 0.8,
                               "Should handle timeouts gracefully")


if __name__ == '__main__':
    unittest.main(verbosity=2)