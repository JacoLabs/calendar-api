"""
Enhanced middleware for rate limiting, error handling, and security.
"""

import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, Optional
import logging
from collections import defaultdict, deque

from fastapi import Request, Response, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from .models import APIError, ErrorDetail, ErrorCode, RateLimitInfo

logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple in-memory rate limiting middleware."""
    
    def __init__(self, app, calls_per_minute: int = 60, calls_per_hour: int = 1000):
        super().__init__(app)
        self.calls_per_minute = calls_per_minute
        self.calls_per_hour = calls_per_hour
        self.minute_buckets: Dict[str, deque] = defaultdict(deque)
        self.hour_buckets: Dict[str, deque] = defaultdict(deque)
    
    async def dispatch(self, request: Request, call_next):
        # Get client identifier (IP address)
        client_ip = self._get_client_ip(request)
        current_time = time.time()
        
        # Clean old entries and check limits
        if self._is_rate_limited(client_ip, current_time):
            return self._create_rate_limit_response(client_ip, current_time)
        
        # Record this request
        self.minute_buckets[client_ip].append(current_time)
        self.hour_buckets[client_ip].append(current_time)
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers
        self._add_rate_limit_headers(response, client_ip, current_time)
        
        return response
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address."""
        # Check for forwarded headers (for reverse proxies)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        # Fallback to direct connection
        if request.client:
            return request.client.host
        
        return "unknown"
    
    def _is_rate_limited(self, client_ip: str, current_time: float) -> bool:
        """Check if client is rate limited."""
        minute_cutoff = current_time - 60
        hour_cutoff = current_time - 3600
        
        # Clean old entries
        minute_bucket = self.minute_buckets[client_ip]
        while minute_bucket and minute_bucket[0] < minute_cutoff:
            minute_bucket.popleft()
        
        hour_bucket = self.hour_buckets[client_ip]
        while hour_bucket and hour_bucket[0] < hour_cutoff:
            hour_bucket.popleft()
        
        # Check limits
        return (len(minute_bucket) >= self.calls_per_minute or 
                len(hour_bucket) >= self.calls_per_hour)
    
    def _create_rate_limit_response(self, client_ip: str, current_time: float) -> JSONResponse:
        """Create rate limit exceeded response."""
        minute_remaining = max(0, self.calls_per_minute - len(self.minute_buckets[client_ip]))
        hour_remaining = max(0, self.calls_per_hour - len(self.hour_buckets[client_ip]))
        
        # Calculate retry after (next minute boundary)
        retry_after = 60 - (current_time % 60)
        
        error = APIError(
            error=ErrorDetail(
                code=ErrorCode.RATE_LIMIT_ERROR,
                message="Rate limit exceeded. Please try again later.",
                suggestion=f"Wait {int(retry_after)} seconds before retrying"
            ),
            request_id=str(uuid.uuid4())
        )
        
        return JSONResponse(
            status_code=429,
            content=error.dict(),
            headers={
                "X-RateLimit-Limit-Minute": str(self.calls_per_minute),
                "X-RateLimit-Limit-Hour": str(self.calls_per_hour),
                "X-RateLimit-Remaining-Minute": str(minute_remaining),
                "X-RateLimit-Remaining-Hour": str(hour_remaining),
                "Retry-After": str(int(retry_after))
            }
        )
    
    def _add_rate_limit_headers(self, response: Response, client_ip: str, current_time: float):
        """Add rate limit headers to successful responses."""
        minute_remaining = max(0, self.calls_per_minute - len(self.minute_buckets[client_ip]))
        hour_remaining = max(0, self.calls_per_hour - len(self.hour_buckets[client_ip]))
        
        response.headers["X-RateLimit-Limit-Minute"] = str(self.calls_per_minute)
        response.headers["X-RateLimit-Limit-Hour"] = str(self.calls_per_hour)
        response.headers["X-RateLimit-Remaining-Minute"] = str(minute_remaining)
        response.headers["X-RateLimit-Remaining-Hour"] = str(hour_remaining)


class SecurityMiddleware(BaseHTTPMiddleware):
    """Basic security headers middleware."""
    
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # Don't cache sensitive endpoints
        if request.url.path in ["/parse", "/ics"]:
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        
        return response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Privacy-aware request logging middleware."""
    
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        request_id = str(uuid.uuid4())
        
        # Add request ID to request state
        request.state.request_id = request_id
        
        # Log request start (no sensitive data)
        client_ip = self._get_client_ip(request)
        user_agent = request.headers.get("user-agent", "unknown")[:100]
        
        logger.info(
            f"Request started - ID: {request_id}, "
            f"Method: {request.method}, "
            f"Path: {request.url.path}, "
            f"IP: {client_ip}, "
            f"User-Agent: {user_agent}"
        )
        
        try:
            response = await call_next(request)
            
            # Log successful completion
            duration = time.time() - start_time
            logger.info(
                f"Request completed - ID: {request_id}, "
                f"Status: {response.status_code}, "
                f"Duration: {duration:.3f}s"
            )
            
            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id
            
            return response
            
        except Exception as e:
            # Log error
            duration = time.time() - start_time
            logger.error(
                f"Request failed - ID: {request_id}, "
                f"Error: {str(e)}, "
                f"Duration: {duration:.3f}s"
            )
            raise
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address."""
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        if request.client:
            return request.client.host
        
        return "unknown"


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """Global error handling middleware."""
    
    async def dispatch(self, request: Request, call_next):
        try:
            return await call_next(request)
        except HTTPException:
            # Let FastAPI handle HTTP exceptions
            raise
        except Exception as e:
            # Handle unexpected errors
            request_id = getattr(request.state, 'request_id', str(uuid.uuid4()))
            
            logger.error(f"Unhandled error in request {request_id}: {str(e)}", exc_info=True)
            
            error = APIError(
                error=ErrorDetail(
                    code=ErrorCode.INTERNAL_ERROR,
                    message="An internal server error occurred",
                    suggestion="Please try again later or contact support if the problem persists"
                ),
                request_id=request_id
            )
            
            return JSONResponse(
                status_code=500,
                content=error.model_dump()
            )