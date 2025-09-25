"""
Calendar service for managing event creation and storage.
Provides interface for event management with validation and error handling.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
from models.event_models import Event, ValidationResult


class CalendarServiceError(Exception):
    """Base exception for calendar service errors."""
    pass


class EventValidationError(CalendarServiceError):
    """Exception raised when event validation fails."""
    pass


class EventCreationError(CalendarServiceError):
    """Exception raised when event creation fails."""
    pass


class CalendarService:
    """
    Service for managing calendar events with validation and storage.
    
    This implementation provides a file-based storage system as a proof of concept.
    In a production environment, this would integrate with actual calendar APIs
    like Google Calendar, Outlook, or other calendar systems.
    """
    
    def __init__(self, storage_path: str = "calendar_events.json", max_retries: int = 3):
        """
        Initialize the calendar service.
        
        Args:
            storage_path: Path to the file where events will be stored
            max_retries: Maximum number of retry attempts for failed operations
        """
        self.storage_path = Path(storage_path)
        self.default_calendar_id = "default"
        self.max_retries = max_retries
        self._ensure_storage_exists()
    
    def _ensure_storage_exists(self):
        """Ensure the storage file exists and is properly formatted."""
        if not self.storage_path.exists():
            self._save_events([])
    
    def _load_events(self) -> List[Dict[str, Any]]:
        """Load events from storage file."""
        try:
            with open(self.storage_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return []
    
    def _save_events(self, events: List[Dict[str, Any]]):
        """Save events to storage file."""
        try:
            with open(self.storage_path, 'w', encoding='utf-8') as f:
                json.dump(events, f, indent=2, ensure_ascii=False)
        except IOError as e:
            raise EventCreationError(f"Failed to save events: {e}")
    
    def validate_event(self, event: Event) -> ValidationResult:
        """
        Validate an event before creation.
        
        Args:
            event: The event to validate
            
        Returns:
            ValidationResult with validation status and any issues found
        """
        result = ValidationResult(is_valid=True)
        
        # Check required fields
        if not event.title or not event.title.strip():
            result.add_missing_field("title", "Event must have a non-empty title")
        
        if not event.start_datetime:
            result.add_missing_field("start_datetime", "Event must have a start date and time")
        
        if not event.end_datetime:
            result.add_missing_field("end_datetime", "Event must have an end date and time")
        
        # Validate datetime logic
        if event.start_datetime and event.end_datetime:
            if event.start_datetime >= event.end_datetime:
                result.add_warning("Start time must be before end time")
                result.is_valid = False
            
            # Check if event is in the past
            if event.start_datetime < datetime.now():
                result.add_warning("Event is scheduled in the past")
            
            # Check for very long events (more than 24 hours)
            duration_hours = (event.end_datetime - event.start_datetime).total_seconds() / 3600
            if duration_hours > 24:
                result.add_warning(f"Event duration is {duration_hours:.1f} hours - unusually long")
        
        # Validate calendar_id
        if not event.calendar_id:
            result.add_suggestion("Using default calendar")
            event.calendar_id = self.default_calendar_id
        
        return result
    
    def create_event(self, event: Event) -> tuple[bool, str, Optional[str]]:
        """
        Create a calendar event after validation.
        
        Args:
            event: The event to create
            
        Returns:
            Tuple of (success, message, event_id)
            - success: True if event was created successfully
            - message: Success or error message
            - event_id: ID of created event if successful, None if failed
            
        Raises:
            EventValidationError: If event validation fails
        """
        # Validate the event first
        validation_result = self.validate_event(event)
        if not validation_result.is_valid:
            error_msg = f"Event validation failed: {', '.join(validation_result.missing_fields + validation_result.warnings)}"
            raise EventValidationError(error_msg)
        
        try:
            # Load existing events
            events = self._load_events()
            
            # Check for conflicts (optional warning)
            conflicts = self._check_conflicts(event, events)
            conflict_warnings = []
            if conflicts:
                conflict_warnings = [f"Conflicts with existing event: {c.get('title', 'Unknown')}" for c in conflicts[:3]]
                if len(conflicts) > 3:
                    conflict_warnings.append(f"... and {len(conflicts) - 3} more conflicts")
            
            # Add the new event
            event_id = self._generate_event_id()
            event_data = event.to_dict()
            event_data['id'] = event_id
            events.append(event_data)
            
            # Save updated events
            self._save_events(events)
            
            # Create success message
            success_msg = self._create_success_message(event, event_id, conflict_warnings)
            
            return True, success_msg, event_id
            
        except Exception as e:
            error_msg = f"Failed to create event: {str(e)}"
            return False, error_msg, None
    
    def _generate_event_id(self) -> str:
        """Generate a unique event ID."""
        return f"event_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
    
    def _check_conflicts(self, new_event: Event, existing_events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Check for scheduling conflicts with existing events.
        
        Args:
            new_event: The event to check for conflicts
            existing_events: List of existing events
            
        Returns:
            List of conflicting events
        """
        conflicts = []
        
        for existing in existing_events:
            try:
                existing_start = datetime.fromisoformat(existing['start_datetime'])
                existing_end = datetime.fromisoformat(existing['end_datetime'])
                
                # Check for overlap
                if (new_event.start_datetime < existing_end and 
                    new_event.end_datetime > existing_start):
                    conflicts.append(existing)
                    
            except (KeyError, ValueError):
                # Skip malformed events
                continue
        
        return conflicts
    
    def _create_success_message(self, event: Event, event_id: str, conflict_warnings: List[str] = None) -> str:
        """
        Create a success message for event creation.
        
        Args:
            event: The created event
            event_id: ID of the created event
            conflict_warnings: Optional list of conflict warnings
            
        Returns:
            Formatted success message
        """
        lines = []
        lines.append("📅 CALENDAR EVENT CREATED SUCCESSFULLY")
        lines.append("=" * 50)
        lines.append(f"Event ID: {event_id}")
        lines.append(f"Title: {event.title}")
        lines.append(f"Start: {event.start_datetime.strftime('%A, %B %d, %Y at %H:%M')}")
        lines.append(f"End: {event.end_datetime.strftime('%A, %B %d, %Y at %H:%M')}")
        lines.append(f"Duration: {event.duration_minutes()} minutes")
        
        if event.location:
            lines.append(f"Location: {event.location}")
        
        if event.description and event.description.strip():
            lines.append(f"Description: {event.description}")
        
        lines.append(f"Calendar: {event.calendar_id}")
        lines.append(f"Created: {event.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
        
        if conflict_warnings:
            lines.append("")
            lines.append("⚠ SCHEDULING CONFLICTS DETECTED:")
            for warning in conflict_warnings:
                lines.append(f"  • {warning}")
            lines.append("You may want to review your calendar for overlapping events.")
        
        lines.append("=" * 50)
        return "\n".join(lines)
    
    def display_event_confirmation(self, event: Event, event_id: str, conflict_warnings: List[str] = None):
        """
        Display event creation confirmation to console.
        
        Args:
            event: The created event
            event_id: ID of the created event
            conflict_warnings: Optional list of conflict warnings
        """
        message = self._create_success_message(event, event_id, conflict_warnings)
        print(f"\n{message}")
    
    def get_default_calendar(self) -> str:
        """
        Get the default calendar ID.
        
        Returns:
            Default calendar identifier
        """
        return self.default_calendar_id
    
    def list_events(self, start_date: Optional[datetime] = None, 
                   end_date: Optional[datetime] = None) -> List[Event]:
        """
        List events within a date range.
        
        Args:
            start_date: Optional start date filter
            end_date: Optional end date filter
            
        Returns:
            List of events matching the criteria
        """
        events_data = self._load_events()
        events = []
        
        for event_data in events_data:
            try:
                event = Event.from_dict(event_data)
                
                # Apply date filters if provided
                if start_date and event.end_datetime < start_date:
                    continue
                if end_date and event.start_datetime > end_date:
                    continue
                
                events.append(event)
                
            except (KeyError, ValueError):
                # Skip malformed events
                continue
        
        return sorted(events, key=lambda e: e.start_datetime)
    
    def delete_event(self, event_id: str) -> bool:
        """
        Delete an event by ID.
        
        Args:
            event_id: The ID of the event to delete
            
        Returns:
            True if event was deleted, False if not found
        """
        events = self._load_events()
        original_count = len(events)
        
        events = [e for e in events if e.get('id') != event_id]
        
        if len(events) < original_count:
            self._save_events(events)
            return True
        
        return False
    
    def get_storage_info(self) -> Dict[str, Any]:
        """
        Get information about the storage system.
        
        Returns:
            Dictionary with storage information
        """
        events = self._load_events()
        
        return {
            'storage_path': str(self.storage_path.absolute()),
            'event_count': len(events),
            'storage_exists': self.storage_path.exists(),
            'storage_size_bytes': self.storage_path.stat().st_size if self.storage_path.exists() else 0
        }
    
    def create_event_with_retry(self, event: Event, interactive: bool = True) -> tuple[bool, str, Optional[str]]:
        """
        Create an event with retry mechanism for failed attempts.
        
        Args:
            event: The event to create
            interactive: Whether to prompt user for retry decisions
            
        Returns:
            Tuple of (success, message, event_id)
        """
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                success, message, event_id = self.create_event(event)
                
                if success:
                    if attempt > 0:
                        # Add retry success note to message
                        message = f"✓ Event created successfully after {attempt + 1} attempt(s)\n\n{message}"
                    return success, message, event_id
                else:
                    last_error = message
                    
            except EventValidationError as e:
                # Validation errors shouldn't be retried
                return False, f"Validation Error: {str(e)}", None
                
            except EventCreationError as e:
                last_error = str(e)
                
            except Exception as e:
                last_error = f"Unexpected error: {str(e)}"
            
            # If not the last attempt, ask user if they want to retry (in interactive mode)
            if attempt < self.max_retries - 1:
                if interactive:
                    print(f"\n❌ Event creation failed (attempt {attempt + 1}/{self.max_retries})")
                    print(f"Error: {last_error}")
                    
                    retry_choice = input(f"\nWould you like to retry? (Y/n): ").strip().lower()
                    if retry_choice in ['n', 'no']:
                        break
                    
                    print("Retrying event creation...")
                else:
                    # In non-interactive mode, automatically retry
                    print(f"Attempt {attempt + 1} failed: {last_error}. Retrying...")
        
        # All attempts failed
        return False, f"Event creation failed after {self.max_retries} attempts. Last error: {last_error}", None
    
    def handle_creation_error(self, error_message: str, event: Event, interactive: bool = True) -> tuple[bool, Optional[Event]]:
        """
        Handle event creation errors with user feedback and options.
        
        Args:
            error_message: The error message to display
            event: The event that failed to create
            interactive: Whether to show interactive error handling
            
        Returns:
            Tuple of (retry_requested, modified_event)
        """
        if not interactive:
            return False, None
        
        print(f"\n❌ EVENT CREATION ERROR")
        print("=" * 50)
        print(f"Error: {error_message}")
        print("\nThe following event could not be created:")
        print(f"  Title: {event.title}")
        print(f"  Start: {event.start_datetime}")
        print(f"  End: {event.end_datetime}")
        if event.location:
            print(f"  Location: {event.location}")
        print("=" * 50)
        
        print("\nOptions:")
        print("  1. Retry with the same event")
        print("  2. Edit the event and retry")
        print("  3. Cancel event creation")
        
        while True:
            try:
                choice = input("\nEnter your choice (1-3): ").strip()
                
                if choice == '1':
                    return True, event
                
                elif choice == '2':
                    # Allow user to edit the event
                    from ui.event_preview import EventPreviewInterface
                    from models.event_models import ParsedEvent
                    
                    # Convert Event back to ParsedEvent for editing
                    parsed_event = ParsedEvent(
                        title=event.title,
                        start_datetime=event.start_datetime,
                        end_datetime=event.end_datetime,
                        location=event.location,
                        description=event.description,
                        confidence_score=1.0,
                        extraction_metadata={}
                    )
                    
                    interface = EventPreviewInterface()
                    interface.display_event_preview(parsed_event)
                    
                    confirmed, modified_event = interface.run_interactive_editing()
                    if confirmed and modified_event:
                        return True, modified_event
                    else:
                        print("Event editing cancelled.")
                        return False, None
                
                elif choice == '3':
                    print("Event creation cancelled.")
                    return False, None
                
                else:
                    print("Invalid choice. Please enter 1, 2, or 3.")
                    
            except KeyboardInterrupt:
                print("\nEvent creation cancelled.")
                return False, None