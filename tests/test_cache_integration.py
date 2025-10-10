"""
Integration tests for CacheManager with event parsing system.

Tests the cache manager integration with existing parsing components
to ensure proper caching behavior in realistic scenarios.
"""

import pytest
from datetime import datetime

from services.cache_manager import CacheManager
from models.event_models import ParsedEvent


class TestCacheIntegration:
    """Integration tests for cache manager with event parsing."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.cache_manager = CacheManager(ttl_hours=24, max_entries=100)
        
        # Create sample events for testing
        self.event1 = ParsedEvent(
            title="Team Meeting",
            start_datetime=datetime(2025, 10, 15, 14, 0),
            end_datetime=datetime(2025, 10, 15, 15, 0),
            location="Conference Room A",
            description="Weekly team sync",
            confidence_score=0.85,
            parsing_path="regex_primary",
            processing_time_ms=120
        )
        
        self.event2 = ParsedEvent(
            title="Lunch with Client",
            start_datetime=datetime(2025, 10, 16, 12, 0),
            end_datetime=datetime(2025, 10, 16, 13, 30),
            location="Downtown Restaurant",
            description="Business lunch meeting",
            confidence_score=0.92,
            parsing_path="regex_primary",
            processing_time_ms=95
        )
    
    def test_cache_different_texts_same_meaning(self):
        """Test that similar texts with same meaning use cache effectively."""
        # Different formatting but same meaning
        text1 = "Team meeting tomorrow at 2pm in Conference Room A"
        text2 = "TEAM   MEETING tomorrow at 2pm in Conference Room A"
        text3 = "Team meeting tomorrow at 2pm in Conference Room A  "
        
        # Cache first text
        success = self.cache_manager.put(text1, self.event1)
        assert success is True
        
        # All variations should hit the cache due to normalization
        result2 = self.cache_manager.get(text2)
        assert result2 is not None
        assert result2.title == self.event1.title
        assert result2.cache_hit is True
        
        result3 = self.cache_manager.get(text3)
        assert result3 is not None
        assert result3.title == self.event1.title
        assert result3.cache_hit is True
        
        # Verify cache stats
        stats = self.cache_manager.get_stats()
        assert stats.cache_hits == 2
        assert stats.cache_misses == 0  # No misses since we only did puts and hits
    
    def test_cache_with_parsing_metadata(self):
        """Test caching preserves parsing metadata correctly."""
        text = "Lunch meeting next Friday at noon downtown"
        
        # Set up event with detailed metadata
        self.event2.field_results = {
            'title': type('FieldResult', (), {
                'value': 'Lunch meeting',
                'source': 'regex',
                'confidence': 0.9,
                'span': (0, 13)
            })(),
            'start_datetime': type('FieldResult', (), {
                'value': self.event2.start_datetime,
                'source': 'regex',
                'confidence': 0.95,
                'span': (14, 35)
            })()
        }
        
        # Cache the event
        success = self.cache_manager.put(text, self.event2)
        assert success is True
        
        # Retrieve and verify metadata is preserved
        cached_event = self.cache_manager.get(text)
        assert cached_event is not None
        assert cached_event.parsing_path == "regex_primary"
        assert cached_event.processing_time_ms == 95
        assert cached_event.confidence_score == 0.92
        assert cached_event.cache_hit is True
        
        # Verify field results are preserved
        assert len(cached_event.field_results) == 2
        assert 'title' in cached_event.field_results
        assert 'start_datetime' in cached_event.field_results
    
    def test_cache_performance_with_realistic_load(self):
        """Test cache performance with realistic parsing load."""
        # Simulate realistic parsing scenarios
        test_cases = [
            ("Meeting tomorrow at 2pm", self.event1),
            ("Lunch next Friday at noon", self.event2),
            ("Conference call at 3:30pm", self.event1),
            ("Doctor appointment Monday 10am", self.event2),
            ("Team standup daily at 9am", self.event1)
        ]
        
        # First pass - populate cache
        for text, event in test_cases:
            success = self.cache_manager.put(text, event)
            assert success is True
        
        # Second pass - should all be cache hits
        hit_count = 0
        for text, expected_event in test_cases:
            result = self.cache_manager.get(text)
            assert result is not None
            assert result.cache_hit is True
            hit_count += 1
        
        # Verify performance stats
        stats = self.cache_manager.get_stats()
        assert stats.cache_hits == hit_count
        assert stats.total_entries == len(test_cases)
        assert stats.hit_rate == 100.0
        
        # Verify average hit time is reasonable (should be very fast)
        assert stats.average_hit_time_ms < 10.0  # Should be under 10ms
    
    def test_cache_with_confidence_variations(self):
        """Test caching behavior with different confidence levels."""
        base_text = "Meeting tomorrow at 2pm"
        
        # Create events with different confidence levels
        high_confidence_event = ParsedEvent(
            title="High Confidence Meeting",
            start_datetime=datetime(2025, 10, 15, 14, 0),
            end_datetime=datetime(2025, 10, 15, 15, 0),
            confidence_score=0.95,
            parsing_path="regex_primary"
        )
        
        low_confidence_event = ParsedEvent(
            title="Low Confidence Meeting",
            start_datetime=datetime(2025, 10, 15, 14, 0),
            end_datetime=datetime(2025, 10, 15, 15, 0),
            confidence_score=0.45,
            parsing_path="llm_fallback",
            needs_confirmation=True
        )
        
        # Cache high confidence event
        self.cache_manager.put(base_text, high_confidence_event)
        
        # Retrieve and verify
        result = self.cache_manager.get(base_text)
        assert result is not None
        assert result.confidence_score == 0.95
        assert result.parsing_path == "regex_primary"
        assert result.needs_confirmation is False
        
        # Cache low confidence event (overwrites previous)
        self.cache_manager.put(base_text, low_confidence_event)
        
        # Retrieve and verify updated
        result = self.cache_manager.get(base_text)
        assert result is not None
        assert result.confidence_score == 0.45
        assert result.parsing_path == "llm_fallback"
        assert result.needs_confirmation is True
    
    def test_cache_entry_details_integration(self):
        """Test cache entry details with realistic event data."""
        text = "Important client meeting next Tuesday at 3pm"
        
        # Create event with comprehensive data
        comprehensive_event = ParsedEvent(
            title="Important Client Meeting",
            start_datetime=datetime(2025, 10, 21, 15, 0),
            end_datetime=datetime(2025, 10, 21, 16, 0),
            location="Client Office",
            description="Quarterly business review",
            confidence_score=0.88,
            parsing_path="regex_primary",
            processing_time_ms=145,
            participants=["john@company.com", "client@clientco.com"]
        )
        
        # Cache the event
        self.cache_manager.put(text, comprehensive_event)
        
        # Access multiple times to increase hit count
        for _ in range(5):
            result = self.cache_manager.get(text)
            assert result is not None
        
        # Get detailed entry information
        details = self.cache_manager.get_entry_details(text)
        assert details is not None
        
        # Verify entry details
        assert details['hit_count'] == 5
        assert details['is_expired'] is False
        
        # Verify result summary
        summary = details['result_summary']
        assert summary['title'] == "Important Client Meeting"
        assert summary['confidence_score'] == 0.88
        assert summary['parsing_path'] == "regex_primary"
        assert summary['processing_time_ms'] == 145
    
    def test_cache_serialization_roundtrip(self):
        """Test that cached events maintain data integrity through serialization."""
        text = "Complex event with all fields next Monday 9am-5pm"
        
        # Create event with all possible fields populated
        complex_event = ParsedEvent(
            title="Complex All-Day Workshop",
            start_datetime=datetime(2025, 10, 20, 9, 0),
            end_datetime=datetime(2025, 10, 20, 17, 0),
            location="Training Center Room B",
            description="Full-day training workshop with multiple sessions",
            recurrence="FREQ=WEEKLY;BYDAY=MO",
            participants=["trainer@company.com", "team@company.com"],
            all_day=False,
            confidence_score=0.91,
            parsing_path="regex_primary",
            processing_time_ms=200,
            cache_hit=False,
            needs_confirmation=False
        )
        
        # Add field results
        complex_event.field_results = {
            'title': type('FieldResult', (), {
                'value': 'Complex All-Day Workshop',
                'source': 'regex',
                'confidence': 0.9,
                'span': (0, 25),
                'alternatives': ['Workshop', 'Training'],
                'processing_time_ms': 50
            })()
        }
        
        # Add extraction metadata
        complex_event.extraction_metadata = {
            'warnings': ['Long duration detected'],
            'suggestions': ['Consider breaking into multiple events'],
            'parsing_method': 'hybrid'
        }
        
        # Cache and retrieve
        success = self.cache_manager.put(text, complex_event)
        assert success is True
        
        cached_event = self.cache_manager.get(text)
        assert cached_event is not None
        
        # Verify all fields are preserved
        assert cached_event.title == complex_event.title
        assert cached_event.start_datetime == complex_event.start_datetime
        assert cached_event.end_datetime == complex_event.end_datetime
        assert cached_event.location == complex_event.location
        assert cached_event.description == complex_event.description
        assert cached_event.recurrence == complex_event.recurrence
        assert cached_event.participants == complex_event.participants
        assert cached_event.all_day == complex_event.all_day
        assert cached_event.confidence_score == complex_event.confidence_score
        assert cached_event.parsing_path == complex_event.parsing_path
        assert cached_event.processing_time_ms == complex_event.processing_time_ms
        assert cached_event.needs_confirmation == complex_event.needs_confirmation
        
        # Verify cache_hit flag is set
        assert cached_event.cache_hit is True
        
        # Verify field results are preserved
        assert len(cached_event.field_results) == 1
        assert 'title' in cached_event.field_results
        
        # Verify extraction metadata is preserved
        assert cached_event.extraction_metadata == complex_event.extraction_metadata


if __name__ == '__main__':
    pytest.main([__file__])