"""
Title extraction service for calendar events.
Provides regex-based title extraction with confidence scoring.
"""

import re
import logging
from typing import List, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger("services.title_extractor")

# Strict Title: line match + meta prefixes
_TITLE_LINE = re.compile(r'(?mi)^\s*title\s*:\s*(.+?)\s*$', re.IGNORECASE)
_META_PREFIXES = tuple(s.lower() for s in ["item id:", "due date:", "deadline:", "date:"])


@dataclass
class TitleMatch:
    """Represents a title extraction match."""
    title: str
    confidence: float
    extraction_type: str
    start_pos: int
    end_pos: int
    matched_text: str


class TitleExtractor:
    """
    Regex-based title extraction for the hybrid parsing pipeline.
    
    Provides structured title extraction with confidence scoring
    and multiple extraction strategies.
    """
    
    def __init__(self):
        """Initialize the title extractor."""
        self.patterns = self._compile_patterns()
    
    def _compile_patterns(self) -> dict:
        """Compile regex patterns for title extraction."""
        return {
            'title_line': re.compile(r'(?mi)^\s*title\s*:\s*(.+?)\s*$'),
            'quoted_title': re.compile(r'"([^"]+)"'),
            'first_line': re.compile(r'^([^\n\r]+)'),
            'before_date': re.compile(r'^(.+?)(?:\s+(?:on|at|from|due|deadline)\s+\d)', re.IGNORECASE),
            'structured_event': re.compile(r'^([^:]+?)(?:\s+(?:DATE|TIME|LOCATION|WHEN|WHERE)\s)', re.IGNORECASE)
        }
    
    def extract_title(self, text: str) -> List[TitleMatch]:
        """
        Extract potential titles from text.
        
        Args:
            text: Input text to extract titles from
            
        Returns:
            List of TitleMatch objects sorted by confidence
        """
        if not text or not text.strip():
            return []
        
        matches = []
        
        # Strategy 1: Explicit title line
        title_line_match = self._extract_title_line(text)
        if title_line_match:
            matches.append(title_line_match)
        
        # Strategy 2: Quoted text
        quoted_matches = self._extract_quoted_titles(text)
        matches.extend(quoted_matches)
        
        # Strategy 3: First line/sentence
        first_line_match = self._extract_first_line(text)
        if first_line_match:
            matches.append(first_line_match)
        
        # Strategy 4: Text before date/time
        before_date_match = self._extract_before_date(text)
        if before_date_match:
            matches.append(before_date_match)
        
        # Strategy 5: Structured event format
        structured_match = self._extract_structured_title(text)
        if structured_match:
            matches.append(structured_match)
        
        # Sort by confidence and remove duplicates
        matches = self._deduplicate_matches(matches)
        matches.sort(key=lambda x: x.confidence, reverse=True)
        
        return matches
    
    def _extract_title_line(self, text: str) -> Optional[TitleMatch]:
        """Extract title from explicit 'Title:' line."""
        match = self.patterns['title_line'].search(text)
        if match:
            title = match.group(1).strip()
            if title and not self._is_meta_prefix(title):
                return TitleMatch(
                    title=title,
                    confidence=0.95,
                    extraction_type='title_line',
                    start_pos=match.start(),
                    end_pos=match.end(),
                    matched_text=match.group(0)
                )
        return None
    
    def _extract_quoted_titles(self, text: str) -> List[TitleMatch]:
        """Extract titles from quoted text."""
        matches = []
        for match in self.patterns['quoted_title'].finditer(text):
            title = match.group(1).strip()
            if title and len(title) > 2:  # Minimum length check
                matches.append(TitleMatch(
                    title=title,
                    confidence=0.8,
                    extraction_type='quoted_text',
                    start_pos=match.start(),
                    end_pos=match.end(),
                    matched_text=match.group(0)
                ))
        return matches
    
    def _extract_first_line(self, text: str) -> Optional[TitleMatch]:
        """Extract title from first line of text."""
        match = self.patterns['first_line'].search(text)
        if match:
            title = match.group(1).strip()
            if title and not self._is_meta_prefix(title) and len(title) <= 100:
                confidence = 0.6 if len(title) <= 50 else 0.4
                return TitleMatch(
                    title=title,
                    confidence=confidence,
                    extraction_type='first_line',
                    start_pos=match.start(),
                    end_pos=match.end(),
                    matched_text=match.group(0)
                )
        return None
    
    def _extract_before_date(self, text: str) -> Optional[TitleMatch]:
        """Extract title from text before date/time indicators."""
        match = self.patterns['before_date'].search(text)
        if match:
            title = match.group(1).strip()
            if title and not self._is_meta_prefix(title):
                return TitleMatch(
                    title=title,
                    confidence=0.7,
                    extraction_type='before_date',
                    start_pos=match.start(),
                    end_pos=match.end(1),
                    matched_text=match.group(1)
                )
        return None
    
    def _extract_structured_title(self, text: str) -> Optional[TitleMatch]:
        """Extract title from structured event format."""
        match = self.patterns['structured_event'].search(text)
        if match:
            title = match.group(1).strip()
            if title and not self._is_meta_prefix(title):
                return TitleMatch(
                    title=title,
                    confidence=0.85,
                    extraction_type='structured_event',
                    start_pos=match.start(),
                    end_pos=match.end(1),
                    matched_text=match.group(1)
                )
        return None
    
    def _is_meta_prefix(self, text: str) -> bool:
        """Check if text starts with metadata prefixes."""
        text_lower = text.lower()
        return any(text_lower.startswith(prefix) for prefix in _META_PREFIXES)
    
    def _deduplicate_matches(self, matches: List[TitleMatch]) -> List[TitleMatch]:
        """Remove duplicate matches based on title content."""
        seen_titles = set()
        unique_matches = []
        
        for match in matches:
            title_normalized = match.title.lower().strip()
            if title_normalized not in seen_titles:
                seen_titles.add(title_normalized)
                unique_matches.append(match)
        
        return unique_matches
    
    def get_best_title(self, text: str) -> Optional[str]:
        """
        Get the best title from text.
        
        Args:
            text: Input text to extract title from
            
        Returns:
            Best title string or None if no good title found
        """
        matches = self.extract_title(text)
        if matches and matches[0].confidence >= 0.5:
            return matches[0].title
        return None