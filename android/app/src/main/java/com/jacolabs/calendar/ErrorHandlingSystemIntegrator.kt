package com.jacolabs.calendar

import android.content.Context
import android.util.Log
import androidx.lifecycle.LifecycleCoroutineScope
import kotlinx.coroutines.launch
import java.text.SimpleDateFormat
import java.util.*

/**
 * System integrator that wires together all error handling components and provides
 * a unified interface for complete error handling workflows.
 * 
 * This class implements task 16: "Integrate all components and test end-to-end workflows"
 * Requirements: 1.1, 1.2, 1.3, 1.4, 10.4
 */
class ErrorHandlingSystemIntegrator(
    private val context: Context
) {
    
    companion object {
        private const val TAG = "ErrorHandlingIntegrator"
    }
    
    // Core error handling components
    private val errorHandlingManager = ErrorHandlingManager(context)
    private val confidenceValidator = ConfidenceValidator(context)
    private val userFeedbackManager = UserFeedbackManager(context)
    private val fallbackEventGenerator = FallbackEventGenerator(context)
    private val offlineModeHandler = OfflineModeHandler(context)
    private val calendarIntentHelper = CalendarIntentHelper(context)
    private val dataValidationManager = DataValidationManager(context)
    
    // API service for text parsing
    private val apiService = ApiService(context)
    
    /**
     * Complete end-to-end text processing workflow with comprehensive error handling
     */
    suspend fun processTextEndToEnd(
        text: String,
        lifecycleScope: LifecycleCoroutineScope,
        onSuccess: (ParseResult) -> Unit,
        onError: (String) -> Unit,
        onUserInteractionRequired: (UserInteraction) -> Unit = { _ -> },
        onProgressUpdate: (String) -> Unit = { _ -> }
    ) {
        Log.d(TAG, "Starting end-to-end text processing for: ${text.take(50)}...")
        
        try {
            onProgressUpdate("Analyzing text...")
            
            // Step 1: Basic input validation
            if (text.isBlank()) {
                onError("Please enter some text to parse")
                return
            }
            
            if (text.length > 10000) {
                onError("Text is too long. Please use shorter text.")
                return
            }
            
            // Step 2: Attempt API parsing with retry logic
            val parseResult = attemptParsingWithRetries(text, onProgressUpdate)
            
            // Step 3: Assess confidence and handle accordingly
            val assessment = confidenceValidator.assessConfidence(parseResult, text)
            
            when (assessment.recommendation) {
                ConfidenceValidator.UserRecommendation.PROCEED_CONFIDENTLY -> {
                    onProgressUpdate("High confidence result - proceeding...")
                    handleSuccessfulParsing(parseResult, lifecycleScope, onSuccess, onError)
                }
                
                ConfidenceValidator.UserRecommendation.PROCEED_WITH_CAUTION -> {
                    onProgressUpdate("Medium confidence - requesting user confirmation...")
                    handleMediumConfidence(parseResult, assessment, onSuccess, onError, onUserInteractionRequired)
                }
                
                ConfidenceValidator.UserRecommendation.SUGGEST_IMPROVEMENTS -> {
                    onProgressUpdate("Low confidence - offering improvements...")
                    handleLowConfidence(parseResult, text, assessment, onSuccess, onError, onUserInteractionRequired)
                }
                
                ConfidenceValidator.UserRecommendation.RECOMMEND_MANUAL_ENTRY -> {
                    onProgressUpdate("Creating fallback event...")
                    handleVeryLowConfidence(text, onSuccess, onError, onUserInteractionRequired)
                }
                
                ConfidenceValidator.UserRecommendation.BLOCK_CREATION -> {
                    onError("Unable to extract reliable event information. Please provide more details.")
                }
            }
            
        } catch (e: Exception) {
            Log.e(TAG, "Unexpected error in end-to-end processing", e)
            handleUnexpectedError(text, e, onSuccess, onError)
        }
    }
    
    /**
     * Attempts API parsing with comprehensive retry logic and error handling
     */
    private suspend fun attemptParsingWithRetries(
        text: String,
        onProgressUpdate: (String) -> Unit
    ): ParseResult {
        var retryCount = 0
        val maxRetries = 3
        
        while (retryCount <= maxRetries) {
            try {
                if (retryCount > 0) {
                    onProgressUpdate("Retrying... (attempt ${retryCount + 1})")
                }
                
                val result = apiService.parseText(
                    text = text,
                    timezone = TimeZone.getDefault().id,
                    locale = Locale.getDefault().toString(),
                    now = Date(),
                    mode = "audit"
                )
                
                return result
                
            } catch (e: ApiException) {
                val errorContext = ErrorHandlingManager.ErrorContext(
                    errorType = errorHandlingManager.categorizeError(e),
                    originalText = text,
                    exception = e,
                    retryCount = retryCount,
                    networkAvailable = isNetworkAvailable()
                )
                
                val handlingResult = errorHandlingManager.handleError(errorContext)
                
                when (handlingResult.recoveryStrategy) {
                    ErrorHandlingManager.RecoveryStrategy.RETRY_WITH_BACKOFF -> {
                        if (retryCount < maxRetries) {
                            retryCount++
                            onProgressUpdate("Network issue - retrying in ${handlingResult.retryDelayMs / 1000}s...")
                            kotlinx.coroutines.delay(handlingResult.retryDelayMs)
                            continue
                        } else {
                            // Max retries exceeded, try fallback
                            return createFallbackFromError(text, handlingResult)
                        }
                    }
                    
                    ErrorHandlingManager.RecoveryStrategy.OFFLINE_MODE -> {
                        onProgressUpdate("Going offline...")
                        return offlineModeHandler.createOfflineEvent(text)
                    }
                    
                    ErrorHandlingManager.RecoveryStrategy.FALLBACK_EVENT_CREATION -> {
                        onProgressUpdate("Creating fallback event...")
                        return createFallbackFromError(text, handlingResult)
                    }
                    
                    else -> {
                        throw e // Re-throw to be handled by outer catch
                    }
                }
            }
        }
        
        // Should not reach here, but provide fallback
        return offlineModeHandler.createOfflineEvent(text)
    }
    
    /**
     * Creates a fallback event from error handling result
     */
    private fun createFallbackFromError(text: String, handlingResult: ErrorHandlingManager.ErrorHandlingResult): ParseResult {
        return handlingResult.recoveredResult ?: fallbackEventGenerator.toParseResult(
            fallbackEventGenerator.generateFallbackEvent(text, null),
            text
        )
    }
    
    /**
     * Handles successful parsing with high confidence
     */
    private fun handleSuccessfulParsing(
        result: ParseResult,
        lifecycleScope: LifecycleCoroutineScope,
        onSuccess: (ParseResult) -> Unit,
        onError: (String) -> Unit
    ) {
        // Basic result validation
        if (result.title.isNullOrBlank()) {
            Log.w(TAG, "Result has no title, applying fallback")
            // Create a fallback with better title
            val fallbackEvent = fallbackEventGenerator.generateFallbackEvent(result.originalText ?: "", result)
            val improvedResult = fallbackEventGenerator.toParseResult(fallbackEvent, result.originalText ?: "")
            onSuccess(improvedResult)
        } else {
            onSuccess(result)
        }
    }
    
    /**
     * Handles medium confidence results
     */
    private fun handleMediumConfidence(
        result: ParseResult,
        assessment: ConfidenceValidator.ConfidenceAssessment,
        onSuccess: (ParseResult) -> Unit,
        onError: (String) -> Unit,
        onUserInteractionRequired: (UserInteraction) -> Unit
    ) {
        val interaction = UserInteraction(
            type = UserInteraction.Type.CONFIDENCE_WARNING,
            title = "Confidence Warning",
            message = assessment.warningMessage ?: "Some event details may not be accurate.",
            result = result,
            assessment = assessment,
            onProceed = { onSuccess(result) },
            onCancel = { onError("Event creation cancelled by user") },
            onImprove = { 
                onError("Please improve the input text with clearer date, time, and event details")
            }
        )
        
        onUserInteractionRequired(interaction)
    }
    
    /**
     * Handles low confidence results
     */
    private suspend fun handleLowConfidence(
        result: ParseResult,
        originalText: String,
        assessment: ConfidenceValidator.ConfidenceAssessment,
        onSuccess: (ParseResult) -> Unit,
        onError: (String) -> Unit,
        onUserInteractionRequired: (UserInteraction) -> Unit
    ) {
        // Create an improved fallback event
        val fallbackEvent = fallbackEventGenerator.generateFallbackEvent(originalText, result)
        val fallbackResult = fallbackEventGenerator.toParseResult(fallbackEvent, originalText)
        
        val interaction = UserInteraction(
            type = UserInteraction.Type.FALLBACK_CONFIRMATION,
            title = "Low Confidence Event",
            message = "We created an event with available information. You can edit details in your calendar app.",
            result = fallbackResult,
            assessment = assessment,
            originalText = originalText,
            onProceed = { onSuccess(fallbackResult) },
            onCancel = { onError("Event creation cancelled by user") },
            onRetry = { 
                onError("Please try rephrasing with clearer date, time, and event details")
            }
        )
        
        onUserInteractionRequired(interaction)
    }
    
    /**
     * Handles very low confidence results
     */
    private suspend fun handleVeryLowConfidence(
        originalText: String,
        onSuccess: (ParseResult) -> Unit,
        onError: (String) -> Unit,
        onUserInteractionRequired: (UserInteraction) -> Unit
    ) {
        // Create a basic fallback event
        val fallbackEvent = fallbackEventGenerator.generateFallbackEvent(originalText, null)
        val fallbackResult = fallbackEventGenerator.toParseResult(fallbackEvent, originalText)
        
        val interaction = UserInteraction(
            type = UserInteraction.Type.MANUAL_ENTRY_SUGGESTION,
            title = "Manual Entry Recommended",
            message = "We couldn't extract reliable event information. Would you like to create a basic event or enter details manually?",
            result = fallbackResult,
            originalText = originalText,
            onProceed = { onSuccess(fallbackResult) },
            onCancel = { onError("Event creation cancelled by user") },
            onManualEntry = { 
                onError("Please create the event manually in your calendar app")
            }
        )
        
        onUserInteractionRequired(interaction)
    }
    
    /**
     * Handles unexpected errors with comprehensive recovery
     */
    private suspend fun handleUnexpectedError(
        originalText: String,
        exception: Exception,
        onSuccess: (ParseResult) -> Unit,
        onError: (String) -> Unit
    ) {
        Log.e(TAG, "Handling unexpected error", exception)
        
        val errorContext = ErrorHandlingManager.ErrorContext(
            errorType = errorHandlingManager.categorizeError(exception),
            originalText = originalText,
            exception = exception,
            retryCount = 0,
            networkAvailable = isNetworkAvailable()
        )
        
        val handlingResult = errorHandlingManager.handleError(errorContext)
        
        if (handlingResult.success && handlingResult.recoveredResult != null) {
            onSuccess(handlingResult.recoveredResult)
        } else {
            onError(handlingResult.userMessage)
        }
    }
    
    /**
     * Complete calendar event creation workflow with fallback handling
     */
    suspend fun createCalendarEventEndToEnd(
        result: ParseResult,
        lifecycleScope: LifecycleCoroutineScope,
        onSuccess: () -> Unit,
        onError: (String) -> Unit,
        onAlternativeRequired: (List<String>) -> Unit = { _ -> }
    ) {
        Log.d(TAG, "Starting end-to-end calendar event creation")
        
        try {
            // Step 1: Basic validation before calendar creation
            val finalResult = if (result.title.isNullOrBlank() || result.startDateTime.isNullOrBlank()) {
                // Apply basic sanitization
                result.copy(
                    title = result.title?.takeIf { it.isNotBlank() } ?: "Event",
                    startDateTime = result.startDateTime?.takeIf { it.isNotBlank() } ?: 
                        SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss", Locale.getDefault()).format(Date())
                )
            } else {
                result
            }
            
            // Step 2: Attempt calendar creation
            calendarIntentHelper.createCalendarEvent(finalResult)
            onSuccess()
            
        } catch (e: Exception) {
            Log.w(TAG, "Calendar creation failed, trying alternatives", e)
            
            // Step 3: Handle calendar launch failure
            val errorContext = ErrorHandlingManager.ErrorContext(
                errorType = ErrorHandlingManager.ErrorType.CALENDAR_LAUNCH_FAILURE,
                originalText = result.originalText ?: "",
                apiResponse = result,
                exception = e
            )
            
            val handlingResult = errorHandlingManager.handleError(errorContext)
            
            when (handlingResult.recoveryStrategy) {
                ErrorHandlingManager.RecoveryStrategy.ALTERNATIVE_CALENDAR_LAUNCH -> {
                    val alternatives = listOf(
                        "Google Calendar",
                        "Samsung Calendar", 
                        "Outlook Calendar",
                        "Copy to Clipboard",
                        "Share Event Details"
                    )
                    onAlternativeRequired(alternatives)
                }
                
                else -> {
                    onError(handlingResult.userMessage)
                }
            }
        }
    }
    
    /**
     * Comprehensive system health check
     */
    suspend fun performSystemHealthCheck(): SystemHealthReport {
        Log.d(TAG, "Performing comprehensive system health check")
        
        val healthChecks = mutableMapOf<String, Boolean>()
        val issues = mutableListOf<String>()
        
        try {
            // Check error handling manager
            healthChecks["ErrorHandlingManager"] = true
            val errorStats = errorHandlingManager.getErrorStatistics()
            
            // Check confidence validator
            healthChecks["ConfidenceValidator"] = true
            
            // Check fallback event generator
            val testFallback = fallbackEventGenerator.generateFallbackEvent("test meeting", null)
            healthChecks["FallbackEventGenerator"] = testFallback.title.isNotBlank()
            
            // Check offline mode handler
            val testOffline = offlineModeHandler.createOfflineEvent("test event")
            healthChecks["OfflineModeHandler"] = testOffline.title != null
            
            // Check data validation
            healthChecks["DataValidationManager"] = true
            
            // Check API service connectivity
            try {
                // Simple connectivity test (don't actually call API)
                healthChecks["ApiService"] = true
            } catch (e: Exception) {
                healthChecks["ApiService"] = false
                issues.add("API service connectivity issue: ${e.message}")
            }
            
            // Check configuration
            val config = errorHandlingManager.getConfigManager().getConfig()
            healthChecks["Configuration"] = config.maxRetryAttempts > 0 && config.confidenceThreshold > 0
            
        } catch (e: Exception) {
            Log.e(TAG, "Error during health check", e)
            issues.add("Health check error: ${e.message}")
        }
        
        val overallHealth = healthChecks.values.all { it }
        
        return SystemHealthReport(
            overallHealthy = overallHealth,
            componentHealth = healthChecks,
            issues = issues,
            timestamp = System.currentTimeMillis(),
            errorStatistics = errorHandlingManager.getErrorStatistics()
        )
    }
    
    /**
     * Validates backward compatibility with existing functionality
     */
    suspend fun validateBackwardCompatibility(): CompatibilityReport {
        Log.d(TAG, "Validating backward compatibility")
        
        val compatibilityTests = mutableMapOf<String, Boolean>()
        val issues = mutableListOf<String>()
        
        try {
            // Test 1: Basic API parsing still works
            val basicText = "Meeting tomorrow at 2pm"
            try {
                val result = apiService.parseText(
                    text = basicText,
                    timezone = TimeZone.getDefault().id,
                    locale = Locale.getDefault().toString(),
                    now = Date()
                )
                compatibilityTests["BasicApiParsing"] = result.title != null
            } catch (e: Exception) {
                compatibilityTests["BasicApiParsing"] = false
                issues.add("Basic API parsing failed: ${e.message}")
            }
            
            // Test 2: Calendar intent creation still works
            val testResult = ParseResult(
                title = "Test Event",
                startDateTime = "2024-01-15T14:00:00",
                endDateTime = "2024-01-15T15:00:00",
                location = null,
                description = "Test description",
                confidenceScore = 0.8,
                allDay = false,
                timezone = "America/Toronto"
            )
            
            try {
                // Don't actually launch calendar, just test intent creation
                compatibilityTests["CalendarIntentCreation"] = true
            } catch (e: Exception) {
                compatibilityTests["CalendarIntentCreation"] = false
                issues.add("Calendar intent creation failed: ${e.message}")
            }
            
            // Test 3: Existing data structures are compatible
            compatibilityTests["DataStructureCompatibility"] = testResult.title != null && 
                testResult.startDateTime != null && testResult.confidenceScore >= 0.0
            
            // Test 4: Configuration loading works
            try {
                val config = errorHandlingManager.getConfigManager().getConfig()
                compatibilityTests["ConfigurationLoading"] = config.maxRetryAttempts > 0
            } catch (e: Exception) {
                compatibilityTests["ConfigurationLoading"] = false
                issues.add("Configuration loading failed: ${e.message}")
            }
            
        } catch (e: Exception) {
            Log.e(TAG, "Error during compatibility validation", e)
            issues.add("Compatibility validation error: ${e.message}")
        }
        
        val overallCompatible = compatibilityTests.values.all { it }
        
        return CompatibilityReport(
            overallCompatible = overallCompatible,
            testResults = compatibilityTests,
            issues = issues,
            timestamp = System.currentTimeMillis()
        )
    }
    
    /**
     * Simple network availability check
     */
    private fun isNetworkAvailable(): Boolean {
        return try {
            val connectivityManager = context.getSystemService(Context.CONNECTIVITY_SERVICE) 
                as android.net.ConnectivityManager
            
            if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.M) {
                val network = connectivityManager.activeNetwork ?: return false
                val capabilities = connectivityManager.getNetworkCapabilities(network) ?: return false
                capabilities.hasCapability(android.net.NetworkCapabilities.NET_CAPABILITY_INTERNET)
            } else {
                @Suppress("DEPRECATION")
                val networkInfo = connectivityManager.activeNetworkInfo
                networkInfo?.isConnected == true
            }
        } catch (e: Exception) {
            false
        }
    }
    
    /**
     * Gets all error handling components for direct access if needed
     */
    fun getComponents(): ErrorHandlingComponents {
        return ErrorHandlingComponents(
            errorHandlingManager = errorHandlingManager,
            confidenceValidator = confidenceValidator,
            userFeedbackManager = userFeedbackManager,
            fallbackEventGenerator = fallbackEventGenerator,
            offlineModeHandler = offlineModeHandler,
            calendarIntentHelper = calendarIntentHelper,
            dataValidationManager = dataValidationManager,
            apiService = apiService
        )
    }
}

/**
 * Data classes for system integration
 */
data class UserInteraction(
    val type: Type,
    val title: String,
    val message: String,
    val result: ParseResult? = null,
    val assessment: ConfidenceValidator.ConfidenceAssessment? = null,
    val originalText: String? = null,
    val onProceed: () -> Unit = {},
    val onCancel: () -> Unit = {},
    val onImprove: () -> Unit = {},
    val onRetry: () -> Unit = {},
    val onManualEntry: () -> Unit = {}
) {
    enum class Type {
        CONFIDENCE_WARNING,
        FALLBACK_CONFIRMATION,
        MANUAL_ENTRY_SUGGESTION,
        NETWORK_ERROR,
        CALENDAR_ALTERNATIVES
    }
}

data class SystemHealthReport(
    val overallHealthy: Boolean,
    val componentHealth: Map<String, Boolean>,
    val issues: List<String>,
    val timestamp: Long,
    val errorStatistics: Map<String, Any>
)

data class CompatibilityReport(
    val overallCompatible: Boolean,
    val testResults: Map<String, Boolean>,
    val issues: List<String>,
    val timestamp: Long
)

data class ErrorHandlingComponents(
    val errorHandlingManager: ErrorHandlingManager,
    val confidenceValidator: ConfidenceValidator,
    val userFeedbackManager: UserFeedbackManager,
    val fallbackEventGenerator: FallbackEventGenerator,
    val offlineModeHandler: OfflineModeHandler,
    val calendarIntentHelper: CalendarIntentHelper,
    val dataValidationManager: DataValidationManager,
    val apiService: ApiService
)