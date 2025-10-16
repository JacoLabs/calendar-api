package com.jacolabs.calendar

import android.content.Context
import org.junit.Before
import org.junit.Test
import org.junit.Assert.*
import org.mockito.Mock
import org.mockito.MockitoAnnotations

/**
 * Unit tests for ConfidenceValidator
 */
class ConfidenceValidatorTest {
    
    @Mock
    private lateinit var mockContext: Context
    
    private lateinit var confidenceValidator: ConfidenceValidator
    
    @Before
    fun setUp() {
        MockitoAnnotations.openMocks(this)
        confidenceValidator = ConfidenceValidator(mockContext)
    }
    
    @Test
    fun testHighConfidenceResult() {
        // Arrange
        val parseResult = ParseResult(
            title = "Team Meeting",
            startDateTime = "2024-12-16T14:00:00",
            endDateTime = "2024-12-16T15:00:00",
            location = "Conference Room A",
            description = "Weekly team standup meeting",
            confidenceScore = 0.85,
            allDay = false,
            timezone = "UTC",
            fieldResults = mapOf(
                "title" to FieldResult("Team Meeting", "llm", 0.9, Pair(0, 12), 100),
                "start_datetime" to FieldResult("2024-12-16T14:00:00", "duckling", 0.95, Pair(13, 25), 150),
                "location" to FieldResult("Conference Room A", "regex", 0.8, Pair(26, 42), 50)
            )
        )
        val originalText = "Team Meeting on Monday at 2 PM in Conference Room A"
        
        // Act
        val assessment = confidenceValidator.assessConfidence(parseResult, originalText)
        
        // Assert
        assertTrue("Should have high overall confidence", assessment.overallConfidence >= 0.7)
        assertEquals("Should recommend proceeding confidently", 
            ConfidenceValidator.UserRecommendation.PROCEED_CONFIDENTLY, assessment.recommendation)
        assertTrue("Should proceed", assessment.shouldProceed)
        assertNull("Should not have warning message", assessment.warningMessage)
        assertTrue("Should have field confidences", assessment.fieldConfidences.isNotEmpty())
    }
    
    @Test
    fun testLowConfidenceResult() {
        // Arrange
        val parseResult = ParseResult(
            title = "meeting",
            startDateTime = "2024-12-16T10:00:00",
            endDateTime = null,
            location = null,
            description = null,
            confidenceScore = 0.25,
            allDay = false,
            timezone = "UTC",
            fieldResults = mapOf(
                "title" to FieldResult("meeting", "fallback", 0.3, Pair(0, 7), 50),
                "start_datetime" to FieldResult("2024-12-16T10:00:00", "default", 0.2, null, 25)
            )
        )
        val originalText = "meeting tomorrow"
        
        // Act
        val assessment = confidenceValidator.assessConfidence(parseResult, originalText)
        
        // Assert
        assertTrue("Should have low overall confidence", assessment.overallConfidence < 0.3)
        assertEquals("Should suggest improvements", 
            ConfidenceValidator.UserRecommendation.SUGGEST_IMPROVEMENTS, assessment.recommendation)
        assertNotNull("Should have warning message", assessment.warningMessage)
        assertEquals("Should have warning severity", 
            ConfidenceValidator.WarningSeverity.WARNING, assessment.warningSeverity)
        assertTrue("Should have improvement suggestions", assessment.improvementSuggestions.isNotEmpty())
    }
    
    @Test
    fun testMissingCriticalFields() {
        // Arrange
        val parseResult = ParseResult(
            title = null,
            startDateTime = null,
            endDateTime = null,
            location = "Office",
            description = "Some description",
            confidenceScore = 0.1,
            allDay = false,
            timezone = "UTC"
        )
        val originalText = "at the office"
        
        // Act
        val assessment = confidenceValidator.assessConfidence(parseResult, originalText)
        
        // Assert
        assertTrue("Should identify missing critical fields", assessment.missingCriticalFields.isNotEmpty())
        assertTrue("Should contain title in missing fields", assessment.missingCriticalFields.contains("title"))
        assertTrue("Should contain start_datetime in missing fields", assessment.missingCriticalFields.contains("start_datetime"))
        assertEquals("Should recommend manual entry", 
            ConfidenceValidator.UserRecommendation.RECOMMEND_MANUAL_ENTRY, assessment.recommendation)
        assertFalse("Should not proceed", assessment.shouldProceed)
    }
    
    @Test
    fun testMediumConfidenceWithWarnings() {
        // Arrange
        val parseResult = ParseResult(
            title = "Meeting",
            startDateTime = "2024-12-16T14:00:00",
            endDateTime = null,
            location = null,
            description = null,
            confidenceScore = 0.5,
            allDay = false,
            timezone = "UTC",
            fieldResults = mapOf(
                "title" to FieldResult("Meeting", "regex", 0.4, Pair(0, 7), 75),
                "start_datetime" to FieldResult("2024-12-16T14:00:00", "duckling", 0.6, Pair(8, 20), 100)
            )
        )
        val originalText = "Meeting Monday afternoon"
        
        // Act
        val assessment = confidenceValidator.assessConfidence(parseResult, originalText)
        
        // Assert
        assertTrue("Should have medium confidence", 
            assessment.overallConfidence >= 0.3 && assessment.overallConfidence < 0.7)
        assertEquals("Should proceed with caution", 
            ConfidenceValidator.UserRecommendation.PROCEED_WITH_CAUTION, assessment.recommendation)
        assertTrue("Should proceed", assessment.shouldProceed)
        assertNotNull("Should have warning message", assessment.warningMessage)
        assertTrue("Should have low confidence fields", assessment.lowConfidenceFields.isNotEmpty())
    }
    
    @Test
    fun testImprovementSuggestions() {
        // Arrange
        val parseResult = ParseResult(
            title = "event",
            startDateTime = null,
            endDateTime = null,
            location = null,
            description = null,
            confidenceScore = 0.2,
            allDay = false,
            timezone = "UTC"
        )
        val originalText = "event tomorrow morning"
        
        // Act
        val suggestions = confidenceValidator.generateImprovementSuggestions(originalText, parseResult)
        
        // Assert
        assertTrue("Should have improvement suggestions", suggestions.isNotEmpty())
        
        val hasDateSuggestion = suggestions.any { it.type == ConfidenceValidator.SuggestionType.ADD_SPECIFIC_DATE }
        val hasTimeSuggestion = suggestions.any { it.type == ConfidenceValidator.SuggestionType.ADD_SPECIFIC_TIME }
        val hasTitleSuggestion = suggestions.any { it.type == ConfidenceValidator.SuggestionType.CLARIFY_EVENT_TITLE }
        
        assertTrue("Should suggest adding specific date", hasDateSuggestion)
        assertTrue("Should suggest adding specific time", hasTimeSuggestion)
        assertTrue("Should suggest clarifying title", hasTitleSuggestion)
        
        // Check that suggestions have proper structure
        suggestions.forEach { suggestion ->
            assertNotNull("Suggestion should have message", suggestion.message)
            assertNotNull("Suggestion should have type", suggestion.type)
            assertNotNull("Suggestion should have priority", suggestion.priority)
        }
    }
    
    @Test
    fun testFieldLevelAnalysis() {
        // Arrange
        val parseResult = ParseResult(
            title = "Team Standup",
            startDateTime = "2024-12-16T09:00:00",
            endDateTime = "2024-12-16T09:30:00",
            location = "Room 101",
            description = "Daily team standup meeting",
            confidenceScore = 0.8,
            allDay = false,
            timezone = "UTC",
            fieldResults = mapOf(
                "title" to FieldResult("Team Standup", "llm", 0.85, Pair(0, 12), 120),
                "start_datetime" to FieldResult("2024-12-16T09:00:00", "duckling", 0.9, Pair(13, 25), 180),
                "end_datetime" to FieldResult("2024-12-16T09:30:00", "duckling", 0.85, Pair(26, 38), 160),
                "location" to FieldResult("Room 101", "regex", 0.7, Pair(39, 47), 80)
            )
        )
        val originalText = "Team Standup Monday 9 AM to 9:30 AM in Room 101"
        
        // Act
        val assessment = confidenceValidator.assessConfidence(parseResult, originalText)
        
        // Assert
        assertEquals("Should analyze all fields", 5, assessment.fieldConfidences.size)
        
        val titleInfo = assessment.fieldConfidences["title"]
        assertNotNull("Should have title field info", titleInfo)
        assertTrue("Title should have value", titleInfo!!.hasValue)
        assertTrue("Title should be required", titleInfo.isRequired)
        assertTrue("Title should have good confidence", titleInfo.confidence > 0.7)
        
        val startTimeInfo = assessment.fieldConfidences["start_datetime"]
        assertNotNull("Should have start_datetime field info", startTimeInfo)
        assertTrue("Start time should have value", startTimeInfo!!.hasValue)
        assertTrue("Start time should be required", startTimeInfo.isRequired)
        
        val locationInfo = assessment.fieldConfidences["location"]
        assertNotNull("Should have location field info", locationInfo)
        assertTrue("Location should have value", locationInfo!!.hasValue)
        assertFalse("Location should not be required", locationInfo.isRequired)
    }
    
    @Test
    fun testDataQualityAssessment() {
        // Arrange - High quality data
        val highQualityResult = ParseResult(
            title = "Project Review Meeting",
            startDateTime = "2024-12-16T14:00:00",
            endDateTime = "2024-12-16T15:30:00",
            location = "Conference Room B",
            description = "Quarterly project review with stakeholders",
            confidenceScore = 0.9,
            allDay = false,
            timezone = "UTC"
        )
        val highQualityText = "Project Review Meeting on Monday December 16th from 2:00 PM to 3:30 PM in Conference Room B"
        
        // Act
        val highQualityAssessment = confidenceValidator.assessConfidence(highQualityResult, highQualityText)
        
        // Assert
        assertTrue("High quality data should have good data quality score", 
            highQualityAssessment.dataQualityScore > 0.7)
        assertTrue("High quality should have high overall confidence", 
            highQualityAssessment.overallConfidence > 0.7)
        
        // Arrange - Low quality data
        val lowQualityResult = ParseResult(
            title = "mtg",
            startDateTime = "2024-12-16T10:00:00",
            endDateTime = null,
            location = null,
            description = null,
            confidenceScore = 0.3,
            allDay = false,
            timezone = "UTC"
        )
        val lowQualityText = "mtg tmrw"
        
        // Act
        val lowQualityAssessment = confidenceValidator.assessConfidence(lowQualityResult, lowQualityText)
        
        // Assert
        assertTrue("Low quality data should have poor data quality score", 
            lowQualityAssessment.dataQualityScore < 0.5)
        assertTrue("Low quality should have low overall confidence", 
            lowQualityAssessment.overallConfidence < 0.5)
    }
    
    @Test
    fun testAnalysisDetails() {
        // Arrange
        val parseResult = ParseResult(
            title = "Weekly Review",
            startDateTime = "2024-12-16T15:00:00",
            endDateTime = null,
            location = "Office",
            description = null,
            confidenceScore = 0.6,
            allDay = false,
            timezone = "UTC",
            fieldResults = mapOf(
                "title" to FieldResult("Weekly Review", "llm", 0.8, Pair(0, 13), 100),
                "start_datetime" to FieldResult("2024-12-16T15:00:00", "duckling", 0.7, Pair(14, 26), 150),
                "location" to FieldResult("Office", "regex", 0.5, Pair(27, 33), 50)
            ),
            parsingPath = "llm_enhanced",
            processingTimeMs = 1250
        )
        val originalText = "Weekly Review Monday 3 PM at Office"
        
        // Act
        val assessment = confidenceValidator.assessConfidence(parseResult, originalText)
        
        // Assert
        val details = assessment.analysisDetails
        assertEquals("Should count total fields", 5, details.totalFields)
        assertEquals("Should count fields with values", 3, details.fieldsWithValues)
        assertTrue("Should have average field confidence", details.averageFieldConfidence > 0.0)
        assertEquals("Should preserve parsing method", "llm_enhanced", details.parsingMethodUsed)
        assertEquals("Should preserve processing time", 1250L, details.processingTimeMs)
        assertTrue("Should calculate text complexity", details.textComplexityScore > 0.0)
    }
    
    @Test
    fun testStrictValidationMode() {
        // Arrange
        val strictConfig = ConfidenceValidator.ConfidenceValidatorConfig(
            strictValidation = true
        )
        val strictValidator = ConfidenceValidator(mockContext, strictConfig)
        
        val parseResult = ParseResult(
            title = null, // Missing critical field
            startDateTime = "2024-12-16T14:00:00",
            endDateTime = null,
            location = null,
            description = null,
            confidenceScore = 0.5,
            allDay = false,
            timezone = "UTC"
        )
        val originalText = "meeting at 2 PM"
        
        // Act
        val assessment = strictValidator.assessConfidence(parseResult, originalText)
        
        // Assert
        assertEquals("Strict mode should block creation for missing critical fields", 
            ConfidenceValidator.UserRecommendation.BLOCK_CREATION, assessment.recommendation)
        assertFalse("Strict mode should not proceed", assessment.shouldProceed)
        assertEquals("Should have critical warning severity", 
            ConfidenceValidator.WarningSeverity.CRITICAL, assessment.warningSeverity)
    }
    
    @Test
    fun testConfigurableThresholds() {
        // Arrange
        val customConfig = ConfidenceValidator.ConfidenceValidatorConfig(
            highConfidenceThreshold = 0.8,
            mediumConfidenceThreshold = 0.5,
            criticalConfidenceThreshold = 0.2
        )
        val customValidator = ConfidenceValidator(mockContext, customConfig)
        
        val parseResult = ParseResult(
            title = "Meeting",
            startDateTime = "2024-12-16T14:00:00",
            endDateTime = null,
            location = null,
            description = null,
            confidenceScore = 0.6,
            allDay = false,
            timezone = "UTC"
        )
        val originalText = "Meeting Monday at 2 PM"
        
        // Act
        val assessment = customValidator.assessConfidence(parseResult, originalText)
        
        // Assert
        // With higher thresholds, this should be medium confidence
        assertTrue("Should respect custom thresholds", 
            assessment.recommendation == ConfidenceValidator.UserRecommendation.PROCEED_WITH_CAUTION ||
            assessment.recommendation == ConfidenceValidator.UserRecommendation.SUGGEST_IMPROVEMENTS)
    }
    
    @Test
    fun testFallbackAssessment() {
        // Arrange - Create a result that might cause analysis to fail
        val parseResult = ParseResult(
            title = "Test Event",
            startDateTime = "invalid-date-format",
            endDateTime = null,
            location = null,
            description = null,
            confidenceScore = 0.4,
            allDay = false,
            timezone = "UTC"
        )
        val originalText = "Test Event with invalid data"
        
        // Act
        val assessment = confidenceValidator.assessConfidence(parseResult, originalText)
        
        // Assert
        // Should still return a valid assessment even with problematic data
        assertNotNull("Should return assessment", assessment)
        assertTrue("Should have reasonable confidence", assessment.overallConfidence >= 0.0)
        assertNotNull("Should have recommendation", assessment.recommendation)
        assertNotNull("Should have analysis details", assessment.analysisDetails)
    }
}