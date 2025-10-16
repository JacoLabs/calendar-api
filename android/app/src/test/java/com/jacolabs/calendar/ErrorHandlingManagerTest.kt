package com.jacolabs.calendar

import android.content.Context
import android.content.SharedPreferences
import kotlinx.coroutines.runBlocking
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith
import org.mockito.Mock
import org.mockito.Mockito.*
import org.mockito.junit.MockitoJUnitRunner
import kotlin.test.assertEquals
import kotlin.test.assertNotNull
import kotlin.test.assertTrue

@RunWith(MockitoJUnitRunner::class)
class ErrorHandlingManagerTest {
    
    @Mock
    private lateinit var mockContext: Context
    
    @Mock
    private lateinit var mockSharedPrefs: SharedPreferences
    
    @Mock
    private lateinit var mockEditor: SharedPreferences.Editor
    
    private lateinit var errorHandlingManager: ErrorHandlingManager
    private lateinit var configManager: ErrorHandlingConfigManager
    
    @Before
    fun setup() {
        // Mock SharedPreferences behavior
        `when`(mockContext.getSharedPreferences(anyString(), anyInt())).thenReturn(mockSharedPrefs)
        `when`(mockSharedPrefs.edit()).thenReturn(mockEditor)
        `when`(mockEditor.putString(anyString(), anyString())).thenReturn(mockEditor)
        `when`(mockEditor.putInt(anyString(), anyInt())).thenReturn(mockEditor)
        `when`(mockEditor.putLong(anyString(), anyLong())).thenReturn(mockEditor)
        `when`(mockEditor.putFloat(anyString(), anyFloat())).thenReturn(mockEditor)
        `when`(mockEditor.putBoolean(anyString(), anyBoolean())).thenReturn(mockEditor)
        
        // Setup default configuration values
        `when`(mockSharedPrefs.getInt(eq("max_retry_attempts"), anyInt())).thenReturn(3)
        `when`(mockSharedPrefs.getLong(eq("base_retry_delay_ms"), anyLong())).thenReturn(1000L)
        `when`(mockSharedPrefs.getLong(eq("max_retry_delay_ms"), anyLong())).thenReturn(30000L)
        `when`(mockSharedPrefs.getFloat(eq("confidence_threshold"), anyFloat())).thenReturn(0.3f)
        `when`(mockSharedPrefs.getBoolean(eq("enable_offline_mode"), anyBoolean())).thenReturn(true)
        `when`(mockSharedPrefs.getBoolean(eq("enable_fallback_creation"), anyBoolean())).thenReturn(true)
        `when`(mockSharedPrefs.getBoolean(eq("enable_analytics_collection"), anyBoolean())).thenReturn(true)
        `when`(mockSharedPrefs.getString(eq("log_level"), anyString())).thenReturn("INFO")
        `when`(mockSharedPrefs.getString(eq("error_analytics"), anyString())).thenReturn("[]")
        `when`(mockSharedPrefs.getString(eq("cached_requests"), anyString())).thenReturn("[]")
        
        configManager = ErrorHandlingConfigManager(mockContext)
        errorHandlingManager = ErrorHandlingManager(mockContext, configManager)
    }
    
    @Test
    fun testErrorCategorization() {
        // Test API exception categorization
        val apiError = ApiService.ApiError(
            type = ApiService.ErrorType.NETWORK_CONNECTIVITY,
            code = "NETWORK_ERROR",
            message = "Network error",
            userMessage = "Network error occurred"
        )
        val apiException = ApiException(apiError)
        
        val categorizedType = errorHandlingManager.categorizeError(apiException)
        assertEquals(ErrorHandlingManager.ErrorType.NETWORK_ERROR, categorizedType)
    }
    
    @Test
    fun testNetworkErrorHandling() = runBlocking {
        val errorContext = ErrorHandlingManager.ErrorContext(
            errorType = ErrorHandlingManager.ErrorType.NETWORK_ERROR,
            originalText = "Meeting tomorrow at 2pm",
            retryCount = 0,
            networkAvailable = false
        )
        
        val result = errorHandlingManager.handleError(errorContext)
        
        assertTrue(result.success)
        assertEquals(ErrorHandlingManager.RecoveryStrategy.OFFLINE_MODE, result.recoveryStrategy)
        assertNotNull(result.recoveredResult)
        assertTrue(result.recoveredResult!!.fallbackApplied)
    }
    
    @Test
    fun testLowConfidenceHandling() = runBlocking {
        val parseResult = ParseResult(
            title = "Meeting",
            startDateTime = "2024-01-15T14:00:00Z",
            endDateTime = "2024-01-15T15:00:00Z",
            location = null,
            description = null,
            confidenceScore = 0.2, // Low confidence
            allDay = false,
            timezone = "UTC"
        )
        
        val result = errorHandlingManager.handleLowConfidence(
            result = parseResult,
            originalText = "Meeting tomorrow",
            userInteractionAllowed = true
        )
        
        assertEquals(ErrorHandlingManager.RecoveryStrategy.USER_CONFIRMATION_REQUIRED, result.recoveryStrategy)
        assertEquals(ErrorHandlingManager.UserAction.CONFIRM_LOW_CONFIDENCE_RESULT, result.actionRequired)
    }
    
    @Test
    fun testParsingFailureHandling() = runBlocking {
        val result = errorHandlingManager.handleParsingFailure(
            originalText = "Some unclear text"
        )
        
        assertTrue(result.success)
        assertEquals(ErrorHandlingManager.RecoveryStrategy.FALLBACK_EVENT_CREATION, result.recoveryStrategy)
        assertNotNull(result.recoveredResult)
        assertEquals("Some unclear text", result.recoveredResult!!.originalText)
    }
    
    @Test
    fun testRetryDelayCalculation() {
        val config = ErrorHandlingConfig(
            baseRetryDelayMs = 1000L,
            maxRetryDelayMs = 10000L
        )
        
        // Test exponential backoff
        val delay0 = errorHandlingManager.calculateRetryDelay(0)
        val delay1 = errorHandlingManager.calculateRetryDelay(1)
        val delay2 = errorHandlingManager.calculateRetryDelay(2)
        
        assertTrue(delay0 >= 1000L)
        assertTrue(delay1 >= delay0)
        assertTrue(delay2 >= delay1)
        assertTrue(delay2 <= 30000L) // Should not exceed max
    }
    
    @Test
    fun testFallbackEventCreation() = runBlocking {
        val result = errorHandlingManager.createFallbackEvent(
            originalText = "Team meeting next Friday at 3pm",
            partialResult = null
        )
        
        assertNotNull(result.title)
        assertTrue(result.title!!.isNotBlank())
        assertNotNull(result.startDateTime)
        assertNotNull(result.endDateTime)
        assertTrue(result.fallbackApplied)
        assertEquals("Team meeting next Friday at 3pm", result.originalText)
        assertTrue(result.confidenceScore < 0.5) // Should be low confidence
    }
    
    @Test
    fun testOfflineEventCreation() = runBlocking {
        val result = errorHandlingManager.createOfflineEvent("Doctor appointment Monday")
        
        assertNotNull(result.title)
        assertTrue(result.title!!.contains("Doctor appointment") || result.title!!.contains("appointment"))
        assertNotNull(result.startDateTime)
        assertNotNull(result.endDateTime)
        assertTrue(result.fallbackApplied)
        assertEquals("Created offline - no network available", result.fallbackReason)
    }
    
    @Test
    fun testConfigurationIntegration() {
        val config = errorHandlingManager.getConfigManager().getConfig()
        
        // Test default configuration values
        assertEquals(3, config.maxRetryAttempts)
        assertEquals(0.3, config.confidenceThreshold, 0.01)
        assertTrue(config.enableOfflineMode)
        assertTrue(config.enableFallbackCreation)
    }
    
    @Test
    fun testConfidenceAcceptability() {
        assertTrue(errorHandlingManager.isConfidenceAcceptable(0.5))
        assertTrue(errorHandlingManager.isConfidenceAcceptable(0.3))
        assertFalse(errorHandlingManager.isConfidenceAcceptable(0.2))
    }
    
    @Test
    fun testErrorStatistics() {
        val stats = errorHandlingManager.getErrorStatistics()
        
        assertNotNull(stats["total_errors"])
        assertNotNull(stats["error_types"])
        assertNotNull(stats["recovery_success_rate"])
        assertNotNull(stats["average_retry_count"])
    }
    
    @Test
    fun testGracefulDegradation() = runBlocking {
        val partialResult = ParseResult(
            title = null, // Missing title
            startDateTime = "2024-01-15T14:00:00Z",
            endDateTime = null, // Missing end time
            location = "Conference Room A",
            description = null,
            confidenceScore = 0.6,
            allDay = false,
            timezone = "UTC"
        )
        
        val result = errorHandlingManager.applyGracefulDegradation(
            originalText = "Important meeting in Conference Room A",
            partialResult = partialResult
        )
        
        assertNotNull(result.title) // Should have generated title
        assertNotNull(result.endDateTime) // Should have generated end time
        assertEquals("Conference Room A", result.location) // Should preserve existing location
        assertTrue(result.fallbackApplied)
    }
}