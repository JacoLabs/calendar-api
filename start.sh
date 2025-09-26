#!/bin/bash
# Render startup script for text-to-calendar API

echo "Starting text-to-calendar API..."
echo "Python version: $(python --version)"
echo "Current directory: $(pwd)"
echo "Files in directory: $(ls -la)"

# Start the FastAPI application
exec uvicorn api.app.main:app --host 0.0.0.0 --port ${PORT:-8000}