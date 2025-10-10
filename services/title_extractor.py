"""
TitleExtractor for label-based or fallback titles.
Implements regex-based title extraction for the hybrid parsing pipeline (Task 26.2).
"""

import re
from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass
from models.event_models import TitleResult


class TitleExtractor:
    """
    Regex-based title extraction for the hybrid parsing pipeline.
    
    Handles:
    - Explicit titles (Title:, Event:, Subject:)
    - Heuristic-based title extraction from sentence structure
    - Fallback title generation from context clues
    - Title quality scoring and validation
    - Cleaning and normalizing extracted titles
    
    Works as a fallback when LLM title generation fails or needs enhancement.
    """
    
    def __init__(self):
        """Initialize the title extractor with compiled patterns."""
        self._compile_patterns()
    
    def _compile_patterns(self):
        """Compile regex patterns for title extraction."""
        
        # Explicit title label patterns (highest confidence)
        # More generalized patterns that stop at common field separators
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
        
        # Quoted title patterns
        self.quoted_patterns = {
            'double_quotes': re.compile(
                r'"([^"]{3,50})"'
            ),
            'single_quotes': re.compile(
                r"'([^']{3,50})'"
            )
        }
        
        # Action-based patterns (meeting with, lunch with, etc.)
        self.action_patterns = {
            'meeting_with': re.compile(
                r'\b(?:meeting|meet)\s+with\s+([^,\n\r\.]+)',
                re.IGNORECASE
            ),
            'lunch_with': re.compile(
                r'\b(?:lunch|dinner|breakfast)\s+with\s+([^,\n\r\.]+)',
                re.IGNORECASE
            ),
            'call_with': re.compile(
                r'\b(?:call|phone\s+call|video\s+call)\s+with\s+([^,\n\r\.]+)',
                re.IGNORECASE
            ),
            'appointment_with': re.compile(
                r'\b(?:appointment|visit)\s+with\s+([^,\n\r\.]+?)(?:\s+(?:DATE|TIME|LOCATION|WHEN|WHERE|AT)\s|[,\n\r\.]|$)',
                re.IGNORECASE
            ),
            'interview_with': re.compile(
                r'\b(?:interview)\s+(?:with\s+)?([^,\n\r\.]+)',
                re.IGNORECASE
            )
        }
        
        # Event type patterns (ordered by priority - structured_event first)
        self.event_type_patterns = {
            # Highest priority: structured event text (like event pages)
            'structured_event': re.compile(
                r'^([^,\n\r\.]+?)(?:\s+(?:DATE|TIME|LOCATION|WHEN|WHERE|AT)\s)',
                re.IGNORECASE
            ),
            'party_celebration': re.compile(
                r'\b([^,\n\r\.]*(?:party|celebration|birthday|anniversary|wedding)[^,\n\r\.]*?)(?:\s+(?:DATE|TIME|LOCATION|WHEN|WHERE|AT)\s|[,\n\r\.]|$)',
                re.IGNORECASE
            ),
            'conference': re.compile(
                r'\b([^,\n\r\.]*(?:conference|summit|workshop|seminar|webinar)[^,\n\r\.]*)',
                re.IGNORECASE
            ),
            'class_course': re.compile(
                r'\b([^,\n\r\.]*(?:class|course|lesson|training|tutorial)[^,\n\r\.]*)',
                re.IGNORECASE
            ),
            'medical': re.compile(
                r'\b([^,\n\r\.]*(?:doctor|dentist|appointment|checkup|surgery)[^,\n\r\.]*)',
                re.IGNORECASE
            ),
            'travel': re.compile(
                r'\b([^,\n\r\.]*(?:flight|trip|vacation|travel|departure|arrival)[^,\n\r\.]*)',
                re.IGNORECASE
            )
        }
        
        # Context clue patterns for title derivation
        self.context_patterns = {
            'going_to': re.compile(
                r'\b(?:going\s+to|attending)\s+([^,\n\r\.]+)',
                re.IGNORECASE
            ),
            'scheduled_for': re.compile(
                r'\b(?:scheduled\s+for|planned\s+for)\s+([^,\n\r\.]+)',
                re.IGNORECASE
            ),
            'reminder_about': re.compile(
                r'\b(?:reminder\s+about|reminder\s+for|reminder\s+that)\s+([^,\n\r\.]+)',
                re.IGNORECASE
            ),
            # Pattern for structured event text (title before DATE/LOCATION/TIME)
            'structured_event_title': re.compile(
                r'^([^A-Z\n\r]+?)(?:\s+(?:DATE|TIME|LOCATION|WHEN|WHERE)\s)',
                re.IGNORECASE
            )
        }
        
        # Sentence structure patterns (first sentence as title)
        self.sentence_patterns = {
            'first_sentence': re.compile(
                r'^([^\.!?\n\r]{10,80})[\.\!?\n\r]',
                re.MULTILINE
            ),
            'imperative_sentence': re.compile(
                r'\b((?:don\'t\s+forget|remember\s+to|need\s+to|have\s+to)\s+[^,\n\r\.]{5,50})',
                re.IGNORECASE
            )
        }
        
        # Noise words to filter out
        self.noise_words = {
            'filler_words': ['the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'],
            'time_words': ['today', 'tomorrow', 'yesterday', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday'],
            'meta_words': ['reminder', 'notification', 'alert', 'message', 'email', 'text', 'note']
        }
        
        # Common title prefixes to clean
        self.title_prefixes = [
            r'^(?:re\s*:\s*|fwd\s*:\s*|fw\s*:\s*)',
            r'^(?:reminder\s*:\s*|alert\s*:\s*)',
            r'^(?:meeting\s*:\s*|event\s*:\s*)',
            r'^(?:subject\s*:\s*|title\s*:\s*)'
        ]
    
    def extract_title(self, text: str) -> TitleResult:
        """
        Extract title from text using regex patterns and heuristics.
        
        Args:
            text: Input text to extract title from
            
        Returns:
            TitleResult with extracted title and confidence score
        """
        if not text or not text.strip():
            return TitleResult.empty(raw_text=text)
        
        text = text.strip()
        
        # Try explicit label patterns first (highest confidence)
        explicit_result = self._extract_explicit_title(text)
        if explicit_result.confidence >= 0.8:
            return explicit_result
        
        # Try quoted titles
        quoted_result = self._extract_quoted_title(text)
        if quoted_result.confidence >= 0.7:
            return quoted_result
        
        # Try action-based patterns
        action_result = self._extract_action_title(text)
        if action_result.confidence >= 0.7:
            return action_result
        
        # Try event type patterns
        event_type_result = self._extract_event_type_title(text)
        if event_type_result.confidence >= 0.6:
            return event_type_result
        
        # Try context clue patterns
        context_result = self._extract_context_title(text)
        if context_result.confidence >= 0.5:
            return context_result
        
        # Try sentence structure patterns
        sentence_result = self._extract_sentence_title(text)
        if sentence_result.confidence >= 0.4:
            return sentence_result
        
        # Generate fallback title from available context
        fallback_result = self._generate_fallback_title(text)
        return fallback_result
    
    def _extract_explicit_title(self, text: str) -> TitleResult:
        """Extract titles from explicit label patterns."""
        for pattern_name, pattern in self.explicit_label_patterns.items():
            match = pattern.search(text)
            if match:
                title = match.group(1).strip()
                if title and len(title) >= 3:
                    cleaned_title = self._clean_title(title)
                    if cleaned_title:
                        return TitleResult(
                            title=cleaned_title,
                            confidence=0.95,
                            generation_method="explicit",
                            raw_text=match.group(0),
                            quality_score=self._calculate_title_quality(cleaned_title),
                            extraction_metadata={
                                'pattern_type': pattern_name,
                                'original_title': title
                            }
                        )
        
        return TitleResult(confidence=0.0)
    
    def _extract_quoted_title(self, text: str) -> TitleResult:
        """Extract titles from quoted text."""
        for pattern_name, pattern in self.quoted_patterns.items():
            matches = pattern.findall(text)
            if matches:
                # Use the longest quoted text as title
                best_title = max(matches, key=len)
                if len(best_title) >= 5:
                    cleaned_title = self._clean_title(best_title)
                    if cleaned_title:
                        return TitleResult(
                            title=cleaned_title,
                            confidence=0.8,
                            generation_method="explicit",
                            raw_text=f'"{best_title}"' if pattern_name == 'double_quotes' else f"'{best_title}'",
                            quality_score=self._calculate_title_quality(cleaned_title),
                            extraction_metadata={
                                'pattern_type': pattern_name,
                                'quote_type': 'double' if pattern_name == 'double_quotes' else 'single'
                            }
                        )
        
        return TitleResult(confidence=0.0)
    
    def _extract_action_title(self, text: str) -> TitleResult:
        """Extract titles from action-based patterns."""
        for pattern_name, pattern in self.action_patterns.items():
            match = pattern.search(text)
            if match:
                action_part = match.group(1).strip()
                if action_part and len(action_part) >= 2:
                    # Generate title based on action type
                    if 'meeting' in pattern_name:
                        title = f"Meeting with {action_part}"
                    elif 'lunch' in pattern_name:
                        meal_type = pattern_name.split('_')[0].capitalize()
                        title = f"{meal_type} with {action_part}"
                    elif 'call' in pattern_name:
                        title = f"Call with {action_part}"
                    elif 'appointment' in pattern_name:
                        title = f"Appointment with {action_part}"
                    elif 'interview' in pattern_name:
                        title = f"Interview with {action_part}"
                    else:
                        title = action_part
                    
                    cleaned_title = self._clean_title(title)
                    if cleaned_title:
                        return TitleResult(
                            title=cleaned_title,
                            confidence=0.75,
                            generation_method="action_based",
                            raw_text=match.group(0),
                            quality_score=self._calculate_title_quality(cleaned_title),
                            extraction_metadata={
                                'pattern_type': pattern_name,
                                'action_subject': action_part
                            }
                        )
        
        return TitleResult(confidence=0.0)
    
    def _extract_event_type_title(self, text: str) -> TitleResult:
        """Extract titles from event type patterns."""
        for pattern_name, pattern in self.event_type_patterns.items():
            match = pattern.search(text)
            if match:
                event_text = match.group(1).strip()
                if event_text and len(event_text) >= 5:
                    cleaned_title = self._clean_title(event_text)
                    if cleaned_title:
                        return TitleResult(
                            title=cleaned_title,
                            confidence=0.7,
                            generation_method="derived",
                            raw_text=match.group(0),
                            quality_score=self._calculate_title_quality(cleaned_title),
                            extraction_metadata={
                                'pattern_type': pattern_name,
                                'event_category': pattern_name
                            }
                        )
        
        return TitleResult(confidence=0.0)
    
    def _extract_context_title(self, text: str) -> TitleResult:
        """Extract titles from context clue patterns."""
        for pattern_name, pattern in self.context_patterns.items():
            match = pattern.search(text)
            if match:
                context_text = match.group(1).strip()
                if context_text and len(context_text) >= 3:
                    cleaned_title = self._clean_title(context_text)
                    if cleaned_title:
                        return TitleResult(
                            title=cleaned_title,
                            confidence=0.6,
                            generation_method="context_derived",
                            raw_text=match.group(0),
                            quality_score=self._calculate_title_quality(cleaned_title),
                            extraction_metadata={
                                'pattern_type': pattern_name,
                                'context_clue': pattern_name
                            }
                        )
        
        return TitleResult(confidence=0.0)
    
    def _extract_sentence_title(self, text: str) -> TitleResult:
        """Extract titles from sentence structure patterns."""
        for pattern_name, pattern in self.sentence_patterns.items():
            match = pattern.search(text)
            if match:
                sentence = match.group(1).strip()
                if sentence and len(sentence) >= 10:
                    cleaned_title = self._clean_title(sentence)
                    if cleaned_title and not self._is_noise_sentence(cleaned_title):
                        return TitleResult(
                            title=cleaned_title,
                            confidence=0.5,
                            generation_method="derived",
                            raw_text=match.group(0),
                            quality_score=self._calculate_title_quality(cleaned_title),
                            extraction_metadata={
                                'pattern_type': pattern_name,
                                'extraction_method': 'sentence_structure'
                            }
                        )
        
        return TitleResult(confidence=0.0)
    
    def _generate_fallback_title(self, text: str) -> TitleResult:
        """Generate a fallback title when no patterns match."""
        # Try to extract meaningful words
        words = re.findall(r'\b[A-Za-z]{3,}\b', text)
        
        # Filter out noise words
        meaningful_words = []
        for word in words:
            if (word.lower() not in self.noise_words['filler_words'] and
                word.lower() not in self.noise_words['time_words'] and
                word.lower() not in self.noise_words['meta_words']):
                meaningful_words.append(word)
        
        if meaningful_words:
            # Take first 3-5 meaningful words
            title_words = meaningful_words[:5]
            fallback_title = ' '.join(title_words)
            
            if len(fallback_title) >= 5:
                return TitleResult(
                    title=fallback_title,
                    confidence=0.3,
                    generation_method="generated",
                    raw_text=text[:50] + "..." if len(text) > 50 else text,
                    quality_score=self._calculate_title_quality(fallback_title),
                    extraction_metadata={
                        'pattern_type': 'fallback_keywords',
                        'word_count': len(title_words),
                        'source_words': title_words
                    }
                )
        
        # Last resort: use first few words of text
        first_words = text.split()[:4]
        if first_words:
            last_resort_title = ' '.join(first_words)
            return TitleResult(
                title=last_resort_title,
                confidence=0.2,
                generation_method="generated",
                raw_text=text[:30] + "..." if len(text) > 30 else text,
                quality_score=0.2,
                extraction_metadata={
                    'pattern_type': 'first_words_fallback',
                    'word_count': len(first_words)
                }
            )
        
        return TitleResult.empty(raw_text=text)
    
    def _clean_title(self, title: str) -> Optional[str]:
        """Clean and normalize a title string."""
        if not title:
            return None
        
        # Remove common prefixes
        cleaned = title
        for prefix_pattern in self.title_prefixes:
            cleaned = re.sub(prefix_pattern, '', cleaned, flags=re.IGNORECASE)
        
        # Clean up whitespace and punctuation
        cleaned = re.sub(r'\s+', ' ', cleaned)  # Normalize whitespace
        cleaned = cleaned.strip(' \t\n\r.,;:')  # Remove leading/trailing punctuation
        
        # Remove email-style formatting
        cleaned = re.sub(r'\[.*?\]', '', cleaned)  # Remove [brackets]
        cleaned = re.sub(r'\(.*?\)', '', cleaned)  # Remove (parentheses) if they contain metadata
        
        # Capitalize properly
        if cleaned and len(cleaned) > 1:
            # Don't change case if it's already properly capitalized
            if not (cleaned[0].isupper() and any(c.islower() for c in cleaned[1:])):
                cleaned = cleaned.title()
        
        # Final validation
        if cleaned and len(cleaned) >= 3 and len(cleaned) <= 100:
            return cleaned
        
        return None
    
    def _calculate_title_quality(self, title: str) -> float:
        """Calculate quality score for a title (0.0 to 1.0)."""
        if not title:
            return 0.0
        
        quality_factors = []
        
        # Length factor (prefer 10-50 characters)
        length = len(title)
        if 10 <= length <= 50:
            length_factor = 1.0
        elif length < 10:
            length_factor = length / 10.0
        else:
            length_factor = max(0.3, 50.0 / length)
        quality_factors.append(length_factor)
        
        # Word count factor (prefer 2-8 words)
        word_count = len(title.split())
        if 2 <= word_count <= 8:
            word_factor = 1.0
        elif word_count == 1:
            word_factor = 0.5
        else:
            word_factor = max(0.3, 8.0 / word_count)
        quality_factors.append(word_factor)
        
        # Completeness factor (avoid truncated phrases)
        completeness_factor = 1.0
        if (title.endswith('...') or title.endswith(' and') or 
            title.endswith(' or') or title.endswith(' with')):
            completeness_factor = 0.3
        quality_factors.append(completeness_factor)
        
        # Capitalization factor
        cap_factor = 1.0
        if title.isupper() or title.islower():
            cap_factor = 0.7  # Prefer proper capitalization
        quality_factors.append(cap_factor)
        
        # Content quality (avoid noise words as main content)
        content_words = [w for w in title.lower().split() 
                        if w not in self.noise_words['filler_words']]
        content_factor = min(1.0, len(content_words) / max(1, len(title.split())))
        quality_factors.append(content_factor)
        
        return sum(quality_factors) / len(quality_factors)
    
    def _is_noise_sentence(self, sentence: str) -> bool:
        """Check if a sentence is mostly noise/filler content."""
        words = sentence.lower().split()
        noise_count = sum(1 for word in words 
                         if word in self.noise_words['filler_words'] or 
                            word in self.noise_words['meta_words'])
        
        # If more than 60% of words are noise, consider it a noise sentence
        return noise_count / len(words) > 0.6 if words else True
    
    def enhance_title(self, title: str, context: str = "") -> TitleResult:
        """
        Enhance an existing title using context information.
        
        Args:
            title: Existing title to enhance
            context: Additional context text for enhancement
            
        Returns:
            Enhanced TitleResult
        """
        if not title:
            return self.extract_title(context) if context else TitleResult.empty()
        
        # Clean the existing title
        cleaned_title = self._clean_title(title)
        if not cleaned_title:
            return self.extract_title(context) if context else TitleResult.empty()
        
        # Calculate quality of existing title
        quality = self._calculate_title_quality(cleaned_title)
        
        # If title is already high quality, return it
        if quality >= 0.7:
            return TitleResult(
                title=cleaned_title,
                confidence=0.9,
                generation_method="enhanced",
                quality_score=quality,
                extraction_metadata={'enhancement_applied': False, 'original_quality': quality}
            )
        
        # Try to enhance with context
        if context:
            context_result = self.extract_title(context)
            if context_result.confidence > 0.5 and context_result.quality_score > quality:
                # Use context title as alternative
                enhanced_result = TitleResult(
                    title=cleaned_title,
                    confidence=min(0.8, context_result.confidence + 0.1),
                    generation_method="enhanced",
                    quality_score=max(quality, context_result.quality_score),
                    extraction_metadata={
                        'enhancement_applied': True,
                        'original_title': title,
                        'context_title': context_result.title,
                        'original_quality': quality,
                        'context_quality': context_result.quality_score
                    }
                )
                enhanced_result.add_alternative(context_result.title, context_result.confidence)
                return enhanced_result
        
        # Return cleaned original title
        return TitleResult(
            title=cleaned_title,
            confidence=0.6,
            generation_method="enhanced",
            quality_score=quality,
            extraction_metadata={'enhancement_applied': False, 'original_quality': quality}
        )