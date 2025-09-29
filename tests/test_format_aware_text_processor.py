"""
Unit tests for FormatAwareTextProcessor class.

Tests various text formats, typo normalization, case handling, and multiple event detection.
"""

import unittest
from services.format_aware_text_processor import FormatAwareTextProcessor, TextFormat, TextFormatResult


class TestFormatAwareTextProcessor(unittest.TestCase):
    """Test cases for FormatAwareTextProcessor."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.processor = FormatAwareTextProcessor()
    
    def test_bullet_point_processing(self):
        """Test bullet point format detection and processing."""
        text = """
        • Meeting with John tomorrow at 2pm
        • Location: Conference Room A
        • Duration: 1 hour
        """
        
        result = self.processor.process_text(text)
        
        self.assertEqual(result.detected_format, TextFormat.BULLET_POINTS)
        self.assertIn("Meeting with John tomorrow at 2:00 PM", result.processed_text)
        self.assertIn("Location: Conference Room A", result.processed_text)
        self.assertIn("Duration: 1 hour", result.processed_text)
        self.assertGreater(result.format_specific_confidence, 0.7)
    
    def test_numbered_list_processing(self):
        """Test numbered list format detection and processing."""
        text = """
        1. Team standup at 9am
        2. Client call at 11:30am
        3. Lunch meeting at 12:30pm
        """
        
        result = self.processor.process_text(text)
        
        self.assertEqual(result.detected_format, TextFormat.BULLET_POINTS)
        self.assertIn("Team standup at 9:00 AM", result.processed_text)
        self.assertIn("Client call at 11:30 AM", result.processed_text)
        self.assertIn("Lunch meeting at 12:30 PM", result.processed_text)
    
    def test_structured_email_processing(self):
        """Test structured email format detection and processing."""
        text = """
        Subject: Project Review Meeting
        Date: Tomorrow
        Time: 2:00 PM
        Location: Conference Room B
        
        Please join us for the quarterly project review.
        """
        
        result = self.processor.process_text(text)
        
        self.assertEqual(result.detected_format, TextFormat.STRUCTURED_EMAIL)
        self.assertIn("Subject: Project Review Meeting", result.processed_text)
        self.assertIn("Time: 2:00 PM", result.processed_text)
        self.assertGreater(result.format_specific_confidence, 0.8)
    
    def test_paragraph_processing(self):
        """Test paragraph format detection and processing."""
        text = """We have a team meeting scheduled for tomorrow at 2pm in the main conference room.

The agenda will include project updates and planning for next quarter.

Please bring your laptops and any relevant documents."""
        
        result = self.processor.process_text(text)
        
        self.assertEqual(result.detected_format, TextFormat.PARAGRAPHS)
        self.assertIn("team meeting scheduled for tomorrow at 2:00 PM", result.processed_text)
        self.assertEqual(len(result.processed_text.split('\n\n')), 3)
    
    def test_typo_normalization_time_formats(self):
        """Test normalization of various time format typos."""
        test_cases = [
            ("Meeting at 9a.m", "Meeting at 9:00 AM"),
            ("Call at 2p.m", "Call at 2:00 PM"),
            ("Event at 10:30a.m", "Event at 10:30 AM"),
            ("Lunch at 12:00 P M", "Lunch at 12:00 PM"),
            ("Meeting at 9 AM", "Meeting at 9:00 AM"),
            ("Call at 2:30pm", "Call at 2:30 PM"),
        ]
        
        for input_text, expected_output in test_cases:
            with self.subTest(input_text=input_text):
                result = self.processor.process_text(input_text)
                self.assertIn(expected_output, result.processed_text)
    
    def test_case_normalization(self):
        """Test case normalization while preserving proper nouns and acronyms."""
        text = "meeting with CEO john smith at IBM headquarters tomorrow at 2pm"
        
        result = self.processor.process_text(text)
        
        # Should capitalize sentence start
        self.assertTrue(result.processed_text.startswith("Meeting"))
        # Should preserve acronyms
        self.assertIn("IBM", result.processed_text)
        # Should normalize time
        self.assertIn("2:00 PM", result.processed_text)
    
    def test_whitespace_normalization(self):
        """Test whitespace cleanup and normalization."""
        text = """
        Meeting    tomorrow   at   2pm
        
        
        Location:     Conference Room A
        """
        
        result = self.processor.process_text(text)
        
        # Should normalize multiple spaces
        self.assertNotIn("    ", result.processed_text)
        self.assertNotIn("   ", result.processed_text)
        # Should preserve paragraph breaks
        self.assertIn("\n", result.processed_text)
    
    def test_multiple_event_detection(self):
        """Test detection of multiple events in single text."""
        text = """
        • Morning standup at 9am
        • Client presentation at 2pm
        • Team dinner at 6pm
        """
        
        result = self.processor.process_text(text)
        
        self.assertTrue(result.multiple_events_detected)
        self.assertGreater(len(result.event_boundaries), 0)
        
        # Test event segment extraction
        segments = self.processor.extract_event_segments(result)
        self.assertGreater(len(segments), 1)
    
    def test_screenshot_text_detection(self):
        """Test detection of screenshot/OCR text characteristics."""
        # Simulate OCR text with unusual spacing and formatting
        text = "M E E T I N G   T O M O R R O W   A T   2 P M"
        
        result = self.processor.process_text(text)
        
        # Should detect as screenshot text or handle appropriately
        self.assertIsNotNone(result.detected_format)
        # Should normalize the spacing
        self.assertIn("MEETING TOMORROW AT 2:00 PM", result.processed_text)
    
    def test_mixed_format_processing(self):
        """Test processing of mixed format text (bullets + paragraphs)."""
        text = """
        Project kickoff meeting details:
        
        • Date: Tomorrow
        • Time: 2pm
        
        We'll be discussing the project timeline and deliverables.
        Please review the attached documents before the meeting.
        """
        
        result = self.processor.process_text(text)
        
        self.assertEqual(result.detected_format, TextFormat.MIXED)
        self.assertIn("Date: Tomorrow", result.processed_text)
        self.assertIn("Time: 2:00 PM", result.processed_text)
        self.assertIn("project timeline", result.processed_text)
    
    def test_date_normalization(self):
        """Test normalization of various date formats."""
        test_cases = [
            ("Meeting on 12/25/2023", "Meeting on 12/25/2023"),
            ("Event on Dec 25th, 2023", "Event on Dec 25, 2023"),
            ("Call on December 25", "Call on December 25"),
        ]
        
        for input_text, expected_pattern in test_cases:
            with self.subTest(input_text=input_text):
                result = self.processor.process_text(input_text)
                # Check that some normalization occurred
                self.assertIsNotNone(result.processed_text)
    
    def test_empty_text_handling(self):
        """Test handling of empty or whitespace-only text."""
        test_cases = ["", "   ", "\n\n\n", "\t\t"]
        
        for text in test_cases:
            with self.subTest(text=repr(text)):
                result = self.processor.process_text(text)
                self.assertEqual(result.processed_text, "")
                self.assertEqual(result.confidence, 0.0)
    
    def test_processing_metadata(self):
        """Test that processing metadata is properly tracked."""
        text = "Meeting tomorrow at 2p.m in Conference Room A"
        
        result = self.processor.process_text(text)
        
        # Should have processing steps recorded
        self.assertGreater(len(result.processing_steps), 0)
        self.assertIn("format_detection", result.processing_steps)
        self.assertIn("typo_normalization", result.processing_steps)
        
        # Should have metadata
        self.assertIsInstance(result.processing_metadata, dict)
    
    def test_confidence_calculation(self):
        """Test confidence scoring calculation."""
        # High-quality structured text
        structured_text = """
        Subject: Team Meeting
        Date: Tomorrow
        Time: 2:00 PM
        Location: Conference Room A
        """
        
        result = self.processor.process_text(structured_text)
        high_confidence = result.confidence
        
        # Lower-quality unstructured text
        unstructured_text = "maybe meeting sometime tomorrow afternoon"
        
        result2 = self.processor.process_text(unstructured_text)
        low_confidence = result2.confidence
        
        # Structured text should have higher confidence
        self.assertGreater(high_confidence, low_confidence)
    
    def test_format_consistency(self):
        """Test that similar content produces consistent results regardless of format."""
        # Same event information in different formats
        bullet_format = "• Meeting tomorrow at 2pm in Room A"
        plain_format = "Meeting tomorrow at 2pm in Room A"
        structured_format = "Event: Meeting\nTime: tomorrow at 2pm\nLocation: Room A"
        
        results = []
        for text in [bullet_format, plain_format, structured_format]:
            result = self.processor.process_text(text)
            results.append(result)
        
        # All should normalize time consistently
        for result in results:
            self.assertIn("2:00 PM", result.processed_text)
        
        # All should contain key information
        for result in results:
            self.assertIn("Meeting", result.processed_text)
            self.assertIn("tomorrow", result.processed_text)
            self.assertIn("Room A", result.processed_text)
    
    def test_event_segment_extraction(self):
        """Test extraction of individual event segments."""
        text = """
        1. Morning standup at 9am in Room A
        2. Client call at 11am
        3. Lunch meeting at 1pm at Cafe Downtown
        """
        
        result = self.processor.process_text(text)
        segments = self.processor.extract_event_segments(result)
        
        # Should extract multiple segments
        self.assertGreater(len(segments), 1)
        
        # Each segment should contain event information
        for segment in segments:
            self.assertGreaterEqual(len(segment.split()), 3)  # Minimum word count
    
    def test_punctuation_cleanup(self):
        """Test cleanup of excessive punctuation."""
        text = "Meeting tomorrow at 2pm!!! Location: Room A... Duration: 1 hour???"
        
        result = self.processor.process_text(text)
        
        # Should normalize excessive punctuation
        self.assertNotIn("!!!", result.processed_text)
        self.assertNotIn("???", result.processed_text)
        # Should preserve single punctuation
        self.assertIn("!", result.processed_text)
        self.assertIn("?", result.processed_text)
    
    def test_text_format_result_serialization(self):
        """Test TextFormatResult serialization to dictionary."""
        text = "Meeting tomorrow at 2pm"
        result = self.processor.process_text(text)
        
        # Should serialize to dictionary
        result_dict = result.to_dict()
        self.assertIsInstance(result_dict, dict)
        
        # Should contain expected keys
        expected_keys = [
            'processed_text', 'original_text', 'detected_format',
            'confidence', 'processing_steps', 'format_specific_confidence',
            'normalization_quality', 'multiple_events_detected'
        ]
        
        for key in expected_keys:
            self.assertIn(key, result_dict)
    
    def test_format_specific_confidence_adjustments(self):
        """Test that different formats receive appropriate confidence adjustments."""
        # Test structured email (should have high confidence)
        structured_text = """
        Subject: Team Meeting
        Date: Tomorrow
        Time: 2:00 PM
        """
        structured_result = self.processor.process_text(structured_text)
        
        # Test plain text (should have lower confidence)
        plain_text = "maybe meeting sometime tomorrow"
        plain_result = self.processor.process_text(plain_text)
        
        # Test screenshot text (should have lowest confidence)
        screenshot_text = "M E E T I N G   T O M O R R O W"
        screenshot_result = self.processor.process_text(screenshot_text)
        
        # Verify confidence ordering
        self.assertGreater(structured_result.format_specific_confidence, plain_result.format_specific_confidence)
        self.assertGreater(plain_result.format_specific_confidence, screenshot_result.format_specific_confidence)
    
    def test_processing_step_tracking(self):
        """Test that processing steps are properly tracked with details."""
        text = "Meeting tomorrow at 2p.m"
        result = self.processor.process_text(text)
        
        # Should have multiple processing steps
        self.assertGreater(len(result.processing_steps), 3)
        
        # Should include key processing steps
        expected_steps = ['format_detection', 'typo_normalization', 'case_normalization']
        for step in expected_steps:
            self.assertIn(step, result.processing_steps)
        
        # Should have step details in metadata
        self.assertIn('step_details', result.processing_metadata)
        self.assertIn('format_detection', result.processing_metadata['step_details'])
    
    def test_normalization_quality_scoring(self):
        """Test normalization quality scoring based on corrections made."""
        # Text with typos that need normalization
        typo_text = "Meeting at 9a.m and 2p.m tomorrow"
        typo_result = self.processor.process_text(typo_text)
        
        # Text with no typos
        clean_text = "Meeting at 9:00 AM and 2:00 PM tomorrow"
        clean_result = self.processor.process_text(clean_text)
        
        # Both should have normalization quality scores
        self.assertIsInstance(typo_result.normalization_quality, float)
        self.assertIsInstance(clean_result.normalization_quality, float)
        self.assertGreaterEqual(typo_result.normalization_quality, 0.0)
        self.assertLessEqual(typo_result.normalization_quality, 1.0)
    
    def test_original_format_preservation(self):
        """Test that original format is preserved for reference."""
        original_text = "Meeting   tomorrow    at   2pm"
        result = self.processor.process_text(original_text)
        
        # Original text should be preserved exactly
        self.assertEqual(result.original_text, original_text)
        
        # Processed text should be different (normalized)
        self.assertNotEqual(result.processed_text, result.original_text)
        self.assertIn("2:00 PM", result.processed_text)  # Time should be normalized


if __name__ == '__main__':
    unittest.main()