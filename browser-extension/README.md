# Calendar Event Creator - Browser Extension

A browser extension that creates calendar events from selected text using natural language processing.

## Features

### Enhanced Popup Interface
- **Event Display**: Shows parsed event details with confidence scores
- **Calendar Integration**: Direct buttons for Google Calendar and Outlook
- **User Preferences**: Customizable settings and advanced options
- **Cross-Browser Support**: Compatible with Chrome, Firefox, and Edge

### Event Parsing Display
- **Title**: Extracted event title with confidence score
- **Date & Time**: Formatted date/time information
- **Location**: Optional location details
- **Description**: Event description from original text
- **Overall Confidence**: Visual progress bar showing parsing confidence

### Calendar Integration
- **Google Calendar**: Direct integration with pre-filled event data
- **Outlook Calendar**: Support for Outlook web calendar
- **Default Service**: User-configurable default calendar service

### User Preferences
- **Calendar Service**: Choose between Google Calendar and Outlook
- **Floating Button**: Optional floating button on web pages
- **Auto-Parse**: Automatically parse selected text when popup opens
- **Confidence Threshold**: Adjust minimum confidence for successful parsing
- **Show Confidence Scores**: Toggle visibility of confidence indicators

## Installation

### Chrome/Edge
1. Open Chrome/Edge and navigate to `chrome://extensions/` or `edge://extensions/`
2. Enable "Developer mode"
3. Click "Load unpacked" and select the `browser-extension` folder
4. The extension icon will appear in the toolbar

### Firefox
1. Open Firefox and navigate to `about:debugging`
2. Click "This Firefox"
3. Click "Load Temporary Add-on"
4. Select the `manifest.json` file in the `browser-extension` folder

## Usage

### Method 1: Context Menu
1. Select text containing event information on any webpage
2. Right-click and select "Create calendar event"
3. The extension will parse the text and open your default calendar

### Method 2: Extension Popup
1. Click the extension icon in the toolbar
2. Paste or type event text in the input field
3. Click "Parse Text & Create Event"
4. Review the parsed results and click a calendar button

### Method 3: Selected Text (Auto-load)
1. Select text on any webpage
2. Click the extension icon
3. The selected text will be automatically loaded
4. If auto-parse is enabled, results will be shown immediately

## Settings

### Basic Settings
- **Default Calendar**: Choose Google Calendar or Outlook as default
- **Show Floating Button**: Enable/disable floating button on web pages

### Advanced Settings
- **Auto-parse on Selection**: Automatically parse when selected text is loaded
- **Confidence Threshold**: Set minimum confidence level (30%, 50%, or 70%)
- **Show Confidence Scores**: Display confidence indicators for parsed fields

## Supported Text Formats

### Date Formats
- Explicit dates: "Monday, Sep 29, 2025", "09/29/2025", "September 29th"
- Relative dates: "tomorrow", "next Friday", "in two weeks"
- Natural phrases: "the first day back after break", "end of month"

### Time Formats
- Standard times: "2:00 PM", "14:00", "2pm", "2 o'clock"
- Typo-tolerant: "2p.m", "2 PM", "2:00 A M"
- Relative times: "after lunch", "before school", "end of day"
- Time ranges: "2-3 PM", "from 2:00 to 3:30"

### Location Formats
- Explicit addresses: "123 Main Street", "Nathan Phillips Square"
- Implicit locations: "at school", "the gym", "downtown"
- Directional: "meet at the front doors", "by the entrance"

## Testing

Open `test-popup.html` in a web browser to test the extension functionality without installing it. This test page includes:

- Event parsing simulation
- Calendar URL generation testing
- Cross-browser compatibility checks
- Mock Chrome extension API responses

## Browser Compatibility

### Chrome (Recommended)
- Full feature support
- Manifest V3 compatibility
- Optimal performance

### Firefox
- Core functionality supported
- Some API differences handled gracefully
- Manifest V2 compatibility mode

### Edge
- Full Chrome compatibility
- Native Chromium support
- All features available

## Troubleshooting

### Extension Loading Slowly?
1. **Use the fast server**: `python browser-extension/start_fast_server.py`
2. **Check API timeout**: Extension will fallback to local parsing after 3 seconds
3. **Works without API**: Extension has built-in parsing and works offline

### Extension Not Loading
- Ensure Developer mode is enabled
- Check for manifest.json syntax errors
- Verify all required files are present

### Context Menu Not Appearing
- Refresh the webpage after installing
- Check extension permissions
- Ensure text is properly selected

### Calendar Not Opening
- Check popup blocker settings
- Verify internet connection
- Ensure calendar service URLs are accessible

### Parsing Issues
- Extension will work with local fallback parsing even if API is down
- Check API connectivity for advanced features
- Verify text contains recognizable event information
- Try adjusting confidence threshold in settings

### Performance Tips:
- Use the lightweight server for fastest startup
- Extension works immediately even if API is slow
- Local fallback handles basic parsing (time, date, location)
- No need to wait for heavy LLM processing

## Performance Optimization

### Fast Server Startup
For the best performance, use the fast startup script:

```bash
# Fast startup (tries lightweight server first)
python browser-extension/start_fast_server.py
```

### Server Options

1. **Lightweight Server** (fastest startup):
```bash
python browser-extension/lightweight_server.py
```

2. **Full Server** (more features, slower startup):
```bash
python api_server.py
```

### Extension Performance Features

- ⚡ **3-second timeout** prevents hanging on slow API calls
- 🔄 **Automatic fallback** to local parsing when API is slow/unavailable
- 📱 **Works offline** with built-in parsing capabilities
- 🚀 **No waiting** - extension responds immediately even if API is down

## API Integration

The extension connects to the Calendar Event Creator API with smart fallback:
- **Primary**: `https://calendar-api-wrxz.onrender.com` (Production FastAPI)
- **Fallback**: `http://localhost:5000` (Local development)
- **Final Fallback**: Local parsing (works offline)
- **Endpoint**: `POST /parse`
- **Health Check**: `GET /healthz`

### Request Format
```json
{
  "text": "Meeting tomorrow at 2pm",
  "timezone": "America/New_York",
  "locale": "en-US",
  "now": "2024-01-15T10:00:00Z"
}
```

### Response Format
```json
{
  "title": "Meeting",
  "start_datetime": "2024-01-16T14:00:00",
  "end_datetime": "2024-01-16T15:00:00",
  "location": null,
  "description": "Meeting tomorrow at 2pm",
  "confidence_score": 0.85,
  "field_confidence": {
    "title": 0.9,
    "start_datetime": 0.8,
    "location": 0.0
  }
}
```

## Privacy

- Text is sent to the API for parsing only when explicitly requested
- No data is stored permanently by the extension
- User preferences are stored locally in browser storage
- No tracking or analytics are implemented

## Development

### File Structure
```
browser-extension/
├── manifest.json          # Extension configuration
├── popup.html            # Enhanced popup interface
├── popup.js              # Popup logic and event handling
├── background.js         # Service worker and API communication
├── content.js            # Content script for text selection
├── test-popup.html       # Testing interface
└── README.md            # This documentation
```

### Key Features Implemented
- ✅ Enhanced popup interface with event display
- ✅ Calendar integration buttons (Google Calendar, Outlook)
- ✅ User preferences and settings management
- ✅ Confidence scoring and visual indicators
- ✅ Cross-browser compatibility testing
- ✅ Advanced settings with customizable options
- ✅ Auto-parse functionality
- ✅ Event editing and re-parsing capabilities

## Requirements Satisfied

This implementation satisfies the following requirements:

**Requirement 1.4**: Pre-populate calendar event creation form with extracted data
- ✅ Calendar integration buttons open web calendars with pre-filled data

**Requirement 5.1**: Save events to user's default calendar
- ✅ Default calendar service setting with Google Calendar and Outlook support

**Requirement 5.2**: Provide confirmation with event details
- ✅ Event results display shows all parsed details before calendar creation
- ✅ Confidence scores provide quality feedback
- ✅ Success messages confirm calendar opening