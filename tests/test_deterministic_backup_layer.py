"""
Integration tests for DeterministicBackupLayer coordination.

Tests the coordination between Duckling and Microsoft Recognizers-Text
for deterministic backup parsing functionality.
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch, MagicMock
import time

from services.deterministic_backup_layer import DeterministicBackupLayer
from models.event_models import FieldResult


class TestDeterministicBackupLayer:
    """Test suite for DeterministicBackupLayer coordination."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.backup_layer = DeterministicBackupLayer(
            duckling_url="http://localhost:8000/parse",
            default_timezone="UTC",
            timeout_seconds=3
        )
    
    def test_initialization(self):
        """Test proper initialization of backup layer."""
        assert self.backup_layer.default_timezone == "UTC"
        assert self.backup_layer.timeout_seconds == 3
        assert self.backup_layer.duckling_extractor is not None
        assert self.backup_layer.recognizers_extractor is not None
        
        # Check performance stats initialization
        stats = self.backup_layer.get_performance_stats()
        assert stats['total_calls'] == 0
        assert stats['success_rate'] == 0.0
    
    @patch('services.deterministic_backup_layer.DucklingExtractor')
    @patch('services.deterministic_backup_layer.RecognizersExtractor')
    def test_extract_with_backup_both_available(self, mock_recognizers_class, mock_duckling_class):
        """Test extraction when both services are available."""
        # Mock Duckling extractor
        mock_duckling = Mock()
        mock_duckling.is_service_available.return_value = True
        mock_duckling.extract_with_duckling.return_value = FieldResult(
            value=datetime(2025, 10, 15, 14, 0, tzinfo=timezone.utc),
            source="duckling",
            confidence=0.75,
            span=(0, 10),
            alternatives=[],
            processing_time_ms=50
        )
        mock_duckling_class.return_value = mock_duckling
        
        # Mock Recognizers extractor
        mock_recognizers = Mock()
        mock_recognizers.is_service_available.return_value = True
        mock_recognizers.extract_with_recognizers.return_value = FieldResult(
            value=datetime(2025, 10, 15, 14, 0, tzinfo=timezone.utc),
            source="recognizers",
            confidence=0.70,
            span=(0, 15),
            alternatives=[],
            processing_time_ms=75
        )
        mock_recognizers_class.return_value = mock_recognizers
        
        # Create new backup layer with mocked extractors
        backup_layer = DeterministicBackupLayer()
        
        # Test extraction
        result = backup_layer.extract_with_backup("tomorrow at 2pm", "datetime")
        
        assert result.value is not None
        assert result.source.startswith("deterministic_backup_")
        assert 0.6 <= result.confidence <= 0.8
        assert result.processing_time_ms > 0
        
        # Verify both extractors were called
        mock_duckling.extract_with_duckling.assert_called_once()
        mock_recognizers.extract_with_recognizers.assert_called_once()
    
    @patch('services.deterministic_backup_layer.DucklingExtractor')
    @patch('services.deterministic_backup_layer.RecognizersExtractor')
    def test_extract_with_backup_duckling_only(self, mock_recognizers_class, mock_duckling_class):
        """Test extraction when only Duckling is available."""
        # Mock Duckling extractor (available)
        mock_duckling = Mock()
        mock_duckling.is_service_available.return_value = True
        mock_duckling.extract_with_duckling.return_value = FieldResult(
            value=datetime(2025, 10, 15, 14, 0, tzinfo=timezone.utc),
            source="duckling",
            confidence=0.75,
            span=(0, 10),
            alternatives=[],
            processing_time_ms=50
        )
        mock_duckling_class.return_value = mock_duckling
        
        # Mock Recognizers extractor (not available)
        mock_recognizers = Mock()
        mock_recognizers.is_service_available.return_value = False
        mock_recognizers_class.return_value = mock_recognizers
        
        # Create new backup layer with mocked extractors
        backup_layer = DeterministicBackupLayer()
        
        # Test extraction
        result = backup_layer.extract_with_backup("tomorrow at 2pm", "datetime")
        
        assert result.value is not None
        assert result.source == "deterministic_backup_duckling"
        assert result.confidence == 0.75
        
        # Verify only Duckling was called
        mock_duckling.extract_with_duckling.assert_called_once()
        mock_recognizers.extract_with_recognizers.assert_not_called()
    
    @patch('services.deterministic_backup_layer.DucklingExtractor')
    @patch('services.deterministic_backup_layer.RecognizersExtractor')
    def test_extract_with_backup_neither_available(self, mock_recognizers_class, mock_duckling_class):
        """Test extraction when neither service is available."""
        # Mock both extractors as unavailable
        mock_duckling = Mock()
        mock_duckling.is_service_available.return_value = False
        mock_duckling_class.return_value = mock_duckling
        
        mock_recognizers = Mock()
        mock_recognizers.is_service_available.return_value = False
        mock_recognizers_class.return_value = mock_recognizers
        
        # Create new backup layer with mocked extractors
        backup_layer = DeterministicBackupLayer()
        
        # Test extraction
        result = backup_layer.extract_with_backup("tomorrow at 2pm", "datetime")
        
        assert result.value is None
        assert result.source == "deterministic_backup"
        assert result.confidence == 0.0
        assert result.span == (0, 0)
        
        # Verify neither extractor was called for extraction
        mock_duckling.extract_with_duckling.assert_not_called()
        mock_recognizers.extract_with_recognizers.assert_not_called()
    
    def test_choose_best_span_single_candidate(self):
        """Test choosing best span with single candidate."""
        candidate = FieldResult(
            value=datetime(2025, 10, 15, 14, 0, tzinfo=timezone.utc),
            source="duckling",
            confidence=0.75,
            span=(0, 10),
            alternatives=[],
            processing_time_ms=50
        )
        
        result = self.backup_layer.choose_best_span([candidate], "tomorrow at 2pm", "datetime")
        
        assert result == candidate
    
    def test_choose_best_span_multiple_candidates(self):
        """Test choosing best span with multiple candidates."""
        # Duckling candidate (shorter span, higher confidence)
        duckling_candidate = FieldResult(
            value=datetime(2025, 10, 15, 14, 0, tzinfo=timezone.utc),
            source="duckling",
            confidence=0.75,
            span=(0, 8),  # Shorter span
            alternatives=[],
            processing_time_ms=50
        )
        
        # Recognizers candidate (longer span, lower confidence)
        recognizers_candidate = FieldResult(
            value=datetime(2025, 10, 15, 14, 30, tzinfo=timezone.utc),
            source="recognizers",
            confidence=0.70,
            span=(0, 15),  # Longer span
            alternatives=[],
            processing_time_ms=75
        )
        
        candidates = [duckling_candidate, recognizers_candidate]
        result = self.backup_layer.choose_best_span(candidates, "tomorrow at 2pm", "datetime")
        
        # Should prefer Duckling due to higher confidence and shorter span
        assert result.source == "duckling"
        assert result.confidence == 0.75
        assert result.span == (0, 8)
        
        # Should include alternative from other candidate
        assert len(result.alternatives) > 0
    
    def test_choose_best_span_empty_candidates(self):
        """Test choosing best span with no candidates."""
        result = self.backup_layer.choose_best_span([], "tomorrow at 2pm", "datetime")
        
        assert result.value is None
        assert result.source == "deterministic_backup"
        assert result.confidence == 0.0
    
    def test_validate_timezone_normalization_valid(self):
        """Test timezone validation with valid datetime."""
        valid_result = FieldResult(
            value=datetime(2025, 10, 15, 14, 0, tzinfo=timezone.utc),
            source="duckling",
            confidence=0.75,
            span=(0, 10),
            alternatives=[],
            processing_time_ms=50
        )
        
        assert self.backup_layer.validate_timezone_normalization(valid_result) is True
    
    def test_validate_timezone_normalization_naive_datetime(self):
        """Test timezone validation with naive datetime."""
        naive_result = FieldResult(
            value=datetime(2025, 10, 15, 14, 0),  # No timezone
            source="duckling",
            confidence=0.75,
            span=(0, 10),
            alternatives=[],
            processing_time_ms=50
        )
        
        assert self.backup_layer.validate_timezone_normalization(naive_result) is False
    
    def test_validate_timezone_normalization_non_datetime(self):
        """Test timezone validation with non-datetime value."""
        non_datetime_result = FieldResult(
            value="not a datetime",
            source="duckling",
            confidence=0.75,
            span=(0, 10),
            alternatives=[],
            processing_time_ms=50
        )
        
        # Non-datetime values should pass validation (they don't need timezone)
        assert self.backup_layer.validate_timezone_normalization(non_datetime_result) is True
    
    def test_validate_timezone_normalization_invalid_offset(self):
        """Test timezone validation with invalid timezone offset."""
        # Create a mock datetime with invalid timezone offset
        mock_dt = Mock(spec=datetime)
        mock_dt.tzinfo = Mock()
        mock_dt.tzinfo.tzname.return_value = "INVALID"
        mock_dt.tzinfo.utcoffset.return_value = timedelta(hours=25)  # Invalid offset
        
        invalid_result = FieldResult(
            value=mock_dt,
            source="duckling",
            confidence=0.75,
            span=(0, 10),
            alternatives=[],
            processing_time_ms=50
        )
        
        assert self.backup_layer.validate_timezone_normalization(invalid_result) is False
    
    def test_extract_multiple_fields(self):
        """Test extracting multiple fields."""
        with patch.object(self.backup_layer, 'extract_with_backup') as mock_extract:
            # Mock different results for different fields
            def mock_extract_side_effect(text, field):
                if field == "start_datetime":
                    return FieldResult(
                        value=datetime(2025, 10, 15, 14, 0, tzinfo=timezone.utc),
                        source="duckling",
                        confidence=0.75,
                        span=(0, 10),
                        alternatives=[],
                        processing_time_ms=50
                    )
                elif field == "end_datetime":
                    return FieldResult(
                        value=datetime(2025, 10, 15, 15, 0, tzinfo=timezone.utc),
                        source="recognizers",
                        confidence=0.70,
                        span=(15, 25),
                        alternatives=[],
                        processing_time_ms=60
                    )
                else:
                    return FieldResult(
                        value=None,
                        source="deterministic_backup",
                        confidence=0.0,
                        span=(0, 0),
                        alternatives=[],
                        processing_time_ms=10
                    )
            
            mock_extract.side_effect = mock_extract_side_effect
            
            # Test multiple field extraction
            fields = ["start_datetime", "end_datetime", "location"]
            results = self.backup_layer.extract_multiple_fields("meeting tomorrow 2-3pm", fields)
            
            assert len(results) == 3
            assert results["start_datetime"].value is not None
            assert results["end_datetime"].value is not None
            assert results["location"].value is None
            
            # Verify extract_with_backup was called for each field
            assert mock_extract.call_count == 3
    
    def test_is_available(self):
        """Test service availability check."""
        with patch.object(self.backup_layer.duckling_extractor, 'is_service_available', return_value=True), \
             patch.object(self.backup_layer.recognizers_extractor, 'is_service_available', return_value=False):
            
            assert self.backup_layer.is_available() is True
        
        with patch.object(self.backup_layer.duckling_extractor, 'is_service_available', return_value=False), \
             patch.object(self.backup_layer.recognizers_extractor, 'is_service_available', return_value=False):
            
            assert self.backup_layer.is_available() is False
    
    def test_get_service_status(self):
        """Test getting service status."""
        with patch.object(self.backup_layer.duckling_extractor, 'is_service_available', return_value=True), \
             patch.object(self.backup_layer.recognizers_extractor, 'is_service_available', return_value=False):
            
            status = self.backup_layer.get_service_status()
            
            assert status['duckling'] is True
            assert status['recognizers'] is False
            assert status['overall'] is True
    
    def test_performance_stats_tracking(self):
        """Test performance statistics tracking."""
        # Initial stats should be zero
        stats = self.backup_layer.get_performance_stats()
        assert stats['total_calls'] == 0
        assert stats['success_rate'] == 0.0
        
        # Mock successful extraction
        with patch.object(self.backup_layer.duckling_extractor, 'is_service_available', return_value=True), \
             patch.object(self.backup_layer.duckling_extractor, 'extract_with_duckling') as mock_duckling, \
             patch.object(self.backup_layer.recognizers_extractor, 'is_service_available', return_value=False):
            
            mock_duckling.return_value = FieldResult(
                value=datetime(2025, 10, 15, 14, 0, tzinfo=timezone.utc),
                source="duckling",
                confidence=0.75,
                span=(0, 10),
                alternatives=[],
                processing_time_ms=50
            )
            
            # Perform extraction
            self.backup_layer.extract_with_backup("tomorrow at 2pm", "datetime")
            
            # Check updated stats
            stats = self.backup_layer.get_performance_stats()
            assert stats['duckling_calls'] == 1
            assert stats['successful_extractions'] == 1
            assert stats['success_rate'] == 1.0
            assert stats['avg_processing_time_ms'] > 0
    
    def test_reset_performance_stats(self):
        """Test resetting performance statistics."""
        # Manually set some stats
        self.backup_layer._performance_stats['duckling_calls'] = 5
        self.backup_layer._performance_stats['successful_extractions'] = 3
        
        # Reset stats
        self.backup_layer.reset_performance_stats()
        
        # Verify reset
        stats = self.backup_layer.get_performance_stats()
        assert stats['total_calls'] == 0
        assert stats['successful_extractions'] == 0
        assert stats['success_rate'] == 0.0
    
    def test_create_fallback_result(self):
        """Test creating fallback result when all methods fail."""
        result = self.backup_layer.create_fallback_result("some text", "datetime", 100)
        
        assert result.value is None
        assert result.source == "deterministic_backup_failed"
        assert result.confidence == 0.0
        assert result.span == (0, 0)
        assert result.processing_time_ms == 100
    
    def test_get_text_hash(self):
        """Test text hashing for caching support."""
        text1 = "Meeting tomorrow at 2pm"
        text2 = "meeting tomorrow at 2pm"  # Different case
        text3 = "  Meeting tomorrow at 2pm  "  # Extra whitespace
        text4 = "Different text entirely"
        
        hash1 = self.backup_layer.get_text_hash(text1)
        hash2 = self.backup_layer.get_text_hash(text2)
        hash3 = self.backup_layer.get_text_hash(text3)
        hash4 = self.backup_layer.get_text_hash(text4)
        
        # Same content should produce same hash (case and whitespace normalized)
        assert hash1 == hash2 == hash3
        
        # Different content should produce different hash
        assert hash1 != hash4
        
        # Hash should be reasonable length
        assert len(hash1) == 16
    
    def test_calculate_candidate_score(self):
        """Test candidate scoring logic."""
        # High quality candidate
        good_candidate = FieldResult(
            value=datetime(2025, 10, 15, 14, 0, tzinfo=timezone.utc),
            source="duckling",
            confidence=0.8,
            span=(0, 8),  # Short, specific span
            alternatives=[],
            processing_time_ms=50
        )
        
        # Lower quality candidate
        poor_candidate = FieldResult(
            value=datetime(2025, 10, 15, 14, 0, tzinfo=timezone.utc),
            source="recognizers",
            confidence=0.6,
            span=(0, 20),  # Long span
            alternatives=[],
            processing_time_ms=100
        )
        
        text = "tomorrow at 2pm"
        
        good_score = self.backup_layer._calculate_candidate_score(good_candidate, text, "datetime")
        poor_score = self.backup_layer._calculate_candidate_score(poor_candidate, text, "datetime")
        
        # Good candidate should score higher
        assert good_score > poor_score
        
        # Scores should be reasonable (0.0 to 1.0 range)
        assert 0.0 <= good_score <= 1.0
        assert 0.0 <= poor_score <= 1.0
    
    def test_span_score_calculation(self):
        """Test span quality scoring."""
        text = "meeting tomorrow at 2pm"
        
        # Optimal span (short and specific)
        optimal_score = self.backup_layer._calculate_span_score((12, 22), text)  # "at 2pm"
        
        # Too short span
        short_score = self.backup_layer._calculate_span_score((12, 13), text)  # "a"
        
        # Very long span
        long_score = self.backup_layer._calculate_span_score((0, len(text)), text)  # Entire text
        
        # Invalid span
        invalid_score = self.backup_layer._calculate_span_score((25, 30), text)  # Beyond text
        
        assert optimal_score > short_score
        assert optimal_score > long_score
        assert invalid_score == 0.0
    
    def test_source_score_calculation(self):
        """Test source reliability scoring."""
        duckling_score = self.backup_layer._calculate_source_score("duckling")
        recognizers_score = self.backup_layer._calculate_source_score("recognizers")
        unknown_score = self.backup_layer._calculate_source_score("unknown")
        
        # Duckling should be preferred
        assert duckling_score > recognizers_score
        assert recognizers_score > unknown_score
        
        # All scores should be valid
        assert 0.0 <= duckling_score <= 1.0
        assert 0.0 <= recognizers_score <= 1.0
        assert 0.0 <= unknown_score <= 1.0
    
    def test_value_score_calculation(self):
        """Test value quality scoring."""
        # Reasonable datetime
        good_datetime = datetime(2025, 10, 15, 14, 0, tzinfo=timezone.utc)
        good_score = self.backup_layer._calculate_value_score(good_datetime, "datetime")
        
        # Very old datetime
        old_datetime = datetime(1990, 1, 1, 14, 0, tzinfo=timezone.utc)
        old_score = self.backup_layer._calculate_value_score(old_datetime, "datetime")
        
        # Very future datetime
        future_datetime = datetime(2030, 1, 1, 14, 0, tzinfo=timezone.utc)
        future_score = self.backup_layer._calculate_value_score(future_datetime, "datetime")
        
        # None value
        none_score = self.backup_layer._calculate_value_score(None, "datetime")
        
        assert good_score > old_score
        assert good_score > future_score
        assert future_score > old_score  # Future is better than very old
        assert none_score == 0.0
    
    @patch('services.deterministic_backup_layer.DucklingExtractor')
    @patch('services.deterministic_backup_layer.RecognizersExtractor')
    def test_timezone_normalization_integration(self, mock_recognizers_class, mock_duckling_class):
        """Test timezone normalization during extraction."""
        # Mock Duckling to return naive datetime
        mock_duckling = Mock()
        mock_duckling.is_service_available.return_value = True
        mock_duckling.extract_with_duckling.return_value = FieldResult(
            value=datetime(2025, 10, 15, 14, 0),  # Naive datetime
            source="duckling",
            confidence=0.75,
            span=(0, 10),
            alternatives=[],
            processing_time_ms=50
        )
        mock_duckling_class.return_value = mock_duckling
        
        # Mock Recognizers as unavailable
        mock_recognizers = Mock()
        mock_recognizers.is_service_available.return_value = False
        mock_recognizers_class.return_value = mock_recognizers
        
        # Create backup layer
        backup_layer = DeterministicBackupLayer()
        
        # Test extraction - should normalize timezone
        result = backup_layer.extract_with_backup("tomorrow at 2pm", "datetime")
        
        assert result.value is not None
        assert isinstance(result.value, datetime)
        assert result.value.tzinfo is not None  # Should have timezone after normalization
        assert result.confidence < 0.75  # Should be slightly penalized for normalization


class TestDeterministicBackupLayerEdgeCases:
    """Test edge cases and error conditions for DeterministicBackupLayer."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.backup_layer = DeterministicBackupLayer()
    
    @patch('services.deterministic_backup_layer.DucklingExtractor')
    @patch('services.deterministic_backup_layer.RecognizersExtractor')
    def test_extraction_with_exception(self, mock_recognizers_class, mock_duckling_class):
        """Test extraction when extractors raise exceptions."""
        # Mock Duckling to raise exception
        mock_duckling = Mock()
        mock_duckling.is_service_available.return_value = True
        mock_duckling.extract_with_duckling.side_effect = Exception("Duckling error")
        mock_duckling_class.return_value = mock_duckling
        
        # Mock Recognizers as unavailable
        mock_recognizers = Mock()
        mock_recognizers.is_service_available.return_value = False
        mock_recognizers_class.return_value = mock_recognizers
        
        # Create backup layer
        backup_layer = DeterministicBackupLayer()
        
        # Test extraction - should handle exception gracefully
        result = backup_layer.extract_with_backup("tomorrow at 2pm", "datetime")
        
        assert result.value is None
        assert result.source == "deterministic_backup"
        assert result.confidence == 0.0
    
    def test_choose_best_span_with_identical_values(self):
        """Test choosing best span when candidates have identical values."""
        # Two candidates with same value but different sources
        candidate1 = FieldResult(
            value=datetime(2025, 10, 15, 14, 0, tzinfo=timezone.utc),
            source="duckling",
            confidence=0.75,
            span=(0, 8),
            alternatives=[],
            processing_time_ms=50
        )
        
        candidate2 = FieldResult(
            value=datetime(2025, 10, 15, 14, 0, tzinfo=timezone.utc),  # Same value
            source="recognizers",
            confidence=0.70,
            span=(0, 10),
            alternatives=[],
            processing_time_ms=60
        )
        
        candidates = [candidate1, candidate2]
        result = self.backup_layer.choose_best_span(candidates, "tomorrow at 2pm", "datetime")
        
        # Should prefer higher confidence (Duckling)
        assert result.source == "duckling"
        assert result.confidence == 0.75
        
        # Should not include identical value in alternatives
        assert len(result.alternatives) == 0
    
    def test_performance_stats_with_zero_calls(self):
        """Test performance stats calculation with zero calls."""
        stats = self.backup_layer.get_performance_stats()
        
        assert stats['total_calls'] == 0
        assert stats['success_rate'] == 0.0
        assert stats['avg_processing_time_ms'] == 0.0
    
    def test_text_hash_with_empty_string(self):
        """Test text hashing with empty string."""
        hash_result = self.backup_layer.get_text_hash("")
        
        assert isinstance(hash_result, str)
        assert len(hash_result) == 16
    
    def test_text_hash_with_unicode(self):
        """Test text hashing with unicode characters."""
        unicode_text = "Meeting tomorrow at 2pm 🕐"
        hash_result = self.backup_layer.get_text_hash(unicode_text)
        
        assert isinstance(hash_result, str)
        assert len(hash_result) == 16
    
    def test_validate_timezone_with_custom_timezone(self):
        """Test timezone validation with custom timezone."""
        # Create custom timezone
        custom_tz = timezone(timedelta(hours=5))
        
        custom_result = FieldResult(
            value=datetime(2025, 10, 15, 14, 0, tzinfo=custom_tz),
            source="duckling",
            confidence=0.75,
            span=(0, 10),
            alternatives=[],
            processing_time_ms=50
        )
        
        assert self.backup_layer.validate_timezone_normalization(custom_result) is True


if __name__ == "__main__":
    pytest.main([__file__])