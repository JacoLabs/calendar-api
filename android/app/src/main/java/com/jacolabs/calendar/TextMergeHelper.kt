package com.jacolabs.calendar

import android.content.ClipboardManager
import android.content.Context
import androidx.lifecycle.lifecycleScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.text.SimpleDateFormat
import java.util.*
import java.util.regex.Pattern

/**
 * Helper class for enhancing selected text with clipboard merge logic and heuristics.
 * Addresses Gmail's limitation of only sending one contiguous text selection.
 */
class TextMergeHelper(private val context: Context) {
    
    companion object {
        private const val MAX_MERGE_LENGTH = 280
        private const val MIN_MERGE_CONFIDENCE = 0.6
        
        // Patterns for detecting time and date information
        private val TIME_PATTERNS = listOf(
            Pattern.compile("\\b\\d{1,2}:\\d{2}\\s*[ap]\\.?m\\.?", Pattern.CASE_INSENSITIVE),
            Pattern.compile("\\b\\d{1,2}\\s*[ap]\\.?m\\.?", Pattern.CASE_INSENSITIVE),
            Pattern.compile("\\b\\d{1,2}:\\d{2}", Pattern.CASE_INSENSITIVE)
        )
        
        private val DATE_PATTERNS = listOf(
            Pattern.compile("\\b(monday|tuesday|wednesday|thursday|friday|saturday|sunday)", Pattern.CASE_INSENSITIVE),
            Pattern.compile("\\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\\w*\\s+\\d{1,2}", Pattern.CASE_INSENSITIVE),
            Pattern.compile("\\b\\d{1,2}/\\d{1,2}(/\\d{2,4})?", Pattern.CASE_INSENSITIVE),
            Pattern.compile("\\b(today|tomorrow|next week)", Pattern.CASE_INSENSITIVE)
        )
        
        private val WEEKDAYS = listOf("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")
    }
    
    private val apiService = ApiService()
    
    /**
     * Enhances selected text using clipboard merge and heuristic line expansion.
     */
    suspend fun enhanceTextForParsing(selectedText: String): String = withContext(Dispatchers.IO) {
        var enhancedText = selectedText
        
        // Step 1: Try clipboard merge if selection lacks time/date
        if (shouldAttemptClipboardMerge(selectedText)) {
            val clipboardText = getClipboardText()
            if (clipboardText != null) {
                val mergedText = attemptClipboardMerge(selectedText, clipboardText)
                if (mergedText != null) {
                    enhancedText = mergedText
                }
            }
        }
        
        // Step 2: Try heuristic line expansion for Gmail
        if (shouldAttemptLineExpansion(enhancedText)) {
            val expandedText = attemptLineExpansion(enhancedText)
            if (expandedText != null) {
                enhancedText = expandedText
            }
        }
        
        return@withContext enhancedText
    }
    
    /**
     * Applies safer defaults for incomplete parsing results.
     */
    fun applySaferDefaults(result: ParseResult, originalText: String): ParseResult {
        // If we have a weekday but no time, apply default 9:00-10:00 AM
        if (hasWeekdayButNoTime(result, originalText)) {
            val defaultStartTime = generateDefaultStartTime(originalText)
            val defaultEndTime = generateDefaultEndTime(defaultStartTime)
            
            return result.copy(
                startDateTime = defaultStartTime,
                endDateTime = defaultEndTime
            )
        }
        
        return result
    }
    
    private fun shouldAttemptClipboardMerge(selectedText: String): Boolean {
        val hasTime = TIME_PATTERNS.any { it.matcher(selectedText).find() }
        val hasDate = DATE_PATTERNS.any { it.matcher(selectedText).find() }
        
        // Attempt merge if we're missing either time or explicit date
        return !hasTime || (!hasDate && hasWeekdayOnly(selectedText))
    }
    
    private fun hasWeekdayOnly(text: String): Boolean {
        val lowerText = text.lowercase()
        return WEEKDAYS.any { lowerText.contains(it) }
    }
    
    private fun getClipboardText(): String? {
        return try {
            val clipboardManager = context.getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
            val clip = clipboardManager.primaryClip
            
            if (clip != null && clip.itemCount > 0) {
                val clipText = clip.getItemAt(0).text?.toString()
                if (!clipText.isNullOrBlank() && clipText.length <= MAX_MERGE_LENGTH) {
                    clipText
                } else null
            } else null
        } catch (e: Exception) {
            null
        }
    }
    
    private suspend fun attemptClipboardMerge(selectedText: String, clipboardText: String): String? {
        // Don't merge if clipboard is the same as selection
        if (selectedText.trim() == clipboardText.trim()) {
            return null
        }
        
        // Check if clipboard appears to be from the same context
        if (!appearsFromSameContext(selectedText, clipboardText)) {
            return null
        }
        
        // Preprocess both parts for better title extraction
        val preprocessedSelected = preprocessTextForMerge(selectedText)
        val preprocessedClipboard = preprocessTextForMerge(clipboardText)
        
        // Try different merge strategies with preprocessed text
        val mergeStrategies = listOf(
            "$preprocessedSelected\n$preprocessedClipboard",
            "$preprocessedClipboard\n$preprocessedSelected",
            "$preprocessedSelected $preprocessedClipboard"
        )
        
        var bestMerge: String? = null
        var bestScore = 0.0
        
        for (mergedText in mergeStrategies) {
            if (mergedText.length <= MAX_MERGE_LENGTH) {
                // Test merge quality by parsing
                val confidence = testMergeQuality(mergedText)
                if (confidence >= MIN_MERGE_CONFIDENCE) {
                    // Calculate a composite score that considers both confidence and title quality
                    val titleQuality = assessTitleQuality(mergedText)
                    val compositeScore = confidence * 0.7 + titleQuality * 0.3
                    
                    if (compositeScore > bestScore) {
                        bestScore = compositeScore
                        bestMerge = mergedText
                    }
                }
            }
        }
        
        return bestMerge
        
        return null
    }
    
    private fun appearsFromSameContext(selectedText: String, clipboardText: String): Boolean {
        val selectedWords = selectedText.lowercase().split("\\s+".toRegex()).filter { it.length > 3 }
        val clipboardWords = clipboardText.lowercase().split("\\s+".toRegex()).filter { it.length > 3 }
        
        // Check for common words (indicating same context)
        val commonWords = selectedWords.intersect(clipboardWords.toSet())
        val contextScore = commonWords.size.toDouble() / maxOf(selectedWords.size, clipboardWords.size)
        
        // Check for complementary information patterns
        val selectedHasTime = TIME_PATTERNS.any { it.matcher(selectedText).find() }
        val clipboardHasTime = TIME_PATTERNS.any { it.matcher(clipboardText).find() }
        val selectedHasDate = DATE_PATTERNS.any { it.matcher(selectedText).find() }
        val clipboardHasDate = DATE_PATTERNS.any { it.matcher(clipboardText).find() }
        val selectedHasLocation = looksLikeLocation(selectedText)
        val clipboardHasLocation = looksLikeLocation(clipboardText)
        
        val isComplementary = (selectedHasTime && !clipboardHasTime && clipboardHasDate) ||
                             (!selectedHasTime && clipboardHasTime && selectedHasDate) ||
                             (selectedHasDate && !clipboardHasDate && clipboardHasTime) ||
                             (!selectedHasDate && clipboardHasDate && selectedHasTime) ||
                             (selectedHasLocation && !clipboardHasLocation && (clipboardHasDate || clipboardHasTime)) ||
                             (!selectedHasLocation && clipboardHasLocation && (selectedHasDate || selectedHasTime))
        
        // Special case: if clipboard is just a location name, be more lenient
        val clipboardIsJustLocation = clipboardHasLocation && clipboardText.trim().split("\\s+".toRegex()).size <= 4
        
        return contextScore > 0.2 || isComplementary || clipboardIsJustLocation
    }
    
    private suspend fun testMergeQuality(mergedText: String): Double {
        return try {
            val timezone = TimeZone.getDefault().id
            val locale = Locale.getDefault().toString()
            val now = Date()
            
            val result = apiService.parseText(mergedText, timezone, locale, now)
            result.confidenceScore
        } catch (e: Exception) {
            0.0
        }
    }
    
    private fun shouldAttemptLineExpansion(text: String): Boolean {
        val hasWeekday = WEEKDAYS.any { text.lowercase().contains(it) }
        val hasTime = TIME_PATTERNS.any { it.matcher(text).find() }
        val hasNewlines = text.contains('\n')
        
        return hasWeekday && !hasTime && hasNewlines && text.length < MAX_MERGE_LENGTH
    }
    
    private fun attemptLineExpansion(text: String): String? {
        val lines = text.split('\n').map { it.trim() }.filter { it.isNotEmpty() }
        
        if (lines.size < 2) return null
        
        // Find the line with weekday
        val weekdayLineIndex = lines.indexOfFirst { line ->
            WEEKDAYS.any { line.lowercase().contains(it) }
        }
        
        if (weekdayLineIndex == -1) return null
        
        // Try to find a line with time information
        val timeLineIndex = lines.indexOfFirst { line ->
            TIME_PATTERNS.any { it.matcher(line).find() }
        }
        
        if (timeLineIndex != -1 && timeLineIndex != weekdayLineIndex) {
            // Combine the weekday line with the time line
            val combinedLines = mutableSetOf<String>()
            combinedLines.add(lines[weekdayLineIndex])
            combinedLines.add(lines[timeLineIndex])
            
            // Also include location lines if present
            lines.forEach { line ->
                if (looksLikeLocation(line) && line !in combinedLines) {
                    combinedLines.add(line)
                }
            }
            
            val expandedText = combinedLines.joinToString("\n")
            return if (expandedText.length <= MAX_MERGE_LENGTH) expandedText else null
        }
        
        return null
    }
    
    private fun looksLikeLocation(line: String): Boolean {
        val locationKeywords = listOf("square", "park", "center", "centre", "hall", "room", "street", "avenue", "building", "plaza", "place", "court")
        val lowerLine = line.lowercase()
        
        // Check for location keywords
        val hasLocationKeyword = locationKeywords.any { lowerLine.contains(it) }
        
        // Check for address patterns
        val hasAddressPattern = line.matches(Regex(".*\\d+\\s+\\w+\\s+(street|st|avenue|ave|road|rd).*", RegexOption.IGNORE_CASE))
        
        // Check for proper nouns that look like places (capitalized words)
        val hasProperNouns = line.split("\\s+".toRegex()).count { word ->
            word.isNotEmpty() && word[0].isUpperCase() && word.length > 2
        } >= 2
        
        // Check if it's a standalone location (short line with place-like words)
        val isStandalonePlaceName = line.trim().split("\\s+".toRegex()).size <= 4 && hasProperNouns
        
        return hasLocationKeyword || hasAddressPattern || isStandalonePlaceName
    }
    
    private fun hasWeekdayButNoTime(result: ParseResult, originalText: String): Boolean {
        val hasWeekday = WEEKDAYS.any { originalText.lowercase().contains(it) }
        val hasTime = !result.startDateTime.isNullOrBlank()
        
        return hasWeekday && !hasTime
    }
    
    private fun generateDefaultStartTime(text: String): String {
        // Find the weekday mentioned in the text
        val weekday = WEEKDAYS.find { text.lowercase().contains(it) }
        
        if (weekday != null) {
            val calendar = Calendar.getInstance()
            val targetDayOfWeek = getCalendarDayOfWeek(weekday)
            
            // Find next occurrence of this weekday
            while (calendar.get(Calendar.DAY_OF_WEEK) != targetDayOfWeek) {
                calendar.add(Calendar.DAY_OF_MONTH, 1)
            }
            
            // Set to 9:00 AM
            calendar.set(Calendar.HOUR_OF_DAY, 9)
            calendar.set(Calendar.MINUTE, 0)
            calendar.set(Calendar.SECOND, 0)
            calendar.set(Calendar.MILLISECOND, 0)
            
            val formatter = SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ssXXX", Locale.US)
            return formatter.format(calendar.time)
        }
        
        // Fallback to tomorrow 9:00 AM
        val calendar = Calendar.getInstance()
        calendar.add(Calendar.DAY_OF_MONTH, 1)
        calendar.set(Calendar.HOUR_OF_DAY, 9)
        calendar.set(Calendar.MINUTE, 0)
        calendar.set(Calendar.SECOND, 0)
        calendar.set(Calendar.MILLISECOND, 0)
        
        val formatter = SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ssXXX", Locale.US)
        return formatter.format(calendar.time)
    }
    
    private fun generateDefaultEndTime(startTime: String): String {
        return try {
            val formatter = SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ssXXX", Locale.US)
            val startDate = formatter.parse(startTime)
            val calendar = Calendar.getInstance()
            calendar.time = startDate
            calendar.add(Calendar.HOUR_OF_DAY, 1) // Add 1 hour
            
            formatter.format(calendar.time)
        } catch (e: Exception) {
            startTime // Fallback to same time
        }
    }
    
    private fun getCalendarDayOfWeek(weekday: String): Int {
        return when (weekday.lowercase()) {
            "sunday" -> Calendar.SUNDAY
            "monday" -> Calendar.MONDAY
            "tuesday" -> Calendar.TUESDAY
            "wednesday" -> Calendar.WEDNESDAY
            "thursday" -> Calendar.THURSDAY
            "friday" -> Calendar.FRIDAY
            "saturday" -> Calendar.SATURDAY
            else -> Calendar.MONDAY
        }
    }
    
    /**
     * Preprocesses text for better merging, focusing on title extraction.
     */
    private fun preprocessTextForMerge(text: String): String {
        var processed = text
        
        // Fix time formats first
        processed = processed.replace(Regex("(\\d{1,2}:\\d{2})a\\.m"), "$1 AM")
        processed = processed.replace(Regex("(\\d{1,2}:\\d{2})p\\.m"), "$1 PM")
        processed = processed.replace(Regex("(\\d{1,2})a\\.m"), "$1:00 AM")
        processed = processed.replace(Regex("(\\d{1,2})p\\.m"), "$1:00 PM")
        processed = processed.replace(Regex("(\\d{1,2}:\\d{2})am"), "$1 AM")
        processed = processed.replace(Regex("(\\d{1,2}:\\d{2})pm"), "$1 PM")
        processed = processed.replace(Regex("(\\d{1,2})am"), "$1:00 AM")
        processed = processed.replace(Regex("(\\d{1,2})pm"), "$1:00 PM")
        
        // Common phrasing improvements
        processed = processed.replace(Regex("^We will (.+?) by (.+)"), "$1 at $2")
        processed = processed.replace(Regex("^I will (.+?) by (.+)"), "$1 at $2")
        processed = processed.replace(Regex("^We need to (.+?) by (.+)"), "$1 at $2")
        
        // Enhanced title extraction
        processed = enhanceTitleExtraction(processed)
        
        return processed
    }
    
    /**
     * Enhances text to improve title extraction.
     */
    private fun enhanceTitleExtraction(text: String): String {
        var enhanced = text
        
        // Pattern 1: "On [day] the [people] will attend [EVENT]" -> "[EVENT] on [day]"
        enhanced = enhanced.replace(
            Regex("^On (\\w+day) the .+? will attend (.+?)(?:\\s+at\\s+(.+?))?(?:\\.|$)", RegexOption.IGNORE_CASE),
            "$2 on $1"
        )
        
        // Pattern 2: "On [day] the [people] will [action] the [EVENT]" -> "[EVENT] on [day]"  
        enhanced = enhanced.replace(
            Regex("^On (\\w+day) the .+? will \\w+ the (.+?)(?:\\s+at\\s+(.+?))?(?:\\.|$)", RegexOption.IGNORE_CASE),
            "$2 on $1"
        )
        
        // Pattern 3: Extract event name from "attend [EVENT] at [LOCATION]"
        enhanced = enhanced.replace(
            Regex("attend (.+?) at (.+?)(?:\\.|$)", RegexOption.IGNORE_CASE),
            "$1 at $2"
        )
        
        // Pattern 4: Extract event name from "will attend [EVENT]"
        enhanced = enhanced.replace(
            Regex("will attend (.+?)(?:\\s+at\\s+(.+?))?(?:\\.|$)", RegexOption.IGNORE_CASE)
        ) { matchResult ->
            val event = matchResult.groupValues[1]
            val location = if (matchResult.groupValues.size > 2) matchResult.groupValues[2] else ""
            if (location.isNotEmpty()) "$event at $location" else event
        }
        
        // Pattern 5: Clean up common prefixes that don't belong in titles
        enhanced = enhanced.replace(Regex("^(On \\w+day )?the (students?|children|kids) will ", RegexOption.IGNORE_CASE), "")
        enhanced = enhanced.replace(Regex("^(We|I) will ", RegexOption.IGNORE_CASE), "")
        
        // Pattern 6: Capitalize first letter and clean up
        enhanced = enhanced.trim()
        if (enhanced.isNotEmpty()) {
            enhanced = enhanced.substring(0, 1).uppercase() + enhanced.substring(1)
        }
        
        return enhanced
    }
    
    /**
     * Assesses the quality of a title for merge selection.
     * Returns a score from 0.0 to 1.0 where higher is better.
     */
    private suspend fun assessTitleQuality(mergedText: String): Double {
        return try {
            val timezone = TimeZone.getDefault().id
            val locale = Locale.getDefault().toString()
            val now = Date()
            
            val result = apiService.parseText(mergedText, timezone, locale, now)
            val title = result.title ?: ""
            
            var score = 0.0
            
            // Prefer event names over actions
            if (title.contains("Gathering", ignoreCase = true) || 
                title.contains("Meeting", ignoreCase = true) ||
                title.contains("Conference", ignoreCase = true) ||
                title.contains("Event", ignoreCase = true)) {
                score += 0.4
            }
            
            // Penalize action-based titles
            if (title.contains("Leave", ignoreCase = true) ||
                title.contains("Go to", ignoreCase = true) ||
                title.contains("Walk", ignoreCase = true)) {
                score -= 0.2
            }
            
            // Prefer titles that don't start with temporal phrases
            if (!title.startsWith("On Monday", ignoreCase = true) &&
                !title.startsWith("On Tuesday", ignoreCase = true) &&
                !title.startsWith("Tomorrow", ignoreCase = true)) {
                score += 0.2
            }
            
            // Prefer titles with proper nouns (capitalized words)
            val capitalizedWords = title.split(" ").count { word ->
                word.isNotEmpty() && word[0].isUpperCase()
            }
            if (capitalizedWords >= 2) {
                score += 0.3
            }
            
            // Ensure score is between 0 and 1
            maxOf(0.0, minOf(1.0, score))
            
        } catch (e: Exception) {
            0.5 // Default neutral score
        }
    }
}

/**
 * Extension function to create a copy of ParseResult with modified fields.
 */
fun ParseResult.copy(
    title: String? = this.title,
    startDateTime: String? = this.startDateTime,
    endDateTime: String? = this.endDateTime,
    location: String? = this.location,
    description: String? = this.description,
    confidenceScore: Double = this.confidenceScore,
    allDay: Boolean = this.allDay,
    timezone: String = this.timezone
): ParseResult {
    return ParseResult(
        title = title,
        startDateTime = startDateTime,
        endDateTime = endDateTime,
        location = location,
        description = description,
        confidenceScore = confidenceScore,
        allDay = allDay,
        timezone = timezone
    )
}