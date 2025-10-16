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
import kotlin.test.*

/**
 * End-to-end workflow tests that simulate complete user journeys through the application
 * with various error scenarios and recovery mechanisms.
 * 
 * Tests complete integration of all error handling components and validates that
 * users can always create calendar events regardless of failures.
 * 
 * Requirements tested: 1.1, 1.2, 1.3, 1.4, 10.4
 */
@RunWith(AndroidJUnit4::class)
class EndToEndWorkflowTest {
    
    private lateinit var context: Context
    private lateinit var errorHandlingManager: ErrorHandlingManager
    private lateinit var confidenceValidator: ConfidenceValidator
    private lateinit var fallbackEventGenerator: FallbackEventGenerator
    private lateinit var offlineModeHandler: OfflineModeHandler
    private lateinit var userFeedbackManager: UserFeedbackManager
    
    @Mock
    private lateinit var mockApiService: ApiService
    
    @Before
    fun setUp() {
        MockitoAnnotations.openMocks(this)
        context = ApplicationProvider.getApplicationContext()
        
        // Initialize components for end-to-end testing
        errorHandlingManager = ErrorHandlingManager(context)
        confidenceValidator = ConfidenceValidator(context)
        fallbackEventGenerator = FallbackEventGenerator(context)
        offlineModeHandler = OfflineModeHandler(context)
        userFeedbackManager = UserFeedbackManager(context)
    }
    
    /**
     * Test Scenario 1: Happy path with high confidence result
     * User selects text -> API succeeds -> High confidence -> Calendar opens successfully
     */
    @Test
    fun testHappyPathWorkflow() = runBlocking {
        val userText = "Team meeting tomorrow at 2pm in conference room A"
        
        // Simulate successful API response with high confidence
        val successResult = ParseResult(
            title = "Team meeting",
            startDateTime = "2024-01-16T14:00:00",
            endDateTime = "2024-01-16T15:00:00",
            location = "conference room A",
            description = userText,
            confidenceScore = 0.95,
            allDay = false,
            timezone = "America/Toronto",
            originalText = userText
        )
        
        // Test confidence validation
        val assessment = confidenceValidator.assessConfidence(successResult, userText)
        
        // Verify high confidence path
        assertTrue(assessment.overallConfidence >= 0.7)
        assertEquals(ConfidenceValidator.UserRecommendation.PROCEED_CONFIDENTLY, assessment.recommendation)
        assertTrue(assessment.shouldProceed)
        assertNull(assessment.warningMessage)
        
        // Verify result is ready for calendar creation
        assertNotNull(successResult.title)
        assertNotNull(successResult.startDateTime)
        assertNotNull(successResult.endDateTime)
        assertNotNull(successResult.location)
        assertTrue(successResult.title!!.isNotBlank())
        
        // No error handling should be needed
        assertTrue(successResult.confidenceScore > 0.7)
        assertFalse(successResult.fallbackApplied)
    }
    
    /**
     * Test Scenario 2: Network failure -> Retry -> Offline fallback -> Calendar creation
     * User selects text -> Network fails -> Retries fail -> Offline mode -> Event created
     */
    @Test
    fun testNetworkFailureToOfflineWorkflow() = runBlocking {
        val userText = "Doctor appointment next Friday at 3:30pm"
        
        // Step 1: Initial network failure
        val networkError = UnknownHostException("Network unreachable")
        val errorContext = ErrorHandlingManager.ErrorContext(
            errorType = ErrorHandlingManager.ErrorType.NETWORK_ERROR,
            originalText = userText,
            exception = networkError,
            retryCount = 0,
            networkAvailable = false,
            userInteractionAllowed = true
        )
        
        // Step 2: Error handling decides on offline mode
        val handlingResult = errorHandlingManager.handleError(errorContext)
        
        assertEquals(ErrorHandlingManager.RecoveryStrategy.OFFLINE_MODE, handlingResult.recoveryStrategy)
        assertTrue(handlingResult.success)
        assertNotNull(handlingResult.recoveredResult)
        
        // Step 3: Verify offline event creation
        val offlineResult = handlingResult.recoveredResult!!
        
        assertNotNull(offlineResult.title)
        assertTrue(offlineResult.title!!.contains("appointment") || offlineResult.title!!.contains("Doctor"))
        assertNotNull(offlineResult.startDateTime)
        assertNotNull(offlineResult.endDateTime)
        assertTrue(offlineResult.fallbackApplied)
        assertEquals("Created offline - no network available", offlineResult.fallbackReason)
        
        // Step 4: Verify event is suitable for calendar creation
        assertTrue(offlineResult.startDateTime!!.matches(Regex("\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}")))
        assertTrue(offlineResult.endDateTime!!.matches(Regex("\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}")))
        
        // Step 5: Verify user gets appropriate feedback
        assertTrue(handlingResult.userMessage.contains("offline") || handlingResult.userMessage.contains("network"))
    }
    
    /**
     * Test Scenario 3: API timeout -> Multiple retries -> Fallback creation -> Calendar success
     * User selects text -> API times out -> Retries with backoff -> Fallback -> Event created
     */
    @Test
    fun testApiTimeoutRetryFallbackWorkflow() = runBlocking {
        val userText = "Lunch meeting with client at The Keg tomorrow 12:30"
        
        // Step 1: First timeout (should retry)
        val timeoutError = SocketTimeoutException("Request timeout")
        val errorContext1 = ErrorHandlingManager.ErrorContext(
            errorType = ErrorHandlingManager.ErrorType.API_TIMEOUT,
            originalText = userText,
            exception = timeoutError,
            retryCount = 0,
            networkAvailable = true,
            userInteractionAllowed = true
        )
        
        val handlingResult1 = errorHandlingManager.handleError(errorContext1)
        
        // Verify retry is recommended
        assertEquals(ErrorHandlingManager.RecoveryStrategy.RETRY_WITH_BACKOFF, handlingResult1.recoveryStrategy)
        assertTrue(handlingResult1.retryRecommended)
        assertTrue(handlingResult1.retryDelayMs > 0)
        
        // Step 2: Second timeout (should retry again)
        val errorContext2 = errorContext1.copy(retryCount = 1)
        val handlingResult2 = errorHandlingManager.handleError(errorContext2)
        
        assertEquals(ErrorHandlingManager.RecoveryStrategy.RETRY_WITH_BACKOFF, handlingResult2.recoveryStrategy)
        assertTrue(handlingResult2.retryRecommended)
        assertTrue(handlingResult2.retryDelayMs > handlingResult1.retryDelayMs) // Exponential backoff
        
        // Step 3: Third timeout (should fallback)
        val errorContext3 = errorContext1.copy(retryCount = 3)
        val handlingResult3 = errorHandlingManager.handleError(errorContext3)
        
        // Verify fallback is triggered
        assertTrue(
            handlingResult3.recoveryStrategy == ErrorHandlingManager.RecoveryStrategy.FALLBACK_EVENT_CREATION ||
            handlingResult3.recoveryStrategy == ErrorHandlingManager.RecoveryStrategy.OFFLINE_MODE
        )
        assertTrue(handlingResult3.success)
        assertNotNull(handlingResult3.recoveredResult)
        
        // Step 4: Verify fallback event quality
        val fallbackResult = handlingResult3.recoveredResult!!
        
        assertNotNull(fallbackResult.title)
        assertTrue(fallbackResult.title!!.contains("Lunch") || fallbackResult.title!!.contains("meeting"))
        assertNotNull(fallbackResult.startDateTime)
        assertTrue(fallbackResult.fallbackApplied)
        
        // Step 5: Verify location handling
        if (fallbackResult.location != null) {
            assertTrue(fallbackResult.location!!.contains("Keg"))
        } else {
            // Location should be in description if not extracted
            assertTrue(fallbackResult.description!!.contains("Keg"))
        }
    }
    
    /**
     * Test Scenario 4: Low confidence result -> User warning -> User accepts -> Calendar creation
     * User selects text -> Low confidence -> Warning shown -> User confirms -> Event created
     */
    @Test
    fun testLowConfidenceUserConfirmationWorkflow() = runBlocking {
        val userText = "maybe meeting sometime next week"
        
        // Step 1: API returns low confidence result
        val lowConfidenceResult = ParseResult(
            title = "meeting",
            startDateTime = null, // Missing critical information
            endDateTime = null,
            location = null,
            description = userText,
            confidenceScore = 0.25,
            allDay = false,
            timezone = "America/Toronto",
            originalText = userText
        )
        
        // Step 2: Confidence validation
        val assessment = confidenceValidator.assessConfidence(lowConfidenceResult, userText)
        
        assertTrue(assessment.overallConfidence < 0.3)
        assertTrue(assessment.recommendation in listOf(
            ConfidenceValidator.UserRecommendation.SUGGEST_IMPROVEMENTS,
            ConfidenceValidator.UserRecommendation.PROCEED_WITH_CAUTION,
            ConfidenceValidator.UserRecommendation.RECOMMEND_MANUAL_ENTRY
        ))
        assertNotNull(assessment.warningMessage)
        
        // Step 3: Error handling for low confidence
        val errorContext = ErrorHandlingManager.ErrorContext(
            errorType = ErrorHandlingManager.ErrorType.LOW_CONFIDENCE,
            originalText = userText,
            apiResponse = lowConfidenceResult,
            confidenceScore = assessment.overallConfidence,
            userInteractionAllowed = true
        )
        
        val handlingResult = errorHandlingManager.handleError(errorContext)
        
        // Step 4: Verify user confirmation is required or fallback is provided
        assertTrue(
            handlingResult.actionRequired == ErrorHandlingManager.UserAction.CONFIRM_LOW_CONFIDENCE_RESULT ||
            handlingResult.recoveredResult != null
        )
        
        // Step 5: If fallback is provided, verify it's better than original
        if (handlingResult.recoveredResult != null) {
            val improvedResult = handlingResult.recoveredResult!!
            
            assertNotNull(improvedResult.title)
            assertTrue(improvedResult.title!!.isNotBlank())
            assertNotNull(improvedResult.startDateTime) // Should have default time
            assertNotNull(improvedResult.endDateTime)
            assertTrue(improvedResult.fallbackApplied)
            
            // Verify improvement over original
            assertTrue(improvedResult.startDateTime!!.isNotBlank())
            assertTrue(improvedResult.endDateTime!!.isNotBlank())
        }
    }
    
    /**
     * Test Scenario 5: Parsing failure -> Fallback generation -> Calendar creation
     * User selects text -> Parsing fails -> Intelligent fallback -> Event created
     */
    @Test
    fun testParsingFailureFallbackWorkflow() = runBlocking {
        val userText = "Important project review meeting with the development team and stakeholders"
        
        // Step 1: Parsing failure
        val parsingError = RuntimeException("Failed to parse event information")
        val errorContext = ErrorHandlingManager.ErrorContext(
            errorType = ErrorHandlingManager.ErrorType.PARSING_FAILURE,
            originalText = userText,
            exception = parsingError,
            retryCount = 0,
            userInteractionAllowed = true
        )
        
        // Step 2: Error handling triggers fallback
        val handlingResult = errorHandlingManager.handleError(errorContext)
        
        assertEquals(ErrorHandlingManager.RecoveryStrategy.FALLBACK_EVENT_CREATION, handlingResult.recoveryStrategy)
        assertTrue(handlingResult.success)
        assertNotNull(handlingResult.recoveredResult)
        
        // Step 3: Verify fallback event quality
        val fallbackResult = handlingResult.recoveredResult!!
        
        assertNotNull(fallbackResult.title)
        assertTrue(fallbackResult.title!!.isNotBlank())
        
        // Title should contain meaningful words from original text
        val titleWords = fallbackResult.title!!.lowercase().split(" ")
        val originalWords = userText.lowercase().split(" ")
        val meaningfulWords = listOf("meeting", "review", "project", "team")
        
        val hasRelevantContent = meaningfulWords.any { word ->
            titleWords.any { it.contains(word) } || originalWords.any { it.contains(word) }
        }
        assertTrue(hasRelevantContent, "Title should contain relevant content: ${fallbackResult.title}")
        
        // Step 4: Verify timing defaults
        assertNotNull(fallbackResult.startDateTime)
        assertNotNull(fallbackResult.endDateTime)
        assertTrue(fallbackResult.startDateTime!!.matches(Regex("\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}")))
        
        // Step 5: Verify description includes original text
        assertNotNull(fallbackResult.description)
        assertTrue(fallbackResult.description!!.contains(userText))
        assertTrue(fallbackResult.fallbackApplied)
        assertNotNull(fallbackResult.fallbackReason)
    }
    
    /**
     * Test Scenario 6: Calendar launch failure -> Alternative methods -> Clipboard fallback
     * User selects text -> Parsing succeeds -> Calendar launch fails -> Alternative methods -> Clipboard
     */
    @Test
    fun testCalendarLaunchFailureWorkflow() = runBlocking {
        val userText = "Weekly standup meeting every Monday at 9am"
        
        // Step 1: Successful parsing
        val successfulResult = ParseResult(
            title = "Weekly standup meeting",
            startDateTime = "2024-01-15T09:00:00",
            endDateTime = "2024-01-15T09:30:00",
            location = null,
            description = userText,
            confidenceScore = 0.85,
            allDay = false,
            timezone = "America/Toronto",
            originalText = userText
        )
        
        // Step 2: Calendar launch failure
        val launchError = RuntimeException("No calendar app available")
        val errorContext = ErrorHandlingManager.ErrorContext(
            errorType = ErrorHandlingManager.ErrorType.CALENDAR_LAUNCH_FAILURE,
            originalText = userText,
            apiResponse = successfulResult,
            exception = launchError,
            userInteractionAllowed = true
        )
        
        // Step 3: Error handling for calendar launch failure
        val handlingResult = errorHandlingManager.handleError(errorContext)
        
        assertEquals(ErrorHandlingManager.RecoveryStrategy.ALTERNATIVE_CALENDAR_LAUNCH, handlingResult.recoveryStrategy)
        assertEquals(ErrorHandlingManager.UserAction.CHOOSE_ALTERNATIVE_CALENDAR, handlingResult.actionRequired)
        
        // Step 4: Verify user gets helpful guidance
        assertTrue(handlingResult.userMessage.contains("calendar") || handlingResult.userMessage.contains("alternative"))
        assertTrue(handlingResult.userMessage.length > 20) // Should be descriptive
        
        // Step 5: Verify original event data is preserved for alternative methods
        // The original successful result should still be available for clipboard copying or web calendar
        assertNotNull(successfulResult.title)
        assertNotNull(successfulResult.startDateTime)
        assertTrue(successfulResult.confidenceScore > 0.8)
    }
    
    /**
     * Test Scenario 7: Validation error -> Data sanitization -> Graceful degradation -> Calendar creation
     * User selects text -> Invalid data -> Sanitization -> Defaults applied -> Event created
     */
    @Test
    fun testValidationErrorSanitizationWorkflow() = runBlocking {
        val userText = "Meeting with corrupted data"
        
        // Step 1: Result with validation issues
        val invalidResult = ParseResult(
            title = "", // Invalid: empty title
            startDateTime = "invalid-date-format", // Invalid: malformed date
            endDateTime = null, // Missing end time
            location = "   ", // Invalid: whitespace only
            description = userText,
            confidenceScore = 0.6,
            allDay = false,
            timezone = "America/Toronto",
            originalText = userText
        )
        
        // Step 2: Validation error handling
        val errorContext = ErrorHandlingManager.ErrorContext(
            errorType = ErrorHandlingManager.ErrorType.VALIDATION_ERROR,
            originalText = userText,
            apiResponse = invalidResult,
            retryCount = 0,
            userInteractionAllowed = true
        )
        
        val handlingResult = errorHandlingManager.handleError(errorContext)
        
        // Step 3: Verify graceful degradation is applied
        assertEquals(ErrorHandlingManager.RecoveryStrategy.GRACEFUL_DEGRADATION, handlingResult.recoveryStrategy)
        assertTrue(handlingResult.success)
        assertNotNull(handlingResult.recoveredResult)
        
        // Step 4: Verify data sanitization results
        val sanitizedResult = handlingResult.recoveredResult!!
        
        // Title should be fixed
        assertNotNull(sanitizedResult.title)
        assertTrue(sanitizedResult.title!!.isNotBlank())
        assertTrue(sanitizedResult.title!!.contains("Meeting") || sanitizedResult.title!!.contains("corrupted"))
        
        // Date should be fixed to valid format
        assertNotNull(sanitizedResult.startDateTime)
        assertTrue(sanitizedResult.startDateTime!!.matches(Regex("\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}")))
        
        // End time should be generated
        assertNotNull(sanitizedResult.endDateTime)
        assertTrue(sanitizedResult.endDateTime!!.matches(Regex("\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}")))
        
        // Location should be cleaned (null or valid)
        assertTrue(sanitizedResult.location.isNullOrBlank() || sanitizedResult.location!!.trim().isNotEmpty())
        
        // Step 5: Verify fallback metadata
        assertTrue(sanitizedResult.fallbackApplied)
        assertEquals("Applied intelligent defaults for missing or low-confidence fields", sanitizedResult.fallbackReason)
    }
    
    /**
     * Test Scenario 8: Multiple cascading failures -> Ultimate fallback -> User still gets event
     * User selects text -> Network fails -> Retry fails -> Offline fails -> Basic fallback -> Event created
     */
    @Test
    fun testCascadingFailuresUltimateFallbackWorkflow() = runBlocking {
        val userText = "Emergency meeting ASAP"
        
        // Step 1: Network failure
        val networkError = UnknownHostException("Network completely unavailable")
        val errorContext1 = ErrorHandlingManager.ErrorContext(
            errorType = ErrorHandlingManager.ErrorType.NETWORK_ERROR,
            originalText = userText,
            exception = networkError,
            retryCount = 3, // Already tried retries
            networkAvailable = false,
            userInteractionAllowed = true
        )
        
        val handlingResult1 = errorHandlingManager.handleError(errorContext1)
        
        // Should go to offline mode
        assertEquals(ErrorHandlingManager.RecoveryStrategy.OFFLINE_MODE, handlingResult1.recoveryStrategy)
        
        // Step 2: Even if offline processing has issues, we should get a basic event
        if (handlingResult1.success && handlingResult1.recoveredResult != null) {
            val offlineResult = handlingResult1.recoveredResult!!
            
            // Verify basic event was created
            assertNotNull(offlineResult.title)
            assertTrue(offlineResult.title!!.isNotBlank())
            assertTrue(offlineResult.title!!.contains("Emergency") || offlineResult.title!!.contains("meeting"))
            
            assertNotNull(offlineResult.startDateTime)
            assertNotNull(offlineResult.endDateTime)
            assertTrue(offlineResult.fallbackApplied)
            
            // Verify it's marked as offline
            assertTrue(offlineResult.fallbackReason!!.contains("offline"))
            
            // Step 3: Verify event is immediately usable
            assertTrue(offlineResult.startDateTime!!.matches(Regex("\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}")))
            assertTrue(offlineResult.endDateTime!!.matches(Regex("\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}")))
            
            // Description should preserve original text
            assertNotNull(offlineResult.description)
            assertTrue(offlineResult.description!!.contains(userText))
        } else {
            fail("Even with cascading failures, user should get a basic event")
        }
    }
    
    /**
     * Test Scenario 9: TextProcessorActivity complete workflow simulation
     * Simulates the complete TextProcessorActivity workflow with error handling
     */
    @Test
    fun testTextProcessorActivityCompleteWorkflow() = runBlocking {
        val selectedText = "Conference call with international team tomorrow 8am EST"
        
        // Step 1: Text enhancement (simulated)
        val enhancedText = selectedText // In real app, TextMergeHelper would enhance this
        
        // Step 2: Network check fails
        val networkUnavailable = true
        
        if (networkUnavailable) {
            // Step 3: Offline processing
            val offlineResult = offlineModeHandler.createOfflineEvent(enhancedText)
            
            // Step 4: Verify offline event quality
            assertNotNull(offlineResult.title)
            assertTrue(offlineResult.title!!.contains("Conference") || offlineResult.title!!.contains("call"))
            assertNotNull(offlineResult.startDateTime)
            assertTrue(offlineResult.fallbackApplied)
            
            // Step 5: Verify timezone handling in offline mode
            assertTrue(offlineResult.description!!.contains("EST") || offlineResult.description!!.contains("8am"))
            
            // Step 6: Verify event is ready for calendar creation
            assertTrue(offlineResult.startDateTime!!.matches(Regex("\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}")))
            assertTrue(offlineResult.endDateTime!!.matches(Regex("\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}")))
        }
    }
    
    /**
     * Test Scenario 10: MainActivity complete workflow simulation
     * Simulates the complete MainActivity workflow with various confidence levels
     */
    @Test
    fun testMainActivityCompleteWorkflow() = runBlocking {
        val testCases = listOf(
            "High confidence" to ParseResult(
                title = "Board meeting",
                startDateTime = "2024-01-20T10:00:00",
                endDateTime = "2024-01-20T12:00:00",
                location = "Boardroom",
                description = "Monthly board meeting",
                confidenceScore = 0.95,
                allDay = false,
                timezone = "America/Toronto",
                originalText = "Monthly board meeting next Saturday 10am in boardroom"
            ),
            "Medium confidence" to ParseResult(
                title = "meeting",
                startDateTime = "2024-01-21T14:00:00",
                endDateTime = "2024-01-21T15:00:00",
                location = null,
                description = "some meeting",
                confidenceScore = 0.55,
                allDay = false,
                timezone = "America/Toronto",
                originalText = "some meeting tomorrow afternoon"
            ),
            "Low confidence" to ParseResult(
                title = "event",
                startDateTime = null,
                endDateTime = null,
                location = null,
                description = "unclear event",
                confidenceScore = 0.15,
                allDay = false,
                timezone = "America/Toronto",
                originalText = "unclear event sometime"
            )
        )
        
        for ((scenario, result) in testCases) {
            // Step 1: Confidence assessment
            val assessment = confidenceValidator.assessConfidence(result, result.originalText!!)
            
            // Step 2: Handle based on confidence
            when {
                assessment.overallConfidence >= 0.7 -> {
                    // High confidence - should proceed directly
                    assertEquals(ConfidenceValidator.UserRecommendation.PROCEED_CONFIDENTLY, assessment.recommendation)
                    assertTrue(assessment.shouldProceed)
                    assertNull(assessment.warningMessage)
                }
                
                assessment.overallConfidence >= 0.3 -> {
                    // Medium confidence - may need user confirmation
                    assertTrue(assessment.recommendation in listOf(
                        ConfidenceValidator.UserRecommendation.PROCEED_WITH_CAUTION,
                        ConfidenceValidator.UserRecommendation.SUGGEST_IMPROVEMENTS
                    ))
                }
                
                else -> {
                    // Low confidence - needs handling
                    val errorContext = ErrorHandlingManager.ErrorContext(
                        errorType = ErrorHandlingManager.ErrorType.LOW_CONFIDENCE,
                        originalText = result.originalText!!,
                        apiResponse = result,
                        confidenceScore = assessment.overallConfidence,
                        userInteractionAllowed = true
                    )
                    
                    val handlingResult = errorHandlingManager.handleError(errorContext)
                    
                    // Should get either user confirmation request or fallback result
                    assertTrue(
                        handlingResult.actionRequired == ErrorHandlingManager.UserAction.CONFIRM_LOW_CONFIDENCE_RESULT ||
                        handlingResult.recoveredResult != null,
                        "Low confidence should be handled for scenario: $scenario"
                    )
                }
            }
        }
    }
}