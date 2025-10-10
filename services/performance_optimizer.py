"""
Performance Optimization Module for Text-to-Calendar Event Parser.

This module implements performance optimizations including:
- Lazy loading for heavy modules (Duckling, Recognizers)
- Regex pattern precompilation at startup
- Model warm-up on boot for reduced first-request latency
- Concurrent field processing with asyncio.gather()
- Timeout handling that returns partial results

Requirements addressed:
- 16.1: Lazy loading for heavy modules to reduce cold start time
- 16.4: Concurrent field processing for improved performance
- 16.5: Timeout handling that returns partial results
"""

import asyncio
import logging
import re
import time
from typing import Dict, List, Optional, Any, Callable, Tuple
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from dataclasses import dataclass
import threading

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetrics:
    """Performance metrics for monitoring optimization effectiveness."""
    module_load_times: Dict[str, float]
    regex_compilation_time: float
    warm_up_time: float
    concurrent_processing_speedup: float
    timeout_occurrences: int
    partial_result_returns: int


class LazyModuleLoader:
    """
    Lazy loader for heavy modules to reduce cold start time.
    
    Requirements:
    - 16.1: Lazy loading for heavy modules (Duckling, Recognizers)
    """
    
    def __init__(self):
        self._modules = {}
        self._loading_locks = {}
        self._load_times = {}
    
    def register_module(self, name: str, loader_func: Callable):
        """
        Register a module for lazy loading.
        
        Args:
            name: Module name
            loader_func: Function that loads and returns the module
        """
        self._modules[name] = {
            'loader': loader_func,
            'instance': None,
            'loaded': False,
            'loading': False
        }
        self._loading_locks[name] = threading.Lock()
    
    def get_module(self, name: str) -> Optional[Any]:
        """
        Get a module, loading it lazily if needed.
        
        Args:
            name: Module name
            
        Returns:
            Module instance or None if loading failed
        """
        if name not in self._modules:
            logger.warning(f"Module {name} not registered for lazy loading")
            return None
        
        module_info = self._modules[name]
        
        # Return cached instance if already loaded
        if module_info['loaded'] and module_info['instance'] is not None:
            return module_info['instance']
        
        # Load module with thread safety
        with self._loading_locks[name]:
            # Double-check after acquiring lock
            if module_info['loaded'] and module_info['instance'] is not None:
                return module_info['instance']
            
            if module_info['loading']:
                # Another thread is loading, wait briefly
                time.sleep(0.1)
                return module_info['instance']
            
            try:
                module_info['loading'] = True
                start_time = time.time()
                
                logger.info(f"Lazy loading module: {name}")
                instance = module_info['loader']()
                
                load_time = time.time() - start_time
                self._load_times[name] = load_time
                
                module_info['instance'] = instance
                module_info['loaded'] = True
                
                logger.info(f"Module {name} loaded in {load_time:.3f}s")
                return instance
                
            except Exception as e:
                logger.error(f"Failed to lazy load module {name}: {e}")
                return None
            finally:
                module_info['loading'] = False
    
    def is_loaded(self, name: str) -> bool:
        """Check if a module is loaded."""
        return name in self._modules and self._modules[name]['loaded']
    
    def get_load_times(self) -> Dict[str, float]:
        """Get load times for all modules."""
        return self._load_times.copy()
    
    def preload_module(self, name: str) -> bool:
        """
        Preload a module (useful for warm-up).
        
        Args:
            name: Module name
            
        Returns:
            True if loaded successfully, False otherwise
        """
        instance = self.get_module(name)
        return instance is not None


class RegexPatternCompiler:
    """
    Precompiles regex patterns at startup for better performance.
    
    Requirements:
    - Regex pattern precompilation at startup
    """
    
    def __init__(self):
        self.compiled_patterns: Dict[str, re.Pattern] = {}
        self.compilation_time = 0.0
    
    def register_patterns(self, patterns: Dict[str, str]):
        """
        Register and compile regex patterns.
        
        Args:
            patterns: Dictionary mapping pattern names to regex strings
        """
        start_time = time.time()
        
        for name, pattern in patterns.items():
            try:
                compiled = re.compile(pattern, re.IGNORECASE | re.MULTILINE)
                self.compiled_patterns[name] = compiled
                logger.debug(f"Compiled regex pattern: {name}")
            except re.error as e:
                logger.error(f"Failed to compile regex pattern {name}: {e}")
        
        self.compilation_time = time.time() - start_time
        logger.info(f"Compiled {len(self.compiled_patterns)} regex patterns in {self.compilation_time:.3f}s")
    
    def get_pattern(self, name: str) -> Optional[re.Pattern]:
        """Get a compiled regex pattern."""
        return self.compiled_patterns.get(name)
    
    def search(self, pattern_name: str, text: str) -> Optional[re.Match]:
        """Search text using a compiled pattern."""
        pattern = self.get_pattern(pattern_name)
        if pattern:
            return pattern.search(text)
        return None
    
    def findall(self, pattern_name: str, text: str) -> List[str]:
        """Find all matches using a compiled pattern."""
        pattern = self.get_pattern(pattern_name)
        if pattern:
            return pattern.findall(text)
        return []


class ModelWarmUp:
    """
    Handles model warm-up on boot for reduced first-request latency.
    
    Requirements:
    - Model warm-up on boot for reduced first-request latency
    """
    
    def __init__(self, lazy_loader: LazyModuleLoader):
        self.lazy_loader = lazy_loader
        self.warm_up_time = 0.0
        self.warm_up_results = {}
    
    def warm_up_models(self, test_inputs: Dict[str, str] = None) -> Dict[str, bool]:
        """
        Warm up models by running test inputs through them.
        
        Args:
            test_inputs: Dictionary mapping service names to test input strings
            
        Returns:
            Dictionary mapping service names to success status
        """
        start_time = time.time()
        
        if test_inputs is None:
            test_inputs = {
                'llm_service': "Meeting tomorrow at 2pm",
                'duckling_extractor': "next Friday at 3:30 PM",
                'recognizers_extractor': "January 15th at noon"
            }
        
        results = {}
        
        # Warm up LLM service
        try:
            llm_service = self.lazy_loader.get_module('llm_service')
            if llm_service:
                test_text = test_inputs.get('llm_service', "test meeting")
                response = llm_service.extract_event(test_text, current_date="2025-01-01")
                results['llm_service'] = response.success
                logger.info("LLM service warmed up successfully")
            else:
                results['llm_service'] = False
        except Exception as e:
            logger.warning(f"LLM service warm-up failed: {e}")
            results['llm_service'] = False
        
        # Warm up Duckling extractor
        try:
            duckling = self.lazy_loader.get_module('duckling_extractor')
            if duckling:
                test_text = test_inputs.get('duckling_extractor', "tomorrow at 2pm")
                result = duckling.extract_with_duckling(test_text, "time")
                results['duckling_extractor'] = result.value is not None
                logger.info("Duckling extractor warmed up successfully")
            else:
                results['duckling_extractor'] = False
        except Exception as e:
            logger.warning(f"Duckling extractor warm-up failed: {e}")
            results['duckling_extractor'] = False
        
        # Warm up Recognizers extractor
        try:
            recognizers = self.lazy_loader.get_module('recognizers_extractor')
            if recognizers:
                test_text = test_inputs.get('recognizers_extractor', "next week")
                result = recognizers.extract_with_recognizers(test_text, "time")
                results['recognizers_extractor'] = result.value is not None
                logger.info("Recognizers extractor warmed up successfully")
            else:
                results['recognizers_extractor'] = False
        except Exception as e:
            logger.warning(f"Recognizers extractor warm-up failed: {e}")
            results['recognizers_extractor'] = False
        
        self.warm_up_time = time.time() - start_time
        self.warm_up_results = results
        
        successful_warmups = sum(1 for success in results.values() if success)
        logger.info(f"Model warm-up completed in {self.warm_up_time:.3f}s ({successful_warmups}/{len(results)} successful)")
        
        return results


class ConcurrentFieldProcessor:
    """
    Implements concurrent field processing with asyncio.gather().
    
    Requirements:
    - 16.4: Concurrent field processing with asyncio.gather()
    """
    
    def __init__(self, max_workers: int = 4):
        self.max_workers = max_workers
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
    
    async def process_fields_concurrently(self, 
                                        field_processors: Dict[str, Callable],
                                        text: str,
                                        timeout_seconds: float = 10.0) -> Dict[str, Any]:
        """
        Process multiple fields concurrently using asyncio.gather().
        
        Args:
            field_processors: Dictionary mapping field names to processor functions
            text: Input text to process
            timeout_seconds: Timeout for concurrent processing
            
        Returns:
            Dictionary mapping field names to processing results
        """
        async def process_field(field_name: str, processor: Callable) -> Tuple[str, Any]:
            """Process a single field asynchronously."""
            try:
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(self.executor, processor, text)
                return field_name, result
            except Exception as e:
                logger.warning(f"Field processing failed for {field_name}: {e}")
                return field_name, None
        
        # Create tasks for all fields
        tasks = [
            process_field(field_name, processor)
            for field_name, processor in field_processors.items()
        ]
        
        try:
            # Process all fields concurrently with timeout
            results = await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True),
                timeout=timeout_seconds
            )
            
            # Convert results to dictionary
            field_results = {}
            for result in results:
                if isinstance(result, tuple) and len(result) == 2:
                    field_name, field_result = result
                    field_results[field_name] = field_result
                elif isinstance(result, Exception):
                    logger.warning(f"Field processing exception: {result}")
            
            return field_results
            
        except asyncio.TimeoutError:
            logger.warning(f"Concurrent field processing timed out after {timeout_seconds}s")
            # Return partial results from completed tasks
            return await self._get_partial_results(tasks, timeout_seconds / 2)
    
    async def _get_partial_results(self, tasks: List[asyncio.Task], 
                                 partial_timeout: float) -> Dict[str, Any]:
        """
        Get partial results from tasks that completed before timeout.
        
        Args:
            tasks: List of asyncio tasks
            partial_timeout: Timeout for collecting partial results
            
        Returns:
            Dictionary of completed results
        """
        try:
            done, pending = await asyncio.wait(
                tasks, 
                timeout=partial_timeout,
                return_when=asyncio.FIRST_COMPLETED
            )
            
            # Cancel pending tasks
            for task in pending:
                task.cancel()
            
            # Collect results from completed tasks
            partial_results = {}
            for task in done:
                try:
                    result = await task
                    if isinstance(result, tuple) and len(result) == 2:
                        field_name, field_result = result
                        partial_results[field_name] = field_result
                except Exception as e:
                    logger.warning(f"Error collecting partial result: {e}")
            
            logger.info(f"Collected {len(partial_results)} partial results")
            return partial_results
            
        except Exception as e:
            logger.error(f"Error collecting partial results: {e}")
            return {}


class TimeoutHandler:
    """
    Handles timeouts and returns partial results.
    
    Requirements:
    - 16.5: Timeout handling that returns partial results
    """
    
    def __init__(self):
        self.timeout_count = 0
        self.partial_result_count = 0
    
    async def execute_with_timeout(self,
                                 operation: Callable,
                                 timeout_seconds: float,
                                 fallback_result: Any = None,
                                 partial_result_collector: Optional[Callable] = None) -> Any:
        """
        Execute an operation with timeout and partial result handling.
        
        Args:
            operation: Async operation to execute
            timeout_seconds: Timeout in seconds
            fallback_result: Result to return if operation fails completely
            partial_result_collector: Function to collect partial results on timeout
            
        Returns:
            Operation result, partial result, or fallback result
        """
        try:
            # Execute operation with timeout
            result = await asyncio.wait_for(operation(), timeout=timeout_seconds)
            return result
            
        except asyncio.TimeoutError:
            self.timeout_count += 1
            logger.warning(f"Operation timed out after {timeout_seconds}s")
            
            # Try to collect partial results
            if partial_result_collector:
                try:
                    partial_result = await asyncio.wait_for(
                        partial_result_collector(),
                        timeout=timeout_seconds / 4  # Quick partial collection
                    )
                    if partial_result:
                        self.partial_result_count += 1
                        logger.info("Returning partial results due to timeout")
                        return partial_result
                except asyncio.TimeoutError:
                    logger.warning("Partial result collection also timed out")
            
            # Return fallback result
            logger.info("Returning fallback result due to timeout")
            return fallback_result
            
        except Exception as e:
            logger.error(f"Operation failed with exception: {e}")
            return fallback_result
    
    def execute_with_timeout_sync(self,
                                operation: Callable,
                                timeout_seconds: float,
                                fallback_result: Any = None) -> Any:
        """
        Execute a synchronous operation with timeout.
        
        Args:
            operation: Synchronous operation to execute
            timeout_seconds: Timeout in seconds
            fallback_result: Result to return if operation fails
            
        Returns:
            Operation result or fallback result
        """
        try:
            # Use ThreadPoolExecutor for timeout handling
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(operation)
                result = future.result(timeout=timeout_seconds)
                return result
                
        except FutureTimeoutError:
            self.timeout_count += 1
            logger.warning(f"Synchronous operation timed out after {timeout_seconds}s")
            return fallback_result
            
        except Exception as e:
            logger.error(f"Synchronous operation failed: {e}")
            return fallback_result
    
    def get_timeout_stats(self) -> Dict[str, int]:
        """Get timeout statistics."""
        return {
            'timeout_count': self.timeout_count,
            'partial_result_count': self.partial_result_count
        }


class PerformanceOptimizer:
    """
    Main performance optimization coordinator.
    
    Integrates all performance optimization features:
    - Lazy loading
    - Regex precompilation
    - Model warm-up
    - Concurrent processing
    - Timeout handling
    """
    
    def __init__(self):
        self.lazy_loader = LazyModuleLoader()
        self.regex_compiler = RegexPatternCompiler()
        self.model_warmup = ModelWarmUp(self.lazy_loader)
        self.concurrent_processor = ConcurrentFieldProcessor()
        self.timeout_handler = TimeoutHandler()
        
        self.initialized = False
        self.initialization_time = 0.0
    
    def initialize(self, 
                  regex_patterns: Dict[str, str] = None,
                  warm_up_inputs: Dict[str, str] = None) -> PerformanceMetrics:
        """
        Initialize all performance optimizations.
        
        Args:
            regex_patterns: Regex patterns to precompile
            warm_up_inputs: Test inputs for model warm-up
            
        Returns:
            Performance metrics from initialization
        """
        start_time = time.time()
        
        # Register lazy-loaded modules
        self._register_lazy_modules()
        
        # Compile regex patterns
        if regex_patterns:
            self.regex_compiler.register_patterns(regex_patterns)
        else:
            self._register_default_patterns()
        
        # Warm up models (optional, can be done in background)
        warm_up_results = self.model_warmup.warm_up_models(warm_up_inputs)
        
        self.initialization_time = time.time() - start_time
        self.initialized = True
        
        logger.info(f"Performance optimizer initialized in {self.initialization_time:.3f}s")
        
        # Create performance metrics
        metrics = PerformanceMetrics(
            module_load_times=self.lazy_loader.get_load_times(),
            regex_compilation_time=self.regex_compiler.compilation_time,
            warm_up_time=self.model_warmup.warm_up_time,
            concurrent_processing_speedup=0.0,  # Will be measured during usage
            timeout_occurrences=0,
            partial_result_returns=0
        )
        
        return metrics
    
    def _register_lazy_modules(self):
        """Register modules for lazy loading."""
        
        def load_llm_service():
            from services.llm_service import get_llm_service
            return get_llm_service()
        
        def load_duckling_extractor():
            from services.duckling_extractor import DucklingExtractor
            return DucklingExtractor()
        
        def load_recognizers_extractor():
            from services.recognizers_extractor import RecognizersExtractor
            return RecognizersExtractor()
        
        def load_location_extractor():
            from services.advanced_location_extractor import AdvancedLocationExtractor
            return AdvancedLocationExtractor()
        
        def load_llm_enhancer():
            from services.llm_enhancer import LLMEnhancer
            return LLMEnhancer()
        
        self.lazy_loader.register_module('llm_service', load_llm_service)
        self.lazy_loader.register_module('duckling_extractor', load_duckling_extractor)
        self.lazy_loader.register_module('recognizers_extractor', load_recognizers_extractor)
        self.lazy_loader.register_module('location_extractor', load_location_extractor)
        self.lazy_loader.register_module('llm_enhancer', load_llm_enhancer)
    
    def _register_default_patterns(self):
        """Register default regex patterns for precompilation."""
        default_patterns = {
            # Date patterns
            'date_slash': r'\b\d{1,2}/\d{1,2}/\d{4}\b',
            'date_dash': r'\b\d{1,2}-\d{1,2}-\d{4}\b',
            'date_dot': r'\b\d{1,2}\.\d{1,2}\.\d{4}\b',
            'date_written': r'\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+\d{1,2},?\s+\d{4}\b',
            
            # Time patterns
            'time_12hour': r'\b\d{1,2}:\d{2}\s*(?:am|pm|a\.m|p\.m)\b',
            'time_24hour': r'\b\d{1,2}:\d{2}\b',
            'time_simple': r'\b\d{1,2}\s*(?:am|pm|a\.m|p\.m)\b',
            
            # Relative date patterns
            'relative_day': r'\b(?:today|tomorrow|yesterday)\b',
            'relative_week': r'\b(?:this|next|last)\s+(?:week|monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b',
            'relative_month': r'\b(?:this|next|last)\s+month\b',
            
            # Duration patterns
            'duration_hours': r'\b\d+\s*(?:hour|hr)s?\b',
            'duration_minutes': r'\b\d+\s*(?:minute|min)s?\b',
            'duration_for': r'\bfor\s+\d+\s*(?:hour|minute|hr|min)s?\b',
            
            # Location patterns
            'location_at': r'\bat\s+([^,\n]+?)(?:\s*,|\s*\n|$)',
            'location_in': r'\bin\s+([^,\n]+?)(?:\s*,|\s*\n|$)',
            'location_room': r'\broom\s+([a-z0-9]+)\b',
            
            # Title patterns
            'title_meeting': r'\b(?:meeting|call|conference|session)\s+(?:with|about|on)\s+([^,\n]+)',
            'title_event': r'\b(?:event|gathering|party|celebration)\s*:?\s*([^,\n]+)',
            
            # Email patterns
            'email_subject': r'subject\s*:\s*([^\n]+)',
            'email_from': r'from\s*:\s*([^\n]+)',
            'email_to': r'to\s*:\s*([^\n]+)',
        }
        
        self.regex_compiler.register_patterns(default_patterns)
    
    def get_lazy_module(self, name: str) -> Optional[Any]:
        """Get a lazy-loaded module."""
        return self.lazy_loader.get_module(name)
    
    def get_regex_pattern(self, name: str) -> Optional[re.Pattern]:
        """Get a precompiled regex pattern."""
        return self.regex_compiler.get_pattern(name)
    
    async def process_fields_with_optimization(self,
                                             field_processors: Dict[str, Callable],
                                             text: str,
                                             timeout_seconds: float = 10.0) -> Dict[str, Any]:
        """
        Process fields with all optimizations applied.
        
        Args:
            field_processors: Field processing functions
            text: Input text
            timeout_seconds: Processing timeout
            
        Returns:
            Field processing results
        """
        return await self.concurrent_processor.process_fields_concurrently(
            field_processors, text, timeout_seconds
        )
    
    async def execute_with_timeout(self,
                                 operation: Callable,
                                 timeout_seconds: float,
                                 fallback_result: Any = None) -> Any:
        """Execute operation with timeout handling."""
        return await self.timeout_handler.execute_with_timeout(
            operation, timeout_seconds, fallback_result
        )
    
    def get_performance_metrics(self) -> PerformanceMetrics:
        """Get current performance metrics."""
        timeout_stats = self.timeout_handler.get_timeout_stats()
        
        return PerformanceMetrics(
            module_load_times=self.lazy_loader.get_load_times(),
            regex_compilation_time=self.regex_compiler.compilation_time,
            warm_up_time=self.model_warmup.warm_up_time,
            concurrent_processing_speedup=0.0,  # Would need benchmarking to measure
            timeout_occurrences=timeout_stats['timeout_count'],
            partial_result_returns=timeout_stats['partial_result_count']
        )
    
    def is_initialized(self) -> bool:
        """Check if optimizer is initialized."""
        return self.initialized


# Global instance
_performance_optimizer = None

def get_performance_optimizer() -> PerformanceOptimizer:
    """Get the global performance optimizer instance."""
    global _performance_optimizer
    if _performance_optimizer is None:
        _performance_optimizer = PerformanceOptimizer()
    return _performance_optimizer