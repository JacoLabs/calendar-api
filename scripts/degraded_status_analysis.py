#!/usr/bin/env python3
"""
Detailed analysis of the health status in Calendar API.
"""

import requests
import json
from datetime import datetime

def analyze_status():
    """Analyze the current health status."""
    
    print("🔍 HEALTH STATUS ANALYSIS")
    print("=" * 60)
    
    # Get current health status
    try:
        response = requests.get("https://calendar-api-wrxz.onrender.com/health", timeout=10)
        if response.status_code == 200:
            health_data = response.json()
            
            print("📊 Current Health Status:")
            overall_status = health_data.get('status', 'unknown').upper()
            status_emoji = "🟢" if overall_status == "HEALTHY" else "🟡" if overall_status == "DEGRADED" else "🔴"
            print(f"   Overall Status: {status_emoji} {overall_status}")
            print(f"   Uptime: {health_data.get('uptime_seconds', 0):.0f} seconds")
            print()
            
            # Analyze each service
            services = health_data.get('services', {})
            print("🔧 Service Analysis:")
            
            issues_found = []
            warnings_found = []
            
            for service, status in services.items():
                emoji = "🟢" if status == "healthy" else "🟡" if status == "warning" else "🔴"
                print(f"   {service}: {emoji} {status}")
                
                # Detailed analysis for each service
                if service == "llm":
                    if status == "healthy":
                        print("      ✅ WORKING: LLM service (OpenAI) is functioning correctly")
                    elif status == "unavailable":
                        print("      ℹ️  INFO: LLM unavailable - using heuristic fallback")
                        print("      💡 IMPACT: None - parser uses regex and deterministic methods first")
                        warnings_found.append("LLM unavailable (non-critical - fallback working)")
                    elif status == "slow":
                        print("      ⚠️  ISSUE: LLM responding slowly")
                        issues_found.append("LLM performance")
                    print()
                
                elif service == "disk" and status == "warning":
                    print("      ⚠️  ISSUE: Disk usage above 80% threshold")
                    print("      📝 CAUSE: Render container disk space is limited")
                    print("      🔧 FIX: Monitor disk usage, clear logs/cache if needed")
                    print("      💡 IMPACT: May affect performance if disk fills up")
                    warnings_found.append("Disk usage >80%")
                    print()
                
                elif service == "parser" and status == "healthy":
                    print("      ✅ WORKING: Parser service is functioning correctly")
                    print()
                
                elif service == "memory":
                    if status == "healthy":
                        print("      ✅ WORKING: Memory usage is within normal limits")
                    elif status == "warning":
                        print("      ⚠️  ISSUE: Memory usage above 85% threshold")
                        warnings_found.append("Memory usage >85%")
                    print()
            
            print()
            
        else:
            print(f"❌ Failed to get health status: HTTP {response.status_code}")
            return
    
    except Exception as e:
        print(f"❌ Error getting health status: {e}")
        return
    
    # Test actual functionality
    print("🧪 FUNCTIONALITY TEST:")
    try:
        test_response = requests.post(
            "https://calendar-api-wrxz.onrender.com/parse",
            json={
                "text": "Team meeting tomorrow at 3pm in conference room A",
                "now": datetime.now().isoformat()
            },
            timeout=15
        )
        
        if test_response.status_code == 200:
            result = test_response.json()
            print("   ✅ Parse endpoint working perfectly")
            print(f"   📝 Title: {result.get('title', 'N/A')}")
            print(f"   🎯 Confidence: {result.get('confidence_score', 0):.2f}")
            print(f"   🛤️  Parsing Path: {result.get('parsing_path', 'unknown')}")
            print(f"   ⏱️  Response Time: {test_response.elapsed.total_seconds() * 1000:.0f}ms")
        else:
            print(f"   ❌ Parse test failed: HTTP {test_response.status_code}")
            issues_found.append("Parse endpoint failing")
    
    except Exception as e:
        print(f"   ❌ Parse test error: {e}")
        issues_found.append(f"Parse endpoint error: {e}")
    
    print()
    
    # Check cache stats
    print("💾 CACHE STATUS:")
    try:
        cache_response = requests.get("https://calendar-api-wrxz.onrender.com/cache/stats", timeout=10)
        if cache_response.status_code == 200:
            cache_data = cache_response.json()
            if cache_data.get('status') == 'error':
                print("   ❌ Cache statistics endpoint error")
                issues_found.append("Cache stats endpoint")
            else:
                print("   ✅ Cache statistics working")
                if 'hit_ratio' in cache_data:
                    print(f"   📊 Hit Ratio: {cache_data['hit_ratio'] * 100:.1f}%")
                if 'entries_count' in cache_data:
                    print(f"   📝 Entries: {cache_data['entries_count']}")
        else:
            print(f"   ❌ Cache stats failed: HTTP {cache_response.status_code}")
            issues_found.append("Cache stats endpoint")
    
    except Exception as e:
        print(f"   ❌ Cache stats error: {e}")
        issues_found.append(f"Cache stats error: {e}")
    
    print()
    
    # Summary
    print("📋 SUMMARY:")
    if overall_status == "HEALTHY":
        print("   🎯 SYSTEM STATUS: ✅ HEALTHY")
        print("   📊 USER IMPACT: None - all features work perfectly")
        print("   🚀 PRODUCTION READY: Yes")
    elif overall_status == "DEGRADED":
        print("   🎯 SYSTEM STATUS: ⚠️ DEGRADED")
        print("   📊 USER IMPACT: Minimal - core functionality works")
        print("   🔧 ACTION NEEDED: Review issues below")
    else:
        print("   🎯 SYSTEM STATUS: ❌ UNHEALTHY")
        print("   📊 USER IMPACT: High - service may not be functioning")
        print("   🚨 ACTION NEEDED: Immediate attention required")
    
    print()
    
    # Issues and recommendations
    if issues_found:
        print("🔧 ISSUES FOUND:")
        for issue in issues_found:
            print(f"   • {issue}")
        print()
    
    if warnings_found:
        print("⚠️  WARNINGS (Non-Critical):")
        for warning in warnings_found:
            print(f"   • {warning}")
        print()
    
    if not issues_found and not warnings_found:
        print("✨ NO ISSUES FOUND")
        print("   Everything is working as expected!")
        print()
    
    # Priority assessment
    print("🎯 PRIORITY ASSESSMENT:")
    if overall_status == "HEALTHY" and not issues_found:
        print("   🟢 STATUS: Excellent - no action needed")
        print("   💡 RECOMMENDATION: Monitor disk usage periodically")
    elif overall_status == "HEALTHY" and warnings_found:
        print("   🟡 STATUS: Good with minor warnings")
        print("   💡 RECOMMENDATION: Address warnings when convenient")
    elif overall_status == "DEGRADED":
        print("   🟡 STATUS: Degraded but functional")
        print("   💡 RECOMMENDATION: Investigate and fix issues")
    else:
        print("   🔴 STATUS: Critical attention needed")
        print("   💡 RECOMMENDATION: Immediate action required")

if __name__ == "__main__":
    analyze_status()