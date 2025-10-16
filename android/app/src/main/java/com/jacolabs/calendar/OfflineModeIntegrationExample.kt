package com.jacolabs.calendar

import android.content.Context
import android.util.Log
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import java.util.*

/**
 * Example integration showing how OfflineModeHandler works with ErrorHandlingManager
 * and other components in the error handling system.
 */
class OfflineModeIntegrationExample(private val context: Context) {
    
    companion object {
        private const val TAG = "OfflineModeIntegration"
    }
    
    private val offlineModeHandler = OfflineModeHandler(context)
    private val errorHandlingManager = ErrorHandlingManager(context)
    private val apiService = ApiService(context)
    
    /**
     * Demonstrates how to handle API calls with offline fallback
     */
    suspend fun handleTextParsingWithOfflineFallback(
        text: String,
        timezone: String = TimeZone.getDefault().id,
        locale: String = Locale.getDefault().toString()
    ): ParseResult {
        
        Log.d(TAG, "Processing text with offline fallback support")
        
        // Check if we're offline first
        if (!offlineModeHandler.isNetworkAvailable()) {
            Log.i(TAG, "Network unavailable, creating offline event")
            return offlineModeHandler.createOfflineEvent(text)
        }
        
        // Try API call with error handling
        return try {
            val result = apiService.parseText(
                text = text,
                timezone = timezone,
                locale = locale,
                now = Date()
            )
            
            Log.i(TAG, "API call successful")
            result
            
        } catch (e: ApiException) {
            Log.w(TAG, "API call failed, handling with ErrorHandlingManager", e)
            
            // Use ErrorHandlingManager to determine recovery strategy
            val errorContext = ErrorHandlingManager.ErrorContext(
                errorType = errorHandlingManager.categorizeError(e),
                originalText = text,
                exception = e,
                networkAvailable = offlineModeHandler.isNetworkAvailable()
            )
            
            val errorResult = errorHandlingManager.handleError(errorContext)
            
            when (errorResult.recoveryStrategy) {
                ErrorHandlingManager.RecoveryStrategy.OFFLINE_MODE -> {
                    Log.i(TAG, "Using offline mode recovery")
                    offlineModeHandler.createOfflineEvent(text)
                }
                
                ErrorHandlingManager.RecoveryStrategy.CACHE_AND_RETRY_LATER -> {
                    Log.i(TAG, "Caching request for later retry")
                    offlineModeHandler.cacheFailedRequest(text, timezone, locale, Date())
                    offlineModeHandler.createOfflineEvent(text)
                }
                
                else -> {
                    // Use the recovery result from ErrorHandlingManager
                    errorResult.recoveredResult ?: offlineModeHandler.createOfflineEvent(text)
                }
            }
        }
    }
    
    /**
     * Demonstrates periodic retry of cached requests
     */
    fun startPeriodicRetryService() {
        Log.d(TAG, "Starting periodic retry service")
        
        CoroutineScope(Dispatchers.IO).launch {
            while (true) {
                try {
                    if (offlineModeHandler.shouldCheckConnectivity()) {
                        val retriedCount = offlineModeHandler.performAutomaticRetry()
                        if (retriedCount > 0) {
                            Log.i(TAG, "Successfully retried $retriedCount cached requests")
                        }
                    }
                    
                    // Wait 30 seconds before next check
                    kotlinx.coroutines.delay(30000)
                    
                } catch (e: Exception) {
                    Log.e(TAG, "Error in periodic retry service", e)
                    kotlinx.coroutines.delay(60000) // Wait longer on error
                }
            }
        }
    }
    
    /**
     * Demonstrates how to show offline status to users
     */
    fun getOfflineStatusForUser(): String {
        val stats = offlineModeHandler.getOfflineStats()
        val statusMessage = offlineModeHandler.getOfflineStatusMessage()
        
        return buildString {
            append(statusMessage)
            
            if (stats.cachedRequestsCount > 0) {
                append("\n\nYou have ${stats.cachedRequestsCount} requests waiting to be processed when you're back online.")
            }
            
            if (stats.totalOfflineEventsCreated > 0) {
                append("\n\nYou've created ${stats.totalOfflineEventsCreated} events while offline.")
            }
        }
    }
    
    /**
     * Demonstrates cache management
     */
    fun manageCacheIfNeeded() {
        val stats = offlineModeHandler.getOfflineStats()
        
        // Clear cache if too many requests are pending
        if (stats.cachedRequestsCount > 40) {
            Log.w(TAG, "Cache getting full (${stats.cachedRequestsCount} requests), consider clearing old requests")
            // In a real app, you might want to show a dialog to the user
        }
        
        // Example: Clear cache older than 7 days
        // This would require additional implementation in OfflineModeHandler
        Log.d(TAG, "Cache contains ${stats.cachedRequestsCount} pending requests")
    }
    
    /**
     * Example of how to integrate offline mode with MainActivity
     */
    suspend fun processTextFromMainActivity(text: String): ParseResult {
        Log.d(TAG, "Processing text from MainActivity: ${text.take(50)}...")
        
        // Show offline status to user if needed
        if (!offlineModeHandler.isNetworkAvailable() && offlineModeHandler.isOfflineModeEnabled()) {
            Log.i(TAG, "User notification: ${offlineModeHandler.getOfflineStatusMessage()}")
        }
        
        // Process with offline fallback
        return handleTextParsingWithOfflineFallback(text)
    }
    
    /**
     * Example of how to handle app startup with cached requests
     */
    suspend fun handleAppStartup() {
        Log.d(TAG, "Handling app startup - checking for cached requests")
        
        if (offlineModeHandler.isNetworkAvailable()) {
            val retriedCount = offlineModeHandler.performAutomaticRetry()
            if (retriedCount > 0) {
                Log.i(TAG, "App startup: Successfully processed $retriedCount cached requests")
                // In a real app, you might want to show a notification to the user
            }
        }
        
        // Show offline stats if relevant
        val stats = offlineModeHandler.getOfflineStats()
        if (stats.cachedRequestsCount > 0 || stats.totalOfflineEventsCreated > 0) {
            Log.i(TAG, "Offline stats: ${stats.cachedRequestsCount} pending, ${stats.totalOfflineEventsCreated} created offline")
        }
    }
}