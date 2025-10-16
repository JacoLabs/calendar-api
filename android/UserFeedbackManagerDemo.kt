package com.jacolabs.calendar

import android.content.Context
import android.util.Log
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import kotlinx.coroutines.launch

/**
 * Demo activity showcasing UserFeedbackManager integration with error handling scenarios.
 * This demonstrates how the UserFeedbackManager works with ErrorHandlingManager and ConfidenceValidator.
 */
@Composable
fun UserFeedbackManagerDemo() {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    
    // Initialize managers
    val userFeedbackManager = remember { UserFeedbackManager(context) }
    val confidenceValidator = remember { ConfidenceValidator(context) }
    val errorHandlingManager = remember { ErrorHandlingManager(context) }
    
    var demoStatus by remember { mutableStateOf("Ready to test user feedback scenarios") }
    var isLoading by remember { mutableStateOf(false) }
    
    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(16.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        
        // Header
        Card(
            modifier = Modifier.fillMaxWidth(),
            elevation = CardDefaults.cardElevation(defaultElevation = 4.dp)
        ) {
            Column(
                modifier = Modifier.padding(16.dp),
                horizontalAlignment = Alignment.CenterHorizontally
            ) {
                Icon(
                    imageVector = Icons.Default.Feedback,
                    contentDescription = "User Feedback Demo",
                    modifier = Modifier.size(48.dp),
                    tint = MaterialTheme.colorScheme.primary
                )
                
                Spacer(modifier = Modifier.height(8.dp))
                
                Text(
                    text = "UserFeedbackManager Demo",
                    style = MaterialTheme.typography.headlineMedium,
                    fontWeight = FontWeight.Bold
                )
                
                Text(
                    text = "Test various user feedback scenarios",
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }
        }
        
        // Status display
        Card(
            modifier = Modifier.fillMaxWidth(),
            colors = CardDefaults.cardColors(
                containerColor = MaterialTheme.colorScheme.surfaceVariant
            )
        ) {
            Text(
                text = "Status: $demoStatus",
                modifier = Modifier.padding(16.dp),
                style = MaterialTheme.typography.bodyMedium
            )
        }
        
        // Demo buttons
        Text(
            text = "Confidence Warning Scenarios",
            style = MaterialTheme.typography.titleMedium,
            fontWeight = FontWeight.Bold
        )
        
        // Low confidence scenario
        Button(
            onClick = {
                scope.launch {
                    isLoading = true
                    demoStatus = "Testing low confidence warning..."
                    
                    val lowConfidenceResult = createLowConfidenceResult()
                    val assessment = confidenceValidator.assessConfidence(lowConfidenceResult, "meeting tomorrow")
                    
                    val userDecision = userFeedbackManager.showConfidenceWarning(assessment)
                    
                    demoStatus = if (userDecision) {
                        "User chose to proceed with low confidence event"
                    } else {
                        "User cancelled low confidence event creation"
                    }
                    isLoading = false
                }
            },
            modifier = Modifier.fillMaxWidth(),
            enabled = !isLoading
        ) {
            Icon(Icons.Default.Warning, contentDescription = null)
            Spacer(modifier = Modifier.width(8.dp))
            Text("Test Low Confidence Warning")
        }
        
        // Medium confidence scenario
        Button(
            onClick = {
                scope.launch {
                    isLoading = true
                    demoStatus = "Testing medium confidence warning..."
                    
                    val mediumConfidenceResult = createMediumConfidenceResult()
                    val assessment = confidenceValidator.assessConfidence(mediumConfidenceResult, "team meeting next Monday at 2pm")
                    
                    val userDecision = userFeedbackManager.showConfidenceWarning(assessment)
                    
                    demoStatus = if (userDecision) {
                        "User chose to proceed with medium confidence event"
                    } else {
                        "User cancelled medium confidence event creation"
                    }
                    isLoading = false
                }
            },
            modifier = Modifier.fillMaxWidth(),
            enabled = !isLoading
        ) {
            Icon(Icons.Default.Info, contentDescription = null)
            Spacer(modifier = Modifier.width(8.dp))
            Text("Test Medium Confidence Warning")
        }
        
        Divider()
        
        Text(
            text = "Network Error Scenarios",
            style = MaterialTheme.typography.titleMedium,
            fontWeight = FontWeight.Bold
        )
        
        // Network error scenario
        Button(
            onClick = {
                scope.launch {
                    isLoading = true
                    demoStatus = "Testing network error dialog..."
                    
                    userFeedbackManager.showNetworkErrorDialog(
                        errorType = ErrorHandlingManager.ErrorType.NETWORK_ERROR,
                        retryAction = {
                            demoStatus = "User chose to retry network request"
                            isLoading = false
                        },
                        offlineAction = {
                            demoStatus = "User chose to create event offline"
                            isLoading = false
                        }
                    )
                }
            },
            modifier = Modifier.fillMaxWidth(),
            enabled = !isLoading
        ) {
            Icon(Icons.Default.CloudOff, contentDescription = null)
            Spacer(modifier = Modifier.width(8.dp))
            Text("Test Network Error Dialog")
        }
        
        // API timeout scenario
        Button(
            onClick = {
                scope.launch {
                    isLoading = true
                    demoStatus = "Testing API timeout dialog..."
                    
                    userFeedbackManager.showNetworkErrorDialog(
                        errorType = ErrorHandlingManager.ErrorType.API_TIMEOUT,
                        retryAction = {
                            demoStatus = "User chose to retry after timeout"
                            isLoading = false
                        },
                        offlineAction = {
                            demoStatus = "User chose offline mode after timeout"
                            isLoading = false
                        }
                    )
                }
            },
            modifier = Modifier.fillMaxWidth(),
            enabled = !isLoading
        ) {
            Icon(Icons.Default.Timer, contentDescription = null)
            Spacer(modifier = Modifier.width(8.dp))
            Text("Test API Timeout Dialog")
        }
        
        Divider()
        
        Text(
            text = "Calendar Fallback Scenarios",
            style = MaterialTheme.typography.titleMedium,
            fontWeight = FontWeight.Bold
        )
        
        // Calendar not found scenario
        Button(
            onClick = {
                scope.launch {
                    isLoading = true
                    demoStatus = "Testing calendar not found dialog..."
                    
                    val sampleResult = createSampleParseResult()
                    val alternatives = listOf("Google Calendar", "Outlook", "Samsung Calendar")
                    
                    userFeedbackManager.showCalendarNotFoundDialog(sampleResult, alternatives)
                    
                    demoStatus = "Showed calendar not found dialog with alternatives"
                    isLoading = false
                }
            },
            modifier = Modifier.fillMaxWidth(),
            enabled = !isLoading
        ) {
            Icon(Icons.Default.CalendarMonth, contentDescription = null)
            Spacer(modifier = Modifier.width(8.dp))
            Text("Test Calendar Not Found Dialog")
        }
        
        Divider()
        
        Text(
            text = "Toast Messages",
            style = MaterialTheme.typography.titleMedium,
            fontWeight = FontWeight.Bold
        )
        
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            // Success message
            Button(
                onClick = {
                    userFeedbackManager.showSuccessMessage("Event created successfully!")
                    demoStatus = "Showed success toast message"
                },
                modifier = Modifier.weight(1f),
                enabled = !isLoading
            ) {
                Icon(Icons.Default.Check, contentDescription = null)
                Spacer(modifier = Modifier.width(4.dp))
                Text("Success")
            }
            
            // Error message
            Button(
                onClick = {
                    userFeedbackManager.showErrorMessage("Failed to create event")
                    demoStatus = "Showed error toast message"
                },
                modifier = Modifier.weight(1f),
                enabled = !isLoading,
                colors = ButtonDefaults.buttonColors(
                    containerColor = MaterialTheme.colorScheme.error
                )
            ) {
                Icon(Icons.Default.Error, contentDescription = null)
                Spacer(modifier = Modifier.width(4.dp))
                Text("Error")
            }
        }
        
        Divider()
        
        Text(
            text = "Integration Test",
            style = MaterialTheme.typography.titleMedium,
            fontWeight = FontWeight.Bold
        )
        
        // Full integration test
        Button(
            onClick = {
                scope.launch {
                    isLoading = true
                    demoStatus = "Running full integration test..."
                    
                    // Simulate a complete error handling flow
                    val errorContext = ErrorHandlingManager.ErrorContext(
                        errorType = ErrorHandlingManager.ErrorType.LOW_CONFIDENCE,
                        originalText = "meeting tomorrow",
                        apiResponse = createLowConfidenceResult(),
                        confidenceScore = 0.25
                    )
                    
                    val errorResult = errorHandlingManager.handleError(errorContext)
                    
                    if (errorResult.actionRequired == ErrorHandlingManager.UserAction.CONFIRM_LOW_CONFIDENCE_RESULT) {
                        val assessment = confidenceValidator.assessConfidence(
                            errorContext.apiResponse!!,
                            errorContext.originalText
                        )
                        
                        val userDecision = userFeedbackManager.showConfidenceWarning(assessment)
                        
                        if (userDecision) {
                            userFeedbackManager.showSuccessMessage("Event created with user confirmation")
                            demoStatus = "Integration test completed - event created after user confirmation"
                        } else {
                            demoStatus = "Integration test completed - user cancelled event creation"
                        }
                    } else {
                        demoStatus = "Integration test completed - ${errorResult.recoveryStrategy}"
                    }
                    
                    isLoading = false
                }
            },
            modifier = Modifier.fillMaxWidth(),
            enabled = !isLoading
        ) {
            Icon(Icons.Default.PlayArrow, contentDescription = null)
            Spacer(modifier = Modifier.width(8.dp))
            Text("Run Full Integration Test")
        }
        
        if (isLoading) {
            CircularProgressIndicator(
                modifier = Modifier.padding(16.dp)
            )
        }
    }
    
    // Render feedback dialogs
    userFeedbackManager.FeedbackDialogRenderer()
}

/**
 * Creates a sample low confidence parse result for testing
 */
private fun createLowConfidenceResult(): ParseResult {
    return ParseResult(
        title = "meeting",
        startDateTime = null,
        endDateTime = null,
        location = null,
        description = "meeting tomorrow",
        confidenceScore = 0.25,
        allDay = false,
        timezone = "UTC",
        fieldResults = mapOf(
            "title" to FieldResult(
                value = "meeting",
                confidence = 0.3,
                source = "text_extraction"
            ),
            "start_datetime" to FieldResult(
                value = null,
                confidence = 0.0,
                source = "none"
            )
        ),
        fallbackApplied = false,
        originalText = "meeting tomorrow"
    )
}

/**
 * Creates a sample medium confidence parse result for testing
 */
private fun createMediumConfidenceResult(): ParseResult {
    return ParseResult(
        title = "team meeting",
        startDateTime = "2024-12-16T14:00:00",
        endDateTime = "2024-12-16T15:00:00",
        location = null,
        description = "team meeting next Monday at 2pm",
        confidenceScore = 0.55,
        allDay = false,
        timezone = "UTC",
        fieldResults = mapOf(
            "title" to FieldResult(
                value = "team meeting",
                confidence = 0.7,
                source = "text_extraction"
            ),
            "start_datetime" to FieldResult(
                value = "2024-12-16T14:00:00",
                confidence = 0.6,
                source = "date_parser"
            ),
            "end_datetime" to FieldResult(
                value = "2024-12-16T15:00:00",
                confidence = 0.4,
                source = "duration_inference"
            )
        ),
        fallbackApplied = false,
        originalText = "team meeting next Monday at 2pm"
    )
}

/**
 * Creates a sample parse result for testing calendar fallbacks
 */
private fun createSampleParseResult(): ParseResult {
    return ParseResult(
        title = "Project Review Meeting",
        startDateTime = "2024-12-15T10:00:00",
        endDateTime = "2024-12-15T11:00:00",
        location = "Conference Room A",
        description = "Quarterly project review with the team",
        confidenceScore = 0.85,
        allDay = false,
        timezone = "UTC",
        fieldResults = mapOf(
            "title" to FieldResult(
                value = "Project Review Meeting",
                confidence = 0.9,
                source = "text_extraction"
            ),
            "start_datetime" to FieldResult(
                value = "2024-12-15T10:00:00",
                confidence = 0.8,
                source = "date_parser"
            ),
            "location" to FieldResult(
                value = "Conference Room A",
                confidence = 0.7,
                source = "location_extractor"
            )
        ),
        fallbackApplied = false,
        originalText = "Project review meeting tomorrow at 10am in Conference Room A"
    )
}