#!/usr/bin/env python3
"""
Setup script for free LLM providers.
Helps users get started with Ollama or other free options.
"""

import os
import sys
import subprocess
import platform
import requests
import time


def check_ollama_installed():
    """Check if Ollama is installed."""
    try:
        result = subprocess.run(['ollama', '--version'], capture_output=True, text=True)
        return result.returncode == 0
    except FileNotFoundError:
        return False


def check_ollama_running():
    """Check if Ollama service is running."""
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=2)
        return response.status_code == 200
    except:
        return False


def get_ollama_models():
    """Get list of installed Ollama models."""
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        if response.status_code == 200:
            return [model['name'] for model in response.json().get('models', [])]
    except:
        pass
    return []


def install_ollama():
    """Guide user through Ollama installation."""
    system = platform.system().lower()
    
    print("🔧 Installing Ollama...")
    print()
    
    if system == "windows":
        print("📥 For Windows:")
        print("1. Download Ollama from: https://ollama.ai/download/windows")
        print("2. Run the installer")
        print("3. Restart this script")
        
    elif system == "darwin":  # macOS
        print("📥 For macOS:")
        print("Option 1 - Download installer:")
        print("  https://ollama.ai/download/mac")
        print()
        print("Option 2 - Use Homebrew:")
        print("  brew install ollama")
        
    else:  # Linux
        print("📥 For Linux:")
        print("Run this command:")
        print("  curl -fsSL https://ollama.ai/install.sh | sh")
        print()
        
        if input("Run the install command now? (y/n): ").lower() == 'y':
            try:
                subprocess.run("curl -fsSL https://ollama.ai/install.sh | sh", shell=True)
                print("✅ Ollama installation completed!")
                return True
            except Exception as e:
                print(f"❌ Installation failed: {e}")
                return False
    
    print()
    print("After installation, restart this script to continue setup.")
    return False


def start_ollama():
    """Start Ollama service."""
    print("🚀 Starting Ollama service...")
    
    system = platform.system().lower()
    
    if system == "windows":
        print("On Windows, Ollama should start automatically after installation.")
        print("If not, search for 'Ollama' in the Start menu and run it.")
        
    else:
        try:
            # Try to start Ollama in the background
            subprocess.Popen(['ollama', 'serve'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            print("✅ Ollama service started!")
            
            # Wait a moment for service to start
            print("⏳ Waiting for service to be ready...")
            for i in range(10):
                if check_ollama_running():
                    print("✅ Ollama is ready!")
                    return True
                time.sleep(1)
                
            print("⚠️  Service may still be starting. Please wait a moment.")
            return True
            
        except Exception as e:
            print(f"❌ Failed to start Ollama: {e}")
            print("Try running 'ollama serve' manually in another terminal.")
            return False


def pull_model(model_name="llama3.2:3b"):
    """Pull a recommended model."""
    print(f"📦 Downloading model: {model_name}")
    print("This may take a few minutes depending on your internet connection...")
    
    try:
        result = subprocess.run(['ollama', 'pull', model_name], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ Model {model_name} downloaded successfully!")
            return True
        else:
            print(f"❌ Failed to download model: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Error downloading model: {e}")
        return False


def test_setup():
    """Test the LLM setup."""
    print("🧪 Testing LLM setup...")
    
    try:
        from services.llm_text_enhancer import LLMTextEnhancer
        
        enhancer = LLMTextEnhancer(provider="auto")
        
        print(f"Provider: {enhancer.provider}")
        print(f"Model: {enhancer.model}")
        print(f"Available: {enhancer.is_available()}")
        
        if enhancer.is_available():
            # Test enhancement
            test_text = "On Monday the elementary students will attend the Indigenous Legacy Gathering"
            result = enhancer.enhance_text_for_parsing(test_text)
            
            print(f"\n📝 Test Enhancement:")
            print(f"Original: {test_text}")
            print(f"Enhanced: {result.enhanced_text}")
            print(f"Confidence: {result.confidence}")
            
            if result.enhanced_text != test_text:
                print("✅ LLM enhancement is working!")
            else:
                print("⚠️  LLM enhancement available but may need tuning")
            
            return True
        else:
            print("❌ LLM enhancement not available")
            return False
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False


def setup_groq_alternative():
    """Guide user through Groq setup as alternative."""
    print("\n🚀 Alternative: Groq (Free Cloud API)")
    print("=" * 40)
    print("Groq offers a generous free tier with fast inference.")
    print()
    print("Setup steps:")
    print("1. Go to: https://console.groq.com/")
    print("2. Sign up for a free account")
    print("3. Get your API key from the dashboard")
    print("4. Set environment variable:")
    
    system = platform.system().lower()
    if system == "windows":
        print("   set GROQ_API_KEY=your_api_key_here")
    else:
        print("   export GROQ_API_KEY=your_api_key_here")
    
    print("5. Restart this application")
    print()
    
    api_key = input("Enter your Groq API key (or press Enter to skip): ").strip()
    if api_key:
        os.environ['GROQ_API_KEY'] = api_key
        print("✅ Groq API key set for this session!")
        return True
    
    return False


def main():
    """Main setup function."""
    print("🤖 Free LLM Setup for Calendar Text Enhancement")
    print("=" * 50)
    print()
    
    # Check current status
    ollama_installed = check_ollama_installed()
    ollama_running = check_ollama_running()
    models = get_ollama_models()
    
    print("📊 Current Status:")
    print(f"   Ollama installed: {'✅' if ollama_installed else '❌'}")
    print(f"   Ollama running: {'✅' if ollama_running else '❌'}")
    print(f"   Models available: {len(models)} ({', '.join(models[:3])}{'...' if len(models) > 3 else ''})")
    print()
    
    # Setup workflow
    if not ollama_installed:
        print("🎯 Recommended: Install Ollama (100% free, runs locally)")
        if input("Install Ollama now? (y/n): ").lower() == 'y':
            if not install_ollama():
                # Offer Groq as alternative
                setup_groq_alternative()
                return
        else:
            # Offer Groq as alternative
            if setup_groq_alternative():
                test_setup()
            return
    
    if not ollama_running:
        if input("Start Ollama service? (y/n): ").lower() == 'y':
            if not start_ollama():
                return
    
    # Check for good models
    recommended_models = ["llama3.2:3b", "llama3.2:7b", "phi3:mini"]
    has_good_model = any(model in models for model in recommended_models)
    
    if not has_good_model:
        print("📦 No recommended models found.")
        print("Recommended models for text processing:")
        for i, model in enumerate(recommended_models, 1):
            print(f"   {i}. {model}")
        
        choice = input(f"Download model (1-{len(recommended_models)}) or skip (s): ").strip()
        
        if choice.isdigit() and 1 <= int(choice) <= len(recommended_models):
            model_to_pull = recommended_models[int(choice) - 1]
            pull_model(model_to_pull)
    
    # Test the setup
    print("\n" + "=" * 50)
    test_setup()
    
    print("\n🎉 Setup Complete!")
    print("You can now use free LLM text enhancement in your calendar app.")
    print()
    print("💡 Tips:")
    print("- Ollama runs locally and is completely free")
    print("- Models are cached locally after first download")
    print("- Works offline once models are downloaded")
    print("- No API keys or rate limits to worry about")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Setup cancelled by user")
    except Exception as e:
        print(f"\n❌ Setup failed: {e}")
        print("Please check the FREE_LLM_SETUP.md guide for manual setup instructions.")