# Calendar Event Creator - Architecture Documentation

## System Overview

The Calendar Event Creator is a hybrid parsing system that combines regex-based extraction with LLM enhancement to convert natural language text into structured calendar events.

## Architecture Diagram

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│ Browser         │    │ API Server       │    │ Parsing Engine  │
│ Extension       │───▶│ (Flask)          │───▶│ (Hybrid)        │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │                        │
                                ▼                        ▼
                       ┌──────────────────┐    ┌─────────────────┐
                       │ Google Calendar  │    │ LLM Service     │
                       │ Integration      │    │ (Ollama/OpenAI) │
                       └──────────────────┘    └─────────────────┘
```

## Core Components

### 1. Parsing Engine (Python Backend)

#### HybridEventParser
**File**: `services/hybrid_event_parser.py`
**Role**: Main orchestrator for the parsing pipeline
**Strategy**:
```python
if regex_confidence >= 0.8:
    use_llm_enhancement_mode()  # Polish regex results
else:
    use_llm_fallback_mode()     # Full LLM parsing (confidence ≤ 0.5)
```

#### RegexDateExtractor
**File**: `services/regex_date_extractor.py`
**Role**: High-confidence datetime extraction
**Patterns**:
- Explicit dates: `Oct 15, 2025`, `10/15/2025`
- Relative dates: `tomorrow`, `next Friday`
- Time ranges: `2–3pm`, `from 2pm to 4pm`
- Durations: `for 2 hours`, `30 minutes long`

#### TitleExtractor
**File**: `services/title_extractor.py`
**Role**: Multi-pattern title extraction
**Strategies**:
1. Explicit labels (`Title:`, `Subject:`)
2. Action patterns (`Meeting with`, `Lunch with`)
3. Event types (conferences, parties, medical)
4. Context clues (`Going to`, `Scheduled for`)
5. Sentence structure (first sentence, imperatives)
6. Fallback generation (meaningful words)

#### LLMEnhancer
**File**: `services/llm_enhancer.py`
**Role**: Controlled LLM enhancement and fallback
**Modes**:
- **Enhancement**: Polish regex results (temperature ≤ 0.1)
- **Fallback**: Full extraction when regex fails (temperature ≤ 0.2)
**Constraints**: Never modify datetime fields, prevent hallucination

### 2. API Server

#### Flask API Server
**File**: `api_server.py`
**Role**: HTTP interface for browser extension
**Endpoints**:
- `POST /parse`: Parse event text using hybrid system
- `GET /health`: Health check and system status
**Features**:
- CORS support for browser extension
- Comprehensive error handling
- Request/response logging
- Fallback mechanisms

### 3. Browser Extension

#### Background Script
**File**: `browser-extension/background.js`
**Role**: Context menu and API communication
**Features**:
- Context menu creation on text selection
- API calls to local parsing service
- Google Calendar URL generation
- Error handling with fallbacks

#### Popup Interface
**File**: `browser-extension/popup.js`
**Role**: Manual text entry and parsing
**Features**:
- Text input with parsing
- Real-time API communication
- Calendar integration buttons
- Loading states and error handling

#### Content Script
**File**: `browser-extension/content.js`
**Role**: Text selection and page interaction
**Features**:
- Text selection tracking
- Optional floating button
- Keyboard shortcuts

## Data Flow

### 1. Text Input
```
User selects text → Browser Extension → API Server
```

### 2. Parsing Pipeline
```
API Server → HybridEventParser → RegexDateExtractor
                                ↓
                              TitleExtractor
                                ↓
                    (if regex confidence ≥ 0.8)
                              LLMEnhancer (enhancement mode)
                                ↓
                            ParsedEvent
```

### 3. Alternative Flow (Low Confidence)
```
API Server → HybridEventParser → RegexDateExtractor (confidence < 0.8)
                                ↓
                              LLMEnhancer (fallback mode)
                                ↓
                            ParsedEvent (confidence ≤ 0.5)
```

### 4. Output
```
ParsedEvent → API Response → Browser Extension → Google Calendar
```

## Configuration

### Hybrid Parser Configuration
```python
config = {
    'regex_confidence_threshold': 0.8,
    'warning_confidence_threshold': 0.6,
    'default_mode': 'hybrid',
    'enable_telemetry': True,
    'max_processing_time': 30.0
}
```

### LLM Service Configuration
```python
llm_config = {
    'provider': 'auto',  # auto|ollama|openai|groq
    'model': 'llama3.2:3b',
    'temperature': 0.1,  # Low for consistency
    'max_tokens': 500
}
```

### Browser Extension Configuration
```javascript
const config = {
    API_BASE_URL: 'http://localhost:5000',
    USE_LOCAL_PARSING: true,
    FALLBACK_ENABLED: true
}
```

## Error Handling

### 1. Parsing Failures
- **Regex fails**: Automatic LLM fallback
- **LLM fails**: Simple heuristic parsing
- **Both fail**: Minimal event with original text

### 2. API Failures
- **Server down**: Browser extension uses simple parsing
- **Network issues**: Retry with exponential backoff
- **Timeout**: Fallback to local parsing

### 3. Browser Extension Failures
- **Permission denied**: Graceful degradation
- **Context invalidated**: Clear error messages
- **Tab access denied**: Skip auto-loading features

## Security Considerations

### 1. Data Privacy
- **No persistent storage**: Text processed in memory only
- **Local processing**: API server runs locally
- **No tracking**: No analytics or user data collection

### 2. Browser Security
- **Minimal permissions**: Only required permissions requested
- **Content Security**: No eval() or unsafe operations
- **CORS restrictions**: API server only accepts local requests

### 3. LLM Security
- **Temperature limits**: Prevent creative/unpredictable outputs
- **Schema validation**: Structured outputs only
- **Prompt injection protection**: Sanitized inputs

## Performance Characteristics

### 1. Parsing Speed
- **Regex extraction**: < 10ms (very fast)
- **LLM enhancement**: 500-2000ms (depends on model)
- **LLM fallback**: 1000-3000ms (full processing)
- **Target**: p50 ≤ 1.5s total processing time

### 2. Accuracy
- **High-confidence regex**: 95%+ accuracy
- **LLM enhancement**: 90%+ accuracy
- **LLM fallback**: 70%+ accuracy
- **Overall system**: 85%+ accuracy across all text types

### 3. Resource Usage
- **Memory**: ~100MB for base system + LLM model size
- **CPU**: Minimal for regex, moderate for LLM
- **Network**: Local API calls only (no external dependencies)

## Monitoring and Observability

### 1. Logging
- **API Server**: Request/response logging with confidence scores
- **Parsing Pipeline**: Detailed path and method logging
- **Browser Extension**: Console logging for debugging

### 2. Telemetry
- **Parsing paths**: Track regex vs LLM usage
- **Confidence scores**: Monitor parsing quality
- **Performance metrics**: Response times and success rates
- **Error tracking**: Categorized error types and frequencies

### 3. Health Checks
- **API Health**: `/health` endpoint with system status
- **Component Status**: Individual service availability
- **Performance Monitoring**: Response time tracking

## Deployment

### Development Environment
1. **Start API server**: `python api_server.py`
2. **Load browser extension**: Chrome Developer Mode
3. **Test with golden cases**: `python run_golden_tests.py`

### Production Considerations
- **API Server**: Use production WSGI server (Gunicorn, uWSGI)
- **Browser Extension**: Package for Chrome Web Store
- **Monitoring**: Add structured logging and metrics
- **Security**: Review CORS settings and input validation

## Future Architecture Improvements

### 1. Microservices
- Split parsing components into separate services
- Add service discovery and load balancing
- Implement circuit breakers for resilience

### 2. Caching
- Cache regex patterns and LLM responses
- Add intelligent caching based on text similarity
- Implement cache invalidation strategies

### 3. Scalability
- Add horizontal scaling for API server
- Implement request queuing for LLM processing
- Add rate limiting and resource management

This architecture provides a solid foundation for the Calendar Event Creator system with room for future enhancements and scaling.