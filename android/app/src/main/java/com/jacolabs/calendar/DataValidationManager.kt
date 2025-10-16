package com.jacolabs.calendar

import android.content.Context
import android.util.Log
import java.text.SimpleDateFormat
import java.util.*
import java.util.regex.Pattern
import kotlin.math.max
import kotlin.math.min

/**
 * Comprehensive data validation and sanitization layer for calendar event data.
 * Ensures data integrity before calendar creation and provides user-friendly feedback.
 * 
 * Implements requirements 5.1-5.4 and 12.1-12.4 for essential data validation,
 * sanitization, error handling, and safe defaults.
 */
class DataValidationManager(private val context: Context) {
    
    companion object {
        private const val TAG = "DataValidationManager"
        
        // Validation constants
        private const val MIN_TITLE_LENGTH = 1
        private const val MAX_TITLE_LENGTH = 200
        private const val MIN_DESCRIPTION_LENGTH = 0
        private const val MAX_DESCRIPTION_LENGTH = 5000
        private const val MIN_LOCATION_LENGTH = 0
        private const val MAX_LOCATION_LENGTH = 500
        private const val MIN_DURATION_MINUTES = 1
        private const val MAX_DURATION_MINUTES = 10080 // 1 week
        private const val DEFAULT_DURATION_MINUTES = 60
        
        // Date/time validation patterns
        private val ISO_DATETIME_PATTERN = Pattern.compile(
            "^\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}(?:\\.\\d{3})?(?:Z|[+-]\\d{2}:\\d{2})$"
        )
        
        // Title sanitization patterns
        private val INVALID_TITLE_CHARS = Pattern.compile("[\\x00-\\x1F\\x7F]") // Control characters
        private val EXCESSIVE_WHITESPACE = Pattern.compile("\\s{2,}")
        private val LEADING_TRAILING_PUNCTUATION = Pattern.compile("^[.,:;!?\\s]+|[.,:;!?\\s]+$")
        
        // Location sanitization patterns
        private val INVALID_LOCATION_CHARS = Pattern.compile("[\\x00-\\x1F\\x7F]")
        
        // Description sanitization patterns
        private val INVALID_DESCRIPTION_CHARS = Pattern.compile("[\\x00-\\x08\\x0B\\x0C\\x0E-\\x1F\\x7F]")
        
        // Safe default values
        private const val DEFAULT_TITLE = "Calendar Event"
        private const val DEFAULT_DESCRIPTION = "Event created from text input"
        
        // Confidence thresholds for validation warnings
        private const val LOW_CONFIDENCE_THRESHOLD = 0.3
        private const val MEDIUM_CONFIDENCE_THRESHOLD = 0.6
        private const val HIGH_CONFIDENCE_THRESHOLD = 0.8
    }
    
    /**
     * Validation severity levels
     */
    enum class ValidationSeverity {
        ERROR,      // Prevents event creation
        WARNING,    // Allows creation but shows warning
        INFO        // Informational message
    }
    
    /**
     * Validation issue with details and suggestions
     */
    data class ValidationIssue(
        val field: String,
        val severity: ValidationSeverity,
        val code: String,
        val message: String,
        val suggestion: String? = null,
        val originalValue: Any? = null,
        val sanitizedValue: Any? = null
    )
    
    /**
     * Comprehensive validation result with detailed feedback
     */
    data class ValidationResult(
        val isValid: Boolean,
        val sanitizedResult: ParseResult,
        val issues: List<ValidationIssue> = emptyList(),
        val warnings: List<String> = emptyList(),
        val suggestions: List<String> = emptyList(),
        val confidenceAssessment: ConfidenceAssessment,
        val appliedDefaults: Map<String, String> = emptyMap(),
        val dataIntegrityScore: Double = 1.0
    )
    
    /**
     * Confidence assessment for validation decisions
     */
    data class ConfidenceAssessment(
        val overallConfidence: Double,
        val fieldConfidences: Map<String, Double>,
        val confidenceWarnings: List<String>,
        val recommendedActions: List<String>
    )
    
    /**
     * Main validation entry point - validates and sanitizes ParseResult
     */
    fun validateAndSanitize(result: ParseResult, originalText: String): ValidationResult {
        Log.d(TAG, "Starting validation for ParseResult with confidence: ${result.confidenceScore}")
        
        val issues = mutableListOf<ValidationIssue>()
        val warnings = mutableListOf<String>()
        val suggestions = mutableListOf<String>()
        val appliedDefaults = mutableMapOf<String, String>()
        
        // Create mutable copy for sanitization
        var sanitizedResult = result.copy()
        
        // 1. Validate and sanitize title
        val titleValidation = validateAndSanitizeTitle(sanitizedResult.title, originalText)
        sanitizedResult = sanitizedResult.copy(title = titleValidation.sanitizedValue)
        issues.addAll(titleValidation.issues)
        appliedDefaults.putAll(titleValidation.appliedDefaults)
        
        // 2. Validate and sanitize date/time
        val dateTimeValidation = validateAndSanitizeDateTime(
            sanitizedResult.startDateTime,
            sanitizedResult.endDateTime,
            sanitizedResult.allDay
        )
        sanitizedResult = sanitizedResult.copy(
            startDateTime = dateTimeValidation.startDateTime,
            endDateTime = dateTimeValidation.endDateTime,
            allDay = dateTimeValidation.allDay
        )
        issues.addAll(dateTimeValidation.issues)
        appliedDefaults.putAll(dateTimeValidation.appliedDefaults)
        
        // 3. Validate and sanitize location
        val locationValidation = validateAndSanitizeLocation(sanitizedResult.location)
        sanitizedResult = sanitizedResult.copy(location = locationValidation.sanitizedValue)
        issues.addAll(locationValidation.issues)
        
        // 4. Validate and sanitize description
        val descriptionValidation = validateAndSanitizeDescription(sanitizedResult.description, originalText)
        sanitizedResult = sanitizedResult.copy(description = descriptionValidation.sanitizedValue)
        issues.addAll(descriptionValidation.issues)
        
        // 5. Validate confidence scores and field results
        val confidenceValidation = validateConfidenceData(sanitizedResult)
        issues.addAll(confidenceValidation.issues)
        
        // 6. Perform data integrity checks
        val integrityValidation = performDataIntegrityChecks(sanitizedResult, originalText)
        issues.addAll(integrityValidation.issues)
        warnings.addAll(integrityValidation.warnings)
        suggestions.addAll(integrityValidation.suggestions)
        
        // 7. Generate confidence assessment
        val confidenceAssessment = generateConfidenceAssessment(sanitizedResult, issues)
        
        // 8. Calculate overall data integrity score
        val dataIntegrityScore = calculateDataIntegrityScore(sanitizedResult, issues)
        
        // 9. Generate user-friendly warnings and suggestions
        val userWarnings = generateUserWarnings(issues, confidenceAssessment)
        val userSuggestions = generateUserSuggestions(issues, confidenceAssessment, originalText)
        
        // 10. Determine if validation passed
        val isValid = !issues.any { it.severity == ValidationSeverity.ERROR }
        
        Log.d(TAG, "Validation completed. Valid: $isValid, Issues: ${issues.size}, Integrity Score: $dataIntegrityScore")
        
        return ValidationResult(
            isValid = isValid,
            sanitizedResult = sanitizedResult,
            issues = issues,
            warnings = warnings + userWarnings,
            suggestions = suggestions + userSuggestions,
            confidenceAssessment = confidenceAssessment,
            appliedDefaults = appliedDefaults,
            dataIntegrityScore = dataIntegrityScore
        )
    }
    
    /**
     * Title validation and sanitization result
     */
    private data class TitleValidationResult(
        val sanitizedValue: String,
        val issues: List<ValidationIssue>,
        val appliedDefaults: Map<String, String>
    )
    
    /**
     * Validates and sanitizes event title
     */
    private fun validateAndSanitizeTitle(title: String?, originalText: String): TitleValidationResult {
        val issues = mutableListOf<ValidationIssue>()
        val appliedDefaults = mutableMapOf<String, String>()
        
        // Handle null or empty title
        if (title.isNullOrBlank()) {
            val defaultTitle = generateDefaultTitle(originalText)
            appliedDefaults["title"] = defaultTitle
            
            issues.add(ValidationIssue(
                field = "title",
                severity = ValidationSeverity.WARNING,
                code = "TITLE_MISSING",
                message = "Event title was missing and has been generated from the text",
                suggestion = "Review the generated title and edit if needed",
                originalValue = title,
                sanitizedValue = defaultTitle
            ))
            
            return TitleValidationResult(defaultTitle, issues, appliedDefaults)
        }
        
        var sanitizedTitle = title
        
        // Remove invalid characters
        val originalLength = sanitizedTitle.length
        sanitizedTitle = INVALID_TITLE_CHARS.matcher(sanitizedTitle).replaceAll("")
        
        if (sanitizedTitle.length != originalLength) {
            issues.add(ValidationIssue(
                field = "title",
                severity = ValidationSeverity.INFO,
                code = "TITLE_CHARS_REMOVED",
                message = "Invalid characters were removed from the title",
                originalValue = title,
                sanitizedValue = sanitizedTitle
            ))
        }
        
        // Normalize whitespace
        sanitizedTitle = EXCESSIVE_WHITESPACE.matcher(sanitizedTitle).replaceAll(" ")
        sanitizedTitle = LEADING_TRAILING_PUNCTUATION.matcher(sanitizedTitle).replaceAll("")
        sanitizedTitle = sanitizedTitle.trim()
        
        // Check length constraints
        if (sanitizedTitle.length < MIN_TITLE_LENGTH) {
            val defaultTitle = generateDefaultTitle(originalText)
            appliedDefaults["title"] = defaultTitle
            
            issues.add(ValidationIssue(
                field = "title",
                severity = ValidationSeverity.WARNING,
                code = "TITLE_TOO_SHORT",
                message = "Title was too short and has been replaced with a default",
                suggestion = "Provide a more descriptive title",
                originalValue = title,
                sanitizedValue = defaultTitle
            ))
            
            return TitleValidationResult(defaultTitle, issues, appliedDefaults)
        }
        
        if (sanitizedTitle.length > MAX_TITLE_LENGTH) {
            sanitizedTitle = sanitizedTitle.substring(0, MAX_TITLE_LENGTH - 3) + "..."
            
            issues.add(ValidationIssue(
                field = "title",
                severity = ValidationSeverity.WARNING,
                code = "TITLE_TRUNCATED",
                message = "Title was too long and has been truncated",
                suggestion = "Consider using a shorter, more concise title",
                originalValue = title,
                sanitizedValue = sanitizedTitle
            ))
        }
        
        // Check title quality
        val qualityIssues = assessTitleQuality(sanitizedTitle, originalText)
        issues.addAll(qualityIssues)
        
        return TitleValidationResult(sanitizedTitle, issues, appliedDefaults)
    }
    
    /**
     * Generates a default title from original text
     */
    private fun generateDefaultTitle(originalText: String): String {
        if (originalText.isBlank()) return DEFAULT_TITLE
        
        // Try to extract a meaningful title from the text
        val sentences = originalText.split(Regex("[.!?]"))
        val firstSentence = sentences.firstOrNull()?.trim()
        
        if (!firstSentence.isNullOrBlank() && firstSentence.length <= 50) {
            return firstSentence
        }
        
        // Take first 50 characters
        val truncated = if (originalText.length > 50) {
            originalText.substring(0, 47) + "..."
        } else {
            originalText
        }
        
        return truncated.ifBlank { DEFAULT_TITLE }
    }
    
    /**
     * Assesses title quality and generates improvement suggestions
     */
    private fun assessTitleQuality(title: String, originalText: String): List<ValidationIssue> {
        val issues = mutableListOf<ValidationIssue>()
        
        // Check for very generic titles
        val genericTitles = setOf("event", "meeting", "appointment", "reminder", "task")
        if (genericTitles.contains(title.lowercase().trim())) {
            issues.add(ValidationIssue(
                field = "title",
                severity = ValidationSeverity.INFO,
                code = "TITLE_GENERIC",
                message = "Title is very generic",
                suggestion = "Consider adding more specific details about the event"
            ))
        }
        
        // Check for incomplete titles
        if (title.endsWith("...") || title.endsWith(" and") || title.endsWith(" or")) {
            issues.add(ValidationIssue(
                field = "title",
                severity = ValidationSeverity.WARNING,
                code = "TITLE_INCOMPLETE",
                message = "Title appears to be incomplete",
                suggestion = "Complete the title with specific event details"
            ))
        }
        
        // Check title length vs original text (compression ratio)
        val compressionRatio = title.length.toDouble() / originalText.length
        if (compressionRatio > 0.8 && originalText.length > 100) {
            issues.add(ValidationIssue(
                field = "title",
                severity = ValidationSeverity.INFO,
                code = "TITLE_NOT_EXTRACTED",
                message = "Title appears to be the entire input text",
                suggestion = "Try rephrasing with a clear event name at the beginning"
            ))
        }
        
        return issues
    }
    
    /**
     * Date/time validation result
     */
    private data class DateTimeValidationResult(
        val startDateTime: String,
        val endDateTime: String,
        val allDay: Boolean,
        val issues: List<ValidationIssue>,
        val appliedDefaults: Map<String, String>
    )
    
    /**
     * Validates and sanitizes date/time fields
     */
    private fun validateAndSanitizeDateTime(
        startDateTime: String?,
        endDateTime: String?,
        allDay: Boolean
    ): DateTimeValidationResult {
        val issues = mutableListOf<ValidationIssue>()
        val appliedDefaults = mutableMapOf<String, String>()
        
        // Handle missing start date/time
        if (startDateTime.isNullOrBlank()) {
            val defaultStart = generateDefaultStartDateTime()
            val defaultEnd = generateDefaultEndDateTime(defaultStart, DEFAULT_DURATION_MINUTES)
            
            appliedDefaults["startDateTime"] = defaultStart
            appliedDefaults["endDateTime"] = defaultEnd
            
            issues.add(ValidationIssue(
                field = "startDateTime",
                severity = ValidationSeverity.WARNING,
                code = "START_TIME_MISSING",
                message = "Start date/time was missing and has been set to a default",
                suggestion = "Specify a clear date and time in your text",
                originalValue = startDateTime,
                sanitizedValue = defaultStart
            ))
            
            return DateTimeValidationResult(defaultStart, defaultEnd, allDay, issues, appliedDefaults)
        }
        
        // Validate start date/time format
        val validatedStart = validateDateTimeFormat(startDateTime)
        if (validatedStart.isValid) {
            var finalStartDateTime = validatedStart.sanitizedValue
            var finalEndDateTime = endDateTime
            
            // Handle missing or invalid end date/time
            if (endDateTime.isNullOrBlank()) {
                finalEndDateTime = generateDefaultEndDateTime(finalStartDateTime, DEFAULT_DURATION_MINUTES)
                appliedDefaults["endDateTime"] = finalEndDateTime
                
                issues.add(ValidationIssue(
                    field = "endDateTime",
                    severity = ValidationSeverity.INFO,
                    code = "END_TIME_GENERATED",
                    message = "End time was generated based on default duration",
                    suggestion = "Specify event duration in your text for more accuracy",
                    originalValue = endDateTime,
                    sanitizedValue = finalEndDateTime
                ))
            } else {
                val validatedEnd = validateDateTimeFormat(endDateTime)
                if (validatedEnd.isValid) {
                    finalEndDateTime = validatedEnd.sanitizedValue
                    
                    // Validate time sequence
                    val sequenceValidation = validateTimeSequence(finalStartDateTime, finalEndDateTime)
                    if (!sequenceValidation.isValid) {
                        finalEndDateTime = generateDefaultEndDateTime(finalStartDateTime, DEFAULT_DURATION_MINUTES)
                        appliedDefaults["endDateTime"] = finalEndDateTime
                        
                        issues.add(ValidationIssue(
                            field = "endDateTime",
                            severity = ValidationSeverity.WARNING,
                            code = "INVALID_TIME_SEQUENCE",
                            message = "End time was before start time and has been corrected",
                            suggestion = "Ensure end time is after start time",
                            originalValue = endDateTime,
                            sanitizedValue = finalEndDateTime
                        ))
                    }
                } else {
                    finalEndDateTime = generateDefaultEndDateTime(finalStartDateTime, DEFAULT_DURATION_MINUTES)
                    appliedDefaults["endDateTime"] = finalEndDateTime
                    
                    issues.add(ValidationIssue(
                        field = "endDateTime",
                        severity = ValidationSeverity.WARNING,
                        code = "END_TIME_INVALID_FORMAT",
                        message = "End time format was invalid and has been regenerated",
                        suggestion = "Use clear time formats like '2:00 PM' or '14:00'",
                        originalValue = endDateTime,
                        sanitizedValue = finalEndDateTime
                    ))
                }
            }
            
            // Validate duration reasonableness
            val durationValidation = validateDuration(finalStartDateTime, finalEndDateTime)
            issues.addAll(durationValidation.issues)
            
            return DateTimeValidationResult(finalStartDateTime, finalEndDateTime, allDay, issues, appliedDefaults)
            
        } else {
            // Invalid start date/time format
            val defaultStart = generateDefaultStartDateTime()
            val defaultEnd = generateDefaultEndDateTime(defaultStart, DEFAULT_DURATION_MINUTES)
            
            appliedDefaults["startDateTime"] = defaultStart
            appliedDefaults["endDateTime"] = defaultEnd
            
            issues.add(ValidationIssue(
                field = "startDateTime",
                severity = ValidationSeverity.ERROR,
                code = "START_TIME_INVALID_FORMAT",
                message = "Start date/time format was invalid and has been set to default",
                suggestion = "Use clear date and time formats in your text",
                originalValue = startDateTime,
                sanitizedValue = defaultStart
            ))
            
            return DateTimeValidationResult(defaultStart, defaultEnd, allDay, issues, appliedDefaults)
        }
    }
    
    /**
     * Date/time format validation result
     */
    private data class DateTimeFormatValidation(
        val isValid: Boolean,
        val sanitizedValue: String,
        val issues: List<ValidationIssue> = emptyList()
    )
    
    /**
     * Validates and sanitizes date/time format
     */
    private fun validateDateTimeFormat(dateTime: String): DateTimeFormatValidation {
        val issues = mutableListOf<ValidationIssue>()
        
        // Check if it matches ISO format
        if (ISO_DATETIME_PATTERN.matcher(dateTime).matches()) {
            try {
                // Try to parse to ensure it's a valid date
                val formatter = SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ssXXX", Locale.getDefault())
                formatter.parse(dateTime)
                return DateTimeFormatValidation(true, dateTime)
            } catch (e: Exception) {
                Log.w(TAG, "Failed to parse ISO datetime: $dateTime", e)
            }
        }
        
        // Try alternative formats and convert to ISO
        val alternativeFormats = listOf(
            "yyyy-MM-dd HH:mm:ss",
            "yyyy-MM-dd HH:mm",
            "MM/dd/yyyy HH:mm:ss",
            "MM/dd/yyyy HH:mm",
            "dd/MM/yyyy HH:mm:ss",
            "dd/MM/yyyy HH:mm"
        )
        
        for (format in alternativeFormats) {
            try {
                val parser = SimpleDateFormat(format, Locale.getDefault())
                val date = parser.parse(dateTime)
                val isoFormatter = SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ssXXX", Locale.getDefault())
                val isoDateTime = isoFormatter.format(date)
                
                issues.add(ValidationIssue(
                    field = "dateTime",
                    severity = ValidationSeverity.INFO,
                    code = "DATETIME_FORMAT_CONVERTED",
                    message = "Date/time format was converted to standard format",
                    originalValue = dateTime,
                    sanitizedValue = isoDateTime
                ))
                
                return DateTimeFormatValidation(true, isoDateTime, issues)
            } catch (e: Exception) {
                // Continue to next format
            }
        }
        
        return DateTimeFormatValidation(false, dateTime, issues)
    }
    
    /**
     * Time sequence validation result
     */
    private data class TimeSequenceValidation(
        val isValid: Boolean,
        val issues: List<ValidationIssue> = emptyList()
    )
    
    /**
     * Validates that end time is after start time
     */
    private fun validateTimeSequence(startDateTime: String, endDateTime: String): TimeSequenceValidation {
        return try {
            val formatter = SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ssXXX", Locale.getDefault())
            val startDate = formatter.parse(startDateTime)
            val endDate = formatter.parse(endDateTime)
            
            if (endDate.after(startDate)) {
                TimeSequenceValidation(true)
            } else {
                TimeSequenceValidation(false, listOf(
                    ValidationIssue(
                        field = "timeSequence",
                        severity = ValidationSeverity.ERROR,
                        code = "END_BEFORE_START",
                        message = "End time is before or equal to start time"
                    )
                ))
            }
        } catch (e: Exception) {
            Log.w(TAG, "Failed to validate time sequence", e)
            TimeSequenceValidation(false, listOf(
                ValidationIssue(
                    field = "timeSequence",
                    severity = ValidationSeverity.ERROR,
                    code = "TIME_PARSE_ERROR",
                    message = "Could not parse date/time for sequence validation"
                )
            ))
        }
    }
    
    /**
     * Duration validation result
     */
    private data class DurationValidationResult(
        val issues: List<ValidationIssue>
    )
    
    /**
     * Validates event duration reasonableness
     */
    private fun validateDuration(startDateTime: String, endDateTime: String): DurationValidationResult {
        val issues = mutableListOf<ValidationIssue>()
        
        try {
            val formatter = SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ssXXX", Locale.getDefault())
            val startDate = formatter.parse(startDateTime)
            val endDate = formatter.parse(endDateTime)
            
            val durationMs = endDate.time - startDate.time
            val durationMinutes = (durationMs / (1000 * 60)).toInt()
            
            when {
                durationMinutes < MIN_DURATION_MINUTES -> {
                    issues.add(ValidationIssue(
                        field = "duration",
                        severity = ValidationSeverity.WARNING,
                        code = "DURATION_TOO_SHORT",
                        message = "Event duration is very short (${durationMinutes} minutes)",
                        suggestion = "Consider if this is the correct duration for your event"
                    ))
                }
                durationMinutes > MAX_DURATION_MINUTES -> {
                    issues.add(ValidationIssue(
                        field = "duration",
                        severity = ValidationSeverity.WARNING,
                        code = "DURATION_TOO_LONG",
                        message = "Event duration is very long (${durationMinutes / 60} hours)",
                        suggestion = "Consider breaking this into multiple events or verify the duration"
                    ))
                }
                durationMinutes > 480 && durationMinutes <= 1440 -> { // 8-24 hours
                    issues.add(ValidationIssue(
                        field = "duration",
                        severity = ValidationSeverity.INFO,
                        code = "DURATION_LONG",
                        message = "Event duration is quite long (${durationMinutes / 60} hours)",
                        suggestion = "Verify this is correct or consider marking as all-day event"
                    ))
                }
            }
        } catch (e: Exception) {
            Log.w(TAG, "Failed to validate duration", e)
            issues.add(ValidationIssue(
                field = "duration",
                severity = ValidationSeverity.WARNING,
                code = "DURATION_VALIDATION_FAILED",
                message = "Could not validate event duration"
            ))
        }
        
        return DurationValidationResult(issues)
    }
    
    /**
     * Generates default start date/time (next hour)
     */
    private fun generateDefaultStartDateTime(): String {
        val calendar = Calendar.getInstance()
        calendar.add(Calendar.HOUR_OF_DAY, 1)
        calendar.set(Calendar.MINUTE, 0)
        calendar.set(Calendar.SECOND, 0)
        calendar.set(Calendar.MILLISECOND, 0)
        
        val formatter = SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ssXXX", Locale.getDefault())
        return formatter.format(calendar.time)
    }
    
    /**
     * Generates default end date/time based on start time and duration
     */
    private fun generateDefaultEndDateTime(startDateTime: String, durationMinutes: Int): String {
        return try {
            val formatter = SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ssXXX", Locale.getDefault())
            val startDate = formatter.parse(startDateTime)
            val calendar = Calendar.getInstance()
            calendar.time = startDate
            calendar.add(Calendar.MINUTE, durationMinutes)
            formatter.format(calendar.time)
        } catch (e: Exception) {
            Log.w(TAG, "Failed to generate default end time", e)
            startDateTime // Fallback to same as start
        }
    }
    
    /**
     * Field validation result for simple fields
     */
    private data class FieldValidationResult(
        val sanitizedValue: String?,
        val issues: List<ValidationIssue>
    )
    
    /**
     * Validates and sanitizes location field
     */
    private fun validateAndSanitizeLocation(location: String?): FieldValidationResult {
        val issues = mutableListOf<ValidationIssue>()
        
        if (location.isNullOrBlank()) {
            return FieldValidationResult(null, issues)
        }
        
        var sanitizedLocation = location
        
        // Remove invalid characters
        val originalLength = sanitizedLocation.length
        sanitizedLocation = INVALID_LOCATION_CHARS.matcher(sanitizedLocation).replaceAll("")
        
        if (sanitizedLocation.length != originalLength) {
            issues.add(ValidationIssue(
                field = "location",
                severity = ValidationSeverity.INFO,
                code = "LOCATION_CHARS_REMOVED",
                message = "Invalid characters were removed from location",
                originalValue = location,
                sanitizedValue = sanitizedLocation
            ))
        }
        
        // Normalize whitespace
        sanitizedLocation = EXCESSIVE_WHITESPACE.matcher(sanitizedLocation).replaceAll(" ")
        sanitizedLocation = sanitizedLocation.trim()
        
        // Check length constraints
        if (sanitizedLocation.length > MAX_LOCATION_LENGTH) {
            sanitizedLocation = sanitizedLocation.substring(0, MAX_LOCATION_LENGTH - 3) + "..."
            
            issues.add(ValidationIssue(
                field = "location",
                severity = ValidationSeverity.WARNING,
                code = "LOCATION_TRUNCATED",
                message = "Location was too long and has been truncated",
                suggestion = "Use a shorter location description",
                originalValue = location,
                sanitizedValue = sanitizedLocation
            ))
        }
        
        // Return null if location became empty after sanitization
        if (sanitizedLocation.isBlank()) {
            return FieldValidationResult(null, issues)
        }
        
        return FieldValidationResult(sanitizedLocation, issues)
    }
    
    /**
     * Validates and sanitizes description field
     */
    private fun validateAndSanitizeDescription(description: String?, originalText: String): FieldValidationResult {
        val issues = mutableListOf<ValidationIssue>()
        
        var sanitizedDescription = description ?: ""
        
        // If description is empty, generate a basic one
        if (sanitizedDescription.isBlank()) {
            sanitizedDescription = generateDefaultDescription(originalText)
        }
        
        // Remove invalid characters
        val originalLength = sanitizedDescription.length
        sanitizedDescription = INVALID_DESCRIPTION_CHARS.matcher(sanitizedDescription).replaceAll("")
        
        if (sanitizedDescription.length != originalLength) {
            issues.add(ValidationIssue(
                field = "description",
                severity = ValidationSeverity.INFO,
                code = "DESCRIPTION_CHARS_REMOVED",
                message = "Invalid characters were removed from description",
                originalValue = description,
                sanitizedValue = sanitizedDescription
            ))
        }
        
        // Normalize whitespace but preserve line breaks
        sanitizedDescription = sanitizedDescription.replace(Regex("[ \\t]+"), " ")
        sanitizedDescription = sanitizedDescription.replace(Regex("\\n{3,}"), "\n\n")
        sanitizedDescription = sanitizedDescription.trim()
        
        // Check length constraints
        if (sanitizedDescription.length > MAX_DESCRIPTION_LENGTH) {
            sanitizedDescription = sanitizedDescription.substring(0, MAX_DESCRIPTION_LENGTH - 3) + "..."
            
            issues.add(ValidationIssue(
                field = "description",
                severity = ValidationSeverity.WARNING,
                code = "DESCRIPTION_TRUNCATED",
                message = "Description was too long and has been truncated",
                suggestion = "Use a more concise description",
                originalValue = description,
                sanitizedValue = sanitizedDescription
            ))
        }
        
        return FieldValidationResult(sanitizedDescription, issues)
    }
    
    /**
     * Generates default description from original text
     */
    private fun generateDefaultDescription(originalText: String): String {
        if (originalText.isBlank()) return DEFAULT_DESCRIPTION
        
        return "Event created from: \"${originalText.take(200)}${if (originalText.length > 200) "..." else ""}\""
    }
    
    /**
     * Confidence validation result
     */
    private data class ConfidenceValidationResult(
        val issues: List<ValidationIssue>
    )
    
    /**
     * Validates confidence scores and field results
     */
    private fun validateConfidenceData(result: ParseResult): ConfidenceValidationResult {
        val issues = mutableListOf<ValidationIssue>()
        
        // Validate overall confidence score
        if (result.confidenceScore < 0.0 || result.confidenceScore > 1.0) {
            issues.add(ValidationIssue(
                field = "confidenceScore",
                severity = ValidationSeverity.WARNING,
                code = "INVALID_CONFIDENCE_RANGE",
                message = "Confidence score is outside valid range (0.0-1.0): ${result.confidenceScore}",
                suggestion = "Confidence scores should be between 0.0 and 1.0"
            ))
        }
        
        // Validate field results if present
        result.fieldResults?.forEach { (fieldName, fieldResult) ->
            if (fieldResult.confidence < 0.0 || fieldResult.confidence > 1.0) {
                issues.add(ValidationIssue(
                    field = fieldName,
                    severity = ValidationSeverity.WARNING,
                    code = "INVALID_FIELD_CONFIDENCE",
                    message = "Field confidence score is outside valid range: ${fieldResult.confidence}",
                    suggestion = "Field confidence scores should be between 0.0 and 1.0"
                ))
            }
        }
        
        // Check for low confidence warnings
        if (result.confidenceScore < LOW_CONFIDENCE_THRESHOLD) {
            issues.add(ValidationIssue(
                field = "confidenceScore",
                severity = ValidationSeverity.WARNING,
                code = "LOW_OVERALL_CONFIDENCE",
                message = "Overall confidence is low (${result.confidenceScore})",
                suggestion = "Review the extracted information carefully before creating the event"
            ))
        }
        
        return ConfidenceValidationResult(issues)
    }
    
    /**
     * Data integrity validation result
     */
    private data class DataIntegrityValidationResult(
        val issues: List<ValidationIssue>,
        val warnings: List<String>,
        val suggestions: List<String>
    )
    
    /**
     * Performs comprehensive data integrity checks
     */
    private fun performDataIntegrityChecks(result: ParseResult, originalText: String): DataIntegrityValidationResult {
        val issues = mutableListOf<ValidationIssue>()
        val warnings = mutableListOf<String>()
        val suggestions = mutableListOf<String>()
        
        // Check for essential data completeness
        if (result.title.isNullOrBlank()) {
            issues.add(ValidationIssue(
                field = "completeness",
                severity = ValidationSeverity.ERROR,
                code = "MISSING_ESSENTIAL_TITLE",
                message = "Event must have a title"
            ))
        }
        
        if (result.startDateTime.isNullOrBlank()) {
            issues.add(ValidationIssue(
                field = "completeness",
                severity = ValidationSeverity.ERROR,
                code = "MISSING_ESSENTIAL_START_TIME",
                message = "Event must have a start date/time"
            ))
        }
        
        // Check for data consistency
        if (!result.title.isNullOrBlank() && !originalText.isBlank()) {
            val titleWords = result.title.lowercase().split("\\s+".toRegex())
            val textWords = originalText.lowercase().split("\\s+".toRegex())
            val commonWords = titleWords.intersect(textWords.toSet())
            
            if (commonWords.isEmpty() && titleWords.size > 1) {
                warnings.add("The generated title doesn't seem to match the original text")
                suggestions.add("Review the title to ensure it accurately represents your event")
            }
        }
        
        // Check for reasonable date/time
        if (!result.startDateTime.isNullOrBlank()) {
            try {
                val formatter = SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ssXXX", Locale.getDefault())
                val startDate = formatter.parse(result.startDateTime)
                val now = Date()
                val oneYearFromNow = Calendar.getInstance().apply { add(Calendar.YEAR, 1) }.time
                
                if (startDate.before(Date(now.time - 24 * 60 * 60 * 1000))) { // More than 1 day ago
                    warnings.add("Event is scheduled for the past")
                    suggestions.add("Verify the date is correct or specify 'next' for future occurrences")
                }
                
                if (startDate.after(oneYearFromNow)) {
                    warnings.add("Event is scheduled more than a year in the future")
                    suggestions.add("Verify the year is correct")
                }
            } catch (e: Exception) {
                Log.w(TAG, "Failed to check date reasonableness", e)
            }
        }
        
        // Check for missing context
        if (originalText.length < 10) {
            warnings.add("Input text is very short - more details could improve accuracy")
            suggestions.add("Provide more context like date, time, and event details")
        }
        
        return DataIntegrityValidationResult(issues, warnings, suggestions)
    }
    
    /**
     * Generates comprehensive confidence assessment
     */
    private fun generateConfidenceAssessment(result: ParseResult, issues: List<ValidationIssue>): ConfidenceAssessment {
        val fieldConfidences = mutableMapOf<String, Double>()
        val confidenceWarnings = mutableListOf<String>()
        val recommendedActions = mutableListOf<String>()
        
        // Extract field confidences
        result.fieldResults?.forEach { (fieldName, fieldResult) ->
            fieldConfidences[fieldName] = fieldResult.confidence
        }
        
        // Add overall confidence
        fieldConfidences["overall"] = result.confidenceScore
        
        // Generate confidence-based warnings
        fieldConfidences.forEach { (field, confidence) ->
            when {
                confidence < LOW_CONFIDENCE_THRESHOLD -> {
                    confidenceWarnings.add("Low confidence for $field (${String.format("%.1f", confidence * 100)}%)")
                    recommendedActions.add("Review and verify $field information")
                }
                confidence < MEDIUM_CONFIDENCE_THRESHOLD -> {
                    confidenceWarnings.add("Medium confidence for $field (${String.format("%.1f", confidence * 100)}%)")
                }
            }
        }
        
        // Add issue-based recommendations
        val errorCount = issues.count { it.severity == ValidationSeverity.ERROR }
        val warningCount = issues.count { it.severity == ValidationSeverity.WARNING }
        
        when {
            errorCount > 0 -> {
                recommendedActions.add("Fix critical issues before creating event")
            }
            warningCount > 2 -> {
                recommendedActions.add("Review warnings and consider improving input text")
            }
            result.confidenceScore < MEDIUM_CONFIDENCE_THRESHOLD -> {
                recommendedActions.add("Consider rephrasing input with clearer details")
            }
        }
        
        return ConfidenceAssessment(
            overallConfidence = result.confidenceScore,
            fieldConfidences = fieldConfidences,
            confidenceWarnings = confidenceWarnings,
            recommendedActions = recommendedActions
        )
    }
    
    /**
     * Calculates overall data integrity score
     */
    private fun calculateDataIntegrityScore(result: ParseResult, issues: List<ValidationIssue>): Double {
        var score = 1.0
        
        // Deduct points for issues
        issues.forEach { issue ->
            when (issue.severity) {
                ValidationSeverity.ERROR -> score -= 0.3
                ValidationSeverity.WARNING -> score -= 0.1
                ValidationSeverity.INFO -> score -= 0.02
            }
        }
        
        // Factor in confidence score
        score *= result.confidenceScore
        
        // Ensure score is within valid range
        return max(0.0, min(1.0, score))
    }
    
    /**
     * Generates user-friendly warnings from validation issues
     */
    private fun generateUserWarnings(issues: List<ValidationIssue>, confidenceAssessment: ConfidenceAssessment): List<String> {
        val warnings = mutableListOf<String>()
        
        // Add critical issues as warnings
        issues.filter { it.severity == ValidationSeverity.ERROR || it.severity == ValidationSeverity.WARNING }
            .forEach { issue ->
                warnings.add(issue.message)
            }
        
        // Add confidence warnings
        warnings.addAll(confidenceAssessment.confidenceWarnings)
        
        return warnings.distinct()
    }
    
    /**
     * Generates user-friendly suggestions from validation results
     */
    private fun generateUserSuggestions(
        issues: List<ValidationIssue>,
        confidenceAssessment: ConfidenceAssessment,
        originalText: String
    ): List<String> {
        val suggestions = mutableListOf<String>()
        
        // Add issue-specific suggestions
        issues.mapNotNull { it.suggestion }.forEach { suggestion ->
            suggestions.add(suggestion)
        }
        
        // Add confidence-based recommendations
        suggestions.addAll(confidenceAssessment.recommendedActions)
        
        // Add general improvement suggestions
        if (originalText.length < 20) {
            suggestions.add("Try providing more details like specific date, time, and event description")
        }
        
        if (confidenceAssessment.overallConfidence < MEDIUM_CONFIDENCE_THRESHOLD) {
            suggestions.add("For better accuracy, include clear date/time and event name in your text")
        }
        
        return suggestions.distinct()
    }
    
    /**
     * Quick validation for essential fields only
     */
    fun validateEssentialFields(result: ParseResult): Boolean {
        return !result.title.isNullOrBlank() && !result.startDateTime.isNullOrBlank()
    }
    
    /**
     * Gets validation summary for UI display
     */
    fun getValidationSummary(validationResult: ValidationResult): String {
        val errorCount = validationResult.issues.count { it.severity == ValidationSeverity.ERROR }
        val warningCount = validationResult.issues.count { it.severity == ValidationSeverity.WARNING }
        
        return when {
            errorCount > 0 -> "Validation failed with $errorCount critical issues"
            warningCount > 0 -> "Validation passed with $warningCount warnings"
            else -> "Validation passed successfully"
        }
    }
}