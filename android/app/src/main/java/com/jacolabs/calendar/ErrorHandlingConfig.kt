package com.jacolabs.calendar

import android.content.Context
import android.content.SharedPreferences

/**
 * Configuration class for error handling behavior with user preferences integration.
 * Provides configurable thresholds, timeouts, and behavior settings for the ErrorHandlingManager.
 * 
 * Addresses requirements:
 * - 6.1: Automatic retry up to configurable times with exponential backoff
 * - 6.2: Alternative calendar app attempts when primary fails
 * - 10.1: Try-catch blocks around all API calls and calendar operations
 * - 10.2: Error categorization by type (network, parsing, calendar, validation)
 */
data class ErrorHandlingConfig(
    // Retry mechanism settings (Requirement 6.1)
    val maxRetryAttempts: Int = 2, // Changed from 3 to 2 per requirement 6.1
    val baseRetryDelayMs: Long = 1000L,
    val maxRetryDelayMs: Long = 30000L,
    val exponentialBackoffMultiplier: Double = 2.0,
    
    // Confidence and validation settings
    val confidenceThreshold: Double = 0.3,
    val enableUserConfirmationDialogs: Boolean = true,
    
    // Offline and fallback settings
    val enableOfflineMode: Boolean = true,
    val enableFallbackCreation: Boolean = true,
    val cacheExpirationHours: Int = 24,
    val maxCachedRequests: Int = 50,
    
    // Calendar launch settings (Requirement 6.2)
    val enableAlternativeCalendarApps: Boolean = true,
    val maxCalendarLaunchAttempts: Int = 3,
    val enableWebCalendarFallback: Boolean = true,
    val enableClipboardFallback: Boolean = true,
    
    // Network and API settings
    val enableNetworkChecks: Boolean = true,
    val processingTimeoutMs: Long = 15000L,
    val apiTimeoutMs: Long = 10000L, // Specific API timeout per requirement 4.1
    
    // Error handling architecture settings (Requirement 10.1, 10.2)
    val enableComprehensiveErrorCatching: Boolean = true,
    val enableErrorCategorization: Boolean = true,
    val enableCrashPrevention: Boolean = true,
    val enableConsistentUIState: Boolean = true,
    
    // Logging and analytics
    val enableAnalyticsCollection: Boolean = true,
    val enableGracefulDegradation: Boolean = true,
    val logLevel: LogLevel = LogLevel.INFO,
    val enablePrivacyCompliantLogging: Boolean = true
) {
    
    enum class LogLevel {
        NONE, ERROR, WARN, INFO, DEBUG
    }
    
    companion object {
        private const val PREFS_NAME = "error_handling_config"
        
        // Retry mechanism keys
        private const val KEY_MAX_RETRY_ATTEMPTS = "max_retry_attempts"
        private const val KEY_BASE_RETRY_DELAY_MS = "base_retry_delay_ms"
        private const val KEY_MAX_RETRY_DELAY_MS = "max_retry_delay_ms"
        private const val KEY_EXPONENTIAL_BACKOFF_MULTIPLIER = "exponential_backoff_multiplier"
        
        // Confidence and validation keys
        private const val KEY_CONFIDENCE_THRESHOLD = "confidence_threshold"
        private const val KEY_ENABLE_USER_CONFIRMATION_DIALOGS = "enable_user_confirmation_dialogs"
        
        // Offline and fallback keys
        private const val KEY_ENABLE_OFFLINE_MODE = "enable_offline_mode"
        private const val KEY_ENABLE_FALLBACK_CREATION = "enable_fallback_creation"
        private const val KEY_CACHE_EXPIRATION_HOURS = "cache_expiration_hours"
        private const val KEY_MAX_CACHED_REQUESTS = "max_cached_requests"
        
        // Calendar launch keys
        private const val KEY_ENABLE_ALTERNATIVE_CALENDAR_APPS = "enable_alternative_calendar_apps"
        private const val KEY_MAX_CALENDAR_LAUNCH_ATTEMPTS = "max_calendar_launch_attempts"
        private const val KEY_ENABLE_WEB_CALENDAR_FALLBACK = "enable_web_calendar_fallback"
        private const val KEY_ENABLE_CLIPBOARD_FALLBACK = "enable_clipboard_fallback"
        
        // Network and API keys
        private const val KEY_ENABLE_NETWORK_CHECKS = "enable_network_checks"
        private const val KEY_PROCESSING_TIMEOUT_MS = "processing_timeout_ms"
        private const val KEY_API_TIMEOUT_MS = "api_timeout_ms"
        
        // Error handling architecture keys
        private const val KEY_ENABLE_COMPREHENSIVE_ERROR_CATCHING = "enable_comprehensive_error_catching"
        private const val KEY_ENABLE_ERROR_CATEGORIZATION = "enable_error_categorization"
        private const val KEY_ENABLE_CRASH_PREVENTION = "enable_crash_prevention"
        private const val KEY_ENABLE_CONSISTENT_UI_STATE = "enable_consistent_ui_state"
        
        // Logging and analytics keys
        private const val KEY_ENABLE_ANALYTICS_COLLECTION = "enable_analytics_collection"
        private const val KEY_ENABLE_GRACEFUL_DEGRADATION = "enable_graceful_degradation"
        private const val KEY_LOG_LEVEL = "log_level"
        private const val KEY_ENABLE_PRIVACY_COMPLIANT_LOGGING = "enable_privacy_compliant_logging"
        
        /**
         * Loads configuration from SharedPreferences with default values
         */
        fun load(context: Context): ErrorHandlingConfig {
            val prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
            
            return ErrorHandlingConfig(
                // Retry mechanism settings
                maxRetryAttempts = prefs.getInt(KEY_MAX_RETRY_ATTEMPTS, 2),
                baseRetryDelayMs = prefs.getLong(KEY_BASE_RETRY_DELAY_MS, 1000L),
                maxRetryDelayMs = prefs.getLong(KEY_MAX_RETRY_DELAY_MS, 30000L),
                exponentialBackoffMultiplier = prefs.getFloat(KEY_EXPONENTIAL_BACKOFF_MULTIPLIER, 2.0f).toDouble(),
                
                // Confidence and validation settings
                confidenceThreshold = prefs.getFloat(KEY_CONFIDENCE_THRESHOLD, 0.3f).toDouble(),
                enableUserConfirmationDialogs = prefs.getBoolean(KEY_ENABLE_USER_CONFIRMATION_DIALOGS, true),
                
                // Offline and fallback settings
                enableOfflineMode = prefs.getBoolean(KEY_ENABLE_OFFLINE_MODE, true),
                enableFallbackCreation = prefs.getBoolean(KEY_ENABLE_FALLBACK_CREATION, true),
                cacheExpirationHours = prefs.getInt(KEY_CACHE_EXPIRATION_HOURS, 24),
                maxCachedRequests = prefs.getInt(KEY_MAX_CACHED_REQUESTS, 50),
                
                // Calendar launch settings
                enableAlternativeCalendarApps = prefs.getBoolean(KEY_ENABLE_ALTERNATIVE_CALENDAR_APPS, true),
                maxCalendarLaunchAttempts = prefs.getInt(KEY_MAX_CALENDAR_LAUNCH_ATTEMPTS, 3),
                enableWebCalendarFallback = prefs.getBoolean(KEY_ENABLE_WEB_CALENDAR_FALLBACK, true),
                enableClipboardFallback = prefs.getBoolean(KEY_ENABLE_CLIPBOARD_FALLBACK, true),
                
                // Network and API settings
                enableNetworkChecks = prefs.getBoolean(KEY_ENABLE_NETWORK_CHECKS, true),
                processingTimeoutMs = prefs.getLong(KEY_PROCESSING_TIMEOUT_MS, 15000L),
                apiTimeoutMs = prefs.getLong(KEY_API_TIMEOUT_MS, 10000L),
                
                // Error handling architecture settings
                enableComprehensiveErrorCatching = prefs.getBoolean(KEY_ENABLE_COMPREHENSIVE_ERROR_CATCHING, true),
                enableErrorCategorization = prefs.getBoolean(KEY_ENABLE_ERROR_CATEGORIZATION, true),
                enableCrashPrevention = prefs.getBoolean(KEY_ENABLE_CRASH_PREVENTION, true),
                enableConsistentUIState = prefs.getBoolean(KEY_ENABLE_CONSISTENT_UI_STATE, true),
                
                // Logging and analytics
                enableAnalyticsCollection = prefs.getBoolean(KEY_ENABLE_ANALYTICS_COLLECTION, true),
                enableGracefulDegradation = prefs.getBoolean(KEY_ENABLE_GRACEFUL_DEGRADATION, true),
                logLevel = LogLevel.valueOf(prefs.getString(KEY_LOG_LEVEL, LogLevel.INFO.name) ?: LogLevel.INFO.name),
                enablePrivacyCompliantLogging = prefs.getBoolean(KEY_ENABLE_PRIVACY_COMPLIANT_LOGGING, true)
            )
        }
        
        /**
         * Creates a configuration optimized for production use
         * Implements stricter settings for reliability and performance
         */
        fun forProduction(): ErrorHandlingConfig {
            return ErrorHandlingConfig(
                // Conservative retry settings for production
                maxRetryAttempts = 2,
                baseRetryDelayMs = 2000L,
                maxRetryDelayMs = 15000L,
                exponentialBackoffMultiplier = 2.0,
                
                // Higher confidence threshold for production
                confidenceThreshold = 0.4,
                enableUserConfirmationDialogs = true,
                
                // Optimized cache settings
                enableOfflineMode = true,
                enableFallbackCreation = true,
                cacheExpirationHours = 12,
                maxCachedRequests = 25,
                
                // Full calendar fallback support
                enableAlternativeCalendarApps = true,
                maxCalendarLaunchAttempts = 3,
                enableWebCalendarFallback = true,
                enableClipboardFallback = true,
                
                // Shorter timeouts for production
                enableNetworkChecks = true,
                processingTimeoutMs = 10000L,
                apiTimeoutMs = 8000L,
                
                // Full error handling architecture
                enableComprehensiveErrorCatching = true,
                enableErrorCategorization = true,
                enableCrashPrevention = true,
                enableConsistentUIState = true,
                
                // Production logging and analytics
                enableAnalyticsCollection = true,
                enableGracefulDegradation = true,
                logLevel = LogLevel.WARN,
                enablePrivacyCompliantLogging = true
            )
        }
        
        /**
         * Creates a configuration optimized for development/testing
         * Includes more verbose logging and relaxed constraints
         */
        fun forDevelopment(): ErrorHandlingConfig {
            return ErrorHandlingConfig(
                // More aggressive retry settings for testing
                maxRetryAttempts = 5,
                baseRetryDelayMs = 500L,
                maxRetryDelayMs = 5000L,
                exponentialBackoffMultiplier = 1.5,
                
                // Lower confidence threshold for testing
                confidenceThreshold = 0.2,
                enableUserConfirmationDialogs = false, // Skip dialogs in testing
                
                // Extended cache settings for development
                enableOfflineMode = true,
                enableFallbackCreation = true,
                cacheExpirationHours = 48,
                maxCachedRequests = 100,
                
                // Full calendar fallback testing
                enableAlternativeCalendarApps = true,
                maxCalendarLaunchAttempts = 5,
                enableWebCalendarFallback = true,
                enableClipboardFallback = true,
                
                // Extended timeouts for debugging
                enableNetworkChecks = true,
                processingTimeoutMs = 30000L,
                apiTimeoutMs = 20000L,
                
                // Full error handling for testing
                enableComprehensiveErrorCatching = true,
                enableErrorCategorization = true,
                enableCrashPrevention = true,
                enableConsistentUIState = true,
                
                // Verbose logging for development
                enableAnalyticsCollection = true,
                enableGracefulDegradation = true,
                logLevel = LogLevel.DEBUG,
                enablePrivacyCompliantLogging = false // Allow more detailed logging in dev
            )
        }
    }
    
    /**
     * Saves the current configuration to SharedPreferences
     */
    fun save(context: Context) {
        val prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
        
        prefs.edit()
            // Retry mechanism settings
            .putInt(KEY_MAX_RETRY_ATTEMPTS, maxRetryAttempts)
            .putLong(KEY_BASE_RETRY_DELAY_MS, baseRetryDelayMs)
            .putLong(KEY_MAX_RETRY_DELAY_MS, maxRetryDelayMs)
            .putFloat(KEY_EXPONENTIAL_BACKOFF_MULTIPLIER, exponentialBackoffMultiplier.toFloat())
            
            // Confidence and validation settings
            .putFloat(KEY_CONFIDENCE_THRESHOLD, confidenceThreshold.toFloat())
            .putBoolean(KEY_ENABLE_USER_CONFIRMATION_DIALOGS, enableUserConfirmationDialogs)
            
            // Offline and fallback settings
            .putBoolean(KEY_ENABLE_OFFLINE_MODE, enableOfflineMode)
            .putBoolean(KEY_ENABLE_FALLBACK_CREATION, enableFallbackCreation)
            .putInt(KEY_CACHE_EXPIRATION_HOURS, cacheExpirationHours)
            .putInt(KEY_MAX_CACHED_REQUESTS, maxCachedRequests)
            
            // Calendar launch settings
            .putBoolean(KEY_ENABLE_ALTERNATIVE_CALENDAR_APPS, enableAlternativeCalendarApps)
            .putInt(KEY_MAX_CALENDAR_LAUNCH_ATTEMPTS, maxCalendarLaunchAttempts)
            .putBoolean(KEY_ENABLE_WEB_CALENDAR_FALLBACK, enableWebCalendarFallback)
            .putBoolean(KEY_ENABLE_CLIPBOARD_FALLBACK, enableClipboardFallback)
            
            // Network and API settings
            .putBoolean(KEY_ENABLE_NETWORK_CHECKS, enableNetworkChecks)
            .putLong(KEY_PROCESSING_TIMEOUT_MS, processingTimeoutMs)
            .putLong(KEY_API_TIMEOUT_MS, apiTimeoutMs)
            
            // Error handling architecture settings
            .putBoolean(KEY_ENABLE_COMPREHENSIVE_ERROR_CATCHING, enableComprehensiveErrorCatching)
            .putBoolean(KEY_ENABLE_ERROR_CATEGORIZATION, enableErrorCategorization)
            .putBoolean(KEY_ENABLE_CRASH_PREVENTION, enableCrashPrevention)
            .putBoolean(KEY_ENABLE_CONSISTENT_UI_STATE, enableConsistentUIState)
            
            // Logging and analytics
            .putBoolean(KEY_ENABLE_ANALYTICS_COLLECTION, enableAnalyticsCollection)
            .putBoolean(KEY_ENABLE_GRACEFUL_DEGRADATION, enableGracefulDegradation)
            .putString(KEY_LOG_LEVEL, logLevel.name)
            .putBoolean(KEY_ENABLE_PRIVACY_COMPLIANT_LOGGING, enablePrivacyCompliantLogging)
            .apply()
    }
    
    /**
     * Validates configuration values and returns a corrected version if needed
     * Ensures all values are within safe and reasonable bounds
     */
    fun validate(): ErrorHandlingConfig {
        return copy(
            // Retry mechanism validation
            maxRetryAttempts = maxRetryAttempts.coerceIn(0, 10),
            baseRetryDelayMs = baseRetryDelayMs.coerceIn(100L, 10000L),
            maxRetryDelayMs = maxRetryDelayMs.coerceIn(baseRetryDelayMs, 60000L),
            exponentialBackoffMultiplier = exponentialBackoffMultiplier.coerceIn(1.0, 5.0),
            
            // Confidence and validation
            confidenceThreshold = confidenceThreshold.coerceIn(0.0, 1.0),
            
            // Cache settings validation
            cacheExpirationHours = cacheExpirationHours.coerceIn(1, 168), // 1 hour to 1 week
            maxCachedRequests = maxCachedRequests.coerceIn(1, 1000),
            
            // Calendar launch validation
            maxCalendarLaunchAttempts = maxCalendarLaunchAttempts.coerceIn(1, 10),
            
            // Timeout validation
            processingTimeoutMs = processingTimeoutMs.coerceIn(1000L, 60000L), // 1 second to 1 minute
            apiTimeoutMs = apiTimeoutMs.coerceIn(1000L, 30000L) // 1 second to 30 seconds
        )
    }
    
    /**
     * Returns true if retry should be attempted based on current configuration
     */
    fun shouldRetry(currentAttempt: Int): Boolean {
        return currentAttempt < maxRetryAttempts
    }
    
    /**
     * Returns true if confidence score meets the threshold
     */
    fun isConfidenceAcceptable(confidence: Double): Boolean {
        return confidence >= confidenceThreshold
    }
    
    /**
     * Returns true if user confirmation should be requested for low confidence
     */
    fun shouldRequestConfirmation(confidence: Double): Boolean {
        return enableUserConfirmationDialogs && !isConfidenceAcceptable(confidence)
    }
    
    /**
     * Returns true if offline mode should be used
     */
    fun shouldUseOfflineMode(networkAvailable: Boolean): Boolean {
        return enableOfflineMode && !networkAvailable
    }
    
    /**
     * Returns true if fallback event creation should be attempted
     */
    fun shouldCreateFallback(): Boolean {
        return enableFallbackCreation
    }
    
    /**
     * Returns true if analytics should be collected
     */
    fun shouldCollectAnalytics(): Boolean {
        return enableAnalyticsCollection
    }
    
    /**
     * Returns true if network connectivity should be checked
     */
    fun shouldCheckNetwork(): Boolean {
        return enableNetworkChecks
    }
    
    /**
     * Returns true if graceful degradation should be applied
     */
    fun shouldApplyGracefulDegradation(): Boolean {
        return enableGracefulDegradation
    }
    
    /**
     * Returns true if the specified log level should be logged
     */
    fun shouldLog(level: LogLevel): Boolean {
        return level.ordinal <= logLevel.ordinal
    }
    
    /**
     * Calculates the retry delay for a given attempt using exponential backoff
     * Implements requirement 6.1 for exponential backoff retry mechanism
     */
    fun calculateRetryDelay(attemptNumber: Int): Long {
        if (attemptNumber <= 0) return baseRetryDelayMs
        
        val exponentialDelay = (baseRetryDelayMs * Math.pow(exponentialBackoffMultiplier, attemptNumber.toDouble())).toLong()
        return exponentialDelay.coerceAtMost(maxRetryDelayMs)
    }
    
    /**
     * Returns true if alternative calendar apps should be tried
     * Implements requirement 6.2 for alternative calendar app attempts
     */
    fun shouldTryAlternativeCalendarApps(): Boolean {
        return enableAlternativeCalendarApps
    }
    
    /**
     * Returns true if comprehensive error catching is enabled
     * Implements requirement 10.1 for try-catch blocks around all operations
     */
    fun shouldUseComprehensiveErrorCatching(): Boolean {
        return enableComprehensiveErrorCatching
    }
    
    /**
     * Returns true if error categorization is enabled
     * Implements requirement 10.2 for error categorization by type
     */
    fun shouldCategorizeErrors(): Boolean {
        return enableErrorCategorization
    }
    
    /**
     * Returns true if crash prevention measures should be applied
     * Implements requirement 10.3 for preventing app crashes
     */
    fun shouldPreventCrashes(): Boolean {
        return enableCrashPrevention
    }
    
    /**
     * Returns true if consistent UI state should be maintained during error recovery
     * Implements requirement 10.4 for maintaining consistent UI state
     */
    fun shouldMaintainConsistentUIState(): Boolean {
        return enableConsistentUIState
    }
    
    /**
     * Returns true if privacy-compliant logging should be used
     */
    fun shouldUsePrivacyCompliantLogging(): Boolean {
        return enablePrivacyCompliantLogging
    }
    
    /**
     * Returns true if web calendar fallback should be attempted
     */
    fun shouldUseWebCalendarFallback(): Boolean {
        return enableWebCalendarFallback
    }
    
    /**
     * Returns true if clipboard fallback should be used
     */
    fun shouldUseClipboardFallback(): Boolean {
        return enableClipboardFallback
    }
}

/**
 * Manager for error handling configuration with runtime updates
 */
class ErrorHandlingConfigManager(private val context: Context) {
    
    private var currentConfig = ErrorHandlingConfig.load(context).validate()
    private val listeners = mutableListOf<(ErrorHandlingConfig) -> Unit>()
    
    /**
     * Gets the current configuration
     */
    fun getConfig(): ErrorHandlingConfig = currentConfig
    
    /**
     * Updates the configuration and notifies listeners
     */
    fun updateConfig(newConfig: ErrorHandlingConfig) {
        val validatedConfig = newConfig.validate()
        validatedConfig.save(context)
        currentConfig = validatedConfig
        
        // Notify listeners of configuration change
        listeners.forEach { listener ->
            try {
                listener(currentConfig)
            } catch (e: Exception) {
                // Log error but don't let it affect other listeners
                android.util.Log.w("ErrorHandlingConfigManager", "Listener failed", e)
            }
        }
    }
    
    /**
     * Adds a listener for configuration changes
     */
    fun addConfigChangeListener(listener: (ErrorHandlingConfig) -> Unit) {
        listeners.add(listener)
    }
    
    /**
     * Removes a configuration change listener
     */
    fun removeConfigChangeListener(listener: (ErrorHandlingConfig) -> Unit) {
        listeners.remove(listener)
    }
    
    /**
     * Resets configuration to defaults
     */
    fun resetToDefaults() {
        updateConfig(ErrorHandlingConfig())
    }
    
    /**
     * Updates specific configuration values
     */
    fun updateRetrySettings(maxAttempts: Int, baseDelayMs: Long, maxDelayMs: Long) {
        updateConfig(currentConfig.copy(
            maxRetryAttempts = maxAttempts,
            baseRetryDelayMs = baseDelayMs,
            maxRetryDelayMs = maxDelayMs
        ))
    }
    
    /**
     * Updates confidence threshold
     */
    fun updateConfidenceThreshold(threshold: Double) {
        updateConfig(currentConfig.copy(confidenceThreshold = threshold))
    }
    
    /**
     * Enables or disables offline mode
     */
    fun setOfflineModeEnabled(enabled: Boolean) {
        updateConfig(currentConfig.copy(enableOfflineMode = enabled))
    }
    
    /**
     * Enables or disables analytics collection
     */
    fun setAnalyticsEnabled(enabled: Boolean) {
        updateConfig(currentConfig.copy(enableAnalyticsCollection = enabled))
    }
    
    /**
     * Updates log level
     */
    fun setLogLevel(level: ErrorHandlingConfig.LogLevel) {
        updateConfig(currentConfig.copy(logLevel = level))
    }
    
    /**
     * Updates calendar launch settings
     * Implements requirement 6.2 for alternative calendar app configuration
     */
    fun updateCalendarLaunchSettings(
        enableAlternativeApps: Boolean,
        maxAttempts: Int,
        enableWebFallback: Boolean,
        enableClipboardFallback: Boolean
    ) {
        updateConfig(currentConfig.copy(
            enableAlternativeCalendarApps = enableAlternativeApps,
            maxCalendarLaunchAttempts = maxAttempts,
            enableWebCalendarFallback = enableWebFallback,
            enableClipboardFallback = enableClipboardFallback
        ))
    }
    
    /**
     * Updates error handling architecture settings
     * Implements requirements 10.1, 10.2 for comprehensive error handling
     */
    fun updateErrorHandlingArchitecture(
        enableComprehensiveErrorCatching: Boolean,
        enableErrorCategorization: Boolean,
        enableCrashPrevention: Boolean,
        enableConsistentUIState: Boolean
    ) {
        updateConfig(currentConfig.copy(
            enableComprehensiveErrorCatching = enableComprehensiveErrorCatching,
            enableErrorCategorization = enableErrorCategorization,
            enableCrashPrevention = enableCrashPrevention,
            enableConsistentUIState = enableConsistentUIState
        ))
    }
    
    /**
     * Updates exponential backoff settings
     * Implements requirement 6.1 for exponential backoff configuration
     */
    fun updateExponentialBackoffSettings(multiplier: Double) {
        updateConfig(currentConfig.copy(exponentialBackoffMultiplier = multiplier))
    }
    
    /**
     * Updates API timeout settings
     */
    fun updateApiTimeout(timeoutMs: Long) {
        updateConfig(currentConfig.copy(apiTimeoutMs = timeoutMs))
    }
    
    /**
     * Enables or disables privacy-compliant logging
     */
    fun setPrivacyCompliantLoggingEnabled(enabled: Boolean) {
        updateConfig(currentConfig.copy(enablePrivacyCompliantLogging = enabled))
    }
    
    /**
     * Gets a configuration summary for debugging purposes
     */
    fun getConfigSummary(): String {
        return buildString {
            appendLine("ErrorHandlingConfig Summary:")
            appendLine("- Max Retry Attempts: ${currentConfig.maxRetryAttempts}")
            appendLine("- Base Retry Delay: ${currentConfig.baseRetryDelayMs}ms")
            appendLine("- Exponential Backoff Multiplier: ${currentConfig.exponentialBackoffMultiplier}")
            appendLine("- Confidence Threshold: ${currentConfig.confidenceThreshold}")
            appendLine("- Alternative Calendar Apps: ${currentConfig.enableAlternativeCalendarApps}")
            appendLine("- Max Calendar Launch Attempts: ${currentConfig.maxCalendarLaunchAttempts}")
            appendLine("- Comprehensive Error Catching: ${currentConfig.enableComprehensiveErrorCatching}")
            appendLine("- Error Categorization: ${currentConfig.enableErrorCategorization}")
            appendLine("- Crash Prevention: ${currentConfig.enableCrashPrevention}")
            appendLine("- API Timeout: ${currentConfig.apiTimeoutMs}ms")
            appendLine("- Log Level: ${currentConfig.logLevel}")
            appendLine("- Privacy Compliant Logging: ${currentConfig.enablePrivacyCompliantLogging}")
        }
    }
}