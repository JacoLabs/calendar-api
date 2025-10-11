# Per-Field Confidence Routing Documentation

## Overview

The per-field confidence routing system optimizes parsing performance by analyzing each field independently and routing them to the most appropriate processing method based on confidence scores. This approach minimizes expensive LLM processing by only enhancing fields that truly need it.

## Architecture

```
Text Input → Field Analysis → Confidence Scoring → Selective Processing → Result Aggregation
```

### Processing Methods by Confidence

| Confidence Range | Processing Method | Description |
|------------------|-------------------|-------------|
| ≥ 0.8 | Regex Only | High-confidence regex extraction, no LLM enhancement |
| 0.6 - 0.8 | Deterministic Backup | Duckling/Recognizers fallback processing |
| < 0.6 | LLM Enhancement | Low-confidence fields routed to LLM processing |

## Field Types and Analysis

### Essential Fields (High Priority)
- **title**: Event name or derived title
- **start_datetime**: Event start date and time
- **end_datetime**: Event end date and time

### Optional Fields (Lower Priority)
- **location**: Event venue or address
- **description**: Additional event details
- **participants**: Attendees or organizers
- **recurrence**: Recurring event patterns

## Confidence Scoring Algorithm

### Regex Confidence Factors
```python
def calculate_regex_confidence(field_result):
    base_confidence = 0.8  # High confidence for successful regex
    
    # Adjust based on pattern specificity
    if field_result.pattern_type == "explicit_datetime":
        return min(0.95, base_confidence + 0.15)
    elif field_result.pattern_type == "relative_datetime":
        return min(0.85, base_confidence + 0.05)
    else:
        return base_confidence
```

### Deterministic Backup Confidence
```python
def calculate_deterministic_confidence(duckling_result, recognizers_result):
    # Choose shortest valid span with proper timezone
    best_result = choose_best_span([duckling_result, recognizers_result])
    
    base_confidence = 0.7
    if best_result.timezone_normalized:
        base_confidence += 0.1
    if best_result.span_length < 20:  # Shorter spans are more precise
        base_confidence += 0.05
        
    return min(0.8, base_confidence)
```

## Processing Decision Flow

### 1. Field Analysis Phase
```python
def analyze_field_extractability(text: str) -> Dict[str, float]:
    """Assess per-field confidence potential before processing"""
    field_confidence = {}
    
    for field in ['start_datetime', 'end_datetime', 'title', 'location']:
        # Pre-analyze text for field-specific patterns
        confidence = assess_field_patterns(text, field)
        field_confidence[field] = confidence
    
    return field_confidence
```

### 2. Routing Decision
```python
def route_processing_method(field: str, confidence: float) -> ProcessingMethod:
    """Choose optimal processing method based on confidence"""
    if confidence >= 0.8:
        return ProcessingMethod.REGEX_ONLY
    elif confidence >= 0.6:
        return ProcessingMethod.DETERMINISTIC_BACKUP
    else:
        return ProcessingMethod.LLM_ENHANCEMENT
```

### 3. Processing Order Optimization
```python
def optimize_processing_order(fields: List[str]) -> List[str]:
    """Order fields for efficient processing"""
    # Process essential fields first
    essential = ['start_datetime', 'end_datetime', 'title']
    optional = ['location', 'description', 'participants', 'recurrence']
    
    # Sort by confidence within each group
    return sort_by_confidence(essential) + sort_by_confidence(optional)
```

## Field Result Structure

Each field result includes comprehensive provenance data:

```python
@dataclass
class FieldResult:
    value: Any                    # Extracted value
    source: str                   # "regex", "duckling", "recognizers", "llm"
    confidence: float             # 0.0 - 1.0 confidence score
    span: Tuple[int, int]        # Character positions in original text
    alternatives: List[Any]       # Other possible values
    processing_time_ms: int       # Time taken to process this field
```

## Cross-Field Validation

### Consistency Checks
```python
def validate_field_consistency(results: Dict[str, FieldResult]) -> ValidationResult:
    """Ensure extracted fields are logically consistent"""
    warnings = []
    
    # Check datetime consistency
    if results['start_datetime'] and results['end_datetime']:
        if results['start_datetime'].value >= results['end_datetime'].value:
            warnings.append("End time should be after start time")
    
    # Check location-title consistency
    if results['location'] and results['title']:
        if location_conflicts_with_title(results['location'], results['title']):
            warnings.append("Location and title may be inconsistent")
    
    return ValidationResult(warnings=warnings)
```

## Performance Optimization

### Selective Processing Benefits
- **Reduced LLM Calls**: Only low-confidence fields use expensive LLM processing
- **Parallel Processing**: Independent fields can be processed concurrently
- **Early Termination**: High-confidence results skip additional processing layers

### Processing Time Tracking
```python
def track_field_processing_time(field: str, method: str, duration_ms: int):
    """Track processing time by field and method"""
    metrics = {
        'field': field,
        'method': method,
        'duration_ms': duration_ms,
        'timestamp': datetime.utcnow()
    }
    performance_logger.log(metrics)
```

## Configuration Options

### Confidence Thresholds
```python
CONFIDENCE_THRESHOLDS = {
    'regex_only': 0.8,
    'deterministic_backup': 0.6,
    'llm_enhancement': 0.0
}
```

### Field Priority Settings
```python
FIELD_PRIORITIES = {
    'essential': ['title', 'start_datetime', 'end_datetime'],
    'optional': ['location', 'description', 'participants', 'recurrence']
}
```

## Troubleshooting

### Common Issues

**Low Confidence Scores**
- Check regex patterns for field-specific text
- Verify deterministic parsers are properly configured
- Review LLM prompt engineering for field enhancement

**Inconsistent Results**
- Enable cross-field validation
- Check for conflicting extraction results
- Review field priority settings

**Performance Issues**
- Monitor per-field processing times
- Adjust confidence thresholds to reduce LLM usage
- Enable concurrent field processing

### Debug Mode
```python
# Enable detailed routing decisions
parser = HybridEventParser(debug_mode=True)
result = parser.parse_event_text(text, mode="audit")
print(result.field_routing_decisions)
```

## Best Practices

1. **Set Appropriate Thresholds**: Adjust confidence thresholds based on your accuracy requirements
2. **Monitor Performance**: Track processing times and adjust routing decisions accordingly
3. **Validate Results**: Always run cross-field validation to catch inconsistencies
4. **Use Audit Mode**: Enable audit mode during development to understand routing decisions
5. **Test Edge Cases**: Verify routing works correctly with ambiguous or incomplete text