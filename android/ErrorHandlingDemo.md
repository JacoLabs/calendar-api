# Enhanced ApiService Error Handling Demo

This document demonstrates the enhanced error handling and retry logic implemented in the ApiService.

## Key Enhancements Implemented

### 1. Exponential Backoff Retry Mechanism
- **Configurable max attempts**: Default 3 retries
- **Exponential backoff**: Base delay of 1000ms, doubles with each retry
- **Maximum delay cap**: 30 seconds to prevent excessive waits
- **Server-provided retry-after**: Respects server's retry-after headers

### 2. Comprehensive Error Categorization
The system now categorizes errors into specific types:

- `NETWORK_CONNECTIVITY`: No internet, DNS failures, connection issues
- `REQUEST_TIMEOUT`: Socket timeouts, I/O timeouts
- `SERVER_ERROR`: 5xx HTTP status codes
- `CLIENT_ERROR`: 4xx HTTP status codes (except rate limiting)
- `PARSING_ERROR`: 422 responses, invalid event data
- `VALIDATION_ERROR`: Empty text, text too long, invalid input
- `RATE_LIMIT`: 429 responses with retry-after information
- `UNKNOWN_ERROR`: Unexpected errors

### 3. Structured Error Response Parsing
Each error now includes:
- **Error type**: Categorized error type for programmatic handling
- **Error code**: Specific error identifier
- **User message**: Human-readable error description
- **Suggestion**: Actionable advice for the user
- **Retryable flag**: Whether the operation can be retried
- **Retry after**: Server-suggested retry delay

### 4. Enhanced Network Connectivity Checking
- **System connectivity manager**: Uses Android's ConnectivityManager for accurate network status
- **DNS resolution test**: Fallback test using DNS resolution to 8.8.8.8
- **Android version compatibility**: Handles API differences between Android versions

### 5. Request Timeout Handling with Graceful Degradation
- **Configurable timeouts**: Default 15 seconds for connect, read, and write operations
- **Timeout categorization**: Distinguishes between different types of timeouts
- **Graceful retry**: Automatic retry for timeout errors with exponential backoff

## Error Handling Flow

```
User Input → Validation → Network Check → API Request → Response Handling
     ↓              ↓            ↓             ↓              ↓
Validation     Network      Request      Response      Success/Error
 Errors        Errors       Timeout      Parsing       Processing
     ↓              ↓            ↓             ↓              ↓
Immediate      Retry with   Retry with   Categorize    Return Result
 Failure       Backoff      Backoff      & Handle      or Throw
```

## Configuration Options

The `ErrorHandlingConfig` class allows customization:

```kotlin
data class ErrorHandlingConfig(
    val maxRetryAttempts: Int = 3,           // Maximum retry attempts
    val baseRetryDelayMs: Long = 1000,       // Base delay between retries
    val timeoutSeconds: Long = 15,           // Request timeout
    val enableNetworkCheck: Boolean = true,  // Pre-request network check
    val enableExponentialBackoff: Boolean = true, // Use exponential backoff
    val maxDelayMs: Long = 30000            // Maximum retry delay
)
```

## Example Error Scenarios

### Network Connectivity Error
```
Error Type: NETWORK_CONNECTIVITY
Error Code: NO_NETWORK
User Message: No internet connection. Please check your network settings and try again.
Retryable: true
```

### Rate Limiting Error
```
Error Type: RATE_LIMIT
Error Code: RATE_LIMIT_ERROR
User Message: Too many requests. Please wait 60 seconds before trying again.
Retryable: true
Retry After: 60 seconds
```

### Validation Error
```
Error Type: VALIDATION_ERROR
Error Code: TEXT_TOO_LONG
User Message: Text is too long. Please limit to 10,000 characters.
Retryable: false
```

### Parsing Error
```
Error Type: PARSING_ERROR
Error Code: PARSING_ERROR
User Message: The text does not contain valid event information. Please try rephrasing with clearer date, time, and event details.
Suggestion: Try including specific dates like 'tomorrow at 2 PM' or 'January 15th at 3:30 PM'
Retryable: false
```

## Enhanced ParseResult

The ParseResult now includes error recovery metadata:

```kotlin
data class ParseResult(
    // ... existing fields ...
    val fallbackApplied: Boolean = false,
    val fallbackReason: String? = null,
    val originalText: String? = null,
    val errorRecoveryInfo: ErrorRecoveryInfo? = null
)
```

## Integration with UI

The MainActivity now provides enhanced error messages with:
- **Structured error information**: Uses the ApiError data for better UX
- **Actionable suggestions**: Shows specific guidance based on error type
- **Retry information**: Indicates when users can try again
- **Visual indicators**: Different styling for different error types

## Testing

The implementation includes comprehensive unit tests covering:
- Input validation scenarios
- Error categorization logic
- Retry mechanism behavior
- Configuration validation
- Backward compatibility

## Requirements Satisfied

This implementation satisfies all the requirements from task 1:

✅ **Exponential backoff retry mechanism with configurable max attempts**
✅ **Comprehensive error categorization for different failure types**
✅ **Structured error response parsing with user-friendly message extraction**
✅ **Network connectivity checking before API calls**
✅ **Request timeout handling with graceful degradation**

The enhanced ApiService provides a robust foundation for the error handling system while maintaining backward compatibility with existing code.