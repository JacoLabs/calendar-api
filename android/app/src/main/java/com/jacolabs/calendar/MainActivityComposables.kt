package com.jacolabs.calendar

import androidx.compose.foundation.layout.*
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Event
import androidx.compose.material.icons.filled.Info
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import java.text.SimpleDateFormat
import java.util.*

/**
 * Confidence Warning Card - shows when confidence is low
 */
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
                        text = "• ${suggestion.suggestion}",
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
 * Enhanced Result Card with confidence indicators
 */
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
                
                // Overall confidence indicator
                val confidence = (result.confidenceScore * 100).toInt()
                val confidenceColor = when {
                    confidence >= 70 -> MaterialTheme.colorScheme.primary
                    confidence >= 30 -> MaterialTheme.colorScheme.tertiary
                    else -> MaterialTheme.colorScheme.error
                }
                
                Surface(
                    color = confidenceColor.copy(alpha = 0.1f),
                    shape = MaterialTheme.shapes.small
                ) {
                    Text(
                        text = "$confidence%",
                        modifier = Modifier.padding(horizontal = 8.dp, vertical = 4.dp),
                        style = MaterialTheme.typography.labelMedium,
                        color = confidenceColor
                    )
                }
            }
            
            Spacer(modifier = Modifier.height(12.dp))
            
            // Show field-level confidence if available
            confidenceAssessment?.fieldConfidences?.let { fieldConfidences ->
                fieldConfidences.forEach { (fieldName, fieldInfo) ->
                    if (fieldInfo.hasValue) {
                        Row(
                            verticalAlignment = Alignment.CenterVertically,
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            val fieldConfidence = (fieldInfo.confidence * 100).toInt()
                            val fieldColor = when {
                                fieldConfidence >= 70 -> MaterialTheme.colorScheme.primary
                                fieldConfidence >= 30 -> MaterialTheme.colorScheme.tertiary
                                else -> MaterialTheme.colorScheme.error
                            }
                            
                            Text(
                                text = "${fieldName.replaceFirstChar { it.uppercase() }}: ${fieldInfo.value}",
                                style = MaterialTheme.typography.bodyMedium,
                                modifier = Modifier.weight(1f)
                            )
                            
                            Surface(
                                color = fieldColor.copy(alpha = 0.1f),
                                shape = MaterialTheme.shapes.extraSmall
                            ) {
                                Text(
                                    text = "$fieldConfidence%",
                                    modifier = Modifier.padding(horizontal = 4.dp, vertical = 2.dp),
                                    style = MaterialTheme.typography.labelSmall,
                                    color = fieldColor
                                )
                            }
                        }
                        Spacer(modifier = Modifier.height(4.dp))
                    }
                }
            } ?: run {
                // Fallback to simple display if no field confidence available
                result.title?.let { title ->
                    Text("Title: $title", style = MaterialTheme.typography.bodyMedium)
                    Spacer(modifier = Modifier.height(4.dp))
                }
                
                result.startDateTime?.let { startDateTime ->
                    val formattedDate = formatDateTime(startDateTime)
                    Text("Start: $formattedDate", style = MaterialTheme.typography.bodyMedium)
                    Spacer(modifier = Modifier.height(4.dp))
                }
                
                result.endDateTime?.let { endDateTime ->
                    val formattedDate = formatDateTime(endDateTime)
                    Text("End: $formattedDate", style = MaterialTheme.typography.bodyMedium)
                    Spacer(modifier = Modifier.height(4.dp))
                }
                
                result.location?.let { location ->
                    Text("Location: $location", style = MaterialTheme.typography.bodyMedium)
                    Spacer(modifier = Modifier.height(4.dp))
                }
            }
            
            // Show fallback information if applicable
            result.fallbackReason?.let { reason ->
                Spacer(modifier = Modifier.height(8.dp))
                Text(
                    text = "ℹ️ $reason",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.tertiary
                )
            }
            
            // Show parsing warnings if any
            result.warnings?.let { warnings ->
                if (warnings.isNotEmpty()) {
                    Spacer(modifier = Modifier.height(8.dp))
                    warnings.forEach { warning ->
                        Text(
                            text = "⚠️ $warning",
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.tertiary
                        )
                    }
                }
            }
            
            Spacer(modifier = Modifier.height(16.dp))
            
            // Action buttons
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                Button(
                    onClick = onCreateEvent,
                    modifier = Modifier.weight(1f)
                ) {
                    Icon(
                        imageVector = Icons.Default.Event,
                        contentDescription = null,
                        modifier = Modifier.size(18.dp)
                    )
                    Spacer(modifier = Modifier.width(8.dp))
                    Text("Create Event")
                }
                
                // Show retry button for low confidence results
                val confidence = (result.confidenceScore * 100).toInt()
                if (confidence < 50) {
                    OutlinedButton(
                        onClick = onRetry,
                        modifier = Modifier.weight(1f)
                    ) {
                        Text("Improve")
                    }
                }
            }
        }
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