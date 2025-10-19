#!/usr/bin/env python3
"""
Comprehensive monitoring for Calendar API on Render.
"""

import requests
import json
import time
from datetime import datetime, timedelta
import sys
from typing import Dict, Any, List
import threading
import queue

class RenderAPIMonitor:
    """Monitor Calendar API deployed on Render."""
    
    def __init__(self, api_url: str = "https://calendar-api-wrxz.onrender.com"):
        self.api_url = api_url.rstrip('/')
        self.metrics_history = []
        self.alerts = []
        self.is_monitoring = False
        
    def check_health(self) -> Dict[str, Any]:
        """Check API health and return detailed status."""
        try:
            response = requests.get(f"{self.api_url}/health", timeout=10)
            if response.status_code == 200:
                health_data = response.json()
                
                # Analyze health status
                status = health_data.get('status', 'unknown')
                services = health_data.get('services', {})
                
                # Count service issues
                healthy_services = sum(1 for s in services.values() if s == 'healthy')
                total_services = len(services)
                
                return {
                    'timestamp': datetime.now(),
                    'status': status,
                    'services': services,
                    'uptime_seconds': health_data.get('uptime_seconds', 0),
                    'healthy_ratio': healthy_services / total_services if total_services > 0 else 0,
                    'response_time_ms': response.elapsed.total_seconds() * 1000,
                    'http_status': response.status_code,
                    'available': True
                }
            else:
                return {
                    'timestamp': datetime.now(),
                    'status': 'error',
                    'http_status': response.status_code,
                    'available': False,
                    'error': f"HTTP {response.status_code}"
                }
        except Exception as e:
            return {
                'timestamp': datetime.now(),
                'status': 'error',
                'available': False,
                'error': str(e)
            }
    
    def test_parse_functionality(self) -> Dict[str, Any]:
        """Test the main parse functionality."""
        test_cases = [
            "Meeting with team tomorrow at 2pm",
            "Doctor appointment next Friday at 10:30 AM",
            "Conference call on Monday 3pm"
        ]
        
        results = []
        
        for test_text in test_cases:
            try:
                response = requests.post(
                    f"{self.api_url}/parse",
                    json={
                        "text": test_text,
                        "now": datetime.now().isoformat(),
                        "timezone_offset": -480
                    },
                    timeout=15
                )
                
                if response.status_code == 200:
                    result = response.json()
                    results.append({
                        'test_text': test_text,
                        'success': True,
                        'confidence': result.get('confidence_score', 0),
                        'parsing_path': result.get('parsing_path', 'unknown'),
                        'response_time_ms': response.elapsed.total_seconds() * 1000
                    })
                else:
                    results.append({
                        'test_text': test_text,
                        'success': False,
                        'error': f"HTTP {response.status_code}",
                        'response_time_ms': response.elapsed.total_seconds() * 1000
                    })
            except Exception as e:
                results.append({
                    'test_text': test_text,
                    'success': False,
                    'error': str(e),
                    'response_time_ms': 0
                })
        
        # Calculate overall success rate
        successful = sum(1 for r in results if r['success'])
        success_rate = successful / len(results) if results else 0
        avg_confidence = sum(r.get('confidence', 0) for r in results if r['success']) / successful if successful > 0 else 0
        avg_response_time = sum(r['response_time_ms'] for r in results) / len(results) if results else 0
        
        return {
            'timestamp': datetime.now(),
            'success_rate': success_rate,
            'avg_confidence': avg_confidence,
            'avg_response_time_ms': avg_response_time,
            'test_results': results
        }
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get Prometheus metrics if available."""
        try:
            response = requests.get(f"{self.api_url}/metrics", timeout=10)
            if response.status_code == 200:
                # Parse basic metrics from Prometheus format
                metrics_text = response.text
                metrics = {}
                
                for line in metrics_text.split('\n'):
                    if line and not line.startswith('#'):
                        try:
                            if ' ' in line:
                                metric_name, value = line.split(' ', 1)
                                if '{' not in metric_name:  # Simple metrics only
                                    metrics[metric_name] = float(value)
                        except:
                            continue
                
                return {
                    'timestamp': datetime.now(),
                    'available': True,
                    'metrics': metrics,
                    'response_time_ms': response.elapsed.total_seconds() * 1000
                }
            else:
                return {'timestamp': datetime.now(), 'available': False, 'error': f"HTTP {response.status_code}"}
        except Exception as e:
            return {'timestamp': datetime.now(), 'available': False, 'error': str(e)}
    
    def collect_comprehensive_status(self) -> Dict[str, Any]:
        """Collect all monitoring data."""
        print("🔍 Collecting comprehensive status...")
        
        # Collect all data
        health_data = self.check_health()
        parse_data = self.test_parse_functionality()
        metrics_data = self.get_metrics()
        
        # Combine into comprehensive status
        status = {
            'timestamp': datetime.now(),
            'health': health_data,
            'functionality': parse_data,
            'metrics': metrics_data,
            'overall_status': self._determine_overall_status(health_data, parse_data)
        }
        
        # Store in history
        self.metrics_history.append(status)
        
        # Keep only last 100 entries
        if len(self.metrics_history) > 100:
            self.metrics_history = self.metrics_history[-100:]
        
        return status
    
    def _determine_overall_status(self, health_data: Dict, parse_data: Dict) -> str:
        """Determine overall system status."""
        if not health_data.get('available', False):
            return 'critical'
        
        if health_data.get('status') == 'healthy' and parse_data.get('success_rate', 0) > 0.8:
            return 'healthy'
        elif health_data.get('status') in ['degraded', 'warning'] or parse_data.get('success_rate', 0) > 0.5:
            return 'degraded'
        else:
            return 'critical'
    
    def print_status_report(self, status: Dict[str, Any]):
        """Print a comprehensive status report."""
        print("\n" + "=" * 80)
        print(f"📊 Calendar API Status Report - {status['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)
        
        # Overall status
        overall = status['overall_status']
        status_emoji = {"healthy": "🟢", "degraded": "🟡", "critical": "🔴"}.get(overall, "⚪")
        print(f"\n{status_emoji} Overall Status: {overall.upper()}")
        
        # Health details
        health = status['health']
        print(f"\n🏥 Health Check:")
        print(f"   Available: {'✅' if health.get('available') else '❌'}")
        if health.get('available'):
            print(f"   Status: {health.get('status', 'unknown')}")
            print(f"   Uptime: {health.get('uptime_seconds', 0):.0f} seconds")
            print(f"   Response Time: {health.get('response_time_ms', 0):.0f}ms")
            
            services = health.get('services', {})
            if services:
                print(f"   Services:")
                for service, service_status in services.items():
                    emoji = "🟢" if service_status == "healthy" else "🟡" if service_status == "warning" else "🔴"
                    print(f"     {service}: {emoji} {service_status}")
        else:
            print(f"   Error: {health.get('error', 'Unknown error')}")
        
        # Functionality test
        func = status['functionality']
        print(f"\n🧪 Functionality Tests:")
        print(f"   Success Rate: {func.get('success_rate', 0):.1%}")
        print(f"   Avg Confidence: {func.get('avg_confidence', 0):.2f}")
        print(f"   Avg Response Time: {func.get('avg_response_time_ms', 0):.0f}ms")
        
        # Test details
        test_results = func.get('test_results', [])
        if test_results:
            print(f"   Test Details:")
            for result in test_results:
                status_icon = "✅" if result['success'] else "❌"
                print(f"     {status_icon} \"{result['test_text'][:30]}...\"")
                if result['success']:
                    print(f"        Confidence: {result.get('confidence', 0):.2f}, Time: {result.get('response_time_ms', 0):.0f}ms")
                else:
                    print(f"        Error: {result.get('error', 'Unknown')}")
        
        # Metrics
        metrics = status['metrics']
        print(f"\n📈 Metrics:")
        print(f"   Available: {'✅' if metrics.get('available') else '❌'}")
        if metrics.get('available'):
            print(f"   Response Time: {metrics.get('response_time_ms', 0):.0f}ms")
            metric_data = metrics.get('metrics', {})
            if metric_data:
                print(f"   Key Metrics: {len(metric_data)} available")
        
        print("\n" + "=" * 80)
    
    def monitor_continuous(self, interval: int = 60):
        """Run continuous monitoring."""
        print(f"🚀 Starting continuous monitoring (interval: {interval}s)")
        print("Press Ctrl+C to stop\n")
        
        self.is_monitoring = True
        
        try:
            while self.is_monitoring:
                status = self.collect_comprehensive_status()
                self.print_status_report(status)
                
                # Check for alerts
                self._check_alerts(status)
                
                print(f"\n⏰ Next check in {interval} seconds...")
                time.sleep(interval)
        
        except KeyboardInterrupt:
            print("\n👋 Monitoring stopped by user")
            self.is_monitoring = False
    
    def _check_alerts(self, status: Dict[str, Any]):
        """Check for alert conditions."""
        alerts = []
        
        # Check if API is down
        if not status['health'].get('available'):
            alerts.append("🚨 API is not responding")
        
        # Check if functionality is severely degraded
        if status['functionality'].get('success_rate', 0) < 0.5:
            alerts.append("🚨 Parse functionality severely degraded")
        
        # Check response times
        if status['health'].get('response_time_ms', 0) > 5000:
            alerts.append("⚠️ High response times detected")
        
        # Print alerts
        for alert in alerts:
            print(f"\n{alert}")
            self.alerts.append({
                'timestamp': datetime.now(),
                'message': alert
            })

def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Monitor Calendar API on Render')
    parser.add_argument('--url', default='https://calendar-api-wrxz.onrender.com', help='API URL')
    parser.add_argument('--continuous', action='store_true', help='Run continuous monitoring')
    parser.add_argument('--interval', type=int, default=60, help='Monitoring interval in seconds')
    
    args = parser.parse_args()
    
    monitor = RenderAPIMonitor(args.url)
    
    if args.continuous:
        monitor.monitor_continuous(args.interval)
    else:
        status = monitor.collect_comprehensive_status()
        monitor.print_status_report(status)

if __name__ == "__main__":
    main()