# Calendar API Quick Start

Get parsing calendar events in 5 minutes!

## 🚀 Fastest Way to Test

### 1. Use the Web Interface

Visit: **https://calendar-api-wrxz.onrender.com/static/test.html**

Type something like:
- "Meeting tomorrow at 2pm"
- "Lunch with Sarah next Friday at noon"
- "Doctor appointment October 25th at 3pm"

Click "Parse Event" and see the magic! ✨

---

### 2. Or Use cURL
```bash
# Simple health check
curl https://calendar-api-wrxz.onrender.com/health
```

Should return: `{"status":"healthy",...}`
```bash
# Parse an event
curl -X POST https://calendar-api-wrxz.onrender.com/parse \
  -H "Content-Type: application/json" \
  -d '{"text": "Coffee with Jane tomorrow at 10am", "timezone_offset": 0}'
```

You'll get:
```json
{
  "title": "coffee",
  "start_datetime": "2025-10-20T10:00:00",
  "confidence_score": 0.98
}
```

---

## 🎯 Try These Examples
```bash
# Meeting with location
curl -X POST https://calendar-api-wrxz.onrender.com/parse \
  -H "Content-Type: application/json" \
  -d '{"text": "Team standup tomorrow 9am in Room 301", "timezone_offset": -480}'

# Event with duration
curl -X POST https://calendar-api-wrxz.onrender.com/parse \
  -H "Content-Type: application/json" \
  -d '{"text": "Client call Friday 2pm for 1 hour", "timezone_offset": -480}'

# Complex event
curl -X POST https://calendar-api-wrxz.onrender.com/parse \
  -H "Content-Type: application/json" \
  -d '{"text": "Quarterly planning meeting next Monday 10am to discuss Q4 goals", "timezone_offset": -480}'
```

---

## 📱 Python Quick Start
```python
import requests
from datetime import datetime

def parse_event(text):
    response = requests.post(
        'https://calendar-api-wrxz.onrender.com/parse',
        json={
            'text': text,
            'now': datetime.now().isoformat(),
            'timezone_offset': -480
        }
    )
    return response.json()

# Try it!
result = parse_event("Team meeting tomorrow at 3pm")
print(f"Title: {result['title']}")
print(f"Start: {result['start_datetime']}")
print(f"Confidence: {result['confidence_score']}")
```

---

## 🌐 JavaScript Quick Start
```javascript
async function parseEvent(text) {
  const res = await fetch('https://calendar-api-wrxz.onrender.com/parse', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      text: text,
      now: new Date().toISOString(),
      timezone_offset: new Date().getTimezoneOffset()
    })
  });
  return await res.json();
}

// Try it!
parseEvent("Lunch next Friday at noon").then(result => {
  console.log('Title:', result.title);
  console.log('Start:', result.start_datetime);
  console.log('Confidence:', result.confidence_score);
});
```

---

## 📖 Next Steps

- **Full Testing Guide:** [TESTING.md](TESTING.md)
- **Report Bugs:** [GitHub Issues](https://github.com/JacoLabs/calendar-api/issues)
- **API Docs:** Coming soon!

---

## 🎯 What to Test

Try these patterns and let us know what works/doesn't work:

✅ **Times:** "tomorrow at 2pm", "next Friday 3:30pm", "Monday 9am"
✅ **Dates:** "October 25th", "next week Wednesday", "in 3 days"
✅ **Locations:** "at Starbucks", "in Conference Room A", "downtown"
✅ **Durations:** "for 2 hours", "30 minute meeting", "all day"
✅ **Complex:** "Quarterly review meeting with team to discuss Q4 goals next Monday at 10am in the boardroom"

---

## 🐛 Found a Bug?

Report it here: https://github.com/JacoLabs/calendar-api/issues

Include:
- The text you tried to parse
- What you expected
- What you got
- Confidence score

---

## ❓ Questions?

Check the [full testing guide](TESTING.md) or open an issue!

Happy parsing! 🚀