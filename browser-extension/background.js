/**
 * Background script for Calendar Event Creator browser extension.
 * Handles context menu creation and API communication.
 */

const API_BASE_URL = 'https://calendar-api-wrxz.onrender.com';

// Create context menu when extension is installed
chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({
    id: 'createCalendarEvent',
    title: 'Create calendar event',
    contexts: ['selection']
  });
});

// Handle context menu clicks
chrome.contextMenus.onClicked.addListener(async (info, tab) => {
  if (info.menuItemId === 'createCalendarEvent' && info.selectionText) {
    try {
      // Show processing notification
      const processingNotificationId = await chrome.notifications.create({
        type: 'basic',
        iconUrl: 'icons/icon-48.png',
        title: 'Calendar Event Creator',
        message: 'Processing selected text...'
      });
      
      // Parse the selected text
      const parseResult = await parseText(info.selectionText);
      
      // Clear processing notification
      chrome.notifications.clear(processingNotificationId);
      
      // Open calendar web app with parsed data
      await openCalendarWithEvent(parseResult);
      
      // Show success notification
      chrome.notifications.create({
        type: 'basic',
        iconUrl: 'icons/icon-48.png',
        title: 'Calendar Event Creator',
        message: `Event "${parseResult.title || 'Untitled Event'}" created successfully!`
      });
      
    } catch (error) {
      console.error('Failed to create calendar event:', error);
      
      // Determine error type and provide appropriate feedback
      let errorMessage = error.message;
      let actionMessage = '';
      
      if (error.message.includes('network') || error.message.includes('connection')) {
        actionMessage = ' Please check your internet connection.';
      } else if (error.message.includes('timeout')) {
        actionMessage = ' Please try again.';
      } else if (error.message.includes('rate limit') || error.message.includes('too many')) {
        actionMessage = ' Please wait a moment before trying again.';
      } else if (error.message.includes('server') || error.message.includes('unavailable')) {
        actionMessage = ' Please try again later.';
      } else if (error.message.includes('extract') || error.message.includes('unclear')) {
        actionMessage = ' Try selecting text with clearer date and time information.';
      }
      
      // Show error notification with action suggestion
      chrome.notifications.create({
        type: 'basic',
        iconUrl: 'icons/icon-48.png',
        title: 'Calendar Event Creator - Error',
        message: errorMessage + actionMessage
      });
    }
  }
});

/**
 * Parse text using the API with comprehensive error handling and retry logic
 */
async function parseText(text, retryCount = 0) {
  const maxRetries = 3;
  
  // Validate input
  if (!text || text.trim().length === 0) {
    throw new Error('Please provide text containing event information.');
  }
  
  if (text.length > 10000) {
    throw new Error('Text is too long. Please limit to 10,000 characters.');
  }
  
  // Check if we're online
  if (!navigator.onLine) {
    throw new Error('No internet connection. Please check your network settings and try again.');
  }
  
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 30000); // 30 second timeout
  
  try {
    const response = await fetch(`${API_BASE_URL}/parse`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'User-Agent': 'CalendarEventCreator-Extension/1.0'
      },
      body: JSON.stringify({
        text: text,
        timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
        locale: navigator.language,
        now: new Date().toISOString(),
        use_llm_enhancement: true
      }),
      signal: controller.signal
    });
    
    clearTimeout(timeoutId);
    
    // Handle different response codes
    if (response.ok) {
      const result = await response.json();
      
      // Validate the result
      validateParseResult(result, text);
      
      return result;
    }
    
    // Handle error responses
    const errorData = await parseErrorResponse(response);
    
    switch (response.status) {
      case 400:
      case 422:
        throw new Error(errorData.userMessage || 'The text does not contain valid event information. Please try rephrasing with clearer date, time, and event details.');
      
      case 429:
        const retryAfter = response.headers.get('Retry-After') || '60';
        throw new Error(`Too many requests. Please wait ${retryAfter} seconds before trying again.`);
      
      case 500:
      case 502:
      case 503:
      case 504:
        if (retryCount < maxRetries) {
          // Exponential backoff for server errors
          const delay = Math.pow(2, retryCount) * 1000;
          await new Promise(resolve => setTimeout(resolve, delay));
          return parseText(text, retryCount + 1);
        } else {
          throw new Error('Server is temporarily unavailable. Please try again in a few minutes.');
        }
      
      default:
        throw new Error(errorData.userMessage || `Request failed with status ${response.status}. Please try again.`);
    }
    
  } catch (error) {
    clearTimeout(timeoutId);
    
    if (error.name === 'AbortError') {
      if (retryCount < maxRetries) {
        return parseText(text, retryCount + 1);
      } else {
        throw new Error('Request timed out after multiple attempts. Please check your internet connection and try again.');
      }
    }
    
    if (error.message.includes('Failed to fetch') || error.message.includes('NetworkError')) {
      if (retryCount < maxRetries) {
        const delay = Math.pow(2, retryCount) * 1000;
        await new Promise(resolve => setTimeout(resolve, delay));
        return parseText(text, retryCount + 1);
      } else {
        throw new Error('Unable to connect to the server. Please check your internet connection and try again.');
      }
    }
    
    // Re-throw other errors as-is
    throw error;
  }
}

/**
 * Parse error response from API to extract user-friendly messages
 */
async function parseErrorResponse(response) {
  try {
    const errorData = await response.json();
    
    if (errorData.error) {
      const { code, message, suggestion } = errorData.error;
      
      let userMessage;
      switch (code) {
        case 'VALIDATION_ERROR':
          userMessage = `Invalid input: ${message}`;
          break;
        case 'PARSING_ERROR':
          userMessage = message + (suggestion ? `. ${suggestion}` : '');
          break;
        case 'TEXT_EMPTY':
          userMessage = 'Please provide text containing event information.';
          break;
        case 'TEXT_TOO_LONG':
          userMessage = 'Text is too long. Please limit to 10,000 characters.';
          break;
        case 'INVALID_TIMEZONE':
          userMessage = 'Invalid timezone. Please check your browser settings.';
          break;
        case 'LLM_UNAVAILABLE':
          userMessage = 'Enhanced parsing is temporarily unavailable. Your request will be processed with basic parsing.';
          break;
        case 'RATE_LIMIT_ERROR':
          userMessage = message + (suggestion ? `. ${suggestion}` : '');
          break;
        case 'SERVICE_UNAVAILABLE':
          userMessage = 'Service is temporarily unavailable. Please try again later.';
          break;
        default:
          userMessage = message;
      }
      
      return { code, message, userMessage, suggestion };
    }
    
    // Fallback to old format
    return { 
      code: 'UNKNOWN_ERROR', 
      message: errorData.detail || 'Unknown error occurred',
      userMessage: errorData.detail || 'Unknown error occurred'
    };
    
  } catch (e) {
    // If we can't parse the error response, return a generic message
    return {
      code: 'PARSE_ERROR',
      message: 'Server returned an error',
      userMessage: 'Server returned an error. Please try again.'
    };
  }
}

/**
 * Validate the parsed result and provide helpful feedback
 */
function validateParseResult(result, originalText) {
  // Check if we got meaningful results
  if ((!result.title || result.title.trim().length === 0) && 
      (!result.start_datetime || result.start_datetime.trim().length === 0)) {
    throw new Error('Could not extract event information from the text. Please try rephrasing with clearer date, time, and event details.');
  }
  
  // Warn about low confidence
  if (result.confidence_score < 0.3) {
    throw new Error('The text is unclear and may not contain valid event information. Please try rephrasing with specific date, time, and event details.');
  }
}

/**
 * Open calendar web application with pre-filled event data
 */
async function openCalendarWithEvent(parseResult) {
  // Get user's preferred calendar service from storage
  const { calendarService = 'google' } = await chrome.storage.sync.get(['calendarService']);
  
  let calendarUrl;
  
  if (calendarService === 'google') {
    calendarUrl = buildGoogleCalendarUrl(parseResult);
  } else if (calendarService === 'outlook') {
    calendarUrl = buildOutlookCalendarUrl(parseResult);
  } else if (calendarService === 'apple') {
    calendarUrl = buildAppleCalendarUrl(parseResult);
  } else {
    // Default to Google Calendar
    calendarUrl = buildGoogleCalendarUrl(parseResult);
  }
  
  // Open calendar in new tab
  chrome.tabs.create({ url: calendarUrl });
}

/**
 * Build Google Calendar URL with event data
 */
function buildGoogleCalendarUrl(parseResult) {
  const baseUrl = 'https://calendar.google.com/calendar/render';
  const params = new URLSearchParams();
  
  params.set('action', 'TEMPLATE');
  
  // Set title
  if (parseResult.title) {
    params.set('text', parseResult.title);
  }
  
  // Set dates
  if (parseResult.start_datetime) {
    const startDate = new Date(parseResult.start_datetime);
    const endDate = parseResult.end_datetime ? 
      new Date(parseResult.end_datetime) : 
      new Date(startDate.getTime() + 60 * 60 * 1000); // +1 hour default
    
    if (parseResult.all_day) {
      // All-day event format: YYYYMMDD/YYYYMMDD
      const nextDay = new Date(startDate);
      nextDay.setDate(nextDay.getDate() + 1);
      params.set('dates', `${formatDateForGoogle(startDate)}/${formatDateForGoogle(nextDay)}`);
    } else {
      // Timed event format: YYYYMMDDTHHMMSSZ/YYYYMMDDTHHMMSSZ
      params.set('dates', `${formatDateTimeForGoogle(startDate)}/${formatDateTimeForGoogle(endDate)}`);
    }
  }
  
  // Set location
  if (parseResult.location) {
    params.set('location', parseResult.location);
  }
  
  // Set description
  if (parseResult.description) {
    params.set('details', parseResult.description);
  }
  
  return `${baseUrl}?${params.toString()}`;
}

/**
 * Build Outlook Calendar URL with event data
 */
function buildOutlookCalendarUrl(parseResult) {
  const baseUrl = 'https://outlook.live.com/calendar/0/deeplink/compose';
  const params = new URLSearchParams();
  
  // Set title
  if (parseResult.title) {
    params.set('subject', parseResult.title);
  }
  
  // Set dates
  if (parseResult.start_datetime) {
    const startDate = new Date(parseResult.start_datetime);
    params.set('startdt', startDate.toISOString());
    
    if (parseResult.end_datetime) {
      const endDate = new Date(parseResult.end_datetime);
      params.set('enddt', endDate.toISOString());
    } else {
      // Default to +1 hour
      const endDate = new Date(startDate.getTime() + 60 * 60 * 1000);
      params.set('enddt', endDate.toISOString());
    }
  }
  
  // Set location
  if (parseResult.location) {
    params.set('location', parseResult.location);
  }
  
  // Set description
  if (parseResult.description) {
    params.set('body', parseResult.description);
  }
  
  // Set all-day flag
  if (parseResult.all_day) {
    params.set('allday', 'true');
  }
  
  return `${baseUrl}?${params.toString()}`;
}

/**
 * Format date for Google Calendar (YYYYMMDD)
 */
function formatDateForGoogle(date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${year}${month}${day}`;
}

/**
 * Format datetime for Google Calendar (YYYYMMDDTHHMMSSZ)
 */
function formatDateTimeForGoogle(date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  const hours = String(date.getUTCHours()).padStart(2, '0');
  const minutes = String(date.getUTCMinutes()).padStart(2, '0');
  const seconds = String(date.getUTCSeconds()).padStart(2, '0');
  return `${year}${month}${day}T${hours}${minutes}${seconds}Z`;
}

/**
 * Build Apple Calendar URL with event data (ICS download)
 */
function buildAppleCalendarUrl(parseResult) {
  // Generate ICS content and create a downloadable blob URL
  const icsContent = generateICSContent(parseResult);
  
  // Create a blob and return a data URL for download
  const blob = new Blob([icsContent], { type: 'text/calendar' });
  const url = URL.createObjectURL(blob);
  
  // For Apple Calendar, we'll trigger a download
  return url;
}

/**
 * Generate ICS content for Apple Calendar
 */
function generateICSContent(parseResult) {
  const now = new Date();
  const uid = `${now.getTime()}@calendar-event-creator`;
  
  let icsContent = [
    'BEGIN:VCALENDAR',
    'VERSION:2.0',
    'PRODID:-//Calendar Event Creator//EN',
    'CALSCALE:GREGORIAN',
    'METHOD:PUBLISH',
    'BEGIN:VEVENT',
    `UID:${uid}`,
    `DTSTAMP:${formatDateTimeForICS(now)}`
  ];
  
  // Add title
  if (parseResult.title) {
    icsContent.push(`SUMMARY:${escapeICSText(parseResult.title)}`);
  } else {
    icsContent.push('SUMMARY:Calendar Event');
  }
  
  // Add dates
  if (parseResult.start_datetime) {
    const startDate = new Date(parseResult.start_datetime);
    const endDate = parseResult.end_datetime ? 
      new Date(parseResult.end_datetime) : 
      new Date(startDate.getTime() + 60 * 60 * 1000); // +1 hour default
    
    if (parseResult.all_day) {
      icsContent.push(`DTSTART;VALUE=DATE:${formatDateForICS(startDate)}`);
      const nextDay = new Date(startDate);
      nextDay.setDate(nextDay.getDate() + 1);
      icsContent.push(`DTEND;VALUE=DATE:${formatDateForICS(nextDay)}`);
    } else {
      icsContent.push(`DTSTART:${formatDateTimeForICS(startDate)}`);
      icsContent.push(`DTEND:${formatDateTimeForICS(endDate)}`);
    }
  }
  
  // Add location
  if (parseResult.location) {
    icsContent.push(`LOCATION:${escapeICSText(parseResult.location)}`);
  }
  
  // Add description
  if (parseResult.description) {
    icsContent.push(`DESCRIPTION:${escapeICSText(parseResult.description)}`);
  }
  
  // Add creation time
  icsContent.push(`CREATED:${formatDateTimeForICS(now)}`);
  icsContent.push(`LAST-MODIFIED:${formatDateTimeForICS(now)}`);
  
  icsContent.push('END:VEVENT');
  icsContent.push('END:VCALENDAR');
  
  return icsContent.join('\r\n');
}

/**
 * Format date for ICS (YYYYMMDD)
 */
function formatDateForICS(date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${year}${month}${day}`;
}

/**
 * Format datetime for ICS (YYYYMMDDTHHMMSSZ)
 */
function formatDateTimeForICS(date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  const hours = String(date.getUTCHours()).padStart(2, '0');
  const minutes = String(date.getUTCMinutes()).padStart(2, '0');
  const seconds = String(date.getUTCSeconds()).padStart(2, '0');
  return `${year}${month}${day}T${hours}${minutes}${seconds}Z`;
}

/**
 * Escape text for ICS format
 */
function escapeICSText(text) {
  if (!text) return '';
  
  return text
    .replace(/\\/g, '\\\\')
    .replace(/;/g, '\\;')
    .replace(/,/g, '\\,')
    .replace(/\n/g, '\\n')
    .replace(/\r/g, '');
}



// Handle messages from content script or popup
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'parseText') {
    parseText(request.text)
      .then(result => {
        sendResponse({ success: true, data: result });
      })
      .catch(error => {
        console.error('Parse text error:', error);
        sendResponse({ 
          success: false, 
          error: error.message,
          errorType: categorizeError(error.message)
        });
      });
    
    // Return true to indicate we'll send a response asynchronously
    return true;
  }
  
  if (request.action === 'openCalendar') {
    try {
      if (request.calendarService === 'apple') {
        // Handle Apple Calendar differently - trigger download
        const icsContent = generateICSContent(request.eventData);
        
        // Create download using chrome.downloads API
        const blob = new Blob([icsContent], { type: 'text/calendar' });
        const url = URL.createObjectURL(blob);
        
        chrome.downloads.download({
          url: url,
          filename: `${request.eventData.title || 'event'}.ics`,
          saveAs: true
        }, () => {
          if (chrome.runtime.lastError) {
            sendResponse({ success: false, error: chrome.runtime.lastError.message });
          } else {
            sendResponse({ success: true });
            // Clean up the blob URL after download
            setTimeout(() => URL.revokeObjectURL(url), 1000);
          }
        });
      } else {
        // Handle Google Calendar and Outlook - open in new tab
        let calendarUrl;
        
        if (request.calendarService === 'outlook') {
          calendarUrl = buildOutlookCalendarUrl(request.eventData);
        } else {
          calendarUrl = buildGoogleCalendarUrl(request.eventData);
        }
        
        chrome.tabs.create({ url: calendarUrl }, (tab) => {
          if (chrome.runtime.lastError) {
            sendResponse({ success: false, error: chrome.runtime.lastError.message });
          } else {
            sendResponse({ success: true });
          }
        });
      }
    } catch (error) {
      console.error('Open calendar error:', error);
      sendResponse({ success: false, error: error.message });
    }
    
    return true;
  }
  
  if (request.action === 'checkHealth') {
    // Health check endpoint for popup
    fetch(`${API_BASE_URL}/healthz`)
      .then(response => response.json())
      .then(data => {
        sendResponse({ success: true, health: data });
      })
      .catch(error => {
        sendResponse({ 
          success: false, 
          error: 'Service unavailable',
          offline: !navigator.onLine
        });
      });
    
    return true;
  }
});

/**
 * Categorize error types for better handling
 */
function categorizeError(errorMessage) {
  const message = errorMessage.toLowerCase();
  
  if (message.includes('network') || message.includes('connection') || message.includes('fetch')) {
    return 'network';
  } else if (message.includes('timeout')) {
    return 'timeout';
  } else if (message.includes('rate limit') || message.includes('too many')) {
    return 'rateLimit';
  } else if (message.includes('server') || message.includes('unavailable')) {
    return 'server';
  } else if (message.includes('extract') || message.includes('unclear') || message.includes('confidence')) {
    return 'parsing';
  } else if (message.includes('validation') || message.includes('invalid')) {
    return 'validation';
  } else {
    return 'unknown';
  }
}