// Background script using our hybrid regex/LLM parsing system
const API_BASE_URL = 'http://localhost:5000';

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

// Parse text using enhanced API with audit mode and partial parsing support
async function parseTextWithHybridSystem(text, options = {}) {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 15000); // 15 second timeout for enhanced processing
  
  try {
    // Build URL with query parameters for enhanced features
    const url = new URL(`${API_BASE_URL}/parse`);
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
      // Enhanced error handling for new API responses
      const errorData = await response.json().catch(() => ({}));
      const errorMessage = errorData.error?.message || `API error: ${response.status}`;
      throw new Error(errorMessage);
    }
    
    const result = await response.json();
    
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
      console.warn('API request timed out after 15 seconds, using local fallback');
    } else {
      console.warn('Enhanced API parsing failed, using local fallback:', error);
    }
    return parseTextLocally(text);
  }
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
    confidence_score: 0.7
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
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  const hours = String(date.getUTCHours()).padStart(2, '0');
  const minutes = String(date.getUTCMinutes()).padStart(2, '0');
  const seconds = String(date.getUTCSeconds()).padStart(2, '0');
  return `${year}${month}${day}T${hours}${minutes}${seconds}Z`;
}