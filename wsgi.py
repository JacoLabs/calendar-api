"""
WSGI entry point for Render deployment.
This file provides a simple import path that Render can auto-detect.
"""

from api.app.main import app

# Export the app for WSGI servers
application = app

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)