#!/usr/bin/env python3
"""
Fast startup script for browser extension API server.
Tries lightweight server first, falls back to full server if needed.
"""

import subprocess
import sys
import os
import time
import requests

def check_server_health(port=5000, timeout=2):
    """Check if server is running and healthy."""
    try:
        response = requests.get(f'http://localhost:{port}/health', timeout=timeout)
        return response.status_code == 200
    except:
        return False

def start_lightweight_server():
    """Start the lightweight server."""
    print("🚀 Starting lightweight server for fast browser extension support...")
    
    # Get the directory of this script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    server_path = os.path.join(script_dir, 'lightweight_server.py')
    
    try:
        # Start the lightweight server
        process = subprocess.Popen([sys.executable, server_path])
        
        # Wait a moment for startup
        time.sleep(2)
        
        # Check if it's running
        if check_server_health():
            print("✅ Lightweight server started successfully!")
            print("📡 Browser extension ready at: http://localhost:5000")
            return process
        else:
            print("❌ Lightweight server failed to start")
            process.terminate()
            return None
            
    except Exception as e:
        print(f"❌ Error starting lightweight server: {e}")
        return None

def start_full_server():
    """Start the full-featured server as fallback."""
    print("🔄 Starting full-featured server...")
    
    # Get the parent directory (project root)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    server_path = os.path.join(project_root, 'api_server.py')
    
    try:
        # Start the full server
        process = subprocess.Popen([sys.executable, server_path], cwd=project_root)
        
        # Wait longer for the full server to start
        time.sleep(5)
        
        # Check if it's running
        if check_server_health():
            print("✅ Full server started successfully!")
            print("📡 Browser extension ready at: http://localhost:5000")
            return process
        else:
            print("❌ Full server failed to start")
            process.terminate()
            return None
            
    except Exception as e:
        print(f"❌ Error starting full server: {e}")
        return None

def main():
    """Main startup logic."""
    print("🎯 Fast Browser Extension Server Startup")
    print("=" * 50)
    
    # Check if a server is already running
    if check_server_health():
        print("✅ Server already running at http://localhost:5000")
        return
    
    # Try lightweight server first
    process = start_lightweight_server()
    
    if not process:
        print("\n🔄 Lightweight server failed, trying full server...")
        process = start_full_server()
        
        if not process:
            print("\n❌ Both servers failed to start!")
            print("💡 Try running manually:")
            print("   python browser-extension/lightweight_server.py")
            print("   or")
            print("   python api_server.py")
            sys.exit(1)
    
    print("\n🎉 Server is ready for browser extension!")
    print("📋 Test with: curl http://localhost:5000/health")
    
    try:
        # Keep the script running
        process.wait()
    except KeyboardInterrupt:
        print("\n🛑 Shutting down server...")
        process.terminate()
        process.wait()

if __name__ == '__main__':
    main()