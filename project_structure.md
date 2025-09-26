# Text-to-Calendar Event System - Mobile Apps

## Project Structure
```
text-to-calendar-system/
├── api/                          # Milestone A: FastAPI Backend
│   ├── app/
│   │   ├── main.py              # FastAPI app with /parse and /healthz
│   │   ├── models.py            # Pydantic models
│   │   └── services/            # Existing EventParser integration
│   ├── tests/
│   │   └── test_api.py          # Contract tests with fixed now/TZ
│   ├── requirements.txt
│   └── Dockerfile
├── android/                      # Milestone B: Android Native App
│   ├── app/
│   │   ├── src/main/java/com/jacolabs/calendar/
│   │   │   ├── MainActivity.kt
│   │   │   ├── TextProcessorActivity.kt
│   │   │   └── ApiService.kt
│   │   ├── AndroidManifest.xml
│   │   └── res/
│   └── build.gradle
├── ios/                         # Milestone C: iOS Native App
│   ├── CalendarEventApp/
│   │   ├── CalendarEventApp.swift
│   │   ├── ContentView.swift
│   │   └── Info.plist
│   ├── CalendarEventExtension/  # Action/Share Extension
│   │   ├── ActionViewController.swift
│   │   ├── ShareViewController.swift
│   │   └── Info.plist
│   └── CalendarEventApp.xcodeproj
├── browser-extension/           # Milestone D: Browser Extension
│   ├── manifest.json           # Manifest V3
│   ├── background.js
│   ├── content.js
│   └── popup.html
└── shared/                     # Existing Python services
    ├── services/
    ├── models/
    └── tests/
```