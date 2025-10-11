"""
Test OpenAPI documentation generation.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from fastapi.testclient import TestClient
from app.main import app
import json

def test_openapi_schema():
    """Test OpenAPI schema generation."""
    client = TestClient(app)
    
    # Get OpenAPI schema
    response = client.get("/openapi.json")
    
    if response.status_code == 200:
        schema = response.json()
        
        print("✓ OpenAPI schema generated successfully")
        print(f"  Title: {schema.get('info', {}).get('title', 'N/A')}")
        print(f"  Version: {schema.get('info', {}).get('version', 'N/A')}")
        print(f"  Description length: {len(schema.get('info', {}).get('description', ''))}")
        
        # Check endpoints
        paths = schema.get('paths', {})
        print(f"  Endpoints: {len(paths)}")
        
        for path, methods in paths.items():
            for method, details in methods.items():
                print(f"    {method.upper()} {path}: {details.get('summary', 'No summary')}")
        
        # Check if async processing is documented
        parse_endpoint = paths.get('/parse', {}).get('post', {})
        description = parse_endpoint.get('description', '')
        
        if 'async' in description.lower() or 'concurrent' in description.lower():
            print("✓ Async processing documented in /parse endpoint")
        else:
            print("⚠ Async processing not clearly documented")
        
        # Check query parameters
        parameters = parse_endpoint.get('parameters', [])
        param_names = [p.get('name') for p in parameters]
        
        if 'mode' in param_names:
            print("✓ 'mode' query parameter documented")
        if 'fields' in param_names:
            print("✓ 'fields' query parameter documented")
        
        # Save schema for inspection
        with open('api/openapi_schema.json', 'w') as f:
            json.dump(schema, f, indent=2)
        print("✓ Schema saved to openapi_schema.json")
        
    else:
        print(f"✗ Failed to get OpenAPI schema: {response.status_code}")
        print(response.text)

if __name__ == "__main__":
    test_openapi_schema()