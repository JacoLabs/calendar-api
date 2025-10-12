import re
import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass

from models.event_models import ParsedEvent

_llm_text_enhancer = None
_TextEnhancement = None  # kept for potential external use, even if unused here

logger = logging.getLogger(__name__)


def _get_llm_text_enhancer():
    """
    Lazy-load the LLM text enhancer to avoid import costs unless needed.
    Returns (llm_enhancer_instance_or_None, TextEnhancement_type_or_None)
    """
    global _llm_text_enhancer, _TextEnhancement

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


@dataclass
class MergeResult:
    final_text: str
    confidence: float
    merge_applied: bool
    enhancement_applied: bool
    original_text: str
    clipboard_text: Optional[str]
    metadata: Dict[str, Any]


class TextMergeHelper:
    def __init__(self, use_llm: bool = True):
        self.use_llm = use_llm
        self.llm_enhancer = None

        self.config: Dict[str, Any] = {
            "max_clipboard_merge_distance": 200,
            "min_confidence_for_merge": 0.6,
            "enable_context_detection": True,
            "enable_safer_defaults": True,
            "max_text_length": 5000,
        }

    def enhance_text_for_parsing(
        self, text: str, clipboard_text: Optional[str] = None
    ) -> MergeResult:
        original_text = text
        merge_applied = False
        enhancement_applied = False
        final_confidence = 0.5
        metadata: Dict[str, Any] = {}

        try:
            # Optional clipboard merge
            if clipboard_text and self._should_merge_with_clipboard(text, clipboard_text):
                text = self._merge_with_clipboard(text, clipboard_text)
                merge_applied = True
                metadata["merge_strategy"] = "clipboard_merge"
                logger.info("Applied clipboard merge")

            # LLM enhancement (if enabled and available)
            if self.use_llm:
                if self.llm_enhancer is None:
                    llm_enhancer, _TextEnhancementType = _get_llm_text_enhancer()
                    self.llm_enhancer = llm_enhancer

                if self.llm_enhancer and getattr(self.llm_enhancer, "is_available", lambda: False)():
                    context = "gmail_selection" if merge_applied else "single_text"
                    enhancement = self.llm_enhancer.enhance_text_for_parsing(text, context)

                    if enhancement and getattr(enhancement, "confidence", 0) > 0.6:
                        text = enhancement.enhanced_text
                        enhancement_applied = True
                        final_confidence = enhancement.confidence
                        metadata.update(
                            {
                                "llm_enhancement": True,
                                "enhancement_type": getattr(enhancement, "enhancement_type", None),
                                "detected_patterns": getattr(enhancement, "detected_patterns", None),
                                "llm_metadata": getattr(enhancement, "metadata", None),
                            }
                        )
                        logger.info(
                            f"Applied LLM enhancement: {getattr(enhancement, 'enhancement_type', 'unknown')}"
                        )
                    else:
                        conf = getattr(enhancement, "confidence", None)
                        metadata["llm_enhancement_skipped"] = (
                            f"Low confidence: {conf}" if conf is not None else "No enhancement returned"
                        )
                else:
                    metadata["llm_enhancement_skipped"] = "LLM enhancer not available"
            else:
                metadata["llm_enhancement_skipped"] = "LLM not enabled"

            # Always run lightweight preprocessing if no LLM enhancement applied
            if not enhancement_applied:
                text = self._apply_basic_preprocessing(text)
                metadata["basic_preprocessing"] = True

            return MergeResult(
                final_text=text,
                confidence=final_confidence,
                merge_applied=merge_applied,
                enhancement_applied=enhancement_applied,
                original_text=original_text,
                clipboard_text=clipboard_text,
                metadata=metadata,
            )

        except Exception as e:
            logger.error(f"Text enhancement failed: {e}", exc_info=True)
            return MergeResult(
                final_text=original_text,
                confidence=0.3,
                merge_applied=False,
                enhancement_applied=False,
                original_text=original_text,
                clipboard_text=clipboard_text,
                metadata={"error": str(e)},
            )

    def apply_safer_defaults(self, parsed_event: ParsedEvent, enhanced_text: str) -> ParsedEvent:
        if not self.config["enable_safer_defaults"]:
            return parsed_event

        if (not getattr(parsed_event, "start_datetime", None)) and self._contains_weekday_only(enhanced_text):
            logger.info("Would apply safer defaults for weekday-only event")
            # Implement safer defaults mutation here if desired.

        return parsed_event

    def _should_merge_with_clipboard(self, text: str, clipboard_text: str) -> bool:
        if not self.config["enable_context_detection"]:
            return True

        if len(text) + len(clipboard_text) > self.config["max_text_length"]:
            return False

        if len(clipboard_text) > len(text) * 3:
            return False

        return self._detect_complementary_content(text, clipboard_text)

    def _detect_complementary_content(self, text1: str, text2: str) -> bool:
        t1_lower = text1.lower()
        t2_lower = text2.lower()

        complementary_indicators = [
            self._has_event_indicators(t1_lower) and self._has_time_indicators(t2_lower),
            self._has_time_indicators(t1_lower) and self._has_event_indicators(t2_lower),
            self._has_location_indicators(t1_lower) and self._has_event_indicators(t2_lower),
            self._has_event_indicators(t1_lower) and self._has_location_indicators(t2_lower),
            self._appears_sequential(text1, text2),
        ]

        return any(complementary_indicators)

    def _has_event_indicators(self, text: str) -> bool:
        event_keywords = [
            "meeting",
            "call",
            "appointment",
            "lunch",
            "dinner",
            "conference",
            "presentation",
            "training",
            "workshop",
            "event",
            "gathering",
            "assembly",
            "class",
            "lesson",
            "session",
        ]
        return any(keyword in text for keyword in event_keywords)

    def _has_time_indicators(self, text: str) -> bool:
        time_patterns = [
            r"\d{1,2}:\d{2}",
            r"\d{1,2}\s*(?:am|pm)",
            r"\b(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b",
            r"\b(?:today|tomorrow|yesterday)\b",
            r"\b(?:morning|afternoon|evening|night)\b",
        ]
        return any(re.search(pattern, text, re.IGNORECASE) for pattern in time_patterns)

    def _has_location_indicators(self, text: str) -> bool:
        location_keywords = ["at", "in", "room", "building", "office", "address", "location"]
        padded = f" {text} "
        return any(f" {kw} " in padded for kw in location_keywords)

    def _appears_sequential(self, text1: str, text2: str) -> bool:
        if text1.rstrip().endswith((".", "!", "?")):
            return False

        t2 = text2.strip()
        if t2 and t2[0].islower():
            return True

        continuation_words = ["and", "but", "or", "so", "then", "also", "we will", "at"]
        t2_start = t2.lower()
        return any(t2_start.startswith(word) for word in continuation_words)

    def _merge_with_clipboard(self, text: str, clipboard_text: str) -> str:
        return f"{text.strip()}\n{clipboard_text.strip()}"

    def _apply_basic_preprocessing(self, text: str) -> str:
        lines = text.split("\n")
        processed_lines = []

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Normalize specific school-style phrasing into a more parseable pattern.
            school_pattern = r"On\s+(\w+)\s+the\s+(\w+)\s+students\s+will\s+(\w+)\s+(.+)"
            match = re.search(school_pattern, line, re.IGNORECASE)
            if match:
                day, grade, action, event = match.groups()
                line = f"{event.strip()} on {day} for {grade} students"

            processed_lines.append(line)

        return "\n".join(processed_lines)

    def _contains_weekday_only(self, text: str) -> bool:
        weekdays = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        text_lower = text.lower()

        has_weekday = any(day in text_lower for day in weekdays)
        has_specific_time = bool(re.search(r"\d{1,2}:\d{2}|\d{1,2}\s*(?:am|pm)", text_lower))

        return has_weekday and not has_specific_time

    def set_config(self, **kwargs) -> None:
        self.config.update(kwargs)

    def get_config(self) -> Dict[str, Any]:
        return self.config.copy()