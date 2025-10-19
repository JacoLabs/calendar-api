# Calendar API Testing Guide

Welcome! Thank you for helping test the Calendar API. This guide will help you get started.

## 🌐 API Endpoint

**Base URL:** `https://calendar-api-wrxz.onrender.com`

**Health Check:** `https://calendar-api-wrxz.onrender.com/health`

**Web Interface:** `https://calendar-api-wrxz.onrender.com/static/test.html`

---

## 🧪 How to Test

### Option 1: Web Interface (Easiest!)

Visit: **https://calendar-api-wrxz.onrender.com/static/test.html**

1. Type or paste your event description
2. Click "Parse Event"
3. See the results instantly!

### Option 2: Command Line (cURL)
```bash
curl -X POST https://calendar-api-wrxz.onrender.com/parse \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Team meeting tomorrow at 2pm in Conference Room A",
    "timezone_offset": -480
  }'
```

### Option 3: Python Script
```python
import requests
from datetime import datetime

def test_parse(text):
    response = requests.post(
        'https://calendar-api-wrxz.onrender.com/parse',
        json={
            'text': text,
            'now': datetime.now().isoformat(),
            'timezone_offset': -480  # Adjust for your timezone
        },
        timeout=10
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ Parsed: {text}")
        print(f"   Title: {result.get('title')}")
        print(f"   Start: {result.get('start_datetime')}")
        print(f"   Confidence: {result.get('confidence_score'):.2f}")
    else:
        print(f"❌ Error: {response.status_code}")
    
    return response.json()

# Test examples
test_parse("Lunch with Sarah next Tuesday at noon")
test_parse("Doctor appointment Friday 3pm")
test_parse("Meeting tomorrow 10am for 2 hours")
```

### Option 4: JavaScript/Node.js
```javascript
async function testParse(text) {
  const response = await fetch('https://calendar-api-wrxz.onrender.com/parse', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      text: text,
      now: new Date().toISOString(),
      timezone_offset: new Date().getTimezoneOffset()
    })
  });
  
  const result = await response.json();
  console.log('✅ Parsed:', text);
  console.log('   Title:', result.title);
  console.log('   Start:', result.start_datetime);
  console.log('   Confidence:', result.confidence_score);
  
  return result;
}

// Test
testParse("Team standup Monday 9am");
```

---

## 🎯 Test Scenarios

Please test these categories and report what works/doesn't work:

### 1. Simple Time References
- [ ] "Meeting tomorrow at 2pm"
- [ ] "Lunch next Friday at noon"
- [ ] "Call mom tonight at 7"
- [ ] "Dentist appointment next week Wednesday 3pm"

### 2. Locations
- [ ] "Meeting at Starbucks on Main Street"
- [ ] "Dinner at The Italian Place downtown"
- [ ] "Conference in Room 301"

### 3. Durations
- [ ] "Meeting for 2 hours"
- [ ] "30 minute standup"
- [ ] "All day conference"

### 4. Complex Descriptions
- [ ] "Quarterly planning meeting with sales team to discuss Q4 goals"
- [ ] "Lunch meeting with potential client to discuss new project"
- [ ] "Team retrospective to review sprint and plan next iteration"

### 5. Edge Cases
- [ ] "Maybe coffee sometime next week"
- [ ] "Call Sarah"
- [ ] "Tomorrow"
- [ ] Very long descriptions (100+ words)

### 6. Dates & Times
- [ ] "October 25, 2025 at 3pm"
- [ ] "3:30 PM tomorrow"
- [ ] "Next Monday 9am"
- [ ] "In 2 hours"

---

## 📝 What to Report

For each test, please note:

1. **Input text** - What you tested
2. **Expected result** - What you hoped it would parse
3. **Actual result** - What it actually parsed
4. **Confidence score** - How confident the API was (0-1)
5. **Issues** - Anything wrong or unexpected

### Reporting Format
```markdown
**Test:** "Meeting tomorrow at 2pm in Room 301"

**Expected:**
- Title: Meeting
- Time: [Tomorrow's date] 2:00 PM
- Location: Room 301

**Actual:**
- Title: meeting
- Time: 2025-10-20 14:00:00
- Location: (missing)
- Confidence: 0.95

**Issue:** Location not detected
```

---

## 🐛 Where to Report Issues

### Option 1: GitHub Issues (Preferred)
Create an issue at: https://github.com/JacoLabs/calendar-api/issues

Use the template:
- Bug Report: For parsing errors or incorrect results
- Feature Request: For new capabilities
- Performance Issue: For slow responses

### Option 2: Discussion
Start a discussion: https://github.com/JacoLabs/calendar-api/discussions

---

## 🎁 Thank You!

Your feedback helps make this API better for everyone!

### What We're Looking For

✅ **Text patterns that work well**
✅ **Text patterns that fail or give wrong results**
✅ **Performance issues (slow responses)**
✅ **Feature requests**
✅ **Use cases we haven't thought of**

---

## 📊 API Response Format
```json
{
  "title": "meeting",
  "start_datetime": "2025-10-20T14:00:00",
  "end_datetime": "2025-10-20T15:00:00",
  "location": "Conference Room A",
  "confidence_score": 0.95,
  "parsing_path": "regex",
  "warnings": []
}
```

**Fields:**
- `title`: Event name/description
- `start_datetime`: When the event starts (ISO format)
- `end_datetime`: When it ends (if specified)
- `location`: Where it happens (if specified)
- `confidence_score`: How confident the parser is (0-1)
- `parsing_path`: Which method was used (regex/deterministic/llm)
- `warnings`: Any issues or ambiguities detected

---

## 🔧 Advanced Testing

### Testing with Different Timezones
```python
# PST (UTC-8)
timezone_offset = -480

# EST (UTC-5)
timezone_offset = -300

# UTC
timezone_offset = 0
```

### Testing with Specific "Now" Time
```python
{
  "text": "Meeting tomorrow at 2pm",
  "now": "2025-10-20T10:00:00",  # Pretend it's Oct 20 at 10am
  "timezone_offset": -480
}
```

---

## 💡 Tips for Better Results

1. **Be specific about times** - "2pm" is better than "afternoon"
2. **Include context** - "Meeting with Bob" is better than just "Meeting"
3. **Use common date formats** - "Next Monday" works better than "the Monday after this weekend"
4. **One event per request** - Don't try to parse multiple events in one text (yet!)

---

## 🚀 Current Limitations

- ❌ Multiple events in one text (coming soon!)
- ❌ Recurring events with complex patterns
- ❌ Relative times without dates ("in 30 minutes")
- ❌ Non-English languages (English only for now)

---

## 📈 Performance Expectations

- **Response time:** Usually < 2 seconds
- **Availability:** 99%+ uptime goal
- **Rate limits:** None currently (please be reasonable!)

---

## 🌟 Example Test Session
```python
# Good examples to try:
texts = [
    "Team standup tomorrow 9am",
    "Lunch with client next Friday at The Bistro",
    "Doctor appointment October 25th 3pm for 30 minutes",
    "All day conference next week Monday",
    "Quick call with Sarah sometime today",
]

for text in texts:
    result = test_parse(text)
    # Report your findings!
```

Happy testing! 🎉