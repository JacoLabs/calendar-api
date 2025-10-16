package com.jacolabs.calendar

import android.content.Context
import android.content.SharedPreferences
import org.junit.Before
import org.junit.Test
import org.junit.Assert.*
import org.mockito.Mock
import org.mockito.Mockito.*
import org.mockito.MockitoAnnotations

/**
 * Unit tests for ErrorHandlingConfig and ErrorHandlingConfigManager
 * Tests configuration validation, persistence, and requirement compliance
 */
class ErrorHandlingConfigTest {

    @Mock
    private lateinit var mockContext: Context
    
    @Mock
    private lateinit var mockSharedPrefs: SharedPreferences
    
    @Mock
    private lateinit var mockEditor: SharedPreferences.Editor

    @Before
    fun setUp() {
        MockitoAnnotations.openMocks(this)
        
        `when`(mockContext.getSharedPreferences(anyString(), anyInt())).thenReturn(mockSharedPrefs)
        `when`(mockSharedPrefs.edit()).thenReturn(mockEditor)
        `when`(mockEditor.putInt(anyString(), anyInt())).thenReturn(mockEditor)
        `when`(mockEditor.putLong(anyString(), anyLong())).thenReturn(mockEditor)
        `when`(mockEditor.putFloat(anyString(), anyFloat())).thenReturn(mockEditor)
        `when`(mockEditor.putBoolean(anyString(), anyBoolean())).thenReturn(mockEditor)
        `when`(mockEditor.putString(anyString(), anyString())).thenReturn(mockEditor)
    }

    @Test
    fun testDefaultConfiguration() {
        val config = ErrorHandlingConfig()
        
        // Test requirement 6.1: Max retry attempts should be 2
        assertEquals(2, config.maxRetryAttempts)
        assertEquals(1000L, config.baseRetryDelayMs)
        assertEquals(2.0, config.exponentialBackoffMultiplier, 0.01)
        
        // Test requirement 6.2: Alternative calendar apps should be enabled
        assertTrue(config.enableAlternativeCalendarApps)
        assertEquals(3, config.maxCalendarLaunchAttempts)
        
        // Test requirement 10.1, 10.2: Error handling architecture should be enabled
        assertTrue(config.enableComprehensiveErrorCatching)
        assertTrue(config.enableErrorCategorization)
        assertTrue(config.enableCrashPrevention)
        assertTrue(config.enableConsistentUIState)
    }

    @Test
    fun testProductionConfiguration() {
        val config = ErrorHandlingConfig.forProduction()
        
        // Production should have conservative retry settings
        assertEquals(2, config.maxRetryAttempts)
        assertEquals(2000L, config.baseRetryDelayMs)
        assertEquals(0.4, config.confidenceThreshold, 0.01)
        
        // Production should have shorter timeouts
        assertEquals(10000L, config.processingTimeoutMs)
        assertEquals(8000L, config.apiTimeoutMs)
        
        // Production should enable privacy-compliant logging
        assertTrue(config.enablePrivacyCompliantLogging)
        assertEquals(ErrorHandlingConfig.LogLevel.WARN, config.logLevel)
    }

    @Test
    fun testDevelopmentConfiguration() {
        val config = ErrorHandlingConfig.forDevelopment()
        
        // Development should have more aggressive retry settings
        assertEquals(5, config.maxRetryAttempts)
        assertEquals(500L, config.baseRetryDelayMs)
        assertEquals(0.2, config.confidenceThreshold, 0.01)
        
        // Development should have extended timeouts
        assertEquals(30000L, config.processingTimeoutMs)
        assertEquals(20000L, config.apiTimeoutMs)
        
        // Development should allow detailed logging
        assertFalse(config.enablePrivacyCompliantLogging)
        assertEquals(ErrorHandlingConfig.LogLevel.DEBUG, config.logLevel)
    }

    @Test
    fun testConfigurationValidation() {
        val invalidConfig = ErrorHandlingConfig(
            maxRetryAttempts = -1,
            baseRetryDelayMs = 50L,
            maxRetryDelayMs = 100000L,
            exponentialBackoffMultiplier = 10.0,
            confidenceThreshold = 1.5,
            cacheExpirationHours = 200,
            maxCachedRequests = 2000,
            maxCalendarLaunchAttempts = 20,
            processingTimeoutMs = 100000L,
            apiTimeoutMs = 50000L
        )
        
        val validatedConfig = invalidConfig.validate()
        
        // Check that invalid values are corrected
        assertEquals(0, validatedConfig.maxRetryAttempts) // Coerced to minimum
        assertEquals(100L, validatedConfig.baseRetryDelayMs) // Coerced to minimum
        assertEquals(60000L, validatedConfig.maxRetryDelayMs) // Coerced to maximum
        assertEquals(5.0, validatedConfig.exponentialBackoffMultiplier, 0.01) // Coerced to maximum
        assertEquals(1.0, validatedConfig.confidenceThreshold, 0.01) // Coerced to maximum
        assertEquals(168, validatedConfig.cacheExpirationHours) // Coerced to maximum (1 week)
        assertEquals(1000, validatedConfig.maxCachedRequests) // Coerced to maximum
        assertEquals(10, validatedConfig.maxCalendarLaunchAttempts) // Coerced to maximum
        assertEquals(60000L, validatedConfig.processingTimeoutMs) // Coerced to maximum
        assertEquals(30000L, validatedConfig.apiTimeoutMs) // Coerced to maximum
    }

    @Test
    fun testRetryDelayCalculation() {
        val config = ErrorHandlingConfig(
            baseRetryDelayMs = 1000L,
            maxRetryDelayMs = 10000L,
            exponentialBackoffMultiplier = 2.0
        )
        
        // Test exponential backoff calculation
        assertEquals(1000L, config.calculateRetryDelay(0))
        assertEquals(1000L, config.calculateRetryDelay(1))
        assertEquals(2000L, config.calculateRetryDelay(2))
        assertEquals(4000L, config.calculateRetryDelay(3))
        assertEquals(8000L, config.calculateRetryDelay(4))
        assertEquals(10000L, config.calculateRetryDelay(5)) // Should be capped at max
    }

    @Test
    fun testRequirementComplianceMethods() {
        val config = ErrorHandlingConfig()
        
        // Test requirement 6.1 compliance
        assertTrue(config.shouldRetry(0))
        assertTrue(config.shouldRetry(1))
        assertFalse(config.shouldRetry(2)) // Should not retry after max attempts
        
        // Test requirement 6.2 compliance
        assertTrue(config.shouldTryAlternativeCalendarApps())
        
        // Test requirement 10.1, 10.2 compliance
        assertTrue(config.shouldUseComprehensiveErrorCatching())
        assertTrue(config.shouldCategorizeErrors())
        assertTrue(config.shouldPreventCrashes())
        assertTrue(config.shouldMaintainConsistentUIState())
    }

    @Test
    fun testConfigurationPersistence() {
        val config = ErrorHandlingConfig(
            maxRetryAttempts = 3,
            confidenceThreshold = 0.5,
            enableOfflineMode = false
        )
        
        config.save(mockContext)
        
        // Verify that save method calls SharedPreferences correctly
        verify(mockEditor).putInt("max_retry_attempts", 3)
        verify(mockEditor).putFloat("confidence_threshold", 0.5f)
        verify(mockEditor).putBoolean("enable_offline_mode", false)
        verify(mockEditor).apply()
    }

    @Test
    fun testConfigurationLoading() {
        // Mock SharedPreferences to return specific values
        `when`(mockSharedPrefs.getInt("max_retry_attempts", 2)).thenReturn(4)
        `when`(mockSharedPrefs.getFloat("confidence_threshold", 0.3f)).thenReturn(0.6f)
        `when`(mockSharedPrefs.getBoolean("enable_offline_mode", true)).thenReturn(false)
        `when`(mockSharedPrefs.getString("log_level", "INFO")).thenReturn("DEBUG")
        
        val config = ErrorHandlingConfig.load(mockContext)
        
        assertEquals(4, config.maxRetryAttempts)
        assertEquals(0.6, config.confidenceThreshold, 0.01)
        assertFalse(config.enableOfflineMode)
        assertEquals(ErrorHandlingConfig.LogLevel.DEBUG, config.logLevel)
    }

    @Test
    fun testConfigManager() {
        val configManager = ErrorHandlingConfigManager(mockContext)
        
        // Test configuration updates
        val newConfig = ErrorHandlingConfig(maxRetryAttempts = 5)
        configManager.updateConfig(newConfig)
        
        assertEquals(5, configManager.getConfig().maxRetryAttempts)
        
        // Test specific update methods
        configManager.updateRetrySettings(3, 2000L, 20000L)
        assertEquals(3, configManager.getConfig().maxRetryAttempts)
        assertEquals(2000L, configManager.getConfig().baseRetryDelayMs)
        assertEquals(20000L, configManager.getConfig().maxRetryDelayMs)
        
        configManager.updateConfidenceThreshold(0.7)
        assertEquals(0.7, configManager.getConfig().confidenceThreshold, 0.01)
    }

    @Test
    fun testConfigManagerListeners() {
        val configManager = ErrorHandlingConfigManager(mockContext)
        var listenerCalled = false
        var receivedConfig: ErrorHandlingConfig? = null
        
        val listener: (ErrorHandlingConfig) -> Unit = { config ->
            listenerCalled = true
            receivedConfig = config
        }
        
        configManager.addConfigChangeListener(listener)
        
        val newConfig = ErrorHandlingConfig(maxRetryAttempts = 7)
        configManager.updateConfig(newConfig)
        
        assertTrue(listenerCalled)
        assertEquals(7, receivedConfig?.maxRetryAttempts)
        
        // Test listener removal
        configManager.removeConfigChangeListener(listener)
        listenerCalled = false
        
        configManager.updateConfig(ErrorHandlingConfig(maxRetryAttempts = 8))
        assertFalse(listenerCalled) // Listener should not be called after removal
    }
}