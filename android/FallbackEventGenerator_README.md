# FallbackEventGenerator Implementation

## Overview

The `FallbackEventGenerator` is a sophisticated component that creates meaningful calendar events when text parsing fails or returns low-confidence results. It implements intelligent text analysis, pattern matching, and contextual reasoning to extract the best possible event information from failed parsing attempts.

## Key Features

### 1. Meaningful Title Extraction
- **Pattern Matching**: Uses 8 different regex patterns to extract event titles from various text formats
- **Text Preprocessing**: Normalizes time formats, fixes spacing issues, and improves phrasing
- **Intelligent Cleanup**: Removes common prefixes and applies proper capitalization
- **Fallback Strategies**: Multiple levels of title extraction with confidence scoring

### 2. Smart Default Date/Time Generation
- **Context Analysis**: Analyzes text for time-related keywords (morning, afternoon, evening, etc.)
- **Weekday Detection**: Recognizes day names and calculates appropriate dates
- **Duration Estimation**: Estimates event duration based on event type keywords
- **Time-of-Day Defaults**: Applies reasonable defaults based on current time and context

### 3. Confidence Scoring
- **Multi-Factor Assessment**: Considers title quality, time relevance, text clarity, and partial results
- **Weighted Scoring**: Uses weighted averages of component confidences
- **Transparency**: Provides detailed confidence factors for debugging and improvement

### 4. Comprehensive Description Generation
- **Original Text Preservation**: Includes the original text for user reference
- **Extraction Details**: Documents how the event was created and what methods were used
- **Partial Result Integration**: Shows what information was available from failed API calls
- **User Guidance**: Provides clear instructions for manual adjustment

## Usage Examples

### Basic Usage

```kotlin
val fallbackEventGenerator = FallbackEventGenerator(context)

// Create fallback event from text only
val fallbackEvent = fallbackEventGenerator.generateFallbackEvent("Team meeting tomorrow at 2 PM")

// Convert to ParseResult for API compatibility
val parseResult = fallbackEventGenerator.toParseResult(fallbackEvent, originalText)
```

### With Partial API Results

```kotlin
// Enhance partial API results
val partialResult = ParseResult(
    title = "Meeting",
    startDateTime = null, // Missing
    endDateTime = null,   // Missing
    confidenceScore = 0.2 // Low confidence
)

val enhancedEvent = fallbackEventGenerator.generateFallbackEvent(
    originalText = "Important client meeting next Tuesday",
    partialResult = partialResult
)
```

### Integration with ErrorHandlingManager

The `FallbackEventGenerator` is automatically integrated into the `ErrorHandlingManager`:

```kotlin
val errorHandlingManager = ErrorHandlingManager(context)

// ErrorHandlingManager uses FallbackEventGenerator internally
val result = errorHandlingManager.createFallbackEvent(originalText, partialResult)
```

## Pattern Matching Examples

The FallbackEventGenerator recognizes various text patterns:

1. **"attend [EVENT] at [LOCATION]"** → **"[EVENT] at [LOCATION]"**
   - Input: "We will attend the conference at the convention center"
   - Output: "Conference at the convention center"

2. **"On [day] the [people] will attend [EVENT]"** → **"[EVENT] on [day]"**
   - Input: "On Friday the students will attend the science fair"
   - Output: "Science fair on Friday"

3. **Time Context Recognition**
   - "Morning meeting" → Scheduled for 9:00 AM
   - "Afternoon call" → Scheduled for 2:00 PM
   - "Evening dinner" → Scheduled for 7:00 PM

4. **Duration Estimation**
   - "Doctor appointment" → 30 minutes
   - "Conference" → 8 hours
   - "Lunch meeting" → 1 hour

## Configuration and Customization

### Event Type Durations

The generator includes predefined durations for common event types:

```kotlin
private val EVENT_TYPE_DURATIONS = mapOf(
    "meeting" to 60,      // 1 hour
    "appointment" to 30,   // 30 minutes
    "conference" to 480,  // 8 hours
    "lunch" to 60,        // 1 hour
    // ... more types
)
```

### Time Context Keywords

Recognizes various time-related keywords:

```kotlin
private val TIME_KEYWORDS = setOf(
    "morning", "afternoon", "evening", "night",
    "monday", "tuesday", "wednesday", // ... weekdays
    "today", "tomorrow", "weekend"
)
```

## Output Structure

### FallbackEvent Data Class

```kotlin
data class FallbackEvent(
    val title: String,                    // Extracted or generated title
    val startDateTime: String,            // ISO 8601 formatted start time
    val endDateTime: String,              // ISO 8601 formatted end time
    val description: String,              // Detailed description with extraction info
    val confidence: Double,               // Overall confidence score (0.0-1.0)
    val fallbackReason: String,           // Explanation of why fallback was used
    val location: String? = null,         // Location if available
    val allDay: Boolean = false,          // Whether it's an all-day event
    val timezone: String,                 // Timezone identifier
    val extractionDetails: ExtractionDetails // Detailed extraction metadata
)
```

### ExtractionDetails

```kotlin
data class ExtractionDetails(
    val titleExtractionMethod: String,           // How the title was extracted
    val timeGenerationMethod: String,            // How the time was generated
    val durationEstimationMethod: String,        // How duration was estimated
    val confidenceFactors: Map<String, Double>,  // Individual confidence factors
    val textPreprocessingApplied: List<String>,  // Preprocessing steps applied
    val patternsMatched: List<String>            // Patterns that matched the text
)
```

## Integration Points

### With ErrorHandlingManager

The `FallbackEventGenerator` is integrated into the `ErrorHandlingManager` for the following recovery strategies:

- `FALLBACK_EVENT_CREATION`: Creates intelligent fallback events
- `OFFLINE_MODE`: Generates events when network is unavailable
- `GRACEFUL_DEGRADATION`: Enhances partial API results

### With ApiService

When the `ApiService` fails or returns low-confidence results, the error handling system automatically uses the `FallbackEventGenerator` to create meaningful events.

## Testing

The implementation includes comprehensive unit tests in `FallbackEventGeneratorTest.kt` that verify:

- Title extraction from various text patterns
- Time context analysis and generation
- Duration estimation accuracy
- Confidence scoring correctness
- Integration with partial API results
- ParseResult conversion compatibility

## Performance Considerations

- **Efficient Pattern Matching**: Uses compiled regex patterns for fast text analysis
- **Minimal Memory Usage**: Processes text in-place without creating large intermediate objects
- **Configurable Complexity**: Balances sophistication with performance
- **Caching Opportunities**: Results can be cached for repeated similar inputs

## Future Enhancements

Potential improvements for future versions:

1. **Machine Learning Integration**: Train models on successful parsing patterns
2. **User Feedback Learning**: Adapt patterns based on user corrections
3. **Localization Support**: Add support for different languages and date formats
4. **Custom Pattern Configuration**: Allow users to define custom extraction patterns
5. **Advanced NLP**: Integrate more sophisticated natural language processing

## Requirements Satisfied

This implementation satisfies the following requirements from the specification:

- **3.1**: Creates meaningful titles from original text using pattern matching ✅
- **3.2**: Implements smart default date/time generation based on context ✅
- **3.3**: Generates descriptions including original text and fallback reasoning ✅
- **3.4**: Creates confidence scoring for fallback-generated events ✅
- **12.1-12.4**: Provides smart defaults and suggestions for missing data ✅

The `FallbackEventGenerator` ensures that users can always create calendar events, even when automatic parsing fails, while providing transparency about the extraction process and confidence in the results.