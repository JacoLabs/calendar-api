"""
Comprehensive error handling and fallback system for event parsing.
Handles low confidence extractions, multiple interpretations, missing fields,
and provides graceful degradation with user interaction.
"""

from typing import Optional, List, Dict, Any, Tuple, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import re

from models.event_models import ParsedEvent, ValidationResult, TitleResult
from ui.safe_input import safe_input, confirm_action, get_choice, is_non_interactive


@dataclass
class ErrorHandlingResult:
    """
    Result of error handling process with resolution details.
    """
    success: bool
    resolved_event: Optional[ParsedEvent] = None
    error_type: str = ""
    error_message: str = ""
    user_action_taken: str = ""
    fallback_used: str = ""
    confidence_improvement: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class InterpretationOption:
    """
    Represents an alternative interpretation for ambiguous parsing results.
    """
    field_name: str
    value: Any
    confidence: float
    source: str  # "llm", "regex", "user_input", "default"
    description: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


class ComprehensiveErrorHandler:
    """
    Comprehensive error handling and fallback system for event parsing.
    
    Handles:
    - Low confidence extraction handling (< 0.3 threshold)
    - Multiple interpretation resolution with user selection
    - Graceful degradation for missing critical fields (title, date/time)
    - Missing optional fields (location) without preventing event creation
    - "No event information found" detection and messaging
    - Partial information handling with completion prompts
    - LLM failure fallbacks to regex-based extraction
    - Consistency validation between input methods
    """
    
    def __init__(self):
        self.config = {
            'low_confidence_threshold': 0.3,
            'critical_fields': ['title', 'start_datetime'],
            'optional_fields': ['location', 'description'],
            'min_title_length': 2,
            'max_auto_retry_attempts': 2,
            'enable_user_interaction': True,
            'fallback_to_regex': True,
            'allow_partial_events': True
        }
        
        # Track error patterns for learning
        self.error_patterns = []
        self.resolution_history = []
    
    def handle_parsing_errors(self, parsed_event: ParsedEvent, original_text: str, 
                            llm_available: bool = True) -> ErrorHandlingResult:
        """
        Main entry point for handling parsing errors and low confidence results.
        
        Args:
            parsed_event: The parsed event that may have errors or low confidence
            original_text: Original input text for fallback processing
            llm_available: Whether LLM service is available for fallback
            
        Returns:
            ErrorHandlingResult with resolution details
        """
        if not parsed_event:
            return self._handle_no_event_found(original_text, llm_available)
        
        # Check overall confidence
        if parsed_event.confidence_score < self.config['low_confidence_threshold']:
            return self._handle_low_confidence(parsed_event, original_text, llm_available)
        
        # Check for multiple interpretations
        if self._has_multiple_interpretations(parsed_event):
            return self._handle_multiple_interpretations(parsed_event, original_text)
        
        # Check for missing critical fields
        missing_critical = self._get_missing_critical_fields(parsed_event)
        if missing_critical:
            return self._handle_missing_critical_fields(parsed_event, original_text, missing_critical, llm_available)
        
        # Handle missing optional fields (don't prevent event creation)
        missing_optional = self._get_missing_optional_fields(parsed_event)
        if missing_optional:
            return self._handle_missing_optional_fields(parsed_event, original_text, missing_optional)
        
        # Validate consistency
        consistency_issues = self._validate_consistency(parsed_event, original_text)
        if consistency_issues:
            return self._handle_consistency_issues(parsed_event, original_text, consistency_issues)
        
        # No errors found
        return ErrorHandlingResult(
            success=True,
            resolved_event=parsed_event,
            error_type="none",
            error_message="No errors detected"
        )
    
    def handle_llm_failure(self, original_text: str, llm_error: str = "") -> ErrorHandlingResult:
        """
        Handle LLM service failures with regex-based fallback extraction.
        
        Args:
            original_text: Original input text to parse with fallback methods
            llm_error: Error message from LLM service
            
        Returns:
            ErrorHandlingResult with fallback parsing results
        """
        if not self.config['fallback_to_regex']:
            return ErrorHandlingResult(
                success=False,
                error_type="llm_failure",
                error_message=f"LLM service failed: {llm_error}",
                fallback_used="none"
            )
        
        try:
            # Attempt regex-based fallback parsing
            fallback_event = self._regex_fallback_extraction(original_text)
            
            if fallback_event and fallback_event.confidence_score > 0:
                # Mark as fallback extraction
                if not fallback_event.extraction_metadata:
                    fallback_event.extraction_metadata = {}
                
                fallback_event.extraction_metadata.update({
                    'llm_failure': True,
                    'llm_error': llm_error,
                    'fallback_method': 'regex',
                    'fallback_confidence': fallback_event.confidence_score
                })
                
                # Reduce confidence due to fallback
                fallback_event.confidence_score *= 0.8
                
                return ErrorHandlingResult(
                    success=True,
                    resolved_event=fallback_event,
                    error_type="llm_failure",
                    error_message=f"LLM failed, used regex fallback: {llm_error}",
                    fallback_used="regex",
                    metadata={'original_llm_error': llm_error}
                )
            else:
                return self._handle_no_event_found(original_text, llm_available=False)
                
        except Exception as e:
            return ErrorHandlingResult(
                success=False,
                error_type="fallback_failure",
                error_message=f"Both LLM and regex fallback failed: {llm_error}, {str(e)}",
                fallback_used="failed"
            )
    
    def resolve_ambiguous_field(self, field_name: str, options: List[InterpretationOption], 
                              current_value: Any = None) -> Tuple[Any, str]:
        """
        Resolve ambiguous field values through user interaction or automatic selection.
        
        Args:
            field_name: Name of the field with ambiguous values
            options: List of possible interpretations
            current_value: Currently selected value
            
        Returns:
            Tuple of (selected_value, resolution_method)
        """
        if not options:
            return current_value, "no_options"
        
        # If only one option, use it
        if len(options) == 1:
            return options[0].value, "single_option"
        
        # Sort options by confidence
        sorted_options = sorted(options, key=lambda x: x.confidence, reverse=True)
        
        # If non-interactive, use highest confidence option
        if is_non_interactive() or not self.config['enable_user_interaction']:
            best_option = sorted_options[0]
            return best_option.value, f"auto_selected_{best_option.source}"
        
        # Interactive resolution
        print(f"\n🤔 Multiple possible values found for {field_name}:")
        choice_texts = []
        
        for i, option in enumerate(sorted_options):
            confidence_pct = option.confidence * 100
            desc = f" - {option.description}" if option.description else ""
            choice_texts.append(
                f"{option.value} ({option.source}, {confidence_pct:.0f}% confidence){desc}"
            )
        
        # Add option to enter custom value
        choice_texts.append("Enter a custom value")
        
        choice_idx = get_choice(f"Which {field_name} did you mean?", choice_texts, 0)
        
        if choice_idx < len(sorted_options):
            selected_option = sorted_options[choice_idx]
            return selected_option.value, f"user_selected_{selected_option.source}"
        else:
            # User wants to enter custom value
            custom_value = safe_input(f"Enter {field_name}: ")
            return custom_value, "user_custom"
    
    def validate_field_consistency(self, parsed_event: ParsedEvent, original_text: str) -> List[str]:
        """
        Validate consistency between extracted fields and original text.
        
        Args:
            parsed_event: Parsed event to validate
            original_text: Original input text
            
        Returns:
            List of consistency issues found
        """
        issues = []
        
        # Check if title appears in original text
        if parsed_event.title:
            title_words = parsed_event.title.lower().split()
            text_lower = original_text.lower()
            
            # Check if at least some title words appear in text
            matching_words = [word for word in title_words if word in text_lower]
            if len(matching_words) < len(title_words) * 0.5:  # Less than 50% match
                issues.append(f"Title '{parsed_event.title}' doesn't closely match text content")
        
        # Check if location appears in original text
        if parsed_event.location:
            location_lower = parsed_event.location.lower()
            text_lower = original_text.lower()
            
            # Look for location keywords in the original text (not in the location itself)
            location_indicators = [' at ', ' in ', '@', 'venue:', 'location:']  # Add spaces to avoid false matches
            has_location_context = any(indicator in text_lower for indicator in location_indicators)
            has_location_text = location_lower in text_lower
            
            if not has_location_context and not has_location_text:
                issues.append(f"Location '{parsed_event.location}' not clearly indicated in text")
        
        # Check datetime consistency
        if parsed_event.start_datetime:
            # Basic sanity checks
            now = datetime.now()
            
            # Check if date is too far in the past (more than 1 year)
            if parsed_event.start_datetime < now - timedelta(days=365):
                issues.append("Event date appears to be more than a year in the past")
            
            # Check if date is too far in the future (more than 10 years)
            if parsed_event.start_datetime > now + timedelta(days=365*10):
                issues.append("Event date appears to be more than 10 years in the future")
            
            # Check if end time is before start time
            if parsed_event.end_datetime and parsed_event.end_datetime <= parsed_event.start_datetime:
                issues.append("End time is before or same as start time")
        
        return issues
    
    def get_completion_prompts(self, parsed_event: ParsedEvent) -> Dict[str, str]:
        """
        Generate completion prompts for missing or low-quality fields.
        
        Args:
            parsed_event: Parsed event with potentially missing information
            
        Returns:
            Dictionary mapping field names to completion prompts
        """
        prompts = {}
        
        # Title prompts
        if not parsed_event.title or len(parsed_event.title.strip()) < self.config['min_title_length']:
            prompts['title'] = "What is the name or title of this event?"
        
        # DateTime prompts
        if not parsed_event.start_datetime:
            prompts['start_datetime'] = "When does this event start? (e.g., 'tomorrow at 2pm', 'March 15 at 9:00 AM')"
        
        if not parsed_event.end_datetime:
            prompts['end_datetime'] = "When does this event end? (or how long is it? e.g., '1 hour', 'until 3pm')"
        
        # Location prompts (optional)
        if not parsed_event.location:
            prompts['location'] = "Where is this event taking place? (optional - press Enter to skip)"
        
        # Description enhancement
        if not parsed_event.description or len(parsed_event.description.strip()) < 10:
            prompts['description'] = "Any additional details about this event? (optional)"
        
        return prompts
    
    def _handle_no_event_found(self, original_text: str, llm_available: bool) -> ErrorHandlingResult:
        """Handle case where no event information was detected."""
        # Try one more time with different approach if LLM is available
        if llm_available and self.config['fallback_to_regex']:
            fallback_event = self._regex_fallback_extraction(original_text)
            if fallback_event and fallback_event.confidence_score > 0:
                return ErrorHandlingResult(
                    success=True,
                    resolved_event=fallback_event,
                    error_type="no_event_found",
                    error_message="No event found with LLM, used regex fallback",
                    fallback_used="regex"
                )
        
        # Offer manual input if interactive
        if self.config['enable_user_interaction'] and not is_non_interactive():
            print(f"\n❌ No event information found in: '{original_text}'")
            
            if confirm_action("Would you like to create an event manually?", default_yes=False):
                manual_event = self._create_manual_event(original_text)
                return ErrorHandlingResult(
                    success=True,
                    resolved_event=manual_event,
                    error_type="no_event_found",
                    error_message="No automatic parsing possible, created manually",
                    user_action_taken="manual_creation"
                )
        
        return ErrorHandlingResult(
            success=False,
            error_type="no_event_found",
            error_message=f"No event information detected in text: '{original_text}'"
        )
    
    def _handle_low_confidence(self, parsed_event: ParsedEvent, original_text: str, 
                             llm_available: bool) -> ErrorHandlingResult:
        """Handle low confidence extraction results."""
        confidence_pct = parsed_event.confidence_score * 100
        
        # Try fallback extraction if available
        if llm_available and self.config['fallback_to_regex']:
            fallback_event = self._regex_fallback_extraction(original_text)
            
            # Use fallback if it has higher confidence
            if fallback_event and fallback_event.confidence_score > parsed_event.confidence_score:
                fallback_event.extraction_metadata = fallback_event.extraction_metadata or {}
                fallback_event.extraction_metadata['replaced_low_confidence_llm'] = True
                
                return ErrorHandlingResult(
                    success=True,
                    resolved_event=fallback_event,
                    error_type="low_confidence",
                    error_message=f"Low LLM confidence ({confidence_pct:.0f}%), used regex fallback",
                    fallback_used="regex",
                    confidence_improvement=fallback_event.confidence_score - parsed_event.confidence_score
                )
        
        # Interactive confirmation for low confidence
        if self.config['enable_user_interaction'] and not is_non_interactive():
            print(f"\n⚠️  Low confidence parsing ({confidence_pct:.0f}%) for: '{original_text}'")
            print("Extracted information:")
            self._display_parsed_event(parsed_event)
            
            if confirm_action("Does this look correct?", default_yes=False):
                return ErrorHandlingResult(
                    success=True,
                    resolved_event=parsed_event,
                    error_type="low_confidence",
                    error_message=f"Low confidence ({confidence_pct:.0f}%) but user confirmed",
                    user_action_taken="confirmed"
                )
            else:
                # Offer to edit
                edited_event = self._edit_parsed_event(parsed_event, original_text)
                return ErrorHandlingResult(
                    success=True,
                    resolved_event=edited_event,
                    error_type="low_confidence",
                    error_message=f"Low confidence ({confidence_pct:.0f}%), user edited",
                    user_action_taken="edited"
                )
        
        # Non-interactive: return as-is with warning
        return ErrorHandlingResult(
            success=True,
            resolved_event=parsed_event,
            error_type="low_confidence",
            error_message=f"Low confidence ({confidence_pct:.0f}%) - please verify results"
        )
    
    def _handle_multiple_interpretations(self, parsed_event: ParsedEvent, original_text: str) -> ErrorHandlingResult:
        """Handle multiple possible interpretations."""
        metadata = parsed_event.extraction_metadata or {}
        
        # Check for multiple datetime interpretations
        if metadata.get('multiple_datetime_matches', 0) > 1:
            datetime_options = self._extract_datetime_options(metadata)
            if datetime_options:
                selected_datetime, method = self.resolve_ambiguous_field(
                    'date/time', datetime_options, parsed_event.start_datetime
                )
                parsed_event.start_datetime = selected_datetime
                
                # Adjust end time if needed
                if parsed_event.end_datetime:
                    duration = parsed_event.end_datetime - datetime_options[0].value
                    parsed_event.end_datetime = selected_datetime + duration
        
        # Check for multiple title interpretations
        if metadata.get('multiple_title_matches', 0) > 1:
            title_options = self._extract_title_options(metadata)
            if title_options:
                selected_title, method = self.resolve_ambiguous_field(
                    'title', title_options, parsed_event.title
                )
                parsed_event.title = selected_title
        
        # Check for multiple location interpretations
        if metadata.get('multiple_location_matches', 0) > 1:
            location_options = self._extract_location_options(metadata)
            if location_options:
                selected_location, method = self.resolve_ambiguous_field(
                    'location', location_options, parsed_event.location
                )
                parsed_event.location = selected_location
        
        return ErrorHandlingResult(
            success=True,
            resolved_event=parsed_event,
            error_type="multiple_interpretations",
            error_message="Resolved multiple possible interpretations",
            user_action_taken="disambiguation"
        )
    
    def _handle_missing_critical_fields(self, parsed_event: ParsedEvent, original_text: str, 
                                      missing_fields: List[str], llm_available: bool) -> ErrorHandlingResult:
        """Handle missing critical fields (title, start_datetime)."""
        # Try fallback extraction for missing fields
        if llm_available and self.config['fallback_to_regex']:
            fallback_event = self._regex_fallback_extraction(original_text)
            
            # Fill in missing fields from fallback
            if fallback_event:
                for field in missing_fields:
                    fallback_value = getattr(fallback_event, field, None)
                    if fallback_value and not getattr(parsed_event, field, None):
                        setattr(parsed_event, field, fallback_value)
                        
                        # Update metadata
                        if not parsed_event.extraction_metadata:
                            parsed_event.extraction_metadata = {}
                        parsed_event.extraction_metadata[f'{field}_from_fallback'] = True
        
        # Check if we still have missing critical fields
        still_missing = self._get_missing_critical_fields(parsed_event)
        
        if still_missing:
            if self.config['enable_user_interaction'] and not is_non_interactive():
                print(f"\n❌ Missing critical information: {', '.join(still_missing)}")
                
                # Prompt for missing fields
                prompts = self.get_completion_prompts(parsed_event)
                for field in still_missing:
                    if field in prompts:
                        value = safe_input(prompts[field])
                        if value.strip():
                            if field == 'start_datetime':
                                # Parse the datetime input
                                try:
                                    from services.datetime_parser import DateTimeParser
                                    dt_parser = DateTimeParser()
                                    dt_matches = dt_parser.extract_datetime(value)
                                    if dt_matches:
                                        parsed_event.start_datetime = dt_matches[0].value
                                        # Set default end time if not present
                                        if not parsed_event.end_datetime:
                                            parsed_event.end_datetime = parsed_event.start_datetime + timedelta(hours=1)
                                except Exception:
                                    print(f"Could not parse datetime: {value}")
                            else:
                                setattr(parsed_event, field, value)
                
                # Check again
                final_missing = self._get_missing_critical_fields(parsed_event)
                if not final_missing:
                    return ErrorHandlingResult(
                        success=True,
                        resolved_event=parsed_event,
                        error_type="missing_critical_fields",
                        error_message=f"Missing fields filled by user: {', '.join(missing_fields)}",
                        user_action_taken="manual_completion"
                    )
            
            # Still missing critical fields
            if not self.config['allow_partial_events']:
                return ErrorHandlingResult(
                    success=False,
                    error_type="missing_critical_fields",
                    error_message=f"Cannot create event without: {', '.join(still_missing)}"
                )
        
        return ErrorHandlingResult(
            success=True,
            resolved_event=parsed_event,
            error_type="missing_critical_fields",
            error_message=f"Resolved missing fields: {', '.join(missing_fields)}",
            fallback_used="regex" if llm_available else "none"
        )
    
    def _handle_missing_optional_fields(self, parsed_event: ParsedEvent, original_text: str, 
                                      missing_fields: List[str]) -> ErrorHandlingResult:
        """Handle missing optional fields (location, description) - don't prevent event creation."""
        if self.config['enable_user_interaction'] and not is_non_interactive():
            print(f"\n💡 Optional information missing: {', '.join(missing_fields)}")
            
            if confirm_action("Would you like to add this information?", default_yes=False):
                prompts = self.get_completion_prompts(parsed_event)
                for field in missing_fields:
                    if field in prompts:
                        value = safe_input(prompts[field])
                        if value.strip():
                            setattr(parsed_event, field, value)
        
        return ErrorHandlingResult(
            success=True,
            resolved_event=parsed_event,
            error_type="missing_optional_fields",
            error_message=f"Optional fields missing (OK): {', '.join(missing_fields)}"
        )
    
    def _handle_consistency_issues(self, parsed_event: ParsedEvent, original_text: str, 
                                 issues: List[str]) -> ErrorHandlingResult:
        """Handle consistency validation issues."""
        if self.config['enable_user_interaction'] and not is_non_interactive():
            print(f"\n⚠️  Consistency issues detected:")
            for issue in issues:
                print(f"  • {issue}")
            
            if confirm_action("Continue with this event anyway?", default_yes=True):
                return ErrorHandlingResult(
                    success=True,
                    resolved_event=parsed_event,
                    error_type="consistency_issues",
                    error_message=f"Consistency issues ignored by user: {'; '.join(issues)}",
                    user_action_taken="ignored_warnings"
                )
            else:
                # Offer to edit
                edited_event = self._edit_parsed_event(parsed_event, original_text)
                return ErrorHandlingResult(
                    success=True,
                    resolved_event=edited_event,
                    error_type="consistency_issues",
                    error_message=f"Consistency issues resolved by editing: {'; '.join(issues)}",
                    user_action_taken="edited"
                )
        
        # Non-interactive: continue with warnings
        return ErrorHandlingResult(
            success=True,
            resolved_event=parsed_event,
            error_type="consistency_issues",
            error_message=f"Consistency warnings: {'; '.join(issues)}"
        )
    
    def _has_multiple_interpretations(self, parsed_event: ParsedEvent) -> bool:
        """Check if parsed event has multiple possible interpretations."""
        metadata = parsed_event.extraction_metadata or {}
        return (
            metadata.get('multiple_datetime_matches', 0) > 1 or
            metadata.get('multiple_title_matches', 0) > 1 or
            metadata.get('multiple_location_matches', 0) > 1
        )
    
    def _get_missing_critical_fields(self, parsed_event: ParsedEvent) -> List[str]:
        """Get list of missing critical fields."""
        missing = []
        for field in self.config['critical_fields']:
            value = getattr(parsed_event, field, None)
            if not value:
                missing.append(field)
            elif field == 'title' and len(str(value).strip()) < self.config['min_title_length']:
                missing.append(field)
        return missing
    
    def _get_missing_optional_fields(self, parsed_event: ParsedEvent) -> List[str]:
        """Get list of missing optional fields."""
        missing = []
        for field in self.config['optional_fields']:
            value = getattr(parsed_event, field, None)
            if not value or (isinstance(value, str) and not value.strip()):
                missing.append(field)
        return missing
    
    def _validate_consistency(self, parsed_event: ParsedEvent, original_text: str) -> List[str]:
        """Validate consistency between parsed event and original text."""
        return self.validate_field_consistency(parsed_event, original_text)
    
    def _regex_fallback_extraction(self, text: str) -> Optional[ParsedEvent]:
        """Perform regex-based fallback extraction when LLM fails."""
        try:
            # Import here to avoid circular imports
            from services.event_parser import EventParser
            
            # Create a basic event parser for fallback
            parser = EventParser()
            
            # Disable LLM and use only regex patterns
            fallback_event = parser.parse_text(text)
            
            # Mark as regex fallback
            if fallback_event.extraction_metadata is None:
                fallback_event.extraction_metadata = {}
            fallback_event.extraction_metadata['extraction_method'] = 'regex_fallback'
            
            return fallback_event
            
        except Exception as e:
            print(f"Regex fallback failed: {e}")
            return None
    
    def _extract_datetime_options(self, metadata: Dict[str, Any]) -> List[InterpretationOption]:
        """Extract datetime interpretation options from metadata."""
        options = []
        all_matches = metadata.get('all_datetime_matches', [])
        
        for i, match in enumerate(all_matches):
            try:
                dt_value = datetime.fromisoformat(match['datetime'])
                options.append(InterpretationOption(
                    field_name='start_datetime',
                    value=dt_value,
                    confidence=match.get('confidence', 0.0),
                    source=match.get('pattern_type', 'unknown'),
                    description=f"from '{match.get('matched_text', '')}'"
                ))
            except (ValueError, KeyError):
                continue
        
        return options
    
    def _extract_title_options(self, metadata: Dict[str, Any]) -> List[InterpretationOption]:
        """Extract title interpretation options from metadata."""
        options = []
        all_matches = metadata.get('all_title_matches', [])
        
        for match in all_matches:
            options.append(InterpretationOption(
                field_name='title',
                value=match.get('title', ''),
                confidence=match.get('confidence', 0.0),
                source=match.get('extraction_type', 'unknown'),
                description=f"from '{match.get('matched_text', '')}'"
            ))
        
        return options
    
    def _extract_location_options(self, metadata: Dict[str, Any]) -> List[InterpretationOption]:
        """Extract location interpretation options from metadata."""
        options = []
        all_matches = metadata.get('all_location_matches', [])
        
        for match in all_matches:
            options.append(InterpretationOption(
                field_name='location',
                value=match.get('location', ''),
                confidence=match.get('confidence', 0.0),
                source=match.get('extraction_type', 'unknown'),
                description=f"from '{match.get('matched_text', '')}'"
            ))
        
        return options
    
    def _display_parsed_event(self, parsed_event: ParsedEvent):
        """Display parsed event information for user review."""
        print(f"  Title: {parsed_event.title or 'Not found'}")
        print(f"  Start: {parsed_event.start_datetime or 'Not found'}")
        print(f"  End: {parsed_event.end_datetime or 'Not found'}")
        print(f"  Location: {parsed_event.location or 'Not found'}")
        print(f"  Confidence: {parsed_event.confidence_score*100:.0f}%")
    
    def _edit_parsed_event(self, parsed_event: ParsedEvent, original_text: str) -> ParsedEvent:
        """Allow user to edit parsed event fields."""
        print("\n✏️  Edit event information:")
        
        # Edit title
        current_title = parsed_event.title or ""
        new_title = safe_input(f"Title [{current_title}]: ") or current_title
        parsed_event.title = new_title
        
        # Edit start datetime
        if parsed_event.start_datetime:
            current_start = parsed_event.start_datetime.strftime("%Y-%m-%d %H:%M")
        else:
            current_start = ""
        
        new_start_str = safe_input(f"Start date/time [{current_start}]: ") or current_start
        if new_start_str and new_start_str != current_start:
            try:
                from services.datetime_parser import DateTimeParser
                dt_parser = DateTimeParser()
                dt_matches = dt_parser.extract_datetime(new_start_str)
                if dt_matches:
                    parsed_event.start_datetime = dt_matches[0].value
            except Exception:
                print(f"Could not parse datetime: {new_start_str}")
        
        # Edit location
        current_location = parsed_event.location or ""
        new_location = safe_input(f"Location [{current_location}]: ") or current_location
        parsed_event.location = new_location if new_location else None
        
        return parsed_event
    
    def _create_manual_event(self, original_text: str) -> ParsedEvent:
        """Create event through manual user input."""
        print("\n📝 Create event manually:")
        
        # Get title
        title = safe_input("Event title: ")
        
        # Get start datetime
        start_str = safe_input("Start date/time (e.g., 'tomorrow at 2pm'): ")
        start_datetime = None
        
        if start_str:
            try:
                from services.datetime_parser import DateTimeParser
                dt_parser = DateTimeParser()
                dt_matches = dt_parser.extract_datetime(start_str)
                if dt_matches:
                    start_datetime = dt_matches[0].value
            except Exception:
                print(f"Could not parse datetime: {start_str}")
        
        # Get end datetime or duration
        end_str = safe_input("End time or duration (e.g., '3pm' or '1 hour'): ")
        end_datetime = None
        
        if end_str and start_datetime:
            try:
                from services.datetime_parser import DateTimeParser
                dt_parser = DateTimeParser()
                
                # Try to parse as end time first
                dt_matches = dt_parser.extract_datetime(end_str)
                if dt_matches:
                    end_datetime = dt_matches[0].value
                else:
                    # Try to parse as duration
                    duration_matches = dt_parser.extract_durations(end_str)
                    if duration_matches:
                        end_datetime = start_datetime + duration_matches[0].duration
            except Exception:
                print(f"Could not parse end time/duration: {end_str}")
        
        # Default end time if not specified
        if start_datetime and not end_datetime:
            end_datetime = start_datetime + timedelta(hours=1)
        
        # Get location (optional)
        location = safe_input("Location (optional): ") or None
        
        # Create manual event
        manual_event = ParsedEvent(
            title=title,
            start_datetime=start_datetime,
            end_datetime=end_datetime,
            location=location,
            description=original_text,
            confidence_score=1.0,  # High confidence for manual input
            extraction_metadata={
                'extraction_method': 'manual',
                'original_text': original_text,
                'manual_creation': True
            }
        )
        
        return manual_event
    
    def set_config(self, **kwargs):
        """Update error handler configuration."""
        self.config.update(kwargs)
    
    def get_config(self) -> Dict[str, Any]:
        """Get current error handler configuration."""
        return self.config.copy()