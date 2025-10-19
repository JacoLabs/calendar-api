"""
Unified event parser service that integrates DateTimeParser and EventInformationExtractor
to provide complete event parsing functionality from natural language text.
"""

from typing import Optional, List, Dict, Any, Tuple, Union
from datetime import datetime, timedelta, time
import re

from models.event_models import ParsedEvent, ValidationResult
from services.datetime_parser import DateTimeParser, DateTimeMatch
from services.event_extractor import EventInformationExtractor, ExtractionMatch
from services.text_merge_helper import TextMergeHelper
from services.hybrid_event_parser import HybridEventParser, HybridParsingResult
from ui.safe_input import safe_input, confirm_action, get_choice, is_non_interactive


class EventParser:
    """
    Unified service for parsing complete event information from natural language text.
    Integrates date/time parsing with event information extraction to create ParsedEvent objects.
    """
    
    def __init__(self):
        self.datetime_parser = DateTimeParser()
        self.info_extractor = EventInformationExtractor()
        self.text_merge_helper = TextMergeHelper()
        
        # Initialize hybrid parser for Task 26.4
        self.hybrid_parser = HybridEventParser()
        
        # Configuration for parsing behavior
        self.config = {
            'prefer_dd_mm_format': False,  # Can be set based on user locale
            'default_event_duration_minutes': 60,  # Default 1 hour if no duration specified
            'max_datetime_distance': 100,  # Max characters between date and time for combination
            'min_confidence_threshold': 0.3,  # Minimum confidence to include in results
            'enable_ambiguity_detection': True,  # Whether to detect and flag ambiguous text
            'use_hybrid_parsing': True,  # Enable hybrid parsing pipeline (Task 26.4)
            'hybrid_mode': 'hybrid',  # hybrid|regex_only|llm_only
        }
    
    def parse_text_enhanced(self, text: str, clipboard_text: Optional[str] = None, **kwargs) -> ParsedEvent:
        """
        Parse natural language text with LLM enhancement and smart merging.
        
        Args:
            text: Input text containing event information
            clipboard_text: Optional clipboard content for smart merging
            **kwargs: Optional configuration overrides
            
        Returns:
            ParsedEvent object with extracted information and confidence scores
        """
        if not text or not text.strip():
            return ParsedEvent(
                description=text,
                confidence_score=0.0,
                extraction_metadata={'error': 'Empty or invalid input text'}
            )
        
        # Step 1: Enhance text using LLM and smart merging
        merge_result = self.text_merge_helper.enhance_text_for_parsing(text, clipboard_text)
        enhanced_text = merge_result.final_text

        # Step 2: Parse the enhanced text using hybrid parsing (uses RegexDateExtractor which handles "noon" correctly)
        parsed_event = self.parse_event_text(enhanced_text, **kwargs)
        
        # Step 3: Apply safer defaults if needed
        parsed_event = self.text_merge_helper.apply_safer_defaults(parsed_event, enhanced_text)
        
        # Step 4: Update metadata with enhancement information
        if parsed_event.extraction_metadata is None:
            parsed_event.extraction_metadata = {}
        
        parsed_event.extraction_metadata.update({
            'text_enhancement': {
                'original_text': text,
                'enhanced_text': enhanced_text,
                'merge_applied': merge_result.merge_applied,
                'enhancement_applied': merge_result.enhancement_applied,
                'enhancement_confidence': merge_result.confidence,
                'enhancement_metadata': merge_result.metadata
            }
        })
        
        # Boost overall confidence if enhancement was successful
        if merge_result.enhancement_applied and merge_result.confidence > 0.7:
            parsed_event.confidence_score = min(1.0, parsed_event.confidence_score * 1.2)
        
        return parsed_event

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
            
            # Check if this should be an all-day event
            if hasattr(best_datetime, 'is_all_day') and best_datetime.is_all_day:
                parsed_event.all_day = True
                # For all-day events, set end_datetime to next day at midnight
                next_day = parsed_event.start_datetime.date() + timedelta(days=1)
                parsed_event.end_datetime = datetime.combine(next_day, time(0, 0))
            else:
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
    
    def parse_event_text(self, text: str, **kwargs) -> ParsedEvent:
        """
        Parse event text using hybrid regex-LLM pipeline (Task 26.4).
        
        This is the new main parsing method that implements the hybrid strategy:
        - Regex ≥ 0.8: LLM enhancement mode
        - Regex < 0.8: Full LLM parsing with confidence ≤ 0.5 and warning
        
        Args:
            text: Input text containing event information
            **kwargs: Configuration overrides (mode, timezone_offset, current_time, etc.)
            
        Returns:
            ParsedEvent object with hybrid parsing results
        """
        if not text or not text.strip():
            return ParsedEvent(
                description=text,
                confidence_score=0.0,
                extraction_metadata={'error': 'Empty or invalid input text'}
            )
        
        # Check if hybrid parsing is enabled
        if not self.config.get('use_hybrid_parsing', True):
            # Fall back to legacy parsing
            return self.parse_text(text, **kwargs)
        
        # Apply configuration overrides
        config = self.config.copy()
        config.update(kwargs)
        
        # Extract parsing parameters
        mode = config.get('hybrid_mode', 'hybrid')
        timezone_offset = config.get('timezone_offset')
        current_time = config.get('current_time')
        
        # Update hybrid parser current time if provided
        if current_time:
            self.hybrid_parser.current_time = current_time
        
        # Execute hybrid parsing
        try:
            result = self.hybrid_parser.parse_event_text(
                text=text,
                mode=mode,
                timezone_offset=timezone_offset,
                current_time=current_time
            )
            
            # Extract ParsedEvent from hybrid result
            parsed_event = result.parsed_event
            
            # Add hybrid-specific metadata
            if not parsed_event.extraction_metadata:
                parsed_event.extraction_metadata = {}
            
            parsed_event.extraction_metadata.update({
                'hybrid_parsing_used': True,
                'parsing_path': result.parsing_path,
                'warnings': result.warnings,
                'processing_metadata': result.processing_metadata,
                'hybrid_confidence': result.confidence_score
            })
            
            # Collect telemetry if enabled
            if config.get('enable_telemetry', True):
                telemetry = self.hybrid_parser.collect_telemetry(text, result)
                parsed_event.extraction_metadata['telemetry'] = telemetry
            
            return parsed_event
            
        except Exception as e:
            # Fall back to legacy parsing on error
            import logging
            logging.error(f"Hybrid parsing failed: {e}")
            
            fallback_event = self.parse_text(text, **kwargs)
            
            # Add error metadata
            if not fallback_event.extraction_metadata:
                fallback_event.extraction_metadata = {}
            
            fallback_event.extraction_metadata.update({
                'hybrid_parsing_used': False,
                'hybrid_parsing_error': str(e),
                'fallback_to_legacy': True
            })
            
            return fallback_event
    
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
                # Use hybrid parsing for each segment
                parsed_event = self.parse_event_text(segment, **kwargs)
                # Only include events that meet minimum confidence threshold
                if parsed_event.confidence_score >= self.config['min_confidence_threshold']:
                    events.append(parsed_event)
        
        # If no valid events found in segments, try parsing the entire text as one event
        if not events:
            full_event = self.parse_event_text(text, **kwargs)
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
                match.pattern_type.endswith('+time_range_end_from_to_mixed') or
                match.pattern_type.endswith('+time_range_end_simple_to_12hour')):
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
        
        # Update hybrid parser configuration if relevant keys are present
        hybrid_keys = ['regex_confidence_threshold', 'warning_confidence_threshold', 
                      'default_mode', 'enable_telemetry', 'max_processing_time']
        hybrid_config = {k: v for k, v in kwargs.items() if k in hybrid_keys}
        if hybrid_config:
            self.hybrid_parser.update_config(**hybrid_config)
    
    def get_config(self) -> Dict[str, Any]:
        """Get current parser configuration."""
        return self.config.copy()
    
    def parse_with_clarification(self, text: str, **kwargs) -> ParsedEvent:
        """
        Parse text with user clarification for ambiguous information.
        
        Args:
            text: Input text containing event information
            **kwargs: Optional configuration overrides
            
        Returns:
            ParsedEvent object with clarified information
        """
        # First, try normal parsing
        parsed_event = self.parse_text(text, **kwargs)
        
        # Check for ambiguities that need clarification
        ambiguities = self._detect_ambiguities(text, parsed_event)
        
        if ambiguities and not is_non_interactive():
            print(f"\n🤔 Found some ambiguous information in: '{text}'")
            parsed_event = self._handle_ambiguities(text, parsed_event, ambiguities)
        
        return parsed_event
    
    def parse_multiple_with_detection(self, text: str, **kwargs) -> List[ParsedEvent]:
        """
        Enhanced multiple event parsing with better detection and user confirmation.
        
        Args:
            text: Input text that may contain multiple events
            **kwargs: Optional configuration overrides
            
        Returns:
            List of ParsedEvent objects with user confirmation for multiple events
        """
        # Try to detect multiple events more intelligently
        potential_events = self._detect_multiple_events(text)
        
        if len(potential_events) > 1 and not is_non_interactive():
            print(f"\n📅 Detected {len(potential_events)} potential events in the text:")
            for i, event_text in enumerate(potential_events, 1):
                print(f"  {i}. '{event_text.strip()}'")
            
            if confirm_action("Parse as separate events?", default_yes=True):
                events = []
                for event_text in potential_events:
                    if event_text.strip():
                        parsed = self.parse_with_clarification(event_text, **kwargs)
                        if parsed.confidence_score >= self.config['min_confidence_threshold']:
                            events.append(parsed)
                return events
            else:
                # Parse as single event
                return [self.parse_with_clarification(text, **kwargs)]
        
        # Fall back to original multiple parsing logic
        return self.parse_multiple_events(text, **kwargs)
    
    def parse_with_fallback(self, text: str, **kwargs) -> ParsedEvent:
        """
        Parse text with fallback mechanisms for failed parsing.
        
        Args:
            text: Input text containing event information
            **kwargs: Optional configuration overrides
            
        Returns:
            ParsedEvent object, potentially with manual input for missing information
        """
        # Try normal parsing first
        parsed_event = self.parse_text(text, **kwargs)
        
        # Check if parsing was successful enough
        if parsed_event.confidence_score < 0.2 or not parsed_event.title:
            if not is_non_interactive():
                print(f"\n⚠️  Having trouble parsing: '{text}'")
                print("Let me help you create this event manually.")
                
                # Offer manual input for missing critical information
                parsed_event = self._manual_input_fallback(text, parsed_event)
            else:
                # In non-interactive mode, try to extract what we can
                parsed_event = self._auto_fallback(text, parsed_event)
        
        return parsed_event
    
    def _detect_ambiguities(self, text: str, parsed_event: ParsedEvent) -> List[Dict[str, Any]]:
        """
        Detect ambiguous information in the parsed event.
        
        Args:
            text: Original input text
            parsed_event: Parsed event to check for ambiguities
            
        Returns:
            List of ambiguity descriptions
        """
        ambiguities = []
        metadata = parsed_event.extraction_metadata
        
        # Check for multiple datetime matches
        if metadata.get('multiple_datetime_matches', 0) > 1:
            all_matches = metadata.get('all_datetime_matches', [])
            if len(all_matches) > 1:
                ambiguities.append({
                    'type': 'datetime',
                    'message': 'Multiple possible dates/times found',
                    'options': all_matches,
                    'current_choice': 0  # Currently using first match
                })
        
        # Check for multiple title matches
        if metadata.get('multiple_title_matches', 0) > 1:
            all_matches = metadata.get('all_title_matches', [])
            if len(all_matches) > 1:
                ambiguities.append({
                    'type': 'title',
                    'message': 'Multiple possible titles found',
                    'options': all_matches,
                    'current_choice': 0
                })
        
        # Check for multiple location matches
        if metadata.get('multiple_location_matches', 0) > 1:
            all_matches = metadata.get('all_location_matches', [])
            if len(all_matches) > 1:
                ambiguities.append({
                    'type': 'location',
                    'message': 'Multiple possible locations found',
                    'options': all_matches,
                    'current_choice': 0
                })
        
        # Check for low confidence extractions
        if metadata.get('datetime_confidence', 1.0) < 0.6 and parsed_event.start_datetime:
            ambiguities.append({
                'type': 'datetime_confidence',
                'message': f"Date/time extraction has low confidence ({metadata.get('datetime_confidence', 0)*100:.0f}%)",
                'current_value': parsed_event.start_datetime,
                'suggestion': 'Please verify the date and time'
            })
        
        if metadata.get('title_confidence', 1.0) < 0.6 and parsed_event.title:
            ambiguities.append({
                'type': 'title_confidence',
                'message': f"Title extraction has low confidence ({metadata.get('title_confidence', 0)*100:.0f}%)",
                'current_value': parsed_event.title,
                'suggestion': 'Please verify the event title'
            })
        
        return ambiguities
    
    def _handle_ambiguities(self, text: str, parsed_event: ParsedEvent, ambiguities: List[Dict[str, Any]]) -> ParsedEvent:
        """
        Handle ambiguities through user interaction.
        
        Args:
            text: Original input text
            parsed_event: Current parsed event
            ambiguities: List of detected ambiguities
            
        Returns:
            ParsedEvent with resolved ambiguities
        """
        for ambiguity in ambiguities:
            if ambiguity['type'] == 'datetime' and 'options' in ambiguity:
                options = ambiguity['options']
                if len(options) > 1:
                    print(f"\n{ambiguity['message']}:")
                    choice_texts = []
                    for i, option in enumerate(options):
                        dt_str = option['datetime']
                        pattern = option.get('pattern_type', 'unknown')
                        confidence = option.get('confidence', 0) * 100
                        choice_texts.append(f"{dt_str} (from {pattern}, {confidence:.0f}% confidence)")
                    
                    choice_idx = get_choice("Which date/time did you mean?", choice_texts, 0)
                    if 0 <= choice_idx < len(options):
                        selected_option = options[choice_idx]
                        parsed_event.start_datetime = datetime.fromisoformat(selected_option['datetime'])
                        # Update end time if it exists
                        if parsed_event.end_datetime:
                            duration = parsed_event.end_datetime - datetime.fromisoformat(ambiguity['options'][0]['datetime'])
                            parsed_event.end_datetime = parsed_event.start_datetime + duration
            
            elif ambiguity['type'] == 'title' and 'options' in ambiguity:
                options = ambiguity['options']
                if len(options) > 1:
                    print(f"\n{ambiguity['message']}:")
                    choice_texts = []
                    for option in options:
                        title = option['title']
                        extraction_type = option.get('extraction_type', 'unknown')
                        confidence = option.get('confidence', 0) * 100
                        choice_texts.append(f"'{title}' (from {extraction_type}, {confidence:.0f}% confidence)")
                    
                    choice_idx = get_choice("Which title did you mean?", choice_texts, 0)
                    if 0 <= choice_idx < len(options):
                        parsed_event.title = options[choice_idx]['title']
            
            elif ambiguity['type'] == 'location' and 'options' in ambiguity:
                options = ambiguity['options']
                if len(options) > 1:
                    print(f"\n{ambiguity['message']}:")
                    choice_texts = []
                    for option in options:
                        location = option['location']
                        extraction_type = option.get('extraction_type', 'unknown')
                        confidence = option.get('confidence', 0) * 100
                        choice_texts.append(f"'{location}' (from {extraction_type}, {confidence:.0f}% confidence)")
                    
                    choice_idx = get_choice("Which location did you mean?", choice_texts, 0)
                    if 0 <= choice_idx < len(options):
                        parsed_event.location = options[choice_idx]['location']
            
            elif ambiguity['type'] in ['datetime_confidence', 'title_confidence']:
                print(f"\n⚠️  {ambiguity['message']}")
                print(f"Current value: {ambiguity['current_value']}")
                if ambiguity.get('suggestion'):
                    print(f"Suggestion: {ambiguity['suggestion']}")
                
                if confirm_action("Would you like to manually correct this?", default_yes=False):
                    if ambiguity['type'] == 'datetime_confidence':
                        new_datetime = self._prompt_for_datetime()
                        if new_datetime:
                            parsed_event.start_datetime = new_datetime
                            # Adjust end time to maintain duration
                            if parsed_event.end_datetime:
                                duration = parsed_event.end_datetime - ambiguity['current_value']
                                parsed_event.end_datetime = new_datetime + duration
                    
                    elif ambiguity['type'] == 'title_confidence':
                        new_title = safe_input("Enter the correct title: ", str(ambiguity['current_value']))
                        if new_title.strip():
                            parsed_event.title = new_title.strip()
        
        return parsed_event
    
    def _detect_multiple_events(self, text: str) -> List[str]:
        """
        Detect multiple events in text using improved heuristics.
        
        Args:
            text: Input text to analyze
            
        Returns:
            List of text segments, each potentially containing one event
        """
        # Enhanced event detection patterns
        event_separators = [
            r'\b(?:then|next|after that|also|and then|followed by)\b',
            r'\b(?:another|second|third|fourth|fifth)\s+(?:meeting|event|appointment|call)\b',
            r'\n\s*[-*•]\s*',  # Bullet points
            r'\n\s*\d+\.\s*',  # Numbered lists
            r'\n\s*\w+\)\s*',  # Letter lists (a), b), etc.
            r'\band\s+(?:at\s+\d+(?::\d+)?(?:am|pm)?|on\s+(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday))',  # "and at 2pm" or "and on Friday"
            r'(?<=\.)[\s\n]+(?=\w+.*(?:meeting|appointment|call|lunch|dinner|event))',  # Sentence boundaries followed by event words
        ]
        
        # First try splitting on clear separators
        segments = [text]
        
        for separator_pattern in event_separators:
            new_segments = []
            for segment in segments:
                parts = re.split(separator_pattern, segment, flags=re.IGNORECASE)
                # Filter out very short segments (likely not complete events)
                parts = [part.strip() for part in parts if len(part.strip()) > 10]
                new_segments.extend(parts)
            segments = new_segments
        
        # If we found multiple segments, validate they look like events
        if len(segments) > 1:
            valid_segments = []
            for segment in segments:
                # Check if segment contains event-like content
                if self._looks_like_event(segment):
                    valid_segments.append(segment)
            
            if len(valid_segments) > 1:
                return valid_segments
        
        # Fall back to original segmentation logic
        return self._split_into_event_segments(text)
    
    def _looks_like_event(self, text: str) -> bool:
        """
        Check if a text segment looks like it contains event information.
        
        Args:
            text: Text segment to check
            
        Returns:
            True if the text looks like an event
        """
        text_lower = text.lower()
        
        # Must be reasonably long first
        if len(text.strip()) <= 5:
            return False
        
        # Check for event keywords
        event_keywords = [
            'meeting', 'call', 'appointment', 'lunch', 'dinner', 'breakfast',
            'interview', 'presentation', 'demo', 'training', 'workshop',
            'conference', 'seminar', 'review', 'standup', 'sync', 'event'
        ]
        
        has_event_keyword = any(keyword in text_lower for keyword in event_keywords)
        
        # Check for time indicators
        time_patterns = [
            r'\b\d{1,2}(?::\d{2})?\s*(?:am|pm)\b',
            r'\b\d{1,2}:\d{2}\b',
            r'\b(?:tomorrow|today|yesterday|monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b',
            r'\b(?:at|on|from|until)\s+\d',
        ]
        
        has_time_indicator = any(re.search(pattern, text_lower) for pattern in time_patterns)
        
        # Must have either event keyword or time indicator
        # Additional check: avoid false positives on generic text
        if not (has_event_keyword or has_time_indicator):
            return False
        
        # Avoid false positives on text that's just describing events generically
        generic_phrases = ['event indicators', 'without event', 'random text']
        if any(phrase in text_lower for phrase in generic_phrases):
            return False
        
        return True
    
    def _manual_input_fallback(self, original_text: str, parsed_event: ParsedEvent) -> ParsedEvent:
        """
        Fallback to manual input for missing information.
        
        Args:
            original_text: Original input text
            parsed_event: Current parsed event (may be incomplete)
            
        Returns:
            ParsedEvent with manually entered information
        """
        print(f"Original text: '{original_text}'")
        print("Let's fill in the missing information:")
        
        # Get title if missing or low confidence
        if not parsed_event.title or parsed_event.extraction_metadata.get('title_confidence', 0) < 0.3:
            title = safe_input("Event title: ", parsed_event.title or "")
            if title and title.strip():
                parsed_event.title = title.strip()
        
        # Get datetime if missing or low confidence
        if not parsed_event.start_datetime or parsed_event.extraction_metadata.get('datetime_confidence', 0) < 0.3:
            new_datetime = self._prompt_for_datetime()
            if new_datetime:
                parsed_event.start_datetime = new_datetime
        
        # Get end time if missing
        if not parsed_event.end_datetime and parsed_event.start_datetime:
            duration_str = safe_input("Event duration (e.g., '1 hour', '30 minutes'): ", "1 hour")
            if duration_str:
                duration = self._parse_duration_string(duration_str)
                parsed_event.end_datetime = parsed_event.start_datetime + duration
        
        # Get location if missing
        if not parsed_event.location:
            location = safe_input("Location (optional): ", "")
            if location and location.strip():
                parsed_event.location = location.strip()
        
        # Update confidence score since we have manual input
        parsed_event.confidence_score = 0.9  # High confidence for manual input
        
        return parsed_event
    
    def _auto_fallback(self, original_text: str, parsed_event: ParsedEvent) -> ParsedEvent:
        """
        Automatic fallback for non-interactive mode.
        
        Args:
            original_text: Original input text
            parsed_event: Current parsed event
            
        Returns:
            ParsedEvent with reasonable defaults
        """
        # Set default title if missing
        if not parsed_event.title:
            # Try to extract first few words as title
            words = original_text.strip().split()[:5]
            parsed_event.title = ' '.join(words) if words else "Event"
        
        # Set default datetime if missing
        if not parsed_event.start_datetime:
            # Default to tomorrow at 9 AM
            from datetime import datetime, timedelta
            tomorrow = datetime.now() + timedelta(days=1)
            parsed_event.start_datetime = tomorrow.replace(hour=9, minute=0, second=0, microsecond=0)
        
        # Set default end time if missing
        if not parsed_event.end_datetime and parsed_event.start_datetime:
            parsed_event.end_datetime = parsed_event.start_datetime + timedelta(hours=1)
        
        # Set reasonable confidence for auto-fallback
        parsed_event.confidence_score = 0.4
        
        return parsed_event
    
    def _prompt_for_datetime(self) -> Optional[datetime]:
        """
        Prompt user for date and time input.
        
        Returns:
            datetime object or None if input failed
        """
        try:
            date_str = safe_input("Date (YYYY-MM-DD or 'today', 'tomorrow'): ", "")
            if not date_str:
                return None
            
            # Parse date
            if date_str.lower() == 'today':
                from datetime import date
                event_date = date.today()
            elif date_str.lower() == 'tomorrow':
                from datetime import date, timedelta
                event_date = date.today() + timedelta(days=1)
            else:
                event_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            
            time_str = safe_input("Time (HH:MM or HH:MM AM/PM): ", "09:00")
            if not time_str:
                time_str = "09:00"
            
            # Parse time
            event_time = self._parse_time_string(time_str)
            
            return datetime.combine(event_date, event_time)
            
        except ValueError as e:
            print(f"Invalid date/time format: {e}")
            return None
    
    def _parse_time_string(self, time_str: str) -> datetime.time:
        """
        Parse time string in various formats.
        
        Args:
            time_str: Time string to parse
            
        Returns:
            time object
        """
        time_str = time_str.strip().upper()
        
        # Try different time formats
        formats = [
            "%H:%M",      # 24-hour
            "%I:%M %p",   # 12-hour with AM/PM
            "%I %p",      # Hour only with AM/PM
            "%H",         # Hour only 24-hour
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(time_str, fmt).time()
            except ValueError:
                continue
        
        raise ValueError(f"Could not parse time: {time_str}")
    
    def _parse_duration_string(self, duration_str: str) -> timedelta:
        """
        Parse duration string into timedelta.
        
        Args:
            duration_str: Duration string like "1 hour", "30 minutes"
            
        Returns:
            timedelta object
        """
        duration_str = duration_str.lower().strip()
        
        # Extract number and unit
        import re
        match = re.search(r'(\d+(?:\.\d+)?)\s*(hour|hr|minute|min|day)s?', duration_str)
        
        if match:
            value = float(match.group(1))
            unit = match.group(2)
            
            if unit in ['hour', 'hr']:
                return timedelta(hours=value)
            elif unit in ['minute', 'min']:
                return timedelta(minutes=value)
            elif unit == 'day':
                return timedelta(days=value)
        
        # Default to 1 hour if parsing fails
        return timedelta(hours=1)