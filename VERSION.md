# Version Information

## Current Version: 1.2.0
**Release Date**: October 7, 2025
**Codename**: "Hybrid Intelligence"

### Development Status: 1.2.1 (In Progress)
**Focus**: Structured text parsing improvements
**Target**: Bug fixes for complex event text extraction

## Version History

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

### New in v1.2.0
- `RegexDateExtractor`: v1.0.0 (new)
- `TitleExtractor`: v1.0.0 (new)
- `LLMEnhancer`: v1.0.0 (new)
- `HybridEventParser`: v1.0.0 (new)

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

### v1.2.0
- **Browser Extension**: Now requires local API server to be running
- **EventParser**: New `parse_event_text()` method (old methods still work)
- **Configuration**: New hybrid parsing configuration options

### v1.1.0
- **LLM Integration**: Requires additional dependencies for full functionality
- **Event Models**: Extended with confidence scoring and metadata

## Migration Guide

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

### v2.0.0 - "Enterprise" (Planned)
- Multi-user support
- Team calendar integration
- Advanced security features
- Production deployment tools

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