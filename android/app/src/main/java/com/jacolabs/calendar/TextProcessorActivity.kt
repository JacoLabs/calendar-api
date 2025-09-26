package com.jacolabs.calendar

import android.content.Intent
import android.os.Bundle
import android.provider.CalendarContract
import android.widget.Toast
import androidx.activity.ComponentActivity
import androidx.lifecycle.lifecycleScope
import kotlinx.coroutines.launch
import java.text.SimpleDateFormat
import java.util.*

/**
 * Activity that handles ACTION_PROCESS_TEXT intents for selected text.
 * This appears in the text selection context menu as "Create calendar event".
 */
class TextProcessorActivity : ComponentActivity() {
    
    private lateinit var apiService: ApiService
    
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        
        apiService = ApiService()
        
        // Get the selected text from the intent
        val selectedText = intent.getCharSequenceExtra(Intent.EXTRA_PROCESS_TEXT)?.toString()
        
        if (selectedText.isNullOrBlank()) {
            showError("No text was selected")
            finish()
            return
        }
        
        // Show loading toast
        Toast.makeText(this, "Processing selected text...", Toast.LENGTH_SHORT).show()
        
        // Process the text
        processSelectedText(selectedText)
    }
    
    private fun processSelectedText(text: String) {
        lifecycleScope.launch {
            try {
                // Get current timezone and locale
                val timezone = TimeZone.getDefault().id
                val locale = Locale.getDefault().toString()
                val now = Date()
                
                // Call API to parse the text
                val result = apiService.parseText(text, timezone, locale, now)
                
                // Check if we got useful results
                if (result.title.isNullOrBlank() && result.startDateTime.isNullOrBlank()) {
                    showError("Could not find event information in the selected text")
                    finish()
                    return@launch
                }
                
                // Create calendar event intent
                createCalendarEvent(result)
                
            } catch (e: ApiException) {
                showError(e.message ?: "Failed to process text")
                finish()
            } catch (e: Exception) {
                showError("An unexpected error occurred")
                finish()
            }
        }
    }
    
    private fun createCalendarEvent(result: ParseResult) {
        try {
            val intent = Intent(Intent.ACTION_INSERT).apply {
                data = CalendarContract.Events.CONTENT_URI
                
                // Set title
                result.title?.let { title ->
                    putExtra(CalendarContract.Events.TITLE, title)
                }
                
                // Set description (original text)
                result.description?.let { description ->
                    putExtra(CalendarContract.Events.DESCRIPTION, description)
                }
                
                // Set location
                result.location?.let { location ->
                    putExtra(CalendarContract.Events.EVENT_LOCATION, location)
                }
                
                // Set start time
                result.startDateTime?.let { startDateTime ->
                    val startTime = parseIsoDateTime(startDateTime)
                    if (startTime != null) {
                        putExtra(CalendarContract.EXTRA_EVENT_BEGIN_TIME, startTime)
                        
                        // Set end time if available, otherwise default to 1 hour later
                        val endTime = result.endDateTime?.let { parseIsoDateTime(it) }
                            ?: (startTime + 60 * 60 * 1000) // 1 hour later
                        
                        putExtra(CalendarContract.EXTRA_EVENT_END_TIME, endTime)
                    }
                }
                
                // Set all day if detected
                if (result.allDay) {
                    putExtra(CalendarContract.Events.ALL_DAY, true)
                }
            }
            
            // Launch calendar app
            if (intent.resolveActivity(packageManager) != null) {
                startActivity(intent)
                
                // Show success message
                Toast.makeText(
                    this,
                    "Opening calendar app with event details...",
                    Toast.LENGTH_SHORT
                ).show()
            } else {
                showError("No calendar app found")
            }
            
        } catch (e: Exception) {
            showError("Failed to create calendar event")
        }
        
        finish()
    }
    
    private fun parseIsoDateTime(isoDateTime: String): Long? {
        return try {
            // Try parsing ISO 8601 format with timezone
            val format = SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ssXXX", Locale.US)
            format.parse(isoDateTime)?.time
        } catch (e: Exception) {
            try {
                // Fallback: try without timezone
                val format = SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss", Locale.US)
                format.parse(isoDateTime)?.time
            } catch (e2: Exception) {
                null
            }
        }
    }
    
    private fun showError(message: String) {
        Toast.makeText(this, message, Toast.LENGTH_LONG).show()
    }
}