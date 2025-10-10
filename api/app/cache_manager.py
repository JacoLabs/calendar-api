"""
Cache manager for API responses with 24h TTL and performance monitoring.
"""

import hashlib
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import json
import logging
from threading import Lock

logger = logging.getLogger(__name__)


class CacheEntry:
    """Individual cache entry with metadata."""
    
    def __init__(self, key: str, value: Any, ttl_hours: int = 24):
        self.key = key
        self.value = value
        self.created_at = datetime.utcnow()
        self.expires_at = self.created_at + timedelta(hours=ttl_hours)
        self.hit_count = 0
        self.last_accessed = self.created_at
        self.size_bytes = len(json.dumps(value, default=str))
    
    def is_expired(self) -> bool:
        """Check if this cache entry has expired."""
        return datetime.utcnow() > self.expires_at
    
    def access(self) -> Any:
        """Access the cached value and update metadata."""
        self.hit_count += 1
        self.last_accessed = datetime.utcnow()
        return self.value
    
    def age_hours(self) -> float:
        """Get the age of this entry in hours."""
        return (datetime.utcnow() - self.created_at).total_seconds() / 3600


class CacheManager:
    """
    Simple in-memory cache manager with TTL and performance monitoring.
    
    In production, this would be replaced with Redis or Memcached.
    """
    
    def __init__(self, max_size_mb: float = 100.0, ttl_hours: int = 24):
        self.max_size_mb = max_size_mb
        self.ttl_hours = ttl_hours
        self.cache: Dict[str, CacheEntry] = {}
        self.lock = Lock()
        
        # Statistics
        self.stats = {
            "total_requests": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "evictions": 0,
            "last_cleanup": datetime.utcnow()
        }
    
    def _normalize_text(self, text: str) -> str:
        """Normalize text for consistent cache keys."""
        # Remove extra whitespace and convert to lowercase
        normalized = ' '.join(text.strip().lower().split())
        return normalized
    
    def _generate_cache_key(self, text: str, **kwargs) -> str:
        """Generate a cache key from normalized text and parameters."""
        normalized_text = self._normalize_text(text)
        
        # Include relevant parameters in the key
        key_data = {
            "text": normalized_text,
            "timezone": kwargs.get("timezone", "UTC"),
            "locale": kwargs.get("locale", "en_US"),
            "use_llm": kwargs.get("use_llm_enhancement", True)
        }
        
        # Create hash of the key data
        key_string = json.dumps(key_data, sort_keys=True)
        return hashlib.sha256(key_string.encode()).hexdigest()[:16]
    
    def get(self, text: str, **kwargs) -> Optional[Any]:
        """Get cached result for the given text and parameters."""
        cache_key = self._generate_cache_key(text, **kwargs)
        
        with self.lock:
            self.stats["total_requests"] += 1
            
            if cache_key in self.cache:
                entry = self.cache[cache_key]
                
                if entry.is_expired():
                    # Remove expired entry
                    del self.cache[cache_key]
                    self.stats["cache_misses"] += 1
                    return None
                
                # Cache hit
                self.stats["cache_hits"] += 1
                return entry.access()
            
            # Cache miss
            self.stats["cache_misses"] += 1
            return None
    
    def set(self, text: str, value: Any, **kwargs) -> None:
        """Cache a result for the given text and parameters."""
        cache_key = self._generate_cache_key(text, **kwargs)
        
        with self.lock:
            # Create new cache entry
            entry = CacheEntry(cache_key, value, self.ttl_hours)
            
            # Check if we need to make space
            self._ensure_space_available(entry.size_bytes)
            
            # Store the entry
            self.cache[cache_key] = entry
    
    def _ensure_space_available(self, new_entry_size: int) -> None:
        """Ensure there's space for a new entry, evicting old entries if needed."""
        max_size_bytes = self.max_size_mb * 1024 * 1024
        current_size = self._calculate_current_size()
        
        if current_size + new_entry_size > max_size_bytes:
            # Need to evict entries
            self._evict_entries(current_size + new_entry_size - max_size_bytes)
    
    def _calculate_current_size(self) -> int:
        """Calculate current cache size in bytes."""
        return sum(entry.size_bytes for entry in self.cache.values())
    
    def _evict_entries(self, bytes_to_free: int) -> None:
        """Evict entries to free up the specified number of bytes."""
        # Sort entries by last accessed time (LRU eviction)
        entries_by_access = sorted(
            self.cache.items(),
            key=lambda x: x[1].last_accessed
        )
        
        freed_bytes = 0
        for cache_key, entry in entries_by_access:
            if freed_bytes >= bytes_to_free:
                break
            
            freed_bytes += entry.size_bytes
            del self.cache[cache_key]
            self.stats["evictions"] += 1
    
    def cleanup_expired(self) -> int:
        """Remove expired entries and return count of removed entries."""
        with self.lock:
            expired_keys = [
                key for key, entry in self.cache.items()
                if entry.is_expired()
            ]
            
            for key in expired_keys:
                del self.cache[key]
            
            self.stats["last_cleanup"] = datetime.utcnow()
            return len(expired_keys)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics."""
        with self.lock:
            total_requests = self.stats["total_requests"]
            hit_ratio = 0.0
            if total_requests > 0:
                hit_ratio = self.stats["cache_hits"] / total_requests
            
            current_size_bytes = self._calculate_current_size()
            current_size_mb = current_size_bytes / (1024 * 1024)
            
            # Calculate average hit speedup (estimated)
            # In a real implementation, this would track actual response times
            average_speedup = 0.0
            if self.stats["cache_hits"] > 0:
                # Estimate based on typical parsing time vs cache lookup time
                average_speedup = 800.0  # Assume 800ms average speedup
            
            # Find oldest entry
            oldest_age_hours = 0.0
            if self.cache:
                oldest_entry = min(self.cache.values(), key=lambda e: e.created_at)
                oldest_age_hours = oldest_entry.age_hours()
            
            return {
                "status": "healthy",
                "total_requests": total_requests,
                "cache_hits": self.stats["cache_hits"],
                "cache_misses": self.stats["cache_misses"],
                "hit_ratio": hit_ratio,
                "cache_size_mb": current_size_mb,
                "max_cache_size_mb": self.max_size_mb,
                "ttl_hours": self.ttl_hours,
                "oldest_entry_age_hours": oldest_age_hours,
                "average_hit_speedup_ms": average_speedup,
                "entries_count": len(self.cache),
                "evictions_count": self.stats["evictions"],
                "last_cleanup": self.stats["last_cleanup"].isoformat(),
                "utilization_percent": (current_size_mb / self.max_size_mb) * 100
            }
    
    def clear(self) -> None:
        """Clear all cached entries."""
        with self.lock:
            self.cache.clear()
            self.stats["evictions"] += len(self.cache)


# Global cache manager instance
cache_manager = CacheManager()