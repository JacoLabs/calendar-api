package com.jacolabs.calendar

import android.content.ClipboardManager
import android.content.Context
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
 * 
 * Enhanced with clipboard merge logic to handle Gmail's selection limitations.
 */
class TextProcessorActivity : ComponentActivity() {
    
    private lateinit var apiService: ApiService
    private lateinit var textMergeHelper: TextMergeHelper
    
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        
        apiService = ApiService()
        textMergeHelper = TextMergeHelper(this)
        
        // Get the selected text from the intent
        val selectedText = intent.getCharSequenceExtra(Intent.EXTRA_PROCESS_TEXT)?.toString()
        
        if (selectedText.isNullOrBlank()) {
            showError("No text was selected")
            finish()
            return
        }
        
        // Show loading toast
        Toast.makeText(this, "Processing selected text...", Toast.LENGTH_SHORT).show()
        
        // Process the text with enhanced merge logic
        processSelectedTextWithMerge(selectedText)
    }
    
    private fun processSelectedTextWithMerge(selectedText: String) {
        lifecycleScope.launch {
            try {
                // Get current timezone and locale
                val timezone = TimeZone.getDefault().id
                val locale = Locale.getDefault().toString()
                val now = Date()
                
                // Try to enhance the selected text with clipboard merge and heuristics
                val enhancedText = textMergeHelper.enhanceTextForParsing(selectedText)
                
                // Call API to parse the enhanced text
                val result = apiService.parseText(enhancedText, timezone, locale, now)
                
                // Apply safer defaults if we have incomplete information
                val finalResult = textMergeHelper.applySaferDefaults(result, enhancedText)
                
                // Check if we got useful results
                if (finalResult.title.isNullOrBlank() && finalResult.startDateTime.isNullOrBlank()) {
                    showError("Could not find event information in the selected text")
                    finish()
                    return@launch
                }
                
                // Create calendar event intent
                createCalendarEvent(finalResult)
                
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