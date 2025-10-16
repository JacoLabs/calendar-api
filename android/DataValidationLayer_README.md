# Data Validation and Sanitization Layer

## Overview

The Data Validation and Sanitization Layer provides comprehensive validation, sanitization, and error handling for calendar event data before creation. This system ensures data integrity, applies safe defaults for missing fields, and provides detailed user feedback.

## Components

### 1. DataValidationManager
**File:** `DataValidationManager.kt`

The core validation engine that performs comprehensive validation and sanitization of ParseResult objects.

**Key Features:**
- Essential field validation (title, start date/time)
- Data format validation and sanitization
- Confidence score assessment
- Smart default generation
- Data integrity checks
- User-friendly error messages and suggestions

**Usage:**
```kotlin
val dataValidationManager = DataValidationManager(context)
val validationResult = dataValidationManager.validateAndSanitize(parseResult, originalText)

if (validationResult.isValid) {
    // Use sanitized result for calendar creation
    val sanitizedResult = validationResult.sanitizedResult
} else {
    // Handle validation errors
    val issues = validationResult.issues
    val suggestions = validationResult.suggestions
}
```

### 2. DataSanitizer
**File:** `DataSanitizer.kt`

Utility class providing specialized sanitization methods for different data types.

**Key Features:**
- HTML tag and script removal
- Control character filtering
- Whitespace normalization
- Safe character validation

**Usage:**
```kotlin
val cleanTitle = DataSanitizer.sanitizeTitle(dirtyTitle)
val cleanLocation = DataSanitizer.sanitizeLocation(dirtyLocation)
val cleanDescription = DataSanitizer.sanitizeDescription(dirtyDescription)
```

### 3. ValidationConfig
**File:** `ValidationConfig.kt`

Configuration manager for customizing validation behavior and thresholds.

**Configurable Settings:**
- Confidence thresholds (min: 0.3, warning: 0.6)
- Field length limits (title: 200, description: 5000, location: 500)
- Duration limits (min: 1 minute, max: 1 week)
- Validation behavior flags

**Usage:**
```kotlin
val config = ValidationConfig(context)
config.minConfidenceThreshold = 0.4
config.enableStrictValidation = true
```

### 4. ValidationIntegration
**File:** `ValidationIntegration.kt`

Integration layer connecting validation with the existing error handling system.

**Key Features:**
- Seamless integration with ErrorHandlingManager
- Automatic error recovery through validation
- User confirmation requirements assessment
- Quick validation for UI feedback

**Usage:**
```kotlin
val integration = ValidationIntegration(context, errorHandlingManager)
val result = integration.validateWithErrorHandling(parseResult, originalText)

// Quick validation for UI
val quickResult = integration.validateQuick(parseResult)
```

## Validation Process

### 1. Title Validation
- **Missing Title:** Generates meaningful title from original text
- **Invalid Characters:** Removes control characters and HTML tags
- **Length Limits:** Truncates if too long, generates default if too short
- **Quality Assessment:** Checks for generic or incomplete titles

### 2. Date/Time Validation
- **Missing DateTime:** Generates default start time (next hour) and duration
- **Invalid Format:** Attempts format conversion, falls back to defaults
- **Time Sequence:** Ensures end time is after start time
- **Duration Reasonableness:** Validates duration is within acceptable range

### 3. Location Validation
- **Sanitization:** Removes invalid characters and normalizes whitespace
- **Length Limits:** Truncates if exceeds maximum length
- **Optional Field:** Allows null/empty values

### 4. Description Validation
- **Default Generation:** Creates description from original text if missing
- **Sanitization:** Removes dangerous content while preserving formatting
- **Length Limits:** Truncates if too long

### 5. Confidence Assessment
- **Overall Confidence:** Validates confidence scores are in valid range (0.0-1.0)
- **Field Confidence:** Checks individual field confidence scores
- **Low Confidence Warnings:** Generates warnings for scores below thresholds
- **Recommendations:** Provides actionable suggestions for improvement

## Error Handling Integration

The validation system integrates seamlessly with the existing ErrorHandlingManager:

### Error Type Mapping
- **INSUFFICIENT_DATA:** Missing essential fields (title, start time)
- **VALIDATION_ERROR:** Invalid data formats or constraint violations
- **LOW_CONFIDENCE:** Confidence scores below minimum threshold

### Recovery Strategies
- **GRACEFUL_DEGRADATION:** Apply sanitization and smart defaults
- **FALLBACK_EVENT_CREATION:** Generate fallback event with available data
- **USER_CONFIRMATION_REQUIRED:** Request user review for low confidence

## Smart Defaults

### Title Generation
1. Extract first meaningful sentence from original text
2. Remove common prefixes ("We will", "I need to")
3. Limit to 50 characters with ellipsis if needed
4. Fallback to "Calendar Event" if no meaningful content

### Date/Time Generation
1. **Start Time:** Next hour on the hour (e.g., if 2:30 PM, default to 3:00 PM)
2. **End Time:** Start time + default duration (60 minutes)
3. **Context Awareness:** Adjust based on keywords (morning → 9 AM, evening → 7 PM)

### Duration Estimation
1. **Explicit Duration:** Parse "2 hours", "30 minutes" from text
2. **Event Type:** Meeting (60 min), Appointment (30 min), Conference (8 hours)
3. **Time of Day:** Breakfast (30 min), Lunch (60 min), Dinner (90 min)

## Configuration Options

### Confidence Thresholds
- **minConfidenceThreshold (0.3):** Minimum acceptable confidence
- **warningConfidenceThreshold (0.6):** Threshold for showing warnings

### Length Limits
- **maxTitleLength (200):** Maximum title length
- **maxDescriptionLength (5000):** Maximum description length
- **maxLocationLength (500):** Maximum location length

### Duration Limits
- **minDurationMinutes (1):** Minimum event duration
- **maxDurationMinutes (10080):** Maximum event duration (1 week)

### Behavior Flags
- **enableStrictValidation (false):** Enable stricter validation rules
- **enableAutoSanitization (true):** Automatically sanitize input data
- **enableSmartDefaults (true):** Apply intelligent defaults for missing data

## Usage Examples

### Basic Validation
```kotlin
val dataValidationManager = DataValidationManager(context)
val result = dataValidationManager.validateAndSanitize(parseResult, originalText)

if (result.isValid) {
    // Create calendar event with sanitized data
    createCalendarEvent(result.sanitizedResult)
} else {
    // Show validation errors to user
    showValidationErrors(result.issues, result.suggestions)
}
```

### Integration with Error Handling
```kotlin
val integration = ValidationIntegration(context, errorHandlingManager)
val errorResult = integration.validateWithErrorHandling(parseResult, originalText)

when {
    errorResult.success -> {
        // Validation passed, use recovered result
        createCalendarEvent(errorResult.recoveredResult!!)
    }
    errorResult.actionRequired != null -> {
        // User action required
        handleUserAction(errorResult.actionRequired, errorResult.userMessage)
    }
    else -> {
        // Show error message
        showError(errorResult.userMessage)
    }
}
```

### Real-time UI Feedback
```kotlin
val quickResult = integration.validateQuick(parseResult)

when (quickResult.confidenceLevel) {
    ConfidenceLevel.HIGH -> showGreenIndicator()
    ConfidenceLevel.MEDIUM -> showYellowIndicator()
    ConfidenceLevel.LOW -> showRedIndicator()
}

createButton.isEnabled = quickResult.readyForCreation
```

## Testing

### Unit Tests
**File:** `DataValidationTest.kt`

Comprehensive unit tests covering:
- Valid data validation
- Missing field handling
- Invalid format sanitization
- Confidence assessment
- Configuration management
- Data integrity scoring

### Demo Class
**File:** `DataValidationDemo.kt`

Interactive demonstration of validation capabilities:
- Valid data with minor issues
- Missing essential fields
- Invalid data formats
- Low confidence handling
- Data sanitization examples
- Smart defaults application
- Error handling integration

## Requirements Fulfilled

This implementation addresses all requirements from the specification:

### Requirement 5.1: Essential Event Data Validation
✅ Validates title and start date/time as minimum required fields
✅ Provides specific error messages for missing essential data

### Requirement 5.2: Safe Defaults for Invalid Data
✅ Applies safe defaults rather than failing validation
✅ Uses intelligent defaults based on context and original text

### Requirement 5.3: Validation Error Handling with User Feedback
✅ Provides specific error messages indicating what needs fixing
✅ Offers actionable suggestions for improvement

### Requirement 5.4: Safe Default Application for Missing Fields
✅ Warns users about missing information before proceeding
✅ Generates meaningful defaults from available context

### Requirement 12.1: Smart Time Defaults
✅ Suggests next reasonable time slot (top of next hour)
✅ Considers context keywords for time selection

### Requirement 12.2: Smart Date Defaults
✅ Defaults to nearest future occurrence for ambiguous dates
✅ Uses "today", "tomorrow", weekday keywords for date selection

### Requirement 12.3: Smart Duration Defaults
✅ Defaults based on event type (meeting: 60min, appointment: 30min)
✅ Uses time of day context for duration estimation

### Requirement 12.4: Clear Default Marking
✅ Clearly marks suggestions as modifiable defaults
✅ Provides transparency about applied defaults in validation results

## Integration Points

### With ErrorHandlingManager
- Automatic error type detection from validation results
- Seamless recovery strategy selection
- Enhanced error messages with validation details

### With FallbackEventGenerator
- Validation of fallback-generated events
- Quality assessment of generated content
- Confidence scoring for fallback results

### With ConfidenceValidator
- Integration of confidence thresholds
- Field-level confidence assessment
- User recommendation generation

### With UserFeedbackManager
- Validation result presentation
- User-friendly error messages
- Actionable improvement suggestions

This comprehensive validation system ensures that calendar events are created with high-quality, sanitized data while providing excellent user feedback and recovery mechanisms for various error scenarios.