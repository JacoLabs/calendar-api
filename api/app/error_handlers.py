"""
Enhanced error handlers for the API.
"""

import logging
from typing import Union
from datetime import datetime

from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
import pytz

from .models import APIError, ErrorDetail, ErrorCode

logger = logging.getLogger(__name__)


def create_error_response(
    error_code: ErrorCode,
    message: str,
    status_code: int = 400,
    field: str = None,
    suggestion: str = None,
    request_id: str = None
) -> JSONResponse:
    """Create a standardized error response."""
    error = APIError(
        error=ErrorDetail(
            code=error_code,
            message=message,
            field=field,
            suggestion=suggestion
        ),
        request_id=request_id
    )
    
    return JSONResponse(
        status_code=status_code,
        content=error.model_dump()
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle Pydantic validation errors."""
    request_id = getattr(request.state, 'request_id', None)
    
    # Extract the first validation error for user-friendly message
    if exc.errors():
        first_error = exc.errors()[0]
        field = ".".join(str(loc) for loc in first_error["loc"])
        error_type = first_error["type"]
        
        # Create user-friendly messages based on error type
        if error_type == "missing":
            message = f"Required field '{field}' is missing"
            suggestion = f"Please provide a value for '{field}'"
        elif error_type == "string_too_short":
            message = f"Field '{field}' is too short"
            suggestion = "Please provide more text to parse"
        elif error_type == "string_too_long":
            message = f"Field '{field}' is too long"
            suggestion = f"Please limit '{field}' to the maximum allowed length"
        elif error_type == "value_error":
            message = f"Invalid value for field '{field}'"
            suggestion = "Please check the format and try again"
        else:
            message = f"Validation error in field '{field}': {first_error['msg']}"
            suggestion = "Please check your input and try again"
        
        logger.warning(f"Validation error in request {request_id}: {message}")
        
        return create_error_response(
            error_code=ErrorCode.VALIDATION_ERROR,
            message=message,
            status_code=422,
            field=field,
            suggestion=suggestion,
            request_id=request_id
        )
    
    # Fallback for unknown validation errors
    return create_error_response(
        error_code=ErrorCode.VALIDATION_ERROR,
        message="Invalid request data",
        status_code=422,
        suggestion="Please check your input format and try again",
        request_id=request_id
    )


async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions with consistent error format."""
    request_id = getattr(request.state, 'request_id', None)
    
    # Map HTTP status codes to error codes
    error_code_map = {
        400: ErrorCode.VALIDATION_ERROR,
        404: ErrorCode.VALIDATION_ERROR,
        429: ErrorCode.RATE_LIMIT_ERROR,
        500: ErrorCode.INTERNAL_ERROR,
        503: ErrorCode.SERVICE_UNAVAILABLE
    }
    
    error_code = error_code_map.get(exc.status_code, ErrorCode.INTERNAL_ERROR)
    
    # Enhance error messages with suggestions
    suggestions = {
        400: "Please check your request format and try again",
        404: "Please check the URL and try again",
        429: "Please wait before making another request",
        500: "Please try again later or contact support",
        503: "The service is temporarily unavailable, please try again later"
    }
    
    suggestion = suggestions.get(exc.status_code, "Please try again later")
    
    logger.warning(f"HTTP exception in request {request_id}: {exc.status_code} - {exc.detail}")
    
    return create_error_response(
        error_code=error_code,
        message=str(exc.detail),
        status_code=exc.status_code,
        suggestion=suggestion,
        request_id=request_id
    )


def handle_parsing_error(error: Exception, request_id: str = None) -> JSONResponse:
    """Handle parsing-specific errors with appropriate error codes."""
    error_message = str(error).lower()
    
    # Categorize parsing errors
    if "timezone" in error_message or "pytz" in error_message:
        return create_error_response(
            error_code=ErrorCode.INVALID_TIMEZONE,
            message="Invalid timezone specified",
            status_code=400,
            field="timezone",
            suggestion="Please use a valid timezone (e.g., 'America/New_York', 'UTC')",
            request_id=request_id
        )
    
    elif "text" in error_message and ("empty" in error_message or "short" in error_message):
        return create_error_response(
            error_code=ErrorCode.TEXT_EMPTY,
            message="Text is empty or too short to parse",
            status_code=400,
            field="text",
            suggestion="Please provide more descriptive text with event information",
            request_id=request_id
        )
    
    elif "timeout" in error_message or "asyncio.timeout" in error_message:
        return create_error_response(
            error_code=ErrorCode.TIMEOUT_ERROR,
            message="Request processing timeout",
            status_code=408,
            suggestion="The request took too long to process. Please try again with simpler text",
            request_id=request_id
        )
    
    elif "concurrent" in error_message or "asyncio" in error_message:
        return create_error_response(
            error_code=ErrorCode.CONCURRENT_PROCESSING_ERROR,
            message="Error in concurrent processing",
            status_code=500,
            suggestion="Please try again. If the problem persists, contact support",
            request_id=request_id
        )
    
    elif "llm" in error_message or "model" in error_message:
        return create_error_response(
            error_code=ErrorCode.LLM_UNAVAILABLE,
            message="LLM service is temporarily unavailable",
            status_code=503,
            suggestion="The request will be processed with fallback parsing. Try again later for enhanced results",
            request_id=request_id
        )
    
    else:
        # Generic parsing error
        return create_error_response(
            error_code=ErrorCode.PARSING_ERROR,
            message="Failed to parse the provided text",
            status_code=400,
            suggestion="Please try rephrasing the text with clearer date, time, and event information",
            request_id=request_id
        )


def validate_timezone(timezone_str: str) -> bool:
    """Validate timezone string."""
    try:
        pytz.timezone(timezone_str)
        return True
    except pytz.exceptions.UnknownTimeZoneError:
        return False


def validate_datetime_string(dt_str: str) -> bool:
    """Validate ISO datetime string."""
    try:
        datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
        return True
    except (ValueError, TypeError):
        return False