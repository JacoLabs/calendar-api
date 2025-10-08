# Design Document

## Overview

The text-to-calendar event feature will be implemented as a comprehensive multi-platform system that enables users to highlight text containing event information and automatically create calendar events. The system prioritizes title and date/time information as essential components while treating location and description as optional enhancements. The architecture emphasizes robust real-world text handling with intelligent fallback mechanisms, confidence scoring, and consistent results across Gmail highlights, plain text, and various formatting styles through multiple client interfaces (CLI, API, mobile apps, browser extension).

## Architecture

The system follows a multi-platform layered architecture with per-field confidence routing and deterministic backup layers:

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

**Design Rationale (Hybrid Parsing Strategy - Requirement 9)**: The architecture implements a hybrid parsing approach where regex/dateutil.parser handles all datetime extraction as the primary method (confidence ≥ 0.8 when successful). Task 26 serves as the integration focal point with the processing flow: pre-clean → RegexDateExtractor → TitleExtractor → LLMEnhancer → confidence/warnings → response. LLM serves two distinct roles: (1) Enhancement - polishing titles and descriptions when regex successfully extracts datetime, and (2) Fallback - attempting full extraction only when regex fails (confidence ≤ 0.5, adds warning). **Critical constraints**: LLM must never invent or override datetime fields (temperature ≤0.2, JSON schema output), all datetime parsing is exclusively handled by regex/dateparser. The system includes comprehensive telemetry, golden test CI validation, and performance targets (p50 ≤1.5s).

## Components and Interfaces

### 1. Per-Field Confidence Router
- **Purpose**: Analyzes text and routes fields to optimal processing methods based on confidence
- **Key Methods**:
  - `analyze_field_extractability(text: str) -> Dict[str, float]`: Assess per-field confidence potential
  - `route_processing_method(field: str, confidence: float) -> ProcessingMethod`: Choose regex/deterministic/LLM
  - `validate_field_consistency(results: Dict[str, FieldResult]) -> ValidationResult`: Cross-field validation
  - `optimize_processing_order(fields: List[str]) -> List[str]`: Order fields for efficient processing

### 2. Deterministic Backup Layer
- **Purpose**: Provides reliable fallback parsing before expensive LLM processing
- **Integration Options**:
  - **Duckling**: Facebook's rule-based parser for dates, times, numbers
  - **Microsoft Recognizers-Text**: Multi-language entity recognition
- **Key Methods**:
  - `extract_with_duckling(text: str, field: str) -> FieldResult`: Duckling-based extraction
  - `extract_with_recognizers(text: str, field: str) -> FieldResult`: Microsoft Recognizers extraction
  - `choose_best_span(candidates: List[FieldResult]) -> FieldResult`: Select shortest valid span
  - `validate_timezone_normalization(datetime_result: FieldResult) -> bool`: Ensure valid timezone handling

### 3. Enhanced LLM Processing with Guardrails
- **Purpose**: Provides LLM enhancement with strict constraints and timeouts
- **Key Methods**:
  - `enhance_low_confidence_fields(text: str, fields: List[str], locked_fields: Dict) -> Dict[str, FieldResult]`: Process only specified fields
  - `enforce_schema_constraints(llm_output: Dict, locked_fields: Dict) -> Dict`: Prevent modification of high-confidence fields
  - `limit_context_to_residual(text: str, extracted_spans: List[Tuple[int, int]]) -> str`: Reduce LLM context
  - `timeout_with_retry(prompt: str, timeout_seconds: int = 3) -> Optional[Dict]`: Handle timeouts and retries
  - `validate_json_schema(output: str) -> Dict`: Ensure structured output compliance

### 2. Enhanced Hybrid Event Parser Service
- **Purpose**: Orchestrates per-field confidence routing with deterministic backup layers
- **Processing Flow**: text → field analysis → confidence routing → selective enhancement → result aggregation
- **Key Methods**:
  - `parse_event_text(text: str, mode: str = "hybrid", fields: List[str] = None) -> ParsedEvent`: Main parsing with field filtering
  - `analyze_field_confidence(text: str, field: str) -> FieldConfidence`: Per-field confidence assessment
  - `route_field_processing(field: str, confidence: float) -> ProcessingMethod`: Determine optimal processing method
  - `extract_with_regex(text: str, field: str) -> FieldResult`: High-confidence regex extraction (≥0.8)
  - `extract_with_deterministic_backup(text: str, field: str) -> FieldResult`: Duckling/Recognizers fallback (0.6-0.8)
  - `enhance_with_llm(text: str, field: str, context: Dict) -> FieldResult`: LLM processing for low-confidence fields (<0.6)
  - `aggregate_field_results(results: Dict[str, FieldResult]) -> ParsedEvent`: Combine results with provenance
  - `validate_and_cache(text_hash: str, result: ParsedEvent) -> ParsedEvent`: Caching and validation

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

### 4. Enhanced Recurrence and Duration Processing
- **Purpose**: Handles complex recurrence patterns and duration calculations
- **Key Methods**:
  - `parse_recurrence_pattern(text: str) -> RecurrenceResult`: Convert natural language to RRULE
  - `handle_every_other_pattern(text: str) -> str`: "every other Tuesday" → FREQ=WEEKLY;INTERVAL=2;BYDAY=TU
  - `calculate_duration_end_time(start: datetime, duration_text: str) -> datetime`: "for 45 minutes" processing
  - `parse_until_time(text: str, start_date: date) -> datetime`: "until noon" → 12:00 PM same day
  - `detect_all_day_indicators(text: str) -> bool`: Identify all-day event markers
  - `validate_rrule_format(rrule: str) -> bool`: Ensure RFC 5545 compliance

### 5. Enhanced API Service Layer
- **Purpose**: Provides comprehensive API with audit, caching, and performance features
- **New Endpoints**:
  - `POST /parse?mode=audit&fields=start,title`: Enhanced parsing with audit data
  - `GET /healthz`: Health check with component status
  - `GET /cache/stats`: Cache performance metrics
- **Key Methods**:
  - `handle_audit_mode(request: ParseRequest) -> AuditResponse`: Expose routing and confidence data
  - `handle_partial_parsing(text: str, fields: List[str]) -> PartialParseResult`: Process only specified fields
  - `manage_cache(text_hash: str, result: ParsedEvent) -> CacheEntry`: 24h TTL caching
  - `collect_performance_metrics() -> PerformanceMetrics`: Component latency tracking
  - `lazy_load_heavy_modules()`: Defer expensive imports for faster cold starts

### 6. Performance Monitoring and Testing
- **Purpose**: Maintains system reliability and performance standards
- **Key Methods**:
  - `track_component_latency(component: str, duration_ms: int)`: Log processing times
  - `maintain_golden_set() -> List[TestCase]`: 50-100 curated test snippets
  - `generate_reliability_diagram(predictions: List[float], outcomes: List[bool]) -> ReliabilityDiagram`: Confidence calibration
  - `precompile_regex_patterns()`: Startup optimization
  - `warm_up_models()`: Model initialization on boot
  - `concurrent_field_processing(fields: List[str]) -> Dict[str, FieldResult]`: asyncio.gather() optimization

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
    recurrence: Optional[str]  # RRULE format
    participants: List[str]
    all_day: bool
    confidence_score: float
    field_results: Dict[str, FieldResult]  # Per-field results with provenance
    parsing_path: str  # "regex_primary", "deterministic_backup", "llm_fallback"
    processing_time_ms: int
    cache_hit: bool
    warnings: List[str]
    needs_confirmation: bool

### FieldResult
```python
@dataclass
class FieldResult:
    value: Any
    source: str  # "regex", "duckling", "recognizers", "llm"
    confidence: float
    span: Tuple[int, int]  # Character positions in original text
    alternatives: List[Any]  # Other possible values
    processing_time_ms: int
```

### RecurrenceResult
```python
@dataclass
class RecurrenceResult:
    rrule: Optional[str]  # RFC 5545 format
    natural_language: str  # Original text like "every other Tuesday"
    confidence: float
    pattern_type: str  # "weekly", "monthly", "daily", "custom"
    
### DurationResult
```python
@dataclass
class DurationResult:
    duration_minutes: Optional[int]
    end_time_override: Optional[datetime]  # For "until noon" cases
    all_day: bool
    confidence: float
    
### CacheEntry
```python
@dataclass
class CacheEntry:
    text_hash: str
    result: ParsedEvent
    timestamp: datetime
    hit_count: int
    
### AuditData
```python
@dataclass
class AuditData:
    field_routing_decisions: Dict[str, str]  # field -> processing_method
    confidence_breakdown: Dict[str, float]
    processing_times: Dict[str, int]  # component -> time_ms
    fallback_triggers: List[str]
    cache_status: str
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

### Enhanced Architecture Strategy

**Per-Field Confidence Routing**:
- **Field-Level Analysis**: Each field (start, end, recurrence, location, title, participants) analyzed independently
- **Confidence-Based Processing**: High confidence (≥0.8) → regex only; Medium (0.6-0.8) → deterministic backup; Low (<0.6) → LLM enhancement
- **Provenance Tracking**: Store {value, source, confidence, span} for each field result
- **Selective Enhancement**: LLM only processes fields that need improvement, reducing cost and latency

**Deterministic Backup Integration**:
- **Duckling Integration**: Facebook's rule-based parser for robust date/time extraction
- **Microsoft Recognizers**: Multi-language entity recognition for comprehensive coverage
- **Span Optimization**: Choose candidate with shortest valid span and proper timezone normalization
- **Confidence Calibration**: Deterministic methods provide 0.6-0.8 confidence range

**Enhanced LLM Guardrails**:
- **Schema Enforcement**: JSON/function-calling schema prevents modification of high-confidence fields
- **Context Limitation**: Only residual unparsed text sent to LLM, reducing token usage
- **Timeout Management**: 3-second timeout with single retry, return partial results on failure
- **Temperature Control**: Temperature=0 for deterministic outputs, prevent hallucination

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

### Enhanced Performance and Scalability

**Optimization Strategies**:
- **Lazy Module Loading**: Defer heavy imports (Duckling, Recognizers) until needed for faster cold starts
- **Regex Precompilation**: Compile patterns at startup for faster matching
- **Model Warm-up**: Initialize small models on boot to reduce first-request latency
- **Concurrent Processing**: Use asyncio.gather() for independent field processing
- **Intelligent Caching**: 24h TTL cache with normalized text hashing

**Resource Management**:
- **Memory efficiency**: Stream processing and lazy loading of large modules
- **CPU optimization**: Per-field routing prevents unnecessary processing
- **Network efficiency**: Partial parsing reduces API payload sizes
- **Timeout Handling**: Return partial results rather than failing completely

**Performance Monitoring**:
- **Component Latency**: Track regex, deterministic backup, and LLM processing times
- **Golden Set Testing**: Maintain 50-100 curated test cases for accuracy validation
- **Reliability Calibration**: Generate reliability diagrams for confidence score validation
- **Health Monitoring**: /healthz endpoint with component status and performance metrics

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