# Text-to-Calendar Event System - Architecture Schema

## System Overview

```mermaid
graph TB
    subgraph "User Interfaces"
        BE[Browser Extension]
        WEB[Web Interface]
        API_CLIENT[API Clients]
        MOBILE[Mobile Apps]
    end
    
    subgraph "API Layer"
        FASTAPI[FastAPI Server<br/>api/app/main.py]
        FLASK[Flask Server<br/>api_server.py]
        HEALTH[Health Endpoints<br/>/health, /healthz]
    end
    
    subgraph "Core Parsing Engine"
        EP[Event Parser<br/>services/event_parser.py]
        HP[Hybrid Parser<br/>LLM + Regex]
        DTP[DateTime Parser]
        IE[Info Extractor]
        TMH[Text Merge Helper]
    end
    
    subgraph "Enhancement Services"
        LLM[LLM Service<br/>OpenAI/Ollama]
        CACHE[Cache Manager]
        METRICS[Metrics Collector]
    end
    
    subgraph "Output Formats"
        GCAL[Google Calendar URL]
        ICS[ICS File]
        JSON[JSON Response]
    end
    
    BE --> FASTAPI
    WEB --> FASTAPI
    API_CLIENT --> FASTAPI
    MOBILE --> FASTAPI
    
    BE --> FLASK
    
    FASTAPI --> EP
    FLASK --> EP
    
    EP --> HP
    EP --> DTP
    EP --> IE
    EP --> TMH
    
    HP --> LLM
    EP --> CACHE
    FASTAPI --> METRICS
    
    EP --> GCAL
    EP --> ICS
    FASTAPI --> JSON
    
    FASTAPI --> HEALTH
```

## Browser Extension Architecture

```mermaid
graph TB
    subgraph "Browser Extension Components"
        MANIFEST[manifest.json<br/>Extension Config]
        POPUP[popup.html + popup.js<br/>Main UI]
        BACKGROUND[background.js<br/>Service Worker]
        CONTENT[content.js<br/>Page Integration]
    end
    
    subgraph "Extension Features"
        CTX[Context Menu<br/>Right-click parsing]
        SELECTION[Text Selection<br/>Auto-detect events]
        FALLBACK[Local Fallback Parser<br/>Offline capability]
        SMART[Smart API Fallback<br/>Production → Local]
    end
    
    subgraph "API Endpoints"
        PROD_API[Production API<br/>calendar-api-wrxz.onrender.com]
        LOCAL_API[Local Development<br/>localhost:5000]
        BACKUP[Local Parsing<br/>No API needed]
    end
    
    subgraph "Calendar Integration"
        GOOGLE[Google Calendar<br/>URL Generation]
        OUTLOOK[Outlook Calendar<br/>Future support]
    end
    
    MANIFEST --> POPUP
    MANIFEST --> BACKGROUND
    MANIFEST --> CONTENT
    
    POPUP --> CTX
    POPUP --> SELECTION
    POPUP --> FALLBACK
    POPUP --> SMART
    
    SMART --> PROD_API
    SMART --> LOCAL_API
    SMART --> BACKUP
    
    POPUP --> GOOGLE
    POPUP --> OUTLOOK
    
    BACKGROUND --> CTX
    CONTENT --> SELECTION
```

## Data Flow Architecture

```mermaid
sequenceDiagram
    participant User
    participant Extension
    participant API
    participant Parser
    participant LLM
    participant Calendar
    
    User->>Extension: Select text "Meeting tomorrow 2pm"
    Extension->>Extension: Check local fallback first
    
    alt API Available
        Extension->>API: POST /parse with text
        API->>Parser: Parse event text
        Parser->>Parser: Regex analysis (confidence check)
        
        alt High Confidence (≥0.8)
            Parser->>LLM: Enhance parsing
            LLM->>Parser: Enhanced results
        else Low Confidence (<0.8)
            Parser->>LLM: Full LLM parsing
            LLM->>Parser: LLM results (max 0.5 confidence)
        end
        
        Parser->>API: Return ParsedEvent
        API->>Extension: JSON response
    else API Unavailable
        Extension->>Extension: Use local fallback parser
    end
    
    Extension->>Extension: Build Google Calendar URL
    Extension->>Calendar: Open calendar with event
    Calendar->>User: Show event creation form
```

## Browser Extension File Structure

```
browser-extension/
├── manifest.json              # Extension configuration
├── popup.html                 # Main UI interface
├── popup.js                   # Main logic & API calls
├── background.js              # Service worker for context menus
├── content.js                 # Page content interaction
├── config.js                  # Configuration settings
├── icons/                     # Extension icons
│   ├── icon16.png
│   ├── icon48.png
│   └── icon128.png
└── test-*.html                # Testing interfaces
```

## API Endpoints Schema

```mermaid
graph LR
    subgraph "FastAPI Endpoints"
        ROOT[GET / <br/>Health check]
        PARSE[POST /parse<br/>Main parsing]
        HEALTH[GET /health<br/>Detailed status]
        HEALTHZ[GET /healthz<br/>Simple probe]
        METRICS[GET /metrics<br/>Prometheus metrics]
        CACHE[GET /cache/stats<br/>Cache statistics]
    end
    
    subgraph "Flask Endpoints (Legacy)"
        FLASK_PARSE[POST /parse<br/>Simple parsing]
        FLASK_HEALTH[GET /health<br/>Basic health]
    end
    
    subgraph "Request/Response Format"
        REQ[Request:<br/>{text, timezone, locale, use_llm_enhancement}]
        RESP[Response:<br/>{title, start_datetime, end_datetime, location, confidence_score}]
    end
    
    PARSE --> REQ
    REQ --> RESP
    FLASK_PARSE --> REQ
```

## Parsing Pipeline Architecture

```mermaid
graph TB
    subgraph "Input Processing"
        TEXT[Input Text]
        MERGE[Text Enhancement<br/>Clipboard merge]
        CLEAN[Text Cleaning]
    end
    
    subgraph "Hybrid Parsing Strategy"
        REGEX[Regex Parser<br/>Pattern matching]
        CONFIDENCE{Confidence ≥ 0.8?}
        LLM_ENHANCE[LLM Enhancement<br/>Improve regex results]
        LLM_FULL[Full LLM Parsing<br/>Max confidence 0.5]
    end
    
    subgraph "Field Extraction"
        TITLE[Title Extraction]
        DATETIME[DateTime Parsing]
        LOCATION[Location Detection]
        DURATION[Duration Analysis]
    end
    
    subgraph "Output Generation"
        EVENT[ParsedEvent Object]
        VALIDATION[Validation & Warnings]
        METADATA[Confidence & Metadata]
    end
    
    TEXT --> MERGE
    MERGE --> CLEAN
    CLEAN --> REGEX
    
    REGEX --> CONFIDENCE
    CONFIDENCE -->|Yes| LLM_ENHANCE
    CONFIDENCE -->|No| LLM_FULL
    
    LLM_ENHANCE --> TITLE
    LLM_FULL --> TITLE
    
    TITLE --> DATETIME
    DATETIME --> LOCATION
    LOCATION --> DURATION
    
    DURATION --> EVENT
    EVENT --> VALIDATION
    VALIDATION --> METADATA
```

## Browser Extension UI Flow

```mermaid
graph TB
    subgraph "Extension Activation"
        ICON[Click Extension Icon]
        CONTEXT[Right-click Context Menu]
        SELECTION[Text Selection Detection]
    end
    
    subgraph "Main Interface (popup.html)"
        INPUT[Text Input Field]
        BUTTON[Create Event Button]
        STATUS[Status Messages]
        CONFIDENCE[Confidence Warnings]
    end
    
    subgraph "Processing States"
        LOADING[Processing... State]
        SUCCESS[Success State]
        ERROR[Error State]
        FALLBACK[Fallback State]
    end
    
    subgraph "Calendar Integration"
        GCAL_URL[Google Calendar URL]
        NEW_TAB[Open New Tab]
        CLOSE[Close Extension]
    end
    
    ICON --> INPUT
    CONTEXT --> INPUT
    SELECTION --> INPUT
    
    INPUT --> BUTTON
    BUTTON --> LOADING
    
    LOADING --> SUCCESS
    LOADING --> ERROR
    LOADING --> FALLBACK
    
    SUCCESS --> GCAL_URL
    ERROR --> FALLBACK
    FALLBACK --> GCAL_URL
    
    GCAL_URL --> NEW_TAB
    NEW_TAB --> CLOSE
```

## Key Features Summary

### Browser Extension Features
- **Smart API Fallback**: Tries production API → local API → offline parsing
- **Local Fallback Parser**: Works without any API connection
- **Context Menu Integration**: Right-click to parse selected text
- **Confidence Warnings**: Alerts users when parsing confidence is low
- **Google Calendar Integration**: Direct URL generation for event creation

### API Features
- **Hybrid Parsing**: Combines regex and LLM for optimal accuracy
- **Concurrent Processing**: Async field extraction for better performance
- **Caching System**: Reduces API calls and improves response times
- **Health Monitoring**: Multiple health check endpoints for deployment
- **Rate Limiting**: Prevents API abuse with configurable limits

### Parsing Engine Features
- **Multi-format Support**: Handles various date/time formats
- **Confidence Scoring**: Provides reliability metrics for each field
- **Text Enhancement**: Smart merging with clipboard content
- **Validation System**: Checks for common parsing errors
- **Metadata Tracking**: Detailed information about parsing decisions

This architecture provides a robust, scalable system for converting natural language text into structured calendar events with multiple fallback mechanisms and comprehensive error handling.