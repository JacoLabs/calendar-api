# Platform-Specific User Guides

## Android User Guide

### Getting Started with Android

The Android app integrates seamlessly with your device's text selection system, allowing you to create calendar events from any app that supports text selection.

#### Installation and Setup

1. **Install the App**
   - Download from Google Play Store
   - Grant calendar permissions when prompted
   - The app will automatically integrate with your text selection menu

2. **First Use**
   - Open any app with text (Gmail, Chrome, Messages, etc.)
   - Select text containing event information
   - Look for "Create Calendar Event" in the context menu

#### How to Use Android Text Selection

**Step 1: Select Text**
```
In Gmail:
"Team meeting tomorrow at 2:00 PM in Conference Room A"
↓
Long press on "Team" → drag to select entire sentence
```

**Step 2: Access Context Menu**
- After selecting text, tap "Create Calendar Event" from the menu
- The app will process the text in the background

**Step 3: Review and Save**
- Android's native calendar app opens with pre-filled event data
- Review the extracted information
- Edit any fields as needed
- Tap "Save" to add to your calendar

#### Android-Specific Features

**Text Selection Integration**
- Works in any app that supports text selection
- Appears in the standard Android text selection menu
- No need to copy/paste or switch apps

**Calendar Integration**
- Uses your default Android calendar app
- Respects your calendar preferences and settings
- Automatically syncs with your Google account (if configured)

**Permissions Required**
- Calendar: Read and write access to create events
- Internet: To process text through the parsing service

#### Troubleshooting Android Issues

**"Create Calendar Event" doesn't appear in menu**
- Check that the app is installed and permissions are granted
- Try restarting the app or device
- Ensure you're selecting actual text (not images or buttons)

**Calendar app doesn't open**
- Check that you have a calendar app installed
- Verify calendar permissions are granted
- Try setting a default calendar app in Android settings

**Events not appearing in calendar**
- Check which calendar the event was saved to
- Verify calendar sync settings
- Look in "My Calendar" or your primary Google calendar

#### Best Practices for Android

**Text Selection Tips**
- Select complete sentences for best results
- Include date, time, and location information
- Avoid selecting extra text that isn't event-related

**Performance Tips**
- Ensure good internet connection for text processing
- Close other apps if processing seems slow
- Use Wi-Fi when possible for faster processing

### Android Video Demonstration Script

*Note: This would be accompanied by actual video demonstrations*

**Video 1: Basic Text Selection (2 minutes)**
1. Open Gmail app
2. Find email with meeting information
3. Long-press to start text selection
4. Drag to select relevant text
5. Tap "Create Calendar Event" from menu
6. Show calendar app opening with event details
7. Save event to calendar

**Video 2: Advanced Features (3 minutes)**
1. Demonstrate text selection in different apps (Chrome, Messages)
2. Show handling of complex text with multiple dates
3. Demonstrate editing extracted information
4. Show different calendar apps integration

---

## iOS User Guide

### Getting Started with iOS

The iOS app uses Apple's Share Extension system to integrate with any app that supports text sharing, providing a native iOS experience for creating calendar events.

#### Installation and Setup

1. **Install the App**
   - Download from Apple App Store
   - Grant calendar permissions when prompted
   - The Share Extension will automatically be available

2. **Enable Share Extension**
   - Select text in any app
   - Tap "Share" button
   - Look for "Create Calendar Event" in the share sheet
   - If not visible, tap "More" and enable the extension

#### How to Use iOS Share Extension

**Step 1: Select Text**
```
In Safari:
"Conference call with development team on Friday at 10:00 AM"
↓
Tap and hold → drag to select → tap "Share"
```

**Step 2: Use Share Extension**
- Tap the "Share" button (square with arrow)
- Find "Create Calendar Event" in the share sheet
- Tap to activate the extension

**Step 3: Review and Save**
- iOS Calendar app opens with pre-filled event
- Review extracted information
- Edit any fields as needed
- Tap "Add" to save to your calendar

#### iOS-Specific Features

**Share Extension Integration**
- Works with any app that supports text sharing
- Native iOS interface and experience
- Follows iOS design guidelines and patterns

**EventKit Integration**
- Uses Apple's native calendar framework
- Integrates with iCloud calendar sync
- Respects iOS calendar and privacy settings

**Privacy and Security**
- Text processing follows iOS privacy guidelines
- No data stored on device beyond standard calendar events
- Respects iOS app sandbox security model

#### Troubleshooting iOS Issues

**Share Extension not appearing**
- Check that the app is installed
- Go to Share Sheet → More → enable "Create Calendar Event"
- Restart the app if needed

**Calendar permissions denied**
- Go to Settings → Privacy & Security → Calendars
- Enable access for the app
- Restart the app and try again

**Events not syncing**
- Check iCloud calendar sync settings
- Verify which calendar the event was added to
- Check internet connection for iCloud sync

#### Best Practices for iOS

**Text Selection Tips**
- Use precise selection for better accuracy
- Include context around dates and times
- Select from apps with clear, formatted text

**Share Sheet Usage**
- Organize your share sheet for quick access
- Pin "Create Calendar Event" to favorites
- Use 3D Touch for quick access (on supported devices)

### iOS Video Demonstration Script

**Video 1: Share Extension Basics (2 minutes)**
1. Open Mail app with meeting invitation
2. Select text with event details
3. Tap Share button
4. Select "Create Calendar Event" from share sheet
5. Show Calendar app opening with event
6. Save event and show in calendar view

**Video 2: Cross-App Usage (3 minutes)**
1. Demonstrate in Safari with web page event
2. Show Messages app with text message event
3. Demonstrate Notes app with meeting notes
4. Show how to edit events before saving

---

## Browser Extension User Guide

### Getting Started with Browser Extension

The browser extension works across Chrome, Firefox, and Edge browsers, providing seamless calendar event creation from any webpage text.

#### Installation and Setup

1. **Install Extension**
   - Chrome: Visit Chrome Web Store → search "Text to Calendar Event"
   - Firefox: Visit Firefox Add-ons → search "Text to Calendar Event"
   - Edge: Visit Microsoft Edge Add-ons → search "Text to Calendar Event"

2. **Grant Permissions**
   - Allow access to webpage content
   - Enable context menu integration
   - No additional setup required

#### How to Use Browser Extension

**Step 1: Select Text**
```
On Gmail web:
"Quarterly review meeting next Thursday at 2:00 PM in the main conference room"
↓
Click and drag to select text
```

**Step 2: Right-Click Menu**
- Right-click on selected text
- Choose "Create Calendar Event" from context menu
- Extension popup will appear

**Step 3: Review and Create**
- Review extracted event information in popup
- Edit any fields as needed
- Choose your preferred calendar service
- Click "Create Event" to open calendar

#### Browser Extension Features

**Context Menu Integration**
- Appears in standard browser right-click menu
- Works on any webpage with selectable text
- No need to copy/paste or switch tabs

**Popup Interface**
- Clean, intuitive interface for reviewing events
- Edit capabilities for all event fields
- Confidence indicators for extracted information

**Calendar Service Integration**
- Google Calendar support
- Outlook/Office 365 support
- Apple iCloud Calendar support
- Generic calendar URL generation

#### Troubleshooting Browser Extension

**Context menu option not appearing**
- Check that extension is installed and enabled
- Refresh the webpage and try again
- Ensure you're selecting actual text content

**Popup not opening**
- Check for popup blockers
- Ensure extension has necessary permissions
- Try disabling other extensions temporarily

**Calendar integration not working**
- Check that you're logged into your calendar service
- Verify popup blockers aren't interfering
- Try a different calendar service

#### Best Practices for Browser Extension

**Text Selection**
- Select complete event descriptions
- Include surrounding context for better accuracy
- Avoid selecting navigation or UI elements

**Calendar Integration**
- Stay logged into your preferred calendar service
- Use the same browser for calendar and extension
- Bookmark calendar creation pages for quick access

### Browser Extension Video Demonstration Script

**Video 1: Basic Usage (2 minutes)**
1. Open Gmail in browser
2. Find email with meeting information
3. Select relevant text
4. Right-click → "Create Calendar Event"
5. Show popup with extracted information
6. Click "Google Calendar" → show event creation

**Video 2: Advanced Features (3 minutes)**
1. Demonstrate on different websites (news, social media)
2. Show editing capabilities in popup
3. Demonstrate different calendar service integrations
4. Show confidence indicators and suggestions

---

## Cross-Platform Comparison

### Feature Comparison

| Feature | Android | iOS | Browser Extension |
|---------|---------|-----|-------------------|
| **Text Selection** | System-wide | Share Extension | Webpage text |
| **Integration** | Native menu | Share sheet | Context menu |
| **Calendar** | Default app | EventKit | Web services |
| **Offline** | Limited | Limited | No |
| **Editing** | In calendar app | In calendar app | In popup |
| **Platforms** | Android 6+ | iOS 12+ | Chrome, Firefox, Edge |

### When to Use Each Platform

**Use Android App When:**
- You primarily use Android devices
- You want system-wide text selection
- You prefer native calendar app integration
- You frequently process text from various Android apps

**Use iOS App When:**
- You primarily use iOS devices
- You want native iOS experience
- You use iCloud calendar sync
- You frequently share text between iOS apps

**Use Browser Extension When:**
- You work primarily in web browsers
- You process events from web-based sources
- You use web-based calendar services
- You work on desktop/laptop computers

### Consistency Across Platforms

**What's the Same:**
- Parsing accuracy and capabilities
- Confidence scoring system
- Error handling and suggestions
- Support for same text formats

**What's Different:**
- User interface and interaction patterns
- Calendar integration methods
- Installation and setup process
- Platform-specific features and limitations

## Getting Help and Support

### Common Issues Across All Platforms

**Low Parsing Accuracy**
- Use more specific date and time formats
- Include clear event titles and descriptions
- Provide complete context in selected text
- Check confidence scores and edit as needed

**Calendar Integration Problems**
- Verify calendar permissions are granted
- Check default calendar settings
- Ensure calendar apps are installed and configured
- Test with simple events first

**Performance Issues**
- Check internet connection
- Try with shorter text selections
- Close other apps to free up resources
- Update to latest app version

### Support Resources

**Documentation**
- Complete parsing documentation
- Platform-specific troubleshooting guides
- Best practices and tips
- FAQ and common issues

**Community Support**
- User forums and discussions
- Feature requests and feedback
- Tips and tricks sharing
- Platform-specific communities

**Technical Support**
- Bug reports and issue tracking
- Performance problem reporting
- Feature enhancement requests
- Integration assistance

This comprehensive platform guide ensures users can effectively use the text-to-calendar event system regardless of their preferred platform or device.