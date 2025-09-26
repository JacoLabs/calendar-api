package com.jacolabs.calendar

import android.app.Activity
import android.content.Intent
import android.os.Bundle
import android.provider.CalendarContract
import android.widget.Toast
import androidx.lifecycle.lifecycleScope
import kotlinx.coroutines.launch
import java.text.SimpleDateFormat
import java.util.*

/**
 * Activity that handles ACTION_PROCESS_TEXT intent.
 * Appears in text selection context menu as "Create calendar event".
 */
class TextProcessorActivity : Activity() {

    private lateinit var apiService: ApiService

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        
        apiService = ApiService()
        
        // Get the selected text from the intent
        val selectedText = intent.getCharSequenceExtra(Intent.EXTRA_PROCESS_TEXT)?.toString()
        
        if (selectedText.isNullOrBlank()) {
            Toast.makeText(this, "No text selected", Toast.LENGTH_SHORT).show()
            finish()
            return
        }

        // Process the text
        processText(selectedText)
    }

    private fun processText(text: String) {
        lifecycleScope.launch {
            try {
                // Validate text length
                if (text.length > 1000) {
                    Toast.makeText(
                        this@TextProcessorActivity, 
                        "Selected text is too long. Please select shorter text.", 
                        Toast.LENGTH_LONG
                    ).show()
                    finish()
                    return@launch
                }
                
                // Show loading toast
                Toast.makeText(this@TextProcessorActivity, "Processing text...", Toast.LENGTH_SHORT).show()
                
                // Get current timezone and locale
                val timezone = TimeZone.getDefault().id
                val locale = Locale.getDefault().toString()
                val now = Date()
                
                // Call API to parse text
                val parseResult = apiService.parseText(
                    text = text,
                    timezone = timezone,
                    locale = locale,
                    now = now
                )
                
                // Check confidence score
                if (parseResult.confidenceScore < 0.3) {
                    Toast.makeText(
                        this@TextProcessorActivity,
                        "Could not extract event information from selected text. Please try selecting text that contains date/time information.",
                        Toast.LENGTH_LONG
                    ).show()
                    finish()
                    return@launch
                }
                
                // Create calendar intent with parsed data
                createCalendarEvent(parseResult)
                
            } catch (e: ApiException) {
                // Handle API-specific errors
                Toast.makeText(
                    this@TextProcessorActivity, 
                    "Unable to process text: ${e.message}", 
                    Toast.LENGTH_LONG
                ).show()
                finish()
            } catch (e: Exception) {
                // Handle general errors
                Toast.makeText(
                    this@TextProcessorActivity, 
                    "An error occurred while processing the text. Please try again.", 
                    Toast.LENGTH_LONG
                ).show()
                finish()
            }
        }
    }

    private fun createCalendarEvent(parseResult: ParseResult) {
        val intent = Intent(Intent.ACTION_INSERT).apply {
            data = CalendarContract.Events.CONTENT_URI
            
            // Set title
            parseResult.title?.let { title ->
                putExtra(CalendarContract.Events.TITLE, title)
            }
            
            // Set start time
            parseResult.startDateTime?.let { startDateTime ->
                val startMillis = parseIsoDateTime(startDateTime)
                putExtra(CalendarContract.EXTRA_EVENT_BEGIN_TIME, startMillis)
            }
            
            // Set end time (default to +30 minutes if not provided)
            val endMillis = parseResult.endDateTime?.let { endDateTime ->
                parseIsoDateTime(endDateTime)
            } ?: run {
                // Default to 30 minutes after start time
                parseResult.startDateTime?.let { startDateTime ->
                    parseIsoDateTime(startDateTime) + (30 * 60 * 1000) // +30 minutes
                }
            }
            
            endMillis?.let { 
                putExtra(CalendarContract.EXTRA_EVENT_END_TIME, it)
            }
            
            // Set location
            parseResult.location?.let { location ->
                putExtra(CalendarContract.Events.EVENT_LOCATION, location)
            }
            
            // Set description
            parseResult.description?.let { description ->
                putExtra(CalendarContract.Events.DESCRIPTION, description)
            }
            
            // Set all day if applicable
            if (parseResult.allDay) {
                putExtra(CalendarContract.EXTRA_EVENT_ALL_DAY, true)
            }
        }
        
        try {
            // Launch native calendar app with pre-filled data
            startActivity(intent)
            
            // Show success message
            Toast.makeText(
                this, 
                "Opening calendar with event details...", 
                Toast.LENGTH_SHORT
            ).show()
            
        } catch (e: Exception) {
            Toast.makeText(
                this, 
                "No calendar app found", 
                Toast.LENGTH_LONG
            ).show()
        } finally {
            finish()
        }
    }

    private fun parseIsoDateTime(isoDateTime: String): Long {
        return try {
            // Parse ISO 8601 datetime string to milliseconds
            val format = SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ssXXX", Locale.US)
            format.parse(isoDateTime)?.time ?: System.currentTimeMillis()
        } catch (e: Exception) {
            // Fallback parsing for different ISO formats
            try {
                val format = SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss'Z'", Locale.US)
                format.timeZone = TimeZone.getTimeZone("UTC")
                format.parse(isoDateTime)?.time ?: System.currentTimeMillis()
            } catch (e2: Exception) {
                System.currentTimeMillis()
            }
        }
    }
}