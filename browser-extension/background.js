// Background script using our hybrid regex/LLM parsing system
// Dynamic API URL based on environment
const API_BASE_URL = (() => {
  // Try production first, fallback to local development
  const PRODUCTION_URL = 'https://calendar-api-wrxz.onrender.com';
  const DEVELOPMENT_URL = 'http://localhost:5000';
  
  // In production extension, use production URL
  // In development, try local first
  return PRODUCTION_URL;
})();

chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({
    id: 'createCalendarEvent',
    title: 'Create calendar event',
    contexts: ['selection']
  });
});

// Handle context menu clicks with enhanced API features
chrome.contextMenus.onClicked.addListener(async (info, tab) => {
  if (info.menuItemId === 'createCalendarEvent' && info.selectionText) {
    try {
      // Use enhanced parsing with performance optimizations
      const parseResult = await parseTextWithHybridSystem(info.selectionText, { mode: 'audit' });
      
      // Log performance metrics for debugging
      if (parseResult.processing_time_ms) {
        console.log(`Parsing completed in ${parseResult.processing_time_ms}ms`);
      }
      
      // Create Google Calendar URL with parsed data
      const calendarUrl = buildGoogleCalendarUrl(parseResult);
      
      // Open calendar
      chrome.tabs.create({ url: calendarUrl });
      
    } catch (error) {
      console.error('Enhanced parsing failed:', error);
      
      // Try partial parsing for essential fields only
      try {
        const partialResult = await parseTextWithHybridSystem(info.selectionText, { 
          fields: ['title', 'start_datetime', 'end_datetime'] 
        });
        
        const calendarUrl = buildGoogleCalendarUrl(partialResult);
        chrome.tabs.create({ url: calendarUrl });
        
      } catch (partialError) {
        console.error('Partial parsing also failed:', partialError);
        
        // Final fallback to simple parsing
        const title = info.selectionText.substring(0, 50);
        const params = new URLSearchParams();
        params.set('action', 'TEMPLATE');
        params.set('text', title);
        
        const calendarUrl = `https://calendar.google.com/calendar/render?${params.toString()}`;
        chrome.tabs.create({ url: calendarUrl });
      }
    }
  }
});

// Parse text using enhanced API with smart fallback between production and development
async function parseTextWithHybridSystem(text, options = {}) {
  const urls = [
    'https://calendar-api-wrxz.onrender.com',
    'http://localhost:5000'
  ];
  
  // Try each URL in order
  for (let i = 0; i < urls.length; i++) {
    const baseUrl = urls[i];
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 10000); // 10 second timeout per attempt
    
    try {
      console.log(`Attempting API call to: ${baseUrl}`);
      
      // Build URL with query parameters for enhanced features
      const url = new URL(`${baseUrl}/parse`);
      if (options.mode === 'audit') {
        url.searchParams.set('mode', 'audit');
      }
      if (options.fields && options.fields.length > 0) {
        url.searchParams.set('fields', options.fields.join(','));
      }
      
      const response = await fetch(url.toString(), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
          'User-Agent': 'CalendarEventExtension/2.0'
        },
        body: JSON.stringify({
          text: text,
          timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
          now: new Date().toISOString(),
          use_llm_enhancement: true
        }),
        signal: controller.signal
      });
      
      clearTimeout(timeoutId);
      
      if (!response.ok) {
        // Try next URL if this one fails
        const errorData = await response.json().catch(() => ({}));
        const errorMessage = errorData.error?.message || `API error: ${response.status}`;
        console.warn(`API ${baseUrl} failed: ${errorMessage}`);
        continue;
      }
      
      const result = await response.json();
      console.log(`Successfully parsed using: ${baseUrl}`);
      
      // Handle enhanced API response format
      if (result.field_results) {
        console.log('Field confidence scores:', result.field_results);
      }
      
      if (result.parsing_path) {
        console.log('Parsing method used:', result.parsing_path);
      }
      
      if (result.cache_hit) {
        console.log('Result served from cache');
      }
      
      // Log warnings for debugging
      if (result.warnings && result.warnings.length > 0) {
        console.warn('Parsing warnings:', result.warnings);
      }
      
      return result;
      
    } catch (error) {
      clearTimeout(timeoutId);
      
      if (error.name === 'AbortError') {
        console.warn(`API ${baseUrl} timed out after 10 seconds`);
      } else {
        console.warn(`API ${baseUrl} failed:`, error);
      }
      
      // Continue to next URL or fallback
      if (i === urls.length - 1) {
        console.warn('All API endpoints failed, using local fallback');
        return parseTextLocally(text);
      }
    }
  }
  
  // This shouldn't be reached, but just in case
  return parseTextLocally(text);
}

// Improved local fallback parser for when API is unavailable or slow
function parseTextLocally(text) {
  const result = {
    title: '',
    start_datetime: null,
    end_datetime: null,
    location: null,
    description: text,
    all_day: false,
    confidence_score: 0.7  // Start with reasonable confidence for local parsing
  };
  
  // Clean up text first - remove extra whitespace and normalize
  const cleanText = text.replace(/\s+/g, ' ').trim();
  
  // Handle structured text with DATE/TIME/LOCATION keywords
  if (/\b(DATE|TIME|LOCATION|WHEN|WHERE)\b/i.test(cleanText)) {
    // Extract title before any structural keywords
    const titleMatch = cleanText.match(/^(.+?)(?:\s+(?:DATE|TIME|LOCATION|WHEN|WHERE)\b)/i);
    if (titleMatch) {
      result.title = titleMatch[1].trim();
    }
  } else {
    // Extract title (first part before time/date/location indicators)
    const titleMatch = cleanText.match(/^([^,]+?)(?:\s+(?:at|on|in|@|tomorrow|today|next|this|from|to)\s|$)/i);
    if (titleMatch) {
      result.title = titleMatch[1].trim();
    } else {
      // Fallback: use first few words or up to first punctuation
      const words = cleanText.split(/\s+/);
      if (words.length <= 4) {
        result.title = cleanText;
      } else {
        result.title = words.slice(0, 4).join(' ');
      }
    }
  }
  
  // Enhanced time parsing with more patterns
  const timePatterns = [
    /\b(\d{1,2}):(\d{2})\s*(am|pm)\b/i,
    /\b(\d{1,2})\s*(am|pm)\b/i,
    /\b(\d{1,2}):(\d{2})\b/,
    /\b(\d{1,2})(?::00)?\s*(?:o'?clock)\b/i
  ];
  
  let timeMatch = null;
  for (const pattern of timePatterns) {
    timeMatch = cleanText.match(pattern);
    if (timeMatch) break;
  }
  
  // Enhanced date parsing
  const now = new Date();
  let targetDate = new Date(now);
  
  // Relative date patterns
  if (/\btomorrow\b/i.test(cleanText)) {
    targetDate.setDate(now.getDate() + 1);
  } else if (/\btoday\b/i.test(cleanText)) {
    // Keep current date
  } else if (/\bnext week\b/i.test(cleanText)) {
    targetDate.setDate(now.getDate() + 7);
  } else if (/\bnext\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)/i.test(cleanText)) {
    const dayMatch = cleanText.match(/\bnext\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)/i);
    if (dayMatch) {
      const targetDay = ['sunday', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday']
        .indexOf(dayMatch[1].toLowerCase());
      const currentDay = now.getDay();
      let daysToAdd = targetDay - currentDay;
      if (daysToAdd <= 0) daysToAdd += 7;
      targetDate.setDate(now.getDate() + daysToAdd);
    }
  } else if (/\b(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b/i.test(cleanText)) {
    // This week's day
    const dayMatch = cleanText.match(/\b(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b/i);
    if (dayMatch) {
      const targetDay = ['sunday', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday']
        .indexOf(dayMatch[1].toLowerCase());
      const currentDay = now.getDay();
      let daysToAdd = targetDay - currentDay;
      if (daysToAdd < 0) daysToAdd += 7; // Next week if day has passed
      targetDate.setDate(now.getDate() + daysToAdd);
    }
  }
  
  // Set time if found
  if (timeMatch) {
    let hours = parseInt(timeMatch[1]);
    const minutes = timeMatch[2] ? parseInt(timeMatch[2]) : 0;
    const ampm = timeMatch[3];
    
    if (ampm && ampm.toLowerCase() === 'pm' && hours !== 12) {
      hours += 12;
    } else if (ampm && ampm.toLowerCase() === 'am' && hours === 12) {
      hours = 0;
    } else if (!ampm && hours < 8) {
      // Assume PM for times like "2" or "3" (likely afternoon meetings)
      hours += 12;
    }
    
    targetDate.setHours(hours, minutes, 0, 0);
    result.start_datetime = targetDate.toISOString();
    
    // Set end time (1 hour later)
    const endDate = new Date(targetDate);
    endDate.setHours(endDate.getHours() + 1);
    result.end_datetime = endDate.toISOString();
  }
  
  // Enhanced location extraction
  const locationPatterns = [
    /\b(?:at|in|@)\s+([^,\n]+?)(?:\s+(?:at|on|from|to|tomorrow|today|next)\s|\s*$)/i,
    /\blocation:\s*([^,\n]+)/i,
    /\bwhere:\s*([^,\n]+)/i,
    /\b(?:room|office|building|hall|center|street|avenue|drive)\s+([^,\n]+?)(?:\s|$)/i
  ];
  
  for (const pattern of locationPatterns) {
    const locationMatch = cleanText.match(pattern);
    if (locationMatch) {
      result.location = locationMatch[1].trim();
      // Clean up location - remove trailing time/date info
      result.location = result.location.replace(/\s+(?:at|on|from|to|tomorrow|today|next)\s.*$/i, '');
      break;
    }
  }
  
  // Clean up title - remove any remaining structural keywords
  if (result.title) {
    result.title = result.title.replace(/\s+(?:DATE|TIME|LOCATION|WHEN|WHERE).*$/i, '').trim();
    // Remove trailing punctuation
    result.title = result.title.replace(/[,;:]$/, '').trim();
  }
  
  // Ensure we have at least a basic title
  if (!result.title || result.title.length < 2) {
    const words = cleanText.split(/\s+/);
    result.title = words.slice(0, Math.min(3, words.length)).join(' ');
  }
  
  // Adjust confidence based on what we successfully parsed
  let confidence = 0.4; // Base confidence for local parsing
  
  if (result.title && result.title.length > 2) confidence += 0.2;
  if (result.start_datetime) confidence += 0.3;
  if (result.location) confidence += 0.1;
  
  result.confidence_score = Math.min(confidence, 0.8); // Cap at 80% for local parsing
  
  return result;
}

// Build Google Calendar URL with parsed event data
function buildGoogleCalendarUrl(parseResult) {
  const params = new URLSearchParams();
  params.set('action', 'TEMPLATE');
  
  if (parseResult.title) {
    params.set('text', parseResult.title);
  }
  
  if (parseResult.start_datetime) {
    const startDate = new Date(parseResult.start_datetime);
    const endDate = parseResult.end_datetime ? 
      new Date(parseResult.end_datetime) : 
      new Date(startDate.getTime() + 60 * 60 * 1000);
    
    if (parseResult.all_day) {
      const nextDay = new Date(startDate);
      nextDay.setDate(nextDay.getDate() + 1);
      params.set('dates', `${formatDateForGoogle(startDate)}/${formatDateForGoogle(nextDay)}`);
    } else {
      params.set('dates', `${formatDateTimeForGoogle(startDate)}/${formatDateTimeForGoogle(endDate)}`);
    }
  } else if (parseResult.title && parseResult.title.trim()) {
    // No specific datetime found - create all-day event for today
    // This allows user to adjust the date in Google Calendar
    const today = new Date();
    const tomorrow = new Date(today);
    tomorrow.setDate(today.getDate() + 1);
    params.set('dates', `${formatDateForGoogle(today)}/${formatDateForGoogle(tomorrow)}`);
  }
  
  if (parseResult.location) {
    params.set('location', parseResult.location);
  }
  
  if (parseResult.description) {
    params.set('details', parseResult.description);
  }
  
  return `https://calendar.google.com/calendar/render?${params.toString()}`;
}

function formatDateForGoogle(date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${year}${month}${day}`;
}

function formatDateTimeForGoogle(date) {
  // Google Calendar expects local time format, not UTC
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  const hours = String(date.getHours()).padStart(2, '0');
  const minutes = String(date.getMinutes()).padStart(2, '0');
  const seconds = String(date.getSeconds()).padStart(2, '0');
  return `${year}${month}${day}T${hours}${minutes}${seconds}`;
}