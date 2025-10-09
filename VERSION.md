# Version Information

## Current Version: 2.0.0
**Release Date**: October 8, 2025
**Codename**: "Guardrails & Precision"

### Development Status: 2.0.0 (Stable)
**Focus**: LLM guardrails and per-field confidence routing
**Target**: Production-ready API with enhanced parsing accuracy

## Version History

### v2.0.0 - "Guardrails & Precision" (2025-10-08)
**Major Features**:
- LLM service with strict guardrails and schema constraints
- Per-field confidence routing for enhanced accuracy
- Timeout and retry mechanisms for reliable LLM calls
- JSON schema validation for structured output compliance
- Context limiting to residual unparsed text only
- Enhanced field-level processing with locked field protection

**Key Components**:
- `LLMEnhancer`: Enhanced with guardrails methods
  - `enhance_low_confidence_fields()`: Targeted field enhancement
  - `enforce_schema_constraints()`: Prevent high-confidence field modification
  - `limit_context_to_residual()`: Reduce LLM context to unparsed text
  - `timeout_with_retry()`: 3-second timeout with single retry
  - `validate_json_schema()`: Structured output compliance
- `FieldResult`: Enhanced field tracking with provenance
- API V2: Production-ready with comprehensive error handling

**API Improvements**:
- Version 2.0.0 endpoints with enhanced features
- Better error handling and validation
- Improved deployment reliability (Render-compatible)
- Optional heavy dependencies for faster startup

### v1.2.0 - "Hybrid Intelligence" (2025-10-07)
**Major Features**:
- Hybrid regex-LLM parsing pipeline
- Browser extension integration with local API
- Advanced title extraction with multiple patterns
- Golden test suite with 100% pass rate

**Key Components**:
- `RegexDateExtractor`: High-confidence datetime extraction
- `TitleExtractor`: Multi-pattern title extraction
- `LLMEnhancer`: Controlled enhancement and fallback
- `HybridEventParser`: Confidence-based routing orchestration

**Browser Extension**:
- Local API server integration
- Improved error handling and fallbacks
- Fixed permission and loading issues

### v1.1.0 - "LLM Integration" (2025-10-06)
**Major Features**:
- LLM service integration (Ollama, OpenAI, Groq)
- Enhanced event parsing with AI assistance
- Multi-event text parsing
- Interactive ambiguity resolution

### v1.0.0 - "Foundation" (2025-10-05)
**Major Features**:
- Core datetime and event parsing
- Basic browser extension
- Google Calendar integration
- Foundational data models

## Component Versions

### Core Services
- `EventParser`: v1.2.0 (hybrid integration)
- `DateTimeParser`: v1.1.0 (stable)
- `EventInformationExtractor`: v1.1.0 (stable)
- `LLMService`: v1.1.0 (stable)

### Enhanced in v2.0.0
- `LLMEnhancer`: v2.0.0 (guardrails and precision)
- `FieldResult`: v2.0.0 (enhanced field tracking)
- `API`: v2.0.0 (production-ready)

### Stable from v1.2.0
- `RegexDateExtractor`: v1.0.0 (stable)
- `TitleExtractor`: v1.0.0 (stable)
- `HybridEventParser`: v1.0.0 (stable)

### Browser Extension
- Extension: v1.2.0 (local API integration)
- API Server: v1.0.0 (new)

## Compatibility

### Python Requirements
- Python 3.8+
- Flask 2.0+ (for API server)
- Requests 2.25+ (for LLM service)
- OpenAI 1.0+ (optional, for OpenAI integration)

### Browser Support
- Chrome 88+ (Manifest V3)
- Edge 88+ (Chromium-based)
- Firefox 109+ (limited support)

### API Compatibility
- Local API: `http://localhost:5000`
- Endpoints: `/parse`, `/health`
- Request format: JSON with `text`, `timezone`, `now` fields
- Response format: Structured event data with confidence scores

## Breaking Changes

### v2.0.0
- **API Version**: Updated to v2.0.0 (backward compatible endpoints)
- **LLMEnhancer**: New guardrails methods (existing methods still work)
- **Dependencies**: `recognizers-text` now optional (commented out in requirements.txt)
- **TextMergeHelper**: Lazy loading for LLM dependencies

### v1.2.0
- **Browser Extension**: Now requires local API server to be running
- **EventParser**: New `parse_event_text()` method (old methods still work)
- **Configuration**: New hybrid parsing configuration options

### v1.1.0
- **LLM Integration**: Requires additional dependencies for full functionality
- **Event Models**: Extended with confidence scoring and metadata

## Migration Guide

### From v1.2.0 to v2.0.0
1. **API Version**: Update API calls to use v2.0.0 endpoints (optional, v1 still works)
2. **Dependencies**: Remove `recognizers-text` if not needed (now optional)
3. **LLM Enhancements**: New guardrails methods available for advanced use cases
4. **Deployment**: Improved Render compatibility with lighter dependencies
5. **No breaking changes**: All existing functionality preserved

### From v1.1.0 to v1.2.0
1. **Install new dependencies**: No new Python packages required
2. **Update browser extension**: Reload extension in Chrome
3. **Start API server**: Run `python api_server.py` for browser extension
4. **Optional**: Use new `parse_event_text()` method for hybrid parsing

### From v1.0.0 to v1.1.0
1. **Install LLM dependencies**: `pip install openai requests`
2. **Configure LLM provider**: Set API keys or install Ollama
3. **Update extension**: Reload browser extension

## Roadmap

### v1.3.0 - "Smart Calendars" (Planned)
- Multiple calendar service integration (Outlook, Apple)
- Calendar conflict detection
- Smart scheduling suggestions
- Enhanced location parsing with maps integration

### v1.4.0 - "Learning System" (Planned)
- User correction learning
- Custom pattern definitions
- Personalized parsing preferences
- Usage analytics and optimization

### v2.1.0 - "Advanced Routing" (Planned)
- Enhanced per-field confidence routing
- Advanced LLM function calling
- Multi-provider LLM fallback chains
- Performance optimizations

### v3.0.0 - "Enterprise" (Planned)
- Multi-user support
- Team calendar integration
- Advanced security features
- Scalable deployment architecture

## Support

### Documentation
- `README.md`: User guide and installation
- `CHANGELOG.md`: Detailed change history
- `docs/DEVELOPMENT_LOG.md`: Technical development notes
- `browser-extension/TROUBLESHOOTING.md`: Extension debugging

### Testing
- `tests/test_hybrid_parsing_golden.py`: Golden test suite
- `run_golden_tests.py`: Test runner with detailed output
- `test_title_fix.py`: Title extraction testing
- `browser-extension/debug-extension.html`: Extension testing

### Contact
- Issues: GitHub Issues (when available)
- Development: See `docs/DEVELOPMENT_LOG.md` for technical details