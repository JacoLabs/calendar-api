# Text-to-Calendar Event Parsing Documentation

## Overview

This document provides comprehensive documentation for the text-to-calendar event parsing system. The system uses an LLM-first approach with comprehensive fallback mechanisms to extract structured event information from natural language text.

## Architecture

The parsing system follows a layered architecture with the following components:

```
┌─────────────────────────────────────┐
│        MasterEventParser           │
│     (LLM-first orchestration)      │
├─────────────────────────────────────┤
│  LLMService  │  FormatProcessor    │
│  (Primary)   │  (Text cleanup)     │
├─────────────────────────────────────┤
│  EventParser │  AdvancedLocation   │
│  (Fallback)  │  SmartTitle        │
├─────────────────────────────────────┤
│     ComprehensiveErrorHandler       │
│     (Validation & Recovery)         │
└─────────────────────────────────────┘
```

## Parsing Strategy

### LLM-First Approach

1. **Primary LLM Processing**: Uses Ollama with Llama 3.2 3B model for natural language understanding
2. **Regex Fallback**: Falls back to pattern-based extraction when LLM confidence is below threshold (0.4)
3. **Component Enhancement**: Specialized extractors enhance results for location and title
4. **Error Handling**: Comprehensive validation and recovery mechanisms

### Execution Order

1. Text Format Processing (normalization and cleanup)
2. LLM Primary Extraction (structured prompts with JSON output)
3. Regex Fallback (if LLM fails or low confidence)
4. Component Enhancement (location and title specialists)
5. Error Handling & Validation
6. Cross-component Validation & Consistency Checking
7. Unified Confidence Scoring & Normalization

## Date and Time Parsing Capabilities

### Supported Date Formats

#### Explicit Dates
- **Full format**: `Monday, Sep 29, 2025`, `September 29th, 2025`
- **Numeric formats**: `09/29/2025`, `29/09/2025`, `2025-09-29`
- **Inline dates**: `Sep 29` (assumes current year)
- **Month variations**: `January`, `Jan`, `Sept`, `September`

#### Relative Dates
- **Simple relative**: `today`, `tomorrow`, `yesterday`
- **Weekday references**: `next Monday`, `this Friday`, `next week`
- **Duration-based**: `in 2 weeks`, `in three days`, `in a month`
- **Natural phrases**: `the first day back after break`, `end of month`

#### Date Parsing Examples
```
Input: "Meeting tomorrow at 2pm"
→ Date: [tomorrow's date], Time: 14:00

Input: "Conference on Monday, Sep 29, 2025"
→ Date: 2025-09-29, Confidence: 0.95

Input: "Lunch next Friday"
→ Date: [next Friday's date], Confidence: 0.9

Input: "Training in two weeks"
→ Date: [date 14 days from now], Confidence: 0.9
```

### Supported Time Formats

#### Explicit Times
- **12-hour format**: `9:00 AM`, `2:30 PM`, `noon`, `midnight`
- **24-hour format**: `14:30`, `09:00`, `21:45`
- **Typo tolerance**: `9a.m`, `9am`, `9:00 A M`, `2 PM`
- **Special times**: `noon`, `midnight`

#### Relative Times
- **Contextual**: `after lunch` → 1:00 PM, `before school` → 8:00 AM
- **General**: `morning` → 9:00 AM, `afternoon` → 2:00 PM, `evening` → 6:00 PM

#### Time Ranges
- **Dash formats**: `9–10 a.m.`, `2:00-3:30 PM`
- **Word formats**: `from 3 p.m. to 5 p.m.`
- **Shared AM/PM**: `9-10 AM` (both times are AM)

#### Duration Calculation
- **Explicit duration**: `for 2 hours`, `30 minutes long`
- **Automatic**: If no end time, defaults to 1-hour duration

#### Time Parsing Examples
```
Input: "Call at 9:30 AM"
→ Time: 09:30, Confidence: 0.95

Input: "Meeting from 2-3 PM"
→ Start: 14:00, End: 15:00, Confidence: 0.9

Input: "Lunch after noon for 1 hour"
→ Start: 12:00, End: 13:00, Confidence: 0.8

Input: "Training at 9a.m"
→ Time: 09:00, Confidence: 0.9 (typo corrected)
```

## Location Extraction Strategies

### Location Types

#### Explicit Addresses
- **Street addresses**: `123 Main Street`, `456 Oak Avenue, Toronto`
- **Named locations**: `Nathan Phillips Square`, `CN Tower`
- **Postal codes**: `M5V 3A8`, `K1A 0A6`
- **Coordinates**: `43.6532, -79.3832`

#### Venue-Based Locations
- **Rooms**: `Conference Room A`, `Room 205`, `Boardroom`
- **Buildings**: `Building B`, `Tower 1`, `Main Building`
- **Floors**: `3rd floor`, `Ground floor`, `Basement`
- **Offices**: `Office 123`, `Suite 456`

#### Implicit Locations
- **Workplace**: `the office`, `work`, `headquarters`
- **Educational**: `school`, `university`, `campus`, `classroom`
- **Generic**: `gym`, `library`, `downtown`, `mall`

#### Directional Locations
- **Entrances**: `front entrance`, `main doors`, `back gate`
- **Relative**: `by the lobby`, `near the parking lot`
- **Floor references**: `upstairs`, `downstairs`, `ground floor`

### Context Clue Patterns

The system recognizes location indicators:
- **Prepositions**: `at [location]`, `in [location]`, `by [location]`
- **Symbols**: `@ [location]`
- **Labels**: `venue: [location]`, `address: [location]`
- **Actions**: `meet at [location]`

### Location Parsing Examples
```
Input: "Meeting at Nathan Phillips Square"
→ Location: "Nathan Phillips Square", Type: ADDRESS, Confidence: 0.9

Input: "Conference in Room 205"
→ Location: "Room 205", Type: VENUE, Confidence: 0.85

Input: "Lunch at the office"
→ Location: "the office", Type: IMPLICIT, Confidence: 0.7

Input: "Meet at the front entrance"
→ Location: "front entrance", Type: DIRECTIONAL, Confidence: 0.75
```

## Title Generation and Extraction Methods

### Title Extraction Strategies

#### Formal Event Names
- **Quoted titles**: `"Annual Planning Meeting"`
- **Proper nouns**: `Indigenous Legacy Gathering`
- **Event keywords**: `Training Session`, `Conference Call`

#### Context-Derived Titles
- **Meeting patterns**: `meeting with John` → "Meeting with John"
- **Call patterns**: `call with the team` → "Call with the Team"
- **Activity patterns**: `lunch with Sarah` → "Lunch with Sarah"

#### Action-Based Generation
- **Future actions**: `we will discuss the budget` → "Discuss the Budget"
- **Plans**: `let's review the proposal` → "Review the Proposal"
- **Needs**: `need to finalize the contract` → "Finalize the Contract"

#### Fallback Methods
- **First words**: Uses first 2-4 meaningful words as title
- **Generic titles**: "Meeting", "Event", "Appointment" when nothing else works
- **User prompt**: Requests manual input for low-quality extractions

### Title Quality Assessment

The system evaluates title quality based on:
- **Completeness**: Not truncated or incomplete
- **Meaningfulness**: Contains descriptive content
- **Length**: Appropriate length (5-50 characters optimal)
- **Context relevance**: Matches the event context

### Title Generation Examples
```
Input: "Annual Planning Meeting tomorrow at 2pm"
→ Title: "Annual Planning Meeting", Method: explicit, Confidence: 0.9

Input: "Let's discuss the quarterly results"
→ Title: "Discuss the Quarterly Results", Method: action_based, Confidence: 0.8

Input: "Call with Sarah about the project"
→ Title: "Call with Sarah", Method: context_derived, Confidence: 0.85

Input: "Meeting tomorrow"
→ Title: "Meeting", Method: simple_action, Confidence: 0.6
```

## Text Format Handling

### Supported Text Formats

#### Email Formats
- **Bullet points**: Structured information in lists
- **Paragraphs**: Event details embedded in prose
- **Multi-paragraph**: Information spread across multiple paragraphs
- **Mixed content**: Combination of structured and unstructured text

#### Format Normalization
- **Typo correction**: `9a.m` → `9:00 AM`, `tommorrow` → `tomorrow`
- **Case normalization**: Proper capitalization for names and places
- **Whitespace cleanup**: Removes extra spaces and line breaks
- **Punctuation standardization**: Consistent use of punctuation

#### Multi-Event Detection
- **Separate events**: Identifies multiple distinct events in single text
- **Event boundaries**: Determines where one event ends and another begins
- **Context preservation**: Maintains context for each identified event

### Format Processing Examples
```
Input: "• Meeting with John tomorrow at 2pm
        • Call with Sarah on Friday at 10am"
→ Detects: 2 separate events with proper parsing

Input: "We have a team meeting scheduled for tomorrow at 2:00 P M in the conference room. Please bring your laptops."
→ Normalizes: "2:00 PM", extracts all components

Input: "URGENT: board meeting TOMORROW at the OFFICE"
→ Normalizes: "Board meeting tomorrow at the office"
```

## Error Handling and Fallback Mechanisms

### Confidence Scoring System

#### Confidence Levels
- **High (0.8-1.0)**: Explicit, unambiguous information
- **Medium (0.4-0.8)**: Clear but potentially ambiguous
- **Low (0.0-0.4)**: Uncertain or inferred information

#### Field-Level Confidence
Each extracted field has individual confidence scores:
- **Title confidence**: Based on extraction method and quality
- **DateTime confidence**: Based on format explicitness
- **Location confidence**: Based on specificity and context
- **Overall confidence**: Weighted average of field confidences

### Error Recovery Strategies

#### Low Confidence Handling
- **Threshold checking**: Confidence below 0.3 triggers user confirmation
- **Alternative suggestions**: Provides multiple interpretation options
- **Partial completion**: Accepts partial information, prompts for missing fields

#### Missing Information Handling
- **Required fields**: Title and start time are required for event creation
- **Optional fields**: Location and description are optional
- **Default values**: Provides sensible defaults (1-hour duration, no location)

#### Ambiguity Resolution
- **Multiple interpretations**: Presents options for user selection
- **Context clues**: Uses surrounding text to resolve ambiguities
- **User clarification**: Prompts for clarification when needed

### Fallback Mechanisms

#### LLM Failure Fallback
1. **Regex patterns**: Falls back to pattern-based extraction
2. **Component extractors**: Uses specialized extractors for specific fields
3. **Manual input**: Prompts user for missing information
4. **Graceful degradation**: Creates partial events when possible

#### Validation and Consistency
- **Cross-field validation**: Ensures extracted fields are consistent
- **Temporal validation**: Checks that dates/times make sense
- **Location validation**: Verifies location format and reasonableness
- **Quality thresholds**: Rejects extractions below minimum quality

### Error Handling Examples
```
Input: "Something tomorrow"
→ Error: Low confidence title, prompts user for clarification
→ Fallback: Uses "Something" as title with low confidence

Input: "Meeting at 25:00"
→ Error: Invalid time format
→ Fallback: Prompts user for correct time

Input: "Event on February 30th"
→ Error: Invalid date
→ Fallback: Suggests nearby valid dates
```

## API Integration

### Parsing Service Endpoints

#### POST /parse
Parses text and returns structured event information.

**Request:**
```json
{
  "text": "Meeting with John tomorrow at 2pm in Conference Room A",
  "preferences": {
    "date_format": "MM/DD/YYYY",
    "time_format": "12_hour",
    "timezone": "America/Toronto"
  }
}
```

**Response:**
```json
{
  "success": true,
  "parsed_event": {
    "title": "Meeting with John",
    "start_datetime": "2025-09-30T14:00:00",
    "end_datetime": "2025-09-30T15:00:00",
    "location": "Conference Room A",
    "description": "Meeting with John tomorrow at 2pm in Conference Room A",
    "confidence_score": 0.85
  },
  "field_confidence": {
    "title": 0.8,
    "start_datetime": 0.9,
    "end_datetime": 0.7,
    "location": 0.85
  },
  "parsing_metadata": {
    "parsing_method": "llm_primary",
    "processing_time": 1.2,
    "llm_used": true
  }
}
```

#### Error Responses
```json
{
  "success": false,
  "error": "No event information found",
  "suggestions": [
    "Please provide more specific date/time information",
    "Consider including a clear event title"
  ],
  "partial_extraction": {
    "detected_elements": ["time_reference"],
    "missing_elements": ["title", "specific_date"]
  }
}
```

### Integration Guidelines

#### Client Implementation
1. **Send text**: POST text content to /parse endpoint
2. **Handle responses**: Process both success and error responses
3. **User confirmation**: Show parsed results for user verification
4. **Error handling**: Implement fallback for parsing failures

#### Rate Limiting
- **Request limits**: 100 requests per minute per client
- **Text size limits**: Maximum 5000 characters per request
- **Timeout handling**: 30-second timeout for processing

#### Authentication
- **API keys**: Required for production usage
- **CORS**: Configured for browser and mobile app access
- **Security**: HTTPS required for all requests

## Performance Characteristics

### Processing Speed
- **LLM processing**: 1-3 seconds for typical text
- **Regex fallback**: <100ms for pattern matching
- **Total processing**: Usually under 5 seconds including validation

### Accuracy Metrics
- **Overall accuracy**: 85-95% for well-formed text
- **Date/time accuracy**: 90-98% for explicit formats
- **Location accuracy**: 75-90% depending on specificity
- **Title accuracy**: 80-95% for clear event descriptions

### Resource Usage
- **Memory**: ~500MB for LLM model loading
- **CPU**: Moderate usage during LLM inference
- **Network**: Minimal (local LLM processing)

## Troubleshooting Guide

### Common Parsing Issues

#### Low Confidence Results
**Symptoms**: Confidence scores below 0.4, uncertain extractions
**Causes**: Ambiguous text, missing context, typos
**Solutions**:
- Provide more specific information
- Use explicit date/time formats
- Include clear event titles
- Check for typos in input text

#### Missing Date/Time Information
**Symptoms**: No date or time extracted
**Causes**: Vague temporal references, missing time information
**Solutions**:
- Use specific dates (e.g., "September 29" instead of "soon")
- Include explicit times (e.g., "2:00 PM" instead of "afternoon")
- Provide context for relative dates

#### Incorrect Location Extraction
**Symptoms**: Wrong location or no location found
**Causes**: Ambiguous location references, missing context clues
**Solutions**:
- Use specific addresses or venue names
- Include location indicators ("at", "in", "@")
- Provide full location context

#### Title Generation Problems
**Symptoms**: Generic or poor-quality titles
**Causes**: Lack of clear event description, action-only text
**Solutions**:
- Include descriptive event names
- Use formal event titles when available
- Provide context about the event purpose

### Debugging Steps

1. **Check input text**: Verify text contains event information
2. **Review confidence scores**: Identify low-confidence fields
3. **Examine parsing metadata**: Check which methods were used
4. **Test with simpler text**: Try with more explicit information
5. **Check API logs**: Review server logs for processing details

### Performance Issues

#### Slow Processing
**Causes**: Large text blocks, LLM model loading, network issues
**Solutions**:
- Limit text to relevant portions
- Use regex fallback for simple cases
- Implement client-side caching

#### Memory Usage
**Causes**: LLM model size, concurrent requests
**Solutions**:
- Monitor server resources
- Implement request queuing
- Consider model optimization

## Best Practices

### Input Text Guidelines

#### Optimal Text Format
- **Clear structure**: Use proper sentences and punctuation
- **Specific information**: Include explicit dates, times, and locations
- **Context**: Provide enough context for understanding
- **Length**: Keep text focused and relevant (under 1000 characters optimal)

#### Examples of Good Input
```
✓ "Team meeting on Monday, September 29th at 2:00 PM in Conference Room A"
✓ "Lunch with Sarah tomorrow at 12:30 PM at the downtown cafe"
✓ "Annual planning session next Friday from 9 AM to 5 PM"
```

#### Examples to Avoid
```
✗ "thing tomorrow" (too vague)
✗ "meet sometime next week" (no specific time)
✗ "important call" (missing all details)
```

### Integration Best Practices

#### Error Handling
- Always check the `success` field in responses
- Implement fallback UI for parsing failures
- Show confidence scores to users
- Allow manual editing of extracted information

#### User Experience
- Display parsed results for confirmation
- Highlight low-confidence fields
- Provide edit capabilities for all fields
- Show alternative suggestions when available

#### Performance Optimization
- Cache parsing results for identical text
- Implement request debouncing for real-time parsing
- Use appropriate timeouts for API calls
- Monitor and log parsing performance

### Quality Assurance

#### Testing Strategies
- Test with various text formats and styles
- Include edge cases and error conditions
- Validate against known good examples
- Monitor accuracy metrics in production

#### Continuous Improvement
- Collect user feedback on parsing accuracy
- Analyze failed parsing attempts
- Update patterns and models based on usage
- Monitor confidence score distributions

This documentation provides comprehensive coverage of the parsing system's capabilities, limitations, and best practices for integration and usage.