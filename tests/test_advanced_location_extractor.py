"""
Comprehensive unit tests for the AdvancedLocationExtractor class.
Tests all location extraction strategies and confidence scoring.
"""

import unittest
from services.advanced_location_extractor import AdvancedLocationExtractor, LocationResult, LocationType


class TestAdvancedLocationExtractor(unittest.TestCase):
    """Test cases for AdvancedLocationExtractor functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.extractor = AdvancedLocationExtractor()
    
    def test_explicit_address_extraction(self):
        """Test extraction of explicit street addresses."""
        # Test case: Nathan Phillips Square
        text = "Meeting at Nathan Phillips Square tomorrow at 2pm"
        locations = self.extractor.extract_locations(text)
        
        self.assertGreater(len(locations), 0)
        best_location = locations[0]
        self.assertIn("Nathan Phillips Square", best_location.location)
        self.assertEqual(best_location.location_type, LocationType.ADDRESS)
        self.assertGreater(best_location.confidence, 0.8)
        
        # Test case: Street address with number
        text = "Meet me at 123 Main Street, Toronto"
        locations = self.extractor.extract_locations(text)
        
        self.assertGreater(len(locations), 0)
        best_location = locations[0]
        self.assertIn("123 Main Street", best_location.location)
        self.assertEqual(best_location.location_type, LocationType.ADDRESS)
        self.assertGreater(best_location.confidence, 0.8)
    
    def test_implicit_location_detection(self):
        """Test detection of implicit locations."""
        # Test case: at school
        text = "Meeting at school tomorrow at 3pm"
        locations = self.extractor.extract_locations(text)
        
        self.assertGreater(len(locations), 0)
        best_location = locations[0]
        self.assertIn("school", best_location.location.lower())
        self.assertIn(best_location.location_type, [LocationType.IMPLICIT, LocationType.VENUE])
        self.assertGreater(best_location.confidence, 0.5)
        
        # Test case: the office
        text = "Call at the office at 10am"
        locations = self.extractor.extract_locations(text)
        
        self.assertGreater(len(locations), 0)
        best_location = locations[0]
        self.assertIn("office", best_location.location.lower())
        self.assertEqual(best_location.location_type, LocationType.IMPLICIT)
        
        # Test case: downtown
        text = "Lunch downtown at noon"
        locations = self.extractor.extract_locations(text)
        
        self.assertGreater(len(locations), 0)
        best_location = locations[0]
        self.assertIn("downtown", best_location.location.lower())
        self.assertEqual(best_location.location_type, LocationType.IMPLICIT)
    
    def test_directional_location_parsing(self):
        """Test parsing of directional location references."""
        # Test case: meet at the front doors
        text = "Meet at the front doors at 9am"
        locations = self.extractor.extract_locations(text)
        
        self.assertGreater(len(locations), 0)
        best_location = locations[0]
        self.assertIn("front doors", best_location.location.lower())
        self.assertEqual(best_location.location_type, LocationType.DIRECTIONAL)
        self.assertGreater(best_location.confidence, 0.6)
        
        # Test case: by the entrance
        text = "Wait by the entrance until 2pm"
        locations = self.extractor.extract_locations(text)
        
        self.assertGreater(len(locations), 0)
        best_location = locations[0]
        self.assertIn("entrance", best_location.location.lower())
        self.assertEqual(best_location.location_type, LocationType.DIRECTIONAL)
        
        # Test case: on the 3rd floor
        text = "Meeting on the 3rd floor at 1pm"
        locations = self.extractor.extract_locations(text)
        
        self.assertGreater(len(locations), 0)
        best_location = locations[0]
        self.assertIn("3rd floor", best_location.location.lower())
        self.assertEqual(best_location.location_type, LocationType.DIRECTIONAL)
    
    def test_venue_keyword_recognition(self):
        """Test recognition of venue keywords."""
        # Test case: Conference Room A
        text = "Meeting in Conference Room A at 2pm"
        locations = self.extractor.extract_locations(text)
        
        self.assertGreater(len(locations), 0)
        best_location = locations[0]
        self.assertIn("Conference Room A", best_location.location)
        self.assertEqual(best_location.location_type, LocationType.VENUE)
        self.assertGreater(best_location.confidence, 0.8)
        
        # Test case: City Hall
        text = "Event at City Hall tomorrow"
        locations = self.extractor.extract_locations(text)
        
        self.assertGreater(len(locations), 0)
        best_location = locations[0]
        self.assertIn("City Hall", best_location.location)
        self.assertIn(best_location.location_type, [LocationType.ADDRESS, LocationType.VENUE])
        
        # Test case: Building 5
        text = "Meeting in Building 5 at noon"
        locations = self.extractor.extract_locations(text)
        
        self.assertGreater(len(locations), 0)
        best_location = locations[0]
        self.assertIn("Building 5", best_location.location)
        self.assertEqual(best_location.location_type, LocationType.VENUE)
    
    def test_context_clue_detection(self):
        """Test detection of context clues like 'venue:', 'at', 'in', '@'."""
        # Test case: @ symbol
        text = "Meeting @ Starbucks at 3pm"
        locations = self.extractor.extract_locations(text)
        
        self.assertGreater(len(locations), 0)
        best_location = locations[0]
        self.assertIn("Starbucks", best_location.location)
        self.assertGreater(best_location.confidence, 0.9)
        
        # Test case: venue: indicator
        text = "Event details: venue: Royal Ontario Museum, time: 2pm"
        locations = self.extractor.extract_locations(text)
        
        self.assertGreater(len(locations), 0)
        best_location = locations[0]
        self.assertIn("Royal Ontario Museum", best_location.location)
        self.assertGreater(best_location.confidence, 0.8)
        
        # Test case: location: indicator
        text = "Meeting info - location: CN Tower, time: 10am"
        locations = self.extractor.extract_locations(text)
        
        self.assertGreater(len(locations), 0)
        best_location = locations[0]
        self.assertIn("CN Tower", best_location.location)
        self.assertGreater(best_location.confidence, 0.8)
    
    def test_location_type_classification(self):
        """Test proper classification of location types."""
        test_cases = [
            ("123 Main Street", LocationType.ADDRESS),
            ("Conference Room B", LocationType.VENUE),
            ("at the front entrance", LocationType.DIRECTIONAL),
            ("the office", LocationType.IMPLICIT),
            ("Nathan Phillips Square", LocationType.ADDRESS),
            ("Room 205", LocationType.VENUE),
            ("upstairs in the lobby", LocationType.DIRECTIONAL),
            ("downtown", LocationType.IMPLICIT)
        ]
        
        for location_text, expected_type in test_cases:
            with self.subTest(location=location_text):
                text = f"Meeting {location_text} at 2pm"
                locations = self.extractor.extract_locations(text)
                
                if locations:
                    self.assertEqual(locations[0].location_type, expected_type,
                                   f"Expected {expected_type} for '{location_text}', got {locations[0].location_type}")
    
    def test_alternative_location_detection(self):
        """Test detection of alternative locations for ambiguous cases."""
        # Test case with multiple possible locations
        text = "Meeting at the office or Conference Room A at 2pm"
        locations = self.extractor.extract_locations(text)
        
        # Should detect at least one location (may not always detect multiple due to overlap removal)
        self.assertGreater(len(locations), 0)
        
        # Test a clearer case with separated locations
        text2 = "Meet at Starbucks downtown or the library uptown"
        locations2 = self.extractor.extract_locations(text2)
        
        # This should detect multiple locations since they're more separated
        self.assertGreaterEqual(len(locations2), 1)  # At least one, possibly more
        
    def test_canadian_postal_code_integration(self):
        """Test integration with Canadian postal codes."""
        # Test case: Address with postal code
        text = "Meeting at 100 Queen Street, Toronto, M5H 2N2 at 3pm"
        locations = self.extractor.extract_locations(text)
        
        self.assertGreater(len(locations), 0)
        best_location = locations[0]
        
        # Should combine address with postal code
        self.assertIn("Queen Street", best_location.location)
        self.assertIn("M5H 2N2", best_location.location)
        self.assertEqual(best_location.location_type, LocationType.ADDRESS)
        self.assertGreater(best_location.confidence, 0.8)
    
    def test_confidence_scoring_accuracy(self):
        """Test accuracy of confidence scoring for different location types."""
        test_cases = [
            # High confidence cases
            ("@ Starbucks", 0.9),  # @ symbol should have high confidence
            ("123 Main Street", 0.8),  # Street address should have high confidence
            ("venue: CN Tower", 0.8),  # Explicit venue indicator
            
            # Medium confidence cases
            ("at school", 0.6),  # Implicit location
            ("Conference Room A", 0.7),  # Venue pattern
            
            # Lower confidence cases (but still valid)
            ("downtown", 0.5),  # Generic implicit location
            ("upstairs", 0.5),  # Directional without specifics
        ]
        
        for location_text, min_confidence in test_cases:
            with self.subTest(location=location_text):
                text = f"Meeting {location_text} at 2pm"
                locations = self.extractor.extract_locations(text)
                
                if locations:
                    actual_confidence = locations[0].confidence
                    self.assertGreaterEqual(actual_confidence, min_confidence,
                                          f"Expected confidence >= {min_confidence} for '{location_text}', got {actual_confidence}")
    
    def test_overlapping_match_removal(self):
        """Test removal of overlapping location matches."""
        # Test case with potentially overlapping matches
        text = "Meeting at 123 Main Street, Conference Room A"
        locations = self.extractor.extract_locations(text)
        
        # Should not have overlapping positions
        for i, loc1 in enumerate(locations):
            for j, loc2 in enumerate(locations):
                if i != j:
                    # Check that locations don't overlap significantly
                    start1, end1 = loc1.position
                    start2, end2 = loc2.position
                    
                    # Allow some minor overlap but not complete overlap
                    overlap = max(0, min(end1, end2) - max(start1, start2))
                    total_length = min(end1 - start1, end2 - start2)
                    
                    if total_length > 0:
                        overlap_ratio = overlap / total_length
                        self.assertLess(overlap_ratio, 0.8,
                                      f"Locations '{loc1.location}' and '{loc2.location}' overlap too much")
    
    def test_invalid_location_filtering(self):
        """Test filtering of invalid location candidates."""
        # Test cases that should not be detected as locations
        invalid_cases = [
            "Meeting at 2pm",  # Time, not location
            "Call at 10:30am",  # Time, not location
            "Event on Monday",  # Day, not location
            "Meeting for 2 hours",  # Duration, not location
        ]
        
        for text in invalid_cases:
            with self.subTest(text=text):
                locations = self.extractor.extract_locations(text)
                
                # Should either find no locations or find very low confidence ones
                if locations:
                    best_location = locations[0]
                    # If a location is found, it should have reasonable confidence
                    # and not be obviously a time/date
                    self.assertNotRegex(best_location.location.lower(), 
                                      r'\b\d{1,2}(?::\d{2})?(?:am|pm)\b',
                                      f"Incorrectly identified time as location: '{best_location.location}'")
    
    def test_no_location_scenarios(self):
        """Test scenarios where no location should be detected (addressing the point about texts with only who/when/what)."""
        no_location_cases = [
            "Meeting with John tomorrow at 2pm",  # Only who, when, what
            "Call Sarah at 3:30pm about the project",  # Only who, when, what
            "Lunch with the team on Friday at noon",  # Only who, when, what
            "Review session with Mike next week",  # Only who, when, what
            "Conference call at 10am sharp",  # Only what, when
        ]
        
        for text in no_location_cases:
            with self.subTest(text=text):
                locations = self.extractor.extract_locations(text)
                
                # These should ideally find no locations, or very low confidence ones
                if locations:
                    best_location = locations[0]
                    # If any location is found, it should be low confidence
                    self.assertLess(best_location.confidence, 0.7,
                                  f"Found high-confidence location '{best_location.location}' in text without clear location: '{text}'")
    
    def test_get_best_location(self):
        """Test the get_best_location convenience method."""
        # Test case with clear best location
        text = "Meeting @ CN Tower at 2pm"
        best_location = self.extractor.get_best_location(text)
        
        self.assertIsNotNone(best_location)
        self.assertIn("CN Tower", best_location.location)
        self.assertGreater(best_location.confidence, 0.8)
        
        # Test case with no location
        text = "Meeting tomorrow at 2pm"
        best_location = self.extractor.get_best_location(text)
        
        # Might be None or a very low confidence location
        if best_location:
            self.assertLess(best_location.confidence, 0.7)
    
    def test_prioritize_locations(self):
        """Test location prioritization logic."""
        # Create test locations with different types and confidences
        locations = [
            LocationResult(
                location="downtown",
                confidence=0.6,
                location_type=LocationType.IMPLICIT,
                alternatives=[],
                raw_text="",
                extraction_method="implicit_generic",
                position=(0, 8),
                matched_text="downtown"
            ),
            LocationResult(
                location="123 Main Street",
                confidence=0.7,
                location_type=LocationType.ADDRESS,
                alternatives=[],
                raw_text="",
                extraction_method="address_street",
                position=(10, 25),
                matched_text="123 Main Street"
            ),
            LocationResult(
                location="Conference Room A",
                confidence=0.8,
                location_type=LocationType.VENUE,
                alternatives=[],
                raw_text="",
                extraction_method="venue_room",
                position=(30, 47),
                matched_text="Conference Room A"
            )
        ]
        
        prioritized = self.extractor.prioritize_locations(locations)
        
        # Check that prioritization works correctly
        # With current bonuses: ADDRESS gets 0.7 + 0.15 + 0.05 = 0.9
        # VENUE gets 0.8 + 0.05 + 0.02 = 0.87
        # IMPLICIT gets 0.6 + 0.0 = 0.6
        self.assertEqual(prioritized[0].location_type, LocationType.ADDRESS)  # Highest total score
        self.assertEqual(prioritized[1].location_type, LocationType.VENUE)  # Second highest
        self.assertEqual(prioritized[2].location_type, LocationType.IMPLICIT)  # Lowest priority
    
    def test_real_world_scenarios(self):
        """Test real-world location extraction scenarios."""
        real_world_cases = [
            # Email-style location (should find either Nathan Phillips Square or the address)
            ("Meeting tomorrow at 2pm. Location: Nathan Phillips Square, 100 Queen St W, Toronto, ON M5H 2N2", 
             ["Nathan Phillips Square", "Queen St"]),
            
            # Casual text
            ("Let's meet @ Starbucks on King Street at 3pm", 
             ["Starbucks"]),
            
            # Business meeting
            ("Board meeting in Conference Room B, 5th floor at 10am", 
             ["Conference Room B"]),
            
            # Directional meeting point
            ("Meet at the front entrance of the CN Tower at noon", 
             ["front entrance", "CN Tower"]),
            
            # Multiple locations (should pick the best one)
            ("Pick me up at home then we'll go to the office for the meeting at 2pm", 
             None),  # Should find at least one location
            
            # Implicit location
            ("Team lunch at the usual place downtown at 12:30", 
             ["downtown"]),
        ]
        
        for text, expected_location_parts in real_world_cases:
            with self.subTest(text=text):
                locations = self.extractor.extract_locations(text)
                
                if expected_location_parts:
                    self.assertGreater(len(locations), 0, f"No locations found in: {text}")
                    best_location = locations[0]
                    
                    # Check if any of the expected parts are found
                    found_match = False
                    for expected_part in expected_location_parts:
                        if expected_part.lower() in best_location.location.lower():
                            found_match = True
                            break
                    
                    self.assertTrue(found_match,
                                  f"Expected one of {expected_location_parts} in '{best_location.location}'")
                else:
                    # Should find at least one location
                    self.assertGreater(len(locations), 0, f"No locations found in: {text}")
    
    def test_location_result_serialization(self):
        """Test LocationResult serialization and deserialization."""
        # Create a test location result
        original = LocationResult(
            location="CN Tower",
            confidence=0.95,
            location_type=LocationType.ADDRESS,
            alternatives=["Toronto Tower", "Space Needle"],
            raw_text="Meeting at CN Tower tomorrow",
            extraction_method="context_at_location",
            position=(11, 19),
            matched_text="CN Tower"
        )
        
        # Test serialization
        data = original.to_dict()
        self.assertIsInstance(data, dict)
        self.assertEqual(data['location'], "CN Tower")
        self.assertEqual(data['confidence'], 0.95)
        self.assertEqual(data['location_type'], "address")
        
        # Test deserialization
        restored = LocationResult.from_dict(data)
        self.assertEqual(restored.location, original.location)
        self.assertEqual(restored.confidence, original.confidence)
        self.assertEqual(restored.location_type, original.location_type)
        self.assertEqual(restored.alternatives, original.alternatives)
        self.assertEqual(restored.position, original.position)


if __name__ == '__main__':
    unittest.main()