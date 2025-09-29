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
 * Activity that handles ACTION_SEND intents for shared text.
 * This appears in the share menu as "Create calendar event".
 */
class ShareHandlerActivity : ComponentActivity() {
    
    private lateinit var apiService: ApiService
    
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        
        apiService = ApiService()
        
        // Handle the shared text
        when (intent.action) {
            Intent.ACTION_SEND -> {
                if (intent.type == "text/plain") {
                    val sharedText = intent.getStringExtra(Intent.EXTRA_TEXT)
                    if (!sharedText.isNullOrBlank()) {
                        processSharedText(sharedText)
                    } else {
                        showError("No text was shared")
                        finish()
                    }
                } else {
                    showError("Only text sharing is supported")
                    finish()
                }
            }
            else -> {
                showError("Unsupported action")
                finish()
            }
        }
    }
    
    private fun processSharedText(text: String) {
        // Show loading toast
        Toast.makeText(this, "Processing shared text...", Toast.LENGTH_SHORT).show()
        
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
                    showError("Could not find event information in the shared text")
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
            val calendarHelper = CalendarIntentHelper(this)
            val success = calendarHelper.createCalendarEvent(result)
            
            if (!success) {
                showError("Could not open calendar app")
            }
            
        } catch (e: Exception) {
            showError("Failed to create calendar event: ${e.message}")
        }
        
        finish()
    }
    

    
    private fun showError(message: String) {
        Toast.makeText(this, message, Toast.LENGTH_LONG).show()
    }
}