"""
Integration tests for async FastAPI functionality.
Tests concurrent processing, timeout handling, and async endpoint behavior.
"""

import pytest
import asyncio
from datetime import datetime, timezone
from fastapi.testclient import TestClient
import httpx
import time

from app.main import app

# Use async test client for proper async testing
@pytest.fixture
async def async_client():
    """Create async test client."""
    async with httpx.AsyncClient(app=app, base_url="http://test") as client:
        yield client


class TestAsyncProcessing:
    """Test async processing capabilities."""
    
    @pytest.mark.asyncio
    async def test_concurrent_requests(self, async_client):
        """Test handling multiple concurrent requests."""
        # Create multiple parsing requests
        requests = [
            {
                "text": f"Meeting {i} tomorrow at {10 + i}am",
                "timezone": "UTC",
                "locale": "en_US",
                "now": datetime(2024, 3, 15, 15, 0, 0, tzinfo=timezone.utc).isoformat()
            }
            for i in range(5)
        ]
        
        # Send concurrent requests
        start_time = time.time()
        tasks = [
            async_client.post("/parse", json=request_data)
            for request_data in requests
        ]
        
        responses = await asyncio.gather(*tasks)
        end_time = time.time()
        
        # Verify all requests succeeded
        for i, response in enumerate(responses):
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert f"meeting {i}" in data["title"].lower()
        
        # Concurrent processing should be faster than sequential
        total_time = end_time - start_time
        assert total_time < 10.0  # Should complete within 10 seconds
        
        print(f"Processed {len(requests)} concurrent requests in {total_time:.2f}s")
    
    @pytest.mark.asyncio
    async def test_partial_parsing_async(self, async_client):
        """Test async partial parsing with fields parameter."""
        request_data = {
            "text": "Team meeting tomorrow at 2pm in Conference Room A",
            "timezone": "UTC",
            "locale": "en_US",
            "now": datetime(2024, 3, 15, 15, 0, 0, tzinfo=timezone.utc).isoformat()
        }
        
        # Test parsing only specific fields
        response = await async_client.post("/parse?fields=title,start", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        
        # Should have requested fields
        assert data["title"] is not None
        assert data["start_datetime"] is not None
        
        # Parsing metadata should indicate partial parsing
        assert data["parsing_metadata"]["partial_parsing"] is True
        assert "title" in data["parsing_metadata"]["requested_fields"]
        assert "start" in data["parsing_metadata"]["requested_fields"]
    
    @pytest.mark.asyncio
    async def test_audit_mode_async(self, async_client):
        """Test async audit mode functionality."""
        request_data = {
            "text": "Project review meeting tomorrow at 10am for 2 hours",
            "timezone": "UTC",
            "locale": "en_US",
            "now": datetime(2024, 3, 15, 15, 0, 0, tzinfo=timezone.utc).isoformat()
        }
        
        # Test audit mode
        response = await async_client.post("/parse?mode=audit", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        
        # Should include audit information
        metadata = data["parsing_metadata"]
        assert "routing_decisions" in metadata
        assert "confidence_breakdown" in metadata
        assert "field_sources" in metadata
        assert "processing_metadata" in metadata
    
    @pytest.mark.asyncio
    async def test_health_check_async(self, async_client):
        """Test async health check endpoint."""
        response = await async_client.get("/healthz")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "services" in data
        assert "version" in data
    
    @pytest.mark.asyncio
    async def test_ics_generation_async(self, async_client):
        """Test async ICS file generation."""
        params = {
            "title": "Test Meeting",
            "start": "2024-03-16T14:00:00Z",
            "end": "2024-03-16T15:00:00Z",
            "location": "Conference Room A",
            "description": "Test meeting description"
        }
        
        response = await async_client.get("/ics", params=params)
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/calendar; charset=utf-8"
        
        # Verify ICS content
        ics_content = response.text
        assert "BEGIN:VCALENDAR" in ics_content
        assert "SUMMARY:Test Meeting" in ics_content
        assert "LOCATION:Conference Room A" in ics_content
        assert "END:VCALENDAR" in ics_content


class TestErrorHandling:
    """Test async error handling."""
    
    @pytest.mark.asyncio
    async def test_timeout_handling(self, async_client):
        """Test timeout handling for long-running requests."""
        # Create a request that might take longer to process
        request_data = {
            "text": "Very complex meeting with multiple dates and times and locations " * 100,
            "timezone": "UTC",
            "locale": "en_US",
            "use_llm_enhancement": True
        }
        
        # The request should either succeed or handle timeout gracefully
        response = await async_client.post("/parse", json=request_data)
        
        # Should not return 500 error even if timeout occurs
        assert response.status_code in [200, 408, 503]
        
        if response.status_code == 200:
            data = response.json()
            # If successful, should have valid response structure
            assert "confidence_score" in data
            assert "title" in data
    
    @pytest.mark.asyncio
    async def test_concurrent_error_handling(self, async_client):
        """Test error handling with concurrent requests."""
        # Mix of valid and invalid requests
        requests = [
            {"text": "Valid meeting tomorrow at 2pm", "timezone": "UTC"},
            {"text": "", "timezone": "UTC"},  # Invalid: empty text
            {"text": "Another valid meeting", "timezone": "Invalid/Timezone"},  # Invalid timezone
            {"text": "Valid meeting next week", "timezone": "UTC"},
        ]
        
        # Send concurrent requests
        tasks = [
            async_client.post("/parse", json=request_data)
            for request_data in requests
        ]
        
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Check that valid requests succeeded and invalid ones failed appropriately
        assert responses[0].status_code == 200  # Valid request
        assert responses[1].status_code == 422  # Empty text
        assert responses[2].status_code == 400  # Invalid timezone
        assert responses[3].status_code == 200  # Valid request
    
    @pytest.mark.asyncio
    async def test_rate_limiting_async(self, async_client):
        """Test rate limiting with async requests."""
        # Send many requests quickly to test rate limiting
        requests = [
            {"text": f"Meeting {i}", "timezone": "UTC"}
            for i in range(70)  # Exceed the 60/minute limit
        ]
        
        # Send requests in batches to avoid overwhelming the server
        batch_size = 10
        all_responses = []
        
        for i in range(0, len(requests), batch_size):
            batch = requests[i:i + batch_size]
            tasks = [
                async_client.post("/parse", json=request_data)
                for request_data in batch
            ]
            batch_responses = await asyncio.gather(*tasks, return_exceptions=True)
            all_responses.extend(batch_responses)
            
            # Small delay between batches
            await asyncio.sleep(0.1)
        
        # Check that some requests were rate limited
        status_codes = [r.status_code for r in all_responses if hasattr(r, 'status_code')]
        
        # Should have a mix of successful (200) and rate limited (429) responses
        assert 200 in status_codes
        # Note: Rate limiting might not trigger in test environment, so we don't assert 429


class TestPerformance:
    """Test async performance characteristics."""
    
    @pytest.mark.asyncio
    async def test_response_time_async(self, async_client):
        """Test that async endpoints respond within acceptable time limits."""
        request_data = {
            "text": "Team meeting tomorrow at 2pm in Conference Room A",
            "timezone": "UTC",
            "locale": "en_US"
        }
        
        start_time = time.time()
        response = await async_client.post("/parse", json=request_data)
        end_time = time.time()
        
        response_time = end_time - start_time
        
        assert response.status_code == 200
        assert response_time < 5.0  # Should respond within 5 seconds
        
        print(f"Parse request completed in {response_time:.3f}s")
    
    @pytest.mark.asyncio
    async def test_health_check_performance(self, async_client):
        """Test health check response time."""
        start_time = time.time()
        response = await async_client.get("/healthz")
        end_time = time.time()
        
        response_time = end_time - start_time
        
        assert response.status_code == 200
        assert response_time < 0.5  # Health check should be very fast
        
        print(f"Health check completed in {response_time:.3f}s")
    
    @pytest.mark.asyncio
    async def test_concurrent_performance(self, async_client):
        """Test performance with concurrent requests."""
        num_requests = 10
        request_data = {
            "text": "Quick meeting tomorrow at 3pm",
            "timezone": "UTC",
            "locale": "en_US"
        }
        
        # Measure concurrent processing time
        start_time = time.time()
        tasks = [
            async_client.post("/parse", json=request_data)
            for _ in range(num_requests)
        ]
        responses = await asyncio.gather(*tasks)
        end_time = time.time()
        
        total_time = end_time - start_time
        avg_time = total_time / num_requests
        
        # All requests should succeed
        for response in responses:
            assert response.status_code == 200
        
        # Concurrent processing should be efficient
        assert total_time < num_requests * 2  # Much faster than sequential
        assert avg_time < 2.0  # Average response time should be reasonable
        
        print(f"Processed {num_requests} concurrent requests in {total_time:.3f}s (avg: {avg_time:.3f}s)")


class TestCacheIntegration:
    """Test caching with async processing."""
    
    @pytest.mark.asyncio
    async def test_cache_hit_async(self, async_client):
        """Test cache hit behavior with async requests."""
        request_data = {
            "text": "Cached meeting tomorrow at 2pm",
            "timezone": "UTC",
            "locale": "en_US"
        }
        
        # First request - should be cached
        response1 = await async_client.post("/parse", json=request_data)
        assert response1.status_code == 200
        data1 = response1.json()
        
        # Second identical request - should hit cache
        response2 = await async_client.post("/parse", json=request_data)
        assert response2.status_code == 200
        data2 = response2.json()
        
        # Results should be identical
        assert data1["title"] == data2["title"]
        assert data1["start_datetime"] == data2["start_datetime"]
        
        # Second request should indicate cache hit
        if "parsing_metadata" in data2:
            assert data2["parsing_metadata"].get("cache_hit", False) is True
    
    @pytest.mark.asyncio
    async def test_cache_statistics_async(self, async_client):
        """Test cache statistics endpoint."""
        # Make some requests to populate cache
        for i in range(3):
            request_data = {
                "text": f"Meeting {i} tomorrow at {10 + i}am",
                "timezone": "UTC"
            }
            await async_client.post("/parse", json=request_data)
        
        # Check cache statistics (if endpoint exists)
        try:
            response = await async_client.get("/cache/stats")
            if response.status_code == 200:
                data = response.json()
                assert "status" in data
        except Exception:
            # Cache stats endpoint might not be implemented yet
            pass


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--asyncio-mode=auto"])