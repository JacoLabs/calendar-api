"""
Performance Monitoring Demo

This example demonstrates how to use the PerformanceMonitor class
to track component latencies, evaluate accuracy against golden test sets,
and generate reliability diagrams for confidence calibration.
"""

import sys
import time
from datetime import datetime
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from services.performance_monitor import PerformanceMonitor, GoldenTestCase
from models.event_models import ParsedEvent


def mock_event_parser(text: str) -> ParsedEvent:
    """
    Mock event parser for demonstration purposes.
    
    In a real implementation, this would be your actual parsing function.
    """
    # Simulate some processing time
    time.sleep(0.01)  # 10ms processing time
    
    # Simple mock parsing logic
    if "meeting" in text.lower():
        return ParsedEvent(
            title="Meeting",
            start_datetime=datetime(2025, 1, 2, 14, 0),
            end_datetime=datetime(2025, 1, 2, 15, 0),
            confidence_score=0.8,
            parsing_path="regex_primary"
        )
    elif "lunch" in text.lower():
        return ParsedEvent(
            title="Lunch",
            start_datetime=datetime(2025, 1, 3, 12, 30),
            end_datetime=datetime(2025, 1, 3, 13, 30),
            location="Restaurant",
            confidence_score=0.9,
            parsing_path="regex_primary"
        )
    else:
        return ParsedEvent(
            title="Event",
            start_datetime=datetime(2025, 1, 1, 10, 0),
            end_datetime=datetime(2025, 1, 1, 11, 0),
            confidence_score=0.6,
            parsing_path="llm_fallback"
        )


def demonstrate_component_latency_tracking():
    """Demonstrate component latency tracking."""
    print("=== Component Latency Tracking Demo ===")
    
    monitor = PerformanceMonitor()
    
    # Simulate component processing with timing
    components = ['regex_extractor', 'llm_enhancer', 'title_extractor']
    
    for component in components:
        print(f"\nTiming {component}...")
        
        # Method 1: Manual timing
        start_time = time.time()
        time.sleep(0.05)  # Simulate 50ms processing
        duration_ms = (time.time() - start_time) * 1000
        monitor.track_component_latency(component, duration_ms)
        
        # Method 2: Context manager timing
        with monitor.time_component(component):
            time.sleep(0.03)  # Simulate 30ms processing
        
        # Get stats for this component
        stats = monitor.component_latencies[component].get_stats()
        print(f"  {component}: {stats['count']} calls, "
              f"mean={stats['mean']:.1f}ms, "
              f"p95={stats['p95']:.1f}ms")
    
    print("\n=== Component Latency Summary ===")
    metrics = monitor.get_performance_metrics()
    for component, stats in metrics.component_latencies.items():
        if stats['count'] > 0:
            print(f"{component}: {stats['count']} calls, "
                  f"mean={stats['mean']:.1f}ms, "
                  f"p95={stats['p95']:.1f}ms")


def demonstrate_golden_set_evaluation():
    """Demonstrate golden set evaluation."""
    print("\n=== Golden Set Evaluation Demo ===")
    
    monitor = PerformanceMonitor()
    
    # Add a custom test case
    custom_case = GoldenTestCase(
        id="demo_001",
        input_text="Team meeting tomorrow at 2pm in Conference Room A",
        expected_title="Team meeting",
        expected_start=datetime(2025, 1, 2, 14, 0),
        expected_end=datetime(2025, 1, 2, 15, 0),
        expected_location="Conference Room A",
        category="demo",
        difficulty="medium"
    )
    
    monitor.add_golden_test_case(custom_case)
    print(f"Added custom test case. Total golden cases: {len(monitor.golden_test_cases)}")
    
    # Evaluate accuracy against golden set
    print("\nEvaluating parser accuracy...")
    evaluation = monitor.evaluate_accuracy(mock_event_parser)
    
    print(f"Overall accuracy: {evaluation['overall_accuracy']:.3f}")
    print("Field accuracies:")
    for field, stats in evaluation['field_accuracies'].items():
        print(f"  {field}: mean={stats['mean']:.3f}, "
              f"median={stats['median']:.3f}")
    
    print(f"Performance: mean={evaluation['performance_stats']['mean_processing_time_ms']:.1f}ms")


def demonstrate_confidence_calibration():
    """Demonstrate confidence calibration tracking."""
    print("\n=== Confidence Calibration Demo ===")
    
    monitor = PerformanceMonitor()
    
    # Simulate some predictions with confidence scores
    predictions = [
        (0.9, True),   # High confidence, correct
        (0.85, True),  # High confidence, correct
        (0.8, False),  # High confidence, incorrect
        (0.7, True),   # Medium confidence, correct
        (0.6, True),   # Medium confidence, correct
        (0.5, False),  # Medium confidence, incorrect
        (0.4, False),  # Low confidence, incorrect
        (0.3, False),  # Low confidence, incorrect
        (0.2, True),   # Low confidence, correct (surprising!)
        (0.1, False),  # Low confidence, incorrect
    ]
    
    print(f"Adding {len(predictions)} confidence predictions...")
    for confidence, is_correct in predictions:
        monitor.confidence_predictions.append((confidence, is_correct))
    
    # Generate reliability diagram
    print("Generating reliability diagram...")
    reliability_data = monitor.generate_reliability_diagram("demo_reliability.png")
    
    if 'error' not in reliability_data:
        print(f"Expected Calibration Error (ECE): {reliability_data['expected_calibration_error']:.3f}")
        print(f"Total predictions: {reliability_data['total_predictions']}")
        print(f"Reliability points: {len(reliability_data['reliability_points'])}")
        
        # Show some reliability points
        for point in reliability_data['reliability_points'][:3]:
            print(f"  Confidence bin {point['confidence_bin']:.1f}: "
                  f"predicted={point['predicted_confidence']:.3f}, "
                  f"actual={point['actual_accuracy']:.3f}, "
                  f"count={point['count']}")
    else:
        print(f"Error: {reliability_data['error']}")


def demonstrate_system_metrics():
    """Demonstrate system metrics recording."""
    print("\n=== System Metrics Demo ===")
    
    monitor = PerformanceMonitor()
    
    # Simulate some parsing requests
    requests = [
        (True, False, 0.8),   # Success, no cache, good quality
        (True, True, 0.9),    # Success, cache hit, excellent quality
        (False, False, None), # Failure, no cache
        (True, False, 0.7),   # Success, no cache, fair quality
        (True, True, 0.85),   # Success, cache hit, good quality
    ]
    
    print(f"Recording {len(requests)} parsing requests...")
    for success, cache_hit, quality in requests:
        monitor.record_request(success, cache_hit, quality)
    
    # Get system metrics
    metrics = monitor.get_performance_metrics()
    
    print(f"Total requests: {metrics.total_requests}")
    print(f"Successful parses: {metrics.successful_parses}")
    print(f"Failed parses: {metrics.failed_parses}")
    print(f"Cache hit rate: {metrics.cache_hit_rate:.2f}")
    print(f"Average quality score: {metrics.average_quality_score:.3f}")
    print(f"Quality distribution: {metrics.quality_distribution}")


def demonstrate_performance_report():
    """Demonstrate comprehensive performance report generation."""
    print("\n=== Performance Report Demo ===")
    
    monitor = PerformanceMonitor()
    
    # Add some sample data
    monitor.track_component_latency("regex_extractor", 25.0)
    monitor.track_component_latency("llm_enhancer", 1200.0)
    monitor.record_request(True, False, 0.8)
    monitor.confidence_predictions.append((0.8, True))
    
    # Generate comprehensive report
    print("Generating comprehensive performance report...")
    report = monitor.generate_performance_report("demo_performance_report.json")
    
    print(f"Report timestamp: {report['report_timestamp']}")
    print(f"Total golden test cases: {report['golden_set_info']['total_cases']}")
    print(f"Categories: {report['golden_set_info']['categories']}")
    
    if report['recommendations']:
        print("Recommendations:")
        for rec in report['recommendations']:
            print(f"  - {rec}")
    else:
        print("No performance issues detected!")


def main():
    """Run all performance monitoring demonstrations."""
    print("Performance Monitoring Demonstration")
    print("=" * 50)
    
    try:
        demonstrate_component_latency_tracking()
        demonstrate_golden_set_evaluation()
        demonstrate_confidence_calibration()
        demonstrate_system_metrics()
        demonstrate_performance_report()
        
        print("\n" + "=" * 50)
        print("Performance monitoring demonstration completed successfully!")
        print("Check the generated files:")
        print("  - demo_reliability.png (reliability diagram)")
        print("  - demo_performance_report.json (comprehensive report)")
        
    except Exception as e:
        print(f"Error during demonstration: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()