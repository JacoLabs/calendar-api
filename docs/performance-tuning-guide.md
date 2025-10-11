# Performance Tuning Guide and Best Practices

## Overview

This guide provides comprehensive strategies for optimizing the performance of the enhanced text-to-calendar event parsing system. It covers configuration tuning, resource optimization, caching strategies, and monitoring best practices to achieve optimal performance across all system components.

## Performance Targets

### Baseline Performance Goals
- **API Response Time**: p50 ≤ 1.5s, p95 ≤ 3.0s
- **Cache Hit Rate**: ≥ 60% for production workloads
- **Error Rate**: ≤ 2% for valid input text
- **Memory Usage**: ≤ 512MB per API instance
- **CPU Usage**: ≤ 70% average under normal load

### Component-Specific Targets
| Component | Target Latency | Success Rate |
|-----------|----------------|--------------|
| Regex Extraction | ≤ 50ms | ≥ 95% |
| Deterministic Backup | ≤ 200ms | ≥ 85% |
| LLM Enhancement | ≤ 2000ms | ≥ 90% |
| Cache Operations | ≤ 5ms | ≥ 99% |

## Configuration Optimization

### Confidence Threshold Tuning

**Default Configuration**:
```python
CONFIDENCE_THRESHOLDS = {
    'regex_only': 0.8,
    'deterministic_backup': 0.6,
    'llm_enhancement': 0.0
}
```

**Performance-Optimized Configuration**:
```python
# Reduce LLM usage by raising thresholds
PERFORMANCE_OPTIMIZED_THRESHOLDS = {
    'regex_only': 0.75,        # Slightly lower to catch more cases
    'deterministic_backup': 0.5, # Lower to use more deterministic parsing
    'llm_enhancement': 0.0
}

# Quality-Optimized Configuration
QUALITY_OPTIMIZED_THRESHOLDS = {
    'regex_only': 0.85,        # Higher for better accuracy
    'deterministic_backup': 0.7, # Higher threshold
    'llm_enhancement': 0.0
}
```

**Dynamic Threshold Adjustment**:
```python
class AdaptiveThresholds:
    def __init__(self):
        self.base_thresholds = CONFIDENCE_THRESHOLDS.copy()
        self.performance_history = []
    
    def adjust_thresholds(self, recent_performance):
        """Adjust thresholds based on recent performance metrics"""
        avg_response_time = recent_performance.get('avg_response_time', 0)
        error_rate = recent_performance.get('error_rate', 0)
        
        # If response time is high, reduce LLM usage
        if avg_response_time > 2000:  # 2 seconds
            self.base_thresholds['regex_only'] -= 0.05
            self.base_thresholds['deterministic_backup'] -= 0.05
        
        # If error rate is high, increase quality thresholds
        elif error_rate > 0.05:  # 5% error rate
            self.base_thresholds['regex_only'] += 0.05
            self.base_thresholds['deterministic_backup'] += 0.05
        
        # Clamp values to reasonable ranges
        self.base_thresholds['regex_only'] = max(0.6, min(0.9, self.base_thresholds['regex_only']))
        self.base_thresholds['deterministic_backup'] = max(0.4, min(0.8, self.base_thresholds['deterministic_backup']))
        
        return self.base_thresholds
```

### LLM Configuration Optimization

**Fast Response Configuration**:
```python
LLM_FAST_CONFIG = {
    'model': 'llama3.2:1b',      # Smaller, faster model
    'temperature': 0.0,           # Deterministic output
    'max_tokens': 150,           # Limit response length
    'timeout': 1.5,              # Aggressive timeout
    'max_retries': 1,            # Single retry only
    'context_limit': 300         # Reduced context size
}
```

**Balanced Configuration**:
```python
LLM_BALANCED_CONFIG = {
    'model': 'llama3.2:3b',      # Better quality
    'temperature': 0.0,
    'max_tokens': 200,
    'timeout': 3.0,              # Standard timeout
    'max_retries': 2,
    'context_limit': 500
}
```

**Quality-First Configuration**:
```python
LLM_QUALITY_CONFIG = {
    'model': 'llama3.2:8b',      # Highest quality
    'temperature': 0.1,          # Slight randomness for creativity
    'max_tokens': 300,
    'timeout': 5.0,              # Longer timeout
    'max_retries': 3,
    'context_limit': 800
}
```

### Deterministic Backup Optimization

**Duckling Configuration**:
```python
DUCKLING_OPTIMIZED_CONFIG = {
    'url': 'http://localhost:8000/parse',
    'timeout': 1.0,              # Reduced timeout
    'connection_pool_size': 10,   # Connection pooling
    'max_retries': 1,
    'supported_dimensions': [
        'time',                   # Only essential dimensions
        'duration'
    ],
    'cache_results': True,        # Enable result caching
    'cache_ttl': 3600            # 1 hour cache
}
```

**Microsoft Recognizers Optimization**:
```python
class OptimizedRecognizersExtractor:
    def __init__(self):
        # Pre-initialize recognizers to avoid startup cost
        self.datetime_recognizer = DateTimeRecognizer()
        self.number_recognizer = NumberRecognizer()
        
        # Cache compiled patterns
        self._pattern_cache = {}
        
        # Limit supported cultures for performance
        self.supported_cultures = [Culture.English]  # Only English for speed
    
    @lru_cache(maxsize=1000)
    def cached_recognize(self, text_hash, culture):
        """Cache recognition results"""
        return self.datetime_recognizer.recognize(text, culture)
```

## Caching Strategies

### Multi-Level Caching Architecture

```python
class MultiLevelCache:
    def __init__(self):
        # L1: In-memory LRU cache (fastest)
        self.l1_cache = LRUCache(maxsize=500)
        
        # L2: Redis cache (shared across instances)
        self.l2_cache = redis.Redis(host='localhost', port=6379, db=0)
        
        # L3: Database cache (persistent)
        self.l3_cache = DatabaseCache()
    
    async def get(self, key):
        # Try L1 first
        result = self.l1_cache.get(key)
        if result:
            return result
        
        # Try L2
        result = await self.l2_cache.get(key)
        if result:
            # Promote to L1
            self.l1_cache.set(key, result)
            return result
        
        # Try L3
        result = await self.l3_cache.get(key)
        if result:
            # Promote to L2 and L1
            await self.l2_cache.setex(key, 3600, result)
            self.l1_cache.set(key, result)
            return result
        
        return None
    
    async def set(self, key, value, ttl=3600):
        # Set in all levels
        self.l1_cache.set(key, value)
        await self.l2_cache.setex(key, ttl, value)
        await self.l3_cache.set(key, value, ttl)
```

### Intelligent Cache Key Generation

```python
class SmartCacheKeyGenerator:
    def __init__(self):
        self.normalizer = TextNormalizer()
        self.feature_extractor = FeatureExtractor()
    
    def generate_key(self, text, fields=None, mode='hybrid'):
        """Generate cache key with semantic awareness"""
        # Normalize text for consistent caching
        normalized_text = self.normalizer.normalize(text)
        
        # Extract semantic features
        features = self.feature_extractor.extract_features(normalized_text)
        
        # Create feature-based key
        feature_hash = hashlib.md5(
            json.dumps(features, sort_keys=True).encode()
        ).hexdigest()[:8]
        
        # Include processing parameters
        params = {
            'fields': sorted(fields) if fields else 'all',
            'mode': mode,
            'version': 'v1.0'
        }
        param_hash = hashlib.md5(
            json.dumps(params, sort_keys=True).encode()
        ).hexdigest()[:8]
        
        return f"{feature_hash}:{param_hash}"

class TextNormalizer:
    def normalize(self, text):
        """Normalize text for consistent caching"""
        # Convert to lowercase
        text = text.lower()
        
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove punctuation except time/date separators
        text = re.sub(r'[^\w\s:/-]', '', text)
        
        # Normalize common variations
        replacements = {
            r'\bam\b': 'a.m.',
            r'\bpm\b': 'p.m.',
            r'\btomorrow\b': 'tomorrow',
            r'\btoday\b': 'today'
        }
        
        for pattern, replacement in replacements.items():
            text = re.sub(pattern, replacement, text)
        
        return text.strip()
```

### Cache Warming Strategies

```python
class CacheWarmer:
    def __init__(self, cache, parser):
        self.cache = cache
        self.parser = parser
        self.common_patterns = [
            "meeting tomorrow at 2pm",
            "lunch next Friday at noon",
            "conference call today at 3:30pm",
            "dinner tonight at 7pm",
            "appointment next Monday at 10am"
        ]
    
    async def warm_cache(self):
        """Pre-populate cache with common patterns"""
        tasks = []
        for pattern in self.common_patterns:
            task = asyncio.create_task(self._warm_pattern(pattern))
            tasks.append(task)
        
        await asyncio.gather(*tasks)
    
    async def _warm_pattern(self, pattern):
        """Warm cache for a specific pattern"""
        try:
            result = await self.parser.parse_event_text(pattern)
            cache_key = self.cache.generate_key(pattern)
            await self.cache.set(cache_key, result)
        except Exception as e:
            logger.warning(f"Cache warming failed for pattern '{pattern}': {e}")
    
    def schedule_warming(self):
        """Schedule regular cache warming"""
        import schedule
        
        # Warm cache every 6 hours
        schedule.every(6).hours.do(self.warm_cache)
        
        # Initial warming
        asyncio.create_task(self.warm_cache())
```

## Resource Optimization

### Memory Management

```python
import gc
import psutil
from typing import Optional

class MemoryManager:
    def __init__(self, max_memory_mb: int = 512):
        self.max_memory_mb = max_memory_mb
        self.cleanup_threshold = 0.8  # Cleanup at 80% of max
        
    def check_memory_usage(self) -> float:
        """Check current memory usage as percentage of max"""
        process = psutil.Process()
        current_mb = process.memory_info().rss / 1024 / 1024
        return current_mb / self.max_memory_mb
    
    def cleanup_if_needed(self):
        """Perform cleanup if memory usage is high"""
        usage = self.check_memory_usage()
        
        if usage > self.cleanup_threshold:
            logger.info(f"Memory usage at {usage:.1%}, performing cleanup")
            
            # Clear caches
            self._clear_caches()
            
            # Force garbage collection
            gc.collect()
            
            # Check if cleanup was effective
            new_usage = self.check_memory_usage()
            logger.info(f"Memory usage after cleanup: {new_usage:.1%}")
    
    def _clear_caches(self):
        """Clear various caches to free memory"""
        # Clear LRU caches
        for obj in gc.get_objects():
            if hasattr(obj, 'cache_clear'):
                try:
                    obj.cache_clear()
                except:
                    pass
        
        # Clear custom caches
        if hasattr(self, 'regex_cache'):
            self.regex_cache.clear()
        
        if hasattr(self, 'pattern_cache'):
            self.pattern_cache.clear()

# Memory monitoring decorator
def monitor_memory(func):
    def wrapper(*args, **kwargs):
        memory_manager = MemoryManager()
        
        # Check memory before execution
        memory_manager.cleanup_if_needed()
        
        # Execute function
        result = func(*args, **kwargs)
        
        # Check memory after execution
        memory_manager.cleanup_if_needed()
        
        return result
    
    return wrapper
```

### CPU Optimization

```python
import asyncio
import concurrent.futures
from multiprocessing import cpu_count

class CPUOptimizer:
    def __init__(self):
        self.cpu_count = cpu_count()
        self.thread_pool = concurrent.futures.ThreadPoolExecutor(
            max_workers=min(4, self.cpu_count)
        )
        self.process_pool = concurrent.futures.ProcessPoolExecutor(
            max_workers=max(1, self.cpu_count // 2)
        )
    
    async def process_fields_parallel(self, text: str, fields: list) -> dict:
        """Process multiple fields in parallel"""
        loop = asyncio.get_event_loop()
        
        # Create tasks for each field
        tasks = []
        for field in fields:
            if self._is_cpu_intensive(field):
                # Use process pool for CPU-intensive tasks
                task = loop.run_in_executor(
                    self.process_pool,
                    self._process_field_cpu_intensive,
                    text, field
                )
            else:
                # Use thread pool for I/O-bound tasks
                task = loop.run_in_executor(
                    self.thread_pool,
                    self._process_field_io_bound,
                    text, field
                )
            tasks.append((field, task))
        
        # Wait for all tasks to complete
        results = {}
        for field, task in tasks:
            try:
                result = await task
                results[field] = result
            except Exception as e:
                logger.error(f"Field {field} processing failed: {e}")
                results[field] = None
        
        return results
    
    def _is_cpu_intensive(self, field: str) -> bool:
        """Determine if field processing is CPU-intensive"""
        cpu_intensive_fields = ['title', 'description']  # LLM processing
        return field in cpu_intensive_fields
    
    def _process_field_cpu_intensive(self, text: str, field: str):
        """Process CPU-intensive field (runs in separate process)"""
        # This runs in a separate process, so imports are needed
        from services.llm_enhancer import LLMEnhancer
        enhancer = LLMEnhancer()
        return enhancer.enhance_field(text, field)
    
    def _process_field_io_bound(self, text: str, field: str):
        """Process I/O-bound field (runs in thread pool)"""
        from services.regex_date_extractor import RegexDateExtractor
        extractor = RegexDateExtractor()
        return extractor.extract_field(text, field)
```

### Lazy Loading Implementation

```python
class LazyComponentLoader:
    def __init__(self):
        self._components = {}
        self._loading_locks = {}
    
    def get_component(self, component_name: str):
        """Get component with lazy loading"""
        if component_name not in self._components:
            # Use lock to prevent multiple threads from loading same component
            if component_name not in self._loading_locks:
                self._loading_locks[component_name] = asyncio.Lock()
            
            async with self._loading_locks[component_name]:
                if component_name not in self._components:
                    self._components[component_name] = self._load_component(component_name)
        
        return self._components[component_name]
    
    def _load_component(self, component_name: str):
        """Load component on demand"""
        start_time = time.time()
        
        if component_name == 'duckling':
            from services.duckling_extractor import DucklingExtractor
            component = DucklingExtractor(DUCKLING_CONFIG)
        elif component_name == 'recognizers':
            from services.recognizers_extractor import RecognizersExtractor
            component = RecognizersExtractor()
        elif component_name == 'llm':
            from services.llm_enhancer import LLMEnhancer
            component = LLMEnhancer(LLM_CONFIG)
        else:
            raise ValueError(f"Unknown component: {component_name}")
        
        load_time = time.time() - start_time
        logger.info(f"Loaded {component_name} in {load_time:.2f}s")
        
        return component

# Usage in main parser
class OptimizedHybridEventParser:
    def __init__(self):
        self.loader = LazyComponentLoader()
        self.regex_extractor = RegexDateExtractor()  # Always loaded (lightweight)
    
    async def parse_event_text(self, text: str, mode: str = "hybrid") -> ParsedEvent:
        # Always try regex first (no lazy loading needed)
        regex_results = self.regex_extractor.extract_all_fields(text)
        
        # Only load other components if needed
        needs_deterministic = any(r.confidence < 0.8 for r in regex_results.values())
        needs_llm = any(r.confidence < 0.6 for r in regex_results.values())
        
        if needs_deterministic:
            duckling = await self.loader.get_component('duckling')
            recognizers = await self.loader.get_component('recognizers')
            # Process with deterministic backup
        
        if needs_llm:
            llm = await self.loader.get_component('llm')
            # Process with LLM enhancement
        
        return self._aggregate_results(regex_results, deterministic_results, llm_results)
```

## Monitoring and Profiling

### Performance Metrics Collection

```python
import time
import statistics
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Dict, List

@dataclass
class PerformanceMetrics:
    component: str
    operation: str
    duration_ms: float
    success: bool
    timestamp: float
    memory_usage_mb: float
    cpu_usage_percent: float

class PerformanceCollector:
    def __init__(self, window_size: int = 1000):
        self.metrics = defaultdict(lambda: deque(maxlen=window_size))
        self.window_size = window_size
    
    def record_metric(self, metric: PerformanceMetrics):
        """Record a performance metric"""
        key = f"{metric.component}:{metric.operation}"
        self.metrics[key].append(metric)
    
    def get_statistics(self, component: str, operation: str) -> Dict:
        """Get performance statistics for a component/operation"""
        key = f"{component}:{operation}"
        metrics = list(self.metrics[key])
        
        if not metrics:
            return {}
        
        durations = [m.duration_ms for m in metrics]
        success_rate = sum(1 for m in metrics if m.success) / len(metrics)
        
        return {
            'count': len(metrics),
            'avg_duration_ms': statistics.mean(durations),
            'p50_duration_ms': statistics.median(durations),
            'p95_duration_ms': statistics.quantiles(durations, n=20)[18] if len(durations) > 20 else max(durations),
            'p99_duration_ms': statistics.quantiles(durations, n=100)[98] if len(durations) > 100 else max(durations),
            'success_rate': success_rate,
            'error_rate': 1 - success_rate
        }
    
    def get_all_statistics(self) -> Dict:
        """Get statistics for all components/operations"""
        stats = {}
        for key in self.metrics:
            component, operation = key.split(':', 1)
            stats[key] = self.get_statistics(component, operation)
        return stats

# Performance monitoring decorator
def monitor_performance(component: str, operation: str):
    def decorator(func):
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            start_memory = psutil.Process().memory_info().rss / 1024 / 1024
            start_cpu = psutil.cpu_percent()
            
            success = True
            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                success = False
                raise
            finally:
                end_time = time.time()
                end_memory = psutil.Process().memory_info().rss / 1024 / 1024
                end_cpu = psutil.cpu_percent()
                
                metric = PerformanceMetrics(
                    component=component,
                    operation=operation,
                    duration_ms=(end_time - start_time) * 1000,
                    success=success,
                    timestamp=end_time,
                    memory_usage_mb=end_memory - start_memory,
                    cpu_usage_percent=(end_cpu + start_cpu) / 2
                )
                
                performance_collector.record_metric(metric)
        
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            start_memory = psutil.Process().memory_info().rss / 1024 / 1024
            start_cpu = psutil.cpu_percent()
            
            success = True
            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                success = False
                raise
            finally:
                end_time = time.time()
                end_memory = psutil.Process().memory_info().rss / 1024 / 1024
                end_cpu = psutil.cpu_percent()
                
                metric = PerformanceMetrics(
                    component=component,
                    operation=operation,
                    duration_ms=(end_time - start_time) * 1000,
                    success=success,
                    timestamp=end_time,
                    memory_usage_mb=end_memory - start_memory,
                    cpu_usage_percent=(end_cpu + start_cpu) / 2
                )
                
                performance_collector.record_metric(metric)
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator

# Global performance collector
performance_collector = PerformanceCollector()
```

### Real-time Performance Dashboard

```python
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import json

app = FastAPI()

@app.get("/performance/dashboard")
async def performance_dashboard():
    """Real-time performance dashboard"""
    stats = performance_collector.get_all_statistics()
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Performance Dashboard</title>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; }}
            .metric-card {{ 
                border: 1px solid #ddd; 
                padding: 15px; 
                margin: 10px; 
                border-radius: 5px; 
                display: inline-block;
                min-width: 300px;
            }}
            .metric-title {{ font-weight: bold; font-size: 18px; }}
            .metric-value {{ font-size: 24px; color: #007bff; }}
            .error {{ color: #dc3545; }}
            .success {{ color: #28a745; }}
        </style>
    </head>
    <body>
        <h1>Performance Dashboard</h1>
        <div id="metrics">
            {generate_metric_cards(stats)}
        </div>
        
        <script>
            // Auto-refresh every 30 seconds
            setInterval(() => {{
                location.reload();
            }}, 30000);
        </script>
    </body>
    </html>
    """
    
    return HTMLResponse(content=html_content)

def generate_metric_cards(stats: Dict) -> str:
    """Generate HTML metric cards"""
    cards = []
    
    for key, stat in stats.items():
        component, operation = key.split(':', 1)
        
        success_class = "success" if stat['success_rate'] > 0.95 else "error"
        performance_class = "success" if stat['p95_duration_ms'] < 2000 else "error"
        
        card = f"""
        <div class="metric-card">
            <div class="metric-title">{component.title()} - {operation.title()}</div>
            <div>Count: <span class="metric-value">{stat['count']}</span></div>
            <div>Avg Duration: <span class="metric-value {performance_class}">{stat['avg_duration_ms']:.1f}ms</span></div>
            <div>P95 Duration: <span class="metric-value {performance_class}">{stat['p95_duration_ms']:.1f}ms</span></div>
            <div>Success Rate: <span class="metric-value {success_class}">{stat['success_rate']:.1%}</span></div>
        </div>
        """
        cards.append(card)
    
    return ''.join(cards)

@app.get("/performance/metrics")
async def get_performance_metrics():
    """API endpoint for performance metrics"""
    return performance_collector.get_all_statistics()
```

## Best Practices Summary

### Configuration Best Practices

1. **Start with Performance-Optimized Settings**: Use lower confidence thresholds to reduce LLM usage
2. **Monitor and Adjust**: Use adaptive thresholds based on performance metrics
3. **Environment-Specific Tuning**: Different settings for development, staging, and production
4. **A/B Testing**: Test configuration changes with a subset of traffic

### Caching Best Practices

1. **Multi-Level Caching**: Implement L1 (memory), L2 (Redis), L3 (database) caching
2. **Smart Cache Keys**: Use semantic features for better cache hit rates
3. **Cache Warming**: Pre-populate cache with common patterns
4. **TTL Management**: Use appropriate TTL values based on data volatility

### Resource Management Best Practices

1. **Lazy Loading**: Load components only when needed
2. **Memory Monitoring**: Implement automatic cleanup at memory thresholds
3. **Parallel Processing**: Use async/await and thread pools for concurrent operations
4. **Connection Pooling**: Reuse connections to external services

### Monitoring Best Practices

1. **Comprehensive Metrics**: Track latency, success rate, memory, and CPU usage
2. **Real-time Dashboards**: Provide visibility into system performance
3. **Alerting**: Set up alerts for performance degradation
4. **Regular Reviews**: Analyze performance trends and optimize accordingly

### Deployment Best Practices

1. **Load Testing**: Test performance under expected load
2. **Gradual Rollouts**: Deploy configuration changes gradually
3. **Rollback Plans**: Have quick rollback procedures for performance issues
4. **Capacity Planning**: Monitor resource usage and plan for scaling

### Development Best Practices

1. **Performance Testing**: Include performance tests in CI/CD pipeline
2. **Profiling**: Regular profiling to identify bottlenecks
3. **Code Reviews**: Review performance implications of code changes
4. **Documentation**: Keep performance tuning documentation up to date