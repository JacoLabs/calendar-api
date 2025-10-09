"""
Per-Field Confidence Router for optimized event parsing.

Implements per-field confidence analysis and routing to determine the optimal
processing method (regex/deterministic/LLM) for each field based on confidence scores.
Supports field-level optimization and cross-field validation.

Requirements: 10.1, 10.2, 10.3, 10.5
"""

import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum

from models.event_models import FieldResult, ValidationResult


class ProcessingMethod(Enum):
    """Available processing methods for field extraction."""
    REGEX = "regex"
    DETERMINISTIC = "deterministic"
    LLM = "llm"
    SKIP = "skip"


@dataclass
class FieldAnalysis:
    """Analysis result for a specific field's extractability."""
    field_name: str
    confidence_potential: float  # 0.0 to 1.0
    complexity_score: float      # 0.0 to 1.0 (higher = more complex)
    pattern_matches: List[str]   # Detected patterns
    ambiguity_indicators: List[str]  # Potential ambiguities
    recommended_method: ProcessingMethod
    processing_priority: int     # Lower number = higher priority


class PerFieldConfidenceRouter:
    """
    Routes field processing based on confidence analysis and optimization.
    
    Analyzes text to determine the best processing method for each field:
    - High confidence (≥0.8): Regex extraction only
    - Medium confidence (0.6-0.8): Deterministic backup methods
    - Low confidence (<0.6): LLM enhancement required
    
    Optimizes processing order and validates field consistency.
    """
    
    def __init__(self):
        """Initialize the router with field analysis patterns."""
        self._compile_field_patterns()
        self._setup_confidence_thresholds()
        self._setup_field_priorities()
    
    def _compile_field_patterns(self):
        """Compile regex patterns for field analysis."""
        
        # DateTime field patterns (high confidence indicators)
        self.datetime_patterns = {
            'explicit_date': [
                re.compile(r'\b(january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\.?\s+\d{1,2}(?:st|nd|rd|th)?,?\s+\d{4}\b', re.IGNORECASE),
                re.compile(r'\b\d{1,2}[\/\-]\d{1,2}[\/\-]\d{4}\b'),
                re.compile(r'\b\d{4}[\/\-]\d{1,2}[\/\-]\d{1,2}\b')
            ],
            'relative_date': [
                re.compile(r'\b(today|tomorrow|yesterday)\b', re.IGNORECASE),
                re.compile(r'\b(next|this)\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b', re.IGNORECASE),
                re.compile(r'\bin\s+\d+\s+(days?|weeks?|months?)\b', re.IGNORECASE)
            ],
            'explicit_time': [
                re.compile(r'\b\d{1,2}(?::\d{2})?\s*(am|pm)\b', re.IGNORECASE),
                re.compile(r'\b\d{1,2}:\d{2}\b'),
                re.compile(r'\b(noon|midnight)\b', re.IGNORECASE)
            ],
            'time_range': [
                re.compile(r'\b\d{1,2}(?::\d{2})?\s*[–\-to]\s*\d{1,2}(?::\d{2})?\s*(am|pm)\b', re.IGNORECASE),
                re.compile(r'\bfrom\s+\d{1,2}(?::\d{2})?\s*(am|pm)\s+to\s+\d{1,2}(?::\d{2})?\s*(am|pm)\b', re.IGNORECASE)
            ]
        }
        
        # Title field patterns
        self.title_patterns = {
            'formal_title': [
                re.compile(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+(Meeting|Conference|Workshop|Seminar|Event|Gathering)\b'),
                re.compile(r'\b(Meeting|Conference|Workshop|Seminar|Event|Gathering)\s*:\s*[A-Z]', re.IGNORECASE)
            ],
            'quoted_title': [
                re.compile(r'"([^"]+)"'),
                re.compile(r"'([^']+)'")
            ],
            'subject_line': [
                re.compile(r'^Subject:\s*(.+)$', re.MULTILINE | re.IGNORECASE),
                re.compile(r'^Re:\s*(.+)$', re.MULTILINE | re.IGNORECASE)
            ]
        }
        
        # Location field patterns
        self.location_patterns = {
            'explicit_address': [
                re.compile(r'\b\d+\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+(Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Drive|Dr|Lane|Ln)\b', re.IGNORECASE),
                re.compile(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+(Square|Park|Center|Centre|Hall|Building|Tower)\b', re.IGNORECASE)
            ],
            'venue_keywords': [
                re.compile(r'\b(at|in|@)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b'),
                re.compile(r'\b(Room|Conference Room|Meeting Room)\s+\w+\b', re.IGNORECASE),
                re.compile(r'\b(main|large|small|big)\s+(conference|meeting)\s+room\b', re.IGNORECASE),
                re.compile(r'\bconference\s+room\b', re.IGNORECASE),
                re.compile(r'\bmeeting\s+room\b', re.IGNORECASE)
            ],
            'implicit_location': [
                re.compile(r'\b(office|school|gym|library|cafeteria|auditorium)\b', re.IGNORECASE),
                re.compile(r'\b(downtown|uptown|campus)\b', re.IGNORECASE)
            ]
        }
        
        # Participants field patterns
        self.participants_patterns = {
            'with_keyword': [
                re.compile(r'\bwith\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)', re.IGNORECASE),
                re.compile(r'\bmeet\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)', re.IGNORECASE)
            ],
            'email_addresses': [
                re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
            ]
        }
        
        # Recurrence field patterns
        self.recurrence_patterns = {
            'explicit_recurrence': [
                re.compile(r'\bevery\s+(day|week|month|year)\b', re.IGNORECASE),
                re.compile(r'\bevery\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b', re.IGNORECASE),
                re.compile(r'\bevery\s+other\s+(day|week|month|year)\b', re.IGNORECASE)
            ],
            'frequency_indicators': [
                re.compile(r'\b(daily|weekly|monthly|yearly|annually)\b', re.IGNORECASE),
                re.compile(r'\b(recurring|repeating|regular)\b', re.IGNORECASE)
            ]
        }
        
        # Duration field patterns
        self.duration_patterns = {
            'explicit_duration': [
                re.compile(r'\bfor\s+\d+(?:\.\d+)?\s+(hours?|hrs?|minutes?|mins?)\b', re.IGNORECASE),
                re.compile(r'\b\d+(?:\.\d+)?\s+(hours?|hrs?|minutes?|mins?)\s+long\b', re.IGNORECASE)
            ],
            'until_time': [
                re.compile(r'\buntil\s+\d{1,2}(?::\d{2})?\s*(am|pm)\b', re.IGNORECASE),
                re.compile(r'\buntil\s+(noon|midnight)\b', re.IGNORECASE)
            ]
        }
    
    def _setup_confidence_thresholds(self):
        """Setup confidence thresholds for routing decisions."""
        self.confidence_thresholds = {
            'high_confidence': 0.8,    # Use regex only
            'medium_confidence': 0.6,  # Use deterministic backup
            'low_confidence': 0.4      # Require LLM enhancement
        }
        
        # Field-specific threshold adjustments
        self.field_threshold_adjustments = {
            'title': 0.0,           # Essential field - no adjustment
            'start_datetime': 0.0,  # Essential field - no adjustment
            'end_datetime': 0.0,    # Essential field - no adjustment
            'location': -0.1,       # Optional field - lower threshold
            'description': -0.2,    # Optional field - much lower threshold
            'participants': -0.1,   # Optional field - lower threshold
            'recurrence': -0.1,     # Optional field - lower threshold
            'duration': 0.0         # Important for end time calculation
        }
    
    def _setup_field_priorities(self):
        """Setup processing priorities for fields."""
        self.field_priorities = {
            'start_datetime': 1,    # Highest priority - needed for all other calculations
            'end_datetime': 2,      # High priority - but may depend on start + duration
            'duration': 3,          # Medium-high priority - affects end_datetime
            'title': 4,             # Medium priority - essential but independent
            'location': 5,          # Lower priority - optional
            'participants': 6,      # Lower priority - optional
            'recurrence': 7,        # Lower priority - optional
            'description': 8        # Lowest priority - can be generated/enhanced
        }
    
    def analyze_field_extractability(self, text: str) -> Dict[str, FieldAnalysis]:
        """
        Analyze text to assess per-field confidence potential.
        
        Args:
            text: Input text to analyze
            
        Returns:
            Dictionary mapping field names to FieldAnalysis objects
        """
        if not text or not text.strip():
            return {}
        
        text = text.strip()
        analyses = {}
        
        # Analyze each field type
        field_analyzers = {
            'start_datetime': self._analyze_datetime_field,
            'end_datetime': self._analyze_datetime_field,
            'title': self._analyze_title_field,
            'location': self._analyze_location_field,
            'participants': self._analyze_participants_field,
            'recurrence': self._analyze_recurrence_field,
            'duration': self._analyze_duration_field
        }
        
        for field_name, analyzer in field_analyzers.items():
            analysis = analyzer(text, field_name)
            if analysis:
                analyses[field_name] = analysis
        
        return analyses
    
    def _analyze_datetime_field(self, text: str, field_name: str) -> Optional[FieldAnalysis]:
        """Analyze datetime field extractability."""
        pattern_matches = []
        confidence_score = 0.0
        complexity_score = 0.0
        ambiguities = []
        
        # Check for explicit date patterns (highest confidence)
        for pattern_type, patterns in self.datetime_patterns.items():
            for pattern in patterns:
                matches = pattern.findall(text)
                if matches:
                    pattern_matches.append(f"{pattern_type}: {len(matches)} matches")
                    
                    if pattern_type == 'explicit_date':
                        confidence_score = max(confidence_score, 0.9)
                    elif pattern_type == 'time_range':
                        confidence_score = max(confidence_score, 0.95)  # Highest confidence
                    elif pattern_type == 'explicit_time':
                        confidence_score = max(confidence_score, 0.85)
                    elif pattern_type == 'relative_date':
                        confidence_score = max(confidence_score, 0.8)
                    
                    # Check for ambiguities
                    if len(matches) > 1:
                        ambiguities.append(f"Multiple {pattern_type} patterns found")
                        complexity_score += 0.2
        
        # Adjust confidence for field-specific factors
        if field_name == 'end_datetime':
            # End datetime often depends on start + duration
            if 'time_range' not in [pm.split(':')[0] for pm in pattern_matches]:
                confidence_score *= 0.8  # Reduce if no explicit range
                complexity_score += 0.1
        
        # Apply field-specific threshold adjustment
        threshold_adjustment = self.field_threshold_adjustments.get(field_name, 0.0)
        adjusted_confidence = confidence_score + threshold_adjustment
        
        # Determine recommended method
        recommended_method = self._determine_processing_method(adjusted_confidence)
        
        # Set processing priority
        priority = self.field_priorities.get(field_name, 10)
        
        return FieldAnalysis(
            field_name=field_name,
            confidence_potential=confidence_score,
            complexity_score=min(1.0, complexity_score),
            pattern_matches=pattern_matches,
            ambiguity_indicators=ambiguities,
            recommended_method=recommended_method,
            processing_priority=priority
        )
    
    def _analyze_title_field(self, text: str, field_name: str) -> Optional[FieldAnalysis]:
        """Analyze title field extractability."""
        pattern_matches = []
        confidence_score = 0.0
        complexity_score = 0.0
        ambiguities = []
        
        # Check for title patterns
        for pattern_type, patterns in self.title_patterns.items():
            for pattern in patterns:
                matches = pattern.findall(text)
                if matches:
                    pattern_matches.append(f"{pattern_type}: {len(matches)} matches")
                    
                    if pattern_type == 'formal_title':
                        confidence_score = max(confidence_score, 0.9)
                    elif pattern_type == 'quoted_title':
                        confidence_score = max(confidence_score, 0.85)
                    elif pattern_type == 'subject_line':
                        confidence_score = max(confidence_score, 0.8)
                    
                    if len(matches) > 1:
                        ambiguities.append(f"Multiple {pattern_type} candidates")
                        complexity_score += 0.15
        
        # Check for title-like capitalization patterns
        capitalized_phrases = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,4}\b', text)
        if capitalized_phrases:
            pattern_matches.append(f"capitalized_phrases: {len(capitalized_phrases)} found")
            confidence_score = max(confidence_score, 0.6)
            
            if len(capitalized_phrases) > 3:
                ambiguities.append("Many capitalized phrases - unclear which is title")
                complexity_score += 0.2
        
        # If no clear patterns, title will likely need LLM generation
        if confidence_score < 0.5:
            complexity_score += 0.3
            ambiguities.append("No clear title patterns - may need generation")
        
        # Apply field-specific threshold adjustment
        threshold_adjustment = self.field_threshold_adjustments.get(field_name, 0.0)
        adjusted_confidence = confidence_score + threshold_adjustment
        
        recommended_method = self._determine_processing_method(adjusted_confidence)
        priority = self.field_priorities.get(field_name, 10)
        
        return FieldAnalysis(
            field_name=field_name,
            confidence_potential=confidence_score,
            complexity_score=min(1.0, complexity_score),
            pattern_matches=pattern_matches,
            ambiguity_indicators=ambiguities,
            recommended_method=recommended_method,
            processing_priority=priority
        )
    
    def _analyze_location_field(self, text: str, field_name: str) -> Optional[FieldAnalysis]:
        """Analyze location field extractability."""
        pattern_matches = []
        confidence_score = 0.0
        complexity_score = 0.0
        ambiguities = []
        
        # Check for location patterns
        for pattern_type, patterns in self.location_patterns.items():
            for pattern in patterns:
                matches = pattern.findall(text)
                if matches:
                    pattern_matches.append(f"{pattern_type}: {len(matches)} matches")
                    
                    if pattern_type == 'explicit_address':
                        confidence_score = max(confidence_score, 0.9)
                    elif pattern_type == 'venue_keywords':
                        confidence_score = max(confidence_score, 0.8)
                    elif pattern_type == 'implicit_location':
                        confidence_score = max(confidence_score, 0.6)
                    
                    if len(matches) > 1:
                        ambiguities.append(f"Multiple {pattern_type} found")
                        complexity_score += 0.15
        
        # Apply field-specific threshold adjustment (location is optional)
        threshold_adjustment = self.field_threshold_adjustments.get(field_name, 0.0)
        adjusted_confidence = confidence_score + threshold_adjustment
        
        recommended_method = self._determine_processing_method(adjusted_confidence)
        priority = self.field_priorities.get(field_name, 10)
        
        return FieldAnalysis(
            field_name=field_name,
            confidence_potential=confidence_score,
            complexity_score=min(1.0, complexity_score),
            pattern_matches=pattern_matches,
            ambiguity_indicators=ambiguities,
            recommended_method=recommended_method,
            processing_priority=priority
        )
    
    def _analyze_participants_field(self, text: str, field_name: str) -> Optional[FieldAnalysis]:
        """Analyze participants field extractability."""
        pattern_matches = []
        confidence_score = 0.0
        complexity_score = 0.0
        ambiguities = []
        
        # Check for participants patterns
        for pattern_type, patterns in self.participants_patterns.items():
            for pattern in patterns:
                matches = pattern.findall(text)
                if matches:
                    pattern_matches.append(f"{pattern_type}: {len(matches)} matches")
                    
                    if pattern_type == 'email_addresses':
                        confidence_score = max(confidence_score, 0.95)
                    elif pattern_type == 'with_keyword':
                        confidence_score = max(confidence_score, 0.7)
                    
                    if len(matches) > 3:
                        ambiguities.append(f"Many {pattern_type} - may need filtering")
                        complexity_score += 0.1
        
        # Apply field-specific threshold adjustment
        threshold_adjustment = self.field_threshold_adjustments.get(field_name, 0.0)
        adjusted_confidence = confidence_score + threshold_adjustment
        
        recommended_method = self._determine_processing_method(adjusted_confidence)
        priority = self.field_priorities.get(field_name, 10)
        
        return FieldAnalysis(
            field_name=field_name,
            confidence_potential=confidence_score,
            complexity_score=min(1.0, complexity_score),
            pattern_matches=pattern_matches,
            ambiguity_indicators=ambiguities,
            recommended_method=recommended_method,
            processing_priority=priority
        )
    
    def _analyze_recurrence_field(self, text: str, field_name: str) -> Optional[FieldAnalysis]:
        """Analyze recurrence field extractability."""
        pattern_matches = []
        confidence_score = 0.0
        complexity_score = 0.0
        ambiguities = []
        
        # Check for recurrence patterns
        for pattern_type, patterns in self.recurrence_patterns.items():
            for pattern in patterns:
                matches = pattern.findall(text)
                if matches:
                    pattern_matches.append(f"{pattern_type}: {len(matches)} matches")
                    
                    if pattern_type == 'explicit_recurrence':
                        confidence_score = max(confidence_score, 0.9)
                    elif pattern_type == 'frequency_indicators':
                        confidence_score = max(confidence_score, 0.7)
                    
                    if len(matches) > 1:
                        ambiguities.append(f"Multiple {pattern_type} patterns")
                        complexity_score += 0.2
        
        # Apply field-specific threshold adjustment
        threshold_adjustment = self.field_threshold_adjustments.get(field_name, 0.0)
        adjusted_confidence = confidence_score + threshold_adjustment
        
        recommended_method = self._determine_processing_method(adjusted_confidence)
        priority = self.field_priorities.get(field_name, 10)
        
        return FieldAnalysis(
            field_name=field_name,
            confidence_potential=confidence_score,
            complexity_score=min(1.0, complexity_score),
            pattern_matches=pattern_matches,
            ambiguity_indicators=ambiguities,
            recommended_method=recommended_method,
            processing_priority=priority
        )
    
    def _analyze_duration_field(self, text: str, field_name: str) -> Optional[FieldAnalysis]:
        """Analyze duration field extractability."""
        pattern_matches = []
        confidence_score = 0.0
        complexity_score = 0.0
        ambiguities = []
        
        # Check for duration patterns
        for pattern_type, patterns in self.duration_patterns.items():
            for pattern in patterns:
                matches = pattern.findall(text)
                if matches:
                    pattern_matches.append(f"{pattern_type}: {len(matches)} matches")
                    
                    if pattern_type == 'explicit_duration':
                        confidence_score = max(confidence_score, 0.9)
                    elif pattern_type == 'until_time':
                        confidence_score = max(confidence_score, 0.85)
                    
                    if len(matches) > 1:
                        ambiguities.append(f"Multiple {pattern_type} found")
                        complexity_score += 0.15
        
        # Apply field-specific threshold adjustment
        threshold_adjustment = self.field_threshold_adjustments.get(field_name, 0.0)
        adjusted_confidence = confidence_score + threshold_adjustment
        
        recommended_method = self._determine_processing_method(adjusted_confidence)
        priority = self.field_priorities.get(field_name, 10)
        
        return FieldAnalysis(
            field_name=field_name,
            confidence_potential=confidence_score,
            complexity_score=min(1.0, complexity_score),
            pattern_matches=pattern_matches,
            ambiguity_indicators=ambiguities,
            recommended_method=recommended_method,
            processing_priority=priority
        )
    
    def _determine_processing_method(self, confidence: float) -> ProcessingMethod:
        """Determine the recommended processing method based on confidence."""
        if confidence >= self.confidence_thresholds['high_confidence']:
            return ProcessingMethod.REGEX
        elif confidence >= self.confidence_thresholds['medium_confidence']:
            return ProcessingMethod.DETERMINISTIC
        elif confidence >= self.confidence_thresholds['low_confidence']:
            return ProcessingMethod.LLM
        else:
            return ProcessingMethod.SKIP
    
    def route_processing_method(self, field: str, confidence: float) -> ProcessingMethod:
        """
        Choose between regex/deterministic/LLM based on confidence.
        
        Args:
            field: Field name to process
            confidence: Confidence score for the field
            
        Returns:
            Recommended ProcessingMethod
        """
        # Apply field-specific threshold adjustment
        threshold_adjustment = self.field_threshold_adjustments.get(field, 0.0)
        adjusted_confidence = confidence + threshold_adjustment
        
        return self._determine_processing_method(adjusted_confidence)
    
    def validate_field_consistency(self, results: Dict[str, FieldResult]) -> ValidationResult:
        """
        Validate cross-field consistency and logical relationships.
        
        Args:
            results: Dictionary of field results to validate
            
        Returns:
            ValidationResult with consistency validation
        """
        validation = ValidationResult(is_valid=True)
        
        # Check for essential fields
        essential_fields = ['title', 'start_datetime']
        for field in essential_fields:
            if field not in results or not results[field].value:
                validation.add_missing_field(field, f"Essential field {field} is required")
        
        # Validate datetime consistency
        if 'start_datetime' in results and 'end_datetime' in results:
            start_dt = results['start_datetime'].value
            end_dt = results['end_datetime'].value
            
            if start_dt and end_dt:
                if isinstance(start_dt, datetime) and isinstance(end_dt, datetime):
                    if start_dt >= end_dt:
                        validation.add_field_warning('end_datetime', 'End time must be after start time')
                        validation.is_valid = False
                    
                    # Check for unreasonable durations
                    duration = end_dt - start_dt
                    duration_hours = duration.total_seconds() / 3600
                    
                    if duration_hours > 24:
                        validation.add_field_warning('end_datetime', 'Event duration exceeds 24 hours - please verify')
                    elif duration_hours < 0.25:  # Less than 15 minutes
                        validation.add_field_warning('end_datetime', 'Very short event duration - please verify')
        
        # Validate confidence consistency
        for field_name, field_result in results.items():
            confidence = field_result.confidence
            
            # Add confidence issues for low-confidence fields
            if field_name in ['title', 'start_datetime'] and confidence < 0.6:
                validation.add_confidence_issue(field_name, confidence, 0.6)
            elif confidence < 0.4:
                validation.add_confidence_issue(field_name, confidence, 0.4)
        
        # Check for conflicting information
        if 'duration' in results and 'end_datetime' in results:
            # Both duration and explicit end time present - flag for review
            validation.add_field_suggestion('end_datetime', 'Both duration and end time specified - using end time')
        
        # Validate location consistency
        if 'location' in results and results['location'].value:
            location = results['location'].value
            if isinstance(location, str) and len(location.strip()) < 3:
                validation.add_field_warning('location', 'Location seems too short - please verify')
        
        # Validate title quality
        if 'title' in results and results['title'].value:
            title = results['title'].value
            if isinstance(title, str):
                if len(title.strip()) < 3:
                    validation.add_field_warning('title', 'Title seems too short')
                elif len(title) > 100:
                    validation.add_field_warning('title', 'Title seems very long - consider shortening')
                elif title.lower().strip() in ['meeting', 'event', 'appointment']:
                    validation.add_field_suggestion('title', 'Generic title - consider making more specific')
        
        return validation
    
    def optimize_processing_order(self, fields: List[str]) -> List[str]:
        """
        Sequence fields for efficient processing based on dependencies.
        
        Args:
            fields: List of field names to process
            
        Returns:
            Optimized list of fields in processing order
        """
        if not fields:
            return []
        
        # Create field priority mapping
        field_priorities = {}
        for field in fields:
            field_priorities[field] = self.field_priorities.get(field, 10)
        
        # Sort by priority (lower number = higher priority)
        sorted_fields = sorted(fields, key=lambda f: field_priorities[f])
        
        # Apply dependency-based adjustments
        optimized_order = []
        remaining_fields = set(sorted_fields)
        
        # Process fields with dependencies first
        dependency_order = [
            'start_datetime',    # Must be first - needed for relative calculations
            'duration',          # Process before end_datetime if both present
            'end_datetime',      # Process after start_datetime and duration
            'title',             # Independent but essential
            'location',          # Independent
            'participants',      # Independent
            'recurrence',        # Independent
            'description'        # Last - can be enhanced based on other fields
        ]
        
        # Add fields in dependency order if they're in the request
        for field in dependency_order:
            if field in remaining_fields:
                optimized_order.append(field)
                remaining_fields.remove(field)
        
        # Add any remaining fields
        for field in sorted(remaining_fields):
            optimized_order.append(field)
        
        return optimized_order
    
    def get_field_routing_summary(self, analyses: Dict[str, FieldAnalysis]) -> Dict[str, Any]:
        """
        Generate a summary of field routing decisions for audit purposes.
        
        Args:
            analyses: Field analyses from analyze_field_extractability
            
        Returns:
            Summary dictionary with routing decisions and confidence breakdown
        """
        summary = {
            'total_fields': len(analyses),
            'routing_decisions': {},
            'confidence_breakdown': {},
            'processing_order': [],
            'high_confidence_fields': [],
            'low_confidence_fields': [],
            'complexity_analysis': {}
        }
        
        # Extract routing decisions and confidence scores
        for field_name, analysis in analyses.items():
            summary['routing_decisions'][field_name] = analysis.recommended_method.value
            summary['confidence_breakdown'][field_name] = analysis.confidence_potential
            
            # Categorize by confidence
            if analysis.confidence_potential >= self.confidence_thresholds['high_confidence']:
                summary['high_confidence_fields'].append(field_name)
            elif analysis.confidence_potential < self.confidence_thresholds['medium_confidence']:
                summary['low_confidence_fields'].append(field_name)
            
            # Add complexity analysis
            summary['complexity_analysis'][field_name] = {
                'complexity_score': analysis.complexity_score,
                'ambiguities': analysis.ambiguity_indicators,
                'pattern_matches': analysis.pattern_matches
            }
        
        # Generate optimized processing order
        field_names = list(analyses.keys())
        summary['processing_order'] = self.optimize_processing_order(field_names)
        
        # Add summary statistics
        confidences = [a.confidence_potential for a in analyses.values()]
        if confidences:
            summary['average_confidence'] = sum(confidences) / len(confidences)
            summary['min_confidence'] = min(confidences)
            summary['max_confidence'] = max(confidences)
        
        return summary