"""
Enhanced data models for the API with comprehensive error handling.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict
from enum import Enum


class ErrorCode(str, Enum):
    """Standard error codes for API responses."""
    VALIDATION_ERROR = "VALIDATION_ERROR"
    PARSING_ERROR = "PARSING_ERROR"
    INTERNAL_ERROR = "INTERNAL_ERROR"
    RATE_LIMIT_ERROR = "RATE_LIMIT_ERROR"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
    INVALID_TIMEZONE = "INVALID_TIMEZONE"
    TEXT_TOO_LONG = "TEXT_TOO_LONG"
    TEXT_EMPTY = "TEXT_EMPTY"
    LLM_UNAVAILABLE = "LLM_UNAVAILABLE"
    TIMEOUT_ERROR = "TIMEOUT_ERROR"
    CONCURRENT_PROCESSING_ERROR = "CONCURRENT_PROCESSING_ERROR"
    ASYNC_PROCESSING_ERROR = "ASYNC_PROCESSING_ERROR"


class ErrorDetail(BaseModel):
    """Detailed error information."""
    model_config = ConfigDict(use_enum_values=True)
    
    code: ErrorCode
    message: str
    field: Optional[str] = None
    suggestion: Optional[str] = None


class APIError(BaseModel):
    """Standard API error response."""
    success: bool = False
    error: ErrorDetail
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    request_id: Optional[str] = None


class ParseRequest(BaseModel):
    """Request model for text parsing."""
    text: str = Field(
        ...,
        description="Natural language text to parse",
        min_length=1,
        max_length=10000,
        example="Meeting with John tomorrow at 2pm in Conference Room A"
    )
    clipboard_text: Optional[str] = Field(
        default=None,
        description="Optional clipboard content for smart merging",
        max_length=10000
    )
    client_tz: Optional[str] = Field(
        default=None,
        description="Client timezone (IANA format, e.g., 'America/New_York'). Takes precedence over timezone field.",
        example="America/New_York"
    )
    timezone: Optional[str] = Field(
        default="UTC",
        description="Timezone for date interpretation (e.g., 'America/New_York'). Deprecated in favor of client_tz.",
        example="America/New_York"
    )
    locale: Optional[str] = Field(
        default="en_US",
        description="Locale for date format preferences (e.g., 'en_US', 'en_GB')",
        example="en_US"
    )
    now: Optional[datetime] = Field(
        default=None,
        description="Current datetime for relative date parsing (ISO 8601)"
    )
    use_llm_enhancement: Optional[bool] = Field(
        default=True,
        description="Whether to use LLM enhancement for better parsing"
    )


class ParseResponse(BaseModel):
    """Response model for parsed event data."""
    success: bool = True
    title: Optional[str] = Field(
        description="Extracted event title",
        example="Meeting with John"
    )
    # Legacy fields (deprecated but maintained for backward compatibility)
    start_datetime: Optional[str] = Field(
        description="Start datetime in ISO 8601 format with timezone (deprecated, use start_local)",
        example="2024-01-16T14:00:00-05:00"
    )
    end_datetime: Optional[str] = Field(
        description="End datetime in ISO 8601 format with timezone (deprecated, use end_local)",
        example="2024-01-16T15:00:00-05:00"
    )
    # New timezone-aware fields
    start_local: Optional[str] = Field(
        default=None,
        description="Start datetime in client timezone (ISO 8601 with offset)",
        example="2024-01-16T14:00:00-05:00"
    )
    end_local: Optional[str] = Field(
        default=None,
        description="End datetime in client timezone (ISO 8601 with offset)",
        example="2024-01-16T15:00:00-05:00"
    )
    start_utc: Optional[str] = Field(
        default=None,
        description="Start datetime in UTC (ISO 8601 with Z suffix)",
        example="2024-01-16T19:00:00Z"
    )
    end_utc: Optional[str] = Field(
        default=None,
        description="End datetime in UTC (ISO 8601 with Z suffix)",
        example="2024-01-16T20:00:00Z"
    )
    location: Optional[str] = Field(
        description="Extracted location",
        example="Conference Room A"
    )
    description: Optional[str] = Field(
        description="Event description or original text"
    )
    confidence_score: float = Field(
        description="Parsing confidence score (0.0 to 1.0)",
        ge=0.0,
        le=1.0,
        example=0.85
    )
    all_day: bool = Field(
        default=False,
        description="Whether this is an all-day event"
    )
    timezone: str = Field(
        description="Timezone used for parsing",
        example="America/New_York"
    )
    client_tz: Optional[str] = Field(
        default=None,
        description="Client timezone (same as timezone, for clarity)",
        example="America/New_York"
    )
    parsing_metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional parsing information for debugging"
    )
    warnings: Optional[List[str]] = Field(
        default=None,
        description="Non-critical parsing warnings"
    )


class HealthResponse(BaseModel):
    """Health check response model."""
    status: str = Field(description="Service status", example="healthy")
    timestamp: str = Field(description="Check timestamp in ISO format")
    version: str = Field(description="API version", example="1.0.0")
    services: Dict[str, str] = Field(
        description="Status of dependent services",
        example={"llm": "available", "parser": "healthy"}
    )
    uptime_seconds: Optional[float] = Field(
        description="Service uptime in seconds"
    )


class ICSRequest(BaseModel):
    """Request model for ICS file generation."""
    title: Optional[str] = Field(
        default=None, 
        description="Event title",
        example="Team Meeting"
    )
    start: Optional[str] = Field(
        default=None, 
        description="Start datetime in ISO format",
        example="2024-01-16T14:00:00-05:00"
    )
    end: Optional[str] = Field(
        default=None, 
        description="End datetime in ISO format",
        example="2024-01-16T15:00:00-05:00"
    )
    location: Optional[str] = Field(
        default=None, 
        description="Event location",
        example="Conference Room A"
    )
    description: Optional[str] = Field(
        default=None, 
        description="Event description"
    )
    allday: Optional[bool] = Field(
        default=False, 
        description="All-day event flag"
    )


class RateLimitInfo(BaseModel):
    """Rate limiting information."""
    limit: int = Field(description="Request limit per window")
    remaining: int = Field(description="Remaining requests in current window")
    reset_time: str = Field(description="When the rate limit resets (ISO format)")
    retry_after: Optional[int] = Field(description="Seconds to wait before retrying")