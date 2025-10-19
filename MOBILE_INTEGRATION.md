# Mobile Integration Guide

Complete guide for integrating the Calendar Event Creator with Android and iOS platforms.

## Overview

The Calendar Event Creator provides native mobile apps for both Android and iOS platforms that integrate with the AI-powered text parsing API. Both apps support multiple input methods and seamless calendar integration.

## Architecture

```
Mobile Apps Architecture
├── API Service (calendar-api-wrxz.onrender.com)
│   ├── /parse endpoint - Text to event parsing
│   └── Hybrid regex/LLM processing
├── Android App
│   ├── Main Activity - Direct text input
│   ├── Text Processor - Text selection integration
│   ├── Share Handler - Share intent processing
│   └── Calendar Intent Helper - Calendar integration
└── iOS App
    ├── Main App - SwiftUI interface
    ├── Share Extension - Text processing from other apps
    └── EventKit Integration - Native calendar access
```

## Android Integration

### Features
- **Material Design 3 UI** with modern Android design guidelines
- **Text Selection Integration** - Select text in any app and create events
- **Share Integration** - Share text from other apps directly
- **Multiple Calendar Support** - Works with Google Calendar, Samsung Calendar, Outlook, etc.
- **Offline-First Design** - Graceful handling of network issues
- **Robust Error Handling** - Comprehensive error management with user feedback

### Prerequisites
- Android Studio Arctic Fox or later
- Android SDK 24+ (Android 7.0+)
- Java 11 or newer (Java 8 not supported)
- Internet connection for API calls

### Quick Setup

1. **Open in Android Studio**:
   ```bash
   # Navigate to android folder
   cd android
   # Open in Android Studio or use command line
   ./gradlew assembleDebug
   ```

2. **Install APK**:
   ```bash
   adb install app/build/outputs/apk/debug/app-debug.apk
   ```

### Usage Methods

#### Method 1: Direct Text Input
1. Open the Calendar Event Creator app
2. Type or paste event text: "Meeting with John tomorrow at 2pm"
3. Tap "Parse Event"
4. Review extracted details
5. Tap "Create Calendar Event"

#### Method 2: Text Selection (Any App)
1. In any app (browser, email, messages), select text containing event info
2. In the context menu, tap "Create calendar event"
3. Calendar app opens with pre-filled event

#### Method 3: Share from Other Apps
1. In any app, use share function on text content
2. Select "Calendar Event Creator" from share menu
3. Calendar app opens with processed event

### Android-Specific Features

#### Calendar Intent Helper
The app includes a robust `CalendarIntentHelper` that:
- Handles Android 11+ package visibility restrictions
- Provides multiple fallback mechanisms
- Supports web calendar fallback (Google Calendar)
- Works with all major calendar apps

#### Text Processing Integration
- Uses `Intent.ACTION_PROCESS_TEXT` for text selection
- Supports share intents from other applications
- Background processing with user notifications

### Troubleshooting Android

**Java Version Issues**:
- Upgrade to Java 11+ or use Android Studio's embedded JDK
- Set JAVA_HOME environment variable correctly

**Calendar App Not Found**:
- Install Google Calendar or Samsung Calendar
- Check calendar app permissions
- App automatically falls back to web calendar if needed

**Text Selection Not Working**:
- Some apps (like Gmail) have restricted text selection menus
- Use share menu instead
- Try screenshot text selection for better results

## iOS Integration

### Features
- **SwiftUI Interface** - Modern, native iOS design
- **Share Extension** - Process text from any iOS app
- **EventKit Integration** - Direct calendar access without leaving the app
- **Background Processing** - Seamless text processing
- **Universal App** - Works on iPhone and iPad

### Prerequisites
- Xcode 15.0+ (recommended)
- iOS 15.0+ deployment target
- macOS for development
- Apple Developer Account (for device testing)

### Quick Setup

1. **Open in Xcode**:
   ```bash
   # Navigate to ios folder
   cd ios
   # Open project file
   open CalendarEventApp.xcodeproj
   ```

2. **Configure Code Signing**:
   - Set your Apple Developer Team
   - Update Bundle Identifiers:
     - Main App: `com.yourname.CalendarEventApp`
     - Extension: `com.yourname.CalendarEventApp.CalendarEventExtension`

3. **Build and Run**: ⌘+R

### Usage Methods

#### Main App Usage
1. Open the Calendar Event Creator app
2. Enter text: "Lunch at Starbucks next Friday 12:30"
3. Tap "Create Event"
4. Review parsed details
5. Tap "Add to Calendar"
6. iOS Calendar opens with pre-filled event

#### Share Extension Usage
1. In any iOS app (Safari, Mail, Messages)
2. Select text containing event information
3. Tap Share button
4. Choose "Calendar Event Creator"
5. Extension processes text and opens Calendar app

### iOS-Specific Features

#### EventKit Integration
- Direct calendar access without switching apps
- Native iOS calendar picker
- Automatic calendar permission handling
- Support for all iOS calendar accounts

#### Share Extension
- Processes text from any iOS app
- Background processing with loading indicators
- Seamless handoff to main Calendar app
- Supports both text selection and share sheet

### Troubleshooting iOS

**Extension Not Appearing**:
- Ensure both targets are built and installed
- Restart the app if needed
- Check extension Info.plist configuration

**Calendar Permission Denied**:
- Go to Settings → Privacy & Security → Calendars
- Enable access for "Calendar Event Creator"

**Build Errors**:
- Clean build folder (⌘+Shift+K)
- Verify EventKit frameworks are linked
- Check bundle identifiers are properly configured

## API Integration

### Endpoint
Both mobile apps connect to: `https://calendar-api-wrxz.onrender.com/parse`

### Request Format
```json
{
  "text": "Meeting with John tomorrow at 2pm",
  "now": "2025-01-15T10:00:00Z",
  "timezone_offset": -300
}
```

### Response Format
```json
{
  "success": true,
  "parsed_event": {
    "title": "Meeting with John",
    "start_datetime": "2025-01-16T14:00:00",
    "end_datetime": "2025-01-16T15:00:00",
    "location": null,
    "description": "Meeting with John tomorrow at 2pm",
    "confidence_score": 0.85,
    "all_day": false,
    "timezone": "America/Toronto"
  }
}
```

### Error Handling
Both apps include comprehensive error handling for:
- Network connectivity issues
- API server errors
- Invalid response formats
- Low confidence scores
- Calendar integration failures

## Supported Text Formats

Both mobile apps understand various natural language formats:

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

## Development Setup

### Android Development
```bash
# Clone repository
git clone <repository-url>
cd android

# Build debug APK
./gradlew assembleDebug

# Install on device
adb install app/build/outputs/apk/debug/app-debug.apk

# Run tests
python ../tests/test_android_complete.py
```

### iOS Development
```bash
# Navigate to iOS project
cd ios

# Open in Xcode
open CalendarEventApp.xcodeproj

# Build from command line (optional)
xcodebuild -project CalendarEventApp.xcodeproj -scheme CalendarEventApp build
```

## Testing

### Android Testing
- Run comprehensive test suite: `python tests/test_android_complete.py`
- Test text selection in Chrome, Messages, Slack
- Test share functionality from various apps
- Verify calendar integration with multiple calendar apps

### iOS Testing
- Test main app with various text inputs
- Test share extension from Safari, Mail, Messages
- Verify EventKit integration and permissions
- Test on both iPhone and iPad

### Cross-Platform Testing
- Verify API compatibility between platforms
- Test identical text inputs on both platforms
- Compare parsing results and calendar integration
- Validate error handling consistency

## Deployment

### Android Deployment
1. **Build Release APK**:
   ```bash
   ./gradlew assembleRelease
   ```

2. **Google Play Store**:
   - Sign APK with release keystore
   - Upload to Google Play Console
   - Complete store listing and review process

### iOS Deployment
1. **Archive for Distribution**:
   - Product → Archive in Xcode
   - Use Xcode Organizer to upload

2. **App Store**:
   - Upload to App Store Connect
   - Complete app review process
   - Submit for review

### TestFlight Distribution (iOS)
- Upload build to App Store Connect
- Add to TestFlight
- Invite beta testers

## Security and Privacy

### Data Handling
- Text is sent to API for processing only
- No data stored on servers
- All processing is stateless and temporary
- Calendar data remains on device

### Permissions
- **Android**: Calendar access, network access
- **iOS**: Calendar access (EventKit), network access
- Both apps request permissions only when needed

### API Security
- HTTPS encryption for all API communication
- Rate limiting to prevent abuse
- No authentication required for basic usage

## Performance Optimization

### Network Optimization
- Efficient HTTP client usage (OkHttp for Android, URLSession for iOS)
- Request/response compression
- Timeout handling and retry logic
- Offline mode support

### UI Performance
- Async processing to prevent UI blocking
- Loading indicators for better user experience
- Smooth animations and transitions
- Memory-efficient image and resource handling

## Monitoring and Analytics

### Error Tracking
- Comprehensive error logging
- Network failure tracking
- Calendar integration issue monitoring
- User feedback collection

### Performance Metrics
- API response time monitoring
- App launch time tracking
- Calendar integration success rates
- User engagement metrics

## Support and Maintenance

### Common Issues
1. **API Connection Problems**
   - Check internet connectivity
   - Verify API endpoint accessibility
   - Review server logs for issues

2. **Calendar Integration Issues**
   - Verify calendar app permissions
   - Check calendar app compatibility
   - Test with multiple calendar applications

3. **Text Processing Problems**
   - Review confidence scores
   - Test with various text formats
   - Check API response format

### Updates and Maintenance
- Regular API endpoint health checks
- Mobile app updates for OS compatibility
- Feature enhancements based on user feedback
- Security updates and patches

## Contributing

### Development Guidelines
- Follow platform-specific design guidelines (Material Design for Android, Human Interface Guidelines for iOS)
- Maintain code consistency between platforms
- Write comprehensive tests for new features
- Document API changes and mobile app updates

### Code Structure
- Shared API integration patterns
- Platform-specific UI implementations
- Common error handling approaches
- Consistent user experience across platforms

---

**Both mobile apps are production-ready with comprehensive features, robust error handling, and seamless calendar integration! 📱✨**