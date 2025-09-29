/**
 * Popup script for Calendar Event Creator browser extension.
 */

document.addEventListener('DOMContentLoaded', async () => {
    // UI Elements
    const textInput = document.getElementById('textInput');
    const createEventBtn = document.getElementById('createEventBtn');
    const getSelectionBtn = document.getElementById('getSelectionBtn');
    const statusDiv = document.getElementById('status');
    
    // Event Results Elements
    const eventResults = document.getElementById('eventResults');
    const inputSection = document.getElementById('inputSection');
    const eventTitle = document.getElementById('eventTitle');
    const eventDateTime = document.getElementById('eventDateTime');
    const eventLocation = document.getElementById('eventLocation');
    const eventDescription = document.getElementById('eventDescription');
    const titleConfidence = document.getElementById('titleConfidence');
    const dateTimeConfidence = document.getElementById('dateTimeConfidence');
    const locationConfidence = document.getElementById('locationConfidence');
    const overallConfidence = document.getElementById('overallConfidence');
    const confidenceProgress = document.getElementById('confidenceProgress');
    const confidenceText = document.getElementById('confidenceText');
    
    // Calendar Integration Elements
    const googleCalendarBtn = document.getElementById('googleCalendarBtn');
    const outlookCalendarBtn = document.getElementById('outlookCalendarBtn');
    const appleCalendarBtn = document.getElementById('appleCalendarBtn');
    const editEventBtn = document.getElementById('editEventBtn');
    const parseAgainBtn = document.getElementById('parseAgainBtn');
    
    // Settings Elements
    const calendarServiceSelect = document.getElementById('calendarService');
    const showFloatingButtonCheckbox = document.getElementById('showFloatingButton');
    const autoParseSelectionCheckbox = document.getElementById('autoParseSelection');
    const confidenceThresholdSelect = document.getElementById('confidenceThreshold');
    const showConfidenceScoresCheckbox = document.getElementById('showConfidenceScores');
    const advancedToggle = document.getElementById('advancedToggle');
    const advancedContent = document.getElementById('advancedContent');
    
    // Current parsed event data
    let currentEventData = null;
    
    // Load saved settings
    const settings = await chrome.storage.sync.get([
        'calendarService',
        'showFloatingButton',
        'autoParseSelection',
        'confidenceThreshold',
        'showConfidenceScores'
    ]);
    
    calendarServiceSelect.value = settings.calendarService || 'google';
    showFloatingButtonCheckbox.checked = settings.showFloatingButton || false;
    autoParseSelectionCheckbox.checked = settings.autoParseSelection || false;
    confidenceThresholdSelect.value = settings.confidenceThreshold || '0.5';
    showConfidenceScoresCheckbox.checked = settings.showConfidenceScores !== false;
    
    // Save settings when changed
    calendarServiceSelect.addEventListener('change', () => {
        chrome.storage.sync.set({
            calendarService: calendarServiceSelect.value
        });
    });
    
    showFloatingButtonCheckbox.addEventListener('change', () => {
        chrome.storage.sync.set({
            showFloatingButton: showFloatingButtonCheckbox.checked
        });
    });
    
    autoParseSelectionCheckbox.addEventListener('change', () => {
        chrome.storage.sync.set({
            autoParseSelection: autoParseSelectionCheckbox.checked
        });
    });
    
    confidenceThresholdSelect.addEventListener('change', () => {
        chrome.storage.sync.set({
            confidenceThreshold: confidenceThresholdSelect.value
        });
    });
    
    showConfidenceScoresCheckbox.addEventListener('change', () => {
        chrome.storage.sync.set({
            showConfidenceScores: showConfidenceScoresCheckbox.checked
        });
        updateConfidenceDisplay();
    });
    
    // Advanced settings toggle
    advancedToggle.addEventListener('click', () => {
        const isVisible = advancedContent.style.display !== 'none';
        advancedContent.style.display = isVisible ? 'none' : 'block';
        advancedToggle.textContent = isVisible ? 'Advanced Settings ▼' : 'Advanced Settings ▲';
    });
    
    // Get selected text from current tab
    getSelectionBtn.addEventListener('click', async () => {
        try {
            const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
            
            const response = await chrome.tabs.sendMessage(tab.id, {
                action: 'getSelectedText'
            });
            
            if (response && response.text) {
                textInput.value = response.text;
                showStatus('Selected text loaded', 'success');
            } else {
                showStatus('No text selected on the page', 'error');
            }
        } catch (error) {
            showStatus('Failed to get selected text', 'error');
        }
    });
    
    // Parse text and show results
    createEventBtn.addEventListener('click', async () => {
        const text = textInput.value.trim();
        
        if (!text) {
            showStatus('Please enter some text', 'error');
            return;
        }
        
        await parseAndDisplayEvent(text);
    });
    
    // Calendar integration buttons
    googleCalendarBtn.addEventListener('click', () => {
        if (currentEventData) {
            openCalendarWithEvent(currentEventData, 'google');
        }
    });
    
    outlookCalendarBtn.addEventListener('click', () => {
        if (currentEventData) {
            openCalendarWithEvent(currentEventData, 'outlook');
        }
    });
    
    appleCalendarBtn.addEventListener('click', () => {
        if (currentEventData) {
            openCalendarWithEvent(currentEventData, 'apple');
        }
    });
    
    // Action buttons
    editEventBtn.addEventListener('click', () => {
        // Show input section again for editing
        showInputSection();
        if (currentEventData && currentEventData.original_text) {
            textInput.value = currentEventData.original_text;
        }
    });
    
    parseAgainBtn.addEventListener('click', () => {
        showInputSection();
        textInput.value = '';
        textInput.focus();
    });
    
    // Handle Enter key in text input (Ctrl+Enter to create event)
    textInput.addEventListener('keydown', (event) => {
        if (event.ctrlKey && event.key === 'Enter') {
            createEventBtn.click();
        }
    });
    
    // Auto-focus text input
    textInput.focus();
    
    // Try to load selected text on popup open
    setTimeout(async () => {
        try {
            const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
            
            const response = await chrome.tabs.sendMessage(tab.id, {
                action: 'getSelectedText'
            });
            
            if (response && response.text && response.text.length > 10) {
                textInput.value = response.text;
                textInput.select();
                
                // Auto-parse if enabled
                if (settings.autoParseSelection) {
                    await parseAndDisplayEvent(response.text);
                }
            }
        } catch (error) {
            // Ignore errors when trying to auto-load selected text
        }
    }, 100);
});

/**
 * Parse text and display event results
 */
async function parseAndDisplayEvent(text) {
    try {
        createEventBtn.disabled = true;
        showStatus('Processing text...', 'loading');
        
        // Send message to background script to parse text
        const response = await chrome.runtime.sendMessage({
            action: 'parseText',
            text: text
        });
        
        if (response.success) {
            currentEventData = response.data;
            currentEventData.original_text = text; // Store original text for editing
            
            displayEventResults(currentEventData);
            showStatus('Event parsed successfully!', 'success');
            
        } else {
            showStatus(`Failed to parse event: ${response.error}`, 'error');
        }
        
    } catch (error) {
        showStatus(`Error: ${error.message}`, 'error');
    } finally {
        createEventBtn.disabled = false;
    }
}

/**
 * Display parsed event results in the UI
 */
function displayEventResults(eventData) {
    // Hide input section and show results
    inputSection.style.display = 'none';
    eventResults.style.display = 'block';
    
    // Populate event fields
    eventTitle.textContent = eventData.title || 'No title detected';
    eventTitle.className = eventData.title ? 'field-value' : 'field-value empty';
    
    // Format date and time
    let dateTimeText = 'No date/time detected';
    if (eventData.start_datetime) {
        const startDate = new Date(eventData.start_datetime);
        const endDate = eventData.end_datetime ? new Date(eventData.end_datetime) : null;
        
        if (eventData.all_day) {
            dateTimeText = startDate.toLocaleDateString();
        } else {
            dateTimeText = `${startDate.toLocaleDateString()} at ${startDate.toLocaleTimeString()}`;
            if (endDate) {
                dateTimeText += ` - ${endDate.toLocaleTimeString()}`;
            }
        }
    }
    eventDateTime.textContent = dateTimeText;
    eventDateTime.className = eventData.start_datetime ? 'field-value' : 'field-value empty';
    
    eventLocation.textContent = eventData.location || 'No location detected';
    eventLocation.className = eventData.location ? 'field-value' : 'field-value empty';
    
    eventDescription.textContent = eventData.description || 'No additional description';
    eventDescription.className = eventData.description ? 'field-value' : 'field-value empty';
    
    // Update confidence scores
    updateConfidenceScores(eventData);
    
    // Update overall confidence
    const overallScore = eventData.confidence_score || 0;
    confidenceProgress.style.width = `${overallScore * 100}%`;
    confidenceText.textContent = `${Math.round(overallScore * 100)}%`;
    
    // Update confidence bar color
    if (overallScore >= 0.7) {
        confidenceProgress.style.background = '#4caf50'; // Green
    } else if (overallScore >= 0.4) {
        confidenceProgress.style.background = '#ff9800'; // Orange
    } else {
        confidenceProgress.style.background = '#f44336'; // Red
    }
    
    // Update confidence display visibility
    updateConfidenceDisplay();
}

/**
 * Update individual field confidence scores
 */
function updateConfidenceScores(eventData) {
    // For API responses, we may not have field-level confidence scores
    // Use overall confidence as fallback
    const overallConfidence = eventData.confidence_score || 0;
    
    // Estimate field confidence based on presence and overall confidence
    const titleConf = eventData.title ? overallConfidence : 0;
    const dateTimeConf = eventData.start_datetime ? overallConfidence : 0;
    const locationConf = eventData.location ? overallConfidence * 0.8 : 0; // Location is optional
    
    titleConfidence.textContent = formatConfidence(titleConf);
    titleConfidence.className = getConfidenceClass(titleConf);
    
    dateTimeConfidence.textContent = formatConfidence(dateTimeConf);
    dateTimeConfidence.className = getConfidenceClass(dateTimeConf);
    
    locationConfidence.textContent = formatConfidence(locationConf);
    locationConfidence.className = getConfidenceClass(locationConf);
}

/**
 * Format confidence score for display
 */
function formatConfidence(score) {
    if (score === undefined || score === null) return '';
    return `Confidence: ${Math.round(score * 100)}%`;
}

/**
 * Get CSS class for confidence level
 */
function getConfidenceClass(score) {
    if (score === undefined || score === null) return 'confidence-score';
    
    const baseClass = 'confidence-score';
    if (score >= 0.7) return `${baseClass} confidence-high`;
    if (score >= 0.4) return `${baseClass} confidence-medium`;
    return `${baseClass} confidence-low`;
}

/**
 * Update confidence display visibility based on settings
 */
function updateConfidenceDisplay() {
    const showScores = showConfidenceScoresCheckbox.checked;
    const confidenceElements = document.querySelectorAll('.confidence-score, .overall-confidence');
    
    confidenceElements.forEach(element => {
        element.style.display = showScores ? 'block' : 'none';
    });
}

/**
 * Show input section and hide results
 */
function showInputSection() {
    inputSection.style.display = 'block';
    eventResults.style.display = 'none';
    currentEventData = null;
}

/**
 * Open calendar with event data
 */
async function openCalendarWithEvent(eventData, calendarType = null) {
    try {
        const calendarService = calendarType || calendarServiceSelect.value;
        
        // Send message to background script to open calendar
        const response = await chrome.runtime.sendMessage({
            action: 'openCalendar',
            eventData: eventData,
            calendarService: calendarService
        });
        
        if (response.success) {
            if (calendarService === 'apple') {
                showStatus('Downloading ICS file for Apple Calendar...', 'success');
            } else {
                showStatus(`Opening ${calendarService === 'google' ? 'Google' : 'Outlook'} Calendar...`, 'success');
            }
            
            // Close popup after a short delay
            setTimeout(() => {
                window.close();
            }, 1500);
        } else {
            showStatus(`Failed to open calendar: ${response.error}`, 'error');
        }
        
    } catch (error) {
        showStatus(`Error opening calendar: ${error.message}`, 'error');
    }
}

/**
 * Show status message
 */
function showStatus(message, type) {
    const statusDiv = document.getElementById('status');
    statusDiv.textContent = message;
    statusDiv.className = `status ${type}`;
    statusDiv.style.display = 'block';
    
    // Auto-hide success messages
    if (type === 'success') {
        setTimeout(() => {
            statusDiv.style.display = 'none';
        }, 3000);
    }
}