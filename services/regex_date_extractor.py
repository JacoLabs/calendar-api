"""
RegexDateExtractor for absolute/relative dates, ranges, and durations.
Implements high-confidence regex-based datetime extraction as the primary method
for the hybrid parsing pipeline (Task 26.1).
"""

import re
from datetime import datetime, date, time, timedelta
from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass
import calendar


@dataclass
class DateTimeResult:
    """Result of regex-based datetime extraction with confidence scoring."""
    start_datetime: Optional[datetime] = None
    end_datetime: Optional[datetime] = None
    confidence: float = 0.0
    extraction_method: str = "regex"  # "explicit", "relative", "inferred"
    ambiguities: List[str] = None
    raw_text: str = ""
    pattern_type: str = ""
    is_all_day: bool = False
    
    def __post_init__(self):
        if self.ambiguities is None:
            self.ambiguities = []


class RegexDateExtractor:
    """
    High-confidence regex-based datetime extraction for the hybrid parsing pipeline.
    
    Handles:
    - Explicit date formats (Oct 15, 2025, 10/15/2025, October 15th)
    - Labeled dates like "Due Date: Oct 15, 2025" or "Deadline Oct 15"
    - Relative date parsing (tomorrow, next Friday, in 2 weeks)
    - Time range extraction (2–3pm, 9:30-10:30, from 2pm to 4pm)
    - Duration parsing (for 2 hours, 30 minutes long)
    - Confidence scoring based on pattern match quality
    
    Returns confidence ≥ 0.8 when successful, enabling LLM enhancement mode.
    """
    
    def __init__(self, current_time: Optional[datetime] = None):
        """
        Initialize the extractor with current time context.
        
        Args:
            current_time: Current datetime for relative date resolution (defaults to now)
        """
        self.current_time = current_time or datetime.now()
        self._compile_patterns()
    
    def _compile_patterns(self):
        """Compile all regex patterns for datetime extraction."""
        # Common fragments
        month_words = (
            r'january|february|march|april|may|june|july|august|september|october|november|december|'
            r'jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec'
        )
        label_prefix = r'(?:due(?:\s*date)?|deadline|date)\s*[:\-]?\s*'  # e.g., "Due Date:" / "Deadline - "

        # Explicit date patterns with high confidence
        self.explicit_date_patterns = {
            # Oct 15, 2025 | October 15th, 2025
            'month_day_year': re.compile(
                rf'\b({month_words})\.?\s+(\d{{1,2}})(?:st|nd|rd|th)?,?\s+(\d{{4}})\b',
                re.IGNORECASE
            ),
            # Labeled: "Due Date: Oct 15, 2025"
            'labeled_month_day_year': re.compile(
                rf'\b{label_prefix}({month_words})\.?\s+(\d{{1,2}})(?:st|nd|rd|th)?,?\s+(\d{{4}})\b',
                re.IGNORECASE
            ),
            # Oct 15 | October 15th (current year assumed)
            'month_day': re.compile(
                rf'\b({month_words})\.?\s+(\d{{1,2}})(?:st|nd|rd|th)?\b',
                re.IGNORECASE
            ),
            # Labeled: "Due Date: Oct 15" (current year assumed)
            'labeled_month_day': re.compile(
                rf'\b{label_prefix}({month_words})\.?\s+(\d{{1,2}})(?:st|nd|rd|th)?\b',
                re.IGNORECASE
            ),
            # 10/15/2025 | 10-15-2025
            'mm_dd_yyyy': re.compile(
                r'\b(\d{1,2})[\/\-](\d{1,2})[\/\-](\d{4})\b'
            ),
            # 10/15 | 10-15 (current year assumed)
            'mm_dd': re.compile(
                r'\b(\d{1,2})[\/\-](\d{1,2})\b'
            ),
            # 2025-10-15 (ISO format)
            'yyyy_mm_dd': re.compile(
                r'\b(\d{4})[\/\-](\d{1,2})[\/\-](\d{1,2})\b'
            )
        }
        
        # Relative date patterns
        self.relative_date_patterns = {
            'today': re.compile(r'\btoday\b', re.IGNORECASE),
            'tomorrow': re.compile(r'\btomorrow\b', re.IGNORECASE),
            'yesterday': re.compile(r'\byesterday\b', re.IGNORECASE),
            
            # Next/This weekday
            'next_weekday': re.compile(
                r'\bnext\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b',
                re.IGNORECASE
            ),
            'this_weekday': re.compile(
                r'\bthis\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b',
                re.IGNORECASE
            ),
            
            # Standalone weekday (assumes next occurrence)
            'standalone_weekday': re.compile(
                r'\b(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b',
                re.IGNORECASE
            ),
            
            # In X days/weeks
            'in_days': re.compile(
                r'\bin\s+(\d+)\s+(days?)\b',
                re.IGNORECASE
            ),
            'in_weeks': re.compile(
                r'\bin\s+(\d+)\s+(weeks?)\b',
                re.IGNORECASE
            ),
            'in_months': re.compile(
                r'\bin\s+(\d+)\s+(months?)\b',
                re.IGNORECASE
            ),
            
            # X days/weeks from now
            'days_from_now': re.compile(
                r'\b(\d+)\s+(days?)\s+from\s+now\b',
                re.IGNORECASE
            ),
            'weeks_from_now': re.compile(
                r'\b(\d+)\s+(weeks?)\s+from\s+now\b',
                re.IGNORECASE
            )
        }
        
        # Time patterns with high confidence
        self.time_patterns = {
            # 2pm | 2:30pm | 2:30 PM
            '12_hour_am_pm': re.compile(
                r'\b(\d{1,2})(?::(\d{2}))?\s*(am|pm)\b',
                re.IGNORECASE
            ),
            # 14:30 | 14:00
            '24_hour': re.compile(
                r'\b(\d{1,2}):(\d{2})\b'
            ),
            # noon | midnight
            'named_times': re.compile(
                r'\b(noon|midnight)\b',
                re.IGNORECASE
            )
        }
        
        # Time range patterns (highest confidence)
        self.time_range_patterns = {
            # 2–3pm | 2-3pm | 2 to 3pm
            'simple_range_12h': re.compile(
                r'\b(\d{1,2})(?::(\d{2}))?\s*[–\-to]\s*(\d{1,2})(?::(\d{2}))?\s*(am|pm)\b',
                re.IGNORECASE
            ),
            # from 2pm to 3pm
            'from_to_12h': re.compile(
                r'\bfrom\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)\s+to\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)\b',
                re.IGNORECASE
            ),
            # 14:00-15:30 | from 14:00 to 15:30
            'range_24h': re.compile(
                r'(?:from\s+)?(\d{1,2}):(\d{2})\s*[–\-to]\s*(\d{1,2}):(\d{2})\b'
            ),
            # 2pm-3:30pm | 2:00pm to 3:30pm
            'mixed_range_12h': re.compile(
                r'\b(\d{1,2})(?::(\d{2}))?\s*(am|pm)\s*[–\-to]\s*(\d{1,2})(?::(\d{2}))?\s*(am|pm)\b',
                re.IGNORECASE
            )
        }
        
        # Duration patterns
        self.duration_patterns = {
            'for_hours': re.compile(
                r'\bfor\s+(\d+(?:\.\d+)?)\s+(hours?|hrs?|h)\b',
                re.IGNORECASE
            ),
            'for_minutes': re.compile(
                r'\bfor\s+(\d+(?:\.\d+)?)\s+(minutes?|mins?|m)\b',
                re.IGNORECASE
            ),
            'duration_hours': re.compile(
                r'\b(\d+(?:\.\d+)?)\s+(hours?|hrs?|h)\s+(?:long|duration)\b',
                re.IGNORECASE
            ),
            'duration_minutes': re.compile(
                r'\b(\d+(?:\.\d+)?)\s+(minutes?|mins?|m)\s+(?:long|duration)\b',
                re.IGNORECASE
            )
        }
        
        # Month name mappings (added 'sept')
        self.month_names = {
            'january': 1, 'jan': 1, 'february': 2, 'feb': 2, 'march': 3, 'mar': 3,
            'april': 4, 'apr': 4, 'may': 5, 'june': 6, 'jun': 6,
            'july': 7, 'jul': 7, 'august': 8, 'aug': 8, 'september': 9, 'sep': 9, 'sept': 9,
            'october': 10, 'oct': 10, 'november': 11, 'nov': 11, 'december': 12, 'dec': 12
        }
        
        # Weekday mappings (Monday = 0)
        self.weekday_names = {
            'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3,
            'friday': 4, 'saturday': 5, 'sunday': 6
        }
    
    def extract_datetime(self, text: str, timezone_offset: Optional[int] = None) -> DateTimeResult:
        """
        Extract datetime information from text using regex patterns.
        
        Args:
            text: Input text to parse
            timezone_offset: Timezone offset in hours (for relative date resolution)
            
        Returns:
            DateTimeResult with confidence ≥ 0.8 if successful, 0.0 if failed
        """
        if not text or not text.strip():
            return DateTimeResult(confidence=0.0, raw_text=text)
        
        text = text.strip()
        
        # Try time ranges first (highest confidence)
        time_range_result = self._extract_time_range(text)
        if time_range_result.confidence >= 0.8:
            return time_range_result
        
        # Try explicit date + time combinations
        datetime_result = self._extract_datetime_combination(text)
        if datetime_result.confidence >= 0.8:
            return datetime_result
        
        # Try relative dates with times
        relative_result = self._extract_relative_datetime(text, timezone_offset)
        if relative_result.confidence >= 0.8:
            return relative_result
        
        # Try standalone dates (all-day events)
        date_result = self._extract_standalone_date(text)
        if date_result.confidence >= 0.8:
            return date_result
        
        # No high-confidence extraction found
        return DateTimeResult(
            confidence=0.0,
            raw_text=text,
            extraction_method="failed",
            ambiguities=["No clear date/time pattern found"]
        )
    
    def _extract_time_range(self, text: str) -> DateTimeResult:
        """Extract time ranges with highest confidence."""
        for pattern_name, pattern in self.time_range_patterns.items():
            match = pattern.search(text)
            if match:
                try:
                    start_time, end_time = self._parse_time_range_match(match, pattern_name)
                    if start_time and end_time:
                        # Use today's date for time ranges
                        today = self.current_time.date()
                        start_dt = datetime.combine(today, start_time)
                        end_dt = datetime.combine(today, end_time)
                        
                        # Handle overnight ranges
                        if end_dt <= start_dt:
                            end_dt += timedelta(days=1)
                        
                        return DateTimeResult(
                            start_datetime=start_dt,
                            end_datetime=end_dt,
                            confidence=0.95,  # Very high confidence for explicit ranges
                            extraction_method="explicit",
                            raw_text=match.group(0),
                            pattern_type=f"time_range_{pattern_name}"
                        )
                except (ValueError, IndexError):
                    continue
        
        return DateTimeResult(confidence=0.0)
    
    def _parse_time_range_match(self, match, pattern_name: str) -> Tuple[Optional[time], Optional[time]]:
        """Parse a time range match into start and end times."""
        if pattern_name == 'simple_range_12h':
            # 2–3pm | 2:30-3:30pm
            start_hour = int(match.group(1))
            start_min = int(match.group(2)) if match.group(2) else 0
            end_hour = int(match.group(3))
            end_min = int(match.group(4)) if match.group(4) else 0
            am_pm = match.group(5).lower()
            
            # Apply AM/PM to both times
            if am_pm == 'pm' and start_hour != 12:
                start_hour += 12
            elif am_pm == 'am' and start_hour == 12:
                start_hour = 0
                
            if am_pm == 'pm' and end_hour != 12:
                end_hour += 12
            elif am_pm == 'am' and end_hour == 12:
                end_hour = 0
            
            return time(start_hour, start_min), time(end_hour, end_min)
        
        elif pattern_name == 'from_to_12h':
            # from 2pm to 3pm
            start_hour = int(match.group(1))
            start_min = int(match.group(2)) if match.group(2) else 0
            start_ampm = match.group(3).lower()
            end_hour = int(match.group(4))
            end_min = int(match.group(5)) if match.group(5) else 0
            end_ampm = match.group(6).lower()
            
            # Convert start time
            if start_ampm == 'pm' and start_hour != 12:
                start_hour += 12
            elif start_ampm == 'am' and start_hour == 12:
                start_hour = 0
            
            # Convert end time
            if end_ampm == 'pm' and end_hour != 12:
                end_hour += 12
            elif end_ampm == 'am' and end_hour == 12:
                end_hour = 0
            
            return time(start_hour, start_min), time(end_hour, end_min)
        
        elif pattern_name == 'range_24h':
            # 14:00-15:30
            start_hour = int(match.group(1))
            start_min = int(match.group(2))
            end_hour = int(match.group(3))
            end_min = int(match.group(4))
            
            if (0 <= start_hour <= 23 and 0 <= start_min <= 59 and
                0 <= end_hour <= 23 and 0 <= end_min <= 59):
                return time(start_hour, start_min), time(end_hour, end_min)
        
        elif pattern_name == 'mixed_range_12h':
            # 2pm-3:30pm
            start_hour = int(match.group(1))
            start_min = int(match.group(2)) if match.group(2) else 0
            start_ampm = match.group(3).lower()
            end_hour = int(match.group(4))
            end_min = int(match.group(5)) if match.group(5) else 0
            end_ampm = match.group(6).lower()
            
            # Convert times
            if start_ampm == 'pm' and start_hour != 12:
                start_hour += 12
            elif start_ampm == 'am' and start_hour == 12:
                start_hour = 0
                
            if end_ampm == 'pm' and end_hour != 12:
                end_hour += 12
            elif end_ampm == 'am' and end_hour == 12:
                end_hour = 0
            
            return time(start_hour, start_min), time(end_hour, end_min)
        
        return None, None
    
    def _extract_datetime_combination(self, text: str) -> DateTimeResult:
        """Extract explicit date + time combinations."""
        # Find date patterns
        date_matches = []
        for pattern_name, pattern in self.explicit_date_patterns.items():
            for match in pattern.finditer(text):
                try:
                    parsed_date = self._parse_date_match(match, pattern_name)
                    if parsed_date:
                        date_matches.append((parsed_date, match, pattern_name))
                except (ValueError, KeyError):
                    continue
        
        # Find time patterns
        time_matches = []
        for pattern_name, pattern in self.time_patterns.items():
            for match in pattern.finditer(text):
                try:
                    parsed_time = self._parse_time_match(match, pattern_name)
                    if parsed_time:
                        time_matches.append((parsed_time, match, pattern_name))
                except (ValueError, KeyError):
                    continue
        
        # Combine closest date and time
        if date_matches and time_matches:
            best_combination = self._find_best_datetime_combination(date_matches, time_matches)
            if best_combination:
                date_obj, time_obj, confidence, combined_text = best_combination
                start_dt = datetime.combine(date_obj, time_obj)
                
                # Check for duration to calculate end time
                duration = self._extract_duration(text)
                end_dt = start_dt + duration if duration else start_dt + timedelta(hours=1)
                
                return DateTimeResult(
                    start_datetime=start_dt,
                    end_datetime=end_dt,
                    confidence=confidence,
                    extraction_method="explicit",
                    raw_text=combined_text,
                    pattern_type="date_time_combination"
                )
        
        # Try standalone date with high confidence
        if date_matches:
            date_obj, match, pattern_name = date_matches[0]  # Use first/best match
            confidence = 0.9 if 'year' in pattern_name else 0.8
            
            return DateTimeResult(
                start_datetime=datetime.combine(date_obj, time(0, 0)),   # All-day: midnight
                end_datetime=datetime.combine(date_obj, time(23, 59)),
                confidence=confidence,
                extraction_method="explicit",
                raw_text=match.group(0),
                pattern_type=f"date_only_{pattern_name}",
                is_all_day=True
            )
        
        return DateTimeResult(confidence=0.0)
    
    def _parse_date_match(self, match, pattern_name: str) -> Optional[date]:
        """Parse a date match into a date object."""
        current_year = self.current_time.year
        
        if pattern_name in ('month_day_year', 'labeled_month_day_year'):
            month_name = match.group(1).lower()
            day = int(match.group(2))
            year = int(match.group(3))
            month = self.month_names[month_name]
            return date(year, month, day)
        
        elif pattern_name in ('month_day', 'labeled_month_day'):
            month_name = match.group(1).lower()
            day = int(match.group(2))
            month = self.month_names[month_name]
            return date(current_year, month, day)
        
        elif pattern_name == 'mm_dd_yyyy':
            month = int(match.group(1))
            day = int(match.group(2))
            year = int(match.group(3))
            if 1 <= month <= 12 and 1 <= day <= 31:
                return date(year, month, day)
        
        elif pattern_name == 'mm_dd':
            month = int(match.group(1))
            day = int(match.group(2))
            if 1 <= month <= 12 and 1 <= day <= 31:
                return date(current_year, month, day)
        
        elif pattern_name == 'yyyy_mm_dd':
            year = int(match.group(1))
            month = int(match.group(2))
            day = int(match.group(3))
            if 1 <= month <= 12 and 1 <= day <= 31:
                return date(year, month, day)
        
        return None
    
    def _parse_time_match(self, match, pattern_name: str) -> Optional[time]:
        """Parse a time match into a time object."""
        if pattern_name == '12_hour_am_pm':
            hour = int(match.group(1))
            minute = int(match.group(2)) if match.group(2) else 0
            am_pm = match.group(3).lower()
            
            if 1 <= hour <= 12:
                if am_pm == 'pm' and hour != 12:
                    hour += 12
                elif am_pm == 'am' and hour == 12:
                    hour = 0
                return time(hour, minute)
        
        elif pattern_name == '24_hour':
            hour = int(match.group(1))
            minute = int(match.group(2))
            if 0 <= hour <= 23 and 0 <= minute <= 59:
                return time(hour, minute)
        
        elif pattern_name == 'named_times':
            name = match.group(1).lower()
            if name == 'noon':
                return time(12, 0)
            elif name == 'midnight':
                return time(0, 0)
        
        return None
    
    def _find_best_datetime_combination(self, date_matches, time_matches) -> Optional[Tuple[date, time, float, str]]:
        """Find the best date+time combination based on proximity."""
        best_combo = None
        min_distance = float('inf')
        
        for date_obj, date_match, date_pattern in date_matches:
            for time_obj, time_match, time_pattern in time_matches:
                # Calculate distance between matches
                distance = abs(date_match.start() - time_match.start())
                
                if distance < min_distance and distance < 100:  # Within 100 characters
                    confidence = 0.9 if 'year' in date_pattern else 0.85
                    if 'am_pm' in time_pattern:
                        confidence += 0.05  # Boost for explicit AM/PM
                    
                    combined_text = f"{date_match.group(0)} {time_match.group(0)}"
                    best_combo = (date_obj, time_obj, min(confidence, 0.97), combined_text)
                    min_distance = distance
        
        return best_combo
    
    def _extract_relative_datetime(self, text: str, timezone_offset: Optional[int] = None) -> DateTimeResult:
        """Extract relative dates with times."""
        # Find relative date patterns
        for pattern_name, pattern in self.relative_date_patterns.items():
            match = pattern.search(text)
            if match:
                try:
                    target_date = self._calculate_relative_date(match, pattern_name)
                    if target_date:
                        # Look for time in the same text
                        time_obj = self._find_time_near_match(text, match)
                        if time_obj:
                            start_dt = datetime.combine(target_date, time_obj)
                            duration = self._extract_duration(text)
                            end_dt = start_dt + (duration or timedelta(hours=1))
                            
                            return DateTimeResult(
                                start_datetime=start_dt,
                                end_datetime=end_dt,
                                confidence=0.9,
                                extraction_method="relative",
                                raw_text=text,
                                pattern_type=f"relative_{pattern_name}"
                            )
                        else:
                            # All-day relative date
                            return DateTimeResult(
                                start_datetime=datetime.combine(target_date, time(0, 0)),
                                end_datetime=datetime.combine(target_date, time(23, 59)),
                                confidence=0.85,
                                extraction_method="relative",
                                raw_text=match.group(0),
                                pattern_type=f"relative_{pattern_name}_all_day",
                                is_all_day=True
                            )
                except (ValueError, OverflowError):
                    continue
        
        return DateTimeResult(confidence=0.0)
    
    def _calculate_relative_date(self, match, pattern_name: str) -> Optional[date]:
        """Calculate the target date for relative patterns."""
        base_date = self.current_time.date()
        
        if pattern_name == 'today':
            return base_date
        elif pattern_name == 'tomorrow':
            return base_date + timedelta(days=1)
        elif pattern_name == 'yesterday':
            return base_date - timedelta(days=1)
        
        elif pattern_name == 'next_weekday':
            weekday_name = match.group(1).lower()
            target_weekday = self.weekday_names[weekday_name]
            days_ahead = target_weekday - base_date.weekday()
            if days_ahead <= 0:  # Target day already happened this week
                days_ahead += 7
            return base_date + timedelta(days=days_ahead)
        
        elif pattern_name == 'this_weekday':
            weekday_name = match.group(1).lower()
            target_weekday = self.weekday_names[weekday_name]
            days_ahead = target_weekday - base_date.weekday()
            if days_ahead < 0:  # Already passed this week, use next week
                days_ahead += 7
            return base_date + timedelta(days=days_ahead)
        
        elif pattern_name == 'standalone_weekday':
            weekday_name = match.group(1).lower()
            target_weekday = self.weekday_names[weekday_name]
            days_ahead = target_weekday - base_date.weekday()
            if days_ahead <= 0:  # Already happened this week, use next week
                days_ahead += 7
            return base_date + timedelta(days=days_ahead)
        
        elif pattern_name in ['in_days', 'days_from_now']:
            days = int(match.group(1))
            return base_date + timedelta(days=days)
        
        elif pattern_name in ['in_weeks', 'weeks_from_now']:
            weeks = int(match.group(1))
            return base_date + timedelta(weeks=weeks)
        
        elif pattern_name == 'in_months':
            months = int(match.group(1))
            # Approximate month calculation
            return base_date + timedelta(days=months * 30)
        
        return None
    
    def _find_time_near_match(self, text: str, date_match) -> Optional[time]:
        """Find a time pattern near the date match."""
        # Look for time patterns within 50 characters of the date match
        search_start = max(0, date_match.start() - 50)
        search_end = min(len(text), date_match.end() + 50)
        search_text = text[search_start:search_end]
        
        for pattern_name, pattern in self.time_patterns.items():
            match = pattern.search(search_text)
            if match:
                return self._parse_time_match(match, pattern_name)
        
        return None
    
    def _extract_standalone_date(self, text: str) -> DateTimeResult:
        """Extract standalone dates for all-day events."""
        for pattern_name, pattern in self.explicit_date_patterns.items():
            match = pattern.search(text)
            if match:
                try:
                    parsed_date = self._parse_date_match(match, pattern_name)
                    if parsed_date:
                        confidence = 0.9 if 'year' in pattern_name else 0.8
                        
                        return DateTimeResult(
                            start_datetime=datetime.combine(parsed_date, time(0, 0)),
                            end_datetime=datetime.combine(parsed_date, time(23, 59)),
                            confidence=confidence,
                            extraction_method="explicit",
                            raw_text=match.group(0),
                            pattern_type=f"standalone_{pattern_name}",
                            is_all_day=True
                        )
                except (ValueError, KeyError):
                    continue
        
        return DateTimeResult(confidence=0.0)
    
    def _extract_duration(self, text: str) -> Optional[timedelta]:
        """Extract duration information from text."""
        for pattern_name, pattern in self.duration_patterns.items():
            match = pattern.search(text)
            if match:
                try:
                    if pattern_name == 'hours':
                        hours = float(match.group(1))
                        return timedelta(hours=hours)
                    elif pattern_name == 'minutes':
                        minutes = int(match.group(1))
                        return timedelta(minutes=minutes)
                    elif pattern_name == 'hours_minutes':
                        hours = int(match.group(1))
                        minutes = int(match.group(3))
                        return timedelta(hours=hours, minutes=minutes)
                except (ValueError, IndexError):
                    continue
        
        return None
    
    def set_current_time(self, current_time: datetime):
        """Update the current time context for relative date resolution."""
        self.current_time = current_time