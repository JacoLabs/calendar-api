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