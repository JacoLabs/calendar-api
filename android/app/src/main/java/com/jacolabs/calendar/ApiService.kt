package com.jacolabs.calendar

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

/**
 * Service for calling the text-to-calendar API.
 */
class ApiService {
    
    companion object {
        private const val API_BASE_URL = "https://calendar-api-wrxz.onrender.com"
        private const val PARSE_ENDPOINT = "$API_BASE_URL/parse"
        private const val TIMEOUT_SECONDS = 15L
    }

    private val client = OkHttpClient.Builder()
        .connectTimeout(TIMEOUT_SECONDS, TimeUnit.SECONDS)
        .readTimeout(TIMEOUT_SECONDS, TimeUnit.SECONDS)
        .writeTimeout(TIMEOUT_SECONDS, TimeUnit.SECONDS)
        .build()

    /**
     * Parse text using the enhanced API with audit mode and partial parsing support.
     */
    suspend fun parseText(
        text: String,
        timezone: String,
        locale: String,
        now: Date,
        mode: String? = null,
        fields: List<String>? = null
    ): ParseResult = withContext(Dispatchers.IO) {
        
        // Check network connectivity first
        if (!isNetworkAvailable()) {
            throw ApiException("No internet connection. Please check your network settings and try again.")
        }
        
        // Preprocess text to handle common formatting issues
        val preprocessedText = preprocessText(text)
        
        // Validate input
        if (preprocessedText.isBlank()) {
            throw ApiException("Please provide text containing event information.")
        }
        
        if (preprocessedText.length > 10000) {
            throw ApiException("Text is too long. Please limit to 10,000 characters.")
        }
        
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
            put("text", preprocessedText)
            put("timezone", timezone)
            put("locale", locale)
            put("now", formatDateTimeForApi(now))
            put("use_llm_enhancement", true)
        }
        
        val mediaType = "application/json; charset=utf-8".toMediaType()
        val body = requestBody.toString().toRequestBody(mediaType)
        
        val request = Request.Builder()
            .url(urlBuilder.build())
            .post(body)
            .addHeader("Content-Type", "application/json")
            .addHeader("Accept", "application/json")
            .addHeader("User-Agent", "CalendarEventApp-Android/2.0")
            .build()
        
        var retryCount = 0
        val maxRetries = 3
        
        while (retryCount <= maxRetries) {
            try {
                val response = client.newCall(request).execute()
                
                response.use { resp ->
                    val responseBody = resp.body?.string() ?: ""
                    
                    when (resp.code) {
                        200 -> {
                            val result = parseApiResponse(responseBody)
                            
                            // Handle enhanced API response format
                            result.fieldResults?.let { fieldResults ->
                                println("Field confidence scores: $fieldResults")
                            }
                            
                            result.parsingPath?.let { path ->
                                println("Parsing method used: $path")
                            }
                            
                            if (result.cacheHit == true) {
                                println("Result served from cache")
                            }
                            
                            // Log warnings for debugging
                            result.warnings?.let { warnings ->
                                if (warnings.isNotEmpty()) {
                                    println("Parsing warnings: $warnings")
                                }
                            }
                            
                            // Validate the parsed result
                            validateParseResult(result, preprocessedText)
                            return@withContext result
                        }
                        400 -> {
                            val errorDetails = parseErrorResponse(responseBody)
                            throw ApiException(errorDetails.userMessage)
                        }
                        422 -> {
                            val errorDetails = parseErrorResponse(responseBody)
                            throw ApiException(errorDetails.userMessage ?: "The text does not contain valid event information. Please try rephrasing with clearer date, time, and event details.")
                        }
                        429 -> {
                            val errorDetails = parseErrorResponse(responseBody)
                            val retryAfter = resp.header("Retry-After")?.toIntOrNull() ?: 60
                            throw ApiException("Too many requests. Please wait ${retryAfter} seconds before trying again.")
                        }
                        500, 502, 503, 504 -> {
                            if (retryCount < maxRetries) {
                                retryCount++
                                val delay = (retryCount * 1000L) // Exponential backoff
                                kotlinx.coroutines.delay(delay)
                                // Will retry in the next loop iteration
                            } else {
                                throw ApiException("Server is temporarily unavailable. Please try again in a few minutes.")
                            }
                        }
                        else -> {
                            val errorDetails = parseErrorResponse(responseBody)
                            throw ApiException(errorDetails.userMessage ?: "Request failed with code ${resp.code}. Please try again.")
                        }
                    }
                }
                
            } catch (e: java.net.SocketTimeoutException) {
                if (retryCount < maxRetries) {
                    retryCount++
                    // Will retry in the next loop iteration
                } else {
                    throw ApiException("Request timed out after multiple attempts. Please check your internet connection and try again.")
                }
            } catch (e: java.net.UnknownHostException) {
                throw ApiException("Unable to connect to the server. Please check your internet connection and try again.")
            } catch (e: java.net.ConnectException) {
                if (retryCount < maxRetries) {
                    retryCount++
                    val delay = (retryCount * 2000L) // Longer delay for connection issues
                    kotlinx.coroutines.delay(delay)
                    // Will retry in the next loop iteration
                } else {
                    throw ApiException("Unable to connect to the server. Please check your internet connection and try again later.")
                }
            } catch (e: IOException) {
                when {
                    e.message?.contains("timeout", ignoreCase = true) == true -> {
                        if (retryCount < maxRetries) {
                            retryCount++
                            // Will retry in the next loop iteration
                        } else {
                            throw ApiException("Request timed out. Please check your internet connection and try again.")
                        }
                    }
                    e.message?.contains("network", ignoreCase = true) == true -> 
                        throw ApiException("Network error occurred. Please check your internet connection and try again.")
                    else -> 
                        throw ApiException("Connection error: ${e.message ?: "Unknown network error"}. Please try again.")
                }
            } catch (e: ApiException) {
                throw e // Re-throw API exceptions without modification
            } catch (e: Exception) {
                throw ApiException("An unexpected error occurred: ${e.message ?: "Unknown error"}. Please try again.")
            }
        }
        
        // This should never be reached, but just in case
        throw ApiException("Failed to complete request after multiple attempts. Please try again later.")
    }
    
    /**
     * Check if network is available (basic check).
     */
    private fun isNetworkAvailable(): Boolean {
        return try {
            // Simple connectivity check - try to resolve a DNS name
            val address = java.net.InetAddress.getByName("8.8.8.8")
            !address.equals("")
        } catch (e: Exception) {
            false
        }
    }
    
    /**
     * Parse error response from API to extract user-friendly messages.
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
 * Data class representing the enhanced API response.
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
    val needsConfirmation: Boolean = false
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
 * Exception for API-related errors.
 */
class ApiException(message: String) : Exception(message)