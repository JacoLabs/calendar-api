"""
Intelligent caching system for parsed events with 24h TTL and performance metrics.

This module implements the CacheManager class that provides:
- Normalized text hashing for cache keys
- 24-hour TTL with automatic cleanup
- Cache hit/miss tracking and performance metrics
- Thread-safe operations for concurrent access
"""

import hashlib
import json
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple, List, Any
from dataclasses import dataclass, field

from models.event_models import ParsedEvent, CacheEntry


@dataclass
class CacheStats:
    """Statistics for cache performance monitoring."""
    total_requests: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    total_entries: int = 0
    expired_entries_cleaned: int = 0
    memory_usage_bytes: int = 0
    average_hit_time_ms: float = 0.0
    average_miss_time_ms: float = 0.0
    
    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate as percentage."""
        if self.total_requests == 0:
            return 0.0
        return (self.cache_hits / self.total_requests) * 100.0
    
    @property
    def miss_rate(self) -> float:
        """Calculate cache miss rate as percentage."""
        return 100.0 - self.hit_rate
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert stats to dictionary for serialization."""
        return {
            'total_requests': self.total_requests,
            'cache_hits': self.cache_hits,
            'cache_misses': self.cache_misses,
            'hit_rate_percent': round(self.hit_rate, 2),
            'miss_rate_percent': round(self.miss_rate, 2),
            'total_entries': self.total_entries,
            'expired_entries_cleaned': self.expired_entries_cleaned,
            'memory_usage_bytes': self.memory_usage_bytes,
            'average_hit_time_ms': round(self.average_hit_time_ms, 2),
            'average_miss_time_ms': round(self.average_miss_time_ms, 2)
        }


class CacheManager:
    """
    Intelligent caching system for parsed events with 24h TTL and performance tracking.
    
    Features:
    - Normalized text hashing for consistent cache keys
    - 24-hour TTL with automatic expiration
    - Thread-safe operations for concurrent access
    - Performance metrics and hit/miss tracking
    - Automatic cleanup of expired entries
    - Memory usage monitoring
    """
    
    def __init__(self, ttl_hours: int = 24, max_entries: int = 10000, cleanup_interval_minutes: int = 60):
        """
        Initialize the cache manager.
        
        Args:
            ttl_hours: Time-to-live for cache entries in hours (default: 24)
            max_entries: Maximum number of entries to store (default: 10000)
            cleanup_interval_minutes: How often to run cleanup in minutes (default: 60)
        """
        self.ttl_hours = ttl_hours
        self.max_entries = max_entries
        self.cleanup_interval_minutes = cleanup_interval_minutes
        
        # Thread-safe cache storage
        self._cache: Dict[str, CacheEntry] = {}
        self._lock = threading.RLock()
        
        # Performance tracking
        self._stats = CacheStats()
        self._hit_times: List[float] = []
        self._miss_times: List[float] = []
        
        # Cleanup tracking
        self._last_cleanup = datetime.now()
        
    def _normalize_text(self, text: str) -> str:
        """
        Normalize text for consistent cache key generation.
        
        Args:
            text: Raw input text
            
        Returns:
            Normalized text string
        """
        if not text:
            return ""
        
        # Convert to lowercase and strip whitespace
        normalized = text.lower().strip()
        
        # Replace multiple whitespace with single space
        import re
        normalized = re.sub(r'\s+', ' ', normalized)
        
        # Remove common punctuation variations that don't affect meaning
        # Keep essential punctuation like colons, dashes for time/date parsing
        normalized = re.sub(r"['\"]", '"', normalized)  # Normalize quotes
        normalized = re.sub(r'[–—]', '-', normalized)  # Normalize dashes
        
        return normalized
    
    def _generate_cache_key(self, text: str) -> str:
        """
        Generate a cache key from normalized text using SHA-256 hashing.
        
        Args:
            text: Input text to hash
            
        Returns:
            SHA-256 hash as hexadecimal string
        """
        normalized_text = self._normalize_text(text)
        
        # Create hash from normalized text
        hash_object = hashlib.sha256(normalized_text.encode('utf-8'))
        return hash_object.hexdigest()
    
    def _is_expired(self, entry: CacheEntry) -> bool:
        """
        Check if a cache entry is expired.
        
        Args:
            entry: Cache entry to check
            
        Returns:
            True if entry is expired
        """
        return entry.is_expired(self.ttl_hours)
    
    def _cleanup_expired_entries(self) -> int:
        """
        Remove expired entries from cache.
        
        Returns:
            Number of entries removed
        """
        with self._lock:
            expired_keys = []
            
            for key, entry in self._cache.items():
                if self._is_expired(entry):
                    expired_keys.append(key)
            
            # Remove expired entries
            for key in expired_keys:
                del self._cache[key]
            
            # Update stats
            self._stats.expired_entries_cleaned += len(expired_keys)
            self._stats.total_entries = len(self._cache)
            
            # Update last cleanup time
            self._last_cleanup = datetime.now()
            
            return len(expired_keys)
    
    def _should_cleanup(self) -> bool:
        """
        Check if automatic cleanup should be performed.
        
        Returns:
            True if cleanup is needed
        """
        time_since_cleanup = datetime.now() - self._last_cleanup
        return time_since_cleanup.total_seconds() > (self.cleanup_interval_minutes * 60)
    
    def _enforce_max_entries(self):
        """
        Enforce maximum entry limit by removing oldest entries.
        """
        with self._lock:
            if len(self._cache) <= self.max_entries:
                return
            
            # Sort entries by timestamp (oldest first)
            sorted_entries = sorted(
                self._cache.items(),
                key=lambda x: x[1].timestamp
            )
            
            # Remove oldest entries until we're under the limit
            entries_to_remove = len(self._cache) - self.max_entries
            for i in range(entries_to_remove):
                key, _ = sorted_entries[i]
                del self._cache[key]
            
            self._stats.total_entries = len(self._cache)
    
    def _update_performance_stats(self, is_hit: bool, processing_time_ms: float):
        """
        Update performance statistics.
        
        Args:
            is_hit: Whether this was a cache hit
            processing_time_ms: Time taken for the operation
        """
        with self._lock:
            self._stats.total_requests += 1
            
            if is_hit:
                self._stats.cache_hits += 1
                self._hit_times.append(processing_time_ms)
                
                # Keep only recent hit times for average calculation
                if len(self._hit_times) > 1000:
                    self._hit_times = self._hit_times[-1000:]
                
                self._stats.average_hit_time_ms = sum(self._hit_times) / len(self._hit_times)
            else:
                self._stats.cache_misses += 1
                self._miss_times.append(processing_time_ms)
                
                # Keep only recent miss times for average calculation
                if len(self._miss_times) > 1000:
                    self._miss_times = self._miss_times[-1000:]
                
                self._stats.average_miss_time_ms = sum(self._miss_times) / len(self._miss_times)
    
    def _estimate_memory_usage(self) -> int:
        """
        Estimate memory usage of cache in bytes.
        
        Returns:
            Estimated memory usage in bytes
        """
        # Rough estimation based on average entry size
        # This is approximate since Python object overhead varies
        if not self._cache:
            return 0
        
        # Sample a few entries to estimate average size
        sample_size = min(10, len(self._cache))
        sample_entries = list(self._cache.values())[:sample_size]
        
        total_sample_size = 0
        for entry in sample_entries:
            # Estimate size of cache entry
            entry_size = (
                len(entry.text_hash) * 2 +  # Hash string
                len(str(entry.result.to_dict())) * 2 +  # Serialized result (rough estimate)
                64 +  # Timestamp and hit_count
                200  # Object overhead
            )
            total_sample_size += entry_size
        
        if sample_size > 0:
            average_entry_size = total_sample_size / sample_size
            return int(average_entry_size * len(self._cache))
        
        return 0
    
    def get(self, text: str) -> Optional[ParsedEvent]:
        """
        Retrieve a cached parsing result for the given text.
        
        Args:
            text: Input text to look up
            
        Returns:
            Cached ParsedEvent if found and not expired, None otherwise
        """
        start_time = time.time()
        
        try:
            # Generate cache key
            cache_key = self._generate_cache_key(text)
            
            # Perform automatic cleanup if needed
            if self._should_cleanup():
                self._cleanup_expired_entries()
            
            with self._lock:
                # Check if entry exists
                if cache_key not in self._cache:
                    processing_time_ms = (time.time() - start_time) * 1000
                    self._update_performance_stats(is_hit=False, processing_time_ms=processing_time_ms)
                    return None
                
                entry = self._cache[cache_key]
                
                # Check if entry is expired
                if self._is_expired(entry):
                    del self._cache[cache_key]
                    self._stats.expired_entries_cleaned += 1
                    self._stats.total_entries = len(self._cache)
                    
                    processing_time_ms = (time.time() - start_time) * 1000
                    self._update_performance_stats(is_hit=False, processing_time_ms=processing_time_ms)
                    return None
                
                # Cache hit - increment hit count and return result
                entry.increment_hit_count()
                result = entry.result
                result.cache_hit = True
                
                processing_time_ms = (time.time() - start_time) * 1000
                self._update_performance_stats(is_hit=True, processing_time_ms=processing_time_ms)
                
                return result
                
        except Exception as e:
            # Log error but don't fail the request
            print(f"Cache get error: {e}")
            processing_time_ms = (time.time() - start_time) * 1000
            self._update_performance_stats(is_hit=False, processing_time_ms=processing_time_ms)
            return None
    
    def put(self, text: str, result: ParsedEvent) -> bool:
        """
        Store a parsing result in the cache.
        
        Args:
            text: Input text used as cache key
            result: ParsedEvent to cache
            
        Returns:
            True if successfully cached, False otherwise
        """
        try:
            # Validate inputs
            if text is None or result is None:
                return False
            
            # Generate cache key
            cache_key = self._generate_cache_key(text)
            
            # Create cache entry
            entry = CacheEntry(
                text_hash=cache_key,
                result=result,
                timestamp=datetime.now(),
                hit_count=0
            )
            
            with self._lock:
                # Store entry
                self._cache[cache_key] = entry
                self._stats.total_entries = len(self._cache)
                
                # Enforce maximum entries limit
                self._enforce_max_entries()
            
            return True
            
        except Exception as e:
            # Log error but don't fail the request
            print(f"Cache put error: {e}")
            return False
    
    def invalidate(self, text: str) -> bool:
        """
        Remove a specific entry from the cache.
        
        Args:
            text: Input text to invalidate
            
        Returns:
            True if entry was found and removed, False otherwise
        """
        try:
            cache_key = self._generate_cache_key(text)
            
            with self._lock:
                if cache_key in self._cache:
                    del self._cache[cache_key]
                    self._stats.total_entries = len(self._cache)
                    return True
                
                return False
                
        except Exception as e:
            print(f"Cache invalidate error: {e}")
            return False
    
    def clear(self) -> int:
        """
        Clear all entries from the cache.
        
        Returns:
            Number of entries removed
        """
        with self._lock:
            entry_count = len(self._cache)
            self._cache.clear()
            self._stats.total_entries = 0
            return entry_count
    
    def cleanup(self) -> int:
        """
        Manually trigger cleanup of expired entries.
        
        Returns:
            Number of expired entries removed
        """
        return self._cleanup_expired_entries()
    
    def get_stats(self) -> CacheStats:
        """
        Get current cache performance statistics.
        
        Returns:
            CacheStats object with current metrics
        """
        with self._lock:
            # Update memory usage estimate
            self._stats.memory_usage_bytes = self._estimate_memory_usage()
            self._stats.total_entries = len(self._cache)
            
            # Return a copy of stats
            return CacheStats(
                total_requests=self._stats.total_requests,
                cache_hits=self._stats.cache_hits,
                cache_misses=self._stats.cache_misses,
                total_entries=self._stats.total_entries,
                expired_entries_cleaned=self._stats.expired_entries_cleaned,
                memory_usage_bytes=self._stats.memory_usage_bytes,
                average_hit_time_ms=self._stats.average_hit_time_ms,
                average_miss_time_ms=self._stats.average_miss_time_ms
            )
    
    def get_cache_info(self) -> Dict[str, Any]:
        """
        Get detailed cache information including configuration and stats.
        
        Returns:
            Dictionary with cache configuration and performance data
        """
        stats = self.get_stats()
        
        return {
            'configuration': {
                'ttl_hours': self.ttl_hours,
                'max_entries': self.max_entries,
                'cleanup_interval_minutes': self.cleanup_interval_minutes
            },
            'statistics': stats.to_dict(),
            'status': {
                'last_cleanup': self._last_cleanup.isoformat(),
                'next_cleanup_due': (self._last_cleanup + timedelta(minutes=self.cleanup_interval_minutes)).isoformat(),
                'cleanup_needed': self._should_cleanup()
            }
        }
    
    def get_entry_details(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a specific cache entry.
        
        Args:
            text: Input text to look up
            
        Returns:
            Dictionary with entry details or None if not found
        """
        try:
            cache_key = self._generate_cache_key(text)
            
            with self._lock:
                if cache_key not in self._cache:
                    return None
                
                entry = self._cache[cache_key]
                
                return {
                    'cache_key': cache_key,
                    'hit_count': entry.hit_count,
                    'created_at': entry.timestamp.isoformat(),
                    'age_hours': (datetime.now() - entry.timestamp).total_seconds() / 3600,
                    'expires_at': (entry.timestamp + timedelta(hours=self.ttl_hours)).isoformat(),
                    'is_expired': self._is_expired(entry),
                    'result_summary': {
                        'title': entry.result.title,
                        'confidence_score': entry.result.confidence_score,
                        'parsing_path': entry.result.parsing_path,
                        'processing_time_ms': entry.result.processing_time_ms
                    }
                }
                
        except Exception as e:
            print(f"Cache entry details error: {e}")
            return None


# Global cache manager instance
_cache_manager: Optional[CacheManager] = None


def get_cache_manager() -> CacheManager:
    """
    Get the global cache manager instance.
    
    Returns:
        CacheManager instance
    """
    global _cache_manager
    if _cache_manager is None:
        # Read configuration from environment variables
        import os
        ttl_hours = int(os.getenv('CACHE_TTL_HOURS', '24'))
        max_entries = int(os.getenv('CACHE_MAX_ENTRIES', '10000'))
        cleanup_interval = int(os.getenv('CACHE_CLEANUP_INTERVAL_MINUTES', '60'))
        
        _cache_manager = CacheManager(
            ttl_hours=ttl_hours,
            max_entries=max_entries,
            cleanup_interval_minutes=cleanup_interval
        )
    return _cache_manager


def initialize_cache_manager(ttl_hours: int = 24, max_entries: int = 10000, cleanup_interval_minutes: int = 60) -> CacheManager:
    """
    Initialize the global cache manager with custom settings.
    
    Args:
        ttl_hours: Time-to-live for cache entries in hours
        max_entries: Maximum number of entries to store
        cleanup_interval_minutes: How often to run cleanup in minutes
        
    Returns:
        Initialized CacheManager instance
    """
    global _cache_manager
    _cache_manager = CacheManager(ttl_hours, max_entries, cleanup_interval_minutes)
    return _cache_manager