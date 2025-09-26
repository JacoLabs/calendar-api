"""
Entry point that matches Render's auto-detection pattern.
Render seems to be looking for app.main:app, so we provide it.
"""

# Import the actual FastAPI app from our api package
from api.app.main import app

# Export the app so Render can find it at app.main:app
__all__ = ["app"]