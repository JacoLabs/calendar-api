"""
Event information extraction service for parsing titles, locations, and other event details
from natural language text using heuristics and keyword detection.
"""

import re
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass
from models.event_models import ParsedEvent


@dataclass
class ExtractionMatch:
    """Represents an extracted piece of information with confidence scoring."""
    value: str
    confidence: float
    start_pos: int
    end_pos: int
    matched_text: str
    extraction_type: str
    keywords_used: List[str]


class EventInformationExtractor:
    """
    Service for extracting event information like titles, locations, and descriptions
    from natural language text using heuristics and keyword detection.
    """
    
    def __init__(self):
        self._compile_patterns()
    
    def _compile_patterns(self):
        """Compile regex patterns and keyword lists for information extraction."""
        
        # Location keywords and patterns
        self.location_keywords = {
            'at': re.compile(r'\bat\s+(?!(?:\d{1,2}(?::\d{2})?(?:am|pm)?))([^,\n!?;]+?)(?:\s+(?:tomorrow|today|yesterday|on\s+\w+|at\s+\d+(?::\d+)?(?:am|pm)?|for\s+\d+)|[.!?]|\s*$)', re.IGNORECASE),
            'in': re.compile(r'\bin\s+((?:the\s+)?[^,\n!?;]+?)(?:\s+(?:tomorrow|today|yesterday|on\s+\w+|at\s+\d+(?::\d+)?(?:am|pm)?|for\s+\d+)|[.!?]|\s*$)', re.IGNORECASE),
            '@': re.compile(r'@\s*([^,\n.!?;]+?)(?:\s*[,.]|\s*$)', re.IGNORECASE),
            'location': re.compile(r'\blocation:?\s*([^,\n.!?;]+)', re.IGNORECASE),
            'venue': re.compile(r'\bvenue:?\s*([^,\n.!?;]+)', re.IGNORECASE),
            'address': re.compile(r'\baddress:?\s*([^,\n.!?;]+)', re.IGNORECASE),

            'room': re.compile(r'\b((?:conference\s+room|meeting\s+room|room)\s+[A-Za-z0-9]+)(?:\s+(?:is|at|on|for|available)|[.!?]|\s*$)', re.IGNORECASE),
            'building': re.compile(r'\b(?:building|bldg)\s+([A-Za-z0-9\s,]+?)(?:\s+(?:at|on|for)|[.!?]|\s*$)', re.IGNORECASE),
            'office': re.compile(r'\boffice\s+([A-Za-z0-9\s]+?)(?:\s|[.!?]|$)', re.IGNORECASE)
        }
        
        # Configuration for location pattern matching
        self.location_config = {
            'enable_coordinates': False,  # Future-proof: can be enabled by locale/config
            'enable_canadian_postal_codes': True,
            'enable_street_addresses': True
        }
        
        # Common location patterns
        self.location_patterns = {
            'room_number': re.compile(r'\b((?:room|rm)\s*#?\d+[a-z]?)\b', re.IGNORECASE),
            'floor': re.compile(r'\b(\d+(?:st|nd|rd|th)\s+floor)\b', re.IGNORECASE),
            'street_address': re.compile(r'\b(\d+\s+[A-Za-z\s]+(?:street|st|avenue|ave|road|rd|drive|dr|lane|ln|boulevard|blvd|way|place|pl|court|ct|crescent|cres|circle|circ)(?:,\s*[A-Za-z\s]+)*(?:,\s*[A-Za-z]\d[A-Za-z]\s*\d[A-Za-z]\d)?)', re.IGNORECASE),
            'canadian_postal_code': re.compile(r'\b([A-Za-z]\d[A-Za-z]\s*\d[A-Za-z]\d)\b'),
            # Placeholder for future coordinate support - currently disabled
            'coordinates': re.compile(r'(-?\d+\.\d+,\s*-?\d+\.\d+)')
        }
        
        # Title extraction patterns
        self.title_indicators = {
            'meeting': re.compile(r'\b((?:meeting|meet)\s+(?:with|about|for|on)\s+[^,\n!?]+?)(?=\s+(?:at\s+\d+(?::\d+)?(?:am|pm)?|on\s+(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday))|[.!?]|\s*$)', re.IGNORECASE),
            'simple_meet': re.compile(r'\b(meet)\s+(?:at|in)\s+', re.IGNORECASE),
            'call': re.compile(r'\b(?:call|phone call|video call)\s+(?:with|about|for|on)\s+([^,\n!?]+?)(?:\s+(?:tomorrow|today|yesterday|at\s+\d+:\d+|on\s+\w+)|[.!?]|\s*$)', re.IGNORECASE),
            'appointment': re.compile(r'\b(?:appointment|appt)\s+(?:with|for|at)\s+([^,\n!?]+?)(?:\s+(?:tomorrow|today|yesterday|at\s+\d+(?::\d+)?(?:am|pm)?|on\s+\w+)|\s*$)', re.IGNORECASE),
            'lunch': re.compile(r'\b(?:lunch|dinner|breakfast)\s+(?:with|at)\s+(?!\d+(?::\d+)?(?:am|pm)?\s+)([^,\n!?]+?)(?:\s+(?:tomorrow|today|yesterday|at\s+\d+(?::\d+)?(?:am|pm)?|on\s+\w+)|[.!?]|\s*$)', re.IGNORECASE),
            'interview': re.compile(r'\b(?:interview|screening)\s+(?:with|for)\s+([^,\n!?]+?)(?:\s+(?:tomorrow|today|yesterday|at\s+\d+:\d+|on\s+\w+)|[.!?]|\s*$)', re.IGNORECASE),
            'presentation': re.compile(r'\b(?:presentation|demo|demonstration)\s+(?:on|about|for)\s+([^,\n!?]+?)(?:\s+(?:tomorrow|today|yesterday|at\s+\d+:\d+|on\s+\w+)|[.!?]|\s*$)', re.IGNORECASE),
            'training': re.compile(r'\b(?:training|workshop|seminar)\s+(?:on|about|for)\s+([^,\n!?]+?)(?:\s+(?:tomorrow|today|yesterday|at\s+\d+:\d+|on\s+\w+)|[.!?]|\s*$)', re.IGNORECASE),
            'conference': re.compile(r'\b(?:conference|summit|symposium)\s+(?:on|about)\s+([^,\n!?]+?)(?:\s+(?:tomorrow|today|yesterday|at\s+\d+:\d+|on\s+\w+)|[.!?]|\s*$)', re.IGNORECASE)
        }
        
        # Event type keywords for confidence scoring
        self.event_type_keywords = [
            'meeting', 'call', 'appointment', 'lunch', 'dinner', 'breakfast',
            'interview', 'presentation', 'demo', 'training', 'workshop',
            'conference', 'seminar', 'review', 'standup', 'sync', 'catchup',
            'planning', 'brainstorm', 'discussion', 'session', 'event'
        ]
        
        # Words to exclude from titles (common noise words)
        self.title_noise_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'from', 'up', 'about', 'into', 'through', 'during',
            'before', 'after', 'above', 'below', 'between', 'among', 'is', 'are',
            'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do',
            'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might',
            'must', 'can', 'today', 'tomorrow', 'yesterday', 'now', 'then'
        }
        
        # Sentence boundary patterns
        self.sentence_boundaries = re.compile(r'[.!?]+\s+')
        
        # Quote patterns for extracting quoted titles
        self.quote_patterns = [
            re.compile(r'"([^"]+)"'),
            re.compile(r"(?<!\w)'([^']+)'(?!\w)"),  # Avoid matching contractions like "let's"
            re.compile(r'`([^`]+)`')
        ]
    
    def extract_title(self, text: str) -> List[ExtractionMatch]:
        """
        Extract potential event titles from text using various heuristics.
        
        Args:
            text: Input text to analyze
            
        Returns:
            List of ExtractionMatch objects for potential titles, sorted by confidence
        """
        matches = []
        
        # Method 1: Extract using event type patterns
        for event_type, pattern in self.title_indicators.items():
            for match in pattern.finditer(text):
                title = match.group(1).strip()
                # Clean up temporal words from the end of titles
                title = self._clean_title(title)
                if self._is_valid_title(title):
                    confidence = self._calculate_title_confidence(title, event_type, text)
                    matches.append(ExtractionMatch(
                        value=title,
                        confidence=confidence,
                        start_pos=match.start(1),
                        end_pos=match.end(1),
                        matched_text=match.group(0),
                        extraction_type=f"title_pattern_{event_type}",
                        keywords_used=[event_type]
                    ))
        
        # Method 2: Extract quoted text as potential titles
        for quote_pattern in self.quote_patterns:
            for match in quote_pattern.finditer(text):
                title = match.group(1).strip()
                if self._is_valid_title(title):
                    confidence = self._calculate_title_confidence(title, "quoted", text)
                    matches.append(ExtractionMatch(
                        value=title,
                        confidence=confidence,
                        start_pos=match.start(1),
                        end_pos=match.end(1),
                        matched_text=match.group(0),
                        extraction_type="title_quoted",
                        keywords_used=["quoted"]
                    ))
        
        # Method 3: Extract first sentence as potential title
        sentences = self.sentence_boundaries.split(text.strip())
        if sentences:
            first_sentence = sentences[0].strip()
            # Remove common prefixes
            first_sentence = re.sub(r'^(?:let\'s|we should|i need to|please|reminder:?)\s+', '', first_sentence, flags=re.IGNORECASE)
            
            if self._is_valid_title(first_sentence):
                confidence = self._calculate_title_confidence(first_sentence, "first_sentence", text)
                matches.append(ExtractionMatch(
                    value=first_sentence,
                    confidence=confidence,
                    start_pos=0,
                    end_pos=len(first_sentence),
                    matched_text=first_sentence,
                    extraction_type="title_first_sentence",
                    keywords_used=["first_sentence"]
                ))
        
        # Method 3.5: Extract simple action words at the beginning
        simple_action_match = re.match(r'^(meet|lunch|dinner|breakfast|call|appointment|interview|conference|workshop|training|presentation|event)\b', text.strip(), re.IGNORECASE)
        if simple_action_match:
            action_word = simple_action_match.group(1)
            confidence = 0.95  # High confidence for simple action words at start
            matches.append(ExtractionMatch(
                value=action_word,
                confidence=confidence,
                start_pos=0,
                end_pos=len(action_word),
                matched_text=action_word,
                extraction_type="title_simple_action",
                keywords_used=["simple_action"]
            ))
        
        # Method 4: Extract capitalized phrases as potential titles
        capitalized_phrases = re.finditer(r'\b[A-Z][A-Za-z\s]{2,30}(?=\s|$|[,.!?])', text)
        for match in capitalized_phrases:
            title = match.group(0).strip()
            if self._is_valid_title(title) and len(title.split()) >= 2:
                confidence = self._calculate_title_confidence(title, "capitalized", text)
                matches.append(ExtractionMatch(
                    value=title,
                    confidence=confidence,
                    start_pos=match.start(),
                    end_pos=match.end(),
                    matched_text=title,
                    extraction_type="title_capitalized",
                    keywords_used=["capitalized"]
                ))
        
        # Remove duplicates and overlapping matches
        filtered_matches = self._remove_overlapping_matches(matches)
        
        # Sort by confidence (highest first)
        filtered_matches.sort(key=lambda x: x.confidence, reverse=True)
        return filtered_matches
    
    def extract_location(self, text: str) -> List[ExtractionMatch]:
        """
        Extract potential locations from text using keyword detection.
        
        Args:
            text: Input text to analyze
            
        Returns:
            List of ExtractionMatch objects for potential locations, sorted by confidence
        """
        matches = []
        
        # Method 1: Extract using location keywords
        for keyword, pattern in self.location_keywords.items():
            for match in pattern.finditer(text):
                location = match.group(1).strip()
                if self._is_valid_location(location):
                    confidence = self._calculate_location_confidence(location, keyword, text)
                    matches.append(ExtractionMatch(
                        value=location,
                        confidence=confidence,
                        start_pos=match.start(1),
                        end_pos=match.end(1),
                        matched_text=match.group(0),
                        extraction_type=f"location_keyword_{keyword}",
                        keywords_used=[keyword]
                    ))
        
        # Method 2: Extract using location patterns
        for pattern_name, pattern in self.location_patterns.items():
            # Skip disabled patterns based on configuration
            if pattern_name == 'coordinates' and not self.location_config.get('enable_coordinates', False):
                continue
            if pattern_name == 'canadian_postal_code' and not self.location_config.get('enable_canadian_postal_codes', True):
                continue
            if pattern_name == 'street_address' and not self.location_config.get('enable_street_addresses', True):
                continue
                
            for match in pattern.finditer(text):
                # For patterns, use group 1 if available, otherwise full match
                location = (match.group(1) if match.groups() and match.group(1) else match.group(0)).strip()
                
                if self._is_valid_location(location):
                    confidence = self._calculate_location_confidence(location, pattern_name, text)
                    matches.append(ExtractionMatch(
                        value=location,
                        confidence=confidence,
                        start_pos=match.start(),
                        end_pos=match.end(),
                        matched_text=match.group(0),
                        extraction_type=f"location_pattern_{pattern_name}",
                        keywords_used=[pattern_name]
                    ))
        
        # Combine street addresses with nearby postal codes BEFORE removing overlaps
        combined_matches = self._combine_address_with_postal_code(text, matches)
        
        # Remove duplicates and overlapping matches
        filtered_matches = self._remove_overlapping_matches(combined_matches)
        
        # Sort by confidence (highest first)
        filtered_matches.sort(key=lambda x: x.confidence, reverse=True)
        return filtered_matches
    
    def _combine_address_with_postal_code(self, text: str, matches: List[ExtractionMatch]) -> List[ExtractionMatch]:
        """Combine street addresses with nearby postal codes to create full addresses."""
        combined_matches = []
        used_matches = set()
        
        for i, match in enumerate(matches):
            if i in used_matches:
                continue
                
            if match.extraction_type == "location_pattern_street_address":
                # Look for a nearby postal code
                best_postal_match = None
                best_distance = float('inf')
                
                for j, other_match in enumerate(matches):
                    if j != i and j not in used_matches and other_match.extraction_type == "location_pattern_canadian_postal_code":
                        # Check if postal code is within reasonable distance (within 50 characters)
                        distance = abs(match.end_pos - other_match.start_pos)
                        if distance < 50 and distance < best_distance:
                            best_distance = distance
                            best_postal_match = (j, other_match)
                
                if best_postal_match:
                    j, postal_match = best_postal_match
                    # Clean up the address value if it ends with partial postal code
                    address_value = match.value
                    if address_value.endswith(', M') or address_value.endswith(', K') or address_value.endswith(', L') or address_value.endswith(', N') or address_value.endswith(', P') or address_value.endswith(', R') or address_value.endswith(', S') or address_value.endswith(', T') or address_value.endswith(', V') or address_value.endswith(', X') or address_value.endswith(', Y'):
                        # Remove the partial postal code letter
                        address_value = address_value[:-3]
                    
                    # Combine the address and postal code
                    combined_value = f"{address_value}, {postal_match.value}"
                    combined_start = min(match.start_pos, postal_match.start_pos)
                    combined_end = max(match.end_pos, postal_match.end_pos)
                    combined_text = text[combined_start:combined_end]
                    
                    combined_matches.append(ExtractionMatch(
                        value=combined_value,
                        confidence=max(match.confidence, postal_match.confidence),
                        start_pos=combined_start,
                        end_pos=combined_end,
                        matched_text=combined_text,
                        extraction_type="location_combined_address",
                        keywords_used=match.keywords_used + postal_match.keywords_used
                    ))
                    
                    used_matches.add(i)
                    used_matches.add(j)
                else:
                    combined_matches.append(match)
                    used_matches.add(i)
            else:
                combined_matches.append(match)
                used_matches.add(i)
        
        return combined_matches
    
    def calculate_overall_confidence(self, parsed_event: ParsedEvent) -> float:
        """
        Calculate overall confidence score for a parsed event based on completeness
        and quality of extracted information.
        
        Args:
            parsed_event: ParsedEvent object to evaluate
            
        Returns:
            Overall confidence score between 0.0 and 1.0
        """
        confidence_factors = []
        
        # Title confidence
        if parsed_event.title:
            title_confidence = parsed_event.extraction_metadata.get('title_confidence', 0.5)
            confidence_factors.append(('title', title_confidence, 0.3))  # 30% weight
        else:
            confidence_factors.append(('title', 0.0, 0.3))
        
        # DateTime confidence
        if parsed_event.start_datetime:
            datetime_confidence = parsed_event.extraction_metadata.get('datetime_confidence', 0.5)
            confidence_factors.append(('datetime', datetime_confidence, 0.4))  # 40% weight
        else:
            confidence_factors.append(('datetime', 0.0, 0.4))
        
        # Location confidence
        if parsed_event.location:
            location_confidence = parsed_event.extraction_metadata.get('location_confidence', 0.5)
            confidence_factors.append(('location', location_confidence, 0.2))  # 20% weight
        else:
            confidence_factors.append(('location', 0.0, 0.2))
        
        # Completeness bonus
        completeness_score = 0.0
        if parsed_event.title:
            completeness_score += 0.4
        if parsed_event.start_datetime:
            completeness_score += 0.4
        if parsed_event.location:
            completeness_score += 0.2
        
        confidence_factors.append(('completeness', completeness_score, 0.1))  # 10% weight
        
        # Calculate weighted average
        total_score = sum(score * weight for _, score, weight in confidence_factors)
        
        # Apply penalties for missing critical information
        if not parsed_event.title:
            total_score *= 0.7  # 30% penalty for missing title
        if not parsed_event.start_datetime:
            total_score *= 0.5  # 50% penalty for missing datetime
        
        return min(1.0, max(0.0, total_score))
    
    def _clean_title(self, title: str) -> str:
        """Clean up extracted title by removing temporal and location indicators."""
        if not title:
            return title
        
        # Remove temporal words from the end
        temporal_pattern = re.compile(r'\s+(?:tomorrow|today|yesterday|next\s+\w+|this\s+\w+|on\s+\w+)$', re.IGNORECASE)
        title = temporal_pattern.sub('', title)
        
        # Remove location indicators from the end
        location_pattern = re.compile(r'\s+(?:at|in)\s+[^,\n!?]+$', re.IGNORECASE)
        title = location_pattern.sub('', title)
        
        return title.strip()
    
    def _is_valid_title(self, title: str) -> bool:
        """Check if extracted text is a valid title candidate."""
        if not title or len(title.strip()) < 3:
            return False
        
        # Remove common noise and check if anything meaningful remains
        words = title.lower().split()
        meaningful_words = [w for w in words if w not in self.title_noise_words and len(w) > 1]
        
        return len(meaningful_words) >= 1 and len(title) <= 100
    
    def _is_valid_location(self, location: str) -> bool:
        """Check if extracted text is a valid location candidate."""
        if not location or len(location.strip()) < 2:
            return False
        
        # Basic validation - not too long, contains some letters
        return len(location) <= 100 and re.search(r'[a-zA-Z]', location)
    
    def _calculate_title_confidence(self, title: str, extraction_method: str, full_text: str) -> float:
        """Calculate confidence score for an extracted title."""
        confidence = 0.5  # Base confidence
        
        # Method-specific confidence adjustments
        method_scores = {
            'meeting': 0.9, 'call': 0.9, 'appointment': 0.9,
            'lunch': 0.85, 'interview': 0.9, 'presentation': 0.85,
            'training': 0.8, 'conference': 0.8, 'quoted': 0.8,
            'first_sentence': 0.6, 'capitalized': 0.5
        }
        confidence = method_scores.get(extraction_method, 0.5)
        
        # Length-based adjustments
        if 5 <= len(title) <= 50:
            confidence += 0.1
        elif len(title) > 50:
            confidence -= 0.1
        
        # Event keyword bonus
        title_lower = title.lower()
        event_keywords_found = sum(1 for keyword in self.event_type_keywords if keyword in title_lower)
        confidence += min(0.2, event_keywords_found * 0.1)
        
        # Capitalization bonus (proper nouns)
        words = title.split()
        capitalized_words = sum(1 for word in words if word[0].isupper() and len(word) > 1)
        if capitalized_words > 0:
            confidence += min(0.1, capitalized_words * 0.05)
        
        # Penalty for too many noise words
        noise_word_ratio = sum(1 for word in words if word.lower() in self.title_noise_words) / len(words)
        if noise_word_ratio > 0.5:
            confidence -= 0.2
        
        return min(1.0, max(0.1, confidence))
    
    def _calculate_location_confidence(self, location: str, extraction_method: str, full_text: str) -> float:
        """Calculate confidence score for an extracted location."""
        confidence = 0.5  # Base confidence
        
        # Method-specific confidence adjustments
        method_scores = {
            '@': 0.95, 'at': 0.9, 'in': 0.7, 'location': 0.9,
            'venue': 0.9, 'address': 0.95, 'room': 0.85,
            'building': 0.8, 'office': 0.8, 'room_number': 0.9,
            'floor': 0.8, 'street_address': 0.95, 'canadian_postal_code': 0.95,
            # Coordinates disabled for now, but pattern preserved for future use
            'coordinates': 0.95
        }
        confidence = method_scores.get(extraction_method, 0.5)
        
        # Length-based adjustments
        if 3 <= len(location) <= 50:
            confidence += 0.1
        elif len(location) > 50:
            confidence -= 0.1
        
        # Pattern-based bonuses
        location_lower = location.lower()
        
        # Room/building indicators
        if re.search(r'\b(?:room|conference|meeting|office|building|floor)\b', location_lower):
            confidence += 0.1
        
        # Address indicators (including Canadian street types)
        if re.search(r'\b(?:street|avenue|road|drive|lane|boulevard|way|place|court|crescent|circle|st|ave|rd|dr|ln|blvd|way|pl|ct|cres|circ)\b', location_lower):
            confidence += 0.15
        
        # Canadian postal code pattern
        if re.search(r'\b[a-z]\d[a-z]\s*\d[a-z]\d\b', location_lower):
            confidence += 0.2
        
        # Numbers (room numbers, addresses)
        if re.search(r'\d+', location):
            confidence += 0.05
        
        # Common Canadian location words and general place types
        location_words = ['center', 'centre', 'hall', 'auditorium', 'lobby', 'cafe', 'restaurant', 'hotel', 'park', 
                         'market', 'mall', 'plaza', 'square', 'library', 'hospital', 'clinic', 'school', 'university',
                         'college', 'station', 'terminal', 'airport', 'downtown', 'uptown', 'midtown']
        if any(word in location_lower for word in location_words):
            confidence += 0.1
        
        # Canadian city names (common ones)
        canadian_cities = ['toronto', 'vancouver', 'montreal', 'calgary', 'ottawa', 'edmonton', 'mississauga', 
                          'winnipeg', 'quebec', 'hamilton', 'brampton', 'surrey', 'laval', 'halifax', 'london',
                          'markham', 'vaughan', 'gatineau', 'saskatoon', 'longueuil', 'burnaby', 'regina',
                          'richmond', 'richmond hill', 'oakville', 'burlington', 'greater sudbury', 'sherbrooke',
                          'oshawa', 'saguenay', 'lévis', 'barrie', 'abbotsford', 'coquitlam', 'st. catharines',
                          'trois-rivières', 'guelph', 'cambridge', 'whitby', 'kelowna', 'kingston', 'ajax']
        if any(city in location_lower for city in canadian_cities):
            confidence += 0.15
        
        return min(1.0, max(0.1, confidence))
    
    def _remove_overlapping_matches(self, matches: List[ExtractionMatch]) -> List[ExtractionMatch]:
        """Remove overlapping matches, keeping the ones with highest confidence."""
        if not matches:
            return matches
        
        # Sort by confidence (highest first)
        sorted_matches = sorted(matches, key=lambda x: x.confidence, reverse=True)
        
        filtered = []
        for match in sorted_matches:
            # Check if this match overlaps with any already accepted match
            overlaps = False
            for accepted in filtered:
                if (match.start_pos < accepted.end_pos and match.end_pos > accepted.start_pos):
                    overlaps = True
                    break
            
            if not overlaps:
                filtered.append(match)
        
        return filtered
    
    def extract_all_information(self, text: str) -> Dict[str, Any]:
        """
        Extract all available information from text and return structured results.
        
        Args:
            text: Input text to analyze
            
        Returns:
            Dictionary containing all extracted information with confidence scores
        """
        title_matches = self.extract_title(text)
        location_matches = self.extract_location(text)
        
        return {
            'titles': [
                {
                    'value': match.value,
                    'confidence': match.confidence,
                    'extraction_type': match.extraction_type,
                    'keywords_used': match.keywords_used,
                    'position': (match.start_pos, match.end_pos),
                    'matched_text': match.matched_text
                }
                for match in title_matches
            ],
            'locations': [
                {
                    'value': match.value,
                    'confidence': match.confidence,
                    'extraction_type': match.extraction_type,
                    'keywords_used': match.keywords_used,
                    'position': (match.start_pos, match.end_pos),
                    'matched_text': match.matched_text
                }
                for match in location_matches
            ],
            'best_title': title_matches[0].value if title_matches else None,
            'best_location': location_matches[0].value if location_matches else None,
            'title_confidence': title_matches[0].confidence if title_matches else 0.0,
            'location_confidence': location_matches[0].confidence if location_matches else 0.0
        }