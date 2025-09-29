"""
FormatAwareTextProcessor for handling various text formats and normalizing content.

This module provides comprehensive text processing capabilities for event extraction,
including bullet point parsing, paragraph processing, typo normalization, and
format consistency handling.
"""

import re
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum


class TextFormat(Enum):
    """Enumeration of detected text formats."""
    BULLET_POINTS = "bullet_points"
    PARAGRAPHS = "paragraphs"
    MIXED = "mixed"
    STRUCTURED_EMAIL = "structured_email"
    PLAIN_TEXT = "plain_text"
    SCREENSHOT_TEXT = "screenshot_text"


@dataclass
class TextFormatResult:
    """
    Result of text format processing with metadata and confidence scoring.
    
    Tracks format detection, processing steps, and quality metrics for debugging
    and confidence adjustments.
    """
    processed_text: str = ""
    original_text: str = ""
    detected_format: TextFormat = TextFormat.PLAIN_TEXT
    confidence: float = 0.0
    processing_steps: List[str] = field(default_factory=list)
    format_specific_confidence: float = 0.0
    normalization_quality: float = 0.0
    multiple_events_detected: bool = False
    event_boundaries: List[Tuple[int, int]] = field(default_factory=list)  # (start, end) positions
    processing_metadata: Dict[str, Any] = field(default_factory=dict)
    
    def add_processing_step(self, step: str, details: Dict[str, Any] = None):
        """Add a processing step with optional details."""
        self.processing_steps.append(step)
        if details:
            if 'step_details' not in self.processing_metadata:
                self.processing_metadata['step_details'] = {}
            self.processing_metadata['step_details'][step] = details
    
    def calculate_overall_confidence(self) -> float:
        """Calculate overall confidence based on format and normalization quality."""
        base_confidence = (self.format_specific_confidence + self.normalization_quality) / 2
        
        # Adjust based on detected format
        format_multipliers = {
            TextFormat.STRUCTURED_EMAIL: 1.1,
            TextFormat.BULLET_POINTS: 1.05,
            TextFormat.PARAGRAPHS: 1.0,
            TextFormat.MIXED: 0.95,
            TextFormat.PLAIN_TEXT: 0.9,
            TextFormat.SCREENSHOT_TEXT: 0.85
        }
        
        multiplier = format_multipliers.get(self.detected_format, 1.0)
        self.confidence = min(1.0, base_confidence * multiplier)
        return self.confidence
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'processed_text': self.processed_text,
            'original_text': self.original_text,
            'detected_format': self.detected_format.value,
            'confidence': self.confidence,
            'processing_steps': self.processing_steps,
            'format_specific_confidence': self.format_specific_confidence,
            'normalization_quality': self.normalization_quality,
            'multiple_events_detected': self.multiple_events_detected,
            'event_boundaries': self.event_boundaries,
            'processing_metadata': self.processing_metadata
        }


class FormatAwareTextProcessor:
    """
    Comprehensive text processor for handling various formats and normalizing content.
    
    Handles bullet points, paragraphs, multi-paragraph text, typo normalization,
    case correction, whitespace cleanup, and format consistency.
    """
    
    def __init__(self):
        """Initialize the text processor with compiled regex patterns."""
        self._compile_patterns()
    
    def _compile_patterns(self):
        """Compile regex patterns for efficient processing."""
        # Bullet point patterns
        self.bullet_patterns = [
            re.compile(r'^[\s]*[-•*]\s+(.+)$', re.MULTILINE),  # Standard bullets
            re.compile(r'^[\s]*\d+[\.\)]\s+(.+)$', re.MULTILINE),  # Numbered lists
            re.compile(r'^[\s]*[a-zA-Z][\.\)]\s+(.+)$', re.MULTILINE),  # Lettered lists
        ]
        
        # Time normalization patterns - order matters for proper matching
        self.time_patterns = [
            # Handle existing HH:MM formats first (most specific)
            (re.compile(r'\b(\d{1,2}):(\d{2})\s*([AaPp])\s*\.?\s*[Mm]\.?\b'), self._normalize_am_pm),
            (re.compile(r'\b(\d{1,2}):(\d{2})\s*a\.?\s*m\.?\b', re.IGNORECASE), r'\1:\2 AM'),
            (re.compile(r'\b(\d{1,2}):(\d{2})\s*p\.?\s*m\.?\b', re.IGNORECASE), r'\1:\2 PM'),
            (re.compile(r'\b(\d{1,2}):(\d{2})\s*A\s*M\b', re.IGNORECASE), r'\1:\2 AM'),
            (re.compile(r'\b(\d{1,2}):(\d{2})\s*P\s*M\b', re.IGNORECASE), r'\1:\2 PM'),
            # Handle hour-only formats (add :00)
            (re.compile(r'\b(\d{1,2})\s*a\.?m\.?\b', re.IGNORECASE), r'\1:00 AM'),
            (re.compile(r'\b(\d{1,2})\s*p\.?m\.?\b', re.IGNORECASE), r'\1:00 PM'),
        ]
        
        # Date normalization patterns
        self.date_patterns = [
            # Handle various date separators
            (re.compile(r'\b(\d{1,2})[\/\-\.](\d{1,2})[\/\-\.](\d{2,4})\b'), self._normalize_date),
            (re.compile(r'\b(\w+)\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(\d{4})\b', re.IGNORECASE), r'\1 \2, \3'),
            (re.compile(r'\b(\w+)\s+(\d{1,2})(?:st|nd|rd|th)?\b', re.IGNORECASE), r'\1 \2'),
        ]
        
        # Multiple event detection patterns
        self.event_boundary_patterns = [
            re.compile(r'^\s*[-•*]\s+', re.MULTILINE),  # Bullet points at line start
            re.compile(r'^\s*\d+[\.\)]\s+', re.MULTILINE),  # Numbered items at line start
            re.compile(r'\b(?:then|next|after that|also|additionally)\b', re.IGNORECASE),  # Sequence words
        ]
        
        # Event keyword patterns for detecting multiple events
        self.event_keywords = re.compile(r'\b(?:meeting|event|appointment|call|lunch|dinner|conference|standup|presentation)\b', re.IGNORECASE)
        
        # Whitespace normalization
        self.whitespace_patterns = [
            (re.compile(r'\n\s*\n\s*\n+'), '\n\n'),  # Multiple newlines to double newline
            (re.compile(r'^[ \t]+|[ \t]+$', re.MULTILINE), ''),  # Trim spaces/tabs from line starts/ends but preserve newlines
            (re.compile(r'[ \t]+'), ' '),  # Multiple spaces/tabs to single space
        ]
        
        # Format detection patterns
        self.format_detection_patterns = {
            'bullet_points': re.compile(r'^[\s]*[-•*]\s+', re.MULTILINE),
            'numbered_list': re.compile(r'^[\s]*\d+[\.\)]\s+', re.MULTILINE),
            'email_headers': re.compile(r'^(From|To|Subject|Date|Time|When|Where):\s*', re.MULTILINE | re.IGNORECASE),
            'structured_content': re.compile(r'^[\s]*(Title|Event|Meeting|Subject|Date|Time|Location|Where|When):\s*', re.MULTILINE | re.IGNORECASE),
        }
    
    def _normalize_am_pm(self, match) -> str:
        """Normalize AM/PM format with proper spacing."""
        hour, minute, period = match.groups()
        period_upper = period.upper() + 'M'
        return f"{hour}:{minute} {period_upper}"
    
    def _normalize_date(self, match) -> str:
        """Normalize date format handling different separators."""
        part1, part2, part3 = match.groups()
        # Use consistent separator
        return f"{part1}/{part2}/{part3}"
    
    def process_text(self, text: str) -> TextFormatResult:
        """
        Main processing method that handles all text format processing.
        
        Args:
            text: Raw input text to process
            
        Returns:
            TextFormatResult with processed text and metadata
        """
        result = TextFormatResult(original_text=text)
        
        if not text or not text.strip():
            result.processed_text = ""
            result.confidence = 0.0
            return result
        
        # Step 1: Detect format
        detected_format = self._detect_format(text)
        result.detected_format = detected_format
        result.add_processing_step("format_detection", {"detected_format": detected_format.value})
        
        # Step 2: Format-specific processing (before whitespace normalization for screenshot text)
        if detected_format == TextFormat.SCREENSHOT_TEXT:
            # Process screenshot text before whitespace normalization to preserve word boundaries
            processed_text = self._process_screenshot_text(text, result)
            # Then apply whitespace normalization
            processed_text = self._normalize_whitespace(processed_text)
            result.add_processing_step("whitespace_normalization")
        else:
            # For other formats, normalize whitespace first
            processed_text = self._normalize_whitespace(text)
            result.add_processing_step("whitespace_normalization")
            
            # Then apply format-specific processing
            if detected_format == TextFormat.BULLET_POINTS:
                processed_text = self._process_bullet_points(processed_text, result)
            elif detected_format == TextFormat.STRUCTURED_EMAIL:
                processed_text = self._process_structured_email(processed_text, result)
            elif detected_format == TextFormat.PARAGRAPHS:
                processed_text = self._process_paragraphs(processed_text, result)
            elif detected_format == TextFormat.MIXED:
                processed_text = self._process_mixed_format(processed_text, result)
            else:
                processed_text = self._process_plain_text(processed_text, result)
        
        # Step 4: Typo normalization
        processed_text = self._normalize_typos(processed_text, result)
        
        # Step 5: Case normalization
        processed_text = self._normalize_case(processed_text, result)
        
        # Step 6: Multiple event detection
        self._detect_multiple_events(processed_text, result)
        
        # Step 7: Final cleanup
        processed_text = self._final_cleanup(processed_text, result)
        
        result.processed_text = processed_text
        result.calculate_overall_confidence()
        
        return result
    
    def _detect_format(self, text: str) -> TextFormat:
        """Detect the primary format of the input text."""
        # Count different format indicators first
        bullet_matches = len(list(self.format_detection_patterns['bullet_points'].finditer(text)))
        numbered_matches = len(list(self.format_detection_patterns['numbered_list'].finditer(text)))
        
        # Count actual paragraphs (separated by double newlines)
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
        paragraph_count = len(paragraphs)
        
        # Count lines that aren't bullets/numbers
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        non_bullet_lines = 0
        for line in lines:
            is_bullet = any(pattern.match(line) for pattern in self.bullet_patterns)
            if not is_bullet:
                non_bullet_lines += 1
        
        # Determine primary format
        total_bullets = bullet_matches + numbered_matches
        
        if total_bullets > 0:
            # Has bullets/numbers - check if it's mixed with other content
            # Mixed format: has bullets AND significant non-bullet content
            if non_bullet_lines > total_bullets and non_bullet_lines >= 2:
                return TextFormat.MIXED
            return TextFormat.BULLET_POINTS
        
        # No bullets, check for structured email format
        if self.format_detection_patterns['email_headers'].search(text):
            return TextFormat.STRUCTURED_EMAIL
        
        # Check for structured content (but only if no bullets)
        if self.format_detection_patterns['structured_content'].search(text):
            return TextFormat.STRUCTURED_EMAIL
        
        # No bullets, check paragraph structure
        if paragraph_count > 1:
            return TextFormat.PARAGRAPHS
        
        # Check for screenshot-like characteristics (OCR artifacts)
        if self._has_screenshot_characteristics(text):
            return TextFormat.SCREENSHOT_TEXT
        
        return TextFormat.PLAIN_TEXT
    
    def _has_screenshot_characteristics(self, text: str) -> bool:
        """Detect if text has characteristics of screenshot/OCR text."""
        # Check for spaced-out single characters (common OCR artifact)
        spaced_chars = bool(re.search(r'\b[A-Z]\s+[A-Z]\s+[A-Z]', text))
        
        indicators = [
            len(re.findall(r'\b[A-Z]{2,}\b', text)) > 2,  # Many all-caps words
            len(re.findall(r'\s+', text)) / len(text) > 0.2,  # Excessive whitespace
            bool(re.search(r'[^\w\s\.,!?;:\-\(\)\'\"]+', text)),  # Unusual characters
            len(text.split('\n')) > len(text) / 20,  # Many short lines
            spaced_chars,  # Spaced-out characters (strong OCR indicator)
        ]
        
        # If we have spaced characters, that's a strong indicator
        if spaced_chars:
            return True
        
        return sum(indicators) >= 2
    
    def _normalize_whitespace(self, text: str) -> str:
        """Normalize whitespace throughout the text."""
        for pattern, replacement in self.whitespace_patterns:
            text = pattern.sub(replacement, text)
        return text.strip()
    
    def _process_bullet_points(self, text: str, result: TextFormatResult) -> str:
        """Process bullet point formatted text."""
        result.add_processing_step("bullet_point_processing")
        
        lines = text.split('\n')
        processed_lines = []
        
        for line in lines:
            # Check if line is a bullet point
            is_bullet = False
            for pattern in self.bullet_patterns:
                match = pattern.match(line)
                if match:
                    # Extract content after bullet marker
                    content = match.group(1).strip()
                    processed_lines.append(content)
                    is_bullet = True
                    break
            
            if not is_bullet and line.strip():
                # Non-bullet line, keep as is but clean up
                processed_lines.append(line.strip())
        
        # Join with appropriate spacing
        processed_text = '\n'.join(processed_lines)
        result.format_specific_confidence = 0.8
        return processed_text
    
    def _process_structured_email(self, text: str, result: TextFormatResult) -> str:
        """Process structured email format with headers."""
        result.add_processing_step("structured_email_processing")
        
        # Extract structured information
        structured_data = {}
        remaining_text = text
        
        # Find and extract structured fields
        for match in self.format_detection_patterns['email_headers'].finditer(text):
            field_name = match.group(1).lower()
            start_pos = match.end()
            
            # Find the end of this field (next field or end of text)
            next_match = None
            for next_field in self.format_detection_patterns['email_headers'].finditer(text, start_pos):
                next_match = next_field
                break
            
            end_pos = next_match.start() if next_match else len(text)
            field_value = text[start_pos:end_pos].strip()
            
            structured_data[field_name] = field_value
        
        # Reconstruct text with normalized structure
        processed_parts = []
        for field, value in structured_data.items():
            if value:
                processed_parts.append(f"{field.title()}: {value}")
        
        # Add any remaining unstructured content
        unstructured_text = remaining_text
        for pattern in [self.format_detection_patterns['email_headers']]:
            unstructured_text = pattern.sub('', unstructured_text)
        
        unstructured_text = unstructured_text.strip()
        if unstructured_text:
            processed_parts.append(unstructured_text)
        
        result.format_specific_confidence = 0.9
        result.processing_metadata['structured_fields'] = list(structured_data.keys())
        
        return '\n'.join(processed_parts)
    
    def _process_paragraphs(self, text: str, result: TextFormatResult) -> str:
        """Process paragraph-formatted text."""
        result.add_processing_step("paragraph_processing")
        
        # Split into paragraphs and clean each one
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
        
        # If we don't have clear paragraph breaks, treat as single paragraph
        if len(paragraphs) <= 1:
            # Check for single line breaks that might indicate paragraphs
            lines = [line.strip() for line in text.split('\n') if line.strip()]
            if len(lines) > 1:
                # Multiple lines, preserve some structure
                processed_text = ' '.join(lines)
                result.format_specific_confidence = 0.6
                result.processing_metadata['paragraph_count'] = len(lines)
                return processed_text
        
        # Process each paragraph
        processed_paragraphs = []
        for paragraph in paragraphs:
            # Clean up internal line breaks within paragraphs
            cleaned = re.sub(r'\n+', ' ', paragraph)
            cleaned = re.sub(r'\s+', ' ', cleaned).strip()
            if cleaned:
                processed_paragraphs.append(cleaned)
        
        result.format_specific_confidence = 0.7
        result.processing_metadata['paragraph_count'] = len(processed_paragraphs)
        
        return '\n\n'.join(processed_paragraphs)
    
    def _process_mixed_format(self, text: str, result: TextFormatResult) -> str:
        """Process mixed format text (bullets + paragraphs)."""
        result.add_processing_step("mixed_format_processing")
        
        # Process as both bullet points and paragraphs
        bullet_processed = self._process_bullet_points(text, TextFormatResult())
        paragraph_processed = self._process_paragraphs(text, TextFormatResult())
        
        # Choose the better result based on structure preservation
        if len(bullet_processed.split('\n')) > len(paragraph_processed.split('\n\n')):
            processed_text = bullet_processed
            result.processing_metadata['mixed_strategy'] = 'bullet_priority'
        else:
            processed_text = paragraph_processed
            result.processing_metadata['mixed_strategy'] = 'paragraph_priority'
        
        result.format_specific_confidence = 0.6
        return processed_text
    
    def _process_screenshot_text(self, text: str, result: TextFormatResult) -> str:
        """Process screenshot/OCR text with special handling for spaced characters."""
        result.add_processing_step("screenshot_text_processing")
        
        # Handle spaced-out characters (common in OCR text)
        # Work with original text that still has multiple spaces to identify word boundaries
        processed = text
        
        # Split by multiple spaces (2+) to identify word boundaries first
        word_parts = re.split(r'\s{2,}', processed)
        
        processed_words = []
        for word_part in word_parts:
            word_part = word_part.strip()
            if not word_part:
                continue
                
            # Check if this part has spaced single characters
            if re.search(r'\b[A-Z]\s+[A-Z]', word_part):
                # Collapse spaced characters within this word part
                collapsed_word = re.sub(r'\s+', '', word_part)
                processed_words.append(collapsed_word)
            else:
                # Keep as-is but normalize internal spaces
                normalized_word = re.sub(r'\s+', ' ', word_part)
                processed_words.append(normalized_word)
        
        # If no multiple spaces were found, fall back to single-space splitting
        if len(processed_words) <= 1:
            # Try to detect word boundaries by looking for patterns
            # This is a fallback for cases where word boundaries aren't clear
            tokens = processed.split()
            grouped_tokens = []
            current_word_chars = []
            
            for token in tokens:
                if len(token) == 1 and token.isalpha():
                    current_word_chars.append(token)
                else:
                    if current_word_chars:
                        grouped_tokens.append(''.join(current_word_chars))
                        current_word_chars = []
                    grouped_tokens.append(token)
            
            if current_word_chars:
                grouped_tokens.append(''.join(current_word_chars))
            
            processed = ' '.join(grouped_tokens)
        else:
            # Rejoin the processed words with single spaces
            processed = ' '.join(processed_words)
        
        result.format_specific_confidence = 0.4  # Lower confidence for OCR text
        result.processing_metadata['screenshot_processing'] = {
            'spaced_chars_detected': True,
            'original_spacing_pattern': 'detected',
            'word_parts_found': len(word_parts),
            'processed_words': len(processed_words)
        }
        
        return processed
    
    def _process_plain_text(self, text: str, result: TextFormatResult) -> str:
        """Process plain text format."""
        result.add_processing_step("plain_text_processing")
        
        # Basic cleanup for plain text
        processed = re.sub(r'\n+', ' ', text)  # Collapse line breaks
        processed = re.sub(r'\s+', ' ', processed).strip()  # Normalize spaces
        
        result.format_specific_confidence = 0.5
        return processed
    
    def _normalize_typos(self, text: str, result: TextFormatResult) -> str:
        """Normalize common typos, especially in time formats."""
        result.add_processing_step("typo_normalization")
        
        original_text = text
        
        # Apply time pattern normalizations - collect all matches first, then apply non-overlapping ones
        all_matches = []
        
        for pattern_idx, (pattern, replacement) in enumerate(self.time_patterns):
            matches = list(pattern.finditer(text))
            for match in matches:
                all_matches.append((match.start(), match.end(), match, replacement, pattern_idx))
        
        # Sort by position and remove overlapping matches (keep the first/most specific one)
        all_matches.sort(key=lambda x: x[0])  # Sort by start position
        non_overlapping_matches = []
        
        for start, end, match, replacement, pattern_idx in all_matches:
            # Check if this match overlaps with any already selected match
            overlaps = False
            for prev_start, prev_end, _, _, _ in non_overlapping_matches:
                if not (end <= prev_start or start >= prev_end):  # Overlapping
                    overlaps = True
                    break
            
            if not overlaps:
                non_overlapping_matches.append((start, end, match, replacement, pattern_idx))
        
        # Apply replacements in reverse order to avoid position shifts
        for start, end, match, replacement, pattern_idx in reversed(non_overlapping_matches):
            if callable(replacement):
                new_text = replacement(match)
            else:
                new_text = match.expand(replacement)
            
            text = text[:start] + new_text + text[end:]
        
        # Apply date pattern normalizations
        for pattern, replacement in self.date_patterns:
            if callable(replacement):
                text = pattern.sub(replacement, text)
            else:
                text = pattern.sub(replacement, text)
        
        # Calculate normalization quality based on changes made
        changes_made = len(re.findall(r'\d+:\d+\s*[AP]M', text, re.IGNORECASE))
        total_time_references = len(re.findall(r'\d+[:\.]?\d*\s*[ap]\.?m?\.?', original_text, re.IGNORECASE))
        
        if total_time_references > 0:
            result.normalization_quality = min(1.0, changes_made / total_time_references)
        else:
            result.normalization_quality = 0.8  # Default for no time references
        
        result.processing_metadata['typo_corrections'] = {
            'time_normalizations': changes_made,
            'total_time_references': total_time_references
        }
        
        return text
    
    def _normalize_case(self, text: str, result: TextFormatResult) -> str:
        """Normalize case while preserving proper nouns and acronyms."""
        result.add_processing_step("case_normalization")
        
        # Preserve paragraph structure by processing each paragraph separately
        paragraphs = text.split('\n\n')
        processed_paragraphs = []
        
        for paragraph in paragraphs:
            if not paragraph.strip():
                continue
            
            # Split paragraph into sentences for better case handling
            sentences = re.split(r'([.!?]+)', paragraph)  # Keep delimiters
            processed_parts = []
            
            i = 0
            while i < len(sentences):
                sentence = sentences[i]
                delimiter = sentences[i + 1] if i + 1 < len(sentences) else ''
                
                if sentence.strip():
                    # Capitalize first letter of sentence
                    sentence = sentence.strip()
                    # Don't change all-caps words (likely acronyms)
                    words = sentence.split()
                    processed_words = []
                    
                    for j, word in enumerate(words):
                        if word.isupper() and len(word) > 1:
                            # Keep acronyms as-is
                            processed_words.append(word)
                        elif j == 0:
                            # Capitalize first word
                            processed_words.append(word.capitalize())
                        else:
                            # Keep other words as-is to preserve proper nouns
                            processed_words.append(word)
                    
                    processed_parts.append(' '.join(processed_words) + delimiter)
                
                i += 2  # Skip delimiter
            
            if processed_parts:
                processed_paragraphs.append(''.join(processed_parts))
        
        result.processing_metadata['case_corrections'] = len(processed_paragraphs)
        return '\n\n'.join(processed_paragraphs)
    
    def _detect_multiple_events(self, text: str, result: TextFormatResult):
        """Detect if text contains multiple events."""
        result.add_processing_step("multiple_event_detection")
        
        event_boundaries = []
        
        # Look for boundary patterns (bullet points, numbered lists)
        for pattern in self.event_boundary_patterns[:2]:  # Only bullet and numbered patterns
            matches = list(pattern.finditer(text))
            for match in matches:
                event_boundaries.append((match.start(), match.end()))
        
        # Count event keywords to help determine multiple events
        event_keyword_matches = list(self.event_keywords.finditer(text))
        
        # Remove duplicates and sort boundaries
        event_boundaries = sorted(list(set(event_boundaries)))
        
        # Determine if multiple events are present
        multiple_events = False
        
        if len(event_boundaries) >= 2:
            # Multiple bullet points or numbered items
            multiple_events = True
        elif len(event_keyword_matches) >= 2:
            # Multiple event keywords found
            multiple_events = True
            # Add keyword positions as boundaries
            for match in event_keyword_matches:
                event_boundaries.append((match.start(), match.end()))
            event_boundaries = sorted(list(set(event_boundaries)))
        
        result.multiple_events_detected = multiple_events
        result.event_boundaries = event_boundaries
        
        result.processing_metadata['multiple_events'] = {
            'detected': multiple_events,
            'boundary_count': len(event_boundaries),
            'event_keyword_count': len(event_keyword_matches)
        }
    
    def _final_cleanup(self, text: str, result: TextFormatResult) -> str:
        """Final cleanup and consistency checks."""
        result.add_processing_step("final_cleanup")
        
        # Remove excessive punctuation but preserve single instances
        text = re.sub(r'[.]{3,}', '...', text)
        text = re.sub(r'[!]{2,}', '!', text)
        text = re.sub(r'[?]{2,}', '?', text)
        
        # Ensure consistent spacing around punctuation (but not colons in times)
        # First handle colons that are NOT part of time formats
        text = re.sub(r'(?<!\d)\s*:\s*(?!\d)', ': ', text)  # Colons not between digits
        # Handle other punctuation, but preserve paragraph breaks
        # Only fix spacing when punctuation is followed by a single space and letter (not newlines)
        text = re.sub(r'([,.!?;]) +([a-zA-Z])', r'\1 \2', text)  # Normalize multiple spaces after punctuation
        text = re.sub(r'([,.!?;])([a-zA-Z])', r'\1 \2', text)  # Add space when punctuation directly touches letter
        text = re.sub(r'\s+([,.!?;])', r'\1', text)  # Remove space before punctuation
        
        # Clean up extra spaces but preserve paragraph breaks
        # Process each paragraph separately to preserve structure
        paragraphs = text.split('\n\n')
        cleaned_paragraphs = []
        
        for paragraph in paragraphs:
            if paragraph.strip():
                # Clean up spaces within the paragraph
                cleaned_paragraph = re.sub(r'\s+', ' ', paragraph).strip()
                if cleaned_paragraph:
                    cleaned_paragraphs.append(cleaned_paragraph)
        
        # Rejoin paragraphs with double newlines
        text = '\n\n'.join(cleaned_paragraphs)
        
        # Clean up excessive empty lines (shouldn't be needed now, but just in case)
        text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
        
        return text.strip()
    
    def extract_event_segments(self, format_result: TextFormatResult) -> List[str]:
        """
        Extract individual event segments from processed text.
        
        Args:
            format_result: Result from process_text()
            
        Returns:
            List of text segments, each potentially containing one event
        """
        if not format_result.multiple_events_detected:
            return [format_result.processed_text]
        
        text = format_result.processed_text
        boundaries = format_result.event_boundaries
        
        if not boundaries:
            return [text]
        
        segments = []
        last_end = 0
        
        for start, end in boundaries:
            # Add text before this boundary as a segment
            if start > last_end:
                segment = text[last_end:start].strip()
                if segment:
                    segments.append(segment)
            
            last_end = end
        
        # Add remaining text after last boundary
        if last_end < len(text):
            segment = text[last_end:].strip()
            if segment:
                segments.append(segment)
        
        # Filter out very short segments that are unlikely to be events
        segments = [s for s in segments if len(s.split()) >= 3]
        
        return segments if segments else [text]