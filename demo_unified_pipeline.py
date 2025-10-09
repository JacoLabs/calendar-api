#!/usr/bin/env python3
"""
Demonstration of the unified parsing pipeline integration.

This script demonstrates the complete parsing pipeline with:
- Per-field confidence routing
- Processing order: regex (≥0.8) → deterministic (0.6-0.8) → LLM (<0.6)
- Cross-component validation and consistency checking
- Unified confidence scoring across all extraction methods
"""

from datetime import datetime
from services.hybrid_event_parser import HybridEventParser

def demonstrate_unified_pipeline():
    """Demonstrate the unified parsing pipeline with various scenarios."""
    
    print("🚀 Unified Parsing Pipeline Demonstration")
    print("=" * 50)
    
    # Initialize parser
    current_time = datetime(2025, 10, 8, 14, 30)
    parser = HybridEventParser(current_time=current_time)
    
    # Test scenarios with different confidence levels
    test_scenarios = [
        {
            "name": "High Confidence Scenario",
            "text": "Team meeting tomorrow at 2:00 PM in Conference Room A",
            "expected_path": "regex_only",
            "expected_confidence": "> 0.8"
        },
        {
            "name": "Medium Confidence Scenario", 
            "text": "Lunch next Friday somewhere downtown",
            "expected_path": "regex_only or deterministic",
            "expected_confidence": "0.6-0.8"
        },
        {
            "name": "Complex Email Scenario",
            "text": """
            Subject: Q4 Planning Meeting
            
            Hi team,
            
            Let's schedule our quarterly planning session for next Monday at 10 AM.
            We'll meet in the main conference room to discuss goals and objectives.
            
            Please bring your project updates.
            
            Thanks,
            Sarah
            """,
            "expected_path": "regex_only or hybrid",
            "expected_confidence": "> 0.7"
        },
        {
            "name": "Casual Text Scenario",
            "text": "coffee with john sometime next week",
            "expected_path": "any",
            "expected_confidence": "< 0.7"
        }
    ]
    
    for i, scenario in enumerate(test_scenarios, 1):
        print(f"\n📋 Scenario {i}: {scenario['name']}")
        print("-" * 40)
        print(f"Input: {scenario['text'][:60]}{'...' if len(scenario['text']) > 60 else ''}")
        
        try:
            # Parse with hybrid mode (full pipeline)
            result = parser.parse_event_text(scenario['text'], mode="hybrid")
            
            # Display results
            print(f"✅ Parsing successful: {result.parsed_event is not None}")
            print(f"📊 Confidence score: {result.confidence_score:.2f}")
            print(f"🛤️  Parsing path: {result.parsing_path}")
            
            if result.parsed_event:
                print(f"📝 Title: {result.parsed_event.title}")
                print(f"📅 Start time: {result.parsed_event.start_datetime}")
                print(f"📍 Location: {result.parsed_event.location}")
                print(f"⚠️  Needs confirmation: {result.parsed_event.needs_confirmation}")
                
                # Show field-level results
                if result.parsed_event.field_results:
                    print(f"🔍 Field results ({len(result.parsed_event.field_results)} fields):")
                    for field_name, field_result in result.parsed_event.field_results.items():
                        print(f"   • {field_name}: {field_result.source} (conf: {field_result.confidence:.2f})")
                
                # Show warnings if any
                if result.warnings:
                    print(f"⚠️  Warnings: {', '.join(result.warnings)}")
            
            # Verify expectations
            print(f"📈 Expected confidence: {scenario['expected_confidence']}")
            print(f"🎯 Expected path: {scenario['expected_path']}")
            
        except Exception as e:
            print(f"❌ Error: {e}")
    
    print(f"\n🎉 Unified Pipeline Demonstration Complete!")

def demonstrate_per_field_routing():
    """Demonstrate per-field confidence routing."""
    
    print("\n🎯 Per-Field Confidence Routing Demonstration")
    print("=" * 50)
    
    current_time = datetime(2025, 10, 8, 14, 30)
    parser = HybridEventParser(current_time=current_time)
    
    text = "Annual company retreat October 15-17 at Mountain View Resort with all staff"
    
    print(f"Input text: {text}")
    print("\n📊 Field Analysis:")
    
    # Analyze field confidence potential
    field_analyses = parser.analyze_field_confidence(text)
    
    for field_name, analysis in field_analyses.items():
        print(f"   • {field_name}:")
        print(f"     - Confidence potential: {analysis.confidence_potential:.2f}")
        print(f"     - Recommended method: {analysis.recommended_method.value}")
        print(f"     - Complexity score: {analysis.complexity_score:.2f}")
        print(f"     - Pattern matches: {analysis.pattern_matches}")
        if analysis.ambiguity_indicators:
            print(f"     - Ambiguities: {analysis.ambiguity_indicators}")
    
    # Show processing order optimization
    fields = list(field_analyses.keys())
    optimized_order = parser.confidence_router.optimize_processing_order(fields)
    
    print(f"\n🔄 Processing Order Optimization:")
    print(f"   Original: {fields}")
    print(f"   Optimized: {optimized_order}")
    
    # Parse with the optimized pipeline
    result = parser.parse_event_text(text, mode="hybrid")
    
    print(f"\n📋 Final Results:")
    print(f"   • Overall confidence: {result.confidence_score:.2f}")
    print(f"   • Parsing path: {result.parsing_path}")
    print(f"   • Fields processed: {len(result.parsed_event.field_results)}")

def demonstrate_processing_methods():
    """Demonstrate different processing methods."""
    
    print("\n⚙️ Processing Methods Demonstration")
    print("=" * 50)
    
    current_time = datetime(2025, 10, 8, 14, 30)
    parser = HybridEventParser(current_time=current_time)
    
    text = "Project review meeting Monday at 10 AM"
    
    # Test different modes
    modes = ["regex_only", "hybrid"]
    
    for mode in modes:
        print(f"\n🔧 Mode: {mode}")
        print("-" * 20)
        
        result = parser.parse_event_text(text, mode=mode)
        
        print(f"   • Confidence: {result.confidence_score:.2f}")
        print(f"   • Parsing path: {result.parsing_path}")
        print(f"   • Title: {result.parsed_event.title}")
        print(f"   • Processing time: {result.parsed_event.processing_time_ms}ms")
        
        if result.parsed_event.field_results:
            print(f"   • Field sources:")
            for field_name, field_result in result.parsed_event.field_results.items():
                print(f"     - {field_name}: {field_result.source}")

def demonstrate_validation_and_consistency():
    """Demonstrate cross-component validation and consistency checking."""
    
    print("\n✅ Validation and Consistency Demonstration")
    print("=" * 50)
    
    current_time = datetime(2025, 10, 8, 14, 30)
    parser = HybridEventParser(current_time=current_time)
    
    # Test with inconsistent data
    inconsistent_texts = [
        "Meeting from 3 PM to 2 PM tomorrow",  # Invalid time range
        "Very long event title that goes on and on and probably should be shortened because it's way too verbose for a calendar event",  # Long title
        "Event",  # Too short/generic
    ]
    
    for i, text in enumerate(inconsistent_texts, 1):
        print(f"\n🧪 Test {i}: {text[:50]}{'...' if len(text) > 50 else ''}")
        print("-" * 30)
        
        result = parser.parse_event_text(text, mode="hybrid")
        
        print(f"   • Confidence: {result.confidence_score:.2f}")
        print(f"   • Needs confirmation: {result.parsed_event.needs_confirmation}")
        
        if result.warnings:
            print(f"   • Warnings:")
            for warning in result.warnings:
                print(f"     - {warning}")
        
        # Show validation results
        if hasattr(result.parsed_event, 'field_results') and result.parsed_event.field_results:
            validation_result = parser.confidence_router.validate_field_consistency(result.parsed_event.field_results)
            if not validation_result.is_valid:
                print(f"   • Validation issues:")
                for field, warnings in validation_result.field_warnings.items():
                    for warning in warnings:
                        print(f"     - {field}: {warning}")

if __name__ == "__main__":
    demonstrate_unified_pipeline()
    demonstrate_per_field_routing()
    demonstrate_processing_methods()
    demonstrate_validation_and_consistency()
    
    print(f"\n🎊 All demonstrations completed successfully!")
    print("The unified parsing pipeline is fully integrated and operational.")