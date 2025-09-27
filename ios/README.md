# Calendar Event Creator - iOS App

A powerful iOS app that creates calendar events from natural language text using AI-powered parsing, with full Share Extension support.

## Features

### 🎯 Core Functionality
- **Main App Interface**: Beautiful SwiftUI interface for text input and event parsing
- **Share Extension**: Select text in any iOS app and create calendar events via Share Sheet
- **EventKit Integration**: Seamlessly integrates with iOS Calendar app
- **Real-time Parsing**: AI-powered natural language processing with confidence scoring

### 🔧 Technical Features
- **SwiftUI Interface**: Modern, native iOS design following Apple's Human Interface Guidelines
- **Share Extension Target**: Appears in Share Sheet when text is selected in any app
- **EventKit Integration**: Direct integration with iOS Calendar for event creation
- **Robust API Integration**: Uses URLSession with proper error handling
- **Async/Await Support**: Modern Swift concurrency for smooth user experience
- **Comprehensive Error Handling**: User-friendly error messages and graceful degradation

## How It Works

1. **Text Processing**: The app sends your text to our AI-powered API
2. **Event Extraction**: Natural language processing extracts event details (title, date, time, location)
3. **Calendar Integration**: Opens iOS Calendar app with pre-filled event information
4. **One-Tap Creation**: Review and save the event in your iOS Calendar

## Installation & Setup

### Prerequisites
- Xcode 14.0 or later
- iOS 15.0+ deployment target
- Apple Developer account (for device testing)
- Internet connection for API calls

### Building the App

1. **Open in Xcode**:
   - Launch Xcode
   - Choose "Open an existing project"
   - Navigate to the `ios` folder
   - Open `CalendarEventApp.xcodeproj`

2. **Configure Signing**:
   - Select the project in the navigator
   - Choose your development team for both targets:
     - CalendarEventApp (main app)
     - CalendarEventExtension (share extension)

3. **Build and run**:
   - Connect an iOS device or start a simulator
   - Select the CalendarEventApp scheme
   - Click the "Run" button or press `Cmd+R`

### App Store Distribution
For App Store distribution, you'll need:
1. Apple Developer Program membership
2. App Store Connect setup
3. Proper provisioning profiles
4. App Store review compliance

## Usage Guide

### Method 1: Main App Interface
1. Open the Calendar Event Creator app
2. Type or paste text containing event information
3. Tap "Create Event"
4. Review the parsed details
5. Tap "Add to Calendar"
6. The iOS Calendar app opens with the event pre-filled

### Method 2: Share Extension (Any App)
1. In any iOS app (Safari, Mail, Messages, Notes, etc.), select text containing event information
2. Tap "Share" in the context menu
3. Choose "Calendar Event Creator" from the share sheet
4. The extension processes the text and opens the Calendar app with the event pre-filled

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

## Project Structure

```
ios/
├── CalendarEventApp/                    # Main iOS app
│   ├── CalendarEventApp.swift          # App entry point
│   ├── ContentView.swift               # Main UI interface
│   ├── ApiService.swift                # API communication
│   ├── Models.swift                    # Data models
│   ├── EventResultView.swift           # Event display and calendar integration
│   └── Info.plist                     # App configuration
├── CalendarEventExtension/             # Share Extension
│   ├── ActionViewController.swift      # Extension UI and logic
│   ├── ApiService.swift               # API service for extension
│   ├── Info.plist                     # Extension configuration
│   └── MainInterface.storyboard       # Extension UI (minimal)
├── CalendarEventApp.xcodeproj/         # Xcode project
└── README.md                          # This file
```

## Key Components

### Main App (`CalendarEventApp`)
- **ContentView**: SwiftUI interface with text input and parsing
- **EventResultView**: Displays parsed results and handles calendar integration
- **ApiService**: Handles API communication with error handling
- **Models**: Data structures for parsed events

### Share Extension (`CalendarEventExtension`)
- **ActionViewController**: Processes shared text and creates calendar events
- **ApiService**: Async API service optimized for extension context
- **EventKit Integration**: Direct calendar event creation

## Permissions

The app requires the following permissions:

### Calendar Access
- **Purpose**: Create calendar events from parsed text
- **Usage**: EventKit framework for reading/writing calendar events
- **User Control**: Users can grant/revoke in Settings > Privacy & Security > Calendars

### Network Access
- **Purpose**: API calls to parse natural language text
- **Endpoint**: `https://calendar-api-wrxz.onrender.com`
- **Security**: HTTPS only, no sensitive data stored

## Troubleshooting

### Common Issues

**Share Extension doesn't appear**
- Make sure you've selected text (not images or other content)
- Some apps may not support the Share Sheet for text
- Try copying the text and using the main app instead

**Calendar permission denied**
- Go to Settings > Privacy & Security > Calendars
- Enable access for "Calendar Event Creator"
- Restart the app and try again

**API connection issues**
- Check your internet connection
- The app connects to: https://calendar-api-wrxz.onrender.com
- Try again in a few minutes (server might be starting up)

**Low confidence scores**
- Be more specific with dates and times
- Add context words like "meeting", "appointment", "lunch"
- Include location information when possible

**Events not appearing in Calendar**
- Check that the Calendar app has proper permissions
- Verify your default calendar is set up correctly
- Try creating a manual event to test Calendar app functionality

### Debug Information

The app provides:
- Confidence scores for parsed events (0-100%)
- Detailed error messages for API issues
- Graceful handling of network timeouts
- Fallback behavior for parsing failures

## API Information

The app connects to: `https://calendar-api-wrxz.onrender.com`

**Privacy**: 
- Text is sent to the API for processing only
- No data is stored on our servers
- All processing is stateless and temporary
- No personal information is collected

**Rate Limits**:
- Reasonable usage limits apply
- If you hit limits, wait a few minutes and try again

## Development

### Architecture
- **SwiftUI**: Modern declarative UI framework
- **EventKit**: iOS calendar integration
- **URLSession**: Network communication
- **Async/Await**: Modern Swift concurrency
- **Share Extension**: iOS extension framework

### Key Dependencies
- iOS 15.0+ (for async/await support)
- EventKit framework (calendar integration)
- Foundation framework (networking and data)

### Testing
Run the comprehensive test suite:
```bash
python tests/test_ios_complete.py
```

### Customization
You can customize:
- API endpoint in `ApiService.swift`
- UI colors and styling in SwiftUI views
- Default event duration (currently 1 hour)
- Error messages and user feedback

## Privacy & Security

### Data Handling
- Text is processed temporarily for event extraction
- No user data is stored locally or remotely
- All API communication uses HTTPS
- Calendar events are stored only in user's iOS Calendar

### Permissions
- Calendar access: Required for event creation
- Network access: Required for text parsing API
- No location, contacts, or other sensitive permissions required

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly on device and simulator
5. Submit a pull request

## License

[Add your license information here]

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Run the test suite to verify setup
3. Create an issue in the repository with:
   - iOS version
   - Device model
   - Xcode version
   - Error messages
   - Steps to reproduce

---

**Happy event creating! 📅✨**

## App Store Description (Draft)

**Calendar Event Creator**

Transform any text into calendar events instantly! Simply select text containing event information from any app and create calendar events with one tap.

**Features:**
• AI-powered text parsing for natural language event extraction
• Works with any iOS app through Share Extension
• Direct integration with iOS Calendar
• Supports dates, times, locations, and descriptions
• Beautiful native iOS interface
• Privacy-focused: no data stored

**Perfect for:**
• Email invitations
• Text messages with event details
• Web pages with event information
• Notes and documents
• Social media posts

**How it works:**
1. Select text containing event info in any app
2. Tap "Share" → "Calendar Event Creator"
3. Review the extracted details
4. Save to your iOS Calendar

Download now and never manually type event details again!