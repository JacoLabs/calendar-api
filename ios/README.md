# Calendar Event Creator - iOS App

A powerful iOS app that creates calendar events from natural language text using AI-powered parsing.

## 🎯 Features

### Main App
- **Text Input Interface**: Type or paste event text and get structured calendar events
- **SwiftUI Interface**: Modern, native iOS design with smooth animations
- **Calendar Integration**: Direct integration with iOS Calendar app via EventKit
- **Error Handling**: Comprehensive error handling with user-friendly messages

### Share Extension
- **Text Selection Integration**: Select text in any iOS app and create calendar events
- **Share Sheet Integration**: Share text from other apps directly to create calendar events
- **Background Processing**: Processes text and opens calendar editor seamlessly

## 📱 Project Structure

```
ios/
├── CalendarEventApp.xcodeproj/          # Xcode project file
├── CalendarEventApp/                    # Main app target
│   ├── CalendarEventApp.swift          # App entry point
│   ├── ContentView.swift               # Main UI view
│   ├── EventResultView.swift           # Event display and creation view
│   ├── ApiService.swift                # API communication service
│   ├── Models.swift                    # Data models
│   └── Info.plist                      # App configuration
├── CalendarEventExtension/             # Share extension target
│   ├── ActionViewController.swift      # Extension main controller
│   ├── ApiService.swift                # API service for extension
│   ├── MainInterface.storyboard        # Extension UI
│   └── Info.plist                      # Extension configuration
└── README.md                           # This file
```

## 🚀 Getting Started

### Prerequisites
- **Xcode 15.0+** (recommended)
- **iOS 15.0+** deployment target
- **macOS** for development
- **Apple Developer Account** (for device testing)

### Opening the Project

1. **Open Xcode**
2. **Open Project**: File → Open → Navigate to `ios/CalendarEventApp.xcodeproj`
3. **Select Target**: Choose "CalendarEventApp" from the scheme selector
4. **Select Device**: Choose your iPhone or iOS Simulator

### Building and Running

1. **Build the Project**: ⌘+B
2. **Run on Simulator**: ⌘+R (with iOS Simulator selected)
3. **Run on Device**: 
   - Connect your iPhone via USB
   - Select your device from the scheme selector
   - Press ⌘+R

### Code Signing Setup

For running on a physical device:

1. **Select Project**: Click on "CalendarEventApp" in the project navigator
2. **Select Target**: Choose "CalendarEventApp" target
3. **Signing & Capabilities**: 
   - Set your **Team** (Apple Developer Account)
   - Ensure **Bundle Identifier** is unique: `com.yourname.CalendarEventApp`
4. **Repeat for Extension**:
   - Select "CalendarEventExtension" target
   - Set the same **Team**
   - Bundle Identifier will be: `com.yourname.CalendarEventApp.CalendarEventExtension`

## 🔧 Configuration

### API Endpoint
The app connects to: `https://calendar-api-wrxz.onrender.com`

To change the API endpoint, update the `baseURL` in:
- `CalendarEventApp/ApiService.swift`
- `CalendarEventExtension/ApiService.swift`

### Bundle Identifiers
- **Main App**: `com.jacolabs.CalendarEventApp`
- **Extension**: `com.jacolabs.CalendarEventApp.CalendarEventExtension`

Update these in the project settings if needed for your Apple Developer Account.

## 📋 How to Use

### Main App Usage
1. **Open the app**
2. **Enter text** like "Meeting with John tomorrow at 2pm"
3. **Tap "Create Event"**
4. **Review parsed details**
5. **Tap "Add to Calendar"**
6. **iOS Calendar app opens** with pre-filled event

### Share Extension Usage
1. **In any iOS app** (Safari, Mail, Messages, etc.)
2. **Select text** containing event information
3. **Tap Share button**
4. **Choose "Calendar Event Creator"**
5. **Extension processes text** and opens Calendar app

### Text Selection Usage
1. **In any iOS app**
2. **Select text** with event information
3. **In the context menu**, look for "Calendar Event Creator"
4. **Tap it** to process and create event

## 🧪 Testing

### Testing the Main App
1. Open the app in Simulator or on device
2. Try these example texts:
   - "Meeting with John tomorrow at 2pm"
   - "Lunch at Starbucks next Friday 12:30"
   - "Conference call Monday 10am for 1 hour"
   - "Doctor appointment on January 15th at 3:30 PM"

### Testing the Share Extension
1. Open Safari and navigate to any webpage
2. Select some text that contains event information
3. Tap the Share button
4. Look for "Calendar Event Creator" in the share sheet
5. Tap it to test the extension

### Troubleshooting

**Extension not appearing in Share Sheet:**
- Make sure both targets are built and installed
- Try restarting the app
- Check that the extension Info.plist is configured correctly

**Calendar permission denied:**
- Go to Settings → Privacy & Security → Calendars
- Enable access for "Calendar Event Creator"

**API connection issues:**
- Check internet connection
- Verify the API endpoint is accessible
- Check console logs in Xcode for detailed error messages

## 🔒 Permissions

The app requires the following permissions:

### Calendar Access (`NSCalendarsUsageDescription`)
- **Purpose**: Create calendar events from parsed text
- **When requested**: When user taps "Add to Calendar"
- **User control**: Can be managed in Settings → Privacy & Security → Calendars

## 🏗️ Architecture

### Main App Architecture
- **SwiftUI**: Modern declarative UI framework
- **MVVM Pattern**: Clean separation of concerns
- **EventKit**: Native iOS calendar integration
- **URLSession**: Network communication

### Share Extension Architecture
- **UIKit**: Extension uses UIKit for compatibility
- **Action Extension**: Handles text processing from other apps
- **Shared Code**: ApiService is shared between targets

### API Integration
- **REST API**: Communicates with parsing service
- **JSON**: Data exchange format
- **Error Handling**: Comprehensive error management
- **Async/Await**: Modern Swift concurrency

## 🚀 Deployment

### App Store Preparation
1. **Update Version**: Increment version in project settings
2. **Archive**: Product → Archive
3. **Upload**: Use Xcode Organizer to upload to App Store Connect
4. **Review**: Submit for App Store review

### TestFlight Distribution
1. **Archive the app**: Product → Archive
2. **Upload to App Store Connect**
3. **Add to TestFlight**
4. **Invite testers**

## 🔄 Updates and Maintenance

### Updating the API
- Update `baseURL` in both ApiService files
- Test thoroughly with new endpoint
- Update error handling if API changes

### Adding Features
- Follow SwiftUI best practices
- Maintain separation between main app and extension
- Update both targets if shared functionality changes

### Performance Optimization
- Monitor API response times
- Optimize UI for smooth animations
- Test on older devices

## 📞 Support

For issues or questions:
1. Check the troubleshooting section above
2. Review Xcode console logs for detailed error information
3. Test API connectivity independently
4. Verify calendar permissions are granted

---

**The iOS app is production-ready with a clean, modern interface and robust functionality! 📱✨**