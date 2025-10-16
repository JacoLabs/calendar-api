package com.jacolabs.calendar

import android.content.Context
import android.util.Log
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch

/**
 * Example integration of the comprehensive error logging and diagnostics system.
 * 
 * This demonstrates how to use the enhanced ErrorHandlingManager with:
 * - Comprehensive error logging (Requirements 7.1-7.4)
 * - Failure pattern analysis (Requirements 9.1-9.4)
 * - User-friendly error reporting
 * - Privacy-compliant diagnostics
 */
class ErrorLoggingIntegrationExample(private val context: Context) {
    
    companion object {
        private const val TAG = "ErrorLoggingExample"
    }
    
    private val errorHandlingManager = ErrorHandlingManager(context)
    private val scope = CoroutineScope(Dispatchers.Main)
    
    /**
     * Example: Handling a parsing failure with comprehensive logging
     */
    fun handleParsingFailureExample(originalText: String) {
        scope.launch {
            try {
                // Simulate a parsing failure
                val errorContext = ErrorHandlingManager.ErrorContext(
                    errorType = ErrorHandlingManager.ErrorType.PARSING_FAILURE,
                    originalText = originalText,
                    processingTimeMs = 1500,
                    retryCount = 0,
                    networkAvailable = true,
                    userInteractionAllowed = true
                )
                
                // Handle the error with comprehensive logging
                val result = errorHandlingManager.handleError(errorContext)
                
                // The error is now logged with:
                // - Detailed context information
                // - Privacy-protected text analysis
                // - Pattern analysis for learning
                // - User-friendly error code
                
                Log.i(TAG, "Error handled with code: ${result.analyticsData["error_code"]}")
                Log.i(TAG, "Recovery strategy: ${result.recoveryStrategy}")
                Log.i(TAG, "User message: ${result.userMessage}")
                
                // Get improvement suggestions based on the failure
                val suggestions = errorHandlingManager.getImprovementSuggestions(originalText)
                Log.i(TAG, "Improvement suggestions: $suggestions")
                
            } catch (e: Exception) {
                Log.e(TAG, "Failed to handle parsing failure example", e)
            }
        }
    }
    
    /**
     * Example: Recording a user correction for learning
     */
    fun recordUserCorrectionExample(
        originalText: String,
        originalTitle: String?,
        correctedTitle: String
    ) {
        scope.launch {
            try {
                // Record the user correction for learning
                errorHandlingManager.recordUserCorrection(
                    originalText = originalText,
                    fieldCorrected = "title",
                    originalValue = originalTitle,
                    correctedValue = correctedTitle,
                    originalConfidence = 0.4,
                    processingTimeMs = 2000,
                    userInteractionTime = 15000 // User took 15 seconds to make correction
                )
                
                Log.i(TAG, "User correction recorded for learning")
                
                // Get updated suggestions based on the correction
                val suggestions = errorHandlingManager.getImprovementSuggestions()
                Log.i(TAG, "Updated suggestions after correction: $suggestions")
                
            } catch (e: Exception) {
                Log.e(TAG, "Failed to record user correction", e)
            }
        }
    }
    
    /**
     * Example: Generating a user-friendly error report
     */
    fun generateErrorReportExample(errorCode: String) {
        scope.launch {
            try {
                val errorReport = errorHandlingManager.generateUserErrorReport(errorCode)
                
                if (errorReport != null) {
                    Log.i(TAG, "Error Report Generated:")
                    Log.i(TAG, "- Error Code: ${errorReport.errorCode}")
                    Log.i(TAG, "- Timestamp: ${errorReport.timestamp}")
                    Log.i(TAG, "- User Message: ${errorReport.userFriendlyMessage}")
                    Log.i(TAG, "- Can Retry: ${errorReport.canRetry}")
                    Log.i(TAG, "- Needs Support: ${errorReport.needsSupport}")
                    Log.i(TAG, "- Suggested Actions: ${errorReport.suggestedActions}")
                    
                    // If support is needed, create support email
                    if (errorReport.needsSupport) {
                        val supportIntent = errorHandlingManager.createSupportEmailIntent(errorCode)
                        Log.i(TAG, "Support email intent created")
                        // In a real app, you would start this intent:
                        // context.startActivity(Intent.createChooser(supportIntent, "Send Support Email"))
                    }
                } else {
                    Log.w(TAG, "No error report found for code: $errorCode")
                }
                
            } catch (e: Exception) {
                Log.e(TAG, "Failed to generate error report", e)
            }
        }
    }
    
    /**
     * Example: Performing a system health check
     */
    fun performHealthCheckExample() {
        scope.launch {
            try {
                val healthCheck = errorHandlingManager.getSystemHealthCheck()
                
                Log.i(TAG, "System Health Check:")
                healthCheck.forEach { (key, value) ->
                    Log.i(TAG, "- $key: $value")
                }
                
                // Check for known issues
                val knownIssues = errorHandlingManager.checkForKnownIssues()
                if (knownIssues.isNotEmpty()) {
                    Log.w(TAG, "Known Issues Detected:")
                    knownIssues.forEach { issue ->
                        Log.w(TAG, "- $issue")
                    }
                }
                
                // Get pattern statistics
                val patternStats = errorHandlingManager.getPatternStatistics()
                Log.i(TAG, "Pattern Statistics: $patternStats")
                
            } catch (e: Exception) {
                Log.e(TAG, "Failed to perform health check", e)
            }
        }
    }
    
    /**
     * Example: Generating a comprehensive diagnostic report
     */
    fun generateDiagnosticReportExample() {
        scope.launch {
            try {
                val diagnosticReport = errorHandlingManager.generateDiagnosticReport()
                
                Log.i(TAG, "Comprehensive Diagnostic Report Generated:")
                Log.i(TAG, "- Report ID: ${diagnosticReport.reportId}")
                Log.i(TAG, "- Generated At: ${diagnosticReport.generatedAt}")
                Log.i(TAG, "- Total Errors: ${diagnosticReport.summary.totalErrors}")
                Log.i(TAG, "- Critical Errors: ${diagnosticReport.summary.criticalErrors}")
                Log.i(TAG, "- Success Rate: ${diagnosticReport.summary.successRate}")
                Log.i(TAG, "- System Stability: ${diagnosticReport.summary.systemStability}")
                Log.i(TAG, "- Most Common Error: ${diagnosticReport.summary.mostCommonErrorType}")
                
                // Log improvement suggestions
                if (diagnosticReport.improvementSuggestions.isNotEmpty()) {
                    Log.i(TAG, "Improvement Suggestions:")
                    diagnosticReport.improvementSuggestions.forEach { suggestion ->
                        Log.i(TAG, "- $suggestion")
                    }
                }
                
                // Export diagnostic data (privacy-safe version)
                val exportFile = errorHandlingManager.exportDiagnosticData(includePersonalData = false)
                if (exportFile != null) {
                    Log.i(TAG, "Diagnostic data exported to: ${exportFile.absolutePath}")
                } else {
                    Log.w(TAG, "Failed to export diagnostic data")
                }
                
            } catch (e: Exception) {
                Log.e(TAG, "Failed to generate diagnostic report", e)
            }
        }
    }
    
    /**
     * Example: Handling a critical error
     */
    fun handleCriticalErrorExample() {
        scope.launch {
            try {
                // Simulate a critical error
                val criticalException = RuntimeException("Critical system failure in calendar integration")
                
                val errorCode = errorHandlingManager.logCriticalError(
                    message = "Calendar integration system failure",
                    exception = criticalException
                )
                
                Log.e(TAG, "Critical error logged with code: $errorCode")
                
                // Generate immediate error report for critical issues
                val errorReport = errorHandlingManager.generateUserErrorReport(errorCode)
                if (errorReport != null) {
                    Log.e(TAG, "Critical Error Report: ${errorReport.userFriendlyMessage}")
                    
                    // For critical errors, automatically create support contact
                    val supportIntent = errorHandlingManager.createSupportEmailIntent(errorCode)
                    Log.e(TAG, "Support contact created for critical error")
                }
                
            } catch (e: Exception) {
                Log.e(TAG, "Failed to handle critical error example", e)
            }
        }
    }
    
    /**
     * Example: Analyzing preprocessing effectiveness
     */
    fun analyzePreprocessingEffectivenessExample() {
        scope.launch {
            try {
                val effectiveness = errorHandlingManager.analyzePreprocessingEffectiveness()
                
                Log.i(TAG, "Preprocessing Effectiveness Analysis:")
                effectiveness.forEach { (metric, value) ->
                    Log.i(TAG, "- $metric: ${String.format("%.2f", value)}")
                }
                
                // Use effectiveness data to adjust preprocessing strategies
                val titleCorrectionRate = effectiveness["title_correction_rate"] ?: 0.0
                if (titleCorrectionRate > 0.3) {
                    Log.w(TAG, "High title correction rate detected - consider improving title extraction")
                }
                
                val parsingImprovement = effectiveness["PARSING_FAILURE_improvement"] ?: 0.0
                if (parsingImprovement < 0.5) {
                    Log.w(TAG, "Low parsing improvement - consider updating parsing algorithms")
                }
                
            } catch (e: Exception) {
                Log.e(TAG, "Failed to analyze preprocessing effectiveness", e)
            }
        }
    }
    
    /**
     * Example: Privacy-compliant data management
     */
    fun privacyComplianceExample() {
        scope.launch {
            try {
                Log.i(TAG, "Demonstrating privacy-compliant data management...")
                
                // All logging automatically anonymizes sensitive data
                // User can clear all diagnostic data at any time
                
                // Show current data status
                val patternStats = errorHandlingManager.getPatternStatistics()
                Log.i(TAG, "Current diagnostic data: $patternStats")
                
                // User requests data deletion (GDPR compliance)
                Log.i(TAG, "User requested data deletion - clearing all diagnostic data")
                errorHandlingManager.clearDiagnosticData()
                
                // Verify data is cleared
                val clearedStats = errorHandlingManager.getPatternStatistics()
                Log.i(TAG, "Data after clearing: $clearedStats")
                
                Log.i(TAG, "Privacy compliance demonstrated - all data cleared")
                
            } catch (e: Exception) {
                Log.e(TAG, "Failed to demonstrate privacy compliance", e)
            }
        }
    }
    
    /**
     * Comprehensive example showing the full error handling workflow
     */
    fun comprehensiveWorkflowExample() {
        scope.launch {
            try {
                Log.i(TAG, "Starting comprehensive error handling workflow example...")
                
                val originalText = "meeting tomorrow afternoon"
                
                // 1. Handle parsing failure with comprehensive logging
                handleParsingFailureExample(originalText)
                
                // 2. Simulate user correction
                recordUserCorrectionExample(originalText, "meeting", "Team meeting with John")
                
                // 3. Perform health check
                performHealthCheckExample()
                
                // 4. Generate diagnostic report
                generateDiagnosticReportExample()
                
                // 5. Analyze effectiveness
                analyzePreprocessingEffectivenessExample()
                
                Log.i(TAG, "Comprehensive workflow example completed")
                
            } catch (e: Exception) {
                Log.e(TAG, "Failed to complete comprehensive workflow example", e)
            }
        }
    }
}