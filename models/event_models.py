"""
Core data models for event parsing and calendar integration.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
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
    all_day: bool = False
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
            'all_day': self.all_day,
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
        event.all_day = data.get('all_day', False)
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
    all_day: bool = False
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
            'all_day': self.all_day,
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
            all_day=data.get('all_day', False),
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
class NormalizedEvent:
    """
    Standardized output format for parsed events with comprehensive confidence scoring.
    Used as the final output format after error handling and validation.
    
    Provides consistent structure regardless of input method (LLM, regex, manual).
    Includes field-level confidence tracking and parsing metadata for debugging.
    """
    title: str
    start_datetime: datetime
    end_datetime: datetime
    location: Optional[str] = None
    description: str = ""
    confidence_score: float = 0.0  # Overall confidence (0.0 to 1.0)
    
    # Field-level confidence tracking
    field_confidence: Dict[str, float] = field(default_factory=dict)
    
    # Parsing metadata and quality information
    parsing_issues: List[str] = field(default_factory=list)
    parsing_suggestions: List[str] = field(default_factory=list)
    extraction_metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Quality validation results
    quality_score: float = 0.0  # Quality assessment (0.0 to 1.0)
    meets_quality_threshold: bool = True
    
    def __post_init__(self):
        """Validate and normalize data after initialization."""
        # Ensure confidence scores are within valid range
        self.confidence_score = max(0.0, min(1.0, self.confidence_score))
        self.quality_score = max(0.0, min(1.0, self.quality_score))
        
        # Normalize field confidence scores
        for field, confidence in self.field_confidence.items():
            self.field_confidence[field] = max(0.0, min(1.0, confidence))
        
        # Validate required fields
        if not self.title or not self.title.strip():
            raise ValueError("NormalizedEvent title cannot be empty")
        
        if self.start_datetime >= self.end_datetime:
            raise ValueError("NormalizedEvent start_datetime must be before end_datetime")
        
        # Clean up string fields
        self.title = self.title.strip()
        self.description = self.description.strip()
        if self.location:
            self.location = self.location.strip()
            if not self.location:
                self.location = None
    
    def get_field_confidence(self, field_name: str) -> float:
        """Get confidence score for a specific field."""
        return self.field_confidence.get(field_name, self.confidence_score)
    
    def set_field_confidence(self, field_name: str, confidence: float):
        """Set confidence score for a specific field."""
        self.field_confidence[field_name] = max(0.0, min(1.0, confidence))
    
    def add_parsing_issue(self, issue: str):
        """Add a parsing issue to the list."""
        if issue and issue not in self.parsing_issues:
            self.parsing_issues.append(issue)
    
    def add_parsing_suggestion(self, suggestion: str):
        """Add a parsing suggestion to the list."""
        if suggestion and suggestion not in self.parsing_suggestions:
            self.parsing_suggestions.append(suggestion)
    
    def calculate_quality_score(self) -> float:
        """
        Calculate overall quality score based on various factors.
        
        Returns:
            Quality score from 0.0 to 1.0
        """
        quality_factors = []
        
        # Title quality (30% weight)
        title_quality = 0.0
        if self.title:
            # Length factor (prefer 10-50 characters)
            length_factor = min(1.0, len(self.title) / 10.0) if len(self.title) < 50 else max(0.5, 50.0 / len(self.title))
            
            # Word count factor (prefer 2-8 words)
            word_count = len(self.title.split())
            word_factor = min(1.0, word_count / 2.0) if word_count < 8 else max(0.5, 8.0 / word_count)
            
            # Completeness factor (avoid truncated phrases)
            completeness_factor = 1.0
            if self.title.endswith('...') or self.title.endswith(' and') or self.title.endswith(' or'):
                completeness_factor = 0.3
            
            title_quality = (length_factor + word_factor + completeness_factor) / 3.0
        
        quality_factors.append(('title', title_quality, 0.3))
        
        # DateTime quality (40% weight)
        datetime_quality = 0.0
        if self.start_datetime and self.end_datetime:
            # Duration reasonableness (prefer 15 minutes to 8 hours)
            duration = self.end_datetime - self.start_datetime
            duration_minutes = duration.total_seconds() / 60
            
            if 15 <= duration_minutes <= 480:  # 15 minutes to 8 hours
                duration_factor = 1.0
            elif duration_minutes < 15:
                duration_factor = max(0.3, duration_minutes / 15.0)
            else:
                duration_factor = max(0.3, 480.0 / duration_minutes)
            
            # Time specificity (prefer specific times over defaults)
            time_specificity = 1.0
            if self.start_datetime.minute == 0 and self.start_datetime.second == 0:
                # Check if this looks like a default time
                if self.start_datetime.hour in [9, 10, 14, 15]:  # Common default hours
                    time_specificity = 0.7
            
            datetime_quality = (duration_factor + time_specificity) / 2.0
        
        quality_factors.append(('datetime', datetime_quality, 0.4))
        
        # Location quality (15% weight) - optional but adds value when present
        location_quality = 0.5  # Neutral score when no location
        if self.location:
            # Length and specificity
            if len(self.location) >= 5:  # Reasonably specific
                location_quality = 1.0
            else:
                location_quality = 0.7  # Short but present
        
        quality_factors.append(('location', location_quality, 0.15))
        
        # Confidence quality (15% weight)
        confidence_quality = self.confidence_score
        quality_factors.append(('confidence', confidence_quality, 0.15))
        
        # Calculate weighted average
        total_score = sum(score * weight for _, score, weight in quality_factors)
        
        # Apply penalties for parsing issues
        issue_penalty = min(0.3, len(self.parsing_issues) * 0.1)
        total_score = max(0.0, total_score - issue_penalty)
        
        self.quality_score = total_score
        return total_score
    
    def meets_minimum_quality(self, threshold: float = 0.5) -> bool:
        """
        Check if the event meets minimum quality standards.
        
        Args:
            threshold: Minimum quality score required (default 0.5)
            
        Returns:
            True if quality meets threshold
        """
        current_quality = self.calculate_quality_score()
        self.meets_quality_threshold = current_quality >= threshold
        return self.meets_quality_threshold
    
    def get_quality_report(self) -> Dict[str, Any]:
        """
        Generate a detailed quality assessment report.
        
        Returns:
            Dictionary with quality breakdown and recommendations
        """
        quality_score = self.calculate_quality_score()
        
        report = {
            'overall_quality': quality_score,
            'overall_confidence': self.confidence_score,
            'meets_threshold': self.meets_quality_threshold,
            'field_scores': {},
            'recommendations': [],
            'parsing_issues': self.parsing_issues.copy(),
            'parsing_suggestions': self.parsing_suggestions.copy()
        }
        
        # Field-specific assessments
        if self.title:
            title_conf = self.get_field_confidence('title')
            report['field_scores']['title'] = {
                'confidence': title_conf,
                'length': len(self.title),
                'word_count': len(self.title.split()),
                'assessment': 'good' if title_conf > 0.7 else 'fair' if title_conf > 0.4 else 'poor'
            }
            
            if title_conf < 0.5:
                report['recommendations'].append("Consider reviewing the event title for accuracy")
        
        if self.start_datetime:
            datetime_conf = self.get_field_confidence('start_datetime')
            duration = self.end_datetime - self.start_datetime
            report['field_scores']['datetime'] = {
                'confidence': datetime_conf,
                'duration_minutes': duration.total_seconds() / 60,
                'assessment': 'good' if datetime_conf > 0.7 else 'fair' if datetime_conf > 0.4 else 'poor'
            }
            
            if datetime_conf < 0.5:
                report['recommendations'].append("Consider verifying the date and time")
        
        if self.location:
            location_conf = self.get_field_confidence('location')
            report['field_scores']['location'] = {
                'confidence': location_conf,
                'length': len(self.location),
                'assessment': 'good' if location_conf > 0.7 else 'fair' if location_conf > 0.4 else 'poor'
            }
            
            if location_conf < 0.5:
                report['recommendations'].append("Consider verifying the location")
        
        # Overall recommendations
        if quality_score < 0.3:
            report['recommendations'].append("Event quality is low - consider manual review")
        elif quality_score < 0.6:
            report['recommendations'].append("Event quality is fair - minor adjustments may improve accuracy")
        
        return report
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'title': self.title,
            'start_datetime': self.start_datetime.isoformat(),
            'end_datetime': self.end_datetime.isoformat(),
            'location': self.location,
            'description': self.description,
            'confidence_score': self.confidence_score,
            'field_confidence': self.field_confidence,
            'parsing_issues': self.parsing_issues,
            'parsing_suggestions': self.parsing_suggestions,
            'extraction_metadata': self.extraction_metadata,
            'quality_score': self.quality_score,
            'meets_quality_threshold': self.meets_quality_threshold
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'NormalizedEvent':
        """Create NormalizedEvent from dictionary."""
        return cls(
            title=data['title'],
            start_datetime=datetime.fromisoformat(data['start_datetime']),
            end_datetime=datetime.fromisoformat(data['end_datetime']),
            location=data.get('location'),
            description=data.get('description', ''),
            confidence_score=data.get('confidence_score', 0.0),
            field_confidence=data.get('field_confidence', {}),
            parsing_issues=data.get('parsing_issues', []),
            parsing_suggestions=data.get('parsing_suggestions', []),
            extraction_metadata=data.get('extraction_metadata', {}),
            quality_score=data.get('quality_score', 0.0),
            meets_quality_threshold=data.get('meets_quality_threshold', True)
        )
    
    @classmethod
    def from_parsed_event(cls, parsed_event: ParsedEvent, 
                         quality_threshold: float = 0.5) -> 'NormalizedEvent':
        """
        Create NormalizedEvent from ParsedEvent with validation and quality assessment.
        
        Args:
            parsed_event: Source ParsedEvent to normalize
            quality_threshold: Minimum quality threshold for validation
            
        Returns:
            NormalizedEvent with quality assessment
            
        Raises:
            ValueError: If parsed_event lacks required fields
        """
        if not parsed_event.title:
            raise ValueError("Cannot create NormalizedEvent: title is required")
        
        if not parsed_event.start_datetime:
            raise ValueError("Cannot create NormalizedEvent: start_datetime is required")
        
        # Use end_datetime or calculate default
        end_datetime = parsed_event.end_datetime
        if not end_datetime:
            end_datetime = parsed_event.start_datetime + timedelta(hours=1)
        
        # Extract field-level confidence from metadata
        metadata = parsed_event.extraction_metadata or {}
        field_confidence = {
            'title': metadata.get('title_confidence', parsed_event.confidence_score),
            'start_datetime': metadata.get('datetime_confidence', parsed_event.confidence_score),
            'end_datetime': metadata.get('datetime_confidence', parsed_event.confidence_score),
        }
        
        if parsed_event.location:
            field_confidence['location'] = metadata.get('location_confidence', parsed_event.confidence_score)
        
        # Create normalized event
        normalized = cls(
            title=parsed_event.title,
            start_datetime=parsed_event.start_datetime,
            end_datetime=end_datetime,
            location=parsed_event.location,
            description=parsed_event.description,
            confidence_score=parsed_event.confidence_score,
            field_confidence=field_confidence,
            extraction_metadata=metadata
        )
        
        # Add parsing issues from metadata
        if metadata.get('has_ambiguous_datetime'):
            normalized.add_parsing_issue("Date/time information was ambiguous")
        
        if metadata.get('multiple_datetime_matches', 0) > 1:
            normalized.add_parsing_issue(f"Multiple possible dates/times found ({metadata['multiple_datetime_matches']})")
        
        if metadata.get('multiple_title_matches', 0) > 1:
            normalized.add_parsing_issue(f"Multiple possible titles found ({metadata['multiple_title_matches']})")
        
        if metadata.get('used_default_duration'):
            normalized.add_parsing_suggestion("Used default 1-hour duration - consider specifying end time")
        
        if metadata.get('extraction_method') == 'regex_fallback':
            normalized.add_parsing_issue("LLM extraction failed, used regex fallback")
        
        # Calculate quality and validate threshold
        normalized.calculate_quality_score()
        normalized.meets_minimum_quality(quality_threshold)
        
        return normalized
    
    @classmethod
    def from_event(cls, event: 'Event', confidence_score: float = 1.0) -> 'NormalizedEvent':
        """
        Create NormalizedEvent from finalized Event object.
        
        Args:
            event: Source Event to normalize
            confidence_score: Confidence score to assign (default 1.0 for finalized events)
            
        Returns:
            NormalizedEvent with high quality scores
        """
        normalized = cls(
            title=event.title,
            start_datetime=event.start_datetime,
            end_datetime=event.end_datetime,
            location=event.location,
            description=event.description,
            confidence_score=confidence_score,
            field_confidence={
                'title': confidence_score,
                'start_datetime': confidence_score,
                'end_datetime': confidence_score,
                'location': confidence_score if event.location else 0.0
            },
            extraction_metadata={
                'source': 'finalized_event',
                'created_at': event.created_at.isoformat() if hasattr(event, 'created_at') else None
            }
        )
        
        normalized.calculate_quality_score()
        return normalized


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