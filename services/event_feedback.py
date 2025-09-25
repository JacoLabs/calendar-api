"""
Event creation feedback system for providing user feedback on event creation status.
Handles success confirmations, error messages, and retry mechanisms.
"""

from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime
from enum import Enum

from models.event_models import Event
from services.calendar_service import CalendarService, EventCreationError, EventValidationError


class FeedbackType(Enum):
    """Types of feedback messages."""
    SUCCESS = "success"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class EventCreationFeedback:
    """
    Manages feedback for event creation operations.
    Provides consistent messaging and user interaction for event creation results.
    """
    
    def __init__(self, calendar_service: CalendarService):
        """
        Initialize the feedback system.
        
        Args:
            calendar_service: Calendar service instance for event operations
        """
        self.calendar_service = calendar_service
        self.feedback_history: List[Dict[str, Any]] = []
    
    def create_event_with_feedback(self, event: Event, interactive: bool = True) -> Tuple[bool, str]:
        """
        Create an event with comprehensive feedback and error handling.
        
        Args:
            event: The event to create
            interactive: Whether to use interactive error handling
            
        Returns:
            Tuple of (success, feedback_message)
        """
        start_time = datetime.now()
        
        try:
            # Attempt to create the event with retry mechanism
            success, message, event_id = self.calendar_service.create_event_with_retry(
                event, interactive=interactive
            )
            
            if success:
                # Log successful creation
                self._log_feedback(FeedbackType.SUCCESS, message, {
                    'event_id': event_id,
                    'event_title': event.title,
                    'creation_time': start_time,
                    'duration_ms': (datetime.now() - start_time).total_seconds() * 1000
                })
                
                # Display success feedback
                if interactive:
                    self._display_success_feedback(event, event_id, message)
                
                return True, message
            else:
                # Handle creation failure
                self._log_feedback(FeedbackType.ERROR, message, {
                    'event_title': event.title,
                    'error_time': start_time,
                    'duration_ms': (datetime.now() - start_time).total_seconds() * 1000
                })
                
                if interactive:
                    retry_requested, modified_event = self.calendar_service.handle_creation_error(
                        message, event, interactive=True
                    )
                    
                    if retry_requested and modified_event:
                        # Recursive retry with modified event
                        return self.create_event_with_feedback(modified_event, interactive)
                
                return False, message
                
        except EventValidationError as e:
            error_msg = f"Event validation failed: {str(e)}"
            self._log_feedback(FeedbackType.ERROR, error_msg, {
                'error_type': 'validation',
                'event_title': event.title,
                'error_time': start_time
            })
            
            if interactive:
                self._display_validation_error(event, str(e))
            
            return False, error_msg
            
        except Exception as e:
            error_msg = f"Unexpected error during event creation: {str(e)}"
            self._log_feedback(FeedbackType.ERROR, error_msg, {
                'error_type': 'unexpected',
                'event_title': event.title,
                'error_time': start_time
            })
            
            if interactive:
                self._display_unexpected_error(event, str(e))
            
            return False, error_msg
    
    def _display_success_feedback(self, event: Event, event_id: str, message: str):
        """
        Display success feedback to the user.
        
        Args:
            event: The created event
            event_id: ID of the created event
            message: Success message from calendar service
        """
        print(f"\n{message}")
        
        # Additional success actions
        print("\n🎉 What's next?")
        print("  • Your event has been saved to your calendar")
        print("  • You can view it in your calendar application")
        print(f"  • Event ID: {event_id} (for reference)")
        
        # Offer additional actions
        print("\nAdditional options:")
        print("  • Press Enter to continue")
        print("  • Type 'details' to see full event information")
        print("  • Type 'copy' to copy event details to clipboard")
        
        try:
            choice = input("\nYour choice: ").strip().lower()
            
            if choice == 'details':
                self._show_detailed_event_info(event, event_id)
            elif choice == 'copy':
                self._copy_event_to_clipboard(event, event_id)
            
        except KeyboardInterrupt:
            pass  # User pressed Ctrl+C, just continue
    
    def _display_validation_error(self, event: Event, error_message: str):
        """
        Display validation error feedback.
        
        Args:
            event: The event that failed validation
            error_message: Validation error message
        """
        print(f"\n❌ EVENT VALIDATION ERROR")
        print("=" * 50)
        print(f"Error: {error_message}")
        print("\nThe event has the following issues:")
        
        # Show event details for context
        print(f"  Title: {event.title or '(missing)'}")
        print(f"  Start: {event.start_datetime or '(missing)'}")
        print(f"  End: {event.end_datetime or '(missing)'}")
        if event.location:
            print(f"  Location: {event.location}")
        
        print("\n💡 Suggestions:")
        print("  • Ensure all required fields are filled")
        print("  • Check that start time is before end time")
        print("  • Verify date and time formats are correct")
        print("=" * 50)
    
    def _display_unexpected_error(self, event: Event, error_message: str):
        """
        Display unexpected error feedback.
        
        Args:
            event: The event that caused the error
            error_message: Error message
        """
        print(f"\n💥 UNEXPECTED ERROR")
        print("=" * 50)
        print(f"An unexpected error occurred: {error_message}")
        print("\nEvent details:")
        print(f"  Title: {event.title}")
        print(f"  Start: {event.start_datetime}")
        print(f"  End: {event.end_datetime}")
        
        print("\n🔧 Troubleshooting:")
        print("  • Check that the calendar storage is accessible")
        print("  • Ensure you have write permissions")
        print("  • Try creating a simpler event first")
        print("  • Contact support if the problem persists")
        print("=" * 50)
    
    def _show_detailed_event_info(self, event: Event, event_id: str):
        """Show detailed event information."""
        print(f"\n📋 DETAILED EVENT INFORMATION")
        print("=" * 50)
        print(f"Event ID: {event_id}")
        print(f"Title: {event.title}")
        print(f"Start: {event.start_datetime.strftime('%A, %B %d, %Y at %I:%M %p')}")
        print(f"End: {event.end_datetime.strftime('%A, %B %d, %Y at %I:%M %p')}")
        print(f"Duration: {event.duration_minutes()} minutes")
        
        if event.location:
            print(f"Location: {event.location}")
        
        if event.description and event.description.strip():
            print(f"Description: {event.description}")
        
        print(f"Calendar: {event.calendar_id}")
        print(f"Created: {event.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Show storage information
        storage_info = self.calendar_service.get_storage_info()
        print(f"\nStorage: {storage_info['storage_path']}")
        print(f"Total events: {storage_info['event_count']}")
        print("=" * 50)
    
    def _copy_event_to_clipboard(self, event: Event, event_id: str):
        """
        Copy event details to clipboard (simplified implementation).
        
        Args:
            event: The event to copy
            event_id: ID of the event
        """
        try:
            import pyperclip
            
            event_text = f"""Event: {event.title}
Start: {event.start_datetime.strftime('%Y-%m-%d %H:%M')}
End: {event.end_datetime.strftime('%Y-%m-%d %H:%M')}
Duration: {event.duration_minutes()} minutes"""
            
            if event.location:
                event_text += f"\nLocation: {event.location}"
            
            if event.description and event.description.strip():
                event_text += f"\nDescription: {event.description}"
            
            event_text += f"\nEvent ID: {event_id}"
            
            pyperclip.copy(event_text)
            print("✓ Event details copied to clipboard!")
            
        except ImportError:
            # Fallback if pyperclip is not available
            print("📋 Event details (copy manually):")
            print("-" * 30)
            print(f"Event: {event.title}")
            print(f"Start: {event.start_datetime.strftime('%Y-%m-%d %H:%M')}")
            print(f"End: {event.end_datetime.strftime('%Y-%m-%d %H:%M')}")
            if event.location:
                print(f"Location: {event.location}")
            print(f"Event ID: {event_id}")
            print("-" * 30)
        except Exception as e:
            print(f"Could not copy to clipboard: {e}")
    
    def _log_feedback(self, feedback_type: FeedbackType, message: str, metadata: Dict[str, Any]):
        """
        Log feedback for debugging and analytics.
        
        Args:
            feedback_type: Type of feedback
            message: Feedback message
            metadata: Additional metadata
        """
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'type': feedback_type.value,
            'message': message,
            'metadata': metadata
        }
        
        self.feedback_history.append(log_entry)
        
        # Keep only last 100 entries to prevent memory issues
        if len(self.feedback_history) > 100:
            self.feedback_history = self.feedback_history[-100:]
    
    def get_feedback_summary(self) -> Dict[str, Any]:
        """
        Get a summary of feedback history.
        
        Returns:
            Dictionary with feedback statistics
        """
        if not self.feedback_history:
            return {'total_events': 0, 'success_rate': 0.0, 'recent_activity': []}
        
        total_events = len(self.feedback_history)
        successful_events = len([f for f in self.feedback_history if f['type'] == FeedbackType.SUCCESS.value])
        success_rate = successful_events / total_events if total_events > 0 else 0.0
        
        # Get recent activity (last 10 entries)
        recent_activity = self.feedback_history[-10:]
        
        return {
            'total_events': total_events,
            'successful_events': successful_events,
            'failed_events': total_events - successful_events,
            'success_rate': success_rate,
            'recent_activity': recent_activity
        }
    
    def display_feedback_summary(self):
        """Display a summary of feedback history."""
        summary = self.get_feedback_summary()
        
        print(f"\n📊 EVENT CREATION SUMMARY")
        print("=" * 40)
        print(f"Total events processed: {summary['total_events']}")
        print(f"Successful creations: {summary['successful_events']}")
        print(f"Failed attempts: {summary['failed_events']}")
        print(f"Success rate: {summary['success_rate']:.1%}")
        
        if summary['recent_activity']:
            print(f"\nRecent activity:")
            for activity in summary['recent_activity'][-5:]:  # Show last 5
                timestamp = datetime.fromisoformat(activity['timestamp']).strftime('%H:%M:%S')
                status = "✓" if activity['type'] == 'success' else "❌"
                event_title = activity['metadata'].get('event_title', 'Unknown')
                print(f"  {timestamp} {status} {event_title}")
        
        print("=" * 40)


def create_event_with_comprehensive_feedback(event: Event, calendar_service: Optional[CalendarService] = None, 
                                           interactive: bool = True) -> Tuple[bool, str]:
    """
    Convenience function to create an event with comprehensive feedback.
    
    Args:
        event: The event to create
        calendar_service: Optional calendar service (creates new one if None)
        interactive: Whether to use interactive feedback
        
    Returns:
        Tuple of (success, feedback_message)
    """
    if calendar_service is None:
        calendar_service = CalendarService()
    
    feedback_system = EventCreationFeedback(calendar_service)
    return feedback_system.create_event_with_feedback(event, interactive)