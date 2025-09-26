"""
Simple entry point for Render deployment.
This file provides the exact import path that Render expects.
"""

# Import the FastAPI app from our api package
from api.app.main import app

# This allows Render to find the app with: uvicorn app:app
# The app variable is now available at module level

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)