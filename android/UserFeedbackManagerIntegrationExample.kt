package com.jacolabs.calendar

import android.content.Context
import android.util.Log
import androidx.compose.foundation.layout.*
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.lifecycle.LifecycleCoroutineScope
import kotlinx.coroutines.launch

/**
 * Integration example showing how to integrate UserFeedbackManager with MainActivity
 * and the existing error handling workflow.
 */

/**
 * Enhanced version of the main parsing function that integrates UserFeedbackManager
 * for comprehensive user feedback during error scenarios.
 */
suspend fun parseTextWithUserFeedback(
    text: String,
    context: Context,
    apiService: ApiService,
    lifecycleScope: LifecycleCoroutineScope,
    onResult: (ParseResult?) -> Unit,
    onError: (String) -> Unit
) {
    // Initialize managers
    val userFeedbackManager = UserFeedbackManager(context)
    val confidenceValidator = ConfidenceValidator(context)
    val errorHandlingManager = ErrorHandlingManager(context)
    
    try {
        Log.d("ParseWithFeedback", "Starting text parsing with user feedback integration")
        
        // Attempt to parse the text
        val result = try {
            apiService.parseText(text)
        } catch (e: ApiException) {
            Log.w("ParseWithFeedback", "API exception occurred", e)
            
            // Handle API exception with user feedback
            val errorResult = errorHandlingManager.handleApiException(e, text)
            
            when (errorResult.actionRequired) {
                ErrorHandlingManager.UserAction.RETRY_WITH_BETTER_TEXT -> {
                    userFeedbackManager.showErrorMessage("Please try rephrasing your text with clearer date and time information")
                    onError("Please improve the input text and try again")
                    return
                }
                
                ErrorHandlingManager.UserAction.ENABLE_NETWORK_CONNECTION -> {
                    userFeedbackManager.showNetworkErrorDialog(
                        errorType = errorHandlingManager.categorizeError(e),
                        retryAction = {
                            lifecycleScope.launch {
                                parseTextWithUserFeedback(text, context, apiService, lifecycleScope, onResult, onError)
                            }
                        },
                        offlineAction = {
                            lifecycleScope.launch {
                                val offlineResult = errorHandlingManager.createOfflineEvent(text)
                                handleParseResult(offlineResult, text, context, userFeedbackManager, confidenceValidator, onResult, onError)
                            }
                        }
                    )
                    return
                }
                
                else -> {
                    // Use recovered result if available
                    if (errorResult.recoveredResult != null) {
                        handleParseResult(errorResult.recoveredResult, text, context, userFeedbackManager, confidenceValidator, onResult, onError)
                        return
                    } else {
                        userFeedbackManager.showErrorMessage(errorResult.userMessage)
                        onError(errorResult.userMessage)
                        return
                    }
                }
            }
        }
        
        // Handle successful parsing result
        handleParseResult(result, text, context, userFeedbackManager, confidenceValidator, onResult, onError)
        
    } catch (e: Exception) {
        Log.e("ParseWithFeedback", "Unexpected error during parsing", e)
        
        // Handle unexpected errors
        val errorContext = ErrorHandlingManager.ErrorContext(
            errorType = ErrorHandlingManager.ErrorType.UNKNOWN_ERROR,
            originalText = text,
            exception = e
        )
        
        val errorResult = errorHandlingManager.handleError(errorContext)
        
        if (errorResult.recoveredResult != null) {
            handleParseResult(errorResult.recoveredResult, text, context, userFeedbackManager, confidenceValidator, onResult, onError)
        } else {
            userFeedbackManager.showErrorMessage("An unexpected error occurred. Please try again.")
            onError("Unexpected error occurred")
        }
    }
}

/**
 * Handles parse results with confidence validation and user feedback
 */
private suspend fun handleParseResult(
    result: ParseResult,
    originalText: String,
    context: Context,
    userFeedbackManager: UserFeedbackManager,
    confidenceValidator: ConfidenceValidator,
    onResult: (ParseResult?) -> Unit,
    onError: (String) -> Unit
) {
    Log.d("ParseWithFeedback", "Handling parse result with confidence: ${result.confidenceScore}")
    
    // Assess confidence
    val assessment = confidenceValidator.assessConfidence(result, originalText)
    
    when (assessment.recommendation) {
        ConfidenceValidator.UserRecommendation.PROCEED_CONFIDENTLY -> {
            // High confidence - proceed directly
            userFeedbackManager.showSuccessMessage("Event details extracted successfully!")
            onResult(result)
        }
        
        ConfidenceValidator.UserRecommendation.PROCEED_WITH_CAUTION,
        ConfidenceValidator.UserRecommendation.SUGGEST_IMPROVEMENTS -> {
            // Medium/low confidence - show warning and get user decision
            val userDecision = userFeedbackManager.showConfidenceWarning(assessment)
            
            if (userDecision) {
                userFeedbackManager.showSuccessMessage("Event created with available information")
                onResult(result)
            } else {
                userFeedbackManager.showErrorMessage("Event creation cancelled. Try improving the input text.")
                onError("User cancelled due to low confidence")
            }
        }
        
        ConfidenceValidator.UserRecommendation.RECOMMEND_MANUAL_ENTRY -> {
            // Very low confidence - recommend manual entry
            userFeedbackManager.showErrorMessage("Unable to extract reliable event information. Please create the event manually.")
            onError("Confidence too low for automatic creation")
        }
        
        ConfidenceValidator.UserRecommendation.BLOCK_CREATION -> {
            // Critical issues - block creation
            userFeedbackManager.showErrorMessage("Missing critical information. Please provide more details and try again.")
            onError("Missing critical event information")
        }
    }
}

/**
 * Enhanced calendar event creation with fallback handling
 */
suspend fun createCalendarEventWithFallbacks(
    result: ParseResult,
    context: Context,
    calendarIntentHelper: CalendarIntentHelper,
    userFeedbackManager: UserFeedbackManager,
    onSuccess: () -> Unit,
    onError: (String) -> Unit
) {
    try {
        Log.d("CreateWithFallbacks", "Attempting to create calendar event")
        
        // Try to create calendar event
        val success = calendarIntentHelper.createCalendarEvent(result)
        
        if (success) {
            userFeedbackManager.showSuccessMessage("Calendar event created successfully!")
            onSuccess()
        } else {
            // Calendar launch failed - show fallback options
            val alternatives = listOf("Google Calendar", "Outlook", "Samsung Calendar")
            userFeedbackManager.showCalendarNotFoundDialog(result, alternatives)
        }
        
    } catch (e: Exception) {
        Log.e("CreateWithFallbacks", "Error creating calendar event", e)
        
        // Show calendar fallback dialog
        val alternatives = listOf("Google Calendar", "Outlook", "Samsung Calendar")
        userFeedbackManager.showCalendarNotFoundDialog(result, alternatives)
    }
}

/**
 * Composable function that demonstrates integration with MainActivity
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun EnhancedMainScreen(
    apiService: ApiService,
    lifecycleScope: LifecycleCoroutineScope
) {
    val context = LocalContext.current
    val userFeedbackManager = remember { UserFeedbackManager(context) }
    val calendarIntentHelper = remember { CalendarIntentHelper(context) }
    
    var textInput by remember { mutableStateOf("") }
    var isLoading by remember { mutableStateOf(false) }
    var parseResult by remember { mutableStateOf<ParseResult?>(null) }
    var errorMessage by remember { mutableStateOf<String?>(null) }
    
    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(24.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        
        // Header
        Icon(
            imageVector = Icons.Default.Event,
            contentDescription = "Calendar Event",
            modifier = Modifier.size(64.dp),
            tint = MaterialTheme.colorScheme.primary
        )
        
        Text(
            text = "Enhanced Calendar Event Creator",
            style = MaterialTheme.typography.headlineMedium
        )
        
        Text(
            text = "With intelligent error handling and user feedback",
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )
        
        // Text input
        OutlinedTextField(
            value = textInput,
            onValueChange = { textInput = it },
            label = { Text("Enter event text") },
            placeholder = { Text("e.g., Meeting with John tomorrow at 2pm") },
            modifier = Modifier.fillMaxWidth(),
            enabled = !isLoading,
            minLines = 3
        )
        
        // Parse button
        Button(
            onClick = {
                if (textInput.isNotBlank()) {
                    isLoading = true
                    errorMessage = null
                    parseResult = null
                    
                    lifecycleScope.launch {
                        parseTextWithUserFeedback(
                            text = textInput,
                            context = context,
                            apiService = apiService,
                            lifecycleScope = lifecycleScope,
                            onResult = { result ->
                                parseResult = result
                                isLoading = false
                            },
                            onError = { error ->
                                errorMessage = error
                                isLoading = false
                            }
                        )
                    }
                }
            },
            modifier = Modifier.fillMaxWidth(),
            enabled = !isLoading && textInput.isNotBlank()
        ) {
            if (isLoading) {
                CircularProgressIndicator(
                    modifier = Modifier.size(16.dp),
                    strokeWidth = 2.dp
                )
                Spacer(modifier = Modifier.width(8.dp))
                Text("Processing...")
            } else {
                Icon(Icons.Default.Psychology, contentDescription = null)
                Spacer(modifier = Modifier.width(8.dp))
                Text("Parse Event with AI")
            }
        }
        
        // Results display
        parseResult?.let { result ->
            Card(
                modifier = Modifier.fillMaxWidth(),
                elevation = CardDefaults.cardElevation(defaultElevation = 4.dp)
            ) {
                Column(
                    modifier = Modifier.padding(16.dp)
                ) {
                    Text(
                        text = "Parsed Event Details",
                        style = MaterialTheme.typography.titleMedium
                    )
                    
                    Spacer(modifier = Modifier.height(8.dp))
                    
                    // Confidence indicator
                    val confidencePercentage = (result.confidenceScore * 100).toInt()
                    val confidenceColor = when {
                        result.confidenceScore >= 0.7 -> MaterialTheme.colorScheme.primary
                        result.confidenceScore >= 0.3 -> MaterialTheme.colorScheme.tertiary
                        else -> MaterialTheme.colorScheme.error
                    }
                    
                    Row(
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Icon(
                            imageVector = when {
                                result.confidenceScore >= 0.7 -> Icons.Default.CheckCircle
                                result.confidenceScore >= 0.3 -> Icons.Default.Warning
                                else -> Icons.Default.Error
                            },
                            contentDescription = null,
                            tint = confidenceColor,
                            modifier = Modifier.size(16.dp)
                        )
                        Spacer(modifier = Modifier.width(8.dp))
                        Text(
                            text = "Confidence: $confidencePercentage%",
                            color = confidenceColor,
                            style = MaterialTheme.typography.bodyMedium
                        )
                    }
                    
                    Spacer(modifier = Modifier.height(12.dp))
                    
                    // Event details
                    result.title?.let {
                        Text("Title: $it", style = MaterialTheme.typography.bodyMedium)
                    }
                    result.startDateTime?.let {
                        Text("Start: $it", style = MaterialTheme.typography.bodyMedium)
                    }
                    result.endDateTime?.let {
                        Text("End: $it", style = MaterialTheme.typography.bodyMedium)
                    }
                    result.location?.let {
                        Text("Location: $it", style = MaterialTheme.typography.bodyMedium)
                    }
                    
                    Spacer(modifier = Modifier.height(16.dp))
                    
                    // Create event button
                    Button(
                        onClick = {
                            lifecycleScope.launch {
                                createCalendarEventWithFallbacks(
                                    result = result,
                                    context = context,
                                    calendarIntentHelper = calendarIntentHelper,
                                    userFeedbackManager = userFeedbackManager,
                                    onSuccess = {
                                        // Event created successfully
                                        parseResult = null
                                        textInput = ""
                                    },
                                    onError = { error ->
                                        errorMessage = error
                                    }
                                )
                            }
                        },
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Icon(Icons.Default.Event, contentDescription = null)
                        Spacer(modifier = Modifier.width(8.dp))
                        Text("Create Calendar Event")
                    }
                }
            }
        }
        
        // Error display
        errorMessage?.let { error ->
            Card(
                modifier = Modifier.fillMaxWidth(),
                colors = CardDefaults.cardColors(
                    containerColor = MaterialTheme.colorScheme.errorContainer
                )
            ) {
                Row(
                    modifier = Modifier.padding(16.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Icon(
                        imageVector = Icons.Default.Error,
                        contentDescription = null,
                        tint = MaterialTheme.colorScheme.error
                    )
                    Spacer(modifier = Modifier.width(8.dp))
                    Text(
                        text = error,
                        color = MaterialTheme.colorScheme.onErrorContainer,
                        style = MaterialTheme.typography.bodyMedium
                    )
                }
            }
        }
    }
    
    // Render feedback dialogs
    userFeedbackManager.FeedbackDialogRenderer()
}

/**
 * Example of how to integrate UserFeedbackManager with existing error handling workflows
 */
class UserFeedbackIntegrationHelper(
    private val context: Context
) {
    private val userFeedbackManager = UserFeedbackManager(context)
    private val errorHandlingManager = ErrorHandlingManager(context)
    private val confidenceValidator = ConfidenceValidator(context)
    
    /**
     * Comprehensive error handling with user feedback
     */
    suspend fun handleErrorWithFeedback(
        errorContext: ErrorHandlingManager.ErrorContext,
        retryAction: (suspend () -> Unit)? = null,
        offlineAction: (suspend () -> Unit)? = null
    ): ErrorHandlingManager.ErrorHandlingResult {
        
        val errorResult = errorHandlingManager.handleError(errorContext)
        
        // Provide user feedback based on the error result
        when (errorResult.actionRequired) {
            ErrorHandlingManager.UserAction.CONFIRM_LOW_CONFIDENCE_RESULT -> {
                errorContext.apiResponse?.let { result ->
                    val assessment = confidenceValidator.assessConfidence(result, errorContext.originalText)
                    val userDecision = userFeedbackManager.showConfidenceWarning(assessment)
                    
                    return if (userDecision) {
                        errorResult.copy(success = true, recoveredResult = result)
                    } else {
                        errorResult.copy(success = false)
                    }
                }
            }
            
            ErrorHandlingManager.UserAction.ENABLE_NETWORK_CONNECTION -> {
                if (retryAction != null) {
                    userFeedbackManager.showNetworkErrorDialog(
                        errorType = errorContext.errorType,
                        retryAction = retryAction,
                        offlineAction = offlineAction
                    )
                }
            }
            
            ErrorHandlingManager.UserAction.CHOOSE_ALTERNATIVE_CALENDAR -> {
                errorContext.apiResponse?.let { result ->
                    val alternatives = listOf("Google Calendar", "Outlook", "Samsung Calendar")
                    userFeedbackManager.showCalendarNotFoundDialog(result, alternatives)
                }
            }
            
            ErrorHandlingManager.UserAction.RETRY_WITH_BETTER_TEXT -> {
                userFeedbackManager.showErrorMessage(
                    "Please try rephrasing with clearer date, time, and event details"
                )
            }
            
            ErrorHandlingManager.UserAction.MANUAL_EVENT_CREATION -> {
                userFeedbackManager.showErrorMessage(
                    "Unable to extract event information. Please create the event manually."
                )
            }
            
            else -> {
                // Handle other cases or show generic feedback
                if (!errorResult.success) {
                    userFeedbackManager.showErrorMessage(errorResult.userMessage)
                } else {
                    userFeedbackManager.showSuccessMessage("Operation completed successfully")
                }
            }
        }
        
        return errorResult
    }
    
    /**
     * Gets the UserFeedbackManager instance for direct use
     */
    fun getFeedbackManager(): UserFeedbackManager = userFeedbackManager
}