#!/usr/bin/env python3
"""
Check available logging endpoints on Render deployment.
"""

import requests
import json
from datetime import datetime

API_BASE_URL = "https://calendar-api-wrxz.onrender.com"

def check_endpoint(endpoint, description):
    """Check if an endpoint exists and what it returns."""
    try:
        response = requests.get(f"{API_BASE_URL}{endpoint}", timeout=10)
        print(f"📍 {description} ({endpoint})")
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                print(f"   Response: {json.dumps(data, indent=2)[:200]}...")
            except:
                print(f"   Response: {response.text[:200]}...")
        elif response.status_code == 404:
            print("   ❌ Not available")
        else:
            print(f"   ⚠️  Unexpected status: {response.text[:100]}")
        
        print()
        return response.status_code == 200
    except Exception as e:
        print(f"   🔴 Error: {e}")
        print()
        return False

def main():
    """Check all possible logging endpoints."""
    print("🔍 Checking Calendar API Logging Endpoints")
    print(f"📡 API: {API_BASE_URL}")
    print("=" * 60)
    
    # Common logging/monitoring endpoints to check
    endpoints = [
        ("/health", "Health Check"),
        ("/healthz", "Kubernetes Health Check"),
        ("/status", "Status Endpoint"),
        ("/metrics", "Prometheus Metrics"),
        ("/logs", "Application Logs"),
        ("/logs/recent", "Recent Logs"),
        ("/admin/logs", "Admin Logs"),
        ("/api/logs", "API Logs"),
        ("/debug", "Debug Info"),
        ("/info", "System Info"),
        ("/stats", "Statistics"),
        ("/cache/stats", "Cache Statistics"),
        ("/monitoring", "Monitoring Dashboard"),
        ("/version", "Version Info")
    ]
    
    available_endpoints = []
    
    for endpoint, description in endpoints:
        if check_endpoint(endpoint, description):
            available_endpoints.append(endpoint)
    
    print("=" * 60)
    print("📋 Summary of Available Endpoints:")
    if available_endpoints:
        for endpoint in available_endpoints:
            print(f"   ✅ {endpoint}")
    else:
        print("   ❌ No additional logging endpoints found")
    
    print(f"\n💡 For Render-specific logs, check your Render dashboard:")
    print("   https://dashboard.render.com/")
    print("   Navigate to your service → Logs tab")

if __name__ == "__main__":
    main()