#!/usr/bin/env python3
"""
Debug hybrid parser for case 3
"""

from services.hybrid_event_parser import HybridEventParser
from datetime import datetime
import json

def debug_hybrid_case3():
    current_time = datetime(2025, 10, 10, 14, 0, 0)
    parser = HybridEventParser(current_time=current_time)
    
    text = "Company Retreat LOCATION Beach Resort DATE Next Friday"
    
    print(f"Input: {text}")
    print("=" * 80)
    
    result = parser.parse_event_text(text, mode="hybrid")
    
    print(f"Title: '{result.parsed_event.title}'")
    print(f"Location: '{result.parsed_event.location}'")
    print(f"Parsing Path: {result.parsing_path}")
    
    print("\nField Results:")
    if hasattr(result.parsed_event, 'field_results') and result.parsed_event.field_results:
        for field, field_result in result.parsed_event.field_results.items():
            print(f"  {field}: '{field_result.value}' (confidence: {field_result.confidence}, source: {field_result.source})")
    
    print(f"\nField Analyses:")
    field_analyses = result.processing_metadata.get('field_analyses', {})
    for field, analysis in field_analyses.items():
        print(f"  {field}: confidence_potential={analysis['confidence_potential']}, method={analysis['recommended_method']}")
    
    print(f"\nProcessing Order:")
    print(result.processing_metadata.get('processing_order', []))

if __name__ == "__main__":
    debug_hybrid_case3()