"""
Unified event parser service that integrates DateTimeParser and EventInformationExtractor
to provide complete event parsing functionality from natural language text.
"""

from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timedelta
import re

from models.event_models import ParsedEvent, ValidationResult
from services.datetime_parser import DateTimeParser, DateTimeMatch
from services.event_extractor import EventInformationExtractor, ExtractionMatch


class EventParser:
    """
    Unified service for parsing complete event information from natural language text.
    Integrates date/time parsing with event information extraction to create ParsedEvent objects.
    """
    
    def __init__(self):
        self.datetime_parser = DateTimeParser()
        self.info_extractor = EventInformationExtractor()
        
        # Configuration for parsing behavior
        self.config = {
            'prefer_dd_mm_format': False,  # Can be set based on user locale
            'default_event_duration_minutes': 60,  # Default 1 hour if no duration specified
            'max_datetime_distance': 100,  # Max characters between date and time for combination
            'min_confidence_threshold': 0.3,  # Minimum confidence to include in results
            'enable_ambiguity_detection': True,  # Whether to detect and flag ambiguous text
        }
    
    def parse_text(self, text: str, **kwargs) -> ParsedEvent:
        """
        Parse natural language text and return a complete ParsedEvent object.
        
        Args:
            text: Input text containing event information
            **kwargs: Optional configuration overrides (prefer_dd_mm, default_duration, etc.)
            
        Returns:
            ParsedEvent object with extracted information and confidence scores
        """
        if not text or not text.strip():
            return ParsedEvent(
                description=text,
                confidence_score=0.0,
                extraction_metadata={'error': 'Empty or invalid input text'}
            )
        
        # Apply any configuration overrides
        config = self.config.copy()
        config.update(kwargs)
        
        # Extract all components
        datetime_matches = self.datetime_parser.extract_datetime(
            text, 
            prefer_dd_mm=config['prefer_dd_mm_format']
        )
        duration_matches = self.datetime_parser.extract_durations(text)
        title_matches = self.info_extractor.extract_title(text)
        location_matches = self.info_extractor.extract_location(text)
        
        # Create ParsedEvent with best matches
        parsed_event = ParsedEvent()
        parsed_event.description = text
        
        # Set title (highest confidence match)
        if title_matches:
            best_title = title_matches[0]
            parsed_event.title = best_title.value
        
        # Set datetime (highest confidence match)
        if datetime_matches:
            best_datetime = datetime_matches[0]
            parsed_event.start_datetime = best_datetime.value
            
            # Check if we have an explicit end time from a time range
            end_time = self._find_explicit_end_time(datetime_matches, best_datetime)
            
            if end_time:
                # Use explicit end time from time range
                parsed_event.end_datetime = end_time
            else:
                # Calculate end time from duration or use default
                end_time = self._calculate_end_time(
                    parsed_event.start_datetime, 
                    duration_matches, 
                    config['default_event_duration_minutes']
                )
                parsed_event.end_datetime = end_time
        
        # Set location (highest confidence match)
        if location_matches:
            best_location = location_matches[0]
            parsed_event.location = best_location.value
        
        # Calculate overall confidence and store metadata
        parsed_event.extraction_metadata = self._build_extraction_metadata(
            text, datetime_matches, duration_matches, title_matches, location_matches, config
        )
        
        # Calculate overall confidence using the info extractor's method
        parsed_event.confidence_score = self.info_extractor.calculate_overall_confidence(parsed_event)
        
        return parsed_event
    
    def parse_multiple_events(self, text: str, **kwargs) -> List[ParsedEvent]:
        """
        Parse text that may contain multiple events and return a list of ParsedEvent objects.
        
        Args:
            text: Input text that may contain multiple events
            **kwargs: Optional configuration overrides
            
        Returns:
            List of ParsedEvent objects, one for each detected event
        """
        # Split text into potential event segments
        event_segments = self._split_into_event_segments(text)
        
        events = []
        for segment in event_segments:
            if segment.strip():
                parsed_event = self.parse_text(segment, **kwargs)
                # Only include events that meet minimum confidence threshold
                if parsed_event.confidence_score >= self.config['min_confidence_threshold']:
                    events.append(parsed_event)
        
        # If no valid events found in segments, try parsing the entire text as one event
        if not events:
            full_event = self.parse_text(text, **kwargs)
            if full_event.confidence_score >= self.config['min_confidence_threshold']:
                events.append(full_event)
        
        return events
    
    def validate_parsed_event(self, parsed_event: ParsedEvent) -> ValidationResult:
        """
        Validate a parsed event and provide feedback on missing or problematic information.
        
        Args:
            parsed_event: ParsedEvent to validate
            
        Returns:
            ValidationResult with validation status and suggestions
        """
        result = ValidationResult(is_valid=True)
        
        # Check required fields
        if not parsed_event.title:
            result.add_missing_field('title', 'Event needs a descriptive title')
        
        if not parsed_event.start_datetime:
            result.add_missing_field('start_datetime', 'Event needs a start date and time')
        
        # Check for potential issues
        if parsed_event.start_datetime and parsed_event.end_datetime:
            if parsed_event.start_datetime >= parsed_event.end_datetime:
                result.add_warning('End time should be after start time')
                result.is_valid = False
            
            # Check for unreasonably long events (more than 12 hours)
            duration = parsed_event.end_datetime - parsed_event.start_datetime
            if duration.total_seconds() > 12 * 3600:
                result.add_warning('Event duration seems unusually long (more than 12 hours)')
        
        # Check confidence levels
        metadata = parsed_event.extraction_metadata
        if metadata.get('title_confidence', 1.0) < 0.5:
            result.add_suggestion('Title extraction has low confidence - please verify')
        
        if metadata.get('datetime_confidence', 1.0) < 0.5:
            result.add_suggestion('Date/time extraction has low confidence - please verify')
        
        if metadata.get('location_confidence', 1.0) < 0.5 and parsed_event.location:
            result.add_suggestion('Location extraction has low confidence - please verify')
        
        # Check for ambiguous information
        if metadata.get('has_ambiguous_datetime', False):
            result.add_warning('Date/time information may be ambiguous')
        
        if metadata.get('multiple_datetime_matches', 0) > 1:
            result.add_suggestion('Multiple possible dates/times found - using most confident match')
        
        if metadata.get('multiple_title_matches', 0) > 1:
            result.add_suggestion('Multiple possible titles found - using most confident match')
        
        return result
    
    def get_parsing_suggestions(self, text: str) -> List[str]:
        """
        Analyze text and provide suggestions for improving parsing accuracy.
        
        Args:
            text: Input text to analyze
            
        Returns:
            List of suggestions for the user
        """
        suggestions = []
        
        # Check for common issues
        if not re.search(r'\d', text):
            suggestions.append('Consider adding specific dates or times (e.g., "tomorrow at 2pm")')
        
        if len(text.split()) < 3:
            suggestions.append('More descriptive text usually improves parsing accuracy')
        
        if not re.search(r'\b(?:at|in|@)\b', text, re.IGNORECASE):
            suggestions.append('Adding location keywords like "at" or "in" can help identify venues')
        
        # Check for potential ambiguities
        datetime_matches = self.datetime_parser.extract_datetime(text)
        if len(datetime_matches) > 1:
            suggestions.append('Multiple dates/times detected - consider being more specific')
        
        title_matches = self.info_extractor.extract_title(text)
        if len(title_matches) > 1:
            suggestions.append('Multiple potential titles found - consider using quotes around the main title')
        
        # Check for missing information
        if not datetime_matches:
            suggestions.append('No date/time information found - try adding when the event occurs')
        
        if not title_matches:
            suggestions.append('No clear title found - consider starting with the event name')
        
        return suggestions
    
    def _find_explicit_end_time(self, datetime_matches: List[DateTimeMatch], start_match: DateTimeMatch) -> Optional[datetime]:
        """
        Find explicit end time from time range patterns.
        
        Args:
            datetime_matches: All datetime matches found
            start_match: The selected start time match
            
        Returns:
            End datetime if found, None otherwise
        """
        # Look for a corresponding end time match from the same time range
        for match in datetime_matches:
            # Check if this is an end time match from the same time range
            if (match.pattern_type.startswith('time_range_end_') and
                match.start_pos == start_match.start_pos and
                match.end_pos == start_match.end_pos and
                match.matched_text == start_match.matched_text):
                return match.value
            
            # Also check for combined date+time_range_end patterns
            if (match.pattern_type.endswith('+time_range_end_from_to_12hour') or
                match.pattern_type.endswith('+time_range_end_from_to_24hour') or
                match.pattern_type.endswith('+time_range_end_from_to_mixed')):
                # This is a combined date+end_time match
                return match.value
        
        return None
    
    def _calculate_end_time(self, start_datetime: datetime, duration_matches: List, default_duration_minutes: int) -> datetime:
        """Calculate end time based on duration information or default duration."""
        if duration_matches:
            # Use the most confident duration match
            best_duration = duration_matches[0]
            return start_datetime + best_duration.duration
        else:
            # Use default duration
            return start_datetime + timedelta(minutes=default_duration_minutes)
    
    def _build_extraction_metadata(self, text: str, datetime_matches: List[DateTimeMatch], 
                                 duration_matches: List, title_matches: List[ExtractionMatch], 
                                 location_matches: List[ExtractionMatch], config: Dict[str, Any]) -> Dict[str, Any]:
        """Build comprehensive metadata about the extraction process."""
        metadata = {
            'original_text': text,
            'parsing_config': config.copy(),
            'extraction_timestamp': datetime.now().isoformat(),
            
            # DateTime extraction info
            'datetime_matches_found': len(datetime_matches),
            'datetime_confidence': datetime_matches[0].confidence if datetime_matches else 0.0,
            'datetime_pattern_type': datetime_matches[0].pattern_type if datetime_matches else None,
            'datetime_matched_text': datetime_matches[0].matched_text if datetime_matches else None,
            
            # Duration extraction info
            'duration_matches_found': len(duration_matches),
            'duration_confidence': duration_matches[0].confidence if duration_matches else 0.0,
            'duration_matched_text': duration_matches[0].matched_text if duration_matches else None,
            'used_default_duration': len(duration_matches) == 0,
            
            # Title extraction info
            'title_matches_found': len(title_matches),
            'title_confidence': title_matches[0].confidence if title_matches else 0.0,
            'title_extraction_type': title_matches[0].extraction_type if title_matches else None,
            'title_matched_text': title_matches[0].matched_text if title_matches else None,
            
            # Location extraction info
            'location_matches_found': len(location_matches),
            'location_confidence': location_matches[0].confidence if location_matches else 0.0,
            'location_extraction_type': location_matches[0].extraction_type if location_matches else None,
            'location_matched_text': location_matches[0].matched_text if location_matches else None,
            
            # Ambiguity detection
            'multiple_datetime_matches': len(datetime_matches),
            'multiple_title_matches': len(title_matches),
            'multiple_location_matches': len(location_matches),
            'has_ambiguous_datetime': len(datetime_matches) > 1,
            'has_ambiguous_title': len(title_matches) > 1,
            'has_ambiguous_location': len(location_matches) > 1,
            
            # All matches for debugging/alternative selection
            'all_datetime_matches': [
                {
                    'datetime': match.value.isoformat(),
                    'confidence': match.confidence,
                    'pattern_type': match.pattern_type,
                    'matched_text': match.matched_text,
                    'position': (match.start_pos, match.end_pos)
                }
                for match in datetime_matches
            ],
            'all_title_matches': [
                {
                    'title': match.value,
                    'confidence': match.confidence,
                    'extraction_type': match.extraction_type,
                    'matched_text': match.matched_text,
                    'position': (match.start_pos, match.end_pos)
                }
                for match in title_matches
            ],
            'all_location_matches': [
                {
                    'location': match.value,
                    'confidence': match.confidence,
                    'extraction_type': match.extraction_type,
                    'matched_text': match.matched_text,
                    'position': (match.start_pos, match.end_pos)
                }
                for match in location_matches
            ]
        }
        
        return metadata
    
    def _split_into_event_segments(self, text: str) -> List[str]:
        """
        Split text into segments that likely represent separate events.
        
        Args:
            text: Input text to segment
            
        Returns:
            List of text segments, each potentially containing one event
        """
        # Simple segmentation based on sentence boundaries and event indicators
        segments = []
        
        # Split on sentence boundaries first
        sentences = re.split(r'[.!?]+\s+', text.strip())
        
        # Look for patterns that indicate separate events
        event_separators = [
            r'\b(?:then|next|after that|also|and then)\b',
            r'\b(?:another|second|third)\s+(?:meeting|event|appointment)\b',
            r'\n\s*[-*•]\s*',  # Bullet points
            r'\n\s*\d+\.\s*',  # Numbered lists
        ]
        
        for sentence in sentences:
            if sentence.strip():
                # Check if this sentence contains multiple events
                for separator_pattern in event_separators:
                    if re.search(separator_pattern, sentence, re.IGNORECASE):
                        # Split on the separator
                        parts = re.split(separator_pattern, sentence, flags=re.IGNORECASE)
                        segments.extend([part.strip() for part in parts if part.strip()])
                        break
                else:
                    # No separator found, treat as single segment
                    segments.append(sentence.strip())
        
        # If no segments found, return the original text
        if not segments:
            segments = [text]
        
        return segments
    
    def set_config(self, **kwargs):
        """Update parser configuration."""
        self.config.update(kwargs)
    
    def get_config(self) -> Dict[str, Any]:
        """Get current parser configuration."""
        return self.config.copy()