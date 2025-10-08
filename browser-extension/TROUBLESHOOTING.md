# Browser Extension Troubleshooting Guide

## Common Issues and Solutions

### Error: "Cannot read properties of undefined (reading 'create')"

**Problem**: This error occurs when the extension tries to use Chrome APIs that aren't available due to missing permissions.

**Solution**: 
1. **Update manifest.json permissions** (✅ Fixed):
   ```json
   "permissions": [
     "contextMenus",
     "activeTab", 
     "storage",
     "downloads",
     "notifications",  // ← Added
     "tabs"            // ← Added
   ]
   ```

2. **Reload the extension**:
   - Go to `chrome://extensions/`
   - Find "Calendar Event Creator"
   - Click the reload button (🔄)
   - Or disable and re-enable the extension

3. **Check permissions granted**:
   - Click "Details" on the extension
   - Verify all permissions are granted

### Error: "Failed to create calendar event"

**Possible Causes & Solutions**:

1. **Network Issues**:
   - Check internet connection
   - Verify API endpoint is accessible: https://calendar-api-wrxz.onrender.com

2. **API Service Down**:
   - The parsing service might be temporarily unavailable
   - Try again in a few minutes

3. **Invalid Text Selection**:
   - Ensure selected text contains date/time information
   - Try more explicit text like "Meeting tomorrow at 2pm"

4. **Browser Permissions**:
   - Check if popup blockers are enabled
   - Ensure the extension has permission to access the current site

### Extension Not Loading

**Solutions**:
1. **Enable Developer Mode**:
   - Go to `chrome://extensions/`
   - Toggle "Developer mode" in the top right

2. **Check Manifest Syntax**:
   - Ensure `manifest.json` is valid JSON
   - No trailing commas or syntax errors

3. **Verify File Structure**:
   ```
   browser-extension/
   ├── manifest.json
   ├── background.js
   ├── popup.html
   ├── popup.js
   ├── content.js
   └── icons/
       └── icon-16.png
   ```

### Context Menu Not Appearing

**Solutions**:
1. **Refresh the webpage** after installing the extension
2. **Select text first** - the context menu only appears when text is selected
3. **Check extension permissions** - ensure it has access to the current site

### Calendar Not Opening

**Solutions**:
1. **Check popup blocker settings** in your browser
2. **Verify internet connection**
3. **Try different calendar service** (Google Calendar vs Outlook)
4. **Check browser console** for additional error messages

## Testing the Fix

After updating the manifest.json with the new permissions:

1. **Reload the extension**:
   - Go to `chrome://extensions/`
   - Find "Calendar Event Creator" 
   - Click the reload button

2. **Use the debug helper**:
   - Open `debug-extension.html` in your browser
   - Select test text and try the context menu
   - Check for any console errors

3. **Test basic functionality**:
   - Select text like "Meeting tomorrow at 2pm"
   - Right-click and select "Create calendar event"
   - Should see processing notification (if notifications work)
   - Should open calendar in new tab

4. **Test popup interface**:
   - Click the extension icon
   - Enter text and click "Parse Text & Create Event"
   - Should show parsed results
   - Calendar buttons should work

## Debug Information

If issues persist, check the browser console:

1. **Background Script Errors**:
   - Go to `chrome://extensions/`
   - Click "Details" on the extension
   - Click "Inspect views: background page"
   - Check console for errors

2. **Popup Script Errors**:
   - Right-click the extension popup
   - Select "Inspect"
   - Check console for errors

3. **Content Script Errors**:
   - Open developer tools on any webpage (F12)
   - Check console for extension-related errors

## API Health Check

Test if the parsing API is working:

```bash
curl -X POST https://calendar-api-wrxz.onrender.com/parse \
  -H "Content-Type: application/json" \
  -d '{"text": "Meeting tomorrow at 2pm"}'
```

Should return JSON with parsed event data.

## Browser Compatibility

- **Chrome**: Full support (recommended)
- **Edge**: Full support (Chromium-based)
- **Firefox**: Limited support (different extension APIs)

## Getting Help

If the issue persists:

1. Check the browser console for specific error messages
2. Try disabling other extensions to check for conflicts
3. Test in an incognito window to rule out browser cache issues
4. Verify the API service is accessible from your network