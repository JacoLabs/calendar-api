"""
Advanced location extraction service for parsing comprehensive location information
from natural language text using multiple strategies and confidence scoring.
"""

import re
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass
from enum import Enum


class LocationType(Enum):
    """Types of locations that can be extracted."""
    ADDRESS = "address"
    VENUE = "venue"
    IMPLICIT = "implicit"
    DIRECTIONAL = "directional"


@dataclass
class LocationResult:
    """
    Represents an extracted location with confidence and type tracking.
    """
    location: Optional[str]
    confidence: float
    location_type: LocationType
    alternatives: List[str]
    raw_text: str
    extraction_method: str
    position: Tuple[int, int]  # (start_pos, end_pos)
    matched_text: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'location': self.location,
            'confidence': self.confidence,
            'location_type': self.location_type.value,
            'alternatives': self.alternatives,
            'raw_text': self.raw_text,
            'extraction_method': self.extraction_method,
            'position': self.position,
            'matched_text': self.matched_text
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LocationResult':
        """Create LocationResult from dictionary."""
        return cls(
            location=data.get('location'),
            confidence=data.get('confidence', 0.0),
            location_type=LocationType(data.get('location_type', 'implicit')),
            alternatives=data.get('alternatives', []),
            raw_text=data.get('raw_text', ''),
            extraction_method=data.get('extraction_method', ''),
            position=tuple(data.get('position', (0, 0))),
            matched_text=data.get('matched_text', '')
        )


class AdvancedLocationExtractor:
    """
    Advanced service for extracting location information from natural language text
    using multiple strategies including explicit addresses, implicit locations,
    directional references, and venue keyword recognition.
    """
    
    def __init__(self):
        self._compile_patterns()
    
    def _compile_patterns(self):
        """Compile regex patterns and keyword lists for comprehensive location extraction."""
        
        # Explicit address patterns
        self.address_patterns = {
            # Full street addresses with numbers
            'street_address': re.compile(
                r'\b(\d+\s+[A-Za-z\s]+(?:Street|St|Avenue|Ave|Road|Rd|Drive|Dr|Lane|Ln|Boulevard|Blvd|Way|Place|Pl|Court|Ct|Crescent|Cres|Circle|Circ|Parkway|Pkwy|Terrace|Ter)(?:\s*,\s*[A-Za-z\s]+)*(?:\s*,\s*[A-Za-z]\d[A-Za-z]\s*\d[A-Za-z]\d)?)\b',
                re.IGNORECASE
            ),
            
            # Named locations (squares, centers, etc.)
            'named_location': re.compile(
                r'\b([A-Z][A-Za-z\s&\']+(?:Square|Plaza|Center|Centre|Market|Mall|Park|Building|Tower|Complex|Hall|Stadium|Arena|Theatre|Theater|Hospital|Clinic|School|University|College|Library|Museum|Gallery|Station|Terminal|Airport))\b',
                re.IGNORECASE
            ),
            
            # Canadian postal codes
            'postal_code': re.compile(r'\b([A-Za-z]\d[A-Za-z]\s*\d[A-Za-z]\d)\b'),
            
            # Coordinates (for future use)
            'coordinates': re.compile(r'(-?\d+\.\d+)\s*,\s*(-?\d+\.\d+)')
        }
        
        # Context clue patterns with improved specificity
        self.context_patterns = {
            'at_location': re.compile(
                r'\bat\s+(?!(?:\d{1,2}(?::\d{2})?(?:\s*(?:am|pm|AM|PM))?|noon|midnight))([^,\n!?;]+?)(?=\s+(?:tomorrow|today|yesterday|on\s+\w+|at\s+\d+(?::\d+)?(?:am|pm|AM|PM)?|for\s+\d+|from\s+\d+)|[.!?]|\s*$)',
                re.IGNORECASE
            ),
            'in_location': re.compile(
                r'\bin\s+((?:the\s+)?[^,\n!?;]+?)(?=\s+(?:tomorrow|today|yesterday|on\s+\w+|at\s+\d+(?::\d+)?(?:am|pm|AM|PM)?|for\s+\d+|from\s+\d+)|[.!?]|\s*$)',
                re.IGNORECASE
            ),
            'by_location': re.compile(
                r'\bby\s+((?:the\s+)?[^,\n!?;]+?)(?=\s+(?:tomorrow|today|yesterday|on\s+\w+|at\s+\d+(?::\d+)?(?:am|pm|AM|PM)?|for\s+\d+|from\s+\d+|until)|[.!?]|\s*$)',
                re.IGNORECASE
            ),
            'at_symbol': re.compile(r'@\s*([^,\n.!?;]+?)(?:\s*[,.]|\s*$)', re.IGNORECASE),
            'location_colon': re.compile(r'\blocation:?\s*([^,\n.!?;]+)', re.IGNORECASE),
            'venue_colon': re.compile(r'\bvenue:?\s*([^,\n.!?;]+)', re.IGNORECASE),
            'address_colon': re.compile(r'\baddress:?\s*([^,\n.!?;]+)', re.IGNORECASE),
            'meet_at': re.compile(r'\bmeet\s+at\s+([^,\n.!?;]+?)(?=\s+(?:at\s+\d+|on\s+\w+|tomorrow|today)|[.!?]|\s*$)', re.IGNORECASE)
        }
        
        # Venue keyword patterns
        self.venue_patterns = {
            'room_patterns': re.compile(
                r'\b((?:conference\s+room|meeting\s+room|boardroom|classroom|room)\s+[A-Za-z0-9]+|room\s+#?\d+[a-z]?)\b',
                re.IGNORECASE
            ),
            'building_patterns': re.compile(
                r'\b((?:building|bldg)\s+[A-Za-z0-9]+)\b',
                re.IGNORECASE
            ),
            'floor_patterns': re.compile(
                r'\b(\d+(?:st|nd|rd|th)\s+floor|floor\s+\d+)\b',
                re.IGNORECASE
            ),
            'office_patterns': re.compile(
                r'\b(office\s+(?:suite\s+)?[0-9]+[A-Za-z]?)\b',
                re.IGNORECASE
            )
        }
        
        # Venue keywords for recognition
        self.venue_keywords = {
            'public_venues': [
                'square', 'plaza', 'park', 'center', 'centre', 'hall', 'auditorium',
                'stadium', 'arena', 'theatre', 'theater', 'museum', 'gallery',
                'library', 'market', 'mall', 'terminal', 'station', 'airport'
            ],
            'educational': [
                'school', 'university', 'college', 'campus', 'classroom', 'lecture hall',
                'lab', 'laboratory', 'gymnasium', 'cafeteria', 'library'
            ],
            'business': [
                'office', 'building', 'tower', 'complex', 'headquarters', 'branch',
                'store', 'shop', 'restaurant', 'cafe', 'hotel', 'conference room',
                'meeting room', 'boardroom'
            ],
            'medical': [
                'hospital', 'clinic', 'medical center', 'health center', 'pharmacy'
            ],
            'recreational': [
                'gym', 'fitness center', 'pool', 'court', 'field', 'track',
                'club', 'bar', 'pub', 'lounge'
            ]
        }
        
        # Implicit location patterns
        self.implicit_patterns = {
            'workplace': re.compile(
                r'\b((?:the\s+)?(?:office|work|workplace|headquarters|hq))(?!\s+[A-Za-z0-9])\b',
                re.IGNORECASE
            ),
            'educational': re.compile(
                r'\b((?:the\s+)?(?:school|university|college|campus|class))\b',
                re.IGNORECASE
            ),
            'home': re.compile(
                r'\b((?:my\s+|the\s+)?(?:home|house|place))\b',
                re.IGNORECASE
            ),
            'generic_places': re.compile(
                r'\b((?:the\s+)?(?:gym|library|hospital|clinic|store|mall|downtown|uptown|city center))\b',
                re.IGNORECASE
            )
        }
        
        # Directional location patterns
        self.directional_patterns = {
            'entrance_directions': re.compile(
                r'\b((?:at|by|near)\s+(?:the\s+)?(?:front|back|main|side)\s+(?:entrance|door|doors|gate))\b',
                re.IGNORECASE
            ),
            'relative_directions': re.compile(
                r'\b((?:in\s+front\s+of|behind|next\s+to|across\s+from|near)\s+[^,\n.!?;]+?)\b',
                re.IGNORECASE
            ),
            'floor_directions': re.compile(
                r'\b((?:on\s+(?:the\s+)?\d+(?:st|nd|rd|th)\s+floor|upstairs|downstairs|ground\s+floor|basement))\b',
                re.IGNORECASE
            ),
            'area_directions': re.compile(
                r'\b((?:in\s+(?:the\s+)?(?:lobby|foyer|atrium|courtyard|parking\s+lot|garage)))\b',
                re.IGNORECASE
            ),
            'simple_directions': re.compile(
                r'\b((?:the\s+)?(?:front|back|main|side)\s+(?:entrance|door|doors|gate))\b',
                re.IGNORECASE
            )
        }
        
        # Common Canadian cities for context
        self.canadian_cities = {
            'toronto', 'vancouver', 'montreal', 'calgary', 'ottawa', 'edmonton',
            'mississauga', 'winnipeg', 'quebec', 'hamilton', 'brampton', 'surrey',
            'laval', 'halifax', 'london', 'markham', 'vaughan', 'gatineau',
            'saskatoon', 'longueuil', 'burnaby', 'regina', 'richmond',
            'richmond hill', 'oakville', 'burlington', 'greater sudbury',
            'sherbrooke', 'oshawa', 'saguenay', 'lévis', 'barrie', 'abbotsford',
            'coquitlam', 'st. catharines', 'trois-rivières', 'guelph',
            'cambridge', 'whitby', 'kelowna', 'kingston', 'ajax'
        }
        
        # Location quality indicators
        self.quality_indicators = {
            'high_quality': [
                'address', 'street', 'avenue', 'road', 'drive', 'lane', 'boulevard',
                'square', 'plaza', 'center', 'centre', 'building', 'tower'
            ],
            'medium_quality': [
                'room', 'office', 'floor', 'hall', 'auditorium', 'conference',
                'meeting', 'classroom', 'lobby'
            ],
            'contextual': [
                'at', 'in', '@', 'venue:', 'location:', 'address:'
            ]
        }
    
    def extract_locations(self, text: str) -> List[LocationResult]:
        """
        Extract all potential locations from text using comprehensive strategies.
        
        Args:
            text: Input text to analyze
            
        Returns:
            List of LocationResult objects sorted by confidence
        """
        locations = []
        
        # Strategy 1: Extract explicit addresses (highest priority)
        locations.extend(self._extract_explicit_addresses(text))
        
        # Strategy 2: Extract locations using context clues (high priority)
        locations.extend(self._extract_context_locations(text))
        
        # Strategy 3: Extract implicit locations (before venue to catch "the office")
        locations.extend(self._extract_implicit_locations(text))
        
        # Strategy 4: Extract venue-based locations
        locations.extend(self._extract_venue_locations(text))
        
        # Strategy 5: Extract directional locations
        locations.extend(self._extract_directional_locations(text))
        
        # Remove overlapping matches and combine related ones
        filtered_locations = self._process_location_matches(text, locations)
        
        # Sort by confidence (highest first)
        filtered_locations.sort(key=lambda x: x.confidence, reverse=True)
        
        return filtered_locations
    
    def _extract_explicit_addresses(self, text: str) -> List[LocationResult]:
        """Extract explicit street addresses and named locations."""
        locations = []
        
        for pattern_name, pattern in self.address_patterns.items():
            for match in pattern.finditer(text):
                if pattern_name == 'coordinates':
                    # Handle coordinate pairs
                    lat, lon = match.groups()
                    location_text = f"{lat}, {lon}"
                    confidence = 0.95
                else:
                    location_text = match.group(1).strip()
                    confidence = self._calculate_address_confidence(location_text, pattern_name)
                
                if self._is_valid_location(location_text):
                    locations.append(LocationResult(
                        location=location_text,
                        confidence=confidence,
                        location_type=LocationType.ADDRESS,
                        alternatives=[],
                        raw_text=text,
                        extraction_method=f"address_{pattern_name}",
                        position=(match.start(), match.end()),
                        matched_text=match.group(0)
                    ))
        
        return locations
    
    def _extract_context_locations(self, text: str) -> List[LocationResult]:
        """Extract locations using context clues like 'at', 'in', '@'."""
        locations = []
        
        for pattern_name, pattern in self.context_patterns.items():
            for match in pattern.finditer(text):
                location_text = match.group(1).strip()
                
                if self._is_valid_location(location_text):
                    confidence = self._calculate_context_confidence(location_text, pattern_name)
                    location_type = self._determine_location_type(location_text)
                    
                    locations.append(LocationResult(
                        location=location_text,
                        confidence=confidence,
                        location_type=location_type,
                        alternatives=[],
                        raw_text=text,
                        extraction_method=f"context_{pattern_name}",
                        position=(match.start(1), match.end(1)),
                        matched_text=match.group(0)
                    ))
        
        return locations
    
    def _extract_venue_locations(self, text: str) -> List[LocationResult]:
        """Extract venue-based locations using keyword recognition."""
        locations = []
        
        for pattern_name, pattern in self.venue_patterns.items():
            for match in pattern.finditer(text):
                location_text = match.group(1).strip()
                
                if self._is_valid_location(location_text):
                    confidence = self._calculate_venue_confidence(location_text, pattern_name)
                    
                    locations.append(LocationResult(
                        location=location_text,
                        confidence=confidence,
                        location_type=LocationType.VENUE,
                        alternatives=[],
                        raw_text=text,
                        extraction_method=f"venue_{pattern_name}",
                        position=(match.start(1), match.end(1)),
                        matched_text=match.group(0)
                    ))
        
        return locations
    
    def _extract_implicit_locations(self, text: str) -> List[LocationResult]:
        """Extract implicit location references."""
        locations = []
        
        for pattern_name, pattern in self.implicit_patterns.items():
            for match in pattern.finditer(text):
                location_text = match.group(1).strip()
                
                if self._is_valid_location(location_text):
                    confidence = self._calculate_implicit_confidence(location_text, pattern_name)
                    
                    locations.append(LocationResult(
                        location=location_text,
                        confidence=confidence,
                        location_type=LocationType.IMPLICIT,
                        alternatives=[],
                        raw_text=text,
                        extraction_method=f"implicit_{pattern_name}",
                        position=(match.start(1), match.end(1)),
                        matched_text=match.group(0)
                    ))
        
        return locations
    
    def _extract_directional_locations(self, text: str) -> List[LocationResult]:
        """Extract directional location references."""
        locations = []
        
        for pattern_name, pattern in self.directional_patterns.items():
            for match in pattern.finditer(text):
                location_text = match.group(1).strip()
                
                if self._is_valid_location(location_text):
                    confidence = self._calculate_directional_confidence(location_text, pattern_name)
                    
                    locations.append(LocationResult(
                        location=location_text,
                        confidence=confidence,
                        location_type=LocationType.DIRECTIONAL,
                        alternatives=[],
                        raw_text=text,
                        extraction_method=f"directional_{pattern_name}",
                        position=(match.start(1), match.end(1)),
                        matched_text=match.group(0)
                    ))
        
        return locations
    
    def _process_location_matches(self, text: str, locations: List[LocationResult]) -> List[LocationResult]:
        """
        Process location matches to remove overlaps, combine related locations,
        and detect alternatives for ambiguous cases.
        """
        if not locations:
            return locations
        
        # Step 1: Combine addresses with postal codes
        combined_locations = self._combine_addresses_with_postal_codes(text, locations)
        
        # Step 2: Remove overlapping matches (keep highest confidence)
        filtered_locations = self._remove_overlapping_locations(combined_locations)
        
        # Step 3: Detect alternatives for ambiguous cases
        processed_locations = self._detect_location_alternatives(filtered_locations)
        
        return processed_locations
    
    def _combine_addresses_with_postal_codes(self, text: str, locations: List[LocationResult]) -> List[LocationResult]:
        """Combine street addresses with nearby postal codes."""
        combined = []
        used_indices = set()
        
        for i, location in enumerate(locations):
            if i in used_indices:
                continue
            
            if (location.location_type == LocationType.ADDRESS and 
                'street_address' in location.extraction_method):
                
                # Look for nearby postal code
                best_postal = None
                best_distance = float('inf')
                
                for j, other_location in enumerate(locations):
                    if (j != i and j not in used_indices and 
                        'postal_code' in other_location.extraction_method):
                        
                        distance = abs(location.position[1] - other_location.position[0])
                        if distance < 50 and distance < best_distance:
                            best_distance = distance
                            best_postal = (j, other_location)
                
                if best_postal:
                    j, postal_location = best_postal
                    
                    # Combine address and postal code
                    combined_text = f"{location.location}, {postal_location.location}"
                    combined_start = min(location.position[0], postal_location.position[0])
                    combined_end = max(location.position[1], postal_location.position[1])
                    
                    combined_location = LocationResult(
                        location=combined_text,
                        confidence=max(location.confidence, postal_location.confidence),
                        location_type=LocationType.ADDRESS,
                        alternatives=[],
                        raw_text=text,
                        extraction_method="combined_address_postal",
                        position=(combined_start, combined_end),
                        matched_text=text[combined_start:combined_end]
                    )
                    
                    combined.append(combined_location)
                    used_indices.add(i)
                    used_indices.add(j)
                else:
                    combined.append(location)
                    used_indices.add(i)
            else:
                combined.append(location)
                used_indices.add(i)
        
        return combined
    
    def _remove_overlapping_locations(self, locations: List[LocationResult]) -> List[LocationResult]:
        """Remove overlapping location matches, keeping highest confidence."""
        if not locations:
            return locations
        
        # Sort by confidence (highest first)
        sorted_locations = sorted(locations, key=lambda x: x.confidence, reverse=True)
        
        filtered = []
        for location in sorted_locations:
            # Check if this location overlaps with any already accepted
            overlaps = False
            for accepted in filtered:
                if self._locations_overlap(location, accepted):
                    overlaps = True
                    break
            
            if not overlaps:
                filtered.append(location)
        
        return filtered
    
    def _detect_location_alternatives(self, locations: List[LocationResult]) -> List[LocationResult]:
        """Detect alternative locations for ambiguous cases."""
        if len(locations) <= 1:
            return locations
        
        # Group locations by similarity and add as alternatives
        processed = []
        
        for i, location in enumerate(locations):
            alternatives = []
            
            # Find similar locations that could be alternatives
            for j, other_location in enumerate(locations):
                if i != j and self._are_location_alternatives(location, other_location):
                    alternatives.append(other_location.location)
            
            # Create new location result with alternatives
            location_with_alternatives = LocationResult(
                location=location.location,
                confidence=location.confidence,
                location_type=location.location_type,
                alternatives=alternatives,
                raw_text=location.raw_text,
                extraction_method=location.extraction_method,
                position=location.position,
                matched_text=location.matched_text
            )
            
            processed.append(location_with_alternatives)
        
        return processed
    
    def _calculate_address_confidence(self, location: str, pattern_type: str) -> float:
        """Calculate confidence for address-based locations."""
        confidence = 0.7  # Base confidence for addresses
        
        # Pattern-specific adjustments
        pattern_scores = {
            'street_address': 0.95,
            'named_address': 0.90,
            'postal_code': 0.85,
            'coordinates': 0.95
        }
        confidence = pattern_scores.get(pattern_type, 0.7)
        
        # Length and content adjustments
        if 10 <= len(location) <= 100:
            confidence += 0.05
        
        # Check for address indicators
        location_lower = location.lower()
        if any(indicator in location_lower for indicator in self.quality_indicators['high_quality']):
            confidence += 0.1
        
        # Canadian city bonus
        if any(city in location_lower for city in self.canadian_cities):
            confidence += 0.1
        
        # Postal code pattern bonus
        if re.search(r'[a-z]\d[a-z]\s*\d[a-z]\d', location_lower):
            confidence += 0.15
        
        return min(1.0, max(0.1, confidence))
    
    def _calculate_context_confidence(self, location: str, pattern_type: str) -> float:
        """Calculate confidence for context-based locations."""
        confidence = 0.6  # Base confidence for context clues
        
        # Pattern-specific adjustments
        pattern_scores = {
            'at_symbol': 0.95,
            'at_location': 0.85,
            'location_colon': 0.90,
            'venue_colon': 0.90,
            'address_colon': 0.95,
            'meet_at': 0.80,
            'in_location': 0.70
        }
        confidence = pattern_scores.get(pattern_type, 0.6)
        
        # Content-based adjustments
        location_lower = location.lower()
        
        # Venue keyword bonus
        all_venue_keywords = []
        for category in self.venue_keywords.values():
            all_venue_keywords.extend(category)
        
        if any(keyword in location_lower for keyword in all_venue_keywords):
            confidence += 0.15
        
        # Quality indicator bonus
        if any(indicator in location_lower for indicator in self.quality_indicators['high_quality']):
            confidence += 0.1
        elif any(indicator in location_lower for indicator in self.quality_indicators['medium_quality']):
            confidence += 0.05
        
        # Length adjustment
        if 3 <= len(location) <= 50:
            confidence += 0.05
        elif len(location) > 50:
            confidence -= 0.1
        
        return min(1.0, max(0.1, confidence))
    
    def _calculate_venue_confidence(self, location: str, pattern_type: str) -> float:
        """Calculate confidence for venue-based locations."""
        confidence = 0.8  # Base confidence for venue patterns
        
        # Pattern-specific adjustments
        pattern_scores = {
            'room_patterns': 0.90,
            'building_patterns': 0.85,
            'floor_patterns': 0.80,
            'office_patterns': 0.85
        }
        confidence = pattern_scores.get(pattern_type, 0.8)
        
        # Content adjustments
        location_lower = location.lower()
        
        # Room/office number bonus
        if re.search(r'\d+', location):
            confidence += 0.05
        
        # Specific venue type bonus
        venue_types = ['conference', 'meeting', 'board', 'class', 'lecture']
        if any(vtype in location_lower for vtype in venue_types):
            confidence += 0.1
        
        return min(1.0, max(0.1, confidence))
    
    def _calculate_implicit_confidence(self, location: str, pattern_type: str) -> float:
        """Calculate confidence for implicit locations."""
        confidence = 0.5  # Base confidence for implicit locations
        
        # Pattern-specific adjustments
        pattern_scores = {
            'workplace': 0.70,
            'educational': 0.75,
            'home': 0.60,
            'generic_places': 0.65
        }
        confidence = pattern_scores.get(pattern_type, 0.5)
        
        # Content adjustments
        location_lower = location.lower()
        
        # Specificity bonus
        if 'the' in location_lower:
            confidence += 0.05
        
        # Common place bonus
        common_places = ['office', 'school', 'gym', 'library', 'hospital']
        if any(place in location_lower for place in common_places):
            confidence += 0.1
        
        return min(1.0, max(0.1, confidence))
    
    def _calculate_directional_confidence(self, location: str, pattern_type: str) -> float:
        """Calculate confidence for directional locations."""
        confidence = 0.6  # Base confidence for directional locations
        
        # Pattern-specific adjustments
        pattern_scores = {
            'entrance_directions': 0.75,
            'relative_directions': 0.65,
            'floor_directions': 0.80,
            'area_directions': 0.70
        }
        confidence = pattern_scores.get(pattern_type, 0.6)
        
        # Content adjustments
        location_lower = location.lower()
        
        # Specific direction bonus
        specific_directions = ['front', 'back', 'main', 'entrance', 'lobby', 'floor']
        if any(direction in location_lower for direction in specific_directions):
            confidence += 0.1
        
        return min(1.0, max(0.1, confidence))
    
    def _determine_location_type(self, location: str) -> LocationType:
        """Determine the type of location based on content."""
        location_lower = location.lower()
        
        # Check for address indicators first (most specific)
        address_indicators = ['street', 'avenue', 'road', 'drive', 'lane', 'boulevard', 'square', 'plaza']
        if any(indicator in location_lower for indicator in address_indicators):
            return LocationType.ADDRESS
        
        # Check for directional indicators (before venue to catch "front entrance" etc.)
        directional_indicators = ['front', 'back', 'entrance', 'lobby', 'upstairs', 'downstairs', 'by the', 'at the', 'near the']
        if any(indicator in location_lower for indicator in directional_indicators):
            return LocationType.DIRECTIONAL
        
        # Check for venue indicators
        venue_indicators = ['room', 'hall', 'center', 'centre', 'building', 'floor', 'conference', 'meeting']
        if any(indicator in location_lower for indicator in venue_indicators):
            return LocationType.VENUE
        
        # Check for implicit location indicators
        implicit_indicators = ['office', 'school', 'home', 'work', 'downtown', 'gym', 'library']
        if any(indicator in location_lower for indicator in implicit_indicators):
            return LocationType.IMPLICIT
        
        # Default to implicit
        return LocationType.IMPLICIT
    
    def _is_valid_location(self, location: str) -> bool:
        """Check if extracted text is a valid location candidate."""
        if not location or len(location.strip()) < 2:
            return False
        
        # Must contain some letters
        if not re.search(r'[a-zA-Z]', location):
            return False
        
        # Not too long
        if len(location) > 150:
            return False
        
        # Exclude common non-location words
        location_lower = location.lower().strip()
        excluded_words = {
            'the', 'and', 'or', 'but', 'with', 'for', 'from', 'to', 'of', 'in', 'on', 'at',
            'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had',
            'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might',
            'must', 'can', 'today', 'tomorrow', 'yesterday', 'now', 'then'
        }
        
        if location_lower in excluded_words:
            return False
        
        return True
    
    def _locations_overlap(self, loc1: LocationResult, loc2: LocationResult) -> bool:
        """Check if two location results overlap in the text."""
        start1, end1 = loc1.position
        start2, end2 = loc2.position
        
        return start1 < end2 and start2 < end1
    
    def _are_location_alternatives(self, loc1: LocationResult, loc2: LocationResult) -> bool:
        """Check if two locations could be alternatives of each other."""
        # Different extraction methods but similar confidence
        if (abs(loc1.confidence - loc2.confidence) < 0.2 and 
            loc1.extraction_method != loc2.extraction_method):
            return True
        
        # Same location type but different specific locations
        if (loc1.location_type == loc2.location_type and 
            loc1.location.lower() != loc2.location.lower()):
            return True
        
        return False
    
    def get_best_location(self, text: str) -> Optional[LocationResult]:
        """
        Get the single best location from the text.
        
        Args:
            text: Input text to analyze
            
        Returns:
            Best LocationResult or None if no valid location found
        """
        locations = self.extract_locations(text)
        return locations[0] if locations else None
    
    def prioritize_locations(self, locations: List[LocationResult]) -> List[LocationResult]:
        """
        Prioritize locations based on type, confidence, and quality.
        
        Args:
            locations: List of LocationResult objects
            
        Returns:
            Sorted list with highest priority locations first
        """
        def priority_score(location: LocationResult) -> float:
            score = location.confidence
            
            # Type-based priority adjustments
            type_bonuses = {
                LocationType.ADDRESS: 0.15,
                LocationType.VENUE: 0.05,
                LocationType.DIRECTIONAL: 0.02,
                LocationType.IMPLICIT: 0.0
            }
            score += type_bonuses.get(location.location_type, 0.0)
            
            # Method-based adjustments
            if 'address' in location.extraction_method:
                score += 0.05
            elif 'venue' in location.extraction_method:
                score += 0.02
            
            return score
        
        return sorted(locations, key=priority_score, reverse=True)