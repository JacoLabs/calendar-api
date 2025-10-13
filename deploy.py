#!/usr/bin/env python3
"""
Simple deployment script for the Calendar API.

This script provides a minimal FastAPI app that can be deployed without
all the advanced monitoring dependencies if needed.
"""

import os
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

try:
    # Try to import the full API with all features
    from api.app.main import app
    print("✅ Full API loaded with all features")
except ImportError as e:
    print(f"⚠️  Could not load full API ({e}), creating minimal version...")
    
    # Create a minimal FastAPI app as fallback
    from fastapi import FastAPI
    from fastapi.responses import JSONResponse
    import json
    from datetime import datetime
    
    app = FastAPI(
        title="Text-to-Calendar Event Parser API (Minimal)",
        description="Minimal version of the Calendar API for deployment",
        version="2.0.0-minimal"
    )
    
    @app.get("/")
    async def root():
        return {
            "name": "Text-to-Calendar Event Parser API",
            "version": "2.0.0-minimal",
            "status": "running",
            "note": "This is a minimal deployment version. Some features may be limited.",
            "endpoints": {
                "health": "/healthz",
                "parse": "/parse (POST)",
                "docs": "/docs"
            }
        }
    
    @app.get("/healthz")
    async def health_check():
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "version": "2.0.0-minimal",
            "services": {
                "api": "healthy",
                "parser": "available"
            }
        }
    
    @app.post("/parse")
    async def parse_text_minimal(request: dict):
        """Minimal parsing endpoint."""
        text = request.get("text", "")
        
        if not text:
            return JSONResponse(
                status_code=400,
                content={"error": "Text is required"}
            )
        
        # Very basic parsing (this would need to be enhanced)
        return {
            "title": "Event",
            "start_datetime": datetime.now().isoformat(),
            "end_datetime": datetime.now().isoformat(),
            "location": None,
            "description": text,
            "confidence_score": 0.5,
            "all_day": False,
            "timezone": "UTC",
            "parsing_metadata": {
                "version": "minimal",
                "note": "This is a minimal parser. Full parsing features require complete deployment."
            },
            "warnings": ["Using minimal parsing - results may be limited"]
        }

# Export the app for deployment
__all__ = ["app"]

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)