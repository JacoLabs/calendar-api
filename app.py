"""
Entry point for Render deployment.
This file imports the FastAPI app from the api package.
"""

from api.app.main import app

# This allows Render to find the app with: uvicorn app:app
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)