"""
Unit tests for the LocationResult data model and confidence scoring functionality.
"""

import unittest
from services.advanced_location_extractor import LocationResult, LocationType


class TestLocationResult(unittest.TestCase):
    """Test cases for LocationResult data model functionality."""
    
    def test_location_result_creation(self):
        """Test basic LocationResult creation and properties."""
        location_result = LocationResult(
            location="CN Tower",
            confidence=0.95,
            location_type=LocationType.ADDRESS,
            alternatives=["Toronto Tower"],
            raw_text="Meeting at CN Tower tomorrow",
            extraction_method="context_at_location",
            position=(11, 19),
            matched_text="CN Tower"
        )
        
        self.assertEqual(location_result.location, "CN Tower")
        self.assertEqual(location_result.confidence, 0.95)
        self.assertEqual(location_result.location_type, LocationType.ADDRESS)
        self.assertEqual(location_result.alternatives, ["Toronto Tower"])
        self.assertEqual(location_result.raw_text, "Meeting at CN Tower tomorrow")
        self.assertEqual(location_result.extraction_method, "context_at_location")
        self.assertEqual(location_result.position, (11, 19))
        self.assertEqual(location_result.matched_text, "CN Tower")
    
    def test_location_result_serialization(self):
        """Test LocationResult to_dict and from_dict methods."""
        original = LocationResult(
            location="Nathan Phillips Square",
            confidence=0.88,
            location_type=LocationType.VENUE,
            alternatives=["City Hall Square", "Toronto Square"],
            raw_text="Event at Nathan Phillips Square on Friday",
            extraction_method="address_named_location",
            position=(9, 30),
            matched_text="Nathan Phillips Square"
        )
        
        # Test serialization
        data = original.to_dict()
        
        expected_keys = {
            'location', 'confidence', 'location_type', 'alternatives',
            'raw_text', 'extraction_method', 'position', 'matched_text'
        }
        self.assertEqual(set(data.keys()), expected_keys)
        
        self.assertEqual(data['location'], "Nathan Phillips Square")
        self.assertEqual(data['confidence'], 0.88)
        self.assertEqual(data['location_type'], "venue")  # Enum value
        self.assertEqual(data['alternatives'], ["City Hall Square", "Toronto Square"])
        self.assertEqual(data['position'], (9, 30))
        
        # Test deserialization
        restored = LocationResult.from_dict(data)
        
        self.assertEqual(restored.location, original.location)
        self.assertEqual(restored.confidence, original.confidence)
        self.assertEqual(restored.location_type, original.location_type)
        self.assertEqual(restored.alternatives, original.alternatives)
        self.assertEqual(restored.raw_text, original.raw_text)
        self.assertEqual(restored.extraction_method, original.extraction_method)
        self.assertEqual(restored.position, original.position)
        self.assertEqual(restored.matched_text, original.matched_text)
    
    def test_location_result_with_empty_alternatives(self):
        """Test LocationResult with empty alternatives list."""
        location_result = LocationResult(
            location="Conference Room A",
            confidence=0.92,
            location_type=LocationType.VENUE,
            alternatives=[],  # Empty alternatives
            raw_text="Meeting in Conference Room A",
            extraction_method="venue_room_patterns",
            position=(11, 27),
            matched_text="Conference Room A"
        )
        
        self.assertEqual(location_result.alternatives, [])
        
        # Test serialization with empty alternatives
        data = location_result.to_dict()
        self.assertEqual(data['alternatives'], [])
        
        # Test deserialization with empty alternatives
        restored = LocationResult.from_dict(data)
        self.assertEqual(restored.alternatives, [])
    
    def test_location_result_confidence_validation(self):
        """Test that confidence scores are handled correctly."""
        # Test various confidence levels
        confidence_levels = [0.0, 0.25, 0.5, 0.75, 1.0]
        
        for confidence in confidence_levels:
            with self.subTest(confidence=confidence):
                location_result = LocationResult(
                    location="Test Location",
                    confidence=confidence,
                    location_type=LocationType.IMPLICIT,
                    alternatives=[],
                    raw_text="Test text",
                    extraction_method="test_method",
                    position=(0, 13),
                    matched_text="Test Location"
                )
                
                self.assertEqual(location_result.confidence, confidence)
                
                # Test serialization preserves confidence
                data = location_result.to_dict()
                self.assertEqual(data['confidence'], confidence)
                
                # Test deserialization preserves confidence
                restored = LocationResult.from_dict(data)
                self.assertEqual(restored.confidence, confidence)
    
    def test_location_type_enum_handling(self):
        """Test that LocationType enum is handled correctly."""
        location_types = [
            LocationType.ADDRESS,
            LocationType.VENUE,
            LocationType.IMPLICIT,
            LocationType.DIRECTIONAL
        ]
        
        for location_type in location_types:
            with self.subTest(location_type=location_type):
                location_result = LocationResult(
                    location="Test Location",
                    confidence=0.8,
                    location_type=location_type,
                    alternatives=[],
                    raw_text="Test text",
                    extraction_method="test_method",
                    position=(0, 13),
                    matched_text="Test Location"
                )
                
                self.assertEqual(location_result.location_type, location_type)
                
                # Test serialization converts enum to string
                data = location_result.to_dict()
                self.assertEqual(data['location_type'], location_type.value)
                
                # Test deserialization converts string back to enum
                restored = LocationResult.from_dict(data)
                self.assertEqual(restored.location_type, location_type)
    
    def test_location_result_with_multiple_alternatives(self):
        """Test LocationResult with multiple alternative locations."""
        alternatives = [
            "Royal Ontario Museum",
            "ROM",
            "Toronto Museum",
            "Ontario Museum"
        ]
        
        location_result = LocationResult(
            location="ROM Building",
            confidence=0.75,
            location_type=LocationType.VENUE,
            alternatives=alternatives,
            raw_text="Visit at ROM Building this weekend",
            extraction_method="venue_building_patterns",
            position=(9, 21),
            matched_text="ROM Building"
        )
        
        self.assertEqual(location_result.alternatives, alternatives)
        self.assertEqual(len(location_result.alternatives), 4)
        
        # Test serialization with multiple alternatives
        data = location_result.to_dict()
        self.assertEqual(data['alternatives'], alternatives)
        
        # Test deserialization with multiple alternatives
        restored = LocationResult.from_dict(data)
        self.assertEqual(restored.alternatives, alternatives)
    
    def test_location_result_position_tracking(self):
        """Test that position information is tracked correctly."""
        test_cases = [
            ((0, 10), "start of text"),
            ((15, 25), "middle of text"),
            ((50, 65), "end of text"),
            ((0, 0), "empty position"),
        ]
        
        for position, description in test_cases:
            with self.subTest(position=position, description=description):
                location_result = LocationResult(
                    location="Test Location",
                    confidence=0.8,
                    location_type=LocationType.IMPLICIT,
                    alternatives=[],
                    raw_text="Test text with location information",
                    extraction_method="test_method",
                    position=position,
                    matched_text="Test Location"
                )
                
                self.assertEqual(location_result.position, position)
                
                # Test serialization preserves position
                data = location_result.to_dict()
                self.assertEqual(data['position'], position)
                
                # Test deserialization preserves position
                restored = LocationResult.from_dict(data)
                self.assertEqual(restored.position, position)
    
    def test_location_result_extraction_method_tracking(self):
        """Test that extraction method is tracked correctly."""
        extraction_methods = [
            "context_at_location",
            "address_street_address",
            "venue_room_patterns",
            "implicit_workplace",
            "directional_entrance_directions",
            "combined_address_postal"
        ]
        
        for method in extraction_methods:
            with self.subTest(method=method):
                location_result = LocationResult(
                    location="Test Location",
                    confidence=0.8,
                    location_type=LocationType.IMPLICIT,
                    alternatives=[],
                    raw_text="Test text",
                    extraction_method=method,
                    position=(0, 13),
                    matched_text="Test Location"
                )
                
                self.assertEqual(location_result.extraction_method, method)
                
                # Test serialization preserves extraction method
                data = location_result.to_dict()
                self.assertEqual(data['extraction_method'], method)
                
                # Test deserialization preserves extraction method
                restored = LocationResult.from_dict(data)
                self.assertEqual(restored.extraction_method, method)
    
    def test_location_result_raw_text_preservation(self):
        """Test that raw text is preserved for debugging purposes."""
        raw_texts = [
            "Meeting at CN Tower tomorrow at 2pm",
            "Let's meet @ Starbucks on King Street",
            "Conference in Room 205, Building A",
            "Lunch downtown near the office",
            ""  # Empty raw text
        ]
        
        for raw_text in raw_texts:
            with self.subTest(raw_text=raw_text):
                location_result = LocationResult(
                    location="Test Location",
                    confidence=0.8,
                    location_type=LocationType.IMPLICIT,
                    alternatives=[],
                    raw_text=raw_text,
                    extraction_method="test_method",
                    position=(0, 13),
                    matched_text="Test Location"
                )
                
                self.assertEqual(location_result.raw_text, raw_text)
                
                # Test serialization preserves raw text
                data = location_result.to_dict()
                self.assertEqual(data['raw_text'], raw_text)
                
                # Test deserialization preserves raw text
                restored = LocationResult.from_dict(data)
                self.assertEqual(restored.raw_text, raw_text)
    
    def test_location_result_edge_cases(self):
        """Test LocationResult with edge cases and boundary values."""
        # Test with None location
        location_result = LocationResult(
            location=None,
            confidence=0.0,
            location_type=LocationType.IMPLICIT,
            alternatives=[],
            raw_text="No location found",
            extraction_method="no_match",
            position=(0, 0),
            matched_text=""
        )
        
        self.assertIsNone(location_result.location)
        self.assertEqual(location_result.confidence, 0.0)
        
        # Test serialization with None location
        data = location_result.to_dict()
        self.assertIsNone(data['location'])
        
        # Test deserialization with None location
        restored = LocationResult.from_dict(data)
        self.assertIsNone(restored.location)
    
    def test_location_result_comparison_for_sorting(self):
        """Test that LocationResult objects can be used for sorting by confidence."""
        locations = [
            LocationResult(
                location="Low Confidence",
                confidence=0.3,
                location_type=LocationType.IMPLICIT,
                alternatives=[],
                raw_text="",
                extraction_method="test",
                position=(0, 0),
                matched_text=""
            ),
            LocationResult(
                location="High Confidence",
                confidence=0.9,
                location_type=LocationType.ADDRESS,
                alternatives=[],
                raw_text="",
                extraction_method="test",
                position=(0, 0),
                matched_text=""
            ),
            LocationResult(
                location="Medium Confidence",
                confidence=0.6,
                location_type=LocationType.VENUE,
                alternatives=[],
                raw_text="",
                extraction_method="test",
                position=(0, 0),
                matched_text=""
            )
        ]
        
        # Sort by confidence (highest first)
        sorted_locations = sorted(locations, key=lambda x: x.confidence, reverse=True)
        
        self.assertEqual(sorted_locations[0].location, "High Confidence")
        self.assertEqual(sorted_locations[1].location, "Medium Confidence")
        self.assertEqual(sorted_locations[2].location, "Low Confidence")
        
        # Verify confidence values are in descending order
        confidences = [loc.confidence for loc in sorted_locations]
        self.assertEqual(confidences, sorted(confidences, reverse=True))


if __name__ == '__main__':
    unittest.main()