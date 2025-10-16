# OfflineModeHandler Implementation

## Overview

The `OfflineModeHandler` provides comprehensive offline functionality for the Android Calendar Event Creator app, ensuring users can create calendar events even when network connectivity is unavailable. This component implements intelligent local text processing, request caching, and automatic retry mechanisms.

## Key Features

### 1. Offline Event Creation
- **Local Text Processing**: Uses the existing `FallbackEventGenerator` for intelligent offline event creation
- **Smart Defaults**: Applies contextual defaults for date/time when parsing fails
- **Minimal Fallback**: Provides basic event creation when sophisticated processing fails
- **Low Confidence Scoring**: Clearly marks offline events with appropriate confidence levels

### 2. Failed Request Caching
- **Persistent Storage**: Caches failed API requests in SharedPreferences with JSON serialization
- **Request Metadata**: Stores complete request context including text, timezone, locale, and timestamp
- **Retry Tracking**: Maintains retry count and request IDs for proper management
- **Expiration Management**: Automatically expires old cached requests (24 hours default)

### 3. Automatic Retry Mechanism
- **Connectivity Detection**: Monitors network availability using multiple detection methods
- **Intelligent Retry**: Automatically retries cached requests when connectivity returns
- **Retry Limits**: Prevents infinite retry loops with configurable maximum attempts (3 default)
- **Batch Processing**: Efficiently processes multiple cached requests in sequence

### 4. Offline Mode Detection
- **Network Monitoring**: Uses ConnectivityManager for accurate network state detection
- **User Notification**: Provides clear status messages about offline mode and cached requests
- **Statistics Tracking**: Maintains usage statistics for offline events and cached requests

### 5. Cache Management
- **Size Limits**: Enforces maximum cache size (50 requests default) with automatic cleanup
- **Expiration Cleanup**: Removes expired requests to prevent storage bloat
- **Manual Management**: Provides methods for clearing cache and statistics

## Architecture Integration

### Integration with ErrorHandlingManager
```kotlin
// Example: ErrorHandlingManager delegates to OfflineModeHandler
when (recoveryStrategy) {
    RecoveryStrategy.OFFLINE_MODE -> {
        offlineModeHandler.createOfflineEvent(text)
    }
    RecoveryStrategy.CACHE_AND_RETRY_LATER -> {
        offlineModeHandler.cacheFailedRequest(text, timezone, locale, now)
        offlineModeHandler.createOfflineEvent(text)
    }
}
```

### Integration with ApiService
```kotlin
// Example: ApiService uses OfflineModeHandler for network failures
try {
    return apiService.parseText(text, timezone, locale, now)
} catch (e: ApiException) {
    if (!offlineModeHandler.isNetworkAvailable()) {
        return offlineModeHandler.createOfflineEvent(text)
    }
    throw e
}
```

## Usage Examples

### Basic Offline Event Creation
```kotlin
val offlineModeHandler = OfflineModeHandler(context)

// Create event when offline
val result = offlineModeHandler.createOfflineEvent("Meeting with John tomorrow at 2 PM")

// Result will have:
// - Intelligent title extraction
// - Smart default date/time
// - Low confidence score (0.15)
// - Fallback reason indicating offline creation
```

### Request Caching and Retry
```kotlin
// Cache a failed request
offlineModeHandler.cacheFailedRequest(
    text = "Team standup Monday 9 AM",
    timezone = "America/New_York", 
    locale = "en_US",
    now = Date()
)

// Later, when connectivity returns
val retriedResults = offlineModeHandler.retryPendingRequests()
// Returns list of successfully retried ParseResults
```

### Automatic Retry Service
```kotlin
// Periodic check and retry (can be called from a service)
CoroutineScope(Dispatchers.IO).launch {
    while (true) {
        val retriedCount = offlineModeHandler.performAutomaticRetry()
        if (retriedCount > 0) {
            // Notify user of successful retries
        }
        delay(30000) // Check every 30 seconds
    }
}
```

### User Status Information
```kotlin
// Get user-friendly status message
val statusMessage = offlineModeHandler.getOfflineStatusMessage()
// Returns: "You're offline. Events will be created locally and may need adjustment later."

// Get detailed statistics
val stats = offlineModeHandler.getOfflineStats()
// Returns: OfflineStats with counts and status information
```

## Configuration

### Default Settings
- **Cache Expiration**: 24 hours
- **Maximum Cached Requests**: 50 requests
- **Cleanup Threshold**: 75 requests (triggers cleanup)
- **Connectivity Check Interval**: 30 seconds
- **Maximum Retry Attempts**: 3 per request
- **Offline Confidence Score**: 0.15

### Customization
The handler uses the existing `ErrorHandlingConfig` system for configuration:
```kotlin
// Enable/disable offline mode
offlineModeHandler.setOfflineModeEnabled(true)

// Check current settings
val isEnabled = offlineModeHandler.isOfflineModeEnabled()
```

## Data Structures

### CachedRequest
```kotlin
data class CachedRequest(
    val text: String,           // Original text to parse
    val timestamp: Long,        // When request was cached
    val timezone: String,       // User's timezone
    val locale: String,         // User's locale
    val retryCount: Int = 0,    // Number of retry attempts
    val id: String,             // Unique request identifier
    val mode: String? = null,   // Optional parsing mode
    val fields: List<String>? = null, // Optional field restrictions
    val originalNow: String? = null   // Original timestamp for context
)
```

### OfflineStats
```kotlin
data class OfflineStats(
    val totalOfflineEventsCreated: Int,  // Total offline events created
    val cachedRequestsCount: Int,        // Current cached requests
    val successfulRetries: Int,          // Successfully retried requests
    val failedRetries: Int,              // Failed retry attempts
    val lastConnectivityCheck: Long,     // Last connectivity check time
    val isCurrentlyOffline: Boolean      // Current offline status
)
```

## Error Handling

### Graceful Degradation
1. **Sophisticated Processing**: Uses `FallbackEventGenerator` for intelligent event creation
2. **Minimal Processing**: Falls back to basic title extraction if sophisticated processing fails
3. **Emergency Fallback**: Creates minimal event with default title if all processing fails

### Exception Safety
- All methods are wrapped in try-catch blocks
- Failures in caching don't prevent offline event creation
- JSON parsing errors fall back to empty cache
- Network detection failures assume offline state

## Testing

### Unit Tests
The implementation includes comprehensive unit tests covering:
- Basic offline event creation functionality
- Request caching and retrieval
- Configuration management
- Error handling scenarios
- Edge cases (empty text, long text, etc.)

### Integration Tests
Example integration with other components:
- `OfflineModeIntegrationExample.kt` shows real-world usage patterns
- Integration with `ErrorHandlingManager` for recovery strategies
- Integration with `ApiService` for network failure handling

## Performance Considerations

### Memory Usage
- Uses SharedPreferences for persistence (lightweight)
- JSON serialization for cached requests (efficient)
- Automatic cleanup prevents unbounded growth

### Processing Speed
- Local text processing is fast (no network calls)
- Batch retry processing for efficiency
- Lazy loading of cached requests

### Storage Impact
- Cached requests are stored as compressed JSON
- Automatic expiration prevents storage bloat
- Configurable limits prevent excessive storage usage

## Requirements Satisfied

This implementation satisfies all requirements from task 6:

✅ **4.1**: Offline event creation using local text processing  
✅ **4.2**: Failed request caching with persistent storage  
✅ **4.3**: Automatic retry mechanism for cached requests when connectivity returns  
✅ **4.4**: Offline mode detection and user notification  
✅ **6.3**: Cache management with expiration and cleanup  

## Future Enhancements

### Potential Improvements
1. **Database Storage**: Replace SharedPreferences with Room database for better performance
2. **Background Sync**: Implement WorkManager for reliable background retry
3. **Conflict Resolution**: Handle conflicts when retrying old cached requests
4. **User Preferences**: Add more granular user control over offline behavior
5. **Analytics**: Enhanced tracking of offline usage patterns

### Integration Opportunities
1. **Push Notifications**: Notify users when cached requests are successfully processed
2. **Sync Status UI**: Visual indicators for sync status in the main UI
3. **Batch Operations**: Allow users to manually trigger batch retry of cached requests