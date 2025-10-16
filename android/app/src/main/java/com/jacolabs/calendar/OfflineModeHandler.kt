package com.jacolabs.calendar

import android.content.Context
import android.content.SharedPreferences
import android.net.ConnectivityManager
import android.net.NetworkCapabilities
import android.os.Build
import android.util.Log
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONArray
import org.json.JSONObject
import java.text.SimpleDateFormat
import java.util.*
import kotlin.collections.ArrayList

/**
 * Handles offline functionality for network-independent event creation.
 * Provides local text processing, request caching, and automatic retry mechanisms.
 * 
 * This component ensures users can create calendar events even when network connectivity
 * is unavailable, with intelligent caching and retry logic for when connectivity returns.
 */
class OfflineModeHandler(private val context: Context) {
    
    companion object {
        private const val TAG = "OfflineModeHandler"
        private const val PREFS_NAME = "offline_mode_prefs"
        private const val KEY_CACHED_REQUESTS = "cached_requests"
        private const val KEY_OFFLINE_MODE_ENABLED = "offline_mode_enabled"
        private const val KEY_LAST_CONNECTIVITY_CHECK = "last_connectivity_check"
        private const val KEY_OFFLINE_EVENTS_CREATED = "offline_events_created"
        
        // Cache management constants
        private const val MAX_CACHED_REQUESTS = 50
        private const val CACHE_CLEANUP_THRESHOLD = 75
        private const val CACHE_EXPIRATION_HOURS = 24
        private const val CONNECTIVITY_CHECK_INTERVAL_MS = 30000L // 30 seconds
        
        // Offline processing constants
        private const val OFFLINE_CONFIDENCE_SCORE = 0.15
        private const val OFFLINE_FALLBACK_REASON = "Created offline - no network available"
    }
    
    /**
     * Data class representing a cached request for later retry
     */
    data class CachedRequest(
        val text: String,
        val timestamp: Long,
        val timezone: String,
        val locale: String,
        val retryCount: Int = 0,
        val id: String = UUID.randomUUID().toString(),
        val mode: String? = null,
        val fields: List<String>? = null,
        val originalNow: String? = null
    )
    
    /**
     * Result of offline processing with metadata
     */
    data class OfflineProcessingResult(
        val parseResult: ParseResult,
        val processingMethod: String,
        val confidence: Double,
        val fallbacksApplied: List<String>
    )
    
    /**
     * Statistics about offline mode usage
     */
    data class OfflineStats(
        val totalOfflineEventsCreated: Int,
        val cachedRequestsCount: Int,
        val successfulRetries: Int,
        val failedRetries: Int,
        val lastConnectivityCheck: Long,
        val isCurrentlyOffline: Boolean
    )
    
    private val sharedPrefs: SharedPreferences = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
    private val fallbackEventGenerator = FallbackEventGenerator(context)
    private val connectivityManager = context.getSystemService(Context.CONNECTIVITY_SERVICE) as? ConnectivityManager
    
    /**
     * Creates an offline event using local text processing
     */
    suspend fun createOfflineEvent(text: String): ParseResult = withContext(Dispatchers.Default) {
        Log.d(TAG, "Creating offline event for text length: ${text.length}")
        
        try {
            // Use FallbackEventGenerator for intelligent offline processing
            val fallbackEvent = fallbackEventGenerator.generateFallbackEvent(text, null)
            
            // Convert to ParseResult with offline-specific metadata
            val offlineResult = fallbackEventGenerator.toParseResult(fallbackEvent, text).copy(
                confidenceScore = OFFLINE_CONFIDENCE_SCORE,
                fallbackApplied = true,
                fallbackReason = OFFLINE_FALLBACK_REASON,
                originalText = text,
                description = "Offline event from: \"$text\"\n\n${fallbackEvent.description}",
                errorRecoveryInfo = ErrorRecoveryInfo(
                    recoveryMethod = "offline_local_processing",
                    confidenceBeforeRecovery = 0.0,
                    dataSourcesUsed = listOf("local_text_processing", "fallback_generator"),
                    userInterventionRequired = true
                )
            )
            
            // Track offline event creation
            incrementOfflineEventsCreated()
            
            Log.i(TAG, "Successfully created offline event with title: ${offlineResult.title}")
            
            return@withContext offlineResult
            
        } catch (e: Exception) {
            Log.e(TAG, "Failed to create offline event", e)
            
            // Create minimal fallback event
            val minimalEvent = createMinimalOfflineEvent(text)
            return@withContext minimalEvent
        }
    }
    
    /**
     * Creates a minimal offline event when sophisticated processing fails
     */
    private fun createMinimalOfflineEvent(text: String): ParseResult {
        val calendar = Calendar.getInstance()
        calendar.add(Calendar.HOUR_OF_DAY, 1) // Default to next hour
        calendar.set(Calendar.MINUTE, 0)
        calendar.set(Calendar.SECOND, 0)
        calendar.set(Calendar.MILLISECOND, 0)
        
        val formatter = SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ssXXX", Locale.getDefault())
        val startTime = formatter.format(calendar.time)
        
        calendar.add(Calendar.HOUR_OF_DAY, 1) // 1 hour duration
        val endTime = formatter.format(calendar.time)
        
        // Extract a basic title from the text
        val title = extractBasicTitle(text)
        
        return ParseResult(
            title = title,
            startDateTime = startTime,
            endDateTime = endTime,
            location = null,
            description = "Offline event from: \"$text\"",
            confidenceScore = 0.1,
            allDay = false,
            timezone = TimeZone.getDefault().id,
            fallbackApplied = true,
            fallbackReason = "Minimal offline processing - sophisticated processing failed",
            originalText = text,
            errorRecoveryInfo = ErrorRecoveryInfo(
                recoveryMethod = "minimal_offline_processing",
                confidenceBeforeRecovery = 0.0,
                dataSourcesUsed = listOf("basic_text_extraction"),
                userInterventionRequired = true
            )
        )
    }
    
    /**
     * Extracts a basic title from text when sophisticated processing fails
     */
    private fun extractBasicTitle(text: String): String {
        val cleaned = text.trim()
        
        // Take first sentence or first 50 characters
        val firstSentence = cleaned.split(Regex("[.!?]")).firstOrNull()?.trim()
        
        return when {
            !firstSentence.isNullOrBlank() && firstSentence.length <= 50 -> firstSentence
            cleaned.length <= 50 -> cleaned
            else -> cleaned.substring(0, 47) + "..."
        }.ifBlank { "Offline Event" }
    }
    
    /**
     * Caches a failed request for later retry when connectivity returns
     */
    fun cacheFailedRequest(request: CachedRequest) {
        try {
            Log.d(TAG, "Caching failed request: ${request.id}")
            
            val cachedRequests = getCachedRequests().toMutableList()
            
            // Remove any existing request with the same ID
            cachedRequests.removeAll { it.id == request.id }
            
            // Add new request
            cachedRequests.add(request)
            
            // Clean up old requests if needed
            val cleanedRequests = if (cachedRequests.size > CACHE_CLEANUP_THRESHOLD) {
                cleanupExpiredRequests(cachedRequests)
            } else {
                cachedRequests
            }
            
            // Limit to max cached requests
            val finalRequests = if (cleanedRequests.size > MAX_CACHED_REQUESTS) {
                cleanedRequests.sortedByDescending { it.timestamp }.take(MAX_CACHED_REQUESTS)
            } else {
                cleanedRequests
            }
            
            // Save to SharedPreferences
            saveCachedRequests(finalRequests)
            
            Log.i(TAG, "Cached request successfully. Total cached: ${finalRequests.size}")
            
        } catch (e: Exception) {
            Log.e(TAG, "Failed to cache request", e)
        }
    }
    
    /**
     * Convenience method to cache a failed request from API parameters
     */
    fun cacheFailedRequest(
        text: String,
        timezone: String,
        locale: String,
        now: Date,
        mode: String? = null,
        fields: List<String>? = null
    ) {
        val formatter = SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss'Z'", Locale.US)
        formatter.timeZone = TimeZone.getTimeZone("UTC")
        
        val request = CachedRequest(
            text = text,
            timestamp = System.currentTimeMillis(),
            timezone = timezone,
            locale = locale,
            mode = mode,
            fields = fields,
            originalNow = formatter.format(now)
        )
        
        cacheFailedRequest(request)
    }
    
    /**
     * Retries all pending cached requests when connectivity returns
     */
    suspend fun retryPendingRequests(): List<ParseResult> = withContext(Dispatchers.IO) {
        Log.d(TAG, "Retrying pending cached requests")
        
        val cachedRequests = getCachedRequests()
        if (cachedRequests.isEmpty()) {
            Log.d(TAG, "No cached requests to retry")
            return@withContext emptyList()
        }
        
        val results = mutableListOf<ParseResult>()
        val successfulRequests = mutableListOf<String>()
        val failedRequests = mutableListOf<CachedRequest>()
        
        // Check connectivity before attempting retries
        if (!isNetworkAvailable()) {
            Log.w(TAG, "Network still unavailable, skipping retry")
            return@withContext emptyList()
        }
        
        Log.i(TAG, "Retrying ${cachedRequests.size} cached requests")
        
        for (request in cachedRequests) {
            try {
                // Check if request has expired
                if (isRequestExpired(request)) {
                    Log.d(TAG, "Request ${request.id} has expired, skipping")
                    continue
                }
                
                // Attempt to retry the request
                val result = retryRequest(request)
                if (result != null) {
                    results.add(result)
                    successfulRequests.add(request.id)
                    Log.d(TAG, "Successfully retried request ${request.id}")
                } else {
                    // Increment retry count and re-cache if under limit
                    val updatedRequest = request.copy(retryCount = request.retryCount + 1)
                    if (updatedRequest.retryCount < 3) { // Max 3 retry attempts
                        failedRequests.add(updatedRequest)
                        Log.d(TAG, "Retry failed for request ${request.id}, will retry again (attempt ${updatedRequest.retryCount})")
                    } else {
                        Log.w(TAG, "Max retries exceeded for request ${request.id}, discarding")
                    }
                }
                
            } catch (e: Exception) {
                Log.e(TAG, "Error retrying request ${request.id}", e)
                
                // Re-cache for later retry if under limit
                val updatedRequest = request.copy(retryCount = request.retryCount + 1)
                if (updatedRequest.retryCount < 3) {
                    failedRequests.add(updatedRequest)
                }
            }
        }
        
        // Update cached requests (remove successful ones, keep failed ones for retry)
        saveCachedRequests(failedRequests)
        
        Log.i(TAG, "Retry completed: ${results.size} successful, ${failedRequests.size} still pending")
        
        return@withContext results
    }
    
    /**
     * Attempts to retry a single cached request
     */
    private suspend fun retryRequest(request: CachedRequest): ParseResult? {
        return try {
            // Create ApiService instance for retry
            val apiService = ApiService(context)
            
            // Parse the original timestamp back to Date
            val now = if (request.originalNow != null) {
                val formatter = SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss'Z'", Locale.US)
                formatter.timeZone = TimeZone.getTimeZone("UTC")
                formatter.parse(request.originalNow) ?: Date()
            } else {
                Date()
            }
            
            // Retry the API call
            apiService.parseText(
                text = request.text,
                timezone = request.timezone,
                locale = request.locale,
                now = now,
                mode = request.mode,
                fields = request.fields
            )
            
        } catch (e: Exception) {
            Log.w(TAG, "Retry attempt failed for request ${request.id}", e)
            null
        }
    }
    
    /**
     * Checks if a cached request has expired
     */
    private fun isRequestExpired(request: CachedRequest): Boolean {
        val expirationTime = request.timestamp + (CACHE_EXPIRATION_HOURS * 60 * 60 * 1000)
        return System.currentTimeMillis() > expirationTime
    }
    
    /**
     * Detects if the device is currently in offline mode
     */
    fun isOfflineModeEnabled(): Boolean {
        return sharedPrefs.getBoolean(KEY_OFFLINE_MODE_ENABLED, true)
    }
    
    /**
     * Enables or disables offline mode
     */
    fun setOfflineModeEnabled(enabled: Boolean) {
        sharedPrefs.edit()
            .putBoolean(KEY_OFFLINE_MODE_ENABLED, enabled)
            .apply()
        
        Log.i(TAG, "Offline mode ${if (enabled) "enabled" else "disabled"}")
    }
    
    /**
     * Checks network availability using multiple methods
     */
    fun isNetworkAvailable(): Boolean {
        // Update last connectivity check timestamp
        sharedPrefs.edit()
            .putLong(KEY_LAST_CONNECTIVITY_CHECK, System.currentTimeMillis())
            .apply()
        
        return try {
            connectivityManager?.let { cm ->
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
                    val network = cm.activeNetwork ?: return false
                    val capabilities = cm.getNetworkCapabilities(network) ?: return false
                    capabilities.hasCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET) &&
                    capabilities.hasCapability(NetworkCapabilities.NET_CAPABILITY_VALIDATED)
                } else {
                    @Suppress("DEPRECATION")
                    val networkInfo = cm.activeNetworkInfo
                    networkInfo?.isConnected == true
                }
            } ?: false
        } catch (e: Exception) {
            Log.w(TAG, "Error checking network availability", e)
            false
        }
    }
    
    /**
     * Provides user notification about offline mode status
     */
    fun getOfflineStatusMessage(): String {
        return when {
            !isOfflineModeEnabled() -> "Offline mode is disabled. Enable it in settings to create events without internet."
            !isNetworkAvailable() -> "You're offline. Events will be created locally and may need adjustment later."
            else -> "You're online. Full parsing features are available."
        }
    }
    
    /**
     * Gets statistics about offline mode usage
     */
    fun getOfflineStats(): OfflineStats {
        val cachedRequests = getCachedRequests()
        
        return OfflineStats(
            totalOfflineEventsCreated = sharedPrefs.getInt(KEY_OFFLINE_EVENTS_CREATED, 0),
            cachedRequestsCount = cachedRequests.size,
            successfulRetries = 0, // Would need additional tracking
            failedRetries = 0,     // Would need additional tracking
            lastConnectivityCheck = sharedPrefs.getLong(KEY_LAST_CONNECTIVITY_CHECK, 0),
            isCurrentlyOffline = !isNetworkAvailable()
        )
    }
    
    /**
     * Clears all cached requests
     */
    fun clearCachedRequests() {
        sharedPrefs.edit()
            .remove(KEY_CACHED_REQUESTS)
            .apply()
        
        Log.i(TAG, "Cleared all cached requests")
    }
    
    /**
     * Clears offline statistics
     */
    fun clearOfflineStats() {
        sharedPrefs.edit()
            .remove(KEY_OFFLINE_EVENTS_CREATED)
            .remove(KEY_LAST_CONNECTIVITY_CHECK)
            .apply()
        
        Log.i(TAG, "Cleared offline statistics")
    }
    
    /**
     * Gets all cached requests from SharedPreferences
     */
    private fun getCachedRequests(): List<CachedRequest> {
        return try {
            val requestsJson = sharedPrefs.getString(KEY_CACHED_REQUESTS, "[]")
            val requestsArray = JSONArray(requestsJson)
            
            val requests = mutableListOf<CachedRequest>()
            for (i in 0 until requestsArray.length()) {
                val requestJson = requestsArray.getJSONObject(i)
                
                val fieldsArray = requestJson.optJSONArray("fields")
                val fields = if (fieldsArray != null) {
                    val fieldsList = mutableListOf<String>()
                    for (j in 0 until fieldsArray.length()) {
                        fieldsList.add(fieldsArray.getString(j))
                    }
                    fieldsList
                } else null
                
                requests.add(
                    CachedRequest(
                        text = requestJson.getString("text"),
                        timestamp = requestJson.getLong("timestamp"),
                        timezone = requestJson.getString("timezone"),
                        locale = requestJson.getString("locale"),
                        retryCount = requestJson.optInt("retry_count", 0),
                        id = requestJson.optString("id", UUID.randomUUID().toString()),
                        mode = requestJson.optString("mode").takeIf { it.isNotEmpty() },
                        fields = fields,
                        originalNow = requestJson.optString("original_now").takeIf { it.isNotEmpty() }
                    )
                )
            }
            
            requests
        } catch (e: Exception) {
            Log.e(TAG, "Failed to load cached requests", e)
            emptyList()
        }
    }
    
    /**
     * Saves cached requests to SharedPreferences
     */
    private fun saveCachedRequests(requests: List<CachedRequest>) {
        try {
            val requestsArray = JSONArray()
            
            for (request in requests) {
                val requestJson = JSONObject().apply {
                    put("text", request.text)
                    put("timestamp", request.timestamp)
                    put("timezone", request.timezone)
                    put("locale", request.locale)
                    put("retry_count", request.retryCount)
                    put("id", request.id)
                    
                    request.mode?.let { put("mode", it) }
                    request.originalNow?.let { put("original_now", it) }
                    
                    request.fields?.let { fields ->
                        val fieldsArray = JSONArray()
                        fields.forEach { fieldsArray.put(it) }
                        put("fields", fieldsArray)
                    }
                }
                
                requestsArray.put(requestJson)
            }
            
            sharedPrefs.edit()
                .putString(KEY_CACHED_REQUESTS, requestsArray.toString())
                .apply()
                
        } catch (e: Exception) {
            Log.e(TAG, "Failed to save cached requests", e)
        }
    }
    
    /**
     * Cleans up expired requests from the cache
     */
    private fun cleanupExpiredRequests(requests: List<CachedRequest>): List<CachedRequest> {
        val currentTime = System.currentTimeMillis()
        val expirationThreshold = CACHE_EXPIRATION_HOURS * 60 * 60 * 1000
        
        val validRequests = requests.filter { request ->
            (currentTime - request.timestamp) < expirationThreshold
        }
        
        val removedCount = requests.size - validRequests.size
        if (removedCount > 0) {
            Log.i(TAG, "Cleaned up $removedCount expired cached requests")
        }
        
        return validRequests
    }
    
    /**
     * Increments the counter for offline events created
     */
    private fun incrementOfflineEventsCreated() {
        val currentCount = sharedPrefs.getInt(KEY_OFFLINE_EVENTS_CREATED, 0)
        sharedPrefs.edit()
            .putInt(KEY_OFFLINE_EVENTS_CREATED, currentCount + 1)
            .apply()
    }
    
    /**
     * Checks if enough time has passed since last connectivity check
     */
    fun shouldCheckConnectivity(): Boolean {
        val lastCheck = sharedPrefs.getLong(KEY_LAST_CONNECTIVITY_CHECK, 0)
        val timeSinceLastCheck = System.currentTimeMillis() - lastCheck
        return timeSinceLastCheck > CONNECTIVITY_CHECK_INTERVAL_MS
    }
    
    /**
     * Performs automatic retry of cached requests if connectivity is available
     * This method can be called periodically by the app
     */
    suspend fun performAutomaticRetry(): Int {
        if (!shouldCheckConnectivity()) {
            return 0
        }
        
        if (!isNetworkAvailable()) {
            return 0
        }
        
        val results = retryPendingRequests()
        return results.size
    }
}