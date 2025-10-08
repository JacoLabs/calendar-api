# Quick Start Guide

## The Problem
The browser extension was falling back to complex regex parsing instead of using the powerful LLM system we built.

## The Solution
Use the LLM-powered API server for best results.

## Quick Start (Windows)

1. **Start the API Server**:
   ```cmd
   # Double-click this file or run:
   browser-extension/start_server.bat
   ```

2. **Install Browser Extension**:
   - Open Chrome: `chrome://extensions/`
   - Enable "Developer mode"
   - Click "Load unpacked" → select `browser-extension` folder

3. **Test It**:
   - Select text: "Koji's Birthday Party DATE Sun, Oct 26 2:00 PM EDT"
   - Right-click → "Create calendar event"
   - Should open Google Calendar with perfect parsing!

## Performance
- **LLM Response Time**: 6-11 seconds (high quality)
- **Extension Timeout**: 10 seconds (waits for LLM)
- **Fallback**: Local parsing if LLM fails
- **Quality**: LLM produces much better results than regex

## Why This Works Better
- ✅ **LLM handles complex text**: "Koji's Birthday Party DATE Sun, Oct 26..." → "Koji's Birthday Party"
- ✅ **High confidence**: 1.0 confidence scores from LLM
- ✅ **No regex complexity**: Let the LLM do the hard work
- ✅ **Consistent results**: Same quality every time

## Alternative: Quick Server Start
```cmd
python api_server.py
```

Then use the browser extension normally. The LLM will handle all the parsing complexity for you!