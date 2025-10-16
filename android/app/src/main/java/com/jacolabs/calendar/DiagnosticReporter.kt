package com.jacolabs.calendar

import android.content.Context
import android.content.Intent
import android.net.Uri
import android.util.Log
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONObject
import java.io.File
import java.text.SimpleDateFormat
import java.util.*

/**
 * Diagnostic reporter for generating user-friendly error reports and support information.
 * 
 * Addresses requirements:
 * - 7.3: Provide users with error codes for support purposes
 * - 7.4: Respect user privacy in diagnostic reporting
 * - 9.1: Analyze error patterns for troubleshooting
 * - 9.2: Provide improvement suggestions based on patterns
 */
class DiagnosticReporter(
    private val context: Context,
    private val errorLoggingManager: ErrorLoggingManager
) {
    
    companion object {
        private const val TAG = "DiagnosticReporter"
        private const val SUPPORT_EMAIL = "support@jacolabs.com"
        private const val DIAGNOSTIC_FILE_NAME = "diagnostic_report.json"
    }
    
    private val dateFormatter = SimpleDateFormat("yyyy-MM-dd HH:mm:ss", Locale.US)
    
    /**
     * User-friendly error report for support purposes
     */
    data class UserErrorReport(
        val errorCode: String,
        val timestamp: String,
        val userFriendlyMessage: String,
        val technicalSummary: String,
        val suggestedActions: List<String>,
        val systemInfo: String,
        val canRetry: Boolean,
        val needsSupport: Boolean
    )
    
    /**
     * Comprehensive diagnostic report for troubleshooting
     */
    data class ComprehensiveDiagnosticReport(
        val reportId: String,
        val generatedAt: String,
        val summary: DiagnosticSummary,
        val errorAnalysis: ErrorAnalysis,
        val systemHealth: SystemHealthReport,
        val improvementSuggestions: List<String>,
        val supportInformation: SupportInformation
    )
    
    data class DiagnosticSummary(
        val totalErrors: Int,
        val criticalErrors: Int,
        val mostCommonErrorType: String,
        val successRate: Double,
        val systemStability: String
    )
    
    data class ErrorAnalysis(
        val errorPatterns: List<ErrorPattern>,
        val timeDistribution: Map<String, Int>,
        val networkRelatedErrors: Int,
        val parsingRelatedErrors: Int,
        val userCorrectionRate: Double
    )
    
    data class ErrorPattern(
        val pattern: String,
        val frequency: Int,
        val impact: String,
        val suggestion: String
    )
    
    data class SystemHealthReport(
        val memoryStatus: String,
        val storageStatus: String,
        val networkStatus: String,
        val appVersion: String,
        val deviceCompatibility: String
    )
    
    data class SupportInformation(
        val contactEmail: String,
        val reportId: String,
        val debugInstructions: List<String>,
        val knownIssues: List<String>
    )
    
    /**
     * Generates a user-friendly error report for a specific error code
     * Requirement 7.3: Provide error codes for support purposes
     */
    suspend fun generateUserErrorReport(errorCode: String): UserErrorReport? = withContext(Dispatchers.IO) {
        try {
            val diagnosticReport = errorLoggingManager.getDiagnosticReport()
            val errorEntry = findErrorByCode(diagnosticReport, errorCode)
            
            if (errorEntry != null) {
                UserErrorReport(
                    errorCode = errorCode,
                    timestamp = dateFormatter.format(Date(errorEntry.timestamp)),
                    userFriendlyMessage = generateUserFriendlyMessage(errorEntry),
                    technicalSummary = generateTechnicalSummary(errorEntry),
                    suggestedActions = generateSuggestedActions(errorEntry),
                    systemInfo = generateSystemInfo(diagnosticReport.deviceInfo, diagnosticReport.networkInfo),
                    canRetry = canRetryError(errorEntry),
                    needsSupport = needsSupportContact(errorEntry)
                )
            } else {
                null
            }
        } catch (e: Exception) {
            Log.e(TAG, "Failed to generate user error report", e)
            null
        }
    }
    
    /**
     * Generates a comprehensive diagnostic report for troubleshooting
     * Requirement 9.1: Analyze error patterns for troubleshooting
     */
    suspend fun generateComprehensiveDiagnosticReport(): ComprehensiveDiagnosticReport = withContext(Dispatchers.IO) {
        try {
            val diagnosticReport = errorLoggingManager.getDiagnosticReport()
            val reportId = generateReportId()
            
            ComprehensiveDiagnosticReport(
                reportId = reportId,
                generatedAt = dateFormatter.format(Date()),
                summary = generateDiagnosticSummary(diagnosticReport),
                errorAnalysis = generateErrorAnalysis(diagnosticReport),
                systemHealth = generateSystemHealthReport(diagnosticReport),
                improvementSuggestions = generateImprovementSuggestions(diagnosticReport),
                supportInformation = generateSupportInformation(reportId)
            )
        } catch (e: Exception) {
            Log.e(TAG, "Failed to generate comprehensive diagnostic report", e)
            createEmptyDiagnosticReport()
        }
    }
    
    /**
     * Exports diagnostic report for sharing with support
     * Requirement 7.4: Privacy-compliant diagnostic export
     */
    suspend fun exportDiagnosticReport(includePersonalData: Boolean = false): File? = withContext(Dispatchers.IO) {
        try {
            val report = generateComprehensiveDiagnosticReport()
            val exportFile = File(context.cacheDir, DIAGNOSTIC_FILE_NAME)
            
            val exportData = if (includePersonalData) {
                // Include full diagnostic data (with user consent)
                createFullDiagnosticExport(report)
            } else {
                // Privacy-safe export with anonymized data
                createAnonymizedDiagnosticExport(report)
            }
            
            exportFile.writeText(exportData.toString(2))
            exportFile
        } catch (e: Exception) {
            Log.e(TAG, "Failed to export diagnostic report", e)
            null
        }
    }
    
    /**
     * Creates a support email intent with diagnostic information
     * Requirement 7.3: Facilitate support contact with error codes
     */
    fun createSupportEmailIntent(errorCode: String? = null): Intent {
        val subject = if (errorCode != null) {
            "Calendar App Support Request - Error Code: $errorCode"
        } else {
            "Calendar App Support Request"
        }
        
        val body = buildString {
            appendLine("Hello Support Team,")
            appendLine()
            appendLine("I'm experiencing an issue with the Calendar Event Creator app.")
            appendLine()
            
            if (errorCode != null) {
                appendLine("Error Code: $errorCode")
                appendLine("Timestamp: ${dateFormatter.format(Date())}")
                appendLine()
            }
            
            appendLine("Device Information:")
            val deviceInfo = errorLoggingManager.getDiagnosticReport().deviceInfo
            appendLine("- Device: ${deviceInfo.manufacturer} ${deviceInfo.deviceModel}")
            appendLine("- Android Version: ${deviceInfo.androidVersion} (API ${deviceInfo.apiLevel})")
            appendLine("- App Version: ${deviceInfo.appVersion}")
            appendLine()
            
            appendLine("Please describe the issue you're experiencing:")
            appendLine("[Please describe what you were trying to do and what happened]")
            appendLine()
            
            appendLine("Steps to reproduce:")
            appendLine("1. [First step]")
            appendLine("2. [Second step]")
            appendLine("3. [What happened]")
            appendLine()
            
            appendLine("Thank you for your help!")
        }
        
        return Intent(Intent.ACTION_SENDTO).apply {
            data = Uri.parse("mailto:")
            putExtra(Intent.EXTRA_EMAIL, arrayOf(SUPPORT_EMAIL))
            putExtra(Intent.EXTRA_SUBJECT, subject)
            putExtra(Intent.EXTRA_TEXT, body)
        }
    }
    
    /**
     * Gets improvement suggestions based on recent error patterns
     * Requirement 9.2: Provide improvement suggestions based on patterns
     */
    suspend fun getPersonalizedImprovementSuggestions(
        recentTextLength: Int = 0
    ): List<String> = withContext(Dispatchers.IO) {
        try {
            val suggestions = errorLoggingManager.getImprovementSuggestions(recentTextLength)
            
            suggestions.map { suggestion ->
                when (suggestion.type) {
                    "PARSING_FAILURE" -> "💡 ${suggestion.suggestion}"
                    "LOW_CONFIDENCE" -> "🎯 ${suggestion.suggestion}"
                    "API_ERROR" -> "🌐 ${suggestion.suggestion}"
                    "NETWORK_ERROR" -> "📶 ${suggestion.suggestion}"
                    else -> "ℹ️ ${suggestion.suggestion}"
                }
            }.take(5) // Limit to top 5 suggestions
        } catch (e: Exception) {
            Log.w(TAG, "Failed to get improvement suggestions", e)
            getDefaultImprovementSuggestions()
        }
    }
    
    /**
     * Checks if the system is experiencing known issues
     */
    suspend fun checkForKnownIssues(): List<String> = withContext(Dispatchers.IO) {
        val knownIssues = mutableListOf<String>()
        
        try {
            val diagnosticReport = errorLoggingManager.getDiagnosticReport()
            
            // Check for common patterns that indicate known issues
            val errorStats = diagnosticReport.errorStatistics
            
            if (errorStats.errorsByType.getOrDefault("NETWORK_ERROR", 0) > 5) {
                knownIssues.add("Network connectivity issues detected. Try switching between WiFi and mobile data.")
            }
            
            if (errorStats.errorsByType.getOrDefault("PARSING_FAILURE", 0) > 10) {
                knownIssues.add("Text parsing issues detected. Try using more specific language with clear dates and times.")
            }
            
            if (diagnosticReport.systemHealth.memoryUsage > 0.9) {
                knownIssues.add("Low memory detected. Try closing other apps to improve performance.")
            }
            
            if (diagnosticReport.deviceInfo.apiLevel < 24) {
                knownIssues.add("Older Android version detected. Some features may have limited functionality.")
            }
            
        } catch (e: Exception) {
            Log.w(TAG, "Failed to check for known issues", e)
        }
        
        return@withContext knownIssues
    }
    
    /**
     * Generates a quick health check report
     */
    suspend fun generateQuickHealthCheck(): Map<String, String> = withContext(Dispatchers.IO) {
        try {
            val diagnosticReport = errorLoggingManager.getDiagnosticReport()
            
            mapOf(
                "Overall Status" to determineOverallStatus(diagnosticReport),
                "Error Rate" to formatErrorRate(diagnosticReport.errorStatistics),
                "Network Status" to formatNetworkStatus(diagnosticReport.networkInfo),
                "Memory Status" to formatMemoryStatus(diagnosticReport.systemHealth),
                "Last Error" to formatLastError(diagnosticReport.recentErrors),
                "Suggestions Available" to "${errorLoggingManager.getImprovementSuggestions().size} tips"
            )
        } catch (e: Exception) {
            Log.e(TAG, "Failed to generate quick health check", e)
            mapOf("Status" to "Unable to determine", "Error" to (e.message ?: "Unknown error"))
        }
    }
    
    // Private helper methods
    
    private fun findErrorByCode(
        diagnosticReport: ErrorLoggingManager.DiagnosticReport,
        errorCode: String
    ): ErrorLoggingManager.ErrorLogEntry? {
        return diagnosticReport.recentErrors.find { it.errorCode == errorCode }
    }
    
    private fun generateUserFriendlyMessage(errorEntry: ErrorLoggingManager.ErrorLogEntry): String {
        return when (errorEntry.errorType) {
            "NETWORK_ERROR" -> "Unable to connect to the service. Please check your internet connection."
            "API_TIMEOUT" -> "The service is taking longer than usual to respond. Please try again."
            "PARSING_FAILURE" -> "We couldn't understand the text you provided. Try being more specific about dates and times."
            "LOW_CONFIDENCE" -> "We extracted some information but aren't very confident about it. Please review before creating the event."
            "CALENDAR_LAUNCH_FAILURE" -> "Unable to open your calendar app. Please check if you have a calendar app installed."
            "VALIDATION_ERROR" -> "The event information appears to be incomplete or invalid."
            "CRITICAL_ERROR" -> "A serious error occurred. Please contact support with the error code."
            else -> "An unexpected error occurred. Please try again or contact support if the problem persists."
        }
    }
    
    private fun generateTechnicalSummary(errorEntry: ErrorLoggingManager.ErrorLogEntry): String {
        return buildString {
            appendLine("Error Type: ${errorEntry.errorType}")
            appendLine("Severity: ${errorEntry.severity}")
            appendLine("Processing Time: ${errorEntry.context.processingTimeMs}ms")
            appendLine("Retry Count: ${errorEntry.context.retryCount}")
            errorEntry.context.confidenceScore?.let {
                appendLine("Confidence Score: $it")
            }
            appendLine("Network Connected: ${errorEntry.networkInfo.isConnected}")
            appendLine("Connection Type: ${errorEntry.networkInfo.connectionType}")
        }
    }
    
    private fun generateSuggestedActions(errorEntry: ErrorLoggingManager.ErrorLogEntry): List<String> {
        return when (errorEntry.errorType) {
            "NETWORK_ERROR" -> listOf(
                "Check your internet connection",
                "Try switching between WiFi and mobile data",
                "Retry the operation",
                "Use offline mode if available"
            )
            "API_TIMEOUT" -> listOf(
                "Wait a moment and try again",
                "Check your internet speed",
                "Try with shorter text",
                "Contact support if problem persists"
            )
            "PARSING_FAILURE" -> listOf(
                "Try using more specific language",
                "Include clear dates and times (e.g., 'March 15 at 2:00 PM')",
                "Break complex events into simpler descriptions",
                "Use the manual event creation option"
            )
            "LOW_CONFIDENCE" -> listOf(
                "Review the extracted information carefully",
                "Edit any incorrect details in your calendar app",
                "Try rephrasing with clearer details",
                "Proceed if the information looks correct"
            )
            "CALENDAR_LAUNCH_FAILURE" -> listOf(
                "Install a calendar app if you don't have one",
                "Check calendar app permissions",
                "Try copying event details to clipboard instead",
                "Restart your device if the problem persists"
            )
            else -> listOf(
                "Try the operation again",
                "Restart the app",
                "Contact support with the error code"
            )
        }
    }
    
    private fun generateSystemInfo(
        deviceInfo: ErrorLoggingManager.DeviceInfo,
        networkInfo: ErrorLoggingManager.NetworkInfo
    ): String {
        return buildString {
            appendLine("Device: ${deviceInfo.manufacturer} ${deviceInfo.deviceModel}")
            appendLine("Android: ${deviceInfo.androidVersion} (API ${deviceInfo.apiLevel})")
            appendLine("App Version: ${deviceInfo.appVersion}")
            appendLine("Network: ${networkInfo.connectionType} (Connected: ${networkInfo.isConnected})")
            appendLine("Memory: ${deviceInfo.availableMemoryMb}MB available")
        }
    }
    
    private fun canRetryError(errorEntry: ErrorLoggingManager.ErrorLogEntry): Boolean {
        return when (errorEntry.errorType) {
            "NETWORK_ERROR", "API_TIMEOUT", "PARSING_FAILURE" -> true
            "CRITICAL_ERROR", "VALIDATION_ERROR" -> false
            else -> errorEntry.context.retryCount < 3
        }
    }
    
    private fun needsSupportContact(errorEntry: ErrorLoggingManager.ErrorLogEntry): Boolean {
        return when (errorEntry.errorType) {
            "CRITICAL_ERROR" -> true
            "CALENDAR_LAUNCH_FAILURE" -> errorEntry.context.retryCount > 2
            else -> errorEntry.context.retryCount > 5
        }
    }
    
    private fun generateDiagnosticSummary(
        diagnosticReport: ErrorLoggingManager.DiagnosticReport
    ): DiagnosticSummary {
        val errorStats = diagnosticReport.errorStatistics
        return DiagnosticSummary(
            totalErrors = errorStats.totalErrors,
            criticalErrors = errorStats.errorsBySeverity.getOrDefault("CRITICAL", 0),
            mostCommonErrorType = errorStats.errorsByType.maxByOrNull { entry -> entry.value }?.key ?: "None",
            successRate = errorStats.successRate,
            systemStability = determineSystemStability(diagnosticReport)
        )
    }
    
    private fun generateErrorAnalysis(
        diagnosticReport: ErrorLoggingManager.DiagnosticReport
    ): ErrorAnalysis {
        val patterns = diagnosticReport.failurePatterns.map { pattern ->
            ErrorPattern(
                pattern = pattern.textPattern,
                frequency = pattern.occurrences,
                impact = determinePatternImpact(pattern),
                suggestion = pattern.suggestedImprovement ?: "No specific suggestion available"
            )
        }
        
        return ErrorAnalysis(
            errorPatterns = patterns,
            timeDistribution = calculateTimeDistribution(diagnosticReport.recentErrors),
            networkRelatedErrors = diagnosticReport.errorStatistics.errorsByType.getOrDefault("NETWORK_ERROR", 0),
            parsingRelatedErrors = diagnosticReport.errorStatistics.errorsByType.getOrDefault("PARSING_FAILURE", 0),
            userCorrectionRate = 0.0 // Would be calculated from user correction data
        )
    }
    
    private fun generateSystemHealthReport(
        diagnosticReport: ErrorLoggingManager.DiagnosticReport
    ): SystemHealthReport {
        return SystemHealthReport(
            memoryStatus = formatMemoryStatus(diagnosticReport.systemHealth),
            storageStatus = formatStorageStatus(diagnosticReport.deviceInfo),
            networkStatus = formatNetworkStatus(diagnosticReport.networkInfo),
            appVersion = diagnosticReport.deviceInfo.appVersion,
            deviceCompatibility = determineDeviceCompatibility(diagnosticReport.deviceInfo)
        )
    }
    
    private fun generateImprovementSuggestions(
        diagnosticReport: ErrorLoggingManager.DiagnosticReport
    ): List<String> {
        val suggestions = mutableListOf<String>()
        
        // Analyze patterns and generate suggestions
        if (diagnosticReport.errorStatistics.errorsByType.getOrDefault("PARSING_FAILURE", 0) > 5) {
            suggestions.add("Consider using more specific language when describing events")
        }
        
        if (diagnosticReport.errorStatistics.errorsByType.getOrDefault("NETWORK_ERROR", 0) > 3) {
            suggestions.add("Check your internet connection stability")
        }
        
        if (diagnosticReport.systemHealth.memoryUsage > 0.8) {
            suggestions.add("Close other apps to free up memory")
        }
        
        return suggestions
    }
    
    private fun generateSupportInformation(reportId: String): SupportInformation {
        return SupportInformation(
            contactEmail = SUPPORT_EMAIL,
            reportId = reportId,
            debugInstructions = listOf(
                "Include the report ID when contacting support",
                "Describe what you were trying to do when the error occurred",
                "Mention if the error happens consistently or occasionally",
                "Include any error codes you've received"
            ),
            knownIssues = listOf(
                "Network timeouts may occur during peak usage",
                "Some older Android versions may have limited functionality",
                "Calendar app compatibility varies by device manufacturer"
            )
        )
    }
    
    private fun createFullDiagnosticExport(report: ComprehensiveDiagnosticReport): JSONObject {
        return JSONObject().apply {
            put("report_id", report.reportId)
            put("generated_at", report.generatedAt)
            put("summary", JSONObject().apply {
                put("total_errors", report.summary.totalErrors)
                put("critical_errors", report.summary.criticalErrors)
                put("most_common_error", report.summary.mostCommonErrorType)
                put("success_rate", report.summary.successRate)
                put("system_stability", report.summary.systemStability)
            })
            put("error_analysis", JSONObject().apply {
                put("network_errors", report.errorAnalysis.networkRelatedErrors)
                put("parsing_errors", report.errorAnalysis.parsingRelatedErrors)
                put("user_correction_rate", report.errorAnalysis.userCorrectionRate)
            })
            put("system_health", JSONObject().apply {
                put("memory_status", report.systemHealth.memoryStatus)
                put("storage_status", report.systemHealth.storageStatus)
                put("network_status", report.systemHealth.networkStatus)
                put("app_version", report.systemHealth.appVersion)
            })
            put("improvement_suggestions", report.improvementSuggestions)
        }
    }
    
    private fun createAnonymizedDiagnosticExport(report: ComprehensiveDiagnosticReport): JSONObject {
        return JSONObject().apply {
            put("report_type", "anonymized")
            put("generated_at", report.generatedAt)
            put("error_summary", JSONObject().apply {
                put("total_errors", report.summary.totalErrors)
                put("error_types", report.errorAnalysis.networkRelatedErrors + report.errorAnalysis.parsingRelatedErrors)
                put("system_stability", report.summary.systemStability)
            })
            put("suggestions", report.improvementSuggestions)
            put("privacy_note", "This report contains anonymized data only")
        }
    }
    
    private fun createEmptyDiagnosticReport(): ComprehensiveDiagnosticReport {
        return ComprehensiveDiagnosticReport(
            reportId = generateReportId(),
            generatedAt = dateFormatter.format(Date()),
            summary = DiagnosticSummary(0, 0, "None", 1.0, "Unknown"),
            errorAnalysis = ErrorAnalysis(emptyList(), emptyMap(), 0, 0, 0.0),
            systemHealth = SystemHealthReport("Unknown", "Unknown", "Unknown", "Unknown", "Unknown"),
            improvementSuggestions = emptyList(),
            supportInformation = generateSupportInformation(generateReportId())
        )
    }
    
    private fun generateReportId(): String {
        return "RPT_${System.currentTimeMillis()}_${(1000..9999).random()}"
    }
    
    private fun determineSystemStability(diagnosticReport: ErrorLoggingManager.DiagnosticReport): String {
        val errorRate = if (diagnosticReport.errorStatistics.totalErrors > 0) {
            1.0 - diagnosticReport.errorStatistics.successRate
        } else {
            0.0
        }
        
        return when {
            errorRate < 0.1 -> "Excellent"
            errorRate < 0.3 -> "Good"
            errorRate < 0.5 -> "Fair"
            else -> "Poor"
        }
    }
    
    private fun determinePatternImpact(pattern: ErrorLoggingManager.FailurePattern): String {
        return when {
            pattern.occurrences > 10 -> "High"
            pattern.occurrences > 5 -> "Medium"
            else -> "Low"
        }
    }
    
    private fun calculateTimeDistribution(errors: List<ErrorLoggingManager.ErrorLogEntry>): Map<String, Int> {
        val distribution = mutableMapOf<String, Int>()
        val calendar = Calendar.getInstance()
        
        errors.forEach { error ->
            calendar.timeInMillis = error.timestamp
            val hour = calendar.get(Calendar.HOUR_OF_DAY)
            val timeSlot = when {
                hour < 6 -> "Night (0-6)"
                hour < 12 -> "Morning (6-12)"
                hour < 18 -> "Afternoon (12-18)"
                else -> "Evening (18-24)"
            }
            distribution[timeSlot] = distribution.getOrDefault(timeSlot, 0) + 1
        }
        
        return distribution
    }
    
    private fun determineOverallStatus(diagnosticReport: ErrorLoggingManager.DiagnosticReport): String {
        val criticalErrors = diagnosticReport.errorStatistics.errorsBySeverity.getOrDefault("CRITICAL", 0)
        val totalErrors = diagnosticReport.errorStatistics.totalErrors
        
        return when {
            criticalErrors > 0 -> "Critical Issues Detected"
            totalErrors > 20 -> "Multiple Issues"
            totalErrors > 5 -> "Some Issues"
            totalErrors > 0 -> "Minor Issues"
            else -> "Healthy"
        }
    }
    
    private fun formatErrorRate(errorStats: ErrorLoggingManager.ErrorStatistics): String {
        val errorRate = 1.0 - errorStats.successRate
        return "${(errorRate * 100).toInt()}% (${errorStats.totalErrors} errors)"
    }
    
    private fun formatNetworkStatus(networkInfo: ErrorLoggingManager.NetworkInfo): String {
        return if (networkInfo.isConnected) {
            "${networkInfo.connectionType} Connected"
        } else {
            "Disconnected"
        }
    }
    
    private fun formatMemoryStatus(systemHealth: ErrorLoggingManager.SystemHealth): String {
        return when {
            systemHealth.memoryUsage > 0.9 -> "Critical (${(systemHealth.memoryUsage * 100).toInt()}%)"
            systemHealth.memoryUsage > 0.7 -> "High (${(systemHealth.memoryUsage * 100).toInt()}%)"
            systemHealth.memoryUsage > 0.5 -> "Moderate (${(systemHealth.memoryUsage * 100).toInt()}%)"
            else -> "Good (${(systemHealth.memoryUsage * 100).toInt()}%)"
        }
    }
    
    private fun formatStorageStatus(deviceInfo: ErrorLoggingManager.DeviceInfo): String {
        val usagePercent = ((deviceInfo.totalStorageMb - deviceInfo.availableMemoryMb).toDouble() / deviceInfo.totalStorageMb * 100).toInt()
        return "$usagePercent% used"
    }
    
    private fun formatLastError(recentErrors: List<ErrorLoggingManager.ErrorLogEntry>): String {
        return if (recentErrors.isNotEmpty()) {
            val lastError = recentErrors.maxByOrNull { it.timestamp }
            val timeDiff = System.currentTimeMillis() - (lastError?.timestamp ?: 0)
            val minutes = timeDiff / (60 * 1000)
            when {
                minutes < 1 -> "Just now"
                minutes < 60 -> "${minutes}m ago"
                minutes < 1440 -> "${minutes / 60}h ago"
                else -> "${minutes / 1440}d ago"
            }
        } else {
            "None"
        }
    }
    
    private fun determineDeviceCompatibility(deviceInfo: ErrorLoggingManager.DeviceInfo): String {
        return when {
            deviceInfo.apiLevel >= 29 -> "Fully Compatible"
            deviceInfo.apiLevel >= 24 -> "Compatible"
            deviceInfo.apiLevel >= 21 -> "Limited Compatibility"
            else -> "Minimal Compatibility"
        }
    }
    
    private fun getDefaultImprovementSuggestions(): List<String> {
        return listOf(
            "💡 Try using specific dates and times (e.g., 'March 15 at 2:00 PM')",
            "🎯 Include event details like location and duration",
            "🌐 Check your internet connection for better parsing results",
            "📱 Keep your app updated for the latest improvements",
            "⚡ Use shorter, clearer descriptions for better accuracy"
        )
    }
}