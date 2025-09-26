#!/usr/bin/env python3
"""
Demonstration of advanced parsing features and error handling.
Shows ambiguity detection, multiple event parsing, and fallback mechanisms.
"""

import os
from services.event_parser import EventParser
from models.event_models import ParsedEvent


def demo_ambiguity_detection():
    """Demonstrate ambiguity detection and resolution."""
    print("=" * 60)
    print("AMBIGUITY DETECTION DEMO")
    print("=" * 60)
    
    parser = EventParser()
    
    # Example with multiple possible dates
    ambiguous_texts = [
        "Meeting on 3/4/2024 at 2pm or maybe 4/3/2024 at 3pm",
        "Call with John or Sarah tomorrow at 2pm or 3pm",
        "Team meeting or project review next Friday at the office or remotely"
    ]
    
    for text in ambiguous_texts:
        print(f"\nParsing: '{text}'")
        
        # Set non-interactive mode for demo
        os.environ['NON_INTERACTIVE'] = '1'
        
        parsed_event = parser.parse_with_clarification(text)
        ambiguities = parser._detect_ambiguities(text, parsed_event)
        
        print(f"  Detected {len(ambiguities)} ambiguities:")
        for amb in ambiguities:
            print(f"    - {amb['type']}: {amb['message']}")
        
        print(f"  Final result: {parsed_event.title} at {parsed_event.start_datetime}")
        print(f"  Confidence: {parsed_event.confidence_score:.2f}")


def demo_multiple_event_detection():
    """Demonstrate multiple event detection and parsing."""
    print("\n" + "=" * 60)
    print("MULTIPLE EVENT DETECTION DEMO")
    print("=" * 60)
    
    parser = EventParser()
    
    multi_event_texts = [
        "Team standup at 9am. Client call at 2pm. Code review at 4pm.",
        """
        • Morning meeting at 9:00 AM
        • Lunch with team at 12:00 PM  
        • Afternoon review at 3:00 PM
        """,
        "Meeting tomorrow at 2pm then call with client at 4pm",
        "1. Interview at 10am\n2. Lunch at 12pm\n3. Presentation at 3pm"
    ]
    
    for text in multi_event_texts:
        print(f"\nParsing: '{text.strip()}'")
        
        # Detect potential events
        potential_events = parser._detect_multiple_events(text)
        print(f"  Detected {len(potential_events)} potential events:")
        for i, event_text in enumerate(potential_events, 1):
            print(f"    {i}. '{event_text.strip()}'")
        
        # Parse as multiple events (non-interactive)
        os.environ['NON_INTERACTIVE'] = '1'
        events = parser.parse_multiple_with_detection(text)
        
        print(f"  Parsed into {len(events)} events:")
        for i, event in enumerate(events, 1):
            print(f"    {i}. {event.title} at {event.start_datetime} (confidence: {event.confidence_score:.2f})")


def demo_fallback_mechanisms():
    """Demonstrate fallback mechanisms for failed parsing."""
    print("\n" + "=" * 60)
    print("FALLBACK MECHANISMS DEMO")
    print("=" * 60)
    
    parser = EventParser()
    
    difficult_texts = [
        "something unclear and vague",
        "xyz abc def",
        "The weather is nice today",
        "Random text without clear event information",
        "Meeting yesterday at tomorrow 25:00"  # Conflicting info
    ]
    
    for text in difficult_texts:
        print(f"\nParsing difficult text: '{text}'")
        
        # Try normal parsing first
        normal_result = parser.parse_text(text)
        print(f"  Normal parsing confidence: {normal_result.confidence_score:.2f}")
        
        # Try with fallback
        os.environ['NON_INTERACTIVE'] = '1'
        fallback_result = parser.parse_with_fallback(text)
        
        print(f"  Fallback result: {fallback_result.title}")
        print(f"  Fallback confidence: {fallback_result.confidence_score:.2f}")
        print(f"  Start time: {fallback_result.start_datetime}")


def demo_error_recovery():
    """Demonstrate error recovery in edge cases."""
    print("\n" + "=" * 60)
    print("ERROR RECOVERY DEMO")
    print("=" * 60)
    
    parser = EventParser()
    
    edge_cases = [
        "",  # Empty text
        "hi",  # Very short text
        "Meeting with café owner at 2pm 🕐",  # Unicode
        "Meeting " + "very " * 100 + "important tomorrow at 2pm",  # Very long
        "Réunion demain à 14h",  # Non-English
        "会议明天下午2点"  # Chinese
    ]
    
    for text in edge_cases:
        display_text = text[:50] + "..." if len(text) > 50 else text
        print(f"\nTesting edge case: '{display_text}'")
        
        try:
            os.environ['NON_INTERACTIVE'] = '1'
            result = parser.parse_with_fallback(text)
            
            print(f"  ✓ Handled gracefully")
            print(f"  Title: {result.title}")
            print(f"  Confidence: {result.confidence_score:.2f}")
            
        except Exception as e:
            print(f"  ✗ Error: {type(e).__name__}: {e}")


def demo_integration_scenarios():
    """Demonstrate integration of all advanced features."""
    print("\n" + "=" * 60)
    print("INTEGRATION SCENARIOS DEMO")
    print("=" * 60)
    
    parser = EventParser()
    
    complex_scenarios = [
        "Team meeting or standup tomorrow at 2pm or 3pm in room A or B, then call with client at 4pm",
        "Interview with John or Sarah on Monday or Tuesday at 10am, followed by lunch at noon",
        "Project review meeting next week sometime in the afternoon, maybe 2pm or 3pm"
    ]
    
    for text in complex_scenarios:
        print(f"\nComplex scenario: '{text}'")
        
        os.environ['NON_INTERACTIVE'] = '1'
        
        # Try multiple event detection first
        events = parser.parse_multiple_with_detection(text)
        
        print(f"  Parsed into {len(events)} events:")
        for i, event in enumerate(events, 1):
            print(f"    {i}. {event.title}")
            print(f"       Time: {event.start_datetime}")
            print(f"       Location: {event.location or 'Not specified'}")
            print(f"       Confidence: {event.confidence_score:.2f}")
            
            # Validate each event
            validation = parser.validate_parsed_event(event)
            if not validation.is_valid:
                print(f"       Issues: {', '.join(validation.warnings)}")
            if validation.suggestions:
                print(f"       Suggestions: {', '.join(validation.suggestions[:2])}")


def main():
    """Run all demonstrations."""
    print("Advanced Event Parser - Feature Demonstration")
    print("This demo shows the advanced parsing features implemented in task 11.")
    
    # Set environment for non-interactive mode
    os.environ['NON_INTERACTIVE'] = '1'
    
    try:
        demo_ambiguity_detection()
        demo_multiple_event_detection()
        demo_fallback_mechanisms()
        demo_error_recovery()
        demo_integration_scenarios()
        
        print("\n" + "=" * 60)
        print("DEMO COMPLETE")
        print("=" * 60)
        print("All advanced parsing features demonstrated successfully!")
        print("\nFeatures implemented:")
        print("✓ Ambiguity detection and resolution")
        print("✓ Multiple event detection and parsing")
        print("✓ Fallback mechanisms for failed parsing")
        print("✓ Error recovery for edge cases")
        print("✓ Integration of all advanced features")
        
    except Exception as e:
        print(f"\nDemo error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Clean up environment
        if 'NON_INTERACTIVE' in os.environ:
            del os.environ['NON_INTERACTIVE']


if __name__ == "__main__":
    main()