# Mac Setup Steps - Getting the Run Button to Appear

## 🖥️ **Do This on Your Mac (Not PC)**

iOS development requires Xcode, which only runs on macOS. Follow these steps on your Mac:

## 🖱️ **Mac Navigation Reminders**
- **No right-click**: Use **Control+Click** or **two-finger tap** on trackpad for context menus
- **Single click**: Select items
- **Double-click**: Open files/applications
- **Command+Click**: Open in new tab/window
- **Trackpad gestures**: Two-finger scroll, pinch to zoom

## 📋 **Step-by-Step Instructions**

### Step 1: Open the Project
1. **Navigate to the `ios` folder** on your Mac (using Finder)
2. **Double-click `CalendarEventApp.xcodeproj`** (NOT the folder, the actual .xcodeproj file)
   - It should have a blue Xcode icon
   - If you see a folder instead, look for the file with .xcodeproj extension
3. **Wait for Xcode to fully load** - this may take a minute

**Mac Tip**: If you need context menu options, use **Control+Click** or **two-finger tap** on trackpad

### Step 2: Check Project Navigator
1. **Look at the left sidebar** - you should see:
   ```
   📁 CalendarEventApp
   ├── 📁 CalendarEventApp
   │   ├── CalendarEventApp.swift
   │   ├── ContentView.swift
   │   ├── EventResultView.swift
   │   ├── ApiService.swift
   │   ├── Models.swift
   │   └── Info.plist
   ├── 📁 CalendarEventExtension
   │   ├── ActionViewController.swift
   │   ├── ApiService.swift
   │   ├── MainInterface.storyboard
   │   └── Info.plist
   └── 📁 Products
   ```

### Step 3: Configure Signing (CRITICAL)
1. **Click on the project root** (top "CalendarEventApp" with blue icon)
2. **Select "CalendarEventApp" target** (under TARGETS)
3. **Go to "Signing & Capabilities" tab**
4. **Set your Team**:
   - If you have an Apple Developer account: Select your team
   - If you don't: Select your personal team (your Apple ID)
5. **Ensure "Automatically manage signing" is checked**
6. **Repeat for "CalendarEventExtension" target**

### Step 4: Fix Bundle Identifiers
1. **Still in project settings**, for CalendarEventApp target:
   - Change Bundle Identifier to: `com.yourname.CalendarEventApp`
   - Replace "yourname" with your actual name/company
2. **For CalendarEventExtension target**:
   - Change Bundle Identifier to: `com.yourname.CalendarEventApp.CalendarEventExtension`
   - Must match the main app + ".CalendarEventExtension"

### Step 5: Select Scheme and Destination
1. **Look at the top toolbar** - you should see dropdowns
2. **First dropdown (Scheme)**: Select "CalendarEventApp"
3. **Second dropdown (Destination)**: Select an iOS Simulator
   - If no simulators appear, go to Xcode → Preferences → Components → Install a simulator

### Step 6: Verify Run Button Appears
- **Look for the ▶️ (Play) button** in the top toolbar
- It should be next to the Stop button (⏹️)
- If still missing, try the troubleshooting steps below

## 🔧 **Troubleshooting Steps**

### If Run Button Still Missing:

#### Option A: Clean and Rebuild
1. **Product → Clean Build Folder** (⌘+Shift+K)
2. **Wait for cleaning to complete**
3. **Product → Build** (⌘+B)
4. **Check if run button appears**

#### Option B: Reset Schemes
1. **Product → Scheme → Manage Schemes**
2. **Delete existing schemes** (select and click -)
3. **Click "Autocreate Schemes Now"**
4. **Close the dialog**

#### Option C: Check Minimum Deployment Target
1. **Project settings → CalendarEventApp target**
2. **Deployment Info → iOS Deployment Target**
3. **Set to iOS 15.0 or higher**
4. **Repeat for extension target**

#### Option D: Restart Xcode
1. **Quit Xcode completely**
2. **Reopen the project**
3. **Wait for indexing to complete**

## 🎯 **Expected Result**

After following these steps, you should see:
- ▶️ **Run button** in the top toolbar
- **Scheme dropdown** showing "CalendarEventApp"
- **Destination dropdown** showing available simulators
- **No red error indicators** in the project navigator

## 🚀 **Testing the App**

Once the run button appears:
1. **Select an iPhone simulator** (iPhone 14, iPhone 15, etc.)
2. **Click the Run button** (▶️)
3. **Wait for build and simulator launch**
4. **App should open** showing the Calendar Event Creator interface

## 📱 **Testing the Extension**

To test the Share Extension:
1. **Open Safari in the simulator**
2. **Go to any webpage with text**
3. **Select some text** (click and drag, or long press on touch)
4. **Click "Share" button** (square with arrow up)
5. **Look for "Create Calendar Event"** in the share sheet

**Mac Navigation Notes:**
- **No right-click on Mac**: Use **Control+Click** or **two-finger tap** on trackpad
- **Simulator controls**: Click and drag to select text (like on iPhone)
- **Share button**: Look for the square icon with arrow pointing up

## ❌ **Common Issues and Solutions**

### "No Developer Program Membership"
- **Solution**: Use your personal Apple ID for development
- **Go to**: Xcode → Preferences → Accounts → Add Apple ID

### "Provisioning Profile Issues"
- **Solution**: Enable "Automatically manage signing"
- **Alternative**: Delete derived data (~/Library/Developer/Xcode/DerivedData)

### "Simulator Not Available"
- **Solution**: Xcode → Preferences → Components → Install iOS Simulator
- **Alternative**: Xcode → Window → Devices and Simulators → Add simulator

### "Build Errors"
- **Check**: All files are properly included in targets
- **Verify**: EventKit framework is linked
- **Try**: Clean build folder and rebuild

## 📞 **If You Still Have Issues**

If the run button still doesn't appear after following all steps:

1. **Take a screenshot** of your Xcode window
2. **Check the Issue Navigator** (⚠️ icon in left sidebar)
3. **Look for any red error messages**
4. **Try creating a new iOS project** to verify Xcode is working

The most common cause is missing signing configuration, so make sure Step 3 is completed properly.

## 🎉 **Success Indicators**

You'll know it's working when:
- ✅ Run button (▶️) is visible and clickable
- ✅ No red errors in project navigator
- ✅ Scheme shows "CalendarEventApp"
- ✅ Destination shows iOS simulators
- ✅ Build succeeds (⌘+B works without errors)

Follow these steps in order, and the run button should appear!