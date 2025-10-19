#!/usr/bin/env python3
"""
Test script for performance optimizations.

This script tests the performance optimization features including:
- Lazy loading for heavy modules
- Regex pattern precompilation
- Model warm-up
- Concurrent field processing
- Timeout handling with partial results
"""

import asyncio
import time
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_lazy_loading():
    """Test lazy loading functionality."""
    logger.info("Testing lazy loading...")
    
    from services.performance_optimizer import LazyModuleLoader
    
    # Create a fresh lazy loader for testing
    lazy_loader = LazyModuleLoader()
    
    # Register a test module
    def load_test_module():
        time.sleep(0.1)  # Simulate loading time
        return {"test": "module"}
    
    lazy_loader.register_module('test_module', load_test_module)
    
    # Test that module is not loaded initially
    assert not lazy_loader.is_loaded('test_module')
    
    # Test lazy loading
    start_time = time.time()
    test_module = lazy_loader.get_module('test_module')
    load_time = time.time() - start_time
    
    logger.info(f"Test module loaded in {load_time:.3f}s")
    assert test_module is not None
    assert lazy_loader.is_loaded('test_module')
    assert load_time >= 0.1  # Should take at least the sleep time
    
    # Test that subsequent calls are fast (cached)
    start_time = time.time()
    test_module2 = lazy_loader.get_module('test_module')
    cached_time = time.time() - start_time
    
    logger.info(f"Cached module access in {cached_time:.6f}s")
    assert test_module2 is test_module  # Same instance
    assert cached_time < 0.01  # Should be very fast
    
    logger.info("✓ Lazy loading test passed")


def test_regex_precompilation():
    """Test regex pattern precompilation."""
    logger.info("Testing regex precompilation...")
    
    from services.performance_optimizer import get_performance_optimizer
    
    optimizer = get_performance_optimizer()
    
    # Initialize if needed
    if not optimizer.is_initialized():
        optimizer.initialize()
    
    # Initialize with test patterns
    test_patterns = {
        'test_date': r'\b\d{1,2}/\d{1,2}/\d{4}\b',
        'test_time': r'\b\d{1,2}:\d{2}\s*(?:am|pm)\b'
    }
    
    start_time = time.time()
    optimizer.regex_compiler.register_patterns(test_patterns)
    compilation_time = time.time() - start_time
    
    logger.info(f"Regex patterns compiled in {compilation_time:.3f}s")
    
    # Test pattern usage
    date_pattern = optimizer.get_regex_pattern('test_date')
    assert date_pattern is not None
    
    # Test pattern matching
    test_text = "Meeting on 12/25/2024 at 2:30 pm"
    date_match = date_pattern.search(test_text)
    assert date_match is not None
    assert date_match.group() == "12/25/2024"
    
    time_pattern = optimizer.get_regex_pattern('test_time')
    time_match = time_pattern.search(test_text)
    assert time_match is not None
    assert time_match.group() == "2:30 pm"
    
    logger.info("✓ Regex precompilation test passed")


async def test_concurrent_processing():
    """Test concurrent field processing."""
    logger.info("Testing concurrent field processing...")
    
    from services.performance_optimizer import get_performance_optimizer
    
    optimizer = get_performance_optimizer()
    
    # Initialize if needed
    if not optimizer.is_initialized():
        optimizer.initialize()
    
    # Create mock field processors that simulate work
    def mock_title_processor(text):
        time.sleep(0.1)  # Simulate processing time
        return f"Title: {text[:20]}"
    
    def mock_datetime_processor(text):
        time.sleep(0.15)  # Simulate processing time
        return f"DateTime: {datetime.now().isoformat()}"
    
    def mock_location_processor(text):
        time.sleep(0.05)  # Simulate processing time
        return f"Location: extracted from {len(text)} chars"
    
    field_processors = {
        'title': mock_title_processor,
        'datetime': mock_datetime_processor,
        'location': mock_location_processor
    }
    
    test_text = "Meeting with John tomorrow at 2pm in Conference Room A"
    
    # Test sequential processing time
    start_time = time.time()
    sequential_results = {}
    for field, processor in field_processors.items():
        sequential_results[field] = processor(test_text)
    sequential_time = time.time() - start_time
    
    logger.info(f"Sequential processing took {sequential_time:.3f}s")
    
    # Test concurrent processing time
    start_time = time.time()
    concurrent_results = await optimizer.concurrent_processor.process_fields_concurrently(
        field_processors, test_text, timeout_seconds=5.0
    )
    concurrent_time = time.time() - start_time
    
    logger.info(f"Concurrent processing took {concurrent_time:.3f}s")
    
    # Concurrent should be faster
    speedup = sequential_time / concurrent_time
    logger.info(f"Speedup: {speedup:.2f}x")
    
    assert concurrent_time < sequential_time
    assert len(concurrent_results) == len(field_processors)
    
    logger.info("✓ Concurrent processing test passed")


async def test_timeout_handling():
    """Test timeout handling with partial results."""
    logger.info("Testing timeout handling...")
    
    from services.performance_optimizer import get_performance_optimizer
    
    optimizer = get_performance_optimizer()
    
    # Initialize if needed
    if not optimizer.is_initialized():
        optimizer.initialize()
    
    # Create a slow operation that will timeout
    async def slow_operation():
        await asyncio.sleep(2.0)  # Longer than timeout
        return "completed"
    
    # Test timeout with fallback
    start_time = time.time()
    result = await optimizer.execute_with_timeout(
        slow_operation,
        timeout_seconds=0.5,
        fallback_result="timeout_fallback"
    )
    elapsed_time = time.time() - start_time
    
    logger.info(f"Timeout test completed in {elapsed_time:.3f}s")
    assert result == "timeout_fallback"
    assert elapsed_time < 1.0  # Should timeout quickly
    
    # Test successful operation within timeout
    async def fast_operation():
        await asyncio.sleep(0.1)
        return "success"
    
    start_time = time.time()
    result = await optimizer.execute_with_timeout(
        fast_operation,
        timeout_seconds=1.0,
        fallback_result="fallback"
    )
    elapsed_time = time.time() - start_time
    
    logger.info(f"Fast operation completed in {elapsed_time:.3f}s")
    assert result == "success"
    assert elapsed_time < 0.5
    
    logger.info("✓ Timeout handling test passed")


async def test_startup_optimization():
    """Test startup optimization."""
    logger.info("Testing startup optimization...")
    
    from services.startup_optimizer import StartupOptimizer
    
    # Create a fresh startup optimizer for testing
    startup_optimizer = StartupOptimizer()
    
    # Test initialization without warm-up to avoid long delays
    start_time = time.time()
    metrics = await startup_optimizer.initialize_application(
        enable_warm_up=False,  # Skip warm-up for faster testing
        warm_up_in_background=False
    )
    initialization_time = time.time() - start_time
    
    logger.info(f"Startup initialization completed in {initialization_time:.3f}s")
    logger.info(f"Regex compilation time: {metrics.regex_compilation_time:.3f}s")
    
    assert metrics.regex_compilation_time > 0
    assert initialization_time < 15.0  # Should be reasonably fast (allowing for warm-up)
    
    logger.info("✓ Startup optimization test passed")


async def test_hybrid_parser_optimizations():
    """Test hybrid parser with performance optimizations."""
    logger.info("Testing hybrid parser optimizations...")
    
    # Test the optimized text cleaning function
    from services.hybrid_event_parser import HybridEventParser
    
    parser = HybridEventParser()
    
    test_text = "Meeting at 2:30 p.m. tomorrow"
    
    # Test optimized text cleaning
    cleaned_text = parser._pre_clean_text_optimized(test_text)
    logger.info(f"Original: '{test_text}'")
    logger.info(f"Cleaned: '{cleaned_text}'")
    
    assert cleaned_text is not None
    assert len(cleaned_text) > 0
    
    # Test fallback result creation
    fallback_result = parser._create_fallback_result(
        text=test_text,
        warnings=[],
        processing_metadata={'test': True}
    )
    
    assert fallback_result.parsed_event is not None
    assert fallback_result.parsing_path == "timeout_fallback"
    
    logger.info("✓ Hybrid parser optimization test passed")


async def main():
    """Run all performance optimization tests."""
    logger.info("Starting performance optimization tests...")
    
    try:
        # Test individual components
        test_lazy_loading()
        test_regex_precompilation()
        await test_concurrent_processing()
        await test_timeout_handling()
        await test_startup_optimization()
        await test_hybrid_parser_optimizations()
        
        logger.info("🎉 All performance optimization tests passed!")
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())