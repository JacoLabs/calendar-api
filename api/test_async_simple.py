"""
Simple test for async API functionality.
"""

import asyncio
import httpx
from datetime import datetime, timezone

async def test_async_api():
    """Test basic async API functionality."""
    
    # Start the server in the background (we'll test with TestClient instead)
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
    
    from fastapi.testclient import TestClient
    from app.main import app
    
    client = TestClient(app)
    
    print("Testing async parse endpoint...")
    
    # Test basic parsing
    request_data = {
        "text": "Meeting tomorrow at 2pm",
        "timezone": "UTC",
        "locale": "en_US",
        "now": datetime(2024, 3, 15, 15, 0, 0, tzinfo=timezone.utc).isoformat()
    }
    
    response = client.post("/parse", json=request_data)
    print(f"Response status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"✓ Parse successful - Confidence: {data.get('confidence_score', 'N/A')}")
        print(f"  Title: {data.get('title', 'N/A')}")
        print(f"  Start: {data.get('start_datetime', 'N/A')}")
    else:
        print(f"✗ Parse failed: {response.text}")
    
    # Test health endpoint
    print("\nTesting health endpoint...")
    health_response = client.get("/healthz")
    print(f"Health status: {health_response.status_code}")
    
    if health_response.status_code == 200:
        health_data = health_response.json()
        print(f"✓ Health check successful - Status: {health_data.get('status', 'N/A')}")
    else:
        print(f"✗ Health check failed: {health_response.text}")
    
    # Test audit mode
    print("\nTesting audit mode...")
    audit_response = client.post("/parse?mode=audit", json=request_data)
    print(f"Audit response status: {audit_response.status_code}")
    
    if audit_response.status_code == 200:
        audit_data = audit_response.json()
        metadata = audit_data.get('parsing_metadata', {})
        print(f"✓ Audit mode successful")
        print(f"  Routing decisions: {metadata.get('routing_decisions', 'N/A')}")
        print(f"  Confidence breakdown: {metadata.get('confidence_breakdown', 'N/A')}")
    else:
        print(f"✗ Audit mode failed: {audit_response.text}")
    
    # Test partial parsing
    print("\nTesting partial parsing...")
    partial_response = client.post("/parse?fields=title,start", json=request_data)
    print(f"Partial parsing status: {partial_response.status_code}")
    
    if partial_response.status_code == 200:
        partial_data = partial_response.json()
        metadata = partial_data.get('parsing_metadata', {})
        print(f"✓ Partial parsing successful")
        print(f"  Partial parsing: {metadata.get('partial_parsing', 'N/A')}")
        print(f"  Requested fields: {metadata.get('requested_fields', 'N/A')}")
    else:
        print(f"✗ Partial parsing failed: {partial_response.text}")
    
    print("\nAsync API tests completed!")

if __name__ == "__main__":
    asyncio.run(test_async_api())