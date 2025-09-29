# Free LLM Setup Guide

This guide shows you how to set up free LLM providers for text enhancement instead of using paid OpenAI API.

## 🆓 Recommended: Ollama (100% Free, Local)

**Best option**: Runs locally, completely free, no API keys needed, works offline.

### 1. Install Ollama

**Windows/Mac/Linux:**
```bash
# Visit https://ollama.ai and download the installer
# Or use curl:
curl -fsSL https://ollama.ai/install.sh | sh
```

### 2. Start Ollama Service

```bash
# Start Ollama (runs on http://localhost:11434)
ollama serve
```

### 3. Pull a Good Model for Text Processing

```bash
# Fast, efficient model (1.7GB)
ollama pull llama3.2:3b

# Or larger, more capable model (4.7GB)
ollama pull llama3.2:7b

# Or very small model (1.3GB)
ollama pull phi3:mini
```

### 4. Test It Works

```bash
# Test the model
ollama run llama3.2:3b "Restructure this text for calendar parsing: On Monday the students will attend the assembly"
```

### 5. Use in Your App

```python
# The app will auto-detect Ollama and use it
enhancer = LLMTextEnhancer(provider="auto")  # Will choose Ollama
# Or explicitly:
enhancer = LLMTextEnhancer(provider="ollama", model="llama3.2:3b")
```

## 🚀 Alternative: Groq (Free Tier, Cloud)

**Good option**: Fast inference, generous free tier, cloud-based.

### 1. Get Free API Key

1. Go to https://console.groq.com/
2. Sign up for free account
3. Get your API key from the dashboard

### 2. Set Environment Variable

```bash
# Linux/Mac
export GROQ_API_KEY=your_api_key_here

# Windows
set GROQ_API_KEY=your_api_key_here
```

### 3. Use in Your App

```python
# The app will auto-detect Groq API key and use it
enhancer = LLMTextEnhancer(provider="auto")  # Will choose Groq
# Or explicitly:
enhancer = LLMTextEnhancer(provider="groq", model="llama-3.1-8b-instant")
```

## 🤗 Alternative: Hugging Face (Free, Local)

**Resource intensive**: Runs locally, free, but needs more RAM/CPU.

### 1. Install Dependencies

```bash
pip install transformers torch
```

### 2. Use in Your App

```python
# Will download model on first use (several GB)
enhancer = LLMTextEnhancer(provider="huggingface", model="microsoft/DialoGPT-small")
```

## 💰 Paid Option: OpenAI (Most Capable)

If you want the best quality and don't mind paying:

### 1. Get API Key

1. Go to https://platform.openai.com/
2. Create account and add billing
3. Get API key

### 2. Set Environment Variable

```bash
export OPENAI_API_KEY=your_api_key_here
```

### 3. Install OpenAI Library

```bash
pip install openai
```

## 🔧 Configuration Options

### Auto-Detection (Recommended)

```python
# Will automatically choose the best available provider
enhancer = LLMTextEnhancer(provider="auto")
```

**Priority order:**
1. Ollama (if running locally)
2. Groq (if API key available)
3. OpenAI (if API key available)
4. Hugging Face (if transformers installed)
5. Heuristic fallback (always works)

### Manual Provider Selection

```python
# Force specific provider
enhancer = LLMTextEnhancer(provider="ollama", model="llama3.2:3b")
enhancer = LLMTextEnhancer(provider="groq", model="llama-3.1-8b-instant")
enhancer = LLMTextEnhancer(provider="openai", model="gpt-3.5-turbo")
```

### Disable LLM Entirely

```python
# Use only heuristic improvements
enhancer = LLMTextEnhancer(provider="heuristic")
```

## 📊 Performance Comparison

| Provider | Cost | Speed | Quality | Setup Difficulty |
|----------|------|-------|---------|------------------|
| **Ollama** | Free | Fast | Good | Easy |
| **Groq** | Free tier | Very Fast | Good | Very Easy |
| **Hugging Face** | Free | Slow | Variable | Medium |
| **OpenAI** | $0.001/req | Fast | Excellent | Easy |
| **Heuristic** | Free | Instant | Basic | None |

## 🎯 Recommended Setup for Production

### For Development/Testing
```bash
# Use Ollama - completely free and works offline
ollama serve
ollama pull llama3.2:3b
```

### For Production (Low Volume)
```bash
# Use Groq free tier - fast and reliable
export GROQ_API_KEY=your_free_groq_key
```

### For Production (High Volume)
```bash
# Use Ollama on your server - no per-request costs
# Deploy Ollama on your production server
```

## 🔍 Testing Your Setup

Run the test script to verify everything works:

```bash
python test_llm_enhancement.py
```

You should see output like:
```
🤖 Testing LLM Text Enhancement
==================================================
LLM Text Enhancer initialized with provider: ollama, model: llama3.2:3b
✅ LLM enhancement available and working!
```

## 🛠️ Troubleshooting

### Ollama Issues

```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# Restart Ollama service
ollama serve

# Check available models
ollama list
```

### Groq Issues

```bash
# Test API key
curl -H "Authorization: Bearer $GROQ_API_KEY" https://api.groq.com/openai/v1/models
```

### Memory Issues (Hugging Face)

```python
# Use smaller model
enhancer = LLMTextEnhancer(provider="huggingface", model="distilgpt2")
```

## 🎉 Benefits of Free Setup

✅ **No ongoing costs** - Ollama is completely free
✅ **Privacy** - Local processing, no data sent to external APIs  
✅ **Offline capable** - Works without internet connection
✅ **No rate limits** - Process as much text as you want
✅ **Consistent performance** - No API downtime issues
✅ **Easy deployment** - Just install Ollama on your server

The free Ollama setup is perfect for most use cases and provides excellent text enhancement quality without any ongoing costs!