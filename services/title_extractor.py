"""
TitleExtractor for label-based or fallback titles.
Implements regex-based title extraction for the hybrid parsing pipeline (Task 26.2).
"""

import re
from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass
from models.event_models import TitleResult

# Strict Title: line match + meta prefixes
_TITLE_LINE = re.compile(r'(?mi)^\s*title\s*:\s*(.+?)\s*$', re.IGNORECASE)
_META_PREFIXES = tuple(s.lower() for s in ["item id:", "due date:", "deadline:", "date:"])


class TitleExtractor:
    """
    Regex-based title extraction for the hybrid parsing pipeline.
    """

    def __init__(self):
        self._compile_patterns()

    def _compile_patterns(self):
        self.explicit_label_patterns = {
            'title_colon': re.compile(
                r'\btitle\s*:\s*([A-Za-z0-9\s!?.,\-]+?)(?:\s*(?:due\s+date|date|time|location|when|where|at|on|in)\s*[:]\s*|\s+(?:due|on|at|in|from|to)\s+|$)',
                re.IGNORECASE
            ),
            'event_name': re.compile(
                r'\b(?:event\s+name|meeting\s+name|appointment\s+name)\s*:\s*([A-Za-z0-9\s!?.,\-]+?)(?:\s*(?:due\s+date|date|time|location|when|where|at|on|in)\s*[:]\s*|\s+(?:due|on|at|in|from|to)\s+|$)',
                re.IGNORECASE
            ),
            'subject_line': re.compile(
                r'\bsubject\s*:\s*([A-Za-z0-9\s!?.,\-]+?)(?:\s*(?:due\s+date|date|time|location|when|where|at|on|in)\s*[:]\s*|\s+(?:due|on|at|in|from|to)\s+|$)',
                re.IGNORECASE
            ),
            'agenda_item': re.compile(
                r'\b(?:agenda|item)\s*:\s*([A-Za-z0-9\s!?.,\-]+?)(?:\s*(?:due\s+date|date|time|location|when|where|at|on|in)\s*[:]\s*|\s+(?:due|on|at|in|from|to)\s+|$)',
                re.IGNORECASE
            )
        }

        self.quoted_patterns = {
            'double_quotes': re.compile(r'"([^"]{3,50})"'),
            'single_quotes': re.compile(r"'([^']{3,50})'")
        }

        self.action_patterns = {
            'meeting_with': re.compile(r'\b(?:meeting|meet)\s+with\s+([^,\n\r\.]+)', re.IGNORECASE),
            'lunch_with': re.compile(r'\b(?:lunch|dinner|breakfast)\s+with\s+([^,\n\r\.]+)', re.IGNORECASE),
            'call_with': re.compile(r'\b(?:call|phone\s+call|video\s+call)\s+with\s+([^,\n\r\.]+)', re.IGNORECASE),
            'appointment_with': re.compile(
                r'\b(?:appointment|visit)\s+with\s+([^,\n\r\.]+?)(?:\s+(?:DATE|TIME|LOCATION|WHEN|WHERE|AT)\s|[,\n\r\.]|$)',
                re.IGNORECASE
            ),
            'interview_with': re.compile(r'\b(?:interview)\s+(?:with\s+)?([^,\n\r\.]+)', re.IGNORECASE)
        }

        self.event_type_patterns = {
            'structured_event': re.compile(r'^([^,\n\r\.]+?)(?:\s+(?:DATE|TIME|LOCATION|WHEN|WHERE|AT)\s)', re.IGNORECASE),
            'party_celebration': re.compile(
                r'\b([^,\n\r\.]*(?:party|celebration|birthday|anniversary|wedding)[^,\n\r\.]*?)(?:\s+(?:DATE|TIME|LOCATION|WHEN|WHERE|AT)\s|[,\n\r\.]|$)',
                re.IGNORECASE
            ),
            'conference': re.compile(r'\b([^,\n\r\.]*(?:conference|summit|workshop|seminar|webinar)[^,\n\r\.]*)', re.IGNORECASE),
            'class_course': re.compile(r'\b([^,\n\r\.]*(?:class|course|lesson|training|tutorial)[^,\n\r\.]*)', re.IGNORECASE),
            'medical': re.compile(r'\b([^,\n\r\.]*(?:doctor|dentist|appointment|checkup|surgery)[^,\n\r\.]*)', re.IGNORECASE),
            'travel': re.compile(r'\b([^,\n\r\.]*(?:flight|trip|vacation|travel|departure|arrival)[^,\n\r\.]*)', re.IGNORECASE)
        }

        self.context_patterns = {
            'going_to': re.compile(r'\b(?:going\s+to|attending)\s+([^,\n\r\.]+)', re.IGNORECASE),
            'scheduled_for': re.compile(r'\b(?:scheduled\s+for|planned\s+for)\s+([^,\n\r\.]+)', re.IGNORECASE),
            'reminder_about': re.compile(r'\b(?:reminder\s+about|reminder\s+for|reminder\s+that)\s+([^,\n\r\.]+)', re.IGNORECASE),
            'structured_event_title': re.compile(r'^([^A-Z\n\r]+?)(?:\s+(?:DATE|TIME|LOCATION|WHEN|WHERE)\s)', re.IGNORECASE)
        }

        self.sentence_patterns = {
            'first_sentence': re.compile(r'^([^\.!?\n\r]{10,80})[\.\!?\n\r]', re.MULTILINE),
            'imperative_sentence': re.compile(r'\b((?:don\'t\s+forget|remember\s+to|need\s+to|have\s+to)\s+[^,\n\r\.]{5,50})', re.IGNORECASE)
        }

        self.noise_words = {
            'filler_words': ['the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'],
            'time_words': ['today', 'tomorrow', 'yesterday', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday'],
            'meta_words': ['reminder', 'notification', 'alert', 'message', 'email', 'text', 'note']
        }

        self.title_prefixes = [
            r'^(?:re\s*:\s*|fwd\s*:\s*|fw\s*:\s*)',
            r'^(?:reminder\s*:\s*|alert\s*:\s*)',
            r'^(?:meeting\s*:\s*|event\s*:\s*)',
            r'^(?:subject\s*:\s*|title\s*:\s*)'
        ]

    # ---------------- new helpers ----------------

    def _extract_title_line_first(self, text: str) -> Optional[str]:
        """Fast path: exact 'Title:' line match."""
        m = _TITLE_LINE.search(text or "")
        if not m:
            return None
        return m.group(1).strip()

    def _first_non_meta_line(self, text: str) -> Optional[str]:
        """Fallback: first non-empty, non-meta line."""
        for line in (text or "").splitlines():
            s = line.strip()
            if not s:
                continue
            if s.lower().startswith(_META_PREFIXES):
                continue
            if re.fullmatch(r'(?i)(date|time|location|when|where)\s*:?.*', s):
                continue
            return s
        return None

    # ---------------- main extraction ----------------

    def extract_title(self, text: str) -> TitleResult:
        if not text or not text.strip():
            return TitleResult.empty(raw_text=text)
        text = text.strip()

        # exact Title: line
        line_title = self._extract_title_line_first(text)
        if line_title:
            cleaned = self._clean_title(line_title)
            if cleaned:
                return TitleResult(
                    title=cleaned,
                    confidence=0.98,
                    generation_method="explicit",
                    raw_text=line_title,
                    quality_score=self._calculate_title_quality(cleaned),
                    extraction_metadata={'pattern_type': 'title_line'}
                )

        # --- existing hierarchy below ---

        explicit_result = self._extract_explicit_title(text)
        if explicit_result.confidence >= 0.8:
            return explicit_result

        quoted_result = self._extract_quoted_title(text)
        if quoted_result.confidence >= 0.7:
            return quoted_result

        action_result = self._extract_action_title(text)
        if action_result.confidence >= 0.7:
            return action_result

        event_type_result = self._extract_event_type_title(text)
        if event_type_result.confidence >= 0.6:
            return event_type_result

        context_result = self._extract_context_title(text)
        if context_result.confidence >= 0.5:
            return context_result

        sentence_result = self._extract_sentence_title(text)
        if sentence_result.confidence >= 0.4:
            return sentence_result

        # safe fallback: first non-meta line
        line = self._first_non_meta_line(text)
        if line:
            cleaned = self._clean_title(line)
            if cleaned:
                return TitleResult(
                    title=cleaned,
                    confidence=0.7,
                    generation_method="heuristic",
                    raw_text=line,
                    quality_score=self._calculate_title_quality(cleaned),
                    extraction_metadata={'pattern_type': 'first_non_meta_line'}
                )

        # final fallback
        return self._generate_fallback_title(text)

    # ---------------- internal helpers ----------------
    # (keep your existing _extract_explicit_title, _extract_quoted_title, etc.)

    # only show changed clean_title block
    def _clean_title(self, title: str) -> Optional[str]:
        if not title:
            return None

        cleaned = title
        for prefix_pattern in self.title_prefixes:
            cleaned = re.sub(prefix_pattern, '', cleaned, flags=re.IGNORECASE)

        cleaned = re.sub(r'\s+', ' ', cleaned)
        cleaned = cleaned.strip(' \t\n\r.,;:')
        cleaned = re.sub(r'\[.*?\]', '', cleaned)
        cleaned = re.sub(r'\(.*?\)', '', cleaned)

        # preserve acronyms / mixed case
        if cleaned and len(cleaned) > 1:
            if len(cleaned) <= 8 and cleaned.isupper():
                pass
            elif re.search(r'[!@#$%^&*()_+\-=\[\]{};:\'",.<>/?]|[\u2190-\u21FF\u2600-\u27BF]', cleaned):
                pass
            elif cleaned[0].isupper() and any(c.islower() for c in cleaned[1:]):
                pass
            else:
                words = cleaned.split()
                cleaned = ' '.join(w if w.isupper() else w.capitalize() for w in words)

        if cleaned and 3 <= len(cleaned) <= 100:
            return cleaned
        return None