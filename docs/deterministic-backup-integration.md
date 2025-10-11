# Deterministic Backup Integration Documentation

## Overview

The deterministic backup layer provides reliable fallback parsing using rule-based systems before resorting to expensive LLM processing. This layer integrates Duckling (Facebook's rule-based parser) and Microsoft Recognizers-Text to handle cases where regex extraction fails but deterministic patterns can still be identified.

## Architecture

```
Regex Extraction (≥0.8 confidence)
    ↓ (if fails)
Deterministic Backup Layer (0.6-0.8 confidence)
    ├── Duckling Parser
    ├── Microsoft Recognizers-Text
    └── Best Span Selection
    ↓ (if fails)
LLM Enhancement (<0.6 confidence)
```

## Duckling Integration

### Installation and Setup

**Docker Installation** (Recommended):
```bash
# Pull Duckling Docker image
docker pull facebook/duckling

# Run Duckling server
docker run -p 8000:8000 facebook/duckling
```

**Local Installation**:
```bash
# Install Haskell Stack
curl -sSL https://get.haskellstack.org/ | sh

# Clone and build Duckling
git clone https://github.com/facebook/duckling.git
cd duckling
stack build
stack exec duckling-example-exe
```

### Configuration

```python
# duckling_config.py
DUCKLING_CONFIG = {
    'url': 'http://localhost:8000/parse',
    'timeout': 2.0,  # 2 second timeout
    'supported_dimensions': [
        'time',
        'duration',
        'number',
        'ordinal',
        'distance',
        'volume'
    ],
    'supported_locales': ['en_US', 'en_GB', 'fr_FR', 'es_ES']
}
```

### DucklingExtractor Implementation

```python
import requests
from datetime import datetime
from typing import Optional, List, Dict, Any

class DucklingExtractor:
    def __init__(self, config: Dict[str, Any]):
        self.url = config['url']
        self.timeout = config['timeout']
        self.supported_dimensions = config['supported_dimensions']
        
    def extract_with_duckling(self, text: str, field: str) -> FieldResult:
        """Extract entities using Duckling parser"""
        try:
            # Map field types to Duckling dimensions
            dimension_map = {
                'start_datetime': 'time',
                'end_datetime': 'time',
                'duration': 'duration',
                'participants': 'number'
            }
            
            dimension = dimension_map.get(field, 'time')
            
            response = requests.post(
                self.url,
                json={
                    'text': text,
                    'dims': [dimension],
                    'locale': 'en_US'
                },
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                results = response.json()
                return self._process_duckling_results(results, field, text)
            else:
                return FieldResult(
                    value=None,
                    source='duckling',
                    confidence=0.0,
                    span=(0, 0),
                    alternatives=[],
                    processing_time_ms=0
                )
                
        except requests.RequestException as e:
            logger.warning(f"Duckling request failed: {e}")
            return self._empty_field_result('duckling')
    
    def _process_duckling_results(self, results: List[Dict], field: str, text: str) -> FieldResult:
        """Process Duckling API results into FieldResult"""
        if not results:
            return self._empty_field_result('duckling')
        
        # Sort by confidence (grain specificity in Duckling)
        sorted_results = sorted(results, key=lambda x: x.get('grain', 0), reverse=True)
        best_result = sorted_results[0]
        
        # Extract value based on field type
        value = self._extract_value_from_duckling(best_result, field)
        confidence = self._calculate_duckling_confidence(best_result, field)
        
        # Get text span
        start = best_result.get('start', 0)
        end = best_result.get('end', len(text))
        
        # Get alternatives
        alternatives = [
            self._extract_value_from_duckling(result, field) 
            for result in sorted_results[1:3]  # Top 2 alternatives
        ]
        
        return FieldResult(
            value=value,
            source='duckling',
            confidence=confidence,
            span=(start, end),
            alternatives=alternatives,
            processing_time_ms=best_result.get('latency', 0)
        )
    
    def _extract_value_from_duckling(self, result: Dict, field: str) -> Any:
        """Extract appropriate value from Duckling result"""
        if field in ['start_datetime', 'end_datetime']:
            # Handle datetime values
            value_dict = result.get('value', {})
            if 'value' in value_dict:
                return datetime.fromisoformat(value_dict['value'].replace('Z', '+00:00'))
            elif 'from' in value_dict and 'to' in value_dict:
                # Handle time ranges
                if field == 'start_datetime':
                    return datetime.fromisoformat(value_dict['from']['value'].replace('Z', '+00:00'))
                else:
                    return datetime.fromisoformat(value_dict['to']['value'].replace('Z', '+00:00'))
        
        elif field == 'duration':
            # Handle duration values
            value_dict = result.get('value', {})
            if 'normalized' in value_dict:
                return value_dict['normalized']['value']
        
        return result.get('value', {}).get('value')
    
    def _calculate_duckling_confidence(self, result: Dict, field: str) -> float:
        """Calculate confidence score for Duckling results"""
        base_confidence = 0.7
        
        # Adjust based on grain (specificity)
        grain = result.get('grain')
        if grain:
            grain_bonus = {
                'second': 0.1,
                'minute': 0.08,
                'hour': 0.06,
                'day': 0.04,
                'week': 0.02,
                'month': 0.01
            }
            base_confidence += grain_bonus.get(grain, 0)
        
        # Adjust based on span length (shorter is more precise)
        span_length = result.get('end', 0) - result.get('start', 0)
        if span_length < 10:
            base_confidence += 0.05
        elif span_length > 30:
            base_confidence -= 0.05
        
        return min(0.8, base_confidence)
```

## Microsoft Recognizers-Text Integration

### Installation

```bash
pip install recognizers-text
pip install recognizers-text-date-time
pip install recognizers-text-number
```

### RecognizersExtractor Implementation

```python
from recognizers_text import Culture
from recognizers_date_time import DateTimeRecognizer
from recognizers_number import NumberRecognizer
from typing import List, Dict, Any

class RecognizersExtractor:
    def __init__(self):
        self.datetime_recognizer = DateTimeRecognizer()
        self.number_recognizer = NumberRecognizer()
        self.supported_cultures = [
            Culture.English,
            Culture.French,
            Culture.Spanish,
            Culture.German
        ]
    
    def extract_with_recognizers(self, text: str, field: str) -> FieldResult:
        """Extract entities using Microsoft Recognizers-Text"""
        try:
            start_time = time.time()
            
            # Choose appropriate recognizer based on field
            if field in ['start_datetime', 'end_datetime', 'duration']:
                results = self.datetime_recognizer.recognize(text, Culture.English)
            elif field == 'participants':
                results = self.number_recognizer.recognize(text, Culture.English)
            else:
                results = []
            
            processing_time = int((time.time() - start_time) * 1000)
            
            if results:
                return self._process_recognizers_results(results, field, text, processing_time)
            else:
                return self._empty_field_result('recognizers', processing_time)
                
        except Exception as e:
            logger.warning(f"Recognizers extraction failed: {e}")
            return self._empty_field_result('recognizers')
    
    def _process_recognizers_results(self, results: List, field: str, text: str, processing_time: int) -> FieldResult:
        """Process Recognizers results into FieldResult"""
        if not results:
            return self._empty_field_result('recognizers', processing_time)
        
        # Sort by resolution confidence
        sorted_results = sorted(results, key=lambda x: len(x.resolution.get('values', [])), reverse=True)
        best_result = sorted_results[0]
        
        # Extract value
        value = self._extract_value_from_recognizers(best_result, field)
        confidence = self._calculate_recognizers_confidence(best_result, field)
        
        # Get span
        start = best_result.start
        end = best_result.end
        
        # Get alternatives
        alternatives = [
            self._extract_value_from_recognizers(result, field)
            for result in sorted_results[1:3]
        ]
        
        return FieldResult(
            value=value,
            source='recognizers',
            confidence=confidence,
            span=(start, end),
            alternatives=alternatives,
            processing_time_ms=processing_time
        )
    
    def _extract_value_from_recognizers(self, result, field: str) -> Any:
        """Extract appropriate value from Recognizers result"""
        resolution = result.resolution
        values = resolution.get('values', [])
        
        if not values:
            return None
        
        # Get the first (most confident) value
        first_value = values[0]
        
        if field in ['start_datetime', 'end_datetime']:
            # Handle datetime values
            if 'value' in first_value:
                return datetime.fromisoformat(first_value['value'])
            elif 'start' in first_value:
                return datetime.fromisoformat(first_value['start'])
        
        elif field == 'duration':
            # Handle duration values
            if 'value' in first_value:
                return int(first_value['value'])  # Duration in seconds
        
        return first_value.get('value')
    
    def _calculate_recognizers_confidence(self, result, field: str) -> float:
        """Calculate confidence score for Recognizers results"""
        base_confidence = 0.65
        
        # Adjust based on number of resolution values
        values_count = len(result.resolution.get('values', []))
        if values_count == 1:
            base_confidence += 0.1  # Single clear interpretation
        elif values_count > 3:
            base_confidence -= 0.05  # Too many interpretations
        
        # Adjust based on span length
        span_length = result.end - result.start
        if span_length < 15:
            base_confidence += 0.05
        elif span_length > 40:
            base_confidence -= 0.05
        
        return min(0.8, base_confidence)
```

## Deterministic Backup Coordination

### DeterministicBackupLayer Implementation

```python
class DeterministicBackupLayer:
    def __init__(self, duckling_config: Dict, enable_recognizers: bool = True):
        self.duckling = DucklingExtractor(duckling_config)
        self.recognizers = RecognizersExtractor() if enable_recognizers else None
        
    def extract_with_backup(self, text: str, field: str) -> FieldResult:
        """Coordinate deterministic backup extraction"""
        candidates = []
        
        # Try Duckling first
        duckling_result = self.duckling.extract_with_duckling(text, field)
        if duckling_result.value is not None:
            candidates.append(duckling_result)
        
        # Try Recognizers if enabled
        if self.recognizers:
            recognizers_result = self.recognizers.extract_with_recognizers(text, field)
            if recognizers_result.value is not None:
                candidates.append(recognizers_result)
        
        # Choose best candidate
        if candidates:
            return self.choose_best_span(candidates)
        else:
            return self._empty_field_result('deterministic_backup')
    
    def choose_best_span(self, candidates: List[FieldResult]) -> FieldResult:
        """Select the best candidate from deterministic parsers"""
        if not candidates:
            return self._empty_field_result('deterministic_backup')
        
        if len(candidates) == 1:
            return candidates[0]
        
        # Scoring criteria for best span selection
        def score_candidate(candidate: FieldResult) -> float:
            score = candidate.confidence
            
            # Prefer shorter spans (more precise)
            span_length = candidate.span[1] - candidate.span[0]
            if span_length < 10:
                score += 0.1
            elif span_length > 30:
                score -= 0.1
            
            # Prefer Duckling for datetime fields
            if candidate.source == 'duckling':
                score += 0.05
            
            # Timezone normalization bonus
            if hasattr(candidate.value, 'tzinfo') and candidate.value.tzinfo:
                score += 0.05
            
            return score
        
        # Select highest scoring candidate
        best_candidate = max(candidates, key=score_candidate)
        
        # Validate timezone normalization
        if self.validate_timezone_normalization(best_candidate):
            return best_candidate
        else:
            # Try next best candidate
            remaining = [c for c in candidates if c != best_candidate]
            if remaining:
                return self.choose_best_span(remaining)
            else:
                return best_candidate  # Return original even if timezone invalid
    
    def validate_timezone_normalization(self, result: FieldResult) -> bool:
        """Ensure datetime results have proper timezone handling"""
        if not hasattr(result.value, 'tzinfo'):
            return True  # Not a datetime, validation passes
        
        # Check if timezone is present and valid
        if result.value.tzinfo is None:
            logger.warning(f"Datetime result missing timezone: {result.value}")
            return False
        
        # Check if timezone is not just UTC when local timezone expected
        if result.value.tzinfo.utcoffset(None).total_seconds() == 0:
            logger.info(f"Datetime result in UTC, may need localization: {result.value}")
        
        return True
```

## Configuration and Deployment

### Environment Configuration

```bash
# .env file
DUCKLING_URL=http://localhost:8000/parse
DUCKLING_TIMEOUT=2.0
ENABLE_RECOGNIZERS=true
DETERMINISTIC_CONFIDENCE_THRESHOLD=0.6
BACKUP_PROCESSING_TIMEOUT=3.0
```

### Docker Compose Setup

```yaml
# docker-compose.yml
version: '3.8'
services:
  duckling:
    image: facebook/duckling
    ports:
      - "8000:8000"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/parse"]
      interval: 30s
      timeout: 10s
      retries: 3
  
  api:
    build: .
    ports:
      - "8080:8080"
    environment:
      - DUCKLING_URL=http://duckling:8000/parse
      - ENABLE_RECOGNIZERS=true
    depends_on:
      - duckling
```

### Health Monitoring

```python
def check_deterministic_backup_health() -> Dict[str, Any]:
    """Check health of deterministic backup components"""
    health_status = {
        'duckling': {'status': 'unknown', 'response_time_ms': None},
        'recognizers': {'status': 'unknown', 'response_time_ms': None}
    }
    
    # Check Duckling
    try:
        start_time = time.time()
        response = requests.post(
            DUCKLING_CONFIG['url'],
            json={'text': 'tomorrow', 'dims': ['time']},
            timeout=1.0
        )
        response_time = int((time.time() - start_time) * 1000)
        
        if response.status_code == 200:
            health_status['duckling'] = {
                'status': 'healthy',
                'response_time_ms': response_time
            }
        else:
            health_status['duckling'] = {
                'status': 'unhealthy',
                'error': f'HTTP {response.status_code}'
            }
    except Exception as e:
        health_status['duckling'] = {
            'status': 'unhealthy',
            'error': str(e)
        }
    
    # Check Recognizers
    try:
        start_time = time.time()
        recognizer = DateTimeRecognizer()
        results = recognizer.recognize('tomorrow', Culture.English)
        response_time = int((time.time() - start_time) * 1000)
        
        health_status['recognizers'] = {
            'status': 'healthy',
            'response_time_ms': response_time
        }
    except Exception as e:
        health_status['recognizers'] = {
            'status': 'unhealthy',
            'error': str(e)
        }
    
    return health_status
```

## Performance Optimization

### Caching Strategy

```python
from functools import lru_cache
import hashlib

class CachedDeterministicBackup:
    def __init__(self, backup_layer: DeterministicBackupLayer):
        self.backup_layer = backup_layer
        self.cache = {}
        self.cache_ttl = 3600  # 1 hour
    
    def extract_with_cache(self, text: str, field: str) -> FieldResult:
        """Extract with caching for deterministic results"""
        cache_key = self._generate_cache_key(text, field)
        
        # Check cache
        if cache_key in self.cache:
            cached_result, timestamp = self.cache[cache_key]
            if time.time() - timestamp < self.cache_ttl:
                cached_result.processing_time_ms = 1  # Cache hit time
                return cached_result
        
        # Extract and cache
        result = self.backup_layer.extract_with_backup(text, field)
        self.cache[cache_key] = (result, time.time())
        
        return result
    
    def _generate_cache_key(self, text: str, field: str) -> str:
        """Generate cache key for text and field combination"""
        content = f"{text.lower().strip()}:{field}"
        return hashlib.md5(content.encode()).hexdigest()
```

### Parallel Processing

```python
import asyncio
from concurrent.futures import ThreadPoolExecutor

class AsyncDeterministicBackup:
    def __init__(self, backup_layer: DeterministicBackupLayer):
        self.backup_layer = backup_layer
        self.executor = ThreadPoolExecutor(max_workers=4)
    
    async def extract_multiple_fields(self, text: str, fields: List[str]) -> Dict[str, FieldResult]:
        """Extract multiple fields concurrently"""
        loop = asyncio.get_event_loop()
        
        # Create tasks for each field
        tasks = [
            loop.run_in_executor(
                self.executor,
                self.backup_layer.extract_with_backup,
                text,
                field
            )
            for field in fields
        ]
        
        # Wait for all tasks to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Combine results
        field_results = {}
        for field, result in zip(fields, results):
            if isinstance(result, Exception):
                logger.error(f"Field {field} extraction failed: {result}")
                field_results[field] = self._empty_field_result('deterministic_backup')
            else:
                field_results[field] = result
        
        return field_results
```

## Troubleshooting

### Common Issues

**Duckling Connection Errors**:
```python
# Check if Duckling is running
curl http://localhost:8000/parse

# Test with simple request
curl -X POST http://localhost:8000/parse \
  -H "Content-Type: application/json" \
  -d '{"text": "tomorrow", "dims": ["time"]}'
```

**Recognizers Import Errors**:
```bash
# Reinstall recognizers packages
pip uninstall recognizers-text recognizers-text-date-time
pip install recognizers-text recognizers-text-date-time
```

**Low Confidence Scores**:
- Check if text contains clear temporal expressions
- Verify timezone handling for datetime results
- Review span selection logic for multiple candidates

### Debug Mode

```python
# Enable debug logging
import logging
logging.getLogger('deterministic_backup').setLevel(logging.DEBUG)

# Test extraction with debug info
backup_layer = DeterministicBackupLayer(DUCKLING_CONFIG)
result = backup_layer.extract_with_backup("meeting tomorrow at 2pm", "start_datetime")
print(f"Result: {result}")
print(f"Source: {result.source}")
print(f"Confidence: {result.confidence}")
print(f"Span: {result.span}")
```

## Best Practices

1. **Always Run Health Checks**: Monitor Duckling service availability
2. **Use Appropriate Timeouts**: Set reasonable timeouts for external services
3. **Cache Deterministic Results**: Cache results for identical text/field combinations
4. **Validate Timezone Handling**: Ensure datetime results have proper timezone information
5. **Prefer Shorter Spans**: Choose candidates with more precise text spans
6. **Handle Service Failures**: Gracefully degrade when deterministic services are unavailable
7. **Monitor Performance**: Track processing times and success rates for each service