"""
FastAPI backend for text-to-calendar event parsing.
Provides stateless API endpoints for mobile apps and browser extensions.
"""

import os
import sys
from datetime import datetime
from typing import Optional
import logging

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

# Add parent directory to path to import existing services
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from services.event_parser import EventParser
from models.event_models import ParsedEvent

# Configure logging (no request body logging for privacy)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Disable request body logging for privacy
class NoBodyLoggingFilter(logging.Filter):
    def filter(self, record):
        # Filter out any log messages that might contain request bodies
        if hasattr(record, 'msg') and isinstance(record.msg, str):
            if 'body' in record.msg.lower() or 'text' in record.msg.lower():
                return False
        return True

logging.getLogger("uvicorn.access").addFilter(NoBodyLoggingFilter())

app = FastAPI(
    title="Text-to-Calendar Event Parser API",
    description="Stateless API for parsing natural language text into calendar events",
    version="1.0.0"
)

# CORS middleware for browser extensions and mobile apps
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your domains
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# Initialize event parser
event_parser = EventParser()


class ParseRequest(BaseModel):
    """Request model for text parsing."""
    text: str = Field(..., description="Natural language text to parse", min_length=1, max_length=10000)
    timezone: Optional[str] = Field(default="UTC", description="Timezone for date interpretation (e.g., 'America/New_York')")
    locale: Optional[str] = Field(default="en_US", description="Locale for date format preferences (e.g., 'en_US', 'en_GB')")
    now: Optional[datetime] = Field(default=None, description="Current datetime for relative date parsing (ISO 8601)")


class ParseResponse(BaseModel):
    """Response model for parsed event data."""
    title: Optional[str] = Field(description="Extracted event title")
    start_datetime: Optional[str] = Field(description="Start datetime in ISO 8601 format with timezone")
    end_datetime: Optional[str] = Field(description="End datetime in ISO 8601 format with timezone")
    location: Optional[str] = Field(description="Extracted location")
    description: Optional[str] = Field(description="Event description or original text")
    confidence_score: float = Field(description="Parsing confidence score (0.0 to 1.0)")
    all_day: bool = Field(default=False, description="Whether this is an all-day event")
    timezone: str = Field(description="Timezone used for parsing")


class HealthResponse(BaseModel):
    """Health check response model."""
    status: str
    timestamp: datetime
    version: str


@app.get("/healthz", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.utcnow(),
        version="1.0.0"
    )


@app.post("/parse", response_model=ParseResponse)
async def parse_text(request: ParseRequest, http_request: Request):
    """
    Parse natural language text into calendar event data.
    
    Returns structured event data with ISO 8601 datetimes including timezone offsets.
    Stateless operation - no data is stored.
    """
    try:
        # Log request metadata only (no body content for privacy)
        client_ip = http_request.client.host if http_request.client else "unknown"
        user_agent = http_request.headers.get("user-agent", "unknown")
        logger.info(f"Parse request from {client_ip}, User-Agent: {user_agent[:100]}")
        
        # Set current time for relative date parsing
        current_time = request.now or datetime.utcnow()
        
        # Configure parser based on locale
        prefer_dd_mm = request.locale.startswith('en_GB') or request.locale.startswith('en_AU')
        
        # Parse the text
        parsed_event = event_parser.parse_text(
            text=request.text,
            prefer_dd_mm_format=prefer_dd_mm,
            current_time=current_time
        )
        
        # Convert to response format with timezone-aware ISO 8601 strings
        response = ParseResponse(
            title=parsed_event.title,
            start_datetime=_format_datetime_with_tz(parsed_event.start_datetime, request.timezone),
            end_datetime=_format_datetime_with_tz(parsed_event.end_datetime, request.timezone),
            location=parsed_event.location,
            description=parsed_event.description or request.text,
            confidence_score=parsed_event.confidence_score,
            all_day=_is_all_day_event(parsed_event),
            timezone=request.timezone
        )
        
        # Log success (no sensitive data)
        logger.info(f"Parse successful, confidence: {parsed_event.confidence_score:.2f}")
        
        return response
        
    except Exception as e:
        logger.error(f"Parse error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to parse text: {str(e)}"
        )


def _format_datetime_with_tz(dt: Optional[datetime], timezone: str) -> Optional[str]:
    """Format datetime as ISO 8601 string with timezone offset."""
    if not dt:
        return None
    
    try:
        import pytz
        
        # If datetime is naive, assume it's in the requested timezone
        if dt.tzinfo is None:
            tz = pytz.timezone(timezone)
            dt = tz.localize(dt)
        
        # Return ISO 8601 format with timezone offset
        return dt.isoformat()
        
    except Exception:
        # Fallback: return as UTC if timezone handling fails
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=pytz.UTC)
        return dt.isoformat()


def _is_all_day_event(parsed_event: ParsedEvent) -> bool:
    """Determine if this should be treated as an all-day event."""
    if not parsed_event.start_datetime or not parsed_event.end_datetime:
        return False
    
    # Check if times are at midnight or if duration is 24+ hours
    start_time = parsed_event.start_datetime.time()
    end_time = parsed_event.end_datetime.time()
    duration = parsed_event.end_datetime - parsed_event.start_datetime
    
    # All-day if starts at midnight and is 24+ hours, or if no specific time was extracted
    return (
        (start_time.hour == 0 and start_time.minute == 0 and duration.days >= 1) or
        (parsed_event.confidence_score < 0.5 and 'all day' in (parsed_event.description or '').lower())
    )


# Custom middleware to prevent request body logging
@app.middleware("http")
async def privacy_middleware(request: Request, call_next):
    """Middleware to ensure request bodies are not logged."""
    # Process request without logging body
    response = await call_next(request)
    return response


if __name__ == "__main__":
    # Development server
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )