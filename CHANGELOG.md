# Calendar Event Creator - Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed
- **Structured Text Parsing**: Added debugging for complex event text parsing
- **Title Extraction**: Improved handling of "Event Name DATE ... LOCATION ..." format

## [1.2.0] - 2025-10-07

### Added
- **Hybrid Regex-LLM Parsing Pipeline** (Task 26)
  - `RegexDateExtractor` for high-confidence datetime extraction (≥0.8 confidence)
  - `TitleExtractor` for intelligent title extraction with multiple fallback patterns
  - `LLMEnhancer` for polishing regex results and fallback parsing
  - `HybridEventParser` orchestrating confidence-based routing
  - Golden test suite with 5 comprehensive test cases (100% pass rate)

- **Browser Extension Integration**
  - API server (`api_server.py`) serving hybrid parsing system
  - Updated extension to call local API instead of external service
  - Fallback parsing when API unavailable
  - CORS support for browser extension communication

- **Advanced Title Extraction**
  - Explicit label patterns (`Title:`, `Subject:`, `Event Name:`)
  - Action-based patterns (`Meeting with`, `Lunch with`, `Call with`)
  - Event type patterns (conferences, parties, medical appointments)
  - Context clue patterns (`Going to`, `Scheduled for`, `Reminder about`)
  - Structured event text parsing (`Event Name DATE ... LOCATION ...`)

- **Comprehensive Testing**
  - Golden test cases covering various text formats
  - Performance benchmarks (p50 ≤ 3.0s)
  - Regression prevention tests
  - Debug tools and test helpers

### Changed
- **Parsing Strategy**: Switched from LLM-first to regex-first approach
  - Regex ≥ 0.8 confidence → LLM enhancement mode
  - Regex < 0.8 confidence → Full LLM parsing with confidence ≤ 0.5
- **Title Extraction**: Improved patterns to handle concatenated text formats
- **LLM Enhancement**: Restricted to prevent hallucination of descriptions
- **Browser Extension**: Now uses local API server instead of external service

### Fixed
- **Title Extraction Issues**
  - Fixed regex patterns to stop at field separators (`Due Date:`, `Location:`, etc.)
  - Added support for structured event text parsing
  - Prevented LLM from overriding high-confidence regex titles
- **Browser Extension Errors**
  - Fixed missing permissions (`notifications`, `tabs`)
  - Removed problematic icon references
  - Added graceful error handling and fallbacks
- **LLM Hallucination**
  - Disabled LLM description generation to prevent invented content
  - Added strict prompts to prevent datetime modification
  - Implemented confidence thresholds to control LLM usage

### Technical Details
- **Confidence Scoring**: Implemented field-level and overall confidence tracking
- **Parsing Metadata**: Added comprehensive logging of parsing paths and methods
- **Error Handling**: Improved fallback mechanisms and user feedback
- **Performance**: Optimized parsing pipeline for speed and accuracy

## [1.1.0] - 2025-10-06

### Added
- **Enhanced Event Parser**
  - Integrated `DateTimeParser` and `EventInformationExtractor`
  - Support for multiple event parsing from single text
  - Ambiguity detection and user clarification prompts
  - Comprehensive validation with `ValidationResult`

- **LLM Integration**
  - `LLMService` with Ollama, OpenAI, and Groq support
  - Structured JSON output with schema validation
  - Fallback heuristic parsing when LLM unavailable
  - Enhanced due date handling for task-like events

- **Browser Extension**
  - Context menu integration for selected text
  - Popup interface for manual text entry
  - Google Calendar integration with pre-filled events
  - Cross-browser compatibility (Chrome, Firefox, Edge)

### Changed
- **Architecture**: Modular service-based design
- **Parsing**: Multi-provider LLM support with automatic fallback
- **User Experience**: Interactive clarification for ambiguous text

### Fixed
- **Date Parsing**: Improved handling of various date formats
- **Time Extraction**: Better support for time ranges and durations
- **Error Handling**: Graceful degradation when services unavailable

## [1.0.0] - 2025-10-05

### Added
- **Core Event Parsing**
  - `DateTimeParser` for extracting dates and times from natural language
  - `EventInformationExtractor` for titles, locations, and descriptions
  - Support for absolute and relative date formats
  - Time range and duration extraction

- **Data Models**
  - `ParsedEvent` for parsing phase with confidence scoring
  - `Event` for finalized calendar events
  - `ValidationResult` for event validation feedback
  - `NormalizedEvent` for standardized output format

- **Basic Browser Extension**
  - Manifest V3 compliance
  - Context menu for selected text
  - Simple popup interface
  - Basic Google Calendar integration

### Technical Foundation
- **Python Backend**: Flask-based parsing service
- **Browser Extension**: Chrome extension with popup and context menu
- **Calendar Integration**: Google Calendar URL generation
- **Testing**: Basic unit tests for core functionality

---

## Version Numbering

- **Major** (X.0.0): Breaking changes, major feature additions
- **Minor** (1.X.0): New features, significant improvements
- **Patch** (1.1.X): Bug fixes, small improvements

## Development Phases

1. **v1.0.0**: Core functionality and basic browser extension
2. **v1.1.0**: LLM integration and enhanced parsing
3. **v1.2.0**: Hybrid regex-LLM pipeline (current)
4. **v1.3.0**: Planned - Advanced calendar integrations
5. **v2.0.0**: Planned - Major architecture improvements