# Text-to-Calendar Event User Guide

## Getting Started

The Text-to-Calendar Event system automatically creates calendar events from highlighted text. Simply select text containing event information and choose "Create Calendar Event" to get started.

### Quick Start

1. **Highlight text** containing event information (date, time, title, location)
2. **Right-click** and select "Create Calendar Event" (or use the browser extension/mobile app)
3. **Review** the extracted information in the preview
4. **Edit** any fields that need correction
5. **Confirm** to create the calendar event

## Understanding Confidence Scoring

### What Confidence Scores Mean

The system provides confidence scores to help you understand how certain it is about the extracted information:

- **🟢 High (80-100%)**: Very confident, likely accurate
- **🟡 Medium (40-79%)**: Moderately confident, please review
- **🔴 Low (0-39%)**: Uncertain, requires your attention

### Confidence Score Examples

```
✅ "Meeting on Monday, September 29th at 2:00 PM" 
   → Confidence: 95% (explicit date and time)

⚠️ "Call with John next week sometime"
   → Confidence: 45% (vague timing)

❌ "Important thing tomorrow"
   → Confidence: 20% (missing details)
```

### How to Interpret Scores

#### Field-Level Confidence
Each part of your event gets its own confidence score:

- **Title**: How certain we are about the event name
- **Date/Time**: How confident we are about when it happens  
- **Location**: How sure we are about where it takes place

#### Overall Confidence
The overall score combines all fields, weighted by importance:
- Title and date/time are most important
- Location is helpful but optional
- Description adds context but doesn't affect the score much

## Optimal Text Selection and Formatting

### What Makes Good Text for Parsing

#### ✅ Excellent Examples
```
"Team standup meeting on Monday, September 29th at 9:00 AM in Conference Room A"
→ Has everything: clear title, specific date, exact time, precise location

"Lunch with Sarah tomorrow at 12:30 PM at Cafe Milano downtown"
→ Clear purpose, relative date, specific time, named location

"Annual planning session next Friday from 9 AM to 5 PM"
→ Descriptive title, clear date reference, time range
```

#### ⚠️ Okay Examples (will work but may need review)
```
"Meeting tomorrow at 2pm"
→ Missing: title details, location
→ System will: ask you to add a better title

"Call with the team next week"
→ Missing: specific day, time
→ System will: ask for clarification on timing

"Lunch at the usual place on Friday"
→ Missing: specific location, time
→ System will: prompt for location and time details
```

#### ❌ Poor Examples (likely to fail or need lots of editing)
```
"Important thing soon"
→ Too vague: no specific date, time, or clear purpose

"Meet me there"
→ Missing: when, where, what for

"Don't forget about tomorrow"
→ No event details, just a reminder
```

### Text Selection Best Practices

#### Select Complete Information
- **Include context**: Select full sentences, not just fragments
- **Get the details**: Make sure date, time, and purpose are included
- **Capture location**: Include location information when mentioned

#### Examples of Good Selection
```
Full email paragraph:
"Hi team, we're scheduling our quarterly review meeting for next Thursday, October 3rd at 2:00 PM in the main conference room. Please bring your project updates."

✅ Select the whole sentence with event details
❌ Don't select just "quarterly review meeting"
```

#### Multi-Paragraph Selection
When event information spans multiple paragraphs, select all relevant text:

```
Email example:
"Thanks for your interest in our product demo.

We'd like to schedule a presentation for next Tuesday, September 30th at 10:00 AM. The session will be held at our downtown office at 123 Main Street.

Please let us know if this works for your schedule."

✅ Select all three paragraphs for complete context
```

## Handling Ambiguous Text

### Common Ambiguity Types

#### Date Ambiguities
**Problem**: "Meeting on 3/4/2025"
- Could be March 4th or April 3rd
- **Solution**: The system will ask which format you prefer (MM/DD or DD/MM)

**Problem**: "Call next Monday"
- Could be this coming Monday or the Monday after
- **Solution**: System assumes the next occurrence; you can edit if wrong

#### Time Ambiguities  
**Problem**: "Meeting at 9"
- Could be 9 AM or 9 PM
- **Solution**: System assumes business hours (9 AM); edit if needed

**Problem**: "Lunch after the meeting"
- Depends on when the meeting is
- **Solution**: System will prompt for specific time

#### Location Ambiguities
**Problem**: "Meet at the office"
- Which office? Main office? Your office?
- **Solution**: System extracts "the office"; you can specify which one

### Resolving Ambiguities

#### When the System Asks for Clarification
The system will present options when it finds multiple valid interpretations:

```
"Meeting on 3/4/2025 at 2pm"

📅 Which date format?
○ March 4, 2025 (MM/DD/YYYY)
○ April 3, 2025 (DD/MM/YYYY)

🕐 Which time?
○ 2:00 PM (afternoon)
○ 2:00 AM (early morning)
```

#### When You Need to Edit
For low-confidence extractions, review and edit:

```
Extracted: "Meeting" (confidence: 30%)
Your edit: "Quarterly Planning Meeting"

Extracted: "next week" (confidence: 40%)  
Your edit: "Tuesday, October 1st"
```

## High-Quality vs Low-Quality Parsing Results

### High-Quality Results (80%+ confidence)

#### Characteristics
- ✅ Specific dates and times
- ✅ Clear, descriptive titles
- ✅ Precise locations
- ✅ Complete information

#### Example
```
Input: "Board meeting on Wednesday, October 2nd at 10:00 AM in the executive boardroom"

Output:
📅 Title: "Board Meeting" (95% confidence)
📅 Date: October 2, 2025 (98% confidence)  
🕐 Time: 10:00 AM - 11:00 AM (95% confidence)
📍 Location: "Executive Boardroom" (90% confidence)
Overall: 94% confidence ✅
```

### Medium-Quality Results (40-79% confidence)

#### Characteristics
- ⚠️ Some missing details
- ⚠️ Relative dates/times
- ⚠️ Generic titles
- ⚠️ Vague locations

#### Example
```
Input: "Team sync tomorrow afternoon"

Output:
📅 Title: "Team Sync" (75% confidence)
📅 Date: September 30, 2025 (85% confidence)
🕐 Time: 2:00 PM - 3:00 PM (60% confidence) ⚠️
📍 Location: (none found)
Overall: 65% confidence ⚠️

Suggestions:
- Confirm the afternoon time is correct
- Add a location if needed
```

### Low-Quality Results (0-39% confidence)

#### Characteristics
- ❌ Vague or missing information
- ❌ Unclear timing
- ❌ Generic or poor titles
- ❌ No location information

#### Example
```
Input: "Don't forget about the thing"

Output:
📅 Title: "The Thing" (20% confidence) ❌
📅 Date: (not found) ❌
🕐 Time: (not found) ❌
📍 Location: (not found)
Overall: 15% confidence ❌

Suggestions:
- Please provide a clear event title
- Specify when this event occurs
- Add location information if applicable
```

## System Limitations and Workarounds

### Current Limitations

#### Language Support
- **Limitation**: Currently optimized for English text
- **Workaround**: Use English keywords for dates/times when possible

#### Complex Scheduling
- **Limitation**: Doesn't handle recurring events or complex scheduling rules
- **Workaround**: Create individual events for each occurrence

#### Context Dependencies
- **Limitation**: May not understand company-specific terms or abbreviations
- **Workaround**: Use full names and standard terminology

#### Multiple Events
- **Limitation**: Works best with single events per text selection
- **Workaround**: Select text for one event at a time

### Known Issues and Workarounds

#### Issue: Time Zone Handling
**Problem**: System assumes local time zone
**Workaround**: Specify time zone in text ("2 PM EST") or edit after creation

#### Issue: All-Day Events
**Problem**: May assign specific times to all-day events
**Workaround**: Edit the event to remove times and mark as all-day

#### Issue: Recurring Events
**Problem**: Creates single occurrence only
**Workaround**: Create the first event, then set up recurrence in your calendar app

#### Issue: Very Long Text
**Problem**: Performance may slow with very large text blocks
**Workaround**: Select only the relevant paragraphs containing event information

### Working Around Limitations

#### For Better Results
1. **Be specific**: Use exact dates, times, and locations
2. **Use standard formats**: Stick to common date/time formats
3. **Include context**: Provide enough information for understanding
4. **Review results**: Always check extracted information before confirming

#### When the System Struggles
1. **Try simpler text**: Remove extra information and focus on event details
2. **Use explicit formats**: "September 29, 2025 at 2:00 PM" instead of "next week sometime"
3. **Break it down**: For complex events, provide information step by step
4. **Manual editing**: Use the edit feature to correct any mistakes

## Frequently Asked Questions

### General Usage

**Q: What types of text work best?**
A: Email invitations, calendar descriptions, meeting notes, and any text with clear date, time, and event information.

**Q: Can I use this with any calendar app?**
A: Yes, the system creates standard calendar events that work with Google Calendar, Outlook, Apple Calendar, and others.

**Q: Does it work offline?**
A: The core parsing requires an internet connection, but once events are created, they're stored locally in your calendar.

### Parsing and Accuracy

**Q: Why is my confidence score low?**
A: Low scores usually mean the text is vague or missing key information. Try including more specific details about when and what the event is.

**Q: Can I improve the parsing accuracy?**
A: Yes! Use specific dates ("Monday, September 29th" instead of "next week"), exact times ("2:00 PM" instead of "afternoon"), and clear event titles.

**Q: What if the system gets something wrong?**
A: You can edit any field before creating the event. The system is designed to be a starting point that you can refine.

### Technical Questions

**Q: How does the confidence scoring work?**
A: The system analyzes how explicit and unambiguous your text is. Specific dates and times get higher scores than vague references.

**Q: Why does processing sometimes take a few seconds?**
A: The system uses advanced AI to understand natural language, which requires some processing time for accuracy.

**Q: Can I batch process multiple events?**
A: Currently, the system works best with one event at a time. For multiple events, select and process each one separately.

### Privacy and Security

**Q: Is my text data stored or shared?**
A: Text is processed locally when possible. Check your specific implementation's privacy policy for details.

**Q: Can I use this for sensitive information?**
A: The system is designed for general calendar events. For highly sensitive information, review your organization's data handling policies.

### Troubleshooting

**Q: What if no event information is found?**
A: Try selecting more text with clearer event details, or use more explicit language about dates, times, and event purposes.

**Q: The location is wrong or missing. What should I do?**
A: Edit the location field manually, or try selecting text that includes clearer location indicators like "at [place]" or "in [room]".

**Q: Can I save my preferences for date formats?**
A: Yes, most implementations allow you to set preferences for date format (MM/DD vs DD/MM), time format (12-hour vs 24-hour), and default duration.

## Tips for Power Users

### Advanced Text Selection

#### Email Processing
- Select the entire invitation paragraph, not just the summary
- Include RSVP information and attendee lists for context
- Capture any agenda or preparation notes

#### Meeting Notes
- Select the scheduling portion of meeting notes
- Include action items that mention deadlines
- Capture follow-up meeting references

#### Document Processing
- Look for scheduling sections in longer documents
- Select complete sentences rather than fragments
- Include any location or dial-in information

### Optimization Strategies

#### For Recurring Use
1. **Learn the patterns**: Notice what text formats work best for your use cases
2. **Standardize input**: Encourage consistent formatting in your team's communications
3. **Use templates**: Create standard formats for common event types

#### For Team Adoption
1. **Share best practices**: Teach colleagues how to write "parser-friendly" text
2. **Create examples**: Maintain a list of good text examples for reference
3. **Feedback loop**: Report parsing issues to help improve the system

### Integration with Workflows

#### Email Workflows
- Use with email scheduling assistants
- Process meeting invitations quickly
- Extract events from newsletter announcements

#### Project Management
- Convert project deadlines to calendar events
- Process milestone notifications
- Create events from task due dates

#### Personal Productivity
- Process social event invitations
- Convert appointment confirmations
- Create events from travel itineraries

This user guide provides comprehensive guidance for getting the best results from the text-to-calendar event system while understanding its capabilities and limitations.