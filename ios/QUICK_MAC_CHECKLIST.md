# Quick Mac Setup Checklist

## ✅ **Simple Steps for Mac (No Right-Click Needed!)**

### 1. **Open Project**
- Double-click `CalendarEventApp.xcodeproj` file
- Wait for Xcode to load completely

### 2. **Fix Signing (Most Important!)**
- Click the blue project icon at the top of left sidebar
- Click "CalendarEventApp" under TARGETS
- Click "Signing & Capabilities" tab
- Set "Team" to your Apple ID
- Check "Automatically manage signing"
- Repeat for "CalendarEventExtension" target

### 3. **Check for Run Button**
- Look at top toolbar for ▶️ (play button)
- Should be next to ⏹️ (stop button)

### 4. **If No Run Button:**
- Select "CalendarEventApp" from first dropdown
- Select an iPhone simulator from second dropdown
- Try Product → Clean Build Folder
- Try Product → Build

## 🎯 **Success = Run Button Appears!**

The run button (▶️) should appear in the top toolbar once signing is configured.

## 🚨 **Mac-Specific Notes:**
- **No right-click**: Use Control+Click or two-finger tap on trackpad
- **Simulator text selection**: Click and drag (like iPhone)
- **Share button**: Square icon with up arrow

## 📞 **If Still Stuck:**
The most common issue is signing. Make sure you:
1. Have an Apple ID signed into Xcode
2. Selected your team in both targets
3. Enabled "Automatically manage signing"

That's it! The project files are all ready - just need proper signing setup on Mac.