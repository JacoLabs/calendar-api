"""
Enhanced server startup with uvloop and async optimizations.
"""

import asyncio
import logging
import sys
import os
from typing import Optional

import uvicorn

try:
    import uvloop
    UVLOOP_AVAILABLE = True
except ImportError:
    UVLOOP_AVAILABLE = False

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def setup_uvloop():
    """Setup uvloop for better async performance."""
    if not UVLOOP_AVAILABLE:
        logger.info("uvloop not available, using default event loop")
        return
        
    try:
        # Only use uvloop on Unix systems
        if sys.platform != 'win32':
            asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
            logger.info("uvloop enabled for enhanced async performance")
        else:
            logger.info("uvloop not available on Windows, using default event loop")
    except Exception as e:
        logger.warning(f"Failed to setup uvloop: {e}, using default event loop")


def create_server_config(
    host: str = "0.0.0.0",
    port: int = 8000,
    workers: int = 1,
    reload: bool = False,
    log_level: str = "info"
) -> dict:
    """Create uvicorn server configuration with async optimizations."""
    
    config = {
        "app": "app.main:app",
        "host": host,
        "port": port,
        "log_level": log_level,
        "access_log": True,
        "use_colors": True,
        "server_header": False,  # Don't expose server info
        "date_header": False,    # Don't add date header
        "reload": reload,
        "workers": workers if not reload else 1,  # Single worker for reload mode
    }
    
    # Add uvloop if available (Unix only)
    if UVLOOP_AVAILABLE and sys.platform != 'win32':
        config["loop"] = "uvloop"
        logger.info("Configured uvicorn to use uvloop")
    else:
        logger.info("uvloop not available, using default loop")
    
    return config


async def startup_tasks():
    """Perform startup tasks asynchronously."""
    logger.info("Running async startup tasks...")
    
    try:
        # Warm up the event parser
        from app.main import event_parser
        logger.info("Event parser initialized")
        
        # Initialize cache manager
        from app.cache_manager import cache_manager
        logger.info("Cache manager initialized")
        
        # Precompile regex patterns (if available)
        try:
            from services.regex_date_extractor import RegexDateExtractor
            extractor = RegexDateExtractor()
            logger.info("Regex patterns precompiled")
        except ImportError:
            logger.info("Regex extractor not available for precompilation")
        
        logger.info("Startup tasks completed successfully")
        
    except Exception as e:
        logger.error(f"Error during startup tasks: {e}")


def run_server(
    host: Optional[str] = None,
    port: Optional[int] = None,
    workers: Optional[int] = None,
    reload: bool = False,
    log_level: str = "info"
):
    """Run the FastAPI server with uvloop and async optimizations."""
    
    # Setup uvloop for better performance
    setup_uvloop()
    
    # Get configuration from environment or defaults
    host = host or os.getenv("HOST", "0.0.0.0")
    port = port or int(os.getenv("PORT", "8000"))
    workers = workers or int(os.getenv("WORKERS", "1"))
    log_level = os.getenv("LOG_LEVEL", log_level).lower()
    
    # Create server configuration
    config = create_server_config(
        host=host,
        port=port,
        workers=workers,
        reload=reload,
        log_level=log_level
    )
    
    logger.info(f"Starting FastAPI server with async processing")
    logger.info(f"Host: {host}, Port: {port}, Workers: {workers}")
    logger.info(f"Reload: {reload}, Log Level: {log_level}")
    
    # Run the server
    uvicorn.run(**config)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Run FastAPI server with async optimizations")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind to")
    parser.add_argument("--workers", type=int, default=1, help="Number of worker processes")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload for development")
    parser.add_argument("--log-level", default="info", help="Log level")
    
    args = parser.parse_args()
    
    run_server(
        host=args.host,
        port=args.port,
        workers=args.workers,
        reload=args.reload,
        log_level=args.log_level
    )