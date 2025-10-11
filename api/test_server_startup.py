"""
Test script to verify async server startup and basic functionality.
"""

import asyncio
import sys
import os

# Add the parent directory to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

async def test_server_startup():
    """Test that the server can start up with async processing."""
    try:
        # Import the server module
        from api.app.server import setup_uvloop, create_server_config
        
        print("Testing uvloop setup...")
        setup_uvloop()
        print("✓ uvloop setup completed")
        
        print("Testing server configuration...")
        config = create_server_config(
            host="127.0.0.1",
            port=8001,
            workers=1,
            reload=False,
            log_level="info"
        )
        print(f"✓ Server config created: {config}")
        
        # Test async parsing functions
        print("Testing async parsing functions...")
        from api.app.main import _parse_text_async
        
        # Simple test
        result = await _parse_text_async(
            text="Meeting tomorrow at 2pm",
            use_llm_enhancement=False,
            requested_fields=None
        )
        print(f"✓ Async parsing test completed with confidence: {result.confidence_score}")
        
        print("All async server tests passed!")
        return True
        
    except Exception as e:
        print(f"✗ Server startup test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_server_startup())
    sys.exit(0 if success else 1)