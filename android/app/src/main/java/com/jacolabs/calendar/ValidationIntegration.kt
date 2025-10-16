package com.jacolabs.calendar

import android.content.Context
import android.util.Log
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

/**
 * Integration layer that connects data validation with the existing error handling system.
 * Provides seamless integration between validation, sanitization, and error recovery.
 */
class ValidationIntegration(
    private val context: Context,
    private val errorHandlingManager: ErrorHandlingManager,
    private val dataValidationManager: DataValidationManager = DataValidationManager(context),
    private val validationConfig: ValidationConfig = ValidationConfig(context)
) {
    
    companion object {
        private const val TAG = "ValidationIntegration"
    }
    
    /**
     * Validates ParseResult and handles any validation errors through the error handling system
     */
    suspend fun validateWithErrorHandling(
        result: ParseResult,
        originalText: String
    ): ErrorHandlingManager.ErrorHandlingResult = withContext(Dispatchers.Default) {
        
        Log.d(TAG, "Starting integrated validation for ParseResult")
        
        try {
            // Perform comprehensive validation
            val validationResult = dataValidationManager.validateAndSanitize(result, originalText)
            
            // If validation passed, return success with sanitized result
            if (validationResult.isValid) {
                return@withContext ErrorHandlingManager.ErrorHandlingResult(
                    success = true,
                    recoveryStrategy = ErrorHandlingManager.RecoveryStrategy.GRACEFUL_DEGRADATION,
                    recoveredResult = validationResult.sanitizedResult,
                    userMessage = generateSuccessMessage(validationResult),
                    analyticsData = mapOf(
                        "validation_passed" to true,
                        "issues_count" to validationResult.issues.size,
                        "warnings_count" to validationResult.warnings.size,
                        "data_integrity_score" to validationResult.dataIntegrityScore,
                        "applied_defaults" to validationResult.appliedDefaults.keys.toList()
                    )
                )
            }
            
            // Validation failed - determine error type and handle through error system
            val errorType = determineErrorType(validationResult)
            val errorContext = ErrorHandlingManager.ErrorContext(
                errorType = errorType,
                originalText = originalText,
                apiResponse = result,
                confidenceScore = result.confidenceScore
            )
            
            // Handle through error handling system
            val errorResult = errorHandlingManager.handleError(errorContext)
            
            // Enhance error result with validation information
            return@withContext errorResult.copy(
                userMessage = enhanceErrorMessage(errorResult.userMessage, validationResult),
                analyticsData = errorResult.analyticsData + mapOf(
                    "validation_failed" to true,
                    "validation_issues" to validationResult.issues.map { "${it.field}:${it.code}" },
                    "data_integrity_score" to validationResult.dataIntegrityScore
                )
            )
            
        } catch (e: Exception) {
            Log.e(TAG, "Validation integration failed", e)
            
            // Fallback to error handling system
            val errorContext = ErrorHandlingManager.ErrorContext(
                errorType = ErrorHandlingManager.ErrorType.VALIDATION_ERROR,
                originalText = originalText,
                apiResponse = result,
                exception = e
            )
            
            return@withContext errorHandlingManager.handleError(errorContext)
        }
    }
    
    /**
     * Quick validation check for essential fields
     */
    fun hasEssentialData(result: ParseResult): Boolean {
        return dataValidationManager.validateEssentialFields(result)
    }
    
    /**
     * Validates and sanitizes data before calendar creation
     */
    suspend fun prepareForCalendarCreation(
        result: ParseResult,
        originalText: String
    ): PreparedEventData = withContext(Dispatchers.Default) {
        
        val validationResult = dataValidationManager.validateAndSanitize(result, originalText)
        
        PreparedEventData(
            sanitizedResult = validationResult.sanitizedResult,
            isReady = validationResult.isValid,
            validationSummary = dataValidationManager.getValidationSummary(validationResult),
            userWarnings = validationResult.warnings,
            userSuggestions = validationResult.suggestions,
            confidenceAssessment = validationResult.confidenceAssessment,
            requiresUserConfirmation = shouldRequireConfirmation(validationResult)
        )
    }
    
    /**
     * Data class for prepared event data ready for calendar creation
     */
    data class PreparedEventData(
        val sanitizedResult: ParseResult,
        val isReady: Boolean,
        val validationSummary: String,
        val userWarnings: List<String>,
        val userSuggestions: List<String>,
        val confidenceAssessment: DataValidationManager.ConfidenceAssessment,
        val requiresUserConfirmation: Boolean
    )
    
    /**
     * Determines error type based on validation results
     */
    private fun determineErrorType(validationResult: DataValidationManager.ValidationResult): ErrorHandlingManager.ErrorType {
        val criticalIssues = validationResult.issues.filter { 
            it.severity == DataValidationManager.ValidationSeverity.ERROR 
        }
        
        return when {
            criticalIssues.any { it.code.contains("MISSING_ESSENTIAL") } -> {
                ErrorHandlingManager.ErrorType.INSUFFICIENT_DATA
            }
            criticalIssues.any { it.code.contains("INVALID_FORMAT") } -> {
                ErrorHandlingManager.ErrorType.VALIDATION_ERROR
            }
            validationResult.confidenceAssessment.overallConfidence < validationConfig.minConfidenceThreshold -> {
                ErrorHandlingManager.ErrorType.LOW_CONFIDENCE
            }
            else -> ErrorHandlingManager.ErrorType.VALIDATION_ERROR
        }
    }
    
    /**
     * Generates success message with validation information
     */
    private fun generateSuccessMessage(validationResult: DataValidationManager.ValidationResult): String {
        val baseMessage = "Event data validated successfully"
        
        return when {
            validationResult.warnings.isNotEmpty() -> {
                "$baseMessage with ${validationResult.warnings.size} minor adjustments"
            }
            validationResult.appliedDefaults.isNotEmpty() -> {
                "$baseMessage with smart defaults applied"
            }
            else -> baseMessage
        }
    }
    
    /**
     * Enhances error message with validation details
     */
    private fun enhanceErrorMessage(
        originalMessage: String,
        validationResult: DataValidationManager.ValidationResult
    ): String {
        val criticalIssues = validationResult.issues.filter { 
            it.severity == DataValidationManager.ValidationSeverity.ERROR 
        }
        
        if (criticalIssues.isEmpty()) return originalMessage
        
        val issueDescriptions = criticalIssues.take(2).map { it.message }
        val additionalIssues = if (criticalIssues.size > 2) " and ${criticalIssues.size - 2} other issues" else ""
        
        return "$originalMessage Issues found: ${issueDescriptions.joinToString(", ")}$additionalIssues"
    }
    
    /**
     * Determines if user confirmation is required based on validation results
     */
    private fun shouldRequireConfirmation(validationResult: DataValidationManager.ValidationResult): Boolean {
        return when {
            // High confidence and no warnings - no confirmation needed
            validationResult.confidenceAssessment.overallConfidence >= validationConfig.warningConfidenceThreshold &&
            validationResult.warnings.isEmpty() -> false
            
            // Low confidence - always require confirmation
            validationResult.confidenceAssessment.overallConfidence < validationConfig.minConfidenceThreshold -> true
            
            // Significant defaults applied - require confirmation
            validationResult.appliedDefaults.size >= 2 -> true
            
            // Multiple warnings - require confirmation
            validationResult.warnings.size >= 3 -> true
            
            // Default to requiring confirmation for safety
            else -> true
        }
    }
    
    /**
     * Gets validation configuration for UI display
     */
    fun getValidationConfig(): ValidationConfig = validationConfig
    
    /**
     * Updates validation configuration
     */
    fun updateValidationConfig(updates: Map<String, Any>) {
        updates.forEach { (key, value) ->
            when (key) {
                "minConfidenceThreshold" -> validationConfig.minConfidenceThreshold = value as Double
                "warningConfidenceThreshold" -> validationConfig.warningConfidenceThreshold = value as Double
                "maxTitleLength" -> validationConfig.maxTitleLength = value as Int
                "maxDescriptionLength" -> validationConfig.maxDescriptionLength = value as Int
                "maxLocationLength" -> validationConfig.maxLocationLength = value as Int
                "enableStrictValidation" -> validationConfig.enableStrictValidation = value as Boolean
                "enableAutoSanitization" -> validationConfig.enableAutoSanitization = value as Boolean
                "enableSmartDefaults" -> validationConfig.enableSmartDefaults = value as Boolean
            }
        }
    }
    
    /**
     * Performs lightweight validation for real-time feedback
     */
    fun validateQuick(result: ParseResult): QuickValidationResult {
        val hasTitle = !result.title.isNullOrBlank()
        val hasStartTime = !result.startDateTime.isNullOrBlank()
        val hasGoodConfidence = result.confidenceScore >= validationConfig.minConfidenceThreshold
        
        return QuickValidationResult(
            hasEssentialData = hasTitle && hasStartTime,
            confidenceLevel = when {
                result.confidenceScore >= validationConfig.warningConfidenceThreshold -> ConfidenceLevel.HIGH
                result.confidenceScore >= validationConfig.minConfidenceThreshold -> ConfidenceLevel.MEDIUM
                else -> ConfidenceLevel.LOW
            },
            readyForCreation = hasTitle && hasStartTime && hasGoodConfidence
        )
    }
    
    /**
     * Quick validation result for UI feedback
     */
    data class QuickValidationResult(
        val hasEssentialData: Boolean,
        val confidenceLevel: ConfidenceLevel,
        val readyForCreation: Boolean
    )
    
    /**
     * Confidence levels for UI display
     */
    enum class ConfidenceLevel {
        HIGH, MEDIUM, LOW
    }
}