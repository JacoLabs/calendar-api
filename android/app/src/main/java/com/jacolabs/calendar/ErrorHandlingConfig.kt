package com.jacolabs.calendar

import android.content.Context
import android.content.SharedPreferences

/**
 * Configuration class for error handling behavior with user preferences integration.
 * Provides configurable thresholds, timeouts, and behavior settings for the ErrorHandlingManager.
 */
data class ErrorHandlingConfig(
    val maxRetryAttempts: Int = 3,
    val baseRetryDelayMs: Long = 1000L,
    val maxRetryDelayMs: Long = 30000L,
    val confidenceThreshold: Double = 0.3,
    val enableOfflineMode: Boolean = true,
    val enableFallbackCreation: Boolean = true,
    val enableAnalyticsCollection: Boolean = true,
    val cacheExpirationHours: Int = 24,
    val maxCachedRequests: Int = 50,
    val enableUserConfirmationDialogs: Boolean = true,
    val enableNetworkChecks: Boolean = true,
    val processingTimeoutMs: Long = 15000L,
    val enableGracefulDegradation: Boolean = true,
    val logLevel: LogLevel = LogLevel.INFO
) {
    
    enum class LogLevel {
        NONE, ERROR, WARN, INFO, DEBUG
    }
    
    companion object {
        private const val PREFS_NAME = "error_handling_config"
        private const val KEY_MAX_RETRY_ATTEMPTS = "max_retry_attempts"
        private const val KEY_BASE_RETRY_DELAY_MS = "base_retry_delay_ms"
        private const val KEY_MAX_RETRY_DELAY_MS = "max_retry_delay_ms"
        private const val KEY_CONFIDENCE_THRESHOLD = "confidence_threshold"
        private const val KEY_ENABLE_OFFLINE_MODE = "enable_offline_mode"
        private const val KEY_ENABLE_FALLBACK_CREATION = "enable_fallback_creation"
        private const val KEY_ENABLE_ANALYTICS_COLLECTION = "enable_analytics_collection"
        private const val KEY_CACHE_EXPIRATION_HOURS = "cache_expiration_hours"
        private const val KEY_MAX_CACHED_REQUESTS = "max_cached_requests"
        private const val KEY_ENABLE_USER_CONFIRMATION_DIALOGS = "enable_user_confirmation_dialogs"
        private const val KEY_ENABLE_NETWORK_CHECKS = "enable_network_checks"
        private const val KEY_PROCESSING_TIMEOUT_MS = "processing_timeout_ms"
        private const val KEY_ENABLE_GRACEFUL_DEGRADATION = "enable_graceful_degradation"
        private const val KEY_LOG_LEVEL = "log_level"
        
        /**
         * Loads configuration from SharedPreferences with default values
         */
        fun load(context: Context): ErrorHandlingConfig {
            val prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
            
            return ErrorHandlingConfig(
                maxRetryAttempts = prefs.getInt(KEY_MAX_RETRY_ATTEMPTS, 3),
                baseRetryDelayMs = prefs.getLong(KEY_BASE_RETRY_DELAY_MS, 1000L),
                maxRetryDelayMs = prefs.getLong(KEY_MAX_RETRY_DELAY_MS, 30000L),
                confidenceThreshold = prefs.getFloat(KEY_CONFIDENCE_THRESHOLD, 0.3f).toDouble(),
                enableOfflineMode = prefs.getBoolean(KEY_ENABLE_OFFLINE_MODE, true),
                enableFallbackCreation = prefs.getBoolean(KEY_ENABLE_FALLBACK_CREATION, true),
                enableAnalyticsCollection = prefs.getBoolean(KEY_ENABLE_ANALYTICS_COLLECTION, true),
                cacheExpirationHours = prefs.getInt(KEY_CACHE_EXPIRATION_HOURS, 24),
                maxCachedRequests = prefs.getInt(KEY_MAX_CACHED_REQUESTS, 50),
                enableUserConfirmationDialogs = prefs.getBoolean(KEY_ENABLE_USER_CONFIRMATION_DIALOGS, true),
                enableNetworkChecks = prefs.getBoolean(KEY_ENABLE_NETWORK_CHECKS, true),
                processingTimeoutMs = prefs.getLong(KEY_PROCESSING_TIMEOUT_MS, 15000L),
                enableGracefulDegradation = prefs.getBoolean(KEY_ENABLE_GRACEFUL_DEGRADATION, true),
                logLevel = LogLevel.valueOf(prefs.getString(KEY_LOG_LEVEL, LogLevel.INFO.name) ?: LogLevel.INFO.name)
            )
        }
        
        /**
         * Creates a configuration optimized for production use
         */
        fun forProduction(): ErrorHandlingConfig {
            return ErrorHandlingConfig(
                maxRetryAttempts = 2,
                baseRetryDelayMs = 2000L,
                maxRetryDelayMs = 15000L,
                confidenceThreshold = 0.4,
                enableOfflineMode = true,
                enableFallbackCreation = true,
                enableAnalyticsCollection = true,
                cacheExpirationHours = 12,
                maxCachedRequests = 25,
                enableUserConfirmationDialogs = true,
                enableNetworkChecks = true,
                processingTimeoutMs = 10000L,
                enableGracefulDegradation = true,
                logLevel = LogLevel.WARN
            )
        }
        
        /**
         * Creates a configuration optimized for development/testing
         */
        fun forDevelopment(): ErrorHandlingConfig {
            return ErrorHandlingConfig(
                maxRetryAttempts = 5,
                baseRetryDelayMs = 500L,
                maxRetryDelayMs = 5000L,
                confidenceThreshold = 0.2,
                enableOfflineMode = true,
                enableFallbackCreation = true,
                enableAnalyticsCollection = true,
                cacheExpirationHours = 48,
                maxCachedRequests = 100,
                enableUserConfirmationDialogs = false, // Skip dialogs in testing
                enableNetworkChecks = true,
                processingTimeoutMs = 30000L,
                enableGracefulDegradation = true,
                logLevel = LogLevel.DEBUG
            )
        }
    }
    
    /**
     * Saves the current configuration to SharedPreferences
     */
    fun save(context: Context) {
        val prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
        
        prefs.edit()
            .putInt(KEY_MAX_RETRY_ATTEMPTS, maxRetryAttempts)
            .putLong(KEY_BASE_RETRY_DELAY_MS, baseRetryDelayMs)
            .putLong(KEY_MAX_RETRY_DELAY_MS, maxRetryDelayMs)
            .putFloat(KEY_CONFIDENCE_THRESHOLD, confidenceThreshold.toFloat())
            .putBoolean(KEY_ENABLE_OFFLINE_MODE, enableOfflineMode)
            .putBoolean(KEY_ENABLE_FALLBACK_CREATION, enableFallbackCreation)
            .putBoolean(KEY_ENABLE_ANALYTICS_COLLECTION, enableAnalyticsCollection)
            .putInt(KEY_CACHE_EXPIRATION_HOURS, cacheExpirationHours)
            .putInt(KEY_MAX_CACHED_REQUESTS, maxCachedRequests)
            .putBoolean(KEY_ENABLE_USER_CONFIRMATION_DIALOGS, enableUserConfirmationDialogs)
            .putBoolean(KEY_ENABLE_NETWORK_CHECKS, enableNetworkChecks)
            .putLong(KEY_PROCESSING_TIMEOUT_MS, processingTimeoutMs)
            .putBoolean(KEY_ENABLE_GRACEFUL_DEGRADATION, enableGracefulDegradation)
            .putString(KEY_LOG_LEVEL, logLevel.name)
            .apply()
    }
    
    /**
     * Validates configuration values and returns a corrected version if needed
     */
    fun validate(): ErrorHandlingConfig {
        return copy(
            maxRetryAttempts = maxRetryAttempts.coerceIn(0, 10),
            baseRetryDelayMs = baseRetryDelayMs.coerceIn(100L, 10000L),
            maxRetryDelayMs = maxRetryDelayMs.coerceIn(baseRetryDelayMs, 60000L),
            confidenceThreshold = confidenceThreshold.coerceIn(0.0, 1.0),
            cacheExpirationHours = cacheExpirationHours.coerceIn(1, 168), // 1 hour to 1 week
            maxCachedRequests = maxCachedRequests.coerceIn(1, 1000),
            processingTimeoutMs = processingTimeoutMs.coerceIn(1000L, 60000L) // 1 second to 1 minute
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
}