# LLM Text Enhancement Integration Guide

## Overview

This document describes the new LLM-based text enhancement system that replaces the pattern-based EmailPatternEnhancer. The system provides intelligent text preprocessing for better calendar event parsing across all platforms.

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Client Apps   │───▶│   API Gateway    │───▶│  Event Parser   │
│ Android/iOS/Web │    │  (FastAPI)       │    │                 │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                                         │
                                                         ▼
                                               ┌─────────────────┐
                                               │ TextMergeHelper │
                                               │                 │
                                               └─────────────────┘
                                                         │
                                                         ▼
                                               ┌─────────────────┐
                                               │ LLMTextEnhancer │
                                               │  (OpenAI GPT)   │
                                               └─────────────────┘
```

## Key Features

### 1. Smart Text Enhancement
- **Pattern Detection**: Automatically detects school, business, and personal communication patterns
- **Text Restructuring**: Reorganizes confusing text for better parsing
- **Context Preservation**: Maintains all original information while improving structure

### 2. Clipboard Merging
- **Gmail Selection Fix**: Handles partial text selections from Gmail
- **Context Detection**: Prevents merging unrelated clipboard content
- **Sequential Content**: Detects and merges fragmented text pieces

### 3. Fallback Mode
- **No API Key Required**: Works without OpenAI API key using heuristics
- **Graceful Degradation**: Falls back to pattern-based improvements
- **Reliability**: Always returns a result, even if enhancement fails

## API Changes

### New Request Parameters

```json
{
  "text": "On Monday the elementary students will attend the Indigenous Legacy Gathering",
  "clipboard_text": "We will leave school by 9:00 AM",
  "timezone": "America/New_York",
  "locale": "en_US",
  "use_llm_enhancement": true
}
```

### New Response Metadata

```json
{
  "title": "Indigenous Legacy Gathering",
  "start_datetime": "2024-01-15T09:00:00-05:00",
  "confidence_score": 0.92,
  "extraction_metadata": {
    "text_enhancement": {
      "original_text": "On Monday the elementary students will attend...",
      "enhanced_text": "Indigenous Legacy Gathering on Monday for elementary students...",
      "merge_applied": true,
      "enhancement_applied": true,
      "enhancement_confidence": 0.89
    }
  }
}
```

## Platform Integration

### Android Integration

Update your HTTP client calls to include the new parameters:

```kotlin
// In your ApiService.kt or similar
data class ParseRequest(
    val text: String,
    val clipboardText: String? = null,
    val timezone: String = "UTC",
    val locale: String = "en_US",
    val useLlmEnhancement: Boolean = true
)

// Usage in TextMergeHelper equivalent
val request = ParseRequest(
    text = selectedText,
    clipboardText = getClipboardText(),
    timezone = getCurrentTimezone(),
    locale = getCurrentLocale(),
    useLlmEnhancement = true
)
```

### iOS Integration

Update your API client to support the new parameters:

```swift
// In your API client
struct ParseRequest: Codable {
    let text: String
    let clipboardText: String?
    let timezone: String
    let locale: String
    let useLlmEnhancement: Bool
    
    enum CodingKeys: String, CodingKey {
        case text
        case clipboardText = "clipboard_text"
        case timezone
        case locale
        case useLlmEnhancement = "use_llm_enhancement"
    }
}

// Usage
let request = ParseRequest(
    text: selectedText,
    clipboardText: UIPasteboard.general.string,
    timezone: TimeZone.current.identifier,
    locale: Locale.current.identifier,
    useLlmEnhancement: true
)
```

### Browser Extension Integration

Update your JavaScript API calls:

```javascript
// In your content script or popup
async function parseText(selectedText, clipboardText = null) {
    const request = {
        text: selectedText,
        clipboard_text: clipboardText,
        timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
        locale: navigator.language,
        use_llm_enhancement: true
    };
    
    const response = await fetch('/parse', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(request)
    });
    
    return await response.json();
}

// Usage with clipboard access
navigator.clipboard.readText().then(clipboardText => {
    return parseText(selectedText, clipboardText);
});
```

## Configuration

### Environment Variables

```bash
# FREE OPTIONS (choose one):

# Option 1: Ollama (100% free, local)
# No environment variables needed - just install Ollama
# ollama serve && ollama pull llama3.2:3b

# Option 2: Groq (free tier, cloud)
GROQ_API_KEY=your_free_groq_api_key

# PAID OPTION:
# Option 3: OpenAI (paid, high quality)
OPENAI_API_KEY=your_openai_api_key

# Optional: Force specific provider
LLM_PROVIDER=auto  # auto, ollama, groq, openai, huggingface, heuristic

# Optional: Force specific model
LLM_MODEL=llama3.2:3b  # provider-specific model name
```

### Runtime Configuration

```python
# In your application startup
from services.text_merge_helper import TextMergeHelper

# Configure the text merge helper
text_helper = TextMergeHelper(use_llm=True)
text_helper.set_config(
    max_clipboard_merge_distance=200,
    min_confidence_for_merge=0.6,
    enable_context_detection=True,
    enable_safer_defaults=True
)
```

## Testing

### Run the Test Suite

```bash
# Set your OpenAI API key
export OPENAI_API_KEY=your_key_here

# Run the test script
python test_llm_enhancement.py
```

### Test Cases Covered

1. **School Event Pattern**: "On Monday the elementary students will attend..."
2. **Business Meeting Fragment**: Partial selections with time/location
3. **Clipboard Merging**: Gmail selection + clipboard content
4. **Fallback Mode**: Operation without API key

## Performance Considerations

### API Costs
- **Ollama (Recommended)**: $0 - Completely free, runs locally
- **Groq**: $0 - Generous free tier, then ~$0.0001 per request
- **OpenAI GPT-3.5-turbo**: ~$0.001 per request
- **OpenAI GPT-4**: ~$0.01 per request
- **Hugging Face**: $0 - Free but uses local compute resources

### Response Times
- **LLM Enhancement**: 1-3 seconds typical
- **Fallback Mode**: <100ms
- **Async Processing**: Consider async processing for better UX

### Rate Limits
- **OpenAI Limits**: Respect API rate limits
- **Graceful Degradation**: Fall back to heuristics if API is unavailable

## Migration Guide

### From Pattern-Based Approach

1. **Update API Calls**: Add new parameters to existing requests
2. **Handle New Metadata**: Process enhancement metadata in responses
3. **Test Thoroughly**: Verify parsing quality improvements
4. **Monitor Costs**: Track API usage and costs

### Backward Compatibility

- **Existing Clients**: Continue to work without changes
- **New Parameters**: Optional, defaults maintain current behavior
- **Response Format**: Maintains existing structure with additional metadata

## Troubleshooting

### Common Issues

1. **No API Key**: System falls back to heuristic mode
2. **API Errors**: Graceful fallback to original parsing
3. **High Costs**: Consider using GPT-3.5-turbo instead of GPT-4
4. **Slow Responses**: Implement client-side timeouts

### Monitoring

```python
# Monitor enhancement usage
enhancement_stats = llm_enhancer.get_usage_stats()
print(f"Total requests: {enhancement_stats['total_requests']}")
print(f"Total tokens: {enhancement_stats['total_tokens']}")
```

## Benefits

### For Users
- **Better Parsing**: Improved accuracy for complex email patterns
- **Gmail Fix**: Handles partial text selections automatically
- **Consistent Results**: More reliable event extraction

### For Developers
- **Cross-Platform**: Same API works for Android, iOS, and web
- **Maintainable**: Less regex maintenance, more intelligent processing
- **Scalable**: Can improve over time with better models

### For Business
- **User Satisfaction**: Better parsing quality reduces user frustration
- **Reduced Support**: Fewer parsing-related support requests
- **Competitive Advantage**: Advanced AI-powered text processing