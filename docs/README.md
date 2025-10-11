# Enhanced Text-to-Calendar Event System Documentation

## Overview

This documentation covers the enhanced text-to-calendar event parsing system with per-field confidence routing, deterministic backup integration, LLM processing with guardrails, and comprehensive performance optimization features.

## Documentation Structure

### Core System Documentation

#### [Per-Field Confidence Routing](per-field-confidence-routing.md)
Comprehensive guide to the per-field confidence routing system that optimizes parsing performance by analyzing each field independently and routing them to the most appropriate processing method.

**Key Topics:**
- Architecture and processing methods
- Field types and confidence scoring
- Processing decision flow
- Cross-field validation
- Performance optimization
- Configuration options

#### [API Documentation](api-documentation.md)
Complete API reference for the enhanced parsing endpoints with audit mode, partial parsing, caching, and performance monitoring capabilities.

**Key Topics:**
- Enhanced endpoints (`/parse`, `/healthz`, `/cache/stats`)
- Request/response formats
- Audit mode and partial parsing
- Error handling and status codes
- SDK examples (Python, JavaScript, cURL)
- Best practices

#### [Deterministic Backup Integration](deterministic-backup-integration.md)
Detailed guide for integrating and configuring the deterministic backup layer using Duckling and Microsoft Recognizers-Text.

**Key Topics:**
- Duckling integration and configuration
- Microsoft Recognizers-Text setup
- Backup coordination and span selection
- Performance optimization
- Health monitoring
- Troubleshooting

### Operational Documentation

#### [Troubleshooting Guide](troubleshooting-guide.md)
Comprehensive troubleshooting guide for diagnosing and resolving common issues with enhanced features.

**Key Topics:**
- Quick diagnostic checklist
- Per-field confidence routing issues
- Deterministic backup problems
- LLM processing issues
- Performance and cache problems
- Monitoring and alerting setup

#### [Performance Tuning Guide](performance-tuning-guide.md)
Complete guide for optimizing system performance including configuration tuning, resource optimization, and monitoring best practices.

**Key Topics:**
- Performance targets and metrics
- Configuration optimization
- Caching strategies
- Resource management
- Monitoring and profiling
- Best practices summary

## Quick Start Guide

### System Requirements

**Minimum Requirements:**
- Python 3.8+
- 4GB RAM
- 2 CPU cores
- Docker (for Duckling)

**Recommended Requirements:**
- Python 3.10+
- 8GB RAM
- 4 CPU cores
- Redis (for caching)
- Ollama (for LLM processing)

### Installation

1. **Install Core Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Set Up Duckling** (Docker):
   ```bash
   docker run -d -p 8000:8000 --name duckling facebook/duckling
   ```

3. **Install Microsoft Recognizers**:
   ```bash
   pip install recognizers-text recognizers-text-date-time
   ```

4. **Configure LLM Service** (Ollama):
   ```bash
   # Install Ollama
   curl -fsSL https://ollama.ai/install.sh | sh
   
   # Pull model
   ollama pull llama3.2:3b
   ```

### Basic Configuration

Create a `.env` file with basic configuration:

```bash
# API Configuration
API_HOST=0.0.0.0
API_PORT=8080

# Duckling Configuration
DUCKLING_URL=http://localhost:8000/parse
DUCKLING_TIMEOUT=2.0

# LLM Configuration
LLM_MODEL=llama3.2:3b
LLM_TIMEOUT=3.0
LLM_TEMPERATURE=0.0

# Cache Configuration
CACHE_TTL=3600
CACHE_MAX_SIZE=1000

# Performance Configuration
CONFIDENCE_THRESHOLD_REGEX=0.8
CONFIDENCE_THRESHOLD_DETERMINISTIC=0.6
ENABLE_PERFORMANCE_MONITORING=true
```

### Running the System

1. **Start the API Server**:
   ```bash
   python -m uvicorn api.main:app --host 0.0.0.0 --port 8080
   ```

2. **Test Basic Functionality**:
   ```bash
   curl -X POST http://localhost:8080/parse \
     -H "Content-Type: application/json" \
     -d '{
       "text": "Meeting tomorrow at 2pm in Conference Room A",
       "timezone": "America/New_York"
     }'
   ```

3. **Check System Health**:
   ```bash
   curl http://localhost:8080/healthz
   ```

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    Client Interfaces                            │
│  Android App | iOS App | Browser Extension | CLI Interface     │
├─────────────────────────────────────────────────────────────────┤
│                Enhanced FastAPI Service                         │
│  /parse | /healthz | /audit | Caching (24h TTL) | Async       │
├─────────────────────────────────────────────────────────────────┤
│              Per-Field Confidence Router                        │
│  Field Analysis → Confidence Scoring → Selective Enhancement   │
├─────────────────────────────────────────────────────────────────┤
│                 Parsing Pipeline Layers                         │
│  1. RegexDateExtractor (conf ≥0.8) → High confidence fields    │
│  2. Deterministic Backup (Duckling/Recognizers) → Med conf     │
│  3. LLMEnhancer (JSON schema, 3s timeout) → Low conf fields    │
├─────────────────────────────────────────────────────────────────┤
│              Enhanced Field Processing                          │
│  Recurrence (RRULE) | Duration | All-day | Timezone handling   │
├─────────────────────────────────────────────────────────────────┤
│           Performance & Monitoring Layer                        │
│  Component Latency | Golden Set Testing | Reliability Diagram  │
├─────────────────────────────────────────────────────────────────┤
│                Enhanced Data Models                             │
│  FieldResult{value,source,confidence,span} | CacheEntry | Audit │
└─────────────────────────────────────────────────────────────────┘
```

## Key Features

### Per-Field Confidence Routing
- **Intelligent Processing**: Routes each field to optimal processing method based on confidence
- **Cost Optimization**: Minimizes expensive LLM processing by using deterministic methods first
- **Provenance Tracking**: Maintains detailed information about how each field was processed

### Deterministic Backup Layer
- **Reliable Fallback**: Uses Duckling and Microsoft Recognizers before LLM processing
- **Span Optimization**: Selects best candidate based on precision and confidence
- **Timezone Handling**: Ensures proper timezone normalization for datetime results

### LLM Processing with Guardrails
- **Schema Enforcement**: Prevents LLM from modifying high-confidence fields
- **Context Limitation**: Reduces LLM context to only unparsed text
- **Timeout Management**: Returns partial results on timeout rather than failing

### Enhanced API Features
- **Audit Mode**: Exposes routing decisions and confidence breakdown
- **Partial Parsing**: Processes only specified fields for efficiency
- **Intelligent Caching**: 24-hour TTL with normalized text hashing
- **Performance Monitoring**: Component latency tracking and health checks

## Performance Targets

| Metric | Target | Monitoring |
|--------|--------|------------|
| API Response Time (p50) | ≤ 1.5s | `/performance/metrics` |
| API Response Time (p95) | ≤ 3.0s | Performance dashboard |
| Cache Hit Rate | ≥ 60% | `/cache/stats` |
| Error Rate | ≤ 2% | Health checks |
| Memory Usage | ≤ 512MB | System monitoring |

## Common Use Cases

### High-Performance Parsing
```python
# Use performance-optimized configuration
result = await parser.parse_event_text(
    text="Meeting tomorrow at 2pm",
    mode="hybrid",
    config="performance_optimized"
)
```

### Quality-First Parsing
```python
# Use quality-optimized configuration
result = await parser.parse_event_text(
    text="Meeting tomorrow at 2pm",
    mode="hybrid",
    config="quality_optimized"
)
```

### Debugging and Analysis
```python
# Use audit mode for detailed analysis
result = await parser.parse_event_text(
    text="Meeting tomorrow at 2pm",
    mode="audit"
)
print(result.audit_data.field_routing_decisions)
```

### Partial Field Processing
```python
# Process only specific fields
result = await parser.parse_event_text(
    text="Meeting tomorrow at 2pm",
    fields=["start_datetime", "title"]
)
```

## Monitoring and Alerting

### Key Metrics to Monitor
- **Response Time**: API latency percentiles
- **Error Rate**: Failed parsing attempts
- **Cache Performance**: Hit rate and memory usage
- **Component Health**: Duckling, Recognizers, LLM availability
- **Resource Usage**: Memory and CPU utilization

### Recommended Alerts
- Response time p95 > 3 seconds
- Error rate > 5%
- Cache hit rate < 40%
- Component unavailability > 1 minute
- Memory usage > 80%

## Support and Troubleshooting

### Getting Help
1. **Check Health Status**: Use `/healthz` endpoint
2. **Review Logs**: Enable debug logging for detailed information
3. **Use Audit Mode**: Analyze routing decisions and confidence scores
4. **Consult Documentation**: Refer to specific troubleshooting guides

### Common Issues
- **Slow Response Times**: Check LLM configuration and confidence thresholds
- **Low Cache Hit Rate**: Review text normalization and cache key generation
- **Parsing Errors**: Verify component health and configuration
- **Memory Issues**: Monitor resource usage and enable cleanup

### Debug Mode
```python
# Enable comprehensive debugging
import logging
logging.basicConfig(level=logging.DEBUG)

parser = HybridEventParser(debug_mode=True)
result = parser.parse_event_text(text, mode="audit")
```

## Contributing

### Development Setup
1. Clone repository and install dependencies
2. Set up development environment with all services
3. Run tests to verify setup
4. Follow coding standards and performance guidelines

### Testing
- **Unit Tests**: Test individual components
- **Integration Tests**: Test complete parsing pipeline
- **Performance Tests**: Verify latency and resource usage
- **Golden Set Tests**: Validate accuracy against curated test cases

### Documentation Updates
- Update relevant documentation for any changes
- Include performance impact analysis
- Add troubleshooting information for new features
- Update configuration examples

## License and Support

This documentation is part of the Enhanced Text-to-Calendar Event System. For technical support, please refer to the troubleshooting guides or contact the development team with detailed diagnostic information.