# Calendar Event Creator - Beta Testing Program

**Welcome Beta Tester!** 🎉

Thank you for joining our beta testing program! You're helping us build the best AI-powered calendar event parser. This guide will get you up and running in minutes.

---

## 📋 Table of Contents
1. [Quick Start](#quick-start)
2. [What to Test](#what-to-test)
3. [Testing Platforms](#testing-platforms)
4. [How to Report Issues](#how-to-report-issues)
5. [Test Scenarios](#test-scenarios)
6. [FAQ](#faq)

---

## 🚀 Quick Start

### Web Interface (Recommended to Start)
**Easiest way to begin testing!**

1. **Open the Web Interface**: https://calendar-api-wrxz.onrender.com/static/test.html
2. **Type an event description**: "Meeting with Sarah tomorrow at 2pm"
3. **Click "Parse Event"**
4. **Review the results** - Check if title, date/time, and location are correct
5. **Report any issues** (see [How to Report](#how-to-report-issues))

**Quick Health Check**: https://calendar-api-wrxz.onrender.com/health
- If this shows "healthy", the API is running!

---

## 🎯 What to Test

### Priority Testing Areas

#### 1. **Date & Time Parsing** (High Priority)
Test if the system correctly understands:
- ✅ "tomorrow at 2pm"
- ✅ "next Friday 3:30pm"
- ✅ "October 25th at 3pm"
- ✅ "in 3 days at noon"
- ✅ "Monday morning 9am"

**What to check**: Is the date and time correct? Does it account for your timezone?

#### 2. **Event Titles** (High Priority)
Test if it extracts good titles:
- ✅ "Lunch with Sarah at The Bistro"
- ✅ "Doctor appointment next week"
- ✅ "Team standup meeting"
- ✅ "Call with client to discuss project"

**What to check**: Is the title clean? Does it remove date/time info from the title?

#### 3. **Location Detection** (Medium Priority)
Test location extraction:
- ✅ "Meeting at Starbucks on Main Street"
- ✅ "Conference in Room 301"
- ✅ "Dinner at 123 Oak Avenue"

**What to check**: Does it correctly identify the location?

#### 4. **Duration & End Times** (Medium Priority)
Test duration understanding:
- ✅ "Meeting for 2 hours"
- ✅ "30 minute standup"
- ✅ "Conference from 9am to 5pm"
- ✅ "All day event"

**What to check**: Does it calculate the end time correctly?

#### 5. **Complex Descriptions** (Low Priority)
Test with detailed descriptions:
- ✅ "Quarterly planning meeting with sales team to discuss Q4 goals and strategy for next year"
- ✅ "Lunch meeting with potential client Sarah Johnson at The Bistro downtown to discuss the new website project"

**What to check**: Does it handle longer text? Does it extract the essential information?

---

## 🖥️ Testing Platforms

### 1. **Web Interface** (Start Here!)
**URL**: https://calendar-api-wrxz.onrender.com/static/test.html

**How to test**:
1. Enter event text
2. Click "Parse Event"
3. Review results
4. Try creating the calendar event

**Best for**: Quick testing, understanding how it works

---

### 2. **Browser Extension** (Chrome/Edge)
**Status**: Ready for testing
**Location**: `browser-extension/` folder

**How to install**:
1. Download the repository or just the `browser-extension` folder
2. Open Chrome/Edge and go to: `chrome://extensions/`
3. Enable "Developer mode" (top right)
4. Click "Load unpacked"
5. Select the `browser-extension` folder
6. Look for the calendar icon in your toolbar!

**How to test**:
1. **Right-click method**: Select text on any webpage → Right-click → "Create calendar event"
2. **Extension popup**: Click the extension icon → Enter text → Click "Create Event"
3. **Share method**: Select text → Use browser's share menu

**What to test**:
- Does it work on different websites?
- Does the context menu appear?
- Does it successfully create calendar events?
- Does offline mode work (when API is down)?

**Supported browsers**: Chrome, Edge (Chromium), Brave
**Note**: Firefox has limited support

---

### 3. **Android App** (Native App)
**Status**: Ready for testing
**Requires**: Android 7.0+ (API 24+)

**How to install**:
1. **Option A - Build from source**:
   ```bash
   cd android
   ./gradlew assembleDebug
   adb install app/build/outputs/apk/debug/app-debug.apk
   ```

2. **Option B - Request APK**: Contact us for a pre-built APK file

**How to test**:
1. **Direct input**: Open app → Type event → Tap "Parse Event" → "Create Calendar Event"
2. **Text selection**: In ANY app, select text → "Create calendar event" from menu
3. **Share**: In ANY app, share text → Select "Calendar Event Creator"

**What to test**:
- Does it integrate with your calendar app (Google Calendar, Samsung, etc.)?
- Does text selection work in different apps (Chrome, Messages, Email)?
- Does share functionality work?
- How's the error handling?

**Three ways to create events**:
- 📝 Type directly in the app
- ✂️ Select text from any app
- 🔗 Share from other apps

---

### 4. **iOS App** (Native App)
**Status**: Ready for testing
**Requires**: iOS 15.0+, Xcode 15+ (to build)

**How to install**:
1. Download the repository
2. Open `ios/CalendarEventApp.xcodeproj` in Xcode
3. Connect your iPhone/iPad
4. Update the Bundle Identifier and Team settings
5. Build and run (⌘+R)

**How to test**:
1. **Main app**: Open app → Type event → Tap "Create Event" → "Add to Calendar"
2. **Share extension**: In Safari/Mail/Messages → Select text → Share → "Calendar Event Creator"

**What to test**:
- Does it integrate with iOS Calendar?
- Does the Share Extension work in different apps?
- Are calendar permissions handled properly?
- Does it work on both iPhone and iPad?

**Note**: Requires Apple Developer Account for device installation

---

### 5. **API Testing** (For Developers)

**Base URL**: https://calendar-api-wrxz.onrender.com

#### cURL Example:
```bash
curl -X POST https://calendar-api-wrxz.onrender.com/parse \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Team meeting tomorrow at 2pm in Conference Room A",
    "timezone": "America/New_York"
  }'
```

#### Python Example:
```python
import requests
from datetime import datetime

def parse_event(text):
    response = requests.post(
        'https://calendar-api-wrxz.onrender.com/parse',
        json={
            'text': text,
            'timezone': 'America/New_York',
            'now': datetime.now().isoformat()
        }
    )
    return response.json()

# Test
result = parse_event("Lunch with Sarah next Friday at noon")
print(f"Title: {result['title']}")
print(f"Start: {result['start_datetime']}")
print(f"Confidence: {result['confidence_score']}")
```

#### JavaScript Example:
```javascript
async function parseEvent(text) {
  const response = await fetch('https://calendar-api-wrxz.onrender.com/parse', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      text: text,
      timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
      now: new Date().toISOString()
    })
  });
  return await response.json();
}

// Test
parseEvent("Team standup Monday 9am").then(result => {
  console.log('Title:', result.title);
  console.log('Start:', result.start_datetime);
  console.log('Confidence:', result.confidence_score);
});
```

**API Endpoints**:
- `POST /parse` - Parse event text
- `GET /health` - Health check
- `GET /healthz` - Simple health probe
- `GET /docs` - Interactive API documentation
- `GET /cache/stats` - Cache performance metrics

---

## 🐛 How to Report Issues

### Quick Report (Recommended)
**Use this format for quick feedback**:

```markdown
**Platform**: [Web/Browser Extension/Android/iOS/API]

**Input**: "Meeting with Sarah tomorrow at 2pm at Starbucks"

**Expected**:
- Title: Meeting with Sarah
- Date: [Tomorrow's date]
- Time: 2:00 PM
- Location: Starbucks

**Actual**:
- Title: meeting
- Date: 2025-10-20 14:00:00
- Time: 2:00 PM
- Location: (missing)
- Confidence: 0.85

**Issue**: Location not detected, title missing proper capitalization
```

### Where to Report

#### Option 1: GitHub Issues (Preferred)
Create an issue at: **[Your GitHub Repo URL]**

**Issue Types**:
- 🐛 **Bug Report**: Something doesn't work correctly
- ✨ **Feature Request**: Suggest a new feature
- ⚡ **Performance Issue**: Slow response or timeout
- 📱 **Mobile Issue**: Android/iOS specific problems
- 🌐 **Browser Extension Issue**: Extension-specific problems

#### Option 2: Email Report
Send to: **[Your Email]**

Include:
- Platform you tested on
- Input text
- Expected vs. actual results
- Screenshots (if applicable)
- Error messages (if any)

#### Option 3: Feedback Form
**[Link to Google Form/Typeform if you create one]**

---

## 📝 Test Scenarios

### Scenario 1: Basic Events
**Goal**: Test simple event parsing

**Test cases**:
```
1. "Meeting tomorrow at 2pm"
2. "Lunch next Friday at noon"
3. "Call mom tonight at 7"
4. "Dentist appointment Wednesday 3pm"
5. "Coffee with Sarah in the morning"
```

**What to check**:
- ✅ Date calculated correctly
- ✅ Time parsed accurately
- ✅ Reasonable event title

---

### Scenario 2: Events with Locations
**Goal**: Test location detection

**Test cases**:
```
1. "Meeting at Starbucks on Main Street"
2. "Dinner at The Italian Restaurant downtown"
3. "Conference in Room 301"
4. "Lunch at 123 Oak Avenue"
5. "Appointment at Dr. Smith's office"
```

**What to check**:
- ✅ Location correctly extracted
- ✅ Location not confused with title
- ✅ Address formats recognized

---

### Scenario 3: Duration & Time Ranges
**Goal**: Test duration understanding

**Test cases**:
```
1. "Meeting for 2 hours"
2. "30 minute standup tomorrow 9am"
3. "Conference from 9am to 5pm"
4. "All day event next Monday"
5. "Quick 15 minute call"
```

**What to check**:
- ✅ End time calculated correctly
- ✅ Duration preserved
- ✅ All-day events handled properly

---

### Scenario 4: Complex Descriptions
**Goal**: Test with detailed event descriptions

**Test cases**:
```
1. "Quarterly planning meeting with sales team to discuss Q4 goals"
2. "Lunch meeting with potential client Sarah Johnson at The Bistro to discuss website project"
3. "Team retrospective to review last sprint and plan next iteration tomorrow at 3pm"
4. "Doctor appointment for annual checkup next Tuesday at 2pm at Downtown Medical Center"
5. "Conference call with international team about product launch Monday 10am for 90 minutes"
```

**What to check**:
- ✅ Essential info extracted (date, time, location)
- ✅ Title is concise and meaningful
- ✅ Handles long descriptions gracefully

---

### Scenario 5: Edge Cases (Challenge Mode!)
**Goal**: Find what breaks it

**Test cases**:
```
1. "Maybe coffee sometime next week"
2. "Call Sarah" (no time)
3. "Tomorrow" (no event info)
4. "Meeting at 25:00" (invalid time)
5. "Event on February 30th" (invalid date)
6. Very long text (200+ words)
7. Empty text
8. Just numbers: "123456"
9. Special characters: "Meeting @#$% tomorrow"
10. Multiple events: "Lunch at noon and dinner at 7pm"
```

**What to check**:
- ✅ Graceful error handling
- ✅ Confidence scores reflect uncertainty
- ✅ Warnings for ambiguous input
- ✅ No crashes or freezes

---

### Scenario 6: Date Format Variations
**Goal**: Test different date formats

**Test cases**:
```
1. "Meeting on 10/25/2025"
2. "Event October 25, 2025"
3. "Appointment 25-10-2025"
4. "Meeting next Monday"
5. "Call in 3 days"
6. "Event this Friday"
7. "Meeting the day after tomorrow"
```

**What to check**:
- ✅ Different formats recognized
- ✅ Relative dates calculated correctly
- ✅ Timezone handling proper

---

### Scenario 7: Time Format Variations
**Goal**: Test different time formats

**Test cases**:
```
1. "Meeting at 2pm"
2. "Event at 14:00"
3. "Call at 2:30 PM"
4. "Meeting at 2"
5. "Event at 14h30"
6. "Call at half past two"
7. "Meeting in the evening"
```

**What to check**:
- ✅ 12-hour and 24-hour formats
- ✅ AM/PM handling
- ✅ Minutes parsed correctly

---

## 🌟 What Makes a Great Bug Report

### ✅ Good Example:
```markdown
**Platform**: Android App
**Device**: Samsung Galaxy S21, Android 13

**Input**: "Lunch with Sarah next Friday at The Bistro downtown"

**Expected**:
- Title: Lunch with Sarah
- Date: 2025-10-25 (next Friday)
- Time: 12:00 PM (assuming noon)
- Location: The Bistro downtown

**Actual**:
- Title: Lunch with Sarah next Friday
- Date: 2025-10-25 12:00:00
- Time: 12:00 PM
- Location: (empty)
- Confidence: 0.72

**Issue**:
1. Location "The Bistro downtown" not detected
2. Title includes "next Friday" which should be removed
3. Confidence is lower than expected for straightforward event

**Screenshots**: [Attached]
```

### ❌ Poor Example:
```markdown
"It doesn't work"
```

**Why it's poor**: Not specific, no details, can't reproduce

---

## 💡 Testing Tips

### 1. **Test in Your Context**
Use real event descriptions from your daily life:
- Your actual meeting invites
- Calendar reminders you receive
- Text messages with event info
- Email event descriptions

### 2. **Vary Your Tests**
- Try morning, afternoon, evening events
- Test different days (today, tomorrow, next week, specific dates)
- Use different locations (restaurants, addresses, room names)
- Mix formal and informal language

### 3. **Check Edge Cases**
- What if you don't specify a time?
- What if you only specify a date?
- What about very vague descriptions?
- How does it handle typos?

### 4. **Compare Across Platforms**
Test the same event text on:
- Web interface
- Browser extension
- Mobile apps (if available)

Do they give consistent results?

### 5. **Pay Attention to Confidence Scores**
- **0.9-1.0**: Very confident (should be very accurate)
- **0.7-0.9**: Confident (generally reliable)
- **0.5-0.7**: Moderate confidence (check carefully)
- **0.0-0.5**: Low confidence (likely issues)

Report when confidence doesn't match accuracy!

---

## ❓ FAQ

### Q: How do I know if the API is working?
**A**: Check the health endpoint: https://calendar-api-wrxz.onrender.com/health
If it returns `{"status":"healthy"}`, it's working!

### Q: What timezone should I use?
**A**: The system detects your timezone automatically in most cases. For API testing, you can specify your timezone explicitly:
- `"timezone": "America/New_York"` (EST/EDT)
- `"timezone": "America/Los_Angeles"` (PST/PDT)
- `"timezone": "Europe/London"` (GMT/BST)
- `"timezone": "UTC"` (UTC)

### Q: How long should responses take?
**A**: Typically 1-3 seconds. If it takes longer than 10 seconds, please report it!

### Q: Can I test with non-English text?
**A**: Currently only English is supported, but international date formats should work.

### Q: What if I find a security issue?
**A**: Please email [Your Email] directly instead of posting publicly.

### Q: Can I test the mobile apps without installing?
**A**: Start with the web interface! It uses the same parsing API. For full mobile testing, installation is required.

### Q: Do I need to test everything?
**A**: No! Test what interests you and what fits your workflow. Even testing one scenario helps!

### Q: How often should I test?
**A**: Test whenever convenient! We'll notify you when major updates are released.

### Q: Will my data be stored?
**A**: No! All parsing is stateless. We don't store your event descriptions.

### Q: Can I suggest new features?
**A**: Absolutely! Use the "Feature Request" issue type or mention it in your feedback.

---

## 🎁 Thank You!

Your testing helps us build a better product. We really appreciate your time and feedback!

### What Happens Next?

1. **We review all feedback** - Every report is read and considered
2. **Issues are prioritized** - Critical bugs get fixed first
3. **Updates are released** - You'll be notified of improvements
4. **Your input shapes the product** - Feature requests influence our roadmap

### Stay Connected

- **Updates**: Watch the GitHub repository for updates
- **Questions**: Open a discussion or issue on GitHub
- **Direct contact**: [Your Email]

---

## 📚 Additional Resources

- **Quick Start Guide**: [quickstart.md](quickstart.md)
- **Testing Guide**: [testing.md](testing.md)
- **Mobile Integration**: [MOBILE_INTEGRATION.md](MOBILE_INTEGRATION.md)
- **API Documentation**: https://calendar-api-wrxz.onrender.com/docs
- **Changelog**: [CHANGELOG.md](CHANGELOG.md)

---

**Happy Testing!** 🚀🧪

*Last Updated: October 19, 2025*
