package com.jacolabs.calendar

import android.content.Context
import android.util.Log
import java.text.SimpleDateFormat
import java.util.*
import kotlin.math.max
import kotlin.math.min

/**
 * ConfidenceValidator evaluates parsing results and provides user guidance based on confidence scores
 * and data quality. Implements confidence threshold evaluation, field-level analysis, and 
 * improvement suggestions for low-confidence parsing results.
 */
class ConfidenceValidator(
    private val context: Context,
    private val config: ConfidenceValidatorConfig = ConfidenceValidatorConfig()
) {
    
    companion object {
        private const val TAG = "ConfidenceValidator"
        
        // Default confidence thresholds
        private const val HIGH_CONFIDENCE_THRESHOLD = 0.7
        private const val MEDIUM_CONFIDENCE_THRESHOLD = 0.3
        private const val CRITICAL_CONFIDENCE_THRESHOLD = 0.1
        
        // Field importance weights for overall confidence calculation
        private const val TITLE_WEIGHT = 0.3
        private const val START_TIME_WEIGHT = 0.25
        private const val END_TIME_WEIGHT = 0.15
        private const val LOCATION_WEIGHT = 0.15
        private const val DESCRIPTION_WEIGHT = 0.15
    }
    
    /**
     * Configuration for confidence validation behavior
     */
    data class ConfidenceValidatorConfig(
        val highConfidenceThreshold: Double = HIGH_CONFIDENCE_THRESHOLD,
        val mediumConfidenceThreshold: Double = MEDIUM_CONFIDENCE_THRESHOLD,
        val criticalConfidenceThreshold: Double = CRITICAL_CONFIDENCE_THRESHOLD,
        val enableFieldLevelAnalysis: Boolean = true,
        val enableImprovementSuggestions: Boolean = true,
        val enableWarningMessages: Boolean = true,
        val strictValidation: Boolean = false
    )
    
    /**
     * User recommendations based on confidence assessment
     */
    enum class UserRecommendation {
        PROCEED_CONFIDENTLY,
        PROCEED_WITH_CAUTION,
        SUGGEST_IMPROVEMENTS,
        RECOMMEND_MANUAL_ENTRY,
        BLOCK_CREATION
    }
    
    /**
     * Severity levels for warning messages
     */
    enum class WarningSeverity {
        INFO,
        WARNING,
        ERROR,
        CRITICAL
    }
    
    /**
     * Comprehensive confidence assessment result
     */
    data class ConfidenceAssessment(
        val overallConfidence: Double,
        val fieldConfidences: Map<String, FieldConfidenceInfo>,
        val recommendation: UserRecommendation,
        val warningMessage: String?,
        val warningSeverity: WarningSeverity,
        val shouldProceed: Boolean,
        val improvementSuggestions: List<ImprovementSuggestion>,
        val dataQualityScore: Double,
        val missingCriticalFields: List<String>,
        val lowConfidenceFields: List<String>,
        val analysisDetails: AnalysisDetails
    )
    
    /**
     * Field-level confidence information
     */
    data class FieldConfidenceInfo(
        val fieldName: String,
        val confidence: Double,
        val value: Any?,
        val source: String,
        val hasValue: Boolean,
        val isRequired: Boolean,
        val qualityScore: Double,
        val issues: List<String>
    )
    
    /**
     * Improvement suggestions for better parsing results
     */
    data class ImprovementSuggestion(
        val type: SuggestionType,
        val message: String,
        val example: String?,
        val priority: SuggestionPriority,
        val fieldAffected: String?
    )
    
    /**
     * Types of improvement suggestions
     */
    enum class SuggestionType {
        ADD_SPECIFIC_DATE,
        ADD_SPECIFIC_TIME,
        CLARIFY_EVENT_TITLE,
        ADD_LOCATION_DETAILS,
        IMPROVE_TIME_FORMAT,
        ADD_DURATION_INFO,
        REMOVE_AMBIGUITY,
        USE_STANDARD_FORMAT,
        ADD_CONTEXT
    }
    
    /**
     * Priority levels for suggestions
     */
    enum class SuggestionPriority {
        HIGH,
        MEDIUM,
        LOW
    }
    
    /**
     * Detailed analysis information
     */
    data class AnalysisDetails(
        val totalFields: Int,
        val fieldsWithValues: Int,
        val fieldsWithHighConfidence: Int,
        val fieldsWithMediumConfidence: Int,
        val fieldsWithLowConfidence: Int,
        val averageFieldConfidence: Double,
        val textComplexityScore: Double,
        val parsingMethodUsed: String?,
        val processingTimeMs: Long,
        val potentialIssues: List<String>
    )
    
    /**
     * Main method to assess confidence of parsing results
     */
    fun assessConfidence(result: ParseResult, originalText: String): ConfidenceAssessment {
        try {
            Log.d(TAG, "Assessing confidence for result with overall score: ${result.confidenceScore}")
            
            // Analyze field-level confidence
            val fieldConfidences = analyzeFieldConfidences(result, originalText)
            
            // Calculate overall confidence (may differ from API confidence)
            val calculatedOverallConfidence = calculateOverallConfidence(fieldConfidences, result.confidenceScore)
            
            // Assess data quality
            val dataQualityScore = assessDataQuality(result, originalText)
            
            // Identify issues
            val missingCriticalFields = identifyMissingCriticalFields(fieldConfidences)
            val lowConfidenceFields = identifyLowConfidenceFields(fieldConfidences)
            
            // Generate improvement suggestions
            val improvementSuggestions = if (config.enableImprovementSuggestions) {
                generateImprovementSuggestions(originalText, result, fieldConfidences)
            } else {
                emptyList()
            }
            
            // Determine recommendation
            val recommendation = determineUserRecommendation(
                calculatedOverallConfidence,
                dataQualityScore,
                missingCriticalFields,
                lowConfidenceFields
            )
            
            // Generate warning message
            val (warningMessage, warningSeverity) = if (config.enableWarningMessages) {
                generateWarningMessage(recommendation, calculatedOverallConfidence, missingCriticalFields, lowConfidenceFields)
            } else {
                Pair(null, WarningSeverity.INFO)
            }
            
            // Determine if should proceed
            val shouldProceed = determineShouldProceed(recommendation, calculatedOverallConfidence)
            
            // Create analysis details
            val analysisDetails = createAnalysisDetails(result, originalText, fieldConfidences)
            
            return ConfidenceAssessment(
                overallConfidence = calculatedOverallConfidence,
                fieldConfidences = fieldConfidences,
                recommendation = recommendation,
                warningMessage = warningMessage,
                warningSeverity = warningSeverity,
                shouldProceed = shouldProceed,
                improvementSuggestions = improvementSuggestions,
                dataQualityScore = dataQualityScore,
                missingCriticalFields = missingCriticalFields,
                lowConfidenceFields = lowConfidenceFields,
                analysisDetails = analysisDetails
            )
            
        } catch (e: Exception) {
            Log.e(TAG, "Error during confidence assessment", e)
            
            // Return safe fallback assessment
            return createFallbackAssessment(result, originalText)
        }
    }
    
    /**
     * Analyzes confidence for individual fields
     */
    private fun analyzeFieldConfidences(result: ParseResult, originalText: String): Map<String, FieldConfidenceInfo> {
        val fieldConfidences = mutableMapOf<String, FieldConfidenceInfo>()
        
        // Analyze title field
        fieldConfidences["title"] = analyzeFieldConfidence(
            fieldName = "title",
            value = result.title,
            fieldResult = result.fieldResults?.get("title"),
            originalText = originalText,
            isRequired = true
        )
        
        // Analyze start_datetime field
        fieldConfidences["start_datetime"] = analyzeFieldConfidence(
            fieldName = "start_datetime",
            value = result.startDateTime,
            fieldResult = result.fieldResults?.get("start_datetime"),
            originalText = originalText,
            isRequired = true
        )
        
        // Analyze end_datetime field
        fieldConfidences["end_datetime"] = analyzeFieldConfidence(
            fieldName = "end_datetime",
            value = result.endDateTime,
            fieldResult = result.fieldResults?.get("end_datetime"),
            originalText = originalText,
            isRequired = false
        )
        
        // Analyze location field
        fieldConfidences["location"] = analyzeFieldConfidence(
            fieldName = "location",
            value = result.location,
            fieldResult = result.fieldResults?.get("location"),
            originalText = originalText,
            isRequired = false
        )
        
        // Analyze description field
        fieldConfidences["description"] = analyzeFieldConfidence(
            fieldName = "description",
            value = result.description,
            fieldResult = result.fieldResults?.get("description"),
            originalText = originalText,
            isRequired = false
        )
        
        return fieldConfidences
    }
    
    /**
     * Analyzes confidence for a single field
     */
    private fun analyzeFieldConfidence(
        fieldName: String,
        value: Any?,
        fieldResult: FieldResult?,
        originalText: String,
        isRequired: Boolean
    ): FieldConfidenceInfo {
        
        val hasValue = !value.toString().isNullOrBlank()
        val apiConfidence = fieldResult?.confidence ?: 0.0
        val source = fieldResult?.source ?: "unknown"
        
        // Calculate quality score based on various factors
        val qualityScore = calculateFieldQualityScore(fieldName, value, originalText, fieldResult)
        
        // Adjust confidence based on quality score
        val adjustedConfidence = if (hasValue) {
            min(1.0, apiConfidence * qualityScore)
        } else {
            0.0
        }
        
        // Identify field-specific issues
        val issues = identifyFieldIssues(fieldName, value, originalText, fieldResult)
        
        return FieldConfidenceInfo(
            fieldName = fieldName,
            confidence = adjustedConfidence,
            value = value,
            source = source,
            hasValue = hasValue,
            isRequired = isRequired,
            qualityScore = qualityScore,
            issues = issues
        )
    }
    
    /**
     * Calculates quality score for a field based on various factors
     */
    private fun calculateFieldQualityScore(
        fieldName: String,
        value: Any?,
        originalText: String,
        fieldResult: FieldResult?
    ): Double {
        if (value == null || value.toString().isBlank()) {
            return 0.0
        }
        
        var qualityScore = 1.0
        val valueStr = value.toString()
        
        when (fieldName) {
            "title" -> {
                // Title quality factors
                if (valueStr.length < 3) qualityScore *= 0.3
                else if (valueStr.length < 10) qualityScore *= 0.7
                
                // Check for meaningful content
                if (valueStr.matches(Regex("^(event|meeting|appointment)$", RegexOption.IGNORE_CASE))) {
                    qualityScore *= 0.4 // Generic titles are low quality
                }
                
                // Check for proper capitalization
                if (valueStr.all { it.isLowerCase() || !it.isLetter() }) {
                    qualityScore *= 0.8
                }
            }
            
            "start_datetime", "end_datetime" -> {
                // DateTime quality factors
                if (isValidDateTime(valueStr)) {
                    qualityScore = 1.0
                } else {
                    qualityScore = 0.2
                }
                
                // Check if time is in the past (for start_datetime)
                if (fieldName == "start_datetime" && isPastDateTime(valueStr)) {
                    qualityScore *= 0.6 // Past dates are suspicious but not invalid
                }
            }
            
            "location" -> {
                // Location quality factors
                if (valueStr.length < 2) qualityScore *= 0.3
                else if (valueStr.length > 100) qualityScore *= 0.7
                
                // Check for common location patterns
                if (valueStr.matches(Regex(".*\\b(room|building|street|avenue|drive)\\b.*", RegexOption.IGNORE_CASE))) {
                    qualityScore *= 1.1 // Boost for location keywords
                }
            }
            
            "description" -> {
                // Description quality factors
                if (valueStr.length < 5) qualityScore *= 0.5
                else if (valueStr.length > 500) qualityScore *= 0.8
            }
        }
        
        return max(0.0, min(1.0, qualityScore))
    }
    
    /**
     * Identifies issues with specific fields
     */
    private fun identifyFieldIssues(
        fieldName: String,
        value: Any?,
        originalText: String,
        fieldResult: FieldResult?
    ): List<String> {
        val issues = mutableListOf<String>()
        
        if (value == null || value.toString().isBlank()) {
            if (fieldName in listOf("title", "start_datetime")) {
                issues.add("Missing required field")
            }
            return issues
        }
        
        val valueStr = value.toString()
        
        when (fieldName) {
            "title" -> {
                if (valueStr.length < 3) {
                    issues.add("Title too short")
                }
                if (valueStr.matches(Regex("^(event|meeting|appointment)$", RegexOption.IGNORE_CASE))) {
                    issues.add("Generic title - needs more specificity")
                }
                if (valueStr.all { it.isLowerCase() || !it.isLetter() }) {
                    issues.add("Title not properly capitalized")
                }
            }
            
            "start_datetime", "end_datetime" -> {
                if (!isValidDateTime(valueStr)) {
                    issues.add("Invalid date/time format")
                }
                if (fieldName == "start_datetime" && isPastDateTime(valueStr)) {
                    issues.add("Date/time appears to be in the past")
                }
            }
            
            "location" -> {
                if (valueStr.length < 2) {
                    issues.add("Location too vague")
                }
                if (valueStr.length > 100) {
                    issues.add("Location description too long")
                }
            }
        }
        
        return issues
    }
    
    /**
     * Calculates overall confidence considering field weights and importance
     */
    private fun calculateOverallConfidence(
        fieldConfidences: Map<String, FieldConfidenceInfo>,
        apiConfidence: Double
    ): Double {
        
        // Use API confidence as base, but adjust based on field analysis
        var weightedSum = 0.0
        var totalWeight = 0.0
        
        // Apply weights to field confidences
        fieldConfidences["title"]?.let { 
            weightedSum += it.confidence * TITLE_WEIGHT
            totalWeight += TITLE_WEIGHT
        }
        
        fieldConfidences["start_datetime"]?.let { 
            weightedSum += it.confidence * START_TIME_WEIGHT
            totalWeight += START_TIME_WEIGHT
        }
        
        fieldConfidences["end_datetime"]?.let { 
            weightedSum += it.confidence * END_TIME_WEIGHT
            totalWeight += END_TIME_WEIGHT
        }
        
        fieldConfidences["location"]?.let { 
            weightedSum += it.confidence * LOCATION_WEIGHT
            totalWeight += LOCATION_WEIGHT
        }
        
        fieldConfidences["description"]?.let { 
            weightedSum += it.confidence * DESCRIPTION_WEIGHT
            totalWeight += DESCRIPTION_WEIGHT
        }
        
        val calculatedConfidence = if (totalWeight > 0) weightedSum / totalWeight else 0.0
        
        // Blend API confidence with calculated confidence (70% API, 30% calculated)
        return (apiConfidence * 0.7) + (calculatedConfidence * 0.3)
    }
    
    /**
     * Assesses overall data quality
     */
    private fun assessDataQuality(result: ParseResult, originalText: String): Double {
        var qualityScore = 1.0
        
        // Factor 1: Completeness
        val completenessScore = calculateCompletenessScore(result)
        qualityScore *= completenessScore
        
        // Factor 2: Text clarity
        val clarityScore = calculateTextClarityScore(originalText)
        qualityScore *= clarityScore
        
        // Factor 3: Consistency
        val consistencyScore = calculateConsistencyScore(result)
        qualityScore *= consistencyScore
        
        return max(0.0, min(1.0, qualityScore))
    }
    
    /**
     * Calculates completeness score based on available fields
     */
    private fun calculateCompletenessScore(result: ParseResult): Double {
        var score = 0.0
        var maxScore = 0.0
        
        // Required fields
        if (!result.title.isNullOrBlank()) score += 0.4 else maxScore += 0.4
        if (!result.startDateTime.isNullOrBlank()) score += 0.4 else maxScore += 0.4
        
        // Optional but valuable fields
        if (!result.endDateTime.isNullOrBlank()) score += 0.1 else maxScore += 0.1
        if (!result.location.isNullOrBlank()) score += 0.1 else maxScore += 0.1
        
        maxScore += score
        return if (maxScore > 0) score / maxScore else 0.0
    }
    
    /**
     * Calculates text clarity score
     */
    private fun calculateTextClarityScore(originalText: String): Double {
        var clarityScore = 1.0
        
        // Length factors
        when {
            originalText.length < 10 -> clarityScore *= 0.3
            originalText.length < 20 -> clarityScore *= 0.6
            originalText.length > 500 -> clarityScore *= 0.8
        }
        
        // Structure factors
        val sentences = originalText.split(Regex("[.!?]+")).filter { it.trim().isNotEmpty() }
        if (sentences.size > 5) clarityScore *= 0.8 // Too many sentences can be confusing
        
        // Keyword presence
        val hasTimeKeywords = originalText.contains(Regex("\\b(at|on|from|to|until|during|\\d{1,2}:\\d{2}|\\d{1,2}(am|pm))\\b", RegexOption.IGNORE_CASE))
        if (!hasTimeKeywords) clarityScore *= 0.7
        
        return max(0.0, min(1.0, clarityScore))
    }
    
    /**
     * Calculates consistency score between fields
     */
    private fun calculateConsistencyScore(result: ParseResult): Double {
        var consistencyScore = 1.0
        
        // Check start/end time consistency
        if (!result.startDateTime.isNullOrBlank() && !result.endDateTime.isNullOrBlank()) {
            if (isEndTimeBeforeStartTime(result.startDateTime, result.endDateTime)) {
                consistencyScore *= 0.3 // Major inconsistency
            }
        }
        
        // Check title/description consistency
        if (!result.title.isNullOrBlank() && !result.description.isNullOrBlank()) {
            val titleWords = result.title.lowercase().split(Regex("\\W+"))
            val descWords = result.description.lowercase().split(Regex("\\W+"))
            val commonWords = titleWords.intersect(descWords.toSet())
            
            if (commonWords.isEmpty() && titleWords.size > 2 && descWords.size > 5) {
                consistencyScore *= 0.8 // Slight inconsistency
            }
        }
        
        return max(0.0, min(1.0, consistencyScore))
    }
    
    /**
     * Identifies missing critical fields
     */
    private fun identifyMissingCriticalFields(fieldConfidences: Map<String, FieldConfidenceInfo>): List<String> {
        val missingFields = mutableListOf<String>()
        
        fieldConfidences.values.forEach { fieldInfo ->
            if (fieldInfo.isRequired && !fieldInfo.hasValue) {
                missingFields.add(fieldInfo.fieldName)
            }
        }
        
        return missingFields
    }
    
    /**
     * Identifies fields with low confidence
     */
    private fun identifyLowConfidenceFields(fieldConfidences: Map<String, FieldConfidenceInfo>): List<String> {
        val lowConfidenceFields = mutableListOf<String>()
        
        fieldConfidences.values.forEach { fieldInfo ->
            if (fieldInfo.hasValue && fieldInfo.confidence < config.mediumConfidenceThreshold) {
                lowConfidenceFields.add(fieldInfo.fieldName)
            }
        }
        
        return lowConfidenceFields
    }
    
    /**
     * Generates improvement suggestions based on analysis
     */
    fun generateImprovementSuggestions(
        originalText: String,
        result: ParseResult,
        fieldConfidences: Map<String, FieldConfidenceInfo>? = null
    ): List<ImprovementSuggestion> {
        
        val suggestions = mutableListOf<ImprovementSuggestion>()
        val confidences = fieldConfidences ?: analyzeFieldConfidences(result, originalText)
        
        // Analyze each field for improvement opportunities
        confidences.forEach { (fieldName, fieldInfo) ->
            suggestions.addAll(generateFieldSpecificSuggestions(fieldName, fieldInfo, originalText))
        }
        
        // Add general text improvement suggestions
        suggestions.addAll(generateGeneralTextSuggestions(originalText, result))
        
        // Sort by priority and return top suggestions
        return suggestions.sortedBy { it.priority.ordinal }.take(5)
    }
    
    /**
     * Generates field-specific improvement suggestions
     */
    private fun generateFieldSpecificSuggestions(
        fieldName: String,
        fieldInfo: FieldConfidenceInfo,
        originalText: String
    ): List<ImprovementSuggestion> {
        
        val suggestions = mutableListOf<ImprovementSuggestion>()
        
        when (fieldName) {
            "title" -> {
                if (!fieldInfo.hasValue) {
                    suggestions.add(ImprovementSuggestion(
                        type = SuggestionType.CLARIFY_EVENT_TITLE,
                        message = "Add a clear event title or description",
                        example = "Instead of 'meeting', try 'Team standup meeting'",
                        priority = SuggestionPriority.HIGH,
                        fieldAffected = fieldName
                    ))
                } else if (fieldInfo.confidence < config.mediumConfidenceThreshold) {
                    suggestions.add(ImprovementSuggestion(
                        type = SuggestionType.CLARIFY_EVENT_TITLE,
                        message = "Make the event title more specific",
                        example = "Instead of '${fieldInfo.value}', try adding more details",
                        priority = SuggestionPriority.MEDIUM,
                        fieldAffected = fieldName
                    ))
                }
            }
            
            "start_datetime" -> {
                if (!fieldInfo.hasValue) {
                    suggestions.add(ImprovementSuggestion(
                        type = SuggestionType.ADD_SPECIFIC_DATE,
                        message = "Include a specific date and time",
                        example = "Try 'Meeting on Monday at 2 PM' or 'December 15th at 3:30 PM'",
                        priority = SuggestionPriority.HIGH,
                        fieldAffected = fieldName
                    ))
                } else if (fieldInfo.confidence < config.mediumConfidenceThreshold) {
                    if (originalText.contains(Regex("\\b(today|tomorrow|next week)\\b", RegexOption.IGNORE_CASE))) {
                        suggestions.add(ImprovementSuggestion(
                            type = SuggestionType.ADD_SPECIFIC_DATE,
                            message = "Use specific dates instead of relative terms",
                            example = "Instead of 'tomorrow', try 'December 16th' or 'Monday'",
                            priority = SuggestionPriority.MEDIUM,
                            fieldAffected = fieldName
                        ))
                    }
                    
                    if (!originalText.contains(Regex("\\d{1,2}:\\d{2}", RegexOption.IGNORE_CASE))) {
                        suggestions.add(ImprovementSuggestion(
                            type = SuggestionType.ADD_SPECIFIC_TIME,
                            message = "Include specific times",
                            example = "Try '2:30 PM' or '14:30' instead of 'afternoon'",
                            priority = SuggestionPriority.MEDIUM,
                            fieldAffected = fieldName
                        ))
                    }
                }
            }
            
            "location" -> {
                if (!fieldInfo.hasValue && originalText.contains(Regex("\\b(at|in|room|building)\\b", RegexOption.IGNORE_CASE))) {
                    suggestions.add(ImprovementSuggestion(
                        type = SuggestionType.ADD_LOCATION_DETAILS,
                        message = "Specify the location more clearly",
                        example = "Try 'Conference Room A' or '123 Main Street'",
                        priority = SuggestionPriority.LOW,
                        fieldAffected = fieldName
                    ))
                }
            }
        }
        
        return suggestions
    }
    
    /**
     * Generates general text improvement suggestions
     */
    private fun generateGeneralTextSuggestions(originalText: String, result: ParseResult): List<ImprovementSuggestion> {
        val suggestions = mutableListOf<ImprovementSuggestion>()
        
        // Check for ambiguous time references
        if (originalText.contains(Regex("\\b(morning|afternoon|evening|night)\\b", RegexOption.IGNORE_CASE)) &&
            !originalText.contains(Regex("\\d{1,2}:\\d{2}"))) {
            suggestions.add(ImprovementSuggestion(
                type = SuggestionType.IMPROVE_TIME_FORMAT,
                message = "Use specific times instead of general time periods",
                example = "Instead of 'morning', try '9:00 AM' or '10:30 AM'",
                priority = SuggestionPriority.MEDIUM,
                fieldAffected = null
            ))
        }
        
        // Check for very short text
        if (originalText.length < 15) {
            suggestions.add(ImprovementSuggestion(
                type = SuggestionType.ADD_CONTEXT,
                message = "Provide more context and details",
                example = "Try 'Team meeting on Monday at 2 PM in Conference Room A'",
                priority = SuggestionPriority.HIGH,
                fieldAffected = null
            ))
        }
        
        // Check for duration information
        if (!originalText.contains(Regex("\\b(for|until|to|duration|hours?|minutes?)\\b", RegexOption.IGNORE_CASE)) &&
            result.endDateTime.isNullOrBlank()) {
            suggestions.add(ImprovementSuggestion(
                type = SuggestionType.ADD_DURATION_INFO,
                message = "Include duration or end time",
                example = "Try 'Meeting from 2 PM to 3 PM' or 'Meeting for 1 hour'",
                priority = SuggestionPriority.LOW,
                fieldAffected = null
            ))
        }
        
        return suggestions
    }
    
    /**
     * Determines user recommendation based on assessment
     */
    private fun determineUserRecommendation(
        overallConfidence: Double,
        dataQualityScore: Double,
        missingCriticalFields: List<String>,
        lowConfidenceFields: List<String>
    ): UserRecommendation {
        
        // Block creation if critical fields are missing
        if (missingCriticalFields.isNotEmpty() && config.strictValidation) {
            return UserRecommendation.BLOCK_CREATION
        }
        
        // Recommend manual entry for very low confidence
        if (overallConfidence < config.criticalConfidenceThreshold) {
            return UserRecommendation.RECOMMEND_MANUAL_ENTRY
        }
        
        // Suggest improvements for low confidence
        if (overallConfidence < config.mediumConfidenceThreshold || dataQualityScore < 0.5) {
            return UserRecommendation.SUGGEST_IMPROVEMENTS
        }
        
        // Proceed with caution for medium confidence
        if (overallConfidence < config.highConfidenceThreshold || lowConfidenceFields.isNotEmpty()) {
            return UserRecommendation.PROCEED_WITH_CAUTION
        }
        
        // Proceed confidently for high confidence
        return UserRecommendation.PROCEED_CONFIDENTLY
    }
    
    /**
     * Generates warning message based on recommendation and issues
     */
    private fun generateWarningMessage(
        recommendation: UserRecommendation,
        overallConfidence: Double,
        missingCriticalFields: List<String>,
        lowConfidenceFields: List<String>
    ): Pair<String?, WarningSeverity> {
        
        return when (recommendation) {
            UserRecommendation.BLOCK_CREATION -> {
                val missingFieldsText = missingCriticalFields.joinToString(", ")
                Pair(
                    "Cannot create event: Missing critical information ($missingFieldsText). Please provide more details.",
                    WarningSeverity.CRITICAL
                )
            }
            
            UserRecommendation.RECOMMEND_MANUAL_ENTRY -> {
                Pair(
                    "The text is unclear and may not contain valid event information (${(overallConfidence * 100).toInt()}% confidence). Consider creating the event manually or rephrasing with clearer details.",
                    WarningSeverity.ERROR
                )
            }
            
            UserRecommendation.SUGGEST_IMPROVEMENTS -> {
                val lowFieldsText = if (lowConfidenceFields.isNotEmpty()) {
                    " Issues with: ${lowConfidenceFields.joinToString(", ")}"
                } else ""
                Pair(
                    "Event information has low confidence (${(overallConfidence * 100).toInt()}%).${lowFieldsText} Consider adding more specific details.",
                    WarningSeverity.WARNING
                )
            }
            
            UserRecommendation.PROCEED_WITH_CAUTION -> {
                Pair(
                    "Event information extracted with medium confidence (${(overallConfidence * 100).toInt()}%). Please review before creating.",
                    WarningSeverity.WARNING
                )
            }
            
            UserRecommendation.PROCEED_CONFIDENTLY -> {
                Pair(null, WarningSeverity.INFO)
            }
        }
    }
    
    /**
     * Determines if processing should proceed based on recommendation
     */
    private fun determineShouldProceed(recommendation: UserRecommendation, overallConfidence: Double): Boolean {
        return when (recommendation) {
            UserRecommendation.PROCEED_CONFIDENTLY -> true
            UserRecommendation.PROCEED_WITH_CAUTION -> true
            UserRecommendation.SUGGEST_IMPROVEMENTS -> !config.strictValidation
            UserRecommendation.RECOMMEND_MANUAL_ENTRY -> false
            UserRecommendation.BLOCK_CREATION -> false
        }
    }
    
    /**
     * Creates detailed analysis information
     */
    private fun createAnalysisDetails(
        result: ParseResult,
        originalText: String,
        fieldConfidences: Map<String, FieldConfidenceInfo>
    ): AnalysisDetails {
        
        val fieldsWithValues = fieldConfidences.values.count { it.hasValue }
        val fieldsWithHighConfidence = fieldConfidences.values.count { it.confidence >= config.highConfidenceThreshold }
        val fieldsWithMediumConfidence = fieldConfidences.values.count { 
            it.confidence >= config.mediumConfidenceThreshold && it.confidence < config.highConfidenceThreshold 
        }
        val fieldsWithLowConfidence = fieldConfidences.values.count { it.confidence < config.mediumConfidenceThreshold }
        
        val averageFieldConfidence = if (fieldsWithValues > 0) {
            fieldConfidences.values.filter { it.hasValue }.map { it.confidence }.average()
        } else {
            0.0
        }
        
        val textComplexityScore = calculateTextComplexityScore(originalText)
        
        val potentialIssues = mutableListOf<String>()
        fieldConfidences.values.forEach { fieldInfo ->
            potentialIssues.addAll(fieldInfo.issues)
        }
        
        return AnalysisDetails(
            totalFields = fieldConfidences.size,
            fieldsWithValues = fieldsWithValues,
            fieldsWithHighConfidence = fieldsWithHighConfidence,
            fieldsWithMediumConfidence = fieldsWithMediumConfidence,
            fieldsWithLowConfidence = fieldsWithLowConfidence,
            averageFieldConfidence = averageFieldConfidence,
            textComplexityScore = textComplexityScore,
            parsingMethodUsed = result.parsingPath,
            processingTimeMs = result.processingTimeMs.toLong(),
            potentialIssues = potentialIssues.distinct()
        )
    }
    
    /**
     * Creates a fallback assessment when analysis fails
     */
    private fun createFallbackAssessment(result: ParseResult, originalText: String): ConfidenceAssessment {
        return ConfidenceAssessment(
            overallConfidence = result.confidenceScore,
            fieldConfidences = emptyMap(),
            recommendation = if (result.confidenceScore < config.mediumConfidenceThreshold) {
                UserRecommendation.SUGGEST_IMPROVEMENTS
            } else {
                UserRecommendation.PROCEED_WITH_CAUTION
            },
            warningMessage = "Unable to perform detailed confidence analysis. Proceeding with basic assessment.",
            warningSeverity = WarningSeverity.WARNING,
            shouldProceed = result.confidenceScore >= config.criticalConfidenceThreshold,
            improvementSuggestions = emptyList(),
            dataQualityScore = result.confidenceScore,
            missingCriticalFields = emptyList(),
            lowConfidenceFields = emptyList(),
            analysisDetails = AnalysisDetails(
                totalFields = 0,
                fieldsWithValues = 0,
                fieldsWithHighConfidence = 0,
                fieldsWithMediumConfidence = 0,
                fieldsWithLowConfidence = 0,
                averageFieldConfidence = result.confidenceScore,
                textComplexityScore = 0.5,
                parsingMethodUsed = result.parsingPath,
                processingTimeMs = result.processingTimeMs.toLong(),
                potentialIssues = listOf("Analysis failed - using fallback assessment")
            )
        )
    }
    
    // Utility methods
    
    /**
     * Validates if a string represents a valid date/time
     */
    private fun isValidDateTime(dateTimeStr: String): Boolean {
        return try {
            val formats = listOf(
                "yyyy-MM-dd'T'HH:mm:ss",
                "yyyy-MM-dd'T'HH:mm:ss'Z'",
                "yyyy-MM-dd HH:mm:ss",
                "yyyy-MM-dd HH:mm",
                "yyyy-MM-dd"
            )
            
            formats.any { format ->
                try {
                    SimpleDateFormat(format, Locale.US).parse(dateTimeStr)
                    true
                } catch (e: Exception) {
                    false
                }
            }
        } catch (e: Exception) {
            false
        }
    }
    
    /**
     * Checks if a date/time is in the past
     */
    private fun isPastDateTime(dateTimeStr: String): Boolean {
        return try {
            val formats = listOf(
                "yyyy-MM-dd'T'HH:mm:ss",
                "yyyy-MM-dd'T'HH:mm:ss'Z'",
                "yyyy-MM-dd HH:mm:ss",
                "yyyy-MM-dd HH:mm",
                "yyyy-MM-dd"
            )
            
            for (format in formats) {
                try {
                    val date = SimpleDateFormat(format, Locale.US).parse(dateTimeStr)
                    return date?.before(Date()) ?: false
                } catch (e: Exception) {
                    continue
                }
            }
            false
        } catch (e: Exception) {
            false
        }
    }
    
    /**
     * Checks if end time is before start time
     */
    private fun isEndTimeBeforeStartTime(startDateTime: String, endDateTime: String): Boolean {
        return try {
            val formats = listOf(
                "yyyy-MM-dd'T'HH:mm:ss",
                "yyyy-MM-dd'T'HH:mm:ss'Z'",
                "yyyy-MM-dd HH:mm:ss",
                "yyyy-MM-dd HH:mm"
            )
            
            for (format in formats) {
                try {
                    val startDate = SimpleDateFormat(format, Locale.US).parse(startDateTime)
                    val endDate = SimpleDateFormat(format, Locale.US).parse(endDateTime)
                    
                    if (startDate != null && endDate != null) {
                        return endDate.before(startDate)
                    }
                } catch (e: Exception) {
                    continue
                }
            }
            false
        } catch (e: Exception) {
            false
        }
    }
    
    /**
     * Calculates text complexity score
     */
    private fun calculateTextComplexityScore(text: String): Double {
        var complexity = 0.5 // Base complexity
        
        // Length factor
        when {
            text.length < 20 -> complexity += 0.1
            text.length > 200 -> complexity += 0.3
            else -> complexity += 0.2
        }
        
        // Sentence count
        val sentences = text.split(Regex("[.!?]+")).filter { it.trim().isNotEmpty() }
        complexity += min(0.3, sentences.size * 0.05)
        
        // Word count
        val words = text.split(Regex("\\s+")).filter { it.isNotEmpty() }
        complexity += min(0.2, words.size * 0.01)
        
        return max(0.0, min(1.0, complexity))
    }
}