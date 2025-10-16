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
 * Enhanced with comprehensive error handling, fallback mechanisms, and offline support.
 */
class TextProcessorActivity : ComponentActivity() {
    
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
            apiService = ApiService(this)
            textMergeHelper = TextMergeHelper(this)
            errorHandlingManager = ErrorHandlingManager(this)
            userFeedbackManager = UserFeedbackManager(this)
            offlineModeHandler = OfflineModeHandler(this)
            calendarIntentHelper = CalendarIntentHelper(this)
            confidenceValidator = ConfidenceValidator(this)
        } catch (e: Exception) {
            // Fallback to basic error handling if component initialization fails
            showError("Failed to initialize app components: ${e.message}")
            finish()
        }
    }
    
    private fun handleEmptyTextError() {
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
        lifecycleScope.launch {
            var retryCount = 0
            var lastException: Exception? = null
            
            while (retryCount <= 3) { // Max 3 attempts
                try {
                    // Get current timezone and locale
                    val timezone = TimeZone.getDefault().id
                    val locale = Locale.getDefault().toString()
                    val now = Date()
                    
                    // Try to enhance the selected text with clipboard merge and heuristics
                    val enhancedText = textMergeHelper.enhanceTextForParsing(selectedText)
                    
                    // Check network connectivity before API call
                    if (!offlineModeHandler.isNetworkAvailable()) {
                        handleOfflineProcessing(enhancedText)
                        return@launch
                    }
                    
                    // Call API to parse the enhanced text with timeout handling
                    val result = apiService.parseText(enhancedText, timezone, locale, now)
                    
                    // Apply safer defaults if we have incomplete information
                    val finalResult = textMergeHelper.applySaferDefaults(result, enhancedText)
                    
                    // Validate and handle the result
                    handleParsingResult(finalResult, enhancedText)
                    return@launch
                    
                } catch (e: ApiException) {
                    lastException = e
                    val errorContext = createErrorContext(e, selectedText, retryCount)
                    
                    if (shouldRetryError(e, retryCount)) {
                        retryCount++
                        val delayMs = calculateRetryDelay(retryCount)
                        Toast.makeText(this@TextProcessorActivity, "Retrying... (attempt $retryCount)", Toast.LENGTH_SHORT).show()
                        kotlinx.coroutines.delay(delayMs)
                        continue
                    } else {
                        handleApiError(errorContext)
                        return@launch
                    }
                    
                } catch (e: Exception) {
                    lastException = e
                    val errorContext = createErrorContext(e, selectedText, retryCount)
                    handleUnexpectedError(errorContext)
                    return@launch
                }
            }
            
            // If we get here, all retries failed
            val errorContext = createErrorContext(lastException!!, selectedText, retryCount)
            handleMaxRetriesExceeded(errorContext)
        }
    }
    
    private suspend fun handleParsingResult(result: ParseResult, originalText: String) {
        // Check if we got useful results
        if (result.title.isNullOrBlank() && result.startDateTime.isNullOrBlank()) {
            val errorContext = ErrorHandlingManager.ErrorContext(
                errorType = ErrorHandlingManager.ErrorType.INSUFFICIENT_DATA,
                originalText = originalText,
                apiResponse = result
            )
            
            val handlingResult = errorHandlingManager.handleError(errorContext)
            
            if (handlingResult.success && handlingResult.recoveredResult != null) {
                createCalendarEventWithFallback(handlingResult.recoveredResult)
            } else {
                userFeedbackManager.showErrorMessage(handlingResult.userMessage)
                finish()
            }
        } else {
            // Check confidence and handle accordingly
            handleConfidenceValidation(result, originalText)
        }
    }
    
    private suspend fun handleConfidenceValidation(result: ParseResult, originalText: String) {
        // Create confidence assessment using ConfidenceValidator
        val assessment = confidenceValidator.assessConfidence(result, originalText)
        
        if (assessment.overallConfidence < 0.3) {
            val errorContext = ErrorHandlingManager.ErrorContext(
                errorType = ErrorHandlingManager.ErrorType.LOW_CONFIDENCE,
                originalText = originalText,
                apiResponse = result,
                confidenceScore = assessment.overallConfidence
            )
            
            val handlingResult = errorHandlingManager.handleError(errorContext)
            
            if (handlingResult.actionRequired == ErrorHandlingManager.UserAction.CONFIRM_PROCEED) {
                val userConfirmed = userFeedbackManager.showConfidenceWarning(assessment)
                
                if (userConfirmed) {
                    createCalendarEventWithFallback(result)
                } else {
                    finish()
                }
            } else if (handlingResult.recoveredResult != null) {
                createCalendarEventWithFallback(handlingResult.recoveredResult)
            } else {
                userFeedbackManager.showErrorMessage(handlingResult.userMessage)
                finish()
            }
        } else {
            createCalendarEventWithFallback(result)
        }
    }
    
    private suspend fun handleOfflineProcessing(text: String) {
        try {
            Toast.makeText(this@TextProcessorActivity, "No internet connection. Creating event offline...", Toast.LENGTH_SHORT).show()
            
            val offlineResult = offlineModeHandler.createOfflineEvent(text)
            
            // Cache the request for later retry
            offlineModeHandler.cacheFailedRequest(
                OfflineModeHandler.CachedRequest(
                    text = text,
                    timestamp = System.currentTimeMillis(),
                    timezone = TimeZone.getDefault().id,
                    locale = Locale.getDefault().toString()
                )
            )
            
            createCalendarEventWithFallback(offlineResult)
            
        } catch (e: Exception) {
            val errorContext = ErrorHandlingManager.ErrorContext(
                errorType = ErrorHandlingManager.ErrorType.NETWORK_ERROR,
                originalText = text,
                exception = e,
                networkAvailable = false
            )
            
            val handlingResult = errorHandlingManager.handleError(errorContext)
            userFeedbackManager.showErrorMessage(handlingResult.userMessage)
            finish()
        }
    }
    
    private fun createErrorContext(
        exception: Exception, 
        originalText: String, 
        retryCount: Int
    ): ErrorHandlingManager.ErrorContext {
        val errorType = when (exception) {
            is ApiException -> when {
                exception.message?.contains("timeout", ignoreCase = true) == true -> 
                    ErrorHandlingManager.ErrorType.API_TIMEOUT
                exception.message?.contains("network", ignoreCase = true) == true -> 
                    ErrorHandlingManager.ErrorType.NETWORK_ERROR
                exception.message?.contains("rate limit", ignoreCase = true) == true -> 
                    ErrorHandlingManager.ErrorType.RATE_LIMIT_ERROR
                else -> ErrorHandlingManager.ErrorType.PARSING_FAILURE
            }
            else -> ErrorHandlingManager.ErrorType.UNKNOWN_ERROR
        }
        
        return ErrorHandlingManager.ErrorContext(
            errorType = errorType,
            originalText = originalText,
            exception = exception,
            retryCount = retryCount,
            networkAvailable = offlineModeHandler.isNetworkAvailable()
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
        return (1000 * kotlin.math.pow(2.0, retryCount.toDouble())).toLong() // Exponential backoff
    }
    
    private suspend fun handleApiError(errorContext: ErrorHandlingManager.ErrorContext) {
        val handlingResult = errorHandlingManager.handleError(errorContext)
        
        when (handlingResult.recoveryStrategy) {
            ErrorHandlingManager.RecoveryStrategy.OFFLINE_MODE -> {
                handleOfflineProcessing(errorContext.originalText)
            }
            ErrorHandlingManager.RecoveryStrategy.FALLBACK_EVENT_CREATION -> {
                if (handlingResult.recoveredResult != null) {
                    createCalendarEventWithFallback(handlingResult.recoveredResult)
                } else {
                    userFeedbackManager.showErrorMessage(handlingResult.userMessage)
                    finish()
                }
            }
            else -> {
                userFeedbackManager.showErrorMessage(handlingResult.userMessage)
                finish()
            }
        }
    }
    
    private suspend fun handleUnexpectedError(errorContext: ErrorHandlingManager.ErrorContext) {
        val handlingResult = errorHandlingManager.handleError(errorContext)
        userFeedbackManager.showErrorMessage(handlingResult.userMessage)
        finish()
    }
    
    private suspend fun handleMaxRetriesExceeded(errorContext: ErrorHandlingManager.ErrorContext) {
        val handlingResult = errorHandlingManager.handleError(errorContext)
        
        if (handlingResult.recoveryStrategy == ErrorHandlingManager.RecoveryStrategy.OFFLINE_MODE) {
            handleOfflineProcessing(errorContext.originalText)
        } else {
            userFeedbackManager.showErrorMessage("Failed after multiple attempts: ${handlingResult.userMessage}")
            finish()
        }
    }
    
    private suspend fun createCalendarEventWithFallback(result: ParseResult) {
        try {
            val success = calendarIntentHelper.createCalendarEvent(result)
            
            if (success) {
                userFeedbackManager.showSuccessMessage("Calendar event created successfully!")
                finish()
            } else {
                handleCalendarLaunchFailure(result)
            }
            
        } catch (e: Exception) {
            val errorContext = ErrorHandlingManager.ErrorContext(
                errorType = ErrorHandlingManager.ErrorType.CALENDAR_LAUNCH_FAILURE,
                originalText = result.originalText ?: "",
                apiResponse = result,
                exception = e
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
        try {
            // Try alternative launch strategies including web calendar fallback
            val launchResult = calendarIntentHelper.launchCalendarWithFallbacks(result)
            
            if (launchResult.success) {
                userFeedbackManager.showSuccessMessage("Calendar event created successfully!")
                finish()
            } else {
                offerManualEventCreation(result)
            }
            
        } catch (e: Exception) {
            offerManualEventCreation(result)
        }
    }
    
    private suspend fun offerManualEventCreation(result: ParseResult) {
        // Show calendar not found dialog which will handle clipboard copying internally
        userFeedbackManager.showCalendarNotFoundDialog(result, emptyList())
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
            val clipboardManager = getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
            val clipData = android.content.ClipData.newPlainText("Calendar Event", eventDetails)
            clipboardManager.setPrimaryClip(clipData)
        } catch (e: Exception) {
            // Fallback if clipboard access fails
            showError("Failed to copy to clipboard: ${e.message}")
        }
    }
    
    private fun showError(message: String) {
        Toast.makeText(this, message, Toast.LENGTH_LONG).show()
    }
}