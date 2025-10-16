package com.jacolabs.calendar

import android.content.Context
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith
import org.mockito.Mock
import org.mockito.MockitoAnnotations
import org.robolectric.RobolectricTestRunner
import org.robolectric.RuntimeEnvironment
import kotlin.test.assertEquals
import kotlin.test.assertFalse
import kotlin.test.assertNotNull
import kotlin.test.assertTrue

/**
 * Unit tests for the data validation and sanitization system.
 */
@RunWith(RobolectricTestRunner::class)
class DataValidationTest {
    
    @Mock
    private lateinit var mockContext: Context
    
    private lateinit var dataValidationManager: DataValidationManager
    private lateinit var validationConfig: ValidationConfig
    
    @Before
    fun setup() {
        MockitoAnnotations.openMocks(this)
        val context = RuntimeEnvironment.getApplication()
        dataValidationManager = DataValidationManager(context)
        validationConfig = ValidationConfig(context)
    }
    
    @Test
    fun testValidDataPassesValidation() {
        val validResult = ParseResult(
            title = "Team Meeting",
            startDateTime = "2024-12-15T14:00:00+00:00",
            endDateTime = "2024-12-15T15:00:00+00:00",
            location = "Conference Room A",
            description = "Weekly team sync",
            confidenceScore = 0.8,
            allDay = false,
            timezone = "UTC"
        )
        
        val validationResult = dataValidationManager.validateAndSanitize(validResult, "Team meeting at 2 PM")
        
        assertTrue(validationResult.isValid)
        assertEquals("Team Meeting", validationResult.sanitizedResult.title)
        assertTrue(validationResult.issues.isEmpty())
    }
    
    @Test
    fun testMissingTitleGetsDefault() {
        val resultWithoutTitle = ParseResult(
            title = null,
            startDateTime = "2024-12-15T14:00:00+00:00",
            endDateTime = "2024-12-15T15:00:00+00:00",
            confidenceScore = 0.6,
            allDay = false,
            timezone = "UTC"
        )
        
        val validationResult = dataValidationManager.validateAndSanitize(
            resultWithoutTitle, 
            "Important meeting tomorrow"
        )
        
        assertTrue(validationResult.isValid)
        assertNotNull(validationResult.sanitizedResult.title)
        assertTrue(validationResult.appliedDefaults.containsKey("title"))
        assertEquals("Important meeting tomorrow", validationResult.sanitizedResult.title)
    }
    
    @Test
    fun testInvalidDateTimeGetsDefault() {
        val resultWithInvalidDateTime = ParseResult(
            title = "Meeting",
            startDateTime = "invalid-date",
            endDateTime = null,
            confidenceScore = 0.5,
            allDay = false,
            timezone = "UTC"
        )
        
        val validationResult = dataValidationManager.validateAndSanitize(
            resultWithInvalidDateTime,
            "Meeting next week"
        )
        
        assertTrue(validationResult.isValid)
        assertNotNull(validationResult.sanitizedResult.startDateTime)
        assertNotNull(validationResult.sanitizedResult.endDateTime)
        assertTrue(validationResult.appliedDefaults.containsKey("startDateTime"))
    }
    
    @Test
    fun testDataSanitization() {
        val dirtyTitle = "Meeting!!!   with    client<script>alert('test')</script>"
        val sanitizedTitle = DataSanitizer.sanitizeTitle(dirtyTitle)
        
        assertFalse(sanitizedTitle.contains("<script>"))
        assertFalse(sanitizedTitle.contains("!!!"))
        assertTrue(sanitizedTitle.contains("Meeting"))
        assertTrue(sanitizedTitle.contains("client"))
    }
    
    @Test
    fun testLowConfidenceDetection() {
        val lowConfidenceResult = ParseResult(
            title = "Event",
            startDateTime = "2024-12-15T10:00:00+00:00",
            endDateTime = "2024-12-15T11:00:00+00:00",
            confidenceScore = 0.2,
            allDay = false,
            timezone = "UTC"
        )
        
        val validationResult = dataValidationManager.validateAndSanitize(
            lowConfidenceResult,
            "something"
        )
        
        assertTrue(validationResult.confidenceAssessment.confidenceWarnings.isNotEmpty())
        assertTrue(validationResult.confidenceAssessment.recommendedActions.isNotEmpty())
    }
    
    @Test
    fun testEssentialFieldsValidation() {
        val completeResult = ParseResult(
            title = "Meeting",
            startDateTime = "2024-12-15T14:00:00+00:00",
            endDateTime = "2024-12-15T15:00:00+00:00",
            confidenceScore = 0.7,
            allDay = false,
            timezone = "UTC"
        )
        
        val incompleteResult = ParseResult(
            title = null,
            startDateTime = null,
            endDateTime = null,
            confidenceScore = 0.3,
            allDay = false,
            timezone = "UTC"
        )
        
        assertTrue(dataValidationManager.validateEssentialFields(completeResult))
        assertFalse(dataValidationManager.validateEssentialFields(incompleteResult))
    }
    
    @Test
    fun testValidationConfiguration() {
        // Test default values
        assertEquals(0.3, validationConfig.minConfidenceThreshold, 0.01)
        assertEquals(0.6, validationConfig.warningConfidenceThreshold, 0.01)
        assertEquals(200, validationConfig.maxTitleLength)
        assertTrue(validationConfig.enableAutoSanitization)
        
        // Test configuration updates
        validationConfig.minConfidenceThreshold = 0.5
        validationConfig.enableStrictValidation = true
        
        assertEquals(0.5, validationConfig.minConfidenceThreshold, 0.01)
        assertTrue(validationConfig.enableStrictValidation)
    }
    
    @Test
    fun testDataIntegrityScore() {
        val highQualityResult = ParseResult(
            title = "Important Team Meeting",
            startDateTime = "2024-12-15T14:00:00+00:00",
            endDateTime = "2024-12-15T15:00:00+00:00",
            location = "Conference Room A",
            description = "Weekly team sync meeting",
            confidenceScore = 0.9,
            allDay = false,
            timezone = "UTC"
        )
        
        val lowQualityResult = ParseResult(
            title = "Event",
            startDateTime = "invalid-date",
            endDateTime = null,
            confidenceScore = 0.1,
            allDay = false,
            timezone = "UTC"
        )
        
        val highQualityValidation = dataValidationManager.validateAndSanitize(
            highQualityResult,
            "Important team meeting at 2 PM in conference room A"
        )
        
        val lowQualityValidation = dataValidationManager.validateAndSanitize(
            lowQualityResult,
            "event"
        )
        
        assertTrue(highQualityValidation.dataIntegrityScore > lowQualityValidation.dataIntegrityScore)
        assertTrue(highQualityValidation.dataIntegrityScore > 0.7)
        assertTrue(lowQualityValidation.dataIntegrityScore < 0.5)
    }
}