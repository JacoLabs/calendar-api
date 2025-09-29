# Design Document

## Overview

The text-to-calendar event feature will be implemented as a Python application that provides text selection capabilities, natural language processing for event extraction, and calendar event creation. The system will use a modular architecture with separate components for text processing, UI interaction, and calendar management.

## Architecture

The application follows a layered architecture pattern:

```
┌─────────────────────────────────────┐
│           User Interface            │
│  (Text Selection + Event Form)      │
├─────────────────────────────────────┤
│         Event Parser Service       │
│    (NLP + Date/Time Extraction)    │
├─────────────────────────────────────┤
│        Calendar Service            │
│     (Event Creation + Storage)     │
├─────────────────────────────────────┤
│           Data Models              │
│    (Event, DateTime, Location)     │
└─────────────────────────────────────┘
```

## Components and Interfaces

### 1. Text Selection Handler
- **Purpose**: Manages text highlighting and context menu integration
- **Key Methods**:
  - `capture_selected_text()`: Gets highlighted text from clipboard or selection
  - `show_context_menu()`: Displays "Create Calendar Event" option
  - `handle_selection()`: Processes user's menu selection

### 2. Event Parser Service
- **Purpose**: Extracts structured event data from natural language text with comprehensive real-world format handling
- **Key Methods**:
  - `parse_event_text(text: str) -> ParsedEvent`: Main parsing method with confidence scoring
  - `extract_datetime(text: str) -> DateTimeResult`: Comprehensive date/time extraction with fallbacks
  - `extract_location(text: str) -> LocationResult`: Multi-strategy location identification
  - `extract_title(text: str) -> TitleResult`: Intelligent title generation and extraction
  - `validate_extraction(event: ParsedEvent) -> ValidationResult`: Quality assessment and completeness check
  - `normalize_output(event: ParsedEvent) -> NormalizedEvent`: Ensures consistent output format

**Comprehensive Parsing Strategy**:

**Date Parsing**:
- Explicit dates: Monday, Sep 29, 2025; 09/29/2025; September 29th
- Relative dates: tomorrow, this Monday, next week, in two weeks
- Natural phrases: the first day back after break, end of month
- Inline dates: Sep 29 (assume current year)
- Handle typos and variations in date formats

**Time Parsing**:
- Explicit times: 9:00 a.m., 21:00, noon, midnight
- Typo handling: 9a.m, 9am, 9:00 A M, 9 AM
- Relative times: after lunch (1:00 PM), before school (8:00 AM), end of day (5:00 PM)
- Time ranges: 9–10 a.m., from 3 p.m. to 5 p.m., 2:00-3:30
- Duration calculation: "for 2 hours", "30 minutes long"

**Location Parsing**:
- Explicit addresses: Nathan Phillips Square, 123 Main Street
- Implicit locations: at school, gym, the office, downtown
- Direction-based: meet at the front doors, by the entrance
- Venue keywords: Square, Park, Center, Hall, School, Building, Room
- Context clues: "venue:", "at", "in", "@" indicators

**Title Generation**:
- Formal event names: Indigenous Legacy Gathering
- Action-based: "We will leave school" → "School Departure"
- Context-derived: Use who/what/where when no explicit title
- Avoid truncated sentences and incomplete phrases
- Prioritize descriptive over generic titles

**Format Handling**:
- Bullet points in emails
- Full paragraphs with embedded information
- Multiple events in single text
- Screenshot text vs highlighted text consistency
- Structured vs unstructured content

### 3. Event Form UI
- **Purpose**: Provides interface for reviewing and editing extracted event data
- **Key Methods**:
  - `display_preview(event: ParsedEvent)`: Shows extracted information
  - `validate_form() -> bool`: Ensures required fields are complete
  - `get_user_input() -> Event`: Returns finalized event data
  - `handle_confirmation()`: Processes user's create/cancel decision

### 4. Calendar Service
- **Purpose**: Manages calendar event creation and storage
- **Key Methods**:
  - `create_event(event: Event) -> bool`: Creates calendar entry
  - `validate_event(event: Event) -> ValidationResult`: Checks event validity
  - `get_default_calendar() -> Calendar`: Retrieves user's primary calendar
  - `handle_conflicts(event: Event) -> ConflictResolution`: Manages scheduling conflicts

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
    generation_method: str  # "explicit", "derived", "generated"
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

### Low Confidence Extraction
- **Confidence < 0.3**: Show "Please confirm" dialog with parsed fields for user review
- **Missing Critical Fields**: Highlight missing information and provide input prompts
- **Ambiguous Parsing**: Present multiple options with confidence scores for user selection

### Multiple Interpretations
- **Multiple Dates/Times**: Default to first occurrence, offer alternatives in confirmation dialog
- **Multiple Locations**: Prioritize explicit addresses over implicit references
- **Multiple Events**: Detect and offer to create separate calendar events

### Graceful Degradation
- **No Calendar Info Detected**: Return clear "No event information found" message instead of creating empty events
- **Partial Information**: Create event with available data, mark missing fields for user completion
- **Format Recognition Failure**: Fall back to basic keyword extraction with lower confidence scores

### Consistency Mechanisms
- **Screenshot vs Highlight Text**: Apply same parsing pipeline regardless of input method
- **Normalization**: Convert all outputs to standard format (title, startDateTime, endDateTime, location, description, confidenceScore)
- **Quality Assurance**: Validate extracted information meets minimum quality thresholds before presenting to user

### Typo and Format Tolerance
- **Time Format Variations**: Normalize 9a.m, 9am, 9:00 A M to standard format
- **Date Format Flexibility**: Handle various separators (/, -, .) and ordering (MM/DD vs DD/MM)
- **Case Insensitivity**: Process text regardless of capitalization
- **Whitespace Handling**: Trim and normalize spacing in extracted fields

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

### Parsing Architecture

**Multi-Strategy Approach**:
- **Primary**: Regex patterns for structured formats
- **Secondary**: Keyword-based extraction for unstructured text
- **Tertiary**: Context-based inference for ambiguous content
- **Libraries**: dateutil.parser, spaCy for NLP, fuzzy string matching

**Confidence Scoring System**:
- **Field-level confidence**: Individual scores for title, date, time, location
- **Overall confidence**: Weighted average based on field importance
- **Threshold-based actions**: Different UI flows based on confidence levels
- **Learning mechanism**: Improve confidence scoring based on user corrections

### User Experience Enhancements

**Progressive Disclosure**:
- **High Confidence (>0.8)**: Direct event creation with minimal confirmation
- **Medium Confidence (0.4-0.8)**: Show preview with editable fields
- **Low Confidence (<0.4)**: Guided form with suggestions and alternatives

**Intelligent Feedback**:
- **Real-time validation**: Immediate feedback on field completeness
- **Contextual suggestions**: "Did you mean [alternative]?" for ambiguous content
- **Quality indicators**: Visual cues for field confidence levels

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

**Modular Design**:
- **Parser plugins**: Separate modules for different text types (email, document, web)
- **Format handlers**: Specialized processors for bullet points, paragraphs, tables
- **Calendar backends**: Abstracted interface for multiple calendar systems

**Configuration Management**:
- **User preferences**: Customizable parsing rules and default behaviors
- **Pattern updates**: Hot-swappable regex patterns and keyword lists
- **Localization support**: Multi-language date/time format handling