"""
Demonstration of Per-Field Confidence Router functionality.

Shows how the router analyzes text and makes routing decisions for optimal processing.
"""

from services.per_field_confidence_router import PerFieldConfidenceRouter, ProcessingMethod
import json


def demo_field_analysis():
    """Demonstrate field analysis capabilities."""
    print("=== Per-Field Confidence Router Demo ===\n")
    
    router = PerFieldConfidenceRouter()
    
    # Test cases with different complexity levels
    test_cases = [
        {
            'name': 'Simple Meeting',
            'text': 'Team meeting tomorrow at 2pm'
        },
        {
            'name': 'Detailed Event',
            'text': 'Annual Sales Conference on October 15, 2025 from 9:00 AM to 5:00 PM at Convention Center with john.doe@company.com'
        },
        {
            'name': 'Email Format',
            'text': '''
            Subject: Q4 Planning Session
            
            Hi team,
            
            We need to schedule our quarterly planning meeting for next Friday,
            October 15th from 2:00 PM to 4:30 PM in the main conference room.
            
            This will be a recurring monthly meeting going forward.
            '''
        },
        {
            'name': 'Ambiguous Text',
            'text': 'Meeting at 2pm or 3pm tomorrow or next week in room A or B'
        }
    ]
    
    for case in test_cases:
        print(f"--- {case['name']} ---")
        print(f"Text: {case['text'][:100]}{'...' if len(case['text']) > 100 else ''}")
        print()
        
        # Analyze field extractability
        analyses = router.analyze_field_extractability(case['text'])
        
        if not analyses:
            print("No fields detected for analysis.\n")
            continue
        
        # Show field analysis results
        print("Field Analysis:")
        for field_name, analysis in analyses.items():
            print(f"  {field_name}:")
            print(f"    Confidence: {analysis.confidence_potential:.2f}")
            print(f"    Method: {analysis.recommended_method.value}")
            print(f"    Priority: {analysis.processing_priority}")
            print(f"    Patterns: {analysis.pattern_matches}")
            if analysis.ambiguity_indicators:
                print(f"    Ambiguities: {analysis.ambiguity_indicators}")
            print()
        
        # Show processing order optimization
        field_names = list(analyses.keys())
        optimized_order = router.optimize_processing_order(field_names)
        print(f"Optimized Processing Order: {' → '.join(optimized_order)}")
        
        # Show routing summary
        summary = router.get_field_routing_summary(analyses)
        print(f"High Confidence Fields: {summary['high_confidence_fields']}")
        print(f"Low Confidence Fields: {summary['low_confidence_fields']}")
        print(f"Average Confidence: {summary['average_confidence']:.2f}")
        
        print("\n" + "="*60 + "\n")


def demo_routing_decisions():
    """Demonstrate routing decision logic."""
    print("=== Routing Decision Examples ===\n")
    
    router = PerFieldConfidenceRouter()
    
    # Test different confidence levels
    confidence_tests = [
        (0.95, "Very High"),
        (0.85, "High"),
        (0.70, "Medium-High"),
        (0.55, "Medium"),
        (0.45, "Low"),
        (0.25, "Very Low")
    ]
    
    fields_to_test = ['title', 'start_datetime', 'location', 'description']
    
    print("Routing Decisions by Confidence Level:")
    print("Field".ljust(15) + "Confidence".ljust(12) + "Level".ljust(15) + "Method")
    print("-" * 60)
    
    for field in fields_to_test:
        for confidence, level in confidence_tests:
            method = router.route_processing_method(field, confidence)
            print(f"{field}".ljust(15) + f"{confidence:.2f}".ljust(12) + 
                  f"{level}".ljust(15) + f"{method.value}")
        print()


def demo_field_consistency_validation():
    """Demonstrate field consistency validation."""
    print("=== Field Consistency Validation ===\n")
    
    from datetime import datetime, timedelta
    from models.event_models import FieldResult
    
    router = PerFieldConfidenceRouter()
    now = datetime.now()
    
    # Test case 1: Valid results
    print("Test 1: Valid Field Results")
    valid_results = {
        'title': FieldResult(
            value="Team Meeting",
            source="regex",
            confidence=0.9,
            span=(0, 12)
        ),
        'start_datetime': FieldResult(
            value=now,
            source="regex",
            confidence=0.95,
            span=(13, 25)
        ),
        'end_datetime': FieldResult(
            value=now + timedelta(hours=1),
            source="regex",
            confidence=0.9,
            span=(26, 35)
        )
    }
    
    validation = router.validate_field_consistency(valid_results)
    print(f"Valid: {validation.is_valid}")
    print(f"Missing Fields: {validation.missing_fields}")
    print(f"Warnings: {validation.warnings}")
    print()
    
    # Test case 2: Invalid datetime order
    print("Test 2: Invalid DateTime Order")
    invalid_results = valid_results.copy()
    invalid_results['end_datetime'] = FieldResult(
        value=now - timedelta(hours=1),  # End before start
        source="regex",
        confidence=0.9,
        span=(26, 35)
    )
    
    validation = router.validate_field_consistency(invalid_results)
    print(f"Valid: {validation.is_valid}")
    print(f"Field Warnings: {validation.field_warnings}")
    print()
    
    # Test case 3: Missing essential fields
    print("Test 3: Missing Essential Fields")
    incomplete_results = {
        'location': FieldResult(
            value="Conference Room A",
            source="regex",
            confidence=0.8,
            span=(0, 17)
        )
    }
    
    validation = router.validate_field_consistency(incomplete_results)
    print(f"Valid: {validation.is_valid}")
    print(f"Missing Fields: {validation.missing_fields}")
    print()


if __name__ == '__main__':
    demo_field_analysis()
    demo_routing_decisions()
    demo_field_consistency_validation()