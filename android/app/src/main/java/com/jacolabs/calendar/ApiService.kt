package com.jacolabs.calendar

import android.content.Context
import android.net.ConnectivityManager
import android.net.NetworkCapabilities
import android.os.Build
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.*
import okhttp3.HttpUrl.Companion.toHttpUrl
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONObject
import java.io.IOException
import java.text.SimpleDateFormat
import java.util.*
import java.util.concurrent.TimeUnit
import kotlin.math.min
import kotlin.math.pow

/**
 * Enhanced service for calling the text-to-calendar API with robust error handling and retry logic.
 */
class ApiService(private val context: Context? = null) {
    
    companion object {
        private const val API_BASE_URL = "https://calendar-api-wrxz.onrender.com"
        private const val PARSE_ENDPOINT = "$API_BASE_URL/parse"
        private const val DEFAULT_TIMEOUT_SECONDS = 15L
        private const val DEFAULT_MAX_RETRIES = 3
        private const val DEFAULT_BASE_DELAY_MS = 1000L
        private const val MAX_DELAY_MS = 30000L
        private const val DNS_TEST_HOST = "8.8.8.8"
        private const val DNS_TEST_TIMEOUT_MS = 5000
    }

    /**
     * Configuration for error handling behavior
     */
    data class ErrorHandlingConfig(
        val maxRetryAttempts: Int = DEFAULT_MAX_RETRIES,
        val baseRetryDelayMs: Long = DEFAULT_BASE_DELAY_MS,
        val timeoutSeconds: Long = DEFAULT_TIMEOUT_SECONDS,
        val enableNetworkCheck: Boolean = true,
        val enableExponentialBackoff: Boolean = true,
        val maxDelayMs: Long = MAX_DELAY_MS
    )

    /**
     * Enumeration of different error types for categorization
     */
    enum class ErrorType {
        NETWORK_CONNECTIVITY,
        REQUEST_TIMEOUT,
        SERVER_ERROR,
        CLIENT_ERROR,
        PARSING_ERROR,
        VALIDATION_ERROR,
        RATE_LIMIT,
        UNKNOWN_ERROR
    }

    /**
     * Structured error information with context
     */
    data class ApiError(
        val type: ErrorType,
        val code: String,
        val message: String,
        val userMessage: String,
        val suggestion: String? = null,
        val retryable: Boolean = false,
        val retryAfterSeconds: Int? = null
    )

    private val config = ErrorHandlingConfig()
    
    private val client = OkHttpClient.Builder()
        .connectTimeout(config.timeoutSeconds, TimeUnit.SECONDS)
        .readTimeout(config.timeoutSeconds, TimeUnit.SECONDS)
        .writeTimeout(config.timeoutSeconds, TimeUnit.SECONDS)
        .build()

    /**
     * Parse text using the enhanced API with robust error handling and retry logic.
     */
    suspend fun parseText(
        text: String,
        timezone: String,
        locale: String,
        now: Date,
        mode: String? = null,
        fields: List<String>? = null
    ): ParseResult = withContext(Dispatchers.IO) {
        
        // Check network connectivity first if enabled
        if (config.enableNetworkCheck && !isNetworkAvailable()) {
            throw ApiException(
                ApiError(
                    type = ErrorType.NETWORK_CONNECTIVITY,
                    code = "NO_NETWORK",
                    message = "No internet connection available",
                    userMessage = "No internet connection. Please check your network settings and try again.",
                    retryable = true
                )
            )
        }
        
        // Preprocess text to handle common formatting issues
        val preprocessedText = preprocessText(text)
        
        // Validate input
        validateInput(preprocessedText)
        
        // Build request
        val request = buildApiRequest(preprocessedText, timezone, locale, now, mode, fields)
        
        // Execute request with retry logic
        return@withContext executeWithRetry(request, preprocessedText)
    }

    /**
     * Executes API request with exponential backoff retry logic
     */
    private suspend fun executeWithRetry(request: Request, originalText: String): ParseResult {
        var lastError: ApiError? = null
        
        for (attempt in 0..config.maxRetryAttempts) {
            try {
                client.newCall(request).execute().use { response ->
                    val responseBody = response.body?.string() ?: ""
                    
                    when (response.code) {
                        200 -> {
                            val result = parseApiResponse(responseBody)
                            logSuccessfulResponse(result)
                            validateParseResult(result, originalText)
                            return result
                        }
                        in 400..499 -> {
                            val error = handleClientError(response.code, responseBody)
                            if (!error.retryable || attempt >= config.maxRetryAttempts) {
                                throw ApiException(error)
                            }
                            lastError = error
                        }
                        in 500..599 -> {
                            val error = handleServerError(response.code, responseBody)
                            if (attempt >= config.maxRetryAttempts) {
                                throw ApiException(error)
                            }
                            lastError = error
                        }
                        else -> {
                            val error = ApiError(
                                type = ErrorType.UNKNOWN_ERROR,
                                code = "HTTP_${response.code}",
                                message = "Unexpected HTTP status code: ${response.code}",
                                userMessage = "Request failed with code ${response.code}. Please try again.",
                                retryable = attempt < config.maxRetryAttempts
                            )
                            if (!error.retryable) {
                                throw ApiException(error)
                            }
                            lastError = error
                        }
                    }
                }
                
            } catch (e: ApiException) {
                throw e // Re-throw API exceptions without modification
            } catch (e: Exception) {
                val error = categorizeException(e)
                if (!error.retryable || attempt >= config.maxRetryAttempts) {
                    throw ApiException(error)
                }
                lastError = error
            }
            
            // Apply exponential backoff delay before retry
            if (attempt < config.maxRetryAttempts) {
                val delay = calculateRetryDelay(attempt, lastError?.retryAfterSeconds)
                kotlinx.coroutines.delay(delay)
            }
        }
        
        // If we get here, all retries failed
        throw ApiException(lastError ?: ApiError(
            type = ErrorType.UNKNOWN_ERROR,
            code = "MAX_RETRIES_EXCEEDED",
            message = "Maximum retry attempts exceeded",
            userMessage = "Failed to complete request after multiple attempts. Please try again later.",
            retryable = false
        ))
    }

    /**
     * Calculates retry delay using exponential backoff
     */
    private fun calculateRetryDelay(attempt: Int, retryAfterSeconds: Int?): Long {
        return if (config.enableExponentialBackoff) {
            // Use server-provided retry-after if available, otherwise exponential backoff
            val baseDelay = retryAfterSeconds?.let { it * 1000L } 
                ?: (config.baseRetryDelayMs * 2.0.pow(attempt).toLong())
            
            min(baseDelay, config.maxDelayMs)
        } else {
            config.baseRetryDelayMs
        }
    }

    /**
     * Builds the API request with proper headers and body
     */
    private fun buildApiRequest(
        text: String,
        timezone: String,
        locale: String,
        now: Date,
        mode: String?,
        fields: List<String>?
    ): Request {
        // Build URL with query parameters for enhanced features
        val urlBuilder = PARSE_ENDPOINT.toHttpUrl().newBuilder()
        
        mode?.let { urlBuilder.addQueryParameter("mode", it) }
        fields?.let { fieldList ->
            if (fieldList.isNotEmpty()) {
                urlBuilder.addQueryParameter("fields", fieldList.joinToString(","))
            }
        }
        
        // Create request body
        val requestBody = JSONObject().apply {
            put("text", text)
            put("timezone", timezone)
            put("locale", locale)
            put("now", formatDateTimeForApi(now))
            put("use_llm_enhancement", true)
        }
        
        val mediaType = "application/json; charset=utf-8".toMediaType()
        val body = requestBody.toString().toRequestBody(mediaType)
        
        return Request.Builder()
            .url(urlBuilder.build())
            .post(body)
            .addHeader("Content-Type", "application/json")
            .addHeader("Accept", "application/json")
            .addHeader("User-Agent", "CalendarEventApp-Android/2.0")
            .build()
    }

    /**
     * Validates input parameters
     */
    private fun validateInput(text: String) {
        if (text.isBlank()) {
            throw ApiException(
                ApiError(
                    type = ErrorType.VALIDATION_ERROR,
                    code = "EMPTY_TEXT",
                    message = "Input text is empty or blank",
                    userMessage = "Please provide text containing event information.",
                    retryable = false
                )
            )
        }
        
        if (text.length > 10000) {
            throw ApiException(
                ApiError(
                    type = ErrorType.VALIDATION_ERROR,
                    code = "TEXT_TOO_LONG",
                    message = "Input text exceeds maximum length of 10,000 characters",
                    userMessage = "Text is too long. Please limit to 10,000 characters.",
                    retryable = false
                )
            )
        }
    }

    /**
     * Handles client errors (4xx status codes)
     */
    private fun handleClientError(statusCode: Int, responseBody: String): ApiError {
        val errorDetails = parseErrorResponse(responseBody)
        
        return when (statusCode) {
            400 -> ApiError(
                type = ErrorType.CLIENT_ERROR,
                code = errorDetails.code,
                message = errorDetails.message,
                userMessage = errorDetails.userMessage,
                suggestion = errorDetails.suggestion,
                retryable = false
            )
            422 -> ApiError(
                type = ErrorType.PARSING_ERROR,
                code = errorDetails.code,
                message = errorDetails.message,
                userMessage = errorDetails.userMessage ?: "The text does not contain valid event information. Please try rephrasing with clearer date, time, and event details.",
                suggestion = errorDetails.suggestion,
                retryable = false
            )
            429 -> {
                val retryAfter = extractRetryAfterFromResponse(responseBody)
                ApiError(
                    type = ErrorType.RATE_LIMIT,
                    code = errorDetails.code,
                    message = errorDetails.message,
                    userMessage = "Too many requests. Please wait ${retryAfter ?: 60} seconds before trying again.",
                    retryable = true,
                    retryAfterSeconds = retryAfter
                )
            }
            else -> ApiError(
                type = ErrorType.CLIENT_ERROR,
                code = "HTTP_$statusCode",
                message = "Client error: $statusCode",
                userMessage = errorDetails.userMessage ?: "Request failed with code $statusCode. Please try again.",
                retryable = false
            )
        }
    }

    /**
     * Handles server errors (5xx status codes)
     */
    private fun handleServerError(statusCode: Int, responseBody: String): ApiError {
        val errorDetails = parseErrorResponse(responseBody)
        
        return ApiError(
            type = ErrorType.SERVER_ERROR,
            code = "HTTP_$statusCode",
            message = "Server error: $statusCode",
            userMessage = when (statusCode) {
                500 -> "Server is experiencing issues. Please try again in a few minutes."
                502 -> "Server is temporarily unavailable. Please try again shortly."
                503 -> "Service is temporarily unavailable. Please try again later."
                504 -> "Request timed out on the server. Please try again."
                else -> "Server error occurred. Please try again later."
            },
            retryable = true
        )
    }

    /**
     * Categorizes exceptions into appropriate error types
     */
    private fun categorizeException(exception: Exception): ApiError {
        return when (exception) {
            is java.net.SocketTimeoutException -> ApiError(
                type = ErrorType.REQUEST_TIMEOUT,
                code = "SOCKET_TIMEOUT",
                message = "Request timed out",
                userMessage = "Request timed out. Please check your internet connection and try again.",
                retryable = true
            )
            is java.net.UnknownHostException -> ApiError(
                type = ErrorType.NETWORK_CONNECTIVITY,
                code = "UNKNOWN_HOST",
                message = "Unable to resolve server hostname",
                userMessage = "Unable to connect to the server. Please check your internet connection and try again.",
                retryable = true
            )
            is java.net.ConnectException -> ApiError(
                type = ErrorType.NETWORK_CONNECTIVITY,
                code = "CONNECTION_FAILED",
                message = "Failed to establish connection",
                userMessage = "Unable to connect to the server. Please check your internet connection and try again later.",
                retryable = true
            )
            is IOException -> {
                when {
                    exception.message?.contains("timeout", ignoreCase = true) == true -> ApiError(
                        type = ErrorType.REQUEST_TIMEOUT,
                        code = "IO_TIMEOUT",
                        message = "I/O operation timed out",
                        userMessage = "Request timed out. Please check your internet connection and try again.",
                        retryable = true
                    )
                    exception.message?.contains("network", ignoreCase = true) == true -> ApiError(
                        type = ErrorType.NETWORK_CONNECTIVITY,
                        code = "NETWORK_ERROR",
                        message = "Network I/O error",
                        userMessage = "Network error occurred. Please check your internet connection and try again.",
                        retryable = true
                    )
                    else -> ApiError(
                        type = ErrorType.NETWORK_CONNECTIVITY,
                        code = "IO_ERROR",
                        message = "I/O error: ${exception.message}",
                        userMessage = "Connection error: ${exception.message ?: "Unknown network error"}. Please try again.",
                        retryable = true
                    )
                }
            }
            else -> ApiError(
                type = ErrorType.UNKNOWN_ERROR,
                code = "UNEXPECTED_ERROR",
                message = "Unexpected error: ${exception.message}",
                userMessage = "An unexpected error occurred: ${exception.message ?: "Unknown error"}. Please try again.",
                retryable = false
            )
        }
    }

    /**
     * Logs successful response details for debugging
     */
    private fun logSuccessfulResponse(result: ParseResult) {
        result.fieldResults?.let { fieldResults ->
            println("Field confidence scores: $fieldResults")
        }
        
        result.parsingPath?.let { path ->
            println("Parsing method used: $path")
        }
        
        if (result.cacheHit == true) {
            println("Result served from cache")
        }
        
        result.warnings?.let { warnings ->
            if (warnings.isNotEmpty()) {
                println("Parsing warnings: $warnings")
            }
        }
    }
    
    /**
     * Enhanced network connectivity check using multiple methods
     */
    private fun isNetworkAvailable(): Boolean {
        // Method 1: Check system connectivity manager (requires context)
        context?.let { ctx ->
            val connectivityManager = ctx.getSystemService(Context.CONNECTIVITY_SERVICE) as? ConnectivityManager
            connectivityManager?.let { cm ->
                return if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
                    val network = cm.activeNetwork ?: return false
                    val capabilities = cm.getNetworkCapabilities(network) ?: return false
                    capabilities.hasCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET) &&
                    capabilities.hasCapability(NetworkCapabilities.NET_CAPABILITY_VALIDATED)
                } else {
                    @Suppress("DEPRECATION")
                    val networkInfo = cm.activeNetworkInfo
                    networkInfo?.isConnected == true
                }
            }
        }
        
        // Method 2: Fallback DNS resolution test
        return try {
            val address = java.net.InetAddress.getByName(DNS_TEST_HOST)
            !address.equals("")
        } catch (e: Exception) {
            false
        }
    }
    
    /**
     * Parse error response from API to extract structured error information.
     */
    private fun parseErrorResponse(responseBody: String): ErrorDetails {
        return try {
            val errorJson = JSONObject(responseBody)
            
            // Check for new enhanced error format
            if (errorJson.has("error")) {
                val errorObj = errorJson.getJSONObject("error")
                val code = errorObj.optString("code", "UNKNOWN_ERROR")
                val message = errorObj.optString("message", "An error occurred")
                val suggestion = errorObj.optString("suggestion")
                
                val userMessage = when (code) {
                    "VALIDATION_ERROR" -> "Invalid input: $message"
                    "PARSING_ERROR" -> message + if (suggestion != null) ". $suggestion" else ""
                    "TEXT_EMPTY" -> "Please provide text containing event information."
                    "TEXT_TOO_LONG" -> "Text is too long. Please limit to 10,000 characters."
                    "INVALID_TIMEZONE" -> "Invalid timezone. Please check your device settings."
                    "LLM_UNAVAILABLE" -> "Enhanced parsing is temporarily unavailable. Your request will be processed with basic parsing."
                    "RATE_LIMIT_ERROR" -> message + if (suggestion != null) ". $suggestion" else ""
                    "SERVICE_UNAVAILABLE" -> "Service is temporarily unavailable. Please try again later."
                    else -> message
                }
                
                ErrorDetails(code, message, userMessage, suggestion)
            } else {
                // Fallback to old format
                val detail = errorJson.optString("detail", "Unknown error occurred")
                ErrorDetails("UNKNOWN_ERROR", detail, detail, null)
            }
        } catch (e: Exception) {
            ErrorDetails("PARSE_ERROR", responseBody, "Server returned an error. Please try again.", null)
        }
    }

    /**
     * Extracts retry-after value from error response
     */
    private fun extractRetryAfterFromResponse(responseBody: String): Int? {
        return try {
            val errorJson = JSONObject(responseBody)
            if (errorJson.has("retry_after")) {
                errorJson.getInt("retry_after")
            } else if (errorJson.has("error")) {
                val errorObj = errorJson.getJSONObject("error")
                errorObj.optInt("retry_after", 60)
            } else {
                null
            }
        } catch (e: Exception) {
            null
        }
    }
    
    /**
     * Validate the parsed result and provide helpful feedback.
     */
    private fun validateParseResult(result: ParseResult, originalText: String) {
        // Check if we got meaningful results
        if (result.title.isNullOrBlank() && result.startDateTime.isNullOrBlank()) {
            throw ApiException("Could not extract event information from the text. Please try rephrasing with clearer date, time, and event details.")
        }
        
        // Warn about low confidence
        if (result.confidenceScore < 0.3) {
            throw ApiException("The text is unclear and may not contain valid event information. Please try rephrasing with specific date, time, and event details.")
        }
    }
    
    /**
     * Data class for structured error information.
     */
    private data class ErrorDetails(
        val code: String,
        val message: String,
        val userMessage: String,
        val suggestion: String?
    )

    private fun parseApiResponse(jsonResponse: String): ParseResult {
        val json = JSONObject(jsonResponse)
        
        // Parse field results if available
        val fieldResults = json.optJSONObject("field_results")?.let { fieldResultsJson ->
            mutableMapOf<String, FieldResult>().apply {
                fieldResultsJson.keys().forEach { key ->
                    val fieldJson = fieldResultsJson.getJSONObject(key)
                    this[key] = FieldResult(
                        value = fieldJson.opt("value"),
                        source = fieldJson.optString("source", "unknown"),
                        confidence = fieldJson.optDouble("confidence", 0.0),
                        span = fieldJson.optJSONArray("span")?.let { spanArray ->
                            Pair(spanArray.optInt(0, 0), spanArray.optInt(1, 0))
                        },
                        processingTimeMs = fieldJson.optInt("processing_time_ms", 0)
                    )
                }
            }
        }
        
        // Parse warnings array
        val warnings = json.optJSONArray("warnings")?.let { warningsArray ->
            mutableListOf<String>().apply {
                for (i in 0 until warningsArray.length()) {
                    add(warningsArray.getString(i))
                }
            }
        }
        
        return ParseResult(
            title = json.optString("title").takeIf { it.isNotEmpty() },
            startDateTime = json.optString("start_datetime").takeIf { it.isNotEmpty() },
            endDateTime = json.optString("end_datetime").takeIf { it.isNotEmpty() },
            location = json.optString("location").takeIf { it.isNotEmpty() },
            description = json.optString("description").takeIf { it.isNotEmpty() },
            confidenceScore = json.optDouble("confidence_score", 0.0),
            allDay = json.optBoolean("all_day", false),
            timezone = json.optString("timezone", "UTC"),
            // Enhanced fields
            fieldResults = fieldResults,
            parsingPath = json.optString("parsing_path").takeIf { it.isNotEmpty() },
            processingTimeMs = json.optInt("processing_time_ms", 0),
            cacheHit = json.optBoolean("cache_hit", false),
            warnings = warnings,
            needsConfirmation = json.optBoolean("needs_confirmation", false)
        )
    }

    /**
     * Preprocesses text to handle common formatting issues that the API might not recognize.
     */
    private fun preprocessText(text: String): String {
        var processed = text
        
        // Fix common time format issues
        processed = processed.replace(Regex("(\\d{1,2}:\\d{2})a\\.m"), "$1 AM")
        processed = processed.replace(Regex("(\\d{1,2}:\\d{2})p\\.m"), "$1 PM")
        processed = processed.replace(Regex("(\\d{1,2})a\\.m"), "$1:00 AM")
        processed = processed.replace(Regex("(\\d{1,2})p\\.m"), "$1:00 PM")
        
        // Fix common spacing issues
        processed = processed.replace(Regex("(\\d{1,2}:\\d{2})am"), "$1 AM")
        processed = processed.replace(Regex("(\\d{1,2}:\\d{2})pm"), "$1 PM")
        processed = processed.replace(Regex("(\\d{1,2})am"), "$1:00 AM")
        processed = processed.replace(Regex("(\\d{1,2})pm"), "$1:00 PM")
        
        // Improve common phrasing patterns for better title extraction
        processed = processed.replace(Regex("^We will (.+?) by (.+)"), "$1 at $2")
        processed = processed.replace(Regex("^I will (.+?) by (.+)"), "$1 at $2")
        processed = processed.replace(Regex("^We need to (.+?) by (.+)"), "$1 at $2")
        
        // Enhanced title extraction patterns
        processed = enhanceTitleExtraction(processed)
        
        return processed
    }
    
    /**
     * Enhances text to improve title extraction by the API.
     */
    private fun enhanceTitleExtraction(text: String): String {
        var enhanced = text
        
        // Pattern 1: "On [day] the [people] will attend [EVENT]" -> "[EVENT] on [day]"
        enhanced = enhanced.replace(
            Regex("^On (\\w+day) the .+? will attend (.+?)(?:\\s+at\\s+(.+?))?(?:\\.|$)", RegexOption.IGNORE_CASE),
            "$2 on $1"
        )
        
        // Pattern 2: "On [day] the [people] will [action] the [EVENT]" -> "[EVENT] on [day]"  
        enhanced = enhanced.replace(
            Regex("^On (\\w+day) the .+? will \\w+ the (.+?)(?:\\s+at\\s+(.+?))?(?:\\.|$)", RegexOption.IGNORE_CASE),
            "$2 on $1"
        )
        
        // Pattern 3: Extract event name from "attend [EVENT] at [LOCATION]"
        enhanced = enhanced.replace(
            Regex("attend (.+?) at (.+?)(?:\\.|$)", RegexOption.IGNORE_CASE),
            "$1 at $2"
        )
        
        // Pattern 4: Extract event name from "will attend [EVENT]"
        enhanced = enhanced.replace(
            Regex("will attend (.+?)(?:\\s+at\\s+(.+?))?(?:\\.|$)", RegexOption.IGNORE_CASE)
        ) { matchResult ->
            val event = matchResult.groupValues[1]
            val location = matchResult.groupValues[2]
            if (location.isNotEmpty()) "$event at $location" else event
        }
        
        // Pattern 5: Clean up common prefixes that don't belong in titles
        enhanced = enhanced.replace(Regex("^(On \\w+day )?the (students?|children|kids) will ", RegexOption.IGNORE_CASE), "")
        enhanced = enhanced.replace(Regex("^(We|I) will ", RegexOption.IGNORE_CASE), "")
        
        // Pattern 6: Capitalize first letter and clean up
        enhanced = enhanced.trim()
        if (enhanced.isNotEmpty()) {
            enhanced = enhanced.substring(0, 1).uppercase() + enhanced.substring(1)
        }
        
        return enhanced
    }

    private fun formatDateTimeForApi(date: Date): String {
        val format = SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss'Z'", Locale.US)
        format.timeZone = TimeZone.getTimeZone("UTC")
        return format.format(date)
    }
}

/**
 * Data class representing the enhanced API response with error handling metadata.
 */
data class ParseResult(
    val title: String?,
    val startDateTime: String?,
    val endDateTime: String?,
    val location: String?,
    val description: String?,
    val confidenceScore: Double,
    val allDay: Boolean,
    val timezone: String,
    // Enhanced fields
    val fieldResults: Map<String, FieldResult>? = null,
    val parsingPath: String? = null,
    val processingTimeMs: Int = 0,
    val cacheHit: Boolean? = null,
    val warnings: List<String>? = null,
    val needsConfirmation: Boolean = false,
    // Error handling fields
    val fallbackApplied: Boolean = false,
    val fallbackReason: String? = null,
    val originalText: String? = null,
    val errorRecoveryInfo: ErrorRecoveryInfo? = null
)

/**
 * Information about error recovery applied to the result
 */
data class ErrorRecoveryInfo(
    val recoveryMethod: String,
    val confidenceBeforeRecovery: Double,
    val dataSourcesUsed: List<String>,
    val userInterventionRequired: Boolean
)

/**
 * Data class representing per-field parsing results.
 */
data class FieldResult(
    val value: Any?,
    val source: String,
    val confidence: Double,
    val span: Pair<Int, Int>?,
    val processingTimeMs: Int
)

/**
 * Enhanced exception for API-related errors with structured error information.
 */
class ApiException : Exception {
    val apiError: ApiService.ApiError
    
    constructor(apiError: ApiService.ApiError) : super(apiError.userMessage) {
        this.apiError = apiError
    }
    
    constructor(message: String) : super(message) {
        this.apiError = ApiService.ApiError(
            type = ApiService.ErrorType.UNKNOWN_ERROR,
            code = "LEGACY_ERROR",
            message = message,
            userMessage = message,
            retryable = false
        )
    }
    
    /**
     * Convenience properties for backward compatibility
     */
    val errorType: ApiService.ErrorType get() = apiError.type
    val errorCode: String get() = apiError.code
    val userMessage: String get() = apiError.userMessage
    val isRetryable: Boolean get() = apiError.retryable
    val suggestion: String? get() = apiError.suggestion
    val retryAfterSeconds: Int? get() = apiError.retryAfterSeconds
}