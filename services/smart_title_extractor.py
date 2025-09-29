"""
Smart title extraction service for intelligent event title generation and extraction.
Implements formal event name detection, action-based title generation, context-derived titles,
and quality assessment to create meaningful event titles from various text formats.

Enhanced as LLM Fallback Service to provide regex-based fallback when LLM fails,
validate LLM-generated titles, and handle user prompts for title completion.
"""

import re
import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from models.event_models import TitleResult

logger = logging.getLogger(__name__)


class SmartTitleExtractor:
    """
    Advanced service for extracting and generating intelligent event titles from natural language text.
    Supports formal event name detection, action-based generation, context-derived titles,
    truncated sentence completion, and quality assessment.
    
    Enhanced as LLM Fallback Service for regex-based fallback when LLM fails.
    """
    
    def __init__(self):
        self._compile_patterns()
    
    def _compile_patterns(self):
        """Compile regex patterns and keyword lists for intelligent title extraction."""
        
        # Formal event name patterns (proper nouns, capitalized phrases)
        self.formal_event_patterns = {
            'proper_noun_event': re.compile(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*(?:\s+(?:Gathering|Meeting|Conference|Summit|Workshop|Seminar|Training|Session|Event|Ceremony|Celebration|Festival|Fair|Expo|Convention|Symposium|Forum|Panel|Discussion|Presentation|Demo|Demonstration|Launch|Opening|Closing)))\b'),
            'quoted_formal': re.compile(r'["\']([^"\']{5,50})["\']'),
            'title_case_phrase': re.compile(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,5})\b(?=\s+(?:will|is|at|on|in|for|tomorrow|today|next|this))'),
            'event_with_descriptor': re.compile(r'\b((?:Annual|Monthly|Weekly|Daily|Special|Emergency|Urgent|Important|Final|Initial|First|Second|Third|Last)\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b'),
        }
        
        # Action-based patterns for generating titles from actions
        self.action_patterns = {
            'we_will': re.compile(r'\bwe\s+will\s+([^.!?]+?)(?:\s+(?:at|in|on|by|before|after|tomorrow|today|next|this)|\s*[.!?]|\s*$)', re.IGNORECASE),
            'lets': re.compile(r'\blet\'?s\s+([^.!?]+?)(?:\s+(?:at|in|on|by|before|after|tomorrow|today|next|this)|\s*[.!?]|\s*$)', re.IGNORECASE),
            'need_to': re.compile(r'\b(?:we\s+)?need\s+to\s+([^.!?]+?)(?:\s+(?:at|in|on|by|before|after|tomorrow|today|next|this)|\s*[.!?]|\s*$)', re.IGNORECASE),
            'should': re.compile(r'\b(?:we\s+)?should\s+([^.!?]+?)(?:\s+(?:at|in|on|by|before|after|tomorrow|today|next|this)|\s*[.!?]|\s*$)', re.IGNORECASE),
            'going_to': re.compile(r'\b(?:we\'re|we\s+are)\s+going\s+to\s+([^.!?]+?)(?:\s+(?:at|in|on|by|before|after|tomorrow|today|next|this)|\s*[.!?]|\s*$)', re.IGNORECASE),
            'plan_to': re.compile(r'\b(?:we\s+)?plan\s+to\s+([^.!?]+?)(?:\s+(?:at|in|on|by|before|after|tomorrow|today|next|this)|\s*[.!?]|\s*$)', re.IGNORECASE),
        }
        
        # Context analysis patterns for who/what/where
        self.context_patterns = {
            'meeting_with': re.compile(r'\b(?:meeting|meet)\s+with\s+([^,\n!?]+?)(?:\s+(?:at|in|on|about|regarding|for|tomorrow|today|next|this)|[.!?]|\s*$)', re.IGNORECASE),
            'call_with': re.compile(r'\b(?:call|phone\s+call|video\s+call)\s+with\s+([^,\n!?]+?)(?:\s+(?:at|in|on|about|regarding|for|tomorrow|today|next|this)|[.!?]|\s*$)', re.IGNORECASE),
            'lunch_with': re.compile(r'\b(?:lunch|dinner|breakfast|coffee)\s+with\s+([^,\n!?]+?)(?:\s+(?:at|in|on|tomorrow|today|next|this)|[.!?]|\s*$)', re.IGNORECASE),
            'appointment_with': re.compile(r'\b(?:appointment|meeting)\s+with\s+([^,\n!?]+?)(?:\s+(?:at|in|on|for|tomorrow|today|next|this)|[.!?]|\s*$)', re.IGNORECASE),
            'interview_with': re.compile(r'\b(?:interview|screening)\s+(?:with|for)\s+([^,\n!?]+?)(?:\s+(?:at|in|on|for|tomorrow|today|next|this)|[.!?]|\s*$)', re.IGNORECASE),
            'presentation_about': re.compile(r'\b(?:presentation|demo|demonstration)\s+(?:on|about|for)\s+([^,\n!?]+?)(?:\s+(?:at|in|on|for|tomorrow|today|next|this)|[.!?]|\s*$)', re.IGNORECASE),
            'training_on': re.compile(r'\b(?:training|workshop|seminar)\s+(?:on|about|for)\s+([^,\n!?]+?)(?:\s+(?:at|in|on|for|tomorrow|today|next|this)|[.!?]|\s*$)', re.IGNORECASE),
        }
        
        # Simple action words that can be titles by themselves
        self.simple_actions = {
            'meet', 'meeting', 'lunch', 'dinner', 'breakfast', 'coffee',
            'call', 'appointment', 'interview', 'presentation', 'demo',
            'training', 'workshop', 'seminar', 'conference', 'review',
            'standup', 'sync', 'catchup', 'planning', 'brainstorm',
            'discussion', 'session', 'event', 'ceremony', 'celebration'
        }
        
        # Title quality indicators
        self.quality_indicators = {
            'positive': [
                'meeting', 'conference', 'workshop', 'training', 'presentation',
                'interview', 'appointment', 'lunch', 'dinner', 'call',
                'review', 'planning', 'discussion', 'session', 'demo'
            ],
            'negative': [
                'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at',
                'to', 'for', 'of', 'with', 'by', 'from', 'up', 'about'
            ]
        }
        
        # Truncation indicators
        self.truncation_patterns = {
            'incomplete_sentence': re.compile(r'\b(?:and|or|but|with|for|at|in|on|to|by|from|about)\s*$', re.IGNORECASE),
            'ellipsis': re.compile(r'\.{2,}$'),
            'dash_continuation': re.compile(r'-\s*$'),
            'comma_continuation': re.compile(r',\s*$'),
        }
        
        # Title normalization patterns
        self.normalization_patterns = {
            'remove_prefixes': re.compile(r'^(?:reminder:?\s*|note:?\s*|fyi:?\s*|please\s+|urgent:?\s*|important:?\s*)', re.IGNORECASE),
            'remove_temporal': re.compile(r'\s+(?:tomorrow|today|yesterday|next\s+\w+|this\s+\w+|on\s+\w+)(?:\s+.*)?$', re.IGNORECASE),
            'remove_time': re.compile(r'\s+at\s+\d+(?::\d+)?(?:am|pm)?(?:\s+.*)?$', re.IGNORECASE),
            'remove_location': re.compile(r'\s+(?:at|in)\s+(?:the\s+)?[a-zA-Z\s]+$', re.IGNORECASE),
            'clean_whitespace': re.compile(r'\s+'),
        }
    
    def extract_title(self, text: str) -> TitleResult:
        """
        Extract or generate a simple title from the given text as LLM fallback.
        
        This is intentionally simple - the LLM should do the heavy lifting.
        This is just a basic fallback when LLM fails.
        
        Args:
            text: Input text containing event information
            
        Returns:
            TitleResult with basic title extraction or empty if nothing found
        """
        if not text or not text.strip():
            return TitleResult.empty(raw_text=text)
        
        # Simple extraction strategies (not trying to be perfect)
        candidates = []
        
        # Method 1: Look for obvious formal event names (quoted or capitalized)
        formal_candidates = self._extract_simple_formal_names(text)
        candidates.extend(formal_candidates)
        
        # Method 2: Simple action words at the beginning
        simple_candidates = self._extract_simple_actions(text)
        candidates.extend(simple_candidates)
        
        # Method 3: Basic context patterns (meeting with X, call with Y)
        context_candidates = self._extract_basic_context(text)
        candidates.extend(context_candidates)
        
        # Method 4: First few words as last resort
        if not candidates:
            fallback_candidate = self._extract_first_words(text)
            if fallback_candidate:
                candidates.append(fallback_candidate)
        
        # Select the best candidate (or return empty if none are good enough)
        if candidates:
            best_candidate = self._select_best_candidate(candidates, text)
            return self._build_title_result(best_candidate, candidates, text)
        else:
            # No decent candidates found - that's okay, user can fill it in
            return TitleResult.empty(raw_text=text)   
 
    def _extract_simple_formal_names(self, text: str) -> List[Dict[str, Any]]:
        """Extract obvious formal event names (quoted text or clear event names)."""
        candidates = []
        
        # Look for quoted text
        quoted_matches = re.finditer(r'["\']([^"\']{3,50})["\']', text)
        for match in quoted_matches:
            title = match.group(1).strip()
            if self._is_reasonable_title(title):
                candidates.append({
                    'title': title,
                    'confidence': 0.8,
                    'method': 'explicit',
                    'pattern': 'quoted',
                    'quality': self._assess_basic_quality(title)
                })
        
        # Look for obvious event names (capitalized words + event keywords)
        event_pattern = re.compile(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+(?:Meeting|Conference|Workshop|Training|Session|Event|Gathering))\b')
        for match in event_pattern.finditer(text):
            title = match.group(1).strip()
            if self._is_reasonable_title(title):
                candidates.append({
                    'title': title,
                    'confidence': 0.9,
                    'method': 'explicit',
                    'pattern': 'formal_event',
                    'quality': self._assess_basic_quality(title)
                })
        
        return candidates
    
    def _extract_simple_actions(self, text: str) -> List[Dict[str, Any]]:
        """Extract simple action words at the beginning of text."""
        candidates = []
        
        # Check if text starts with a simple action word
        words = text.strip().split()
        if words:
            first_word = words[0].lower().rstrip('.,!?:;')
            if first_word in self.simple_actions:
                candidates.append({
                    'title': first_word.capitalize(),
                    'confidence': 0.6,
                    'method': 'action_based',
                    'pattern': 'simple_action',
                    'quality': self._assess_basic_quality(first_word)
                })
        
        return candidates
    
    def _extract_basic_context(self, text: str) -> List[Dict[str, Any]]:
        """Extract basic context patterns like 'meeting with X' or 'call with Y'."""
        candidates = []
        
        # Simple patterns for common contexts
        patterns = {
            'meeting_with': re.compile(r'\b(?:meeting|meet)\s+with\s+([^,\n!?]{3,30})(?:\s|$)', re.IGNORECASE),
            'call_with': re.compile(r'\b(?:call|phone\s+call)\s+with\s+([^,\n!?]{3,30})(?:\s|$)', re.IGNORECASE),
            'lunch_with': re.compile(r'\b(?:lunch|dinner|coffee)\s+with\s+([^,\n!?]{3,30})(?:\s|$)', re.IGNORECASE),
        }
        
        for pattern_name, pattern in patterns.items():
            match = pattern.search(text)
            if match:
                context_info = match.group(1).strip()
                # Clean up the context (remove time/location info)
                context_info = re.sub(r'\s+(?:at|on|in|tomorrow|today|next|this).*$', '', context_info, flags=re.IGNORECASE)
                
                if context_info and len(context_info) >= 2:
                    if pattern_name == 'meeting_with':
                        title = f"Meeting with {context_info.title()}"
                    elif pattern_name == 'call_with':
                        title = f"Call with {context_info.title()}"
                    elif pattern_name == 'lunch_with':
                        title = f"Lunch with {context_info.title()}"
                    
                    if self._is_reasonable_title(title):
                        candidates.append({
                            'title': title,
                            'confidence': 0.7,
                            'method': 'context_derived',
                            'pattern': pattern_name,
                            'quality': self._assess_basic_quality(title)
                        })
        
        return candidates
    
    def _extract_first_words(self, text: str) -> Optional[Dict[str, Any]]:
        """Extract first few words as a last resort title."""
        words = text.strip().split()
        if len(words) >= 2:
            # Take first 2-4 words, but not more than 40 characters
            title_words = []
            char_count = 0
            for word in words[:4]:
                if char_count + len(word) + 1 <= 40:  # +1 for space
                    title_words.append(word)
                    char_count += len(word) + 1
                else:
                    break
            
            if len(title_words) >= 2:
                title = ' '.join(title_words)
                # Clean up punctuation
                title = re.sub(r'[.!?,:;]+$', '', title)
                
                if self._is_reasonable_title(title):
                    return {
                        'title': title.title(),
                        'confidence': 0.3,  # Low confidence for this fallback
                        'method': 'derived',
                        'pattern': 'first_words',
                        'quality': self._assess_basic_quality(title)
                    }
        
        return None
    
    def _is_reasonable_title(self, title: str) -> bool:
        """Check if a title is reasonable (basic validation)."""
        if not title or len(title.strip()) < 2:
            return False
        
        title = title.strip()
        
        # Basic checks
        if len(title) > 80:  # Too long
            return False
        
        if not re.search(r'[a-zA-Z]', title):  # Must contain letters
            return False
        
        # Don't accept titles that are mostly noise words
        words = title.lower().split()
        noise_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
        meaningful_words = [w for w in words if w not in noise_words and len(w) > 1]
        
        return len(meaningful_words) >= 1
    
    def _assess_basic_quality(self, title: str) -> float:
        """Basic quality assessment for titles."""
        if not title:
            return 0.0
        
        score = 0.5  # Base score
        
        # Length bonus
        if 5 <= len(title) <= 40:
            score += 0.2
        
        # Word count bonus
        word_count = len(title.split())
        if 2 <= word_count <= 5:
            score += 0.2
        
        # Contains action words
        if any(word in title.lower() for word in self.quality_indicators['positive']):
            score += 0.1
        
        return min(1.0, score)
    
    def _select_best_candidate(self, candidates: List[Dict[str, Any]], text: str) -> Dict[str, Any]:
        """Select the best title candidate from options."""
        if not candidates:
            return None
        
        # Sort by combined score (confidence * quality)
        def candidate_score(candidate):
            confidence = candidate['confidence']
            quality = candidate['quality']
            
            # Method preference (explicit > context > action > derived)
            method_bonus = {
                'explicit': 0.2,
                'context_derived': 0.1,
                'action_based': 0.05,
                'derived': 0.0
            }.get(candidate['method'], 0.0)
            
            return (confidence * 0.7 + quality * 0.3) + method_bonus
        
        candidates.sort(key=candidate_score, reverse=True)
        return candidates[0]
    
    def _build_title_result(self, best_candidate: Dict[str, Any], all_candidates: List[Dict[str, Any]], text: str) -> TitleResult:
        """Build a TitleResult from the best candidate."""
        if not best_candidate:
            return TitleResult.empty(raw_text=text)
        
        result = TitleResult(
            title=best_candidate['title'],
            confidence=best_candidate['confidence'],
            generation_method=best_candidate['method'],
            raw_text=text,
            quality_score=best_candidate['quality']
        )
        
        # Add basic metadata
        result.extraction_metadata = {
            'pattern': best_candidate['pattern'],
            'total_candidates': len(all_candidates),
            'extraction_note': 'Simple regex fallback - LLM should be primary method'
        }
        
        # Add alternatives (limit to 3 for simplicity)
        for candidate in all_candidates[1:4]:  # Skip the best one, take next 3
            if candidate['title'] != result.title:
                result.add_alternative(candidate['title'], candidate['confidence'])
        
        return result    

    # ===== LLM FALLBACK SERVICE METHODS (Main Purpose) =====
    
    def validate_llm_title(self, llm_title: Optional[str], text: str, llm_confidence: float = 0.0) -> TitleResult:
        """
        Validate and enhance LLM-generated titles. This is the main purpose of this class.
        
        Args:
            llm_title: Title generated by LLM
            text: Original text for context
            llm_confidence: Confidence score from LLM
            
        Returns:
            TitleResult with validation and potential improvements
        """
        if not llm_title or not llm_title.strip():
            logger.debug("LLM returned empty title, falling back to simple regex extraction")
            return self.extract_title_fallback(text, reason="llm_empty_title")
        
        # Clean the LLM title
        cleaned_title = llm_title.strip()
        
        # Basic validation
        if not self._is_reasonable_title(cleaned_title):
            logger.debug(f"LLM title '{llm_title}' failed basic validation, falling back")
            return self.extract_title_fallback(text, reason="llm_invalid_title")
        
        # If LLM confidence is very low, enhance with regex alternatives
        if llm_confidence < 0.4:
            logger.debug(f"LLM confidence too low ({llm_confidence}), enhancing with regex")
            return self._enhance_llm_title_with_regex(cleaned_title, text, llm_confidence)
        
        # LLM title is good - use it but get regex alternatives for comparison
        regex_result = self.extract_title(text)
        
        result = TitleResult(
            title=cleaned_title,
            confidence=max(llm_confidence, 0.6),  # Boost confidence for validated LLM titles
            generation_method="llm_validated",
            raw_text=text,
            quality_score=self._assess_basic_quality(cleaned_title)
        )
        
        # Add regex alternative if it's different and decent
        if (regex_result.title and 
            regex_result.title != cleaned_title and 
            regex_result.confidence >= 0.5):
            result.add_alternative(regex_result.title, regex_result.confidence)
        
        # Add validation metadata
        result.extraction_metadata = {
            'llm_original_title': llm_title,
            'llm_confidence': llm_confidence,
            'validation_passed': True,
            'validation_method': 'basic_checks',
            'note': 'LLM title validated and accepted'
        }
        
        return result
    
    def extract_title_fallback(self, text: str, reason: str = "llm_unavailable") -> TitleResult:
        """
        Extract title using simple regex as fallback when LLM fails.
        
        Args:
            text: Input text containing event information
            reason: Reason for fallback (for metadata)
            
        Returns:
            TitleResult from simple regex extraction (may be empty - that's okay)
        """
        logger.debug(f"Using simple regex fallback for title extraction: {reason}")
        
        # Use simple regex-based extraction
        result = self.extract_title(text)
        
        # Update metadata to indicate this was a fallback
        if result.extraction_metadata is None:
            result.extraction_metadata = {}
        
        result.extraction_metadata.update({
            'fallback_reason': reason,
            'extraction_method': 'simple_regex_fallback',
            'llm_available': False,
            'note': 'Simple fallback used - user can provide better title if needed'
        })
        
        # Adjust generation method to indicate fallback
        if result.generation_method and result.generation_method != "none":
            result.generation_method = f"regex_fallback_{result.generation_method}"
        else:
            result.generation_method = "regex_fallback_none"
        
        return result
    
    def _enhance_llm_title_with_regex(self, llm_title: str, text: str, llm_confidence: float) -> TitleResult:
        """
        Enhance low-confidence LLM title with regex alternatives.
        
        Args:
            llm_title: Original LLM title
            text: Input text
            llm_confidence: LLM confidence score
            
        Returns:
            Enhanced TitleResult with best available title
        """
        # Get regex alternatives
        regex_result = self.extract_title(text)
        
        # If regex found something significantly better, prefer it
        if (regex_result.title and 
            regex_result.confidence > llm_confidence + 0.2):  # Regex needs to be notably better
            
            logger.debug(f"Regex title '{regex_result.title}' preferred over low-confidence LLM title '{llm_title}'")
            result = regex_result
            result.generation_method = "regex_preferred_over_llm"
            result.add_alternative(llm_title, llm_confidence)
        else:
            # Keep LLM title but add regex as alternative
            result = TitleResult(
                title=llm_title,
                confidence=llm_confidence,
                generation_method="llm_enhanced",
                raw_text=text,
                quality_score=self._assess_basic_quality(llm_title)
            )
            
            if regex_result.title and regex_result.title != llm_title:
                result.add_alternative(regex_result.title, regex_result.confidence)
        
        # Add enhancement metadata
        result.extraction_metadata.update({
            'llm_title': llm_title,
            'llm_confidence': llm_confidence,
            'regex_title': regex_result.title if regex_result else None,
            'regex_confidence': regex_result.confidence if regex_result else 0.0,
            'enhancement_applied': True,
            'note': 'Low LLM confidence enhanced with regex alternatives'
        })
        
        return result
    
    def extract_with_llm_fallback(self, text: str, llm_result: Optional[Dict[str, Any]] = None) -> TitleResult:
        """
        Main method for LLM-first title extraction with simple regex fallback.
        
        This is the primary interface for the LLM fallback service.
        
        Args:
            text: Input text containing event information
            llm_result: Optional LLM extraction result
            
        Returns:
            TitleResult with best available title (may be empty if nothing good found)
        """
        # If LLM result is provided, validate it
        if llm_result:
            llm_title = llm_result.get('title')
            llm_confidence = llm_result.get('confidence', {}).get('title', 0.0)
            
            if llm_title:
                return self.validate_llm_title(llm_title, text, llm_confidence)
        
        # No LLM result or LLM failed, use simple regex fallback
        result = self.extract_title_fallback(text, reason="no_llm_result")
        
        # If regex also failed to find anything decent, that's okay - user can fill it in
        if not result.title or result.confidence < 0.4 or result.quality_score < 0.3:
            # Add metadata suggesting user input
            if result.extraction_metadata is None:
                result.extraction_metadata = {}
            
            # Generate suggestions for potential user prompt
            suggestions = self.generate_title_suggestions(text)
            
            result.extraction_metadata.update({
                'low_quality_extraction': True,
                'user_input_recommended': True,
                'user_prompt_suggested': True,  # For test compatibility
                'title_suggestions': suggestions,
                'prompt_reason': 'low_confidence_extraction',
                'note': 'No high-quality title found - user input recommended'
            })
        
        return result
    
    def generate_title_suggestions(self, text: str, context: Optional[Dict[str, Any]] = None) -> List[str]:
        """
        Generate simple title suggestions for user selection.
        
        Args:
            text: Input text containing event information
            context: Optional context (datetime, location, etc.)
            
        Returns:
            List of simple title suggestions
        """
        suggestions = []
        
        # Get candidates from simple extraction
        result = self.extract_title(text)
        if result.title:
            suggestions.append(result.title)
        
        # Add alternatives
        suggestions.extend(result.alternatives[:3])
        
        # Add context-based suggestions if available
        if context:
            if context.get('location'):
                suggestions.append(f"Meeting at {context['location']}")
            
            if context.get('datetime'):
                dt = context['datetime']
                if hasattr(dt, 'strftime'):
                    time_str = dt.strftime('%I:%M %p').lstrip('0')
                    suggestions.append(f"Event at {time_str}")
        
        # Add generic suggestions if we don't have enough
        if len(suggestions) < 3:
            generic_suggestions = ["Meeting", "Appointment", "Event", "Discussion", "Call"]
            for generic in generic_suggestions:
                if generic not in suggestions and len(suggestions) < 5:
                    suggestions.append(generic)
        
        return suggestions[:5]  # Limit to 5 suggestions
    
    def assess_title_completeness(self, title: str, text: str) -> Dict[str, Any]:
        """
        Simple assessment of title completeness.
        
        Args:
            title: Title to assess
            text: Original text for context
            
        Returns:
            Basic assessment results
        """
        if not title:
            return {
                'is_complete': False,
                'completeness_score': 0.0,
                'issues': ['Title is empty'],
                'suggestions': ['Use LLM or provide manual title']
            }
        
        issues = []
        suggestions = []
        score = 1.0
        
        # Basic checks
        if len(title) < 3:
            issues.append('Title is very short')
            suggestions.append('Consider a more descriptive title')
            score -= 0.3
        elif len(title) > 60:
            issues.append('Title is quite long')
            suggestions.append('Consider shortening the title')
            score -= 0.1
        
        # Check for meaningful content
        if not self._is_reasonable_title(title):
            issues.append('Title may not be meaningful')
            suggestions.append('Consider using LLM or manual input')
            score -= 0.4
        
        # Check for truncation patterns (simplified)
        if title.endswith((' with', ' for', ' about', ' at', ' in', ' on')):
            issues.append('Title appears truncated')
            suggestions.append('Complete the title')
            score -= 0.3
        
        return {
            'is_complete': len(issues) == 0,
            'completeness_score': max(0.0, score),
            'issues': issues,
            'suggestions': suggestions,
            'note': 'Basic assessment - LLM should provide better titles'
        }
    
    # ===== SIMPLIFIED INTERFACE METHODS =====
    
    def extract_multiple_titles(self, text: str) -> List[TitleResult]:
        """
        Simple multiple title extraction (basic implementation).
        
        Args:
            text: Input text that may contain multiple events
            
        Returns:
            List with single TitleResult (keeping interface compatible)
        """
        # For simplicity, just return single result
        # LLM should handle multiple event detection better
        return [self.extract_title(text)] 
   
    def prompt_user_for_title(self, text: str, suggestions: Optional[List[str]] = None) -> TitleResult:
        """
        Simplified user prompt method - in practice, UI should handle this.
        
        Args:
            text: Original text
            suggestions: Optional list of title suggestions
            
        Returns:
            TitleResult (empty in non-interactive mode)
        """
        # For the LLM fallback service, we keep this simple
        # The actual UI implementation should handle user prompts
        try:
            from ui.safe_input import is_non_interactive
            if is_non_interactive():
                return TitleResult.empty(raw_text=text)
        except ImportError:
            pass
        
        # In practice, this would be handled by the UI layer
        # For now, just return empty to indicate user should provide title
        return TitleResult.empty(raw_text=text)