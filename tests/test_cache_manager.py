"""
Unit tests for the CacheManager class.

Tests cover:
- Cache key generation from normalized text
- 24h TTL handling and expiration
- Cache hit/miss tracking and performance metrics
- Cache invalidation and cleanup mechanisms
- Thread safety and concurrent access
- Memory usage estimation
"""

import pytest
import time
import threading
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from services.cache_manager import CacheManager, CacheStats, get_cache_manager, initialize_cache_manager
from models.event_models import ParsedEvent, CacheEntry


class TestCacheManager:
    """Test cases for CacheManager functionality."""
    
    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.cache_manager = CacheManager(ttl_hours=24, max_entries=100, cleanup_interval_minutes=60)
        
        # Create sample parsed event for testing
        self.sample_event = ParsedEvent(
            title="Test Meeting",
            start_datetime=datetime(2025, 10, 15, 14, 0),
            end_datetime=datetime(2025, 10, 15, 15, 0),
            location="Conference Room A",
            description="Test meeting description",
            confidence_score=0.85,
            parsing_path="regex_primary",
            processing_time_ms=150
        )
    
    def test_normalize_text(self):
        """Test text normalization for consistent cache keys."""
        # Test basic normalization
        assert self.cache_manager._normalize_text("  Hello World  ") == "hello world"
        
        # Test multiple whitespace handling
        assert self.cache_manager._normalize_text("Hello    World\n\tTest") == "hello world test"
        
        # Test quote normalization
        assert self.cache_manager._normalize_text('Meeting "tomorrow" at 2pm') == 'meeting "tomorrow" at 2pm'
        assert self.cache_manager._normalize_text("Meeting 'tomorrow' at 2pm") == 'meeting "tomorrow" at 2pm'
        
        # Test dash normalization
        assert self.cache_manager._normalize_text("Meeting 2–3pm") == "meeting 2-3pm"
        assert self.cache_manager._normalize_text("Meeting 2—3pm") == "meeting 2-3pm"
        
        # Test empty and None handling
        assert self.cache_manager._normalize_text("") == ""
        assert self.cache_manager._normalize_text("   ") == ""
    
    def test_generate_cache_key(self):
        """Test cache key generation from text."""
        # Same text should generate same key
        text1 = "Meeting tomorrow at 2pm"
        text2 = "Meeting tomorrow at 2pm"
        key1 = self.cache_manager._generate_cache_key(text1)
        key2 = self.cache_manager._generate_cache_key(text2)
        assert key1 == key2
        
        # Normalized equivalent text should generate same key
        text3 = "  MEETING   tomorrow  at 2pm  "
        key3 = self.cache_manager._generate_cache_key(text3)
        assert key1 == key3
        
        # Different text should generate different keys
        text4 = "Meeting tomorrow at 3pm"
        key4 = self.cache_manager._generate_cache_key(text4)
        assert key1 != key4
        
        # Keys should be valid SHA-256 hashes (64 hex characters)
        assert len(key1) == 64
        assert all(c in '0123456789abcdef' for c in key1)
    
    def test_put_and_get_basic(self):
        """Test basic cache put and get operations."""
        text = "Meeting tomorrow at 2pm"
        
        # Initially should be cache miss
        result = self.cache_manager.get(text)
        assert result is None
        
        # Put event in cache
        success = self.cache_manager.put(text, self.sample_event)
        assert success is True
        
        # Should now be cache hit
        result = self.cache_manager.get(text)
        assert result is not None
        assert result.title == self.sample_event.title
        assert result.cache_hit is True
        
        # Verify stats updated
        stats = self.cache_manager.get_stats()
        assert stats.total_requests == 2  # 1 miss + 1 hit
        assert stats.cache_hits == 1
        assert stats.cache_misses == 1
        assert stats.total_entries == 1
    
    def test_ttl_expiration(self):
        """Test TTL expiration handling."""
        # Create cache manager with very short TTL for testing
        short_ttl_cache = CacheManager(ttl_hours=0.001)  # ~3.6 seconds
        
        text = "Meeting tomorrow at 2pm"
        
        # Put event in cache
        success = short_ttl_cache.put(text, self.sample_event)
        assert success is True
        
        # Should be available immediately
        result = short_ttl_cache.get(text)
        assert result is not None
        
        # Wait for expiration
        time.sleep(4)
        
        # Should now be expired and return None
        result = short_ttl_cache.get(text)
        assert result is None
        
        # Verify expired entry was cleaned up
        stats = short_ttl_cache.get_stats()
        assert stats.expired_entries_cleaned >= 1
    
    def test_cache_entry_expiration_check(self):
        """Test CacheEntry expiration checking."""
        # Create entry with past timestamp
        past_time = datetime.now() - timedelta(hours=25)
        entry = CacheEntry(
            text_hash="test_hash",
            result=self.sample_event,
            timestamp=past_time,
            hit_count=0
        )
        
        # Should be expired with 24h TTL
        assert self.cache_manager._is_expired(entry) is True
        
        # Create entry with recent timestamp
        recent_time = datetime.now() - timedelta(hours=1)
        entry.timestamp = recent_time
        
        # Should not be expired
        assert self.cache_manager._is_expired(entry) is False
    
    def test_hit_count_tracking(self):
        """Test cache hit count tracking."""
        text = "Meeting tomorrow at 2pm"
        
        # Put event in cache
        self.cache_manager.put(text, self.sample_event)
        
        # Get multiple times to increment hit count
        for i in range(5):
            result = self.cache_manager.get(text)
            assert result is not None
        
        # Check entry details
        entry_details = self.cache_manager.get_entry_details(text)
        assert entry_details is not None
        assert entry_details['hit_count'] == 5
    
    def test_invalidate(self):
        """Test cache invalidation."""
        text = "Meeting tomorrow at 2pm"
        
        # Put event in cache
        self.cache_manager.put(text, self.sample_event)
        
        # Verify it's cached
        result = self.cache_manager.get(text)
        assert result is not None
        
        # Invalidate the entry
        success = self.cache_manager.invalidate(text)
        assert success is True
        
        # Should now be cache miss
        result = self.cache_manager.get(text)
        assert result is None
        
        # Invalidating non-existent entry should return False
        success = self.cache_manager.invalidate("non-existent text")
        assert success is False
    
    def test_clear_cache(self):
        """Test clearing all cache entries."""
        # Add multiple entries
        texts = [
            "Meeting tomorrow at 2pm",
            "Lunch next Friday at noon",
            "Conference call at 3pm"
        ]
        
        for text in texts:
            self.cache_manager.put(text, self.sample_event)
        
        # Verify entries are cached
        stats = self.cache_manager.get_stats()
        assert stats.total_entries == 3
        
        # Clear cache
        cleared_count = self.cache_manager.clear()
        assert cleared_count == 3
        
        # Verify cache is empty
        stats = self.cache_manager.get_stats()
        assert stats.total_entries == 0
        
        # Verify entries are no longer accessible
        for text in texts:
            result = self.cache_manager.get(text)
            assert result is None
    
    def test_max_entries_enforcement(self):
        """Test maximum entries limit enforcement."""
        # Create cache with small max entries for testing
        small_cache = CacheManager(max_entries=5)
        
        # Add more entries than the limit
        for i in range(10):
            text = f"Meeting {i} tomorrow at 2pm"
            small_cache.put(text, self.sample_event)
        
        # Should only have max_entries in cache
        stats = small_cache.get_stats()
        assert stats.total_entries == 5
        
        # Oldest entries should have been removed
        # First few entries should be gone
        for i in range(5):
            text = f"Meeting {i} tomorrow at 2pm"
            result = small_cache.get(text)
            assert result is None
        
        # Last few entries should still be there
        for i in range(5, 10):
            text = f"Meeting {i} tomorrow at 2pm"
            result = small_cache.get(text)
            assert result is not None
    
    def test_cleanup_expired_entries(self):
        """Test manual cleanup of expired entries."""
        # Create cache with short TTL
        short_ttl_cache = CacheManager(ttl_hours=0.001)
        
        # Add entries
        texts = ["Meeting 1", "Meeting 2", "Meeting 3"]
        for text in texts:
            short_ttl_cache.put(text, self.sample_event)
        
        # Verify entries are there
        stats = short_ttl_cache.get_stats()
        assert stats.total_entries == 3
        
        # Wait for expiration
        time.sleep(4)
        
        # Manual cleanup
        cleaned_count = short_ttl_cache.cleanup()
        assert cleaned_count == 3
        
        # Verify cache is empty
        stats = short_ttl_cache.get_stats()
        assert stats.total_entries == 0
    
    def test_performance_stats_tracking(self):
        """Test performance statistics tracking."""
        text = "Meeting tomorrow at 2pm"
        
        # Initial stats should be zero
        stats = self.cache_manager.get_stats()
        assert stats.total_requests == 0
        assert stats.cache_hits == 0
        assert stats.cache_misses == 0
        
        # Cache miss
        result = self.cache_manager.get(text)
        assert result is None
        
        stats = self.cache_manager.get_stats()
        assert stats.total_requests == 1
        assert stats.cache_misses == 1
        assert stats.miss_rate == 100.0
        
        # Cache put and hit
        self.cache_manager.put(text, self.sample_event)
        result = self.cache_manager.get(text)
        assert result is not None
        
        stats = self.cache_manager.get_stats()
        assert stats.total_requests == 2
        assert stats.cache_hits == 1
        assert stats.cache_misses == 1
        assert stats.hit_rate == 50.0
        assert stats.miss_rate == 50.0
    
    def test_cache_info(self):
        """Test cache information retrieval."""
        info = self.cache_manager.get_cache_info()
        
        # Check configuration
        assert info['configuration']['ttl_hours'] == 24
        assert info['configuration']['max_entries'] == 100
        assert info['configuration']['cleanup_interval_minutes'] == 60
        
        # Check statistics structure
        assert 'statistics' in info
        assert 'status' in info
        
        # Check status fields
        assert 'last_cleanup' in info['status']
        assert 'next_cleanup_due' in info['status']
        assert 'cleanup_needed' in info['status']
    
    def test_entry_details(self):
        """Test detailed entry information retrieval."""
        text = "Meeting tomorrow at 2pm"
        
        # Non-existent entry should return None
        details = self.cache_manager.get_entry_details(text)
        assert details is None
        
        # Add entry and check details
        self.cache_manager.put(text, self.sample_event)
        details = self.cache_manager.get_entry_details(text)
        
        assert details is not None
        assert 'cache_key' in details
        assert details['hit_count'] == 0
        assert 'created_at' in details
        assert 'age_hours' in details
        assert 'expires_at' in details
        assert details['is_expired'] is False
        assert 'result_summary' in details
        
        # Check result summary
        summary = details['result_summary']
        assert summary['title'] == self.sample_event.title
        assert summary['confidence_score'] == self.sample_event.confidence_score
    
    def test_thread_safety(self):
        """Test thread safety of cache operations."""
        text_base = "Meeting"
        results = []
        errors = []
        
        def cache_worker(worker_id):
            """Worker function for thread safety testing."""
            try:
                for i in range(10):
                    text = f"{text_base} {worker_id}-{i}"
                    
                    # Put operation
                    success = self.cache_manager.put(text, self.sample_event)
                    results.append(('put', worker_id, i, success))
                    
                    # Get operation
                    result = self.cache_manager.get(text)
                    results.append(('get', worker_id, i, result is not None))
                    
                    # Small delay to increase chance of race conditions
                    time.sleep(0.001)
            except Exception as e:
                errors.append(f"Worker {worker_id}: {e}")
        
        # Create and start multiple threads
        threads = []
        for worker_id in range(5):
            thread = threading.Thread(target=cache_worker, args=(worker_id,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Check for errors
        assert len(errors) == 0, f"Thread safety errors: {errors}"
        
        # Verify operations completed successfully
        put_operations = [r for r in results if r[0] == 'put']
        get_operations = [r for r in results if r[0] == 'get']
        
        assert len(put_operations) == 50  # 5 workers * 10 operations
        assert len(get_operations) == 50
        
        # All put operations should succeed
        assert all(r[3] for r in put_operations)
        
        # All get operations should succeed (since we get immediately after put)
        assert all(r[3] for r in get_operations)
    
    def test_memory_usage_estimation(self):
        """Test memory usage estimation."""
        # Initial memory usage should be minimal
        stats = self.cache_manager.get_stats()
        initial_memory = stats.memory_usage_bytes
        
        # Add several entries
        for i in range(10):
            text = f"Meeting {i} tomorrow at 2pm"
            self.cache_manager.put(text, self.sample_event)
        
        # Memory usage should increase
        stats = self.cache_manager.get_stats()
        final_memory = stats.memory_usage_bytes
        
        assert final_memory > initial_memory
        assert final_memory > 0
    
    def test_automatic_cleanup_trigger(self):
        """Test automatic cleanup triggering."""
        # Create cache with very short cleanup interval
        auto_cleanup_cache = CacheManager(ttl_hours=0.0005, cleanup_interval_minutes=0.005)  # ~0.3 seconds
        
        text = "Meeting tomorrow at 2pm"
        
        # Add entry
        auto_cleanup_cache.put(text, self.sample_event)
        
        # Verify entry is there initially
        result = auto_cleanup_cache.get(text)
        assert result is not None
        
        # Wait for expiration and cleanup interval
        time.sleep(2)
        
        # Next get operation should trigger automatic cleanup
        result = auto_cleanup_cache.get("some other text")
        assert result is None  # Should be miss
        
        # Original entry should be cleaned up
        result = auto_cleanup_cache.get(text)
        assert result is None
    
    def test_global_cache_manager(self):
        """Test global cache manager functions."""
        # Get default global instance
        global_cache = get_cache_manager()
        assert isinstance(global_cache, CacheManager)
        
        # Should return same instance on subsequent calls
        global_cache2 = get_cache_manager()
        assert global_cache is global_cache2
        
        # Initialize with custom settings
        custom_cache = initialize_cache_manager(ttl_hours=12, max_entries=500)
        assert isinstance(custom_cache, CacheManager)
        assert custom_cache.ttl_hours == 12
        assert custom_cache.max_entries == 500
        
        # Should return new instance
        global_cache3 = get_cache_manager()
        assert global_cache3 is custom_cache
        assert global_cache3 is not global_cache


class TestCacheStats:
    """Test cases for CacheStats functionality."""
    
    def test_cache_stats_initialization(self):
        """Test CacheStats initialization and properties."""
        stats = CacheStats()
        
        # Check default values
        assert stats.total_requests == 0
        assert stats.cache_hits == 0
        assert stats.cache_misses == 0
        assert stats.hit_rate == 0.0
        assert stats.miss_rate == 100.0
    
    def test_cache_stats_calculations(self):
        """Test CacheStats rate calculations."""
        stats = CacheStats(
            total_requests=100,
            cache_hits=75,
            cache_misses=25
        )
        
        assert stats.hit_rate == 75.0
        assert stats.miss_rate == 25.0
    
    def test_cache_stats_serialization(self):
        """Test CacheStats to_dict method."""
        stats = CacheStats(
            total_requests=100,
            cache_hits=75,
            cache_misses=25,
            total_entries=50,
            expired_entries_cleaned=10,
            memory_usage_bytes=1024,
            average_hit_time_ms=1.5,
            average_miss_time_ms=25.3
        )
        
        stats_dict = stats.to_dict()
        
        expected_keys = [
            'total_requests', 'cache_hits', 'cache_misses',
            'hit_rate_percent', 'miss_rate_percent', 'total_entries',
            'expired_entries_cleaned', 'memory_usage_bytes',
            'average_hit_time_ms', 'average_miss_time_ms'
        ]
        
        for key in expected_keys:
            assert key in stats_dict
        
        assert stats_dict['hit_rate_percent'] == 75.0
        assert stats_dict['miss_rate_percent'] == 25.0
        assert stats_dict['average_hit_time_ms'] == 1.5
        assert stats_dict['average_miss_time_ms'] == 25.3


class TestCacheManagerErrorHandling:
    """Test error handling in CacheManager."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.cache_manager = CacheManager()
        self.sample_event = ParsedEvent(
            title="Test Meeting",
            start_datetime=datetime(2025, 10, 15, 14, 0),
            end_datetime=datetime(2025, 10, 15, 15, 0)
        )
    
    def test_get_with_invalid_text(self):
        """Test get operation with invalid text."""
        # None text should not crash
        result = self.cache_manager.get(None)
        assert result is None
        
        # Empty text should not crash
        result = self.cache_manager.get("")
        assert result is None
    
    def test_put_with_invalid_data(self):
        """Test put operation with invalid data."""
        # None text should not crash
        success = self.cache_manager.put(None, self.sample_event)
        assert success is False
        
        # None result should not crash
        success = self.cache_manager.put("valid text", None)
        assert success is False
    
    @patch('services.cache_manager.hashlib.sha256')
    def test_hash_generation_error(self, mock_sha256):
        """Test error handling in hash generation."""
        # Mock hash generation to raise exception
        mock_sha256.side_effect = Exception("Hash error")
        
        # Should handle error gracefully
        result = self.cache_manager.get("test text")
        assert result is None
        
        success = self.cache_manager.put("test text", self.sample_event)
        assert success is False
    
    def test_concurrent_access_error_handling(self):
        """Test error handling during concurrent access."""
        text = "Meeting tomorrow at 2pm"
        
        # Put entry in cache
        self.cache_manager.put(text, self.sample_event)
        
        # Simulate concurrent modification by directly manipulating cache
        with self.cache_manager._lock:
            # This should not cause issues in subsequent operations
            pass
        
        # Operations should still work
        result = self.cache_manager.get(text)
        assert result is not None
        
        success = self.cache_manager.invalidate(text)
        assert success is True


if __name__ == '__main__':
    pytest.main([__file__])