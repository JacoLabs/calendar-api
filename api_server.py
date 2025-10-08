#!/usr/bin/env python3
"""
Simple API server to serve our hybrid regex/LLM parsing to the browser extension.
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime
import logging

from services.event_parser import EventParser

app = Flask(__name__)
CORS(app)  # Allow browser extension to call this API

# Initialize our hybrid parser
event_parser = EventParser()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.route('/parse', methods=['POST'])
def parse_event():
    """Parse event text using our hybrid regex/LLM system."""
    try:
        data = request.get_json()
        
        if not data or 'text' not in data:
            return jsonify({'error': 'Missing text parameter'}), 400
        
        text = data['text']
        current_time = datetime.now()
        
        if 'now' in data:
            try:
                current_time = datetime.fromisoformat(data['now'].replace('Z', '+00:00'))
            except:
                pass
        
        # Use our hybrid parsing system
        logger.info(f"Parsing text: '{text}'")
        logger.info(f"Text length: {len(text)}")
        logger.info(f"Text repr: {repr(text)}")  # This will show \n characters
        parsed_event = event_parser.parse_event_text(
            text, 
            current_time=current_time,
            timezone_offset=data.get('timezone_offset')
        )
        
        # Clean up the title if it's missing or too long
        title = parsed_event.title
        
        # Handle structured event text (like "Event Name DATE ... LOCATION ...")
        logger.info(f"Title length: {len(title)}, has DATE: {' DATE ' in title.upper()}")
        if title and len(title) > 50 and ' DATE ' in title.upper():
            import re
            logger.info("Attempting structured title extraction...")
            # Extract just the part before DATE/LOCATION/TIME
            structured_match = re.match(r'^(.+?)(?:\s+(?:DATE|TIME|LOCATION|WHEN|WHERE)\s)', title, re.IGNORECASE)
            logger.info(f"Regex match result: {structured_match}")
            if structured_match:
                title = structured_match.group(1).strip()
                logger.info(f"Structured title extraction: '{title}'")
        
        # Handle explicit title labels
        elif not title and 'title:' in text.lower():
            # Try to extract title manually as fallback
            import re
            title_match = re.search(r'title:\s*([^!]+!?)', text, re.IGNORECASE)
            if title_match:
                title = title_match.group(1).strip()
                logger.info(f"Manual title extraction: '{title}'")
        
        # Debug logging (after title cleanup)
        logger.info(f"Final title: '{title}'")
        logger.info(f"Parsed location: '{parsed_event.location}'")
        logger.info(f"Parsed description: '{parsed_event.description}'")
        logger.info(f"Parsing path: '{parsed_event.extraction_metadata.get('parsing_path', 'unknown')}'")
        logger.info(f"Confidence: {parsed_event.confidence_score}")
        
        # Convert to API response format
        response = {
            'title': title,
            'start_datetime': parsed_event.start_datetime.isoformat() if parsed_event.start_datetime else None,
            'end_datetime': parsed_event.end_datetime.isoformat() if parsed_event.end_datetime else None,
            'location': parsed_event.location,
            'description': text,  # Always use original text to avoid hallucination
            'all_day': parsed_event.all_day,
            'confidence_score': parsed_event.confidence_score,
            'parsing_path': parsed_event.extraction_metadata.get('parsing_path', 'unknown'),
            'warnings': parsed_event.extraction_metadata.get('warnings', [])
        }
        
        logger.info(f"Parsed result: confidence={response['confidence_score']:.2f}, path={response['parsing_path']}")
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Parsing error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'hybrid_parser_available': True,
        'timestamp': datetime.now().isoformat()
    })

if __name__ == '__main__':
    print("🚀 Starting Calendar Event Parser API Server")
    print("📡 Browser extension can connect to: http://localhost:5000")
    print("🧠 Using hybrid regex/LLM parsing system")
    
    app.run(host='localhost', port=5000, debug=True)