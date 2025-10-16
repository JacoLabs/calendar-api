package com.jacolabs.calendar

import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.content.pm.ResolveInfo
import android.net.Uri
import android.os.Build
import android.provider.CalendarContract
import android.widget.Toast
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.text.SimpleDateFormat
import java.util.*

/**
 * Enhanced helper class for creating and launching calendar intents with comprehensive fallback mechanisms.
 * Handles Android 11+ package visibility restrictions and provides multiple fallback strategies.
 */
class CalendarIntentHelper(private val context: Context) {
    
    /**
     * Enumeration of calendar launch strategies in priority order
     */
    enum class LaunchStrategy {
        NATIVE_CALENDAR_INTENT,
        SPECIFIC_APP_TARGETING,
        GENERIC_CALENDAR_INTENT,
        WEB_CALENDAR_FALLBACK,
        MANUAL_COPY_TO_CLIPBOARD
    }

    /**
     * Result of calendar launch attempt
     */
    data class LaunchResult(
        val success: Boolean,
        val strategy: LaunchStrategy,
        val errorMessage: String? = null,
        val alternativesAvailable: List<LaunchStrategy> = emptyList(),
        val appUsed: String? = null
    )

    /**
     * Configuration for calendar launch behavior
     */
    data class CalendarLaunchConfig(
        val enableWebFallback: Boolean = true,
        val enableClipboardFallback: Boolean = true,
        val maxRetryAttempts: Int = 3,
        val showSuccessMessages: Boolean = true,
        val showErrorDialogs: Boolean = true
    )

    companion object {
        // Priority-ordered calendar app package names with display names
        private val KNOWN_CALENDAR_APPS = listOf(
            CalendarApp("com.google.android.calendar", "Google Calendar"),
            CalendarApp("com.samsung.android.calendar", "Samsung Calendar"), 
            CalendarApp("com.microsoft.office.outlook", "Microsoft Outlook"),
            CalendarApp("com.android.calendar", "Android Calendar"),
            CalendarApp("com.htc.calendar", "HTC Calendar"),
            CalendarApp("com.lge.calendar", "LG Calendar"),
            CalendarApp("com.sonyericsson.organizer", "Sony Calendar"),
            CalendarApp("com.motorola.blur.calendar", "Motorola Calendar"),
            CalendarApp("com.oneplus.calendar", "OnePlus Calendar"),
            CalendarApp("com.xiaomi.calendar", "Xiaomi Calendar"),
            CalendarApp("com.huawei.calendar", "Huawei Calendar"),
            CalendarApp("com.oppo.calendar", "OPPO Calendar"),
            CalendarApp("com.vivo.calendar", "Vivo Calendar")
        )
        
        // Fallback web calendar URLs with enhanced parameters
        private val WEB_CALENDAR_URLS = mapOf(
            "google" to "https://calendar.google.com/calendar/render?action=TEMPLATE",
            "outlook" to "https://outlook.live.com/calendar/0/deeplink/compose",
            "yahoo" to "https://calendar.yahoo.com/?v=60&TITLE={title}&ST1={start}&DUR={duration}&DESC={description}&in_loc={location}",
            "apple" to "https://www.icloud.com/calendar/"
        )

        // Default launch strategies in priority order
        private val DEFAULT_STRATEGIES = listOf(
            LaunchStrategy.NATIVE_CALENDAR_INTENT,
            LaunchStrategy.SPECIFIC_APP_TARGETING,
            LaunchStrategy.GENERIC_CALENDAR_INTENT,
            LaunchStrategy.WEB_CALENDAR_FALLBACK,
            LaunchStrategy.MANUAL_COPY_TO_CLIPBOARD
        )
    }

    /**
     * Data class for calendar app information
     */
    private data class CalendarApp(
        val packageName: String,
        val displayName: String
    )

    private val config = CalendarLaunchConfig()
    
    /**
     * Creates a calendar event using comprehensive fallback mechanisms (synchronous version).
     * Maintains backward compatibility with existing code.
     */
    fun createCalendarEvent(result: ParseResult): Boolean {
        return try {
            // Validate input data first
            val validationResult = validateEventData(result)
            if (!validationResult.success) {
                if (config.showErrorDialogs) {
                    showErrorMessage(validationResult.errorMessage ?: "Validation failed")
                }
                return false
            }

            // Try each strategy in order until one succeeds
            val launchResult = launchCalendarWithFallbacksSync(result, DEFAULT_STRATEGIES)
            
            if (launchResult.success) {
                if (config.showSuccessMessages) {
                    showSuccessMessage(getSuccessMessage(launchResult))
                }
                return true
            } else {
                if (config.showErrorDialogs) {
                    showCalendarNotFoundDialog(result, launchResult)
                }
                return false
            }
        } catch (e: Exception) {
            showErrorMessage("Failed to create calendar event: ${e.message}")
            false
        }
    }

    /**
     * Creates a calendar event using comprehensive fallback mechanisms (asynchronous version).
     * Provides detailed error reporting and launch results.
     */
    suspend fun createCalendarEventAsync(result: ParseResult): LaunchResult = withContext(Dispatchers.Main) {
        return@withContext try {
            // Validate input data first
            val validationResult = validateEventData(result)
            if (!validationResult.success) {
                return@withContext LaunchResult(
                    success = false,
                    strategy = LaunchStrategy.NATIVE_CALENDAR_INTENT,
                    errorMessage = validationResult.errorMessage,
                    alternativesAvailable = if (config.enableClipboardFallback) 
                        listOf(LaunchStrategy.MANUAL_COPY_TO_CLIPBOARD) else emptyList()
                )
            }

            // Try each strategy in order until one succeeds
            launchCalendarWithFallbacks(result, DEFAULT_STRATEGIES)
        } catch (e: Exception) {
            LaunchResult(
                success = false,
                strategy = LaunchStrategy.NATIVE_CALENDAR_INTENT,
                errorMessage = "Unexpected error: ${e.message}",
                alternativesAvailable = if (config.enableClipboardFallback) 
                    listOf(LaunchStrategy.MANUAL_COPY_TO_CLIPBOARD) else emptyList()
            )
        }
    }

    /**
     * Attempts to launch calendar using multiple fallback strategies (synchronous version).
     */
    private fun launchCalendarWithFallbacksSync(
        result: ParseResult,
        strategies: List<LaunchStrategy> = DEFAULT_STRATEGIES
    ): LaunchResult {
        val availableAlternatives = mutableListOf<LaunchStrategy>()
        var lastError: String? = null

        for (strategy in strategies) {
            val launchResult = when (strategy) {
                LaunchStrategy.NATIVE_CALENDAR_INTENT -> tryNativeCalendarIntent(result)
                LaunchStrategy.SPECIFIC_APP_TARGETING -> trySpecificCalendarApps(result)
                LaunchStrategy.GENERIC_CALENDAR_INTENT -> tryGenericCalendarIntent(result)
                LaunchStrategy.WEB_CALENDAR_FALLBACK -> {
                    if (config.enableWebFallback) tryWebCalendarFallback(result)
                    else LaunchResult(false, strategy, "Web fallback disabled")
                }
                LaunchStrategy.MANUAL_COPY_TO_CLIPBOARD -> {
                    if (config.enableClipboardFallback) copyEventToClipboard(result)
                    else LaunchResult(false, strategy, "Clipboard fallback disabled")
                }
            }

            if (launchResult.success) {
                return launchResult.copy(
                    alternativesAvailable = availableAlternatives
                )
            } else {
                lastError = launchResult.errorMessage
                // Add remaining strategies as alternatives
                if (strategies.indexOf(strategy) < strategies.size - 1) {
                    availableAlternatives.addAll(strategies.subList(strategies.indexOf(strategy) + 1, strategies.size))
                }
            }
        }

        // All strategies failed
        return LaunchResult(
            success = false,
            strategy = strategies.first(),
            errorMessage = lastError ?: "All calendar launch strategies failed",
            alternativesAvailable = availableAlternatives
        )
    }

    /**
     * Attempts to launch calendar using multiple fallback strategies (asynchronous version).
     */
    suspend fun launchCalendarWithFallbacks(
        result: ParseResult,
        strategies: List<LaunchStrategy> = DEFAULT_STRATEGIES
    ): LaunchResult = withContext(Dispatchers.Main) {
        return@withContext launchCalendarWithFallbacksSync(result, strategies)
    }
    
    /**
     * Validates event data and provides specific feedback about missing information.
     */
    private fun validateEventData(result: ParseResult): ValidationResult {
        // Check confidence score
        if (result.confidenceScore < 0.3) {
            return ValidationResult(
                success = false,
                errorMessage = "Low confidence parsing (${(result.confidenceScore * 100).toInt()}%). " +
                        "The text might not contain clear event information. " +
                        "Try rephrasing with clearer date, time, and event details."
            )
        }
        
        // Check if we have essential event data
        if (result.title.isNullOrBlank() && result.startDateTime.isNullOrBlank()) {
            return ValidationResult(
                success = false,
                errorMessage = "Insufficient event information. Could not extract title or time from the text. " +
                        "Please include event title and date/time information."
            )
        }

        return ValidationResult(success = true)
    }

    /**
     * Data class for validation results
     */
    private data class ValidationResult(
        val success: Boolean,
        val errorMessage: String? = null
    )

    /**
     * Attempts to launch native calendar app with enhanced error detection.
     */
    private fun tryNativeCalendarIntent(result: ParseResult): LaunchResult {
        return try {
            val intent = createCalendarIntent(result)
            
            // Check if intent can be resolved
            if (canLaunchIntent(intent)) {
                context.startActivity(intent)
                LaunchResult(
                    success = true,
                    strategy = LaunchStrategy.NATIVE_CALENDAR_INTENT,
                    appUsed = "Default Calendar App"
                )
            } else {
                LaunchResult(
                    success = false,
                    strategy = LaunchStrategy.NATIVE_CALENDAR_INTENT,
                    errorMessage = "No default calendar app found or app not visible"
                )
            }
        } catch (e: Exception) {
            LaunchResult(
                success = false,
                strategy = LaunchStrategy.NATIVE_CALENDAR_INTENT,
                errorMessage = "Failed to launch native calendar: ${e.message}"
            )
        }
    }

    /**
     * Attempts to launch specific calendar apps in priority order.
     */
    private fun trySpecificCalendarApps(result: ParseResult): LaunchResult {
        val intent = createCalendarIntent(result)
        val installedApps = getInstalledCalendarApps()
        
        if (installedApps.isEmpty()) {
            return LaunchResult(
                success = false,
                strategy = LaunchStrategy.SPECIFIC_APP_TARGETING,
                errorMessage = "No known calendar apps are installed"
            )
        }

        // Try each installed app in priority order
        for (app in installedApps) {
            try {
                val specificIntent = Intent(intent).apply {
                    setPackage(app.packageName)
                }
                
                context.startActivity(specificIntent)
                return LaunchResult(
                    success = true,
                    strategy = LaunchStrategy.SPECIFIC_APP_TARGETING,
                    appUsed = app.displayName
                )
            } catch (e: Exception) {
                // Continue to next app
                continue
            }
        }

        return LaunchResult(
            success = false,
            strategy = LaunchStrategy.SPECIFIC_APP_TARGETING,
            errorMessage = "Failed to launch any of the ${installedApps.size} installed calendar apps"
        )
    }

    /**
     * Gets list of installed calendar apps in priority order.
     */
    private fun getInstalledCalendarApps(): List<CalendarApp> {
        return KNOWN_CALENDAR_APPS.filter { app ->
            isAppInstalled(app.packageName)
        }
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
     * Tries a generic calendar intent without package restrictions.
     * This is more likely to work on newer Android versions.
     */
    private fun tryGenericCalendarIntent(result: ParseResult): LaunchResult {
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
            LaunchResult(
                success = true,
                strategy = LaunchStrategy.GENERIC_CALENDAR_INTENT,
                appUsed = "Generic Calendar Handler"
            )
        } catch (e: Exception) {
            LaunchResult(
                success = false,
                strategy = LaunchStrategy.GENERIC_CALENDAR_INTENT,
                errorMessage = "Failed to launch generic calendar intent: ${e.message}"
            )
        }
    }
    
    /**
     * Checks if a specific app is installed.
     */
    private fun isAppInstalled(packageName: String): Boolean {
        return try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
                context.packageManager.getPackageInfo(
                    packageName, 
                    PackageManager.PackageInfoFlags.of(0)
                )
            } else {
                @Suppress("DEPRECATION")
                context.packageManager.getPackageInfo(packageName, 0)
            }
            true
        } catch (e: PackageManager.NameNotFoundException) {
            false
        }
    }
    
    /**
     * Attempts to open a web-based calendar as fallback with multiple providers.
     */
    private fun tryWebCalendarFallback(result: ParseResult): LaunchResult {
        // Try Google Calendar first (most compatible)
        val googleResult = tryWebCalendarProvider(result, "google")
        if (googleResult.success) {
            return googleResult
        }

        // Try Outlook as secondary option
        val outlookResult = tryWebCalendarProvider(result, "outlook")
        if (outlookResult.success) {
            return outlookResult
        }

        return LaunchResult(
            success = false,
            strategy = LaunchStrategy.WEB_CALENDAR_FALLBACK,
            errorMessage = "Failed to open web calendar. No browser available or network error."
        )
    }

    /**
     * Attempts to open a specific web calendar provider.
     */
    private fun tryWebCalendarProvider(result: ParseResult, provider: String): LaunchResult {
        return try {
            val url = when (provider) {
                "google" -> buildGoogleCalendarUrl(result)
                "outlook" -> buildOutlookCalendarUrl(result)
                else -> buildGoogleCalendarUrl(result) // Default fallback
            }
            
            val webIntent = Intent(Intent.ACTION_VIEW, Uri.parse(url)).apply {
                addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            }
            
            // Check if browser is available
            if (canLaunchIntent(webIntent)) {
                context.startActivity(webIntent)
                LaunchResult(
                    success = true,
                    strategy = LaunchStrategy.WEB_CALENDAR_FALLBACK,
                    appUsed = "${provider.capitalize()} Calendar (Web)"
                )
            } else {
                LaunchResult(
                    success = false,
                    strategy = LaunchStrategy.WEB_CALENDAR_FALLBACK,
                    errorMessage = "No browser app available to open web calendar"
                )
            }
        } catch (e: Exception) {
            LaunchResult(
                success = false,
                strategy = LaunchStrategy.WEB_CALENDAR_FALLBACK,
                errorMessage = "Failed to open $provider calendar: ${e.message}"
            )
        }
    }

    /**
     * Copies event details to clipboard as a manual fallback option.
     */
    private fun copyEventToClipboard(result: ParseResult): LaunchResult {
        return try {
            val clipboardManager = context.getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
            val eventText = formatEventForClipboard(result)
            
            val clipData = ClipData.newPlainText("Calendar Event", eventText)
            clipboardManager.setPrimaryClip(clipData)
            
            // Show instructions to user
            showClipboardCopyInstructions(result)
            
            LaunchResult(
                success = true,
                strategy = LaunchStrategy.MANUAL_COPY_TO_CLIPBOARD,
                appUsed = "Clipboard"
            )
        } catch (e: Exception) {
            LaunchResult(
                success = false,
                strategy = LaunchStrategy.MANUAL_COPY_TO_CLIPBOARD,
                errorMessage = "Failed to copy to clipboard: ${e.message}"
            )
        }
    }

    /**
     * Formats event details for clipboard copying.
     */
    private fun formatEventForClipboard(result: ParseResult): String {
        return buildString {
            appendLine("📅 Calendar Event Details")
            appendLine("=" * 30)
            
            result.title?.let { 
                appendLine("Title: $it")
            }
            
            result.startDateTime?.let { startDateTime ->
                val formattedStart = formatDateTime(startDateTime)
                appendLine("Start: $formattedStart")
                
                result.endDateTime?.let { endDateTime ->
                    val formattedEnd = formatDateTime(endDateTime)
                    appendLine("End: $formattedEnd")
                }
            }
            
            if (result.allDay) {
                appendLine("All Day: Yes")
            }
            
            result.location?.let {
                appendLine("Location: $it")
            }
            
            result.description?.let {
                appendLine("Description: $it")
            }
            
            appendLine()
            appendLine("Confidence: ${(result.confidenceScore * 100).toInt()}%")
            appendLine("Generated by Calendar Event App")
        }
    }

    /**
     * Shows instructions for manual event creation after clipboard copy.
     */
    private fun showClipboardCopyInstructions(result: ParseResult) {
        val message = buildString {
            appendLine("📋 Event details copied to clipboard!")
            appendLine()
            appendLine("To create the event manually:")
            appendLine("1. Open your calendar app")
            appendLine("2. Create a new event")
            appendLine("3. Paste the details (long press in text fields)")
            appendLine()
            result.title?.let { appendLine("Title: $it") }
            result.startDateTime?.let { appendLine("Time: ${formatDateTime(it)}") }
        }
        
        Toast.makeText(context, message, Toast.LENGTH_LONG).show()
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
     * Builds an Outlook Calendar web URL with pre-filled event data.
     */
    private fun buildOutlookCalendarUrl(result: ParseResult): String {
        val baseUrl = WEB_CALENDAR_URLS["outlook"]!!
        val params = mutableListOf<String>()
        
        result.title?.let { title ->
            params.add("subject=${Uri.encode(title)}")
        }
        
        result.startDateTime?.let { startDateTime ->
            parseIsoDateTime(startDateTime)?.let { startTime ->
                val date = Date(startTime)
                val formatter = SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss.SSS'Z'", Locale.US)
                formatter.timeZone = TimeZone.getTimeZone("UTC")
                
                params.add("startdt=${Uri.encode(formatter.format(date))}")
                
                val endTime = result.endDateTime?.let { parseIsoDateTime(it) }
                    ?: (startTime + 60 * 60 * 1000)
                val endDate = Date(endTime)
                
                params.add("enddt=${Uri.encode(formatter.format(endDate))}")
            }
        }
        
        result.location?.let { location ->
            params.add("location=${Uri.encode(location)}")
        }
        
        result.description?.let { description ->
            params.add("body=${Uri.encode(description)}")
        }
        
        if (result.allDay) {
            params.add("allday=true")
        }
        
        return if (params.isNotEmpty()) {
            "$baseUrl?${params.joinToString("&")}"
        } else {
            baseUrl
        }
    }
    
    /**
     * Shows enhanced dialog when calendar launch fails, offering specific alternatives.
     */
    private fun showCalendarNotFoundDialog(result: ParseResult, launchResult: LaunchResult) {
        val message = buildString {
            appendLine("❌ Calendar Launch Failed")
            appendLine()
            appendLine("Error: ${launchResult.errorMessage}")
            appendLine()
            
            if (launchResult.alternativesAvailable.isNotEmpty()) {
                appendLine("Available alternatives:")
                launchResult.alternativesAvailable.forEach { strategy ->
                    when (strategy) {
                        LaunchStrategy.WEB_CALENDAR_FALLBACK -> 
                            appendLine("• Open web calendar (requires browser)")
                        LaunchStrategy.MANUAL_COPY_TO_CLIPBOARD -> 
                            appendLine("• Copy event details to clipboard")
                        LaunchStrategy.SPECIFIC_APP_TARGETING -> 
                            appendLine("• Try specific calendar apps")
                        LaunchStrategy.GENERIC_CALENDAR_INTENT -> 
                            appendLine("• Try generic calendar handler")
                        else -> appendLine("• ${strategy.name.lowercase().replace('_', ' ')}")
                    }
                }
                appendLine()
            }
            
            appendLine("Event details:")
            result.title?.let { appendLine("Title: $it") }
            result.startDateTime?.let { appendLine("Time: ${formatDateTime(it)}") }
            result.location?.let { appendLine("Location: $it") }
            
            appendLine()
            appendLine("Suggestions:")
            appendLine("• Install Google Calendar or another calendar app")
            appendLine("• Check app permissions")
            appendLine("• Try copying details to clipboard for manual entry")
        }
        
        Toast.makeText(context, message, Toast.LENGTH_LONG).show()
    }

    /**
     * Gets success message based on launch result.
     */
    private fun getSuccessMessage(launchResult: LaunchResult): String {
        return when (launchResult.strategy) {
            LaunchStrategy.NATIVE_CALENDAR_INTENT -> 
                "✅ Opening ${launchResult.appUsed ?: "calendar app"}..."
            LaunchStrategy.SPECIFIC_APP_TARGETING -> 
                "✅ Opening ${launchResult.appUsed}..."
            LaunchStrategy.GENERIC_CALENDAR_INTENT -> 
                "✅ Opening calendar app..."
            LaunchStrategy.WEB_CALENDAR_FALLBACK -> 
                "✅ Opening ${launchResult.appUsed}..."
            LaunchStrategy.MANUAL_COPY_TO_CLIPBOARD -> 
                "✅ Event details copied to clipboard!"
        }
    }

    /**
     * Detects and reports available calendar apps for troubleshooting.
     */
    fun getAvailableCalendarApps(): List<String> {
        val installedApps = getInstalledCalendarApps()
        return installedApps.map { "${it.displayName} (${it.packageName})" }
    }

    /**
     * Validates calendar launch success by checking if the intent was handled.
     */
    private fun validateCalendarLaunchSuccess(intent: Intent): Boolean {
        return try {
            // Check if there are apps that can handle this intent
            val resolveInfos = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
                context.packageManager.queryIntentActivities(
                    intent,
                    PackageManager.ResolveInfoFlags.of(PackageManager.MATCH_DEFAULT_ONLY.toLong())
                )
            } else {
                @Suppress("DEPRECATION")
                context.packageManager.queryIntentActivities(intent, PackageManager.MATCH_DEFAULT_ONLY)
            }
            
            resolveInfos.isNotEmpty()
        } catch (e: Exception) {
            false
        }
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
     * Provides comprehensive error reporting and diagnostics.
     */
    fun generateErrorReport(result: ParseResult, launchResult: LaunchResult): String {
        return buildString {
            appendLine("=== Calendar Launch Error Report ===")
            appendLine("Timestamp: ${Date()}")
            appendLine()
            
            appendLine("Launch Result:")
            appendLine("- Success: ${launchResult.success}")
            appendLine("- Strategy: ${launchResult.strategy}")
            appendLine("- App Used: ${launchResult.appUsed ?: "None"}")
            appendLine("- Error: ${launchResult.errorMessage ?: "None"}")
            appendLine()
            
            appendLine("Parse Result:")
            appendLine("- Title: ${result.title ?: "None"}")
            appendLine("- Start Time: ${result.startDateTime ?: "None"}")
            appendLine("- End Time: ${result.endDateTime ?: "None"}")
            appendLine("- Location: ${result.location ?: "None"}")
            appendLine("- All Day: ${result.allDay}")
            appendLine("- Confidence: ${(result.confidenceScore * 100).toInt()}%")
            appendLine()
            
            appendLine("System Information:")
            appendLine("- Android Version: ${Build.VERSION.RELEASE} (API ${Build.VERSION.SDK_INT})")
            appendLine("- Device: ${Build.MANUFACTURER} ${Build.MODEL}")
            appendLine()
            
            appendLine("Available Calendar Apps:")
            val availableApps = getAvailableCalendarApps()
            if (availableApps.isEmpty()) {
                appendLine("- None detected")
            } else {
                availableApps.forEach { app ->
                    appendLine("- $app")
                }
            }
            
            appendLine()
            appendLine("Alternative Strategies Available:")
            launchResult.alternativesAvailable.forEach { strategy ->
                appendLine("- $strategy")
            }
        }
    }
    
    private fun showSuccessMessage(message: String) {
        if (config.showSuccessMessages) {
            Toast.makeText(context, message, Toast.LENGTH_SHORT).show()
        }
    }
    
    private fun showErrorMessage(message: String) {
        Toast.makeText(context, message, Toast.LENGTH_LONG).show()
    }

    /**
     * Extension function to capitalize first letter of string.
     */
    private fun String.capitalize(): String {
        return if (isEmpty()) this else this[0].uppercaseChar() + substring(1)
    }

    /**
     * Extension function to repeat string (for formatting).
     */
    private operator fun String.times(count: Int): String {
        return this.repeat(count)
    }
}