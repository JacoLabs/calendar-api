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
from fastapi.responses import Response
from pydantic import BaseModel, Field
import pytz
import uvicorn
from urllib.parse import unquote

# Add parent directories to path to import existing services
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(os.path.dirname(current_dir))
sys.path.insert(0, parent_dir)

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
    clipboard_text: Optional[str] = Field(default=None, description="Optional clipboard content for smart merging", max_length=10000)
    timezone: Optional[str] = Field(default="UTC", description="Timezone for date interpretation (e.g., 'America/New_York')")
    locale: Optional[str] = Field(default="en_US", description="Locale for date format preferences (e.g., 'en_US', 'en_GB')")
    now: Optional[datetime] = Field(default=None, description="Current datetime for relative date parsing (ISO 8601)")
    use_llm_enhancement: Optional[bool] = Field(default=True, description="Whether to use LLM enhancement for better parsing")


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


class ICSRequest(BaseModel):
    """Request model for ICS file generation."""
    title: Optional[str] = Field(default=None, description="Event title")
    start: Optional[str] = Field(default=None, description="Start datetime in ISO format")
    end: Optional[str] = Field(default=None, description="End datetime in ISO format")
    location: Optional[str] = Field(default=None, description="Event location")
    description: Optional[str] = Field(default=None, description="Event description")
    allday: Optional[bool] = Field(default=False, description="All-day event flag")


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
            "docs": "/docs",
            "openapi": "/openapi.json"
        },
        "example_usage": {
            "parse": {
                "method": "POST",
                "url": "/parse",
                "body": {
                    "text": "Meeting with John tomorrow at 2pm",
                    "timezone": "America/New_York",
                    "locale": "en_US"
                }
            },
            "ics": {
                "method": "GET",
                "url": "/ics?title=Meeting&start=2024-01-16T14:00:00&end=2024-01-16T15:00:00"
            }
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
        
        # Parse the text with enhancement if requested
        if request.use_llm_enhancement:
            parsed_event = event_parser.parse_text_enhanced(
                text=request.text,
                clipboard_text=request.clipboard_text,
                prefer_dd_mm_format=prefer_dd_mm,
                current_time=current_time
            )
        else:
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
    # Use the all_day field from the parsed event if available
    if hasattr(parsed_event, 'all_day'):
        return parsed_event.all_day
    
    # Fallback to heuristic detection for older parsing results
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


@app.get("/ics")
async def generate_ics(
    title: Optional[str] = None,
    start: Optional[str] = None,
    end: Optional[str] = None,
    location: Optional[str] = None,
    description: Optional[str] = None,
    allday: Optional[bool] = False,
    http_request: Request = None
):
    """
    Generate an ICS (iCalendar) file for Apple Calendar and other calendar applications.
    
    Returns an ICS file that can be downloaded or opened directly in calendar applications.
    """
    try:
        # Log request metadata
        client_ip = http_request.client.host if http_request.client else "unknown"
        logger.info(f"ICS generation request from {client_ip}")
        
        # Generate ICS content
        ics_content = _generate_ics_content(
            title=title,
            start_datetime=start,
            end_datetime=end,
            location=location,
            description=description,
            all_day=allday
        )
        
        # Return ICS file with proper headers
        return Response(
            content=ics_content,
            media_type="text/calendar",
            headers={
                "Content-Disposition": f"attachment; filename=event.ics",
                "Cache-Control": "no-cache"
            }
        )
        
    except Exception as e:
        logger.error(f"ICS generation error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate ICS file: {str(e)}"
        )


def _generate_ics_content(
    title: Optional[str] = None,
    start_datetime: Optional[str] = None,
    end_datetime: Optional[str] = None,
    location: Optional[str] = None,
    description: Optional[str] = None,
    all_day: bool = False
) -> str:
    """Generate ICS file content."""
    import uuid
    
    # Generate unique ID
    uid = f"{uuid.uuid4()}@calendar-event-creator"
    now = datetime.utcnow()
    
    # Start building ICS content
    ics_lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Calendar Event Creator//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "BEGIN:VEVENT",
        f"UID:{uid}",
        f"DTSTAMP:{_format_datetime_for_ics(now)}"
    ]
    
    # Add title
    if title:
        ics_lines.append(f"SUMMARY:{_escape_ics_text(title)}")
    else:
        ics_lines.append("SUMMARY:Calendar Event")
    
    # Add dates
    if start_datetime:
        try:
            start_dt = datetime.fromisoformat(start_datetime.replace('Z', '+00:00'))
            
            if all_day:
                # All-day event
                ics_lines.append(f"DTSTART;VALUE=DATE:{_format_date_for_ics(start_dt)}")
                if end_datetime:
                    end_dt = datetime.fromisoformat(end_datetime.replace('Z', '+00:00'))
                else:
                    # Default to next day for all-day events
                    from datetime import timedelta
                    end_dt = start_dt + timedelta(days=1)
                ics_lines.append(f"DTEND;VALUE=DATE:{_format_date_for_ics(end_dt)}")
            else:
                # Timed event
                ics_lines.append(f"DTSTART:{_format_datetime_for_ics(start_dt)}")
                if end_datetime:
                    end_dt = datetime.fromisoformat(end_datetime.replace('Z', '+00:00'))
                else:
                    # Default to +1 hour
                    from datetime import timedelta
                    end_dt = start_dt + timedelta(hours=1)
                ics_lines.append(f"DTEND:{_format_datetime_for_ics(end_dt)}")
                
        except Exception as e:
            logger.warning(f"Date parsing error in ICS generation: {e}")
            # Add current time as fallback
            ics_lines.append(f"DTSTART:{_format_datetime_for_ics(now)}")
            from datetime import timedelta
            ics_lines.append(f"DTEND:{_format_datetime_for_ics(now + timedelta(hours=1))}")
    
    # Add location
    if location:
        ics_lines.append(f"LOCATION:{_escape_ics_text(location)}")
    
    # Add description
    if description:
        ics_lines.append(f"DESCRIPTION:{_escape_ics_text(description)}")
    
    # Add creation time
    ics_lines.append(f"CREATED:{_format_datetime_for_ics(now)}")
    ics_lines.append(f"LAST-MODIFIED:{_format_datetime_for_ics(now)}")
    
    # Close event and calendar
    ics_lines.extend([
        "END:VEVENT",
        "END:VCALENDAR"
    ])
    
    return "\r\n".join(ics_lines)


def _format_date_for_ics(dt: datetime) -> str:
    """Format date for ICS (YYYYMMDD)."""
    return dt.strftime("%Y%m%d")


def _format_datetime_for_ics(dt: datetime) -> str:
    """Format datetime for ICS (YYYYMMDDTHHMMSSZ)."""
    # Convert to UTC if not already
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=pytz.UTC)
    elif dt.tzinfo != pytz.UTC:
        dt = dt.astimezone(pytz.UTC)
    
    return dt.strftime("%Y%m%dT%H%M%SZ")


def _escape_ics_text(text: str) -> str:
    """Escape text for ICS format."""
    if not text:
        return ""
    
    return (text
            .replace("\\", "\\\\")
            .replace(";", "\\;")
            .replace(",", "\\,")
            .replace("\n", "\\n")
            .replace("\r", ""))


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