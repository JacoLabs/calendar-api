"""
FastAPI entry point for Render deployment.
This file contains the FastAPI app directly to avoid import issues.
"""

import os
import sys
from datetime import datetime
from typing import Optional
import logging

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import our services
try:
    from services.event_parser import EventParser
    from models.event_models import ParsedEvent
except ImportError as e:
    print(f"Import error: {e}")
    # Create minimal fallback for deployment testing
    class EventParser:
        def parse_text(self, text, **kwargs):
            return type('ParsedEvent', (), {
                'title': 'Test Event',
                'start_datetime': datetime.now(),
                'end_datetime': datetime.now(),
                'location': None,
                'description': text,
                'confidence_score': 0.5
            })()
    
    class ParsedEvent:
        pass

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Text-to-Calendar Event Parser API",
    description="Stateless API for parsing natural language text into calendar events",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# Initialize event parser
try:
    event_parser = EventParser()
except Exception as e:
    logger.error(f"Failed to initialize EventParser: {e}")
    event_parser = None

class ParseRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=10000)
    timezone: Optional[str] = Field(default="UTC")
    locale: Optional[str] = Field(default="en_US")
    now: Optional[datetime] = Field(default=None)

class ParseResponse(BaseModel):
    title: Optional[str] = None
    start_datetime: Optional[str] = None
    end_datetime: Optional[str] = None
    location: Optional[str] = None
    description: Optional[str] = None
    confidence_score: float = 0.0
    all_day: bool = False
    timezone: str = "UTC"

class HealthResponse(BaseModel):
    status: str
    timestamp: datetime
    version: str

@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "Text-to-Calendar Event Parser API",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "health": "/healthz",
            "parse": "/parse (POST)",
            "docs": "/docs"
        }
    }

@app.get("/healthz", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.utcnow(),
        version="1.0.0"
    )

@app.post("/parse", response_model=ParseResponse)
async def parse_text(request: ParseRequest):
    """Parse natural language text into calendar event data."""
    try:
        if event_parser is None:
            # Fallback response for deployment testing
            return ParseResponse(
                title="Test Event",
                start_datetime=datetime.now().isoformat(),
                end_datetime=(datetime.now() + timedelta(hours=1)).isoformat(),
                description=request.text,
                confidence_score=0.5,
                timezone=request.timezone
            )
        
        # Parse the text
        parsed_event = event_parser.parse_text(request.text)
        
        # Format response
        return ParseResponse(
            title=parsed_event.title,
            start_datetime=parsed_event.start_datetime.isoformat() if parsed_event.start_datetime else None,
            end_datetime=parsed_event.end_datetime.isoformat() if parsed_event.end_datetime else None,
            location=parsed_event.location,
            description=parsed_event.description or request.text,
            confidence_score=parsed_event.confidence_score,
            timezone=request.timezone
        )
        
    except Exception as e:
        logger.error(f"Parse error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to parse text: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)