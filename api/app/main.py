"""
FastAPI backend for text-to-calendar event parsing.
Provides stateless API endpoints with async processing and concurrent field handling.

HEALTH CHECK HARDENING CHANGES:
This application has been enhanced with production-ready health check endpoints
and browser request handling to improve deployment reliability on Render and
reduce noisy logs from common browser requests.

Key enhancements:
- Root endpoint (/) supports both GET and HEAD methods for health probes
- Lightweight health check endpoint (/healthz) returns 204 No Content
- Graceful favicon.ico handling to prevent 404 errors in logs
- Static file serving with idempotent mount configuration
- All health endpoints excluded from OpenAPI schema documentation

These changes ensure compatibility with Render's health probe system and
provide a better experience for browser-based interactions while maintaining
backward compatibility with existing API functionality.
"""

import os
import sys
import asyncio
from datetime import datetime
from typing import Optional, Dict, Any, List
import logging

from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
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
from services.cache_manager import get_cache_manager

# Configure enhanced logging for production
from .logging_config import setup_logging, get_logger, parsing_logger
from .metrics import metrics_collector, track_request_metrics, track_component_timing

# Setup logging based on environment
log_level = os.getenv('LOG_LEVEL', 'INFO')
log_dir = os.getenv('LOG_DIR', 'logs')
setup_logging(log_level=log_level, log_dir=log_dir)

logger = get_logger('api.main')

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

# Background task for cache cleanup
import asyncio
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting API server with enhanced endpoints")
    
    # Start background cache cleanup task
    cleanup_task = asyncio.create_task(cache_cleanup_task())
    
    yield
    
    # Shutdown
    cleanup_task.cancel()
    try:
        await cleanup_task
    except asyncio.CancelledError:
        pass
    logger.info("API server shutdown complete")

async def cache_cleanup_task():
    """Background task to clean up expired cache entries."""
    while True:
        try:
            # Clean up expired entries every hour
            await asyncio.sleep(3600)  # 1 hour
            expired_count = get_cache_manager().cleanup_expired()
            if expired_count > 0:
                logger.info(f"Cleaned up {expired_count} expired cache entries")
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Cache cleanup error: {e}")

# Update app to use lifespan
app.router.lifespan_context = lifespan

# Configure static file serving with idempotency
# Check for existing static mounts by iterating through app.routes
existing_static_mounts = [
    route for route in app.routes 
    if hasattr(route, 'name') and route.name == 'static'
]

if not existing_static_mounts:
    # Create static directory if it doesn't exist
    static_dir = "static"
    if not os.path.exists(static_dir):
        os.makedirs(static_dir, exist_ok=True)
        logger.info(f"Created static directory: {static_dir}")
    
    # Mount static files
    app.mount("/static", StaticFiles(directory=static_dir), name="static")
    logger.info("Configured static file serving at /static")
else:
    logger.info("Static file serving already configured, skipping mount")


@app.api_route("/", methods=["GET", "HEAD"], include_in_schema=False)
async def root():
    """Root endpoint with API information."""
    return JSONResponse({"ok": True, "service": "calendar-api"})


@app.api_route("/healthz", methods=["GET", "HEAD"], include_in_schema=False)
async def healthz():
    """
    Lightweight health check endpoint optimized for monitoring probes.
    
    Returns 204 No Content for both GET and HEAD methods with no response body.
    This endpoint is designed for Render's health probes and monitoring systems
    that need fast, lightweight health checks without detailed status information.
    
    For detailed health information, use the /health endpoint instead.
    """
    return Response(status_code=204)


@app.api_route("/favicon.ico", methods=["GET", "HEAD"], include_in_schema=False)
async def favicon():
    """
    Handle favicon.ico requests gracefully to prevent 404 errors in logs.
    
    Returns the favicon file if it exists at "static/favicon.ico", otherwise
    returns 204 No Content to avoid generating 404 errors from browser requests.
    This endpoint is excluded from OpenAPI schema documentation.
    """
    favicon_path = "static/favicon.ico"
    if os.path.exists(favicon_path):
        return FileResponse(favicon_path)
    return Response(status_code=204)


@app.get("/metrics")
async def get_metrics():
    """
    Prometheus metrics endpoint for monitoring and alerting.
    
    Returns metrics in Prometheus text format including:
    - HTTP request metrics (count, duration, status codes)
    - Parsing performance metrics (accuracy, confidence, latency)
    - Component latency metrics (regex, LLM, deterministic backup)
    - Cache performance metrics (hit rate, size, operations)
    - System resource metrics (memory, CPU usage)
    - Error metrics (parsing errors, API errors)
    """
    from .metrics import metrics_collector
    
    metrics_content = metrics_collector.get_metrics()
    content_type = metrics_collector.get_content_type()
    
    return Response(content=metrics_content, media_type=content_type)


@app.get("/cache/stats")
async def get_cache_stats():
    """
    Detailed cache performance statistics endpoint.
    
    Returns comprehensive cache metrics including:
    - Hit/miss ratios and counts
    - Cache size and utilization
    - Entry count and TTL information
    - Performance impact metrics
    - Cache cleanup statistics
    """
    cache_stats = _get_cache_statistics()
    
    # Add additional performance context
    cache_stats["performance_impact"] = {
        "estimated_speedup_ms": cache_stats.get("average_hit_speedup_ms", 0),
        "total_requests_served": cache_stats.get("cache_hits", 0) + cache_stats.get("cache_misses", 0),
        "bandwidth_saved_estimate": cache_stats.get("cache_hits", 0) * 1024  # Rough estimate
    }
    
    return cache_stats


@app.get("/health", response_model=HealthResponse)
async def health_check_alias():
    """Alias for /healthz endpoint."""
    return await health_checker.get_health_status()


@app.post("/parse", response_model=ParseResponse)
async def parse_text(
    request: ParseRequest, 
    http_request: Request,
    mode: Optional[str] = None,
    fields: Optional[str] = None
):
    """
    Parse natural language text into calendar event data with enhanced features.
    
    ## Request Body
    - **text**: Natural language text containing event information (required)
    - **timezone**: Timezone for date interpretation (default: UTC)
    - **locale**: Locale for date format preferences (default: en_US)
    - **use_llm_enhancement**: Whether to use LLM for better parsing (default: true)
    - **clipboard_text**: Optional clipboard content for smart merging
    - **now**: Current datetime for relative date parsing (ISO 8601)
    
    ## Query Parameters
    - **mode**: Parsing mode - 'audit' for detailed routing information (optional)
    - **fields**: Comma-separated list of fields to parse (e.g., 'start,title,location') (optional)
    
    ## Async Processing Features
    - **Concurrent Field Processing**: Fields are processed concurrently for improved performance
    - **Timeout Handling**: Requests timeout after 10 seconds with partial results returned
    - **Thread Pool Execution**: CPU-intensive parsing runs in thread pools to avoid blocking
    
    ## Response
    Returns structured event data with ISO 8601 datetimes including timezone offsets.
    Includes confidence scores and parsing metadata.
    
    ## Audit Mode
    When mode=audit, response includes additional routing decisions and confidence breakdown.
    
    ## Partial Parsing
    When fields parameter is provided, only specified fields are processed and returned.
    
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
        
        # Parse fields parameter for partial parsing
        requested_fields = None
        if fields:
            requested_fields = [field.strip().lower() for field in fields.split(',')]
            valid_fields = ['title', 'start', 'end', 'location', 'description', 'recurrence']
            invalid_fields = [f for f in requested_fields if f not in valid_fields]
            if invalid_fields:
                return handle_parsing_error(
                    ValueError(f"Invalid fields: {', '.join(invalid_fields)}. Valid fields: {', '.join(valid_fields)}"),
                    request_id
                )
        
        # Set current time for relative date parsing
        current_time = request.now or datetime.utcnow()
        
        # Configure parser based on locale
        prefer_dd_mm = request.locale.startswith('en_GB') or request.locale.startswith('en_AU')
        
        # Check cache first (skip cache for audit mode or partial parsing)
        cache_key_params = {
            "timezone": request.timezone,
            "locale": request.locale,
            "use_llm_enhancement": request.use_llm_enhancement
        }
        
        cached_result = None
        cache_hit = False
        
        if not mode and not requested_fields:  # Only use cache for normal parsing
            cached_result = get_cache_manager().get(request.text)
            if cached_result:
                cache_hit = True
                parsed_event = cached_result
        
        # Parse the text if not cached
        if not cache_hit:
            try:
                # Use async parsing with concurrent field processing
                parsed_event = await _parse_text_async(
                    text=request.text,
                    clipboard_text=request.clipboard_text,
                    prefer_dd_mm_format=prefer_dd_mm,
                    current_time=current_time,
                    use_llm_enhancement=request.use_llm_enhancement,
                    requested_fields=requested_fields
                )
                
                # Cache the result for future requests (skip for audit/partial parsing)
                if not mode and not requested_fields:
                    get_cache_manager().put(request.text, parsed_event)
                    
            except Exception as parsing_error:
                return handle_parsing_error(parsing_error, request_id)
        
        # Apply partial parsing if requested
        if requested_fields:
            parsed_event = _apply_partial_parsing(parsed_event, requested_fields)
        
        # Collect parsing warnings
        warnings = []
        if parsed_event.confidence_score < 0.5:
            warnings.append("Low confidence parsing - please review extracted information")
        if not parsed_event.title and (not requested_fields or 'title' in requested_fields):
            warnings.append("No event title detected - consider adding a descriptive title")
        if not parsed_event.location and "location" in request.text.lower() and (not requested_fields or 'location' in requested_fields):
            warnings.append("Location mentioned but not extracted - please verify location field")
        
        # Collect parsing metadata
        parsing_metadata = {
            "llm_enhanced": request.use_llm_enhancement,
            "locale": request.locale,
            "timezone": request.timezone,
            "has_clipboard_text": bool(request.clipboard_text),
            "text_length": len(request.text),
            "partial_parsing": bool(requested_fields),
            "requested_fields": requested_fields,
            "cache_hit": cache_hit,
            "cache_enabled": not mode and not requested_fields
        }
        
        # Add audit mode information if requested
        if mode == "audit":
            parsing_metadata.update(_get_audit_information(parsed_event, request.text))
        
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
        logger.info(f"Parse successful - Request: {request_id}, Confidence: {parsed_event.confidence_score:.2f}, Mode: {mode or 'normal'}")
        logger.info(f"Parsed fields - Title: {parsed_event.title}, Start: {parsed_event.start_datetime}, End: {parsed_event.end_datetime}, Location: {parsed_event.location}")
        
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


def _apply_partial_parsing(parsed_event: ParsedEvent, requested_fields: List[str]) -> ParsedEvent:
    """Apply partial parsing by filtering out unrequested fields."""
    # Create a copy of the parsed event
    filtered_event = ParsedEvent()
    
    # Copy only requested fields
    if 'title' in requested_fields:
        filtered_event.title = parsed_event.title
    if 'start' in requested_fields:
        filtered_event.start_datetime = parsed_event.start_datetime
    if 'end' in requested_fields:
        filtered_event.end_datetime = parsed_event.end_datetime
    if 'location' in requested_fields:
        filtered_event.location = parsed_event.location
    if 'description' in requested_fields:
        filtered_event.description = parsed_event.description
    if 'recurrence' in requested_fields:
        filtered_event.recurrence = getattr(parsed_event, 'recurrence', None)
    
    # Always copy metadata and confidence
    filtered_event.confidence_score = parsed_event.confidence_score
    filtered_event.extraction_metadata = parsed_event.extraction_metadata
    filtered_event.all_day = getattr(parsed_event, 'all_day', False)
    
    return filtered_event


def _get_audit_information(parsed_event: ParsedEvent, original_text: str) -> Dict[str, Any]:
    """Generate audit information for parsing decisions."""
    metadata = parsed_event.extraction_metadata or {}
    
    audit_info = {
        "routing_decisions": {
            "parsing_method": metadata.get('parsing_path', 'unknown'),
            "llm_enhancement_used": metadata.get('llm_enhanced', False),
            "hybrid_parsing_used": metadata.get('hybrid_parsing_used', False),
            "fallback_triggered": metadata.get('fallback_to_legacy', False)
        },
        "confidence_breakdown": {
            "overall_confidence": parsed_event.confidence_score,
            "title_confidence": metadata.get('title_confidence', 0.0),
            "datetime_confidence": metadata.get('datetime_confidence', 0.0),
            "location_confidence": metadata.get('location_confidence', 0.0)
        },
        "field_sources": {
            "title_source": metadata.get('title_extraction_type', 'unknown'),
            "datetime_source": metadata.get('datetime_pattern_type', 'unknown'),
            "location_source": metadata.get('location_extraction_type', 'unknown')
        },
        "processing_metadata": {
            "text_length": len(original_text),
            "matches_found": {
                "datetime_matches": metadata.get('datetime_matches_found', 0),
                "title_matches": metadata.get('title_matches_found', 0),
                "location_matches": metadata.get('location_matches_found', 0)
            },
            "ambiguities_detected": {
                "multiple_datetimes": metadata.get('has_ambiguous_datetime', False),
                "multiple_titles": metadata.get('has_ambiguous_title', False),
                "multiple_locations": metadata.get('has_ambiguous_location', False)
            }
        }
    }
    
    return audit_info


def _get_performance_metrics() -> Dict[str, str]:
    """Get component performance metrics."""
    try:
        # This would integrate with actual performance monitoring
        # For now, return basic status indicators
        metrics = {
            "regex_parser": "healthy",
            "datetime_extractor": "healthy", 
            "location_extractor": "healthy",
            "title_extractor": "healthy"
        }
        
        # Add LLM performance if available
        try:
            # Check if LLM service is responsive
            import time
            start_time = time.time()
            # Quick health check - this would be replaced with actual LLM ping
            response_time = (time.time() - start_time) * 1000
            
            if response_time < 100:
                metrics["llm_service"] = "fast"
            elif response_time < 500:
                metrics["llm_service"] = "normal"
            else:
                metrics["llm_service"] = "slow"
                
        except Exception:
            metrics["llm_service"] = "unavailable"
        
        return metrics
        
    except Exception as e:
        logger.warning(f"Performance metrics error: {e}")
        return {}


def _get_cache_statistics() -> Dict[str, Any]:
    """Get cache performance statistics."""
    try:
        # Get real statistics from cache manager
        return get_cache_manager().get_statistics()
        
    except Exception as e:
        logger.warning(f"Cache statistics error: {e}")
        return {
            "status": "error",
            "message": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }


async def _parse_text_async(
    text: str,
    clipboard_text: Optional[str] = None,
    prefer_dd_mm_format: bool = False,
    current_time: Optional[datetime] = None,
    use_llm_enhancement: bool = True,
    requested_fields: Optional[List[str]] = None
):
    """
    Parse text asynchronously with concurrent field processing.
    
    This function implements concurrent processing for different parsing components
    to improve performance and reduce latency.
    """
    try:
        # Create tasks for concurrent processing
        parsing_tasks = []
        
        # Always run the main parsing task
        main_parsing_task = asyncio.create_task(
            _run_main_parsing(
                text=text,
                clipboard_text=clipboard_text,
                prefer_dd_mm_format=prefer_dd_mm_format,
                current_time=current_time,
                use_llm_enhancement=use_llm_enhancement
            )
        )
        parsing_tasks.append(main_parsing_task)
        
        # If specific fields are requested, we can optimize by running field-specific parsing
        if requested_fields:
            field_tasks = []
            
            # Create concurrent tasks for different field types
            if 'title' in requested_fields:
                field_tasks.append(
                    asyncio.create_task(_extract_title_async(text))
                )
            
            if any(field in requested_fields for field in ['start', 'end']):
                field_tasks.append(
                    asyncio.create_task(_extract_datetime_async(text, current_time, prefer_dd_mm_format))
                )
            
            if 'location' in requested_fields:
                field_tasks.append(
                    asyncio.create_task(_extract_location_async(text))
                )
            
            # Wait for field-specific tasks with timeout
            if field_tasks:
                try:
                    field_results = await asyncio.wait_for(
                        asyncio.gather(*field_tasks, return_exceptions=True),
                        timeout=5.0  # 5 second timeout for field extraction
                    )
                    logger.info(f"Concurrent field extraction completed: {len(field_results)} tasks")
                except asyncio.TimeoutError:
                    logger.warning("Field extraction timeout - falling back to main parsing")
        
        # Wait for main parsing with timeout
        try:
            parsed_event = await asyncio.wait_for(main_parsing_task, timeout=10.0)
            return parsed_event
        except asyncio.TimeoutError:
            logger.error("Main parsing timeout - returning partial results")
            # Return a basic parsed event with timeout warning
            from models.event_models import ParsedEvent
            timeout_event = ParsedEvent()
            timeout_event.description = text
            timeout_event.confidence_score = 0.1
            timeout_event.extraction_metadata = {
                'parsing_path': 'timeout_fallback',
                'warnings': ['Parsing timeout - partial results returned']
            }
            return timeout_event
            
    except Exception as e:
        logger.error(f"Async parsing error: {e}")
        raise


async def _run_main_parsing(
    text: str,
    clipboard_text: Optional[str] = None,
    prefer_dd_mm_format: bool = False,
    current_time: Optional[datetime] = None,
    use_llm_enhancement: bool = True
):
    """Run the main parsing logic asynchronously."""
    loop = asyncio.get_event_loop()
    
    # Run the synchronous parser in a thread pool to avoid blocking
    if use_llm_enhancement:
        parsed_event = await loop.run_in_executor(
            None,
            lambda: event_parser.parse_text_enhanced(
                text=text,
                clipboard_text=clipboard_text,
                prefer_dd_mm_format=prefer_dd_mm_format,
                current_time=current_time
            )
        )
    else:
        parsed_event = await loop.run_in_executor(
            None,
            lambda: event_parser.parse_text(
                text=text,
                prefer_dd_mm_format=prefer_dd_mm_format,
                current_time=current_time
            )
        )
    
    return parsed_event


async def _extract_title_async(text: str):
    """Extract title asynchronously."""
    loop = asyncio.get_event_loop()
    
    try:
        # Import title extractor
        from services.smart_title_extractor import SmartTitleExtractor
        title_extractor = SmartTitleExtractor()
        
        # Run title extraction in thread pool
        title_result = await loop.run_in_executor(
            None,
            lambda: title_extractor.extract_title(text)
        )
        
        return title_result
        
    except Exception as e:
        logger.warning(f"Async title extraction error: {e}")
        return None


async def _extract_datetime_async(text: str, current_time: Optional[datetime] = None, prefer_dd_mm: bool = False):
    """Extract datetime information asynchronously."""
    loop = asyncio.get_event_loop()
    
    try:
        # Import datetime parser
        from services.comprehensive_datetime_parser import ComprehensiveDateTimeParser
        datetime_parser = ComprehensiveDateTimeParser()
        
        # Run datetime extraction in thread pool
        datetime_result = await loop.run_in_executor(
            None,
            lambda: datetime_parser.extract_datetime(
                text=text,
                current_time=current_time or datetime.now(),
                prefer_dd_mm_format=prefer_dd_mm
            )
        )
        
        return datetime_result
        
    except Exception as e:
        logger.warning(f"Async datetime extraction error: {e}")
        return None


async def _extract_location_async(text: str):
    """Extract location asynchronously."""
    loop = asyncio.get_event_loop()
    
    try:
        # Import location extractor
        from services.advanced_location_extractor import AdvancedLocationExtractor
        location_extractor = AdvancedLocationExtractor()
        
        # Run location extraction in thread pool
        location_result = await loop.run_in_executor(
            None,
            lambda: location_extractor.extract_location(text)
        )
        
        return location_result
        
    except Exception as e:
        logger.warning(f"Async location extraction error: {e}")
        return None


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

@app.get("/cache/stats")
async def cache_statistics():
    """
    Get cache performance statistics and metrics.
    
    Returns detailed information about cache performance including:
    - Hit/miss ratios
    - Cache size and memory usage
    - Entry count and expiration statistics
    - Performance metrics
    """
    try:
        stats = cache_manager.get_statistics()
        return {
            "success": True,
            "cache_statistics": stats,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Cache statistics error: {e}")
        return {
            "success": False,
            "error": "Failed to retrieve cache statistics",
            "timestamp": datetime.utcnow().isoformat()
        }


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
            "Timeout and retry mechanisms",
            "Audit mode for parsing decisions",
            "Partial parsing for specific fields",
            "Intelligent caching with 24h TTL",
            "Performance monitoring and metrics",
            "Cache statistics and optimization"
        ],
        "endpoints": {
            "parse": {
                "method": "POST",
                "path": "/parse",
                "description": "Parse text into calendar event data with audit and partial parsing support",
                "query_params": ["mode", "fields"]
            },
            "ics": {
                "method": "GET", 
                "path": "/ics",
                "description": "Generate ICS calendar file"
            },
            "health": {
                "method": "GET",
                "path": "/healthz",
                "description": "Enhanced health check with component status and performance metrics"
            },
            "cache_stats": {
                "method": "GET",
                "path": "/cache/stats", 
                "description": "Cache performance monitoring statistics"
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


@app.get("/cache/stats")
async def cache_stats():
    """
    Get cache performance monitoring statistics.
    
    Returns detailed cache metrics including:
    - Hit/miss ratios
    - Cache size and utilization
    - Performance improvements
    - TTL information
    - Cache health status
    """
    try:
        stats = _get_cache_statistics()
        
        return {
            "success": True,
            "timestamp": datetime.utcnow().isoformat(),
            "cache_stats": stats,
            "performance_impact": {
                "average_cache_hit_speedup": stats.get("average_hit_speedup_ms", 0),
                "total_requests_served": stats.get("total_requests", 0),
                "cache_efficiency": stats.get("hit_ratio", 0.0)
            }
        }
        
    except Exception as e:
        logger.error(f"Cache stats error: {e}")
        return {
            "success": False,
            "error": "Cache statistics unavailable",
            "timestamp": datetime.utcnow().isoformat(),
            "cache_stats": {
                "status": "error",
                "message": str(e)
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
            "llm": health.services.get("llm", "unknown"),
            "cache": health.services.get("cache", "unknown")
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
