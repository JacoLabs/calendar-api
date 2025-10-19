#!/usr/bin/env python3
"""
Simple production monitoring script for Render-deployed Calendar API.
"""

import requests
import json
import time
from datetime import datetime
import sys

API_BASE_URL = "https://calendar-api-wrxz.onrender.com"

def check_health():
    """Check API health status."""
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=10)
        if response.status_code == 200:
            health_data = response.json()
            print(f"🟢 API Health Check - {datetime.now().strftime('%H:%M:%S')}")
            print(f"   Status: {health_data.get('status', 'unknown')}")
            print(f"   Uptime: {health_data.get('uptime_seconds', 0):.0f} seconds")
            
            services = health_data.get('services', {})
            for service, status in services.items():
                emoji = "🟢" if status == "healthy" else "🟡" if status == "warning" else "🔴"
                print(f"   {service}: {emoji} {status}")
            
            return health_data
        else:
            print(f"🔴 Health check failed: HTTP {response.status_code}")
            return None
    except Exception as e:
        print(f"🔴 Health check error: {e}")
        return None

def test_parse_endpoint():
    """Test the parse endpoint with a sample request."""
    try:
        test_data = {
            "text": "Meeting with team tomorrow at 2pm",
            "now": datetime.now().isoformat(),
            "timezone_offset": -480  # PST
        }
        
        response = requests.post(
            f"{API_BASE_URL}/parse", 
            json=test_data, 
            timeout=15
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"🟢 Parse Test - {datetime.now().strftime('%H:%M:%S')}")
            print(f"   Title: {result.get('title', 'N/A')}")
            print(f"   Confidence: {result.get('confidence_score', 0):.2f}")
            print(f"   Parsing Path: {result.get('parsing_path', 'unknown')}")
            return True
        else:
            print(f"🔴 Parse test failed: HTTP {response.status_code}")
            print(f"   Response: {response.text}")
            return False
    except Exception as e:
        print(f"🔴 Parse test error: {e}")
        return False

def monitor_continuous():
    """Continuously monitor the API."""
    print("🚀 Starting continuous monitoring of Calendar API")
    print(f"📡 Monitoring: {API_BASE_URL}")
    print("Press Ctrl+C to stop\n")
    
    try:
        while True:
            print("=" * 60)
            
            # Health check
            health_data = check_health()
            print()
            
            # Parse test
            test_parse_endpoint()
            print()
            
            # Wait before next check
            print(f"⏰ Next check in 60 seconds...")
            time.sleep(60)
            
    except KeyboardInterrupt:
        print("\n👋 Monitoring stopped by user")

def main():
    """Main function."""
    if len(sys.argv) > 1 and sys.argv[1] == "--continuous":
        monitor_continuous()
    else:
        print("🔍 Single API Check")
        print("=" * 40)
        check_health()
        print()
        test_parse_endpoint()
        print("\n💡 Use --continuous for continuous monitoring")

if __name__ == "__main__":
    main()