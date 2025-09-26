/**
 * Content script for Calendar Event Creator browser extension.
 * Handles text selection and provides additional UI if needed.
 */

// Track the last selected text for context menu
let lastSelectedText = '';

// Listen for text selection changes
document.addEventListener('selectionchange', () => {
  const selection = window.getSelection();
  const selectedText = selection.toString().trim();
  
  if (selectedText && selectedText.length > 0) {
    lastSelectedText = selectedText;
  }
});

// Optional: Add floating button for quick access (can be enabled via settings)
let floatingButton = null;

function createFloatingButton() {
  if (floatingButton) {
    return;
  }
  
  floatingButton = document.createElement('div');
  floatingButton.id = 'calendar-event-creator-button';
  floatingButton.innerHTML = '📅';
  floatingButton.style.cssText = `
    position: fixed;
    top: 20px;
    right: 20px;
    width: 40px;
    height: 40px;
    background: #4285f4;
    color: white;
    border: none;
    border-radius: 50%;
    font-size: 18px;
    cursor: pointer;
    z-index: 10000;
    display: none;
    align-items: center;
    justify-content: center;
    box-shadow: 0 2px 10px rgba(0,0,0,0.2);
    transition: all 0.2s ease;
  `;
  
  floatingButton.addEventListener('click', () => {
    if (lastSelectedText) {
      // Send message to background script to process text
      chrome.runtime.sendMessage({
        action: 'parseText',
        text: lastSelectedText
      }, (response) => {
        if (response.success) {
          // Hide the button after successful processing
          hideFloatingButton();
        } else {
          console.error('Failed to parse text:', response.error);
        }
      });
    }
  });
  
  document.body.appendChild(floatingButton);
}

function showFloatingButton() {
  if (!floatingButton) {
    createFloatingButton();
  }
  floatingButton.style.display = 'flex';
}

function hideFloatingButton() {
  if (floatingButton) {
    floatingButton.style.display = 'none';
  }
}

// Show floating button when text is selected (optional feature)
document.addEventListener('mouseup', () => {
  const selection = window.getSelection();
  const selectedText = selection.toString().trim();
  
  if (selectedText && selectedText.length > 10) {
    // Check if the selected text might contain event information
    const eventKeywords = [
      'meeting', 'call', 'lunch', 'dinner', 'appointment', 'conference',
      'workshop', 'training', 'event', 'party', 'celebration',
      'tomorrow', 'today', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday',
      'am', 'pm', 'o\'clock', ':', 'at', 'from', 'to'
    ];
    
    const hasEventKeywords = eventKeywords.some(keyword => 
      selectedText.toLowerCase().includes(keyword)
    );
    
    if (hasEventKeywords) {
      // Only show floating button if user has enabled it in settings
      chrome.storage.sync.get(['showFloatingButton'], (result) => {
        if (result.showFloatingButton) {
          showFloatingButton();
          
          // Hide after 5 seconds
          setTimeout(hideFloatingButton, 5000);
        }
      });
    }
  } else {
    hideFloatingButton();
  }
});

// Hide floating button when clicking elsewhere
document.addEventListener('click', (event) => {
  if (event.target !== floatingButton) {
    hideFloatingButton();
  }
});

// Listen for messages from popup or background script
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'getSelectedText') {
    const selection = window.getSelection();
    const selectedText = selection.toString().trim();
    sendResponse({ text: selectedText || lastSelectedText });
  }
});

// Optional: Keyboard shortcut support
document.addEventListener('keydown', (event) => {
  // Ctrl+Shift+C (or Cmd+Shift+C on Mac) to create calendar event from selection
  if ((event.ctrlKey || event.metaKey) && event.shiftKey && event.key === 'C') {
    const selection = window.getSelection();
    const selectedText = selection.toString().trim();
    
    if (selectedText) {
      event.preventDefault();
      
      // Send message to background script to process text
      chrome.runtime.sendMessage({
        action: 'parseText',
        text: selectedText
      }, (response) => {
        if (!response.success) {
          console.error('Failed to parse text:', response.error);
        }
      });
    }
  }
});