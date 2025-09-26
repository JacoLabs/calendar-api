package com.jacolabs.calendar

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.*
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
     * Parse text using the remote API.
     */
    suspend fun parseText(
        text: String,
        timezone: String,
        locale: String,
        now: Date
    ): ParseResult = withContext(Dispatchers.IO) {
        
        // Create request body
        val requestBody = JSONObject().apply {
            put("text", text)
            put("timezone", timezone)
            put("locale", locale)
            put("now", formatDateTimeForApi(now))
        }
        
        val mediaType = "application/json; charset=utf-8".toMediaType()
        val body = requestBody.toString().toRequestBody(mediaType)
        
        val request = Request.Builder()
            .url(PARSE_ENDPOINT)
            .post(body)
            .addHeader("Content-Type", "application/json")
            .addHeader("Accept", "application/json")
            .addHeader("User-Agent", "CalendarEventApp-Android/1.0")
            .build()
        
        try {
            val response = client.newCall(request).execute()
            
            response.use { resp ->
                val responseBody = resp.body?.string() ?: ""
                
                when (resp.code) {
                    200 -> parseApiResponse(responseBody)
                    422 -> throw ApiException("The selected text does not contain valid event information")
                    429 -> throw ApiException("Too many requests. Please try again later")
                    500 -> throw ApiException("Server error. Please try again later")
                    else -> {
                        val errorMsg = try {
                            val errorJson = JSONObject(responseBody)
                            errorJson.optString("detail", "Unknown error")
                        } catch (e: Exception) {
                            "Request failed (code ${resp.code})"
                        }
                        throw ApiException(errorMsg)
                    }
                }
            }
            
        } catch (e: IOException) {
            when {
                e.message?.contains("timeout") == true -> 
                    throw ApiException("Request timed out. Please check your internet connection")
                e.message?.contains("Unable to resolve host") == true -> 
                    throw ApiException("Unable to connect to server. Please check your internet connection")
                else -> 
                    throw ApiException("Network error occurred. Please try again")
            }
        } catch (e: ApiException) {
            throw e
        } catch (e: Exception) {
            throw ApiException("An unexpected error occurred: ${e.message}")
        }
    }

    private fun parseApiResponse(jsonResponse: String): ParseResult {
        val json = JSONObject(jsonResponse)
        
        return ParseResult(
            title = json.optString("title").takeIf { it.isNotEmpty() },
            startDateTime = json.optString("start_datetime").takeIf { it.isNotEmpty() },
            endDateTime = json.optString("end_datetime").takeIf { it.isNotEmpty() },
            location = json.optString("location").takeIf { it.isNotEmpty() },
            description = json.optString("description").takeIf { it.isNotEmpty() },
            confidenceScore = json.optDouble("confidence_score", 0.0),
            allDay = json.optBoolean("all_day", false),
            timezone = json.optString("timezone", "UTC")
        )
    }

    private fun formatDateTimeForApi(date: Date): String {
        val format = SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss'Z'", Locale.US)
        format.timeZone = TimeZone.getTimeZone("UTC")
        return format.format(date)
    }
}

/**
 * Data class representing the API response.
 */
data class ParseResult(
    val title: String?,
    val startDateTime: String?,
    val endDateTime: String?,
    val location: String?,
    val description: String?,
    val confidenceScore: Double,
    val allDay: Boolean,
    val timezone: String
)

/**
 * Exception for API-related errors.
 */
class ApiException(message: String) : Exception(message)