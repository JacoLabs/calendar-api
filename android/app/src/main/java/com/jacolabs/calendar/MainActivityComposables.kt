package com.jacolabs.calendar

import androidx.compose.animation.*
import androidx.compose.animation.core.*
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import java.text.SimpleDateFormat
import java.util.*

/**
 * Confidence Warning Card - shows when confidence is low
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ConfidenceWarningCard(
    assessment: ConfidenceValidator.ConfidenceAssessment,
    onProceed: () -> Unit,
    onImprove: () -> Unit,
    onDismiss: () -> Unit
) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(
            containerColor = when (assessment.warningSeverity) {
                ConfidenceValidator.WarningSeverity.WARNING -> MaterialTheme.colorScheme.secondaryContainer
                ConfidenceValidator.WarningSeverity.ERROR -> MaterialTheme.colorScheme.errorContainer
                else -> MaterialTheme.colorScheme.surfaceVariant
            }
        )
    ) {
        Column(
            modifier = Modifier.padding(16.dp)
        ) {
            Row(
                verticalAlignment = Alignment.CenterVertically
            ) {
                Icon(
                    imageVector = Icons.Default.Info,
                    contentDescription = null,
                    tint = when (assessment.warningSeverity) {
                        ConfidenceValidator.WarningSeverity.WARNING -> MaterialTheme.colorScheme.onSecondaryContainer
                        ConfidenceValidator.WarningSeverity.ERROR -> MaterialTheme.colorScheme.onErrorContainer
                        else -> MaterialTheme.colorScheme.onSurfaceVariant
                    }
                )
                Spacer(modifier = Modifier.width(8.dp))
                Text(
                    text = "Confidence Warning",
                    style = MaterialTheme.typography.titleMedium,
                    color = when (assessment.warningSeverity) {
                        ConfidenceValidator.WarningSeverity.WARNING -> MaterialTheme.colorScheme.onSecondaryContainer
                        ConfidenceValidator.WarningSeverity.ERROR -> MaterialTheme.colorScheme.onErrorContainer
                        else -> MaterialTheme.colorScheme.onSurfaceVariant
                    }
                )
            }
            
            Spacer(modifier = Modifier.height(8.dp))
            
            assessment.warningMessage?.let { message ->
                Text(
                    text = message,
                    style = MaterialTheme.typography.bodyMedium,
                    color = when (assessment.warningSeverity) {
                        ConfidenceValidator.WarningSeverity.WARNING -> MaterialTheme.colorScheme.onSecondaryContainer
                        ConfidenceValidator.WarningSeverity.ERROR -> MaterialTheme.colorScheme.onErrorContainer
                        else -> MaterialTheme.colorScheme.onSurfaceVariant
                    }
                )
            }
            
            // Show improvement suggestions
            if (assessment.improvementSuggestions.isNotEmpty()) {
                Spacer(modifier = Modifier.height(8.dp))
                Text(
                    text = "💡 Suggestions:",
                    style = MaterialTheme.typography.labelMedium,
                    color = when (assessment.warningSeverity) {
                        ConfidenceValidator.WarningSeverity.WARNING -> MaterialTheme.colorScheme.onSecondaryContainer
                        ConfidenceValidator.WarningSeverity.ERROR -> MaterialTheme.colorScheme.onErrorContainer
                        else -> MaterialTheme.colorScheme.onSurfaceVariant
                    }
                )
                assessment.improvementSuggestions.take(3).forEach { suggestion ->
                    Text(
                        text = "• $suggestion",
                        style = MaterialTheme.typography.bodySmall,
                        color = when (assessment.warningSeverity) {
                            ConfidenceValidator.WarningSeverity.WARNING -> MaterialTheme.colorScheme.onSecondaryContainer
                            ConfidenceValidator.WarningSeverity.ERROR -> MaterialTheme.colorScheme.onErrorContainer
                            else -> MaterialTheme.colorScheme.onSurfaceVariant
                        }
                    )
                }
            }
            
            Spacer(modifier = Modifier.height(16.dp))
            
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                if (assessment.shouldProceed) {
                    Button(
                        onClick = onProceed,
                        modifier = Modifier.weight(1f)
                    ) {
                        Text("Proceed Anyway")
                    }
                }
                
                OutlinedButton(
                    onClick = onImprove,
                    modifier = Modifier.weight(1f)
                ) {
                    Text("Improve Text")
                }
                
                TextButton(
                    onClick = onDismiss
                ) {
                    Text("Dismiss")
                }
            }
        }
    }
}

/**
 * Fallback Confirmation Card - shows when fallback event is created
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun FallbackConfirmationCard(
    fallbackResult: ParseResult,
    originalText: String,
    onAccept: () -> Unit,
    onRetry: () -> Unit,
    onDismiss: () -> Unit
) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.tertiaryContainer
        )
    ) {
        Column(
            modifier = Modifier.padding(16.dp)
        ) {
            Row(
                verticalAlignment = Alignment.CenterVertically
            ) {
                Icon(
                    imageVector = Icons.Default.Event,
                    contentDescription = null,
                    tint = MaterialTheme.colorScheme.onTertiaryContainer
                )
                Spacer(modifier = Modifier.width(8.dp))
                Text(
                    text = "Fallback Event Created",
                    style = MaterialTheme.typography.titleMedium,
                    color = MaterialTheme.colorScheme.onTertiaryContainer
                )
            }
            
            Spacer(modifier = Modifier.height(8.dp))
            
            Text(
                text = "We couldn't parse all details reliably, so we created a basic event with available information:",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onTertiaryContainer
            )
            
            Spacer(modifier = Modifier.height(12.dp))
            
            // Show fallback event details
            fallbackResult.title?.let { title ->
                Text(
                    text = "Title: $title",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onTertiaryContainer
                )
            }
            
            fallbackResult.startDateTime?.let { startDateTime ->
                val formattedDate = formatDateTime(startDateTime)
                Text(
                    text = "Time: $formattedDate",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onTertiaryContainer
                )
            }
            
            fallbackResult.fallbackReason?.let { reason ->
                Spacer(modifier = Modifier.height(4.dp))
                Text(
                    text = "ℹ️ $reason",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onTertiaryContainer
                )
            }
            
            Spacer(modifier = Modifier.height(16.dp))
            
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                Button(
                    onClick = onAccept,
                    modifier = Modifier.weight(1f)
                ) {
                    Text("Accept Event")
                }
                
                OutlinedButton(
                    onClick = onRetry,
                    modifier = Modifier.weight(1f)
                ) {
                    Text("Try Again")
                }
                
                TextButton(
                    onClick = onDismiss
                ) {
                    Text("Cancel")
                }
            }
        }
    }
}

/**
 * Enhanced Result Card with confidence indicators and visual feedback
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun EnhancedResultCard(
    result: ParseResult,
    confidenceAssessment: ConfidenceValidator.ConfidenceAssessment?,
    onCreateEvent: () -> Unit,
    onRetry: () -> Unit
) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.surfaceVariant
        )
    ) {
        Column(
            modifier = Modifier.padding(16.dp)
        ) {
            // Header with overall confidence
            Row(
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.SpaceBetween,
                modifier = Modifier.fillMaxWidth()
            ) {
                Text(
                    text = "Parsed Event Details",
                    style = MaterialTheme.typography.titleMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
                
                // Enhanced confidence indicator with visual feedback
                OverallConfidenceIndicator(
                    confidence = result.confidenceScore,
                    assessment = confidenceAssessment
                )
            }
            
            Spacer(modifier = Modifier.height(12.dp))
            
            // Field-level confidence display with enhanced indicators
            confidenceAssessment?.fieldConfidences?.let { fieldConfidences ->
                fieldConfidences.forEach { (fieldName, fieldInfo) ->
                    if (fieldInfo.hasValue) {
                        FieldConfidenceRow(
                            fieldName = fieldName,
                            fieldInfo = fieldInfo
                        )
                        Spacer(modifier = Modifier.height(6.dp))
                    }
                }
            } ?: run {
                // Fallback display with basic confidence indicators
                BasicFieldDisplay(result)
            }
            
            // Enhanced status indicators
            StatusIndicatorsSection(result, confidenceAssessment)
            
            Spacer(modifier = Modifier.height(16.dp))
            
            // Enhanced action buttons with state indicators
            EnhancedActionButtons(
                result = result,
                confidenceAssessment = confidenceAssessment,
                onCreateEvent = onCreateEvent,
                onRetry = onRetry
            )
        }
    }
}

/**
 * Overall confidence indicator with enhanced visual feedback
 */
@Composable
private fun OverallConfidenceIndicator(
    confidence: Double,
    assessment: ConfidenceValidator.ConfidenceAssessment?
) {
    val confidencePercentage = (confidence * 100).toInt()
    val (color, icon, label) = getConfidenceVisualInfo(confidence)
    
    Row(
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(4.dp)
    ) {
        // Confidence icon
        Icon(
            imageVector = icon,
            contentDescription = null,
            tint = color,
            modifier = Modifier.size(16.dp)
        )
        
        // Confidence badge with enhanced styling
        Surface(
            color = color.copy(alpha = 0.15f),
            shape = RoundedCornerShape(12.dp),
            modifier = Modifier.border(
                width = 1.dp,
                color = color.copy(alpha = 0.3f),
                shape = RoundedCornerShape(12.dp)
            )
        ) {
            Row(
                verticalAlignment = Alignment.CenterVertically,
                modifier = Modifier.padding(horizontal = 8.dp, vertical = 4.dp)
            ) {
                Text(
                    text = "$confidencePercentage%",
                    style = MaterialTheme.typography.labelMedium,
                    color = color,
                    fontWeight = FontWeight.SemiBold
                )
                
                Spacer(modifier = Modifier.width(4.dp))
                
                Text(
                    text = label,
                    style = MaterialTheme.typography.labelSmall,
                    color = color.copy(alpha = 0.8f)
                )
            }
        }
    }
}

/**
 * Field confidence row with enhanced visual indicators
 */
@Composable
private fun FieldConfidenceRow(
    fieldName: String,
    fieldInfo: ConfidenceValidator.FieldConfidenceInfo
) {
    val fieldConfidence = (fieldInfo.confidence * 100).toInt()
    val (color, icon, _) = getConfidenceVisualInfo(fieldInfo.confidence)
    
    Row(
        verticalAlignment = Alignment.CenterVertically,
        modifier = Modifier.fillMaxWidth()
    ) {
        // Field confidence indicator
        Icon(
            imageVector = icon,
            contentDescription = null,
            tint = color,
            modifier = Modifier.size(14.dp)
        )
        
        Spacer(modifier = Modifier.width(8.dp))
        
        // Field content
        Column(modifier = Modifier.weight(1f)) {
            Text(
                text = "${fieldName.replaceFirstChar { it.uppercase() }}: ${fieldInfo.value}",
                style = MaterialTheme.typography.bodyMedium
            )
            
            // Show field issues if any
            if (fieldInfo.issues.isNotEmpty()) {
                Text(
                    text = "⚠ ${fieldInfo.issues.first()}",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.tertiary
                )
            }
        }
        
        // Confidence percentage with visual indicator
        Surface(
            color = color.copy(alpha = 0.1f),
            shape = MaterialTheme.shapes.extraSmall
        ) {
            Text(
                text = "$fieldConfidence%",
                modifier = Modifier.padding(horizontal = 6.dp, vertical = 2.dp),
                style = MaterialTheme.typography.labelSmall,
                color = color,
                fontWeight = FontWeight.Medium
            )
        }
    }
}

/**
 * Basic field display for fallback scenarios
 */
@Composable
private fun BasicFieldDisplay(result: ParseResult) {
    result.title?.let { title ->
        BasicFieldRow("Title", title, result.confidenceScore)
    }
    
    result.startDateTime?.let { startDateTime ->
        val formattedDate = formatDateTime(startDateTime)
        BasicFieldRow("Start", formattedDate, result.confidenceScore)
    }
    
    result.endDateTime?.let { endDateTime ->
        val formattedDate = formatDateTime(endDateTime)
        BasicFieldRow("End", formattedDate, result.confidenceScore)
    }
    
    result.location?.let { location ->
        BasicFieldRow("Location", location, result.confidenceScore)
    }
}

/**
 * Basic field row with simple confidence indicator
 */
@Composable
private fun BasicFieldRow(fieldName: String, value: String, confidence: Double) {
    val (color, icon, _) = getConfidenceVisualInfo(confidence)
    
    Row(
        verticalAlignment = Alignment.CenterVertically,
        modifier = Modifier.fillMaxWidth()
    ) {
        Icon(
            imageVector = icon,
            contentDescription = null,
            tint = color,
            modifier = Modifier.size(14.dp)
        )
        
        Spacer(modifier = Modifier.width(8.dp))
        
        Text(
            text = "$fieldName: $value",
            style = MaterialTheme.typography.bodyMedium,
            modifier = Modifier.weight(1f)
        )
    }
    
    Spacer(modifier = Modifier.height(4.dp))
}

/**
 * Status indicators section for fallback info, warnings, etc.
 */
@Composable
private fun StatusIndicatorsSection(
    result: ParseResult,
    assessment: ConfidenceValidator.ConfidenceAssessment?
) {
    var hasStatusInfo = false
    
    // Fallback information
    result.fallbackReason?.let { reason ->
        hasStatusInfo = true
        StatusIndicatorCard(
            icon = Icons.Default.Info,
            message = reason,
            color = MaterialTheme.colorScheme.tertiary,
            backgroundColor = MaterialTheme.colorScheme.tertiaryContainer
        )
    }
    
    // Parsing warnings
    result.warnings?.let { warnings ->
        if (warnings.isNotEmpty()) {
            hasStatusInfo = true
            warnings.forEach { warning ->
                StatusIndicatorCard(
                    icon = Icons.Default.Warning,
                    message = warning,
                    color = MaterialTheme.colorScheme.tertiary,
                    backgroundColor = MaterialTheme.colorScheme.tertiaryContainer
                )
            }
        }
    }
    
    // Missing critical fields warning
    assessment?.missingCriticalFields?.let { missingFields ->
        if (missingFields.isNotEmpty()) {
            hasStatusInfo = true
            StatusIndicatorCard(
                icon = Icons.Default.Error,
                message = "Missing: ${missingFields.joinToString(", ")}",
                color = MaterialTheme.colorScheme.error,
                backgroundColor = MaterialTheme.colorScheme.errorContainer
            )
        }
    }
    
    if (hasStatusInfo) {
        Spacer(modifier = Modifier.height(8.dp))
    }
}

/**
 * Status indicator card for warnings, info, etc.
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun StatusIndicatorCard(
    icon: ImageVector,
    message: String,
    color: Color,
    backgroundColor: Color
) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(containerColor = backgroundColor),
        shape = RoundedCornerShape(8.dp)
    ) {
        Row(
            verticalAlignment = Alignment.CenterVertically,
            modifier = Modifier.padding(12.dp)
        ) {
            Icon(
                imageVector = icon,
                contentDescription = null,
                tint = color,
                modifier = Modifier.size(16.dp)
            )
            
            Spacer(modifier = Modifier.width(8.dp))
            
            Text(
                text = message,
                style = MaterialTheme.typography.bodySmall,
                color = color
            )
        }
    }
    
    Spacer(modifier = Modifier.height(4.dp))
}

/**
 * Enhanced action buttons with state indicators
 */
@Composable
private fun EnhancedActionButtons(
    result: ParseResult,
    confidenceAssessment: ConfidenceValidator.ConfidenceAssessment?,
    onCreateEvent: () -> Unit,
    onRetry: () -> Unit
) {
    val confidence = (result.confidenceScore * 100).toInt()
    val shouldShowRetry = confidence < 50 || 
                         confidenceAssessment?.recommendation == ConfidenceValidator.UserRecommendation.SUGGEST_IMPROVEMENTS
    
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.spacedBy(8.dp)
    ) {
        // Primary create event button with confidence-based styling
        Button(
            onClick = onCreateEvent,
            modifier = Modifier.weight(1f),
            colors = ButtonDefaults.buttonColors(
                containerColor = when {
                    confidence >= 70 -> MaterialTheme.colorScheme.primary
                    confidence >= 30 -> MaterialTheme.colorScheme.tertiary
                    else -> MaterialTheme.colorScheme.error
                }
            )
        ) {
            Icon(
                imageVector = Icons.Default.Event,
                contentDescription = null,
                modifier = Modifier.size(18.dp)
            )
            Spacer(modifier = Modifier.width(8.dp))
            Text(
                text = when {
                    confidence >= 70 -> "Create Event"
                    confidence >= 30 -> "Create Anyway"
                    else -> "Force Create"
                }
            )
        }
        
        // Retry/improve button for low confidence results
        if (shouldShowRetry) {
            OutlinedButton(
                onClick = onRetry,
                modifier = Modifier.weight(1f)
            ) {
                Icon(
                    imageVector = Icons.Default.Refresh,
                    contentDescription = null,
                    modifier = Modifier.size(18.dp)
                )
                Spacer(modifier = Modifier.width(8.dp))
                Text("Improve")
            }
        }
    }
}

/**
 * Progress indicator for retry operations
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun RetryProgressIndicator(
    isRetrying: Boolean,
    retryCount: Int,
    maxRetries: Int = 3
) {
    AnimatedVisibility(
        visible = isRetrying,
        enter = fadeIn() + slideInVertically(),
        exit = fadeOut() + slideOutVertically()
    ) {
        Card(
            modifier = Modifier.fillMaxWidth(),
            colors = CardDefaults.cardColors(
                containerColor = MaterialTheme.colorScheme.primaryContainer
            )
        ) {
            Row(
                verticalAlignment = Alignment.CenterVertically,
                modifier = Modifier.padding(16.dp)
            ) {
                CircularProgressIndicator(
                    modifier = Modifier.size(24.dp),
                    strokeWidth = 3.dp,
                    color = MaterialTheme.colorScheme.primary
                )
                
                Spacer(modifier = Modifier.width(12.dp))
                
                Column {
                    Text(
                        text = "Retrying request...",
                        style = MaterialTheme.typography.bodyMedium,
                        fontWeight = FontWeight.Medium
                    )
                    
                    Text(
                        text = "Attempt ${retryCount + 1} of $maxRetries",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onPrimaryContainer.copy(alpha = 0.7f)
                    )
                }
                
                Spacer(modifier = Modifier.weight(1f))
                
                // Retry progress indicator
                LinearProgressIndicator(
                    progress = (retryCount.toFloat() / maxRetries),
                    modifier = Modifier.width(60.dp),
                    color = MaterialTheme.colorScheme.primary,
                    trackColor = MaterialTheme.colorScheme.primary.copy(alpha = 0.3f)
                )
            }
        }
    }
}

/**
 * Offline mode indicator
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun OfflineModeIndicator(
    isOffline: Boolean,
    onRetryConnection: (() -> Unit)? = null
) {
    AnimatedVisibility(
        visible = isOffline,
        enter = fadeIn() + slideInVertically(),
        exit = fadeOut() + slideOutVertically()
    ) {
        Card(
            modifier = Modifier.fillMaxWidth(),
            colors = CardDefaults.cardColors(
                containerColor = MaterialTheme.colorScheme.errorContainer
            )
        ) {
            Row(
                verticalAlignment = Alignment.CenterVertically,
                modifier = Modifier.padding(16.dp)
            ) {
                Icon(
                    imageVector = Icons.Default.CloudOff,
                    contentDescription = null,
                    tint = MaterialTheme.colorScheme.onErrorContainer,
                    modifier = Modifier.size(24.dp)
                )
                
                Spacer(modifier = Modifier.width(12.dp))
                
                Column(modifier = Modifier.weight(1f)) {
                    Text(
                        text = "Offline Mode",
                        style = MaterialTheme.typography.bodyMedium,
                        fontWeight = FontWeight.Medium,
                        color = MaterialTheme.colorScheme.onErrorContainer
                    )
                    
                    Text(
                        text = "Events will be created with basic information",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onErrorContainer.copy(alpha = 0.8f)
                    )
                }
                
                onRetryConnection?.let { retry ->
                    TextButton(
                        onClick = retry,
                        colors = ButtonDefaults.textButtonColors(
                            contentColor = MaterialTheme.colorScheme.onErrorContainer
                        )
                    ) {
                        Icon(
                            imageVector = Icons.Default.Refresh,
                            contentDescription = null,
                            modifier = Modifier.size(16.dp)
                        )
                        Spacer(modifier = Modifier.width(4.dp))
                        Text("Retry")
                    }
                }
            }
        }
    }
}

/**
 * Network error state indicator
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun NetworkErrorIndicator(
    errorMessage: String,
    onRetry: () -> Unit,
    onOfflineMode: (() -> Unit)? = null
) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.errorContainer
        )
    ) {
        Column(
            modifier = Modifier.padding(16.dp)
        ) {
            Row(
                verticalAlignment = Alignment.CenterVertically
            ) {
                Icon(
                    imageVector = Icons.Default.ErrorOutline,
                    contentDescription = null,
                    tint = MaterialTheme.colorScheme.onErrorContainer,
                    modifier = Modifier.size(24.dp)
                )
                
                Spacer(modifier = Modifier.width(12.dp))
                
                Text(
                    text = "Connection Error",
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.Medium,
                    color = MaterialTheme.colorScheme.onErrorContainer
                )
            }
            
            Spacer(modifier = Modifier.height(8.dp))
            
            Text(
                text = errorMessage,
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onErrorContainer.copy(alpha = 0.9f)
            )
            
            Spacer(modifier = Modifier.height(12.dp))
            
            Row(
                horizontalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                Button(
                    onClick = onRetry,
                    colors = ButtonDefaults.buttonColors(
                        containerColor = MaterialTheme.colorScheme.error
                    )
                ) {
                    Icon(
                        imageVector = Icons.Default.Refresh,
                        contentDescription = null,
                        modifier = Modifier.size(16.dp)
                    )
                    Spacer(modifier = Modifier.width(8.dp))
                    Text("Retry")
                }
                
                onOfflineMode?.let { offlineAction ->
                    OutlinedButton(
                        onClick = offlineAction,
                        colors = ButtonDefaults.outlinedButtonColors(
                            contentColor = MaterialTheme.colorScheme.onErrorContainer
                        )
                    ) {
                        Icon(
                            imageVector = Icons.Default.CloudOff,
                            contentDescription = null,
                            modifier = Modifier.size(16.dp)
                        )
                        Spacer(modifier = Modifier.width(8.dp))
                        Text("Offline Mode")
                    }
                }
            }
        }
    }
}

/**
 * Loading state indicator with enhanced animation
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun LoadingStateIndicator(
    isLoading: Boolean,
    message: String = "Processing...",
    progress: Float? = null
) {
    AnimatedVisibility(
        visible = isLoading,
        enter = fadeIn() + slideInVertically(),
        exit = fadeOut() + slideOutVertically()
    ) {
        Card(
            modifier = Modifier.fillMaxWidth(),
            colors = CardDefaults.cardColors(
                containerColor = MaterialTheme.colorScheme.surfaceVariant
            )
        ) {
            Row(
                verticalAlignment = Alignment.CenterVertically,
                modifier = Modifier.padding(16.dp)
            ) {
                if (progress != null) {
                    CircularProgressIndicator(
                        progress = progress,
                        modifier = Modifier.size(24.dp),
                        strokeWidth = 3.dp,
                        color = MaterialTheme.colorScheme.primary
                    )
                } else {
                    CircularProgressIndicator(
                        modifier = Modifier.size(24.dp),
                        strokeWidth = 3.dp,
                        color = MaterialTheme.colorScheme.primary
                    )
                }
                
                Spacer(modifier = Modifier.width(12.dp))
                
                Text(
                    text = message,
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }
        }
    }
}

/**
 * Gets confidence visual information (color, icon, label)
 */
private fun getConfidenceVisualInfo(confidence: Double): Triple<Color, ImageVector, String> {
    return when {
        confidence >= 0.7 -> Triple(
            Color(0xFF4CAF50), // Green
            Icons.Default.CheckCircle,
            "High"
        )
        confidence >= 0.3 -> Triple(
            Color(0xFFFF9800), // Orange
            Icons.Default.Warning,
            "Medium"
        )
        else -> Triple(
            Color(0xFFF44336), // Red
            Icons.Default.Error,
            "Low"
        )
    }
}

private fun formatDateTime(isoDateTime: String): String {
    return try {
        val inputFormat = SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ssXXX", Locale.getDefault())
        val outputFormat = SimpleDateFormat("MMM dd, yyyy 'at' h:mm a", Locale.getDefault())
        val date = inputFormat.parse(isoDateTime)
        date?.let { outputFormat.format(it) } ?: isoDateTime
    } catch (e: Exception) {
        try {
            val inputFormat = SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss", Locale.getDefault())
            val outputFormat = SimpleDateFormat("MMM dd, yyyy 'at' h:mm a", Locale.getDefault())
            val date = inputFormat.parse(isoDateTime)
            date?.let { outputFormat.format(it) } ?: isoDateTime
        } catch (e2: Exception) {
            isoDateTime
        }
    }
}
/**
 * 
Enhanced button with state indicators for different scenarios
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun EnhancedStateButton(
    text: String,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    enabled: Boolean = true,
    isLoading: Boolean = false,
    isRetrying: Boolean = false,
    retryCount: Int = 0,
    maxRetries: Int = 3,
    icon: ImageVector? = null,
    buttonState: ButtonState = ButtonState.NORMAL
) {
    val buttonColor = when (buttonState) {
        ButtonState.NORMAL -> MaterialTheme.colorScheme.primary
        ButtonState.SUCCESS -> Color(0xFF4CAF50)
        ButtonState.WARNING -> Color(0xFFFF9800)
        ButtonState.ERROR -> MaterialTheme.colorScheme.error
        ButtonState.RETRY -> MaterialTheme.colorScheme.tertiary
    }
    
    Button(
        onClick = onClick,
        modifier = modifier,
        enabled = enabled && !isLoading && !isRetrying,
        colors = ButtonDefaults.buttonColors(
            containerColor = buttonColor,
            disabledContainerColor = buttonColor.copy(alpha = 0.6f)
        )
    ) {
        when {
            isLoading -> {
                CircularProgressIndicator(
                    modifier = Modifier.size(16.dp),
                    color = MaterialTheme.colorScheme.onPrimary,
                    strokeWidth = 2.dp
                )
                Spacer(modifier = Modifier.width(8.dp))
                Text("Processing...")
            }
            
            isRetrying -> {
                CircularProgressIndicator(
                    modifier = Modifier.size(16.dp),
                    color = MaterialTheme.colorScheme.onPrimary,
                    strokeWidth = 2.dp
                )
                Spacer(modifier = Modifier.width(8.dp))
                Text("Retrying... (${retryCount + 1}/$maxRetries)")
            }
            
            else -> {
                icon?.let { iconVector ->
                    Icon(
                        imageVector = iconVector,
                        contentDescription = null,
                        modifier = Modifier.size(16.dp)
                    )
                    Spacer(modifier = Modifier.width(8.dp))
                }
                Text(text)
            }
        }
    }
}

/**
 * Button state enum for different scenarios
 */
enum class ButtonState {
    NORMAL,
    SUCCESS,
    WARNING,
    ERROR,
    RETRY
}

/**
 * Connection status indicator with animated states
 */
@Composable
fun ConnectionStatusIndicator(
    isConnected: Boolean,
    isRetrying: Boolean = false,
    modifier: Modifier = Modifier
) {
    val infiniteTransition = rememberInfiniteTransition()
    val alpha by infiniteTransition.animateFloat(
        initialValue = 0.3f,
        targetValue = 1f,
        animationSpec = infiniteRepeatable(
            animation = tween(1000),
            repeatMode = RepeatMode.Reverse
        )
    )
    
    Row(
        verticalAlignment = Alignment.CenterVertically,
        modifier = modifier
    ) {
        Box(
            modifier = Modifier
                .size(8.dp)
                .clip(CircleShape)
                .background(
                    when {
                        isRetrying -> Color(0xFFFF9800).copy(alpha = alpha)
                        isConnected -> Color(0xFF4CAF50)
                        else -> Color(0xFFF44336)
                    }
                )
        )
        
        Spacer(modifier = Modifier.width(8.dp))
        
        Text(
            text = when {
                isRetrying -> "Reconnecting..."
                isConnected -> "Online"
                else -> "Offline"
            },
            style = MaterialTheme.typography.labelSmall,
            color = when {
                isRetrying -> Color(0xFFFF9800)
                isConnected -> Color(0xFF4CAF50)
                else -> Color(0xFFF44336)
            }
        )
    }
}

/**
 * Confidence meter with visual progress indicator
 */
@Composable
fun ConfidenceMeter(
    confidence: Double,
    modifier: Modifier = Modifier,
    showPercentage: Boolean = true,
    animated: Boolean = true
) {
    val animatedProgress by animateFloatAsState(
        targetValue = if (animated) confidence.toFloat() else confidence.toFloat(),
        animationSpec = tween(durationMillis = 1000)
    )
    
    val (color, label) = when {
        confidence >= 0.7 -> Color(0xFF4CAF50) to "High"
        confidence >= 0.3 -> Color(0xFFFF9800) to "Medium"
        else -> Color(0xFFF44336) to "Low"
    }
    
    Column(modifier = modifier) {
        Row(
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.SpaceBetween,
            modifier = Modifier.fillMaxWidth()
        ) {
            Text(
                text = "Confidence: $label",
                style = MaterialTheme.typography.labelMedium,
                color = color
            )
            
            if (showPercentage) {
                Text(
                    text = "${(confidence * 100).toInt()}%",
                    style = MaterialTheme.typography.labelMedium,
                    color = color,
                    fontWeight = FontWeight.Bold
                )
            }
        }
        
        Spacer(modifier = Modifier.height(4.dp))
        
        LinearProgressIndicator(
            progress = animatedProgress,
            modifier = Modifier
                .fillMaxWidth()
                .height(6.dp)
                .clip(RoundedCornerShape(3.dp)),
            color = color,
            trackColor = color.copy(alpha = 0.2f)
        )
    }
}

/**
 * Field validation indicator for individual fields
 */
@Composable
fun FieldValidationIndicator(
    fieldName: String,
    isValid: Boolean,
    confidence: Double? = null,
    issues: List<String> = emptyList(),
    modifier: Modifier = Modifier
) {
    Row(
        verticalAlignment = Alignment.CenterVertically,
        modifier = modifier
    ) {
        Icon(
            imageVector = when {
                !isValid -> Icons.Default.Error
                confidence != null && confidence < 0.3 -> Icons.Default.Warning
                confidence != null && confidence < 0.7 -> Icons.Default.Info
                else -> Icons.Default.CheckCircle
            },
            contentDescription = null,
            tint = when {
                !isValid -> Color(0xFFF44336)
                confidence != null && confidence < 0.3 -> Color(0xFFFF9800)
                confidence != null && confidence < 0.7 -> Color(0xFF2196F3)
                else -> Color(0xFF4CAF50)
            },
            modifier = Modifier.size(16.dp)
        )
        
        Spacer(modifier = Modifier.width(8.dp))
        
        Column {
            Text(
                text = fieldName,
                style = MaterialTheme.typography.bodySmall,
                fontWeight = FontWeight.Medium
            )
            
            if (issues.isNotEmpty()) {
                Text(
                    text = issues.first(),
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.6f)
                )
            }
        }
        
        Spacer(modifier = Modifier.weight(1f))
        
        confidence?.let { conf ->
            Text(
                text = "${(conf * 100).toInt()}%",
                style = MaterialTheme.typography.labelSmall,
                color = when {
                    conf < 0.3 -> Color(0xFFFF9800)
                    conf < 0.7 -> Color(0xFF2196F3)
                    else -> Color(0xFF4CAF50)
                }
            )
        }
    }
}

/**
 * Error recovery suggestions card
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ErrorRecoverySuggestions(
    suggestions: List<String>,
    onSuggestionClick: (String) -> Unit = {},
    modifier: Modifier = Modifier
) {
    if (suggestions.isEmpty()) return
    
    Card(
        modifier = modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.secondaryContainer
        )
    ) {
        Column(
            modifier = Modifier.padding(16.dp)
        ) {
            Row(
                verticalAlignment = Alignment.CenterVertically
            ) {
                Icon(
                    imageVector = Icons.Default.Lightbulb,
                    contentDescription = null,
                    tint = MaterialTheme.colorScheme.onSecondaryContainer,
                    modifier = Modifier.size(20.dp)
                )
                
                Spacer(modifier = Modifier.width(8.dp))
                
                Text(
                    text = "Suggestions",
                    style = MaterialTheme.typography.titleSmall,
                    fontWeight = FontWeight.Medium,
                    color = MaterialTheme.colorScheme.onSecondaryContainer
                )
            }
            
            Spacer(modifier = Modifier.height(12.dp))
            
            suggestions.take(3).forEach { suggestion ->
                Row(
                    verticalAlignment = Alignment.Top,
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(vertical = 2.dp)
                ) {
                    Text(
                        text = "•",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSecondaryContainer,
                        modifier = Modifier.padding(end = 8.dp, top = 2.dp)
                    )
                    
                    Text(
                        text = suggestion,
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSecondaryContainer,
                        modifier = Modifier.weight(1f)
                    )
                }
            }
        }
    }
}

/**
 * Processing status timeline for showing parsing steps
 */
@Composable
fun ProcessingStatusTimeline(
    steps: List<ProcessingStep>,
    currentStep: Int,
    modifier: Modifier = Modifier
) {
    Column(modifier = modifier) {
        steps.forEachIndexed { index, step ->
            Row(
                verticalAlignment = Alignment.CenterVertically,
                modifier = Modifier.padding(vertical = 4.dp)
            ) {
                // Step indicator
                Box(
                    modifier = Modifier
                        .size(24.dp)
                        .clip(CircleShape)
                        .background(
                            when {
                                index < currentStep -> Color(0xFF4CAF50)
                                index == currentStep -> MaterialTheme.colorScheme.primary
                                else -> MaterialTheme.colorScheme.outline.copy(alpha = 0.3f)
                            }
                        ),
                    contentAlignment = Alignment.Center
                ) {
                    when {
                        index < currentStep -> {
                            Icon(
                                imageVector = Icons.Default.Check,
                                contentDescription = null,
                                tint = Color.White,
                                modifier = Modifier.size(14.dp)
                            )
                        }
                        index == currentStep -> {
                            CircularProgressIndicator(
                                modifier = Modifier.size(14.dp),
                                strokeWidth = 2.dp,
                                color = Color.White
                            )
                        }
                        else -> {
                            Text(
                                text = "${index + 1}",
                                style = MaterialTheme.typography.labelSmall,
                                color = MaterialTheme.colorScheme.outline
                            )
                        }
                    }
                }
                
                Spacer(modifier = Modifier.width(12.dp))
                
                Column {
                    Text(
                        text = step.title,
                        style = MaterialTheme.typography.bodyMedium,
                        fontWeight = if (index == currentStep) FontWeight.Medium else FontWeight.Normal,
                        color = when {
                            index <= currentStep -> MaterialTheme.colorScheme.onSurface
                            else -> MaterialTheme.colorScheme.onSurface.copy(alpha = 0.6f)
                        }
                    )
                    
                    if (step.description.isNotEmpty()) {
                        Text(
                            text = step.description,
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.7f)
                        )
                    }
                }
            }
            
            // Connector line (except for last item)
            if (index < steps.size - 1) {
                Box(
                    modifier = Modifier
                        .padding(start = 12.dp)
                        .width(2.dp)
                        .height(16.dp)
                        .background(
                            if (index < currentStep) {
                                Color(0xFF4CAF50)
                            } else {
                                MaterialTheme.colorScheme.outline.copy(alpha = 0.3f)
                            }
                        )
                )
            }
        }
    }
}

/**
 * Processing step data class
 */
data class ProcessingStep(
    val title: String,
    val description: String = ""
)