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
import androidx.compose.material.icons.filled.*
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
 * Main activity with integrated error handling system.
 * Enhanced with comprehensive error handling and fallback mechanisms.
 * 
 * Task 16 Integration: Complete end-to-end error handling workflow
 * Requirements: 1.1, 1.2, 1.3, 1.4, 10.4
 */
class MainActivity : ComponentActivity() {
    
    private lateinit var apiService: ApiService
    private lateinit var errorHandlingManager: ErrorHandlingManager
    private lateinit var confidenceValidator: ConfidenceValidator
    private lateinit var userFeedbackManager: UserFeedbackManager
    private lateinit var systemIntegrator: ErrorHandlingSystemIntegrator
    
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        
        // Initialize services with integrated error handling system
        apiService = ApiService(this)
        errorHandlingManager = ErrorHandlingManager(this)
        confidenceValidator = ConfidenceValidator(this)
        userFeedbackManager = UserFeedbackManager(this)
        systemIntegrator = ErrorHandlingSystemIntegrator(this)
        
        setContent {
            MaterialTheme {
                Surface(
                    modifier = Modifier.fillMaxSize(),
                    color = MaterialTheme.colorScheme.background
                ) {
                    MainScreen(
                        systemIntegrator = systemIntegrator,
                        userFeedbackManager = userFeedbackManager,
                        lifecycleScope = lifecycleScope
                    )
                }
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun MainScreen(
    systemIntegrator: ErrorHandlingSystemIntegrator,
    userFeedbackManager: UserFeedbackManager,
    lifecycleScope: androidx.lifecycle.LifecycleCoroutineScope
) {
    var textInput by remember { mutableStateOf("") }
    var isLoading by remember { mutableStateOf(false) }
    var parseResult by remember { mutableStateOf<ParseResult?>(null) }
    var errorMessage by remember { mutableStateOf<String?>(null) }
    var clipboardText by remember { mutableStateOf<String?>(null) }
    var showTimeConfirmBanner by remember { mutableStateOf(false) }
    var userInteraction by remember { mutableStateOf<UserInteraction?>(null) }
    var progressMessage by remember { mutableStateOf<String?>(null) }
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
            text = "Create calendar events from natural language text with intelligent error handling",
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
                    userInteraction = null
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
                    processTextWithIntegratedSystem(
                        text = clipboardText!!,
                        systemIntegrator = systemIntegrator,
                        lifecycleScope = lifecycleScope,
                        onLoading = { loading -> isLoading = loading },
                        onSuccess = { result ->
                            parseResult = result
                            showTimeConfirmBanner = hasDefaultTimes(result, clipboardText!!)
                            errorMessage = null
                            userInteraction = null
                        },
                        onError = { error ->
                            errorMessage = error
                            parseResult = null
                            userInteraction = null
                        },
                        onUserInteraction = { interaction ->
                            userInteraction = interaction
                        },
                        onProgress = { progress ->
                            progressMessage = progress
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
        
        // Submit button with integrated error handling
        Button(
            onClick = {
                processTextWithIntegratedSystem(
                    text = textInput,
                    systemIntegrator = systemIntegrator,
                    lifecycleScope = lifecycleScope,
                    onLoading = { loading -> isLoading = loading },
                    onSuccess = { result ->
                        parseResult = result
                        showTimeConfirmBanner = hasDefaultTimes(result, textInput)
                        errorMessage = null
                        userInteraction = null
                    },
                    onError = { error ->
                        errorMessage = error
                        parseResult = null
                        userInteraction = null
                    },
                    onUserInteraction = { interaction ->
                        userInteraction = interaction
                    },
                    onProgress = { progress ->
                        progressMessage = progress
                    }
                )
            },
            modifier = Modifier.fillMaxWidth(),
            enabled = textInput.isNotBlank() && !isLoading
        ) {
            if (isLoading) {
                CircularProgressIndicator(
                    modifier = Modifier.size(16.dp),
                    color = MaterialTheme.colorScheme.onPrimary,
                    strokeWidth = 2.dp
                )
                Spacer(modifier = Modifier.width(8.dp))
                Text("Processing...")
            } else {
                Icon(
                    imageVector = Icons.Default.Search,
                    contentDescription = null,
                    modifier = Modifier.size(16.dp)
                )
                Spacer(modifier = Modifier.width(8.dp))
                Text("Parse Event")
            }
        }
        
        Spacer(modifier = Modifier.height(24.dp))
        
        // Progress message display
        progressMessage?.let { progress ->
            Card(
                modifier = Modifier.fillMaxWidth(),
                colors = CardDefaults.cardColors(
                    containerColor = MaterialTheme.colorScheme.primaryContainer
                )
            ) {
                Row(
                    modifier = Modifier.padding(16.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    CircularProgressIndicator(
                        modifier = Modifier.size(16.dp),
                        strokeWidth = 2.dp
                    )
                    Spacer(modifier = Modifier.width(12.dp))
                    Text(
                        text = progress,
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.onPrimaryContainer
                    )
                }
            }
            Spacer(modifier = Modifier.height(16.dp))
        }
        
        // User interaction handling
        userInteraction?.let { interaction ->
            UserInteractionCard(
                interaction = interaction,
                onDismiss = { userInteraction = null }
            )
            Spacer(modifier = Modifier.height(16.dp))
        }
        
        // Time confirmation banner
        if (showTimeConfirmBanner) {
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
            Spacer(modifier = Modifier.height(16.dp))
        }
        
        // Display results
        parseResult?.let { result ->
            EnhancedResultCard(
                result = result,
                onCreateEvent = { 
                    createCalendarEventWithIntegratedSystem(
                        result = result,
                        systemIntegrator = systemIntegrator,
                        lifecycleScope = lifecycleScope,
                        onSuccess = {
                            parseResult = null
                            textInput = ""
                            userFeedbackManager.showSuccessMessage("Calendar event created successfully!")
                        },
                        onError = { error ->
                            errorMessage = error
                        },
                        onAlternatives = { alternatives ->
                            lifecycleScope.launch {
                                userFeedbackManager.showCalendarNotFoundDialog(result, alternatives)
                            }
                        }
                    )
                },
                onRetry = {
                    parseResult = null
                    errorMessage = "Please try rephrasing with clearer date, time, and event details."
                }
            )
        }
        
        // Enhanced error display
        errorMessage?.let { error ->
            Card(
                modifier = Modifier.fillMaxWidth(),
                colors = CardDefaults.cardColors(
                    containerColor = MaterialTheme.colorScheme.errorContainer
                )
            ) {
                Row(
                    modifier = Modifier.padding(16.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Icon(
                        imageVector = Icons.Default.Error,
                        contentDescription = null,
                        tint = MaterialTheme.colorScheme.error
                    )
                    Spacer(modifier = Modifier.width(8.dp))
                    Text(
                        text = error,
                        color = MaterialTheme.colorScheme.onErrorContainer,
                        style = MaterialTheme.typography.bodyMedium
                    )
                }
            }
            Spacer(modifier = Modifier.height(16.dp))
        }
        
        Spacer(modifier = Modifier.height(32.dp))
        
        // Instructions card
        InstructionsCard()
        
        Spacer(modifier = Modifier.height(32.dp))
    }
    
    // Render feedback dialogs
    userFeedbackManager.FeedbackDialogRenderer()
}

/**
 * Process text using the integrated error handling system
 */
private fun processTextWithIntegratedSystem(
    text: String,
    systemIntegrator: ErrorHandlingSystemIntegrator,
    lifecycleScope: androidx.lifecycle.LifecycleCoroutineScope,
    onLoading: (Boolean) -> Unit,
    onSuccess: (ParseResult) -> Unit,
    onError: (String) -> Unit,
    onUserInteraction: (UserInteraction) -> Unit,
    onProgress: (String) -> Unit
) {
    onLoading(true)
    
    lifecycleScope.launch {
        systemIntegrator.processTextEndToEnd(
            text = text,
            lifecycleScope = lifecycleScope,
            onSuccess = { result ->
                onSuccess(result)
                onLoading(false)
            },
            onError = { error ->
                onError(error)
                onLoading(false)
            },
            onUserInteractionRequired = { interaction ->
                onUserInteraction(interaction)
                onLoading(false)
            },
            onProgressUpdate = { progress ->
                onProgress(progress)
            }
        )
    }
}

/**
 * Create calendar event using the integrated system
 */
private fun createCalendarEventWithIntegratedSystem(
    result: ParseResult,
    systemIntegrator: ErrorHandlingSystemIntegrator,
    lifecycleScope: androidx.lifecycle.LifecycleCoroutineScope,
    onSuccess: () -> Unit,
    onError: (String) -> Unit,
    onAlternatives: (List<String>) -> Unit
) {
    lifecycleScope.launch {
        systemIntegrator.createCalendarEventEndToEnd(
            result = result,
            lifecycleScope = lifecycleScope,
            onSuccess = onSuccess,
            onError = onError,
            onAlternativeRequired = onAlternatives
        )
    }
}

/**
 * User interaction card for handling various user interactions
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun UserInteractionCard(
    interaction: UserInteraction,
    onDismiss: () -> Unit
) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(
            containerColor = when (interaction.type) {
                UserInteraction.Type.CONFIDENCE_WARNING -> MaterialTheme.colorScheme.tertiaryContainer
                UserInteraction.Type.FALLBACK_CONFIRMATION -> MaterialTheme.colorScheme.secondaryContainer
                else -> MaterialTheme.colorScheme.surfaceVariant
            }
        )
    ) {
        Column(
            modifier = Modifier.padding(16.dp)
        ) {
            Text(
                text = interaction.title,
                style = MaterialTheme.typography.titleMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
            
            Spacer(modifier = Modifier.height(8.dp))
            
            Text(
                text = interaction.message,
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
            
            Spacer(modifier = Modifier.height(16.dp))
            
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                OutlinedButton(
                    onClick = {
                        interaction.onCancel()
                        onDismiss()
                    },
                    modifier = Modifier.weight(1f)
                ) {
                    Text("Cancel")
                }
                
                Button(
                    onClick = {
                        interaction.onProceed()
                        onDismiss()
                    },
                    modifier = Modifier.weight(1f)
                ) {
                    Text("Proceed")
                }
            }
        }
    }
}

/**
 * Enhanced result card with confidence indicators
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun EnhancedResultCard(
    result: ParseResult,
    onCreateEvent: () -> Unit,
    onRetry: () -> Unit
) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        elevation = CardDefaults.cardElevation(defaultElevation = 4.dp)
    ) {
        Column(
            modifier = Modifier.padding(16.dp)
        ) {
            Text(
                text = "Parsed Event Details",
                style = MaterialTheme.typography.titleMedium
            )
            
            Spacer(modifier = Modifier.height(8.dp))
            
            // Confidence indicator
            val confidencePercentage = (result.confidenceScore * 100).toInt()
            val confidenceColor = when {
                result.confidenceScore >= 0.7 -> MaterialTheme.colorScheme.primary
                result.confidenceScore >= 0.3 -> MaterialTheme.colorScheme.tertiary
                else -> MaterialTheme.colorScheme.error
            }
            
            Row(
                verticalAlignment = Alignment.CenterVertically
            ) {
                Icon(
                    imageVector = when {
                        result.confidenceScore >= 0.7 -> Icons.Default.CheckCircle
                        result.confidenceScore >= 0.3 -> Icons.Default.Warning
                        else -> Icons.Default.Error
                    },
                    contentDescription = null,
                    tint = confidenceColor,
                    modifier = Modifier.size(16.dp)
                )
                Spacer(modifier = Modifier.width(8.dp))
                Text(
                    text = "Confidence: $confidencePercentage%",
                    color = confidenceColor,
                    style = MaterialTheme.typography.bodyMedium
                )
            }
            
            Spacer(modifier = Modifier.height(12.dp))
            
            // Event details
            result.title?.let {
                Text("Title: $it", style = MaterialTheme.typography.bodyMedium)
            }
            result.startDateTime?.let {
                Text("Start: ${formatDateTime(it)}", style = MaterialTheme.typography.bodyMedium)
            }
            result.endDateTime?.let {
                Text("End: ${formatDateTime(it)}", style = MaterialTheme.typography.bodyMedium)
            }
            result.location?.let {
                Text("Location: $it", style = MaterialTheme.typography.bodyMedium)
            }
            
            // Show fallback information if applicable
            if (result.fallbackApplied) {
                Spacer(modifier = Modifier.height(8.dp))
                Text(
                    text = "ℹ️ ${result.fallbackReason}",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.tertiary
                )
            }
            
            Spacer(modifier = Modifier.height(16.dp))
            
            // Action buttons
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                if (result.confidenceScore < 0.5) {
                    OutlinedButton(
                        onClick = onRetry,
                        modifier = Modifier.weight(1f)
                    ) {
                        Text("Improve Text")
                    }
                }
                
                Button(
                    onClick = onCreateEvent,
                    modifier = Modifier.weight(1f)
                ) {
                    Icon(Icons.Default.Event, contentDescription = null)
                    Spacer(modifier = Modifier.width(8.dp))
                    Text("Create Event")
                }
            }
        }
    }
}

/**
 * Instructions card component
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun InstructionsCard() {
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
                        "3. Review the results and tap 'Create Event'\n\n" +
                        "The app includes intelligent error handling:\n" +
                        "• Automatic retries for network issues\n" +
                        "• Offline event creation when needed\n" +
                        "• Smart fallbacks for unclear text\n" +
                        "• Multiple calendar app support",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onPrimaryContainer
            )
        }
    }
}

// Helper functions
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

private fun hasDefaultTimes(result: ParseResult, originalText: String): Boolean {
    // Check if we applied default 9:00 AM time
    val hasWeekday = listOf("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")
        .any { originalText.lowercase().contains(it) }
    
    val hasDefaultTime = result.startDateTime?.contains("09:00:00") == true
    
    return hasWeekday && hasDefaultTime && !originalText.contains("9:00") && !originalText.contains("9am")
}