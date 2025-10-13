#!/usr/bin/env python3
"""
Setup script for configuring OpenAI API key on Render.
This script provides instructions and validation for OpenAI integration.
"""

import os
import sys
import requests
from typing import Optional

def check_openai_key_format(api_key: str) -> bool:
    """Check if API key has the correct format."""
    if not api_key:
        return False
    
    # OpenAI API keys typically start with 'sk-' and are 51 characters long
    if api_key.startswith('sk-') and len(api_key) >= 40:
        return True
    
    return False

def test_openai_connection(api_key: str) -> bool:
    """Test if the OpenAI API key works."""
    try:
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
        
        # Test with a simple models list request
        response = requests.get(
            'https://api.openai.com/v1/models',
            headers=headers,
            timeout=10
        )
        
        return response.status_code == 200
        
    except Exception as e:
        print(f"Connection test failed: {e}")
        return False

def main():
    """Main setup function."""
    print("🔧 OpenAI API Key Setup for Render Deployment")
    print("=" * 50)
    
    # Check if API key is already configured
    existing_key = os.getenv('OPENAI_API_KEY')
    if existing_key:
        print(f"✅ OpenAI API key found in environment")
        
        if check_openai_key_format(existing_key):
            print("✅ API key format looks correct")
            
            print("🔍 Testing API key connection...")
            if test_openai_connection(existing_key):
                print("✅ API key works correctly!")
                print("\n🎉 Your OpenAI integration is ready!")
                return 0
            else:
                print("❌ API key test failed - key may be invalid or expired")
        else:
            print("⚠️ API key format looks incorrect")
    else:
        print("❌ No OpenAI API key found in environment")
    
    print("\n📋 Setup Instructions for Render:")
    print("1. Go to your Render dashboard")
    print("2. Select your calendar-api service")
    print("3. Go to Environment tab")
    print("4. Add new environment variable:")
    print("   - Key: OPENAI_API_KEY")
    print("   - Value: your_openai_api_key_here")
    print("5. Click 'Save Changes'")
    print("6. Render will automatically redeploy with the new key")
    
    print("\n🔑 Getting an OpenAI API Key:")
    print("1. Go to https://platform.openai.com/")
    print("2. Sign up or log in")
    print("3. Go to API Keys section")
    print("4. Create a new API key")
    print("5. Copy the key (starts with 'sk-')")
    
    print("\n💰 Cost Information:")
    print("- GPT-3.5-turbo: ~$0.001 per request")
    print("- GPT-4: ~$0.01 per request")
    print("- Free tier includes $5 credit for new accounts")
    
    print("\n🆓 Free Alternatives (if you prefer):")
    print("- Ollama: 100% free, runs locally")
    print("- Groq: Free tier available")
    print("- The system will work without OpenAI using these alternatives")
    
    print("\n🔍 To test your setup after adding the key:")
    print("Run this script again or check the /healthz endpoint")
    
    return 1

if __name__ == "__main__":
    sys.exit(main())