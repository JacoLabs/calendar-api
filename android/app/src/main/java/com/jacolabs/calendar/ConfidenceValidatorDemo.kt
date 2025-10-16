package com.jacolabs.calendar

import android.content.Context
import android.util.Log
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

/**
 * Demonstration class showing how to integrate ConfidenceValidator with the existing
 * error handling system and user interface components.
 */
class ConfidenceValidatorDemo(private val context: Context) {
    
    companion object {
        private const val TAG = "ConfidenceValidatorDemo"
    }
    
    private val confidenceValidator = ConfidenceValidator(context)
    private val errorHandlingManager = ErrorHandlingManager(context)
    
    /**
     * Demonstrates the complete confidence validation workflow
     */
    suspend fun demonstrateConfidenceValidation(
        parseResult: ParseResult,
        originalText: String
    ): ConfidenceValidationResult = withContext(Dispatchers.Default) {
        
        Log.d(TAG, "Starting confidence validation for text: ${originalText.take(50)}...")
        
        try {
            // Step 1: Assess confidence using ConfidenceValidator
            val assessment = confidenceValidator.assessConfidence(parseResult, originalText)
            
            Log.d(TAG, "Confidence assessment completed:")
            Log.d(TAG, "  Overall confidence: ${(assessment.overallConfidence * 100).toInt()}%")
            Log.d(TAG, "  Recommendation: ${assessment.recommendation}")
            Log.d(TAG, "  Should proceed: ${assessment.shouldProceed}")
            Log.d(TAG, "  Warning: ${assessment.warningMessage}")
            
            // Step 2: Handle the assessment result based on recommendation
            val handlingResult = when (assessment.recommendation) {
                ConfidenceValidator.UserRecommendation.PROCEED_CONFIDENTLY -> {
                    handleHighConfidenceResult(assessment, parseResult, originalText)
                }
                
                ConfidenceValidator.UserRecommendation.PROCEED_WITH_CAUTION -> {
                    handleMediumConfidenceResult(assessment, parseResult, originalText)
                }
                
                ConfidenceValidator.UserRecommendation.SUGGEST_IMPROVEMENTS -> {
                    handleLowConfidenceResult(assessment, parseResult, originalText)
                }
                
                ConfidenceValidator.UserRecommendation.RECOMMEND_MANUAL_ENTRY -> {
                    handleVeryLowConfidenceResult(assessment, parseResult, originalText)
                }
                
                ConfidenceValidator.UserRecommendation.BLOCK_CREATION -> {
                    handleBlockedResult(assessment, parseResult, originalText)
                }
            }
            
            // Step 3: Return comprehensive result
            ConfidenceValidationResult(
                assessment = assessment,
                handlingResult = handlingResult,
                success = handlingResult.success,
                finalResult = handlingResult.recoveredResult ?: parseResult,
                userMessage = handlingResult.userMessage,
                actionRequired = handlingResult.actionRequired
            )
            
        } catch (e: Exception) {
            Log.e(TAG, "Error during confidence validation", e)
            
            // Fallback to error handling manager
            val errorContext = ErrorHandlingManager.ErrorContext(
                errorType = ErrorHandlingManager.ErrorType.VALIDATION_ERROR,
                originalText = originalText,
                apiResponse = parseResult,
                exception = e
            )
            
            val fallbackResult = errorHandlingManager.handleError(errorContext)
            
            ConfidenceValidationResult(
                assessment = null,
                handlingResult = fallbackResult,
                success = fallbackResult.success,
                finalResult = fallbackResult.recoveredResult ?: parseResult,
                userMessage = fallbackResult.userMessage,
                actionRequired = fallbackResult.actionRequired
            )
        }
    }
    
    /**
     * Handles high confidence results - proceed directly
     */
    private suspend fun handleHighConfidenceResult(
        assessment: ConfidenceValidator.ConfidenceAssessment,
        parseResult: ParseResult,
        originalText: String
    ): ErrorHandlingManager.ErrorHandlingResult {
        
        Log.d(TAG, "Handling high confidence result - proceeding directly")
        
        return ErrorHandlingManager.ErrorHandlingResult(
            success = true,
            recoveryStrategy = ErrorHandlingManager.RecoveryStrategy.GRACEFUL_DEGRADATION,
            recoveredResult = parseResult,
            userMessage = "Event information extracted successfully with high confidence.",
            analyticsData = mapOf(
                "confidence_level" to "high",
                "overall_confidence" to assessment.overallConfidence,
                "fields_with_values" to assessment.analysisDetails.fieldsWithValues,
                "data_quality_score" to assessment.dataQualityScore
            )
        )
    }
    
    /**
     * Handles medium confidence results - proceed with user awareness
     */
    private suspend fun handleMediumConfidenceResult(
        assessment: ConfidenceValidator.ConfidenceAssessment,
        parseResult: ParseResult,
        originalText: String
    ): ErrorHandlingManager.ErrorHandlingResult {
        
        Log.d(TAG, "Handling medium confidence result - proceeding with caution")
        
        val warningMessage = assessment.warningMessage ?: 
            "Event information extracted with medium confidence. Please review before creating."
        
        return ErrorHandlingManager.ErrorHandlingResult(
            success = true,
            recoveryStrategy = ErrorHandlingManager.RecoveryStrategy.USER_CONFIRMATION_REQUIRED,
            recoveredResult = parseResult,
            userMessage = warningMessage,
            actionRequired = ErrorHandlingManager.UserAction.CONFIRM_LOW_CONFIDENCE_RESULT,
            analyticsData = mapOf(
                "confidence_level" to "medium",
                "overall_confidence" to assessment.overallConfidence,
                "low_confidence_fields" to assessment.lowConfidenceFields,
                "improvement_suggestions_count" to assessment.improvementSuggestions.size
            )
        )
    }
    
    /**
     * Handles low confidence results - suggest improvements
     */
    private suspend fun handleLowConfidenceResult(
        assessment: ConfidenceValidator.ConfidenceAssessment,
        parseResult: ParseResult,
        originalText: String
    ): ErrorHandlingManager.ErrorHandlingResult {
        
        Log.d(TAG, "Handling low confidence result - suggesting improvements")
        
        // Generate user-friendly improvement message
        val improvementMessage = generateImprovementMessage(assessment.improvementSuggestions)
        
        val userMessage = "${assessment.warningMessage ?: "Event information has low confidence."} $improvementMessage"
        
        return ErrorHandlingManager.ErrorHandlingResult(
            success = false,
            recoveryStrategy = ErrorHandlingManager.RecoveryStrategy.MANUAL_INPUT_SUGGESTION,
            userMessage = userMessage,
            actionRequired = ErrorHandlingManager.UserAction.RETRY_WITH_BETTER_TEXT,
            analyticsData = mapOf(
                "confidence_level" to "low",
                "overall_confidence" to assessment.overallConfidence,
                "missing_critical_fields" to assessment.missingCriticalFields,
                "improvement_suggestions" to assessment.improvementSuggestions.map { it.type.name },
                "data_quality_score" to assessment.dataQualityScore
            )
        )
    }
    
    /**
     * Handles very low confidence results - recommend manual entry
     */
    private suspend fun handleVeryLowConfidenceResult(
        assessment: ConfidenceValidator.ConfidenceAssessment,
        parseResult: ParseResult,
        originalText: String
    ): ErrorHandlingManager.ErrorHandlingResult {
        
        Log.d(TAG, "Handling very low confidence result - recommending manual entry")
        
        // Use error handling manager for fallback event creation
        val errorContext = ErrorHandlingManager.ErrorContext(
            errorType = ErrorHandlingManager.ErrorType.LOW_CONFIDENCE,
            originalText = originalText,
            apiResponse = parseResult,
            confidenceScore = assessment.overallConfidence
        )
        
        return errorHandlingManager.handleError(errorContext)
    }
    
    /**
     * Handles blocked results - cannot proceed
     */
    private suspend fun handleBlockedResult(
        assessment: ConfidenceValidator.ConfidenceAssessment,
        parseResult: ParseResult,
        originalText: String
    ): ErrorHandlingManager.ErrorHandlingResult {
        
        Log.d(TAG, "Handling blocked result - cannot proceed")
        
        val errorContext = ErrorHandlingManager.ErrorContext(
            errorType = ErrorHandlingManager.ErrorType.INSUFFICIENT_DATA,
            originalText = originalText,
            apiResponse = parseResult
        )
        
        return errorHandlingManager.handleError(errorContext)
    }
    
    /**
     * Generates user-friendly improvement message from suggestions
     */
    private fun generateImprovementMessage(suggestions: List<ConfidenceValidator.ImprovementSuggestion>): String {
        if (suggestions.isEmpty()) {
            return "Try providing more specific details about the event."
        }
        
        val topSuggestions = suggestions.take(3)
        val messages = mutableListOf<String>()
        
        topSuggestions.forEach { suggestion ->
            when (suggestion.type) {
                ConfidenceValidator.SuggestionType.ADD_SPECIFIC_DATE -> {
                    messages.add("include a specific date")
                }
                ConfidenceValidator.SuggestionType.ADD_SPECIFIC_TIME -> {
                    messages.add("add a specific time")
                }
                ConfidenceValidator.SuggestionType.CLARIFY_EVENT_TITLE -> {
                    messages.add("make the event title more descriptive")
                }
                ConfidenceValidator.SuggestionType.ADD_LOCATION_DETAILS -> {
                    messages.add("specify the location")
                }
                ConfidenceValidator.SuggestionType.IMPROVE_TIME_FORMAT -> {
                    messages.add("use clearer time format (e.g., '2:30 PM')")
                }
                ConfidenceValidator.SuggestionType.ADD_DURATION_INFO -> {
                    messages.add("include duration or end time")
                }
                ConfidenceValidator.SuggestionType.REMOVE_AMBIGUITY -> {
                    messages.add("remove ambiguous terms")
                }
                ConfidenceValidator.SuggestionType.USE_STANDARD_FORMAT -> {
                    messages.add("use standard date/time format")
                }
                ConfidenceValidator.SuggestionType.ADD_CONTEXT -> {
                    messages.add("provide more context")
                }
            }
        }
        
        return when (messages.size) {
            1 -> "Try to ${messages[0]}."
            2 -> "Try to ${messages[0]} and ${messages[1]}."
            else -> "Try to ${messages.dropLast(1).joinToString(", ")} and ${messages.last()}."
        }
    }
    
    /**
     * Demonstrates field-level confidence analysis
     */
    fun demonstrateFieldAnalysis(parseResult: ParseResult, originalText: String) {
        Log.d(TAG, "=== Field-Level Confidence Analysis ===")
        
        val assessment = confidenceValidator.assessConfidence(parseResult, originalText)
        
        assessment.fieldConfidences.forEach { (fieldName, fieldInfo) ->
            Log.d(TAG, "Field: $fieldName")
            Log.d(TAG, "  Value: ${fieldInfo.value}")
            Log.d(TAG, "  Confidence: ${(fieldInfo.confidence * 100).toInt()}%")
            Log.d(TAG, "  Quality Score: ${(fieldInfo.qualityScore * 100).toInt()}%")
            Log.d(TAG, "  Source: ${fieldInfo.source}")
            Log.d(TAG, "  Required: ${fieldInfo.isRequired}")
            Log.d(TAG, "  Issues: ${fieldInfo.issues}")
            Log.d(TAG, "")
        }
        
        Log.d(TAG, "Analysis Summary:")
        Log.d(TAG, "  Total Fields: ${assessment.analysisDetails.totalFields}")
        Log.d(TAG, "  Fields with Values: ${assessment.analysisDetails.fieldsWithValues}")
        Log.d(TAG, "  High Confidence Fields: ${assessment.analysisDetails.fieldsWithHighConfidence}")
        Log.d(TAG, "  Medium Confidence Fields: ${assessment.analysisDetails.fieldsWithMediumConfidence}")
        Log.d(TAG, "  Low Confidence Fields: ${assessment.analysisDetails.fieldsWithLowConfidence}")
        Log.d(TAG, "  Average Field Confidence: ${(assessment.analysisDetails.averageFieldConfidence * 100).toInt()}%")
        Log.d(TAG, "  Data Quality Score: ${(assessment.dataQualityScore * 100).toInt()}%")
    }
    
    /**
     * Demonstrates improvement suggestions
     */
    fun demonstrateImprovementSuggestions(parseResult: ParseResult, originalText: String) {
        Log.d(TAG, "=== Improvement Suggestions ===")
        
        val suggestions = confidenceValidator.generateImprovementSuggestions(originalText, parseResult)
        
        if (suggestions.isEmpty()) {
            Log.d(TAG, "No improvement suggestions needed - text is clear!")
            return
        }
        
        suggestions.forEachIndexed { index, suggestion ->
            Log.d(TAG, "${index + 1}. ${suggestion.message}")
            Log.d(TAG, "   Type: ${suggestion.type}")
            Log.d(TAG, "   Priority: ${suggestion.priority}")
            suggestion.example?.let { example ->
                Log.d(TAG, "   Example: $example")
            }
            suggestion.fieldAffected?.let { field ->
                Log.d(TAG, "   Affects: $field")
            }
            Log.d(TAG, "")
        }
    }
    
    /**
     * Result of the complete confidence validation workflow
     */
    data class ConfidenceValidationResult(
        val assessment: ConfidenceValidator.ConfidenceAssessment?,
        val handlingResult: ErrorHandlingManager.ErrorHandlingResult,
        val success: Boolean,
        val finalResult: ParseResult,
        val userMessage: String,
        val actionRequired: ErrorHandlingManager.UserAction?
    )
}

/**
 * Example usage and integration patterns
 */
class ConfidenceValidatorIntegrationExample {
    
    companion object {
        private const val TAG = "ConfidenceValidatorIntegration"
        
        /**
         * Example of integrating ConfidenceValidator into the main parsing workflow
         */
        suspend fun integrateWithMainWorkflow(
            context: Context,
            apiService: ApiService,
            originalText: String
        ): ParseResult? {
            
            return try {
                // Step 1: Get parsing result from API
                val parseResult = apiService.parseText(
                    text = originalText,
                    timezone = "UTC",
                    locale = "en-US",
                    now = java.util.Date()
                )
                
                // Step 2: Validate confidence
                val confidenceValidator = ConfidenceValidator(context)
                val assessment = confidenceValidator.assessConfidence(parseResult, originalText)
                
                // Step 3: Handle based on confidence
                when (assessment.recommendation) {
                    ConfidenceValidator.UserRecommendation.PROCEED_CONFIDENTLY -> {
                        Log.d(TAG, "High confidence - proceeding with result")
                        parseResult
                    }
                    
                    ConfidenceValidator.UserRecommendation.PROCEED_WITH_CAUTION -> {
                        Log.d(TAG, "Medium confidence - showing warning to user")
                        // In real app, show warning dialog here
                        parseResult
                    }
                    
                    ConfidenceValidator.UserRecommendation.SUGGEST_IMPROVEMENTS -> {
                        Log.d(TAG, "Low confidence - suggesting improvements")
                        // In real app, show improvement suggestions to user
                        null // Don't proceed automatically
                    }
                    
                    ConfidenceValidator.UserRecommendation.RECOMMEND_MANUAL_ENTRY -> {
                        Log.d(TAG, "Very low confidence - recommending manual entry")
                        // In real app, offer manual event creation
                        null
                    }
                    
                    ConfidenceValidator.UserRecommendation.BLOCK_CREATION -> {
                        Log.d(TAG, "Insufficient data - blocking creation")
                        null
                    }
                }
                
            } catch (e: Exception) {
                Log.e(TAG, "Error in confidence validation workflow", e)
                null
            }
        }
        
        /**
         * Example of using ConfidenceValidator for user feedback
         */
        fun generateUserFeedback(
            context: Context,
            parseResult: ParseResult,
            originalText: String
        ): UserFeedbackInfo {
            
            val confidenceValidator = ConfidenceValidator(context)
            val assessment = confidenceValidator.assessConfidence(parseResult, originalText)
            
            return UserFeedbackInfo(
                shouldShowWarning = assessment.warningMessage != null,
                warningMessage = assessment.warningMessage,
                confidencePercentage = (assessment.overallConfidence * 100).toInt(),
                improvementSuggestions = assessment.improvementSuggestions.take(3).map { it.message },
                canProceed = assessment.shouldProceed,
                fieldIssues = assessment.fieldConfidences.values
                    .filter { it.issues.isNotEmpty() }
                    .associate { it.fieldName to it.issues }
            )
        }
        
        data class UserFeedbackInfo(
            val shouldShowWarning: Boolean,
            val warningMessage: String?,
            val confidencePercentage: Int,
            val improvementSuggestions: List<String>,
            val canProceed: Boolean,
            val fieldIssues: Map<String, List<String>>
        )
    }
}