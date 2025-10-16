package com.jacolabs.calendar

import android.content.Context
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.launch

/**
 * Example integration showing how to use ErrorHandlingManager in existing activities.
 * This demonstrates the integration patterns for the MainActivity and other components.
 */
class ErrorHandlingIntegrationExample(
    private val context: Context,
    private val coroutineScope: CoroutineScope
) {
    
    private val errorHandlingManager = ErrorHandlingManager(context)
    private val apiService = ApiService(context)
    
    /**
     * Example of enhanced API call with error handling
     */
    fun parseTextWithErrorHandling(
        text: String,
        onSuccess: (ParseResult) -> Unit,
        onError: (String) -> Unit,
        onRetry: (Long) -> Unit = {},
        onUserActionRequired: (ErrorHandlingManager.UserAction, String) -> Unit = { _, _ -> }
    ) {
        coroutineScope.launch {
            var retryCount = 0
            var lastResult: ErrorHandlingManager.ErrorHandlingResult? = null
            
            do {
                try {
                    // Attempt API call
                    val result = apiService.parseText(
                        text = text,
                        timezone = java.util.TimeZone.getDefault().id,
                        locale = java.util.Locale.getDefault().toString(),
                        now = java.util.Date()
                    )
                    
                    // Check confidence level
                    if (!errorHandlingManager.isConfidenceAcceptable(result.confidenceScore)) {
                        val errorResult = errorHandlingManager.handleLowConfidence(
                            result = result,
                            originalText = text,
                            userInteractionAllowed = true
                        )
                        
                        handleErrorResult(errorResult, onSuccess, onError, onRetry, onUserActionRequired)
                        return@launch
                    }
                    
                    // Success case
                    onSuccess(result)
                    return@launch
                    
                } catch (e: ApiException) {
                    // Handle API exception through error manager
                    val errorResult = errorHandlingManager.handleApiException(
                        exception = e,
                        originalText = text,
                        retryCount = retryCount,
                        networkAvailable = isNetworkAvailable()
                    )
                    
                    lastResult = errorResult
                    
                    if (errorResult.retryRecommended && retryCount < 3) {
                        retryCount++
                        onRetry(errorResult.retryDelayMs)
                        kotlinx.coroutines.delay(errorResult.retryDelayMs)
                        continue // Retry the loop
                    } else {
                        handleErrorResult(errorResult, onSuccess, onError, onRetry, onUserActionRequired)
                        return@launch
                    }
                    
                } catch (e: Exception) {
                    // Handle unexpected exceptions
                    val errorResult = errorHandlingManager.handleParsingFailure(
                        originalText = text,
                        exception = e
                    )
                    
                    handleErrorResult(errorResult, onSuccess, onError, onRetry, onUserActionRequired)
                    return@launch
                }
            } while (retryCount < 3)
            
            // If we get here, all retries failed
            lastResult?.let { result ->
                handleErrorResult(result, onSuccess, onError, onRetry, onUserActionRequired)
            } ?: onError("Maximum retry attempts exceeded")
        }
    }
    
    /**
     * Handles the error result from ErrorHandlingManager
     */
    private fun handleErrorResult(
        errorResult: ErrorHandlingManager.ErrorHandlingResult,
        onSuccess: (ParseResult) -> Unit,
        onError: (String) -> Unit,
        onRetry: (Long) -> Unit,
        onUserActionRequired: (ErrorHandlingManager.UserAction, String) -> Unit
    ) {
        when {
            errorResult.success && errorResult.recoveredResult != null -> {
                onSuccess(errorResult.recoveredResult)
            }
            
            errorResult.actionRequired != null -> {
                onUserActionRequired(errorResult.actionRequired, errorResult.userMessage)
            }
            
            errorResult.retryRecommended -> {
                onRetry(errorResult.retryDelayMs)
            }
            
            else -> {
                onError(errorResult.userMessage)
            }
        }
    }
    
    /**
     * Example of handling calendar launch failures
     */
    fun createCalendarEventWithErrorHandling(
        result: ParseResult,
        originalText: String,
        onSuccess: () -> Unit,
        onError: (String) -> Unit,
        onAlternativeRequired: (List<String>) -> Unit = {}
    ) {
        coroutineScope.launch {
            try {
                val calendarHelper = CalendarIntentHelper(context)
                calendarHelper.createCalendarEvent(result)
                onSuccess()
                
            } catch (e: Exception) {
                val errorResult = errorHandlingManager.handleCalendarLaunchFailure(
                    result = result,
                    originalText = originalText,
                    exception = e
                )
                
                when (errorResult.recoveryStrategy) {
                    ErrorHandlingManager.RecoveryStrategy.ALTERNATIVE_CALENDAR_LAUNCH -> {
                        // Provide alternative calendar options
                        onAlternativeRequired(listOf("Google Calendar", "Samsung Calendar", "Copy to Clipboard"))
                    }
                    
                    else -> {
                        if (errorResult.recoveredResult != null) {
                            // Try again with recovered result
                            try {
                                val calendarHelper = CalendarIntentHelper(context)
                                calendarHelper.createCalendarEvent(errorResult.recoveredResult)
                                onSuccess()
                            } catch (retryException: Exception) {
                                onError(errorResult.userMessage)
                            }
                        } else {
                            onError(errorResult.userMessage)
                        }
                    }
                }
            }
        }
    }
    
    /**
     * Example of batch error handling for multiple requests
     */
    fun processBatchRequests(
        texts: List<String>,
        onBatchComplete: (List<ParseResult>, List<String>) -> Unit
    ) {
        coroutineScope.launch {
            val results = mutableListOf<ParseResult>()
            val errors = mutableListOf<String>()
            
            texts.forEach { text ->
                try {
                    val result = apiService.parseText(
                        text = text,
                        timezone = java.util.TimeZone.getDefault().id,
                        locale = java.util.Locale.getDefault().toString(),
                        now = java.util.Date()
                    )
                    
                    if (errorHandlingManager.isConfidenceAcceptable(result.confidenceScore)) {
                        results.add(result)
                    } else {
                        // Apply fallback for low confidence
                        val fallbackResult = errorHandlingManager.createFallbackEvent(text, result)
                        results.add(fallbackResult)
                    }
                    
                } catch (e: Exception) {
                    val errorResult = errorHandlingManager.handleParsingFailure(text, e)
                    
                    if (errorResult.success && errorResult.recoveredResult != null) {
                        results.add(errorResult.recoveredResult)
                    } else {
                        errors.add("Failed to process: \"$text\" - ${errorResult.userMessage}")
                    }
                }
            }
            
            onBatchComplete(results, errors)
        }
    }
    
    /**
     * Example of getting error analytics for monitoring
     */
    fun getErrorAnalyticsReport(): Map<String, Any> {
        val statistics = errorHandlingManager.getErrorStatistics()
        val cachedRequests = errorHandlingManager.getCachedRequests()
        
        return mapOf(
            "error_statistics" to statistics,
            "cached_requests_count" to cachedRequests.size,
            "configuration" to mapOf(
                "confidence_threshold" to errorHandlingManager.getConfigManager().getConfig().confidenceThreshold,
                "max_retry_attempts" to errorHandlingManager.getConfigManager().getConfig().maxRetryAttempts,
                "offline_mode_enabled" to errorHandlingManager.getConfigManager().getConfig().enableOfflineMode
            )
        )
    }
    
    /**
     * Example of updating error handling configuration
     */
    fun updateErrorHandlingSettings(
        confidenceThreshold: Double? = null,
        maxRetryAttempts: Int? = null,
        enableOfflineMode: Boolean? = null
    ) {
        val configManager = errorHandlingManager.getConfigManager()
        val currentConfig = configManager.getConfig()
        
        val newConfig = currentConfig.copy(
            confidenceThreshold = confidenceThreshold ?: currentConfig.confidenceThreshold,
            maxRetryAttempts = maxRetryAttempts ?: currentConfig.maxRetryAttempts,
            enableOfflineMode = enableOfflineMode ?: currentConfig.enableOfflineMode
        )
        
        configManager.updateConfig(newConfig)
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
}

/**
 * Usage example for MainActivity integration
 */
object MainActivityIntegrationExample {
    
    fun integrateWithMainActivity(
        context: Context,
        lifecycleScope: androidx.lifecycle.LifecycleCoroutineScope,
        textInput: String,
        onParseResult: (ParseResult) -> Unit,
        onError: (String) -> Unit,
        onShowConfirmationDialog: (ParseResult, String) -> Unit,
        onShowRetryDialog: (Long) -> Unit
    ) {
        val integration = ErrorHandlingIntegrationExample(context, lifecycleScope)
        
        integration.parseTextWithErrorHandling(
            text = textInput,
            onSuccess = { result ->
                onParseResult(result)
            },
            onError = { errorMessage ->
                onError(errorMessage)
            },
            onRetry = { delayMs ->
                onShowRetryDialog(delayMs)
            },
            onUserActionRequired = { action, message ->
                when (action) {
                    ErrorHandlingManager.UserAction.CONFIRM_LOW_CONFIDENCE_RESULT -> {
                        // Show confirmation dialog for low confidence
                        val fallbackResult = ErrorHandlingManager(context).createFallbackEvent(textInput, null)
                        onShowConfirmationDialog(fallbackResult, message)
                    }
                    
                    ErrorHandlingManager.UserAction.RETRY_WITH_BETTER_TEXT -> {
                        onError("$message\n\nTry rephrasing with clearer date, time, and event details.")
                    }
                    
                    else -> {
                        onError(message)
                    }
                }
            }
        )
    }
}