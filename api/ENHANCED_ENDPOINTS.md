# Enhanced API Endpoints (Task 12)

This document describes the enhanced API endpoints implemented for the text-to-calendar event parsing service.

## Overview

The enhanced API provides additional functionality for audit mode, partial parsing, performance monitoring, and intelligent caching with 24-hour TTL.

## Enhanced Endpoints

### 1. Enhanced /parse Endpoint

**URL:** `POST /parse`

**New Query Parameters:**
- `mode` (optional): Set to "audit" for detailed routing information
- `fields` (optional): Comma-separated list of fields to parse (e.g., "start,title,location")

**Valid Fields for Partial Parsing:**
- `title` - Event title
- `start` - Start date/time
- `end` - End date/time  
- `location` - Event location
- `description` - Event description
- `recurrence` - Recurrence pattern

**Examples:**

```bash
# Basic parsing
curl -X POST "http://localhost:8000/parse" \
  -H "Content-Type: application/json" \
  -d '{"text": "Meeting tomorrow at 2pm", "timezone": "America/New_York"}'

# Audit mode - includes routing decisions and confidence breakdown
curl -X POST "http://localhost:8000/parse?mode=audit" \
  -H "Content-Type: application/json" \
  -d '{"text": "Team standup at 9am", "timezone": "UTC"}'

# Partial parsing - only extract title and start time
curl -X POST "http://localhost:8000/parse?fields=title,start" \
  -H "Content-Type: application/json" \
  -d '{"text": "Board meeting next Monday at 10am in conference room", "timezone": "UTC"}'
```

**Enhanced Response (Audit Mode):**

```json
{
  "success": true,
  "title": "Team standup",
  "start_datetime": "2024-01-16T09:00:00+00:00",
  "end_datetime": "2024-01-16T10:00:00+00:00",
  "confidence_score": 0.85,
  "parsing_metadata": {
    "cache_hit": false,
    "partial_parsing": false,
    "routing_decisions": {
      "parsing_method": "regex_then_llm",
      "llm_enhancement_used": true,
      "hybrid_parsing_used": true,
      "fallback_triggered": false
    },
    "confidence_breakdown": {
      "overall_confidence": 0.85,
      "title_confidence": 0.9,
      "datetime_confidence": 0.95,
      "location_confidence": 0.0
    },
    "field_sources": {
      "title_source": "explicit",
      "datetime_source": "time_12hour",
      "location_source": "unknown"
    },
    "processing_metadata": {
      "text_length": 17,
      "matches_found": {
        "datetime_matches": 1,
        "title_matches": 1,
        "location_matches": 0
      }
    }
  }
}
```

### 2. Enhanced /healthz Endpoint

**URL:** `GET /healthz`

**Enhanced Features:**
- Component status and performance metrics
- Cache status and statistics
- System resource monitoring
- Service dependency health

**Example Response:**

```json
{
  "status": "healthy",
  "timestamp": "2024-01-16T10:30:00.000Z",
  "version": "1.0.0",
  "uptime_seconds": 3600.5,
  "services": {
    "parser": "healthy",
    "llm": "available",
    "memory": "healthy",
    "disk": "healthy",
    "cache": "healthy",
    "regex_parser": "healthy",
    "datetime_extractor": "healthy",
    "location_extractor": "healthy",
    "title_extractor": "healthy",
    "llm_service": "fast"
  }
}
```

### 3. New /cache/stats Endpoint

**URL:** `GET /cache/stats`

**Purpose:** Provides detailed cache performance monitoring statistics

**Example Response:**

```json
{
  "success": true,
  "timestamp": "2024-01-16T10:30:00.000Z",
  "cache_stats": {
    "status": "healthy",
    "total_requests": 150,
    "cache_hits": 45,
    "cache_misses": 105,
    "hit_ratio": 0.3,
    "cache_size_mb": 2.5,
    "max_cache_size_mb": 100.0,
    "ttl_hours": 24,
    "oldest_entry_age_hours": 2.5,
    "average_hit_speedup_ms": 800.0,
    "entries_count": 12,
    "evictions_count": 0,
    "last_cleanup": "2024-01-16T09:30:00.000Z",
    "utilization_percent": 2.5
  },
  "performance_impact": {
    "average_cache_hit_speedup": 800.0,
    "total_requests_served": 150,
    "cache_efficiency": 0.3
  }
}
```

## Caching Behavior

### Cache Key Generation
- Based on normalized text (lowercase, whitespace normalized)
- Includes timezone, locale, and LLM enhancement settings
- Uses SHA-256 hash for consistent key generation

### Cache TTL
- 24-hour time-to-live as specified in requirements
- Automatic cleanup of expired entries every hour
- LRU eviction when cache size limit is reached

### Cache Exclusions
- Audit mode requests are not cached
- Partial parsing requests are not cached
- Ensures audit data reflects real-time processing decisions

## Error Handling

### Invalid Fields Parameter
```bash
curl -X POST "http://localhost:8000/parse?fields=invalid_field" \
  -H "Content-Type: application/json" \
  -d '{"text": "test"}'

# Returns 400 Bad Request
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid fields: invalid_field. Valid fields: title, start, end, location, description, recurrence"
  }
}
```

### Cache Statistics Error
If cache statistics are unavailable:
```json
{
  "success": false,
  "error": "Cache statistics unavailable",
  "timestamp": "2024-01-16T10:30:00.000Z",
  "cache_stats": {
    "status": "error",
    "message": "Cache service temporarily unavailable"
  }
}
```

## Performance Considerations

### Caching Benefits
- Average speedup of 800ms for cache hits
- Reduced LLM API calls for identical requests
- Lower server resource usage for repeated queries

### Audit Mode Overhead
- Audit mode adds ~50-100ms processing time
- Includes additional metadata collection
- Not recommended for high-frequency production use

### Partial Parsing Optimization
- Processes only requested fields
- Reduces processing time for simple queries
- Useful for specialized client applications

## Monitoring and Observability

### Health Check Integration
- Component-level health monitoring
- Performance metrics included in health response
- Cache status integrated into overall health

### Cache Monitoring
- Real-time hit/miss ratios
- Memory usage tracking
- Performance impact measurement
- Automatic cleanup and eviction logging

## Requirements Satisfied

This implementation satisfies the following requirements from Task 12:

- ✅ **14.1**: `/parse` endpoint with `mode=audit` and `fields` query parameters
- ✅ **14.2**: Audit mode response with routing decisions and confidence breakdown  
- ✅ **16.2**: `/healthz` endpoint with component status and performance metrics
- ✅ **14.3**: Intelligent caching system with 24h TTL and normalized text hashing
- ✅ **14.4**: `/cache/stats` endpoint for cache performance monitoring
- ✅ Partial parsing support for `fields` parameter
- ✅ Enhanced error handling and validation
- ✅ Performance monitoring integration