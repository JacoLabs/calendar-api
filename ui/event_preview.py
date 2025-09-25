"""
Event preview and editing interface for reviewing extracted event information.
Provides console-based interface for displaying and editing parsed events before creation.
"""

import sys
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple
import re

from models.event_models import ParsedEvent, Event, ValidationResult
from ui.safe_input import safe_input, is_non_interactive, confirm_action


class EventPreviewInterface:
    """
    Console-based interface for previewing and editing extracted event information.
    Allows users to review, modify, and confirm event details before creation.
    """
    
    def __init__(self):
        self.current_event: Optional[ParsedEvent] = None
        self.validation_result: Optional[ValidationResult] = None
        
    def display_event_preview(self, parsed_event: ParsedEvent, validation_result: Optional[ValidationResult] = None) -> None:
        """
        Display the extracted event information in a formatted preview.
        
        Args:
            parsed_event: The parsed event to display
            validation_result: Optional validation result to show issues
        """
        self.current_event = parsed_event
        self.validation_result = validation_result
        
        print("\n" + "=" * 60)
        print("EVENT PREVIEW")
        print("=" * 60)
        
        # Display basic event information
        print(f"1. Title:       {parsed_event.title or '(not specified)'}")
        print(f"2. Start Date:  {self._format_date(parsed_event.start_datetime)}")
        print(f"3. Start Time:  {self._format_time(parsed_event.start_datetime)}")
        print(f"4. End Date:    {self._format_date(parsed_event.end_datetime)}")
        print(f"5. End Time:    {self._format_time(parsed_event.end_datetime)}")
        print(f"6. Location:    {parsed_event.location or '(not specified)'}")
        print(f"7. Description: {parsed_event.description or '(not specified)'}")
        
        # Show confidence score
        confidence_pct = parsed_event.confidence_score * 100
        print(f"\nExtraction Confidence: {confidence_pct:.1f}%")
        
        # Display validation issues if any
        if validation_result:
            self._display_validation_issues(validation_result)
        
        print("=" * 60)
    
    def _format_date(self, dt: Optional[datetime]) -> str:
        """Format date for display."""
        if dt is None:
            return "(not specified)"
        return dt.strftime("%Y-%m-%d (%A)")
    
    def _format_time(self, dt: Optional[datetime]) -> str:
        """Format time for display."""
        if dt is None:
            return "(not specified)"
        return dt.strftime("%H:%M")
    
    def _display_validation_issues(self, validation_result: ValidationResult) -> None:
        """Display validation issues and suggestions."""
        if not validation_result.is_valid:
            print("\n⚠ VALIDATION ISSUES:")
            
            if validation_result.missing_fields:
                print("Missing required fields:")
                for field in validation_result.missing_fields:
                    print(f"  • {field}")
            
            if validation_result.warnings:
                print("Warnings:")
                for warning in validation_result.warnings:
                    print(f"  • {warning}")
        
        if validation_result.suggestions:
            print("\n💡 SUGGESTIONS:")
            for suggestion in validation_result.suggestions:
                print(f"  • {suggestion}")
    
    def run_interactive_editing(self) -> Tuple[bool, Optional[Event]]:
        """
        Run the interactive editing interface.
        
        Returns:
            Tuple of (confirmed, finalized_event)
            - confirmed: True if user confirmed the event, False if cancelled
            - finalized_event: Event object if confirmed, None if cancelled
        """
        if not self.current_event:
            raise ValueError("No event to edit. Call display_event_preview first.")
        
        # In non-interactive mode, auto-accept the event if it's valid
        if is_non_interactive():
            return self._handle_non_interactive_confirmation()
        
        print("\nYou can edit any field by entering its number, or:")
        print("  'c' or 'confirm' - Confirm and create event")
        print("  'q' or 'cancel'  - Cancel without creating event")
        print("  'r' or 'refresh' - Refresh the preview display")
        print("  'h' or 'help'    - Show detailed help")
        
        retry_count = 0
        max_retries = 3
        
        while retry_count < max_retries:
            try:
                choice = safe_input("\nEnter your choice: ", "c").strip().lower()
                
                if not choice:
                    retry_count += 1
                    if retry_count >= max_retries:
                        print("No input received. Auto-confirming event.")
                        return self._handle_confirmation()
                    continue
                
                if choice in ['c', 'confirm']:
                    return self._handle_confirmation()
                
                elif choice in ['q', 'cancel']:
                    print("Event creation cancelled.")
                    return False, None
                
                elif choice in ['r', 'refresh']:
                    self.display_event_preview(self.current_event, self.validation_result)
                    retry_count = 0  # Reset retry count on valid action
                    continue
                
                elif choice in ['h', 'help']:
                    self._show_detailed_help()
                    retry_count = 0  # Reset retry count on valid action
                    continue
                
                elif choice.isdigit():
                    field_num = int(choice)
                    if 1 <= field_num <= 7:
                        self._edit_field(field_num)
                        # Re-validate after editing
                        self.validation_result = self._validate_current_event()
                        self.display_event_preview(self.current_event, self.validation_result)
                        retry_count = 0  # Reset retry count on valid action
                    else:
                        print("Invalid field number. Please enter 1-7.")
                        retry_count += 1
                
                else:
                    print("Invalid choice. Enter a field number (1-7), 'c' to confirm, 'q' to cancel, or 'h' for help.")
                    retry_count += 1
            
            except KeyboardInterrupt:
                print("\nEvent creation cancelled.")
                return False, None
            except Exception as e:
                print(f"Input error: {type(e).__name__}: {e}", file=sys.stderr)
                retry_count += 1
        
        # Max retries reached, auto-confirm
        print("Maximum input attempts reached. Auto-confirming event.")
        return self._handle_confirmation()
    
    def _edit_field(self, field_num: int) -> None:
        """
        Edit a specific field of the event.
        
        Args:
            field_num: Field number to edit (1-7)
        """
        field_map = {
            1: self._edit_title,
            2: self._edit_start_date,
            3: self._edit_start_time,
            4: self._edit_end_date,
            5: self._edit_end_time,
            6: self._edit_location,
            7: self._edit_description
        }
        
        field_map[field_num]()
    
    def _edit_title(self) -> None:
        """Edit the event title."""
        if is_non_interactive():
            return  # Skip editing in non-interactive mode
            
        current = self.current_event.title or ""
        print(f"\nCurrent title: {current or '(not specified)'}")
        
        new_title = safe_input("Enter new title (or press Enter to keep current): ", "").strip()
        if new_title:
            self.current_event.title = new_title
            print(f"Title updated to: {new_title}")
        else:
            print("Title unchanged.")
    
    def _edit_start_date(self) -> None:
        """Edit the start date."""
        if is_non_interactive():
            return  # Skip editing in non-interactive mode
            
        current = self.current_event.start_datetime
        print(f"\nCurrent start date: {self._format_date(current)}")
        print("Enter new date in format YYYY-MM-DD (e.g., 2024-03-15)")
        
        new_date_str = safe_input("New start date (or press Enter to keep current): ", "").strip()
        if new_date_str:
            try:
                new_date = datetime.strptime(new_date_str, "%Y-%m-%d").date()
                
                if current:
                    # Keep the existing time
                    new_datetime = datetime.combine(new_date, current.time())
                else:
                    # Default to 9:00 AM if no time was set
                    new_datetime = datetime.combine(new_date, datetime.min.time().replace(hour=9))
                
                self.current_event.start_datetime = new_datetime
                
                # Adjust end datetime if it exists and is before new start
                if self.current_event.end_datetime and self.current_event.end_datetime <= new_datetime:
                    self.current_event.end_datetime = new_datetime + timedelta(hours=1)
                    print(f"End time automatically adjusted to maintain 1-hour duration.")
                
                print(f"Start date updated to: {self._format_date(new_datetime)}")
                
            except ValueError:
                print("Invalid date format. Please use YYYY-MM-DD format.")
        else:
            print("Start date unchanged.")
    
    def _edit_start_time(self) -> None:
        """Edit the start time."""
        if is_non_interactive():
            return  # Skip editing in non-interactive mode
            
        current = self.current_event.start_datetime
        print(f"\nCurrent start time: {self._format_time(current)}")
        print("Enter new time in format HH:MM (24-hour) or HH:MM AM/PM")
        
        new_time_str = safe_input("New start time (or press Enter to keep current): ", "").strip()
        if new_time_str:
            try:
                new_time = self._parse_time_input(new_time_str)
                
                if current:
                    # Keep the existing date
                    new_datetime = datetime.combine(current.date(), new_time)
                else:
                    # Use today's date if no date was set
                    new_datetime = datetime.combine(datetime.now().date(), new_time)
                
                # Calculate duration to preserve it
                duration = timedelta(hours=1)  # Default 1 hour
                if self.current_event.end_datetime and current:
                    duration = self.current_event.end_datetime - current
                
                self.current_event.start_datetime = new_datetime
                self.current_event.end_datetime = new_datetime + duration
                
                print(f"Start time updated to: {self._format_time(new_datetime)}")
                print(f"End time adjusted to: {self._format_time(self.current_event.end_datetime)}")
                
            except ValueError as e:
                print(f"Invalid time format: {e}")
        else:
            print("Start time unchanged.")
    
    def _edit_end_date(self) -> None:
        """Edit the end date."""
        if is_non_interactive():
            return  # Skip editing in non-interactive mode
            
        current = self.current_event.end_datetime
        print(f"\nCurrent end date: {self._format_date(current)}")
        print("Enter new date in format YYYY-MM-DD (e.g., 2024-03-15)")
        
        new_date_str = safe_input("New end date (or press Enter to keep current): ", "").strip()
        if new_date_str:
            try:
                new_date = datetime.strptime(new_date_str, "%Y-%m-%d").date()
                
                if current:
                    # Keep the existing time
                    new_datetime = datetime.combine(new_date, current.time())
                else:
                    # Default to 10:00 AM if no time was set
                    new_datetime = datetime.combine(new_date, datetime.min.time().replace(hour=10))
                
                # Validate that end is after start
                if self.current_event.start_datetime and new_datetime <= self.current_event.start_datetime:
                    print("End date/time must be after start date/time.")
                    return
                
                self.current_event.end_datetime = new_datetime
                print(f"End date updated to: {self._format_date(new_datetime)}")
                
            except ValueError:
                print("Invalid date format. Please use YYYY-MM-DD format.")
        else:
            print("End date unchanged.")
    
    def _edit_end_time(self) -> None:
        """Edit the end time."""
        if is_non_interactive():
            return  # Skip editing in non-interactive mode
            
        current = self.current_event.end_datetime
        print(f"\nCurrent end time: {self._format_time(current)}")
        print("Enter new time in format HH:MM (24-hour) or HH:MM AM/PM")
        
        new_time_str = safe_input("New end time (or press Enter to keep current): ", "").strip()
        if new_time_str:
            try:
                new_time = self._parse_time_input(new_time_str)
                
                if current:
                    # Keep the existing date
                    new_datetime = datetime.combine(current.date(), new_time)
                else:
                    # Use start date if available, otherwise today
                    if self.current_event.start_datetime:
                        new_datetime = datetime.combine(self.current_event.start_datetime.date(), new_time)
                    else:
                        new_datetime = datetime.combine(datetime.now().date(), new_time)
                
                # Validate that end is after start
                if self.current_event.start_datetime and new_datetime <= self.current_event.start_datetime:
                    print("End time must be after start time.")
                    return
                
                self.current_event.end_datetime = new_datetime
                print(f"End time updated to: {self._format_time(new_datetime)}")
                
            except ValueError as e:
                print(f"Invalid time format: {e}")
        else:
            print("End time unchanged.")
    
    def _edit_location(self) -> None:
        """Edit the event location."""
        if is_non_interactive():
            return  # Skip editing in non-interactive mode
            
        current = self.current_event.location or ""
        print(f"\nCurrent location: {current or '(not specified)'}")
        
        new_location = safe_input("Enter new location (or press Enter to keep current): ", "").strip()
        if new_location:
            self.current_event.location = new_location
            print(f"Location updated to: {new_location}")
        elif new_location == "" and current:
            # Allow clearing the location
            if confirm_action("Clear the location?", default_yes=False):
                self.current_event.location = None
                print("Location cleared.")
        else:
            print("Location unchanged.")
    
    def _edit_description(self) -> None:
        """Edit the event description."""
        if is_non_interactive():
            return  # Skip editing in non-interactive mode
            
        current = self.current_event.description or ""
        print(f"\nCurrent description: {current or '(not specified)'}")
        
        new_description = safe_input("Enter new description (or press Enter to keep current): ", "").strip()
        if new_description:
            self.current_event.description = new_description
            print(f"Description updated to: {new_description}")
        elif new_description == "" and current:
            # Allow clearing the description
            if confirm_action("Clear the description?", default_yes=False):
                self.current_event.description = ""
                print("Description cleared.")
        else:
            print("Description unchanged.")
    
    def _parse_time_input(self, time_str: str) -> datetime.time:
        """
        Parse time input in various formats.
        
        Args:
            time_str: Time string to parse
            
        Returns:
            datetime.time object
            
        Raises:
            ValueError: If time format is invalid
        """
        time_str = time_str.strip().upper()
        
        # Try 24-hour format first (HH:MM)
        if re.match(r'^\d{1,2}:\d{2}$', time_str):
            try:
                return datetime.strptime(time_str, "%H:%M").time()
            except ValueError:
                pass
        
        # Try 12-hour format with AM/PM
        for fmt in ["%I:%M %p", "%I %p", "%I:%M%p", "%I%p"]:
            try:
                return datetime.strptime(time_str, fmt).time()
            except ValueError:
                continue
        
        # Try just hour (assume :00 minutes)
        if re.match(r'^\d{1,2}$', time_str):
            hour = int(time_str)
            if 0 <= hour <= 23:
                from datetime import time
                return time(hour, 0)
        
        raise ValueError("Invalid time format. Use HH:MM (24-hour) or HH:MM AM/PM")
    
    def _validate_current_event(self) -> ValidationResult:
        """
        Validate the current event and return validation result.
        
        Returns:
            ValidationResult with validation status and issues
        """
        result = ValidationResult(is_valid=True)
        
        # Check required fields
        if not self.current_event.title or not self.current_event.title.strip():
            result.add_missing_field('title', 'Event needs a descriptive title')
        
        if not self.current_event.start_datetime:
            result.add_missing_field('start_datetime', 'Event needs a start date and time')
        
        if not self.current_event.end_datetime:
            result.add_missing_field('end_datetime', 'Event needs an end date and time')
        
        # Check logical consistency
        if (self.current_event.start_datetime and self.current_event.end_datetime and 
            self.current_event.start_datetime >= self.current_event.end_datetime):
            result.add_warning('End time must be after start time')
            result.is_valid = False
        
        # Check for reasonable duration
        if (self.current_event.start_datetime and self.current_event.end_datetime):
            duration = self.current_event.end_datetime - self.current_event.start_datetime
            duration_hours = duration.total_seconds() / 3600
            
            if duration_hours > 12:
                result.add_warning('Event duration is very long (more than 12 hours)')
            elif duration_hours < 0.25:  # Less than 15 minutes
                result.add_warning('Event duration is very short (less than 15 minutes)')
        
        return result
    
    def _handle_non_interactive_confirmation(self) -> Tuple[bool, Optional[Event]]:
        """
        Handle confirmation in non-interactive mode.
        
        Returns:
            Tuple of (confirmed, finalized_event)
        """
        # Ensure we have minimum required fields
        if not self.current_event.start_datetime:
            # Set default start time if missing
            from datetime import datetime
            self.current_event.start_datetime = datetime.now().replace(hour=9, minute=0, second=0, microsecond=0)
        
        if not self.current_event.end_datetime and self.current_event.start_datetime:
            # Set default 60-minute duration if end time is missing
            self.current_event.end_datetime = self.current_event.start_datetime + timedelta(minutes=60)
        
        if not self.current_event.title:
            # Set default title if missing
            self.current_event.title = "Event"
        
        # Validate the event
        validation_result = self._validate_current_event()
        
        if not validation_result.is_valid:
            # In non-interactive mode, try to fix basic issues
            if not self.current_event.title:
                self.current_event.title = "Untitled Event"
            
            # Re-validate
            validation_result = self._validate_current_event()
            
            if not validation_result.is_valid:
                return False, None
        
        try:
            # Convert ParsedEvent to Event
            finalized_event = Event(
                title=self.current_event.title,
                start_datetime=self.current_event.start_datetime,
                end_datetime=self.current_event.end_datetime,
                location=self.current_event.location,
                description=self.current_event.description or ""
            )
            
            return True, finalized_event
            
        except ValueError as e:
            print(f"Error creating event in non-interactive mode: {e}", file=sys.stderr)
            return False, None
    
    def _handle_confirmation(self) -> Tuple[bool, Optional[Event]]:
        """
        Handle event confirmation and creation.
        
        Returns:
            Tuple of (confirmed, finalized_event)
        """
        # Validate the event
        validation_result = self._validate_current_event()
        
        if not validation_result.is_valid:
            print("\n⚠ Cannot create event - validation issues found:")
            self._display_validation_issues(validation_result)
            print("\nPlease fix the issues above before confirming.")
            return False, None
        
        # Show final confirmation
        print("\n" + "=" * 60)
        print("FINAL EVENT CONFIRMATION")
        print("=" * 60)
        self.display_event_preview(self.current_event, validation_result)
        
        if confirm_action("\nCreate this event?", default_yes=True):
            try:
                # Convert ParsedEvent to Event
                finalized_event = Event(
                    title=self.current_event.title,
                    start_datetime=self.current_event.start_datetime,
                    end_datetime=self.current_event.end_datetime,
                    location=self.current_event.location,
                    description=self.current_event.description or ""
                )
                
                print("✓ Event confirmed and ready for creation!")
                return True, finalized_event
                
            except ValueError as e:
                print(f"Error creating event: {e}")
                return False, None
        else:
            print("Event creation cancelled.")
            return False, None
    
    def _show_detailed_help(self) -> None:
        """Show detailed help for the editing interface."""
        help_text = """
DETAILED HELP - Event Preview and Editing Interface

FIELD EDITING:
  1 - Edit Title:       Event name or description
  2 - Edit Start Date:  Date when event begins (YYYY-MM-DD format)
  3 - Edit Start Time:  Time when event begins (HH:MM or HH:MM AM/PM)
  4 - Edit End Date:    Date when event ends (YYYY-MM-DD format)
  5 - Edit End Time:    Time when event ends (HH:MM or HH:MM AM/PM)
  6 - Edit Location:    Where the event takes place
  7 - Edit Description: Additional event details

COMMANDS:
  c, confirm - Confirm event and proceed to creation
  q, cancel  - Cancel event creation and exit
  r, refresh - Refresh the preview display
  h, help    - Show this help message

TIME FORMAT EXAMPLES:
  24-hour: 14:30, 09:00, 23:45
  12-hour: 2:30 PM, 9:00 AM, 11:45 PM
  Short:   2 PM, 9 AM (assumes :00 minutes)

DATE FORMAT:
  YYYY-MM-DD (e.g., 2024-03-15 for March 15, 2024)

VALIDATION:
  - Title and start/end times are required
  - End time must be after start time
  - Very long (>12h) or short (<15min) events will show warnings

TIPS:
  - Press Enter without typing to keep current values
  - Times automatically adjust to maintain duration when possible
  - Use 'r' to refresh the display after making changes
        """
        print(help_text)


def create_event_from_text(text: str, parser=None) -> Tuple[bool, Optional[Event]]:
    """
    Convenience function to create an event from text with interactive editing.
    
    Args:
        text: Text to parse for event information
        parser: Optional EventParser instance (creates new one if None)
        
    Returns:
        Tuple of (success, event) where success indicates if event was created
    """
    if parser is None:
        from services.event_parser import EventParser
        parser = EventParser()
    
    # Parse the text
    parsed_event = parser.parse_text(text)
    validation_result = parser.validate_parsed_event(parsed_event)
    
    # Create and run the preview interface
    interface = EventPreviewInterface()
    interface.display_event_preview(parsed_event, validation_result)
    
    return interface.run_interactive_editing()


if __name__ == "__main__":
    # Example usage for testing
    if len(sys.argv) > 1:
        text = " ".join(sys.argv[1:])
        success, event = create_event_from_text(text)
        
        if success and event:
            print(f"\n✓ Event created successfully!")
            print(f"Title: {event.title}")
            print(f"Start: {event.start_datetime}")
            print(f"End: {event.end_datetime}")
            if event.location:
                print(f"Location: {event.location}")
        else:
            print("\nEvent creation was cancelled or failed.")
    else:
        print("Usage: python event_preview.py <text to parse>")
        print("Example: python event_preview.py 'Meeting tomorrow at 2pm'")