# iOS Calendar Event Creator

A native iOS app that allows users to create calendar events from natural language text input.

## Features

### Main App
- **Text Input Interface**: Simple text field for entering event descriptions
- **API Integration**: Connects to the calendar parsing API at `https://calendar-api-wrxz.onrender.com`
- **Event Preview**: Displays parsed event information with confidence score
- **Calendar Integration**: Creates events in the native iOS Calendar app using EventKit
- **Error Handling**: Graceful handling of network errors and parsing failures

### Share Extension
- **Text Selection**: Select text from any iOS app (Safari, Notes, Messages, etc.)
- **Share Sheet Integration**: Appears as "Calendar Event Creator" in the Share Sheet
- **Automatic Parsing**: Calls API to parse selected text automatically
- **Native Calendar Editor**: Opens iOS EventKit calendar editor with pre-filled data
- **Seamless Workflow**: Complete text-to-calendar flow without leaving the source app

## Project Structure

```
ios/
├── CalendarEventApp/
│   ├── CalendarEventApp.swift      # Main app entry point
│   ├── ContentView.swift           # Main UI with text input
│   ├── Models.swift                # Data models for ParsedEvent
│   ├── ApiService.swift            # API communication service
│   ├── EventResultView.swift       # Event preview and calendar integration
│   └── Info.plist                  # App configuration and permissions
├── CalendarEventExtension/
│   ├── ActionViewController.swift  # Share Extension main controller
│   ├── ApiService.swift            # API service for extension
│   ├── MainInterface.storyboard    # Extension UI storyboard
│   └── Info.plist                  # Extension configuration and permissions
├── CalendarEventApp.xcodeproj/     # Xcode project file
└── README.md                       # This file
```

## Requirements

- iOS 15.0+
- Xcode 15.0+
- Swift 5.0+
- Internet connection for API calls
- Calendar access permission

## Setup

1. Open `CalendarEventApp.xcodeproj` in Xcode
2. Select your development team in the project settings
3. Build and run on device or simulator

## Usage

### Main App
1. Launch the app
2. Enter text containing event information (e.g., "Meeting with John tomorrow at 2pm")
3. Tap "Create Event" to parse the text
4. Review the parsed event details
5. Tap "Add to Calendar" to create the event in your calendar

### Share Extension
1. **Select Text**: In any iOS app (Safari, Notes, Messages, etc.), select text containing event information
2. **Open Share Sheet**: Tap the Share button (square with arrow)
3. **Choose Extension**: Tap "Calendar Event Creator" from the share options
4. **Automatic Processing**: Extension parses the text and opens the calendar editor
5. **Edit & Save**: Review the pre-filled event details and save to your calendar

## API Integration

The app communicates with the calendar parsing API using:
- **Endpoint**: `POST https://calendar-api-wrxz.onrender.com/parse`
- **Request**: JSON with `text` field
- **Response**: ParsedEvent object with title, dates, location, etc.

## Testing

### Main App Test
Run the API integration test:
```bash
python test_ios_basic.py
```

This verifies:
- API connectivity
- Request/response format
- Error handling
- Various text parsing scenarios

### Share Extension Test
Run the end-to-end Share Extension workflow test:
```bash
python test_ios_flow.py
```

This simulates:
- Text selection from other apps
- Share Sheet integration
- API calls from extension
- EventKit calendar editor integration
- Complete workflow validation

## Permissions

The app requires:
- **Calendar Access**: To create events in the user's calendar
- **Network Access**: To communicate with the parsing API

## Example Text Inputs

- "Meeting with John tomorrow at 2pm"
- "Lunch at Starbucks next Friday 12:30"
- "Conference call Monday 10am for 1 hour"
- "Doctor appointment on January 15th at 3:30 PM"