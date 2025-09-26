/**
 * Popup script for Calendar Event Creator browser extension.
 */

document.addEventListener('DOMContentLoaded', async () => {
    const textInput = document.getElementById('textInput');
    const createEventBtn = document.getElementById('createEventBtn');
    const getSelectionBtn = document.getElementById('getSelectionBtn');
    const statusDiv = document.getElementById('status');
    const calendarServiceSelect = document.getElementById('calendarService');
    const showFloatingButtonCheckbox = document.getElementById('showFloatingButton');
    
    // Load saved settings
    const settings = await chrome.storage.sync.get([
        'calendarService',
        'showFloatingButton'
    ]);
    
    calendarServiceSelect.value = settings.calendarService || 'google';
    showFloatingButtonCheckbox.checked = settings.showFloatingButton || false;
    
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
    
    // Create calendar event
    createEventBtn.addEventListener('click', async () => {
        const text = textInput.value.trim();
        
        if (!text) {
            showStatus('Please enter some text', 'error');
            return;
        }
        
        try {
            createEventBtn.disabled = true;
            showStatus('Processing text...', 'loading');
            
            // Send message to background script to parse text
            const response = await chrome.runtime.sendMessage({
                action: 'parseText',
                text: text
            });
            
            if (response.success) {
                showStatus('Calendar opened with event details!', 'success');
                
                // Clear the text input
                textInput.value = '';
                
                // Close popup after a short delay
                setTimeout(() => {
                    window.close();
                }, 1500);
                
            } else {
                showStatus(`Failed to create event: ${response.error}`, 'error');
            }
            
        } catch (error) {
            showStatus(`Error: ${error.message}`, 'error');
        } finally {
            createEventBtn.disabled = false;
        }
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
            }
        } catch (error) {
            // Ignore errors when trying to auto-load selected text
        }
    }, 100);
});

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