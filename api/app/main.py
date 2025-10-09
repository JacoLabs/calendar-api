"""
FastAPI backend for text-to-calendar event parsing.
Provides stateless API endpoints for mobile apps and browser extensions.
"""

import os
import sys
from datetime import datetime
from typing import Optional
import logging

from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from fastapi.exceptions import RequestValidationError
import pytz
import uvicorn
from urllib.parse import unquote

# Add parent directories to path to import existing services
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(os.path.dirname(current_dir))
sys.path.insert(0, parent_dir)

from services.event_parser import EventParser
from models.event_models import ParsedEvent

# Import enhanced components
from .models import (
    ParseRequest, ParseResponse, HealthResponse, ICSRequest, 
    APIError, ErrorDetail, ErrorCode
)
from .middleware import (
    RateLimitMiddleware, SecurityMiddleware, 
    RequestLoggingMiddleware, ErrorHandlingMiddleware
)
from .error_handlers import (
    validation_exception_handler, http_exception_handler, 
    handle_parsing_error, validate_timezone, validate_datetime_string
)
from .health import health_checker

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

# Create FastAPI app with enhanced configuration
app = FastAPI(
    title="Text-to-Calendar Event Parser API",
    description="""
    Stateless API for parsing natural language text into calendar events.
    
    ## Features
    - Natural language parsing with LLM enhancement
    - Support for multiple date/time formats
    - Location and title extraction
    - Confidence scoring
    - Rate limiting and error handling
    - ICS file generation
    - Per-field confidence routing with strict guardrails
    
    ## Rate Limits
    - 60 requests per minute per IP
    - 1000 requests per hour per IP
    
    ## Error Handling
    All errors return a consistent format with error codes and suggestions.
    
    ## Version 2.0 Updates
    - Enhanced LLM service with strict guardrails
    - Per-field confidence routing
    - Improved parsing accuracy
    - Better error handling and validation
    """,
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Enhanced CORS middleware with specific origins for production
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "*",  # Allow all origins for development
        # In production, replace with specific domains:
        # "https://yourdomain.com",
        # "https://api.yourdomain.com",
        # "chrome-extension://*",  # For browser extensions
        # "moz-extension://*",     # For Firefox extensions
    ],
    allow_credentials=False,  # Set to False for public API
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=[
        "Accept",
        "Accept-Language", 
        "Content-Language",
        "Content-Type",
        "Authorization",
        "X-Requested-With",
        "User-Agent"
    ],
    expose_headers=[
        "X-Request-ID",
        "X-RateLimit-Limit-Minute",
        "X-RateLimit-Limit-Hour", 
        "X-RateLimit-Remaining-Minute",
        "X-RateLimit-Remaining-Hour",
        "Retry-After"
    ]
)

# Add enhanced middleware
app.add_middleware(ErrorHandlingMiddleware)
app.add_middleware(SecurityMiddleware)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(RateLimitMiddleware, calls_per_minute=60, calls_per_hour=1000)

# Add exception handlers
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(HTTPException, http_exception_handler)

# Initialize event parser
event_parser = EventParser()


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "Text-to-Calendar Event Parser API",
        "version": "2.0.0",
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
    """
    Comprehensive health check endpoint.
    
    Returns detailed status of the API and its dependencies including:
    - Overall service status
    - Parser service status  
    - LLM service availability
    - System resource usage
    - Service uptime
    """
    return await health_checker.get_health_status()


@app.get("/health", response_model=HealthResponse)
async def health_check_alias():
    """Alias for /healthz endpoint."""
    return await health_checker.get_health_status()


@app.post("/parse", response_model=ParseResponse)
async def parse_text(request: ParseRequest, http_request: Request):
    """
    Parse natural language text into calendar event data.
    
    ## Request Body
    - **text**: Natural language text containing event information (required)
    - **timezone**: Timezone for date interpretation (default: UTC)
    - **locale**: Locale for date format preferences (default: en_US)
    - **use_llm_enhancement**: Whether to use LLM for better parsing (default: true)
    - **clipboard_text**: Optional clipboard content for smart merging
    - **now**: Current datetime for relative date parsing (ISO 8601)
    
    ## Response
    Returns structured event data with ISO 8601 datetimes including timezone offsets.
    Includes confidence scores and parsing metadata.
    
    ## Error Handling
    - Returns 400 for validation errors with specific field information
    - Returns 503 when LLM service is unavailable (falls back to regex parsing)
    - Returns 429 when rate limit is exceeded
    
    Stateless operation - no data is stored.
    """
    request_id = getattr(http_request.state, 'request_id', None)
    
    try:
        # Validate timezone
        if request.timezone and not validate_timezone(request.timezone):
            return handle_parsing_error(
                ValueError(f"Invalid timezone: {request.timezone}"),
                request_id
            )
        
        # Validate datetime if provided
        if request.now and not validate_datetime_string(request.now.isoformat()):
            return handle_parsing_error(
                ValueError("Invalid datetime format for 'now' field"),
                request_id
            )
        
        # Set current time for relative date parsing
        current_time = request.now or datetime.utcnow()
        
        # Configure parser based on locale
        prefer_dd_mm = request.locale.startswith('en_GB') or request.locale.startswith('en_AU')
        
        # Parse the text with enhancement if requested
        try:
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
        except Exception as parsing_error:
            return handle_parsing_error(parsing_error, request_id)
        
        # Collect parsing warnings
        warnings = []
        if parsed_event.confidence_score < 0.5:
            warnings.append("Low confidence parsing - please review extracted information")
        if not parsed_event.title:
            warnings.append("No event title detected - consider adding a descriptive title")
        if not parsed_event.location and "location" in request.text.lower():
            warnings.append("Location mentioned but not extracted - please verify location field")
        
        # Collect parsing metadata
        parsing_metadata = {
            "llm_enhanced": request.use_llm_enhancement,
            "locale": request.locale,
            "timezone": request.timezone,
            "has_clipboard_text": bool(request.clipboard_text),
            "text_length": len(request.text)
        }
        
        # Convert to response format with timezone-aware ISO 8601 strings
        response = ParseResponse(
            title=parsed_event.title,
            start_datetime=_format_datetime_with_tz(parsed_event.start_datetime, request.timezone),
            end_datetime=_format_datetime_with_tz(parsed_event.end_datetime, request.timezone),
            location=parsed_event.location,
            description=parsed_event.description or request.text,
            confidence_score=parsed_event.confidence_score,
            all_day=_is_all_day_event(parsed_event),
            timezone=request.timezone,
            parsing_metadata=parsing_metadata,
            warnings=warnings if warnings else None
        )
        
        # Log success (no sensitive data)
        logger.info(f"Parse successful - Request: {request_id}, Confidence: {parsed_event.confidence_score:.2f}")
        
        return response
        
    except Exception as e:
        logger.error(f"Unexpected parse error - Request: {request_id}, Error: {str(e)}")
        return handle_parsing_error(e, request_id)


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
    
    ## Query Parameters
    - **title**: Event title (optional, defaults to "Calendar Event")
    - **start**: Start datetime in ISO 8601 format (optional, defaults to current time)
    - **end**: End datetime in ISO 8601 format (optional, defaults to start + 1 hour)
    - **location**: Event location (optional)
    - **description**: Event description (optional)
    - **allday**: Whether this is an all-day event (optional, default: false)
    
    ## Response
    Returns an ICS file that can be downloaded or opened directly in calendar applications.
    Compatible with Apple Calendar, Google Calendar, Outlook, and other iCalendar-compliant apps.
    
    ## Error Handling
    - Returns 400 for invalid datetime formats
    - Returns 500 for ICS generation failures
    """
    request_id = getattr(http_request.state, 'request_id', None)
    
    try:
        # Validate datetime parameters
        if start and not validate_datetime_string(start):
            return handle_parsing_error(
                ValueError("Invalid start datetime format"),
                request_id
            )
        
        if end and not validate_datetime_string(end):
            return handle_parsing_error(
                ValueError("Invalid end datetime format"),
                request_id
            )
        
        # Generate ICS content
        ics_content = _generate_ics_content(
            title=title,
            start_datetime=start,
            end_datetime=end,
            location=location,
            description=description,
            all_day=allday
        )
        
        # Log success
        logger.info(f"ICS generated successfully - Request: {request_id}")
        
        # Return ICS file with proper headers
        return Response(
            content=ics_content,
            media_type="text/calendar",
            headers={
                "Content-Disposition": f"attachment; filename=event.ics",
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0"
            }
        )
        
    except Exception as e:
        logger.error(f"ICS generation error - Request: {request_id}, Error: {str(e)}")
        return handle_parsing_error(e, request_id)


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


# Additional API endpoints for monitoring and documentation

@app.get("/api/info")
async def api_info():
    """
    Get API information and usage statistics.
    
    Returns basic API information, version, and available endpoints.
    """
    return {
        "name": "Text-to-Calendar Event Parser API",
        "version": "2.0.0",
        "description": "Parse natural language text into structured calendar events with enhanced LLM guardrails",
        "features": [
            "Natural language parsing",
            "LLM enhancement with strict guardrails",
            "Per-field confidence routing",
            "Multiple date/time formats",
            "Location extraction",
            "Advanced confidence scoring",
            "ICS file generation",
            "Rate limiting",
            "Comprehensive error handling",
            "Schema constraint enforcement",
            "Timeout and retry mechanisms"
        ],
        "endpoints": {
            "parse": {
                "method": "POST",
                "path": "/parse",
                "description": "Parse text into calendar event data"
            },
            "ics": {
                "method": "GET", 
                "path": "/ics",
                "description": "Generate ICS calendar file"
            },
            "health": {
                "method": "GET",
                "path": "/healthz",
                "description": "Health check with service status"
            },
            "docs": {
                "method": "GET",
                "path": "/docs",
                "description": "Interactive API documentation"
            }
        },
        "rate_limits": {
            "per_minute": 60,
            "per_hour": 1000
        },
        "supported_formats": {
            "dates": ["MM/DD/YYYY", "DD/MM/YYYY", "Month DD, YYYY", "relative dates"],
            "times": ["12-hour", "24-hour", "relative times", "time ranges"],
            "locations": ["addresses", "venue names", "implicit locations"],
            "timezones": "All IANA timezone identifiers"
        }
    }


@app.get("/api/status")
async def api_status():
    """
    Get current API status and basic metrics.
    
    Returns simplified status information for monitoring systems.
    """
    health = await health_checker.get_health_status()
    
    return {
        "status": health.status,
        "timestamp": health.timestamp,
        "uptime_seconds": health.uptime_seconds,
        "services": {
            "parser": health.services.get("parser", "unknown"),
            "llm": health.services.get("llm", "unknown")
        }
    }


if __name__ == "__main__":
    # Development server
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )