// Dynamic API URL based on environment
const API_BASE_URL = (() => {
  // Try production first, fallback to local development
  const PRODUCTION_URL = 'https://calendar-api-wrxz.onrender.com';
  const DEVELOPMENT_URL = 'http://localhost:5000';
  
  // In production extension, use production URL
  // In development, try local first
  return PRODUCTION_URL;
})();

document.addEventListener('DOMContentLoaded', () => {
  const textInput = document.getElementById('textInput');
  const createEventBtn = document.getElementById('createEvent');
  
  createEventBtn.addEventListener('click', async () => {
    const text = textInput.value.trim();
    if (!text) {
      alert('Please enter some text');
      return;
    }
    
    // Show loading state
    createEventBtn.disabled = true;
    createEventBtn.textContent = 'Processing...';
    
    try {
      // Use enhanced parsing with audit mode for debugging
      const parseResult = await parseTextWithHybridSystem(text, { mode: 'audit' });
      
      // Show confidence warnings if needed
      if (parseResult.needs_confirmation) {
        const proceed = confirm(
          `Parsing confidence is low (${Math.round(parseResult.confidence_score * 100)}%). ` +
          `The extracted information might not be accurate. Do you want to proceed?`
        );
        if (!proceed) {
          return;
        }
      }
      
      // Show warnings to user if any
      if (parseResult.warnings && parseResult.warnings.length > 0) {
        console.warn('Parsing warnings:', parseResult.warnings);
      }
      
      // Create Google Calendar URL with parsed data
      const calendarUrl = buildGoogleCalendarUrl(parseResult);
      
      // Open calendar
      chrome.tabs.create({ url: calendarUrl });
      window.close();
      
    } catch (error) {
      console.error('Enhanced parsing failed:', error);
      
      // Try partial parsing for essential fields only
      try {
        const partialResult = await parseTextWithHybridSystem(text, { 
          fields: ['title', 'start_datetime', 'end_datetime'] 
        });
        
        const calendarUrl = buildGoogleCalendarUrl(partialResult);
        chrome.tabs.create({ url: calendarUrl });
        window.close();
        
      } catch (partialError) {
        console.error('Partial parsing also failed:', partialError);
        
        // Final fallback to simple parsing
        const title = text.substring(0, 50);
        const params = new URLSearchParams();
        params.set('action', 'TEMPLATE');
        params.set('text', title);
        
        const calendarUrl = `https://calendar.google.com/calendar/render?${params.toString()}`;
        chrome.tabs.create({ url: calendarUrl });
        window.close();
      }
      
    } finally {
      // Reset button state
      createEventBtn.disabled = false;
      createEventBtn.textContent = 'Create Event';
    }
  });
  
  // Auto-focus input
  textInput.focus();
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
      
      // Show warnings for low confidence fields
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

// Local fallback parser for when API is unavailable or slow
function parseTextLocally(text) {
  const result = {
    title: '',
    start_datetime: null,
    end_datetime: null,
    location: null,
    description: text,
    all_day: false,
    confidence_score: 0.6
  };
  
  // Extract title (first part before time/date indicators)
  const titleMatch = text.match(/^([^,]+?)(?:\s+(?:at|on|in|@|tomorrow|today|next|this)\s|$)/i);
  if (titleMatch) {
    result.title = titleMatch[1].trim();
  } else {
    result.title = text.substring(0, 50).trim();
  }
  
  // Simple time parsing
  const timePatterns = [
    /\b(\d{1,2}):(\d{2})\s*(am|pm)\b/i,
    /\b(\d{1,2})\s*(am|pm)\b/i,
    /\b(\d{1,2}):(\d{2})\b/
  ];
  
  let timeMatch = null;
  for (const pattern of timePatterns) {
    timeMatch = text.match(pattern);
    if (timeMatch) break;
  }
  
  // Simple date parsing
  const now = new Date();
  let targetDate = new Date(now);
  
  if (/\btomorrow\b/i.test(text)) {
    targetDate.setDate(now.getDate() + 1);
  } else if (/\btoday\b/i.test(text)) {
    // Keep current date
  } else if (/\bnext week\b/i.test(text)) {
    targetDate.setDate(now.getDate() + 7);
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
    }
    
    targetDate.setHours(hours, minutes, 0, 0);
    result.start_datetime = targetDate.toISOString();
    
    // Set end time (1 hour later)
    const endDate = new Date(targetDate);
    endDate.setHours(endDate.getHours() + 1);
    result.end_datetime = endDate.toISOString();
  }
  
  // Simple location extraction
  const locationPatterns = [
    /\b(?:at|in|@)\s+([^,\n]+?)(?:\s+(?:at|on|from|to)\s|\s*$)/i,
    /\blocation:\s*([^,\n]+)/i
  ];
  
  for (const pattern of locationPatterns) {
    const locationMatch = text.match(pattern);
    if (locationMatch) {
      result.location = locationMatch[1].trim();
      break;
    }
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