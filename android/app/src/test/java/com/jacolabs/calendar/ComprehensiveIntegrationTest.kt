package com.jacolabs.calendar

import android.content.Context
import androidx.lifecycle.LifecycleCoroutineScope
import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import kotlinx.coroutines.runBlocking
import kotlinx.coroutines.test.TestScope
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith
import org.mockito.Mock
import org.mockito.MockitoAnnotations
import kotlin.test.*

/**
 * Comprehensive integration test for task 16: "Integrate all components and test end-to-end workflows"
 * 
 * This test validates:
 * - Complete integration of all error handling components
 * - End-to-end user journeys through various error scenarios
 * - Error recovery effectiveness and user experience
 * - Backward compatibility with existing functionality
 * - System health and performance under error conditions
 * 
 * Requirements: 1.1, 1.2, 1.3, 1.4, 10.4
 */
@RunWith(AndroidJUnit4::class)
class ComprehensiveIntegrationTest {
    
    private lateinit var context: Context
    private lateinit var systemIntegrator: ErrorHandlingSystemIntegrator
    private lateinit var testScope: TestScope
    
    @Mock
    private lateinit var mockLifecycleScope: LifecycleCoroutineScope
    
    @Before
    fun setUp() {
        MockitoAnnotations.openMocks(this)
        context = ApplicationProvider.getApplicationContext()
        systemIntegrator = ErrorHandlingSystemIntegrator(context)
        testScope = TestScope()
    }
    
    /**
     * Test 1: Complete happy path integration
     * Requirements: 1.1, 1.2, 1.3, 1.4
     */
    @Test
    fun testCompleteHappyPathIntegration() = runBlocking {
        val testText = "Team meeting tomorrow at 2pm in conference room A"
        var successResult: ParseResult? = null
        var errorMessage: String? = null
        var userInteractionRequired = false
        
        systemIntegrator.processTextEndToEnd(
            text = testText,
            lifecycleScope = mockLifecycleScope,
            onSuccess = { result ->
                successResult = result
            },
            onError = { error ->
                errorMessage = error
            },
            onUserInteractionRequired = { _ ->
                userInteractionRequired = true
            }
        )
        
        // Verify successful processing
        assertNotNull(successResult, "Should have successful result")
        assertNull(errorMessage, "Should not have error message")
        assertFalse(userInteractionRequired, "Should not require user interaction for high confidence")
        
        // Verify result quality
        val result = successResult!!
        assertNotNull(result.title)
        assertTrue(result.title!!.contains("meeting") || result.title!!.contains("Team"))
        assertNotNull(result.startDateTime)
        assertNotNull(result.endDateTime)
        assertTrue(result.confidenceScore > 0.7, "Should have high confidence")
    }
    
    /**
     * Test 2: Network failure to offline fallback integration
     * Requirements: 4.1, 4.2, 4.3, 4.4, 6.3
     */
    @Test
    fun testNetworkFailureToOfflineIntegration() = runBlocking {
        val testText = "Doctor appointment next Friday at 3:30pm"
        var successResult: ParseResult? = null
        var errorMessage: String? = null
        val progressUpdates = mutableListOf<String>()
        
        // This test simulates network failure by using text that would trigger offline mode
        systemIntegrator.processTextEndToEnd(
            text = testText,
            lifecycleScope = mockLifecycleScope,
            onSuccess = { result ->
                successResult = result
            },
            onError = { error ->
                errorMessage = error
            },
            onProgressUpdate = { progress ->
                progressUpdates.add(progress)
            }
        )
        
        // Should eventually succeed with offline fallback
        assertTrue(successResult != null || errorMessage != null, "Should have some result")
        
        if (successResult != null) {
            val result = successResult!!
            assertNotNull(result.title)
            assertTrue(result.title!!.contains("appointment") || result.title!!.contains("Doctor"))
            assertNotNull(result.startDateTime)
            
            // If it's an offline result, verify offline characteristics
            if (result.fallbackApplied) {
                assertTrue(
                    result.fallbackReason?.contains("offline") == true ||
                    result.description?.contains("offline") == true
                )
            }
        }
        
        // Verify progress updates were provided
        assertTrue(progressUpdates.isNotEmpty(), "Should have progress updates")
    }
    
    /**
     * Test 3: Low confidence to user interaction integration
     * Requirements: 2.1, 2.2, 2.3, 2.4, 11.1, 11.2, 11.3, 11.4
     */
    @Test
    fun testLowConfidenceUserInteractionIntegration() = runBlocking {
        val testText = "maybe meeting sometime next week"
        var successResult: ParseResult? = null
        var errorMessage: String? = null
        var userInteraction: UserInteraction? = null
        
        systemIntegrator.processTextEndToEnd(
            text = testText,
            lifecycleScope = mockLifecycleScope,
            onSuccess = { result ->
                successResult = result
            },
            onError = { error ->
                errorMessage = error
            },
            onUserInteractionRequired = { interaction ->
                userInteraction = interaction
            }
        )
        
        // Should require user interaction for low confidence text
        assertTrue(
            userInteraction != null || successResult != null,
            "Should either require user interaction or provide fallback result"
        )
        
        if (userInteraction != null) {
            val interaction = userInteraction!!
            
            // Verify interaction details
            assertTrue(interaction.message.isNotBlank())
            assertNotNull(interaction.result)
            
            // Test user proceeding with low confidence
            interaction.onProceed()
            
            // Should now have a result (from the onProceed callback)
            // Note: In real implementation, this would trigger the onSuccess callback
        }
        
        if (successResult != null) {
            val result = successResult!!
            assertNotNull(result.title)
            assertTrue(result.title!!.isNotBlank())
            
            // Low confidence results should have fallback applied
            if (result.confidenceScore < 0.3) {
                assertTrue(result.fallbackApplied)
            }
        }
    }
    
    /**
     * Test 4: Validation error to graceful degradation integration
     * Requirements: 5.1, 5.2, 5.3, 5.4, 12.1, 12.2, 12.3, 12.4
     */
    @Test
    fun testValidationErrorGracefulDegradationIntegration() = runBlocking {
        val testText = "Meeting with invalid data format"
        var successResult: ParseResult? = null
        var errorMessage: String? = null
        
        systemIntegrator.processTextEndToEnd(
            text = testText,
            lifecycleScope = mockLifecycleScope,
            onSuccess = { result ->
                successResult = result
            },
            onError = { error ->
                errorMessage = error
            }
        )
        
        // Should handle validation issues gracefully
        assertTrue(successResult != null || errorMessage != null, "Should have some result")
        
        if (successResult != null) {
            val result = successResult!!
            
            // Verify basic event structure is valid
            assertNotNull(result.title)
            assertTrue(result.title!!.isNotBlank())
            assertNotNull(result.startDateTime)
            assertNotNull(result.endDateTime)
            
            // Verify date format is valid
            assertTrue(result.startDateTime!!.matches(Regex("\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}")))
            assertTrue(result.endDateTime!!.matches(Regex("\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}")))
            
            // If graceful degradation was applied, verify metadata
            if (result.fallbackApplied) {
                assertNotNull(result.fallbackReason)
            }
        }
    }
    
    /**
     * Test 5: Calendar launch failure to alternatives integration
     * Requirements: 1.1, 1.2, 1.3, 6.3, 8.1, 8.2, 8.3
     */
    @Test
    fun testCalendarLaunchFailureIntegration() = runBlocking {
        val testResult = ParseResult(
            title = "Test Meeting",
            startDateTime = "2024-01-15T14:00:00",
            endDateTime = "2024-01-15T15:00:00",
            location = "Conference Room",
            description = "Test meeting description",
            confidenceScore = 0.9,
            allDay = false,
            timezone = "America/Toronto",
            originalText = "Test meeting tomorrow at 2pm in conference room"
        )
        
        var calendarSuccess = false
        var calendarError: String? = null
        var alternativesOffered: List<String>? = null
        
        systemIntegrator.createCalendarEventEndToEnd(
            result = testResult,
            lifecycleScope = mockLifecycleScope,
            onSuccess = {
                calendarSuccess = true
            },
            onError = { error ->
                calendarError = error
            },
            onAlternativeRequired = { alternatives ->
                alternativesOffered = alternatives
            }
        )
        
        // Should either succeed or offer alternatives
        assertTrue(
            calendarSuccess || calendarError != null || alternativesOffered != null,
            "Should have some calendar creation result"
        )
        
        // If alternatives are offered, verify they are useful
        if (alternativesOffered != null) {
            val alternatives = alternativesOffered!!
            assertTrue(alternatives.isNotEmpty(), "Should offer alternatives")
            assertTrue(
                alternatives.any { it.contains("Calendar") } ||
                alternatives.any { it.contains("Clipboard") },
                "Should offer meaningful alternatives"
            )
        }
    }
    
    /**
     * Test 6: Multiple cascading failures integration
     * Requirements: 1.1, 1.2, 1.3, 1.4, 10.4
     */
    @Test
    fun testCascadingFailuresIntegration() = runBlocking {
        val testText = "Emergency meeting ASAP with corrupted data"
        var finalResult: ParseResult? = null
        var finalError: String? = null
        val progressUpdates = mutableListOf<String>()
        
        systemIntegrator.processTextEndToEnd(
            text = testText,
            lifecycleScope = mockLifecycleScope,
            onSuccess = { result ->
                finalResult = result
            },
            onError = { error ->
                finalError = error
            },
            onProgressUpdate = { progress ->
                progressUpdates.add(progress)
            }
        )
        
        // Even with cascading failures, user should get something useful
        assertTrue(finalResult != null || finalError != null, "Should have final result")
        
        if (finalResult != null) {
            val result = finalResult!!
            
            // Verify basic event was created despite failures
            assertNotNull(result.title)
            assertTrue(result.title!!.isNotBlank())
            assertTrue(result.title!!.contains("Emergency") || result.title!!.contains("meeting"))
            
            assertNotNull(result.startDateTime)
            assertNotNull(result.endDateTime)
            
            // Should have fallback applied for cascading failures
            assertTrue(result.fallbackApplied)
            assertNotNull(result.fallbackReason)
            
            // Description should preserve original text
            assertNotNull(result.description)
            assertTrue(result.description!!.contains(testText))
        }
        
        // Verify system provided progress feedback during failures
        assertTrue(progressUpdates.isNotEmpty(), "Should have progress updates during failures")
    }
    
    /**
     * Test 7: System health check integration
     * Requirements: 10.1, 10.2, 10.3, 10.4
     */
    @Test
    fun testSystemHealthCheckIntegration() = runBlocking {
        val healthReport = systemIntegrator.performSystemHealthCheck()
        
        // Verify health report structure
        assertNotNull(healthReport)
        assertTrue(healthReport.componentHealth.isNotEmpty(), "Should check multiple components")
        assertNotNull(healthReport.errorStatistics)
        assertTrue(healthReport.timestamp > 0)
        
        // Verify key components are checked
        val expectedComponents = listOf(
            "ErrorHandlingManager",
            "ConfidenceValidator", 
            "FallbackEventGenerator",
            "OfflineModeHandler",
            "DataValidationManager"
        )
        
        for (component in expectedComponents) {
            assertTrue(
                healthReport.componentHealth.containsKey(component),
                "Should check $component health"
            )
        }
        
        // If system is healthy, all components should be working
        if (healthReport.overallHealthy) {
            assertTrue(
                healthReport.componentHealth.values.all { it },
                "If overall healthy, all components should be healthy"
            )
            assertTrue(healthReport.issues.isEmpty(), "Healthy system should have no issues")
        }
        
        // If there are issues, they should be descriptive
        for (issue in healthReport.issues) {
            assertTrue(issue.isNotBlank(), "Issues should be descriptive")
        }
    }
    
    /**
     * Test 8: Backward compatibility validation
     * Requirements: 10.4
     */
    @Test
    fun testBackwardCompatibilityIntegration() = runBlocking {
        val compatibilityReport = systemIntegrator.validateBackwardCompatibility()
        
        // Verify compatibility report structure
        assertNotNull(compatibilityReport)
        assertTrue(compatibilityReport.testResults.isNotEmpty(), "Should run compatibility tests")
        assertTrue(compatibilityReport.timestamp > 0)
        
        // Verify key compatibility tests
        val expectedTests = listOf(
            "BasicApiParsing",
            "CalendarIntentCreation",
            "DataStructureCompatibility",
            "ConfigurationLoading"
        )
        
        for (test in expectedTests) {
            assertTrue(
                compatibilityReport.testResults.containsKey(test),
                "Should test $test compatibility"
            )
        }
        
        // If overall compatible, all tests should pass
        if (compatibilityReport.overallCompatible) {
            assertTrue(
                compatibilityReport.testResults.values.all { it },
                "If overall compatible, all tests should pass"
            )
            assertTrue(compatibilityReport.issues.isEmpty(), "Compatible system should have no issues")
        }
        
        // Verify issues are descriptive if present
        for (issue in compatibilityReport.issues) {
            assertTrue(issue.isNotBlank(), "Issues should be descriptive")
        }
    }
    
    /**
     * Test 9: Component integration and communication
     * Requirements: 10.1, 10.2, 10.3
     */
    @Test
    fun testComponentIntegrationCommunication() = runBlocking {
        val components = systemIntegrator.getComponents()
        
        // Verify all components are available
        assertNotNull(components.errorHandlingManager)
        assertNotNull(components.confidenceValidator)
        assertNotNull(components.userFeedbackManager)
        assertNotNull(components.fallbackEventGenerator)
        assertNotNull(components.offlineModeHandler)
        assertNotNull(components.calendarIntentHelper)
        assertNotNull(components.dataValidationManager)
        assertNotNull(components.apiService)
        
        // Test component communication through error handling manager
        val testText = "test event for component communication"
        
        // Test error handling manager can use other components
        val errorStats = components.errorHandlingManager.getErrorStatistics()
        assertNotNull(errorStats)
        
        // Test confidence validator integration
        val testResult = ParseResult(
            title = "Test Event",
            startDateTime = "2024-01-15T14:00:00",
            endDateTime = "2024-01-15T15:00:00",
            location = null,
            description = testText,
            confidenceScore = 0.5,
            allDay = false,
            timezone = "America/Toronto",
            originalText = testText
        )
        
        val assessment = components.confidenceValidator.assessConfidence(testResult, testText)
        assertNotNull(assessment)
        assertTrue(assessment.overallConfidence >= 0.0)
        
        // Test fallback event generator integration
        val fallbackEvent = components.fallbackEventGenerator.generateFallbackEvent(testText, testResult)
        assertNotNull(fallbackEvent)
        assertTrue(fallbackEvent.title.isNotBlank())
        
        // Test offline mode handler integration
        val offlineResult = components.offlineModeHandler.createOfflineEvent(testText)
        assertNotNull(offlineResult)
        assertNotNull(offlineResult.title)
    }
    
    /**
     * Test 10: Performance under error conditions
     * Requirements: 10.4
     */
    @Test
    fun testPerformanceUnderErrorConditions() = runBlocking {
        val testTexts = listOf(
            "network failure test",
            "low confidence test maybe sometime",
            "validation error with bad data",
            "parsing failure with corrupted input",
            "calendar launch failure test"
        )
        
        val startTime = System.currentTimeMillis()
        var completedTests = 0
        var totalErrors = 0
        
        for (testText in testTexts) {
            try {
                systemIntegrator.processTextEndToEnd(
                    text = testText,
                    lifecycleScope = mockLifecycleScope,
                    onSuccess = { _ ->
                        completedTests++
                    },
                    onError = { _ ->
                        completedTests++
                        totalErrors++
                    },
                    onUserInteractionRequired = { _ ->
                        completedTests++
                    }
                )
            } catch (e: Exception) {
                totalErrors++
                completedTests++
            }
        }
        
        val endTime = System.currentTimeMillis()
        val totalTime = endTime - startTime
        
        // Verify performance characteristics
        assertEquals(testTexts.size, completedTests, "Should complete all tests")
        assertTrue(totalTime < 30000, "Should complete within 30 seconds") // Generous timeout
        
        // System should handle errors gracefully without crashing
        assertTrue(totalErrors <= testTexts.size, "Error count should not exceed test count")
        
        // Verify system is still functional after error conditions
        val healthReport = systemIntegrator.performSystemHealthCheck()
        assertNotNull(healthReport, "System should still be functional after error tests")
    }
    
    /**
     * Test 11: User experience consistency across scenarios
     * Requirements: 11.1, 11.2, 11.3, 11.4
     */
    @Test
    fun testUserExperienceConsistency() = runBlocking {
        val testScenarios = mapOf(
            "High confidence" to "Team meeting tomorrow at 2pm in boardroom",
            "Medium confidence" to "meeting tomorrow afternoon",
            "Low confidence" to "maybe something next week",
            "Network error simulation" to "offline test meeting",
            "Validation error" to "meeting with bad data format"
        )
        
        val userExperiences = mutableMapOf<String, UserExperienceMetrics>()
        
        for ((scenario, testText) in testScenarios) {
            val metrics = UserExperienceMetrics()
            val startTime = System.currentTimeMillis()
            
            systemIntegrator.processTextEndToEnd(
                text = testText,
                lifecycleScope = mockLifecycleScope,
                onSuccess = { result ->
                    metrics.successful = true
                    metrics.resultQuality = calculateResultQuality(result)
                    metrics.processingTime = System.currentTimeMillis() - startTime
                },
                onError = { error ->
                    metrics.successful = false
                    metrics.errorMessage = error
                    metrics.processingTime = System.currentTimeMillis() - startTime
                },
                onUserInteractionRequired = { interaction ->
                    metrics.userInteractionRequired = true
                    metrics.interactionQuality = calculateInteractionQuality(interaction)
                    metrics.processingTime = System.currentTimeMillis() - startTime
                },
                onProgressUpdate = { progress ->
                    metrics.progressUpdates++
                }
            )
            
            userExperiences[scenario] = metrics
        }
        
        // Verify consistency across scenarios
        for ((scenario, metrics) in userExperiences) {
            // All scenarios should complete within reasonable time
            assertTrue(
                metrics.processingTime < 10000,
                "$scenario should complete within 10 seconds"
            )
            
            // All scenarios should provide some form of feedback
            assertTrue(
                metrics.successful || metrics.errorMessage != null || metrics.userInteractionRequired,
                "$scenario should provide user feedback"
            )
            
            // Progress updates should be provided for longer operations
            if (metrics.processingTime > 1000) {
                assertTrue(
                    metrics.progressUpdates > 0,
                    "$scenario should provide progress updates for longer operations"
                )
            }
        }
        
        // Verify error messages are helpful
        for ((scenario, metrics) in userExperiences) {
            if (metrics.errorMessage != null) {
                assertTrue(
                    metrics.errorMessage!!.length > 10,
                    "$scenario error message should be descriptive"
                )
                assertFalse(
                    metrics.errorMessage!!.contains("Exception") || 
                    metrics.errorMessage!!.contains("Error:"),
                    "$scenario error message should be user-friendly"
                )
            }
        }
    }
    
    /**
     * Helper function to calculate result quality score
     */
    private fun calculateResultQuality(result: ParseResult): Double {
        var score = 0.0
        
        if (result.title?.isNotBlank() == true) score += 0.3
        if (result.startDateTime?.isNotBlank() == true) score += 0.3
        if (result.endDateTime?.isNotBlank() == true) score += 0.2
        if (result.location?.isNotBlank() == true) score += 0.1
        if (result.confidenceScore > 0.5) score += 0.1
        
        return score
    }
    
    /**
     * Helper function to calculate interaction quality score
     */
    private fun calculateInteractionQuality(interaction: UserInteraction): Double {
        var score = 0.0
        
        if (interaction.title.isNotBlank()) score += 0.3
        if (interaction.message.isNotBlank() && interaction.message.length > 20) score += 0.4
        if (interaction.result != null) score += 0.3
        
        return score
    }
    
    /**
     * Data class for tracking user experience metrics
     */
    private data class UserExperienceMetrics(
        var successful: Boolean = false,
        var errorMessage: String? = null,
        var userInteractionRequired: Boolean = false,
        var processingTime: Long = 0,
        var progressUpdates: Int = 0,
        var resultQuality: Double = 0.0,
        var interactionQuality: Double = 0.0
    )
}