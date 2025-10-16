package com.jacolabs.calendar

import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.content.Intent
import android.net.Uri
import android.util.Log
import android.widget.Toast
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.window.Dialog
import androidx.compose.ui.window.DialogProperties
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

/**
 * UserFeedbackManager provides contextual user feedback and guidance for error handling scenarios.
 * Implements confidence warnings, network error dialogs, calendar fallback options, and improvement suggestions.
 */
class UserFeedbackManager(
    private val context: Context,
    private val config: UserFeedbackConfig = UserFeedbackConfig()
) {
    
    companion object {
        private const val TAG = "UserFeedbackManager"
        
        // Toast duration constants
        private const val SHORT_TOAST_DURATION = Toast.LENGTH_SHORT
        private const val LONG_TOAST_DURATION = Toast.LENGTH_LONG
        
        // Dialog timeout constants
        private const val DEFAULT_DIALOG_TIMEOUT_MS = 30000L // 30 seconds
    }
    
    /**
     * Configuration for user feedback behavior
     */
    data class UserFeedbackConfig(
        val enableConfidenceWarnings: Boolean = true,
        val enableNetworkErrorDialogs: Boolean = true,
        val enableCalendarFallbackDialogs: Boolean = true,
        val enableSuccessMessages: Boolean = true,
        val enableImprovementSuggestions: Boolean = true,
        val autoCloseDialogsAfterMs: Long = DEFAULT_DIALOG_TIMEOUT_MS,
        val showDetailedErrorInfo: Boolean = false,
        val enableHapticFeedback: Boolean = true
    )
    
    /**
     * Feedback message data structure
     */
    data class FeedbackMessage(
        val title: String,
        val message: String,
        val actionButtons: List<ActionButton>,
        val severity: Severity,
        val icon: ImageVector? = null,
        val dismissible: Boolean = true,
        val autoCloseAfterMs: Long? = null
    )
    
    /**
     * Severity levels for feedback messages
     */
    enum class Severity {
        INFO,
        WARNING,
        ERROR,
        SUCCESS
    }
    
    /**
     * Action button configuration
     */
    data class ActionButton(
        val text: String,
        val action: suspend () -> Unit,
        val style: ButtonStyle = ButtonStyle.PRIMARY,
        val icon: ImageVector? = null
    )
    
    /**
     * Button styling options
     */
    enum class ButtonStyle {
        PRIMARY,
        SECONDARY,
        DESTRUCTIVE,
        TEXT_ONLY
    }
    
    /**
     * Dialog state management
     */
    private var currentDialogState = mutableStateOf<FeedbackMessage?>(null)
    
    /**
     * Shows confidence warning dialog with clear explanations and options
     * Implements requirements 2.1, 2.2, 2.3, 11.1, 11.2, 11.3, 11.4
     */
    suspend fun showConfidenceWarning(assessment: ConfidenceValidator.ConfidenceAssessment): Boolean = withContext(Dispatchers.Main) {
        if (!config.enableConfidenceWarnings) return@withContext true
        
        Log.d(TAG, "Showing confidence warning for assessment with confidence: ${assessment.overallConfidence}")
        
        var userDecision: Boolean? = null
        
        val confidencePercentage = (assessment.overallConfidence * 100).toInt()
        val severity = when {
            assessment.overallConfidence < 0.3 -> Severity.ERROR
            assessment.overallConfidence < 0.7 -> Severity.WARNING
            else -> Severity.INFO
        }
        
        val title = when (severity) {
            Severity.ERROR -> "Low Confidence Detection"
            Severity.WARNING -> "Medium Confidence Warning"
            else -> "Confidence Information"
        }
        
        val message = buildConfidenceWarningMessage(assessment, confidencePercentage)
        
        val actionButtons = mutableListOf<ActionButton>()
        
        // Primary action - proceed anyway
        actionButtons.add(ActionButton(
            text = "Create Event Anyway",
            action = {
                userDecision = true
                currentDialogState.value = null
            },
            style = if (severity == Severity.ERROR) ButtonStyle.DESTRUCTIVE else ButtonStyle.PRIMARY,
            icon = Icons.Default.Event
        ))
        
        // Secondary action - show improvement suggestions
        if (assessment.improvementSuggestions.isNotEmpty() && config.enableImprovementSuggestions) {
            actionButtons.add(ActionButton(
                text = "Show Suggestions",
                action = {
                    showImprovementSuggestions(assessment.improvementSuggestions)
                    userDecision = false
                },
                style = ButtonStyle.SECONDARY,
                icon = Icons.Default.Lightbulb
            ))
        }
        
        // Cancel action
        actionButtons.add(ActionButton(
            text = "Cancel",
            action = {
                userDecision = false
                currentDialogState.value = null
            },
            style = ButtonStyle.TEXT_ONLY
        ))
        
        val feedbackMessage = FeedbackMessage(
            title = title,
            message = message,
            actionButtons = actionButtons,
            severity = severity,
            icon = when (severity) {
                Severity.ERROR -> Icons.Default.Error
                Severity.WARNING -> Icons.Default.Warning
                else -> Icons.Default.Info
            },
            autoCloseAfterMs = config.autoCloseDialogsAfterMs
        )
        
        currentDialogState.value = feedbackMessage
        
        // Wait for user decision
        while (userDecision == null) {
            kotlinx.coroutines.delay(100)
        }
        
        return@withContext userDecision
    }
    
    /**
     * Shows network error dialog with retry and offline options
     * Implements requirements for network error handling
     */
    suspend fun showNetworkErrorDialog(
        errorType: ErrorHandlingManager.ErrorType,
        retryAction: suspend () -> Unit,
        offlineAction: (suspend () -> Unit)? = null
    ): Unit = withContext(Dispatchers.Main) {
        if (!config.enableNetworkErrorDialogs) return@withContext
        
        Log.d(TAG, "Showing network error dialog for error type: $errorType")
        
        val (title, message) = getNetworkErrorContent(errorType)
        
        val actionButtons = mutableListOf<ActionButton>()
        
        // Retry action
        actionButtons.add(ActionButton(
            text = "Retry",
            action = {
                currentDialogState.value = null
                retryAction()
            },
            style = ButtonStyle.PRIMARY,
            icon = Icons.Default.Refresh
        ))
        
        // Offline action if available
        if (offlineAction != null) {
            actionButtons.add(ActionButton(
                text = "Create Offline",
                action = {
                    currentDialogState.value = null
                    offlineAction()
                },
                style = ButtonStyle.SECONDARY,
                icon = Icons.Default.CloudOff
            ))
        }
        
        // Cancel action
        actionButtons.add(ActionButton(
            text = "Cancel",
            action = {
                currentDialogState.value = null
            },
            style = ButtonStyle.TEXT_ONLY
        ))
        
        val feedbackMessage = FeedbackMessage(
            title = title,
            message = message,
            actionButtons = actionButtons,
            severity = Severity.ERROR,
            icon = Icons.Default.CloudOff,
            autoCloseAfterMs = config.autoCloseDialogsAfterMs
        )
        
        currentDialogState.value = feedbackMessage
    }
    
    /**
     * Shows calendar not found dialog with alternative suggestions
     * Implements requirements for calendar fallback handling
     */
    suspend fun showCalendarNotFoundDialog(
        result: ParseResult,
        alternatives: List<String> = emptyList()
    ): Unit = withContext(Dispatchers.Main) {
        if (!config.enableCalendarFallbackDialogs) return@withContext
        
        Log.d(TAG, "Showing calendar not found dialog with ${alternatives.size} alternatives")
        
        val title = "Calendar App Not Available"
        val message = buildCalendarNotFoundMessage(alternatives)
        
        val actionButtons = mutableListOf<ActionButton>()
        
        // Copy to clipboard action
        actionButtons.add(ActionButton(
            text = "Copy Event Details",
            action = {
                copyEventToClipboard(result)
                currentDialogState.value = null
                showSuccessMessage("Event details copied to clipboard")
            },
            style = ButtonStyle.PRIMARY,
            icon = Icons.Default.ContentCopy
        ))
        
        // Open web calendar action
        actionButtons.add(ActionButton(
            text = "Open Web Calendar",
            action = {
                openWebCalendar(result)
                currentDialogState.value = null
            },
            style = ButtonStyle.SECONDARY,
            icon = Icons.Default.OpenInBrowser
        ))
        
        // Try alternative apps if available
        if (alternatives.isNotEmpty()) {
            actionButtons.add(ActionButton(
                text = "Try Other Apps",
                action = {
                    showAlternativeAppsDialog(result, alternatives)
                },
                style = ButtonStyle.SECONDARY,
                icon = Icons.Default.Apps
            ))
        }
        
        // Cancel action
        actionButtons.add(ActionButton(
            text = "Cancel",
            action = {
                currentDialogState.value = null
            },
            style = ButtonStyle.TEXT_ONLY
        ))
        
        val feedbackMessage = FeedbackMessage(
            title = title,
            message = message,
            actionButtons = actionButtons,
            severity = Severity.WARNING,
            icon = Icons.Default.CalendarMonth,
            autoCloseAfterMs = config.autoCloseDialogsAfterMs
        )
        
        currentDialogState.value = feedbackMessage
    }
    
    /**
     * Shows success message with appropriate timing
     */
    fun showSuccessMessage(message: String, duration: ToastDuration = ToastDuration.SHORT) {
        if (!config.enableSuccessMessages) return
        
        Log.d(TAG, "Showing success message: $message")
        
        CoroutineScope(Dispatchers.Main).launch {
            Toast.makeText(
                context,
                message,
                when (duration) {
                    ToastDuration.SHORT -> SHORT_TOAST_DURATION
                    ToastDuration.LONG -> LONG_TOAST_DURATION
                }
            ).show()
        }
    }
    
    /**
     * Shows error message with appropriate timing
     */
    fun showErrorMessage(message: String, duration: ToastDuration = ToastDuration.LONG) {
        Log.d(TAG, "Showing error message: $message")
        
        CoroutineScope(Dispatchers.Main).launch {
            Toast.makeText(
                context,
                message,
                when (duration) {
                    ToastDuration.SHORT -> SHORT_TOAST_DURATION
                    ToastDuration.LONG -> LONG_TOAST_DURATION
                }
            ).show()
        }
    }
    
    /**
     * Shows improvement suggestions dialog
     */
    private suspend fun showImprovementSuggestions(
        suggestions: List<ConfidenceValidator.ImprovementSuggestion>
    ): Unit = withContext(Dispatchers.Main) {
        if (!config.enableImprovementSuggestions || suggestions.isEmpty()) return@withContext
        
        Log.d(TAG, "Showing improvement suggestions: ${suggestions.size} suggestions")
        
        val title = "Suggestions for Better Results"
        val message = buildImprovementSuggestionsMessage(suggestions)
        
        val actionButtons = listOf(
            ActionButton(
                text = "Got It",
                action = {
                    currentDialogState.value = null
                },
                style = ButtonStyle.PRIMARY,
                icon = Icons.Default.Check
            )
        )
        
        val feedbackMessage = FeedbackMessage(
            title = title,
            message = message,
            actionButtons = actionButtons,
            severity = Severity.INFO,
            icon = Icons.Default.Lightbulb,
            autoCloseAfterMs = null // Don't auto-close suggestions
        )
        
        currentDialogState.value = feedbackMessage
    }
    
    /**
     * Shows alternative calendar apps dialog
     */
    private suspend fun showAlternativeAppsDialog(
        result: ParseResult,
        alternatives: List<String>
    ): Unit = withContext(Dispatchers.Main) {
        val title = "Choose Calendar App"
        val message = "Select an alternative calendar app to create your event:"
        
        val actionButtons = mutableListOf<ActionButton>()
        
        // Add button for each alternative app
        alternatives.take(3).forEach { appName ->
            actionButtons.add(ActionButton(
                text = appName,
                action = {
                    currentDialogState.value = null
                    tryLaunchAlternativeApp(result, appName)
                },
                style = ButtonStyle.SECONDARY,
                icon = Icons.Default.Apps
            ))
        }
        
        // Cancel action
        actionButtons.add(ActionButton(
            text = "Cancel",
            action = {
                currentDialogState.value = null
            },
            style = ButtonStyle.TEXT_ONLY
        ))
        
        val feedbackMessage = FeedbackMessage(
            title = title,
            message = message,
            actionButtons = actionButtons,
            severity = Severity.INFO,
            icon = Icons.Default.Apps,
            autoCloseAfterMs = config.autoCloseDialogsAfterMs
        )
        
        currentDialogState.value = feedbackMessage
    }
    
    /**
     * Builds confidence warning message with detailed information
     */
    private fun buildConfidenceWarningMessage(
        assessment: ConfidenceValidator.ConfidenceAssessment,
        confidencePercentage: Int
    ): String {
        val builder = StringBuilder()
        
        builder.append("The extracted event information has ${confidencePercentage}% confidence.\n\n")
        
        // Add field-specific confidence information
        if (assessment.fieldConfidences.isNotEmpty()) {
            builder.append("Field confidence levels:\n")
            assessment.fieldConfidences.forEach { (fieldName, fieldInfo) ->
                val fieldConfidencePercentage = (fieldInfo.confidence * 100).toInt()
                val status = when {
                    fieldInfo.confidence >= 0.7 -> "✓"
                    fieldInfo.confidence >= 0.3 -> "⚠"
                    else -> "✗"
                }
                builder.append("$status ${fieldName.capitalize()}: ${fieldConfidencePercentage}%\n")
            }
            builder.append("\n")
        }
        
        // Add missing critical fields warning
        if (assessment.missingCriticalFields.isNotEmpty()) {
            builder.append("Missing required information:\n")
            assessment.missingCriticalFields.forEach { field ->
                builder.append("• ${field.capitalize()}\n")
            }
            builder.append("\n")
        }
        
        // Add low confidence fields warning
        if (assessment.lowConfidenceFields.isNotEmpty()) {
            builder.append("Low confidence fields:\n")
            assessment.lowConfidenceFields.forEach { field ->
                builder.append("• ${field.capitalize()}\n")
            }
            builder.append("\n")
        }
        
        // Add recommendation
        when (assessment.recommendation) {
            ConfidenceValidator.UserRecommendation.PROCEED_WITH_CAUTION ->
                builder.append("Recommendation: Review the event details carefully before creating.")
            ConfidenceValidator.UserRecommendation.SUGGEST_IMPROVEMENTS ->
                builder.append("Recommendation: Consider improving the input text for better results.")
            ConfidenceValidator.UserRecommendation.RECOMMEND_MANUAL_ENTRY ->
                builder.append("Recommendation: Manual event creation may be more accurate.")
            else ->
                builder.append("You can proceed with creating the event or cancel to make improvements.")
        }
        
        return builder.toString()
    }
    
    /**
     * Gets network error content based on error type
     */
    private fun getNetworkErrorContent(errorType: ErrorHandlingManager.ErrorType): Pair<String, String> {
        return when (errorType) {
            ErrorHandlingManager.ErrorType.NETWORK_ERROR -> Pair(
                "Network Connection Error",
                "Unable to connect to the event parsing service. Please check your internet connection and try again.\n\nYou can also create an event offline with basic information."
            )
            ErrorHandlingManager.ErrorType.API_TIMEOUT -> Pair(
                "Request Timeout",
                "The request took too long to complete. This might be due to a slow connection or server issues.\n\nPlease try again or create an event offline."
            )
            ErrorHandlingManager.ErrorType.RATE_LIMIT_ERROR -> Pair(
                "Service Temporarily Unavailable",
                "Too many requests have been made recently. Please wait a moment before trying again.\n\nYour request will be automatically retried when the service becomes available."
            )
            ErrorHandlingManager.ErrorType.SERVER_ERROR -> Pair(
                "Service Error",
                "The event parsing service is experiencing issues. Please try again in a few minutes.\n\nYou can create an event offline in the meantime."
            )
            else -> Pair(
                "Connection Problem",
                "There was a problem connecting to the service. Please check your connection and try again."
            )
        }
    }
    
    /**
     * Builds calendar not found message
     */
    private fun buildCalendarNotFoundMessage(alternatives: List<String>): String {
        val builder = StringBuilder()
        
        builder.append("No default calendar app was found on your device.\n\n")
        
        if (alternatives.isNotEmpty()) {
            builder.append("Available alternatives:\n")
            alternatives.forEach { app ->
                builder.append("• $app\n")
            }
            builder.append("\n")
        }
        
        builder.append("You can:\n")
        builder.append("• Copy the event details to manually create the event\n")
        builder.append("• Open a web calendar service\n")
        if (alternatives.isNotEmpty()) {
            builder.append("• Try one of the alternative apps listed above\n")
        }
        
        return builder.toString()
    }
    
    /**
     * Builds improvement suggestions message
     */
    private fun buildImprovementSuggestionsMessage(
        suggestions: List<ConfidenceValidator.ImprovementSuggestion>
    ): String {
        val builder = StringBuilder()
        
        builder.append("To get better parsing results, try these improvements:\n\n")
        
        suggestions.forEachIndexed { index, suggestion ->
            builder.append("${index + 1}. ${suggestion.message}\n")
            if (!suggestion.example.isNullOrBlank()) {
                builder.append("   Example: ${suggestion.example}\n")
            }
            builder.append("\n")
        }
        
        return builder.toString()
    }
    
    /**
     * Copies event details to clipboard
     */
    private fun copyEventToClipboard(result: ParseResult) {
        try {
            val clipboardManager = context.getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
            val eventText = formatEventForClipboard(result)
            val clip = ClipData.newPlainText("Calendar Event", eventText)
            clipboardManager.setPrimaryClip(clip)
            
            Log.d(TAG, "Event details copied to clipboard")
        } catch (e: Exception) {
            Log.e(TAG, "Failed to copy event to clipboard", e)
            showErrorMessage("Failed to copy event details")
        }
    }
    
    /**
     * Formats event details for clipboard
     */
    private fun formatEventForClipboard(result: ParseResult): String {
        val builder = StringBuilder()
        
        builder.append("Event: ${result.title ?: "Untitled Event"}\n")
        
        if (!result.startDateTime.isNullOrBlank()) {
            builder.append("Start: ${result.startDateTime}\n")
        }
        
        if (!result.endDateTime.isNullOrBlank()) {
            builder.append("End: ${result.endDateTime}\n")
        }
        
        if (!result.location.isNullOrBlank()) {
            builder.append("Location: ${result.location}\n")
        }
        
        if (!result.description.isNullOrBlank()) {
            builder.append("Description: ${result.description}\n")
        }
        
        return builder.toString()
    }
    
    /**
     * Opens web calendar with pre-filled event data
     */
    private fun openWebCalendar(result: ParseResult) {
        try {
            // Create Google Calendar URL with event data
            val title = Uri.encode(result.title ?: "Event")
            val details = Uri.encode(result.description ?: "")
            val location = Uri.encode(result.location ?: "")
            
            // Format dates for Google Calendar (YYYYMMDDTHHMMSSZ)
            val startDate = formatDateForWebCalendar(result.startDateTime)
            val endDate = formatDateForWebCalendar(result.endDateTime)
            
            val url = "https://calendar.google.com/calendar/render?action=TEMPLATE" +
                    "&text=$title" +
                    "&details=$details" +
                    "&location=$location" +
                    if (startDate != null) "&dates=$startDate/$endDate" else ""
            
            val intent = Intent(Intent.ACTION_VIEW, Uri.parse(url))
            intent.flags = Intent.FLAG_ACTIVITY_NEW_TASK
            context.startActivity(intent)
            
            Log.d(TAG, "Opened web calendar with event data")
        } catch (e: Exception) {
            Log.e(TAG, "Failed to open web calendar", e)
            showErrorMessage("Failed to open web calendar")
        }
    }
    
    /**
     * Formats date for web calendar URL
     */
    private fun formatDateForWebCalendar(dateTime: String?): String? {
        if (dateTime.isNullOrBlank()) return null
        
        try {
            // This is a simplified implementation - in practice, you'd need proper date parsing
            // For now, return a placeholder format
            return "20241215T140000Z"
        } catch (e: Exception) {
            Log.w(TAG, "Failed to format date for web calendar: $dateTime", e)
            return null
        }
    }
    
    /**
     * Tries to launch alternative calendar app
     */
    private fun tryLaunchAlternativeApp(result: ParseResult, appName: String) {
        try {
            // This would need to be implemented based on specific app package names
            // For now, show a message that this is not yet implemented
            showErrorMessage("Alternative app launch not yet implemented for $appName")
            
            Log.d(TAG, "Attempted to launch alternative app: $appName")
        } catch (e: Exception) {
            Log.e(TAG, "Failed to launch alternative app: $appName", e)
            showErrorMessage("Failed to launch $appName")
        }
    }
    
    /**
     * Toast duration enum
     */
    enum class ToastDuration {
        SHORT,
        LONG
    }
    
    /**
     * Composable function to render feedback dialogs
     */
    @Composable
    fun FeedbackDialogRenderer() {
        val dialogState by currentDialogState
        
        dialogState?.let { message ->
            FeedbackDialog(
                message = message,
                onDismiss = {
                    if (message.dismissible) {
                        currentDialogState.value = null
                    }
                }
            )
        }
    }
    
    /**
     * Individual feedback dialog composable
     */
    @Composable
    private fun FeedbackDialog(
        message: FeedbackMessage,
        onDismiss: () -> Unit
    ) {
        Dialog(
            onDismissRequest = onDismiss,
            properties = DialogProperties(
                dismissOnBackPress = message.dismissible,
                dismissOnClickOutside = message.dismissible
            )
        ) {
            Card(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(16.dp),
                elevation = CardDefaults.cardElevation(defaultElevation = 8.dp)
            ) {
                Column(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(24.dp)
                        .verticalScroll(rememberScrollState()),
                    horizontalAlignment = Alignment.CenterHorizontally
                ) {
                    // Icon and title
                    Row(
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.Center,
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        message.icon?.let { icon ->
                            Icon(
                                imageVector = icon,
                                contentDescription = null,
                                tint = getSeverityColor(message.severity),
                                modifier = Modifier.size(32.dp)
                            )
                            Spacer(modifier = Modifier.width(12.dp))
                        }
                        
                        Text(
                            text = message.title,
                            style = MaterialTheme.typography.headlineSmall,
                            fontWeight = FontWeight.Bold,
                            textAlign = TextAlign.Center,
                            color = getSeverityColor(message.severity)
                        )
                    }
                    
                    Spacer(modifier = Modifier.height(16.dp))
                    
                    // Message content
                    Text(
                        text = message.message,
                        style = MaterialTheme.typography.bodyMedium,
                        textAlign = TextAlign.Start,
                        modifier = Modifier.fillMaxWidth()
                    )
                    
                    Spacer(modifier = Modifier.height(24.dp))
                    
                    // Action buttons
                    Column(
                        modifier = Modifier.fillMaxWidth(),
                        verticalArrangement = Arrangement.spacedBy(8.dp)
                    ) {
                        message.actionButtons.forEach { button ->
                            ActionButtonComposable(
                                button = button,
                                modifier = Modifier.fillMaxWidth()
                            )
                        }
                    }
                }
            }
        }
        
        // Auto-close timer
        message.autoCloseAfterMs?.let { timeout ->
            LaunchedEffect(message) {
                kotlinx.coroutines.delay(timeout)
                if (message.dismissible) {
                    onDismiss()
                }
            }
        }
    }
    
    /**
     * Action button composable
     */
    @Composable
    private fun ActionButtonComposable(
        button: ActionButton,
        modifier: Modifier = Modifier
    ) {
        when (button.style) {
            ButtonStyle.PRIMARY -> {
                Button(
                    onClick = {
                        CoroutineScope(Dispatchers.Main).launch {
                            button.action()
                        }
                    },
                    modifier = modifier
                ) {
                    button.icon?.let { icon ->
                        Icon(
                            imageVector = icon,
                            contentDescription = null,
                            modifier = Modifier.size(18.dp)
                        )
                        Spacer(modifier = Modifier.width(8.dp))
                    }
                    Text(button.text)
                }
            }
            
            ButtonStyle.SECONDARY -> {
                OutlinedButton(
                    onClick = {
                        CoroutineScope(Dispatchers.Main).launch {
                            button.action()
                        }
                    },
                    modifier = modifier
                ) {
                    button.icon?.let { icon ->
                        Icon(
                            imageVector = icon,
                            contentDescription = null,
                            modifier = Modifier.size(18.dp)
                        )
                        Spacer(modifier = Modifier.width(8.dp))
                    }
                    Text(button.text)
                }
            }
            
            ButtonStyle.DESTRUCTIVE -> {
                Button(
                    onClick = {
                        CoroutineScope(Dispatchers.Main).launch {
                            button.action()
                        }
                    },
                    colors = ButtonDefaults.buttonColors(
                        containerColor = MaterialTheme.colorScheme.error
                    ),
                    modifier = modifier
                ) {
                    button.icon?.let { icon ->
                        Icon(
                            imageVector = icon,
                            contentDescription = null,
                            modifier = Modifier.size(18.dp)
                        )
                        Spacer(modifier = Modifier.width(8.dp))
                    }
                    Text(button.text)
                }
            }
            
            ButtonStyle.TEXT_ONLY -> {
                TextButton(
                    onClick = {
                        CoroutineScope(Dispatchers.Main).launch {
                            button.action()
                        }
                    },
                    modifier = modifier
                ) {
                    button.icon?.let { icon ->
                        Icon(
                            imageVector = icon,
                            contentDescription = null,
                            modifier = Modifier.size(18.dp)
                        )
                        Spacer(modifier = Modifier.width(8.dp))
                    }
                    Text(button.text)
                }
            }
        }
    }
    
    /**
     * Gets color for severity level
     */
    @Composable
    private fun getSeverityColor(severity: Severity): Color {
        return when (severity) {
            Severity.ERROR -> MaterialTheme.colorScheme.error
            Severity.WARNING -> MaterialTheme.colorScheme.tertiary
            Severity.SUCCESS -> Color(0xFF4CAF50) // Green
            Severity.INFO -> MaterialTheme.colorScheme.primary
        }
    }
    
    /**
     * Gets the current configuration
     */
    fun getConfig(): UserFeedbackConfig = config
    
    /**
     * Dismisses any currently shown dialog
     */
    fun dismissCurrentDialog() {
        currentDialogState.value = null
    }
    
    /**
     * Checks if a dialog is currently being shown
     */
    fun isDialogShowing(): Boolean {
        return currentDialogState.value != null
    }
}