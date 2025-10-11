#!/usr/bin/env python3
"""
Simple monitoring dashboard script for Calendar API.
Provides real-time monitoring of key metrics and system health.
"""

import json
import time
import requests
import sys
from datetime import datetime
from typing import Dict, Any, Optional


class MonitoringDashboard:
    """Simple terminal-based monitoring dashboard."""
    
    def __init__(self, api_base_url: str = "http://localhost:8000"):
        self.api_base_url = api_base_url.rstrip('/')
        self.last_metrics = {}
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get current health status."""
        try:
            response = requests.get(f"{self.api_base_url}/healthz", timeout=5)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"error": str(e), "status": "unhealthy"}
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        try:
            response = requests.get(f"{self.api_base_url}/cache/stats", timeout=5)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"error": str(e)}
    
    def get_metrics(self) -> Dict[str, float]:
        """Parse Prometheus metrics."""
        try:
            response = requests.get(f"{self.api_base_url}/metrics", timeout=5)
            response.raise_for_status()
            
            metrics = {}
            for line in response.text.split('\n'):
                if line.startswith('#') or not line.strip():
                    continue
                
                parts = line.split(' ')
                if len(parts) >= 2:
                    metric_name = parts[0]
                    try:
                        metric_value = float(parts[1])
                        metrics[metric_name] = metric_value
                    except ValueError:
                        continue
            
            return metrics
        except Exception as e:
            return {"error": str(e)}
    
    def format_uptime(self, seconds: float) -> str:
        """Format uptime in human-readable format."""
        if seconds < 60:
            return f"{seconds:.0f}s"
        elif seconds < 3600:
            return f"{seconds/60:.1f}m"
        elif seconds < 86400:
            return f"{seconds/3600:.1f}h"
        else:
            return f"{seconds/86400:.1f}d"
    
    def format_bytes(self, bytes_value: float) -> str:
        """Format bytes in human-readable format."""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if bytes_value < 1024:
                return f"{bytes_value:.1f}{unit}"
            bytes_value /= 1024
        return f"{bytes_value:.1f}TB"
    
    def display_dashboard(self):
        """Display the monitoring dashboard."""
        # Clear screen
        print("\033[2J\033[H")
        
        # Header
        print("=" * 80)
        print(f"Calendar API Monitoring Dashboard - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)
        
        # Health Status
        health = self.get_health_status()
        print(f"\n🏥 HEALTH STATUS")
        print("-" * 40)
        
        if "error" in health:
            print(f"❌ API Status: ERROR - {health['error']}")
        else:
            status = health.get('status', 'unknown')
            status_emoji = "✅" if status == "healthy" else "⚠️" if status == "degraded" else "❌"
            print(f"{status_emoji} API Status: {status.upper()}")
            
            if 'uptime_seconds' in health:
                uptime = self.format_uptime(health['uptime_seconds'])
                print(f"⏱️  Uptime: {uptime}")
            
            # Service status
            services = health.get('services', {})
            for service, status in services.items():
                service_emoji = "✅" if status == "healthy" else "⚠️" if status in ["degraded", "slow"] else "❌"
                print(f"   {service_emoji} {service}: {status}")
        
        # Cache Statistics
        cache_stats = self.get_cache_stats()
        print(f"\n💾 CACHE PERFORMANCE")
        print("-" * 40)
        
        if "error" in cache_stats:
            print(f"❌ Cache Error: {cache_stats['error']}")
        else:
            hit_rate = cache_stats.get('hit_ratio', 0) * 100
            hit_rate_emoji = "✅" if hit_rate > 50 else "⚠️" if hit_rate > 20 else "❌"
            print(f"{hit_rate_emoji} Hit Rate: {hit_rate:.1f}%")
            
            if 'cache_size_mb' in cache_stats:
                size = cache_stats['cache_size_mb']
                max_size = cache_stats.get('max_cache_size_mb', 100)
                utilization = (size / max_size) * 100 if max_size > 0 else 0
                print(f"📊 Size: {size:.1f}MB / {max_size}MB ({utilization:.1f}%)")
            
            if 'entries_count' in cache_stats:
                print(f"📝 Entries: {cache_stats['entries_count']}")
            
            if 'average_hit_speedup_ms' in cache_stats:
                speedup = cache_stats['average_hit_speedup_ms']
                print(f"⚡ Avg Speedup: {speedup:.0f}ms")
        
        # Metrics
        metrics = self.get_metrics()
        print(f"\n📊 PERFORMANCE METRICS")
        print("-" * 40)
        
        if "error" in metrics:
            print(f"❌ Metrics Error: {metrics['error']}")
        else:
            # Request metrics
            total_requests = sum(v for k, v in metrics.items() if k.startswith('http_requests_total'))
            if total_requests > 0:
                print(f"📈 Total Requests: {total_requests:.0f}")
            
            # Error rate
            error_requests = sum(v for k, v in metrics.items() 
                               if k.startswith('http_requests_total') and '5' in k)
            if total_requests > 0:
                error_rate = (error_requests / total_requests) * 100
                error_emoji = "✅" if error_rate < 1 else "⚠️" if error_rate < 5 else "❌"
                print(f"{error_emoji} Error Rate: {error_rate:.2f}%")
            
            # Parsing accuracy
            accuracy = metrics.get('parsing_accuracy_score', 0) * 100
            if accuracy > 0:
                accuracy_emoji = "✅" if accuracy > 80 else "⚠️" if accuracy > 60 else "❌"
                print(f"{accuracy_emoji} Parsing Accuracy: {accuracy:.1f}%")
            
            # Memory usage
            memory_bytes = metrics.get('system_memory_usage_bytes', 0)
            if memory_bytes > 0:
                memory_mb = memory_bytes / 1024 / 1024
                memory_emoji = "✅" if memory_mb < 500 else "⚠️" if memory_mb < 800 else "❌"
                print(f"{memory_emoji} Memory Usage: {memory_mb:.0f}MB")
            
            # CPU usage
            cpu_percent = metrics.get('system_cpu_usage_percent', 0)
            if cpu_percent > 0:
                cpu_emoji = "✅" if cpu_percent < 50 else "⚠️" if cpu_percent < 80 else "❌"
                print(f"{cpu_emoji} CPU Usage: {cpu_percent:.1f}%")
            
            # LLM service
            llm_available = metrics.get('llm_service_available', 0)
            llm_emoji = "✅" if llm_available == 1 else "❌"
            llm_status = "Available" if llm_available == 1 else "Unavailable"
            print(f"{llm_emoji} LLM Service: {llm_status}")
        
        # Component Latencies
        component_metrics = {k: v for k, v in metrics.items() if 'component_latency' in k}
        if component_metrics:
            print(f"\n⚡ COMPONENT LATENCIES")
            print("-" * 40)
            
            # Group by component
            components = {}
            for metric_name, value in component_metrics.items():
                if 'component=' in metric_name:
                    component = metric_name.split('component="')[1].split('"')[0]
                    if component not in components:
                        components[component] = []
                    components[component].append(value * 1000)  # Convert to ms
            
            for component, latencies in components.items():
                if latencies:
                    avg_latency = sum(latencies) / len(latencies)
                    latency_emoji = "✅" if avg_latency < 100 else "⚠️" if avg_latency < 500 else "❌"
                    print(f"{latency_emoji} {component}: {avg_latency:.1f}ms")
        
        # Footer
        print("\n" + "=" * 80)
        print("Press Ctrl+C to exit | Refreshing every 10 seconds")
        print("=" * 80)
    
    def run(self, refresh_interval: int = 10):
        """Run the monitoring dashboard with auto-refresh."""
        try:
            while True:
                self.display_dashboard()
                time.sleep(refresh_interval)
        except KeyboardInterrupt:
            print("\n\nMonitoring dashboard stopped.")
            sys.exit(0)


def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Calendar API Monitoring Dashboard")
    parser.add_argument(
        "--url", 
        default="http://localhost:8000",
        help="API base URL (default: http://localhost:8000)"
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=10,
        help="Refresh interval in seconds (default: 10)"
    )
    
    args = parser.parse_args()
    
    dashboard = MonitoringDashboard(args.url)
    dashboard.run(args.interval)


if __name__ == "__main__":
    main()