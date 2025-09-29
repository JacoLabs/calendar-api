package com.jacolabs.calendar

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.ClipboardManager
import android.content.Context
import android.content.Intent
import android.os.Build
import android.os.IBinder
import androidx.core.app.NotificationCompat
import kotlinx.coroutines.*
import java.util.*

/**
 * Background service that monitors clipboard for potential calendar events.
 * Shows notifications when calendar-worthy text is copied.
 */
class ClipboardMonitorService : Service() {
    
    companion object {
        private const val NOTIFICATION_ID = 1001
        private const val CHANNEL_ID = "clipboard_monitor"
        private const val CHANNEL_NAME = "Calendar Event Detection"
        
        // Minimum confidence threshold for showing notifications
        private const val MIN_CONFIDENCE_THRESHOLD = 0.4
        
        // Minimum time between notifications (to avoid spam)
        private const val MIN_NOTIFICATION_INTERVAL_MS = 5000L
    }
    
    private lateinit var clipboardManager: ClipboardManager
    private lateinit var notificationManager: NotificationManager
    private lateinit var apiService: ApiService
    
    private var serviceScope = CoroutineScope(Dispatchers.Main + SupervisorJob())
    private var lastNotificationTime = 0L
    private var lastProcessedText = ""
    
    private val clipboardListener = ClipboardManager.OnPrimaryClipChangedListener {
        handleClipboardChange()
    }
    
    override fun onCreate() {
        super.onCreate()
        
        clipboardManager = getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
        notificationManager = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        apiService = ApiService()
        
        createNotificationChannel()
        startForegroundService()
        
        // Start monitoring clipboard
        clipboardManager.addPrimaryClipChangedListener(clipboardListener)
    }
    
    override fun onDestroy() {
        super.onDestroy()
        clipboardManager.removePrimaryClipChangedListener(clipboardListener)
        serviceScope.cancel()
    }
    
    override fun onBind(intent: Intent?): IBinder? = null
    
    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                CHANNEL_ID,
                CHANNEL_NAME,
                NotificationManager.IMPORTANCE_LOW
            ).apply {
                description = "Detects calendar events in copied text"
                setShowBadge(false)
            }
            notificationManager.createNotificationChannel(channel)
        }
    }
    
    private fun startForegroundService() {
        val notification = createServiceNotification()
        startForeground(NOTIFICATION_ID, notification)
    }
    
    private fun createServiceNotification(): Notification {
        val intent = Intent(this, MainActivity::class.java)
        val pendingIntent = PendingIntent.getActivity(
            this, 0, intent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )
        
        return NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle("Calendar Event Detection")
            .setContentText("Monitoring clipboard for calendar events")
            .setSmallIcon(R.drawable.ic_launcher_foreground)
            .setContentIntent(pendingIntent)
            .setOngoing(true)
            .setSilent(true)
            .setPriority(NotificationCompat.PRIORITY_LOW)
            .build()
    }
    
    private fun handleClipboardChange() {
        val clip = clipboardManager.primaryClip
        if (clip != null && clip.itemCount > 0) {
            val clipText = clip.getItemAt(0).text?.toString()
            
            if (!clipText.isNullOrBlank() && clipText != lastProcessedText) {
                lastProcessedText = clipText
                
                // Avoid processing very short text or common clipboard content
                if (clipText.length < 10 || isCommonClipboardContent(clipText)) {
                    return
                }
                
                // Process the text asynchronously
                serviceScope.launch {
                    processClipboardText(clipText)
                }
            }
        }
    }
    
    private fun isCommonClipboardContent(text: String): Boolean {
        val lowerText = text.lowercase()
        
        // Skip common non-event content
        val skipPatterns = listOf(
            "http", "www.", "@", "password", "username",
            "copy", "paste", "cut", "select all"
        )
        
        return skipPatterns.any { lowerText.contains(it) } ||
                text.matches(Regex("^\\d+$")) || // Just numbers
                text.matches(Regex("^[a-zA-Z]$")) || // Single letter
                text.length > 500 // Very long text (probably not an event)
    }
    
    private suspend fun processClipboardText(text: String) {
        try {
            // Check if enough time has passed since last notification
            val currentTime = System.currentTimeMillis()
            if (currentTime - lastNotificationTime < MIN_NOTIFICATION_INTERVAL_MS) {
                return
            }
            
            // Call API to analyze the text
            val timezone = TimeZone.getDefault().id
            val locale = Locale.getDefault().toString()
            val now = Date()
            
            val result = apiService.parseText(text, timezone, locale, now)
            
            // Check if the result is worth showing to the user
            if (result.confidenceScore >= MIN_CONFIDENCE_THRESHOLD &&
                (!result.title.isNullOrBlank() || !result.startDateTime.isNullOrBlank())) {
                
                showCalendarEventNotification(text, result)
                lastNotificationTime = currentTime
            }
            
        } catch (e: Exception) {
            // Silently handle errors - don't spam user with error notifications
            // Could log to analytics in production
        }
    }
    
    private fun showCalendarEventNotification(originalText: String, result: ParseResult) {
        val title = "📅 Calendar event detected"
        val content = buildString {
            result.title?.let { append("$it") }
            result.startDateTime?.let { 
                if (isNotEmpty()) append(" • ")
                append(formatDateTime(it))
            }
        }
        
        // Create intent to process the text
        val processIntent = Intent(this, TextProcessorActivity::class.java).apply {
            action = Intent.ACTION_PROCESS_TEXT
            putExtra(Intent.EXTRA_PROCESS_TEXT, originalText)
            flags = Intent.FLAG_ACTIVITY_NEW_TASK
        }
        
        val processPendingIntent = PendingIntent.getActivity(
            this, 
            System.currentTimeMillis().toInt(),
            processIntent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )
        
        // Create dismiss intent
        val dismissIntent = Intent(this, NotificationDismissReceiver::class.java)
        val dismissPendingIntent = PendingIntent.getBroadcast(
            this,
            System.currentTimeMillis().toInt(),
            dismissIntent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )
        
        val notification = NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle(title)
            .setContentText(content)
            .setStyle(NotificationCompat.BigTextStyle().bigText(content))
            .setSmallIcon(R.drawable.ic_launcher_foreground)
            .setAutoCancel(true)
            .setPriority(NotificationCompat.PRIORITY_DEFAULT)
            .addAction(
                R.drawable.ic_launcher_foreground,
                "Create Event",
                processPendingIntent
            )
            .addAction(
                R.drawable.ic_launcher_foreground,
                "Dismiss",
                dismissPendingIntent
            )
            .build()
        
        notificationManager.notify(
            System.currentTimeMillis().toInt(),
            notification
        )
    }
    
    private fun formatDateTime(isoDateTime: String): String {
        return try {
            val inputFormat = java.text.SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ssXXX", Locale.getDefault())
            val outputFormat = java.text.SimpleDateFormat("MMM dd 'at' h:mm a", Locale.getDefault())
            val date = inputFormat.parse(isoDateTime)
            date?.let { outputFormat.format(it) } ?: isoDateTime
        } catch (e: Exception) {
            try {
                val inputFormat = java.text.SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss", Locale.getDefault())
                val outputFormat = java.text.SimpleDateFormat("MMM dd 'at' h:mm a", Locale.getDefault())
                val date = inputFormat.parse(isoDateTime)
                date?.let { outputFormat.format(it) } ?: isoDateTime
            } catch (e2: Exception) {
                "Soon"
            }
        }
    }
}