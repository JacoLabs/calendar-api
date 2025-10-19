# Repository Cleanup Analysis

Analysis performed: October 19, 2025

## 🎯 Currently Used Services (via API)

These are actively imported and used by the production API:

### Core Parsing
- ✅ `event_parser.py` - Main entry point (API uses this)
- ✅ `hybrid_event_parser.py` - Modern parser (used by event_parser)
- ✅ `regex_date_extractor.py` - Datetime extraction (used by hybrid)
- ✅ `title_extractor.py` - Title extraction
- ✅ `advanced_location_extractor.py` - Location extraction

### LLM Integration
- ✅ `llm_service.py` - LLM provider abstraction
- ✅ `llm_enhancer.py` - LLM enhancement logic
- ✅ `llm_prompts.py` - Prompt templates
- ✅ `llm_text_enhancer.py` - Text enhancement
- ✅ `text_merge_helper.py` - Smart text merging

### Backup/Fallback Systems
- ✅ `deterministic_backup_layer.py` - Deterministic fallback
- ✅ `duckling_extractor.py` - Duckling integration
- ✅ `recognizers_extractor.py` - Microsoft Recognizers

### Routing & Optimization
- ✅ `per_field_confidence_router.py` - Per-field routing
- ✅ `performance_optimizer.py` - Performance optimizations
- ✅ `cache_manager.py` - Caching system

### Supporting Services
- ✅ `comprehensive_datetime_parser.py` - Comprehensive datetime
- ✅ `smart_title_extractor.py` - Smart title extraction
- ✅ `event_extractor.py` - Event information extraction

## ⚠️ LEGACY/PROBLEMATIC Services

### 🔴 DANGEROUS - Known to cause bugs

**`datetime_parser.py`** - **LEGACY - DO NOT USE**
- Missing "noon" support (just caused a bug!)
- Missing "midnight" support
- Less comprehensive than regex_date_extractor
- Used by old `parse_text()` method
- **RECOMMENDATION**: Keep for now (EventParser still references it in parse_text), but mark as deprecated

### 🟡 POTENTIALLY UNUSED Services

These exist but might not be actively used:

**Need to investigate**:
- `master_event_parser.py` - Might be another legacy parser
- `startup_optimizer.py` - Might be used only at startup
- `performance_monitor.py` - Might be monitoring only
- `duration_processor.py` - Might be imported indirectly
- `recurrence_processor.py` - Might be imported indirectly
- `date_formatter.py` - Might be utility only

## 📁 Test Files Organization

### Current State
Test files are scattered across:
- `/` (root) - 40+ test files
- `/tests/` - 70+ test files
- `/api/` - 4 test files
- `/api/tests/` - 3 test files
- `/scripts/` - 1 test file

### Proposed Structure

```
tests/
├── unit/                      # Unit tests for individual components
│   ├── services/              # Service layer tests
│   ├── models/                # Model tests
│   └── api/                   # API tests
├── integration/               # Integration tests
│   ├── parser_integration/
│   ├── llm_integration/
│   └── api_integration/
├── e2e/                       # End-to-end tests
│   ├── android/
│   ├── ios/
│   └── browser/
├── performance/               # Performance/benchmark tests
├── golden/                    # Golden test suites
└── fixtures/                  # Shared test data

test_results_demo/             # Keep separate - demo outputs
```

## 🗂️ Files to Move

### Root → tests/integration/
```
test_android_access_methods.py
test_android_calendar_fix.py
test_android_flow.py
test_android_improvements.py
test_api_due_date.py
test_api_fix.py
test_api_parsing.py
test_api_sync.py
test_canadian_extraction.py
test_deployment.py
test_due_date_parsing.py
test_duration_validation.py
test_enhanced_api_endpoints.py
test_enhanced_client_integration.py
test_enhanced_merge.py
test_final_android_fix.py
test_gmail_fix_final.py
test_gmail_fix_focused.py
test_gmail_selection_fix.py
test_integration_simple.py
test_ios_basic.py
test_ios_flow.py
test_local_api.py
test_location_pattern.py
test_multiline_fix.py
test_multiple_cases.py
test_preprocessing.py
test_structured_title.py
test_title_extraction.py
test_title_fix.py
test_title_pattern.py
test_title_quality_merge.py
```

### Root → tests/golden/
```
test_golden_suite_validation.py
run_golden_tests.py
test_milestones.py
```

### Root → tests/performance/
```
test_llm_performance.py
test_performance_optimizations.py
test_live_api.py
test_production_validation.py
```

### Root → tests/integration/llm/
```
test_llm_enhancement.py
test_llm_vs_heuristic.py
test_ollama_integration.py
```

### api/ → tests/unit/api/
```
api/test_async_simple.py
api/test_openapi.py
api/test_server_startup.py
api/test_task_completion.py
```

### scripts/ → tests/integration/
```
scripts/test_llm_functionality.py
```

### tests/ - Already in right place, but reorganize:
Keep in `tests/` but potentially reorganize into subdirectories

## 🚨 High Priority: Legacy Code That Could Cause Bugs

### 1. `datetime_parser.py` (CRITICAL)
**Issue**: Missing support for common time expressions
- No "noon" support → caused production bug
- No "midnight" support
- Less comprehensive than `regex_date_extractor.py`

**Current Usage**:
- Called by `EventParser.parse_text()` (legacy method)
- NOT called by `EventParser.parse_event_text()` (modern method)

**Action**:
- [ ] Add deprecation warning to the file
- [ ] Add comment: "LEGACY - Use regex_date_extractor instead"
- [ ] Eventually remove once parse_text() is phased out

### 2. `master_event_parser.py`
**Need to check**: Is this used? Sounds like another top-level parser that could conflict

### 3. Multiple Title Extractors
We have:
- `title_extractor.py` (used)
- `smart_title_extractor.py` (used)
- `event_extractor.py` (has title extraction too)

**Risk**: Confusion about which to use, inconsistent results

## 📋 Cleanup Checklist

### Phase 1: Test Organization (Low Risk)
- [ ] Create new test directory structure
- [ ] Move root test files to appropriate subdirectories
- [ ] Move api test files
- [ ] Move scripts test files
- [ ] Update test runners (`run_comprehensive_tests.py`, etc.)
- [ ] Update CI/CD if applicable
- [ ] Verify all tests still run

### Phase 2: Mark Legacy Code (Low Risk)
- [ ] Add deprecation comments to `datetime_parser.py`
- [ ] Add warnings when legacy methods are called
- [ ] Document which components are legacy vs modern

### Phase 3: Identify Truly Unused Files (Medium Risk)
- [ ] Check if `master_event_parser.py` is used
- [ ] Check all services in `/services/` for actual usage
- [ ] Create list of confirmed unused files

### Phase 4: Archive Unused Code (Medium Risk)
- [ ] Create `legacy/` or `archive/` directory
- [ ] Move confirmed unused files there
- [ ] Update any imports (should be none if truly unused)
- [ ] Keep for reference but out of main codebase

### Phase 5: Remove Dead Code (High Risk - Do Last)
- [ ] After 1-2 months in archive, consider deletion
- [ ] Only if confirmed no usage
- [ ] Git history preserves it anyway

## 🎯 Immediate Actions (This Session)

### 1. Organize Test Files (30-45 minutes)
Move scattered test files into organized structure

### 2. Mark Legacy datetime_parser.py (5 minutes)
Add clear warnings so this doesn't cause bugs again

### 3. Create inventory document (Done - this file!)
Document what's used vs unused

## 📊 Statistics

**Total Test Files**: ~120
- Root directory: 42 files
- /tests/ directory: 70+ files
- Other locations: 8 files

**Services**: 40+ files
- Actively used: ~20 files
- Legacy/unclear: ~10 files
- Utilities: ~10 files

## 🔍 Files That Need Investigation

These need manual review to determine if they're used:

1. `services/master_event_parser.py`
2. `services/duration_processor.py`
3. `services/recurrence_processor.py`
4. `services/performance_monitor.py`
5. `services/startup_optimizer.py`
6. `services/date_formatter.py`
7. `services/validation_service.py`

## ⚠️ Important Notes

1. **Don't delete without testing** - Even "unused" code might be imported somewhere
2. **Archive first, delete later** - Move to archive/ before deleting
3. **Update this document** as you learn more about what's actually used
4. **Test after each phase** - Don't break production!

---

*Last Updated: October 19, 2025*
*Status: Analysis Complete - Ready for cleanup*
