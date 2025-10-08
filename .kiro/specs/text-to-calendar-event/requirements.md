# Requirements Document

## Introduction

This feature enables users to highlight text containing event information and automatically create calendar events from the extracted data. The system will parse natural language text to identify key event components with the following priority: title and date/time information are essential for successful event creation, while location and description are optional enhancements. The system provides robust handling of real-world email formats, typos, and ambiguous content with intelligent fallback mechanisms and confidence scoring to ensure consistent results across Gmail highlights, plain text, and various formatting styles.

## Requirements

### Requirement 1

**User Story:** As a user, I want to highlight text containing event information, so that I can quickly create calendar events without manual data entry.

#### Acceptance Criteria

1. WHEN a user highlights text THEN the system SHALL display a "Create Calendar Event" option
2. WHEN a user selects the "Create Calendar Event" option THEN the system SHALL parse the highlighted text for event information
3. WHEN the system parses text THEN it SHALL extract date, time, title, and location information when present
4. WHEN event information is extracted THEN the system SHALL pre-populate a calendar event creation form

### Requirement 2

**User Story:** As a user, I want the system to intelligently parse comprehensive date and time formats including typos and variations, so that I can create events from any real-world text source.

#### Acceptance Criteria

1. WHEN text contains explicit dates (Monday, Sep 29, 2025; 09/29/2025; September 29) THEN the system SHALL correctly identify the date
2. WHEN text contains relative dates (this Monday, tomorrow, next week, in two weeks, the first day back after break) THEN the system SHALL convert them to absolute dates
3. WHEN text contains inline dates without year (Sep 29) THEN the system SHALL assume current year
4. WHEN text contains natural date phrases (the first day back after break, in two weeks) THEN the system SHALL interpret contextually
5. WHEN text contains explicit times (9:00 a.m., 21:00, noon, 9a.m, 9am, 9:00 A M) THEN the system SHALL normalize to standard format
6. WHEN text contains relative times (after lunch, before school, end of day) THEN the system SHALL convert to approximate times
7. WHEN text contains time ranges (9–10 a.m., from 3 p.m. to 5 p.m.) THEN the system SHALL extract start and end times
8. WHEN text contains duration information ("for 2 hours", "30 minutes") THEN the system SHALL calculate the end time

### Requirement 3

**User Story:** As a user, I want to review and edit the extracted event information before creating the calendar event, so that I can ensure accuracy and add missing details.

#### Acceptance Criteria

1. WHEN event information is extracted THEN the system SHALL display a preview form with all extracted data
2. WHEN the preview form is displayed THEN the user SHALL be able to edit any field (title, date, time, location, description)
3. WHEN required information is missing THEN the system SHALL highlight missing fields and prompt for input
4. WHEN the user confirms the event details THEN the system SHALL create the calendar event

### Requirement 4

**User Story:** As a user, I want the system to optionally extract location information when available, so that I can enhance my calendar events with venue details when present.

#### Acceptance Criteria

1. WHEN text contains explicit addresses (Nathan Phillips Square, 123 Main St) THEN the system SHOULD extract the full address
2. WHEN text contains implicit locations (at school, gym, the office) THEN the system SHOULD identify and extract them
3. WHEN text contains directions as locations (meet at the front doors) THEN the system SHOULD capture the meeting point
4. WHEN text contains venue keywords (Square, Park, Center, Hall, School, Building) THEN the system SHOULD recognize them as locations
5. WHEN multiple locations are present THEN the system SHOULD prioritize the most relevant location
6. WHEN no location is present THEN the system SHALL still create a valid event without location information
7. WHEN location extraction fails THEN the system SHALL NOT prevent event creation

### Requirement 5

**User Story:** As a user, I want the system to intelligently extract and generate event titles from various text formats, so that my calendar events have meaningful names.

#### Acceptance Criteria

1. WHEN text contains formal event names (Indigenous Legacy Gathering) THEN the system SHALL use them as titles
2. WHEN no explicit title is given THEN the system SHALL derive titles from who/what/where context
3. WHEN titles would be truncated sentences THEN the system SHALL create complete, meaningful titles
4. WHEN multiple title candidates exist THEN the system SHALL select the most descriptive option

### Requirement 6

**User Story:** As a user, I want the system to handle various text formats and sources consistently, so that I can create events from emails, documents, and web pages.

#### Acceptance Criteria

1. WHEN text contains bullet points in emails THEN the system SHALL parse structured information correctly
2. WHEN text contains full paragraphs with buried info THEN the system SHALL extract relevant event details
3. WHEN text spans multiple paragraphs THEN the system SHALL treat the entire highlighted text as one event description and extract information from across all paragraphs
4. WHEN text contains multiple events in one email THEN the system SHALL identify and offer to create separate events
5. WHEN text contains typos and odd casing (9a.m, 9am, 9:00 A M) THEN the system SHALL normalize and parse correctly
6. WHEN text format varies (screenshots vs highlights vs plain text) THEN the system SHALL produce equally structured results

### Requirement 7

**User Story:** As a user, I want robust error handling and confidence scoring, so that I can trust the system's parsing results and get helpful feedback.

#### Acceptance Criteria

1. WHEN extraction confidence is low THEN the system SHALL provide fallback options and show parsed fields for confirmation
2. WHEN multiple possible dates/times exist THEN the system SHALL ask for clarification or default to the most likely option
3. WHEN no calendar info is detected THEN the system SHALL gracefully indicate "not found" without creating junk events
4. WHEN parsing fails THEN the system SHALL provide specific error messages and suggest manual input
5. WHEN extraction is successful THEN the system SHALL provide confidence scores for essential fields (title, startDateTime, endDateTime) and optional fields (location, description) with lower confidence thresholds for optional fields

### Requirement 8

**User Story:** As a user, I want the created events to be saved to my calendar system with consistent output format, so that I can access them through my regular calendar interface.

#### Acceptance Criteria

1. WHEN a calendar event is created THEN it SHALL be saved to the user's default calendar
2. WHEN an event is saved THEN the system SHALL provide confirmation with event details
3. WHEN an event creation fails THEN the system SHALL display an error message and allow retry
4. WHEN an event is created THEN it SHALL include normalized output with title, startDateTime, endDateTime, location, description, and confidenceScore
5. WHEN events are created from different sources THEN they SHALL follow the same structured format regardless of input method

### Requirement 9

**User Story:** As a user, I want the system to reliably convert messy, real-world text into calendar events, so that I can highlight anything (emails, reminders, receipts, tickets) and still get accurate event details.

#### Acceptance Criteria

1. WHEN text contains explicit dates/times (Oct 15, 2025, 2–3pm, tomorrow at noon) THEN the system SHALL extract and normalize them
2. WHEN text contains metadata or noise (Item ID, Status, Assignee) THEN the system SHALL ignore or downweight it
3. WHEN regex extraction succeeds THEN the system SHALL set confidence ≥ 0.8 and LLM SHALL only polish titles/description
4. WHEN regex fails THEN the system SHALL fall back to LLM parsing, mark confidence ≤ 0.5, and add a warning
5. WHEN extraction confidence < 0.6 THEN the system SHALL flag needs_confirmation in the response
6. WHEN user's timezone and current time are provided THEN the system SHALL resolve relative dates/times accurately (e.g., "tomorrow 7am")
7. WHEN event information is extracted THEN the response SHALL always include: title, start_datetime, end_datetime, all_day, description, confidence_score, warnings

### Requirement 10

**User Story:** As a developer, I want per-field confidence tracking and routing, so that the system can optimize parsing performance by only enhancing low-confidence fields with LLM processing.

#### Acceptance Criteria

1. WHEN parsing text THEN the system SHALL compute confidence scores for each field (start, end, recurrence, location, title, participants)
2. WHEN a field has high confidence (≥0.8) THEN the system SHALL NOT invoke LLM enhancement for that field
3. WHEN a field has low confidence (<0.8) THEN the system SHALL route only that field to LLM enhancement
4. WHEN storing field results THEN the system SHALL include {value, source, confidence, span} provenance data
5. WHEN multiple parsing methods extract the same field THEN the system SHALL choose the highest confidence result
6. WHEN field confidence varies THEN the system SHALL provide field-level confidence in API responses

### Requirement 11

**User Story:** As a developer, I want a deterministic backup parsing layer, so that the system has reliable fallback options before invoking expensive LLM processing.

#### Acceptance Criteria

1. WHEN regex parsing fails THEN the system SHALL attempt parsing with Duckling or Microsoft Recognizers-Text
2. WHEN multiple deterministic parsers succeed THEN the system SHALL choose the candidate with shortest valid span
3. WHEN deterministic parsers extract dates THEN the system SHALL validate timezone normalization
4. WHEN deterministic backup succeeds THEN the system SHALL set confidence between 0.6-0.8
5. WHEN all deterministic methods fail THEN the system SHALL invoke LLM parsing as final fallback

### Requirement 12

**User Story:** As a developer, I want LLM processing with strict guardrails, so that high-confidence regex fields cannot be corrupted and processing remains efficient.

#### Acceptance Criteria

1. WHEN using LLM enhancement THEN the system SHALL enforce JSON/function-calling schema
2. WHEN high-confidence regex fields exist THEN the LLM SHALL NOT be allowed to modify those fields
3. WHEN invoking LLM THEN the system SHALL limit context to residual unparsed text only
4. WHEN LLM processing exceeds 3 seconds THEN the system SHALL timeout and retry once
5. WHEN using LLM THEN the system SHALL set temperature to 0 for deterministic results
6. WHEN LLM fails after retry THEN the system SHALL return partial results with warnings

### Requirement 13

**User Story:** As a user, I want enhanced recurrence and duration support, so that I can create recurring events and events with specific durations from natural language.

#### Acceptance Criteria

1. WHEN text contains "every other Tuesday" THEN the system SHALL create RRULE with FREQ=WEEKLY;INTERVAL=2;BYDAY=TU
2. WHEN text contains "for 45 minutes" THEN the system SHALL calculate end time as start time + 45 minutes
3. WHEN text contains "until noon" THEN the system SHALL set end time to 12:00 PM
4. WHEN text contains "all-day" THEN the system SHALL create all-day event with no specific times
5. WHEN recurrence is detected THEN the system SHALL normalize to RFC 5545 RRULE format
6. WHEN duration conflicts with explicit end time THEN the system SHALL prioritize explicit end time

### Requirement 14

**User Story:** As a developer, I want enhanced API capabilities, so that I can audit parsing decisions, request partial parses, and benefit from caching.

#### Acceptance Criteria

1. WHEN mode=audit is specified THEN the API SHALL expose routing decisions and confidence data
2. WHEN fields=start,title query param is provided THEN the API SHALL compute partial parse for only those fields
3. WHEN identical normalized text is parsed THEN the system SHALL return cached results within 24h TTL
4. WHEN caching THEN the system SHALL use normalized text hash as cache key
5. WHEN audit mode is used THEN the response SHALL include parsing_path, field_sources, and confidence_breakdown
6. WHEN partial parsing is requested THEN the system SHALL only process and return specified fields

### Requirement 15

**User Story:** As a developer, I want comprehensive performance monitoring, so that I can track system performance and maintain reliability standards.

#### Acceptance Criteria

1. WHEN parsing text THEN the system SHALL log latency by component (regex, deterministic backup, LLM)
2. WHEN evaluating accuracy THEN the system SHALL maintain golden set of 50-100 test snippets
3. WHEN measuring calibration THEN the system SHALL produce reliability diagram for confidence scores
4. WHEN API responds THEN the system SHALL include performance metrics in headers
5. WHEN system starts THEN the system SHALL precompile regex patterns and warm up models
6. WHEN LLM times out THEN the system SHALL return partial parse results rather than failing

### Requirement 16

**User Story:** As a user, I want optimized API performance, so that parsing requests complete quickly and the system remains responsive.

#### Acceptance Criteria

1. WHEN API starts THEN the system SHALL lazy-load large modules to reduce cold start time
2. WHEN health check is requested THEN the system SHALL respond at /healthz endpoint within 100ms
3. WHEN using FastAPI THEN the system SHALL use async processing with uvicorn and uvloop
4. WHEN parsing multiple fields THEN the system SHALL use asyncio.gather() for concurrent processing
5. WHEN LLM processing times out THEN the system SHALL return partial results rather than failing completely
6. WHEN system performance degrades THEN the health check SHALL reflect degraded status
