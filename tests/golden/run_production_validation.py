#!/usr/bin/env python3
"""
Production Validation Runner.

This script runs comprehensive production validation including:
- Golden set accuracy validation
- Component latency tracking
- Confidence calibration validation
- Cache performance monitoring
- Production performance reporting

Usage:
    python run_production_validation.py --single-run
    python run_production_validation.py --continuous
    python run_production_validation.py --dashboard
"""

import asyncio
import argparse
import logging
import sys
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from scripts.production_performance_validator import ProductionPerformanceValidator
from scripts.production_dashboard import ProductionDashboard

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def run_single_validation(api_url: str, golden_set_path: str):
    """Run a single validation cycle."""
    logger.info("Starting single production validation cycle")
    
    validator = ProductionPerformanceValidator(
        api_base_url=api_url,
        golden_set_path=golden_set_path
    )
    
    # Generate comprehensive report
    report = await validator.generate_production_dashboard_report()
    
    # Print summary
    print("\n" + "="*80)
    print("PRODUCTION VALIDATION REPORT")
    print("="*80)
    
    summary = report.get('summary', {})
    print(f"Overall Status: {summary.get('overall_status', 'unknown').upper()}")
    print(f"Report Time: {report.get('report_timestamp', 'unknown')}")
    
    # Accuracy metrics
    accuracy = report.get('metrics', {}).get('accuracy', {})
    if accuracy and not accuracy.get('error'):
        print(f"\n📊 ACCURACY METRICS")
        print(f"   Overall Accuracy: {accuracy.get('overall_accuracy', 0):.2%}")
        
        field_accuracies = accuracy.get('field_accuracies', {})
        for field, stats in field_accuracies.items():
            if isinstance(stats, dict):
                print(f"   {field.title()} Accuracy: {stats.get('mean', 0):.2%}")
        
        perf_stats = accuracy.get('performance_stats', {})
        if perf_stats:
            print(f"   Mean Processing Time: {perf_stats.get('mean_processing_time_ms', 0):.0f}ms")
            print(f"   P95 Processing Time: {perf_stats.get('p95_processing_time_ms', 0):.0f}ms")
    else:
        print(f"\n❌ ACCURACY METRICS: {accuracy.get('error', 'Unknown error')}")
    
    # Performance metrics
    latency = report.get('metrics', {}).get('latency', {})
    if latency and not latency.get('error'):
        print(f"\n⚡ PERFORMANCE METRICS")
        system_metrics = latency.get('system_metrics', {})
        if system_metrics:
            print(f"   CPU Usage: {system_metrics.get('cpu_usage_percent', 0):.1f}%")
            print(f"   Memory Usage: {system_metrics.get('memory_usage_percent', 0):.1f}%")
    else:
        print(f"\n❌ PERFORMANCE METRICS: {latency.get('error', 'Unknown error')}")
    
    # Cache metrics
    cache = report.get('metrics', {}).get('cache', {})
    if cache and not cache.get('error'):
        print(f"\n🗄️  CACHE METRICS")
        cache_stats = cache.get('cache_stats', {})
        if cache_stats:
            print(f"   Hit Rate: {cache_stats.get('hit_rate', 0):.2%}")
            print(f"   Cache Size: {cache_stats.get('cache_size', 0)} entries")
            
        performance_analysis = cache.get('performance_analysis', {})
        if performance_analysis:
            print(f"   Performance Grade: {performance_analysis.get('performance_grade', 'unknown').title()}")
    else:
        print(f"\n❌ CACHE METRICS: {cache.get('error', 'Unknown error')}")
    
    # Calibration metrics
    calibration = report.get('metrics', {}).get('calibration', {})
    if calibration and not calibration.get('error'):
        print(f"\n🎯 CALIBRATION METRICS")
        print(f"   Expected Calibration Error: {calibration.get('expected_calibration_error', 0):.3f}")
        print(f"   Total Predictions: {calibration.get('total_predictions', 0)}")
        
        confidence_dist = calibration.get('confidence_distribution', {})
        if confidence_dist:
            total = sum(confidence_dist.values())
            if total > 0:
                print(f"   High Confidence: {confidence_dist.get('high', 0)/total:.1%}")
                print(f"   Medium Confidence: {confidence_dist.get('medium', 0)/total:.1%}")
                print(f"   Low Confidence: {confidence_dist.get('low', 0)/total:.1%}")
    else:
        print(f"\n❌ CALIBRATION METRICS: {calibration.get('error', 'Unknown error')}")
    
    # Alerts and recommendations
    alerts = summary.get('alerts', [])
    if alerts:
        print(f"\n🚨 ALERTS")
        for alert in alerts:
            print(f"   - {alert}")
    
    recommendations = summary.get('recommendations', [])
    if recommendations:
        print(f"\n💡 RECOMMENDATIONS")
        for rec in recommendations:
            print(f"   - {rec}")
    
    print("="*80)
    
    # Save detailed report
    report_file = f"production_validation_report_{report.get('report_timestamp', '').replace(':', '-').replace('.', '-')}.json"
    try:
        import json
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        print(f"\n📄 Detailed report saved to: {report_file}")
    except Exception as e:
        logger.error(f"Failed to save report: {e}")
    
    return report


async def run_continuous_validation(api_url: str, golden_set_path: str, interval: int):
    """Run continuous validation."""
    logger.info(f"Starting continuous production validation (interval: {interval}s)")
    
    validator = ProductionPerformanceValidator(
        api_base_url=api_url,
        golden_set_path=golden_set_path,
        validation_interval=interval
    )
    
    await validator.run_continuous_validation()


def run_dashboard(api_url: str, update_interval: int):
    """Run the production dashboard."""
    logger.info("Starting production dashboard")
    
    dashboard = ProductionDashboard(api_base_url=api_url)
    dashboard.update_interval = update_interval
    
    print("Starting Production Performance Dashboard...")
    print(f"API URL: {api_url}")
    print(f"Update Interval: {update_interval} seconds")
    print("Close the window to exit.")
    
    dashboard.create_gui_dashboard()


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description='Production Validation Runner',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run single validation cycle
  python run_production_validation.py --single-run
  
  # Run continuous validation every 5 minutes
  python run_production_validation.py --continuous --interval 300
  
  # Run GUI dashboard
  python run_production_validation.py --dashboard
  
  # Use custom API URL
  python run_production_validation.py --single-run --api-url http://production-api.com
        """
    )
    
    # Mode selection (mutually exclusive)
    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument('--single-run', action='store_true', 
                           help='Run single validation cycle')
    mode_group.add_argument('--continuous', action='store_true', 
                           help='Run continuous validation')
    mode_group.add_argument('--dashboard', action='store_true', 
                           help='Run GUI dashboard')
    
    # Configuration options
    parser.add_argument('--api-url', default='http://localhost:8000', 
                       help='API base URL (default: http://localhost:8000)')
    parser.add_argument('--golden-set', default='tests/golden_set.json', 
                       help='Golden test set path (default: tests/golden_set.json)')
    parser.add_argument('--interval', type=int, default=300, 
                       help='Validation interval in seconds (default: 300)')
    parser.add_argument('--update-interval', type=int, default=30, 
                       help='Dashboard update interval in seconds (default: 30)')
    parser.add_argument('--verbose', '-v', action='store_true', 
                       help='Enable verbose logging')
    
    args = parser.parse_args()
    
    # Configure logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Validate golden set file exists
    golden_set_path = Path(args.golden_set)
    if not golden_set_path.exists():
        logger.error(f"Golden set file not found: {golden_set_path}")
        logger.info("Please ensure the golden test set exists or run the test suite to generate it")
        sys.exit(1)
    
    try:
        if args.single_run:
            # Run single validation
            report = asyncio.run(run_single_validation(args.api_url, args.golden_set))
            
            # Exit with appropriate code based on overall status
            summary = report.get('summary', {})
            overall_status = summary.get('overall_status', 'unknown')
            
            if overall_status == 'healthy':
                sys.exit(0)
            elif overall_status == 'warning':
                sys.exit(1)
            else:  # critical or unknown
                sys.exit(2)
        
        elif args.continuous:
            # Run continuous validation
            asyncio.run(run_continuous_validation(args.api_url, args.golden_set, args.interval))
        
        elif args.dashboard:
            # Run GUI dashboard
            run_dashboard(args.api_url, args.update_interval)
    
    except KeyboardInterrupt:
        logger.info("Validation stopped by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Validation failed: {e}")
        sys.exit(3)


if __name__ == "__main__":
    main()