"""
Unit tests for event data models.
"""

import unittest
from datetime import datetime, timedelta
from models.event_models import ParsedEvent, Event, ValidationResult


class TestParsedEvent(unittest.TestCase):
    """Test cases for ParsedEvent model."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.sample_datetime = datetime(2024, 1, 15, 14, 30)
        self.sample_end_datetime = datetime(2024, 1, 15, 15, 30)
    
    def test_parsed_event_creation(self):
        """Test basic ParsedEvent creation."""
        event = ParsedEvent(
            title="Team Meeting",
            start_datetime=self.sample_datetime,
            end_datetime=self.sample_end_datetime,
            location="Conference Room A",
            description="Weekly team sync",
            confidence_score=0.85
        )
        
        self.assertEqual(event.title, "Team Meeting")
        self.assertEqual(event.start_datetime, self.sample_datetime)
        self.assertEqual(event.end_datetime, self.sample_end_datetime)
        self.assertEqual(event.location, "Conference Room A")
        self.assertEqual(event.description, "Weekly team sync")
        self.assertEqual(event.confidence_score, 0.85)
    
    def test_parsed_event_defaults(self):
        """Test ParsedEvent with default values."""
        event = ParsedEvent()
        
        self.assertIsNone(event.title)
        self.assertIsNone(event.start_datetime)
        self.assertIsNone(event.end_datetime)
        self.assertIsNone(event.location)
        self.assertEqual(event.description, "")
        self.assertEqual(event.confidence_score, 0.0)
        self.assertEqual(event.extraction_metadata, {})
    
    def test_is_complete_valid(self):
        """Test is_complete with valid data."""
        event = ParsedEvent(
            title="Meeting",
            start_datetime=self.sample_datetime
        )
        
        self.assertTrue(event.is_complete())
    
    def test_is_complete_missing_title(self):
        """Test is_complete with missing title."""
        event = ParsedEvent(start_datetime=self.sample_datetime)
        
        self.assertFalse(event.is_complete())
    
    def test_is_complete_missing_datetime(self):
        """Test is_complete with missing datetime."""
        event = ParsedEvent(title="Meeting")
        
        self.assertFalse(event.is_complete())
    
    def test_to_dict_serialization(self):
        """Test ParsedEvent serialization to dictionary."""
        event = ParsedEvent(
            title="Meeting",
            start_datetime=self.sample_datetime,
            end_datetime=self.sample_end_datetime,
            location="Room A",
            description="Test meeting",
            confidence_score=0.9,
            extraction_metadata={"source": "email"}
        )
        
        result = event.to_dict()
        
        self.assertEqual(result['title'], "Meeting")
        self.assertEqual(result['start_datetime'], self.sample_datetime.isoformat())
        self.assertEqual(result['end_datetime'], self.sample_end_datetime.isoformat())
        self.assertEqual(result['location'], "Room A")
        self.assertEqual(result['description'], "Test meeting")
        self.assertEqual(result['confidence_score'], 0.9)
        self.assertEqual(result['extraction_metadata'], {"source": "email"})
    
    def test_from_dict_deserialization(self):
        """Test ParsedEvent deserialization from dictionary."""
        data = {
            'title': 'Meeting',
            'start_datetime': self.sample_datetime.isoformat(),
            'end_datetime': self.sample_end_datetime.isoformat(),
            'location': 'Room A',
            'description': 'Test meeting',
            'confidence_score': 0.9,
            'extraction_metadata': {'source': 'email'}
        }
        
        event = ParsedEvent.from_dict(data)
        
        self.assertEqual(event.title, "Meeting")
        self.assertEqual(event.start_datetime, self.sample_datetime)
        self.assertEqual(event.end_datetime, self.sample_end_datetime)
        self.assertEqual(event.location, "Room A")
        self.assertEqual(event.description, "Test meeting")
        self.assertEqual(event.confidence_score, 0.9)
        self.assertEqual(event.extraction_metadata, {"source": "email"})


class TestEvent(unittest.TestCase):
    """Test cases for Event model."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.sample_datetime = datetime(2024, 1, 15, 14, 30)
        self.sample_end_datetime = datetime(2024, 1, 15, 15, 30)
    
    def test_event_creation(self):
        """Test basic Event creation."""
        event = Event(
            title="Team Meeting",
            start_datetime=self.sample_datetime,
            end_datetime=self.sample_end_datetime,
            location="Conference Room A",
            description="Weekly team sync"
        )
        
        self.assertEqual(event.title, "Team Meeting")
        self.assertEqual(event.start_datetime, self.sample_datetime)
        self.assertEqual(event.end_datetime, self.sample_end_datetime)
        self.assertEqual(event.location, "Conference Room A")
        self.assertEqual(event.description, "Weekly team sync")
        self.assertEqual(event.calendar_id, "default")
        self.assertIsInstance(event.created_at, datetime)
    
    def test_event_validation_empty_title(self):
        """Test Event validation with empty title."""
        with self.assertRaises(ValueError) as context:
            Event(
                title="",
                start_datetime=self.sample_datetime,
                end_datetime=self.sample_end_datetime
            )
        
        self.assertIn("title cannot be empty", str(context.exception))
    
    def test_event_validation_whitespace_title(self):
        """Test Event validation with whitespace-only title."""
        with self.assertRaises(ValueError) as context:
            Event(
                title="   ",
                start_datetime=self.sample_datetime,
                end_datetime=self.sample_end_datetime
            )
        
        self.assertIn("title cannot be empty", str(context.exception))
    
    def test_event_validation_invalid_time_order(self):
        """Test Event validation with start time after end time."""
        with self.assertRaises(ValueError) as context:
            Event(
                title="Meeting",
                start_datetime=self.sample_end_datetime,
                end_datetime=self.sample_datetime
            )
        
        self.assertIn("Start time must be before end time", str(context.exception))
    
    def test_event_validation_same_start_end_time(self):
        """Test Event validation with same start and end time."""
        with self.assertRaises(ValueError) as context:
            Event(
                title="Meeting",
                start_datetime=self.sample_datetime,
                end_datetime=self.sample_datetime
            )
        
        self.assertIn("Start time must be before end time", str(context.exception))
    
    def test_duration_minutes(self):
        """Test duration calculation in minutes."""
        event = Event(
            title="Meeting",
            start_datetime=self.sample_datetime,
            end_datetime=self.sample_end_datetime
        )
        
        self.assertEqual(event.duration_minutes(), 60)
    
    def test_duration_minutes_partial_hour(self):
        """Test duration calculation with partial hours."""
        end_time = self.sample_datetime + timedelta(minutes=45)
        event = Event(
            title="Meeting",
            start_datetime=self.sample_datetime,
            end_datetime=end_time
        )
        
        self.assertEqual(event.duration_minutes(), 45)
    
    def test_to_dict_serialization(self):
        """Test Event serialization to dictionary."""
        created_time = datetime(2024, 1, 10, 10, 0)
        event = Event(
            title="Meeting",
            start_datetime=self.sample_datetime,
            end_datetime=self.sample_end_datetime,
            location="Room A",
            description="Test meeting",
            calendar_id="work",
            created_at=created_time
        )
        
        result = event.to_dict()
        
        self.assertEqual(result['title'], "Meeting")
        self.assertEqual(result['start_datetime'], self.sample_datetime.isoformat())
        self.assertEqual(result['end_datetime'], self.sample_end_datetime.isoformat())
        self.assertEqual(result['location'], "Room A")
        self.assertEqual(result['description'], "Test meeting")
        self.assertEqual(result['calendar_id'], "work")
        self.assertEqual(result['created_at'], created_time.isoformat())
    
    def test_from_dict_deserialization(self):
        """Test Event deserialization from dictionary."""
        created_time = datetime(2024, 1, 10, 10, 0)
        data = {
            'title': 'Meeting',
            'start_datetime': self.sample_datetime.isoformat(),
            'end_datetime': self.sample_end_datetime.isoformat(),
            'location': 'Room A',
            'description': 'Test meeting',
            'calendar_id': 'work',
            'created_at': created_time.isoformat()
        }
        
        event = Event.from_dict(data)
        
        self.assertEqual(event.title, "Meeting")
        self.assertEqual(event.start_datetime, self.sample_datetime)
        self.assertEqual(event.end_datetime, self.sample_end_datetime)
        self.assertEqual(event.location, "Room A")
        self.assertEqual(event.description, "Test meeting")
        self.assertEqual(event.calendar_id, "work")
        self.assertEqual(event.created_at, created_time)


class TestValidationResult(unittest.TestCase):
    """Test cases for ValidationResult model."""
    
    def test_validation_result_creation(self):
        """Test basic ValidationResult creation."""
        result = ValidationResult(
            is_valid=False,
            missing_fields=["title", "date"],
            warnings=["Time format unclear"],
            suggestions=["Use 24-hour format"]
        )
        
        self.assertFalse(result.is_valid)
        self.assertEqual(result.missing_fields, ["title", "date"])
        self.assertEqual(result.warnings, ["Time format unclear"])
        self.assertEqual(result.suggestions, ["Use 24-hour format"])
    
    def test_validation_result_defaults(self):
        """Test ValidationResult with default values."""
        result = ValidationResult(is_valid=True)
        
        self.assertTrue(result.is_valid)
        self.assertEqual(result.missing_fields, [])
        self.assertEqual(result.warnings, [])
        self.assertEqual(result.suggestions, [])
    
    def test_add_missing_field(self):
        """Test adding missing field."""
        result = ValidationResult(is_valid=True)
        result.add_missing_field("title", "Event needs a descriptive title")
        
        self.assertFalse(result.is_valid)
        self.assertIn("title", result.missing_fields)
        self.assertIn("title: Event needs a descriptive title", result.suggestions)
    
    def test_add_missing_field_no_suggestion(self):
        """Test adding missing field without suggestion."""
        result = ValidationResult(is_valid=True)
        result.add_missing_field("date")
        
        self.assertFalse(result.is_valid)
        self.assertIn("date", result.missing_fields)
        self.assertEqual(len(result.suggestions), 0)
    
    def test_add_missing_field_duplicate(self):
        """Test adding duplicate missing field."""
        result = ValidationResult(is_valid=True)
        result.add_missing_field("title")
        result.add_missing_field("title")
        
        self.assertEqual(result.missing_fields.count("title"), 1)
    
    def test_add_warning(self):
        """Test adding warning message."""
        result = ValidationResult(is_valid=True)
        result.add_warning("Date format is ambiguous")
        
        self.assertIn("Date format is ambiguous", result.warnings)
    
    def test_add_suggestion(self):
        """Test adding suggestion message."""
        result = ValidationResult(is_valid=True)
        result.add_suggestion("Consider using ISO date format")
        
        self.assertIn("Consider using ISO date format", result.suggestions)
    
    def test_to_dict_serialization(self):
        """Test ValidationResult serialization to dictionary."""
        result = ValidationResult(
            is_valid=False,
            missing_fields=["title"],
            warnings=["Unclear time"],
            suggestions=["Use 24-hour format"]
        )
        
        data = result.to_dict()
        
        self.assertEqual(data['is_valid'], False)
        self.assertEqual(data['missing_fields'], ["title"])
        self.assertEqual(data['warnings'], ["Unclear time"])
        self.assertEqual(data['suggestions'], ["Use 24-hour format"])
    
    def test_from_dict_deserialization(self):
        """Test ValidationResult deserialization from dictionary."""
        data = {
            'is_valid': False,
            'missing_fields': ['title'],
            'warnings': ['Unclear time'],
            'suggestions': ['Use 24-hour format']
        }
        
        result = ValidationResult.from_dict(data)
        
        self.assertFalse(result.is_valid)
        self.assertEqual(result.missing_fields, ["title"])
        self.assertEqual(result.warnings, ["Unclear time"])
        self.assertEqual(result.suggestions, ["Use 24-hour format"])
    
    def test_valid_class_method(self):
        """Test ValidationResult.valid() class method."""
        result = ValidationResult.valid()
        
        self.assertTrue(result.is_valid)
        self.assertEqual(result.missing_fields, [])
        self.assertEqual(result.warnings, [])
        self.assertEqual(result.suggestions, [])
    
    def test_invalid_class_method(self):
        """Test ValidationResult.invalid() class method."""
        result = ValidationResult.invalid(
            missing_fields=["title", "date"],
            warnings=["Time unclear"]
        )
        
        self.assertFalse(result.is_valid)
        self.assertEqual(result.missing_fields, ["title", "date"])
        self.assertEqual(result.warnings, ["Time unclear"])
        self.assertEqual(result.suggestions, [])


if __name__ == '__main__':
    unittest.main()