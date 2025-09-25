#!/usr/bin/env python3
"""
Command-line interface for text-to-calendar event parsing.
Provides a simple CLI that accepts text input and displays parsed results.
"""

import argparse
import sys
import json
from typing import Optional, Dict, Any
from datetime import datetime

from services.event_parser import EventParser
from models.event_models import ParsedEvent, ValidationResult
from ui.safe_input import safe_input, is_non_interactive


class EventParserCLI:
    """
    Command-line interface for the event parser service.
    Handles user input, parsing configuration, and result display.
    """
    
    def __init__(self):
        self.parser = EventParser()
        self.config = {
            'prefer_dd_mm_format': False,
            'default_event_duration_minutes': 60,
            'output_format': 'human',  # 'human' or 'json'
            'show_confidence': True,
            'show_metadata': False,
            'validate_results': True
        }
    
    def create_argument_parser(self) -> argparse.ArgumentParser:
        """Create and configure the argument parser."""
        parser = argparse.ArgumentParser(
            description='Parse natural language text to extract calendar event information',
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
  %(prog)s "Meeting with John tomorrow at 2pm"
  %(prog)s --dd-mm "Lunch at cafe 15/03/2024 12:30"
  %(prog)s --json --duration 90 "Conference call next Friday"
  %(prog)s --interactive
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
            help='Run in interactive mode for multiple inputs'
        )
        
        # Parsing configuration
        parser.add_argument(
            '--dd-mm',
            action='store_true',
            dest='prefer_dd_mm',
            help='Interpret ambiguous dates as DD/MM instead of MM/DD'
        )
        
        parser.add_argument(
            '--duration',
            type=int,
            metavar='MINUTES',
            help='Default event duration in minutes (default: 60)'
        )
        
        # Output options
        parser.add_argument(
            '--json',
            action='store_true',
            help='Output results in JSON format'
        )
        
        parser.add_argument(
            '--no-confidence',
            action='store_true',
            help='Hide confidence scores in output'
        )
        
        parser.add_argument(
            '--show-metadata',
            action='store_true',
            help='Show detailed extraction metadata'
        )
        
        parser.add_argument(
            '--no-validation',
            action='store_true',
            help='Skip validation of parsed results'
        )
        
        parser.add_argument(
            '--preview',
            action='store_true',
            help='Show interactive preview and editing interface'
        )
        
        # Utility options
        parser.add_argument(
            '--version',
            action='version',
            version='Event Parser CLI 1.0.0'
        )
        
        return parser
    
    def validate_input(self, text: str) -> tuple[bool, Optional[str]]:
        """
        Validate input text for basic requirements.
        
        Args:
            text: Input text to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not text:
            return False, "Input text cannot be empty"
        
        if not text.strip():
            return False, "Input text cannot be only whitespace"
        
        if len(text.strip()) < 3:
            return False, "Input text is too short (minimum 3 characters)"
        
        if len(text) > 1000:
            return False, "Input text is too long (maximum 1000 characters)"
        
        return True, None
    
    def parse_text(self, text: str) -> ParsedEvent:
        """
        Parse text using the configured event parser.
        
        Args:
            text: Text to parse
            
        Returns:
            ParsedEvent object with extracted information
        """
        # Apply configuration to parser
        parser_config = {
            'prefer_dd_mm_format': self.config['prefer_dd_mm_format'],
            'default_event_duration_minutes': self.config['default_event_duration_minutes']
        }
        
        return self.parser.parse_text(text, **parser_config)
    
    def format_output(self, parsed_event: ParsedEvent, validation_result: Optional[ValidationResult] = None) -> str:
        """
        Format the parsed event for display.
        
        Args:
            parsed_event: Parsed event to format
            validation_result: Optional validation result
            
        Returns:
            Formatted output string
        """
        if self.config['output_format'] == 'json':
            return self._format_json_output(parsed_event, validation_result)
        else:
            return self._format_human_output(parsed_event, validation_result)
    
    def _format_json_output(self, parsed_event: ParsedEvent, validation_result: Optional[ValidationResult] = None) -> str:
        """Format output as JSON."""
        output = {
            'parsed_event': parsed_event.to_dict(),
            'validation': validation_result.to_dict() if validation_result else None
        }
        
        if not self.config['show_metadata']:
            # Remove metadata from output
            output['parsed_event'].pop('extraction_metadata', None)
        
        return json.dumps(output, indent=2, default=str)
    
    def _format_human_output(self, parsed_event: ParsedEvent, validation_result: Optional[ValidationResult] = None) -> str:
        """Format output for human reading."""
        lines = []
        
        # Header
        lines.append("=" * 50)
        lines.append("EVENT PARSING RESULTS")
        lines.append("=" * 50)
        
        # Basic event information
        lines.append(f"Title: {parsed_event.title or '(not found)'}")
        lines.append(f"Start: {self._format_datetime(parsed_event.start_datetime)}")
        lines.append(f"End: {self._format_datetime(parsed_event.end_datetime)}")
        lines.append(f"Location: {parsed_event.location or '(not found)'}")
        
        if parsed_event.description and parsed_event.description.strip():
            lines.append(f"Description: {parsed_event.description}")
        
        # Confidence score
        if self.config['show_confidence']:
            confidence_pct = parsed_event.confidence_score * 100
            lines.append(f"Confidence: {confidence_pct:.1f}%")
        
        # Validation results
        if validation_result and self.config['validate_results']:
            lines.append("")
            lines.append("VALIDATION:")
            if validation_result.is_valid:
                lines.append("✓ Event is valid and ready for creation")
            else:
                lines.append("⚠ Event has issues that need attention")
            
            if validation_result.missing_fields:
                lines.append("Missing fields:")
                for field in validation_result.missing_fields:
                    lines.append(f"  - {field}")
            
            if validation_result.warnings:
                lines.append("Warnings:")
                for warning in validation_result.warnings:
                    lines.append(f"  - {warning}")
            
            if validation_result.suggestions:
                lines.append("Suggestions:")
                for suggestion in validation_result.suggestions:
                    lines.append(f"  - {suggestion}")
        
        # Metadata (if requested)
        if self.config['show_metadata'] and parsed_event.extraction_metadata:
            lines.append("")
            lines.append("EXTRACTION METADATA:")
            metadata = parsed_event.extraction_metadata
            
            # Show key metadata fields
            if 'datetime_confidence' in metadata:
                lines.append(f"  Date/Time confidence: {metadata['datetime_confidence']:.2f}")
            if 'title_confidence' in metadata:
                lines.append(f"  Title confidence: {metadata['title_confidence']:.2f}")
            if 'location_confidence' in metadata:
                lines.append(f"  Location confidence: {metadata['location_confidence']:.2f}")
            
            if 'datetime_pattern_type' in metadata:
                lines.append(f"  Date/Time pattern: {metadata['datetime_pattern_type']}")
            if 'title_extraction_type' in metadata:
                lines.append(f"  Title extraction: {metadata['title_extraction_type']}")
            if 'location_extraction_type' in metadata:
                lines.append(f"  Location extraction: {metadata['location_extraction_type']}")
        
        lines.append("=" * 50)
        return "\n".join(lines)
    
    def _format_datetime(self, dt: Optional[datetime]) -> str:
        """Format datetime for display."""
        if dt is None:
            return "(not found)"
        return dt.strftime("%Y-%m-%d %H:%M")
    
    def run_interactive_mode(self):
        """Run the CLI in interactive mode for multiple inputs."""
        print("Event Parser - Interactive Mode")
        print("Enter text to parse (or 'quit' to exit, 'help' for commands)")
        print("-" * 50)
        
        retry_count = 0
        max_retries = 3
        
        while retry_count < max_retries:
            try:
                text = safe_input("\n> ", "").strip()
                
                if not text:
                    if is_non_interactive():
                        print("No input in non-interactive mode. Exiting.")
                        break
                    retry_count += 1
                    if retry_count >= max_retries:
                        print("No input received. Exiting.")
                        break
                    print("Please enter some text to parse.")
                    continue
                
                # Reset retry count on valid input
                retry_count = 0
                
                if text.lower() in ['quit', 'exit', 'q']:
                    print("Goodbye!")
                    break
                
                if text.lower() in ['help', 'h']:
                    self._show_interactive_help()
                    continue
                
                if text.lower().startswith('config'):
                    self._handle_config_command(text)
                    continue
                
                if not text:
                    print("Please enter some text to parse.")
                    continue
                
                # Validate and parse
                is_valid, error = self.validate_input(text)
                if not is_valid:
                    print(f"Error: {error}")
                    continue
                
                parsed_event = self.parse_text(text)
                validation_result = None
                
                if self.config['validate_results']:
                    validation_result = self.parser.validate_parsed_event(parsed_event)
                
                # Check if user wants preview mode
                if self.config.get('show_preview', False):
                    from ui.event_preview import EventPreviewInterface
                    from services.event_feedback import create_event_with_comprehensive_feedback
                    
                    interface = EventPreviewInterface()
                    interface.display_event_preview(parsed_event, validation_result)
                    
                    confirmed, event = interface.run_interactive_editing()
                    
                    if confirmed and event:
                        # Use comprehensive feedback system for event creation
                        success, feedback_message = create_event_with_comprehensive_feedback(
                            event, interactive=True
                        )
                        
                        if not success:
                            print(f"\nEvent creation failed: {feedback_message}")
                    else:
                        print("\nEvent creation was cancelled.")
                else:
                    output = self.format_output(parsed_event, validation_result)
                    print(output)
                
            except KeyboardInterrupt:
                print("\nGoodbye!")
                break
            except Exception as e:
                print(f"Error: {e}")
    
    def _show_interactive_help(self):
        """Show help for interactive mode."""
        help_text = """
Interactive Mode Commands:
  help, h          - Show this help message
  quit, exit, q    - Exit the program
  config           - Show current configuration
  config <key>=<value> - Set configuration option
  
Configuration Options:
  dd_mm=true/false     - Use DD/MM date format
  duration=<minutes>   - Default event duration
  confidence=true/false - Show confidence scores
  metadata=true/false  - Show extraction metadata
  validation=true/false - Enable validation
  format=human/json    - Output format
  preview=true/false   - Enable interactive preview mode

Examples:
  Meeting with John tomorrow at 2pm
  config dd_mm=true
  config duration=90
        """
        print(help_text)
    
    def _handle_config_command(self, command: str):
        """Handle configuration commands in interactive mode."""
        parts = command.split('=', 1)
        if len(parts) == 1:
            # Show current config
            print("Current Configuration:")
            for key, value in self.config.items():
                print(f"  {key}: {value}")
            return
        
        # Set config value
        key_part = parts[0].replace('config ', '').strip()
        value_part = parts[1].strip()
        
        # Map command keys to config keys
        key_mapping = {
            'dd_mm': 'prefer_dd_mm_format',
            'duration': 'default_event_duration_minutes',
            'confidence': 'show_confidence',
            'metadata': 'show_metadata',
            'validation': 'validate_results',
            'format': 'output_format',
            'preview': 'show_preview'
        }
        
        config_key = key_mapping.get(key_part)
        if not config_key:
            print(f"Unknown configuration key: {key_part}")
            return
        
        # Convert value
        try:
            if config_key in ['prefer_dd_mm_format', 'show_confidence', 'show_metadata', 'validate_results', 'show_preview']:
                value = value_part.lower() in ['true', '1', 'yes', 'on']
            elif config_key == 'default_event_duration_minutes':
                value = int(value_part)
            elif config_key == 'output_format':
                if value_part not in ['human', 'json']:
                    print("Output format must be 'human' or 'json'")
                    return
                value = value_part
            else:
                value = value_part
            
            self.config[config_key] = value
            print(f"Set {key_part} = {value}")
            
        except ValueError as e:
            print(f"Invalid value for {key_part}: {e}")
    
    def run(self, args: Optional[list] = None) -> int:
        """
        Run the CLI with the given arguments.
        
        Args:
            args: Command line arguments (uses sys.argv if None)
            
        Returns:
            Exit code (0 for success, 1 for error)
        """
        try:
            # Parse arguments
            arg_parser = self.create_argument_parser()
            parsed_args = arg_parser.parse_args(args)
            
            # Update configuration from arguments
            if parsed_args.prefer_dd_mm:
                self.config['prefer_dd_mm_format'] = True
            
            if parsed_args.duration:
                self.config['default_event_duration_minutes'] = parsed_args.duration
            
            if parsed_args.json:
                self.config['output_format'] = 'json'
            
            if parsed_args.no_confidence:
                self.config['show_confidence'] = False
            
            if parsed_args.show_metadata:
                self.config['show_metadata'] = True
            
            if parsed_args.no_validation:
                self.config['validate_results'] = False
            
            if parsed_args.preview:
                self.config['show_preview'] = True
            
            # Handle interactive mode
            if parsed_args.interactive:
                self.run_interactive_mode()
                return 0
            
            # Handle single text input
            if not parsed_args.text:
                print("Error: No text provided. Use --interactive for interactive mode or provide text as argument.")
                print("Use --help for usage information.")
                return 1
            
            # Validate input
            is_valid, error = self.validate_input(parsed_args.text)
            if not is_valid:
                print(f"Error: {error}", file=sys.stderr)
                return 1
            
            # Parse text
            parsed_event = self.parse_text(parsed_args.text)
            
            # Validate results if enabled
            validation_result = None
            if self.config['validate_results']:
                validation_result = self.parser.validate_parsed_event(parsed_event)
            
            # Handle preview mode
            if self.config.get('show_preview', False):
                from ui.event_preview import EventPreviewInterface
                from services.event_feedback import create_event_with_comprehensive_feedback
                
                interface = EventPreviewInterface()
                interface.display_event_preview(parsed_event, validation_result)
                
                confirmed, event = interface.run_interactive_editing()
                
                if confirmed and event:
                    # Use comprehensive feedback system for event creation
                    success, feedback_message = create_event_with_comprehensive_feedback(
                        event, interactive=True
                    )
                    
                    if not success:
                        print(f"\nEvent creation failed: {feedback_message}")
                        return 1
                else:
                    print("\nEvent creation was cancelled.")
                
                return 0
            
            # Output results (non-preview mode)
            output = self.format_output(parsed_event, validation_result)
            print(output)
            
            return 0
            
        except KeyboardInterrupt:
            print("\nOperation cancelled by user.", file=sys.stderr)
            return 1
        except Exception as e:
            print(f"Unexpected error: {e}", file=sys.stderr)
            return 1


def main():
    """Main entry point for the CLI."""
    cli = EventParserCLI()
    exit_code = cli.run()
    sys.exit(exit_code)


if __name__ == '__main__':
    main()