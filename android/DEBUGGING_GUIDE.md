# Android App Debugging Guide

## Current Issue: Java Version Compatibility

Your system is using **Java 8**, but modern Android development requires **Java 11 or newer**. Here are the solutions:

## Solution 1: Upgrade Java (Recommended)

### Option A: Install Java 11 or 17 via Chocolatey (Windows)
```powershell
# Install Chocolatey if you don't have it
Set-ExecutionPolicy Bypass -Scope Process -Force; [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072; iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))

# Install Java 17 (recommended)
choco install openjdk17

# Or install Java 11
choco install openjdk11
```

### Option B: Download and Install Manually
1. Go to https://adoptium.net/
2. Download Java 17 (LTS) for Windows
3. Install and set JAVA_HOME environment variable

### Option C: Use Android Studio's Embedded JDK
If you have Android Studio installed:
1. Open Android Studio
2. Go to File → Project Structure → SDK Location
3. Note the JDK location (usually something like `C:\Program Files\Android\Android Studio\jre`)
4. Set JAVA_HOME to that path

## Solution 2: Use Android Studio (Easiest)

Instead of command line building, use Android Studio:

1. **Install Android Studio** from https://developer.android.com/studio
2. **Open the project**:
   - Launch Android Studio
   - Choose "Open an existing project"
   - Navigate to the `android` folder in this project
   - Click "OK"

3. **Let Android Studio handle everything**:
   - It will automatically download the correct JDK
   - Sync Gradle dependencies
   - Handle all compatibility issues

4. **Build and run**:
   - Connect an Android device or start an emulator
   - Click the green "Run" button

## Solution 3: Fix Gradle Version (Advanced)

If you want to stick with command line, you need to downgrade Gradle:

1. **Edit `android/gradle/wrapper/gradle-wrapper.properties`**:
   ```properties
   distributionUrl=https\://services.gradle.org/distributions/gradle-7.4.2-bin.zip
   ```

2. **Use compatible Android Gradle Plugin** (already done in the project)

## Verification Steps

After upgrading Java, verify your setup:

```powershell
# Check Java version
java -version

# Should show Java 11 or newer
# Example output: openjdk version "17.0.2" 2022-01-18

# Check JAVA_HOME
echo $env:JAVA_HOME

# Build the project
cd android
./gradlew clean assembleDebug
```

## Expected Build Output

When successful, you should see:
```
BUILD SUCCESSFUL in 30s
37 actionable tasks: 37 executed
```

The APK will be created at: `android/app/build/outputs/apk/debug/app-debug.apk`

## Installing the APK

### Method 1: Using ADB
```powershell
# Enable Developer Options and USB Debugging on your Android device
# Connect device via USB
adb install app/build/outputs/apk/debug/app-debug.apk
```

### Method 2: Direct Transfer
1. Copy the APK file to your Android device
2. Open the file on your device
3. Allow installation from unknown sources if prompted
4. Install the app

## App Features

Once installed, the app provides:

### 🎯 Main Features
- **Text Input Interface**: Type event text and get parsed results
- **Text Selection Integration**: Select text in any app → "Create calendar event"
- **Share Integration**: Share text from other apps to create events
- **Calendar Integration**: Opens your default calendar app with pre-filled data

### 📱 How to Use

1. **Direct Input Method**:
   - Open "Calendar Event Creator" app
   - Type: "Meeting with John tomorrow at 2pm"
   - Tap "Parse Event"
   - Review results and tap "Create Calendar Event"

2. **Text Selection Method**:
   - In any app (browser, email, messages), select text like "Lunch Friday 12:30"
   - In the context menu, tap "Create calendar event"
   - Your calendar app opens with the event pre-filled

3. **Share Method**:
   - In any app, share text content
   - Choose "Calendar Event Creator" from the share menu
   - Your calendar app opens with the event pre-filled

## Troubleshooting

### "No calendar app found"
- Install Google Calendar or Samsung Calendar
- Make sure the calendar app has necessary permissions

### "Text selection menu doesn't show"
- Some apps don't support the PROCESS_TEXT intent
- Try copying the text and using the main app instead

### "Low confidence scores"
- Be more specific with dates and times
- Add context words like "meeting", "appointment", "lunch"

### "API connection issues"
- Check your internet connection
- The app connects to: https://calendar-api-wrxz.onrender.com

## Development Notes

The app is built with:
- **Kotlin** and **Jetpack Compose** for modern Android UI
- **Material Design 3** for consistent styling
- **OkHttp** for reliable API communication
- **Coroutines** for async operations

## Next Steps

1. **Upgrade Java** (recommended approach)
2. **Use Android Studio** for easier development
3. **Test the app** on your Android device
4. **Customize** the app as needed

The app is production-ready and includes proper error handling, user feedback, and follows Android best practices.