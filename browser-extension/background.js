/**
 * Background script for Calendar Event Creator browser extension.
 * Handles context menu creation and API communication.
 */

const API_BASE_URL = 'https://api.jacolabs.com';

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
      // Parse the selected text
      const parseResult = await parseText(info.selectionText);
      
      // Open calendar web app with parsed data
      await openCalendarWithEvent(parseResult);
      
    } catch (error) {
      console.error('Failed to create calendar event:', error);
      
      // Show error notification
      chrome.notifications.create({
        type: 'basic',
        iconUrl: 'icons/icon-48.png',
        title: 'Calendar Event Creator',
        message: `Failed to create event: ${error.message}`
      });
    }
  }
});

/**
 * Parse text using the API
 */
async function parseText(text) {
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
      now: new Date().toISOString()
    })
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`API request failed: ${response.status} ${errorText}`);
  }

  return await response.json();
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
      new Date(startDate.getTime() + 30 * 60 * 1000); // +30 minutes default
    
    if (parseResult.all_day) {
      // All-day event format: YYYYMMDD
      params.set('dates', `${formatDateForGoogle(startDate)}/${formatDateForGoogle(endDate)}`);
    } else {
      // Timed event format: YYYYMMDDTHHMMSSZ
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
      // Default to +30 minutes
      const endDate = new Date(startDate.getTime() + 30 * 60 * 1000);
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

// Handle messages from content script or popup
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'parseText') {
    parseText(request.text)
      .then(result => sendResponse({ success: true, data: result }))
      .catch(error => sendResponse({ success: false, error: error.message }));
    
    // Return true to indicate we'll send a response asynchronously
    return true;
  }
});