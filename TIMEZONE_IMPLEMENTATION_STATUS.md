# Timezone Implementation Status

## ✅ Completed

### 1. Frontend Updates (static/test.html)
- ✅ Client timezone detection using `Intl.DateTimeFormat().resolvedOptions().timeZone`
- ✅ Sends timezone in both `X-Timezone` header and `client_tz` body parameter
- ✅ Display shows both local time and UTC with toggle button
- ✅ Timezone info panel shows client timezone and offset

### 2. Backend Infrastructure
- ✅ Created `api/app/timezone_utils.py` with comprehensive timezone handling:
  - `validate_timezone()` - Validates IANA timezone strings
  - `get_safe_timezone()` - Safe timezone resolution with fallbacks
  - `get_now_with_timezone()` - Gets current time in client TZ and UTC
  - `coerce_to_local()` - Converts datetimes to local TZ with DST handling
  - `serialize_datetime_pair()` - Serializes to both local and UTC
  - `log_timezone_context()` - Observability logging
  - `handle_dst_transition()` - Explicit DST ambiguity handling
  - `parse_iso_with_timezone()` - ISO string parsing with TZ

### 3. API Models Updated
- ✅ `ParseRequest` now includes:
  - `client_tz` field (takes precedence)
  - `timezone` field (deprecated but maintained for backward compatibility)

- ✅ `ParseResponse` now includes:
  - `start_local` - Start time in client timezone
  - `end_local` - End time in client timezone
  - `start_utc` - Start time in UTC (with Z suffix)
  - `end_utc` - End time in UTC (with Z suffix)
  - `client_tz` - Echo of client timezone
  - Legacy `start_datetime` and `end_datetime` maintained for backward compatibility

## 🔄 In Progress

### 4. Parse Endpoint Integration
The main parse endpoint (`/parse` in `api/app/main.py`) needs to be updated to:

**Required changes**:
```python
# Add import
from .timezone_utils import (
    validate_timezone, get_safe_timezone, get_now_with_timezone,
    coerce_to_local, serialize_datetime_pair, log_timezone_context
)

# In parse_text() function:
# 1. Extract client timezone from header or body
client_tz = http_request.headers.get('X-Timezone') or request.client_tz or request.timezone or 'UTC'

# 2. Validate timezone
if not validate_timezone(client_tz):
    client_tz = 'UTC'
    warnings.append(f"Invalid timezone, using UTC")

# 3. Get timezone-aware current time
now_local, now_utc = get_now_with_timezone(client_tz)

# 4. Log timezone context
log_timezone_context(client_tz, now_local, now_utc, request_id)

# 5. Pass timezone info to parser
current_time = request.now if request.now else now_local

# 6. After parsing, convert datetimes to both local and UTC
tz = get_safe_timezone(client_tz)
start_local = coerce_to_local(parsed_event.start_datetime, tz)
end_local = coerce_to_local(parsed_event.end_datetime, tz)

# 7. Serialize for response
start_utc = start_local.astimezone(timezone.utc) if start_local else None
end_utc = end_local.astimezone(timezone.utc) if end_local else None

# 8. Build response with all timezone formats
return ParseResponse(
    success=True,
    title=parsed_event.title,
    # Legacy fields (for backward compatibility)
    start_datetime=start_local.isoformat() if start_local else None,
    end_datetime=end_local.isoformat() if end_local else None,
    # New timezone-aware fields
    start_local=start_local.isoformat() if start_local else None,
    end_local=end_local.isoformat() if end_local else None,
    start_utc=start_utc.isoformat().replace('+00:00', 'Z') if start_utc else None,
    end_utc=end_utc.isoformat().replace('+00:00', 'Z') if end_utc else None,
    timezone=client_tz,
    client_tz=client_tz,
    ...
)
```

**Location**: Lines 297-500 in `api/app/main.py`

## ⏳ Pending

### 5. Parser Integration
The underlying parsers need timezone support:

**Files to update**:
- `services/regex_date_extractor.py` - Pass timezone to dateutil.parser
- `services/llm_enhancer.py` - Include timezone context in LLM prompts
- `services/hybrid_event_parser.py` - Use timezone-aware datetimes throughout

**Key changes**:
```python
# In regex_date_extractor.py
from datetime import timezone as dt_timezone
from zoneinfo import ZoneInfo

def extract_datetime(self, text: str, client_tz: str = 'UTC'):
    tz = ZoneInfo(client_tz)
    # Use tz when parsing dates
    parsed_date = dateutil.parser.parse(text, default=datetime.now(tz))
    # Ensure result is timezone-aware
    if parsed_date.tzinfo is None:
        parsed_date = parsed_date.replace(tzinfo=tz)
    return parsed_date
```

### 6. Tests
Create comprehensive timezone test suite:

**File**: `tests/test_timezones.py`

**Test cases**:
```python
import pytest
from datetime import datetime
from zoneinfo import ZoneInfo

TIMEZONES = [
    'America/Toronto',      # EST/EDT
    'America/Los_Angeles',  # PST/PDT
    'Europe/London',        # GMT/BST
    'Europe/Berlin',        # CET/CEST
    'Australia/Sydney',     # AEST/AEDT
]

@pytest.mark.parametrize('timezone', TIMEZONES)
def test_tonight_7pm_parsing(timezone):
    """Test 'tonight 7pm' parses correctly in different timezones"""
    result = parse_event("tonight at 7pm", client_tz=timezone)

    # Should be 19:00 in local timezone
    local_time = datetime.fromisoformat(result['start_local'])
    assert local_time.hour == 19

    # UTC conversion should match offset
    utc_time = datetime.fromisoformat(result['start_utc'].replace('Z', '+00:00'))
    expected_offset = local_time.utcoffset()
    assert utc_time == local_time.astimezone(ZoneInfo('UTC'))

def test_dst_transition_fall():
    """Test Nov 2 1:30am during fall-back DST transition"""
    # In America/New_York, Nov 2 2025 at 1:30 AM occurs twice
    result = parse_event(
        "Nov 2 2025 1:30am",
        client_tz="America/New_York",
        now="2025-10-20T12:00:00"
    )

    # Should handle ambiguity (prefer later time with fold=1)
    local_time = datetime.fromisoformat(result['start_local'])
    assert local_time.fold == 1  # Later occurrence

def test_noon_semantics():
    """Test that noon is correctly interpreted as 12:00 PM"""
    result = parse_event("tomorrow at noon", client_tz="America/New_York")
    local_time = datetime.fromisoformat(result['start_local'])
    assert local_time.hour == 12
    assert local_time.minute == 0

def test_midnight_semantics():
    """Test that midnight is correctly interpreted as 00:00"""
    result = parse_event("tomorrow at midnight", client_tz="America/New_York")
    local_time = datetime.fromisoformat(result['start_local'])
    assert local_time.hour == 0
    assert local_time.minute == 0
```

### 7. Server Configuration
Update deployment configuration:

**docker-compose.yml** or **Render settings**:
```yaml
environment:
  - TZ=UTC              # Run server in UTC
  - DEFAULT_TZ=UTC      # Fallback timezone
```

### 8. Documentation
Update API documentation:

**Files**:
- `docs/API.md` - Document new timezone fields
- `BETA_TESTING_GUIDE.md` - Add timezone testing scenarios
- `quickstart.md` - Show timezone examples

## 📊 Testing Progress

### Manual Testing Needed:
- [ ] Toronto (EST/EDT): "tonight at 7pm" returns 19:00 -04:00 or -05:00
- [ ] Los Angeles (PST/PDT): Same text, different offset
- [ ] London (GMT/BST): Verify offset changes with DST
- [ ] Sydney (AEST/AEDT): Southern hemisphere DST
- [ ] UTC: Baseline test

### Expected Behavior:
1. Web tester in Toronto shows "7:00 PM EDT" for "tonight 7pm"
2. Same event in device calendar shows identical time
3. UTC toggle shows correct UTC equivalent
4. API logs show both ref_local and ref_utc

## 🚀 Deployment Strategy

### Phase 1: Backend Update (Priority)
1. Update `main.py` parse endpoint with timezone handling
2. Deploy to staging/dev environment
3. Test with curl/Postman

### Phase 2: Parser Updates (Critical)
1. Update regex_date_extractor with timezone support
2. Update llm_enhancer to respect timezones
3. Test parsing accuracy

### Phase 3: Testing & Validation
1. Run automated timezone tests
2. Manual testing across timezones
3. Beta tester validation

### Phase 4: Documentation
1. Update API docs
2. Update testing guides
3. Add timezone troubleshooting

## 🎯 Definition of Done

- [ ] Parse endpoint accepts `client_tz` from header or body
- [ ] Response includes `start_local`, `end_local`, `start_utc`, `end_utc`
- [ ] All datetimes are timezone-aware (no naive datetimes)
- [ ] Web tester shows correct local time matching device
- [ ] UTC toggle displays correct UTC time
- [ ] Timezone logging for debugging
- [ ] Tests pass across 5+ timezones
- [ ] DST transitions handled correctly
- [ ] Documentation updated
- [ ] Backward compatibility maintained

## 📝 Current Status Summary

**Completed**: 40%
- ✅ Frontend ready
- ✅ Models updated
- ✅ Utility functions created

**In Progress**: 30%
- 🔄 Parse endpoint integration

**Pending**: 30%
- ⏳ Parser timezone support
- ⏳ Test suite
- ⏳ Documentation

## 🔧 Quick Start for Completion

To finish the implementation:

1. **Update `api/app/main.py`** (30 minutes)
   - Add timezone utility imports
   - Extract client_tz from request
   - Convert parsed datetimes to local and UTC
   - Update response with new fields

2. **Update parsers** (1-2 hours)
   - Modify regex_date_extractor
   - Modify llm_enhancer
   - Test parsing accuracy

3. **Create tests** (1 hour)
   - Write timezone test suite
   - Run tests across timezones
   - Fix any issues

4. **Manual verification** (30 minutes)
   - Test in web interface
   - Verify with device calendar
   - Check multiple timezones

Total estimated time: **3-4 hours**

## 💡 Notes

- All changes maintain backward compatibility
- Legacy `start_datetime`/`end_datetime` still work
- Frontend gracefully handles both old and new API responses
- Server should run with `TZ=UTC` to avoid confusion
- Client timezone is the source of truth for interpretation

---

*Last Updated: October 19, 2025*
