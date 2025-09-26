package com.jacolabs.calendar

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONObject
import java.io.BufferedReader
import java.io.InputStreamReader
import java.io.OutputStreamWriter
import java.net.HttpURLConnection
import java.net.URL
import java.text.SimpleDateFormat
import java.util.*

/**
 * Service for calling the text-to-calendar API.
 */
class ApiService {
    
    companion object {
        private const val API_BASE_URL = "https://calendar-api-wrxz.onrender.com"
        private const val PARSE_ENDPOINT = "$API_BASE_URL/parse"
        private const val TIMEOUT_MS = 10000 // 10 seconds
    }

    /**
     * Parse text using the remote API.
     */
    suspend fun parseText(
        text: String,
        timezone: String,
        locale: String,
        now: Date
    ): ParseResult = withContext(Dispatchers.IO) {
        
        val url = URL(PARSE_ENDPOINT)
        val connection = url.openConnection() as HttpURLConnection
        
        try {
            // Configure connection
            connection.requestMethod = "POST"
            connection.setRequestProperty("Content-Type", "application/json")
            connection.setRequestProperty("Accept", "application/json")
            connection.setRequestProperty("User-Agent", "CalendarEventApp-Android/1.0")
            connection.connectTimeout = TIMEOUT_MS
            connection.readTimeout = TIMEOUT_MS
            connection.doOutput = true
            
            // Create request body
            val requestBody = JSONObject().apply {
                put("text", text)
                put("timezone", timezone)
                put("locale", locale)
                put("now", formatDateTimeForApi(now))
            }
            
            // Send request
            OutputStreamWriter(connection.outputStream).use { writer ->
                writer.write(requestBody.toString())
                writer.flush()
            }
            
            // Read response
            val responseCode = connection.responseCode
            
            if (responseCode == HttpURLConnection.HTTP_OK) {
                val response = BufferedReader(InputStreamReader(connection.inputStream)).use { reader ->
                    reader.readText()
                }
                
                parseApiResponse(response)
                
            } else {
                val errorResponse = try {
                    BufferedReader(InputStreamReader(connection.errorStream)).use { reader ->
                        reader.readText()
                    }
                } catch (e: Exception) {
                    "Unknown error"
                }
                
                when (responseCode) {
                    422 -> throw ApiException("The selected text does not contain valid event information")
                    429 -> throw ApiException("Too many requests. Please try again later")
                    500 -> throw ApiException("Server error. Please try again later")
                    else -> throw ApiException("Request failed (code $responseCode): $errorResponse")
                }
            }
            
        } catch (e: java.net.SocketTimeoutException) {
            throw ApiException("Request timed out. Please check your internet connection")
        } catch (e: java.net.UnknownHostException) {
            throw ApiException("Unable to connect to server. Please check your internet connection")
        } catch (e: java.io.IOException) {
            throw ApiException("Network error occurred. Please try again")
        } finally {
            connection.disconnect()
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