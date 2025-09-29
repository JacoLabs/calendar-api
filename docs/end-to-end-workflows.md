# End-to-End User Workflows Documentation

## Overview

This document provides comprehensive documentation of complete user workflows from text selection to calendar event creation across all supported platforms: Android, iOS, and Browser Extension.

## Complete User Workflows

### Workflow 1: Android Text Selection Flow

#### Step-by-Step Process

1. **Text Selection**
   - User highlights text in any Android app (Gmail, Chrome, Messages, etc.)
   - Long-press to select text containing event information
   - Selection handles appear to adjust selection boundaries

2. **Context Menu Activation**
   - Android displays text selection context menu
   - "Create Calendar Event" option appears (added by our app)
   - User taps "Create Calendar Event"

3. **Background Processing**
   - Android launches our app's ACTION_PROCESS_TEXT intent handler
   - App receives selected text as intent extra
   - Background service makes API call to parsing endpoint

4. **API Processing**
   - Text sent to POST /parse endpoint
   - MasterEventParser processes text using LLM-first strategy
   - Structured event data returned with confidence scores

5. **Event Creation**
   - App receives parsed event data
   - CalendarContract.Events used to create calendar entry
   - Native Android calendar app opens with pre-filled event data

6. **User Confirmation**
   - User reviews event in native calendar interface
   - Can edit any fields (title, time, location, etc.)
   - Saves event to their default calendar

#### Technical Flow Diagram
```
[Text Selection] → [Context Menu] → [Intent Handler] → [API Call] → [Calendar Integration] → [Event Saved]
     ↓                ↓               ↓               ↓              ↓                    ↓
  User Action    Android System   Our App Service   Parsing API    Android Calendar    User Calendar
```

#### Example Workflow
```
1. User selects: "Team meeting tomorrow at 2pm in Conference Room A"
2. Taps "Create Calendar Event" from context menu
3. App processes text → API returns:
   {
     "title": "Team Meeting",
     "start_datetime": "2025-09-30T14:00:00",
     "location": "Conference Room A",
     "confidence_score": 0.85
   }
4. Android calendar opens with pre-filled event
5. User confirms and saves to calendar
```

### Workflow 2: iOS Share Extension Flow

#### Step-by-Step Process

1. **Text Selection**
   - User highlights text in any iOS app (Safari, Mail, Messages, etc.)
   - Tap and hold to select text with event information
   - Selection handles appear for adjustment

2. **Share Sheet Activation**
   - User taps "Share" button or uses share gesture
   - iOS Share Sheet appears with available actions
   - "Create Calendar Event" extension appears in action list

3. **Extension Processing**
   - User taps "Create Calendar Event" extension
   - iOS launches our Share Extension with selected text
   - Extension makes API call to parsing service

4. **API Processing**
   - Selected text sent to POST /parse endpoint
   - Server processes text and returns structured event data
   - Extension receives parsed information

5. **EventKit Integration**
   - Extension creates EKEvent object with parsed data
   - EventKit framework handles calendar integration
   - Native iOS calendar editor opens with pre-filled event

6. **User Confirmation**
   - User reviews event in native iOS calendar interface
   - Can modify any fields as needed
   - Saves event to selected calendar

#### Technical Flow Diagram
```
[Text Selection] → [Share Sheet] → [Extension] → [API Call] → [EventKit] → [Event Saved]
     ↓               ↓             ↓            ↓            ↓           ↓
  User Action    iOS System    Our Extension  Parsing API  iOS Calendar User Calendar
```

#### Example Workflow
```
1. User selects: "Lunch with Sarah next Friday at 12:30 PM at Cafe Milano"
2. Taps Share → "Create Calendar Event"
3. Extension processes text → API returns:
   {
     "title": "Lunch with Sarah",
     "start_datetime": "2025-10-03T12:30:00",
     "location": "Cafe Milano",
     "confidence_score": 0.90
   }
4. iOS calendar editor opens with event details
5. User confirms and saves to calendar
```

### Workflow 3: Browser Extension Flow

#### Step-by-Step Process

1. **Text Selection**
   - User highlights text on any webpage (Gmail, calendar sites, etc.)
   - Right-click on selected text
   - Browser context menu appears

2. **Context Menu Action**
   - "Create Calendar Event" option appears in context menu
   - User clicks the option
   - Browser extension activates

3. **Extension Processing**
   - Background script captures selected text
   - Makes API call to parsing service
   - Processes response data

4. **Popup Interface**
   - Extension popup opens showing parsed event details
   - User can review and edit extracted information
   - Confidence scores displayed for each field

5. **Calendar Integration**
   - User selects preferred calendar service (Google, Outlook, etc.)
   - Extension generates calendar URL with event data
   - Opens calendar web app in new tab with pre-filled event

6. **Event Creation**
   - Calendar web app displays event creation form
   - User reviews and confirms event details
   - Event saved to selected calendar service

#### Technical Flow Diagram
```
[Text Selection] → [Context Menu] → [Background Script] → [API Call] → [Popup UI] → [Calendar URL] → [Event Saved]
     ↓               ↓               ↓                  ↓            ↓           ↓              ↓
  User Action    Browser System   Extension Service   Parsing API  Extension UI Calendar Web   User Calendar
```

#### Example Workflow
```
1. User selects: "Board meeting on Monday, Oct 6th at 10 AM in the executive conference room"
2. Right-click → "Create Calendar Event"
3. Extension processes text → API returns:
   {
     "title": "Board Meeting",
     "start_datetime": "2025-10-06T10:00:00",
     "location": "Executive Conference Room",
     "confidence_score": 0.92
   }
4. Extension popup shows parsed details with edit options
5. User selects Google Calendar → opens with pre-filled event
6. User confirms and saves in Google Calendar
```

## Platform-Specific Implementation Details

### Android Implementation

#### Key Components
- **MainActivity**: Handles ACTION_PROCESS_TEXT intents
- **ApiService**: Manages HTTP requests to parsing API
- **CalendarIntegration**: Uses CalendarContract for event creation
- **PermissionManager**: Handles calendar permissions

#### Required Permissions
```xml
<uses-permission android:name="android.permission.INTERNET" />
<uses-permission android:name="android.permission.WRITE_CALENDAR" />
<uses-permission android:name="android.permission.READ_CALENDAR" />
```

#### Intent Filter Configuration
```xml
<activity android:name=".MainActivity">
    <intent-filter>
        <action android:name="android.intent.action.PROCESS_TEXT" />
        <category android:name="android.intent.category.DEFAULT" />
        <data android:mimeType="text/plain" />
    </intent-filter>
</activity>
```

#### Error Handling
- Network connectivity checks
- API timeout handling (30 seconds)
- Calendar permission validation
- Graceful fallback for parsing failures

### iOS Implementation

#### Key Components
- **ShareExtension**: Handles text sharing from other apps
- **ApiService**: Manages URLSession requests to parsing API
- **EventKitManager**: Handles calendar integration
- **ErrorHandler**: Manages error states and user feedback

#### Required Capabilities
```xml
<key>NSCalendarsUsageDescription</key>
<string>Create calendar events from selected text</string>
<key>NSAppTransportSecurity</key>
<dict>
    <key>NSAllowsArbitraryLoads</key>
    <true/>
</dict>
```

#### Extension Configuration
```xml
<key>NSExtensionActivationRule</key>
<dict>
    <key>NSExtensionActivationSupportsText</key>
    <true/>
</dict>
```

#### Error Handling
- EventKit authorization checks
- Network reachability validation
- API response validation
- User-friendly error messages

### Browser Extension Implementation

#### Key Components
- **background.js**: Handles context menu and API calls
- **popup.js**: Manages popup interface and user interactions
- **content.js**: Handles text selection and page interaction
- **manifest.json**: Defines permissions and configuration

#### Required Permissions
```json
{
  "permissions": [
    "contextMenus",
    "activeTab",
    "storage",
    "https://your-api-domain.com/*"
  ]
}
```

#### Context Menu Setup
```javascript
chrome.contextMenus.create({
  id: "createCalendarEvent",
  title: "Create Calendar Event",
  contexts: ["selection"]
});
```

#### Error Handling
- CORS configuration validation
- API endpoint availability checks
- Calendar service integration errors
- User notification system

## API Integration Specifications

### Request Format
```json
POST /parse
Content-Type: application/json

{
  "text": "Selected text containing event information",
  "preferences": {
    "timezone": "America/Toronto",
    "date_format": "MM/DD/YYYY",
    "time_format": "12_hour"
  },
  "context": {
    "platform": "android|ios|browser",
    "app_version": "1.0.0",
    "user_id": "optional_user_identifier"
  }
}
```

### Response Format
```json
{
  "success": true,
  "parsed_event": {
    "title": "Event Title",
    "start_datetime": "2025-09-30T14:00:00",
    "end_datetime": "2025-09-30T15:00:00",
    "location": "Event Location",
    "description": "Original text with event details",
    "confidence_score": 0.85
  },
  "field_confidence": {
    "title": 0.8,
    "start_datetime": 0.9,
    "end_datetime": 0.7,
    "location": 0.85
  },
  "parsing_metadata": {
    "parsing_method": "llm_primary",
    "processing_time": 1.2,
    "llm_used": true,
    "suggestions": []
  }
}
```

### Error Response Format
```json
{
  "success": false,
  "error": "No event information found",
  "error_code": "NO_EVENT_DETECTED",
  "suggestions": [
    "Please include specific date and time information",
    "Consider adding a clear event title"
  ],
  "partial_extraction": {
    "detected_elements": ["time_reference"],
    "missing_elements": ["title", "specific_date"]
  }
}
```

## Testing Strategies

### Automated Integration Tests

#### Test Categories

1. **API Integration Tests**
   - Test parsing accuracy with various text formats
   - Validate response format consistency
   - Test error handling and edge cases
   - Performance and timeout testing

2. **Platform Integration Tests**
   - Android: Test intent handling and calendar integration
   - iOS: Test share extension and EventKit integration
   - Browser: Test context menu and popup functionality

3. **End-to-End Workflow Tests**
   - Simulate complete user workflows
   - Test cross-platform consistency
   - Validate calendar event creation
   - Test error recovery scenarios

#### Sample Test Cases

```javascript
// API Integration Test
describe('Parsing API Integration', () => {
  test('should parse explicit event information', async () => {
    const response = await parseText(
      "Team meeting on Monday, Sep 29th at 2:00 PM in Conference Room A"
    );
    
    expect(response.success).toBe(true);
    expect(response.parsed_event.title).toBe("Team Meeting");
    expect(response.parsed_event.location).toBe("Conference Room A");
    expect(response.field_confidence.title).toBeGreaterThan(0.8);
  });
  
  test('should handle ambiguous text gracefully', async () => {
    const response = await parseText("meeting tomorrow");
    
    expect(response.success).toBe(true);
    expect(response.parsed_event.confidence_score).toBeLessThan(0.6);
    expect(response.parsing_metadata.suggestions).toHaveLength(greaterThan(0));
  });
});

// Android Integration Test
describe('Android Calendar Integration', () => {
  test('should create calendar event from parsed data', async () => {
    const eventData = {
      title: "Test Meeting",
      start_datetime: "2025-09-30T14:00:00",
      location: "Test Location"
    };
    
    const result = await createCalendarEvent(eventData);
    expect(result.success).toBe(true);
    expect(result.event_id).toBeDefined();
  });
});
```

### Manual Testing Procedures

#### Pre-Release Testing Checklist

**Android Testing:**
- [ ] Test text selection in Gmail app
- [ ] Test text selection in Chrome browser
- [ ] Test text selection in Messages app
- [ ] Verify calendar permissions are requested
- [ ] Test with various text formats and languages
- [ ] Test error scenarios (no internet, invalid text)
- [ ] Verify calendar event appears in default calendar app

**iOS Testing:**
- [ ] Test share extension in Safari
- [ ] Test share extension in Mail app
- [ ] Test share extension in Messages app
- [ ] Verify calendar permissions are requested
- [ ] Test with various text formats and languages
- [ ] Test error scenarios (no internet, invalid text)
- [ ] Verify calendar event appears in Calendar app

**Browser Extension Testing:**
- [ ] Test context menu in Gmail web interface
- [ ] Test context menu on various websites
- [ ] Test popup interface functionality
- [ ] Test calendar service integration (Google, Outlook)
- [ ] Test with various text formats and languages
- [ ] Test error scenarios (API unavailable, CORS issues)
- [ ] Verify events appear in selected calendar service

#### User Acceptance Testing

**Scenario 1: Email Processing**
1. Open Gmail and find an email with meeting information
2. Select the relevant text containing date, time, and location
3. Use the appropriate method for your platform to create calendar event
4. Verify all information is extracted correctly
5. Confirm event appears in calendar

**Scenario 2: Complex Text Processing**
1. Find text with multiple dates or ambiguous information
2. Select and process the text
3. Verify system asks for clarification when needed
4. Edit any incorrect information
5. Confirm final event is accurate

**Scenario 3: Error Recovery**
1. Select text with minimal event information
2. Process the text and note low confidence scores
3. Use edit functionality to complete missing information
4. Verify event creation succeeds with manual corrections

### Performance Testing

#### Metrics to Monitor

1. **API Response Time**
   - Target: < 3 seconds for typical text
   - Maximum: < 10 seconds for complex text
   - Timeout: 30 seconds

2. **Parsing Accuracy**
   - Target: > 85% accuracy for well-formed text
   - Minimum: > 70% accuracy for typical user text
   - Confidence correlation: High confidence should correlate with accuracy

3. **User Completion Rate**
   - Target: > 90% of users complete the workflow
   - Measure: From text selection to calendar event creation
   - Track: Drop-off points in the workflow

#### Load Testing

```javascript
// Example load test configuration
const loadTest = {
  concurrent_users: 100,
  requests_per_second: 50,
  test_duration: '5m',
  text_samples: [
    "Meeting tomorrow at 2pm",
    "Conference call with John on Friday at 10 AM",
    "Lunch with the team next week at the downtown restaurant"
  ]
};
```

## Deployment and Monitoring

### Deployment Checklist

**API Deployment:**
- [ ] Deploy parsing service to production environment
- [ ] Configure CORS for all client platforms
- [ ] Set up monitoring and logging
- [ ] Configure rate limiting and security measures
- [ ] Test API endpoints from all platforms

**Mobile App Deployment:**
- [ ] Submit Android app to Google Play Store
- [ ] Submit iOS app to Apple App Store
- [ ] Configure app store listings and descriptions
- [ ] Set up crash reporting and analytics
- [ ] Test installation and permissions on various devices

**Browser Extension Deployment:**
- [ ] Submit extension to Chrome Web Store
- [ ] Submit extension to Firefox Add-ons
- [ ] Configure extension listings and descriptions
- [ ] Set up usage analytics and error reporting
- [ ] Test installation across different browsers

### Monitoring and Analytics

#### Key Metrics to Track

1. **Usage Metrics**
   - Number of text selections processed
   - Success rate of event creation
   - Platform distribution (Android/iOS/Browser)
   - Most common text formats processed

2. **Performance Metrics**
   - API response times
   - Parsing accuracy rates
   - Error rates by platform
   - User retention and engagement

3. **Quality Metrics**
   - Confidence score distributions
   - User edit rates (how often users modify extracted data)
   - Calendar integration success rates
   - User feedback and ratings

#### Monitoring Setup

```javascript
// Example monitoring configuration
const monitoring = {
  api_metrics: {
    response_time: 'track_percentiles',
    error_rate: 'alert_threshold_5_percent',
    throughput: 'requests_per_minute'
  },
  user_metrics: {
    completion_rate: 'track_funnel',
    accuracy_feedback: 'collect_ratings',
    platform_usage: 'track_distribution'
  },
  alerts: {
    api_down: 'immediate_notification',
    high_error_rate: 'threshold_alert',
    performance_degradation: 'trend_alert'
  }
};
```

This comprehensive documentation provides complete coverage of all user workflows, implementation details, testing strategies, and deployment considerations for the text-to-calendar event system across all supported platforms.