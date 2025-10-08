"""
Unit tests for enhanced event models with per-field confidence tracking.
Tests serialization, validation, and new functionality.
"""

import pytest
from datetime import datetime, timedelta
from models.event_models import (
    FieldResult, RecurrenceResult, DurationResult, CacheEntry, AuditData,
    ParsedEvent, ValidationResult
)


class TestFieldResult:
    """Test FieldResult class functionality."""
    
    def test_field_result_creation(self):
        """Test basic FieldResult creation and validation."""
        result = FieldResult(
            value="Meeting with team",
            source="regex",
            confidence=0.85,
            span=(10, 25),
            alternatives=["Team meeting", "Meeting"],
            processing_time_ms=150
        )
        
        assert result.value == "Meeting with team"
        assert result.source == "regex"
        assert result.confidence == 0.85
        assert result.span == (10, 25)
        assert len(result.alternatives) == 2
        assert result.processing_time_ms == 150
    
    def test_field_result_confidence_normalization(self):
        """Test confidence score normalization to 0.0-1.0 range."""
        # Test upper bound
        result = FieldResult(value="test", source="llm", confidence=1.5, span=(0, 4))
        assert result.confidence == 1.0
        
        # Test lower bound
        result = FieldResult(value="test", source="llm", confidence=-0.5, span=(0, 4))
        assert result.confidence == 0.0
        
        # Test valid range
        result = FieldResult(value="test", source="llm", confidence=0.7, span=(0, 4))
        assert result.confidence == 0.7
    
    def test_field_result_processing_time_validation(self):
        """Test processing time validation (non-negative)."""
        result = FieldResult(value="test", source="regex", confidence=0.8, span=(0, 4), processing_time_ms=-10)
        assert result.processing_time_ms == 0
    
    def test_field_result_serialization(self):
        """Test FieldResult to_dict and from_dict methods."""
        original = FieldResult(
            value="Conference Room A",
            source="duckling",
            confidence=0.75,
            span=(15, 32),
            alternatives=["Room A", "Conference A"],
            processing_time_ms=200
        )
        
        # Test serialization
        data = original.to_dict()
        expected_keys = {'value', 'source', 'confidence', 'span', 'alternatives', 'processing_time_ms'}
        assert set(data.keys()) == expected_keys
        
        # Test deserialization
        restored = FieldResult.from_dict(data)
        assert restored.value == original.value
        assert restored.source == original.source
        assert restored.confidence == original.confidence
        assert restored.span == original.span
        assert restored.alternatives == original.alternatives
        assert restored.processing_time_ms == original.processing_time_ms


class TestRecurrenceResult:
    """Test RecurrenceResult class functionality."""
    
    def test_recurrence_result_creation(self):
        """Test basic RecurrenceResult creation."""
        result = RecurrenceResult(
            rrule="FREQ=WEEKLY;INTERVAL=2;BYDAY=TU",
            natural_language="every other Tuesday",
            confidence=0.9,
            pattern_type="weekly"
        )
        
        assert result.rrule == "FREQ=WEEKLY;INTERVAL=2;BYDAY=TU"
        assert result.natural_language == "every other Tuesday"
        assert result.confidence == 0.9
        assert result.pattern_type == "weekly"
    
    def test_recurrence_result_confidence_normalization(self):
        """Test confidence score normalization."""
        result = RecurrenceResult(confidence=1.5)
        assert result.confidence == 1.0
        
        result = RecurrenceResult(confidence=-0.2)
        assert result.confidence == 0.0
    
    def test_recurrence_result_text_cleanup(self):
        """Test natural language text cleanup."""
        result = RecurrenceResult(natural_language="  every Tuesday  ")
        assert result.natural_language == "every Tuesday"
    
    def test_recurrence_result_serialization(self):
        """Test RecurrenceResult serialization."""
        original = RecurrenceResult(
            rrule="FREQ=DAILY;COUNT=5",
            natural_language="daily for 5 days",
            confidence=0.8,
            pattern_type="daily"
        )
        
        data = original.to_dict()
        restored = RecurrenceResult.from_dict(data)
        
        assert restored.rrule == original.rrule
        assert restored.natural_language == original.natural_language
        assert restored.confidence == original.confidence
        assert restored.pattern_type == original.pattern_type


class TestDurationResult:
    """Test DurationResult class functionality."""
    
    def test_duration_result_creation(self):
        """Test basic DurationResult creation."""
        end_time = datetime(2025, 10, 15, 15, 0)
        result = DurationResult(
            duration_minutes=90,
            end_time_override=end_time,
            all_day=False,
            confidence=0.85
        )
        
        assert result.duration_minutes == 90
        assert result.end_time_override == end_time
        assert result.all_day is False
        assert result.confidence == 0.85
    
    def test_duration_result_validation(self):
        """Test duration validation (non-negative)."""
        result = DurationResult(duration_minutes=-30)
        assert result.duration_minutes == 0
    
    def test_duration_result_serialization(self):
        """Test DurationResult serialization with datetime handling."""
        end_time = datetime(2025, 10, 15, 17, 30)
        original = DurationResult(
            duration_minutes=120,
            end_time_override=end_time,
            all_day=True,
            confidence=0.7
        )
        
        data = original.to_dict()
        restored = DurationResult.from_dict(data)
        
        assert restored.duration_minutes == original.duration_minutes
        assert restored.end_time_override == original.end_time_override
        assert restored.all_day == original.all_day
        assert restored.confidence == original.confidence


class TestCacheEntry:
    """Test CacheEntry class functionality."""
    
    def test_cache_entry_creation(self):
        """Test basic CacheEntry creation."""
        parsed_event = ParsedEvent(title="Test Event", confidence_score=0.8)
        timestamp = datetime.now()
        
        entry = CacheEntry(
            text_hash="abc123",
            result=parsed_event,
            timestamp=timestamp,
            hit_count=5
        )
        
        assert entry.text_hash == "abc123"
        assert entry.result == parsed_event
        assert entry.timestamp == timestamp
        assert entry.hit_count == 5
    
    def test_cache_entry_expiration(self):
        """Test cache entry expiration logic."""
        parsed_event = ParsedEvent(title="Test Event")
        
        # Fresh entry (not expired)
        fresh_entry = CacheEntry(
            text_hash="fresh",
            result=parsed_event,
            timestamp=datetime.now()
        )
        assert not fresh_entry.is_expired()
        
        # Old entry (expired)
        old_timestamp = datetime.now() - timedelta(hours=25)
        old_entry = CacheEntry(
            text_hash="old",
            result=parsed_event,
            timestamp=old_timestamp
        )
        assert old_entry.is_expired()
        
        # Custom TTL
        recent_timestamp = datetime.now() - timedelta(hours=2)
        recent_entry = CacheEntry(
            text_hash="recent",
            result=parsed_event,
            timestamp=recent_timestamp
        )
        assert not recent_entry.is_expired(ttl_hours=24)
        assert recent_entry.is_expired(ttl_hours=1)
    
    def test_cache_entry_hit_count(self):
        """Test hit count increment functionality."""
        parsed_event = ParsedEvent(title="Test Event")
        entry = CacheEntry(
            text_hash="test",
            result=parsed_event,
            timestamp=datetime.now()
        )
        
        assert entry.hit_count == 0
        entry.increment_hit_count()
        assert entry.hit_count == 1
        entry.increment_hit_count()
        assert entry.hit_count == 2


class TestAuditData:
    """Test AuditData class functionality."""
    
    def test_audit_data_creation(self):
        """Test basic AuditData creation."""
        audit = AuditData(
            field_routing_decisions={"title": "regex", "start_datetime": "llm"},
            confidence_breakdown={"title": 0.9, "start_datetime": 0.4},
            processing_times={"regex": 50, "llm": 1200},
            fallback_triggers=["regex_failed", "low_confidence"],
            cache_status="hit"
        )
        
        assert audit.field_routing_decisions["title"] == "regex"
        assert audit.confidence_breakdown["title"] == 0.9
        assert audit.processing_times["llm"] == 1200
        assert "regex_failed" in audit.fallback_triggers
        assert audit.cache_status == "hit"
    
    def test_audit_data_methods(self):
        """Test AuditData helper methods."""
        audit = AuditData()
        
        # Test routing decision
        audit.add_routing_decision("location", "duckling")
        assert audit.field_routing_decisions["location"] == "duckling"
        
        # Test confidence score
        audit.add_confidence_score("location", 0.75)
        assert audit.confidence_breakdown["location"] == 0.75
        
        # Test processing time
        audit.add_processing_time("duckling", 300)
        assert audit.processing_times["duckling"] == 300
        
        # Test fallback trigger (no duplicates)
        audit.add_fallback_trigger("timeout")
        audit.add_fallback_trigger("timeout")  # Should not duplicate
        assert audit.fallback_triggers.count("timeout") == 1
    
    def test_audit_data_serialization(self):
        """Test AuditData serialization."""
        original = AuditData(
            field_routing_decisions={"title": "regex"},
            confidence_breakdown={"title": 0.85},
            processing_times={"regex": 100},
            fallback_triggers=["none"],
            cache_status="miss"
        )
        
        data = original.to_dict()
        restored = AuditData.from_dict(data)
        
        assert restored.field_routing_decisions == original.field_routing_decisions
        assert restored.confidence_breakdown == original.confidence_breakdown
        assert restored.processing_times == original.processing_times
        assert restored.fallback_triggers == original.fallback_triggers
        assert restored.cache_status == original.cache_status


class TestEnhancedParsedEvent:
    """Test enhanced ParsedEvent class functionality."""
    
    def test_parsed_event_creation_with_field_results(self):
        """Test ParsedEvent creation with field results."""
        title_result = FieldResult(
            value="Team Meeting",
            source="regex",
            confidence=0.9,
            span=(0, 12)
        )
        
        datetime_result = FieldResult(
            value=datetime(2025, 10, 15, 14, 0),
            source="regex",
            confidence=0.85,
            span=(13, 25)
        )
        
        event = ParsedEvent(
            title="Team Meeting",
            start_datetime=datetime(2025, 10, 15, 14, 0),
            end_datetime=datetime(2025, 10, 15, 15, 0),
            confidence_score=0.87,
            field_results={
                "title": title_result,
                "start_datetime": datetime_result
            },
            parsing_path="regex_primary",
            processing_time_ms=250,
            cache_hit=False,
            needs_confirmation=False
        )
        
        assert event.title == "Team Meeting"
        assert event.confidence_score == 0.87
        assert event.field_results["title"].confidence == 0.9
        assert event.parsing_path == "regex_primary"
        assert event.processing_time_ms == 250
        assert not event.cache_hit
        assert not event.needs_confirmation
    
    def test_parsed_event_with_recurrence_and_participants(self):
        """Test ParsedEvent with new fields (recurrence, participants)."""
        event = ParsedEvent(
            title="Weekly Standup",
            recurrence="FREQ=WEEKLY;BYDAY=MO",
            participants=["alice@example.com", "bob@example.com"],
            all_day=False
        )
        
        assert event.recurrence == "FREQ=WEEKLY;BYDAY=MO"
        assert len(event.participants) == 2
        assert "alice@example.com" in event.participants


class TestEnhancedValidationResult:
    """Test enhanced ValidationResult class functionality."""
    
    def test_validation_result_field_warnings(self):
        """Test field-specific warning functionality."""
        result = ValidationResult(is_valid=True)
        
        result.add_field_warning("title", "Title seems incomplete")
        result.add_field_warning("title", "Title contains typos")
        result.add_field_warning("location", "Location is ambiguous")
        
        assert len(result.field_warnings["title"]) == 2
        assert len(result.field_warnings["location"]) == 1
        assert "Title seems incomplete" in result.field_warnings["title"]
        
        # Test no duplicates
        result.add_field_warning("title", "Title seems incomplete")
        assert len(result.field_warnings["title"]) == 2
    
    def test_validation_result_field_suggestions(self):
        """Test field-specific suggestion functionality."""
        result = ValidationResult(is_valid=True)
        
        result.add_field_suggestion("start_datetime", "Consider specifying AM/PM")
        result.add_field_suggestion("location", "Try 'Conference Room A'")
        
        assert len(result.field_suggestions["start_datetime"]) == 1
        assert len(result.field_suggestions["location"]) == 1
        assert "Consider specifying AM/PM" in result.field_suggestions["start_datetime"]
    
    def test_validation_result_confidence_issues(self):
        """Test confidence issue tracking."""
        result = ValidationResult(is_valid=True)
        
        # Low confidence should add warning
        result.add_confidence_issue("title", 0.4)
        assert "title" in result.confidence_issues
        assert result.confidence_issues["title"] == 0.4
        assert len(result.field_warnings["title"]) == 1
        assert "Low confidence" in result.field_warnings["title"][0]
        
        # High confidence should not add warning
        result.add_confidence_issue("location", 0.8)
        assert "location" not in result.confidence_issues
    
    def test_validation_result_get_field_issues(self):
        """Test getting all issues for a specific field."""
        result = ValidationResult(is_valid=True)
        
        result.add_field_warning("title", "Warning 1")
        result.add_field_warning("title", "Warning 2")
        result.add_field_suggestion("title", "Suggestion 1")
        
        issues = result.get_field_issues("title")
        assert len(issues["warnings"]) == 2
        assert len(issues["suggestions"]) == 1
        assert "Warning 1" in issues["warnings"]
        assert "Suggestion 1" in issues["suggestions"]
        
        # Test field with no issues
        empty_issues = result.get_field_issues("nonexistent")
        assert len(empty_issues["warnings"]) == 0
        assert len(empty_issues["suggestions"]) == 0
    
    def test_validation_result_enhanced_serialization(self):
        """Test enhanced ValidationResult serialization."""
        result = ValidationResult(
            is_valid=False,
            missing_fields=["start_datetime"],
            warnings=["General warning"],
            suggestions=["General suggestion"]
        )
        
        result.add_field_warning("title", "Field warning")
        result.add_field_suggestion("location", "Field suggestion")
        result.add_confidence_issue("title", 0.3)
        
        data = result.to_dict()
        restored = ValidationResult.from_dict(data)
        
        # Test basic fields
        assert restored.is_valid == result.is_valid
        assert restored.missing_fields == result.missing_fields
        assert restored.warnings == result.warnings
        assert restored.suggestions == result.suggestions
        
        # Test enhanced fields
        assert restored.field_warnings == result.field_warnings
        assert restored.field_suggestions == result.field_suggestions
        assert restored.confidence_issues == result.confidence_issues


if __name__ == "__main__":
    pytest.main([__file__])


class TestEnhancedParsedEventMethods:
    """Test enhanced ParsedEvent methods and functionality."""
    
    def test_parsed_event_get_field_confidence(self):
        """Test getting field confidence scores."""
        title_result = FieldResult(
            value="Meeting",
            source="regex",
            confidence=0.9,
            span=(0, 7)
        )
        
        event = ParsedEvent(
            title="Meeting",
            confidence_score=0.7,
            field_results={"title": title_result}
        )
        
        # Should return field-specific confidence
        assert event.get_field_confidence("title") == 0.9
        
        # Should return overall confidence for missing field
        assert event.get_field_confidence("location") == 0.7
    
    def test_parsed_event_set_field_result(self):
        """Test setting field results."""
        event = ParsedEvent(title="Test Event")
        
        location_result = FieldResult(
            value="Conference Room A",
            source="duckling",
            confidence=0.8,
            span=(15, 32)
        )
        
        event.set_field_result("location", location_result)
        assert "location" in event.field_results
        assert event.field_results["location"].value == "Conference Room A"
        assert event.field_results["location"].confidence == 0.8
    
    def test_parsed_event_add_warning(self):
        """Test adding warnings to extraction metadata."""
        event = ParsedEvent(title="Test Event")
        
        event.add_warning("Date is ambiguous")
        event.add_warning("Location not found")
        event.add_warning("Date is ambiguous")  # Should not duplicate
        
        warnings = event.extraction_metadata.get('warnings', [])
        assert len(warnings) == 2
        assert "Date is ambiguous" in warnings
        assert "Location not found" in warnings
    
    def test_parsed_event_should_confirm(self):
        """Test confirmation requirement logic."""
        # High confidence event - should not need confirmation
        high_conf_event = ParsedEvent(
            title="Meeting",
            confidence_score=0.9,
            field_results={
                "title": FieldResult(value="Meeting", source="regex", confidence=0.9, span=(0, 7)),
                "start_datetime": FieldResult(value=datetime.now(), source="regex", confidence=0.85, span=(8, 20))
            }
        )
        assert not high_conf_event.should_confirm()
        
        # Low overall confidence - should need confirmation
        low_conf_event = ParsedEvent(
            title="Meeting",
            confidence_score=0.4
        )
        assert low_conf_event.should_confirm()
        
        # Low field confidence - should need confirmation
        low_field_conf_event = ParsedEvent(
            title="Meeting",
            confidence_score=0.8,
            field_results={
                "title": FieldResult(value="Meeting", source="llm", confidence=0.3, span=(0, 7))
            }
        )
        assert low_field_conf_event.should_confirm()
        
        # Explicitly marked for confirmation
        explicit_conf_event = ParsedEvent(
            title="Meeting",
            confidence_score=0.9,
            needs_confirmation=True
        )
        assert explicit_conf_event.should_confirm()
    
    def test_parsed_event_enhanced_serialization(self):
        """Test enhanced ParsedEvent serialization with all new fields."""
        title_result = FieldResult(
            value="Team Standup",
            source="regex",
            confidence=0.9,
            span=(0, 12),
            alternatives=["Standup Meeting"],
            processing_time_ms=50
        )
        
        datetime_result = FieldResult(
            value=datetime(2025, 10, 15, 9, 0),
            source="regex",
            confidence=0.85,
            span=(13, 25),
            processing_time_ms=75
        )
        
        original = ParsedEvent(
            title="Team Standup",
            start_datetime=datetime(2025, 10, 15, 9, 0),
            end_datetime=datetime(2025, 10, 15, 9, 30),
            location="Conference Room A",
            description="Daily team standup meeting",
            recurrence="FREQ=DAILY;BYDAY=MO,TU,WE,TH,FR",
            participants=["alice@example.com", "bob@example.com"],
            all_day=False,
            confidence_score=0.87,
            field_results={
                "title": title_result,
                "start_datetime": datetime_result
            },
            parsing_path="regex_primary",
            processing_time_ms=125,
            cache_hit=False,
            needs_confirmation=False,
            extraction_metadata={"source": "email", "warnings": ["No end time specified"]}
        )
        
        # Test serialization
        data = original.to_dict()
        
        # Verify all fields are present
        expected_keys = {
            'title', 'start_datetime', 'end_datetime', 'location', 'description',
            'recurrence', 'participants', 'all_day', 'confidence_score',
            'field_results', 'parsing_path', 'processing_time_ms', 'cache_hit',
            'needs_confirmation', 'extraction_metadata'
        }
        assert set(data.keys()) == expected_keys
        
        # Test deserialization
        restored = ParsedEvent.from_dict(data)
        
        # Verify basic fields
        assert restored.title == original.title
        assert restored.start_datetime == original.start_datetime
        assert restored.end_datetime == original.end_datetime
        assert restored.location == original.location
        assert restored.description == original.description
        assert restored.recurrence == original.recurrence
        assert restored.participants == original.participants
        assert restored.all_day == original.all_day
        assert restored.confidence_score == original.confidence_score
        
        # Verify enhanced fields
        assert restored.parsing_path == original.parsing_path
        assert restored.processing_time_ms == original.processing_time_ms
        assert restored.cache_hit == original.cache_hit
        assert restored.needs_confirmation == original.needs_confirmation
        assert restored.extraction_metadata == original.extraction_metadata
        
        # Verify field results
        assert len(restored.field_results) == 2
        assert "title" in restored.field_results
        assert "start_datetime" in restored.field_results
        assert restored.field_results["title"].value == "Team Standup"
        assert restored.field_results["title"].confidence == 0.9
        assert restored.field_results["start_datetime"].confidence == 0.85


class TestDataModelIntegration:
    """Test integration between different enhanced data models."""
    
    def test_parsed_event_with_all_enhanced_models(self):
        """Test ParsedEvent integration with all new model types."""
        # Create field results
        title_result = FieldResult(
            value="Weekly Team Meeting",
            source="regex",
            confidence=0.9,
            span=(0, 19),
            processing_time_ms=25
        )
        
        datetime_result = FieldResult(
            value=datetime(2025, 10, 15, 14, 0),
            source="regex",
            confidence=0.85,
            span=(20, 35),
            processing_time_ms=50
        )
        
        location_result = FieldResult(
            value="Conference Room B",
            source="duckling",
            confidence=0.75,
            span=(36, 53),
            processing_time_ms=150
        )
        
        # Create ParsedEvent with comprehensive field results
        event = ParsedEvent(
            title="Weekly Team Meeting",
            start_datetime=datetime(2025, 10, 15, 14, 0),
            end_datetime=datetime(2025, 10, 15, 15, 0),
            location="Conference Room B",
            description="Weekly team sync and planning session",
            recurrence="FREQ=WEEKLY;BYDAY=TU",
            participants=["team@example.com"],
            all_day=False,
            confidence_score=0.83,
            field_results={
                "title": title_result,
                "start_datetime": datetime_result,
                "location": location_result
            },
            parsing_path="regex_with_duckling_backup",
            processing_time_ms=225,
            cache_hit=False,
            needs_confirmation=False
        )
        
        # Test validation with enhanced ValidationResult
        validation = ValidationResult(is_valid=True)
        validation.add_field_warning("location", "Location confidence is moderate")
        validation.add_confidence_issue("location", 0.5)  # Below threshold to trigger warning
        
        # Test audit data creation
        audit = AuditData()
        audit.add_routing_decision("title", "regex")
        audit.add_routing_decision("start_datetime", "regex")
        audit.add_routing_decision("location", "duckling")
        audit.add_confidence_score("title", 0.9)
        audit.add_confidence_score("start_datetime", 0.85)
        audit.add_confidence_score("location", 0.75)
        audit.add_processing_time("regex", 75)
        audit.add_processing_time("duckling", 150)
        audit.cache_status = "miss"
        
        # Test cache entry creation
        cache_entry = CacheEntry(
            text_hash="abc123def456",
            result=event,
            timestamp=datetime.now()
        )
        
        # Verify integration works
        assert event.get_field_confidence("title") == 0.9
        assert event.get_field_confidence("location") == 0.75
        assert not event.should_confirm()  # High enough confidence
        
        assert len(validation.field_warnings["location"]) == 2  # Warning + confidence issue
        assert "location" in validation.confidence_issues
        
        assert audit.field_routing_decisions["location"] == "duckling"
        assert audit.processing_times["duckling"] == 150
        
        assert not cache_entry.is_expired()
        assert cache_entry.result.title == event.title
    
    def test_serialization_roundtrip_integration(self):
        """Test complete serialization roundtrip with all models."""
        # Create complex ParsedEvent
        event = ParsedEvent(
            title="Complex Event",
            start_datetime=datetime(2025, 10, 15, 10, 0),
            end_datetime=datetime(2025, 10, 15, 11, 30),
            recurrence="FREQ=WEEKLY;INTERVAL=2",
            participants=["user1@example.com", "user2@example.com"],
            field_results={
                "title": FieldResult(
                    value="Complex Event",
                    source="llm",
                    confidence=0.7,
                    span=(0, 13),
                    alternatives=["Event", "Meeting"],
                    processing_time_ms=1200
                )
            },
            parsing_path="llm_fallback",
            processing_time_ms=1500,
            needs_confirmation=True
        )
        
        # Create ValidationResult
        validation = ValidationResult(is_valid=False)
        validation.add_missing_field("location")
        validation.add_field_warning("title", "Generated by LLM")
        validation.add_confidence_issue("title", 0.5)  # Below threshold to trigger warning
        
        # Create AuditData
        audit = AuditData(
            field_routing_decisions={"title": "llm"},
            confidence_breakdown={"title": 0.7},
            processing_times={"llm": 1200},
            fallback_triggers=["regex_failed"],
            cache_status="miss"
        )
        
        # Serialize all
        event_data = event.to_dict()
        validation_data = validation.to_dict()
        audit_data = audit.to_dict()
        
        # Deserialize all
        restored_event = ParsedEvent.from_dict(event_data)
        restored_validation = ValidationResult.from_dict(validation_data)
        restored_audit = AuditData.from_dict(audit_data)
        
        # Verify event restoration
        assert restored_event.title == event.title
        assert restored_event.recurrence == event.recurrence
        assert restored_event.participants == event.participants
        assert restored_event.parsing_path == event.parsing_path
        assert restored_event.needs_confirmation == event.needs_confirmation
        assert len(restored_event.field_results) == 1
        assert restored_event.field_results["title"].confidence == 0.7
        assert len(restored_event.field_results["title"].alternatives) == 2
        
        # Verify validation restoration
        assert not restored_validation.is_valid
        assert "location" in restored_validation.missing_fields
        assert len(restored_validation.field_warnings["title"]) == 2
        assert "title" in restored_validation.confidence_issues
        
        # Verify audit restoration
        assert restored_audit.field_routing_decisions["title"] == "llm"
        assert restored_audit.confidence_breakdown["title"] == 0.7
        assert "regex_failed" in restored_audit.fallback_triggers
        assert restored_audit.cache_status == "miss"