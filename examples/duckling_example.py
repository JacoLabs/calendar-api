#!/usr/bin/env python3
"""
Example usage of DucklingExtractor for deterministic date/time parsing.

This example demonstrates how to use the DucklingExtractor as a backup
parsing method when regex-based extraction fails.

Requirements:
- Duckling service running on localhost:8000
- Install Duckling: stack install duckling && duckling-example-exe

Usage:
    python examples/duckling_example.py
"""

import sys
import os
from datetime import datetime

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.duckling_extractor import DucklingExtractor


def main():
    """Demonstrate Duckling extraction capabilities."""
    print("Duckling Extractor Example")
    print("=" * 40)
    
    # Initialize extractor
    extractor = DucklingExtractor(
        duckling_url="http://localhost:8000/parse",
        timeout_seconds=3,
        default_timezone="UTC"
    )
    
    # Check if service is available
    print(f"Duckling service available: {extractor.is_service_available()}")
    print()
    
    # Test cases for different types of date/time expressions
    test_cases = [
        ("tomorrow at 3pm", "start_datetime"),
        ("next Friday from 2 to 4", "start_datetime"),
        ("in 2 hours", "start_datetime"),
        ("for 30 minutes", "duration"),
        ("until noon", "end_datetime"),
        ("every Tuesday", "start_datetime"),
        ("January 15th at 9am", "start_datetime"),
        ("2024-03-15 14:30", "start_datetime"),
    ]
    
    print("Testing various date/time expressions:")
    print("-" * 40)
    
    for text, field in test_cases:
        print(f"Text: '{text}' (field: {field})")
        
        result = extractor.extract_with_duckling(text, field)
        
        print(f"  Value: {result.value}")
        print(f"  Source: {result.source}")
        print(f"  Confidence: {result.confidence:.3f}")
        print(f"  Span: {result.span}")
        print(f"  Processing time: {result.processing_time_ms}ms")
        
        if result.alternatives:
            print(f"  Alternatives: {result.alternatives}")
        
        # Validate timezone if it's a datetime result
        if result.value and isinstance(result.value, datetime):
            is_valid_tz = extractor.validate_timezone_normalization(result)
            print(f"  Timezone valid: {is_valid_tz}")
        
        print()
    
    # Test multiple field extraction
    print("Testing multiple field extraction:")
    print("-" * 40)
    
    text = "Meeting tomorrow from 2pm to 4pm"
    fields = ["start_datetime", "end_datetime"]
    
    results = extractor.extract_multiple_fields(text, fields)
    
    print(f"Text: '{text}'")
    for field, result in results.items():
        print(f"  {field}: {result.value} (confidence: {result.confidence:.3f})")
    
    print()
    
    # Demonstrate confidence scoring
    print("Confidence scoring examples:")
    print("-" * 40)
    
    confidence_tests = [
        "3pm",  # High coverage, specific time
        "tomorrow at 3pm in the conference room",  # Lower coverage
        "sometime next week",  # Vague, low confidence expected
        "2024-01-15T15:00:00Z",  # ISO format, should be high confidence
    ]
    
    for text in confidence_tests:
        result = extractor.extract_with_duckling(text, "start_datetime")
        print(f"'{text}' -> confidence: {result.confidence:.3f}")
    
    print()
    print("Example completed!")


if __name__ == "__main__":
    main()