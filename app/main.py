"""
Entry point that matches Render's auto-detection pattern.
Render seems to be looking for app.main:app, so we provide it.
"""

import sys
import os

# Add the project root to the Python path so we can import from api
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.insert(0, project_root)

# Import the actual FastAPI app from our api package
from api.app.main import app

# Export the app so Render can find it at app.main:app
__all__ = ["app"]