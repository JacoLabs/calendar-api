# iOS App Xcode Setup Guide

## Issues Fixed

This guide addresses the common Xcode issues that were found and fixed in the iOS Calendar Event App:

### 1. Missing MainInterface.storyboard
**Issue**: Extension was missing the required storyboard file
**Fix**: Created `MainInterface.storyboard` with proper UI layout

### 2. API Response Parsing Mismatch
**Issue**: Main app and extension were expecting different response formats
**Fix**: Updated both to handle nested `parsed_event` response format

### 3. Model Property Inconsistencies
**Issue**: Optional properties causing crashes when accessing
**Fix**: Made `allDay` and `timezone` optional with default values

### 4. EventKit Framework Missing
**Issue**: Project wasn't linking EventKit and EventKitUI frameworks
**Fix**: Added framework references to project configuration

### 5. Bundle Identifier Issues
**Issue**: Generic bundle identifiers that might conflict
**Fix**: Updated to use `com.yourcompany.CalendarEventApp` format

## Setup Instructions

### Step 1: Open Project in Xcode
1. Navigate to the `ios` folder
2. Double-click `CalendarEventApp.xcodeproj`
3. Wait for Xcode to load the project

### Step 2: Configure Development Team
1. Select the project root in the navigator
2. Select the "CalendarEventApp" target
3. In the "Signing & Capabilities" tab:
   - Set your Development Team
   - Ensure "Automatically manage signing" is checked
4. Repeat for the "CalendarEventExtension" target

### Step 3: Update Bundle Identifiers (if needed)
1. For the main app target:
   - Change `com.yourcompany.CalendarEventApp` to your preferred identifier
2. For the extension target:
   - Change `com.yourcompany.CalendarEventApp.CalendarEventExtension` to match your main app

### Step 4: Verify Framework Links
The project should automatically link these frameworks:
- EventKit.framework
- EventKitUI.framework

If they're missing:
1. Select the target
2. Go to "Build Phases" → "Link Binary With Libraries"
3. Click "+" and add the missing frameworks

### Step 5: Build and Test
1. Select a simulator or device
2. Build the project (⌘+B)
3. Run the app (⌘+R)

## Common Xcode Issues and Solutions

### Issue: "No such module 'EventKit'"
**Solution**: 
1. Clean build folder (⌘+Shift+K)
2. Verify EventKit is linked in Build Phases
3. Check deployment target is iOS 15.0+

### Issue: Extension not appearing in Share Sheet
**Solution**:
1. Verify Info.plist has correct NSExtension configuration
2. Check that NSExtensionActivationSupportsText is true
3. Ensure extension bundle identifier is correct

### Issue: API calls failing
**Solution**:
1. Check network permissions in Info.plist
2. Verify API endpoint URL is correct
3. Test with a simple network request first

### Issue: Calendar permissions not working
**Solution**:
1. Verify NSCalendarsUsageDescription is in both Info.plist files
2. Check that EventKit is properly imported
3. Test permission request in simulator

### Issue: Storyboard compilation errors
**Solution**:
1. Open MainInterface.storyboard in Interface Builder
2. Check for any missing constraints or outlets
3. Verify the custom class is set to ActionViewController

## Testing the Extension

### Test in Simulator
1. Open Safari or Notes app
2. Type some text with event information
3. Select the text
4. Tap Share button
5. Look for "Create Calendar Event" option

### Test on Device
1. Install the app on a physical device
2. Open any app with selectable text
3. Select text containing event information
4. Use Share → "Create Calendar Event"

## Debugging Tips

### Enable Debug Logging
Add this to your ApiService for debugging:
```swift
print("API Request: \(String(data: request.httpBody ?? Data(), encoding: .utf8) ?? "")")
print("API Response: \(String(data: data, encoding: .utf8) ?? "")")
```

### Check Extension Logs
1. Open Console app on Mac
2. Connect your iOS device
3. Filter by your app's bundle identifier
4. Look for extension-related logs

### Verify Network Requests
1. Use Charles Proxy or similar tool
2. Monitor HTTP requests from the app
3. Verify request format and response handling

## Project Structure

```
ios/
├── CalendarEventApp/
│   ├── CalendarEventApp.swift      # Main app entry point
│   ├── ContentView.swift           # Main UI
│   ├── EventResultView.swift       # Result display
│   ├── ApiService.swift            # API communication
│   ├── Models.swift                # Data models
│   └── Info.plist                  # App configuration
├── CalendarEventExtension/
│   ├── ActionViewController.swift  # Extension controller
│   ├── ApiService.swift            # Extension API service
│   ├── MainInterface.storyboard    # Extension UI
│   └── Info.plist                  # Extension configuration
└── CalendarEventApp.xcodeproj/     # Xcode project
```

## Key Files Explained

### CalendarEventApp.swift
- SwiftUI app entry point
- Minimal configuration required

### ContentView.swift
- Main app interface
- Text input and parsing UI
- Handles API calls and result display

### EventResultView.swift
- Displays parsed event information
- Handles calendar integration
- Shows confidence scores and allows editing

### ActionViewController.swift
- Extension entry point
- Processes shared text
- Creates calendar events directly

### ApiService.swift (both versions)
- Handles API communication
- Error handling and retry logic
- Response parsing and validation

### Models.swift
- Data structures for parsed events
- Codable implementations
- Helper methods for display

## Troubleshooting Checklist

- [ ] Development team is set for both targets
- [ ] Bundle identifiers are unique and properly formatted
- [ ] EventKit and EventKitUI frameworks are linked
- [ ] NSCalendarsUsageDescription is in both Info.plist files
- [ ] MainInterface.storyboard exists and is properly configured
- [ ] API endpoint URL is correct and accessible
- [ ] Extension Info.plist has correct NSExtension configuration
- [ ] Build settings match for both targets (iOS 15.0+ deployment)

## Next Steps

1. Test the app thoroughly on both simulator and device
2. Customize the UI to match your design preferences
3. Add additional error handling as needed
4. Consider adding analytics or crash reporting
5. Prepare for App Store submission if desired

This setup should resolve the common Xcode issues and provide a solid foundation for the iOS Calendar Event App.