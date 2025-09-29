# Gmail Calendar Parsing - Comprehensive Solution Spec

## 🎯 Problem Statement

**Current State**: Gmail text highlighting produces poor calendar events (0-2/4 quality score)
**Desired State**: Screenshot-quality results (4/4 quality score) from Gmail text selections

### Root Cause Analysis

Our analysis reveals the fundamental issue isn't our preprocessing - it's that **Gmail's API limitations prevent access to the full context** that makes screenshot parsing successful.

#### Screenshot Success Factors ✅
- Full email context preserved
- Multiple time references (9:00am, 12:00pm, 12-1pm) 
- Complete location information
- No text truncation by app
- OCR preserves formatting and structure

#### Gmail Failure Factors ❌
- Limited to single contiguous selection
- Text truncation by Gmail's API
- No access to email structure/headers
- Missing context from other parts of email
- No formatting preservation

## 📋 Requirements

### Functional Requirements

**FR1: Context Reconstruction**
- System SHALL intelligently reconstruct full email context from partial Gmail selections
- System SHALL maintain context history from multiple user interactions
- System SHALL infer missing information using email structure patterns

**FR2: Smart Email Parsing**
- System SHALL detect email communication patterns (school, business, personal)
- System SHALL apply domain-specific parsing rules
- System SHALL extract multiple time references and select the most relevant
- System SHALL identify location information from various email sections

**FR3: Multi-Pass Enhancement**
- System SHALL attempt multiple parsing strategies in order of confidence
- System SHALL combine results using confidence-weighted scoring
- System SHALL provide fallback parsing when primary methods fail

**FR4: User-Guided Context**
- System SHALL provide intuitive ways for users to add missing context
- System SHALL learn from user corrections and preferences
- System SHALL offer template-based creation for common event types

**FR5: Quality Assurance**
- System SHALL achieve 4/4 quality score (good title, correct time, location, high confidence)
- System SHALL provide confidence indicators and allow user review
- System SHALL gracefully handle edge cases and provide helpful feedback

### Non-Functional Requirements

**NFR1: Performance**
- Context reconstruction SHALL complete within 2 seconds
- Multi-pass parsing SHALL not exceed 5 seconds total processing time

**NFR2: Usability**
- User-guided context SHALL require no more than 2 additional taps
- System SHALL provide clear feedback about parsing quality and suggestions

**NFR3: Reliability**
- System SHALL maintain 90%+ success rate for common email patterns
- System SHALL fail gracefully with helpful error messages

## 🏗️ Architecture Design

### Component Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Gmail Text Input                         │
└─────────────────┬───────────────────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────────────────┐
│              Context Reconstructor                          │
│  • Clipboard History Analysis                               │
│  • Email Pattern Detection                                  │
│  • Missing Information Inference                            │
└─────────────────┬───────────────────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────────────────┐
│              Smart Email Parser                             │
│  • Domain-Specific Rules (School/Business/Personal)        │
│  • Multi-Time Reference Analysis                           │
│  • Location Extraction Enhancement                         │
└─────────────────┬───────────────────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────────────────┐
│              Multi-Pass Enhancer                           │
│  • Strategy 1: Event-First Parsing                         │
│  • Strategy 2: Time-First Parsing                          │
│  • Strategy 3: Location-First Parsing                      │
│  • Confidence-Weighted Result Combination                  │
└─────────────────┬───────────────────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────────────────┐
│              Quality Validator                              │
│  • 4/4 Quality Score Assessment                            │
│  • User Feedback Integration                               │
│  • Learning from Corrections                               │
└─────────────────┬───────────────────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────────────────┐
│              User-Guided Context UI                        │
│  • "Add More Context" Button                               │
│  • Template Selection                                      │
│  • Quick Corrections Interface                             │
└─────────────────────────────────────────────────────────────┘
```

### Key Components

#### 1. Context Reconstructor
**Purpose**: Build full email context from partial Gmail selections

**Implementation**:
```kotlin
class ContextReconstructor(context: Context) {
    private val clipboardHistory = mutableListOf<ClipboardEntry>()
    private val emailPatterns = EmailPatternDetector()
    
    suspend fun reconstructContext(selection: String): EnhancedContext {
        val history = getRecentClipboardHistory()
        val emailStructure = detectEmailStructure(selection, history)
        val inferredInfo = inferMissingInformation(emailStructure)
        
        return EnhancedContext(
            originalSelection = selection,
            reconstructedText = buildFullContext(emailStructure, inferredInfo),
            confidence = calculateContextConfidence(emailStructure),
            missingElements = identifyMissingElements(emailStructure)
        )
    }
}
```

#### 2. Smart Email Parser
**Purpose**: Apply domain-specific parsing rules based on email type

**Implementation**:
```kotlin
class SmartEmailParser {
    private val schoolEventRules = SchoolEventRules()
    private val businessMeetingRules = BusinessMeetingRules()
    private val personalEventRules = PersonalEventRules()
    
    suspend fun parseWithContext(context: EnhancedContext): ParseResult {
        val emailType = detectEmailType(context)
        val parser = selectParser(emailType)
        
        return parser.parse(context).also { result ->
            enhanceWithMultiTimeAnalysis(result, context)
            enhanceWithLocationExtraction(result, context)
        }
    }
}
```

#### 3. Multi-Pass Enhancer
**Purpose**: Try multiple parsing strategies and combine results

**Implementation**:
```kotlin
class MultiPassEnhancer {
    suspend fun enhanceWithMultipleStrategies(context: EnhancedContext): ParseResult {
        val strategies = listOf(
            EventFirstStrategy(),
            TimeFirstStrategy(), 
            LocationFirstStrategy(),
            TemplateMatchingStrategy()
        )
        
        val results = strategies.map { strategy ->
            strategy.parse(context)
        }
        
        return combineResultsWithConfidenceWeighting(results)
    }
}
```

#### 4. User-Guided Context UI
**Purpose**: Help users provide missing context intuitively

**Implementation**:
```kotlin
@Composable
fun EnhancedParsingUI(
    initialResult: ParseResult,
    onContextAdded: (String) -> Unit,
    onTemplateSelected: (EventTemplate) -> Unit
) {
    // Quality indicator
    QualityScoreIndicator(result = initialResult)
    
    // Quick context additions
    if (initialResult.needsMoreContext) {
        ContextSuggestions(
            suggestions = generateContextSuggestions(initialResult),
            onSuggestionSelected = onContextAdded
        )
    }
    
    // Template selection for common patterns
    if (initialResult.confidence < 0.6) {
        EventTemplateSelector(
            templates = getRelevantTemplates(initialResult),
            onTemplateSelected = onTemplateSelected
        )
    }
}
```

## 📝 Implementation Plan

### Phase 1: Context Reconstruction (2 weeks)
**Tasks**:
1. Implement clipboard history tracking
2. Create email pattern detection algorithms
3. Build context inference engine
4. Add context confidence scoring

**Acceptance Criteria**:
- Can reconstruct 80% of missing context from clipboard history
- Detects school/business/personal email patterns with 90% accuracy
- Context confidence scoring correlates with parsing success

### Phase 2: Smart Email Parsing (2 weeks)
**Tasks**:
1. Implement domain-specific parsing rules
2. Create multi-time reference analysis
3. Enhance location extraction algorithms
4. Add email structure awareness

**Acceptance Criteria**:
- School event parsing improves from 0/4 to 3/4 quality score
- Business meeting parsing achieves 3/4 quality score
- Location extraction success rate > 80%

### Phase 3: Multi-Pass Enhancement (1 week)
**Tasks**:
1. Implement multiple parsing strategies
2. Create confidence-weighted result combination
3. Add fallback hierarchy
4. Optimize performance

**Acceptance Criteria**:
- Multi-pass parsing achieves 4/4 quality score on test cases
- Processing time < 5 seconds
- Graceful degradation when strategies fail

### Phase 4: User-Guided Context UI (1 week)
**Tasks**:
1. Design and implement context suggestion UI
2. Create event template system
3. Add quick correction interface
4. Implement learning from user feedback

**Acceptance Criteria**:
- Users can achieve 4/4 quality score with ≤ 2 additional taps
- Template system covers 80% of common event types
- User corrections improve future parsing accuracy

### Phase 5: Integration & Testing (1 week)
**Tasks**:
1. Integrate all components
2. Comprehensive testing with real Gmail emails
3. Performance optimization
4. User acceptance testing

**Acceptance Criteria**:
- Overall system achieves 4/4 quality score on 90% of test cases
- Performance meets NFR requirements
- User satisfaction > 4.5/5 in testing

## 🧪 Testing Strategy

### Test Cases

**TC1: School Event Email**
```
Input: "On Monday the elementary students will attend the Indigenous Legacy Gathering"
Expected Output: 
- Title: "Indigenous Legacy Gathering"
- Time: Next Monday 9:00 AM (inferred from context)
- Location: "Nathan Phillips Square" (from context reconstruction)
- Quality: 4/4
```

**TC2: Business Meeting Email**
```
Input: "Team standup tomorrow at 10am"
Expected Output:
- Title: "Team Standup"
- Time: Tomorrow 10:00 AM
- Location: (inferred from team context or marked as TBD)
- Quality: 4/4
```

**TC3: Personal Event Email**
```
Input: "Dinner with Sarah Friday night"
Expected Output:
- Title: "Dinner with Sarah"
- Time: Friday 7:00 PM (inferred default)
- Location: (prompt user or use previous context)
- Quality: 3/4 (acceptable with user guidance)
```

## 📊 Success Metrics

### Primary Metrics
- **Quality Score**: 4/4 on 90% of common email patterns
- **User Satisfaction**: > 4.5/5 rating
- **Processing Time**: < 5 seconds for complex parsing

### Secondary Metrics
- **Context Reconstruction Accuracy**: > 80%
- **Template Usage**: 60% of users use templates for faster creation
- **Learning Effectiveness**: 20% improvement in accuracy after user corrections

## 🎯 Expected Outcomes

After implementation, Gmail users should experience:

1. **Screenshot-Quality Results**: 4/4 quality score matching screenshot parsing
2. **Intuitive Context Addition**: Easy ways to provide missing information
3. **Smart Defaults**: System learns common patterns and applies intelligent defaults
4. **Reliable Performance**: Consistent results across different email types
5. **User Confidence**: Clear quality indicators and easy correction methods

This comprehensive approach addresses the root cause (Gmail's API limitations) by building intelligence around context reconstruction and user guidance, rather than just improving regex patterns.