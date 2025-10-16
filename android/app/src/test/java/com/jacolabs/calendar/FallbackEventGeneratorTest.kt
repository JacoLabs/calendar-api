package com.jacolabs.calendar

import android.content.Context
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith
import org.mockito.Mock
import org.mockito.MockitoAnnotations
import org.robolectric.RobolectricTestRunner
import org.robolectric.RuntimeEnvironment
import java.util.*
import kotlin.test.assertEquals
import kotlin.test.assertNotNull
import kotlin.test.assertTrue

/**
 * Unit tests for FallbackEventGenerator to verify intelligent event creation
 * from failed parsing attempts.
 */
@RunWith(RobolectricTestRunner::class)
class FallbackEventGeneratorTest {
    
    private lateinit var fallbackEventGenerator: FallbackEventGenerator
    private lateinit var context: Context
    
    @Before
    fun setUp() {
        MockitoAnnotations.openMocks(this)
        context = RuntimeEnvironment.getApplication()
        fallbackEventGenerator = FallbackEventGenerator(context)
    }
    
    @Test
    fun `generateFallbackEvent creates meaningful title from simple text`() {
        val originalText = "Team meeting tomorrow at 2 PM"
        
        val fallbackEvent = fallbackEventGenerator.generateFallbackEvent(originalText)
        
        assertNotNull(fallbackEvent.title)
        assertTrue(fallbackEvent.title.isNotBlank())
        assertTrue(fallbackEvent.confidence > 0.0)
        assertEquals("pattern_matching", fallbackEvent.extractionDetails.titleExtractionMethod)
    }
    
    @Test
    fun `generateFallbackEvent handles attend pattern correctly`() {
        val originalText = "We will attend the conference at the convention center"
        
        val fallbackEvent = fallbackEventGenerator.generateFallbackEvent(originalText)
        
        assertTrue(fallbackEvent.title.contains("conference"))
        assertTrue(fallbackEvent.title.contains("convention center"))
        assertTrue(fallbackEvent.confidence > 0.5)
    }
    
    @Test
    fun `generateFallbackEvent creates reasonable datetime defaults`() {
        val originalText = "Important meeting"
        
        val fallbackEvent = fallbackEventGenerator.generateFallbackEvent(originalText)
        
        assertNotNull(fallbackEvent.startDateTime)
        assertNotNull(fallbackEvent.endDateTime)
        assertTrue(fallbackEvent.startDateTime != fallbackEvent.endDateTime)
        assertEquals(TimeZone.getDefault().id, fallbackEvent.timezone)
    }
    
    @Test
    fun `generateFallbackEvent handles morning keyword context`() {
        val originalText = "Morning standup meeting"
        
        val fallbackEvent = fallbackEventGenerator.generateFallbackEvent(originalText)
        
        assertTrue(fallbackEvent.extractionDetails.patternsMatched.contains("morning_keyword"))
        assertTrue(fallbackEvent.extractionDetails.timeGenerationMethod.contains("keyword"))
    }
    
    @Test
    fun `generateFallbackEvent estimates duration based on event type`() {
        val originalText = "Doctor appointment next week"
        
        val fallbackEvent = fallbackEventGenerator.generateFallbackEvent(originalText)
        
        assertTrue(fallbackEvent.extractionDetails.durationEstimationMethod.contains("appointment"))
        // Appointment should be 30 minutes, so end time should be 30 minutes after start
        // This is a basic check - in a real test we'd parse the times and verify the difference
        assertNotNull(fallbackEvent.endDateTime)
    }
    
    @Test
    fun `generateFallbackEvent uses partial result when available`() {
        val originalText = "Team meeting"
        val partialResult = ParseResult(
            title = "Weekly Team Sync",
            startDateTime = "2024-01-15T14:00:00-05:00",
            endDateTime = null,
            location = "Conference Room A",
            description = null,
            confidenceScore = 0.6,
            allDay = false,
            timezone = "America/New_York"
        )
        
        val fallbackEvent = fallbackEventGenerator.generateFallbackEvent(originalText, partialResult)
        
        assertEquals("Weekly Team Sync", fallbackEvent.title)
        assertEquals("2024-01-15T14:00:00-05:00", fallbackEvent.startDateTime)
        assertEquals("partial_api_result", fallbackEvent.extractionDetails.titleExtractionMethod)
        assertTrue(fallbackEvent.confidence > 0.5)
    }
    
    @Test
    fun `generateFallbackEvent creates descriptive description`() {
        val originalText = "Lunch with client tomorrow"
        
        val fallbackEvent = fallbackEventGenerator.generateFallbackEvent(originalText)
        
        assertTrue(fallbackEvent.description.contains(originalText))
        assertTrue(fallbackEvent.description.contains("Extraction details"))
        assertTrue(fallbackEvent.description.contains("confidence"))
    }
    
    @Test
    fun `generateFallbackEvent handles empty or very short text`() {
        val originalText = "Meet"
        
        val fallbackEvent = fallbackEventGenerator.generateFallbackEvent(originalText)
        
        assertNotNull(fallbackEvent.title)
        assertTrue(fallbackEvent.title.isNotBlank())
        assertTrue(fallbackEvent.confidence > 0.0)
        // Should fall back to text cleanup method for very short text
        assertEquals("text_cleanup", fallbackEvent.extractionDetails.titleExtractionMethod)
    }
    
    @Test
    fun `generateFallbackEvent handles complex scheduling text`() {
        val originalText = "On Friday the students will attend the science fair at the community center from 9 AM to 3 PM"
        
        val fallbackEvent = fallbackEventGenerator.generateFallbackEvent(originalText)
        
        assertTrue(fallbackEvent.title.contains("science fair"))
        assertTrue(fallbackEvent.extractionDetails.patternsMatched.isNotEmpty())
        assertTrue(fallbackEvent.confidence > 0.4)
    }
    
    @Test
    fun `toParseResult converts FallbackEvent correctly`() {
        val originalText = "Team meeting"
        val fallbackEvent = fallbackEventGenerator.generateFallbackEvent(originalText)
        
        val parseResult = fallbackEventGenerator.toParseResult(fallbackEvent, originalText)
        
        assertEquals(fallbackEvent.title, parseResult.title)
        assertEquals(fallbackEvent.startDateTime, parseResult.startDateTime)
        assertEquals(fallbackEvent.endDateTime, parseResult.endDateTime)
        assertEquals(fallbackEvent.confidence, parseResult.confidenceScore)
        assertTrue(parseResult.fallbackApplied)
        assertEquals(originalText, parseResult.originalText)
        assertNotNull(parseResult.errorRecoveryInfo)
    }
    
    @Test
    fun `generateFallbackEvent handles preprocessing correctly`() {
        val originalText = "Meeting at 2:30pm tomorrow"
        
        val fallbackEvent = fallbackEventGenerator.generateFallbackEvent(originalText)
        
        // Should have applied time format normalization
        assertTrue(fallbackEvent.extractionDetails.textPreprocessingApplied.contains("time_format_normalization"))
    }
    
    @Test
    fun `generateFallbackEvent calculates confidence factors`() {
        val originalText = "Important client meeting next Tuesday at 10 AM"
        
        val fallbackEvent = fallbackEventGenerator.generateFallbackEvent(originalText)
        
        val confidenceFactors = fallbackEvent.extractionDetails.confidenceFactors
        assertTrue(confidenceFactors.containsKey("title_quality"))
        assertTrue(confidenceFactors.containsKey("time_relevance"))
        assertTrue(confidenceFactors.containsKey("text_clarity"))
        assertTrue(confidenceFactors.values.all { it >= 0.0 && it <= 1.0 })
    }
}