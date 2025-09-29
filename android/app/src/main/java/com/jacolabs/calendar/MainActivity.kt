package com.jacolabs.calendar

import android.content.Intent
import android.os.Bundle
import android.provider.CalendarContract
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Event
import androidx.compose.material.icons.filled.Info
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import android.content.Context
import androidx.lifecycle.lifecycleScope
import kotlinx.coroutines.launch
import java.text.SimpleDateFormat
import java.util.*

/**
 * Main activity with text input interface for testing API integration.
 */
class MainActivity : ComponentActivity() {
    
    private lateinit var apiService: ApiService
    
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        
        apiService = ApiService()
        
        setContent {
            MaterialTheme {
                Surface(
                    modifier = Modifier.fillMaxSize(),
                    color = MaterialTheme.colorScheme.background
                ) {
                    MainScreen(apiService, lifecycleScope)
                }
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun MainScreen(apiService: ApiService, lifecycleScope: androidx.lifecycle.LifecycleCoroutineScope) {
    var textInput by remember { mutableStateOf("") }
    var isLoading by remember { mutableStateOf(false) }
    var parseResult by remember { mutableStateOf<ParseResult?>(null) }
    var errorMessage by remember { mutableStateOf<String?>(null) }
    var clipboardText by remember { mutableStateOf<String?>(null) }
    var showTimeConfirmBanner by remember { mutableStateOf(false) }
    val context = LocalContext.current
    
    // Check clipboard content on composition
    LaunchedEffect(Unit) {
        clipboardText = getClipboardText(context)
    }
    
    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(24.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Top
    ) {
        
        Spacer(modifier = Modifier.height(32.dp))
        
        Icon(
            imageVector = Icons.Default.Event,
            contentDescription = "Calendar Event",
            modifier = Modifier.size(64.dp),
            tint = MaterialTheme.colorScheme.primary
        )
        
        Spacer(modifier = Modifier.height(24.dp))
        
        Text(
            text = "Calendar Event Creator",
            style = MaterialTheme.typography.headlineMedium,
            textAlign = TextAlign.Center
        )
        
        Spacer(modifier = Modifier.height(16.dp))
        
        Text(
            text = "Create calendar events from natural language text",
            style = MaterialTheme.typography.bodyLarge,
            textAlign = TextAlign.Center,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )
        
        Spacer(modifier = Modifier.height(32.dp))
        
        // Text input field
        OutlinedTextField(
            value = textInput,
            onValueChange = { newValue ->
                textInput = newValue
                // Clear previous results when user starts typing
                if (parseResult != null || errorMessage != null) {
                    parseResult = null
                    errorMessage = null
                    showTimeConfirmBanner = false
                }
            },
            label = { Text("Enter event text") },
            placeholder = { Text("e.g., Meeting with John tomorrow at 2pm") },
            modifier = Modifier.fillMaxWidth(),
            maxLines = 5,
            enabled = !isLoading
        )
        
        // Paste from Clipboard button (visible when clipboard has text)
        if (!clipboardText.isNullOrBlank() && clipboardText != textInput) {
            Spacer(modifier = Modifier.height(8.dp))
            
            OutlinedButton(
                onClick = {
                    textInput = clipboardText!!
                    // Auto-parse clipboard content
                    parseClipboardContent(
                        clipboardText!!,
                        apiService,
                        lifecycleScope,
                        context,
                        onResult = { result ->
                            parseResult = result
                            // Check if we applied default times
                            showTimeConfirmBanner = hasDefaultTimes(result, clipboardText!!)
                        },
                        onError = { error ->
                            errorMessage = error
                        }
                    )
                },
                modifier = Modifier.fillMaxWidth(),
                enabled = !isLoading
            ) {
                Icon(
                    imageVector = Icons.Default.Event,
                    contentDescription = null,
                    modifier = Modifier.size(16.dp)
                )
                Spacer(modifier = Modifier.width(8.dp))
                Text("Paste from Clipboard & Parse")
            }
        }
        
        Spacer(modifier = Modifier.height(16.dp))
        
        // Submit button
        Button(
            onClick = {
                isLoading = true
                errorMessage = null
                parseResult = null
                
                lifecycleScope.launch {
                    try {
                        val timezone = TimeZone.getDefault().id
                        val locale = Locale.getDefault().toString()
                        val now = Date()
                        
                        val result = apiService.parseText(
                            text = textInput,
                            timezone = timezone,
                            locale = locale,
                            now = now
                        )
                        
                        parseResult = result
                        
                    } catch (e: ApiException) {
                        errorMessage = e.message
                    } catch (e: Exception) {
                        errorMessage = "An unexpected error occurred. Please try again."
                    } finally {
                        isLoading = false
                    }
                }
            },
            modifier = Modifier.fillMaxWidth(),
            enabled = textInput.isNotBlank() && !isLoading
        ) {
            if (isLoading) {
                CircularProgressIndicator(
                    modifier = Modifier.size(16.dp),
                    color = MaterialTheme.colorScheme.onPrimary
                )
                Spacer(modifier = Modifier.width(8.dp))
            }
            Text(if (isLoading) "Processing..." else "Parse Event")
        }
        
        Spacer(modifier = Modifier.height(24.dp))
        
        // Time confirmation banner
        if (showTimeConfirmBanner) {
            Spacer(modifier = Modifier.height(16.dp))
            Card(
                modifier = Modifier.fillMaxWidth(),
                colors = CardDefaults.cardColors(
                    containerColor = MaterialTheme.colorScheme.tertiaryContainer
                )
            ) {
                Column(
                    modifier = Modifier.padding(16.dp)
                ) {
                    Text(
                        text = "⏰ Default Time Applied",
                        style = MaterialTheme.typography.titleSmall,
                        color = MaterialTheme.colorScheme.onTertiaryContainer
                    )
                    Spacer(modifier = Modifier.height(4.dp))
                    Text(
                        text = "We found a weekday but no specific time, so we set it to 9:00-10:00 AM. You can adjust this in your calendar app.",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onTertiaryContainer
                    )
                }
            }
        }
        
        // Display results
        parseResult?.let { result ->
            Card(
                modifier = Modifier.fillMaxWidth(),
                colors = CardDefaults.cardColors(
                    containerColor = MaterialTheme.colorScheme.surfaceVariant
                )
            ) {
                Column(
                    modifier = Modifier.padding(16.dp)
                ) {
                    Text(
                        text = "Parsed Event Details",
                        style = MaterialTheme.typography.titleMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                    
                    Spacer(modifier = Modifier.height(12.dp))
                    
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
                    
                    // Confidence score with color coding
                    val confidence = (result.confidenceScore * 100).toInt()
                    val confidenceColor = when {
                        confidence >= 70 -> MaterialTheme.colorScheme.primary
                        confidence >= 30 -> MaterialTheme.colorScheme.tertiary
                        else -> MaterialTheme.colorScheme.error
                    }
                    
                    Text(
                        "Confidence: $confidence%",
                        style = MaterialTheme.typography.bodyMedium,
                        color = confidenceColor
                    )
                    
                    // Show warning for low confidence
                    if (confidence < 30) {
                        Spacer(modifier = Modifier.height(8.dp))
                        Text(
                            "⚠️ Low confidence - consider rephrasing with clearer date/time",
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.error
                        )
                    }
                    
                    Spacer(modifier = Modifier.height(16.dp))
                    
                    // Create Calendar Event button
                    Button(
                        onClick = {
                            createCalendarEvent(context, result)
                        },
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Icon(
                            imageVector = Icons.Default.Event,
                            contentDescription = null,
                            modifier = Modifier.size(18.dp)
                        )
                        Spacer(modifier = Modifier.width(8.dp))
                        Text("Create Calendar Event")
                    }
                }
            }
        }
        
        // Display error message
        errorMessage?.let { error ->
            Spacer(modifier = Modifier.height(16.dp))
            Card(
                modifier = Modifier.fillMaxWidth(),
                colors = CardDefaults.cardColors(
                    containerColor = MaterialTheme.colorScheme.errorContainer
                )
            ) {
                Text(
                    text = error,
                    modifier = Modifier.padding(16.dp),
                    color = MaterialTheme.colorScheme.onErrorContainer,
                    style = MaterialTheme.typography.bodyMedium
                )
            }
        }
        
        Spacer(modifier = Modifier.height(32.dp))
        
        // Instructions card
        Card(
            modifier = Modifier.fillMaxWidth(),
            colors = CardDefaults.cardColors(
                containerColor = MaterialTheme.colorScheme.primaryContainer
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
                        tint = MaterialTheme.colorScheme.onPrimaryContainer
                    )
                    Spacer(modifier = Modifier.width(8.dp))
                    Text(
                        text = "How to Use",
                        style = MaterialTheme.typography.titleMedium,
                        color = MaterialTheme.colorScheme.onPrimaryContainer
                    )
                }
                
                Spacer(modifier = Modifier.height(12.dp))
                
                Text(
                    text = "1. Type or paste text containing event information\n" +
                            "2. Tap 'Parse Event' to extract details\n" +
                            "3. Review the results and tap 'Create Calendar Event'\n\n" +
                            "You can also:\n" +
                            "• Select text in any app and choose 'Create calendar event'\n" +
                            "• Share text to this app from other apps",
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onPrimaryContainer
                )
            }
        }
        
        Spacer(modifier = Modifier.height(16.dp))
        
        Text(
            text = "Examples:\n" +
                    "• \"Meeting with John tomorrow at 2pm\"\n" +
                    "• \"Lunch at The Keg next Friday 12:30\"\n" +
                    "• \"Conference call Monday 10am for 1 hour\"\n" +
                    "• \"Doctor appointment on January 15th at 3:30 PM\"",
            style = MaterialTheme.typography.bodySmall,
            textAlign = TextAlign.Center,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )
        
        Spacer(modifier = Modifier.height(32.dp))
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

private fun createCalendarEvent(context: android.content.Context, result: ParseResult) {
    val calendarHelper = CalendarIntentHelper(context)
    calendarHelper.createCalendarEvent(result)
}

private fun getClipboardText(context: Context): String? {
    return try {
        val clipboardManager = context.getSystemService(Context.CLIPBOARD_SERVICE) as android.content.ClipboardManager
        val clip = clipboardManager.primaryClip
        
        if (clip != null && clip.itemCount > 0) {
            val clipText = clip.getItemAt(0).text?.toString()
            if (!clipText.isNullOrBlank() && clipText.length <= 500) {
                clipText
            } else null
        } else null
    } catch (e: Exception) {
        null
    }
}

private fun parseClipboardContent(
    text: String,
    apiService: ApiService,
    lifecycleScope: androidx.lifecycle.LifecycleCoroutineScope,
    context: Context,
    onResult: (ParseResult) -> Unit,
    onError: (String) -> Unit
) {
    lifecycleScope.launch {
        try {
            val timezone = TimeZone.getDefault().id
            val locale = Locale.getDefault().toString()
            val now = Date()
            
            // Use TextMergeHelper for enhanced processing
            val textMergeHelper = TextMergeHelper(context)
            val enhancedText = textMergeHelper.enhanceTextForParsing(text)
            val result = apiService.parseText(enhancedText, timezone, locale, now)
            val finalResult = textMergeHelper.applySaferDefaults(result, enhancedText)
            
            onResult(finalResult)
            
        } catch (e: ApiException) {
            onError(e.message ?: "Failed to process clipboard text")
        } catch (e: Exception) {
            onError("An unexpected error occurred")
        }
    }
}

private fun hasDefaultTimes(result: ParseResult, originalText: String): Boolean {
    // Check if we applied default 9:00 AM time
    val hasWeekday = listOf("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")
        .any { originalText.lowercase().contains(it) }
    
    val hasDefaultTime = result.startDateTime?.contains("09:00:00") == true
    
    return hasWeekday && hasDefaultTime && !originalText.contains("9:00") && !originalText.contains("9am")
}

