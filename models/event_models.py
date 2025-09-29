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


@dataclass
class TitleResult:
    """
    Represents the result of title extraction with confidence and method tracking.
    Used for intelligent title generation and extraction with multiple alternatives.
    """
    title: Optional[str] = None
    confidence: float = 0.0
    generation_method: str = "unknown"  # "explicit", "derived", "generated", "action_based", "context_derived"
    alternatives: List[str] = field(default_factory=list)
    raw_text: str = ""
    quality_score: float = 0.0  # Based on completeness and relevance
    extraction_metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate and normalize data after initialization."""
        # Ensure confidence is within valid range
        self.confidence = max(0.0, min(1.0, self.confidence))
        self.quality_score = max(0.0, min(1.0, self.quality_score))
        
        # Clean up title if present
        if self.title:
            self.title = self.title.strip()
            if not self.title:
                self.title = None
    
    def is_high_quality(self) -> bool:
        """Check if this is a high-quality title result."""
        return (
            self.title is not None and
            self.confidence >= 0.7 and
            self.quality_score >= 0.6 and
            len(self.title) >= 3
        )
    
    def is_complete_phrase(self) -> bool:
        """Check if the title is a complete phrase (not truncated)."""
        if not self.title:
            return False
        
        # Check for common indicators of incomplete phrases
        incomplete_indicators = [
            self.title.endswith('...'),
            self.title.endswith(' and'),
            self.title.endswith(' or'),
            self.title.endswith(' with'),
            self.title.endswith(' for'),
            self.title.endswith(' at'),
            self.title.endswith(' in'),
            len(self.title.split()) == 1 and self.generation_method != "action_based"
        ]
        
        return not any(incomplete_indicators)
    
    def add_alternative(self, alternative_title: str, confidence: float = None):
        """Add an alternative title option."""
        if alternative_title and alternative_title.strip():
            clean_alt = alternative_title.strip()
            if clean_alt not in self.alternatives and clean_alt != self.title:
                self.alternatives.append(clean_alt)
                
                # Update metadata with alternative confidence if provided
                if confidence is not None:
                    if 'alternative_confidences' not in self.extraction_metadata:
                        self.extraction_metadata['alternative_confidences'] = {}
                    self.extraction_metadata['alternative_confidences'][clean_alt] = confidence
    
    def get_best_title(self) -> Optional[str]:
        """Get the best available title (main or alternative)."""
        if self.title and self.is_complete_phrase():
            return self.title
        
        # Look for complete alternatives
        for alt in self.alternatives:
            alt_result = TitleResult(title=alt, generation_method=self.generation_method)
            if alt_result.is_complete_phrase():
                return alt
        
        # Return main title even if incomplete
        return self.title
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'title': self.title,
            'confidence': self.confidence,
            'generation_method': self.generation_method,
            'alternatives': self.alternatives,
            'raw_text': self.raw_text,
            'quality_score': self.quality_score,
            'extraction_metadata': self.extraction_metadata,
            'is_high_quality': self.is_high_quality(),
            'is_complete_phrase': self.is_complete_phrase()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TitleResult':
        """Create TitleResult from dictionary."""
        return cls(
            title=data.get('title'),
            confidence=data.get('confidence', 0.0),
            generation_method=data.get('generation_method', 'unknown'),
            alternatives=data.get('alternatives', []),
            raw_text=data.get('raw_text', ''),
            quality_score=data.get('quality_score', 0.0),
            extraction_metadata=data.get('extraction_metadata', {})
        )
    
    @classmethod
    def empty(cls, raw_text: str = "") -> 'TitleResult':
        """Create an empty title result."""
        return cls(
            title=None,
            confidence=0.0,
            generation_method="none",
            raw_text=raw_text,
            quality_score=0.0
        )
    
    @classmethod
    def from_explicit(cls, title: str, raw_text: str = "", confidence: float = 0.9) -> 'TitleResult':
        """Create a title result from explicit title detection."""
        return cls(
            title=title,
            confidence=confidence,
            generation_method="explicit",
            raw_text=raw_text,
            quality_score=0.8  # High quality for explicit titles
        )