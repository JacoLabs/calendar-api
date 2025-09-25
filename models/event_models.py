"""
Core data models for event parsing and calendar integration.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any
import json


@dataclass
class ParsedEvent:
    """
    Represents an event extracted from text with confidence scoring.
    Used during the parsing phase before user confirmation.
    """
    title: Optional[str] = None
    start_datetime: Optional[datetime] = None
    end_datetime: Optional[datetime] = None
    location: Optional[str] = None
    description: str = ""
    confidence_score: float = 0.0
    extraction_metadata: Dict[str, Any] = field(default_factory=dict)
    
    def is_complete(self) -> bool:
        """Check if the parsed event has minimum required information."""
        return (
            self.title is not None and 
            self.start_datetime is not None
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'title': self.title,
            'start_datetime': self.start_datetime.isoformat() if self.start_datetime else None,
            'end_datetime': self.end_datetime.isoformat() if self.end_datetime else None,
            'location': self.location,
            'description': self.description,
            'confidence_score': self.confidence_score,
            'extraction_metadata': self.extraction_metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ParsedEvent':
        """Create ParsedEvent from dictionary."""
        event = cls()
        event.title = data.get('title')
        event.start_datetime = datetime.fromisoformat(data['start_datetime']) if data.get('start_datetime') else None
        event.end_datetime = datetime.fromisoformat(data['end_datetime']) if data.get('end_datetime') else None
        event.location = data.get('location')
        event.description = data.get('description', '')
        event.confidence_score = data.get('confidence_score', 0.0)
        event.extraction_metadata = data.get('extraction_metadata', {})
        return event


@dataclass
class Event:
    """
    Represents a finalized calendar event ready for creation.
    Used after user confirmation and validation.
    """
    title: str
    start_datetime: datetime
    end_datetime: datetime
    location: Optional[str] = None
    description: str = ""
    calendar_id: str = "default"
    created_at: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        """Validate event data after initialization."""
        if not self.title.strip():
            raise ValueError("Event title cannot be empty")
        
        if self.start_datetime >= self.end_datetime:
            raise ValueError("Start time must be before end time")
    
    def duration_minutes(self) -> int:
        """Calculate event duration in minutes."""
        delta = self.end_datetime - self.start_datetime
        return int(delta.total_seconds() / 60)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'title': self.title,
            'start_datetime': self.start_datetime.isoformat(),
            'end_datetime': self.end_datetime.isoformat(),
            'location': self.location,
            'description': self.description,
            'calendar_id': self.calendar_id,
            'created_at': self.created_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Event':
        """Create Event from dictionary."""
        return cls(
            title=data['title'],
            start_datetime=datetime.fromisoformat(data['start_datetime']),
            end_datetime=datetime.fromisoformat(data['end_datetime']),
            location=data.get('location'),
            description=data.get('description', ''),
            calendar_id=data.get('calendar_id', 'default'),
            created_at=datetime.fromisoformat(data.get('created_at', datetime.now().isoformat()))
        )


@dataclass
class ValidationResult:
    """
    Represents the result of validating event data.
    Used to provide feedback to users about missing or invalid information.
    """
    is_valid: bool
    missing_fields: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    
    def add_missing_field(self, field_name: str, suggestion: str = None):
        """Add a missing field with optional suggestion."""
        if field_name not in self.missing_fields:
            self.missing_fields.append(field_name)
        if suggestion:
            self.suggestions.append(f"{field_name}: {suggestion}")
        self.is_valid = False
    
    def add_warning(self, message: str):
        """Add a warning message."""
        self.warnings.append(message)
    
    def add_suggestion(self, message: str):
        """Add a suggestion message."""
        self.suggestions.append(message)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'is_valid': self.is_valid,
            'missing_fields': self.missing_fields,
            'warnings': self.warnings,
            'suggestions': self.suggestions
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ValidationResult':
        """Create ValidationResult from dictionary."""
        return cls(
            is_valid=data['is_valid'],
            missing_fields=data.get('missing_fields', []),
            warnings=data.get('warnings', []),
            suggestions=data.get('suggestions', [])
        )
    
    @classmethod
    def valid(cls) -> 'ValidationResult':
        """Create a valid validation result."""
        return cls(is_valid=True)
    
    @classmethod
    def invalid(cls, missing_fields: List[str] = None, warnings: List[str] = None) -> 'ValidationResult':
        """Create an invalid validation result."""
        return cls(
            is_valid=False,
            missing_fields=missing_fields or [],
            warnings=warnings or []
        )