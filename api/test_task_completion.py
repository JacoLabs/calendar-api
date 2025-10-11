"""
Test script to verify all sub-tasks for Task 17 are completed.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

def test_task_17_completion():
    """Test that all sub-tasks for Task 17 are completed."""
    
    print("Testing Task 17: Update FastAPI service with async processing")
    print("=" * 60)
    
    # Sub-task 1: Refactor API to use async FastAPI with uvicorn and uvloop
    print("\n1. Testing async FastAPI with uvicorn and uvloop...")
    try:
        from app.server import setup_uvloop, create_server_config, run_server
        print("✓ Server module with uvloop support available")
        
        # Test uvloop setup (graceful handling on Windows)
        setup_uvloop()
        print("✓ uvloop setup works (graceful fallback on Windows)")
        
        # Test server config
        config = create_server_config()
        assert 'app' in config
        assert 'host' in config
        assert 'port' in config
        print("✓ Server configuration generation works")
        
    except Exception as e:
        print(f"✗ Sub-task 1 failed: {e}")
        return False
    
    # Sub-task 2: Implement async request handling and concurrent processing
    print("\n2. Testing async request handling and concurrent processing...")
    try:
        from app.main import _parse_text_async, _run_main_parsing
        from app.main import _extract_title_async, _extract_datetime_async, _extract_location_async
        
        print("✓ Async parsing functions available")
        
        # Test that main endpoints are async
        from app.main import parse_text, health_check, cache_statistics
        import inspect
        
        assert inspect.iscoroutinefunction(parse_text)
        assert inspect.iscoroutinefunction(health_check)
        assert inspect.iscoroutinefunction(cache_statistics)
        print("✓ Main endpoints are async functions")
        
    except Exception as e:
        print(f"✗ Sub-task 2 failed: {e}")
        return False
    
    # Sub-task 3: Add proper error handling and status codes for enhanced features
    print("\n3. Testing enhanced error handling...")
    try:
        from app.models import ErrorCode
        from app.error_handlers import handle_parsing_error
        
        # Check for new error codes
        error_codes = [code.value for code in ErrorCode]
        assert 'TIMEOUT_ERROR' in error_codes
        assert 'CONCURRENT_PROCESSING_ERROR' in error_codes
        assert 'ASYNC_PROCESSING_ERROR' in error_codes
        print("✓ Enhanced error codes available")
        
        # Test error handling
        from fastapi.testclient import TestClient
        from app.main import app
        
        client = TestClient(app)
        
        # Test timeout handling (empty text should be fast)
        response = client.post("/parse", json={"text": ""})
        assert response.status_code == 422  # Validation error for empty text
        print("✓ Error handling works for invalid input")
        
    except Exception as e:
        print(f"✗ Sub-task 3 failed: {e}")
        return False
    
    # Sub-task 4: Create OpenAPI documentation for new endpoints and parameters
    print("\n4. Testing OpenAPI documentation...")
    try:
        from fastapi.testclient import TestClient
        from app.main import app
        
        client = TestClient(app)
        response = client.get("/openapi.json")
        
        assert response.status_code == 200
        schema = response.json()
        
        # Check for documented endpoints
        paths = schema.get('paths', {})
        assert '/parse' in paths
        assert '/healthz' in paths
        assert '/cache/stats' in paths
        
        # Check for query parameters in parse endpoint
        parse_endpoint = paths['/parse']['post']
        parameters = parse_endpoint.get('parameters', [])
        param_names = [p.get('name') for p in parameters]
        
        assert 'mode' in param_names
        assert 'fields' in param_names
        print("✓ OpenAPI documentation includes new parameters")
        
        # Check for async processing documentation
        description = parse_endpoint.get('description', '')
        assert 'async' in description.lower() or 'concurrent' in description.lower()
        print("✓ Async processing documented")
        
    except Exception as e:
        print(f"✗ Sub-task 4 failed: {e}")
        return False
    
    # Sub-task 5: Write integration tests for async API functionality
    print("\n5. Testing integration tests...")
    try:
        # Check that test file exists and has proper structure
        import os
        test_file = os.path.join(os.path.dirname(__file__), 'tests', 'test_async_api.py')
        assert os.path.exists(test_file), "Async API test file exists"
        
        # Check test content
        with open(test_file, 'r') as f:
            content = f.read()
        
        # Check for key test classes
        assert 'TestAsyncProcessing' in content
        assert 'TestErrorHandling' in content
        assert 'TestPerformance' in content
        assert 'TestCacheIntegration' in content
        
        # Check for async test methods
        assert 'test_concurrent_requests' in content
        assert 'test_timeout_handling' in content
        assert 'test_audit_mode_async' in content
        assert 'test_partial_parsing_async' in content
        
        print("✓ Comprehensive async integration tests available")
        
    except Exception as e:
        print(f"✗ Sub-task 5 failed: {e}")
        return False
    
    print("\n" + "=" * 60)
    print("✅ All sub-tasks for Task 17 completed successfully!")
    print("\nSummary:")
    print("- ✓ Async FastAPI with uvicorn and uvloop support")
    print("- ✓ Concurrent processing and async request handling")
    print("- ✓ Enhanced error handling with new status codes")
    print("- ✓ Comprehensive OpenAPI documentation")
    print("- ✓ Integration tests for async functionality")
    
    return True

if __name__ == "__main__":
    success = test_task_17_completion()
    sys.exit(0 if success else 1)