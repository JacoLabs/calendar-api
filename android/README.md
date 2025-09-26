# Calendar Event Creator - Android App

A powerful Android app that creates calendar events from natural language text using AI-powered parsing.

## Features

### 🎯 Core Functionality
- **Text Input Interface**: Type or paste event text and get structured calendar events
- **Text Selection Integration**: Select text in any app and create calendar events via context menu
- **Share Integration**: Share text from other apps directly to create calendar events
- **Calendar Integration**: Seamlessly opens your default calendar app with pre-filled event details

### 🔧 Technical Features
- **Material Design 3 UI**: Modern, accessible interface following Android design guidelines
- **Robust API Integration**: Uses OkHttp for reliable network requests
- **Error Handling**: Comprehensive error handling with user-friendly messages
- **Offline-First Design**: Graceful handling of network issues
- **Multiple Input Methods**: Supports typing, pasting, text selection, and sharing

## How It Works

1. **Text Processing**: The app sends your text to our AI-powered API
2. **Event Extraction**: Natural language processing extracts event details (title, date, time, location)
3. **Calendar Integration**: Opens your calendar app with pre-filled event information
4. **One-Tap Creation**: Review and save the event in your preferred calendar app

## Installation & Setup

### Prerequisites
- Android Studio Arctic Fox or later
- Android SDK 24+ (Android 7.0+)
- Internet connection for API calls

### Building the App

1. **Clone the repository** (if not already done):
   ```bash
   git clone <repository-url>
   cd <repository-name>
   ```

2. **Open in Android Studio**:
   - Open Android Studio
   - Select "Open an existing project"
   - Navigate to the `android` folder
   - Click "OK"

3. **Sync dependencies**:
   - Android Studio will automatically sync Gradle dependencies
   - If not, click "Sync Now" in the notification bar

4. **Build and run**:
   - Connect an Android device or start an emulator
   - Click the "Run" button (green play icon) or press `Ctrl+R`

### APK Installation
If you want to install directly on a device:

1. **Build APK**:
   ```bash
   cd android
   ./gradlew assembleDebug
   ```

2. **Install APK**:
   ```bash
   adb install app/build/outputs/apk/debug/app-debug.apk
   ```

## Usage Guide

### Method 1: Direct Text Input
1. Open the Calendar Event Creator app
2. Type or paste text containing event information
3. Tap "Parse Event"
4. Review the extracted details
5. Tap "Create Calendar Event"
6. Your calendar app opens with the event pre-filled

### Method 2: Text Selection (Any App)
1. In any app (browser, email, messages, etc.), select text containing event information
2. In the context menu, tap "Create calendar event"
3. The app processes the text and opens your calendar app

### Method 3: Share from Other Apps
1. In any app, use the share function on text content
2. Select "Calendar Event Creator" from the share menu
3. The app processes the text and opens your calendar app

## Example Text Formats

The app understands various natural language formats:

### Basic Events
- "Meeting with John tomorrow at 2pm"
- "Lunch next Friday at 12:30"
- "Conference call Monday 10am"

### Events with Locations
- "Dinner at The Keg tonight 7pm"
- "Meeting in Conference Room A tomorrow 3pm"
- "Appointment at 123 Main St on January 15th 2pm"

### Events with Duration
- "Conference call Monday 10am for 1 hour"
- "Workshop from 9am to 5pm next Tuesday"
- "Meeting tomorrow 2pm-3pm"

### Complex Events
- "Doctor appointment on January 15th at 3:30 PM at the medical center"
- "Team standup every Monday at 9am in the main conference room"
- "Lunch meeting with Sarah at Starbucks downtown next Friday 12:30"

## Troubleshooting

### Common Issues

**App won't connect to API**
- Check your internet connection
- Ensure you're not behind a restrictive firewall
- Try again in a few minutes (server might be starting up)

**Text selection menu doesn't show**
- Make sure you've selected actual text (not images or buttons)
- Some apps may not support the PROCESS_TEXT intent
- Try copying the text and using the main app instead

**Calendar app doesn't open**
- Make sure you have a calendar app installed (Google Calendar, Samsung Calendar, etc.)
- Check that the calendar app has necessary permissions
- Try creating an event manually in your calendar app first

**Low confidence scores**
- The text might not contain clear event information
- Try being more specific with dates and times
- Add context like "meeting", "appointment", "lunch", etc.

### Debug Information

To help with troubleshooting, the app provides:
- Confidence scores for parsed events
- Detailed error messages
- Network status indicators

## API Information

The app connects to: `https://calendar-api-wrxz.onrender.com`

**Privacy**: 
- Text is sent to the API for processing only
- No data is stored on our servers
- All processing is stateless and temporary

**Rate Limits**:
- Reasonable usage limits apply
- If you hit limits, wait a few minutes and try again

## Development

### Project Structure
```
android/
├── app/
│   ├── build.gradle                 # Dependencies and build config
│   └── src/main/
│       ├── AndroidManifest.xml      # App permissions and activities
│       ├── java/com/jacolabs/calendar/
│       │   ├── MainActivity.kt      # Main UI and text input
│       │   ├── ApiService.kt        # API communication
│       │   ├── TextProcessorActivity.kt  # Text selection handler
│       │   └── ShareHandlerActivity.kt   # Share intent handler
│       └── res/
│           ├── values/strings.xml   # String resources
│           └── drawable/            # Icons and graphics
└── README.md                        # This file
```

### Key Dependencies
- **Jetpack Compose**: Modern UI toolkit
- **Material Design 3**: Latest design system
- **OkHttp**: HTTP client for API calls
- **Kotlin Coroutines**: Async programming

### Testing
Run the comprehensive test suite:
```bash
python tests/test_android_complete.py
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

[Add your license information here]

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Run the test suite to verify setup
3. Create an issue in the repository with:
   - Android version
   - Device model
   - Error messages
   - Steps to reproduce

---

**Happy event creating! 📅✨**