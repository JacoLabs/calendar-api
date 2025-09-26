"""
Main entry point for Render auto-detection.
This file ensures Render can find our FastAPI app regardless of configuration.
"""

# Import the actual FastAPI app from the correct location
from api.app.main import app

# This allows Render's auto-detection to find: uvicorn main:app
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)