# Troubleshooting Guide for Enhanced Features

## Overview

This guide helps diagnose and resolve common issues with the enhanced text-to-calendar event parsing system, including per-field confidence routing, deterministic backup integration, LLM processing, and performance optimization features.

## Quick Diagnostic Checklist

### System Health Check
```bash
# Check API health
curl https://your-api-domain.com/healthz

# Check component status
curl https://your-api-domain.com/cache/stats

# Test basic parsing
curl -X POST https://your-api-domain.com/parse \
  -H "Content-Type: application/json" \
  -d '{"text": "meeting tomorrow at 2pm", "timezone": "America/New_York"}'
```

### Common Symptoms and Quick Fixes

| Symptom | Likely Cause | Quick Fix |
|---------|--------------|-----------|
| Low confidence scores | Regex patterns not matching | Check text format and patterns |
| Slow response times | LLM processing all fields | Review confidence thresholds |
| Cache misses | Text normalization issues | Check cache key generation |
| Parsing failures | Service dependencies down | Check Duckling/LLM services |
| Inconsistent results | Field validation errors | Enable cross-field validation |

## Per-Field Confidence Routing Issues

### Problem: All Fields Routed to LLM
**Symptoms**:
- High processing times (>2 seconds)
- All fields show `source: "llm"` in audit mode
- Confidence scores consistently below 0.8

**Diagnosis**:
```python
# Test regex extraction directly
from services.regex_date_extractor import RegexDateExtractor
extractor = RegexDateExtractor()
result = extractor.extract_datetime("meeting tomorrow at 2pm")
print(f"Regex result: {result}")
```

**Solutions**:
1. **Check Regex Patterns**:
   ```python
   # Verify patterns are loaded
   print(extractor.patterns.keys())
   
   # Test specific patterns
   import re
   pattern = r'\b(tomorrow|today|yesterday)\b'
   matches = re.findall(pattern, "meeting tomorrow at 2pm", re.IGNORECASE)
   print(f"Matches: {matches}")
   ```

2. **Adjust Confidence Thresholds**:
   ```python
   # Lower thresholds for testing
   CONFIDENCE_THRESHOLDS = {
       'regex_only': 0.7,  # Was 0.8
       'deterministic_backup': 0.5,  # Was 0.6
       'llm_enhancement': 0.0
   }
   ```

3. **Enable Debug Mode**:
   ```python
   parser = HybridEventParser(debug_mode=True)
   result = parser.parse_event_text(text, mode="audit")
   print(result.audit_data.field_routing_decisions)
   ```

### Problem: High-Confidence Fields Being Modified by LLM
**Symptoms**:
- Regex extracts correct datetime but LLM changes it
- Audit mode shows LLM overriding high-confidence fields
- Inconsistent datetime results

**Diagnosis**:
```python
# Check LLM guardrails
result = parser.parse_event_text(text, mode="audit")
locked_fields = result.audit_data.get('locked_fields', {})
print(f"Locked fields: {locked_fields}")
```

**Solutions**:
1. **Verify Schema Enforcement**:
   ```python
   # Check LLM schema constraints
   def enforce_schema_constraints(llm_output, locked_fields):
       for field, value in locked_fields.items():
           if field in llm_output and llm_output[field] != value:
               logger.warning(f"LLM attempted to modify locked field {field}")
               llm_output[field] = value
       return llm_output
   ```

2. **Review LLM Prompts**:
   ```python
   # Ensure prompts specify locked fields
   prompt = f"""
   Extract event information. DO NOT modify these locked fields:
   {json.dumps(locked_fields)}
   
   Only enhance: {', '.join(unlocked_fields)}
   """
   ```

### Problem: Inconsistent Field Confidence Scores
**Symptoms**:
- Same text produces different confidence scores
- Field confidence doesn't match extraction quality
- Routing decisions seem random

**Diagnosis**:
```python
# Test confidence calculation
def debug_confidence_calculation(text, field):
    # Test multiple times
    scores = []
    for i in range(5):
        result = parser.analyze_field_confidence(text, field)
        scores.append(result)
    
    print(f"Confidence scores for {field}: {scores}")
    print(f"Standard deviation: {np.std(scores)}")
```

**Solutions**:
1. **Normalize Text Input**:
   ```python
   def normalize_text(text):
       # Consistent normalization
       text = text.lower().strip()
       text = re.sub(r'\s+', ' ', text)  # Normalize whitespace
       text = re.sub(r'[^\w\s:/-]', '', text)  # Remove special chars
       return text
   ```

2. **Use Deterministic Confidence Calculation**:
   ```python
   def calculate_field_confidence(text, field, pattern_matches):
       base_confidence = 0.5
       
       # Deterministic factors
       if pattern_matches:
           base_confidence += 0.3
       if len(text.split()) < 10:  # Shorter text is clearer
           base_confidence += 0.1
       if field in ['start_datetime', 'end_datetime']:
           base_confidence += 0.1  # Essential fields get bonus
       
       return min(0.95, base_confidence)
   ```

## Deterministic Backup Issues

### Problem: Duckling Service Unavailable
**Symptoms**:
- Health check shows Duckling as unhealthy
- Deterministic backup always fails
- Fallback to LLM for all medium-confidence fields

**Diagnosis**:
```bash
# Check Duckling service
curl http://localhost:8000/parse
docker ps | grep duckling
docker logs duckling_container
```

**Solutions**:
1. **Restart Duckling Service**:
   ```bash
   # Docker restart
   docker restart duckling_container
   
   # Or rebuild
   docker-compose down
   docker-compose up -d duckling
   ```

2. **Configure Fallback URL**:
   ```python
   DUCKLING_CONFIG = {
       'primary_url': 'http://localhost:8000/parse',
       'fallback_url': 'http://duckling-backup:8000/parse',
       'timeout': 2.0
   }
   ```

3. **Disable Duckling Temporarily**:
   ```python
   # Skip Duckling if unavailable
   class DeterministicBackupLayer:
       def __init__(self, config):
           self.duckling_enabled = self._check_duckling_health()
           
       def extract_with_backup(self, text, field):
           if self.duckling_enabled:
               return self.duckling.extract_with_duckling(text, field)
           else:
               return self.recognizers.extract_with_recognizers(text, field)
   ```

### Problem: Microsoft Recognizers Import Errors
**Symptoms**:
- ImportError when loading recognizers
- Deterministic backup fails to initialize
- Only Duckling results available

**Diagnosis**:
```python
# Test recognizers import
try:
    from recognizers_text import Culture
    from recognizers_date_time import DateTimeRecognizer
    print("Recognizers imported successfully")
except ImportError as e:
    print(f"Import error: {e}")
```

**Solutions**:
1. **Reinstall Recognizers**:
   ```bash
   pip uninstall recognizers-text recognizers-text-date-time
   pip install recognizers-text==1.0.2 recognizers-text-date-time==1.0.2
   ```

2. **Use Alternative Installation**:
   ```bash
   # Try conda if pip fails
   conda install -c conda-forge recognizers-text
   ```

3. **Disable Recognizers**:
   ```python
   # Fallback to Duckling only
   backup_layer = DeterministicBackupLayer(
       duckling_config=DUCKLING_CONFIG,
       enable_recognizers=False
   )
   ```

### Problem: Poor Span Selection
**Symptoms**:
- Wrong datetime values selected from multiple candidates
- Longer, less precise spans chosen over shorter ones
- Timezone information lost in selection

**Diagnosis**:
```python
# Debug span selection
def debug_span_selection(candidates):
    for i, candidate in enumerate(candidates):
        span_length = candidate.span[1] - candidate.span[0]
        print(f"Candidate {i}: {candidate.value}")
        print(f"  Source: {candidate.source}")
        print(f"  Confidence: {candidate.confidence}")
        print(f"  Span: {candidate.span} (length: {span_length})")
        print(f"  Timezone: {getattr(candidate.value, 'tzinfo', None)}")
```

**Solutions**:
1. **Improve Scoring Algorithm**:
   ```python
   def score_candidate(candidate):
       score = candidate.confidence
       
       # Prefer shorter spans (more precise)
       span_length = candidate.span[1] - candidate.span[0]
       if span_length < 10:
           score += 0.15
       elif span_length < 20:
           score += 0.05
       elif span_length > 40:
           score -= 0.1
       
       # Timezone bonus
       if hasattr(candidate.value, 'tzinfo') and candidate.value.tzinfo:
           score += 0.1
       
       # Source preference
       if candidate.source == 'duckling':
           score += 0.05
       
       return score
   ```

2. **Add Validation Checks**:
   ```python
   def validate_candidate(candidate):
       # Check for reasonable datetime
       if hasattr(candidate.value, 'year'):
           current_year = datetime.now().year
           if candidate.value.year < current_year - 1 or candidate.value.year > current_year + 5:
               return False
       
       # Check timezone
       if hasattr(candidate.value, 'tzinfo') and candidate.value.tzinfo is None:
           logger.warning("Candidate missing timezone info")
       
       return True
   ```

## LLM Processing Issues

### Problem: LLM Timeouts
**Symptoms**:
- Frequent timeout errors (>3 seconds)
- Partial results returned
- High error rates in logs

**Diagnosis**:
```python
# Monitor LLM response times
import time

def monitor_llm_performance(text, field):
    start_time = time.time()
    try:
        result = llm_enhancer.enhance_field(text, field)
        duration = time.time() - start_time
        print(f"LLM processing time: {duration:.2f}s")
        return result
    except TimeoutError:
        duration = time.time() - start_time
        print(f"LLM timeout after {duration:.2f}s")
        return None
```

**Solutions**:
1. **Optimize LLM Context**:
   ```python
   def limit_context_to_residual(text, extracted_spans):
       # Remove already extracted text
       residual_text = text
       for start, end in sorted(extracted_spans, reverse=True):
           residual_text = residual_text[:start] + residual_text[end:]
       
       # Limit context length
       max_context = 500  # characters
       if len(residual_text) > max_context:
           residual_text = residual_text[:max_context] + "..."
       
       return residual_text
   ```

2. **Implement Retry Logic**:
   ```python
   async def llm_with_retry(prompt, max_retries=2):
       for attempt in range(max_retries + 1):
           try:
               result = await asyncio.wait_for(
                   llm_client.generate(prompt),
                   timeout=3.0
               )
               return result
           except asyncio.TimeoutError:
               if attempt == max_retries:
                   logger.error("LLM timeout after all retries")
                   return None
               await asyncio.sleep(0.5)  # Brief delay before retry
   ```

3. **Use Smaller Models**:
   ```python
   # Switch to faster model for simple enhancements
   LLM_CONFIG = {
       'enhancement_model': 'llama3.2:1b',  # Faster for simple tasks
       'fallback_model': 'llama3.2:3b',     # More capable for complex parsing
       'timeout': 2.0  # Reduced timeout
   }
   ```

### Problem: LLM Hallucination
**Symptoms**:
- LLM invents dates/times not in original text
- Confidence scores don't reflect actual accuracy
- Inconsistent results for similar inputs

**Diagnosis**:
```python
# Compare LLM output with original text
def validate_llm_output(original_text, llm_result):
    # Check if extracted values appear in original text
    for field, value in llm_result.items():
        if isinstance(value, str) and len(value) > 3:
            if value.lower() not in original_text.lower():
                print(f"Potential hallucination in {field}: {value}")
```

**Solutions**:
1. **Enforce Temperature=0**:
   ```python
   llm_params = {
       'temperature': 0.0,  # Deterministic output
       'top_p': 0.1,        # Limit token selection
       'max_tokens': 200    # Prevent verbose responses
   }
   ```

2. **Add Validation Constraints**:
   ```python
   def validate_llm_datetime(extracted_datetime, original_text):
       # Check if datetime components appear in text
       if extracted_datetime:
           date_str = extracted_datetime.strftime("%Y-%m-%d")
           time_str = extracted_datetime.strftime("%H:%M")
           
           # Look for date/time indicators in original text
           has_date_indicator = any(word in original_text.lower() 
                                  for word in ['tomorrow', 'today', 'monday', 'jan', 'feb'])
           has_time_indicator = any(word in original_text.lower() 
                                  for word in ['am', 'pm', ':', 'noon', 'midnight'])
           
           if not (has_date_indicator or has_time_indicator):
               logger.warning("LLM extracted datetime without clear indicators")
               return False
       
       return True
   ```

3. **Use Structured Prompts**:
   ```python
   def create_structured_prompt(text, field, locked_fields):
       prompt = f"""
       Extract {field} from this text: "{text}"
       
       Rules:
       - Only extract information explicitly stated in the text
       - Do not modify these locked fields: {locked_fields}
       - If {field} is not clearly stated, return null
       - Use JSON format: {{"field": "value"}}
       
       Response:
       """
       return prompt
   ```

## Performance Issues

### Problem: Slow API Response Times
**Symptoms**:
- Response times >2 seconds consistently
- High CPU usage
- Memory leaks over time

**Diagnosis**:
```python
# Profile API performance
import cProfile
import pstats

def profile_parsing(text):
    profiler = cProfile.Profile()
    profiler.enable()
    
    result = parser.parse_event_text(text)
    
    profiler.disable()
    stats = pstats.Stats(profiler)
    stats.sort_stats('cumulative')
    stats.print_stats(10)  # Top 10 slowest functions
```

**Solutions**:
1. **Enable Lazy Loading**:
   ```python
   # Lazy load heavy modules
   class LazyLoader:
       def __init__(self):
           self._duckling = None
           self._recognizers = None
           self._llm = None
       
       @property
       def duckling(self):
           if self._duckling is None:
               from services.duckling_extractor import DucklingExtractor
               self._duckling = DucklingExtractor(DUCKLING_CONFIG)
           return self._duckling
   ```

2. **Implement Caching**:
   ```python
   from functools import lru_cache
   import hashlib
   
   @lru_cache(maxsize=1000)
   def cached_regex_extraction(text_hash, field):
       return regex_extractor.extract_field(text, field)
   
   def get_text_hash(text):
       return hashlib.md5(text.encode()).hexdigest()
   ```

3. **Use Async Processing**:
   ```python
   async def parse_fields_concurrently(text, fields):
       tasks = [
           asyncio.create_task(process_field(text, field))
           for field in fields
       ]
       results = await asyncio.gather(*tasks, return_exceptions=True)
       return dict(zip(fields, results))
   ```

### Problem: High Memory Usage
**Symptoms**:
- Memory usage grows over time
- Out of memory errors
- Slow garbage collection

**Diagnosis**:
```python
import psutil
import gc

def monitor_memory():
    process = psutil.Process()
    memory_info = process.memory_info()
    print(f"RSS: {memory_info.rss / 1024 / 1024:.2f} MB")
    print(f"VMS: {memory_info.vms / 1024 / 1024:.2f} MB")
    print(f"Objects in memory: {len(gc.get_objects())}")
```

**Solutions**:
1. **Clear Caches Periodically**:
   ```python
   import threading
   import time
   
   def cache_cleanup_worker():
       while True:
           time.sleep(3600)  # Every hour
           # Clear old cache entries
           current_time = time.time()
           expired_keys = [
               key for key, (_, timestamp) in cache.items()
               if current_time - timestamp > 3600
           ]
           for key in expired_keys:
               del cache[key]
           gc.collect()
   
   # Start cleanup thread
   cleanup_thread = threading.Thread(target=cache_cleanup_worker, daemon=True)
   cleanup_thread.start()
   ```

2. **Limit Cache Size**:
   ```python
   from collections import OrderedDict
   
   class LRUCache:
       def __init__(self, max_size=1000):
           self.cache = OrderedDict()
           self.max_size = max_size
       
       def get(self, key):
           if key in self.cache:
               # Move to end (most recently used)
               self.cache.move_to_end(key)
               return self.cache[key]
           return None
       
       def set(self, key, value):
           if key in self.cache:
               self.cache.move_to_end(key)
           elif len(self.cache) >= self.max_size:
               # Remove least recently used
               self.cache.popitem(last=False)
           self.cache[key] = value
   ```

## Cache Issues

### Problem: Low Cache Hit Rate
**Symptoms**:
- Cache stats show <30% hit rate
- Similar requests not being cached
- High processing times for repeated requests

**Diagnosis**:
```python
# Analyze cache keys
def analyze_cache_keys():
    cache_keys = list(cache.keys())
    print(f"Total cache entries: {len(cache_keys)}")
    
    # Look for similar keys that should match
    for i, key1 in enumerate(cache_keys[:10]):
        for key2 in cache_keys[i+1:11]:
            similarity = calculate_similarity(key1, key2)
            if similarity > 0.8:
                print(f"Similar keys: {key1} | {key2} (similarity: {similarity})")
```

**Solutions**:
1. **Improve Text Normalization**:
   ```python
   def normalize_for_cache(text):
       # Consistent normalization for cache keys
       text = text.lower().strip()
       text = re.sub(r'\s+', ' ', text)  # Normalize whitespace
       text = re.sub(r'[^\w\s:/-]', '', text)  # Remove punctuation
       text = re.sub(r'\b(a|an|the)\b', '', text)  # Remove articles
       return text
   ```

2. **Use Semantic Hashing**:
   ```python
   from sentence_transformers import SentenceTransformer
   
   class SemanticCache:
       def __init__(self):
           self.model = SentenceTransformer('all-MiniLM-L6-v2')
           self.cache = {}
           self.embeddings = {}
       
       def get_similar(self, text, threshold=0.9):
           embedding = self.model.encode([text])[0]
           
           for cached_text, cached_embedding in self.embeddings.items():
               similarity = cosine_similarity([embedding], [cached_embedding])[0][0]
               if similarity > threshold:
                   return self.cache[cached_text]
           
           return None
   ```

### Problem: Cache Invalidation Issues
**Symptoms**:
- Stale results returned from cache
- Cache grows indefinitely
- Inconsistent results for time-sensitive queries

**Solutions**:
1. **Implement TTL-based Expiration**:
   ```python
   import time
   
   class TTLCache:
       def __init__(self, ttl_seconds=3600):
           self.cache = {}
           self.ttl = ttl_seconds
       
       def get(self, key):
           if key in self.cache:
               value, timestamp = self.cache[key]
               if time.time() - timestamp < self.ttl:
                   return value
               else:
                   del self.cache[key]
           return None
       
       def set(self, key, value):
           self.cache[key] = (value, time.time())
   ```

2. **Add Cache Versioning**:
   ```python
   def generate_cache_key(text, field, version="v1.0"):
       content = f"{text}:{field}:{version}"
       return hashlib.md5(content.encode()).hexdigest()
   ```

## Monitoring and Alerting

### Set Up Performance Monitoring
```python
import logging
from datetime import datetime

class PerformanceMonitor:
    def __init__(self):
        self.metrics = {
            'request_count': 0,
            'total_processing_time': 0,
            'error_count': 0,
            'cache_hits': 0,
            'cache_misses': 0
        }
    
    def log_request(self, processing_time, cache_hit, error=None):
        self.metrics['request_count'] += 1
        self.metrics['total_processing_time'] += processing_time
        
        if cache_hit:
            self.metrics['cache_hits'] += 1
        else:
            self.metrics['cache_misses'] += 1
        
        if error:
            self.metrics['error_count'] += 1
            logging.error(f"Processing error: {error}")
        
        # Alert on high error rate
        error_rate = self.metrics['error_count'] / self.metrics['request_count']
        if error_rate > 0.1:  # 10% error rate
            self.send_alert(f"High error rate: {error_rate:.2%}")
    
    def send_alert(self, message):
        # Implement alerting (email, Slack, etc.)
        logging.critical(f"ALERT: {message}")
```

### Health Check Automation
```python
import requests
import time

def automated_health_check():
    """Run automated health checks every 5 minutes"""
    while True:
        try:
            # Check API health
            response = requests.get('http://localhost:8080/healthz', timeout=5)
            if response.status_code != 200:
                send_alert(f"API health check failed: {response.status_code}")
            
            # Check component health
            health_data = response.json()
            for component, status in health_data.get('components', {}).items():
                if status.get('status') != 'healthy':
                    send_alert(f"Component {component} is unhealthy: {status}")
            
        except Exception as e:
            send_alert(f"Health check failed: {e}")
        
        time.sleep(300)  # 5 minutes
```

## Getting Help

### Enable Debug Logging
```python
import logging

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('text_to_calendar')

# Add detailed logging to key functions
def parse_with_debug(text):
    logger.debug(f"Parsing text: {text}")
    
    # Log each processing step
    logger.debug("Starting regex extraction...")
    regex_result = regex_extractor.extract(text)
    logger.debug(f"Regex result: {regex_result}")
    
    if regex_result.confidence < 0.8:
        logger.debug("Starting deterministic backup...")
        backup_result = deterministic_backup.extract(text)
        logger.debug(f"Backup result: {backup_result}")
    
    return result
```

### Collect Diagnostic Information
```python
def collect_diagnostics():
    """Collect system diagnostic information"""
    diagnostics = {
        'timestamp': datetime.utcnow().isoformat(),
        'system_info': {
            'python_version': sys.version,
            'platform': platform.platform(),
            'memory_usage': psutil.virtual_memory()._asdict(),
            'cpu_usage': psutil.cpu_percent(interval=1)
        },
        'service_health': check_all_services_health(),
        'recent_errors': get_recent_errors(),
        'performance_metrics': get_performance_metrics(),
        'cache_stats': get_cache_stats()
    }
    
    return diagnostics
```

### Contact Support
When reporting issues, please include:
1. **Error messages and stack traces**
2. **Input text that caused the issue**
3. **Expected vs actual output**
4. **System diagnostic information**
5. **API response with audit mode enabled**
6. **Relevant log entries**

For urgent issues, enable debug mode and collect diagnostic information before contacting support.