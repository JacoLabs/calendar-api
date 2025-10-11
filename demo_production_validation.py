#!/usr/bin/env python3
"""
Demo Production Validation System.

This script demonstrates the production validation capabilities without requiring
a running API server by using mock data.
"""

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
import sys

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from scripts.production_performance_validator import ProductionPerformanceValidator, ConfidencePrediction

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MockProductionValidator(ProductionPerformanceValidator):
    """Mock validator for demonstration purposes."""
    
    async def validate_golden_set_accuracy(self):
        """Mock golden set validation with realistic results."""
        logger.info("Running mock golden set accuracy validation...")
        
        # Simulate validation results
        mock_results = []
        total_accuracy = 0.0
        field_accuracies = {'title': [], 'start_datetime': [], 'end_datetime': [], 'location': []}
        
        for i, test_case in enumerate(self.golden_test_cases[:10]):  # Limit to 10 for demo
            # Simulate varying accuracy
            base_accuracy = 0.85 + (i % 3 - 1) * 0.1  # Vary between 0.75-0.95
            
            mock_result = {
                'test_case_id': test_case['id'],
                'accuracy_score': base_accuracy,
                'field_accuracies': {
                    'title': min(1.0, base_accuracy + 0.05),
                    'start_datetime': min(1.0, base_accuracy + 0.02),
                    'end_datetime': min(1.0, base_accuracy + 0.02),
                    'location': min(1.0, base_accuracy - 0.05) if test_case.get('expected_location') else 1.0
                },
                'errors': [] if base_accuracy > 0.8 else ['Low confidence parsing'],
                'processing_time_ms': 150 + i * 20,
                'confidence_score': base_accuracy
            }
            
            mock_results.append(mock_result)
            total_accuracy += base_accuracy
            
            for field, accuracy in mock_result['field_accuracies'].items():
                field_accuracies[field].append(accuracy)
            
            # Add confidence prediction for calibration
            is_accurate = base_accuracy > 0.7
            self.confidence_predictions.append(ConfidencePrediction(
                predicted_confidence=base_accuracy,
                actual_accuracy=base_accuracy,
                text_length=len(test_case['input_text']),
                parsing_method='hybrid' if base_accuracy > 0.8 else 'llm_fallback'
            ))
        
        # Calculate summary statistics
        overall_accuracy = total_accuracy / len(mock_results)
        
        field_accuracy_summary = {}
        for field, accuracies in field_accuracies.items():
            if accuracies:
                field_accuracy_summary[field] = {
                    'mean': sum(accuracies) / len(accuracies),
                    'median': sorted(accuracies)[len(accuracies)//2],
                    'min': min(accuracies),
                    'max': max(accuracies),
                    'count': len(accuracies)
                }
        
        processing_times = [r['processing_time_ms'] for r in mock_results]
        performance_stats = {
            'mean_processing_time_ms': sum(processing_times) / len(processing_times),
            'median_processing_time_ms': sorted(processing_times)[len(processing_times)//2],
            'p95_processing_time_ms': sorted(processing_times)[int(len(processing_times) * 0.95)],
            'p99_processing_time_ms': sorted(processing_times)[int(len(processing_times) * 0.99)]
        }
        
        return {
            'timestamp': datetime.now().isoformat(),
            'total_test_cases': len(mock_results),
            'overall_accuracy': overall_accuracy,
            'field_accuracies': field_accuracy_summary,
            'performance_stats': performance_stats,
            'confidence_predictions': len(self.confidence_predictions),
            'results': mock_results
        }
    
    async def track_component_latency(self):
        """Mock component latency tracking."""
        logger.info("Tracking mock component latency...")
        
        return {
            'timestamp': datetime.now().isoformat(),
            'component_metrics': {
                'regex_extractor_duration_ms': [45, 52, 38, 41, 49],
                'llm_enhancer_duration_ms': [850, 920, 780, 890, 810],
                'deterministic_backup_duration_ms': [120, 135, 115, 128, 122],
                'overall_parsing_duration_ms': [980, 1050, 920, 1010, 940]
            },
            'health_data': {
                'status': 'healthy',
                'services': {
                    'regex_parser': 'healthy',
                    'llm_service': 'healthy',
                    'deterministic_backup': 'healthy'
                }
            },
            'system_metrics': {
                'cpu_usage_percent': 45.2,
                'memory_usage_percent': 62.8,
                'disk_usage_percent': 78.5
            }
        }
    
    async def validate_confidence_calibration(self):
        """Mock confidence calibration validation."""
        logger.info("Validating mock confidence calibration...")
        
        if len(self.confidence_predictions) < 5:
            # Add some mock predictions if we don't have enough
            mock_predictions = [
                ConfidencePrediction(0.9, 0.88),
                ConfidencePrediction(0.8, 0.82),
                ConfidencePrediction(0.7, 0.68),
                ConfidencePrediction(0.6, 0.55),
                ConfidencePrediction(0.4, 0.35),
                ConfidencePrediction(0.3, 0.25),
                ConfidencePrediction(0.9, 0.92),
                ConfidencePrediction(0.8, 0.78),
                ConfidencePrediction(0.5, 0.48)
            ]
            self.confidence_predictions.extend(mock_predictions)
        
        confidences = [pred.predicted_confidence for pred in self.confidence_predictions]
        accuracies = [pred.actual_accuracy for pred in self.confidence_predictions]
        
        reliability_data = self._calculate_reliability_diagram(confidences, accuracies)
        ece = self._calculate_expected_calibration_error(confidences, accuracies)
        
        return {
            'timestamp': datetime.now().isoformat(),
            'total_predictions': len(self.confidence_predictions),
            'expected_calibration_error': ece,
            'reliability_points': reliability_data,
            'confidence_distribution': self._get_confidence_distribution(confidences),
            'accuracy_by_confidence_bin': self._get_accuracy_by_confidence_bin(confidences, accuracies)
        }
    
    async def monitor_cache_performance(self):
        """Mock cache performance monitoring."""
        logger.info("Monitoring mock cache performance...")
        
        cache_stats = {
            'hit_rate': 0.72,
            'cache_hits': 720,
            'cache_misses': 280,
            'cache_size': 450,
            'max_cache_size': 1000,
            'average_hit_speedup_ms': 480,
            'total_requests': 1000,
            'cache_efficiency': 0.85
        }
        
        return {
            'timestamp': datetime.now().isoformat(),
            'cache_stats': cache_stats,
            'performance_analysis': self._analyze_cache_performance(cache_stats)
        }


async def run_demo():
    """Run the production validation demo."""
    print("🚀 Production Validation System Demo")
    print("="*60)
    
    # Initialize mock validator
    validator = MockProductionValidator(
        api_base_url="http://mock-api:8000",
        golden_set_path="tests/golden_set.json"
    )
    
    print(f"\n📊 Loaded {len(validator.golden_test_cases)} golden test cases")
    
    # Run comprehensive validation
    print("\n🔍 Running comprehensive production validation...")
    dashboard_report = await validator.generate_production_dashboard_report()
    
    # Display results
    print("\n" + "="*60)
    print("PRODUCTION VALIDATION RESULTS")
    print("="*60)
    
    summary = dashboard_report.get('summary', {})
    print(f"📈 Overall Status: {summary.get('overall_status', 'unknown').upper()}")
    print(f"⏰ Report Time: {dashboard_report.get('report_timestamp', 'unknown')}")
    
    # Accuracy Results
    accuracy = dashboard_report.get('metrics', {}).get('accuracy', {})
    if accuracy and not accuracy.get('error'):
        print(f"\n🎯 ACCURACY METRICS")
        print(f"   Overall Accuracy: {accuracy.get('overall_accuracy', 0):.1%}")
        
        field_accuracies = accuracy.get('field_accuracies', {})
        for field, stats in field_accuracies.items():
            if isinstance(stats, dict):
                print(f"   {field.replace('_', ' ').title()}: {stats.get('mean', 0):.1%} (min: {stats.get('min', 0):.1%}, max: {stats.get('max', 0):.1%})")
        
        perf_stats = accuracy.get('performance_stats', {})
        if perf_stats:
            print(f"   Processing Time: {perf_stats.get('mean_processing_time_ms', 0):.0f}ms avg, {perf_stats.get('p95_processing_time_ms', 0):.0f}ms p95")
    
    # Performance Results
    latency = dashboard_report.get('metrics', {}).get('latency', {})
    if latency and not latency.get('error'):
        print(f"\n⚡ PERFORMANCE METRICS")
        system_metrics = latency.get('system_metrics', {})
        if system_metrics:
            print(f"   CPU Usage: {system_metrics.get('cpu_usage_percent', 0):.1f}%")
            print(f"   Memory Usage: {system_metrics.get('memory_usage_percent', 0):.1f}%")
            print(f"   Disk Usage: {system_metrics.get('disk_usage_percent', 0):.1f}%")
        
        component_metrics = latency.get('component_metrics', {})
        if component_metrics:
            print(f"   Component Latencies:")
            for component, values in component_metrics.items():
                if isinstance(values, list) and values:
                    avg_latency = sum(values) / len(values)
                    print(f"     {component.replace('_', ' ').title()}: {avg_latency:.0f}ms avg")
    
    # Cache Results
    cache = dashboard_report.get('metrics', {}).get('cache', {})
    if cache and not cache.get('error'):
        print(f"\n🗄️  CACHE METRICS")
        cache_stats = cache.get('cache_stats', {})
        if cache_stats:
            print(f"   Hit Rate: {cache_stats.get('hit_rate', 0):.1%}")
            print(f"   Cache Size: {cache_stats.get('cache_size', 0)}/{cache_stats.get('max_cache_size', 0)} entries")
            print(f"   Performance Improvement: {cache_stats.get('average_hit_speedup_ms', 0):.0f}ms per hit")
        
        performance_analysis = cache.get('performance_analysis', {})
        if performance_analysis:
            print(f"   Performance Grade: {performance_analysis.get('performance_grade', 'unknown').title()}")
    
    # Calibration Results
    calibration = dashboard_report.get('metrics', {}).get('calibration', {})
    if calibration and not calibration.get('error'):
        print(f"\n🎯 CONFIDENCE CALIBRATION")
        print(f"   Expected Calibration Error: {calibration.get('expected_calibration_error', 0):.3f}")
        print(f"   Total Predictions: {calibration.get('total_predictions', 0)}")
        
        confidence_dist = calibration.get('confidence_distribution', {})
        if confidence_dist:
            total = sum(confidence_dist.values())
            if total > 0:
                print(f"   Confidence Distribution:")
                print(f"     High (≥0.8): {confidence_dist.get('high', 0)/total:.1%}")
                print(f"     Medium (0.4-0.8): {confidence_dist.get('medium', 0)/total:.1%}")
                print(f"     Low (<0.4): {confidence_dist.get('low', 0)/total:.1%}")
        
        accuracy_by_bin = calibration.get('accuracy_by_confidence_bin', {})
        if accuracy_by_bin:
            print(f"   Accuracy by Confidence:")
            for bin_name, accuracy in accuracy_by_bin.items():
                print(f"     {bin_name.title()}: {accuracy:.1%}")
    
    # Alerts and Recommendations
    alerts = summary.get('alerts', [])
    if alerts:
        print(f"\n🚨 ALERTS")
        for alert in alerts:
            print(f"   ⚠️  {alert}")
    
    recommendations = summary.get('recommendations', [])
    if recommendations:
        print(f"\n💡 RECOMMENDATIONS")
        for rec in recommendations:
            print(f"   💡 {rec}")
    
    if not alerts:
        print(f"\n✅ No alerts - system is performing well!")
    
    print("="*60)
    
    # Save demo report
    report_file = f"demo_production_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    try:
        with open(report_file, 'w') as f:
            json.dump(dashboard_report, f, indent=2, default=str)
        print(f"\n📄 Demo report saved to: {report_file}")
    except Exception as e:
        logger.error(f"Failed to save demo report: {e}")
    
    print(f"\n🎉 Demo completed successfully!")
    print(f"\nThis demonstrates the production validation capabilities:")
    print(f"✅ Golden set accuracy monitoring")
    print(f"✅ Component latency tracking")
    print(f"✅ Confidence calibration validation")
    print(f"✅ Cache performance monitoring")
    print(f"✅ Comprehensive health assessment")
    print(f"✅ Automated alerting and recommendations")


def main():
    """Main demo function."""
    try:
        asyncio.run(run_demo())
    except KeyboardInterrupt:
        print("\n\n👋 Demo interrupted by user")
    except Exception as e:
        logger.error(f"Demo failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()