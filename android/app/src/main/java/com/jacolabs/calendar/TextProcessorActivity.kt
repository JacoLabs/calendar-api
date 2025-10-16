package com.jacolabs.calendar

import android.content.ClipboardManager
import android.content.Context
import android.content.Intent
import android.net.ConnectivityManager
import android.net.NetworkCapabilities
import android.os.Build
import android.os.Bundle
import android.provider.CalendarContract
import android.util.Log
import android.widget.Toast
import androidx.activity.ComponentActivity
import androidx.lifecycle.lifecycleScope
import kotlinx.coroutines.launch
import java.text.SimpleDateFormat
import java.util.*
import kotlin.math.pow

/**
 * Activity that handles ACTION_PROCESS_TEXT intents for selected text.
 * This appears in the text selection context menu as "Create calendar event".
 * 
 * Enhanced with comprehensive error handling, fallback mechanisms, and offline support.
 * Implements requirements 1.1, 1.2, 4.1, 4.2, 7.1, 10.1, 10.3, 10.4 for robust text processing.
 */
class TextProcessorActivity : ComponentActivity() {
    
    companion object {
        private const val TAG = "TextProcessorActivity"
        private const val MAX_RETRY_ATTEMPTS = 3
        private const val PROCESSING_TIMEOUT_MS = 15000L
    }
    
    private lateinit var apiService: ApiService
    private lateinit var textMergeHelper: TextMergeHelper
    private lateinit var errorHandlingManager: ErrorHandlingManager
    private lateinit var userFeedbackManager: UserFeedbackManager
    private lateinit var offlineModeHandler: OfflineModeHandler
    private lateinit var calendarIntentHelper: CalendarIntentHelper
    private lateinit var confidenceValidator: ConfidenceValidator
    
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        
        // Initialize all components with error handling
        initializeComponents()
        
        // Get the selected text from the intent
        val selectedText = intent.getCharSequenceExtra(Intent.EXTRA_PROCESS_TEXT)?.toString()
        
        if (selectedText.isNullOrBlank()) {
            handleEmptyTextError()
            return
        }
        
        // Show loading feedback
        Toast.makeText(this, "Processing selected text...", Toast.LENGTH_SHORT).show()
        
        // Process the text with comprehensive error handling
        processSelectedTextWithErrorHandling(selectedText)
    }
    
    private fun initializeComponents() {
        try {
            Log.d(TAG, "Initializing TextProcessorActivity components")
            apiService = ApiService(this)
            textMergeHelper = TextMergeHelper(this)
            errorHandlingManager = ErrorHandlingManager(this)
            userFeedbackManager = UserFeedbackManager(this)
            offlineModeHandler = OfflineModeHandler(this)
            calendarIntentHelper = CalendarIntentHelper(this)
            confidenceValidator = ConfidenceValidator(this)
            Log.d(TAG, "All components initialized successfully")
        } catch (e: Exception) {
            Log.e(TAG, "Failed to initialize app components", e)
            // Fallback to basic error handling if component initialization fails
            showError("Failed to initialize app components: ${e.message}")
            finish()
        }
    }
    
    private fun handleEmptyTextError() {
        Log.w(TAG, "No text was selected for processing")
        val errorContext = ErrorHandlingManager.ErrorContext(
            errorType = ErrorHandlingManager.ErrorType.INSUFFICIENT_DATA,
            originalText = "",
            exception = IllegalArgumentException("No text was selected")
        )
        
        lifecycleScope.launch {
            val result = errorHandlingManager.handleError(errorContext)
            userFeedbackManager.showErrorMessage(result.userMessage)
            finish()
        }
    }
    
    private fun processSelectedTextWithErrorHandling(selectedText: String) {
        Log.d(TAG, "Processing selected text with length: ${selectedText.length}")
        lifecycleScope.launch {
            var retryCount = 0
            var lastException: Exception? = null
            val startTime = System.currentTimeMillis()
            val previousErrors = mutableListOf<ErrorHandlingManager.ErrorType>()
            
            // Validate text input before processing
            if (selectedText.length > 10000) {
                Log.w(TAG, "Selected text is very long (${selectedText.length} chars), may cause processing issues")
                Toast.makeText(this@TextProcessorActivity, "Processing large text selection...", Toast.LENGTH_SHORT).show()
            }
            
            while (retryCount <= MAX_RETRY_ATTEMPTS) {
                try {
                    Log.d(TAG, "Processing attempt ${retryCount + 1}/${MAX_RETRY_ATTEMPTS + 1}")
                    
                    // Check for timeout on processing
                    val currentTime = System.currentTimeMillis()
                    if (currentTime - startTime > PROCESSING_TIMEOUT_MS) {
                        Log.w(TAG, "Processing timeout exceeded (${currentTime - startTime}ms)")
                        val timeoutContext = ErrorHandlingManager.ErrorContext(
                            errorType = ErrorHandlingManager.ErrorType.API_TIMEOUT,
                            originalText = selectedText,
                            retryCount = retryCount,
                            processingTimeMs = currentTime - startTime,
                            previousErrors = previousErrors.toList()
                        )
                        handleMaxRetriesExceeded(timeoutContext)
                        return@launch
                    }
                    
                    // Get current timezone and locale
                    val timezone = TimeZone.getDefault().id
                    val locale = Locale.getDefault().toString()
                    val now = Date()
                    
                    // Try to enhance the selected text with clipboard merge and heuristics
                    val enhancedText = try {
                        textMergeHelper.enhanceTextForParsing(selectedText)
                    } catch (e: Exception) {
                        Log.w(TAG, "Text enhancement failed, using original text: ${e.message}")
                        selectedText // Fallback to original text if enhancement fails
                    }
                    Log.d(TAG, "Enhanced text length: ${enhancedText.length}")
                    
                    // Check network connectivity before API call
                    if (!isNetworkAvailable()) {
                        Log.i(TAG, "No network available, switching to offline processing")
                        handleOfflineProcessing(enhancedText)
                        return@launch
                    }
                    
                    // Call API to parse the enhanced text with timeout handling
                    val result = apiService.parseText(enhancedText, timezone, locale, now)
                    Log.d(TAG, "API parsing completed with confidence: ${result.confidenceScore}")
                    
                    // Apply safer defaults if we have incomplete information
                    val finalResult = try {
                        textMergeHelper.applySaferDefaults(result, enhancedText)
                    } catch (e: Exception) {
                        Log.w(TAG, "Failed to apply safer defaults, using original result: ${e.message}")
                        result.copy(originalText = enhancedText) // Preserve original text
                    }
                    
                    // Validate and handle the result
                    handleParsingResult(finalResult, enhancedText)
                    return@launch
                    
                } catch (e: ApiException) {
                    lastException = e
                    val errorType = categorizeApiException(e)
                    previousErrors.add(errorType)
                    Log.w(TAG, "API exception on attempt ${retryCount + 1}: ${e.message}", e)
                    val errorContext = createErrorContext(e, selectedText, retryCount).copy(
                        previousErrors = previousErrors.toList(),
                        processingTimeMs = System.currentTimeMillis() - startTime
                    )
                    
                    if (shouldRetryError(e, retryCount)) {
                        retryCount++
                        val delayMs = calculateRetryDelay(retryCount)
                        Log.d(TAG, "Retrying after ${delayMs}ms delay")
                        Toast.makeText(this@TextProcessorActivity, "Retrying... (attempt $retryCount)", Toast.LENGTH_SHORT).show()
                        kotlinx.coroutines.delay(delayMs)
                        continue
                    } else {
                        Log.e(TAG, "API error not retryable, handling error")
                        handleApiError(errorContext)
                        return@launch
                    }
                    
                } catch (e: Exception) {
                    lastException = e
                    val errorType = ErrorHandlingManager.ErrorType.UNKNOWN_ERROR
                    previousErrors.add(errorType)
                    Log.e(TAG, "Unexpected error on attempt ${retryCount + 1}: ${e.message}", e)
                    val errorContext = createErrorContext(e, selectedText, retryCount).copy(
                        previousErrors = previousErrors.toList(),
                        processingTimeMs = System.currentTimeMillis() - startTime
                    )
                    handleUnexpectedError(errorContext)
                    return@launch
                }
            }
            
            // If we get here, all retries failed
            val processingTime = System.currentTimeMillis() - startTime
            Log.e(TAG, "All retry attempts failed after ${processingTime}ms")
            val errorContext = createErrorContext(lastException!!, selectedText, retryCount).copy(
                processingTimeMs = processingTime,
                previousErrors = previousErrors.toList()
            )
            handleMaxRetriesExceeded(errorContext)
        }
    }
    
    private suspend fun handleParsingResult(result: ParseResult, originalText: String) {
        Log.d(TAG, "Handling parsing result - title: ${result.title?.isNotBlank()}, startTime: ${result.startDateTime?.isNotBlank()}, confidence: ${result.confidenceScore}")
        
        // Check if we got useful results
        if (result.title.isNullOrBlank() && result.startDateTime.isNullOrBlank()) {
            Log.w(TAG, "Insufficient data in parsing result")
            val errorContext = ErrorHandlingManager.ErrorContext(
                errorType = ErrorHandlingManager.ErrorType.INSUFFICIENT_DATA,
                originalText = originalText,
                apiResponse = result,
                confidenceScore = result.confidenceScore
            )
            
            val handlingResult = errorHandlingManager.handleError(errorContext)
            
            if (handlingResult.success && handlingResult.recoveredResult != null) {
                Log.d(TAG, "Error handling provided recovered result")
                createCalendarEventWithFallback(handlingResult.recoveredResult)
            } else {
                Log.w(TAG, "No recovery possible for insufficient data")
                userFeedbackManager.showErrorMessage(handlingResult.userMessage)
                finish()
            }
        } else {
            // Check confidence and handle accordingly
            handleConfidenceValidation(result, originalText)
        }
    }
    
    private suspend fun handleConfidenceValidation(result: ParseResult, originalText: String) {
        Log.d(TAG, "Validating confidence for result with score: ${result.confidenceScore}")
        
        // Create confidence assessment using ConfidenceValidator
        val assessment = confidenceValidator.assessConfidence(result, originalText)
        Log.d(TAG, "Confidence assessment: overall=${assessment.overallConfidence}, recommendation=${assessment.recommendation}")
        
        if (assessment.overallConfidence < 0.3) {
            Log.i(TAG, "Low confidence detected (${assessment.overallConfidence}), handling appropriately")
            val errorContext = ErrorHandlingManager.ErrorContext(
                errorType = ErrorHandlingManager.ErrorType.LOW_CONFIDENCE,
                originalText = originalText,
                apiResponse = result,
                confidenceScore = assessment.overallConfidence,
                userInteractionAllowed = true
            )
            
            val handlingResult = errorHandlingManager.handleError(errorContext)
            
            if (handlingResult.actionRequired == ErrorHandlingManager.UserAction.CONFIRM_LOW_CONFIDENCE_RESULT) {
                Log.d(TAG, "User confirmation required for low confidence result")
                val userConfirmed = userFeedbackManager.showConfidenceWarning(assessment)
                
                if (userConfirmed) {
                    Log.d(TAG, "User confirmed low confidence result, proceeding")
                    createCalendarEventWithFallback(result)
                } else {
                    Log.d(TAG, "User declined low confidence result, cancelling")
                    finish()
                }
            } else if (handlingResult.recoveredResult != null) {
                Log.d(TAG, "Using recovered result from error handling")
                createCalendarEventWithFallback(handlingResult.recoveredResult)
            } else {
                Log.w(TAG, "No recovery available for low confidence result")
                userFeedbackManager.showErrorMessage(handlingResult.userMessage)
                finish()
            }
        } else {
            Log.d(TAG, "Confidence acceptable, proceeding with calendar creation")
            createCalendarEventWithFallback(result)
        }
    }
    
    /**
     * Checks if network connectivity is available
     * Requirement 4.1, 4.2: Handle network connectivity issues gracefully
     */
    private fun isNetworkAvailable(): Boolean {
        val connectivityManager = getSystemService(Context.CONNECTIVITY_SERVICE) as? ConnectivityManager
            ?: return false
        
        return if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
            val network = connectivityManager.activeNetwork ?: return false
            val capabilities = connectivityManager.getNetworkCapabilities(network) ?: return false
            capabilities.hasCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET) &&
                    capabilities.hasCapability(NetworkCapabilities.NET_CAPABILITY_VALIDATED)
        } else {
            @Suppress("DEPRECATION")
            val networkInfo = connectivityManager.activeNetworkInfo
            networkInfo?.isConnected == true
        }
    }

    /**
     * Handles offline processing when network is unavailable
     * Requirements 4.1, 4.2, 4.3: Network error handling and offline functionality
     */
    private suspend fun handleOfflineProcessing(text: String) {
        Log.i(TAG, "Handling offline processing for text length: ${text.length}")
        try {
            // Show user-friendly offline message
            Toast.makeText(this@TextProcessorActivity, "No internet connection. Creating event offline...", Toast.LENGTH_LONG).show()
            
            // Validate text for offline processing
            if (text.isBlank()) {
                Log.w(TAG, "Cannot process empty text in offline mode")
                val errorContext = ErrorHandlingManager.ErrorContext(
                    errorType = ErrorHandlingManager.ErrorType.INSUFFICIENT_DATA,
                    originalText = text,
                    networkAvailable = false
                )
                val handlingResult = errorHandlingManager.handleError(errorContext)
                userFeedbackManager.showErrorMessage(handlingResult.userMessage)
                finish()
                return
            }
            
            // Create offline event with enhanced error handling
            val offlineResult = try {
                offlineModeHandler.createOfflineEvent(text)
            } catch (e: Exception) {
                Log.w(TAG, "Offline event creation failed, creating basic fallback: ${e.message}")
                // Create a very basic fallback event if offline handler fails
                createBasicFallbackEvent(text)
            }
            
            Log.d(TAG, "Offline event created with confidence: ${offlineResult.confidenceScore}")
            
            // Cache the request for later retry when network returns
            try {
                offlineModeHandler.cacheFailedRequest(
                    OfflineModeHandler.CachedRequest(
                        text = text,
                        timestamp = System.currentTimeMillis(),
                        timezone = TimeZone.getDefault().id,
                        locale = Locale.getDefault().toString()
                    )
                )
                Log.d(TAG, "Request cached for later retry")
            } catch (e: Exception) {
                Log.w(TAG, "Failed to cache request for retry: ${e.message}")
                // Continue with offline event creation even if caching fails
            }
            
            // Mark result as offline-created for user awareness
            val finalResult = offlineResult.copy(
                fallbackApplied = true,
                fallbackReason = "Created offline due to network unavailability",
                originalText = text
            )
            
            createCalendarEventWithFallback(finalResult)
            
        } catch (e: Exception) {
            Log.e(TAG, "Failed to handle offline processing", e)
            val errorContext = ErrorHandlingManager.ErrorContext(
                errorType = ErrorHandlingManager.ErrorType.NETWORK_ERROR,
                originalText = text,
                exception = e,
                networkAvailable = false
            )
            
            val handlingResult = errorHandlingManager.handleError(errorContext)
            
            // As a last resort, try to create a very basic event
            if (handlingResult.recoveredResult != null) {
                createCalendarEventWithFallback(handlingResult.recoveredResult)
            } else {
                // Final fallback - create basic event manually
                try {
                    val basicEvent = createBasicFallbackEvent(text)
                    createCalendarEventWithFallback(basicEvent)
                } catch (fallbackException: Exception) {
                    Log.e(TAG, "All offline processing failed", fallbackException)
                    userFeedbackManager.showErrorMessage("Unable to create event offline: ${handlingResult.userMessage}")
                    finish()
                }
            }
        }
    }
    
    /**
     * Creates a very basic fallback event when all other processing fails
     * Requirement 3.4: Create event with original text when all parsing fails
     */
    private fun createBasicFallbackEvent(text: String): ParseResult {
        Log.d(TAG, "Creating basic fallback event from text")
        
        // Extract a reasonable title from the text
        val title = when {
            text.length <= 50 -> text.trim()
            else -> {
                // Try to find the first sentence or take first 50 chars
                val firstSentence = text.split('.', '!', '?').firstOrNull()?.trim()
                when {
                    !firstSentence.isNullOrBlank() && firstSentence.length <= 50 -> firstSentence
                    else -> text.take(47).trim() + "..."
                }
            }
        }
        
        // Default to next hour for timing
        val calendar = Calendar.getInstance()
        calendar.add(Calendar.HOUR_OF_DAY, 1)
        calendar.set(Calendar.MINUTE, 0)
        calendar.set(Calendar.SECOND, 0)
        calendar.set(Calendar.MILLISECOND, 0)
        
        val startTime = calendar.time
        calendar.add(Calendar.HOUR_OF_DAY, 1) // 1 hour duration
        val endTime = calendar.time
        
        val dateFormat = SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss", Locale.getDefault())
        
        return ParseResult(
            title = title,
            startDateTime = dateFormat.format(startTime),
            endDateTime = dateFormat.format(endTime),
            location = null,
            description = "Original text: $text",
            confidenceScore = 0.1, // Very low confidence for basic fallback
            allDay = false,
            timezone = TimeZone.getDefault().id,
            fallbackApplied = true,
            fallbackReason = "Basic fallback event created due to processing failure",
            originalText = text
        )
    }
    
    /**
     * Categorizes API exceptions into specific error types for better handling
     * Requirement 7.1: Detailed error logging and categorization
     */
    private fun categorizeApiException(exception: ApiException): ErrorHandlingManager.ErrorType {
        return when {
            exception.message?.contains("timeout", ignoreCase = true) == true -> 
                ErrorHandlingManager.ErrorType.API_TIMEOUT
            exception.message?.contains("network", ignoreCase = true) == true -> 
                ErrorHandlingManager.ErrorType.NETWORK_ERROR
            exception.message?.contains("rate limit", ignoreCase = true) == true -> 
                ErrorHandlingManager.ErrorType.RATE_LIMIT_ERROR
            exception.message?.contains("429", ignoreCase = true) == true -> 
                ErrorHandlingManager.ErrorType.RATE_LIMIT_ERROR
            exception.message?.contains("500", ignoreCase = true) == true || 
            exception.message?.contains("502", ignoreCase = true) == true ||
            exception.message?.contains("503", ignoreCase = true) == true -> 
                ErrorHandlingManager.ErrorType.SERVER_ERROR
            exception.message?.contains("400", ignoreCase = true) == true ||
            exception.message?.contains("422", ignoreCase = true) == true -> 
                ErrorHandlingManager.ErrorType.VALIDATION_ERROR
            else -> ErrorHandlingManager.ErrorType.PARSING_FAILURE
        }
    }
    
    /**
     * Creates comprehensive error context for error handling decisions
     * Requirement 7.1, 10.1: Context preservation and error categorization
     */
    private fun createErrorContext(
        exception: Exception, 
        originalText: String, 
        retryCount: Int
    ): ErrorHandlingManager.ErrorContext {
        val errorType = when (exception) {
            is ApiException -> categorizeApiException(exception)
            is java.net.SocketTimeoutException -> ErrorHandlingManager.ErrorType.API_TIMEOUT
            is java.net.UnknownHostException -> ErrorHandlingManager.ErrorType.NETWORK_ERROR
            is java.net.ConnectException -> ErrorHandlingManager.ErrorType.NETWORK_ERROR
            is java.io.IOException -> {
                when {
                    exception.message?.contains("timeout", ignoreCase = true) == true -> 
                        ErrorHandlingManager.ErrorType.API_TIMEOUT
                    exception.message?.contains("network", ignoreCase = true) == true -> 
                        ErrorHandlingManager.ErrorType.NETWORK_ERROR
                    else -> ErrorHandlingManager.ErrorType.NETWORK_ERROR
                }
            }
            else -> ErrorHandlingManager.ErrorType.UNKNOWN_ERROR
        }
        
        Log.d(TAG, "Created error context: type=$errorType, retryCount=$retryCount, textLength=${originalText.length}")
        
        return ErrorHandlingManager.ErrorContext(
            errorType = errorType,
            originalText = originalText,
            exception = exception,
            retryCount = retryCount,
            networkAvailable = isNetworkAvailable(),
            timestamp = System.currentTimeMillis(),
            userInteractionAllowed = true // TextProcessorActivity allows user interaction
        )
    }
    
    private fun shouldRetryError(exception: ApiException, retryCount: Int): Boolean {
        return retryCount < 3 && (
            exception.message?.contains("timeout", ignoreCase = true) == true ||
            exception.message?.contains("network", ignoreCase = true) == true ||
            exception.message?.contains("temporary", ignoreCase = true) == true
        )
    }
    
    private fun calculateRetryDelay(retryCount: Int): Long {
        return (1000 * 2.0.pow(retryCount.toDouble())).toLong() // Exponential backoff
    }
    
    private suspend fun handleApiError(errorContext: ErrorHandlingManager.ErrorContext) {
        Log.w(TAG, "Handling API error: ${errorContext.errorType}")
        val handlingResult = errorHandlingManager.handleError(errorContext)
        
        when (handlingResult.recoveryStrategy) {
            ErrorHandlingManager.RecoveryStrategy.OFFLINE_MODE -> {
                Log.d(TAG, "Switching to offline mode due to API error")
                handleOfflineProcessing(errorContext.originalText)
            }
            ErrorHandlingManager.RecoveryStrategy.FALLBACK_EVENT_CREATION -> {
                if (handlingResult.recoveredResult != null) {
                    Log.d(TAG, "Using fallback event creation")
                    createCalendarEventWithFallback(handlingResult.recoveredResult)
                } else {
                    Log.w(TAG, "Fallback event creation failed")
                    userFeedbackManager.showErrorMessage(handlingResult.userMessage)
                    finish()
                }
            }
            ErrorHandlingManager.RecoveryStrategy.RETRY_WITH_BACKOFF -> {
                if (handlingResult.retryRecommended) {
                    Log.d(TAG, "Retry recommended, will be handled by main retry loop")
                    // This will be handled by the main retry loop
                    return
                }
                userFeedbackManager.showErrorMessage(handlingResult.userMessage)
                finish()
            }
            else -> {
                Log.w(TAG, "No suitable recovery strategy for API error")
                userFeedbackManager.showErrorMessage(handlingResult.userMessage)
                finish()
            }
        }
    }
    
    private suspend fun handleUnexpectedError(errorContext: ErrorHandlingManager.ErrorContext) {
        Log.e(TAG, "Handling unexpected error: ${errorContext.exception?.message}")
        val handlingResult = errorHandlingManager.handleError(errorContext)
        
        // For unexpected errors, try fallback creation if possible
        if (handlingResult.recoveredResult != null) {
            Log.d(TAG, "Using recovered result for unexpected error")
            createCalendarEventWithFallback(handlingResult.recoveredResult)
        } else {
            Log.w(TAG, "No recovery possible for unexpected error")
            userFeedbackManager.showErrorMessage(handlingResult.userMessage)
            finish()
        }
    }
    
    private suspend fun handleMaxRetriesExceeded(errorContext: ErrorHandlingManager.ErrorContext) {
        Log.e(TAG, "Maximum retry attempts exceeded")
        val handlingResult = errorHandlingManager.handleError(errorContext)
        
        when (handlingResult.recoveryStrategy) {
            ErrorHandlingManager.RecoveryStrategy.OFFLINE_MODE -> {
                Log.d(TAG, "Switching to offline mode after max retries")
                handleOfflineProcessing(errorContext.originalText)
            }
            ErrorHandlingManager.RecoveryStrategy.FALLBACK_EVENT_CREATION -> {
                if (handlingResult.recoveredResult != null) {
                    Log.d(TAG, "Using fallback event creation after max retries")
                    createCalendarEventWithFallback(handlingResult.recoveredResult)
                } else {
                    Log.w(TAG, "Fallback creation failed after max retries")
                    userFeedbackManager.showErrorMessage("Failed after multiple attempts: ${handlingResult.userMessage}")
                    finish()
                }
            }
            else -> {
                Log.w(TAG, "No recovery available after max retries")
                userFeedbackManager.showErrorMessage("Failed after multiple attempts: ${handlingResult.userMessage}")
                finish()
            }
        }
    }
    
    private suspend fun createCalendarEventWithFallback(result: ParseResult) {
        Log.d(TAG, "Creating calendar event with title: ${result.title}")
        try {
            val success = calendarIntentHelper.createCalendarEvent(result)
            
            if (success) {
                Log.d(TAG, "Calendar event created successfully")
                userFeedbackManager.showSuccessMessage("Calendar event created successfully!")
                finish()
            } else {
                Log.w(TAG, "Calendar launch failed, trying fallback mechanisms")
                handleCalendarLaunchFailure(result)
            }
            
        } catch (e: Exception) {
            Log.e(TAG, "Exception during calendar event creation", e)
            val errorContext = ErrorHandlingManager.ErrorContext(
                errorType = ErrorHandlingManager.ErrorType.CALENDAR_LAUNCH_FAILURE,
                originalText = result.originalText ?: "",
                apiResponse = result,
                exception = e,
                networkAvailable = isNetworkAvailable()
            )
            
            val handlingResult = errorHandlingManager.handleError(errorContext)
            
            when (handlingResult.recoveryStrategy) {
                ErrorHandlingManager.RecoveryStrategy.ALTERNATIVE_CALENDAR_LAUNCH -> {
                    Log.d(TAG, "Trying alternative calendar launch")
                    tryAlternativeCalendarLaunch(result)
                }
                ErrorHandlingManager.RecoveryStrategy.MANUAL_INPUT_SUGGESTION -> {
                    Log.d(TAG, "Offering manual event creation")
                    offerManualEventCreation(result)
                }
                else -> {
                    Log.w(TAG, "No recovery strategy available for calendar launch failure")
                    userFeedbackManager.showErrorMessage(handlingResult.userMessage)
                    finish()
                }
            }
        }
    }
    
    private suspend fun handleCalendarLaunchFailure(result: ParseResult) {
        val errorContext = ErrorHandlingManager.ErrorContext(
            errorType = ErrorHandlingManager.ErrorType.CALENDAR_LAUNCH_FAILURE,
            originalText = result.originalText ?: "",
            apiResponse = result
        )
        
        val handlingResult = errorHandlingManager.handleError(errorContext)
        
        when (handlingResult.recoveryStrategy) {
            ErrorHandlingManager.RecoveryStrategy.ALTERNATIVE_CALENDAR_LAUNCH -> {
                tryAlternativeCalendarLaunch(result)
            }
            ErrorHandlingManager.RecoveryStrategy.MANUAL_INPUT_SUGGESTION -> {
                offerManualEventCreation(result)
            }
            else -> {
                userFeedbackManager.showErrorMessage(handlingResult.userMessage)
                finish()
            }
        }
    }
    
    private suspend fun tryAlternativeCalendarLaunch(result: ParseResult) {
        Log.d(TAG, "Attempting alternative calendar launch strategies")
        try {
            // Try alternative launch strategies including web calendar fallback
            val launchResult = calendarIntentHelper.launchCalendarWithFallbacks(result)
            
            if (launchResult.success) {
                Log.d(TAG, "Alternative calendar launch successful")
                userFeedbackManager.showSuccessMessage("Calendar event created successfully!")
                finish()
            } else {
                Log.w(TAG, "All calendar launch strategies failed, offering manual creation")
                offerManualEventCreation(result)
            }
            
        } catch (e: Exception) {
            Log.e(TAG, "Exception during alternative calendar launch", e)
            offerManualEventCreation(result)
        }
    }
    
    private suspend fun offerManualEventCreation(result: ParseResult) {
        Log.d(TAG, "Offering manual event creation as final fallback")
        // Show calendar not found dialog which will handle clipboard copying internally
        userFeedbackManager.showCalendarNotFoundDialog(result, emptyList())
        
        // Also copy event details to clipboard as backup
        val eventDetails = buildEventDetailsString(result)
        copyEventToClipboard(eventDetails)
        
        finish()
    }
    
    private fun buildEventDetailsString(result: ParseResult): String {
        return buildString {
            appendLine("Event Details:")
            appendLine("Title: ${result.title ?: "No title"}")
            appendLine("Start: ${result.startDateTime ?: "No start time"}")
            appendLine("End: ${result.endDateTime ?: "No end time"}")
            if (!result.location.isNullOrBlank()) {
                appendLine("Location: ${result.location}")
            }
            if (!result.description.isNullOrBlank()) {
                appendLine("Description: ${result.description}")
            }
            if (result.fallbackApplied) {
                appendLine("Note: Created with fallback processing")
            }
        }
    }
    
    private fun copyEventToClipboard(eventDetails: String) {
        try {
            Log.d(TAG, "Copying event details to clipboard")
            val clipboardManager = getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
            val clipData = android.content.ClipData.newPlainText("Calendar Event", eventDetails)
            clipboardManager.setPrimaryClip(clipData)
            Toast.makeText(this, "Event details copied to clipboard", Toast.LENGTH_SHORT).show()
        } catch (e: Exception) {
            Log.e(TAG, "Failed to copy to clipboard", e)
            // Fallback if clipboard access fails
            showError("Failed to copy to clipboard: ${e.message}")
        }
    }
    

    


    private fun showError(message: String) {
        Log.e(TAG, "Showing error to user: $message")
        Toast.makeText(this, message, Toast.LENGTH_LONG).show()
    }
}