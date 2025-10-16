package com.jacolabs.calendar

import android.content.Context
import android.util.Log

/**
 * Demonstration class showing how to use FallbackEventGenerator
 * for intelligent event creation from failed parsing attempts.
 * 
 * This class provides examples of different scenarios where the
 * FallbackEventGenerator can be used to create meaningful calendar events.
 */
class FallbackEventGeneratorDemo(private val context: Context) {
    
    companion object {
        private const val TAG = "FallbackEventGeneratorDemo"
    }
    
    private val fallbackEventGenerator = FallbackEventGenerator(context)
    
    /**
     * Demonstrates basic fallback event creation from simple text
     */
    fun demonstrateBasicFallback() {
        Log.d(TAG, "=== Basic Fallback Event Creation Demo ===")
        
        val testTexts = listOf(
            "Team meeting tomorrow at 2 PM",
            "Doctor appointment next week",
            "Lunch with client",
            "Conference call at 9 AM",
            "Birthday party on Saturday"
        )
        
        testTexts.forEach { text ->
            Log.d(TAG, "Input: $text")
            
            val fallbackEvent = fallbackEventGenerator.generateFallbackEvent(text)
            
            Log.d(TAG, "Generated Event:")
            Log.d(TAG, "  Title: ${fallbackEvent.title}")
            Log.d(TAG, "  Start: ${fallbackEvent.startDateTime}")
            Log.d(TAG, "  End: ${fallbackEvent.endDateTime}")
            Log.d(TAG, "  Confidence: ${String.format("%.2f", fallbackEvent.confidence)}")
            Log.d(TAG, "  Method: ${fallbackEvent.extractionDetails.titleExtractionMethod}")
            Log.d(TAG, "  Reason: ${fallbackEvent.fallbackReason}")
            Log.d(TAG, "")
        }
    }
    
    /**
     * Demonstrates fallback event creation with partial API results
     */
    fun demonstratePartialResultEnhancement() {
        Log.d(TAG, "=== Partial Result Enhancement Demo ===")
        
        val originalText = "Team standup meeting"
        
        // Simulate a partial result from API with missing end time
        val partialResult = ParseResult(
            title = "Daily Standup",
            startDateTime = "2024-01-15T09:00:00-05:00",
            endDateTime = null, // Missing end time
            location = null,
            description = null,
            confidenceScore = 0.4, // Low confidence
            allDay = false,
            timezone = "America/New_York"
        )
        
        Log.d(TAG, "Original text: $originalText")
        Log.d(TAG, "Partial API result: title='${partialResult.title}', confidence=${partialResult.confidenceScore}")
        
        val enhancedEvent = fallbackEventGenerator.generateFallbackEvent(originalText, partialResult)
        
        Log.d(TAG, "Enhanced Event:")
        Log.d(TAG, "  Title: ${enhancedEvent.title}")
        Log.d(TAG, "  Start: ${enhancedEvent.startDateTime}")
        Log.d(TAG, "  End: ${enhancedEvent.endDateTime}")
        Log.d(TAG, "  Confidence: ${String.format("%.2f", enhancedEvent.confidence)}")
        Log.d(TAG, "  Enhancement reason: ${enhancedEvent.fallbackReason}")
        Log.d(TAG, "")
    }
    
    /**
     * Demonstrates complex text pattern matching
     */
    fun demonstrateComplexPatternMatching() {
        Log.d(TAG, "=== Complex Pattern Matching Demo ===")
        
        val complexTexts = listOf(
            "On Friday the students will attend the science fair at the community center",
            "We will attend the quarterly review meeting at the main office",
            "I need to attend the doctor appointment by 3 PM tomorrow",
            "The team will participate in the training session next Monday morning"
        )
        
        complexTexts.forEach { text ->
            Log.d(TAG, "Complex input: $text")
            
            val fallbackEvent = fallbackEventGenerator.generateFallbackEvent(text)
            
            Log.d(TAG, "Extracted:")
            Log.d(TAG, "  Title: ${fallbackEvent.title}")
            Log.d(TAG, "  Patterns matched: ${fallbackEvent.extractionDetails.patternsMatched}")
            Log.d(TAG, "  Preprocessing applied: ${fallbackEvent.extractionDetails.textPreprocessingApplied}")
            Log.d(TAG, "  Confidence factors: ${fallbackEvent.extractionDetails.confidenceFactors}")
            Log.d(TAG, "")
        }
    }
    
    /**
     * Demonstrates time context analysis
     */
    fun demonstrateTimeContextAnalysis() {
        Log.d(TAG, "=== Time Context Analysis Demo ===")
        
        val timeContextTexts = listOf(
            "Morning team meeting",
            "Afternoon client call",
            "Evening dinner with family",
            "Lunch meeting tomorrow",
            "Weekend workshop",
            "All day conference"
        )
        
        timeContextTexts.forEach { text ->
            Log.d(TAG, "Time context input: $text")
            
            val fallbackEvent = fallbackEventGenerator.generateFallbackEvent(text)
            
            Log.d(TAG, "Time analysis:")
            Log.d(TAG, "  Generated time: ${fallbackEvent.startDateTime}")
            Log.d(TAG, "  All day: ${fallbackEvent.allDay}")
            Log.d(TAG, "  Time method: ${fallbackEvent.extractionDetails.timeGenerationMethod}")
            Log.d(TAG, "  Duration method: ${fallbackEvent.extractionDetails.durationEstimationMethod}")
            Log.d(TAG, "")
        }
    }
    
    /**
     * Demonstrates conversion to ParseResult for API compatibility
     */
    fun demonstrateParseResultConversion() {
        Log.d(TAG, "=== ParseResult Conversion Demo ===")
        
        val originalText = "Important client presentation next Tuesday"
        
        val fallbackEvent = fallbackEventGenerator.generateFallbackEvent(originalText)
        val parseResult = fallbackEventGenerator.toParseResult(fallbackEvent, originalText)
        
        Log.d(TAG, "Original FallbackEvent:")
        Log.d(TAG, "  Title: ${fallbackEvent.title}")
        Log.d(TAG, "  Confidence: ${fallbackEvent.confidence}")
        Log.d(TAG, "  Extraction details available: ${fallbackEvent.extractionDetails}")
        
        Log.d(TAG, "Converted ParseResult:")
        Log.d(TAG, "  Title: ${parseResult.title}")
        Log.d(TAG, "  Confidence: ${parseResult.confidenceScore}")
        Log.d(TAG, "  Fallback applied: ${parseResult.fallbackApplied}")
        Log.d(TAG, "  Original text preserved: ${parseResult.originalText}")
        Log.d(TAG, "  Error recovery info: ${parseResult.errorRecoveryInfo}")
        Log.d(TAG, "")
    }
    
    /**
     * Runs all demonstrations
     */
    fun runAllDemonstrations() {
        Log.d(TAG, "Starting FallbackEventGenerator demonstrations...")
        
        demonstrateBasicFallback()
        demonstratePartialResultEnhancement()
        demonstrateComplexPatternMatching()
        demonstrateTimeContextAnalysis()
        demonstrateParseResultConversion()
        
        Log.d(TAG, "All demonstrations completed!")
    }
    
    /**
     * Demonstrates error handling integration
     */
    fun demonstrateErrorHandlingIntegration() {
        Log.d(TAG, "=== Error Handling Integration Demo ===")
        
        val errorHandlingManager = ErrorHandlingManager(context)
        val originalText = "Team meeting with low confidence parsing"
        
        // Simulate a low confidence API result
        val lowConfidenceResult = ParseResult(
            title = "Meeting",
            startDateTime = null,
            endDateTime = null,
            location = null,
            description = null,
            confidenceScore = 0.2, // Very low confidence
            allDay = false,
            timezone = "UTC"
        )
        
        // Create error context
        val errorContext = ErrorHandlingManager.ErrorContext(
            errorType = ErrorHandlingManager.ErrorType.LOW_CONFIDENCE,
            originalText = originalText,
            apiResponse = lowConfidenceResult,
            confidenceScore = 0.2
        )
        
        Log.d(TAG, "Simulating low confidence error handling...")
        Log.d(TAG, "Original text: $originalText")
        Log.d(TAG, "API confidence: ${lowConfidenceResult.confidenceScore}")
        
        // The ErrorHandlingManager will use FallbackEventGenerator internally
        val fallbackResult = errorHandlingManager.createFallbackEvent(originalText, lowConfidenceResult)
        
        Log.d(TAG, "Error handling result:")
        Log.d(TAG, "  Enhanced title: ${fallbackResult.title}")
        Log.d(TAG, "  Generated time: ${fallbackResult.startDateTime}")
        Log.d(TAG, "  Fallback applied: ${fallbackResult.fallbackApplied}")
        Log.d(TAG, "  Recovery method: ${fallbackResult.errorRecoveryInfo?.recoveryMethod}")
        Log.d(TAG, "")
    }
}