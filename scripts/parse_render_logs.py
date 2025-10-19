#!/usr/bin/env python3
"""
Parse and analyze Render logs for Calendar API.
"""

import re
from datetime import datetime
from collections import defaultdict, Counter
import sys

def parse_log_line(line):
    """Parse a single log line."""
    # Render log format: timestamp level module message
    pattern = r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+Z)\s+(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})\s+-\s+([^\s]+)\s+-\s+(\w+)\s+-\s+(.*)'
    
    match = re.match(pattern, line)
    if match:
        render_timestamp, app_timestamp, module, level, message = match.groups()
        return {
            'render_timestamp': render_timestamp,
            'app_timestamp': app_timestamp,
            'module': module,
            'level': level,
            'message': message,
            'raw': line
        }
    
    # Handle special Render messages
    if '==>' in line:
        return {
            'render_timestamp': None,
            'app_timestamp': None,
            'module': 'render',
            'level': 'INFO',
            'message': line.strip(),
            'raw': line
        }
    
    return None

def analyze_logs(log_text):
    """Analyze the log content."""
    lines = log_text.strip().split('\n')
    parsed_logs = []
    
    for line in lines:
        if line.strip():
            parsed = parse_log_line(line)
            if parsed:
                parsed_logs.append(parsed)
    
    # Statistics
    stats = {
        'total_lines': len(parsed_logs),
        'levels': Counter(),
        'modules': Counter(),
        'errors': [],
        'warnings': [],
        'requests': [],
        'startup_events': [],
        'issues': []
    }
    
    for log in parsed_logs:
        stats['levels'][log['level']] += 1
        stats['modules'][log['module']] += 1
        
        message = log['message']
        
        # Categorize messages
        if log['level'] == 'ERROR':
            stats['errors'].append(log)
        elif log['level'] == 'WARNING':
            stats['warnings'].append(log)
        
        # Track requests
        if 'Request started' in message:
            # Extract request info
            request_match = re.search(r'Method: (\w+), Path: ([^,]+)', message)
            if request_match:
                method, path = request_match.groups()
                stats['requests'].append({
                    'timestamp': log['app_timestamp'],
                    'method': method,
                    'path': path,
                    'log': log
                })
        
        # Track startup events
        if any(keyword in message for keyword in ['Started server', 'Application startup', 'service is live']):
            stats['startup_events'].append(log)
        
        # Identify specific issues
        if 'LLM health check failed' in message:
            stats['issues'].append({
                'type': 'LLM_SERVICE_ERROR',
                'message': message,
                'log': log
            })
        
        if 'Cache statistics error' in message:
            stats['issues'].append({
                'type': 'CACHE_ERROR',
                'message': message,
                'log': log
            })
    
    return parsed_logs, stats

def print_analysis(stats):
    """Print analysis results."""
    print("🔍 Render Log Analysis")
    print("=" * 60)
    
    # Overview
    print(f"📊 Overview:")
    print(f"   Total log entries: {stats['total_lines']}")
    print(f"   Log levels: {dict(stats['levels'])}")
    print(f"   Modules: {dict(stats['modules'])}")
    print()
    
    # Issues
    if stats['issues']:
        print("🚨 Critical Issues Found:")
        for issue in stats['issues']:
            print(f"   • {issue['type']}: {issue['message']}")
        print()
    
    # Errors
    if stats['errors']:
        print("❌ Errors:")
        for error in stats['errors']:
            print(f"   • [{error['app_timestamp']}] {error['module']}: {error['message']}")
        print()
    
    # Warnings
    if stats['warnings']:
        print("⚠️  Warnings:")
        for warning in stats['warnings']:
            print(f"   • [{warning['app_timestamp']}] {warning['module']}: {warning['message']}")
        print()
    
    # Recent requests
    if stats['requests']:
        print("📡 Recent API Requests:")
        for req in stats['requests'][-10:]:  # Last 10 requests
            print(f"   • {req['method']} {req['path']} at {req['timestamp']}")
        print()
    
    # Startup events
    if stats['startup_events']:
        print("🚀 Startup Events:")
        for event in stats['startup_events']:
            print(f"   • {event['message']}")
        print()

def main():
    """Main function."""
    # Sample log data from your Render logs
    sample_logs = """2025-10-16T02:31:01.967656011Z ==> Running 'uvicorn app.main:app --host 0.0.0.0 --port 10000'
2025-10-16T02:31:04.673175055Z 2025-10-16 02:31:04 - api.startup - INFO - Logging system initialized [logging_config.py:302]
2025-10-16T02:31:04.689776623Z 2025-10-16 02:31:04 - api.main - INFO - Created static directory: static [main.py:202]
2025-10-16T02:31:04.689970278Z 2025-10-16 02:31:04 - api.main - INFO - Configured static file serving at /static [main.py:206]
2025-10-16T02:31:04.746826187Z 2025-10-16 02:31:04 - uvicorn.error - INFO - Started server process [62] [server.py:82]
2025-10-16T02:31:04.74694031Z 2025-10-16 02:31:04 - uvicorn.error - INFO - Waiting for application startup. [on.py:48]
2025-10-16T02:31:04.747230278Z 2025-10-16 02:31:04 - api.main - INFO - Starting API server with enhanced endpoints [main.py:158]
2025-10-16T02:31:04.747400793Z 2025-10-16 02:31:04 - uvicorn.error - INFO - Application startup complete. [on.py:62]
2025-10-16T02:31:04.74803786Z 2025-10-16 02:31:04 - uvicorn.error - INFO - Uvicorn running on http://0.0.0.0:10000 (Press CTRL+C to quit) [server.py:214]
2025-10-16T02:31:10.736889404Z ==> Your service is live 🎉
2025-10-16T02:32:04.754704008Z 2025-10-16 02:32:04 - api.app.health - WARNING - LLM health check failed: 'LLMService' object has no attribute 'extract_event_info' [health.py:123]
2025-10-16T02:32:07.63399227Z 2025-10-16 02:32:07 - api.main - WARNING - Cache statistics error: 'CacheManager' object has no attribute 'get_statistics' [main.py:621]"""
    
    if len(sys.argv) > 1:
        # Read from file if provided
        try:
            with open(sys.argv[1], 'r') as f:
                log_content = f.read()
        except Exception as e:
            print(f"Error reading file: {e}")
            return
    else:
        # Use sample logs
        log_content = sample_logs
    
    parsed_logs, stats = analyze_logs(log_content)
    print_analysis(stats)
    
    # Recommendations
    print("💡 Recommendations:")
    if any(issue['type'] == 'LLM_SERVICE_ERROR' for issue in stats['issues']):
        print("   • Fix LLM service: Add missing 'extract_event_info' method")
    if any(issue['type'] == 'CACHE_ERROR' for issue in stats['issues']):
        print("   • Fix cache manager: Add missing 'get_statistics' method")
    if stats['warnings']:
        print("   • Address warnings to improve service health status")
    
    print(f"\n📋 Service Status: {'🟡 Degraded' if stats['warnings'] or stats['errors'] else '🟢 Healthy'}")

if __name__ == "__main__":
    main()