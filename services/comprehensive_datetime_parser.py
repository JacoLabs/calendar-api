"""
Comprehensive DateTime extraction service for parsing dates and times from natural language text.
Supports advanced date formats, typo tolerance, natural phrases, and comprehensive time parsing.
"""

import re
from datetime import datetime, time, date, timedelta
from typing import Optional, Tuple, List, Dict, Any, Union
from dataclasses import dataclass
import calendar


@dataclass
class DateTimeResult:
    """Represents the result of comprehensive date/time parsing."""
    start_datetime: Optional[datetime]
    end_datetime: Optional[datetime]
    confidence: float
    extraction_method: str  # "explicit", "relative", "inferred"
    ambiguities: List[str]  # Multiple possible interpretations
    raw_text: str  # Original text that was parsed
    field_confidence: Dict[str, float]  # Individual field confidence scores
    parsing_issues: List[str]  # Issues encountered during parsing
    suggestions: List[str]  # Suggestions for improvement


class ComprehensiveDateTimeParser:
    """
    Advanced service for extracting dates and times from natural language text.
    Handles comprehensive real-world scenarios including typos, natural phrases, and complex formats.
    """
    
    def __init__(self):
        self._compile_patterns()
        self._setup_mappings()
    
    def _compile_patterns(self):
        """Compile comprehensive regex patterns for date and time matching."""
        
        # Enhanced date patterns with typo tolerance
        self.date_patterns = {
            # Explicit dates with various formats
            'weekday_month_dd_yyyy': re.compile(
                r'\b(monday|tuesday|wednesday|thursday|friday|saturday|sunday),?\s+'
                r'(jan|january|feb|february|mar|march|apr|april|may|jun|june|'
                r'jul|july|aug|august|sep|september|oct|october|nov|november|dec|december)\s+'
                r'(\d{1,2})(?:st|nd|rd|th)?,?\s+(\d{4})\b',
                re.IGNORECASE
            ),
            'month_dd_yyyy': re.compile(
                r'\b(jan|january|feb|february|mar|march|apr|april|may|jun|june|'
                r'jul|july|aug|august|sep|september|oct|october|nov|november|dec|december)\s+'
                r'(\d{1,2})(?:st|nd|rd|th)?,?\s+(\d{4})\b',
                re.IGNORECASE
            ),
            'month_dd': re.compile(
                r'\b(jan|january|feb|february|mar|march|apr|april|may|jun|june|'
                r'jul|july|aug|august|sep|september|oct|october|nov|november|dec|december)\s+'
                r'(\d{1,2})(?:st|nd|rd|th)?\b',
                re.IGNORECASE
            ),
            'mm_dd_yyyy': re.compile(
                r'\b(\d{1,2})[\/\-\.](\d{1,2})[\/\-\.](\d{4})\b'
            ),
            'dd_mm_yyyy': re.compile(
                r'\b(\d{1,2})[\/\-\.](\d{1,2})[\/\-\.](\d{4})\b'
            ),
            'yyyy_mm_dd': re.compile(
                r'\b(\d{4})[\/\-\.](\d{1,2})[\/\-\.](\d{1,2})\b'
            ),
            # Inline dates (Sep 29 - assumes current year)
            'month_dd_inline': re.compile(
                r'\b(jan|january|feb|february|mar|march|apr|april|may|jun|june|'
                r'jul|july|aug|august|sep|september|oct|october|nov|november|dec|december)\s+'
                r'(\d{1,2})(?:st|nd|rd|th)?\b(?!\s*,?\s*\d{4})',
                re.IGNORECASE
            ),
            # Typo-tolerant date patterns
            'month_dd_no_space': re.compile(
                r'\b(jan|january|feb|february|mar|march|apr|april|may|jun|june|'
                r'jul|july|aug|august|sep|september|oct|october|nov|november|dec|december)(\d{1,2})(?:st|nd|rd|th)?\b',
                re.IGNORECASE
            ),
            'month_period_dd': re.compile(
                r'\b(jan|january|feb|february|mar|march|apr|april|may|jun|june|'
                r'jul|july|aug|august|sep|september|oct|october|nov|november|dec|december)\.\s*(\d{1,2})(?:st|nd|rd|th)?\b',
                re.IGNORECASE
            )
        }
        
        # Enhanced time patterns with typo tolerance
        self.time_patterns = {
            # Standard formats
            '12_hour_am_pm': re.compile(
                r'\b(\d{1,2})(?::(\d{2}))?\s*(a\.?m\.?|p\.?m\.?)\b',
                re.IGNORECASE
            ),
            '24_hour': re.compile(
                r'\b(\d{1,2}):(\d{2})\b'
            ),
            '24_hour_hrs': re.compile(
                r'\b(\d{1,2}):(\d{2})hrs?\b',
                re.IGNORECASE
            ),
            # Typo-tolerant formats - more comprehensive
            'typo_am_pm': re.compile(
                r'\b(\d{1,2})(?::(\d{2}))?\s*(a\s*\.?\s*m\.?|p\s*\.?\s*m\.?|am|pm)\b',
                re.IGNORECASE
            ),
            'typo_time_space': re.compile(
                r'\b(\d{1,2})\s*:\s*(\d{2})\s*(a\s*\.?\s*m\.?|p\s*\.?\s*m\.?|am|pm)\b',
                re.IGNORECASE
            ),
            # Special time words
            'noon': re.compile(r'\bnoon\b', re.IGNORECASE),
            'midnight': re.compile(r'\bmidnight\b', re.IGNORECASE),
            # Relative times
            'after_lunch': re.compile(r'\bafter\s+lunch\b', re.IGNORECASE),
            'before_school': re.compile(r'\bbefore\s+school\b', re.IGNORECASE),
            'end_of_day': re.compile(r'\bend\s+of\s+(the\s+)?day\b', re.IGNORECASE),
            'morning': re.compile(r'\bin\s+the\s+morning\b', re.IGNORECASE),
            'afternoon': re.compile(r'\bin\s+the\s+afternoon\b', re.IGNORECASE),
            'evening': re.compile(r'\bin\s+the\s+evening\b', re.IGNORECASE)
        }
        
        # Time range patterns with enhanced dash/hyphen support
        self.time_range_patterns = {
            'range_12hour': re.compile(
                r'\b(\d{1,2})(?::(\d{2}))?\s*(a\.?m\.?|p\.?m\.?)\s*[–\-−~]\s*'
                r'(\d{1,2})(?::(\d{2}))?\s*(a\.?m\.?|p\.?m\.?)\b',
                re.IGNORECASE
            ),
            'range_12hour_shared_ampm': re.compile(
                r'\b(\d{1,2})(?::(\d{2}))?\s*[–\-−~]\s*(\d{1,2})(?::(\d{2}))?\s*(a\.?m\.?|p\.?m\.?)\b',
                re.IGNORECASE
            ),
            'range_24hour': re.compile(
                r'\b(\d{1,2}):(\d{2})\s*[–\-−~]\s*(\d{1,2}):(\d{2})\b'
            ),
            'from_to_12hour': re.compile(
                r'\bfrom\s+(\d{1,2})(?::(\d{2}))?\s*(a\.?m\.?|p\.?m\.?)\s+to\s+'
                r'(\d{1,2})(?::(\d{2}))?\s*(a\.?m\.?|p\.?m\.?)\b',
                re.IGNORECASE
            ),
            'from_to_24hour': re.compile(
                r'\bfrom\s+(\d{1,2}):(\d{2})\s+to\s+(\d{1,2}):(\d{2})\b'
            )
        }
        
        # Relative date patterns with natural phrases
        self.relative_date_patterns = {
            'today': re.compile(r'\btoday\b', re.IGNORECASE),
            'tomorrow': re.compile(r'\btomorrow\b', re.IGNORECASE),
            'yesterday': re.compile(r'\byesterday\b', re.IGNORECASE),
            'next_weekday': re.compile(
                r'\bnext\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b',
                re.IGNORECASE
            ),
            'this_weekday': re.compile(
                r'\bthis\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b',
                re.IGNORECASE
            ),
            'in_days': re.compile(
                r'\bin\s+(\d+|one|two|three|four|five|six|seven|eight|nine|ten)\s+(days?)\b',
                re.IGNORECASE
            ),
            'in_weeks': re.compile(
                r'\bin\s+(\d+|one|two|three|four)\s+(weeks?)\b',
                re.IGNORECASE
            ),
            'next_week': re.compile(r'\bnext\s+week\b', re.IGNORECASE),
            'this_week': re.compile(r'\bthis\s+week\b', re.IGNORECASE),
            'end_of_month': re.compile(r'\bend\s+of\s+(the\s+)?month\b', re.IGNORECASE),
            'beginning_of_month': re.compile(r'\b(beginning|start)\s+of\s+(the\s+)?month\b', re.IGNORECASE),
            'first_day_back': re.compile(
                r'\b(the\s+)?first\s+day\s+back\s+(after\s+)?(break|vacation|holiday)\b',
                re.IGNORECASE
            )
        }
        
        # Duration patterns
        self.duration_patterns = {
            'for_hours': re.compile(
                r'\bfor\s+(\d+(?:\.\d+)?)\s+(hours?|hrs?)\b',
                re.IGNORECASE
            ),
            'for_minutes': re.compile(
                r'\bfor\s+(\d+)\s+(minutes?|mins?)\b',
                re.IGNORECASE
            ),
            'duration_long': re.compile(
                r'\b(\d+)\s+(minutes?|mins?)\s+long\b',
                re.IGNORECASE
            ),
            'hours_long': re.compile(
                r'\b(\d+(?:\.\d+)?)\s+(hours?|hrs?)\s+long\b',
                re.IGNORECASE
            )
        }
    
    def _setup_mappings(self):
        """Setup mapping dictionaries for month names, weekdays, and number words."""
        
        # Month name to number mapping (supports abbreviations)
        self.month_names = {
            'january': 1, 'jan': 1,
            'february': 2, 'feb': 2,
            'march': 3, 'mar': 3,
            'april': 4, 'apr': 4,
            'may': 5,
            'june': 6, 'jun': 6,
            'july': 7, 'jul': 7,
            'august': 8, 'aug': 8,
            'september': 9, 'sep': 9,
            'october': 10, 'oct': 10,
            'november': 11, 'nov': 11,
            'december': 12, 'dec': 12
        }
        
        # Weekday name to number mapping (Monday = 0)
        self.weekday_names = {
            'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3,
            'friday': 4, 'saturday': 5, 'sunday': 6
        }
        
        # Number words to digits
        self.number_words = {
            'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5,
            'six': 6, 'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10
        }
        
        # Relative time mappings
        self.relative_times = {
            'after_lunch': time(13, 0),  # 1:00 PM
            'before_school': time(8, 0),  # 8:00 AM
            'end_of_day': time(17, 0),   # 5:00 PM
            'morning': time(9, 0),       # 9:00 AM
            'afternoon': time(14, 0),    # 2:00 PM
            'evening': time(18, 0)       # 6:00 PM
        }
    
    def parse_datetime(self, text: str, prefer_dd_mm: bool = False) -> DateTimeResult:
        """
        Parse comprehensive date and time information from text.
        
        Args:
            text: Input text to parse
            prefer_dd_mm: If True, interpret ambiguous dates as DD/MM instead of MM/DD
            
        Returns:
            DateTimeResult with comprehensive parsing information
        """
        # Initialize result
        result = DateTimeResult(
            start_datetime=None,
            end_datetime=None,
            confidence=0.0,
            extraction_method="none",
            ambiguities=[],
            raw_text=text,
            field_confidence={},
            parsing_issues=[],
            suggestions=[]
        )
        
        # Extract dates
        date_results = self._extract_comprehensive_dates(text, prefer_dd_mm)
        
        # Extract times
        time_results = self._extract_comprehensive_times(text)
        
        # Extract time ranges
        range_results = self._extract_time_ranges(text)
        
        # Extract durations
        duration_results = self._extract_durations(text)
        
        # Combine and evaluate results
        combined_result = self._combine_datetime_components(
            text, date_results, time_results, range_results, duration_results
        )
        
        # Update result with best combination
        if combined_result:
            result.start_datetime = combined_result['start_datetime']
            result.end_datetime = combined_result.get('end_datetime')
            result.confidence = combined_result['confidence']
            result.extraction_method = combined_result['method']
            result.field_confidence = combined_result['field_confidence']
            result.ambiguities = combined_result.get('ambiguities', [])
            result.parsing_issues = combined_result.get('issues', [])
            result.suggestions = combined_result.get('suggestions', [])
        
        return result
    
    def _extract_comprehensive_dates(self, text: str, prefer_dd_mm: bool = False) -> List[Dict[str, Any]]:
        """Extract all possible date interpretations from text."""
        results = []
        
        # Extract explicit dates
        for pattern_name, pattern in self.date_patterns.items():
            for match in pattern.finditer(text):
                date_result = self._parse_date_match(match, pattern_name, prefer_dd_mm)
                if date_result:
                    results.append(date_result)
        
        # Extract relative dates
        for pattern_name, pattern in self.relative_date_patterns.items():
            for match in pattern.finditer(text):
                date_result = self._parse_relative_date_match(match, pattern_name)
                if date_result:
                    results.append(date_result)
        
        return results
    
    def _parse_date_match(self, match: re.Match, pattern_name: str, prefer_dd_mm: bool) -> Optional[Dict[str, Any]]:
        """Parse a specific date match based on pattern type."""
        try:
            current_year = datetime.now().year
            
            if pattern_name == 'weekday_month_dd_yyyy':
                weekday = match.group(1).lower()
                month_name = match.group(2).lower()
                day = int(match.group(3))
                year = int(match.group(4))
                month = self.month_names[month_name]
                
                date_obj = date(year, month, day)
                
                # Validate weekday matches
                actual_weekday = date_obj.weekday()
                expected_weekday = self.weekday_names[weekday]
                
                confidence = 0.95
                issues = []
                if actual_weekday != expected_weekday:
                    confidence = 0.7
                    issues.append(f"Weekday mismatch: {weekday} vs actual {list(self.weekday_names.keys())[actual_weekday]}")
                
                return {
                    'date': date_obj,
                    'confidence': confidence,
                    'method': 'explicit',
                    'matched_text': match.group(0),
                    'position': (match.start(), match.end()),
                    'issues': issues
                }
            
            elif pattern_name in ['month_dd_yyyy', 'month_dd', 'month_dd_inline', 'month_dd_no_space', 'month_period_dd']:
                month_name = match.group(1).lower()
                day = int(match.group(2))
                
                if pattern_name == 'month_dd_yyyy':
                    year = int(match.group(3))
                else:
                    year = current_year
                
                month = self.month_names[month_name]
                date_obj = date(year, month, day)
                
                # Lower confidence for typo patterns
                if pattern_name in ['month_dd_no_space', 'month_period_dd']:
                    confidence = 0.8
                else:
                    confidence = 0.95 if pattern_name == 'month_dd_yyyy' else 0.85
                
                return {
                    'date': date_obj,
                    'confidence': confidence,
                    'method': 'explicit',
                    'matched_text': match.group(0),
                    'position': (match.start(), match.end()),
                    'issues': []
                }
            
            elif pattern_name in ['mm_dd_yyyy', 'dd_mm_yyyy']:
                num1, num2, year = int(match.group(1)), int(match.group(2)), int(match.group(3))
                
                # Determine month and day based on preference and validation
                if prefer_dd_mm or pattern_name == 'dd_mm_yyyy':
                    day, month = num1, num2
                else:
                    month, day = num1, num2
                
                # Validate ranges
                if not (1 <= month <= 12 and 1 <= day <= 31):
                    # Try swapping if invalid
                    if 1 <= day <= 12 and 1 <= month <= 31:
                        month, day = day, month
                    else:
                        return None
                
                date_obj = date(year, month, day)
                
                # Check for ambiguity
                ambiguities = []
                if num1 <= 12 and num2 <= 12 and num1 != num2:
                    alt_date = date(year, num2, num1) if prefer_dd_mm else date(year, num1, num2)
                    ambiguities.append(f"Could also be {alt_date.strftime('%Y-%m-%d')}")
                
                confidence = 0.8 if ambiguities else 0.9
                
                return {
                    'date': date_obj,
                    'confidence': confidence,
                    'method': 'explicit',
                    'matched_text': match.group(0),
                    'position': (match.start(), match.end()),
                    'ambiguities': ambiguities,
                    'issues': []
                }
            
            elif pattern_name == 'yyyy_mm_dd':
                year, month, day = int(match.group(1)), int(match.group(2)), int(match.group(3))
                
                if 1 <= month <= 12 and 1 <= day <= 31:
                    date_obj = date(year, month, day)
                    
                    return {
                        'date': date_obj,
                        'confidence': 0.95,
                        'method': 'explicit',
                        'matched_text': match.group(0),
                        'position': (match.start(), match.end()),
                        'issues': []
                    }
            
        except (ValueError, KeyError, calendar.IllegalMonthError):
            return None
        
        return None
    
    def _parse_relative_date_match(self, match: re.Match, pattern_name: str) -> Optional[Dict[str, Any]]:
        """Parse a relative date match."""
        try:
            today = date.today()
            
            if pattern_name == 'today':
                return {
                    'date': today,
                    'confidence': 0.98,
                    'method': 'relative',
                    'matched_text': match.group(0),
                    'position': (match.start(), match.end()),
                    'issues': []
                }
            
            elif pattern_name == 'tomorrow':
                return {
                    'date': today + timedelta(days=1),
                    'confidence': 0.98,
                    'method': 'relative',
                    'matched_text': match.group(0),
                    'position': (match.start(), match.end()),
                    'issues': []
                }
            
            elif pattern_name == 'yesterday':
                return {
                    'date': today - timedelta(days=1),
                    'confidence': 0.98,
                    'method': 'relative',
                    'matched_text': match.group(0),
                    'position': (match.start(), match.end()),
                    'issues': []
                }
            
            elif pattern_name == 'next_weekday':
                weekday_name = match.group(1).lower()
                target_weekday = self.weekday_names[weekday_name]
                target_date = self._get_next_weekday(today, target_weekday)
                
                return {
                    'date': target_date,
                    'confidence': 0.9,
                    'method': 'relative',
                    'matched_text': match.group(0),
                    'position': (match.start(), match.end()),
                    'issues': []
                }
            
            elif pattern_name == 'this_weekday':
                weekday_name = match.group(1).lower()
                target_weekday = self.weekday_names[weekday_name]
                target_date = self._get_this_weekday(today, target_weekday)
                
                return {
                    'date': target_date,
                    'confidence': 0.85,
                    'method': 'relative',
                    'matched_text': match.group(0),
                    'position': (match.start(), match.end()),
                    'issues': []
                }
            
            elif pattern_name == 'in_days':
                days_str = match.group(1).lower()
                days = self.number_words.get(days_str, int(days_str) if days_str.isdigit() else 0)
                
                if days > 0:
                    return {
                        'date': today + timedelta(days=days),
                        'confidence': 0.9,
                        'method': 'relative',
                        'matched_text': match.group(0),
                        'position': (match.start(), match.end()),
                        'issues': []
                    }
            
            elif pattern_name == 'in_weeks':
                weeks_str = match.group(1).lower()
                weeks = self.number_words.get(weeks_str, int(weeks_str) if weeks_str.isdigit() else 0)
                
                if weeks > 0:
                    return {
                        'date': today + timedelta(weeks=weeks),
                        'confidence': 0.9,
                        'method': 'relative',
                        'matched_text': match.group(0),
                        'position': (match.start(), match.end()),
                        'issues': []
                    }
            
            elif pattern_name == 'next_week':
                return {
                    'date': today + timedelta(weeks=1),
                    'confidence': 0.85,
                    'method': 'relative',
                    'matched_text': match.group(0),
                    'position': (match.start(), match.end()),
                    'issues': []
                }
            
            elif pattern_name == 'end_of_month':
                # Get last day of current month
                last_day = calendar.monthrange(today.year, today.month)[1]
                end_date = date(today.year, today.month, last_day)
                
                return {
                    'date': end_date,
                    'confidence': 0.8,
                    'method': 'inferred',
                    'matched_text': match.group(0),
                    'position': (match.start(), match.end()),
                    'issues': []
                }
            
            elif pattern_name == 'first_day_back':
                # This is context-dependent, assume next Monday as a reasonable default
                next_monday = self._get_next_weekday(today, 0)  # Monday = 0
                
                return {
                    'date': next_monday,
                    'confidence': 0.6,
                    'method': 'inferred',
                    'matched_text': match.group(0),
                    'position': (match.start(), match.end()),
                    'issues': ['Context-dependent phrase, assumed next Monday'],
                    'suggestions': ['Please specify the exact date for "first day back"']
                }
            
        except (ValueError, KeyError):
            return None
        
        return None
    
    def _extract_comprehensive_times(self, text: str) -> List[Dict[str, Any]]:
        """Extract all possible time interpretations from text."""
        results = []
        
        # Extract explicit times - prioritize AM/PM patterns over 24-hour when AM/PM is present
        am_pm_patterns = ['12_hour_am_pm', 'typo_am_pm', 'typo_time_space']
        other_patterns = [name for name in self.time_patterns.keys() if name not in am_pm_patterns]
        
        # First try AM/PM patterns
        for pattern_name in am_pm_patterns:
            pattern = self.time_patterns[pattern_name]
            for match in pattern.finditer(text):
                time_result = self._parse_time_match(match, pattern_name)
                if time_result:
                    results.append(time_result)
        
        # Only try other patterns if no AM/PM patterns matched
        if not results:
            for pattern_name in other_patterns:
                pattern = self.time_patterns[pattern_name]
                for match in pattern.finditer(text):
                    time_result = self._parse_time_match(match, pattern_name)
                    if time_result:
                        results.append(time_result)
        
        return results
    
    def _parse_time_match(self, match: re.Match, pattern_name: str) -> Optional[Dict[str, Any]]:
        """Parse a specific time match based on pattern type."""
        try:
            if pattern_name in ['12_hour_am_pm', 'typo_am_pm', 'typo_time_space']:
                hour = int(match.group(1))
                minute = int(match.group(2)) if match.group(2) else 0
                am_pm_raw = match.group(3).lower()
                
                # Normalize AM/PM with typo tolerance
                am_pm = self._normalize_am_pm(am_pm_raw)
                
                if 1 <= hour <= 12 and 0 <= minute <= 59:
                    if am_pm == 'pm' and hour != 12:
                        hour += 12
                    elif am_pm == 'am' and hour == 12:
                        hour = 0
                    
                    time_obj = time(hour, minute)
                    confidence = 0.95 if pattern_name == '12_hour_am_pm' else 0.9
                    
                    return {
                        'time': time_obj,
                        'confidence': confidence,
                        'method': 'explicit',
                        'matched_text': match.group(0),
                        'position': (match.start(), match.end()),
                        'issues': []
                    }
            
            elif pattern_name in ['24_hour', '24_hour_hrs']:
                hour = int(match.group(1))
                minute = int(match.group(2))
                
                if 0 <= hour <= 23 and 0 <= minute <= 59:
                    time_obj = time(hour, minute)
                    
                    # Lower confidence for typo patterns
                    confidence = 0.85 if pattern_name == '24_hour_hrs' else 0.9
                    
                    return {
                        'time': time_obj,
                        'confidence': confidence,
                        'method': 'explicit',
                        'matched_text': match.group(0),
                        'position': (match.start(), match.end()),
                        'issues': []
                    }
            
            elif pattern_name == 'noon':
                return {
                    'time': time(12, 0),
                    'confidence': 0.98,
                    'method': 'explicit',
                    'matched_text': match.group(0),
                    'position': (match.start(), match.end()),
                    'issues': []
                }
            
            elif pattern_name == 'midnight':
                return {
                    'time': time(0, 0),
                    'confidence': 0.98,
                    'method': 'explicit',
                    'matched_text': match.group(0),
                    'position': (match.start(), match.end()),
                    'issues': []
                }
            
            elif pattern_name in self.relative_times:
                relative_time = self.relative_times[pattern_name]
                
                return {
                    'time': relative_time,
                    'confidence': 0.7,
                    'method': 'inferred',
                    'matched_text': match.group(0),
                    'position': (match.start(), match.end()),
                    'issues': ['Relative time converted to approximate time']
                }
            
        except (ValueError, IndexError):
            return None
        
        return None
    
    def _normalize_am_pm(self, am_pm_text: str) -> str:
        """Normalize AM/PM text with typo tolerance."""
        # Remove spaces, dots, and normalize
        normalized = re.sub(r'[\s\.]', '', am_pm_text.lower())
        
        if normalized in ['am', 'a']:
            return 'am'
        elif normalized in ['pm', 'p']:
            return 'pm'
        
        # Handle spaced versions by checking for letters
        clean_text = am_pm_text.lower().replace(' ', '').replace('.', '')
        if clean_text in ['am', 'a']:
            return 'am'
        elif clean_text in ['pm', 'p']:
            return 'pm'
        
        # Check if it contains p and m (for "P M" style)
        if 'p' in am_pm_text.lower() and 'm' in am_pm_text.lower():
            return 'pm'
        elif 'a' in am_pm_text.lower() and 'm' in am_pm_text.lower():
            return 'am'
        
        return 'am'  # Default fallback
    
    def _extract_time_ranges(self, text: str) -> List[Dict[str, Any]]:
        """Extract time range patterns from text."""
        results = []
        
        for pattern_name, pattern in self.time_range_patterns.items():
            for match in pattern.finditer(text):
                range_result = self._parse_time_range_match(match, pattern_name)
                if range_result:
                    results.append(range_result)
        
        return results
    
    def _parse_time_range_match(self, match: re.Match, pattern_name: str) -> Optional[Dict[str, Any]]:
        """Parse a time range match."""
        try:
            start_time = None
            end_time = None
            
            if pattern_name in ['range_12hour', 'from_to_12hour']:
                # Extract start time
                start_hour = int(match.group(1))
                start_minute = int(match.group(2)) if match.group(2) else 0
                start_am_pm = self._normalize_am_pm(match.group(3))
                
                # Extract end time
                end_hour = int(match.group(4))
                end_minute = int(match.group(5)) if match.group(5) else 0
                end_am_pm = self._normalize_am_pm(match.group(6))
                
                # Convert to 24-hour format
                if 1 <= start_hour <= 12:
                    if start_am_pm == 'pm' and start_hour != 12:
                        start_hour += 12
                    elif start_am_pm == 'am' and start_hour == 12:
                        start_hour = 0
                
                if 1 <= end_hour <= 12:
                    if end_am_pm == 'pm' and end_hour != 12:
                        end_hour += 12
                    elif end_am_pm == 'am' and end_hour == 12:
                        end_hour = 0
                
                if (0 <= start_hour <= 23 and 0 <= start_minute <= 59 and
                    0 <= end_hour <= 23 and 0 <= end_minute <= 59):
                    start_time = time(start_hour, start_minute)
                    end_time = time(end_hour, end_minute)
            
            elif pattern_name == 'range_12hour_shared_ampm':
                # Handle "9–10 a.m." format where AM/PM applies to both times
                start_hour = int(match.group(1))
                start_minute = int(match.group(2)) if match.group(2) else 0
                end_hour = int(match.group(3))
                end_minute = int(match.group(4)) if match.group(4) else 0
                shared_am_pm = self._normalize_am_pm(match.group(5))
                
                # Apply AM/PM to both times
                if 1 <= start_hour <= 12:
                    if shared_am_pm == 'pm' and start_hour != 12:
                        start_hour += 12
                    elif shared_am_pm == 'am' and start_hour == 12:
                        start_hour = 0
                
                if 1 <= end_hour <= 12:
                    if shared_am_pm == 'pm' and end_hour != 12:
                        end_hour += 12
                    elif shared_am_pm == 'am' and end_hour == 12:
                        end_hour = 0
                
                if (0 <= start_hour <= 23 and 0 <= start_minute <= 59 and
                    0 <= end_hour <= 23 and 0 <= end_minute <= 59):
                    start_time = time(start_hour, start_minute)
                    end_time = time(end_hour, end_minute)
            
            elif pattern_name in ['range_24hour', 'from_to_24hour']:
                start_hour = int(match.group(1))
                start_minute = int(match.group(2))
                end_hour = int(match.group(3))
                end_minute = int(match.group(4))
                
                if (0 <= start_hour <= 23 and 0 <= start_minute <= 59 and
                    0 <= end_hour <= 23 and 0 <= end_minute <= 59):
                    start_time = time(start_hour, start_minute)
                    end_time = time(end_hour, end_minute)
            
            if start_time and end_time:
                # Validate range
                issues = []
                if end_time <= start_time:
                    issues.append("End time appears to be before start time")
                
                return {
                    'start_time': start_time,
                    'end_time': end_time,
                    'confidence': 0.95,
                    'method': 'explicit',
                    'matched_text': match.group(0),
                    'position': (match.start(), match.end()),
                    'issues': issues
                }
            
        except (ValueError, IndexError):
            return None
        
        return None
    
    def _extract_durations(self, text: str) -> List[Dict[str, Any]]:
        """Extract duration patterns from text."""
        results = []
        
        for pattern_name, pattern in self.duration_patterns.items():
            for match in pattern.finditer(text):
                duration_result = self._parse_duration_match(match, pattern_name)
                if duration_result:
                    results.append(duration_result)
        
        return results
    
    def _parse_duration_match(self, match: re.Match, pattern_name: str) -> Optional[Dict[str, Any]]:
        """Parse a duration match."""
        try:
            if pattern_name == 'for_hours':
                hours = float(match.group(1))
                duration = timedelta(hours=hours)
                
                return {
                    'duration': duration,
                    'confidence': 0.95,
                    'matched_text': match.group(0),
                    'position': (match.start(), match.end())
                }
            
            elif pattern_name == 'for_minutes':
                minutes = int(match.group(1))
                duration = timedelta(minutes=minutes)
                
                return {
                    'duration': duration,
                    'confidence': 0.95,
                    'matched_text': match.group(0),
                    'position': (match.start(), match.end())
                }
            
            elif pattern_name in ['duration_long', 'hours_long']:
                if pattern_name == 'duration_long':
                    minutes = int(match.group(1))
                    duration = timedelta(minutes=minutes)
                else:
                    hours = float(match.group(1))
                    duration = timedelta(hours=hours)
                
                return {
                    'duration': duration,
                    'confidence': 0.9,
                    'matched_text': match.group(0),
                    'position': (match.start(), match.end())
                }
            
        except (ValueError, IndexError):
            return None
        
        return None    

    def _combine_datetime_components(self, text: str, date_results: List[Dict], 
                                   time_results: List[Dict], range_results: List[Dict], 
                                   duration_results: List[Dict]) -> Optional[Dict[str, Any]]:
        """Combine date, time, range, and duration components into final result."""
        
        # Priority 1: Time ranges with dates
        if range_results and date_results:
            best_date = max(date_results, key=lambda x: x['confidence'])
            best_range = max(range_results, key=lambda x: x['confidence'])
            
            start_dt = datetime.combine(best_date['date'], best_range['start_time'])
            end_dt = datetime.combine(best_date['date'], best_range['end_time'])
            
            # Handle next-day end times
            if end_dt <= start_dt:
                end_dt += timedelta(days=1)
            
            combined_confidence = (best_date['confidence'] + best_range['confidence']) / 2
            
            return {
                'start_datetime': start_dt,
                'end_datetime': end_dt,
                'confidence': combined_confidence,
                'method': 'explicit',
                'field_confidence': {
                    'date': best_date['confidence'],
                    'start_time': best_range['confidence'],
                    'end_time': best_range['confidence']
                },
                'ambiguities': best_date.get('ambiguities', []),
                'issues': best_date.get('issues', []) + best_range.get('issues', [])
            }
        
        # Priority 2: Dates with single times and durations
        if date_results and time_results and duration_results:
            best_date = max(date_results, key=lambda x: x['confidence'])
            best_time = max(time_results, key=lambda x: x['confidence'])
            best_duration = max(duration_results, key=lambda x: x['confidence'])
            
            start_dt = datetime.combine(best_date['date'], best_time['time'])
            end_dt = start_dt + best_duration['duration']
            
            combined_confidence = (best_date['confidence'] + best_time['confidence'] + 
                                 best_duration['confidence']) / 3
            
            return {
                'start_datetime': start_dt,
                'end_datetime': end_dt,
                'confidence': combined_confidence,
                'method': 'explicit',
                'field_confidence': {
                    'date': best_date['confidence'],
                    'start_time': best_time['confidence'],
                    'duration': best_duration['confidence']
                },
                'ambiguities': best_date.get('ambiguities', []),
                'issues': (best_date.get('issues', []) + best_time.get('issues', []))
            }
        
        # Priority 3: Dates with single times
        if date_results and time_results:
            best_date = max(date_results, key=lambda x: x['confidence'])
            best_time = max(time_results, key=lambda x: x['confidence'])
            
            start_dt = datetime.combine(best_date['date'], best_time['time'])
            
            combined_confidence = (best_date['confidence'] + best_time['confidence']) / 2
            
            return {
                'start_datetime': start_dt,
                'end_datetime': None,
                'confidence': combined_confidence,
                'method': 'explicit',
                'field_confidence': {
                    'date': best_date['confidence'],
                    'start_time': best_time['confidence']
                },
                'ambiguities': best_date.get('ambiguities', []),
                'issues': best_date.get('issues', []) + best_time.get('issues', [])
            }
        
        # Priority 4: Standalone time ranges (use today's date)
        if range_results:
            best_range = max(range_results, key=lambda x: x['confidence'])
            today = date.today()
            
            start_dt = datetime.combine(today, best_range['start_time'])
            end_dt = datetime.combine(today, best_range['end_time'])
            
            if end_dt <= start_dt:
                end_dt += timedelta(days=1)
            
            return {
                'start_datetime': start_dt,
                'end_datetime': end_dt,
                'confidence': best_range['confidence'] * 0.8,  # Lower confidence for assumed date
                'method': 'inferred',
                'field_confidence': {
                    'date': 0.6,  # Assumed today
                    'start_time': best_range['confidence'],
                    'end_time': best_range['confidence']
                },
                'issues': ['Date assumed to be today'] + best_range.get('issues', [])
            }
        
        # Priority 5: Dates only (all-day events)
        if date_results:
            best_date = max(date_results, key=lambda x: x['confidence'])
            
            # Create all-day event starting at midnight
            start_dt = datetime.combine(best_date['date'], time(0, 0))
            end_dt = datetime.combine(best_date['date'] + timedelta(days=1), time(0, 0))
            
            return {
                'start_datetime': start_dt,
                'end_datetime': end_dt,
                'confidence': best_date['confidence'],  # Keep original confidence
                'method': 'all_day',
                'is_all_day': True,  # Mark as all-day event
                'field_confidence': {
                    'date': best_date['confidence'],
                    'start_time': 1.0  # All-day events have perfect time confidence
                },
                'ambiguities': best_date.get('ambiguities', []),
                'issues': best_date.get('issues', []),
                'suggestions': ['This will be created as an all-day event']
            }
        
        # Priority 6: Times with durations (use today's date)
        if time_results and duration_results:
            best_time = max(time_results, key=lambda x: x['confidence'])
            best_duration = max(duration_results, key=lambda x: x['confidence'])
            today = date.today()
            
            start_dt = datetime.combine(today, best_time['time'])
            end_dt = start_dt + best_duration['duration']
            
            combined_confidence = (best_time['confidence'] + best_duration['confidence']) / 2 * 0.6
            
            return {
                'start_datetime': start_dt,
                'end_datetime': end_dt,
                'confidence': combined_confidence,
                'method': 'inferred',
                'field_confidence': {
                    'date': 0.6,  # Assumed today
                    'start_time': best_time['confidence'],
                    'duration': best_duration['confidence']
                },
                'issues': ['Date assumed to be today'] + best_time.get('issues', []),
                'suggestions': ['Please specify a date for this event']
            }
        
        # Priority 7: Times only (use today's date)
        if time_results:
            best_time = max(time_results, key=lambda x: x['confidence'])
            today = date.today()
            
            start_dt = datetime.combine(today, best_time['time'])
            
            return {
                'start_datetime': start_dt,
                'end_datetime': None,
                'confidence': best_time['confidence'] * 0.6,  # Lower confidence for assumed date
                'method': 'inferred',
                'field_confidence': {
                    'date': 0.6,  # Assumed today
                    'start_time': best_time['confidence']
                },
                'issues': ['Date assumed to be today'] + best_time.get('issues', []),
                'suggestions': ['Please specify a date for this event']
            }
        
        # No valid datetime components found
        return None
    
    def _get_next_weekday(self, from_date: date, target_weekday: int) -> date:
        """Get the next occurrence of a specific weekday."""
        days_ahead = target_weekday - from_date.weekday()
        if days_ahead <= 0:  # Target day already happened this week
            days_ahead += 7
        return from_date + timedelta(days=days_ahead)
    
    def _get_this_weekday(self, from_date: date, target_weekday: int) -> date:
        """Get the occurrence of a specific weekday in the current week."""
        days_ahead = target_weekday - from_date.weekday()
        if days_ahead < 0:  # Target day already happened this week, get next week
            days_ahead += 7
        elif days_ahead == 0:  # Target day is today
            return from_date
        return from_date + timedelta(days=days_ahead)
    
    def validate_extraction(self, result: DateTimeResult) -> Dict[str, Any]:
        """
        Validate the extraction result and provide quality assessment.
        
        Args:
            result: DateTimeResult to validate
            
        Returns:
            Dictionary with validation information
        """
        validation = {
            'is_valid': False,
            'quality_score': 0.0,
            'missing_fields': [],
            'warnings': [],
            'recommendations': []
        }
        
        # Check if we have a start datetime
        if result.start_datetime:
            validation['is_valid'] = True
            validation['quality_score'] = result.confidence
            
            # Check for missing end time
            if not result.end_datetime:
                validation['missing_fields'].append('end_time')
                validation['recommendations'].append('Consider specifying an end time or duration')
            
            # Check confidence levels
            if result.confidence < 0.7:
                validation['warnings'].append('Low confidence in extraction results')
                validation['recommendations'].append('Please review and confirm the extracted information')
            
            # Check for ambiguities
            if result.ambiguities:
                validation['warnings'].append('Multiple interpretations possible')
                validation['recommendations'].append('Please clarify ambiguous date/time information')
            
            # Check for parsing issues
            if result.parsing_issues:
                validation['warnings'].extend(result.parsing_issues)
            
            # Check if datetime is in the past
            if result.start_datetime < datetime.now():
                validation['warnings'].append('Event appears to be in the past')
        else:
            validation['missing_fields'].extend(['date', 'time'])
            validation['recommendations'].append('No valid date/time information found in text')
        
        return validation
    
    def get_parsing_suggestions(self, text: str, result: DateTimeResult) -> List[str]:
        """
        Generate suggestions for improving parsing results.
        
        Args:
            text: Original input text
            result: Parsing result
            
        Returns:
            List of suggestions for better parsing
        """
        suggestions = []
        
        if not result.start_datetime:
            suggestions.append("Try including explicit date and time information (e.g., 'Monday, Sep 29, 2025 at 2:00 PM')")
            return suggestions
        
        if result.confidence < 0.8:
            suggestions.append("For better accuracy, use explicit formats like 'September 29, 2025 at 2:00 PM'")
        
        if result.extraction_method == 'inferred':
            if 'Date assumed' in str(result.parsing_issues):
                suggestions.append("Specify the date explicitly to avoid assumptions")
            if 'Time assumed' in str(result.parsing_issues):
                suggestions.append("Include the specific time to improve accuracy")
        
        if result.ambiguities:
            suggestions.append("Use unambiguous date formats (e.g., 'September 29' instead of '9/29')")
        
        if not result.end_datetime:
            suggestions.append("Consider adding duration information (e.g., 'for 2 hours') or end time")
        
        return suggestions