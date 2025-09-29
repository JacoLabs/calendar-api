package com.jacolabs.calendar

import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.content.pm.ResolveInfo
import android.net.Uri
import android.os.Build
import android.provider.CalendarContract
import android.widget.Toast
import java.text.SimpleDateFormat
import java.util.*

/**
 * Helper class for creating and launching calendar intents with robust app detection.
 * Handles Android 11+ package visibility restrictions and provides fallback mechanisms.
 */
class CalendarIntentHelper(private val context: Context) {
    
    companion object {
        // Common calendar app package names
        private val KNOWN_CALENDAR_APPS = listOf(
            "com.google.android.calendar",
            "com.samsung.android.calendar", 
            "com.microsoft.office.outlook",
            "com.android.calendar",
            "com.htc.calendar",
            "com.lge.calendar",
            "com.sonyericsson.organizer",
            "com.motorola.blur.calendar",
            "com.oneplus.calendar"
        )
        
        // Fallback web calendar URLs
        private val WEB_CALENDAR_URLS = mapOf(
            "google" to "https://calendar.google.com/calendar/render?action=TEMPLATE",
            "outlook" to "https://outlook.live.com/calendar/0/deeplink/compose"
        )
    }
    
    /**
     * Creates a calendar event using the most appropriate method available.
     * Tries native calendar apps first, then falls back to web calendars.
     */
    fun createCalendarEvent(result: ParseResult): Boolean {
        return try {
            // Check confidence score and provide appropriate feedback
            if (result.confidenceScore < 0.3) {
                showLowConfidenceWarning(result)
                return false
            }
            
            // Check if we have essential event data
            if (result.title.isNullOrBlank() && result.startDateTime.isNullOrBlank()) {
                showInsufficientDataError(result)
                return false
            }
            
            // First try native calendar intent
            if (tryNativeCalendarIntent(result)) {
                showSuccessMessage("Opening calendar app...")
                true
            } else if (tryWebCalendarFallback(result)) {
                showSuccessMessage("Opening web calendar...")
                true
            } else {
                showCalendarNotFoundDialog(result)
                false
            }
        } catch (e: Exception) {
            showErrorMessage("Failed to create calendar event: ${e.message}")
            false
        }
    }
    
    /**
     * Attempts to launch native calendar app with pre-filled event data.
     * Uses multiple strategies to handle Android 11+ package visibility restrictions.
     */
    private fun tryNativeCalendarIntent(result: ParseResult): Boolean {
        val intent = createCalendarIntent(result)
        
        // Strategy 1: Try direct intent launch (works if calendar app is visible)
        if (canLaunchIntent(intent)) {
            context.startActivity(intent)
            return true
        }
        
        // Strategy 2: Try specific calendar apps that we declared in queries
        for (packageName in KNOWN_CALENDAR_APPS) {
            if (trySpecificCalendarApp(intent, packageName)) {
                return true
            }
        }
        
        // Strategy 3: Try generic calendar intent without package restriction
        return tryGenericCalendarIntent(result)
    }
    
    /**
     * Creates the base calendar intent with event data.
     */
    private fun createCalendarIntent(result: ParseResult): Intent {
        return Intent(Intent.ACTION_INSERT).apply {
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
            
            // Add flags for better compatibility
            addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        }
    }
    
    /**
     * Checks if an intent can be launched using multiple detection methods.
     */
    private fun canLaunchIntent(intent: Intent): Boolean {
        return try {
            // Method 1: Try resolveActivity (may fail on Android 11+ due to package visibility)
            val resolveInfo = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
                context.packageManager.resolveActivity(
                    intent, 
                    PackageManager.ResolveInfoFlags.of(PackageManager.MATCH_DEFAULT_ONLY.toLong())
                )
            } else {
                @Suppress("DEPRECATION")
                context.packageManager.resolveActivity(intent, PackageManager.MATCH_DEFAULT_ONLY)
            }
            
            resolveInfo != null
        } catch (e: Exception) {
            // Method 2: Try queryIntentActivities as fallback
            try {
                val activities = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
                    context.packageManager.queryIntentActivities(
                        intent,
                        PackageManager.ResolveInfoFlags.of(PackageManager.MATCH_DEFAULT_ONLY.toLong())
                    )
                } else {
                    @Suppress("DEPRECATION")
                    context.packageManager.queryIntentActivities(intent, PackageManager.MATCH_DEFAULT_ONLY)
                }
                activities.isNotEmpty()
            } catch (e2: Exception) {
                false
            }
        }
    }
    
    /**
     * Tries to launch a specific calendar app by package name.
     */
    private fun trySpecificCalendarApp(intent: Intent, packageName: String): Boolean {
        return try {
            // Check if the specific app is installed
            if (isAppInstalled(packageName)) {
                val specificIntent = Intent(intent).apply {
                    setPackage(packageName)
                }
                
                context.startActivity(specificIntent)
                true
            } else {
                false
            }
        } catch (e: Exception) {
            false
        }
    }
    
    /**
     * Tries a generic calendar intent without package restrictions.
     * This is more likely to work on newer Android versions.
     */
    private fun tryGenericCalendarIntent(result: ParseResult): Boolean {
        return try {
            // Create a more generic intent that should work with any calendar app
            val genericIntent = Intent().apply {
                action = Intent.ACTION_EDIT
                type = "vnd.android.cursor.item/event"
                
                result.title?.let { putExtra("title", it) }
                result.description?.let { putExtra("description", it) }
                result.location?.let { putExtra("eventLocation", it) }
                
                result.startDateTime?.let { startDateTime ->
                    parseIsoDateTime(startDateTime)?.let { startTime ->
                        putExtra("beginTime", startTime)
                        
                        val endTime = result.endDateTime?.let { parseIsoDateTime(it) }
                            ?: (startTime + 60 * 60 * 1000)
                        putExtra("endTime", endTime)
                    }
                }
                
                if (result.allDay) {
                    putExtra("allDay", true)
                }
                
                addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            }
            
            context.startActivity(genericIntent)
            true
        } catch (e: Exception) {
            false
        }
    }
    
    /**
     * Checks if a specific app is installed.
     */
    private fun isAppInstalled(packageName: String): Boolean {
        return try {
            context.packageManager.getPackageInfo(packageName, 0)
            true
        } catch (e: PackageManager.NameNotFoundException) {
            false
        }
    }
    
    /**
     * Attempts to open a web-based calendar as fallback.
     */
    private fun tryWebCalendarFallback(result: ParseResult): Boolean {
        return try {
            val url = buildGoogleCalendarUrl(result)
            val webIntent = Intent(Intent.ACTION_VIEW, Uri.parse(url)).apply {
                addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            }
            
            context.startActivity(webIntent)
            true
        } catch (e: Exception) {
            false
        }
    }
    
    /**
     * Builds a Google Calendar web URL with pre-filled event data.
     */
    private fun buildGoogleCalendarUrl(result: ParseResult): String {
        val baseUrl = WEB_CALENDAR_URLS["google"]!!
        val params = mutableListOf<String>()
        
        result.title?.let { title ->
            params.add("text=${Uri.encode(title)}")
        }
        
        result.startDateTime?.let { startDateTime ->
            parseIsoDateTime(startDateTime)?.let { startTime ->
                val date = Date(startTime)
                val formatter = SimpleDateFormat("yyyyMMdd'T'HHmmss'Z'", Locale.US)
                formatter.timeZone = TimeZone.getTimeZone("UTC")
                
                val endTime = result.endDateTime?.let { parseIsoDateTime(it) }
                    ?: (startTime + 60 * 60 * 1000)
                val endDate = Date(endTime)
                
                val dateString = "${formatter.format(date)}/${formatter.format(endDate)}"
                params.add("dates=${Uri.encode(dateString)}")
            }
        }
        
        result.location?.let { location ->
            params.add("location=${Uri.encode(location)}")
        }
        
        result.description?.let { description ->
            params.add("details=${Uri.encode(description)}")
        }
        
        return if (params.isNotEmpty()) {
            "$baseUrl&${params.joinToString("&")}"
        } else {
            baseUrl
        }
    }
    
    /**
     * Shows a dialog when no calendar app is found, offering alternatives.
     */
    private fun showCalendarNotFoundDialog(result: ParseResult) {
        // For now, show a toast with instructions
        // In a full implementation, this could be a proper dialog
        val message = buildString {
            appendLine("No calendar app found.")
            appendLine("Please install Google Calendar or another calendar app.")
            appendLine()
            appendLine("Event details:")
            result.title?.let { appendLine("Title: $it") }
            result.startDateTime?.let { appendLine("Time: ${formatDateTime(it)}") }
            result.location?.let { appendLine("Location: $it") }
        }
        
        Toast.makeText(context, message, Toast.LENGTH_LONG).show()
    }
    
    /**
     * Parses ISO datetime string to milliseconds.
     */
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
    
    /**
     * Formats datetime for display.
     */
    private fun formatDateTime(isoDateTime: String): String {
        return try {
            val inputFormat = SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ssXXX", Locale.getDefault())
            val outputFormat = SimpleDateFormat("MMM dd, yyyy 'at' h:mm a", Locale.getDefault())
            val date = inputFormat.parse(isoDateTime)
            date?.let { outputFormat.format(it) } ?: isoDateTime
        } catch (e: Exception) {
            try {
                val inputFormat = SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss", Locale.getDefault())
                val outputFormat = SimpleDateFormat("MMM dd, yyyy 'at' h:mm a", Locale.getDefault())
                val date = inputFormat.parse(isoDateTime)
                date?.let { outputFormat.format(it) } ?: isoDateTime
            } catch (e2: Exception) {
                isoDateTime
            }
        }
    }
    
    /**
     * Shows a warning when confidence score is too low.
     */
    private fun showLowConfidenceWarning(result: ParseResult) {
        val confidence = (result.confidenceScore * 100).toInt()
        val message = buildString {
            appendLine("⚠️ Low confidence parsing ($confidence%)")
            appendLine()
            appendLine("The text might not contain clear event information.")
            appendLine("Try rephrasing with:")
            appendLine("• Clear date/time (e.g., 'tomorrow at 2 PM')")
            appendLine("• Specific event title")
            appendLine("• Standard time format (e.g., '9:00 AM' not '9:00a.m')")
        }
        
        Toast.makeText(context, message, Toast.LENGTH_LONG).show()
    }
    
    /**
     * Shows error when insufficient data is available.
     */
    private fun showInsufficientDataError(result: ParseResult) {
        val message = buildString {
            appendLine("❌ Insufficient event information")
            appendLine()
            appendLine("Could not extract title or time from the text.")
            appendLine("Please include:")
            appendLine("• Event title or description")
            appendLine("• Date and time information")
            appendLine()
            appendLine("Example: 'Meeting with John tomorrow at 2 PM'")
        }
        
        Toast.makeText(context, message, Toast.LENGTH_LONG).show()
    }
    
    private fun showSuccessMessage(message: String) {
        Toast.makeText(context, message, Toast.LENGTH_SHORT).show()
    }
    
    private fun showErrorMessage(message: String) {
        Toast.makeText(context, message, Toast.LENGTH_LONG).show()
    }
}