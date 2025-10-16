package com.jacolabs.calendar

import android.content.Context
import android.util.Log
import java.text.SimpleDateFormat
import java.util.*
import java.util.regex.Pattern
import kotlin.math.max
import kotlin.math.min

/**
 * Intelligent fallback event generator that creates meaningful calendar events
 * when text parsing fails or returns low-confidence results.
 * 
 * This component implements sophisticated text analysis and pattern matching
 * to extract the best possible event information from failed parsing attempts.
 */
class FallbackEventGenerator(private val context: Context) {
    
    companion object {
        private const val TAG = "FallbackEventGenerator"
        
        // Title extraction patterns (ordered by priority)
        private val TITLE_PATTERNS = listOf(
            // Pattern 1: "attend [EVENT] at [LOCATION]" -> "[EVENT] at [LOCATION]"
            Pattern.compile("attend\\s+(.+?)\\s+at\\s+(.+?)(?:\\.|$)", Pattern.CASE_INSENSITIVE),
            
            // Pattern 2: "On [day] the [people] will attend [EVENT]" -> "[EVENT] on [day]"
            Pattern.compile("^On\\s+(\\w+day)\\s+the\\s+.+?\\s+will\\s+attend\\s+(.+?)(?:\\s+at\\s+(.+?))?(?:\\.|$)", Pattern.CASE_INSENSITIVE),
            
            // Pattern 3: "On [day] the [people] will [action] the [EVENT]" -> "[EVENT] on [day]"
            Pattern.compile("^On\\s+(\\w+day)\\s+the\\s+.+?\\s+will\\s+\\w+\\s+the\\s+(.+?)(?:\\s+at\\s+(.+?))?(?:\\.|$)", Pattern.CASE_INSENSITIVE),
            
            // Pattern 4: "will attend [EVENT]" -> "[EVENT]"
            Pattern.compile("will\\s+attend\\s+(.+?)(?:\\s+at\\s+(.+?))?(?:\\.|$)", Pattern.CASE_INSENSITIVE),
            
            // Pattern 5: "[EVENT] on [day]" -> "[EVENT] on [day]"
            Pattern.compile("^(.+?)\\s+on\\s+(\\w+day)(?:\\.|$)", Pattern.CASE_INSENSITIVE),
            
            // Pattern 6: "[EVENT] at [time]" -> "[EVENT]"
            Pattern.compile("^(.+?)\\s+at\\s+\\d{1,2}(?::\\d{2})?\\s*(?:AM|PM|am|pm)?(?:\\.|$)", Pattern.CASE_INSENSITIVE),
            
            // Pattern 7: Meeting/appointment patterns
            Pattern.compile("(?:meeting|appointment|call)\\s+(?:with|about)\\s+(.+?)(?:\\.|$)", Pattern.CASE_INSENSITIVE),
            
            // Pattern 8: Simple event patterns
            Pattern.compile("^(.+?)\\s+(?:meeting|appointment|event|session)(?:\\.|$)", Pattern.CASE_INSENSITIVE)
        )
        
        // Common prefixes to remove from titles
        private val TITLE_PREFIXES_TO_REMOVE = listOf(
            "We will", "I will", "We need to", "I need to", "We should", "I should",
            "We must", "I must", "We have to", "I have to", "Let's", "Please",
            "On \\w+day the \\w+ will", "The \\w+ will", "The \\w+ should"
        )
        
        // Time-related keywords for context detection
        private val TIME_KEYWORDS = setOf(
            "morning", "afternoon", "evening", "night", "noon", "midnight",
            "am", "pm", "today", "tomorrow", "yesterday", "weekend",
            "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday",
            "week", "month", "year", "daily", "weekly", "monthly"
        )
        
        // Event type keywords for duration estimation
        private val EVENT_TYPE_DURATIONS = mapOf(
            "meeting" to 60,      // 1 hour
            "appointment" to 30,   // 30 minutes
            "call" to 30,         // 30 minutes
            "interview" to 60,    // 1 hour
            "presentation" to 60, // 1 hour
            "conference" to 480,  // 8 hours
            "workshop" to 240,    // 4 hours
            "training" to 240,    // 4 hours
            "seminar" to 120,     // 2 hours
            "class" to 90,        // 1.5 hours
            "lecture" to 90,      // 1.5 hours
            "exam" to 120,        // 2 hours
            "test" to 60,         // 1 hour
            "lunch" to 60,        // 1 hour
            "dinner" to 90,       // 1.5 hours
            "breakfast" to 30,    // 30 minutes
            "party" to 180,       // 3 hours
            "celebration" to 180, // 3 hours
            "wedding" to 360,     // 6 hours
            "funeral" to 120,     // 2 hours
            "concert" to 180,     // 3 hours
            "game" to 120,        // 2 hours
            "match" to 120,       // 2 hours
            "practice" to 90,     // 1.5 hours
            "rehearsal" to 120,   // 2 hours
            "checkup" to 30,      // 30 minutes
            "visit" to 60,        // 1 hour
            "trip" to 480,        // 8 hours (day trip)
            "vacation" to 10080   // 1 week
        )
        
        // Default durations by time of day
        private val DEFAULT_DURATIONS_BY_TIME = mapOf(
            6 to 30,   // 6 AM - breakfast
            7 to 30,   // 7 AM - breakfast
            8 to 60,   // 8 AM - morning meeting
            9 to 60,   // 9 AM - morning meeting
            10 to 60,  // 10 AM - meeting
            11 to 60,  // 11 AM - meeting
            12 to 60,  // 12 PM - lunch
            13 to 60,  // 1 PM - lunch/meeting
            14 to 60,  // 2 PM - afternoon meeting
            15 to 60,  // 3 PM - afternoon meeting
            16 to 60,  // 4 PM - meeting
            17 to 60,  // 5 PM - meeting
            18 to 90,  // 6 PM - dinner
            19 to 90,  // 7 PM - dinner/evening event
            20 to 120, // 8 PM - evening event
            21 to 120, // 9 PM - evening event
            22 to 60   // 10 PM - short evening event
        )
    }
    
    /**
     * Data class representing a fallback event with confidence and reasoning
     */
    data class FallbackEvent(
        val title: String,
        val startDateTime: String,
        val endDateTime: String,
        val description: String,
        val confidence: Double,
        val fallbackReason: String,
        val location: String? = null,
        val allDay: Boolean = false,
        val timezone: String = TimeZone.getDefault().id,
        val extractionDetails: ExtractionDetails
    )
    
    /**
     * Details about how the event was extracted and processed
     */
    data class ExtractionDetails(
        val titleExtractionMethod: String,
        val timeGenerationMethod: String,
        val durationEstimationMethod: String,
        val confidenceFactors: Map<String, Double>,
        val textPreprocessingApplied: List<String>,
        val patternsMatched: List<String>
    )
    
    /**
     * Generates a fallback event from original text and optional partial parsing results
     */
    fun generateFallbackEvent(
        originalText: String,
        partialResult: ParseResult? = null
    ): FallbackEvent {
        
        Log.d(TAG, "Generating fallback event for text length: ${originalText.length}")
        
        // Step 1: Preprocess text to improve extraction quality
        val preprocessedText = preprocessText(originalText)
        val preprocessingSteps = getPreprocessingSteps(originalText, preprocessedText)
        
        // Step 2: Extract meaningful title
        val titleResult = extractMeaningfulTitle(preprocessedText, partialResult?.title)
        
        // Step 3: Generate smart default date/time
        val dateTimeResult = generateSmartDateTime(preprocessedText, partialResult)
        
        // Step 4: Create descriptive description
        val description = generateDescription(originalText, titleResult, dateTimeResult, partialResult)
        
        // Step 5: Calculate confidence score
        val confidence = calculateConfidenceScore(
            originalText, 
            titleResult, 
            dateTimeResult, 
            partialResult
        )
        
        // Step 6: Determine fallback reason
        val fallbackReason = determineFallbackReason(partialResult, confidence)
        
        // Step 7: Create extraction details
        val extractionDetails = ExtractionDetails(
            titleExtractionMethod = titleResult.method,
            timeGenerationMethod = dateTimeResult.method,
            durationEstimationMethod = dateTimeResult.durationMethod,
            confidenceFactors = mapOf(
                "title_quality" to titleResult.confidence,
                "time_relevance" to dateTimeResult.confidence,
                "text_clarity" to calculateTextClarity(originalText),
                "partial_result_available" to if (partialResult != null) 0.3 else 0.0
            ),
            textPreprocessingApplied = preprocessingSteps,
            patternsMatched = titleResult.patternsMatched + dateTimeResult.patternsMatched
        )
        
        return FallbackEvent(
            title = titleResult.title,
            startDateTime = dateTimeResult.startDateTime,
            endDateTime = dateTimeResult.endDateTime,
            description = description,
            confidence = confidence,
            fallbackReason = fallbackReason,
            location = partialResult?.location,
            allDay = dateTimeResult.allDay,
            timezone = dateTimeResult.timezone,
            extractionDetails = extractionDetails
        )
    }
    
    /**
     * Preprocesses text to improve title extraction quality
     */
    private fun preprocessText(text: String): String {
        var processed = text.trim()
        
        // Fix common time format issues
        processed = processed.replace(Regex("(\\d{1,2}:\\d{2})a\\.m"), "$1 AM")
        processed = processed.replace(Regex("(\\d{1,2}:\\d{2})p\\.m"), "$1 PM")
        processed = processed.replace(Regex("(\\d{1,2})a\\.m"), "$1:00 AM")
        processed = processed.replace(Regex("(\\d{1,2})p\\.m"), "$1:00 PM")
        
        // Fix common spacing issues
        processed = processed.replace(Regex("(\\d{1,2}:\\d{2})am"), "$1 AM")
        processed = processed.replace(Regex("(\\d{1,2}:\\d{2})pm"), "$1 PM")
        processed = processed.replace(Regex("(\\d{1,2})am"), "$1:00 AM")
        processed = processed.replace(Regex("(\\d{1,2})pm"), "$1:00 PM")
        
        // Improve common phrasing patterns
        processed = processed.replace(Regex("^We will (.+?) by (.+)"), "$1 at $2")
        processed = processed.replace(Regex("^I will (.+?) by (.+)"), "$1 at $2")
        processed = processed.replace(Regex("^We need to (.+?) by (.+)"), "$1 at $2")
        
        // Clean up multiple spaces
        processed = processed.replace(Regex("\\s+"), " ")
        
        return processed
    }
    
    /**
     * Tracks what preprocessing steps were applied
     */
    private fun getPreprocessingSteps(original: String, processed: String): List<String> {
        val steps = mutableListOf<String>()
        
        if (original != processed) {
            if (original.contains(Regex("\\d{1,2}:\\d{2}[ap]\\.m"))) {
                steps.add("time_format_normalization")
            }
            if (original.contains(Regex("\\s{2,}"))) {
                steps.add("whitespace_cleanup")
            }
            if (original.contains(Regex("^(We|I) will .+? by"))) {
                steps.add("phrasing_improvement")
            }
        }
        
        return steps
    }
    
    /**
     * Result of title extraction with metadata
     */
    private data class TitleExtractionResult(
        val title: String,
        val confidence: Double,
        val method: String,
        val patternsMatched: List<String>
    )
    
    /**
     * Extracts meaningful title using pattern matching and heuristics
     */
    private fun extractMeaningfulTitle(
        preprocessedText: String, 
        partialTitle: String?
    ): TitleExtractionResult {
        
        // If we have a partial title from API, use it if it's good quality
        if (!partialTitle.isNullOrBlank() && partialTitle.length >= 3) {
            return TitleExtractionResult(
                title = partialTitle.trim(),
                confidence = 0.8,
                method = "partial_api_result",
                patternsMatched = listOf("api_partial_title")
            )
        }
        
        val matchedPatterns = mutableListOf<String>()
        
        // Try each title extraction pattern
        for ((index, pattern) in TITLE_PATTERNS.withIndex()) {
            val matcher = pattern.matcher(preprocessedText)
            if (matcher.find()) {
                val extractedTitle = when (index) {
                    0 -> { // attend [EVENT] at [LOCATION]
                        val event = matcher.group(1)?.trim() ?: ""
                        val location = matcher.group(2)?.trim() ?: ""
                        "$event at $location"
                    }
                    1, 2 -> { // On [day] patterns
                        val day = matcher.group(1)?.trim() ?: ""
                        val event = matcher.group(2)?.trim() ?: ""
                        "$event on $day"
                    }
                    else -> matcher.group(1)?.trim() ?: ""
                }
                
                if (extractedTitle.isNotBlank() && extractedTitle.length >= 3) {
                    matchedPatterns.add("pattern_${index + 1}")
                    return TitleExtractionResult(
                        title = cleanTitle(extractedTitle),
                        confidence = calculatePatternConfidence(index, extractedTitle),
                        method = "pattern_matching",
                        patternsMatched = matchedPatterns
                    )
                }
            }
        }
        
        // Fallback: Clean up the original text
        val cleanedTitle = cleanTitle(preprocessedText)
        matchedPatterns.add("text_cleanup_fallback")
        
        return TitleExtractionResult(
            title = cleanedTitle,
            confidence = calculateFallbackTitleConfidence(cleanedTitle, preprocessedText),
            method = "text_cleanup",
            patternsMatched = matchedPatterns
        )
    }
    
    /**
     * Cleans and formats extracted title
     */
    private fun cleanTitle(title: String): String {
        var cleaned = title.trim()
        
        // Remove common prefixes
        for (prefix in TITLE_PREFIXES_TO_REMOVE) {
            cleaned = cleaned.replace(Regex("^$prefix\\s+", RegexOption.IGNORE_CASE), "")
        }
        
        // Take first sentence or limit length
        val firstSentence = cleaned.split(Regex("[.!?]")).firstOrNull()?.trim()
        if (!firstSentence.isNullOrBlank() && firstSentence.length <= 60) {
            cleaned = firstSentence
        } else if (cleaned.length > 60) {
            cleaned = cleaned.substring(0, 57) + "..."
        }
        
        // Capitalize first letter
        if (cleaned.isNotEmpty()) {
            cleaned = cleaned.substring(0, 1).uppercase() + cleaned.substring(1)
        }
        
        return cleaned.ifBlank { "Event from Calendar App" }
    }
    
    /**
     * Calculates confidence for pattern-matched titles
     */
    private fun calculatePatternConfidence(patternIndex: Int, extractedTitle: String): Double {
        val baseConfidence = when (patternIndex) {
            0, 1, 2 -> 0.8  // High confidence patterns
            3, 4 -> 0.7     // Medium-high confidence
            5, 6 -> 0.6     // Medium confidence
            else -> 0.5     // Lower confidence
        }
        
        // Adjust based on title quality
        val lengthFactor = when {
            extractedTitle.length < 5 -> 0.7
            extractedTitle.length > 50 -> 0.8
            else -> 1.0
        }
        
        val wordCount = extractedTitle.split("\\s+".toRegex()).size
        val wordCountFactor = when {
            wordCount < 2 -> 0.8
            wordCount > 8 -> 0.9
            else -> 1.0
        }
        
        return (baseConfidence * lengthFactor * wordCountFactor).coerceIn(0.0, 1.0)
    }
    
    /**
     * Calculates confidence for fallback titles
     */
    private fun calculateFallbackTitleConfidence(cleanedTitle: String, originalText: String): Double {
        val baseConfidence = 0.3
        
        // Higher confidence if title is much shorter than original (good extraction)
        val compressionRatio = cleanedTitle.length.toDouble() / originalText.length
        val compressionFactor = when {
            compressionRatio < 0.3 -> 1.2  // Good compression
            compressionRatio < 0.6 -> 1.0  // Moderate compression
            else -> 0.8                    // Poor compression
        }
        
        // Higher confidence if title contains event-related keywords
        val eventKeywords = setOf("meeting", "appointment", "call", "event", "session", "class", "training")
        val hasEventKeywords = eventKeywords.any { cleanedTitle.lowercase().contains(it) }
        val keywordFactor = if (hasEventKeywords) 1.3 else 1.0
        
        return (baseConfidence * compressionFactor * keywordFactor).coerceIn(0.0, 1.0)
    }
    
    /**
     * Result of date/time generation with metadata
     */
    private data class DateTimeGenerationResult(
        val startDateTime: String,
        val endDateTime: String,
        val allDay: Boolean,
        val timezone: String,
        val confidence: Double,
        val method: String,
        val durationMethod: String,
        val patternsMatched: List<String>
    )
    
    /**
     * Generates smart default date/time based on current time and context
     */
    private fun generateSmartDateTime(
        preprocessedText: String,
        partialResult: ParseResult?
    ): DateTimeGenerationResult {
        
        val calendar = Calendar.getInstance()
        val matchedPatterns = mutableListOf<String>()
        
        // Use partial result if available and valid
        if (partialResult?.startDateTime != null) {
            try {
                val endTime = partialResult.endDateTime ?: calculateEndTime(
                    partialResult.startDateTime, 
                    estimateDuration(preprocessedText)
                )
                
                return DateTimeGenerationResult(
                    startDateTime = partialResult.startDateTime,
                    endDateTime = endTime,
                    allDay = partialResult.allDay,
                    timezone = partialResult.timezone,
                    confidence = 0.7,
                    method = "partial_api_result",
                    durationMethod = if (partialResult.endDateTime != null) "api_provided" else "estimated",
                    patternsMatched = listOf("api_partial_datetime")
                )
            } catch (e: Exception) {
                Log.w(TAG, "Failed to use partial datetime result", e)
            }
        }
        
        // Analyze text for time context
        val timeContext = analyzeTimeContext(preprocessedText)
        matchedPatterns.addAll(timeContext.patternsFound)
        
        // Generate start time based on context
        val startTime = generateContextualStartTime(calendar, timeContext)
        
        // Estimate duration
        val durationMinutes = estimateDuration(preprocessedText)
        val durationMethod = getDurationEstimationMethod(preprocessedText, durationMinutes)
        
        // Calculate end time
        val endCalendar = Calendar.getInstance()
        endCalendar.time = startTime
        endCalendar.add(Calendar.MINUTE, durationMinutes)
        
        val formatter = SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ssXXX", Locale.getDefault())
        
        return DateTimeGenerationResult(
            startDateTime = formatter.format(startTime),
            endDateTime = formatter.format(endCalendar.time),
            allDay = timeContext.suggestsAllDay,
            timezone = TimeZone.getDefault().id,
            confidence = calculateTimeConfidence(timeContext, durationMinutes),
            method = timeContext.method,
            durationMethod = durationMethod,
            patternsMatched = matchedPatterns
        )
    }
    
    /**
     * Context information extracted from text about timing
     */
    private data class TimeContext(
        val suggestsAllDay: Boolean,
        val preferredHour: Int?,
        val preferredDay: Int?, // 0 = today, 1 = tomorrow, etc.
        val timeKeywordsFound: List<String>,
        val patternsFound: List<String>,
        val method: String
    )
    
    /**
     * Analyzes text for time-related context clues
     */
    private fun analyzeTimeContext(text: String): TimeContext {
        val lowerText = text.lowercase()
        val timeKeywordsFound = mutableListOf<String>()
        val patternsFound = mutableListOf<String>()
        
        // Check for time keywords
        for (keyword in TIME_KEYWORDS) {
            if (lowerText.contains(keyword)) {
                timeKeywordsFound.add(keyword)
            }
        }
        
        // Determine preferred time based on keywords
        val preferredHour = when {
            timeKeywordsFound.any { it in setOf("morning", "am") } -> {
                patternsFound.add("morning_keyword")
                9 // 9 AM
            }
            timeKeywordsFound.any { it in setOf("afternoon", "pm") } -> {
                patternsFound.add("afternoon_keyword")
                14 // 2 PM
            }
            timeKeywordsFound.any { it in setOf("evening", "night") } -> {
                patternsFound.add("evening_keyword")
                19 // 7 PM
            }
            timeKeywordsFound.contains("lunch") -> {
                patternsFound.add("lunch_keyword")
                12 // 12 PM
            }
            timeKeywordsFound.contains("dinner") -> {
                patternsFound.add("dinner_keyword")
                18 // 6 PM
            }
            timeKeywordsFound.contains("breakfast") -> {
                patternsFound.add("breakfast_keyword")
                8 // 8 AM
            }
            else -> null
        }
        
        // Determine preferred day
        val preferredDay = when {
            timeKeywordsFound.contains("today") -> {
                patternsFound.add("today_keyword")
                0
            }
            timeKeywordsFound.contains("tomorrow") -> {
                patternsFound.add("tomorrow_keyword")
                1
            }
            timeKeywordsFound.any { it in setOf("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday") } -> {
                patternsFound.add("weekday_keyword")
                calculateDaysUntilWeekday(timeKeywordsFound.first { it in setOf("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday") })
            }
            else -> null
        }
        
        // Check if suggests all-day event
        val suggestsAllDay = timeKeywordsFound.any { it in setOf("daily", "all day", "entire day", "whole day") } ||
                lowerText.contains("all day") || lowerText.contains("entire day")
        
        if (suggestsAllDay) {
            patternsFound.add("all_day_indicator")
        }
        
        val method = when {
            preferredHour != null && preferredDay != null -> "keyword_time_and_day"
            preferredHour != null -> "keyword_time_only"
            preferredDay != null -> "keyword_day_only"
            timeKeywordsFound.isNotEmpty() -> "keyword_context"
            else -> "default_next_hour"
        }
        
        return TimeContext(
            suggestsAllDay = suggestsAllDay,
            preferredHour = preferredHour,
            preferredDay = preferredDay,
            timeKeywordsFound = timeKeywordsFound,
            patternsFound = patternsFound,
            method = method
        )
    }
    
    /**
     * Calculates days until specified weekday
     */
    private fun calculateDaysUntilWeekday(weekdayName: String): Int {
        val weekdays = mapOf(
            "sunday" to Calendar.SUNDAY,
            "monday" to Calendar.MONDAY,
            "tuesday" to Calendar.TUESDAY,
            "wednesday" to Calendar.WEDNESDAY,
            "thursday" to Calendar.THURSDAY,
            "friday" to Calendar.FRIDAY,
            "saturday" to Calendar.SATURDAY
        )
        
        val targetDay = weekdays[weekdayName.lowercase()] ?: return 1
        val today = Calendar.getInstance()
        val currentDay = today.get(Calendar.DAY_OF_WEEK)
        
        var daysUntil = targetDay - currentDay
        if (daysUntil <= 0) {
            daysUntil += 7 // Next week
        }
        
        return daysUntil
    }
    
    /**
     * Generates contextual start time based on analysis
     */
    private fun generateContextualStartTime(calendar: Calendar, timeContext: TimeContext): Date {
        // Apply day offset if specified
        timeContext.preferredDay?.let { dayOffset ->
            calendar.add(Calendar.DAY_OF_YEAR, dayOffset)
        }
        
        // Apply hour preference or default to next hour
        val targetHour = timeContext.preferredHour ?: run {
            val currentHour = calendar.get(Calendar.HOUR_OF_DAY)
            val currentMinute = calendar.get(Calendar.MINUTE)
            
            // If it's past 30 minutes, go to next hour
            if (currentMinute > 30) currentHour + 2 else currentHour + 1
        }
        
        calendar.set(Calendar.HOUR_OF_DAY, targetHour.coerceIn(0, 23))
        calendar.set(Calendar.MINUTE, 0)
        calendar.set(Calendar.SECOND, 0)
        calendar.set(Calendar.MILLISECOND, 0)
        
        return calendar.time
    }
    
    /**
     * Estimates event duration based on text content
     */
    private fun estimateDuration(text: String): Int {
        val lowerText = text.lowercase()
        
        // Check for explicit duration mentions
        val durationPattern = Pattern.compile("(\\d+)\\s*(hour|hr|minute|min)s?", Pattern.CASE_INSENSITIVE)
        val matcher = durationPattern.matcher(text)
        if (matcher.find()) {
            val number = matcher.group(1)?.toIntOrNull() ?: 1
            val unit = matcher.group(2)?.lowercase() ?: "hour"
            
            return when {
                unit.startsWith("hour") || unit.startsWith("hr") -> number * 60
                unit.startsWith("minute") || unit.startsWith("min") -> number
                else -> 60 // Default to 1 hour
            }
        }
        
        // Check for event type keywords
        for ((eventType, duration) in EVENT_TYPE_DURATIONS) {
            if (lowerText.contains(eventType)) {
                return duration
            }
        }
        
        // Default based on time of day
        val calendar = Calendar.getInstance()
        val hour = calendar.get(Calendar.HOUR_OF_DAY)
        return DEFAULT_DURATIONS_BY_TIME[hour] ?: 60 // Default to 1 hour
    }
    
    /**
     * Gets the method used for duration estimation
     */
    private fun getDurationEstimationMethod(text: String, estimatedDuration: Int): String {
        val lowerText = text.lowercase()
        
        // Check if explicit duration was found
        if (text.contains(Regex("\\d+\\s*(hour|hr|minute|min)s?", RegexOption.IGNORE_CASE))) {
            return "explicit_duration"
        }
        
        // Check if event type was matched
        for (eventType in EVENT_TYPE_DURATIONS.keys) {
            if (lowerText.contains(eventType)) {
                return "event_type_$eventType"
            }
        }
        
        return "time_of_day_default"
    }
    
    /**
     * Calculates end time from start time and duration
     */
    private fun calculateEndTime(startDateTime: String, durationMinutes: Int): String {
        return try {
            val formatter = SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ssXXX", Locale.getDefault())
            val startDate = formatter.parse(startDateTime)
            val calendar = Calendar.getInstance()
            calendar.time = startDate
            calendar.add(Calendar.MINUTE, durationMinutes)
            formatter.format(calendar.time)
        } catch (e: Exception) {
            Log.w(TAG, "Failed to calculate end time", e)
            startDateTime // Fallback to same as start time
        }
    }
    
    /**
     * Calculates confidence for time generation
     */
    private fun calculateTimeConfidence(timeContext: TimeContext, durationMinutes: Int): Double {
        var confidence = 0.4 // Base confidence for generated time
        
        // Boost confidence based on context clues
        when (timeContext.method) {
            "keyword_time_and_day" -> confidence += 0.3
            "keyword_time_only" -> confidence += 0.2
            "keyword_day_only" -> confidence += 0.1
            "keyword_context" -> confidence += 0.1
        }
        
        // Boost confidence for reasonable durations
        if (durationMinutes in 15..480) { // 15 minutes to 8 hours
            confidence += 0.1
        }
        
        return confidence.coerceIn(0.0, 1.0)
    }
    
    /**
     * Generates descriptive description including original text and reasoning
     */
    private fun generateDescription(
        originalText: String,
        titleResult: TitleExtractionResult,
        dateTimeResult: DateTimeGenerationResult,
        partialResult: ParseResult?
    ): String {
        val description = StringBuilder()
        
        // Add original text
        description.append("Event created from: \"$originalText\"\n\n")
        
        // Add extraction details
        description.append("Extraction details:\n")
        description.append("• Title: ${titleResult.method} (confidence: ${String.format("%.1f", titleResult.confidence * 100)}%)\n")
        description.append("• Time: ${dateTimeResult.method} (confidence: ${String.format("%.1f", dateTimeResult.confidence * 100)}%)\n")
        description.append("• Duration: ${dateTimeResult.durationMethod}\n")
        
        // Add partial result info if available
        partialResult?.let { result ->
            description.append("\nPartial parsing results were available:\n")
            if (!result.title.isNullOrBlank()) description.append("• Title: ${result.title}\n")
            if (!result.startDateTime.isNullOrBlank()) description.append("• Start time: ${result.startDateTime}\n")
            if (!result.location.isNullOrBlank()) description.append("• Location: ${result.location}\n")
            description.append("• Original confidence: ${String.format("%.1f", result.confidenceScore * 100)}%\n")
        }
        
        description.append("\nPlease review and adjust the event details as needed in your calendar app.")
        
        return description.toString()
    }
    
    /**
     * Calculates overall confidence score for the fallback event
     */
    private fun calculateConfidenceScore(
        originalText: String,
        titleResult: TitleExtractionResult,
        dateTimeResult: DateTimeGenerationResult,
        partialResult: ParseResult?
    ): Double {
        
        // Weighted average of component confidences
        val titleWeight = 0.4
        val timeWeight = 0.3
        val textQualityWeight = 0.2
        val partialResultWeight = 0.1
        
        val textQuality = calculateTextClarity(originalText)
        val partialResultBonus = if (partialResult != null) 0.3 else 0.0
        
        val weightedScore = (titleResult.confidence * titleWeight) +
                (dateTimeResult.confidence * timeWeight) +
                (textQuality * textQualityWeight) +
                (partialResultBonus * partialResultWeight)
        
        // Fallback events should generally have lower confidence
        return (weightedScore * 0.8).coerceIn(0.1, 0.6)
    }
    
    /**
     * Calculates text clarity score based on various factors
     */
    private fun calculateTextClarity(text: String): Double {
        var clarity = 0.5 // Base clarity
        
        // Length factor
        when (text.length) {
            in 10..100 -> clarity += 0.2  // Good length
            in 100..500 -> clarity += 0.1 // Acceptable length
            else -> clarity -= 0.1        // Too short or too long
        }
        
        // Word count factor
        val wordCount = text.split("\\s+".toRegex()).size
        when (wordCount) {
            in 3..20 -> clarity += 0.2   // Good word count
            in 20..50 -> clarity += 0.1  // Acceptable word count
            else -> clarity -= 0.1       // Too few or too many words
        }
        
        // Punctuation factor (indicates structure)
        if (text.contains(Regex("[.!?]"))) {
            clarity += 0.1
        }
        
        // Event-related keywords
        val eventKeywords = setOf("meeting", "appointment", "call", "event", "session", "class", "training", "conference")
        if (eventKeywords.any { text.lowercase().contains(it) }) {
            clarity += 0.2
        }
        
        return clarity.coerceIn(0.0, 1.0)
    }
    
    /**
     * Determines the reason for fallback event creation
     */
    private fun determineFallbackReason(partialResult: ParseResult?, confidence: Double): String {
        return when {
            partialResult == null -> "API parsing failed completely - created from original text analysis"
            partialResult.confidenceScore < 0.3 -> "API parsing returned low confidence results (${String.format("%.1f", partialResult.confidenceScore * 100)}%) - enhanced with fallback processing"
            partialResult.title.isNullOrBlank() && partialResult.startDateTime.isNullOrBlank() -> "API parsing returned incomplete results - filled missing fields with intelligent defaults"
            partialResult.title.isNullOrBlank() -> "API parsing missing title - extracted from original text"
            partialResult.startDateTime.isNullOrBlank() -> "API parsing missing date/time - generated contextual defaults"
            else -> "API parsing partially successful - enhanced with additional processing"
        }
    }
    
    /**
     * Converts FallbackEvent to ParseResult for compatibility
     */
    fun toParseResult(fallbackEvent: FallbackEvent, originalText: String): ParseResult {
        return ParseResult(
            title = fallbackEvent.title,
            startDateTime = fallbackEvent.startDateTime,
            endDateTime = fallbackEvent.endDateTime,
            location = fallbackEvent.location,
            description = fallbackEvent.description,
            confidenceScore = fallbackEvent.confidence,
            allDay = fallbackEvent.allDay,
            timezone = fallbackEvent.timezone,
            fallbackApplied = true,
            fallbackReason = fallbackEvent.fallbackReason,
            originalText = originalText,
            errorRecoveryInfo = ErrorRecoveryInfo(
                recoveryMethod = "fallback_event_generation",
                confidenceBeforeRecovery = 0.0,
                dataSourcesUsed = listOf(
                    fallbackEvent.extractionDetails.titleExtractionMethod,
                    fallbackEvent.extractionDetails.timeGenerationMethod,
                    fallbackEvent.extractionDetails.durationEstimationMethod
                ),
                userInterventionRequired = true
            )
        )
    }
}