package com.jacolabs.calendar

import android.content.Context
import android.util.Log
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONObject
import java.text.SimpleDateFormat
import java.util.*
import kotlin.math.min
import kotlin.math.pow

/**
 * Centralized error handling manager for coordinating error responses across the application.
 * Provides error categorization, recovery strategy selection, and analytics collection.
 */
class ErrorHandlingManager(
    private val context: Context,
    private val configManager: ErrorHandlingConfigManager = ErrorHandlingConfigManager(context)
) {
    
    // Initialize the FallbackEventGenerator for intelligent event creation
    private val fallbackEventGenerator = FallbackEventGenerator(context)
    
    companion object {
        private const val TAG = "ErrorHandlingManager"
        private const val PREFS_NAME = "error_handling_prefs"
        private const val KEY_ERROR_ANALYTICS = "error_analytics"
        private const val MAX_ANALYTICS_ENTRIES = 100
        private const val ANALYTICS_CLEANUP_THRESHOLD = 150
    }
    
    private val config: ErrorHandlingConfig
        get() = configManager.getConfig()
    
    /**
     * Enumeration of error types for categorization and strategy selection
     */
    enum class ErrorType {
        NETWORK_ERROR,
        API_TIMEOUT,
        PARSING_FAILURE,
        LOW_CONFIDENCE,
        VALIDATION_ERROR,
        CALENDAR_LAUNCH_FAILURE,
        INSUFFICIENT_DATA,
        RATE_LIMIT_ERROR,
        SERVER_ERROR,
        UNKNOWN_ERROR
    }
    
    /**
     * Recovery strategies available for different error scenarios
     */
    enum class RecoveryStrategy {
        RETRY_WITH_BACKOFF,
        FALLBACK_EVENT_CREATION,
        OFFLINE_MODE,
        USER_CONFIRMATION_REQUIRED,
        ALTERNATIVE_CALENDAR_LAUNCH,
        MANUAL_INPUT_SUGGESTION,
        CACHE_AND_RETRY_LATER,
        GRACEFUL_DEGRADATION,
        NO_RECOVERY_POSSIBLE
    }
    
    /**
     * Context information for error handling decisions
     */
    data class ErrorContext(
        val errorType: ErrorType,
        val originalText: String,
        val apiResponse: ParseResult? = null,
        val exception: Exception? = null,
        val retryCount: Int = 0,
        val timestamp: Long = System.currentTimeMillis(),
        val networkAvailable: Boolean = true,
        val userInteractionAllowed: Boolean = true,
        val previousErrors: List<ErrorType> = emptyList(),
        val confidenceScore: Double? = null,
        val processingTimeMs: Long = 0
    )
    
    /**
     * Result of error handling with recovery information
     */
    data class ErrorHandlingResult(
        val success: Boolean,
        val recoveryStrategy: RecoveryStrategy,
        val recoveredResult: ParseResult? = null,
        val userMessage: String,
        val actionRequired: UserAction? = null,
        val retryRecommended: Boolean = false,
        val retryDelayMs: Long = 0,
        val analyticsData: Map<String, Any> = emptyMap()
    )
    
    /**
     * User actions that may be required for error recovery
     */
    enum class UserAction {
        CONFIRM_LOW_CONFIDENCE_RESULT,
        RETRY_WITH_BETTER_TEXT,
        CHOOSE_ALTERNATIVE_CALENDAR,
        ENABLE_NETWORK_CONNECTION,
        WAIT_AND_RETRY,
        MANUAL_EVENT_CREATION,
        COPY_TO_CLIPBOARD
    }
    
    /**
     * Analytics data for error pattern identification
     */
    private data class ErrorAnalyticsEntry(
        val errorType: ErrorType,
        val timestamp: Long,
        val originalTextLength: Int,
        val confidenceScore: Double?,
        val recoveryStrategy: RecoveryStrategy,
        val recoverySuccess: Boolean,
        val retryCount: Int,
        val processingTimeMs: Long,
        val networkAvailable: Boolean,
        val deviceInfo: String
    )
    
    private val sharedPrefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
    
    /**
     * Main entry point for handling errors with context-aware recovery
     */
    suspend fun handleError(errorContext: ErrorContext): ErrorHandlingResult = withContext(Dispatchers.Default) {
        
        // Log error with privacy protection
        logErrorWithContext(errorContext)
        
        // Categorize error if not already categorized
        val finalErrorType = if (errorContext.errorType == ErrorType.UNKNOWN_ERROR && errorContext.exception != null) {
            categorizeError(errorContext.exception)
        } else {
            errorContext.errorType
        }
        
        // Select recovery strategy based on error type and context
        val recoveryStrategy = getRecoveryStrategy(finalErrorType, errorContext)
        
        // Execute recovery strategy
        val result = executeRecoveryStrategy(recoveryStrategy, errorContext)
        
        // Collect analytics data
        collectErrorAnalytics(finalErrorType, errorContext, recoveryStrategy, result.success)
        
        result
    }
    
    /**
     * Categorizes exceptions into appropriate error types
     */
    fun categorizeError(exception: Exception): ErrorType {
        return when (exception) {
            is ApiException -> {
                when (exception.apiError.type) {
                    ApiService.ErrorType.NETWORK_CONNECTIVITY -> ErrorType.NETWORK_ERROR
                    ApiService.ErrorType.REQUEST_TIMEOUT -> ErrorType.API_TIMEOUT
                    ApiService.ErrorType.PARSING_ERROR -> ErrorType.PARSING_FAILURE
                    ApiService.ErrorType.VALIDATION_ERROR -> ErrorType.VALIDATION_ERROR
                    ApiService.ErrorType.RATE_LIMIT -> ErrorType.RATE_LIMIT_ERROR
                    ApiService.ErrorType.SERVER_ERROR -> ErrorType.SERVER_ERROR
                    else -> ErrorType.UNKNOWN_ERROR
                }
            }
            is java.net.SocketTimeoutException -> ErrorType.API_TIMEOUT
            is java.net.UnknownHostException -> ErrorType.NETWORK_ERROR
            is java.net.ConnectException -> ErrorType.NETWORK_ERROR
            is java.io.IOException -> {
                when {
                    exception.message?.contains("timeout", ignoreCase = true) == true -> ErrorType.API_TIMEOUT
                    exception.message?.contains("network", ignoreCase = true) == true -> ErrorType.NETWORK_ERROR
                    else -> ErrorType.NETWORK_ERROR
                }
            }
            else -> ErrorType.UNKNOWN_ERROR
        }
    }
    
    /**
     * Determines the best recovery strategy based on error type and context
     */
    private fun getRecoveryStrategy(errorType: ErrorType, context: ErrorContext): RecoveryStrategy {
        return when (errorType) {
            ErrorType.NETWORK_ERROR -> {
                if (context.networkAvailable) {
                    if (config.shouldRetry(context.retryCount)) RecoveryStrategy.RETRY_WITH_BACKOFF
                    else if (config.enableOfflineMode) RecoveryStrategy.OFFLINE_MODE
                    else RecoveryStrategy.NO_RECOVERY_POSSIBLE
                } else if (config.enableOfflineMode) {
                    RecoveryStrategy.OFFLINE_MODE
                } else {
                    RecoveryStrategy.NO_RECOVERY_POSSIBLE
                }
            }
            
            ErrorType.API_TIMEOUT -> {
                if (config.shouldRetry(context.retryCount)) RecoveryStrategy.RETRY_WITH_BACKOFF
                else if (config.enableFallbackCreation) RecoveryStrategy.FALLBACK_EVENT_CREATION
                else RecoveryStrategy.NO_RECOVERY_POSSIBLE
            }
            
            ErrorType.PARSING_FAILURE -> {
                if (context.originalText.isNotBlank() && config.enableFallbackCreation) {
                    RecoveryStrategy.FALLBACK_EVENT_CREATION
                } else {
                    RecoveryStrategy.MANUAL_INPUT_SUGGESTION
                }
            }
            
            ErrorType.LOW_CONFIDENCE -> {
                if (context.userInteractionAllowed && config.enableUserConfirmationDialogs) {
                    RecoveryStrategy.USER_CONFIRMATION_REQUIRED
                } else if (config.enableFallbackCreation) {
                    RecoveryStrategy.FALLBACK_EVENT_CREATION
                } else {
                    RecoveryStrategy.MANUAL_INPUT_SUGGESTION
                }
            }
            
            ErrorType.VALIDATION_ERROR -> {
                if (config.enableGracefulDegradation) {
                    RecoveryStrategy.GRACEFUL_DEGRADATION
                } else {
                    RecoveryStrategy.MANUAL_INPUT_SUGGESTION
                }
            }
            
            ErrorType.CALENDAR_LAUNCH_FAILURE -> {
                RecoveryStrategy.ALTERNATIVE_CALENDAR_LAUNCH
            }
            
            ErrorType.INSUFFICIENT_DATA -> {
                if (context.originalText.isNotBlank() && config.enableFallbackCreation) {
                    RecoveryStrategy.FALLBACK_EVENT_CREATION
                } else {
                    RecoveryStrategy.MANUAL_INPUT_SUGGESTION
                }
            }
            
            ErrorType.RATE_LIMIT_ERROR -> {
                RecoveryStrategy.CACHE_AND_RETRY_LATER
            }
            
            ErrorType.SERVER_ERROR -> {
                if (config.shouldRetry(context.retryCount)) RecoveryStrategy.RETRY_WITH_BACKOFF
                else if (config.enableOfflineMode) RecoveryStrategy.OFFLINE_MODE
                else RecoveryStrategy.NO_RECOVERY_POSSIBLE
            }
            
            ErrorType.UNKNOWN_ERROR -> {
                if (config.shouldRetry(context.retryCount)) RecoveryStrategy.RETRY_WITH_BACKOFF
                else RecoveryStrategy.NO_RECOVERY_POSSIBLE
            }
        }
    }
    
    /**
     * Executes the selected recovery strategy
     */
    private suspend fun executeRecoveryStrategy(
        strategy: RecoveryStrategy,
        context: ErrorContext
    ): ErrorHandlingResult {
        
        return when (strategy) {
            RecoveryStrategy.RETRY_WITH_BACKOFF -> {
                val retryDelay = calculateRetryDelay(context.retryCount)
                ErrorHandlingResult(
                    success = false,
                    recoveryStrategy = strategy,
                    userMessage = "Request failed. Retrying in ${retryDelay / 1000} seconds...",
                    retryRecommended = true,
                    retryDelayMs = retryDelay,
                    analyticsData = mapOf(
                        "retry_count" to context.retryCount,
                        "retry_delay_ms" to retryDelay
                    )
                )
            }
            
            RecoveryStrategy.FALLBACK_EVENT_CREATION -> {
                val fallbackEvent = fallbackEventGenerator.generateFallbackEvent(context.originalText, context.apiResponse)
                val fallbackResult = fallbackEventGenerator.toParseResult(fallbackEvent, context.originalText)
                ErrorHandlingResult(
                    success = true,
                    recoveryStrategy = strategy,
                    recoveredResult = fallbackResult,
                    userMessage = "Created event with available information. You can edit details in your calendar app.",
                    analyticsData = mapOf(
                        "fallback_confidence" to fallbackResult.confidenceScore,
                        "original_text_length" to context.originalText.length,
                        "title_extraction_method" to fallbackEvent.extractionDetails.titleExtractionMethod,
                        "time_generation_method" to fallbackEvent.extractionDetails.timeGenerationMethod,
                        "patterns_matched" to fallbackEvent.extractionDetails.patternsMatched.size
                    )
                )
            }
            
            RecoveryStrategy.OFFLINE_MODE -> {
                // Use FallbackEventGenerator for offline mode as well, but mark it as offline
                val fallbackEvent = fallbackEventGenerator.generateFallbackEvent(context.originalText, null)
                val offlineResult = fallbackEventGenerator.toParseResult(fallbackEvent, context.originalText).copy(
                    fallbackReason = "Created offline - no network available",
                    description = "Offline event from: \"${context.originalText}\"\n\n${fallbackEvent.description}"
                )
                ErrorHandlingResult(
                    success = true,
                    recoveryStrategy = strategy,
                    recoveredResult = offlineResult,
                    userMessage = "Created event offline. Some details may need adjustment in your calendar app.",
                    analyticsData = mapOf(
                        "offline_mode" to true,
                        "original_text_length" to context.originalText.length,
                        "title_extraction_method" to fallbackEvent.extractionDetails.titleExtractionMethod,
                        "time_generation_method" to fallbackEvent.extractionDetails.timeGenerationMethod
                    )
                )
            }
            
            RecoveryStrategy.USER_CONFIRMATION_REQUIRED -> {
                ErrorHandlingResult(
                    success = false,
                    recoveryStrategy = strategy,
                    userMessage = "The extracted information has low confidence. Please review before creating the event.",
                    actionRequired = UserAction.CONFIRM_LOW_CONFIDENCE_RESULT,
                    analyticsData = mapOf(
                        "confidence_score" to (context.confidenceScore ?: 0.0),
                        "requires_confirmation" to true
                    )
                )
            }
            
            RecoveryStrategy.ALTERNATIVE_CALENDAR_LAUNCH -> {
                ErrorHandlingResult(
                    success = false,
                    recoveryStrategy = strategy,
                    userMessage = "Default calendar app not available. Please choose an alternative or copy event details.",
                    actionRequired = UserAction.CHOOSE_ALTERNATIVE_CALENDAR,
                    analyticsData = mapOf(
                        "calendar_launch_failed" to true
                    )
                )
            }
            
            RecoveryStrategy.MANUAL_INPUT_SUGGESTION -> {
                ErrorHandlingResult(
                    success = false,
                    recoveryStrategy = strategy,
                    userMessage = "Unable to extract event information. Please try rephrasing with clearer date, time, and event details.",
                    actionRequired = UserAction.RETRY_WITH_BETTER_TEXT,
                    analyticsData = mapOf(
                        "manual_input_suggested" to true,
                        "original_text_length" to context.originalText.length
                    )
                )
            }
            
            RecoveryStrategy.CACHE_AND_RETRY_LATER -> {
                // Cache the request for later retry
                cacheFailedRequest(context)
                ErrorHandlingResult(
                    success = false,
                    recoveryStrategy = strategy,
                    userMessage = "Service temporarily unavailable. Your request has been saved and will be retried automatically.",
                    actionRequired = UserAction.WAIT_AND_RETRY,
                    analyticsData = mapOf(
                        "cached_for_retry" to true,
                        "retry_count" to context.retryCount
                    )
                )
            }
            
            RecoveryStrategy.GRACEFUL_DEGRADATION -> {
                // Use FallbackEventGenerator for graceful degradation with partial results
                val fallbackEvent = fallbackEventGenerator.generateFallbackEvent(context.originalText, context.apiResponse)
                val degradedResult = fallbackEventGenerator.toParseResult(fallbackEvent, context.originalText).copy(
                    fallbackReason = "Applied intelligent defaults for missing or low-confidence fields"
                )
                ErrorHandlingResult(
                    success = true,
                    recoveryStrategy = strategy,
                    recoveredResult = degradedResult,
                    userMessage = "Event created with enhanced information. Some details may need adjustment.",
                    analyticsData = mapOf(
                        "graceful_degradation" to true,
                        "degraded_fields" to getDegradedFields(context.apiResponse),
                        "title_extraction_method" to fallbackEvent.extractionDetails.titleExtractionMethod,
                        "enhancement_applied" to true
                    )
                )
            }
            
            RecoveryStrategy.NO_RECOVERY_POSSIBLE -> {
                ErrorHandlingResult(
                    success = false,
                    recoveryStrategy = strategy,
                    userMessage = "Unable to process the request. Please try again later or create the event manually.",
                    actionRequired = UserAction.MANUAL_EVENT_CREATION,
                    analyticsData = mapOf(
                        "no_recovery_possible" to true,
                        "error_type" to context.errorType.name
                    )
                )
            }
        }
    }
    
    /**
     * Creates a fallback event when parsing fails
     * Delegates to FallbackEventGenerator for intelligent event creation
     */
    fun createFallbackEvent(originalText: String, partialResult: ParseResult?): ParseResult {
        val fallbackEvent = fallbackEventGenerator.generateFallbackEvent(originalText, partialResult)
        return fallbackEventGenerator.toParseResult(fallbackEvent, originalText)
    }
    
    /**
     * Creates an offline event using local processing
     * Delegates to FallbackEventGenerator for intelligent offline event creation
     */
    fun createOfflineEvent(originalText: String): ParseResult {
        val fallbackEvent = fallbackEventGenerator.generateFallbackEvent(originalText, null)
        return fallbackEventGenerator.toParseResult(fallbackEvent, originalText).copy(
            fallbackReason = "Created offline - no network available",
            confidenceScore = 0.1, // Very low confidence for offline
            description = "Offline event from: \"$originalText\"\n\n${fallbackEvent.description}"
        )
    }
    
    /**
     * Applies graceful degradation to partial results
     * Uses FallbackEventGenerator for intelligent enhancement of partial results
     */
    fun applyGracefulDegradation(originalText: String, partialResult: ParseResult?): ParseResult {
        val fallbackEvent = fallbackEventGenerator.generateFallbackEvent(originalText, partialResult)
        return fallbackEventGenerator.toParseResult(fallbackEvent, originalText).copy(
            fallbackReason = "Applied intelligent defaults for missing or low-confidence fields"
        )
    }
    
    // Note: extractMeaningfulTitle and generateDefaultDateTime methods have been replaced
    // by the more sophisticated FallbackEventGenerator class
    
    /**
     * Calculates retry delay with exponential backoff using configuration
     */
    fun calculateRetryDelay(retryCount: Int): Long {
        val exponentialDelay = config.baseRetryDelayMs * 2.0.pow(retryCount.toDouble()).toLong()
        return min(exponentialDelay, config.maxRetryDelayMs)
    }
    
    /**
     * Caches failed request for later retry
     */
    private fun cacheFailedRequest(context: ErrorContext) {
        try {
            val cachedRequest = JSONObject().apply {
                put("text", context.originalText)
                put("timestamp", context.timestamp)
                put("retry_count", context.retryCount)
                put("error_type", context.errorType.name)
            }
            
            // Store in SharedPreferences (in a real app, consider using Room database)
            val existingCache = sharedPrefs.getString("cached_requests", "[]")
            val cacheArray = org.json.JSONArray(existingCache)
            cacheArray.put(cachedRequest)
            
            sharedPrefs.edit()
                .putString("cached_requests", cacheArray.toString())
                .apply()
                
        } catch (e: Exception) {
            Log.w(TAG, "Failed to cache request", e)
        }
    }
    
    /**
     * Gets list of fields that were degraded
     */
    private fun getDegradedFields(partialResult: ParseResult?): List<String> {
        val degradedFields = mutableListOf<String>()
        
        partialResult?.let { result ->
            if (result.title.isNullOrBlank()) degradedFields.add("title")
            if (result.startDateTime.isNullOrBlank()) degradedFields.add("start_time")
            if (result.endDateTime.isNullOrBlank()) degradedFields.add("end_time")
            if (result.location.isNullOrBlank()) degradedFields.add("location")
        }
        
        return degradedFields
    }
    
    /**
     * Logs error with context preservation and privacy protection
     */
    private fun logErrorWithContext(context: ErrorContext) {
        try {
            // Only log if enabled in configuration
            if (!config.shouldLog(ErrorHandlingConfig.LogLevel.INFO)) return
            
            // Create privacy-safe log entry
            val logData = mapOf(
                "error_type" to context.errorType.name,
                "text_length" to context.originalText.length,
                "retry_count" to context.retryCount,
                "network_available" to context.networkAvailable,
                "confidence_score" to context.confidenceScore,
                "processing_time_ms" to context.processingTimeMs,
                "timestamp" to context.timestamp,
                "has_partial_result" to (context.apiResponse != null)
            )
            
            Log.i(TAG, "Error handled: $logData")
            
            // Don't log the actual text content for privacy
            if (context.exception != null && config.shouldLog(ErrorHandlingConfig.LogLevel.WARN)) {
                Log.w(TAG, "Exception details", context.exception)
            }
            
        } catch (e: Exception) {
            if (config.shouldLog(ErrorHandlingConfig.LogLevel.ERROR)) {
                Log.e(TAG, "Failed to log error context", e)
            }
        }
    }
    
    /**
     * Collects error analytics for pattern identification
     */
    private fun collectErrorAnalytics(
        errorType: ErrorType,
        context: ErrorContext,
        recoveryStrategy: RecoveryStrategy,
        recoverySuccess: Boolean
    ) {
        // Only collect analytics if enabled in configuration
        if (!config.shouldCollectAnalytics()) return
        
        try {
            val analyticsEntry = ErrorAnalyticsEntry(
                errorType = errorType,
                timestamp = context.timestamp,
                originalTextLength = context.originalText.length,
                confidenceScore = context.confidenceScore,
                recoveryStrategy = recoveryStrategy,
                recoverySuccess = recoverySuccess,
                retryCount = context.retryCount,
                processingTimeMs = context.processingTimeMs,
                networkAvailable = context.networkAvailable,
                deviceInfo = "${android.os.Build.MODEL} (API ${android.os.Build.VERSION.SDK_INT})"
            )
            
            // Store analytics data (limit size to prevent storage bloat)
            val existingAnalytics = sharedPrefs.getString(KEY_ERROR_ANALYTICS, "[]")
            val analyticsArray = org.json.JSONArray(existingAnalytics)
            
            // Add new entry
            val entryJson = JSONObject().apply {
                put("error_type", analyticsEntry.errorType.name)
                put("timestamp", analyticsEntry.timestamp)
                put("text_length", analyticsEntry.originalTextLength)
                put("confidence_score", analyticsEntry.confidenceScore)
                put("recovery_strategy", analyticsEntry.recoveryStrategy.name)
                put("recovery_success", analyticsEntry.recoverySuccess)
                put("retry_count", analyticsEntry.retryCount)
                put("processing_time_ms", analyticsEntry.processingTimeMs)
                put("network_available", analyticsEntry.networkAvailable)
                put("device_info", analyticsEntry.deviceInfo)
            }
            analyticsArray.put(entryJson)
            
            // Cleanup old entries if needed
            if (analyticsArray.length() > ANALYTICS_CLEANUP_THRESHOLD) {
                val cleanedArray = org.json.JSONArray()
                val startIndex = analyticsArray.length() - MAX_ANALYTICS_ENTRIES
                for (i in startIndex until analyticsArray.length()) {
                    cleanedArray.put(analyticsArray.get(i))
                }
                
                sharedPrefs.edit()
                    .putString(KEY_ERROR_ANALYTICS, cleanedArray.toString())
                    .apply()
            } else {
                sharedPrefs.edit()
                    .putString(KEY_ERROR_ANALYTICS, analyticsArray.toString())
                    .apply()
            }
            
        } catch (e: Exception) {
            Log.w(TAG, "Failed to collect error analytics", e)
        }
    }
    
    /**
     * Gets error analytics for pattern analysis
     */
    fun getErrorAnalytics(): List<Map<String, Any>> {
        return try {
            val analyticsJson = sharedPrefs.getString(KEY_ERROR_ANALYTICS, "[]")
            val analyticsArray = org.json.JSONArray(analyticsJson)
            
            mutableListOf<Map<String, Any>>().apply {
                for (i in 0 until analyticsArray.length()) {
                    val entry = analyticsArray.getJSONObject(i)
                    add(mapOf(
                        "error_type" to entry.getString("error_type"),
                        "timestamp" to entry.getLong("timestamp"),
                        "text_length" to entry.getInt("text_length"),
                        "confidence_score" to entry.optDouble("confidence_score"),
                        "recovery_strategy" to entry.getString("recovery_strategy"),
                        "recovery_success" to entry.getBoolean("recovery_success"),
                        "retry_count" to entry.getInt("retry_count"),
                        "processing_time_ms" to entry.getLong("processing_time_ms"),
                        "network_available" to entry.getBoolean("network_available"),
                        "device_info" to entry.getString("device_info")
                    ))
                }
            }
        } catch (e: Exception) {
            Log.w(TAG, "Failed to get error analytics", e)
            emptyList()
        }
    }
    
    /**
     * Clears error analytics data
     */
    fun clearErrorAnalytics() {
        sharedPrefs.edit()
            .remove(KEY_ERROR_ANALYTICS)
            .apply()
    }
    
    /**
     * Gets the current configuration manager
     */
    fun getConfigManager(): ErrorHandlingConfigManager = configManager
    
    /**
     * Convenience method to handle API exceptions
     */
    suspend fun handleApiException(
        exception: ApiException,
        originalText: String,
        retryCount: Int = 0,
        networkAvailable: Boolean = true
    ): ErrorHandlingResult {
        val errorContext = ErrorContext(
            errorType = categorizeError(exception),
            originalText = originalText,
            exception = exception,
            retryCount = retryCount,
            networkAvailable = networkAvailable,
            confidenceScore = null
        )
        
        return handleError(errorContext)
    }
    
    /**
     * Convenience method to handle low confidence results
     */
    suspend fun handleLowConfidence(
        result: ParseResult,
        originalText: String,
        userInteractionAllowed: Boolean = true
    ): ErrorHandlingResult {
        val errorContext = ErrorContext(
            errorType = ErrorType.LOW_CONFIDENCE,
            originalText = originalText,
            apiResponse = result,
            confidenceScore = result.confidenceScore,
            userInteractionAllowed = userInteractionAllowed
        )
        
        return handleError(errorContext)
    }
    
    /**
     * Convenience method to handle parsing failures
     */
    suspend fun handleParsingFailure(
        originalText: String,
        exception: Exception? = null
    ): ErrorHandlingResult {
        val errorContext = ErrorContext(
            errorType = ErrorType.PARSING_FAILURE,
            originalText = originalText,
            exception = exception
        )
        
        return handleError(errorContext)
    }
    
    /**
     * Convenience method to handle calendar launch failures
     */
    suspend fun handleCalendarLaunchFailure(
        result: ParseResult,
        originalText: String,
        exception: Exception? = null
    ): ErrorHandlingResult {
        val errorContext = ErrorContext(
            errorType = ErrorType.CALENDAR_LAUNCH_FAILURE,
            originalText = originalText,
            apiResponse = result,
            exception = exception
        )
        
        return handleError(errorContext)
    }
    
    /**
     * Checks if a confidence score is acceptable based on current configuration
     */
    fun isConfidenceAcceptable(confidence: Double): Boolean {
        return config.isConfidenceAcceptable(confidence)
    }
    
    /**
     * Gets cached requests for retry processing
     */
    fun getCachedRequests(): List<Map<String, Any>> {
        return try {
            val cachedJson = sharedPrefs.getString("cached_requests", "[]")
            val cachedArray = org.json.JSONArray(cachedJson)
            
            mutableListOf<Map<String, Any>>().apply {
                for (i in 0 until cachedArray.length()) {
                    val request = cachedArray.getJSONObject(i)
                    add(mapOf(
                        "text" to request.getString("text"),
                        "timestamp" to request.getLong("timestamp"),
                        "retry_count" to request.getInt("retry_count"),
                        "error_type" to request.getString("error_type")
                    ))
                }
            }
        } catch (e: Exception) {
            if (config.shouldLog(ErrorHandlingConfig.LogLevel.WARN)) {
                Log.w(TAG, "Failed to get cached requests", e)
            }
            emptyList()
        }
    }
    
    /**
     * Clears cached requests
     */
    fun clearCachedRequests() {
        sharedPrefs.edit()
            .remove("cached_requests")
            .apply()
    }
    
    /**
     * Gets error statistics for monitoring
     */
    fun getErrorStatistics(): Map<String, Any> {
        val analytics = getErrorAnalytics()
        
        if (analytics.isEmpty()) {
            return mapOf(
                "total_errors" to 0,
                "error_types" to emptyMap<String, Int>(),
                "recovery_success_rate" to 0.0,
                "average_retry_count" to 0.0
            )
        }
        
        val errorTypeCounts = analytics.groupingBy { it["error_type"] as String }.eachCount()
        val successfulRecoveries = analytics.count { it["recovery_success"] as Boolean }
        val totalRetries = analytics.sumOf { it["retry_count"] as Int }
        
        return mapOf(
            "total_errors" to analytics.size,
            "error_types" to errorTypeCounts,
            "recovery_success_rate" to (successfulRecoveries.toDouble() / analytics.size),
            "average_retry_count" to (totalRetries.toDouble() / analytics.size),
            "most_common_error" to (errorTypeCounts.maxByOrNull { it.value }?.key ?: "none"),
            "analytics_period_days" to calculateAnalyticsPeriodDays(analytics)
        )
    }
    
    /**
     * Calculates the period covered by analytics data in days
     */
    private fun calculateAnalyticsPeriodDays(analytics: List<Map<String, Any>>): Int {
        if (analytics.isEmpty()) return 0
        
        val timestamps = analytics.mapNotNull { it["timestamp"] as? Long }
        if (timestamps.isEmpty()) return 0
        
        val oldestTimestamp = timestamps.minOrNull() ?: return 0
        val newestTimestamp = timestamps.maxOrNull() ?: return 0
        
        return ((newestTimestamp - oldestTimestamp) / (24 * 60 * 60 * 1000)).toInt()
    }
    
    /**
     * Convenience method to handle calendar launch failures
     */
    suspend fun handleCalendarLaunchFailure(
        result: ParseResult,
        exception: Exception? = null
    ): ErrorHandlingResult {
        val errorContext = ErrorContext(
            errorType = ErrorType.CALENDAR_LAUNCH_FAILURE,
            originalText = result.originalText ?: "",
            apiResponse = result,
            exception = exception
        )
        
        return handleError(errorContext)
    }
}