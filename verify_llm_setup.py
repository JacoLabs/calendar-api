#!/usr/bin/env python3
"""
Verification script for LLM setup with Ollama.
Checks if Ollama is installed and configured properly for the calendar app.
"""

import subprocess
import requests
import time
import sys
from services.llm_service import LLMService


def check_ollama_installed():
    """Check if Ollama is installed."""
    try:
        result = subprocess.run(['ollama', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ Ollama is installed")
            print(f"   Version: {result.stdout.strip()}")
            return True
        else:
            print("❌ Ollama command failed")
            return False
    except FileNotFoundError:
        print("❌ Ollama not found in PATH")
        return False


def check_ollama_running():
    """Check if Ollama service is running."""
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=3)
        if response.status_code == 200:
            print("✅ Ollama service is running")
            return True
        else:
            print(f"❌ Ollama service returned status {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to Ollama service")
        return False
    except Exception as e:
        print(f"❌ Error checking Ollama service: {e}")
        return False


def get_ollama_models():
    """Get list of installed Ollama models."""
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        if response.status_code == 200:
            models = response.json().get('models', [])
            model_names = [model['name'] for model in models]
            
            if model_names:
                print(f"✅ Found {len(model_names)} models:")
                for name in model_names:
                    print(f"   - {name}")
            else:
                print("⚠️  No models installed")
            
            return model_names
        else:
            print("❌ Failed to get model list")
            return []
    except Exception as e:
        print(f"❌ Error getting models: {e}")
        return []


def test_llm_service():
    """Test the LLM service integration."""
    print("\n🧪 Testing LLM Service...")
    
    service = LLMService(provider="auto")
    print(f"   Provider: {service.provider}")
    print(f"   Model: {service.model}")
    print(f"   Available: {service.is_available()}")
    
    # Test extraction
    test_text = "Meeting tomorrow at 2pm"
    try:
        response = service.extract_event(test_text)
        if response.success:
            print("✅ LLM extraction test passed")
            if response.data.get('title'):
                print(f"   Extracted title: {response.data['title']}")
        else:
            print(f"❌ LLM extraction failed: {response.error}")
    except Exception as e:
        print(f"❌ LLM test error: {e}")


def provide_setup_instructions():
    """Provide setup instructions for Ollama."""
    print("\n📋 Setup Instructions:")
    print("=" * 30)
    
    print("\n1. Install Ollama:")
    print("   Windows: Download from https://ollama.ai/download/windows")
    print("   macOS: Download from https://ollama.ai/download/mac or 'brew install ollama'")
    print("   Linux: curl -fsSL https://ollama.ai/install.sh | sh")
    
    print("\n2. Start Ollama service:")
    print("   Windows: Ollama should start automatically after installation")
    print("   macOS/Linux: Run 'ollama serve' in terminal")
    
    print("\n3. Install a recommended model:")
    print("   ollama pull llama3.2:3b    # Fast, good for text processing")
    print("   ollama pull llama3.2:7b    # Better quality, slower")
    print("   ollama pull phi3:mini      # Very fast, smaller model")
    
    print("\n4. Test the setup:")
    print("   python verify_llm_setup.py")
    
    print("\n💡 Alternative: Use free cloud APIs")
    print("   - Groq: Set GROQ_API_KEY environment variable")
    print("   - OpenAI: Set OPENAI_API_KEY environment variable")


def main():
    """Main verification function."""
    print("🔍 LLM Setup Verification for Calendar App")
    print("=" * 45)
    
    # Check Ollama installation
    print("\n📦 Checking Ollama installation...")
    ollama_installed = check_ollama_installed()
    
    if not ollama_installed:
        provide_setup_instructions()
        return False
    
    # Check Ollama service
    print("\n🚀 Checking Ollama service...")
    ollama_running = check_ollama_running()
    
    if not ollama_running:
        print("\n💡 To start Ollama service:")
        print("   Windows: Search for 'Ollama' in Start menu")
        print("   macOS/Linux: Run 'ollama serve' in terminal")
        provide_setup_instructions()
        return False
    
    # Check models
    print("\n🤖 Checking installed models...")
    models = get_ollama_models()
    
    recommended_models = ["llama3.2:3b", "llama3.2:7b", "phi3:mini"]
    has_recommended = any(model in models for model in recommended_models)
    
    if not has_recommended and models:
        print("⚠️  No recommended models found for text processing")
        print("   Consider installing: ollama pull llama3.2:3b")
    elif not models:
        print("❌ No models installed")
        print("   Install a model: ollama pull llama3.2:3b")
        return False
    
    # Test LLM service
    test_llm_service()
    
    print("\n🎉 Setup verification completed!")
    
    if ollama_running and models:
        print("✅ Ollama is ready for use with the calendar app")
        return True
    else:
        print("⚠️  Some issues found - see instructions above")
        return False


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n👋 Verification cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Verification failed: {e}")
        sys.exit(1)