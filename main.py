#!/usr/bin/env python3
"""
Main entry point for the text-to-calendar event application.
Orchestrates the complete workflow from text input to event creation.
"""

import sys
import argparse
from typing import Optional, Dict, Any
from datetime import datetime

from cli import EventParserCLI
from services.event_parser import EventParser
from services.calendar_service import CalendarService
from services.event_feedback import create_event_with_comprehensive_feedback
from ui.event_preview import EventPreviewInterface
from models.event_models import ParsedEvent, Event


class TextToCalendarApp:
    """
    Main application class that orchestrates the complete text-to-calendar workflow.
    Integrates CLI input, parsing, preview interface, and calendar services.
    """
    
    def __init__(self):
        """Initialize the application with all required services."""
        self.event_parser = EventParser()
        self.calendar_service = CalendarService()
        self.cli = EventParserCLI()
        
        # Application configuration
        self.config = {
            'auto_preview': True,  # Always show preview by default
            'auto_create': False,  # Don't auto-create without confirmation
            'verbose_output': True,  # Show detailed information
            'error_recovery': True,  # Enable error recovery mechanisms
            'max_retries': 3,  # Maximum retry attempts
            'default_duration_minutes': 60,  # Default event duration
            'prefer_dd_mm_format': False,  # Date format preference
        }
    
    def run_complete_workflow(self, text: str, **kwargs) -> tuple[bool, Optional[Event], str]:
        """
        Run the complete workflow from text input to event creation.
        
        Args:
            text: Input text containing event information
            **kwargs: Optional configuration overrides
            
        Returns:
            Tuple of (success, created_event, message)
        """
        # Apply configuration overrides
        config = self.config.copy()
        config.update(kwargs)
        
        try:
            # Step 1: Parse the text
            if config.get('verbose_output', True):
                print("🔍 Parsing text for event information...")
            
            parsed_event = self.event_parser.parse_text(
                text,
                prefer_dd_mm_format=config.get('prefer_dd_mm_format', False),
                default_event_duration_minutes=config.get('default_duration_minutes', 60)
            )
            
            # Step 2: Validate the parsed event
            validation_result = self.event_parser.validate_parsed_event(parsed_event)
            
            if config.get('verbose_output', True):
                confidence_pct = parsed_event.confidence_score * 100
                print(f"✓ Parsing complete (confidence: {confidence_pct:.1f}%)")
            
            # Step 3: Show preview and allow editing (if enabled)
            if config.get('auto_preview', True):
                if config.get('verbose_output', True):
                    print("\n📋 Displaying event preview...")
                
                interface = EventPreviewInterface()
                interface.display_event_preview(parsed_event, validation_result)
                
                # Run interactive editing
                confirmed, finalized_event = interface.run_interactive_editing()
                
                if not confirmed or not finalized_event:
                    return False, None, "Event creation was cancelled by user"
                
            else:
                # Auto-create mode: convert ParsedEvent to Event without preview
                if not validation_result.is_valid:
                    return False, None, f"Event validation failed: {', '.join(validation_result.missing_fields + validation_result.warnings)}"
                
                finalized_event = Event(
                    title=parsed_event.title or "Untitled Event",
                    start_datetime=parsed_event.start_datetime,
                    end_datetime=parsed_event.end_datetime,
                    location=parsed_event.location,
                    description=parsed_event.description or ""
                )
            
            # Step 4: Create the calendar event
            if config.get('verbose_output', True):
                print("\n📅 Creating calendar event...")
            
            success, feedback_message = create_event_with_comprehensive_feedback(
                finalized_event,
                calendar_service=self.calendar_service,
                interactive=config.get('error_recovery', True)
            )
            
            if success:
                if config.get('verbose_output', True):
                    print("✅ Event created successfully!")
                return True, finalized_event, feedback_message
            else:
                return False, None, feedback_message
                
        except KeyboardInterrupt:
            return False, None, "Operation cancelled by user"
        except Exception as e:
            error_msg = f"Unexpected error in workflow: {str(e)}"
            if config.get('verbose_output', True):
                print(f"❌ {error_msg}")
            return False, None, error_msg
    
    def run_batch_workflow(self, texts: list[str], **kwargs) -> list[tuple[bool, Optional[Event], str]]:
        """
        Run the workflow for multiple text inputs.
        
        Args:
            texts: List of text inputs to process
            **kwargs: Optional configuration overrides
            
        Returns:
            List of (success, created_event, message) tuples
        """
        results = []
        config = kwargs.copy()
        config['auto_preview'] = False  # Disable preview for batch mode
        config['verbose_output'] = False  # Reduce verbosity for batch
        
        print(f"🔄 Processing {len(texts)} text inputs in batch mode...")
        
        for i, text in enumerate(texts, 1):
            print(f"\n[{i}/{len(texts)}] Processing: {text[:50]}{'...' if len(text) > 50 else ''}")
            
            success, event, message = self.run_complete_workflow(text, **config)
            results.append((success, event, message))
            
            if success:
                print(f"✅ Event created: {event.title}")
            else:
                print(f"❌ Failed: {message}")
        
        # Summary
        successful = sum(1 for success, _, _ in results if success)
        print(f"\n📊 Batch processing complete: {successful}/{len(texts)} events created successfully")
        
        return results
    
    def run_interactive_mode(self, **kwargs):
        """
        Run the application in interactive mode with enhanced workflow.
        
        Args:
            **kwargs: Optional configuration overrides
        """
        config = self.config.copy()
        config.update(kwargs)
        
        print("🎯 Text-to-Calendar Event Creator - Interactive Mode")
        print("=" * 60)
        print("Enter text containing event information, or use commands:")
        print("  'help' - Show available commands")
        print("  'config' - Show/modify configuration")
        print("  'batch' - Enter batch processing mode")
        print("  'quit' - Exit the application")
        print("=" * 60)
        
        while True:
            try:
                text = input("\n📝 Enter event text: ").strip()
                
                if not text:
                    print("Please enter some text to parse.")
                    continue
                
                # Handle commands
                if text.lower() in ['quit', 'exit', 'q']:
                    print("👋 Goodbye!")
                    break
                
                elif text.lower() in ['help', 'h']:
                    self._show_interactive_help()
                    continue
                
                elif text.lower().startswith('config'):
                    self._handle_config_command(text)
                    continue
                
                elif text.lower() == 'batch':
                    self._run_batch_input_mode()
                    continue
                
                elif text.lower() == 'summary':
                    self._show_session_summary()
                    continue
                
                # Process the text through the complete workflow
                success, event, message = self.run_complete_workflow(text, **config)
                
                if not success:
                    print(f"\n❌ {message}")
                
            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"\n❌ Error: {e}")
    
    def _show_interactive_help(self):
        """Show help for interactive mode."""
        help_text = """
📚 INTERACTIVE MODE HELP

BASIC USAGE:
  Simply type natural language text describing an event:
  • "Meeting with John tomorrow at 2pm"
  • "Lunch at Cafe Downtown next Friday 12:30-1:30"
  • "Conference call on March 15th at 10am for 2 hours"

COMMANDS:
  help, h          - Show this help message
  config           - Show current configuration
  config <key>=<value> - Set configuration option
  batch            - Enter batch processing mode
  summary          - Show session statistics
  quit, exit, q    - Exit the application

CONFIGURATION OPTIONS:
  auto_preview=true/false     - Show preview interface (default: true)
  auto_create=true/false      - Auto-create without confirmation (default: false)
  verbose_output=true/false   - Show detailed progress (default: true)
  dd_mm_format=true/false     - Use DD/MM date format (default: false)
  duration=<minutes>          - Default event duration (default: 60)

WORKFLOW:
  1. Text is parsed to extract event information
  2. Preview interface shows extracted data with confidence scores
  3. You can edit any field before confirming
  4. Event is created in your calendar with confirmation

TIPS:
  • Be specific with dates and times for better accuracy
  • Include location keywords like "at" or "in" for venues
  • Use quotes around titles if they contain common words
  • The system learns from your corrections over time
        """
        print(help_text)
    
    def _handle_config_command(self, command: str):
        """Handle configuration commands."""
        parts = command.split('=', 1)
        if len(parts) == 1:
            # Show current config
            print("\n⚙️ CURRENT CONFIGURATION:")
            print("-" * 40)
            for key, value in self.config.items():
                print(f"  {key}: {value}")
            print("-" * 40)
            return
        
        # Set config value
        key_part = parts[0].replace('config ', '').strip()
        value_part = parts[1].strip()
        
        # Map command keys to config keys
        key_mapping = {
            'auto_preview': 'auto_preview',
            'auto_create': 'auto_create',
            'verbose_output': 'verbose_output',
            'dd_mm_format': 'prefer_dd_mm_format',
            'duration': 'default_duration_minutes',
            'error_recovery': 'error_recovery',
            'retries': 'max_retries'
        }
        
        config_key = key_mapping.get(key_part)
        if not config_key:
            print(f"❌ Unknown configuration key: {key_part}")
            print("Available keys:", ", ".join(key_mapping.keys()))
            return
        
        # Convert and validate value
        try:
            if config_key in ['auto_preview', 'auto_create', 'verbose_output', 'prefer_dd_mm_format', 'error_recovery']:
                value = value_part.lower() in ['true', '1', 'yes', 'on']
            elif config_key in ['default_duration_minutes', 'max_retries']:
                value = int(value_part)
                if value <= 0:
                    print(f"❌ {key_part} must be a positive number")
                    return
            else:
                value = value_part
            
            self.config[config_key] = value
            print(f"✅ Set {key_part} = {value}")
            
            # Update parser config if needed
            if config_key in ['prefer_dd_mm_format', 'default_duration_minutes']:
                self.event_parser.set_config(**{config_key: value})
            
        except ValueError as e:
            print(f"❌ Invalid value for {key_part}: {e}")
    
    def _run_batch_input_mode(self):
        """Run batch input mode for processing multiple texts."""
        print("\n📦 BATCH PROCESSING MODE")
        print("Enter multiple event texts, one per line.")
        print("Type 'END' on a new line when finished, or Ctrl+C to cancel.")
        print("-" * 50)
        
        texts = []
        try:
            while True:
                text = input(f"Event {len(texts) + 1}: ").strip()
                if text.upper() == 'END':
                    break
                if text:
                    texts.append(text)
        except KeyboardInterrupt:
            print("\nBatch input cancelled.")
            return
        
        if not texts:
            print("No texts entered.")
            return
        
        # Process batch
        results = self.run_batch_workflow(texts, verbose_output=True)
        
        # Show detailed results
        print(f"\n📋 BATCH RESULTS SUMMARY")
        print("=" * 50)
        for i, (success, event, message) in enumerate(results, 1):
            status = "✅" if success else "❌"
            title = event.title if event else "Failed"
            print(f"{i:2d}. {status} {title}")
        print("=" * 50)
    
    def _show_session_summary(self):
        """Show session statistics and summary."""
        # Get feedback summary from calendar service
        from services.event_feedback import EventCreationFeedback
        feedback_system = EventCreationFeedback(self.calendar_service)
        feedback_system.display_feedback_summary()
        
        # Show storage info
        storage_info = self.calendar_service.get_storage_info()
        print(f"\n💾 STORAGE INFORMATION:")
        print(f"  Location: {storage_info['storage_path']}")
        print(f"  Total events: {storage_info['event_count']}")
        print(f"  File size: {storage_info['storage_size_bytes']} bytes")
    
    def set_config(self, **kwargs):
        """Update application configuration."""
        self.config.update(kwargs)
        
        # Update parser config for relevant settings
        parser_config = {}
        if 'prefer_dd_mm_format' in kwargs:
            parser_config['prefer_dd_mm_format'] = kwargs['prefer_dd_mm_format']
        if 'default_duration_minutes' in kwargs:
            parser_config['default_event_duration_minutes'] = kwargs['default_duration_minutes']
        
        if parser_config:
            self.event_parser.set_config(**parser_config)
    
    def get_config(self) -> Dict[str, Any]:
        """Get current application configuration."""
        return self.config.copy()


def create_argument_parser() -> argparse.ArgumentParser:
    """Create the main application argument parser."""
    parser = argparse.ArgumentParser(
        description='Text-to-Calendar Event Creator - Convert natural language to calendar events',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s "Meeting with John tomorrow at 2pm"
  %(prog)s --no-preview --auto-create "Lunch next Friday 12:30"
  %(prog)s --interactive
  %(prog)s --batch file1.txt file2.txt
        """
    )
    
    # Input options
    parser.add_argument(
        'text',
        nargs='?',
        help='Text to parse for event information'
    )
    
    parser.add_argument(
        '-i', '--interactive',
        action='store_true',
        help='Run in interactive mode'
    )
    
    parser.add_argument(
        '--batch',
        nargs='+',
        metavar='FILE',
        help='Process multiple text files in batch mode'
    )
    
    # Workflow options
    parser.add_argument(
        '--no-preview',
        action='store_true',
        help='Skip preview interface and create event directly'
    )
    
    parser.add_argument(
        '--auto-create',
        action='store_true',
        help='Automatically create events without confirmation'
    )
    
    # Configuration options
    parser.add_argument(
        '--dd-mm',
        action='store_true',
        help='Interpret ambiguous dates as DD/MM instead of MM/DD'
    )
    
    parser.add_argument(
        '--duration',
        type=int,
        metavar='MINUTES',
        default=60,
        help='Default event duration in minutes (default: 60)'
    )
    
    parser.add_argument(
        '--quiet',
        action='store_true',
        help='Reduce output verbosity'
    )
    
    # Utility options
    parser.add_argument(
        '--version',
        action='version',
        version='Text-to-Calendar Event Creator 1.0.0'
    )
    
    return parser


def main():
    """Main entry point for the application."""
    try:
        # Parse command line arguments
        arg_parser = create_argument_parser()
        args = arg_parser.parse_args()
        
        # Create application instance
        app = TextToCalendarApp()
        
        # Configure application based on arguments
        config = {}
        if args.no_preview:
            config['auto_preview'] = False
        if args.auto_create:
            config['auto_create'] = True
        if args.dd_mm:
            config['prefer_dd_mm_format'] = True
        if args.duration:
            config['default_duration_minutes'] = args.duration
        if args.quiet:
            config['verbose_output'] = False
        
        app.set_config(**config)
        
        # Handle different execution modes
        if args.interactive:
            # Interactive mode
            app.run_interactive_mode()
            
        elif args.batch:
            # Batch mode - process files
            all_texts = []
            for filename in args.batch:
                try:
                    with open(filename, 'r', encoding='utf-8') as f:
                        file_texts = [line.strip() for line in f if line.strip()]
                        all_texts.extend(file_texts)
                        print(f"📁 Loaded {len(file_texts)} texts from {filename}")
                except FileNotFoundError:
                    print(f"❌ File not found: {filename}")
                    return 1
                except Exception as e:
                    print(f"❌ Error reading {filename}: {e}")
                    return 1
            
            if all_texts:
                app.run_batch_workflow(all_texts)
            else:
                print("❌ No texts found in batch files")
                return 1
                
        elif args.text:
            # Single text mode
            success, event, message = app.run_complete_workflow(args.text)
            if not success:
                print(f"❌ {message}")
                return 1
                
        else:
            # No arguments provided - show help and enter interactive mode
            print("No text provided. Entering interactive mode...")
            print("Use --help for command line options.")
            app.run_interactive_mode()
        
        return 0
        
    except KeyboardInterrupt:
        print("\n👋 Operation cancelled by user.")
        return 1
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())