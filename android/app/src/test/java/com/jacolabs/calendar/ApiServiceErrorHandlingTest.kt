package com.jacolabs.calendar

import kotlinx.coroutines.runBlocking
import org.junit.Test
import org.junit.Assert.*
import java.util.*

/**
 * Unit tests for ApiService error handling and retry logic.
 */
class ApiServiceErrorHandlingTest {

    @Test
    fun testValidationError_EmptyText() {
        val apiService = ApiService()
        
        runBlocking {
            try {
                apiService.parseText(
                    text = "",
                    timezone = "UTC",
                    locale = "en_US",
                    now = Date()
                )
                fail("Expected ApiException for empty text")
            } catch (e: ApiException) {
                assertEquals(ApiService.ErrorType.VALIDATION_ERROR, e.errorType)
                assertEquals("EMPTY_TEXT", e.errorCode)
                assertFalse(e.isRetryable)
                assertTrue(e.userMessage.contains("Please provide text"))
            }
        }
    }

    @Test
    fun testValidationError_TextTooLong() {
        val apiService = ApiService()
        val longText = "a".repeat(10001) // Exceeds 10,000 character limit
        
        runBlocking {
            try {
                apiService.parseText(
                    text = longText,
                    timezone = "UTC",
                    locale = "en_US",
                    now = Date()
                )
                fail("Expected ApiException for text too long")
            } catch (e: ApiException) {
                assertEquals(ApiService.ErrorType.VALIDATION_ERROR, e.errorType)
                assertEquals("TEXT_TOO_LONG", e.errorCode)
                assertFalse(e.isRetryable)
                assertTrue(e.userMessage.contains("too long"))
            }
        }
    }

    @Test
    fun testErrorHandlingConfig_DefaultValues() {
        val config = ApiService.ErrorHandlingConfig()
        
        assertEquals(3, config.maxRetryAttempts)
        assertEquals(1000L, config.baseRetryDelayMs)
        assertEquals(15L, config.timeoutSeconds)
        assertTrue(config.enableNetworkCheck)
        assertTrue(config.enableExponentialBackoff)
        assertEquals(30000L, config.maxDelayMs)
    }

    @Test
    fun testApiError_Structure() {
        val apiError = ApiService.ApiError(
            type = ApiService.ErrorType.NETWORK_CONNECTIVITY,
            code = "NO_NETWORK",
            message = "No internet connection available",
            userMessage = "Please check your network settings",
            suggestion = "Try connecting to WiFi",
            retryable = true,
            retryAfterSeconds = 30
        )
        
        assertEquals(ApiService.ErrorType.NETWORK_CONNECTIVITY, apiError.type)
        assertEquals("NO_NETWORK", apiError.code)
        assertTrue(apiError.retryable)
        assertEquals(30, apiError.retryAfterSeconds)
        assertNotNull(apiError.suggestion)
    }

    @Test
    fun testApiException_BackwardCompatibility() {
        val legacyException = ApiException("Legacy error message")
        
        assertEquals("Legacy error message", legacyException.message)
        assertEquals("Legacy error message", legacyException.userMessage)
        assertEquals(ApiService.ErrorType.UNKNOWN_ERROR, legacyException.errorType)
        assertEquals("LEGACY_ERROR", legacyException.errorCode)
        assertFalse(legacyException.isRetryable)
    }

    @Test
    fun testEnhancedParseResult_ErrorRecoveryInfo() {
        val errorRecoveryInfo = ErrorRecoveryInfo(
            recoveryMethod = "fallback_generation",
            confidenceBeforeRecovery = 0.1,
            dataSourcesUsed = listOf("regex", "heuristics"),
            userInterventionRequired = true
        )
        
        val parseResult = ParseResult(
            title = "Fallback Event",
            startDateTime = null,
            endDateTime = null,
            location = null,
            description = null,
            confidenceScore = 0.3,
            allDay = false,
            timezone = "UTC",
            fallbackApplied = true,
            fallbackReason = "Low confidence parsing",
            originalText = "some unclear text",
            errorRecoveryInfo = errorRecoveryInfo
        )
        
        assertTrue(parseResult.fallbackApplied)
        assertEquals("Low confidence parsing", parseResult.fallbackReason)
        assertEquals("some unclear text", parseResult.originalText)
        assertNotNull(parseResult.errorRecoveryInfo)
        assertEquals("fallback_generation", parseResult.errorRecoveryInfo?.recoveryMethod)
        assertTrue(parseResult.errorRecoveryInfo?.userInterventionRequired == true)
    }
}