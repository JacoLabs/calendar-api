# Design Document

## Overview

The text-to-calendar event feature will be implemented as a comprehensive multi-platform system that enables users to highlight text containing event information and automatically create calendar events. The system prioritizes title and date/time information as essential components while treating location and description as optional enhancements. The architecture emphasizes robust real-world text handling with intelligent fallback mechanisms, confidence scoring, and consistent results across Gmail highlights, plain text, and various formatting styles through multiple client interfaces (CLI, API, mobile apps, browser extension).

## Architecture

The system follows a multi-platform layered architecture with a central API service and multiple client interfaces:

```
┌─────────────────────────────────────────────────────────────────┐
│                    Client Interfaces                            │
│  Android App | iOS App | Browser Extension | CLI Interface     │
├─────────────────────────────────────────────────────────────────┤
│                     FastAPI Service                             │
│         (REST API + CORS + OpenAPI + Telemetry)                │
├─────────────────────────────────────────────────────────────────┤
│                  Master Event Parser (Task 26)                 │
│        Hybrid: Regex-first datetime; LLM polish/fallback       │
├─────────────────────────────────────────────────────────────────┤
│  Pre-clean → RegexDateExtractor → TitleExtractor → LLMEnhancer  │
│    → Confidence/Warnings → Response (parsing_path included)    │
├─────────────────────────────────────────────────────────────────┤
│              LLM Constraints & Telemetry                       │
│  Never invent datetime | Temp ≤0.2 | JSON schema | Metrics    │
├─────────────────────────────────────────────────────────────────┤
│    Mode Support | Golden Tests CI | Performance (p50 ≤1.5s)    │
│  hybrid|regex_only|llm_only | 5 test cases | Latency tracking  │
├─────────────────────────────────────────────────────────────────┤
│                   Data Models                                  │
│  ParsedEvent | DateTimeResult | LocationResult | TitleResult   │
└─────────────────────────────────────────────────────────────────┘
```

**Design Rationale (Hybrid Parsing Strategy - Requirement 9)**: The architecture implements a hybrid parsing approach where regex/dateutil.parser handles all datetime extraction as the primary method (confidence ≥ 0.8 when successful). Task 26 serves as the integration focal point with the processing flow: pre-clean → RegexDateExtractor → TitleExtractor → LLMEnhancer → confidence/warnings → response. LLM serves two distinct roles: (1) Enhancement - polishing titles and descriptions when regex successfully extracts datetime, and (2) Fallback - attempting full extraction only when regex fails (confidence ≤ 0.5, adds warning). **Critical constraints**: LLM must never invent or override datetime fields (temperature ≤0.2, JSON schema output), all datetime parsing is exclusively handled by regex/dateparser. The system includes comprehensive telemetry, golden test CI validation, and performance targets (p50 ≤1.5s).

## Components and Interfaces

### 1. Text Selection Handler
- **Purpose**: Manages text highlighting and context menu integration
- **Key Methods**:
  - `capture_selected_text()`: Gets highlighted text from clipboard or selection
  - `show_context_menu()`: Displays "Create Calendar Event" option
  - `handle_selection()`: Processes user's menu selection

### 2. Master Event Parser Service (Task 26 Integration Focal Point)
- **Purpose**: Orchestrates hybrid parsing with regex-first datetime extraction and LLM enhancement/fallback
- **Processing Flow**: pre-clean → RegexDateExtractor → TitleExtractor → LLMEnhancer → confidence/warnings → response
- **Key Methods**:
  - `parse_text(text: str, mode: str = "hybrid") -> ParsedEvent`: Main parsing orchestration with mode support (hybrid|regex_only|llm_only)
  - `regex_extract_datetime(text: str) -> DateTimeResult`: Primary regex-based datetime extraction (confidence ≥ 0.8)
  - `llm_enhance_fields(event: ParsedEvent) -> ParsedEvent`: LLM title/description polishing when regex succeeds
  - `llm_fallback_extract(text: str) -> ParsedEvent`: Full LLM extraction only when regex fails (confidence ≤ 0.5, add warning)
  - `validate_and_score(event: ParsedEvent) -> ParsedEvent`: Confidence scoring and warning generation
  - `collect_telemetry(input_text: str, result: ParsedEvent) -> TelemetryData`: Track parsing metrics and performance

**Hybrid Parsing Strategy (Requirement 9)**:

**Regex-First DateTime Extraction**:
- **Primary Method**: Regex patterns and dateutil.parser for reliable date/time extraction
- **High Confidence**: Regex success results in confidence ≥ 0.8 for datetime fields
- **Comprehensive Coverage**: Handle explicit dates/times, relative dates, typos, and format variations
- **Timezone Resolution**: Use user's timezone and current time for accurate relative date conversion

**LLM Enhancement for Title/Description**:
- **Secondary Role**: LLM polishes titles and enhances descriptions when regex succeeds
- **Fallback Role**: LLM attempts full extraction only when regex fails (confidence ≤ 0.5)
- **Quality Focus**: LLM improves title quality and generates meaningful descriptions
- **Structured Output**: Always return standardized format with confidence scoring

**Comprehensive Parsing Strategy**:

**Priority-Based Extraction**: The system prioritizes essential fields (title, date/time) for successful event creation while treating location and description as optional enhancements that won't prevent event creation if missing.

**Date/Time Parsing (Essential - High Priority)**:
- Explicit dates: Monday, Sep 29, 2025; 09/29/2025; September 29th
- Relative dates: tomorrow, this Monday, next week, in two weeks, the first day back after break
- Natural phrases: end of month, after the holidays
- Inline dates: Sep 29 (assume current year)
- Explicit times: 9:00 a.m., 21:00, noon, midnight
- Typo-tolerant parsing: 9a.m, 9am, 9:00 A M, 9 AM → normalized to 9:00 AM
- Relative times: after lunch (1:00 PM), before school (8:00 AM), end of day (5:00 PM)
- Time ranges: 9–10 a.m., from 3 p.m. to 5 p.m., 2:00-3:30
- Duration calculation: "for 2 hours", "30 minutes long"

**Location Parsing (Optional - Lower Priority)**:
- Explicit addresses: Nathan Phillips Square, 123 Main Street
- Implicit locations: at school, gym, the office, downtown
- Direction-based: meet at the front doors, by the entrance
- Venue keywords: Square, Park, Center, Hall, School, Building, Room
- Context clues: "venue:", "at", "in", "@" indicators
- **Graceful degradation**: Events created successfully without location information
- **Multiple location handling**: Prioritize most relevant location when multiple candidates exist

**Title Generation (Essential - High Priority)**:
- Formal event names: Indigenous Legacy Gathering
- Context-derived: Use who/what/where when no explicit title
- Avoid truncated sentences and incomplete phrases
- Prioritize descriptive over generic titles
- **Fallback strategy**: Generate meaningful titles from available context when explicit titles missing

**Multi-Format Text Handling**:
- Bullet points in emails with structured information extraction
- Full paragraphs with embedded event details
- **Multi-paragraph processing**: Treat entire highlighted text as single event context
- Multiple event detection in single text blocks
- **Consistency guarantee**: Same structured output regardless of input method (screenshot vs highlight vs plain text)
- Typo normalization across all text formats
- Case-insensitive processing with proper output capitalization

### 3. Multi-Platform Client Interfaces
- **Purpose**: Provides consistent event review and editing across different platforms
- **Platforms**:
  - **CLI Interface**: Console-based preview and editing for development/testing
  - **Android App**: Native Android UI with text selection integration and calendar creation
  - **iOS App**: Native iOS interface with Share Extension and EventKit integration
  - **Browser Extension**: Web-based popup with calendar service integration
- **Common Methods**:
  - `display_preview(event: ParsedEvent)`: Shows extracted information with confidence indicators
  - `validate_form() -> bool`: Ensures required fields are complete
  - `get_user_input() -> Event`: Returns finalized event data
  - `handle_confirmation()`: Processes user's create/cancel decision
  - `show_confidence_warnings()`: Displays low-confidence field warnings for user review

### 4. Calendar Integration Services
- **Purpose**: Manages calendar event creation across different platforms and services
- **Platform-Specific Implementations**:
  - **Android**: CalendarContract integration for native Android calendar
  - **iOS**: EventKit framework for native iOS calendar
  - **Browser**: URL generation for Google Calendar, Outlook web interfaces
  - **CLI**: File output and console confirmation for development
- **Key Methods**:
  - `create_event(event: Event) -> bool`: Creates calendar entry with platform-specific implementation
  - `validate_event(event: Event) -> ValidationResult`: Checks event validity before creation
  - `get_calendar_url(event: Event) -> str`: Generates calendar service URLs for web integration
  - `handle_creation_errors() -> ErrorResponse`: Provides user-friendly error messages and retry options

## Data Models

### ParsedEvent
```python
@dataclass
class ParsedEvent:
    title: Optional[str]
    start_datetime: Optional[datetime]
    end_datetime: Optional[datetime]
    location: Optional[str]
    description: str
    confidence_score: float
    field_confidence: Dict[str, float]  # Individual field confidence scores
    extraction_metadata: Dict[str, Any]
    parsing_issues: List[str]  # Issues encountered during parsing
    suggestions: List[str]  # Suggestions for improvement
```

### DateTimeResult
```python
@dataclass
class DateTimeResult:
    start_datetime: Optional[datetime]
    end_datetime: Optional[datetime]
    confidence: float
    extraction_method: str  # "explicit", "relative", "inferred"
    ambiguities: List[str]  # Multiple possible interpretations
    raw_text: str  # Original text that was parsed
```

### LocationResult
```python
@dataclass
class LocationResult:
    location: Optional[str]
    confidence: float
    location_type: str  # "address", "venue", "implicit", "directional"
    alternatives: List[str]  # Other possible locations found
    raw_text: str
```

### TitleResult
```python
@dataclass
class TitleResult:
    title: Optional[str]
    confidence: float
    generation_method: str  # "explicit", "derived", "user_prompt_required"
    alternatives: List[str]
    raw_text: str
```

### Event
```python
@dataclass
class Event:
    title: str
    start_datetime: datetime
    end_datetime: datetime
    location: Optional[str]
    description: str
    calendar_id: str
    created_at: datetime
```

### ValidationResult
```python
@dataclass
class ValidationResult:
    is_valid: bool
    missing_fields: List[str]
    warnings: List[str]
    suggestions: List[str]
```

## Error Handling and Fallback Mechanisms

### Confidence-Based User Experience
- **High Confidence (≥0.8)**: Direct event creation with minimal confirmation when regex extraction succeeds
- **Medium Confidence (0.4-0.8)**: Show preview with editable fields and confidence indicators
- **Low Confidence (<0.4)**: Flag needs_confirmation and provide guided form with suggestions
- **Missing Critical Fields**: Highlight missing title/date/time and provide input prompts
- **Optional Field Handling**: Create events successfully even when location/description are missing

### Hybrid Strategy with Regex-First DateTime Extraction
- **Primary DateTime Extraction**: Regex patterns and dateutil.parser for reliable date/time parsing with confidence ≥ 0.8
- **LLM Title/Description Enhancement**: Use Ollama/Llama 3.2 to polish titles and generate descriptions when regex succeeds
- **LLM Fallback Processing**: Full LLM extraction only when regex fails, with confidence ≤ 0.5 and needs_confirmation flag
- **Component Fallback**: Specialized location and title extractors for additional field enhancement

### Multiple Interpretation Resolution
- **Multiple Dates/Times**: Default to first occurrence, offer alternatives in confirmation dialog
- **Multiple Locations**: Prioritize explicit addresses over implicit references, store alternatives
- **Multiple Events**: Detect and offer to create separate calendar events from single text
- **Ambiguous Content**: Present options with confidence scores for user selection

### Graceful Degradation Strategies
- **No Event Information**: Return clear "No event information found" message with specific reasons
- **Partial Information**: Create events with available essential data (title + date/time), prompt for missing optional fields
- **Format Recognition Failure**: Apply normalization and retry with different parsing strategies
- **API/LLM Unavailable**: Fall back to regex-only parsing with appropriate confidence adjustment

### Consistency and Quality Assurance
- **Input Method Consistency**: Same parsing pipeline and output format regardless of source (screenshot, highlight, plain text)
- **Normalized Output**: Always return standardized format (title, startDateTime, endDateTime, location, description, confidenceScore)
- **Quality Thresholds**: Validate extracted information meets minimum requirements before user presentation
- **Cross-Platform Consistency**: Identical parsing results across CLI, API, mobile apps, and browser extension

### Real-World Text Handling
- **Typo Tolerance**: Normalize 9a.m, 9am, 9:00 A M → 9:00 AM automatically
- **Format Flexibility**: Handle various date separators (/, -, .) and ordering preferences
- **Case Normalization**: Process text case-insensitively, output with proper capitalization
- **Whitespace Cleanup**: Trim and normalize spacing in all extracted fields
- **Metadata Filtering**: Ignore or downweight irrelevant information (Item ID, Status, Assignee) in emails

## Testing Strategy

### Unit Tests
- **Event Parser Service**: Test various text formats and edge cases
- **DateTime Extraction**: Verify different date/time format handling
- **Location Parsing**: Test location identification accuracy
- **Data Models**: Validate serialization and validation logic

### Integration Tests
- **End-to-End Flow**: Test complete text-to-event creation process
- **Calendar Integration**: Verify event creation in actual calendar system
- **UI Interaction**: Test form validation and user input handling

### Test Data Sets
- **Common Formats**: "Meeting tomorrow at 2pm in Conference Room A"
- **Complex Scenarios**: "Lunch with John next Friday from 12:30-1:30 at Cafe Downtown"
- **Edge Cases**: Ambiguous dates, missing information, multiple events
- **Error Conditions**: Invalid text, calendar access issues, malformed input

## Implementation Considerations

### Multi-Platform Architecture Strategy

**API-Centric Design**:
- **FastAPI Backend**: Central parsing service with REST endpoints and CORS support
- **Client Applications**: Android, iOS, Browser Extension, CLI all consume same API
- **Consistent Results**: Identical parsing logic ensures same output across all platforms
- **Scalability**: Centralized service allows easy updates and improvements

**Hybrid Parsing Strategy (Requirement 9)**:
- **Primary DateTime**: Regex patterns and dateutil.parser for reliable date/time extraction with high confidence
- **LLM Enhancement**: Ollama/Llama 3.2 for title polishing and description generation when regex succeeds
- **LLM Fallback**: Full LLM extraction only when regex fails, with confidence ≤ 0.5 and needs_confirmation flag
- **Component Fallback**: Specialized parsers for location extraction and title generation as needed

**LLM Integration Details (Enhancement Role)**:
- **Model Selection**: Llama 3.2 3B for local deployment, avoiding API costs and ensuring privacy
- **Critical Constraints**: Never invent/alter datetime fields, temperature ≤0.2, JSON schema output validation
- **Primary Use**: Title polishing and description generation when regex successfully extracts datetime
- **Fallback Use**: Full extraction attempts only when regex fails, with confidence ≤ 0.5 and warning flags
- **Structured Output**: Always return standardized format including parsing_path (regex_then_llm|llm_only|regex_only)
- **Telemetry Integration**: Track model usage, temperature, confidence scores, and parsing paths

**Advanced Confidence Scoring System**:
- **Field-Level Confidence**: Individual scores for title (essential), startDateTime (essential), endDateTime (essential), location (optional), description (optional)
- **Priority-Based Thresholds**: Lower confidence requirements for optional fields vs essential fields
- **Extraction Method Tracking**: Different confidence adjustments based on LLM vs regex vs component extraction
- **User Feedback Integration**: Confidence calibration based on user corrections and confirmations

### User Experience Enhancements

**Platform-Specific User Flows**:
- **Android**: Text selection → context menu → API call → native calendar creation
- **iOS**: Share extension → API call → EventKit calendar editor with pre-filled data
- **Browser**: Text selection → context menu → popup preview → calendar service URL generation
- **CLI**: Text input → parsing preview → interactive editing → confirmation

**Progressive Disclosure Based on Confidence**:
- **High Confidence (≥0.8)**: Streamlined creation with minimal user intervention
- **Medium Confidence (0.4-0.8)**: Preview interface with editable fields and confidence indicators
- **Low Confidence (<0.4)**: Guided form with field-specific suggestions and alternatives
- **Missing Essential Fields**: Mandatory completion prompts for title and date/time

**Intelligent User Feedback**:
- **Real-time Validation**: Immediate feedback on field completeness and format validity
- **Contextual Suggestions**: "Did you mean [alternative]?" for ambiguous dates, times, locations
- **Confidence Indicators**: Visual cues showing extraction quality for each field
- **Error Recovery**: Clear error messages with specific suggestions for improvement

### Performance and Scalability

**Optimization Strategies**:
- **Compiled regex patterns**: Pre-compile frequently used patterns
- **Caching layer**: Store parsing results for identical text
- **Async processing**: Non-blocking operations for API calls
- **Batch processing**: Handle multiple events efficiently

**Resource Management**:
- **Memory efficiency**: Stream processing for large text blocks
- **CPU optimization**: Prioritize fast patterns before complex analysis
- **Network efficiency**: Minimize API calls through intelligent caching

### Extensibility and Maintenance

**Modular Component Architecture**:
- **Specialized Parsers**: ComprehensiveDateTimeParser, AdvancedLocationExtractor, SmartTitleExtractor
- **Format Processors**: FormatAwareTextProcessor for bullet points, paragraphs, multi-paragraph text
- **Error Handlers**: ComprehensiveErrorHandler for fallback mechanisms and user guidance
- **Platform Adapters**: Separate calendar integration modules for Android, iOS, web services

**Configuration and Deployment**:
- **API Configuration**: FastAPI with CORS, health checks, and error handling
- **LLM Configuration**: Ollama setup with model management and fallback configuration
- **Client Configuration**: Platform-specific settings for calendar integration and user preferences
- **Deployment Strategy**: Render deployment for API, platform-specific app stores for mobile clients

**Quality Assurance and Testing**:
- **Golden Test CI**: 5 comprehensive test cases in CI pipeline, build fails on regressions
- **Performance Targets**: p50 latency ≤ 1.5s with continuous monitoring
- **Telemetry Tracking**: Input length, regex hits, detected range, parsing_path, model, temperature, confidence
- **Mode Isolation**: Support mode=hybrid|regex_only|llm_only for quick debugging and testing
- **OpenAPI Documentation**: Required fields documented with confidence thresholds (≥0.8 regex; ≤0.5 LLM-only; warn <0.6)
- **Cross-Platform Validation**: Consistent parsing results across all client interfaces