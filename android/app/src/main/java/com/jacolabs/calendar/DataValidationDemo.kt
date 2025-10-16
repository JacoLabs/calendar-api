package com.jacolabs.calendar

import android.content.Context
import android.util.Log
import kotlinx.coroutines.runBlocking

/**
 * Demonstration class showing data validation and sanitization capabilities.
 * Provides examples of how the validation system handles various data scenarios.
 */
class DataValidationDemo(private val context: Context) {
    
    companion object {
        private const val TAG = "DataValidationDemo"
    }
    
    private val dataValidationManager = DataValidationManager(context)
    private val errorHandlingManager = ErrorHandlingManager(context)
    private val validationIntegration = ValidationIntegration(context, errorHandlingManager)
    
    /**
     * Runs comprehensive validation demos
     */
    fun runValidationDemos() {
        Log.i(TAG, "Starting Data Validation Demos")
        
        // Demo 1: Valid data with minor issues
        demoValidDataWithMinorIssues()
        
        // Demo 2: Missing essential fields
        demoMissingEssentialFields()
        
        // Demo 3: Invalid data formats
        demoInvalidDataFormats()
        
        // Demo 4: Low confidence handling
        demoLowConfidenceHandling()
        
        // Demo 5: Data sanitization
        demoDataSanitization()
        
        // Demo 6: Smart defaults application
        demoSmartDefaults()
        
        // Demo 7: Integration with error handling
        demoErrorHandlingIntegration()
        
        Log.i(TAG, "Data Validation Demos completed")
    }
    
    /**
     * Demo 1: Valid data with minor formatting issues
     */
    private fun demoValidDataWithMinorIssues() {
        Log.i(TAG, "Demo 1: Valid data with minor issues")
        
        val testResult = ParseResult(
            title = "  Team Meeting   ", // Extra whitespace
            startDateTime = "2024-12-15T14:00:00+00:00",
            endDateTime = "2024-12-15T15:00:00+00:00",
            location = "Conference Room A",
            description = "Weekly team sync meeting",
            confidenceScore = 0.85,
            allDay = false,
            timezone = "UTC"
        )
        
        val validationResult = dataValidationManager.validateAndSanitize(testResult, "Team meeting at 2 PM")
        
        Log.i(TAG, "Validation passed: ${validationResult.isValid}")
        Log.i(TAG, "Sanitized title: '${validationResult.sanitizedResult.title}'")
        Log.i(TAG, "Issues found: ${validationResult.issues.size}")
        Log.i(TAG, "Data integrity score: ${validationResult.dataIntegrityScore}")
    }
    
    /**
     * Demo 2: Missing essential fields
     */
    private fun demoMissingEssentialFields() {
        Log.i(TAG, "Demo 2: Missing essential fields")
        
        val testResult = ParseResult(
            title = null, // Missing title
            startDateTime = null, // Missing start time
            endDateTime = null,
            location = "Office",
            description = "Some event",
            confidenceScore = 0.3,
            allDay = false,
            timezone = "UTC"
        )
        
        val validationResult = dataValidationManager.validateAndSanitize(testResult, "Something happening at the office")
        
        Log.i(TAG, "Validation passed: ${validationResult.isValid}")
        Log.i(TAG, "Applied defaults: ${validationResult.appliedDefaults}")
        Log.i(TAG, "Generated title: '${validationResult.sanitizedResult.title}'")
        Log.i(TAG, "Generated start time: ${validationResult.sanitizedResult.startDateTime}")
    }
    
    /**
     * Demo 3: Invalid data formats
     */
    private fun demoInvalidDataFormats() {
        Log.i(TAG, "Demo 3: Invalid data formats")
        
        val testResult = ParseResult(
            title = "Meeting with <script>alert('xss')</script> client", // Malicious content
            startDateTime = "invalid-date-format",
            endDateTime = "2024-12-15T13:00:00+00:00", // End before start
            location = "Room\u0000A\u0001", // Control characters
            description = "Meeting\n\n\n\n\n\ndescription", // Excessive newlines
            confidenceScore = 0.6,
            allDay = false,
            timezone = "UTC"
        )
        
        val validationResult = dataValidationManager.validateAndSanitize(testResult, "Meeting with client")
        
        Log.i(TAG, "Validation passed: ${validationResult.isValid}")
        Log.i(TAG, "Sanitized title: '${validationResult.sanitizedResult.title}'")
        Log.i(TAG, "Sanitized location: '${validationResult.sanitizedResult.location}'")
        Log.i(TAG, "Critical issues: ${validationResult.issues.count { it.severity == DataValidationManager.ValidationSeverity.ERROR }}")
    }
    
    /**
     * Demo 4: Low confidence handling
     */
    private fun demoLowConfidenceHandling() {
        Log.i(TAG, "Demo 4: Low confidence handling")
        
        val testResult = ParseResult(
            title = "Event",
            startDateTime = "2024-12-15T10:00:00+00:00",
            endDateTime = "2024-12-15T11:00:00+00:00",
            location = null,
            description = "",
            confidenceScore = 0.2, // Very low confidence
            allDay = false,
            timezone = "UTC"
        )
        
        val validationResult = dataValidationManager.validateAndSanitize(testResult, "something tomorrow")
        
        Log.i(TAG, "Confidence assessment: ${validationResult.confidenceAssessment.overallConfidence}")
        Log.i(TAG, "Confidence warnings: ${validationResult.confidenceAssessment.confidenceWarnings}")
        Log.i(TAG, "Recommended actions: ${validationResult.confidenceAssessment.recommendedActions}")
    }
    
    /**
     * Demo 5: Data sanitization
     */
    private fun demoDataSanitization() {
        Log.i(TAG, "Demo 5: Data sanitization")
        
        val dirtyTitle = "Meeting!!!   with    client<script>alert('test')</script>"
        val dirtyLocation = "Room\u0001A\u0002\u0003"
        val dirtyDescription = "This is a\n\n\n\n\nvery\t\t\tspaced\u0000description"
        
        val sanitizedTitle = DataSanitizer.sanitizeTitle(dirtyTitle)
        val sanitizedLocation = DataSanitizer.sanitizeLocation(dirtyLocation)
        val sanitizedDescription = DataSanitizer.sanitizeDescription(dirtyDescription)
        
        Log.i(TAG, "Original title: '$dirtyTitle'")
        Log.i(TAG, "Sanitized title: '$sanitizedTitle'")
        Log.i(TAG, "Original location: '$dirtyLocation'")
        Log.i(TAG, "Sanitized location: '$sanitizedLocation'")
        Log.i(TAG, "Original description: '$dirtyDescription'")
        Log.i(TAG, "Sanitized description: '$sanitizedDescription'")
    }
    
    /**
     * Demo 6: Smart defaults application
     */
    private fun demoSmartDefaults() {
        Log.i(TAG, "Demo 6: Smart defaults application")
        
        val testResult = ParseResult(
            title = "",
            startDateTime = null,
            endDateTime = null,
            location = null,
            description = null,
            confidenceScore = 0.1,
            allDay = false,
            timezone = "UTC"
        )
        
        val originalText = "We need to discuss the quarterly budget review next week"
        val validationResult = dataValidationManager.validateAndSanitize(testResult, originalText)
        
        Log.i(TAG, "Applied defaults: ${validationResult.appliedDefaults}")
        Log.i(TAG, "Generated title: '${validationResult.sanitizedResult.title}'")
        Log.i(TAG, "Generated start time: ${validationResult.sanitizedResult.startDateTime}")
        Log.i(TAG, "Generated description: '${validationResult.sanitizedResult.description}'")
    }
    
    /**
     * Demo 7: Integration with error handling
     */
    private fun demoErrorHandlingIntegration() {
        Log.i(TAG, "Demo 7: Integration with error handling")
        
        runBlocking {
            val problematicResult = ParseResult(
                title = null,
                startDateTime = "invalid",
                endDateTime = null,
                location = null,
                description = null,
                confidenceScore = 0.1,
                allDay = false,
                timezone = "UTC"
            )
            
            val originalText = "something"
            val errorResult = validationIntegration.validateWithErrorHandling(problematicResult, originalText)
            
            Log.i(TAG, "Error handling success: ${errorResult.success}")
            Log.i(TAG, "Recovery strategy: ${errorResult.recoveryStrategy}")
            Log.i(TAG, "User message: ${errorResult.userMessage}")
            Log.i(TAG, "Analytics data: ${errorResult.analyticsData}")
            
            errorResult.recoveredResult?.let { recovered ->
                Log.i(TAG, "Recovered title: '${recovered.title}'")
                Log.i(TAG, "Recovered start time: ${recovered.startDateTime}")
            }
        }
    }
    
    /**
     * Demonstrates quick validation for UI feedback
     */
    fun demoQuickValidation() {
        Log.i(TAG, "Demo: Quick validation for UI feedback")
        
        val testCases = listOf(
            ParseResult(
                title = "Good Meeting",
                startDateTime = "2024-12-15T14:00:00+00:00",
                endDateTime = "2024-12-15T15:00:00+00:00",
                confidenceScore = 0.9,
                allDay = false,
                timezone = "UTC"
            ),
            ParseResult(
                title = "Uncertain Event",
                startDateTime = "2024-12-15T14:00:00+00:00",
                endDateTime = "2024-12-15T15:00:00+00:00",
                confidenceScore = 0.4,
                allDay = false,
                timezone = "UTC"
            ),
            ParseResult(
                title = null,
                startDateTime = null,
                endDateTime = null,
                confidenceScore = 0.1,
                allDay = false,
                timezone = "UTC"
            )
        )
        
        testCases.forEachIndexed { index, testCase ->
            val quickResult = validationIntegration.validateQuick(testCase)
            Log.i(TAG, "Test case ${index + 1}:")
            Log.i(TAG, "  Has essential data: ${quickResult.hasEssentialData}")
            Log.i(TAG, "  Confidence level: ${quickResult.confidenceLevel}")
            Log.i(TAG, "  Ready for creation: ${quickResult.readyForCreation}")
        }
    }
    
    /**
     * Demonstrates validation configuration
     */
    fun demoValidationConfiguration() {
        Log.i(TAG, "Demo: Validation configuration")
        
        val config = validationIntegration.getValidationConfig()
        
        Log.i(TAG, "Current configuration:")
        Log.i(TAG, "  Min confidence threshold: ${config.minConfidenceThreshold}")
        Log.i(TAG, "  Warning confidence threshold: ${config.warningConfidenceThreshold}")
        Log.i(TAG, "  Max title length: ${config.maxTitleLength}")
        Log.i(TAG, "  Enable strict validation: ${config.enableStrictValidation}")
        Log.i(TAG, "  Enable auto sanitization: ${config.enableAutoSanitization}")
        Log.i(TAG, "  Enable smart defaults: ${config.enableSmartDefaults}")
        
        // Demonstrate configuration update
        validationIntegration.updateValidationConfig(mapOf(
            "minConfidenceThreshold" to 0.4,
            "enableStrictValidation" to true
        ))
        
        Log.i(TAG, "Updated min confidence threshold: ${config.minConfidenceThreshold}")
        Log.i(TAG, "Updated strict validation: ${config.enableStrictValidation}")
    }
}