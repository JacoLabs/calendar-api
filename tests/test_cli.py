"""
Tests for the command-line interface functionality.
"""

import unittest
import json
import sys
from io import StringIO
from unittest.mock import patch, MagicMock
from datetime import datetime

from cli import EventParserCLI
from models.event_models import ParsedEvent, ValidationResult


class TestEventParserCLI(unittest.TestCase):
    """Test cases for the EventParserCLI class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.cli = EventParserCLI()
        
        # Create a sample parsed event for testing
        self.sample_event = ParsedEvent(
            title="Meeting with John",
            start_datetime=datetime(2024, 3, 15, 14, 0),
            end_datetime=datetime(2024, 3, 15, 15, 0),
            location="Conference Room A",
            description="Meeting with John tomorrow at 2pm in Conference Room A",
            confidence_score=0.85,
            extraction_metadata={
                'datetime_confidence': 0.9,
                'title_confidence': 0.8,
                'location_confidence': 0.85,
                'datetime_pattern_type': 'relative_tomorrow+12_hour_am_pm',
                'title_extraction_type': 'title_pattern_meeting',
                'location_extraction_type': 'location_keyword_in'
            }
        )
        
        self.sample_validation = ValidationResult(
            is_valid=True,
            missing_fields=[],
            warnings=[],
            suggestions=["Event looks good!"]
        )
    
    def test_argument_parser_creation(self):
        """Test that argument parser is created correctly."""
        parser = self.cli.create_argument_parser()
        
        # Test that parser exists and has expected arguments
        self.assertIsNotNone(parser)
        
        # Test parsing valid arguments
        args = parser.parse_args(['--dd-mm', '--duration', '90', '--json', 'test text'])
        self.assertTrue(args.prefer_dd_mm)
        self.assertEqual(args.duration, 90)
        self.assertTrue(args.json)
        self.assertEqual(args.text, 'test text')
    
    def test_input_validation_valid_cases(self):
        """Test input validation with valid inputs."""
        valid_inputs = [
            "Meeting tomorrow at 2pm",
            "Lunch with Sarah next Friday at noon",
            "Conference call on March 15th at 3:30pm",
            "A" * 100,  # Long but valid text
        ]
        
        for text in valid_inputs:
            with self.subTest(text=text):
                is_valid, error = self.cli.validate_input(text)
                self.assertTrue(is_valid, f"Should be valid: {text}")
                self.assertIsNone(error)
    
    def test_input_validation_invalid_cases(self):
        """Test input validation with invalid inputs."""
        invalid_inputs = [
            ("", "Input text cannot be empty"),
            ("   ", "Input text cannot be only whitespace"),
            ("ab", "Input text is too short (minimum 3 characters)"),
            ("A" * 1001, "Input text is too long (maximum 1000 characters)"),
        ]
        
        for text, expected_error in invalid_inputs:
            with self.subTest(text=text):
                is_valid, error = self.cli.validate_input(text)
                self.assertFalse(is_valid)
                self.assertIn(expected_error, error)
    
    @patch('cli.EventParser')
    def test_parse_text_with_configuration(self, mock_parser_class):
        """Test that parse_text applies configuration correctly."""
        mock_parser = MagicMock()
        mock_parser_class.return_value = mock_parser
        mock_parser.parse_text.return_value = self.sample_event
        
        # Create new CLI instance to get fresh parser
        cli = EventParserCLI()
        cli.config['prefer_dd_mm_format'] = True
        cli.config['default_event_duration_minutes'] = 90
        
        result = cli.parse_text("test text")
        
        # Verify parser was called with correct configuration
        mock_parser.parse_text.assert_called_once_with(
            "test text",
            prefer_dd_mm_format=True,
            default_event_duration_minutes=90
        )
        self.assertEqual(result, self.sample_event)
    
    def test_human_output_formatting(self):
        """Test human-readable output formatting."""
        self.cli.config['output_format'] = 'human'
        self.cli.config['show_confidence'] = True
        self.cli.config['show_metadata'] = False
        
        output = self.cli.format_output(self.sample_event, self.sample_validation)
        
        # Check that key information is present
        self.assertIn("Meeting with John", output)
        self.assertIn("2024-03-15 14:00", output)
        self.assertIn("2024-03-15 15:00", output)
        self.assertIn("Conference Room A", output)
        self.assertIn("85.0%", output)  # Confidence score
        self.assertIn("Event is valid", output)  # Validation result
    
    def test_json_output_formatting(self):
        """Test JSON output formatting."""
        self.cli.config['output_format'] = 'json'
        self.cli.config['show_metadata'] = False
        
        output = self.cli.format_output(self.sample_event, self.sample_validation)
        
        # Parse JSON to verify structure
        data = json.loads(output)
        
        self.assertIn('parsed_event', data)
        self.assertIn('validation', data)
        
        event_data = data['parsed_event']
        self.assertEqual(event_data['title'], "Meeting with John")
        self.assertEqual(event_data['location'], "Conference Room A")
        self.assertEqual(event_data['confidence_score'], 0.85)
        
        # Metadata should be excluded when show_metadata is False
        self.assertNotIn('extraction_metadata', event_data)
        
        validation_data = data['validation']
        self.assertTrue(validation_data['is_valid'])
    
    def test_json_output_with_metadata(self):
        """Test JSON output with metadata included."""
        self.cli.config['output_format'] = 'json'
        self.cli.config['show_metadata'] = True
        
        output = self.cli.format_output(self.sample_event, self.sample_validation)
        data = json.loads(output)
        
        # Metadata should be included when show_metadata is True
        self.assertIn('extraction_metadata', data['parsed_event'])
        metadata = data['parsed_event']['extraction_metadata']
        self.assertEqual(metadata['datetime_confidence'], 0.9)
        self.assertEqual(metadata['title_confidence'], 0.8)
    
    def test_datetime_formatting(self):
        """Test datetime formatting helper."""
        dt = datetime(2024, 3, 15, 14, 30)
        formatted = self.cli._format_datetime(dt)
        self.assertEqual(formatted, "2024-03-15 14:30")
        
        # Test None datetime
        formatted_none = self.cli._format_datetime(None)
        self.assertEqual(formatted_none, "(not found)")
    
    @patch('builtins.input')
    @patch('builtins.print')
    def test_interactive_mode_quit(self, mock_print, mock_input):
        """Test interactive mode quit functionality."""
        mock_input.side_effect = ['quit']
        
        self.cli.run_interactive_mode()
        
        # Verify quit message was printed
        mock_print.assert_any_call("Goodbye!")
    
    @patch('builtins.input')
    @patch('builtins.print')
    def test_interactive_mode_help(self, mock_print, mock_input):
        """Test interactive mode help command."""
        mock_input.side_effect = ['help', 'quit']
        
        self.cli.run_interactive_mode()
        
        # Check that help text was printed
        help_calls = [call for call in mock_print.call_args_list 
                     if 'Interactive Mode Commands' in str(call)]
        self.assertTrue(len(help_calls) > 0)
    
    @patch('builtins.input')
    @patch('builtins.print')
    def test_interactive_mode_config(self, mock_print, mock_input):
        """Test interactive mode configuration commands."""
        mock_input.side_effect = ['config', 'config dd_mm=true', 'quit']
        
        self.cli.run_interactive_mode()
        
        # Verify config was updated
        self.assertTrue(self.cli.config['prefer_dd_mm_format'])
    
    @patch('builtins.input')
    @patch('builtins.print')
    def test_interactive_mode_parsing(self, mock_print, mock_input):
        """Test interactive mode text parsing."""
        mock_input.side_effect = ['Meeting tomorrow at 2pm', 'quit']
        
        with patch.object(self.cli, 'parse_text', return_value=self.sample_event):
            with patch.object(self.cli.parser, 'validate_parsed_event', return_value=self.sample_validation):
                self.cli.run_interactive_mode()
        
        # Verify parsing was called and results were printed
        parsing_calls = [call for call in mock_print.call_args_list 
                        if 'Meeting with John' in str(call)]
        self.assertTrue(len(parsing_calls) > 0)
    
    def test_run_with_text_argument(self):
        """Test running CLI with text argument."""
        with patch.object(self.cli, 'parse_text', return_value=self.sample_event):
            with patch.object(self.cli.parser, 'validate_parsed_event', return_value=self.sample_validation):
                with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
                    exit_code = self.cli.run(['Meeting tomorrow at 2pm'])
        
        self.assertEqual(exit_code, 0)
        output = mock_stdout.getvalue()
        self.assertIn("Meeting with John", output)
    
    def test_run_with_json_flag(self):
        """Test running CLI with JSON output flag."""
        with patch.object(self.cli, 'parse_text', return_value=self.sample_event):
            with patch.object(self.cli.parser, 'validate_parsed_event', return_value=self.sample_validation):
                with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
                    exit_code = self.cli.run(['--json', 'Meeting tomorrow at 2pm'])
        
        self.assertEqual(exit_code, 0)
        output = mock_stdout.getvalue()
        
        # Verify JSON output
        data = json.loads(output)
        self.assertIn('parsed_event', data)
        self.assertEqual(data['parsed_event']['title'], "Meeting with John")
    
    def test_run_with_dd_mm_flag(self):
        """Test running CLI with DD/MM date format flag."""
        with patch.object(self.cli, 'parse_text', return_value=self.sample_event) as mock_parse:
            exit_code = self.cli.run(['--dd-mm', 'Meeting 15/03/2024'])
        
        self.assertEqual(exit_code, 0)
        # Verify configuration was applied
        self.assertTrue(self.cli.config['prefer_dd_mm_format'])
    
    def test_run_with_duration_flag(self):
        """Test running CLI with duration flag."""
        with patch.object(self.cli, 'parse_text', return_value=self.sample_event):
            exit_code = self.cli.run(['--duration', '90', 'Meeting tomorrow'])
        
        self.assertEqual(exit_code, 0)
        # Verify configuration was applied
        self.assertEqual(self.cli.config['default_event_duration_minutes'], 90)
    
    def test_run_with_no_text_error(self):
        """Test running CLI without text argument."""
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            exit_code = self.cli.run([])
        
        self.assertEqual(exit_code, 1)
        output = mock_stdout.getvalue()
        self.assertIn("No text provided", output)
    
    def test_run_with_invalid_text_error(self):
        """Test running CLI with invalid text."""
        with patch('sys.stderr', new_callable=StringIO) as mock_stderr:
            exit_code = self.cli.run(['ab'])  # Too short
        
        self.assertEqual(exit_code, 1)
        error_output = mock_stderr.getvalue()
        self.assertIn("too short", error_output)
    
    def test_run_interactive_mode_flag(self):
        """Test running CLI with interactive mode flag."""
        with patch.object(self.cli, 'run_interactive_mode') as mock_interactive:
            exit_code = self.cli.run(['--interactive'])
        
        self.assertEqual(exit_code, 0)
        mock_interactive.assert_called_once()
    
    def test_config_command_parsing(self):
        """Test configuration command parsing in interactive mode."""
        # Test setting boolean values
        self.cli._handle_config_command('config dd_mm=true')
        self.assertTrue(self.cli.config['prefer_dd_mm_format'])
        
        self.cli._handle_config_command('config confidence=false')
        self.assertFalse(self.cli.config['show_confidence'])
        
        # Test setting integer values
        self.cli._handle_config_command('config duration=120')
        self.assertEqual(self.cli.config['default_event_duration_minutes'], 120)
        
        # Test setting string values
        self.cli._handle_config_command('config format=json')
        self.assertEqual(self.cli.config['output_format'], 'json')
    
    def test_config_command_invalid_key(self):
        """Test configuration command with invalid key."""
        with patch('builtins.print') as mock_print:
            self.cli._handle_config_command('config invalid_key=value')
        
        mock_print.assert_called_with("Unknown configuration key: invalid_key")
    
    def test_config_command_invalid_format(self):
        """Test configuration command with invalid format value."""
        with patch('builtins.print') as mock_print:
            self.cli._handle_config_command('config format=invalid')
        
        mock_print.assert_called_with("Output format must be 'human' or 'json'")
    
    def test_config_command_invalid_integer(self):
        """Test configuration command with invalid integer value."""
        with patch('builtins.print') as mock_print:
            self.cli._handle_config_command('config duration=invalid')
        
        # Should print error about invalid value
        error_calls = [call for call in mock_print.call_args_list 
                      if 'Invalid value' in str(call)]
        self.assertTrue(len(error_calls) > 0)
    
    def test_keyboard_interrupt_handling(self):
        """Test handling of keyboard interrupt."""
        with patch('sys.stderr', new_callable=StringIO) as mock_stderr:
            with patch.object(self.cli, 'parse_text', side_effect=KeyboardInterrupt):
                exit_code = self.cli.run(['test'])
        
        self.assertEqual(exit_code, 1)
        error_output = mock_stderr.getvalue()
        self.assertIn("cancelled by user", error_output)
    
    def test_unexpected_error_handling(self):
        """Test handling of unexpected errors."""
        with patch('sys.stderr', new_callable=StringIO) as mock_stderr:
            with patch.object(self.cli, 'parse_text', side_effect=Exception("Test error")):
                exit_code = self.cli.run(['test'])
        
        self.assertEqual(exit_code, 1)
        error_output = mock_stderr.getvalue()
        self.assertIn("Unexpected error", error_output)
        self.assertIn("Test error", error_output)


class TestCLIIntegration(unittest.TestCase):
    """Integration tests for CLI functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.cli = EventParserCLI()
    
    def test_end_to_end_parsing(self):
        """Test complete end-to-end parsing workflow."""
        test_text = "Meeting with Sarah tomorrow at 3pm in Conference Room B"
        
        # Validate input
        is_valid, error = self.cli.validate_input(test_text)
        self.assertTrue(is_valid)
        self.assertIsNone(error)
        
        # Parse text
        parsed_event = self.cli.parse_text(test_text)
        self.assertIsNotNone(parsed_event)
        self.assertIsNotNone(parsed_event.title)
        
        # Validate results
        validation_result = self.cli.parser.validate_parsed_event(parsed_event)
        self.assertIsNotNone(validation_result)
        
        # Format output
        human_output = self.cli.format_output(parsed_event, validation_result)
        self.assertIn("Sarah", human_output)
        
        # Test JSON output
        self.cli.config['output_format'] = 'json'
        json_output = self.cli.format_output(parsed_event, validation_result)
        data = json.loads(json_output)
        self.assertIn('parsed_event', data)
    
    def test_configuration_persistence(self):
        """Test that configuration changes persist across operations."""
        # Set configuration
        self.cli.config['prefer_dd_mm_format'] = True
        self.cli.config['default_event_duration_minutes'] = 120
        
        # Parse text and verify configuration is used
        with patch.object(self.cli.parser, 'parse_text') as mock_parse:
            mock_parse.return_value = ParsedEvent()
            self.cli.parse_text("test")
        
        # Verify parser was called with correct config
        mock_parse.assert_called_once_with(
            "test",
            prefer_dd_mm_format=True,
            default_event_duration_minutes=120
        )
    
    def test_error_recovery(self):
        """Test error recovery in interactive-like scenarios."""
        # Test with various invalid inputs
        invalid_inputs = ["", "  ", "ab", "A" * 1001]
        
        for invalid_input in invalid_inputs:
            is_valid, error = self.cli.validate_input(invalid_input)
            self.assertFalse(is_valid)
            self.assertIsNotNone(error)
        
        # Test that valid input still works after invalid ones
        is_valid, error = self.cli.validate_input("Valid meeting text")
        self.assertTrue(is_valid)
        self.assertIsNone(error)


if __name__ == '__main__':
    unittest.main()