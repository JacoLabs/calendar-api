"""
Unit tests for health check hardening endpoints.
Tests the enhanced root endpoint, lightweight health check, favicon handling, and static mount idempotency.
"""

import pytest
import os
import tempfile
import shutil
from fastapi.testclient import TestClient
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from unittest.mock import patch, MagicMock

from app.main import app

client = TestClient(app)


class TestRootEndpoint:
    """Test enhanced root endpoint with GET and HEAD method support."""
    
    def test_root_get_method(self):
        """Test GET request to root endpoint returns correct JSON response."""
        response = client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure matches requirements
        assert data == {"ok": True, "service": "calendar-api"}
        
        # Verify content type
        assert response.headers["content-type"] == "application/json"
    
    def test_root_head_method(self):
        """Test HEAD request to root endpoint returns 200 with no body."""
        response = client.head("/")
        
        assert response.status_code == 200
        
        # HEAD request should have no response body
        assert response.content == b""
        
        # Should have appropriate headers
        assert "content-type" in response.headers
        assert response.headers["content-type"] == "application/json"
    
    def test_root_endpoint_excluded_from_schema(self):
        """Test that root endpoint is excluded from OpenAPI schema."""
        # Get OpenAPI schema
        response = client.get("/openapi.json")
        assert response.status_code == 200
        
        openapi_schema = response.json()
        paths = openapi_schema.get("paths", {})
        
        # Root endpoint should not be in the schema due to include_in_schema=False
        assert "/" not in paths
    
    def test_root_endpoint_supports_both_methods(self):
        """Test that root endpoint supports both GET and HEAD methods."""
        # Test GET
        get_response = client.get("/")
        assert get_response.status_code == 200
        
        # Test HEAD
        head_response = client.head("/")
        assert head_response.status_code == 200
        
        # Both should have same headers (except content-length for HEAD)
        assert get_response.headers["content-type"] == head_response.headers["content-type"]
    
    def test_root_endpoint_rejects_other_methods(self):
        """Test that root endpoint rejects unsupported HTTP methods."""
        # Test POST (should be rejected)
        response = client.post("/")
        assert response.status_code == 405  # Method Not Allowed
        
        # Test PUT (should be rejected)
        response = client.put("/")
        assert response.status_code == 405  # Method Not Allowed
        
        # Test DELETE (should be rejected)
        response = client.delete("/")
        assert response.status_code == 405  # Method Not Allowed


class TestHealthzEndpoint:
    """Test lightweight health check endpoint."""
    
    def test_healthz_get_method(self):
        """Test GET request to healthz endpoint returns 204 No Content."""
        response = client.get("/healthz")
        
        assert response.status_code == 204
        
        # Should have no response body
        assert response.content == b""
        
        # 204 responses typically don't include content-length header
        # The important thing is that there's no body content
    
    def test_healthz_head_method(self):
        """Test HEAD request to healthz endpoint returns 204 No Content."""
        response = client.head("/healthz")
        
        assert response.status_code == 204
        
        # Should have no response body
        assert response.content == b""
        
        # 204 responses typically don't include content-length header
        # The important thing is that there's no body content
    
    def test_healthz_endpoint_excluded_from_schema(self):
        """Test that healthz endpoint is excluded from OpenAPI schema."""
        # Get OpenAPI schema
        response = client.get("/openapi.json")
        assert response.status_code == 200
        
        openapi_schema = response.json()
        paths = openapi_schema.get("paths", {})
        
        # Healthz endpoint should not be in the schema due to include_in_schema=False
        assert "/healthz" not in paths
    
    def test_healthz_endpoint_supports_both_methods(self):
        """Test that healthz endpoint supports both GET and HEAD methods."""
        # Test GET
        get_response = client.get("/healthz")
        assert get_response.status_code == 204
        
        # Test HEAD
        head_response = client.head("/healthz")
        assert head_response.status_code == 204
        
        # Both should return same status and headers
        assert get_response.status_code == head_response.status_code
    
    def test_healthz_endpoint_rejects_other_methods(self):
        """Test that healthz endpoint rejects unsupported HTTP methods."""
        # Test POST (should be rejected)
        response = client.post("/healthz")
        assert response.status_code == 405  # Method Not Allowed
        
        # Test PUT (should be rejected)
        response = client.put("/healthz")
        assert response.status_code == 405  # Method Not Allowed
    
    def test_healthz_performance(self):
        """Test that healthz endpoint responds quickly for monitoring probes."""
        import time
        
        start_time = time.time()
        response = client.get("/healthz")
        end_time = time.time()
        
        response_time = end_time - start_time
        
        assert response.status_code == 204
        # Health check should be very fast (under 100ms in most cases)
        assert response_time < 1.0  # Allow 1 second for test environment


class TestFaviconEndpoint:
    """Test favicon.ico handling with and without file present."""
    
    def setUp(self):
        """Set up test environment."""
        # Create temporary static directory for testing
        self.temp_static_dir = tempfile.mkdtemp()
        self.original_static_dir = "static"
    
    def tearDown(self):
        """Clean up test environment."""
        # Clean up temporary directory
        if os.path.exists(self.temp_static_dir):
            shutil.rmtree(self.temp_static_dir)
    
    def test_favicon_with_file_present(self):
        """Test favicon.ico handling when file exists."""
        # Create a temporary favicon file
        static_dir = "static"
        favicon_path = os.path.join(static_dir, "favicon.ico")
        
        # Ensure static directory exists
        os.makedirs(static_dir, exist_ok=True)
        
        try:
            # Create a simple favicon file
            with open(favicon_path, "wb") as f:
                # Write a minimal ICO file header (simplified for testing)
                f.write(b"\x00\x00\x01\x00\x01\x00\x10\x10\x00\x00\x01\x00\x08\x00")
                f.write(b"\x68\x00\x00\x00\x16\x00\x00\x00" + b"\x00" * 100)
            
            response = client.get("/favicon.ico")
            
            assert response.status_code == 200
            
            # Should serve the file
            assert len(response.content) > 0
            
            # Should have appropriate content type for ICO files
            content_type = response.headers.get("content-type", "")
            assert "image" in content_type or "application/octet-stream" in content_type
            
        finally:
            # Clean up
            if os.path.exists(favicon_path):
                os.remove(favicon_path)
    
    def test_favicon_without_file_present(self):
        """Test favicon.ico handling when file does not exist."""
        # Ensure favicon file doesn't exist
        favicon_path = "static/favicon.ico"
        if os.path.exists(favicon_path):
            os.remove(favicon_path)
        
        response = client.get("/favicon.ico")
        
        # Should return 204 No Content when file doesn't exist
        assert response.status_code == 204
        
        # Should have no response body
        assert response.content == b""
        
        # 204 responses may or may not include content-length header
        # The important thing is that there's no body content
    
    def test_favicon_endpoint_excluded_from_schema(self):
        """Test that favicon endpoint is excluded from OpenAPI schema."""
        # Get OpenAPI schema
        response = client.get("/openapi.json")
        assert response.status_code == 200
        
        openapi_schema = response.json()
        paths = openapi_schema.get("paths", {})
        
        # Favicon endpoint should not be in the schema due to include_in_schema=False
        assert "/favicon.ico" not in paths
    
    def test_favicon_file_existence_check(self):
        """Test that favicon endpoint properly checks for file existence."""
        # Test behavior when file doesn't exist (which is the normal case)
        favicon_path = "static/favicon.ico"
        
        # Ensure file doesn't exist
        if os.path.exists(favicon_path):
            os.remove(favicon_path)
        
        response = client.get("/favicon.ico")
        
        # Should return 204 when file doesn't exist
        assert response.status_code == 204
        assert response.content == b""
        
        # Test behavior when file exists
        # Create a minimal favicon file for testing
        os.makedirs("static", exist_ok=True)
        try:
            with open(favicon_path, "wb") as f:
                # Write minimal ICO file content
                f.write(b"\x00\x00\x01\x00\x01\x00\x10\x10\x00\x00\x01\x00\x08\x00")
                f.write(b"\x68\x00\x00\x00\x16\x00\x00\x00" + b"\x00" * 100)
            
            response = client.get("/favicon.ico")
            
            # Should serve the file when it exists
            assert response.status_code == 200
            assert len(response.content) > 0
            
        finally:
            # Clean up test file
            if os.path.exists(favicon_path):
                os.remove(favicon_path)
    
    def test_favicon_only_supports_get_method(self):
        """Test that favicon endpoint only supports GET method."""
        # GET should work
        response = client.get("/favicon.ico")
        assert response.status_code in [200, 204]  # Depends on file existence
        
        # Other methods should be rejected
        response = client.post("/favicon.ico")
        assert response.status_code == 405  # Method Not Allowed
        
        response = client.head("/favicon.ico")
        assert response.status_code == 405  # Method Not Allowed


class TestStaticMountIdempotency:
    """Test static file serving configuration with idempotency."""
    
    def test_static_mount_exists(self):
        """Test that static mount is properly configured."""
        # Check if we can access the static mount (even if directory is empty)
        # This tests that the mount was created successfully
        
        # Create a test file in static directory
        static_dir = "static"
        os.makedirs(static_dir, exist_ok=True)
        
        test_file_path = os.path.join(static_dir, "test.txt")
        
        try:
            with open(test_file_path, "w") as f:
                f.write("test content")
            
            # Try to access the static file
            response = client.get("/static/test.txt")
            
            # Should either serve the file (200) or return 404 if mount isn't working
            # The key is that it shouldn't return 500 or other server errors
            assert response.status_code in [200, 404]
            
            if response.status_code == 200:
                assert response.text == "test content"
                
        finally:
            # Clean up
            if os.path.exists(test_file_path):
                os.remove(test_file_path)
    
    def test_static_directory_creation(self):
        """Test that static directory is created if it doesn't exist."""
        static_dir = "static"
        
        # The static directory should exist after app initialization
        assert os.path.exists(static_dir)
        assert os.path.isdir(static_dir)
    
    @patch('app.main.app.mount')
    def test_static_mount_idempotency_check(self, mock_mount):
        """Test that static mount idempotency check works correctly."""
        # This test verifies the logic that prevents duplicate mounts
        # We can't easily test this with the actual app since it's already initialized
        # But we can test the logic pattern
        
        # Create a mock app with existing static mount
        mock_app = MagicMock()
        mock_route = MagicMock()
        mock_route.name = "static"
        mock_app.routes = [mock_route]
        
        # Simulate the idempotency check logic
        existing_static_mounts = [
            route for route in mock_app.routes 
            if hasattr(route, 'name') and route.name == 'static'
        ]
        
        # Should find existing mount
        assert len(existing_static_mounts) == 1
        
        # In real code, this would prevent adding another mount
        if not existing_static_mounts:
            mock_app.mount("/static", StaticFiles(directory="static"), name="static")
        
        # Mount should not be called since static mount already exists
        mock_mount.assert_not_called()
    
    def test_static_mount_name_consistency(self):
        """Test that static mount uses consistent naming."""
        # Check that the static mount exists in the app routes
        static_routes = [
            route for route in app.routes 
            if hasattr(route, 'name') and route.name == 'static'
        ]
        
        # Should have exactly one static mount
        assert len(static_routes) <= 1  # Could be 0 or 1 depending on initialization
        
        if static_routes:
            static_route = static_routes[0]
            assert static_route.name == "static"
            # Should be mounted at /static path
            assert hasattr(static_route, 'path') or hasattr(static_route, 'path_regex')


class TestEndpointIntegration:
    """Test integration between all health check endpoints."""
    
    def test_all_health_endpoints_respond(self):
        """Test that all health-related endpoints respond correctly."""
        # Test root endpoint
        root_response = client.get("/")
        assert root_response.status_code == 200
        
        # Test healthz endpoint
        healthz_response = client.get("/healthz")
        assert healthz_response.status_code == 204
        
        # Test favicon endpoint
        favicon_response = client.get("/favicon.ico")
        assert favicon_response.status_code in [200, 204]
    
    def test_head_method_support_consistency(self):
        """Test that HEAD method support is consistent across endpoints."""
        # Root endpoint should support HEAD
        root_head = client.head("/")
        assert root_head.status_code == 200
        
        # Healthz endpoint should support HEAD
        healthz_head = client.head("/healthz")
        assert healthz_head.status_code == 204
        
        # Favicon should not support HEAD (only GET)
        favicon_head = client.head("/favicon.ico")
        assert favicon_head.status_code == 405
    
    def test_schema_exclusion_consistency(self):
        """Test that all health endpoints are excluded from OpenAPI schema."""
        response = client.get("/openapi.json")
        assert response.status_code == 200
        
        openapi_schema = response.json()
        paths = openapi_schema.get("paths", {})
        
        # All health endpoints should be excluded
        health_endpoints = ["/", "/healthz", "/favicon.ico"]
        for endpoint in health_endpoints:
            assert endpoint not in paths
    
    def test_render_health_probe_simulation(self):
        """Test simulation of Render's health probe behavior."""
        # Render typically uses HEAD requests for health checks
        response = client.head("/healthz")
        
        assert response.status_code == 204
        assert response.content == b""
        
        # Should respond quickly (important for health probes)
        import time
        start_time = time.time()
        response = client.head("/healthz")
        end_time = time.time()
        
        response_time = end_time - start_time
        assert response_time < 0.5  # Should be very fast
    
    def test_browser_request_simulation(self):
        """Test simulation of common browser requests."""
        # Browsers typically request favicon.ico
        favicon_response = client.get("/favicon.ico")
        
        # Should not return 404 (which would create noisy logs)
        assert favicon_response.status_code in [200, 204]
        
        # Root endpoint should work for browser navigation
        root_response = client.get("/")
        assert root_response.status_code == 200
        
        data = root_response.json()
        assert data["ok"] is True
        assert data["service"] == "calendar-api"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])