# Enhanced API Documentation

## Overview

The Enhanced Text-to-Calendar Event API provides comprehensive parsing capabilities with audit mode, partial parsing, caching, and performance monitoring. This documentation covers the enhanced endpoints and features.

## Base URL
```
https://your-api-domain.com/api/v1
```

## Authentication
Currently, the API does not require authentication. Future versions may include API key authentication.

## Enhanced Endpoints

### POST /parse

Parse text to extract calendar event information with enhanced features.

#### Request

**URL**: `/parse`
**Method**: `POST`
**Content-Type**: `application/json`

**Query Parameters**:
- `mode` (optional): Processing mode
  - `hybrid` (default): Full parsing with all layers
  - `audit`: Include detailed parsing decisions and confidence data
  - `regex_only`: Use only regex extraction
  - `llm_only`: Use only LLM processing
- `fields` (optional): Comma-separated list of fields to parse
  - Available fields: `start,end,title,location,description,participants,recurrence`
  - Example: `?fields=start,title` for partial parsing

**Request Body**:
```json
{
  "text": "Meeting with John tomorrow at 2pm in Conference Room A",
  "timezone": "America/New_York",
  "current_time": "2024-01-15T10:00:00Z"
}
```

#### Response

**Standard Response** (`mode=hybrid`):
```json
{
  "title": "Meeting with John",
  "start_datetime": "2024-01-16T14:00:00-05:00",
  "end_datetime": "2024-01-16T15:00:00-05:00",
  "location": "Conference Room A",
  "description": "Meeting with John tomorrow at 2pm in Conference Room A",
  "recurrence": null,
  "participants": ["John"],
  "all_day": false,
  "confidence_score": 0.85,
  "warnings": [],
  "needs_confirmation": false,
  "processing_time_ms": 245,
  "cache_hit": false
}
```

**Audit Response** (`mode=audit`):
```json
{
  "title": "Meeting with John",
  "start_datetime": "2024-01-16T14:00:00-05:00",
  "end_datetime": "2024-01-16T15:00:00-05:00",
  "location": "Conference Room A",
  "description": "Meeting with John tomorrow at 2pm in Conference Room A",
  "recurrence": null,
  "participants": ["John"],
  "all_day": false,
  "confidence_score": 0.85,
  "warnings": [],
  "needs_confirmation": false,
  "processing_time_ms": 245,
  "cache_hit": false,
  "audit_data": {
    "parsing_path": "regex_primary",
    "field_results": {
      "start_datetime": {
        "value": "2024-01-16T14:00:00-05:00",
        "source": "regex",
        "confidence": 0.9,
        "span": [25, 32],
        "alternatives": [],
        "processing_time_ms": 15
      },
      "title": {
        "value": "Meeting with John",
        "source": "llm",
        "confidence": 0.8,
        "span": [0, 17],
        "alternatives": ["John Meeting"],
        "processing_time_ms": 180
      }
    },
    "field_routing_decisions": {
      "start_datetime": "regex_only",
      "end_datetime": "regex_only",
      "title": "llm_enhancement",
      "location": "regex_only"
    },
    "confidence_breakdown": {
      "start_datetime": 0.9,
      "end_datetime": 0.9,
      "title": 0.8,
      "location": 0.85
    },
    "processing_times": {
      "regex": 45,
      "deterministic_backup": 0,
      "llm": 180,
      "validation": 20
    },
    "fallback_triggers": [],
    "cache_status": "miss"
  }
}
```

**Partial Parsing Response** (`fields=start,title`):
```json
{
  "start_datetime": "2024-01-16T14:00:00-05:00",
  "title": "Meeting with John",
  "confidence_score": 0.85,
  "processing_time_ms": 120,
  "cache_hit": false,
  "partial_parse": true,
  "requested_fields": ["start", "title"]
}
```

#### Error Responses

**400 Bad Request**:
```json
{
  "error": "Invalid request",
  "message": "Text field is required",
  "code": "MISSING_TEXT"
}
```

**422 Unprocessable Entity**:
```json
{
  "error": "Processing failed",
  "message": "No event information could be extracted from the provided text",
  "code": "NO_EVENT_DATA",
  "suggestions": [
    "Ensure text contains date/time information",
    "Check for typos in date/time formats",
    "Try including more context around the event"
  ]
}
```

**500 Internal Server Error**:
```json
{
  "error": "Internal server error",
  "message": "LLM processing timeout",
  "code": "LLM_TIMEOUT",
  "partial_results": {
    "start_datetime": "2024-01-16T14:00:00-05:00",
    "confidence_score": 0.6
  }
}
```

### GET /healthz

Health check endpoint with component status and performance metrics.

#### Request

**URL**: `/healthz`
**Method**: `GET`

#### Response

**200 OK** (Healthy):
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:00:00Z",
  "version": "1.0.0",
  "components": {
    "regex_parser": {
      "status": "healthy",
      "last_check": "2024-01-15T09:59:55Z",
      "response_time_ms": 5
    },
    "duckling": {
      "status": "healthy",
      "last_check": "2024-01-15T09:59:55Z",
      "response_time_ms": 45
    },
    "recognizers": {
      "status": "healthy",
      "last_check": "2024-01-15T09:59:55Z",
      "response_time_ms": 32
    },
    "llm_service": {
      "status": "healthy",
      "last_check": "2024-01-15T09:59:55Z",
      "response_time_ms": 1200
    },
    "cache": {
      "status": "healthy",
      "last_check": "2024-01-15T09:59:55Z",
      "hit_rate": 0.65,
      "size": 1024
    }
  },
  "performance_metrics": {
    "avg_response_time_ms": 450,
    "p95_response_time_ms": 1200,
    "requests_per_minute": 25,
    "error_rate": 0.02
  }
}
```

**503 Service Unavailable** (Degraded):
```json
{
  "status": "degraded",
  "timestamp": "2024-01-15T10:00:00Z",
  "version": "1.0.0",
  "components": {
    "regex_parser": {
      "status": "healthy",
      "last_check": "2024-01-15T09:59:55Z",
      "response_time_ms": 5
    },
    "llm_service": {
      "status": "unhealthy",
      "last_check": "2024-01-15T09:59:55Z",
      "error": "Connection timeout",
      "response_time_ms": null
    }
  },
  "degraded_features": [
    "LLM enhancement unavailable",
    "Falling back to regex + deterministic parsing only"
  ]
}
```

### GET /cache/stats

Cache performance monitoring endpoint.

#### Request

**URL**: `/cache/stats`
**Method**: `GET`

#### Response

**200 OK**:
```json
{
  "cache_stats": {
    "total_entries": 1024,
    "hit_rate": 0.65,
    "miss_rate": 0.35,
    "total_hits": 6500,
    "total_misses": 3500,
    "avg_hit_time_ms": 2,
    "avg_miss_time_ms": 450,
    "memory_usage_mb": 128,
    "oldest_entry_age_hours": 18,
    "ttl_hours": 24
  },
  "performance_impact": {
    "time_saved_ms": 2925000,
    "requests_served_from_cache": 6500,
    "estimated_cost_savings": "$45.50"
  }
}
```

## Request/Response Headers

### Request Headers
- `Content-Type: application/json` (required for POST requests)
- `Accept: application/json` (optional, defaults to JSON)
- `X-Request-ID: <uuid>` (optional, for request tracking)

### Response Headers
- `Content-Type: application/json`
- `X-Request-ID: <uuid>` (if provided in request)
- `X-Processing-Time-Ms: <milliseconds>`
- `X-Cache-Status: hit|miss`
- `X-Rate-Limit-Remaining: <count>` (future feature)

## Rate Limiting

Currently, no rate limiting is implemented. Future versions will include:
- 100 requests per minute per IP
- 1000 requests per hour per IP
- Burst allowance of 10 requests

## Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `MISSING_TEXT` | 400 | Text field is required |
| `INVALID_TIMEZONE` | 400 | Invalid timezone format |
| `INVALID_FIELDS` | 400 | Invalid fields parameter |
| `NO_EVENT_DATA` | 422 | No event information found |
| `PARSING_FAILED` | 422 | Text parsing failed |
| `LLM_TIMEOUT` | 500 | LLM processing timeout |
| `CACHE_ERROR` | 500 | Cache system error |
| `INTERNAL_ERROR` | 500 | Unexpected server error |

## SDK Examples

### Python
```python
import requests

# Basic parsing
response = requests.post('https://api.example.com/parse', json={
    'text': 'Meeting tomorrow at 2pm',
    'timezone': 'America/New_York'
})
event = response.json()

# Audit mode
response = requests.post('https://api.example.com/parse?mode=audit', json={
    'text': 'Meeting tomorrow at 2pm',
    'timezone': 'America/New_York'
})
audit_data = response.json()['audit_data']

# Partial parsing
response = requests.post('https://api.example.com/parse?fields=start,title', json={
    'text': 'Meeting tomorrow at 2pm',
    'timezone': 'America/New_York'
})
partial_event = response.json()
```

### JavaScript
```javascript
// Basic parsing
const response = await fetch('https://api.example.com/parse', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    text: 'Meeting tomorrow at 2pm',
    timezone: 'America/New_York'
  })
});
const event = await response.json();

// Audit mode with error handling
try {
  const response = await fetch('https://api.example.com/parse?mode=audit', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      text: 'Meeting tomorrow at 2pm',
      timezone: 'America/New_York'
    })
  });
  
  if (!response.ok) {
    const error = await response.json();
    console.error('Parsing failed:', error.message);
    return;
  }
  
  const result = await response.json();
  console.log('Routing decisions:', result.audit_data.field_routing_decisions);
} catch (error) {
  console.error('Network error:', error);
}
```

### cURL
```bash
# Basic parsing
curl -X POST https://api.example.com/parse \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Meeting tomorrow at 2pm",
    "timezone": "America/New_York"
  }'

# Audit mode
curl -X POST "https://api.example.com/parse?mode=audit" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Meeting tomorrow at 2pm",
    "timezone": "America/New_York"
  }'

# Health check
curl https://api.example.com/healthz

# Cache stats
curl https://api.example.com/cache/stats
```

## Best Practices

1. **Always Include Timezone**: Provide user's timezone for accurate relative date parsing
2. **Use Audit Mode for Debugging**: Enable audit mode to understand parsing decisions
3. **Handle Partial Results**: Be prepared to handle timeout scenarios with partial results
4. **Cache Responses**: Implement client-side caching for identical requests
5. **Validate Required Fields**: Check for `needs_confirmation` flag before creating events
6. **Monitor Performance**: Use processing time headers to monitor API performance
7. **Handle Errors Gracefully**: Implement proper error handling for all error codes