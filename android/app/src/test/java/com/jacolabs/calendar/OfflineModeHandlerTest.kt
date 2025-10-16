package com.jacolabs.calendar

import android.content.Context
import android.content.SharedPreferences
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith
import org.mockito.Mock
import org.mockito.Mockito.*
import org.mockito.junit.MockitoJUnitRunner
import kotlinx.coroutines.runBlocking
import java.util.*
import org.junit.Assert.*

/**
 * Unit tests for OfflineModeHandler functionality
 */
@RunWith(MockitoJUnitRunner::class)
class OfflineModeHandlerTest {
    
    @Mock
    private lateinit var mockContext: Context
    
    @Mock
    private lateinit var mockSharedPrefs: SharedPreferences
    
    @Mock
    private lateinit var mockEditor: SharedPreferences.Editor
    
    private lateinit var offlineModeHandler: OfflineModeHandler
    
    @Before
    fun setup() {
        // Setup SharedPreferences mocking
        `when`(mockContext.getSharedPreferences(anyString(), anyInt())).thenReturn(mockSharedPrefs)
        `when`(mockSharedPrefs.edit()).thenReturn(mockEditor)
        `when`(mockEditor.putString(anyString(), anyString())).thenReturn(mockEditor)
        `when`(mockEditor.putBoolean(anyString(), anyBoolean())).thenReturn(mockEditor)
        `when`(mockEditor.putInt(anyString(), anyInt())).thenReturn(mockEditor)
        `when`(mockEditor.putLong(anyString(), anyLong())).thenReturn(mockEditor)
        `when`(mockEditor.remove(anyString())).thenReturn(mockEditor)
        
        // Default SharedPreferences values
        `when`(mockSharedPrefs.getBoolean("offline_mode_enabled", true)).thenReturn(true)
        `when`(mockSharedPrefs.getString("cached_requests", "[]")).thenReturn("[]")
        `when`(mockSharedPrefs.getInt("offline_events_created", 0)).thenReturn(0)
        `when`(mockSharedPrefs.getLong("last_connectivity_check", 0)).thenReturn(0L)
        
        offlineModeHandler = OfflineModeHandler(mockContext)
    }
    
    @Test
    fun testCreateOfflineEvent_BasicFunctionality() = runBlocking {
        // Given
        val inputText = "Meeting with John tomorrow at 2 PM"
        
        // When
        val result = offlineModeHandler.createOfflineEvent(inputText)
        
        // Then
        assertNotNull("Result should not be null", result)
        assertNotNull("Title should not be null", result.title)
        assertNotNull("Start date time should not be null", result.startDateTime)
        assertNotNull("End date time should not be null", result.endDateTime)
        assertTrue("Should be marked as fallback applied", result.fallbackApplied)
        assertEquals("Should have offline fallback reason", 
            "Created offline - no network available", result.fallbackReason)
        assertEquals("Should have low confidence score", 0.15, result.confidenceScore, 0.01)
        assertTrue("Description should contain original text", 
            result.description?.contains(inputText) == true)
    }
    
    @Test
    fun testCreateOfflineEvent_EmptyText() = runBlocking {
        // Given
        val inputText = ""
        
        // When
        val result = offlineModeHandler.createOfflineEvent(inputText)
        
        // Then
        assertNotNull("Result should not be null", result)
        assertEquals("Should have default title", "Offline Event", result.title)
        assertTrue("Should be marked as fallback applied", result.fallbackApplied)
    }
    
    @Test
    fun testCreateOfflineEvent_LongText() = runBlocking {
        // Given
        val inputText = "This is a very long text that contains a lot of information about a meeting that should be scheduled for next week with multiple participants and various agenda items that need to be discussed in detail"
        
        // When
        val result = offlineModeHandler.createOfflineEvent(inputText)
        
        // Then
        assertNotNull("Result should not be null", result)
        assertNotNull("Title should not be null", result.title)
        assertTrue("Title should be truncated appropriately", 
            result.title!!.length <= 60)
        assertTrue("Should be marked as fallback applied", result.fallbackApplied)
    }
    
    @Test
    fun testCacheFailedRequest_BasicFunctionality() {
        // Given
        val request = OfflineModeHandler.CachedRequest(
            text = "Test meeting",
            timestamp = System.currentTimeMillis(),
            timezone = "UTC",
            locale = "en_US"
        )
        
        // When
        offlineModeHandler.cacheFailedRequest(request)
        
        // Then
        verify(mockEditor).putString(eq("cached_requests"), anyString())
        verify(mockEditor).apply()
    }
    
    @Test
    fun testCacheFailedRequest_ConvenienceMethod() {
        // Given
        val text = "Test meeting"
        val timezone = "UTC"
        val locale = "en_US"
        val now = Date()
        
        // When
        offlineModeHandler.cacheFailedRequest(text, timezone, locale, now)
        
        // Then
        verify(mockEditor).putString(eq("cached_requests"), anyString())
        verify(mockEditor).apply()
    }
    
    @Test
    fun testOfflineModeEnabled_DefaultValue() {
        // When
        val isEnabled = offlineModeHandler.isOfflineModeEnabled()
        
        // Then
        assertTrue("Offline mode should be enabled by default", isEnabled)
    }
    
    @Test
    fun testSetOfflineModeEnabled() {
        // When
        offlineModeHandler.setOfflineModeEnabled(false)
        
        // Then
        verify(mockEditor).putBoolean("offline_mode_enabled", false)
        verify(mockEditor).apply()
    }
    
    @Test
    fun testGetOfflineStatusMessage_OfflineModeDisabled() {
        // Given
        `when`(mockSharedPrefs.getBoolean("offline_mode_enabled", true)).thenReturn(false)
        
        // When
        val message = offlineModeHandler.getOfflineStatusMessage()
        
        // Then
        assertTrue("Message should indicate offline mode is disabled", 
            message.contains("Offline mode is disabled"))
    }
    
    @Test
    fun testGetOfflineStats() {
        // Given
        `when`(mockSharedPrefs.getInt("offline_events_created", 0)).thenReturn(5)
        `when`(mockSharedPrefs.getString("cached_requests", "[]")).thenReturn("[]")
        `when`(mockSharedPrefs.getLong("last_connectivity_check", 0)).thenReturn(System.currentTimeMillis())
        
        // When
        val stats = offlineModeHandler.getOfflineStats()
        
        // Then
        assertEquals("Should have correct offline events count", 5, stats.totalOfflineEventsCreated)
        assertEquals("Should have correct cached requests count", 0, stats.cachedRequestsCount)
        assertTrue("Last connectivity check should be recent", 
            stats.lastConnectivityCheck > 0)
    }
    
    @Test
    fun testClearCachedRequests() {
        // When
        offlineModeHandler.clearCachedRequests()
        
        // Then
        verify(mockEditor).remove("cached_requests")
        verify(mockEditor).apply()
    }
    
    @Test
    fun testClearOfflineStats() {
        // When
        offlineModeHandler.clearOfflineStats()
        
        // Then
        verify(mockEditor).remove("offline_events_created")
        verify(mockEditor).remove("last_connectivity_check")
        verify(mockEditor).apply()
    }
    
    @Test
    fun testShouldCheckConnectivity_InitialState() {
        // Given - last check was 0 (never checked)
        `when`(mockSharedPrefs.getLong("last_connectivity_check", 0)).thenReturn(0L)
        
        // When
        val shouldCheck = offlineModeHandler.shouldCheckConnectivity()
        
        // Then
        assertTrue("Should check connectivity on first run", shouldCheck)
    }
    
    @Test
    fun testShouldCheckConnectivity_RecentCheck() {
        // Given - last check was very recent
        val recentTime = System.currentTimeMillis() - 10000 // 10 seconds ago
        `when`(mockSharedPrefs.getLong("last_connectivity_check", 0)).thenReturn(recentTime)
        
        // When
        val shouldCheck = offlineModeHandler.shouldCheckConnectivity()
        
        // Then
        assertFalse("Should not check connectivity if recently checked", shouldCheck)
    }
    
    @Test
    fun testShouldCheckConnectivity_OldCheck() {
        // Given - last check was long ago
        val oldTime = System.currentTimeMillis() - 60000 // 60 seconds ago
        `when`(mockSharedPrefs.getLong("last_connectivity_check", 0)).thenReturn(oldTime)
        
        // When
        val shouldCheck = offlineModeHandler.shouldCheckConnectivity()
        
        // Then
        assertTrue("Should check connectivity if last check was long ago", shouldCheck)
    }
    
    @Test
    fun testRetryPendingRequests_EmptyCache() = runBlocking {
        // Given - empty cache
        `when`(mockSharedPrefs.getString("cached_requests", "[]")).thenReturn("[]")
        
        // When
        val results = offlineModeHandler.retryPendingRequests()
        
        // Then
        assertTrue("Should return empty list for empty cache", results.isEmpty())
    }
    
    @Test
    fun testPerformAutomaticRetry_RecentCheck() = runBlocking {
        // Given - recent connectivity check
        val recentTime = System.currentTimeMillis() - 10000
        `when`(mockSharedPrefs.getLong("last_connectivity_check", 0)).thenReturn(recentTime)
        
        // When
        val retryCount = offlineModeHandler.performAutomaticRetry()
        
        // Then
        assertEquals("Should not retry if recently checked", 0, retryCount)
    }
    
    @Test
    fun testExtractBasicTitle_ShortText() {
        // This tests the private method indirectly through createOfflineEvent
        runBlocking {
            // Given
            val inputText = "Short meeting"
            
            // When
            val result = offlineModeHandler.createOfflineEvent(inputText)
            
            // Then
            assertEquals("Should use full text as title", "Short meeting", result.title)
        }
    }
    
    @Test
    fun testExtractBasicTitle_LongText() {
        runBlocking {
            // Given
            val inputText = "This is a very long meeting description that should be truncated"
            
            // When
            val result = offlineModeHandler.createOfflineEvent(inputText)
            
            // Then
            assertNotNull("Title should not be null", result.title)
            assertTrue("Title should be truncated", result.title!!.length <= 60)
            if (result.title!!.length == 50) { // If truncated
                assertTrue("Truncated title should end with ...", result.title!!.endsWith("..."))
            }
        }
    }
}