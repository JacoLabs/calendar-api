package com.jacolabs.calendar

import android.content.Intent
import android.os.Bundle
import android.provider.CalendarContract
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Event
import androidx.compose.material.icons.filled.Info
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import android.content.Context
import androidx.lifecycle.lifecycleScope
import kotlinx.coroutines.launch
import java.text.SimpleDateFormat
import java.util.*

/**
 * Main activity with text input interface for testing API integration.
 * Enhanced with comprehensive error handling and fallback mechanisms.
 */
class MainActivity : ComponentActivity() {
    
    private lateinit var apiService: ApiService
    private lateinit var errorHandlingManager: ErrorHandlingManager
    private lateinit var confidenceValidator: ConfidenceValidator
    private lateinit var userFeedbackManager: UserFeedbackManager
    
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        
        // Initialize services with error handling integration
        apiService = ApiService(this)
        errorHandlingManager = ErrorHandlingManager(this)
        confidenceValidator = ConfidenceValidator(this)
        userFeedbackManager = UserFeedbackManager(this)
        
        setContent {
            MaterialTheme {
                Surface(
                    modifier = Modifier.fillMaxSize(),
                    color = MaterialTheme.colorScheme.background
                ) {
                    MainScreen(
                        apiService = apiService,
                        errorHandlingManager = errorHandlingManager,
                        confidenceValidator = confidenceValidator,
                        userFeedbackManager = userFeedbackManager,
                        lifecycleScope = lifecycleScope
                    )
                }
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun MainScreen(
    apiService: ApiService,
    errorHandlingManager: ErrorHandlingManager,
    confidenceValidator: ConfidenceValidator,
    userFeedbackManager: UserFeedbackManager,
    lifecycleScope: androidx.lifecycle.LifecycleCoroutineScope
) {
    var textInput by remember { mutableStateOf("") }
    var isLoading by remember { mutableStateOf(false) }
    var parseResult by remember { mutableStateOf<ParseResult?>(null) }
    var errorMessage by remember { mutableStateOf<String?>(null) }
    var clipboardText by remember { mutableStateOf<String?>(null) }
    var showTimeConfirmBanner by remember { mutableStateOf(false) }
    var confidenceAssessment by remember { mutableStateOf<ConfidenceValidator.ConfidenceAssessment?>(null) }
    var showConfidenceWarning by remember { mutableStateOf(false) }
    var retryCount by remember { mutableStateOf(0) }
    var isRetrying by remember { mutableStateOf(false) }
    var fallbackResult by remember { mutableStateOf<ParseResult?>(null) }
    var showFallbackConfirmation by remember { mutableStateOf(false) }
    val context = LocalContext.current
    
    // Check clipboard content on composition
    LaunchedEffect(Unit) {
        clipboardText = getClipboardText(context)
    }
    
    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(24.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Top
    ) {
        
        Spacer(modifier = Modifier.height(32.dp))
        
        Icon(
            imageVector = Icons.Default.Event,
            contentDescription = "Calendar Event",
            modifier = Modifier.size(64.dp),
            tint = MaterialTheme.colorScheme.primary
        )
        
        Spacer(modifier = Modifier.height(24.dp))
        
        Text(
            text = "Calendar Event Creator",
            style = MaterialTheme.typography.headlineMedium,
            textAlign = TextAlign.Center
        )
        
        Spacer(modifier = Modifier.height(16.dp))
        
        Text(
            text = "Create calendar events from natural language text",
            style = MaterialTheme.typography.bodyLarge,
            textAlign = TextAlign.Center,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )
        
        Spacer(modifier = Modifier.height(32.dp))
        
        // Text input field
        OutlinedTextField(
            value = textInput,
            onValueChange = { newValue ->
                textInput = newValue
                // Clear previous results when user starts typing
                if (parseResult != null || errorMessage != null) {
                    parseResult = null
                    errorMessage = null
                    showTimeConfirmBanner = false
                }
            },
            label = { Text("Enter event text") },
            placeholder = { Text("e.g., Meeting with John tomorrow at 2pm") },
            modifier = Modifier.fillMaxWidth(),
            maxLines = 5,
            enabled = !isLoading
        )
        
        // Paste from Clipboard button (visible when clipboard has text)
        if (!clipboardText.isNullOrBlank() && clipboardText != textInput) {
            Spacer(modifier = Modifier.height(8.dp))
            
            OutlinedButton(
                onClick = {
                    textInput = clipboardText!!
                    // Auto-parse clipboard content
                    parseTextWithErrorHandling(
                        text = clipboardText!!,
                        apiService = apiService,
                        errorHandlingManager = errorHandlingManager,
                        confidenceValidator = confidenceValidator,
                        retryCount = 0,
                        onLoading = { loading -> isLoading = loading },
                        onRetrying = { retrying -> isRetrying = retrying },
                        onSuccess = { result, assessment ->
                            textInput = clipboardText!!
                            parseResult = result
                            confidenceAssessment = assessment
                            showTimeConfirmBanner = hasDefaultTimes(result, clipboardText!!)
                            errorMessage = null
                            
                            // Show confidence warning if needed
                            if (assessment.recommendation == ConfidenceValidator.UserRecommendation.SUGGEST_IMPROVEMENTS ||
                                assessment.recommendation == ConfidenceValidator.UserRecommendation.PROCEED_WITH_CAUTION) {
                                showConfidenceWarning = true
                            }
                        },
                        onFallback = { fallback ->
                            textInput = clipboardText!!
                            fallbackResult = fallback
                            showFallbackConfirmation = true
                        },
                        onError = { error ->
                            textInput = clipboardText!!
                            errorMessage = error
                        },
                        onRetryCountUpdate = { count -> retryCount = count }
                    )
                },
                modifier = Modifier.fillMaxWidth(),
                enabled = !isLoading
            ) {
                Icon(
                    imageVector = Icons.Default.Event,
                    contentDescription = null,
                    modifier = Modifier.size(16.dp)
                )
                Spacer(modifier = Modifier.width(8.dp))
                Text("Paste from Clipboard & Parse")
            }
        }
        
        Spacer(modifier = Modifier.height(16.dp))
        
        // Submit button
        Button(
            onClick = {
                lifecycleScope.launch {
                    parseTextWithErrorHandling(
                        text = textInput,
                        apiService = apiService,
                        errorHandlingManager = errorHandlingManager,
                        confidenceValidator = confidenceValidator,
                        retryCount = retryCount,
                        onLoading = { loading -> isLoading = loading },
                        onRetrying = { retrying -> isRetrying = retrying },
                        onSuccess = { result, assessment ->
                            parseResult = result
                            confidenceAssessment = assessment
                            showTimeConfirmBanner = hasDefaultTimes(result, textInput)
                            errorMessage = null
                            fallbackResult = null
                            showFallbackConfirmation = false
                            
                            // Show confidence warning if needed
                            if (assessment.recommendation == ConfidenceValidator.UserRecommendation.SUGGEST_IMPROVEMENTS ||
                                assessment.recommendation == ConfidenceValidator.UserRecommendation.PROCEED_WITH_CAUTION) {
                                showConfidenceWarning = true
                            }
                        },
                        onFallback = { fallback ->
                            fallbackResult = fallback
                            showFallbackConfirmation = true
                            parseResult = null
                            confidenceAssessment = null
                            errorMessage = null
                        },
                        onError = { error ->
                            errorMessage = error
                            parseResult = null
                            confidenceAssessment = null
                            fallbackResult = null
                            showFallbackConfirmation = false
                        },
                        onRetryCountUpdate = { count -> retryCount = count }
                    )
                }
            },
            modifier = Modifier.fillMaxWidth(),
            enabled = textInput.isNotBlank() && !isLoading && !isRetrying
        ) {
            if (isLoading || isRetrying) {
                CircularProgressIndicator(
                    modifier = Modifier.size(16.dp),
                    color = MaterialTheme.colorScheme.onPrimary
                )
                Spacer(modifier = Modifier.width(8.dp))
            }
            Text(
                when {
                    isRetrying -> "Retrying..."
                    isLoading -> "Processing..."
                    retryCount > 0 -> "Parse Event (Retry ${retryCount + 1})"
                    else -> "Parse Event"
                }
            )
        }
        
        Spacer(modifier = Modifier.height(24.dp))
        
        // Confidence Warning Dialog
        if (showConfidenceWarning && confidenceAssessment != null) {
            ConfidenceWarningCard(
                assessment = confidenceAssessment!!,
                onProceed = {
                    showConfidenceWarning = false
                    // Keep the current result
                },
                onImprove = {
                    showConfidenceWarning = false
                    // Clear results to encourage user to improve text
                    parseResult = null
                    confidenceAssessment = null
                },
                onDismiss = {
                    showConfidenceWarning = false
                }
            )
            Spacer(modifier = Modifier.height(16.dp))
        }
        
        // Fallback Confirmation Dialog
        if (showFallbackConfirmation && fallbackResult != null) {
            FallbackConfirmationCard(
                fallbackResult = fallbackResult!!,
                originalText = textInput,
                onAccept = {
                    parseResult = fallbackResult
                    showFallbackConfirmation = false
                    fallbackResult = null
                },
                onRetry = {
                    showFallbackConfirmation = false
                    fallbackResult = null
                    // Trigger retry with improved text suggestion
                    lifecycleScope.launch {
                        parseTextWithErrorHandling(
                            text = textInput,
                            apiService = apiService,
                            errorHandlingManager = errorHandlingManager,
                            confidenceValidator = confidenceValidator,
                            retryCount = retryCount,
                            onLoading = { loading -> isLoading = loading },
                            onRetrying = { retrying -> isRetrying = retrying },
                            onSuccess = { result, assessment ->
                                parseResult = result
                                confidenceAssessment = assessment
                                showTimeConfirmBanner = hasDefaultTimes(result, textInput)
                                errorMessage = null
                            },
                            onFallback = { fallback ->
                                fallbackResult = fallback
                                showFallbackConfirmation = true
                            },
                            onError = { error ->
                                errorMessage = error
                            },
                            onRetryCountUpdate = { count -> retryCount = count }
                        )
                    }
                },
                onDismiss = {
                    showFallbackConfirmation = false
                    fallbackResult = null
                }
            )
            Spacer(modifier = Modifier.height(16.dp))
        }
        
        // Time confirmation banner
        if (showTimeConfirmBanner) {
            Spacer(modifier = Modifier.height(16.dp))
            Card(
                modifier = Modifier.fillMaxWidth(),
                colors = CardDefaults.cardColors(
                    containerColor = MaterialTheme.colorScheme.tertiaryContainer
                )
            ) {
                Column(
                    modifier = Modifier.padding(16.dp)
                ) {
                    Text(
                        text = "⏰ Default Time Applied",
                        style = MaterialTheme.typography.titleSmall,
                        color = MaterialTheme.colorScheme.onTertiaryContainer
                    )
                    Spacer(modifier = Modifier.height(4.dp))
                    Text(
                        text = "We found a weekday but no specific time, so we set it to 9:00-10:00 AM. You can adjust this in your calendar app.",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onTertiaryContainer
                    )
                }
            }
        }
        
        // Display results with enhanced confidence indicators
        parseResult?.let { result ->
            EnhancedResultCard(
                result = result,
                confidenceAssessment = confidenceAssessment,
                onCreateEvent = { createCalendarEventWithFallback(context, result, errorHandlingManager) },
                onRetry = {
                    // Clear results and suggest improvements
                    parseResult = null
                    confidenceAssessment = null
                    errorMessage = "Please try rephrasing with clearer date, time, and event details."
                }
            )
        }
        
        // Display error message
        errorMessage?.let { error ->
            Spacer(modifier = Modifier.height(16.dp))
            Card(
                modifier = Modifier.fillMaxWidth(),
                colors = CardDefaults.cardColors(
                    containerColor = MaterialTheme.colorScheme.errorContainer
                )
            ) {
                Text(
                    text = error,
                    modifier = Modifier.padding(16.dp),
                    color = MaterialTheme.colorScheme.onErrorContainer,
                    style = MaterialTheme.typography.bodyMedium
                )
            }
        }
        
        Spacer(modifier = Modifier.height(32.dp))
        
        // Instructions card
        Card(
            modifier = Modifier.fillMaxWidth(),
            colors = CardDefaults.cardColors(
                containerColor = MaterialTheme.colorScheme.primaryContainer
            )
        ) {
            Column(
                modifier = Modifier.padding(16.dp)
            ) {
                Row(
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Icon(
                        imageVector = Icons.Default.Info,
                        contentDescription = null,
                        tint = MaterialTheme.colorScheme.onPrimaryContainer
                    )
                    Spacer(modifier = Modifier.width(8.dp))
                    Text(
                        text = "How to Use",
                        style = MaterialTheme.typography.titleMedium,
                        color = MaterialTheme.colorScheme.onPrimaryContainer
                    )
                }
                
                Spacer(modifier = Modifier.height(12.dp))
                
                Text(
                    text = "1. Type or paste text containing event information\n" +
                            "2. Tap 'Parse Event' to extract details\n" +
                            "3. Review the results and tap 'Create Calendar Event'\n\n" +
                            "You can also:\n" +
                            "• Select text in any app and choose 'Create calendar event'\n" +
                            "• Share text to this app from other apps",
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onPrimaryContainer
                )
            }
        }
        
        Spacer(modifier = Modifier.height(16.dp))
        
        Text(
            text = "Examples:\n" +
                    "• \"Meeting with John tomorrow at 2pm\"\n" +
                    "• \"Lunch at The Keg next Friday 12:30\"\n" +
                    "• \"Conference call Monday 10am for 1 hour\"\n" +
                    "• \"Doctor appointment on January 15th at 3:30 PM\"",
            style = MaterialTheme.typography.bodySmall,
            textAlign = TextAlign.Center,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )
        
        Spacer(modifier = Modifier.height(32.dp))
    }
}

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

private fun createCalendarEvent(context: android.content.Context, result: ParseResult) {
    val calendarHelper = CalendarIntentHelper(context)
    calendarHelper.createCalendarEvent(result)
}

private fun getClipboardText(context: Context): String? {
    return try {
        val clipboardManager = context.getSystemService(Context.CLIPBOARD_SERVICE) as android.content.ClipboardManager
        val clip = clipboardManager.primaryClip
        
        if (clip != null && clip.itemCount > 0) {
            val clipText = clip.getItemAt(0).text?.toString()
            if (!clipText.isNullOrBlank() && clipText.length <= 500) {
                clipText
            } else null
        } else null
    } catch (e: Exception) {
        null
    }
}

private fun parseClipboardContent(
    text: String,
    apiService: ApiService,
    lifecycleScope: androidx.lifecycle.LifecycleCoroutineScope,
    context: Context,
    onResult: (ParseResult) -> Unit,
    onError: (String) -> Unit
) {
    lifecycleScope.launch {
        try {
            val timezone = TimeZone.getDefault().id
            val locale = Locale.getDefault().toString()
            val now = Date()
            
            // Use TextMergeHelper for enhanced processing with audit mode
            val textMergeHelper = TextMergeHelper(context)
            val enhancedText = textMergeHelper.enhanceTextForParsing(text)
            val result = apiService.parseText(
                text = enhancedText, 
                timezone = timezone, 
                locale = locale, 
                now = now,
                mode = "audit"
            )
            val finalResult = textMergeHelper.applySaferDefaults(result, enhancedText)
            
            onResult(finalResult)
            
        } catch (e: ApiException) {
            onError(e.message ?: "Failed to process clipboard text")
        } catch (e: Exception) {
            onError("An unexpected error occurred")
        }
    }
}

private fun hasDefaultTimes(result: ParseResult, originalText: String): Boolean {
    // Check if we applied default 9:00 AM time
    val hasWeekday = listOf("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")
        .any { originalText.lowercase().contains(it) }
    
    val hasDefaultTime = result.startDateTime?.contains("09:00:00") == true
    
    return hasWeekday && hasDefaultTime && !originalText.contains("9:00") && !originalText.contains("9am")
}

/**
 * Enhanced text parsing with comprehensive error handling and fallback mechanisms
 */
private suspend fun parseTextWithErrorHandling(
    text: String,
    apiService: ApiService,
    errorHandlingManager: ErrorHandlingManager,
    confidenceValidator: ConfidenceValidator,
    retryCount: Int,
    onLoading: (Boolean) -> Unit,
    onRetrying: (Boolean) -> Unit,
    onSuccess: (ParseResult, ConfidenceValidator.ConfidenceAssessment) -> Unit,
    onFallback: (ParseResult) -> Unit,
    onError: (String) -> Unit,
    onRetryCountUpdate: (Int) -> Unit
) {
    onLoading(true)
    
    try {
        val timezone = TimeZone.getDefault().id
        val locale = Locale.getDefault().toString()
        val now = Date()
        
        val result = apiService.parseText(
            text = text,
            timezone = timezone,
            locale = locale,
            now = now,
            mode = "audit"
        )
        
        // Assess confidence
        val assessment = confidenceValidator.assessConfidence(result, text)
        
        when (assessment.recommendation) {
            ConfidenceValidator.UserRecommendation.PROCEED_CONFIDENTLY,
            ConfidenceValidator.UserRecommendation.PROCEED_WITH_CAUTION -> {
                onSuccess(result, assessment)
            }
            
            ConfidenceValidator.UserRecommendation.SUGGEST_IMPROVEMENTS -> {
                if (assessment.shouldProceed) {
                    onSuccess(result, assessment)
                } else {
                    // Handle as low confidence - offer fallback
                    val errorHandlingResult = errorHandlingManager.handleLowConfidence(
                        result = result,
                        originalText = text,
                        userInteractionAllowed = true
                    )
                    
                    if (errorHandlingResult.success && errorHandlingResult.recoveredResult != null) {
                        onFallback(errorHandlingResult.recoveredResult)
                    } else {
                        onError(errorHandlingResult.userMessage)
                    }
                }
            }
            
            ConfidenceValidator.UserRecommendation.RECOMMEND_MANUAL_ENTRY -> {
                // Create fallback event
                val errorHandlingResult = errorHandlingManager.handleParsingFailure(text)
                if (errorHandlingResult.success && errorHandlingResult.recoveredResult != null) {
                    onFallback(errorHandlingResult.recoveredResult)
                } else {
                    onError(errorHandlingResult.userMessage)
                }
            }
            
            ConfidenceValidator.UserRecommendation.BLOCK_CREATION -> {
                onError("Unable to extract reliable event information. Please try rephrasing with clearer details.")
            }
        }
        
    } catch (e: ApiException) {
        // Handle API exceptions with error handling manager
        val errorHandlingResult = errorHandlingManager.handleApiException(
            exception = e,
            originalText = text,
            retryCount = retryCount,
            networkAvailable = isNetworkAvailable()
        )
        
        when (errorHandlingResult.recoveryStrategy) {
            ErrorHandlingManager.RecoveryStrategy.RETRY_WITH_BACKOFF -> {
                if (retryCount < 3) {
                    onRetrying(true)
                    onRetryCountUpdate(retryCount + 1)
                    
                    // Wait for retry delay
                    kotlinx.coroutines.delay(errorHandlingResult.retryDelayMs)
                    
                    onRetrying(false)
                    
                    // Retry the request
                    parseTextWithErrorHandling(
                        text = text,
                        apiService = apiService,
                        errorHandlingManager = errorHandlingManager,
                        confidenceValidator = confidenceValidator,
                        retryCount = retryCount + 1,
                        onLoading = onLoading,
                        onRetrying = onRetrying,
                        onSuccess = onSuccess,
                        onFallback = onFallback,
                        onError = onError,
                        onRetryCountUpdate = onRetryCountUpdate
                    )
                    return
                } else {
                    // Max retries exceeded, try fallback
                    if (errorHandlingResult.recoveredResult != null) {
                        onFallback(errorHandlingResult.recoveredResult)
                    } else {
                        onError(errorHandlingResult.userMessage)
                    }
                }
            }
            
            ErrorHandlingManager.RecoveryStrategy.FALLBACK_EVENT_CREATION,
            ErrorHandlingManager.RecoveryStrategy.OFFLINE_MODE,
            ErrorHandlingManager.RecoveryStrategy.GRACEFUL_DEGRADATION -> {
                if (errorHandlingResult.success && errorHandlingResult.recoveredResult != null) {
                    onFallback(errorHandlingResult.recoveredResult)
                } else {
                    onError(errorHandlingResult.userMessage)
                }
            }
            
            else -> {
                onError(errorHandlingResult.userMessage)
            }
        }
        
    } catch (e: Exception) {
        // Handle unexpected exceptions
        val errorHandlingResult = errorHandlingManager.handleError(
            ErrorHandlingManager.ErrorContext(
                errorType = errorHandlingManager.categorizeError(e),
                originalText = text,
                exception = e,
                retryCount = retryCount
            )
        )
        
        if (errorHandlingResult.success && errorHandlingResult.recoveredResult != null) {
            onFallback(errorHandlingResult.recoveredResult)
        } else {
            onError(errorHandlingResult.userMessage)
        }
        
    } finally {
        onLoading(false)
        onRetrying(false)
    }
}

/**
 * Check network availability
 */
private fun isNetworkAvailable(): Boolean {
    return try {
        val connectivityManager = android.content.Context.CONNECTIVITY_SERVICE
        true // Simplified for now - in real implementation, check actual network state
    } catch (e: Exception) {
        false
    }
}

/**
 * Enhanced calendar event creation with fallback handling
 */
private fun createCalendarEventWithFallback(
    context: android.content.Context, 
    result: ParseResult,
    errorHandlingManager: ErrorHandlingManager
) {
    try {
        val calendarHelper = CalendarIntentHelper(context)
        calendarHelper.createCalendarEvent(result)
    } catch (e: Exception) {
        // Handle calendar launch failure
        kotlinx.coroutines.CoroutineScope(kotlinx.coroutines.Dispatchers.Main).launch {
            val errorHandlingResult = errorHandlingManager.handleCalendarLaunchFailure(
                result = result,
                exception = e
            )
            
            // The CalendarFallbackManager will handle alternative launch strategies
            // This is a simplified version - the actual implementation would show UI feedback
        }
    }
}{
    try {
        val calendarHelper = CalendarIntentHelper(context)
        calendarHelper.createCalendarEvent(result)
    } catch (e: Exception) {
        // Handle calendar launch failure
        kotlinx.coroutines.CoroutineScope(kotlinx.coroutines.Dispatchers.Main).launch {
            val errorHandlingResult = errorHandlingManager.handleCalendarLaunchFailure(
                result = result,
                exception = e
            )
            
            // The CalendarFallbackManager will handle alternative launch strategies
            // This is a simplified version - the actual implementation would show UI feedback
        }
    }
}

/**
 * Handle API errors with enhanced error information and retry suggestions.
 */
private fun handleApiError(exception: ApiException): String {
    val apiError = exception.apiError
    
    // Use the structured error information for better user experience
    val baseMessage = apiError.userMessage
    val suggestion = apiError.suggestion
    
    val enhancedMessage = buildString {
        append(baseMessage)
        
        // Add suggestion if available
        suggestion?.let { suggestionText ->
            append("\n\n💡 Suggestion: $suggestionText")
        }
        
        // Add retry information for retryable errors
        if (apiError.retryable) {
            apiError.retryAfterSeconds?.let { seconds ->
                append("\n\n⏱️ You can try again in $seconds seconds.")
            } ?: run {
                append("\n\n🔄 You can try again.")
            }
        }
        
        // Add specific guidance based on error type
        when (apiError.type) {
            ApiService.ErrorType.NETWORK_CONNECTIVITY -> {
                append("\n\n📶 Check your internet connection and try again.")
            }
            ApiService.ErrorType.REQUEST_TIMEOUT -> {
                append("\n\n⏱️ The request took too long. Try again with a shorter text or check your connection.")
            }
            ApiService.ErrorType.PARSING_ERROR -> {
                append("\n\n📝 Try rephrasing with clearer date, time, and event details.")
            }
            ApiService.ErrorType.RATE_LIMIT -> {
                append("\n\n⏳ Please wait before making another request.")
            }
            ApiService.ErrorType.VALIDATION_ERROR -> {
                append("\n\n✏️ Please check your input and try again.")
            }
            else -> {
                // No additional guidance needed
            }
        }
    }
    
    return enhancedMessage
}


/**
 * Confidence Warning Card - shows when confidence is low
 */
@Composable
private fun ConfidenceWarningCard(
    assessment: ConfidenceValidator.ConfidenceAssessment,
    onProceed: () -> Unit,
    onImprove: () -> Unit,
    onDismiss: () -> Unit
) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(
            containerColor = when (assessment.warningSeverity) {
                ConfidenceValidator.WarningSeverity.WARNING -> MaterialT
}   }
    }    
     }          }
            }
                  ")
    ove"Impr     Text(                 ) {
              
        t(1f)r.weighfieifier = Modi     mod             
      nRetry,onClick = o               
         on(nedButtli   Out      
           ) { 50onfidence <    if (c        Int()
    ).tocore * 100idenceSult.confce = (resconfidenl  va        s
       ence resultw confidlotton for try bu/ Show re        /         
              }
              ")
   Create Event  Text("               8.dp))
   .width(fierifier = ModiSpacer(mod                  
         )            
 e(18.dp)ifier.sizier = Mod   modif                    null,
  escription = contentD                     ,
  efault.Eventns.Dr = IcoeVecto     imag               
    n(   Ico                  ) {
              (1f)
 r.weightfie Modi modifier =             t,
      onCreateEvenick = nCl        o           
 utton(       B
                  ) {
   p)dBy(8.daceangement.spArrement = ontalArrang       horiz        xWidth(),
 er.fillMadififier = Moodi          m         Row(
         ons
on butt/ Acti   /             

        ))ight(16.dp.he = Modifierierpacer(modif     S             
          }
}
                
                  }   )
                            
   .tertiaryhemeolorScerialTheme.c Mator =       col                 mall,
    graphy.bodySme.typoMaterialThe = tyle          s                 rning",
 wa= "⚠️ $      text                    ext(
            T               rning ->
forEach { wangs.      warni             8.dp))
 ier.height(ier = Modif(modif Spacer                  {
  NotEmpty())rnings.is(waf   i             
 gs ->let { warninings?.lt.warnsu      reany
      arnings if g wsinow par// Sh                
             }
     
          )        e.tertiary
emolorSchlTheme.crialor = Mate      co        
      dySmall,phy.boheme.typogra= MaterialTtyle           s    
      ,eason" $rtext = "ℹ️                 
          Text()
         .dp)er.height(8fiier = Modiodif  Spacer(m           
   eason -> ret {Reason?.lllbackfalt.   resue
         ablon if applicinformatiow fallback       // Sh   
               }
         
          }       ))
  ht(4.dpier.heigfier = Modif Spacer(modi            
       dium)y.bodyMetypographalTheme.ri Mate", style =onlocatin: $tiocaLoText("          
          location ->t { cation?.lesult.lo        re       
           
                 }   dp))
  (4.heightdifier.difier = Mo(moacer     Sp               
ium)edhy.bodyMme.typograpThe= Material", style ttedDateEnd: $forma    Text("            
    teTime)eTime(endDamatDat = forteformattedDa       val             ->
  ndDateTimelet { e?..endDateTimesult         re
                      }
                ht(4.dp))
 ifier.heigifier = Modcer(mod    Spa           m)
     y.bodyMediu.typographemeerialTh Mate =e", stylmattedDatStart: $for Text("            me)
       (startDateTiateTimee = formatDDatformatted      val              eTime ->
  { startDatme?.lettDateTiesult.star    r                 
             }
         .dp))
     er.height(4r = Modifiacer(modifie Sp                  
 bodyMedium)ography.me.typTherialtele = Male", stye: $tititl"T    Text(              title ->
  let { title?.    result.     
       lableence avaiconfidif no field le display imp stolback / Fal    /            {
 } ?: run             }
              }
                     dp))
(4.heightifier.= Modr fiepacer(modi       S                
            }            
 }                      
              )                    Color
     field color =                                mall,
   .labelSographytyplTheme.= Materiatyle            s                  
       ),cal = 2.dp4.dp, vertiorizontal = adding(hodifier.pdifier = M   mo                               
  ",nfidence%= "$fieldCoext    t                            t(
      Tex                        
       ) {                        all
    es.extraSmme.shapterialThepe = Ma       sha                       
  ha = 0.1f),(alpopyColor.cld= fie     color                              Surface(
                         
                        
           )                      
ht(1f)r.weig = Modifiefier    modi                           um,
 bodyMediography.typheme. MaterialTyle =      st                      ",
    Info.value}{fieldlize()}: $.capita${fieldName  text = "                      
        ext(       T                 
                                }
                           rror
 rScheme.elolTheme.coateria   else -> M                           ry
  rtia.teolorSchememe.crialThe 30 -> Mateonfidence >=   fieldC                         
    imaryprScheme.oralTheme.colMateri= 70 -> onfidence >     fieldC                     en {
      or = whColfield       val                    t()
  * 100).toIn.confidence ieldInfodence = (ffieldCon     val fi                ) {
                          h()
     llMaxWidt.fifierier = Modi      modif              ,
        llycaenterVertiAlignment.Cnt = calAlignme       verti                       Row(
             
         e) {alueldInfo.hasV  if (fi                 o) ->
 e, fieldInf(fieldNamforEach { onfidences.  fieldC              ->
 esdenceldConfi?.let { fidConfidencesent?.fieldenceAssessm      confi   
   vailableif afidence  conelow field-lev  // Sh         
             p))
.der.height(12Modifiodifier = r(m       Space          
  }
                  }
              
   )             
     fidenceColorcolor = con                        ium,
y.labelMedographlTheme.typ= Materia    style              
        4.dp),al =.dp, verticrizontal = 8padding(hoer.difir = Mofiedi      mo                
  ence%",confidxt = "$ te                       
     Text(               {
     )           es.small
 Theme.shaprialshape = Mate                   0.1f),
  ha =r.copy(alpenceColor = confid        colo       
     ace(   Surf               
      
               }r
         Scheme.erroorme.colaterialTheelse -> M                  
  tiaryercheme.tTheme.colorSateriale >= 30 -> M  confidenc                
  imarylorScheme.prlTheme.co Materia>= 70 ->onfidence    c       
           {or = whenidenceColval conf          nt()
      ).toI* 100ceScore .confiden= (resultidence al conf           vtor
     e indical confidenc // Overal               
                 )
          
     ceVarianteme.onSurfalorSchalTheme.co= Materir   colo        
          ium,Medphy.titlegraeme.typoerialThstyle = Mat                  
  ls",nt Detaised EvePar  text = "             ext(
          T               ) {
      h()
  idtier.fillMaxWdifdifier = Mo          moen,
      weent.SpaceBet= Arrangemt rangemenzontalArri  ho            cally,
  CenterVertit.nmen Alignt =mealAlign      vertic               Row(
 {
       
        ).dp)padding(16 = Modifier.odifier        m   lumn(
     Co  ) {
         )
    
 Variantace.surfemeeme.colorSchalThMaterir = nerColo     contai
       Colors(cardfaults.Deolors = Card
        cth(),xWidfillMaifier. Mod  modifier =   
   Card(   it
) {
 () -> Untry:    onReUnit,
 > () -nt:  onCreateEvesment?,
   enceAssestor.ConfididenceValida: ConfntAssessmenceconfideesult,
    : ParseRult  resultCard(
  cedRes fun Enhanatele
priv
@Composab
 */catorsence indiidith conflt Card wsuanced Re
 * Enh}
}

/**   }
      }
               }
               
 ")ncelCaext("      T     
            ) {        
     issck = onDism       onCli             Button(
       Text           
               }
           ")
    ainTry Ag" Text(                  ) {
           
      ght(1f)ifier.weidifier = Mod   mo             etry,
    = onRck li        onC           utton(
  OutlinedB               
               }
              t")
   t Even"Accepext(     T            
     ) {             ight(1f)
 er.weer = Modifi  modifi               
   cept,ck = onAcnCli   o         (
        ton But        ) {
               
    dp)By(8.spacedgement. Arranement =lArrangontahoriz               xWidth(),
 llMafir. = Modifieifier     mod  (
                  Row   
       .dp))
     .height(16= Modifierodifier cer(m Spa          
                 }
  
              )     
   aryContainere.onTertilorSchemialTheme.coolor = Mater       c          all,
   aphy.bodySmTheme.typogr Materiale =tyl        s     ",
       reason️ $ "ℹ  text =              
    Text(                (4.dp))
r.heightfie= Modiier modif    Spacer(          ason ->
  on?.let { reackReasllbfaResult.llback      fa  
      
                 }              )
r
       ontainenTertiaryCeme.olorSchialTheme.co= Materlor        co         
    all,bodySmy.raphheme.typog MaterialT  style =                
  ate",formattedD $"Time:=       text            Text(
            
       Time)tDateime(stareTmatDatDate = forormatted       val f      >
   DateTime -let { startrtDateTime?..stalbackResult      fal           
   }
           
             )       iner
 ntartiaryCoe.onTeorScheme.colalThemriolor = Mate           c  ,
       bodySmallaphy.typogrme.alTheaterie = Mstyl                    ",
 $title = "Title:   text               
     Text(            
 le ->et { titult.title?.l fallbackRes         
  ils detak eventllbacw fa/ Sho    /         
      
     ))eight(12.dpModifier.hdifier = r(mo     Space 
              )
                yContainer
rtiarnTeeme.oeme.colorSchterialTh = Ma    color            edium,
odyMraphy.b.typoglThemee = Materia        styl
        tion:",able informa with availasic event a b we createdliably, sos rel detail parse al'tuldn co = "We       text   t(
            Tex
        
          8.dp))ht(er.heig= Modifir(modifier pace           S  
           }
                 )
          er
 ntainTertiaryCoeme.onSchorTheme.colerial = Matcolor         
           eMedium,.titlypographylTheme.tle = Materiasty              
      ed",eatEvent Crllback "Faext =  t                xt(
       Te        )
    .dp)(8ifier.widthdifier = Modacer(mo Sp                  )
           ntainer
  tiaryCo.onTeremeolorSchrialTheme.c = Mateint           t         null,
iption = tDescrconten                   t.Event,
 Defaulons. = IcgeVectorma           i
          Icon(               
) {          lly
  rVerticant.Centelignme = AAlignment   vertical        (
              Row ) {
   
       6.dp)dding(1.pa = Modifier  modifier          
n(olum   C{
      )      )
   iner
   taConry.tertiaemelorSch.coerialTheme = MatnerColorontai  c
          rs(locardCofaults.ors = CardDe   col    th(),
 lMaxWidier.filfier = Modif      modi(
  
    Card) {it
-> Unss: () smi
    onDi -> Unit,()ry: Ret on   Unit,
) -> pt: (ceg,
    onAcint: StrTexinal  origResult,
  rsekResult: Pabac(
    fallnCardioirmatlbackConfe fun Fale
privatablosomp*/
@C
 s createdack event iwhen fallbws hoion Card - snfirmatllback CoFa * 

/**    }
}

}
        }        
            }      s")
  is Text("Dism                  
    ) {            nDismiss
 lick = o   onC                on(
    TextButt     
                               }

         rove Text")ext("Imp           T          ) {
             1f)
  eight( Modifier.w =  modifier                 prove,
 k = onIm   onClic            
     edButton(lin    Out        
                          }
           }
                 
  yway")ceed An Text("Pro                          ) {
               
  .weight(1f)ierdififier = Mo     mod                 ,
  ed= onProceick nCl    o                   on(
  Butt               d) {
    Proceeouldshent. if (assessm          ) {
              
   By(8.dp)ent.spacedgemrran Ant =rangemerizontalAr          ho),
      Width(er.fillMaxr = Modifi  modifie             w(
         Ro    
    
        ).dp).height(16r = Modifierifiecer(mod   Spa     
               
      }  }
                    )
                   }
                         ant
 rfaceVarirScheme.onSulTheme.coloiaatere -> Mls   e                      iner
   ntarorCome.onErrScheeme.colo> MaterialThERROR -erity..WarningSevorenceValidatConfid                        er
    daryContainonSeconcheme.heme.colorSrialTG -> Materity.WARNINngSevearniidator.WonfidenceVal  C                        ) {
  verityingSent.warnsmeesn (asslor = whe  co                     all,
 y.bodySmtypographrialTheme.tyle = Mate       s           }",
      stionon.suggeuggesti "• ${sext =   t                  (
      Text              ->
   estion suggEach { orake(3).f.tSuggestionsprovement.immentassess             
        )      }
                        eVariant
 nSurfacScheme.ooralTheme.colateri> Mlse -    e                   ntainer
 rorCorScheme.onErolorialTheme.c Mateity.ERROR ->Severarningor.WlidatnfidenceVa   Co             er
        ndaryContainSecoe.oncolorSchemrialTheme. -> Materity.WARNING.WarningSevenceValidator    Confide           
         erity) {ningSevent.warsmen (assesor = wh  col               ium,
   abelMedhy.lme.typograpterialThe  style = Ma               ons:",
   tiest = "💡 Sugg       tex          Text(
               
    ))ight(8.dpifier.heifier = ModSpacer(mod            )) {
    mpty(NotEstions.isgeprovementSugessment.im     if (ass     gestions
  vement sugproow im       // Sh          
     
          }  )
        
                    }      ant
    rfaceVarime.onSulorSchecoalTheme. -> Materi       else               r
  taine.onErrorConhemee.colorScrialThemMate> ERROR -erity.WarningSevalidator.nfidenceV    Co               er
     yContaincondarme.onSecherSme.coloalThe -> MateriWARNINGngSeverity.r.WarnitoenceValidaonfid          C          
    ) {ngSeveritywarniassessment. = when (or col             ,
      edium.bodyMhypograplTheme.ty Materiastyle =                    
age, = mess        text          (
         Text        ge ->
  { messasage?.letrningMesssment.wa    asse             
      
 ight(8.dp)) Modifier.heifier =mod Spacer(                 

            }
       )              }
              
       faceVarianteme.onSurolorScheme.cterialThMa  else ->                     iner
  ntae.onErrorCoe.colorSchemThemalOR -> Materirity.ERRrningSevelidator.WaceVaConfiden                    
    ainercondaryContonSeeme.orSch.colialThemeterNG -> Maity.WARNIarningSeverdator.WenceVali Confid                    rity) {
   ngSevet.warnisessmenr = when (as     colo           ium,
    hy.titleMedograplTheme.typteria  style = Ma                g",
  ninnfidence Warxt = "Co        te           Text(
             
    p))er.width(8.dier = Modifir(modif  Space          )
                   }
               iant
      aceVaronSurfrScheme.heme.coloerialT-> Matlse          e         er
      rContainme.onErroScheolor.cialThemeROR -> Materty.ERingSeverirnalidator.WaceV  Confiden               
       eraryContainnSecondrScheme.oTheme.colo> Material.WARNING -veritySengor.WarniidatonfidenceVal      C                rity) {
  Sevearningent.wassessm= when (      tint          
     null,on = ntDescripti     conte              ,
 nfot.Iefaul = Icons.DimageVector                    on(
   Ic             ) {
      
      rticallynterVeignment.Cent = AlticalAlignme ver         (
              Row{
    
        ) p)g(16.dpaddiner. Modifiifier =     modmn(
              Colu {
     )
    )         }
 
      riantfaceVae.sur.colorSchemalThemese -> Materi    el      
      ainere.errorContorSchememe.colrialTh> Materity.ERROR -rningSeveor.WaalidatdenceV  Confi       r
       yContaine.secondarchemeheme.colorS