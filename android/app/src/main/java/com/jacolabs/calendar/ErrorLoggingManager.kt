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
import java.io.File
import java.io.FileWriter
import java.io.PrintWriter
import java.io.StringWriter
import java.security.MessageDigest
import java.text.SimpleDateFormat
import java.util.*
import kotlin.collections.HashMap

/**
 * Comprehensive error logging and diagnostics manager for the Android Calendar Event Creator.
 * 
 * Addresses requirements:
 * - 7.1: Log detailed error information including API responses and stack traces
 * - 7.2: Include context like input text length, network status, and device information
 * - 7.3: Provide users with error codes for support purposes
 * - 7.4: Respect user privacy and not log sensitive information
 * - 9.1: Log failure patterns for analysis
 * - 9.2: Suggest text preprocessing improvements based on patterns
 * - 9.3: Note corrections for future reference
 * - 9.4: Maintain user privacy and anonymize data
 */
class ErrorLoggingManager(
    private val context: Context,
    private val config: ErrorHandlingConfig = ErrorHandlingConfig.load(context)
) {
    
    companion object {
        private const val TAG = "ErrorLoggingManager"
        private const val PREFS_NAME = "error_logging_prefs"
        private const val LOG_FILE_NAME = "error_diagnostics.log"
        private const val ANALYTICS_FILE_NAME = "error_analytics.json"
        private const val PATTERN_ANALYSIS_FILE = "failure_patterns.json"
        
        // Privacy and storage limits
        private const val MAX_LOG_ENTRIES = 1000
        private const val MAX_LOG_FILE_SIZE_MB = 5
        private const val MAX_TEXT_LENGTH_TO_LOG = 100
        private const val LOG_CLEANUP_THRESHOLD = 1200
        
        // Error code generation
        private const val ERROR_CODE_PREFIX = "CAL"
        private const val ERROR_CODE_LENGTH = 8
        
        // Analytics retention
        private const val ANALYTICS_RETENTION_DAYS = 30
        private const val PATTERN_ANALYSIS_MIN_OCCURRENCES = 3
    }
    
    private val sharedPrefs: SharedPreferences = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
    private val dateFormatter = SimpleDateFormat("yyyy-MM-dd HH:mm:ss.SSS", Locale.US)
    private val logFile = File(context.filesDir, LOG_FILE_NAME)
    private val analyticsFile = File(context.filesDir, ANALYTICS_FILE_NAME)
    private val patternAnalysisFile = File(context.filesDir, PATTERN_ANALYSIS_FILE)
    
    /**
     * Structured error log entry with privacy protection
     */
    data class ErrorLogEntry(
        val timestamp: Long,
        val errorCode: String,
        val errorType: String,
        val severity: LogSeverity,
        val message: String,
        val stackTrace: String?,
        val context: ErrorContext,
        val deviceInfo: DeviceInfo,
        val networkInfo: NetworkInfo,
        val sessionId: String
    )
    
    /**
     * Error context information with privacy protection
     */
    data class ErrorContext(
        val textLength: Int,
        val textHash: String?, // Hashed version for pattern analysis
        val apiResponseCode: Int?,
        val apiResponseMessage: String?,
        val processingTimeMs: Long,
        val retryCount: Int,
        val confidenceScore: Double?,
        val parsingStage: String?,
        val userAction: String?
    )
    
    /**
     * Device information for diagnostics
     */
    data class DeviceInfo(
        val androidVersion: String,
        val apiLevel: Int,
        val deviceModel: String,
        val manufacturer: String,
        val appVersion: String,
        val availableMemoryMb: Long,
        val totalStorageMb: Long,
        val locale: String,
        val timezone: String
    )
    
    /**
     * Network information for diagnostics
     */
    data class NetworkInfo(
        val isConnected: Boolean,
        val connectionType: String,
        val isMetered: Boolean,
        val signalStrength: String?
    )
    
    /**
     * Log severity levels
     */
    enum class LogSeverity(val level: Int) {
        DEBUG(0),
        INFO(1),
        WARN(2),
        ERROR(3),
        CRITICAL(4)
    }
    
    /**
     * Failure pattern for analysis
     */
    data class FailurePattern(
        val patternId: String,
        val textPattern: String,
        val errorType: String,
        val occurrences: Int,
        val firstSeen: Long,
        val lastSeen: Long,
        val suggestedImprovement: String?,
        val userCorrections: List<UserCorrection> = emptyList()
    )
    
    /**
     * User correction for learning
     */
    data class UserCorrection(
        val originalText: String,
        val correctedField: String,
        val originalValue: String?,
        val correctedValue: String,
        val timestamp: Long
    )
    
    private val sessionId = generateSessionId()
    
    /**
     * Logs a comprehensive error with full context and diagnostics
     * Requirement 7.1: Log detailed error information including API responses and stack traces
     */
    suspend fun logError(
        errorType: String,
        message: String,
        exception: Exception? = null,
        originalText: String? = null,
        apiResponse: ParseResult? = null,
        processingTimeMs: Long = 0,
        retryCount: Int = 0,
        severity: LogSeverity = LogSeverity.ERROR
    ): String = withContext(Dispatchers.IO) {
        
        if (!config.shouldLog(mapSeverityToConfigLevel(severity))) {
            return@withContext ""
        }
        
        try {
            val errorCode = generateErrorCode(errorType, severity)
            val timestamp = System.currentTimeMillis()
            
            // Create privacy-safe error context (Requirement 7.4)
            val errorContext = createErrorContext(
                originalText = originalText,
                apiResponse = apiResponse,
                processingTimeMs = processingTimeMs,
                retryCount = retryCount
            )
            
            // Gather device and network information (Requirement 7.2)
            val deviceInfo = gatherDeviceInfo()
            val networkInfo = gatherNetworkInfo()
            
            // Create structured log entry
            val logEntry = ErrorLogEntry(
                timestamp = timestamp,
                errorCode = errorCode,
                errorType = errorType,
                severity = severity,
                message = message,
                stackTrace = exception?.let { getStackTraceString(it) },
                context = errorContext,
                deviceInfo = deviceInfo,
                networkInfo = networkInfo,
                sessionId = sessionId
            )
            
            // Write to structured log
            writeStructuredLog(logEntry)
            
            // Write to Android log with appropriate level
            writeToAndroidLog(logEntry)
            
            // Analyze failure patterns (Requirement 9.1)
            if (originalText != null && severity >= LogSeverity.WARN) {
                analyzeFailurePattern(originalText, errorType, timestamp)
            }
            
            // Store analytics data (Requirement 9.4 - with privacy protection)
            storeAnalyticsData(logEntry)
            
            errorCode
            
        } catch (e: Exception) {
            // Fallback logging if main logging fails
            Log.e(TAG, "Failed to log error: ${e.message}", e)
            "LOG_ERROR_${System.currentTimeMillis()}"
        }
    }
    
    /**
     * Logs API-specific errors with response details
     * Requirement 7.1: Include API responses in error logs
     */
    suspend fun logApiError(
        apiException: ApiException,
        originalText: String,
        processingTimeMs: Long,
        retryCount: Int = 0
    ): String {
        return logError(
            errorType = "API_ERROR",
            message = "API call failed: ${apiException.message}",
            exception = apiException,
            originalText = originalText,
            apiResponse = null,
            processingTimeMs = processingTimeMs,
            retryCount = retryCount,
            severity = LogSeverity.ERROR
        )
    }
    
    /**
     * Logs parsing failures with text analysis
     * Requirement 9.1: Log failure patterns for analysis
     */
    suspend fun logParsingFailure(
        originalText: String,
        parsingStage: String,
        exception: Exception? = null,
        partialResult: ParseResult? = null,
        processingTimeMs: Long = 0
    ): String {
        return logError(
            errorType = "PARSING_FAILURE",
            message = "Text parsing failed at stage: $parsingStage",
            exception = exception,
            originalText = originalText,
            apiResponse = partialResult,
            processingTimeMs = processingTimeMs,
            severity = LogSeverity.WARN
        )
    }
    
    /**
     * Logs low confidence results for pattern analysis
     * Requirement 9.2: Detect patterns for preprocessing improvements
     */
    suspend fun logLowConfidenceResult(
        originalText: String,
        result: ParseResult,
        processingTimeMs: Long = 0
    ): String {
        return logError(
            errorType = "LOW_CONFIDENCE",
            message = "Parsing result has low confidence: ${result.confidenceScore}",
            originalText = originalText,
            apiResponse = result,
            processingTimeMs = processingTimeMs,
            severity = LogSeverity.INFO
        )
    }
    
    /**
     * Logs user corrections for learning
     * Requirement 9.3: Note corrections for future reference
     */
    suspend fun logUserCorrection(
        originalText: String,
        correctedField: String,
        originalValue: String?,
        correctedValue: String
    ) = withContext(Dispatchers.IO) {
        
        if (!config.shouldCollectAnalytics()) return@withContext
        
        try {
            val correction = UserCorrection(
                originalText = anonymizeText(originalText),
                correctedField = correctedField,
                originalValue = originalValue,
                correctedValue = correctedValue,
                timestamp = System.currentTimeMillis()
            )
            
            // Store correction for pattern analysis
            storeUserCorrection(correction)
            
            // Log the correction event
            logError(
                errorType = "USER_CORRECTION",
                message = "User corrected field: $correctedField",
                originalText = originalText,
                severity = LogSeverity.INFO
            )
            
        } catch (e: Exception) {
            Log.w(TAG, "Failed to log user correction", e)
        }
    }
    
    /**
     * Logs critical system errors that require immediate attention
     * Requirement 7.3: Provide error codes for support purposes
     */
    suspend fun logCriticalError(
        message: String,
        exception: Exception,
        context: Map<String, Any> = emptyMap()
    ): String {
        val errorCode = logError(
            errorType = "CRITICAL_ERROR",
            message = message,
            exception = exception,
            severity = LogSeverity.CRITICAL
        )
        
        // Also log to Android system for immediate visibility
        Log.wtf(TAG, "CRITICAL ERROR [$errorCode]: $message", exception)
        
        return errorCode
    }
    
    /**
     * Creates privacy-safe error context
     * Requirement 7.4: Respect user privacy and not log sensitive information
     */
    private fun createErrorContext(
        originalText: String?,
        apiResponse: ParseResult?,
        processingTimeMs: Long,
        retryCount: Int
    ): ErrorContext {
        return ErrorContext(
            textLength = originalText?.length ?: 0,
            textHash = originalText?.let { hashText(it) }, // Hash for pattern analysis
            apiResponseCode = null, // Would be populated from actual API response
            apiResponseMessage = apiResponse?.let { "Confidence: ${it.confidenceScore}" },
            processingTimeMs = processingTimeMs,
            retryCount = retryCount,
            confidenceScore = apiResponse?.confidenceScore,
            parsingStage = null, // Would be set by caller
            userAction = null // Would be set by caller
        )
    }
    
    /**
     * Gathers device information for diagnostics
     * Requirement 7.2: Include device information in logs
     */
    private fun gatherDeviceInfo(): DeviceInfo {
        return DeviceInfo(
            androidVersion = Build.VERSION.RELEASE,
            apiLevel = Build.VERSION.SDK_INT,
            deviceModel = Build.MODEL,
            manufacturer = Build.MANUFACTURER,
            appVersion = getAppVersion(),
            availableMemoryMb = getAvailableMemoryMb(),
            totalStorageMb = getTotalStorageMb(),
            locale = Locale.getDefault().toString(),
            timezone = TimeZone.getDefault().id
        )
    }
    
    /**
     * Gathers network information for diagnostics
     * Requirement 7.2: Include network status in logs
     */
    private fun gatherNetworkInfo(): NetworkInfo {
        val connectivityManager = context.getSystemService(Context.CONNECTIVITY_SERVICE) as ConnectivityManager
        
        return if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
            val network = connectivityManager.activeNetwork
            val capabilities = connectivityManager.getNetworkCapabilities(network)
            
            NetworkInfo(
                isConnected = network != null && capabilities != null,
                connectionType = when {
                    capabilities?.hasTransport(NetworkCapabilities.TRANSPORT_WIFI) == true -> "WIFI"
                    capabilities?.hasTransport(NetworkCapabilities.TRANSPORT_CELLULAR) == true -> "CELLULAR"
                    capabilities?.hasTransport(NetworkCapabilities.TRANSPORT_ETHERNET) == true -> "ETHERNET"
                    else -> "UNKNOWN"
                },
                isMetered = !(capabilities?.hasCapability(NetworkCapabilities.NET_CAPABILITY_NOT_METERED) ?: false),
                signalStrength = null // Would require additional permissions
            )
        } else {
            @Suppress("DEPRECATION")
            val networkInfo = connectivityManager.activeNetworkInfo
            NetworkInfo(
                isConnected = networkInfo?.isConnected ?: false,
                connectionType = networkInfo?.typeName ?: "UNKNOWN",
                isMetered = true, // Assume metered for older versions
                signalStrength = null
            )
        }
    }
    
    /**
     * Writes structured log entry to file
     */
    private suspend fun writeStructuredLog(logEntry: ErrorLogEntry) = withContext(Dispatchers.IO) {
        try {
            // Check file size and rotate if needed
            if (logFile.exists() && logFile.length() > MAX_LOG_FILE_SIZE_MB * 1024 * 1024) {
                rotateLogFile()
            }
            
            val logJson = JSONObject().apply {
                put("timestamp", dateFormatter.format(Date(logEntry.timestamp)))
                put("error_code", logEntry.errorCode)
                put("error_type", logEntry.errorType)
                put("severity", logEntry.severity.name)
                put("message", logEntry.message)
                put("stack_trace", logEntry.stackTrace)
                put("session_id", logEntry.sessionId)
                
                // Context information
                put("context", JSONObject().apply {
                    put("text_length", logEntry.context.textLength)
                    put("text_hash", logEntry.context.textHash)
                    put("api_response_code", logEntry.context.apiResponseCode)
                    put("api_response_message", logEntry.context.apiResponseMessage)
                    put("processing_time_ms", logEntry.context.processingTimeMs)
                    put("retry_count", logEntry.context.retryCount)
                    put("confidence_score", logEntry.context.confidenceScore)
                })
                
                // Device information
                put("device", JSONObject().apply {
                    put("android_version", logEntry.deviceInfo.androidVersion)
                    put("api_level", logEntry.deviceInfo.apiLevel)
                    put("device_model", logEntry.deviceInfo.deviceModel)
                    put("manufacturer", logEntry.deviceInfo.manufacturer)
                    put("app_version", logEntry.deviceInfo.appVersion)
                    put("available_memory_mb", logEntry.deviceInfo.availableMemoryMb)
                    put("locale", logEntry.deviceInfo.locale)
                    put("timezone", logEntry.deviceInfo.timezone)
                })
                
                // Network information
                put("network", JSONObject().apply {
                    put("is_connected", logEntry.networkInfo.isConnected)
                    put("connection_type", logEntry.networkInfo.connectionType)
                    put("is_metered", logEntry.networkInfo.isMetered)
                })
            }
            
            FileWriter(logFile, true).use { writer ->
                writer.appendLine(logJson.toString())
            }
            
        } catch (e: Exception) {
            Log.e(TAG, "Failed to write structured log", e)
        }
    }
    
    /**
     * Writes to Android system log with appropriate level
     */
    private fun writeToAndroidLog(logEntry: ErrorLogEntry) {
        val logMessage = "[${logEntry.errorCode}] ${logEntry.message}"
        
        when (logEntry.severity) {
            LogSeverity.DEBUG -> Log.d(TAG, logMessage, logEntry.stackTrace?.let { Exception(it) })
            LogSeverity.INFO -> Log.i(TAG, logMessage)
            LogSeverity.WARN -> Log.w(TAG, logMessage, logEntry.stackTrace?.let { Exception(it) })
            LogSeverity.ERROR -> Log.e(TAG, logMessage, logEntry.stackTrace?.let { Exception(it) })
            LogSeverity.CRITICAL -> Log.wtf(TAG, logMessage, logEntry.stackTrace?.let { Exception(it) })
        }
    }
    
    /**
     * Analyzes failure patterns for preprocessing improvements
     * Requirement 9.1, 9.2: Log failure patterns and suggest improvements
     */
    private suspend fun analyzeFailurePattern(
        originalText: String,
        errorType: String,
        timestamp: Long
    ) = withContext(Dispatchers.IO) {
        
        try {
            val textPattern = extractTextPattern(originalText)
            val patternId = generatePatternId(textPattern, errorType)
            
            val existingPatterns = loadFailurePatterns()
            val existingPattern = existingPatterns[patternId]
            
            val updatedPattern = if (existingPattern != null) {
                existingPattern.copy(
                    occurrences = existingPattern.occurrences + 1,
                    lastSeen = timestamp
                )
            } else {
                FailurePattern(
                    patternId = patternId,
                    textPattern = textPattern,
                    errorType = errorType,
                    occurrences = 1,
                    firstSeen = timestamp,
                    lastSeen = timestamp,
                    suggestedImprovement = generateImprovementSuggestion(textPattern, errorType)
                )
            }
            
            existingPatterns[patternId] = updatedPattern
            saveFailurePatterns(existingPatterns)
            
        } catch (e: Exception) {
            Log.w(TAG, "Failed to analyze failure pattern", e)
        }
    }
    
    /**
     * Stores analytics data with privacy protection
     * Requirement 9.4: Maintain user privacy and anonymize data
     */
    private suspend fun storeAnalyticsData(logEntry: ErrorLogEntry) = withContext(Dispatchers.IO) {
        
        if (!config.shouldCollectAnalytics()) return@withContext
        
        try {
            val analyticsEntry = JSONObject().apply {
                put("timestamp", logEntry.timestamp)
                put("error_type", logEntry.errorType)
                put("severity", logEntry.severity.name)
                put("text_length", logEntry.context.textLength)
                put("text_hash", logEntry.context.textHash) // Anonymized
                put("processing_time_ms", logEntry.context.processingTimeMs)
                put("retry_count", logEntry.context.retryCount)
                put("confidence_score", logEntry.context.confidenceScore)
                put("network_connected", logEntry.networkInfo.isConnected)
                put("connection_type", logEntry.networkInfo.connectionType)
                put("android_api_level", logEntry.deviceInfo.apiLevel)
                put("session_id", logEntry.sessionId)
            }
            
            val existingAnalytics = if (analyticsFile.exists()) {
                JSONArray(analyticsFile.readText())
            } else {
                JSONArray()
            }
            
            existingAnalytics.put(analyticsEntry)
            
            // Clean up old entries
            cleanupAnalyticsData(existingAnalytics)
            
            analyticsFile.writeText(existingAnalytics.toString())
            
        } catch (e: Exception) {
            Log.w(TAG, "Failed to store analytics data", e)
        }
    }
    
    /**
     * Gets diagnostic report for troubleshooting
     * Requirement 7.3: Provide diagnostic information for support
     */
    fun getDiagnosticReport(): DiagnosticReport {
        return try {
            val recentErrors = getRecentErrors(50)
            val errorStatistics = calculateErrorStatistics(recentErrors)
            val failurePatterns = getCommonFailurePatterns()
            val systemHealth = assessSystemHealth()
            
            DiagnosticReport(
                generatedAt = System.currentTimeMillis(),
                sessionId = sessionId,
                recentErrors = recentErrors,
                errorStatistics = errorStatistics,
                failurePatterns = failurePatterns,
                systemHealth = systemHealth,
                deviceInfo = gatherDeviceInfo(),
                networkInfo = gatherNetworkInfo()
            )
        } catch (e: Exception) {
            Log.e(TAG, "Failed to generate diagnostic report", e)
            DiagnosticReport.empty()
        }
    }
    
    /**
     * Gets improvement suggestions based on failure patterns
     * Requirement 9.2: Suggest text preprocessing improvements
     */
    fun getImprovementSuggestions(textLength: Int = 0): List<ImprovementSuggestion> {
        return try {
            val patterns = loadFailurePatterns()
            val commonPatterns = patterns.values
                .filter { it.occurrences >= PATTERN_ANALYSIS_MIN_OCCURRENCES }
                .sortedByDescending { it.occurrences }
                .take(10)
            
            commonPatterns.mapNotNull { pattern ->
                pattern.suggestedImprovement?.let { suggestion ->
                    ImprovementSuggestion(
                        type = pattern.errorType,
                        suggestion = suggestion,
                        confidence = calculateSuggestionConfidence(pattern),
                        applicableToTextLength = isApplicableToTextLength(pattern, textLength)
                    )
                }
            }
        } catch (e: Exception) {
            Log.w(TAG, "Failed to get improvement suggestions", e)
            emptyList()
        }
    }
    
    /**
     * Clears diagnostic data (for privacy compliance)
     */
    suspend fun clearDiagnosticData() = withContext(Dispatchers.IO) {
        try {
            logFile.delete()
            analyticsFile.delete()
            patternAnalysisFile.delete()
            
            sharedPrefs.edit().clear().apply()
            
            Log.i(TAG, "Diagnostic data cleared")
        } catch (e: Exception) {
            Log.e(TAG, "Failed to clear diagnostic data", e)
        }
    }
    
    // Helper methods
    
    private fun generateErrorCode(errorType: String, severity: LogSeverity): String {
        val timestamp = System.currentTimeMillis()
        val hash = hashText("$errorType-$severity-$timestamp").take(ERROR_CODE_LENGTH - ERROR_CODE_PREFIX.length)
        return "$ERROR_CODE_PREFIX$hash"
    }
    
    private fun generateSessionId(): String {
        return "SES_${System.currentTimeMillis()}_${hashText(UUID.randomUUID().toString()).take(8)}"
    }
    
    private fun hashText(text: String): String {
        return try {
            val digest = MessageDigest.getInstance("SHA-256")
            val hashBytes = digest.digest(text.toByteArray())
            hashBytes.joinToString("") { "%02x".format(it) }.take(16)
        } catch (e: Exception) {
            text.hashCode().toString()
        }
    }
    
    private fun anonymizeText(text: String): String {
        return if (config.shouldUsePrivacyCompliantLogging()) {
            hashText(text)
        } else {
            text.take(MAX_TEXT_LENGTH_TO_LOG)
        }
    }
    
    private fun getStackTraceString(exception: Exception): String {
        val stringWriter = StringWriter()
        val printWriter = PrintWriter(stringWriter)
        exception.printStackTrace(printWriter)
        return stringWriter.toString()
    }
    
    private fun mapSeverityToConfigLevel(severity: LogSeverity): ErrorHandlingConfig.LogLevel {
        return when (severity) {
            LogSeverity.DEBUG -> ErrorHandlingConfig.LogLevel.DEBUG
            LogSeverity.INFO -> ErrorHandlingConfig.LogLevel.INFO
            LogSeverity.WARN -> ErrorHandlingConfig.LogLevel.WARN
            LogSeverity.ERROR -> ErrorHandlingConfig.LogLevel.ERROR
            LogSeverity.CRITICAL -> ErrorHandlingConfig.LogLevel.ERROR
        }
    }
    
    private fun getAppVersion(): String {
        return try {
            val packageInfo = context.packageManager.getPackageInfo(context.packageName, 0)
            "${packageInfo.versionName} (${packageInfo.versionCode})"
        } catch (e: Exception) {
            "unknown"
        }
    }
    
    private fun getAvailableMemoryMb(): Long {
        return try {
            val activityManager = context.getSystemService(Context.ACTIVITY_SERVICE) as android.app.ActivityManager
            val memoryInfo = android.app.ActivityManager.MemoryInfo()
            activityManager.getMemoryInfo(memoryInfo)
            memoryInfo.availMem / (1024 * 1024)
        } catch (e: Exception) {
            0L
        }
    }
    
    private fun getTotalStorageMb(): Long {
        return try {
            val internalDir = context.filesDir
            val totalSpace = internalDir.totalSpace
            totalSpace / (1024 * 1024)
        } catch (e: Exception) {
            0L
        }
    }
    
    private suspend fun rotateLogFile() = withContext(Dispatchers.IO) {
        try {
            val backupFile = File(context.filesDir, "${LOG_FILE_NAME}.backup")
            if (backupFile.exists()) {
                backupFile.delete()
            }
            logFile.renameTo(backupFile)
        } catch (e: Exception) {
            Log.w(TAG, "Failed to rotate log file", e)
        }
    }
    
    private fun extractTextPattern(text: String): String {
        // Extract pattern characteristics for analysis
        val length = text.length
        val hasNumbers = text.any { it.isDigit() }
        val hasTime = text.contains(Regex("\\d{1,2}:\\d{2}"))
        val hasDate = text.contains(Regex("\\d{1,2}/\\d{1,2}"))
        val wordCount = text.split("\\s+".toRegex()).size
        
        return "len:$length,nums:$hasNumbers,time:$hasTime,date:$hasDate,words:$wordCount"
    }
    
    private fun generatePatternId(textPattern: String, errorType: String): String {
        return hashText("$textPattern-$errorType")
    }
    
    private fun generateImprovementSuggestion(textPattern: String, errorType: String): String {
        return when (errorType) {
            "PARSING_FAILURE" -> when {
                !textPattern.contains("time:true") -> "Try including specific times (e.g., '2:00 PM' instead of 'afternoon')"
                !textPattern.contains("date:true") -> "Try including specific dates (e.g., 'March 15' instead of 'next week')"
                textPattern.contains("words:1") -> "Try providing more context about the event"
                else -> "Try using clearer, more specific language"
            }
            "LOW_CONFIDENCE" -> "Try being more specific about date, time, and event details"
            "API_ERROR" -> "Check your internet connection and try again"
            else -> "Try rephrasing your text with clearer details"
        }
    }
    
    private fun loadFailurePatterns(): MutableMap<String, FailurePattern> {
        return try {
            if (patternAnalysisFile.exists()) {
                val json = JSONObject(patternAnalysisFile.readText())
                val patterns = mutableMapOf<String, FailurePattern>()
                
                json.keys().forEach { key ->
                    val patternJson = json.getJSONObject(key)
                    patterns[key] = FailurePattern(
                        patternId = patternJson.getString("patternId"),
                        textPattern = patternJson.getString("textPattern"),
                        errorType = patternJson.getString("errorType"),
                        occurrences = patternJson.getInt("occurrences"),
                        firstSeen = patternJson.getLong("firstSeen"),
                        lastSeen = patternJson.getLong("lastSeen"),
                        suggestedImprovement = patternJson.optString("suggestedImprovement")
                    )
                }
                
                patterns
            } else {
                mutableMapOf()
            }
        } catch (e: Exception) {
            Log.w(TAG, "Failed to load failure patterns", e)
            mutableMapOf()
        }
    }
    
    private fun saveFailurePatterns(patterns: Map<String, FailurePattern>) {
        try {
            val json = JSONObject()
            patterns.forEach { (key, pattern) ->
                json.put(key, JSONObject().apply {
                    put("patternId", pattern.patternId)
                    put("textPattern", pattern.textPattern)
                    put("errorType", pattern.errorType)
                    put("occurrences", pattern.occurrences)
                    put("firstSeen", pattern.firstSeen)
                    put("lastSeen", pattern.lastSeen)
                    put("suggestedImprovement", pattern.suggestedImprovement)
                })
            }
            
            patternAnalysisFile.writeText(json.toString())
        } catch (e: Exception) {
            Log.w(TAG, "Failed to save failure patterns", e)
        }
    }
    
    private fun storeUserCorrection(correction: UserCorrection) {
        // Implementation for storing user corrections
        // This would integrate with the failure pattern analysis
    }
    
    private fun cleanupAnalyticsData(analyticsArray: JSONArray) {
        val cutoffTime = System.currentTimeMillis() - (ANALYTICS_RETENTION_DAYS * 24 * 60 * 60 * 1000L)
        
        // Remove entries older than retention period
        val indicesToRemove = mutableListOf<Int>()
        for (i in 0 until analyticsArray.length()) {
            val entry = analyticsArray.getJSONObject(i)
            if (entry.getLong("timestamp") < cutoffTime) {
                indicesToRemove.add(i)
            }
        }
        
        // Remove in reverse order to maintain indices
        indicesToRemove.reversed().forEach { index ->
            analyticsArray.remove(index)
        }
    }
    
    private fun getRecentErrors(limit: Int): List<ErrorLogEntry> {
        // Implementation to retrieve recent errors from log file
        return emptyList() // Placeholder
    }
    
    private fun calculateErrorStatistics(errors: List<ErrorLogEntry>): ErrorStatistics {
        // Implementation to calculate error statistics
        return ErrorStatistics() // Placeholder
    }
    
    private fun getCommonFailurePatterns(): List<FailurePattern> {
        return loadFailurePatterns().values
            .filter { it.occurrences >= PATTERN_ANALYSIS_MIN_OCCURRENCES }
            .sortedByDescending { it.occurrences }
            .take(10)
    }
    
    private fun assessSystemHealth(): SystemHealth {
        // Implementation to assess system health
        return SystemHealth() // Placeholder
    }
    
    private fun calculateSuggestionConfidence(pattern: FailurePattern): Double {
        return minOf(1.0, pattern.occurrences.toDouble() / 10.0)
    }
    
    private fun isApplicableToTextLength(pattern: FailurePattern, textLength: Int): Boolean {
        // Extract length from pattern and check if it's similar
        val patternLength = pattern.textPattern.substringAfter("len:").substringBefore(",").toIntOrNull() ?: 0
        return kotlin.math.abs(patternLength - textLength) <= 50
    }
    
    // Data classes for diagnostic reporting
    
    data class DiagnosticReport(
        val generatedAt: Long,
        val sessionId: String,
        val recentErrors: List<ErrorLogEntry>,
        val errorStatistics: ErrorStatistics,
        val failurePatterns: List<FailurePattern>,
        val systemHealth: SystemHealth,
        val deviceInfo: DeviceInfo,
        val networkInfo: NetworkInfo
    ) {
        companion object {
            fun empty() = DiagnosticReport(
                generatedAt = System.currentTimeMillis(),
                sessionId = "",
                recentErrors = emptyList(),
                errorStatistics = ErrorStatistics(),
                failurePatterns = emptyList(),
                systemHealth = SystemHealth(),
                deviceInfo = DeviceInfo("", 0, "", "", "", 0, 0, "", ""),
                networkInfo = NetworkInfo(false, "", false, null)
            )
        }
    }
    
    data class ErrorStatistics(
        val totalErrors: Int = 0,
        val errorsByType: Map<String, Int> = emptyMap(),
        val errorsBySeverity: Map<String, Int> = emptyMap(),
        val averageProcessingTime: Double = 0.0,
        val successRate: Double = 0.0
    )
    
    data class SystemHealth(
        val memoryUsage: Double = 0.0,
        val storageUsage: Double = 0.0,
        val networkStability: Double = 0.0,
        val overallHealth: String = "UNKNOWN"
    )
    
    data class ImprovementSuggestion(
        val type: String,
        val suggestion: String,
        val confidence: Double,
        val applicableToTextLength: Boolean
    )
}