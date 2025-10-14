// Configuration for Calendar Event Creator Extension
const CONFIG = {
  // API endpoints in order of preference
  API_ENDPOINTS: [
    'https://calendar-api-wrxz.onrender.com',  // Production FastAPI
    'http://localhost:5000'                    // Local development Flask
  ],
  
  // Request timeout per endpoint (milliseconds)
  REQUEST_TIMEOUT: 10000,
  
  // Extension version
  VERSION: '2.0',
  
  // User agent for API requests
  USER_AGENT: 'CalendarEventExtension/2.0',
  
  // Default timezone
  DEFAULT_TIMEZONE: 'UTC',
  
  // Enable debug logging
  DEBUG: false
};

// Export for use in other files
if (typeof module !== 'undefined' && module.exports) {
  module.exports = CONFIG;
}