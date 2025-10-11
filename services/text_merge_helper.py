"""
Python equivalent of the Android TextMergeHelper with LLM enhancement integration.
Handles text preprocessing, clipboard merging, and smart text enhancement for better parsing.
"""

import re
import logging
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass

from models.event_models import ParsedEvent

# Lazy import to avoid loading heavy ML dependencies at startup

_llm_text_enhancer = None
_TextEnhancement = None

logger = logging.getLogger(**name**)

def _get_llm_text_enhancer():
""" Lazily import and initialize LLM text enhancer to avoid heavy ML dependencies at startup."""
global _llm_text_enhancer, _TextEnhancement

```
if _llm_text_enhancer is None:
    try:
        from services.llm_text_enhancer import LLMTextEnhancer, TextEnhancement
        _llm_text_enhancer = LLMTextEnhancer(provider="auto")
        _TextEnhancement = TextEnhancement
        logger.info("LLM text enhancer loaded successfully")
    except ImportError as e:
        logger.warning(f"LLM text enhancer not available: {e}")
        _llm_text_enhancer = None
        _TextEnhancement = None
    except Exception as e:
        logger.warning(f"Failed to initialize LLM text enhancer: {e}")
        _llm_text_enhancer = None
        _TextEnhancement = None

return _llm_text_enhancer, _TextEnhancement
```

@dataclass
class MergeResult:
“”“Result of text merging and enhancement.”””
final_text: str
confidence: float
merge_applied: bool
enhancement_applied: bool
original_text: str
clipboard_text: Optional[str]
metadata: Dict[str, Any]

class TextMergeHelper:
"""
Python text merge helper that provides:
1. Smart clipboard merging for fragmented Gmail selections
2. LLM-based text enhancement for better parsing
3. Context detection to prevent bad merges
4. Safer defaults for incomplete information
"""

```
def __init__(self, use_llm: bool = True):
    """
    Initialize the text merge helper.
    
    Args:
        use_llm: Whether to use LLM enhancement (requires OpenAI API key)
    """
    self.use_llm = use_llm
    self.llm_enhancer = None  # Will be lazily loaded when needed
    
    # Configuration
    self.config = {
        'max_clipboard_merge_distance': 200,  # Max chars between related content
        'min_confidence_for_merge': 0.6,      # Min confidence to apply merge
        'enable_context_detection': True,      # Prevent unrelated merges
        'enable_safer_defaults': True,         # Apply safer defaults for incomplete info
        'max_text_length': 5000               # Max total text length to process
    }

def enhance_text_for_parsing(self, text: str, clipboard_text: Optional[str] = None) -> MergeResult:
    """
    Main method to enhance text for parsing using merge and LLM enhancement.
    
    Args:
        text: Primary text (e.g., Gmail selection)
        clipboard_text: Optional clipboard content for merging
        
    Returns:
        MergeResult with enhanced text and metadata
    """
    original_text = text
    merge_applied = False
    enhancement_applied = False
    final_confidence = 0.5
    metadata = {}
    
    try:
        # Step 1: Attempt clipboard merge if provided
        if clipboard_text and self._should_merge_with_clipboard(text, clipboard_text):
            text = self._merge_with_clipboard(text, clipboard_text)
            merge_applied = True
            metadata['merge_strategy'] = 'clipboard_merge'
            logger.info("Applied clipboard merge")
        
        # Step 2: Apply LLM enhancement if available
        if self.use_llm:
            # Lazy load the LLM enhancer
            if self.llm_enhancer is None:
                llm_enhancer, TextEnhancement = _get_llm_text_enhancer()
                self.llm_enhancer = llm_enhancer
            
            if self.llm_enhancer and self.llm_enhancer.is_available():
                context = "gmail_selection" if merge_applied else "single_text"
                enhancement = self.llm_enhancer.enhance_text_for_parsing(text, context)
            
                # Use enhanced text if confidence is good
                if enhancement.confidence > 0.6:
                    text = enhancement.enhanced_text
                    enhancement_applied = True
                    final_confidence = enhancement.confidence
                    metadata.update({
                        'llm_enhancement': True,
                        'enhancement_type': enhancement.enhancement_type,
                        'detected_patterns': enhancement.detected_patterns,
                        'llm_metadata': enhancement.metadata
                    })
                    logger.info(f"Applied LLM enhancement: {enhancement.enhancement_type}")
            else:
                # LLM not available, skip enhancement
                pass
            else:
                # LLM enhancer not available
                metadata['llm_enhancement_skipped'] = 'LLM enhancer not available'
        else:
            # LLM not enabled
            metadata['llm_enhancement_skipped'] = 'LLM not enabled'
        
        # Step 3: Apply basic preprocessing if no LLM enhancement
        if not enhancement_applied:
            text = self._apply_basic_preprocessing(text)
            metadata['basic_preprocessing'] = True
        
        return MergeResult(
            final_text=text,
            confidence=final_confidence,
            merge_applied=merge_applied,
            enhancement_applied=enhancement_applied,
            original_text=original_text,
            clipboard_text=clipboard_text,
            metadata=metadata
        )
        
    except Exception as e:
        logger.error(f"Text enhancement failed: {e}")
        # Return original text on error
        return MergeResult(
            final_text=original_text,
            confidence=0.3,
            merge_applied=False,
            enhancement_applied=False,
            original_text=original_text,
            clipboard_text=clipboard_text,
            metadata={'error': str(e)}
        )

def apply_safer_defaults(self, parsed_event: ParsedEvent, enhanced_text: str) -> ParsedEvent:
    """
    Apply safer defaults for incomplete parsing results.
    
    Args:
        parsed_event: Original parsed event
        enhanced_text: The enhanced text that was parsed
        
    Returns:
        ParsedEvent with safer defaults applied
    """
    if not self.config['enable_safer_defaults']:
        return parsed_event
    
    # Apply safer defaults for weekday-only events
    if (not parsed_event.start_datetime and 
        self._contains_weekday_only(enhanced_text)):
        
        # This would set default time (9:00-10:00 AM next occurrence of weekday)
        # Implementation would depend on the specific requirements
        logger.info("Would apply safer defaults for weekday-only event")
        # For now, just log - actual implementation would set default times
    
    return parsed_event

def _should_merge_with_clipboard(self, text: str, clipboard_text: str) -> bool:
    """
    Determine if clipboard content should be merged with the main text.
    
    Args:
        text: Main text
        clipboard_text: Clipboard content
        
    Returns:
        True if merge should be applied
    """
    if not self.config['enable_context_detection']:
        return True
    
    # Don't merge if either text is too long
    if len(text) + len(clipboard_text) > self.config['max_text_length']:
        return False
    
    # Don't merge if clipboard is much longer than main text (likely unrelated)
    if len(clipboard_text) > len(text) * 3:
        return False
    
    # Check for complementary content
    return self._detect_complementary_content(text, clipboard_text)

def _detect_complementary_content(self, text1: str, text2: str) -> bool:
    """
    Detect if two pieces of text are complementary (should be merged).
    
    Args:
        text1: First text
        text2: Second text
        
    Returns:
        True if texts appear to be complementary
    """
    # Convert to lowercase for comparison
    t1_lower = text1.lower()
    t2_lower = text2.lower()
    
    # Check for complementary patterns
    complementary_indicators = [
        # One has event name, other has time/date
        (self._has_event_indicators(t1_lower) and self._has_time_indicators(t2_lower)),
        (self._has_time_indicators(t1_lower) and self._has_event_indicators(t2_lower)),
        
        # One has location, other has event details
        (self._has_location_indicators(t1_lower) and self._has_event_indicators(t2_lower)),
        (self._has_event_indicators(t1_lower) and self._has_location_indicators(t2_lower)),
        
        # Sequential content (common with Gmail partial selections)
        self._appears_sequential(text1, text2)
    ]
    
    return any(complementary_indicators)

def _has_event_indicators(self, text: str) -> bool:
    """Check if text contains event-related keywords."""
    event_keywords = [
        'meeting', 'call', 'appointment', 'lunch', 'dinner', 'conference',
        'presentation', 'training', 'workshop', 'event', 'gathering',
        'assembly', 'class', 'lesson', 'session'
    ]
    return any(keyword in text for keyword in event_keywords)

def _has_time_indicators(self, text: str) -> bool:
    """Check if text contains time-related information."""
    time_patterns = [
        r'\d{1,2}:\d{2}',  # 10:30
        r'\d{1,2}\s*(?:am|pm)',  # 10 am
        r'\b(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b',
        r'\b(?:today|tomorrow|yesterday)\b',
        r'\b(?:morning|afternoon|evening|night)\b'
    ]
    return any(re.search(pattern, text, re.IGNORECASE) for pattern in time_patterns)

def _has_location_indicators(self, text: str) -> bool:
    """Check if text contains location-related information."""
    location_keywords = ['at', 'in', 'room', 'building', 'office', 'address', 'location']
    return any(f' {keyword} ' in f' {text} ' for keyword in location_keywords)

def _appears_sequential(self, text1: str, text2: str) -> bool:
    """Check if texts appear to be sequential parts of the same content."""
    # Simple heuristic: check if one ends where the other might begin
    # This is a simplified version - could be more sophisticated
    
    # Check for sentence continuation patterns
    if text1.rstrip().endswith(('.', '!', '?')):
        return False  # First text ends complete sentence
    
    # Check if second text starts with lowercase (continuation)
    if text2.strip() and text2.strip()[0].islower():
        return True
    
    # Check for common continuation words
    continuation_words = ['and', 'but', 'or', 'so', 'then', 'also', 'we will', 'at']
    text2_start = text2.strip().lower()
    return any(text2_start.startswith(word) for word in continuation_words)

def _merge_with_clipboard(self, text: str, clipboard_text: str) -> str:
    """
    Merge text with clipboard content.
    
    Args:
        text: Main text
        clipboard_text: Clipboard content
        
    Returns:
        Merged text
    """
    # Simple merge strategy - could be more sophisticated
    # Add clipboard content after main text with newline separator
    return f"{text.strip()}\n{clipboard_text.strip()}"

def _apply_basic_preprocessing(self, text: str) -> str:
    """
    Apply basic preprocessing when LLM enhancement is not available.
    
    Args:
        text: Text to preprocess
        
    Returns:
        Preprocessed text
    """
    # Basic improvements without LLM
    lines = text.split('\n')
    processed_lines = []
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # Basic school event pattern restructuring
        # "On Monday the elementary students will attend the Indigenous Legacy Gathering"
        # -> "Indigenous Legacy Gathering on Monday for elementary students"
        school_pattern = r'On\s+(\w+)\s+the\s+(\w+)\s+students\s+will\s+(\w+)\s+(.+)'
        match = re.search(school_pattern, line, re.IGNORECASE)
        if match:
            day, grade, action, event = match.groups()
            line = f"{event.strip()} on {day} for {grade} students"
        
        processed_lines.append(line)
    
    return '\n'.join(processed_lines)

def _contains_weekday_only(self, text: str) -> bool:
    """Check if text contains only weekday information without specific time."""
    weekdays = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
    text_lower = text.lower()
    
    has_weekday = any(day in text_lower for day in weekdays)
    has_specific_time = bool(re.search(r'\d{1,2}:\d{2}|\d{1,2}\s*(?:am|pm)', text_lower))
    
    return has_weekday and not has_specific_time

def set_config(self, **kwargs):
    """Update configuration."""
    self.config.update(kwargs)

def get_config(self) -> Dict[str, Any]:
    """Get current configuration."""
    return self.config.copy()
```