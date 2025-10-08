#!/usr/bin/env python3
"""
Lightweight API server for browser extension with minimal dependencies.
This server starts much faster than the full api_server.py.
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime, timedelta
import re
import logging

app = Flask(__name__)
CORS(app)

# Configure minimal logging
logging.basicConfig(level=logging.WARNING)

@app.route('/parse', methods=['POST'])
def parse_event():
    """Lightweight event parsing with basic regex patterns."""
    try:
        data = request.get_json()
        
        if not data or 'text' not in data:
            return jsonify({'error': 'Missing text parameter'}), 400
        
        text = data['text']
        result = parse_text_simple(text)
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def parse_text_simple(text):
    """Simple, fast text parsing without heavy dependencies."""
    result = {
        'title': '',
        'start_datetime': None,
        'end_datetime': None,
        'location': None,
        'description': text,
        'all_day': False,
        'confidence_score': 0.7,
        'parsing_path': 'lightweight_server'
    }
    
    # Extract title (first part before time/date indicators)
    title_match = re.match(r'^([^,]+?)(?:\s+(?:at|on|in|@|tomorrow|today|next|this)\s|$)', text, re.IGNORECASE)
    if title_match:
        result['title'] = title_match.group(1).strip()
    else:
        result['title'] = text[:50].strip()
    
    # Time parsing
    time_patterns = [
        r'\b(\d{1,2}):(\d{2})\s*(am|pm)\b',
        r'\b(\d{1,2})\s*(am|pm)\b',
        r'\b(\d{1,2}):(\d{2})\b'
    ]
    
    time_match = None
    for pattern in time_patterns:
        time_match = re.search(pattern, text, re.IGNORECASE)
        if time_match:
            break
    
    # Date parsing
    now = datetime.now()
    target_date = now
    
    if re.search(r'\btomorrow\b', text, re.IGNORECASE):
        target_date = now + timedelta(days=1)
    elif re.search(r'\btoday\b', text, re.IGNORECASE):
        target_date = now
    elif re.search(r'\bnext week\b', text, re.IGNORECASE):
        target_date = now + timedelta(days=7)
    
    # Set time if found
    if time_match:
        hours = int(time_match.group(1))
        minutes = int(time_match.group(2)) if time_match.group(2) else 0
        ampm = time_match.group(3) if len(time_match.groups()) >= 3 else None
        
        if ampm and ampm.lower() == 'pm' and hours != 12:
            hours += 12
        elif ampm and ampm.lower() == 'am' and hours == 12:
            hours = 0
        
        target_date = target_date.replace(hour=hours, minute=minutes, second=0, microsecond=0)
        result['start_datetime'] = target_date.isoformat()
        
        # End time (1 hour later)
        end_date = target_date + timedelta(hours=1)
        result['end_datetime'] = end_date.isoformat()
    
    # Location extraction
    location_patterns = [
        r'\b(?:at|in|@)\s+([^,\n]+?)(?:\s+(?:at|on|from|to)\s|\s*$)',
        r'\blocation:\s*([^,\n]+)'
    ]
    
    for pattern in location_patterns:
        location_match = re.search(pattern, text, re.IGNORECASE)
        if location_match:
            result['location'] = location_match.group(1).strip()
            break
    
    return result

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'server_type': 'lightweight',
        'timestamp': datetime.now().isoformat()
    })

if __name__ == '__main__':
    print("🚀 Starting Lightweight Calendar Event Parser API Server")
    print("📡 Browser extension can connect to: http://localhost:5000")
    print("⚡ Fast startup with basic parsing capabilities")
    
    app.run(host='localhost', port=5000, debug=False)