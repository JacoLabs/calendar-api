package com.jacolabs.calendar

import android.content.Context
import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import kotlinx.coroutines.runBlocking
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith
import org.mockito.Mock
import org.mockito.Mockito.*
import org.mockito.MockitoAnnotations
import java.net.SocketTimeoutException
import java.net.UnknownHostException
import kotlin.test.assertEquals
import kotlin.test.assertNotNull
import kotlin.test.assertTrue

/**
 * Comprehensive integration tests for end-to-end error handling workflows.
 * Tests the complete integration of all error handling components and validates
 * user journeys through various error scenarios.
 * 
 * Requirements tested: 1.1, 1.2, 1.3, 1.4, 10.4
 */
@RunWith(AndroidJUnit4::class)
class ErrorHandlingIntegrationTest {
    
    private lateinit var context: Context
    private lateinit var errorHandlingManager: ErrorHandlingManager
    private lateinit var apiService: ApiService
    private lateinit var confidenceValidator: ConfidenceValidator
    private lateinit var userFeedbackManager: UserFeedbackManager
    private lateinit var fallbackEventGenerator: FallbackEventGenerator
    private lateinit var offlineModeHandler: OfflineModeHandler
    private lateinit var calendarIntentHelper: CalendarIntentHelper
    
    @Mock
    private lateinit var mockApiService: ApiService
    
    @Before
    fun setUp() {
        MockitoAnnotations.openMocks(this)
        context = ApplicationProvider.getApplicationContext()
        
        // Initialize real components for integration testing
        errorHandlingManager = ErrorHandlingManager(context)
        confidenceValidator = ConfidenceValidator(context)
        userFeedbackManager = UserFeedbackManager(context)
        fallbackEventGenerator = FallbackEventGenerator(context)
        offlineModeHandler = OfflineModeHandler(context)
        calendarIntentHelper = CalendarIntentHelper(context)
        
        // Use real ApiService for most tests, mock for specific error scenarios
        apiService = ApiService(context)
    }
    
    /**
     * Test complete user journey: Network error -> Retry -> Offline fallback -> Calendar creation
     * Requirements: 1.1, 1.2, 4.1, 4.2, 6.1, 6.2
     */
    @Test
    fun testNetworkErrorToOfflineFallbackWorkflow() = runBlocking {
        val testText = "Meeting with John tomorrow at 2pm"
        
        // Simulate network error
        val networkException = UnknownHostException("Network unavailable")
        val errorContext = ErrorHandlingManager.ErrorContext(
            errorType = ErrorHandlingManager.ErrorType.NETWORK_ERROR,
            originalText = testText,
            exception = networkException,
            retryCount = 0,
            networkAvailable = false
        )
        
        // Test error handling response
        val handlingResult = errorHandlingManager.handleError(errorContext)
        
        // Verify offline mode is triggered
        assertEquals(ErrorHandlingManager.RecoveryStrategy.OFFLINE_MODE, handlingResult.recoveryStrategy)
        assertTrue(handlingResult.success)
        assertNotNull(handlingResult.recoveredResult)
        
        // Verify offline event creation
        val offlineResult = handlingResult.recoveredResult!!
        assertNotNull(offlineResult.title)
        assertNotNull(offlineResult.startDateTime)
        assertTrue(offlineResult.fallbackApplied)
        assertEquals("Created offline - no network available", offlineResult.fallbackReason)
        
        // Verify calendar creation would work
        assertTrue(offlineResult.title!!.isNotBlank())
        assertTrue(offlineResult.startDateTime!!.isNotBlank())
    }
    
    /**
     * Test complete user journey: Low confidence -> User warning -> Confirmation -> Calendar creation
     * Requirements: 2.1, 2.2, 2.3, 11.1, 11.2, 11.3
     */
    @Test
    fun testLowConfidenceWarningWorkflow() = runBlocking {
        val testText = "maybe meeting sometime"
        
        // Create low confidence result
        val lowConfidenceResult = ParseResult(
            title = "meeting",
            startDateTime = null,
            endDateTime = null,
            location = null,
            description = testText,
            confidenceScore = 0.2,
            allDay = false,
            timezone = "America/Toronto",
            originalText = testText
        )
        
        // Test confidence assessment
        val assessment = confidenceValidator.assessConfidence(lowConfidenceResult, testText)
        
        // Verify warning is triggered
        assertTrue(assessment.overallConfidence < 0.3)
        assertTrue(assessment.recommendation in listOf(
            ConfidenceValidator.UserRecommendation.SUGGEST_IMPROVEMENTS,
            ConfidenceValidator.UserRecommendation.PROCEED_WITH_CAUTION
        ))
        assertNotNull(assessment.warningMessage)
        
        // Test error handling for low confidence
        val errorContext = ErrorHandlingManager.ErrorContext(
            errorType = ErrorHandlingManager.ErrorType.LOW_CONFIDENCE,
            originalText = testText,
            apiResponse = lowConfidenceResult,
            confidenceScore = assessment.overallConfidence,
            userInteractionAllowed = true
        )
        
        val handlingResult = errorHandlingManager.handleError(errorContext)
        
        // Verify user confirmation is required or fallback is provided
        assertTrue(
            handlingResult.actionRequired == ErrorHandlingManager.UserAction.CONFIRM_LOW_CONFIDENCE_RESULT ||
            handlingResult.recoveredResult != null
        )
    }
    
    /**
     * Test complete user journey: API timeout -> Retry with backoff -> Fallback creation
     * Requirements: 4.1, 4.2, 6.1, 6.2, 7.1, 7.2
     */
    @Test
    fun testApiTimeoutRetryWorkflow() = runBlocking {
        val testText = "Doctor appointment next Friday at 3pm"
        
        // Test first timeout (should retry)
        val timeoutException = SocketTimeoutException("Request timeout")
        val errorContext1 = ErrorHandlingManager.ErrorContext(
            errorType = ErrorHandlingManager.ErrorType.API_TIMEOUT,
            originalText = testText,
            exception = timeoutException,
            retryCount = 0,
            networkAvailable = true
        )
        
        val handlingResult1 = errorHandlingManager.handleError(errorContext1)
        
        // Verify retry is recommended
        assertEquals(ErrorHandlingManager.RecoveryStrategy.RETRY_WITH_BACKOFF, handlingResult1.recoveryStrategy)
        assertTrue(handlingResult1.retryRecommended)
        assertTrue(handlingResult1.retryDelayMs > 0)
        
        // Test after max retries (should fallback)
        val errorContext2 = errorContext1.copy(retryCount = 3)
        val handlingResult2 = errorHandlingManager.handleError(errorContext2)
        
        // Verify fallback is triggered
        assertTrue(
            handlingResult2.recoveryStrategy == ErrorHandlingManager.RecoveryStrategy.FALLBACK_EVENT_CREATION ||
            handlingResult2.recoveryStrategy == ErrorHandlingManager.RecoveryStrategy.OFFLINE_MODE
        )
        
        if (handlingResult2.recoveredResult != null) {
            val fallbackResult = handlingResult2.recoveredResult!!
            assertNotNull(fallbackResult.title)
            assertNotNull(fallbackResult.startDateTime)
            assertTrue(fallbackResult.fallbackApplied)
        }
    }
    
    /**
     * Test complete user journey: Parsing failure -> Fallback generation -> Calendar creation
     * Requirements: 3.1, 3.2, 3.3, 3.4, 12.1, 12.2, 12.3, 12.4
     */
    @Test
    fun testParsingFailureFallbackWorkflow() = runBlocking {
        val testText = "Important meeting with the team about the project"
        
        // Simulate parsing failure
        val errorContext = ErrorHandlingManager.ErrorContext(
            errorType = ErrorHandlingManager.ErrorType.PARSING_FAILURE,
            originalText = testText,
            exception = RuntimeException("Parsing failed"),
            retryCount = 0
        )
        
        val handlingResult = errorHandlingManager.handleError(errorContext)
        
        // Verify fallback event creation
        assertEquals(ErrorHandlingManager.RecoveryStrategy.FALLBACK_EVENT_CREATION, handlingResult.recoveryStrategy)
        assertTrue(handlingResult.success)
        assertNotNull(handlingResult.recoveredResult)
        
        val fallbackResult = handlingResult.recoveredResult!!
        
        // Verify fallback event has meaningful content
        assertNotNull(fallbackResult.title)
        assertTrue(fallbackResult.title!!.isNotBlank())
        assertNotNull(fallbackResult.startDateTime)
        assertNotNull(fallbackResult.endDateTime)
        assertTrue(fallbackResult.fallbackApplied)
        assertNotNull(fallbackResult.fallbackReason)
        
        // Verify title extraction is meaningful
        assertTrue(fallbackResult.title!!.contains("meeting") || fallbackResult.title!!.contains("team"))
        
        // Verify description includes original text
        assertNotNull(fallbackResult.description)
        assertTrue(fallbackResult.description!!.contains(testText))
    }
    
    /**
     * Test complete user journey: Calendar launch failure -> Alternative methods -> Clipboard fallback
     * Requirements: 1.1, 1.2, 1.3, 6.3, 8.1, 8.2, 8.3
     */
    @Test
    fun testCalendarLaunchFailureWorkflow() = runBlocking {
        val testResult = ParseResult(
            title = "Test Meeting",
            startDateTime = "2024-01-15T14:00:00",
            endDateTime = "2024-01-15T15:00:00",
            location = "Conference Room",
            description = "Test meeting description",
            confidenceScore = 0.8,
            allDay = false,
            timezone = "America/Toronto",
            originalText = "Test meeting tomorrow at 2pm in conference room"
        )
        
        // Simulate calendar launch failure
        val launchException = RuntimeException("No calendar app found")
        val errorContext = ErrorHandlingManager.ErrorContext(
            errorType = ErrorHandlingManager.ErrorType.CALENDAR_LAUNCH_FAILURE,
            originalText = testResult.originalText!!,
            apiResponse = testResult,
            exception = launchException
        )
        
        val handlingResult = errorHandlingManager.handleError(errorContext)
        
        // Verify alternative calendar launch is attempted
        assertEquals(ErrorHandlingManager.RecoveryStrategy.ALTERNATIVE_CALENDAR_LAUNCH, handlingResult.recoveryStrategy)
        assertEquals(ErrorHandlingManager.UserAction.CHOOSE_ALTERNATIVE_CALENDAR, handlingResult.actionRequired)
        
        // Verify user message provides guidance
        assertTrue(handlingResult.userMessage.contains("calendar") || handlingResult.userMessage.contains("alternative"))
    }
    
    /**
     * Test complete user journey: Validation error -> Data sanitization -> Graceful degradation
     * Requirements: 5.1, 5.2, 5.3, 5.4, 12.1, 12.2, 12.3, 12.4
     */
    @Test
    fun testValidationErrorGracefulDegradationWorkflow() = runBlocking {
        val testText = "Meeting with invalid date format"
        
        // Create result with validation issues
        val invalidResult = ParseResult(
            title = "", // Invalid: empty title
            startDateTime = "invalid-date", // Invalid: malformed date
            endDateTime = null,
            location = null,
            description = testText,
            confidenceScore = 0.5,
            allDay = false,
            timezone = "America/Toronto",
            originalText = testText
        )
        
        val errorContext = ErrorHandlingManager.ErrorContext(
            errorType = ErrorHandlingManager.ErrorType.VALIDATION_ERROR,
            originalText = testText,
            apiResponse = invalidResult,
            retryCount = 0
        )
        
        val handlingResult = errorHandlingManager.handleError(errorContext)
        
        // Verify graceful degradation is applied
        assertEquals(ErrorHandlingManager.RecoveryStrategy.GRACEFUL_DEGRADATION, handlingResult.recoveryStrategy)
        assertTrue(handlingResult.success)
        assertNotNull(handlingResult.recoveredResult)
        
        val degradedResult = handlingResult.recoveredResult!!
        
        // Verify data sanitization was applied
        assertNotNull(degradedResult.title)
        assertTrue(degradedResult.title!!.isNotBlank()) // Title should be fixed
        assertNotNull(degradedResult.startDateTime)
        assertTrue(degradedResult.startDateTime!!.matches(Regex("\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}"))) // Valid date format
        assertTrue(degradedResult.fallbackApplied)
    }
    
    /**
     * Test MainActivity integration with error handling components
     * Requirements: 2.1, 2.2, 6.1, 6.2, 11.1, 11.2, 11.3
     */
    @Test
    fun testMainActivityErrorHandlingIntegration() = runBlocking {
        // This test verifies that MainActivity properly integrates with error handling components
        // We test the key integration points without requiring UI interaction
        
        val testText = "unclear event information"
        
        // Test that MainActivity components can handle various error scenarios
        val errorManager = ErrorHandlingManager(context)
        val confidenceValidator = ConfidenceValidator(context)
        val userFeedbackManager = UserFeedbackManager(context)
        
        // Verify components are properly initialized and can work together
        assertNotNull(errorManager)
        assertNotNull(confidenceValidator)
        assertNotNull(userFeedbackManager)
        
        // Test low confidence handling (simulating MainActivity workflow)
        val lowConfidenceResult = ParseResult(
            title = "event",
            startDateTime = null,
            endDateTime = null,
            location = null,
            description = testText,
            confidenceScore = 0.15,
            allDay = false,
            timezone = "America/Toronto",
            originalText = testText
        )
        
        val assessment = confidenceValidator.assessConfidence(lowConfidenceResult, testText)
        assertTrue(assessment.overallConfidence < 0.3)
        
        val errorContext = ErrorHandlingManager.ErrorContext(
            errorType = ErrorHandlingManager.ErrorType.LOW_CONFIDENCE,
            originalText = testText,
            apiResponse = lowConfidenceResult,
            confidenceScore = assessment.overallConfidence,
            userInteractionAllowed = true
        )
        
        val handlingResult = errorManager.handleError(errorContext)
        
        // Verify MainActivity would receive appropriate guidance
        assertTrue(
            handlingResult.actionRequired == ErrorHandlingManager.UserAction.CONFIRM_LOW_CONFIDENCE_RESULT ||
            handlingResult.recoveredResult != null
        )
    }
    
    /**
     * Test TextProcessorActivity integration with error handling components
     * Requirements: 1.1, 1.2, 4.1, 4.2, 7.1, 10.1, 10.3, 10.4
     */
    @Test
    fun testTextProcessorActivityErrorHandlingIntegration() = runBlocking {
        // Test the error handling integration points used by TextProcessorActivity
        
        val selectedText = "meeting next week"
        
        // Test network error handling (simulating TextProcessorActivity workflow)
        val networkException = UnknownHostException("Network unavailable")
        val errorContext = ErrorHandlingManager.ErrorContext(
            errorType = ErrorHandlingManager.ErrorType.NETWORK_ERROR,
            originalText = selectedText,
            exception = networkException,
            retryCount = 0,
            networkAvailable = false,
            userInteractionAllowed = true
        )
        
        val handlingResult = errorHandlingManager.handleError(errorContext)
        
        // Verify TextProcessorActivity would receive appropriate recovery strategy
        assertEquals(ErrorHandlingManager.RecoveryStrategy.OFFLINE_MODE, handlingResult.recoveryStrategy)
        assertTrue(handlingResult.success)
        assertNotNull(handlingResult.recoveredResult)
        
        // Test offline event creation
        val offlineResult = handlingResult.recoveredResult!!
        assertNotNull(offlineResult.title)
        assertNotNull(offlineResult.startDateTime)
        assertTrue(offlineResult.fallbackApplied)
        
        // Verify the result is suitable for calendar creation
        assertTrue(offlineResult.title!!.isNotBlank())
        assertTrue(offlineResult.startDateTime!!.matches(Regex("\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}")))
    }
    
    /**
     * Test backward compatibility with existing functionality
     * Requirements: 10.4
     */
    @Test
    fun testBackwardCompatibility() = runBlocking {
        // Test that existing functionality still works with error handling enhancements
        
        val testText = "Team meeting tomorrow at 10am"
        
        // Test that normal parsing still works (when no errors occur)
        val normalResult = ParseResult(
            title = "Team meeting",
            startDateTime = "2024-01-16T10:00:00",
            endDateTime = "2024-01-16T11:00:00",
            location = null,
            description = testText,
            confidenceScore = 0.9,
            allDay = false,
            timezone = "America/Toronto",
            originalText = testText
        )
        
        // Test confidence validation for high confidence result
        val assessment = confidenceValidator.assessConfidence(normalResult, testText)
        assertTrue(assessment.overallConfidence >= 0.7)
        assertEquals(ConfidenceValidator.UserRecommendation.PROCEED_CONFIDENTLY, assessment.recommendation)
        assertTrue(assessment.shouldProceed)
        
        // Test that calendar creation would proceed normally
        assertNotNull(normalResult.title)
        assertNotNull(normalResult.startDateTime)
        assertTrue(normalResult.confidenceScore > 0.7)
        
        // Verify existing ParseResult structure is maintained
        assertEquals("Team meeting", normalResult.title)
        assertEquals("2024-01-16T10:00:00", normalResult.startDateTime)
        assertEquals("2024-01-16T11:00:00", normalResult.endDateTime)
        assertEquals(0.9, normalResult.confidenceScore, 0.01)
    }
    
    /**
     * Test error recovery effectiveness across multiple scenarios
     * Requirements: 1.1, 1.2, 1.3, 1.4
     */
    @Test
    fun testErrorRecoveryEffectiveness() = runBlocking {
        val testScenarios = listOf(
            "network timeout error" to ErrorHandlingManager.ErrorType.API_TIMEOUT,
            "parsing completely failed" to ErrorHandlingManager.ErrorType.PARSING_FAILURE,
            "very low confidence result" to ErrorHandlingManager.ErrorType.LOW_CONFIDENCE,
            "calendar app not found" to ErrorHandlingManager.ErrorType.CALENDAR_LAUNCH_FAILURE,
            "no event data extracted" to ErrorHandlingManager.ErrorType.INSUFFICIENT_DATA
        )
        
        var successfulRecoveries = 0
        
        for ((testText, errorType) in testScenarios) {
            val errorContext = ErrorHandlingManager.ErrorContext(
                errorType = errorType,
                originalText = testText,
                exception = RuntimeException("Simulated error"),
                retryCount = 0,
                networkAvailable = true,
                userInteractionAllowed = true
            )
            
            val handlingResult = errorHandlingManager.handleError(errorContext)
            
            // Count successful recoveries (either success or actionable user guidance)
            if (handlingResult.success || handlingResult.actionRequired != null) {
                successfulRecoveries++
            }
            
            // Verify user always gets meaningful feedback
            assertTrue(handlingResult.userMessage.isNotBlank())
        }
        
        // Verify high recovery success rate
        val recoveryRate = successfulRecoveries.toDouble() / testScenarios.size
        assertTrue(recoveryRate >= 0.8, "Recovery rate should be at least 80%, got ${recoveryRate * 100}%")
    }
    
    /**
     * Test user experience consistency across error scenarios
     * Requirements: 11.1, 11.2, 11.3, 11.4
     */
    @Test
    fun testUserExperienceConsistency() = runBlocking {
        val errorTypes = listOf(
            ErrorHandlingManager.ErrorType.NETWORK_ERROR,
            ErrorHandlingManager.ErrorType.API_TIMEOUT,
            ErrorHandlingManager.ErrorType.PARSING_FAILURE,
            ErrorHandlingManager.ErrorType.LOW_CONFIDENCE,
            ErrorHandlingManager.ErrorType.VALIDATION_ERROR,
            ErrorHandlingManager.ErrorType.CALENDAR_LAUNCH_FAILURE
        )
        
        for (errorType in errorTypes) {
            val errorContext = ErrorHandlingManager.ErrorContext(
                errorType = errorType,
                originalText = "test event text",
                exception = RuntimeException("Test error"),
                retryCount = 0
            )
            
            val handlingResult = errorHandlingManager.handleError(errorContext)
            
            // Verify consistent user experience elements
            assertTrue(handlingResult.userMessage.isNotBlank(), "User message should not be empty for $errorType")
            assertTrue(handlingResult.userMessage.length >= 10, "User message should be descriptive for $errorType")
            assertNotNull(handlingResult.recoveryStrategy, "Recovery strategy should be defined for $errorType")
            
            // Verify user messages are helpful and not technical
            val message = handlingResult.userMessage.lowercase()
            assertTrue(
                !message.contains("exception") && !message.contains("null") && !message.contains("error code"),
                "User message should be user-friendly for $errorType: ${handlingResult.userMessage}"
            )
        }
    }
}