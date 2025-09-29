"""
DateTime extraction service for parsing dates and times from natural language text.
Supports various date formats, time representations, and relative date parsing.
"""

import re
from datetime import datetime, time, date, timedelta
from typing import Optional, Tuple, List, Dict, Any
from dataclasses import dataclass


@dataclass
class DateTimeMatch:
    """Represents a matched date/time pattern in text."""
    value: datetime
    confidence: float
    start_pos: int
    end_pos: int
    matched_text: str
    pattern_type: str


@dataclass
class DurationMatch:
    """Represents a matched duration pattern in text."""
    duration: timedelta
    confidence: float
    start_pos: int
    end_pos: int
    matched_text: str
    pattern_type: str


class DateTimeParser:
    """
    Service for extracting dates and times from natural language text.
    Supports absolute dates, various time formats, and relative date parsing.
    """
    
    def __init__(self):
        self._compile_patterns()
    
    def _compile_patterns(self):
        """Compile regex patterns for date and time matching."""
        
        # Date patterns (MM/DD/YYYY, DD/MM/YYYY, Month DD, YYYY)
        self.date_patterns = {
            'mm_dd_yyyy': re.compile(
                r'\b(\d{1,2})[\/\-](\d{1,2})[\/\-](\d{4})\b',
                re.IGNORECASE
            ),
            'dd_mm_yyyy': re.compile(
                r'\b(\d{1,2})[\/\-](\d{1,2})[\/\-](\d{4})\b',
                re.IGNORECASE
            ),
            'month_dd_yyyy': re.compile(
                r'\b(january|february|march|april|may|june|july|august|september|october|november|december)\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(\d{4})\b',
                re.IGNORECASE
            ),
            'month_dd_range_yyyy': re.compile(
                r'\b(january|february|march|april|may|june|july|august|september|october|november|december)\s+(\d{1,2})(?:st|nd|rd|th)?\s+to\s+\d{1,2}(?:st|nd|rd|th)?,?\s+(\d{4})\b',
                re.IGNORECASE
            ),
            'month_dd': re.compile(
                r'\b(january|february|march|april|may|june|july|august|september|october|november|december)\s+(\d{1,2})(?:st|nd|rd|th)?\b',
                re.IGNORECASE
            ),
            'month_dd_original': re.compile(
                r'\b(january|february|march|april|may|june|july|august|september|october|november|december)\s+(\d{1,2})\b',
                re.IGNORECASE
            ),
            'yyyy_mm_dd': re.compile(
                r'\b(\d{4})[\/\-](\d{1,2})[\/\-](\d{1,2})\b',
                re.IGNORECASE
            )
        }
        
        # Time patterns (12-hour and 24-hour formats)
        self.time_patterns = {
            '12_hour_am_pm': re.compile(
                r'\b(\d{1,2})(?::(\d{2}))?\s*(am|pm)\b',
                re.IGNORECASE
            ),
            '24_hour': re.compile(
                r'\b(\d{1,2}):(\d{2})\b'
            ),
            '12_hour_colon': re.compile(
                r'\b(\d{1,2}):(\d{2})\s*(am|pm)\b',
                re.IGNORECASE
            ),
            'hour_only': re.compile(
                r'\b(\d{1,2})\s*o\'?clock\b',
                re.IGNORECASE
            )
        }
        
        # Month name to number mapping
        self.month_names = {
            'january': 1, 'february': 2, 'march': 3, 'april': 4,
            'may': 5, 'june': 6, 'july': 7, 'august': 8,
            'september': 9, 'october': 10, 'november': 11, 'december': 12
        }
        
        # Relative date patterns
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
            'days_from_now': re.compile(
                r'\b(\d+)\s+(days?)\s+from\s+now\b',
                re.IGNORECASE
            ),
            'weeks_from_now': re.compile(
                r'\b(\d+)\s+(weeks?)\s+from\s+now\b',
                re.IGNORECASE
            )
        }
        
        # Duration patterns
        self.duration_patterns = {
            'for_hours': re.compile(
                r'\bfor\s+(\d+(?:\.\d+)?)\s+(hours?)\b',
                re.IGNORECASE
            ),
            'for_minutes': re.compile(
                r'\bfor\s+(\d+)\s+(minutes?|mins?)\b',
                re.IGNORECASE
            ),
            'for_hours_minutes': re.compile(
                r'\bfor\s+(\d+)\s+(hours?)\s+(?:and\s+)?(\d+)\s+(minutes?|mins?)\b',
                re.IGNORECASE
            ),
            'duration_hours': re.compile(
                r'\b(\d+(?:\.\d+)?)\s+(hours?)\b',
                re.IGNORECASE
            ),
            'duration_minutes': re.compile(
                r'\b(\d+)\s+(minutes?|mins?)\b',
                re.IGNORECASE
            ),
            'duration_colon': re.compile(
                r'\b(\d{1,2}):(\d{2})\s+(?:hours?|hrs?|duration)\b',
                re.IGNORECASE
            )
        }
        
        # Time range patterns (from X to Y)
        self.time_range_patterns = {
            'from_to_12hour': re.compile(
                r'\bfrom\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)\s+to\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)\b',
                re.IGNORECASE
            ),
            'from_to_24hour': re.compile(
                r'\bfrom\s+(\d{1,2}):(\d{2})\s+to\s+(\d{1,2}):(\d{2})\b',
                re.IGNORECASE
            ),
            'from_to_mixed': re.compile(
                r'\bfrom\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\s+to\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\b',
                re.IGNORECASE
            ),
            'simple_to_12hour': re.compile(
                r'\b(\d{1,2})(?::(\d{2}))?\s*(am|pm)\s+to\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)\b',
                re.IGNORECASE
            )
        }
        
        # Weekday name to number mapping (Monday = 0)
        self.weekday_names = {
            'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3,
            'friday': 4, 'saturday': 5, 'sunday': 6
        }
    
    def extract_datetime(self, text: str, prefer_dd_mm: bool = False) -> List[DateTimeMatch]:
        """
        Extract all date/time combinations from text.
        
        Args:
            text: Input text to parse
            prefer_dd_mm: If True, interpret ambiguous dates as DD/MM instead of MM/DD
            
        Returns:
            List of DateTimeMatch objects sorted by confidence
        """
        matches = []
        
        # First, check for time ranges (from X to Y) - these have highest priority
        time_range_matches = self._extract_time_ranges(text)
        matches.extend(time_range_matches)
        
        # Extract absolute dates and times separately
        date_matches = self._extract_dates(text, prefer_dd_mm)
        time_matches = self._extract_times(text)
        
        # Extract relative dates
        relative_matches = self._extract_relative_dates(text)
        
        # Combine dates with time ranges first (highest priority)
        if time_range_matches:
            combined_range_matches = self._combine_date_time_range_matches(text, date_matches + relative_matches, time_range_matches)
            matches.extend(combined_range_matches)
        
        # Combine dates with regular times when they appear close together
        combined_matches = self._combine_date_time_matches(text, date_matches + relative_matches, time_matches)
        matches.extend(combined_matches)
        
        # Add standalone dates (with default time)
        all_date_matches = date_matches + relative_matches
        for date_match in all_date_matches:
            if not any(abs(date_match.start_pos - match.start_pos) < 50 for match in combined_matches + time_range_matches):
                # Create datetime with default time (9:00 AM)
                dt = datetime.combine(date_match.value.date(), time(9, 0))
                matches.append(DateTimeMatch(
                    value=dt,
                    confidence=date_match.confidence * 0.8,  # Lower confidence for assumed time
                    start_pos=date_match.start_pos,
                    end_pos=date_match.end_pos,
                    matched_text=date_match.matched_text,
                    pattern_type=f"{date_match.pattern_type}_default_time"
                ))
        
        # Add standalone times (with today's date)
        for time_match in time_matches:
            if not any(abs(time_match.start_pos - match.start_pos) < 50 for match in combined_matches + time_range_matches):
                matches.append(time_match)  # Time matches already have today's date
        
        # Sort by confidence and preference for combined date+time matches
        def sort_key(match):
            confidence = match.confidence
            # Boost confidence for combined date+time patterns
            if '+' in match.pattern_type:
                confidence += 0.1  # Small boost for combined patterns
            # Boost confidence for patterns that include year information
            if 'yyyy' in match.pattern_type:
                confidence += 0.05
            return confidence
        
        matches.sort(key=sort_key, reverse=True)
        return matches
    
    def _extract_dates(self, text: str, prefer_dd_mm: bool = False) -> List[DateTimeMatch]:
        """Extract date patterns from text."""
        matches = []
        current_year = datetime.now().year
        
        for pattern_name, pattern in self.date_patterns.items():
            for match in pattern.finditer(text):
                try:
                    date_obj = None
                    confidence = 0.9
                    
                    if pattern_name == 'mm_dd_yyyy':
                        if prefer_dd_mm:
                            # Interpret as DD/MM/YYYY
                            day, month, year = int(match.group(1)), int(match.group(2)), int(match.group(3))
                            confidence = 0.8  # Lower confidence due to ambiguity
                        else:
                            # Interpret as MM/DD/YYYY
                            month, day, year = int(match.group(1)), int(match.group(2)), int(match.group(3))
                        
                        if 1 <= month <= 12 and 1 <= day <= 31:
                            date_obj = date(year, month, day)
                    
                    elif pattern_name == 'dd_mm_yyyy':
                        day, month, year = int(match.group(1)), int(match.group(2)), int(match.group(3))
                        if 1 <= month <= 12 and 1 <= day <= 31:
                            date_obj = date(year, month, day)
                    
                    elif pattern_name == 'yyyy_mm_dd':
                        year, month, day = int(match.group(1)), int(match.group(2)), int(match.group(3))
                        if 1 <= month <= 12 and 1 <= day <= 31:
                            date_obj = date(year, month, day)
                    
                    elif pattern_name == 'month_dd_yyyy':
                        month_name = match.group(1).lower()
                        day = int(match.group(2))
                        year = int(match.group(3))
                        month = self.month_names[month_name]
                        if 1 <= day <= 31:
                            date_obj = date(year, month, day)
                            confidence = 0.95  # High confidence for explicit month names
                    
                    elif pattern_name == 'month_dd_range_yyyy':
                        month_name = match.group(1).lower()
                        day = int(match.group(2))  # Start day of range
                        year = int(match.group(3))
                        month = self.month_names[month_name]
                        if 1 <= day <= 31:
                            date_obj = date(year, month, day)
                            confidence = 0.95  # High confidence for explicit month names and year
                    
                    elif pattern_name == 'month_dd':
                        month_name = match.group(1).lower()
                        day = int(match.group(2))
                        month = self.month_names[month_name]
                        if 1 <= day <= 31:
                            date_obj = date(current_year, month, day)
                            confidence = 0.85  # Lower confidence due to assumed year
                    
                    if date_obj:
                        matches.append(DateTimeMatch(
                            value=datetime.combine(date_obj, time(0, 0)),
                            confidence=confidence,
                            start_pos=match.start(),
                            end_pos=match.end(),
                            matched_text=match.group(0),
                            pattern_type=pattern_name
                        ))
                
                except (ValueError, KeyError):
                    # Invalid date, skip
                    continue
        
        return matches
    
    def _extract_times(self, text: str) -> List[DateTimeMatch]:
        """Extract time patterns from text."""
        matches = []
        
        for pattern_name, pattern in self.time_patterns.items():
            for match in pattern.finditer(text):
                try:
                    time_obj = None
                    confidence = 0.9
                    
                    if pattern_name == '12_hour_am_pm':
                        hour = int(match.group(1))
                        minute = int(match.group(2)) if match.group(2) else 0
                        am_pm = match.group(3).lower()
                        
                        if 1 <= hour <= 12:
                            if am_pm == 'pm' and hour != 12:
                                hour += 12
                            elif am_pm == 'am' and hour == 12:
                                hour = 0
                            time_obj = time(hour, minute)
                            confidence = 0.95  # High confidence for explicit AM/PM
                    
                    elif pattern_name == '12_hour_colon':
                        hour = int(match.group(1))
                        minute = int(match.group(2))
                        am_pm = match.group(3).lower()
                        
                        if 1 <= hour <= 12 and 0 <= minute <= 59:
                            if am_pm == 'pm' and hour != 12:
                                hour += 12
                            elif am_pm == 'am' and hour == 12:
                                hour = 0
                            time_obj = time(hour, minute)
                            confidence = 0.95
                    
                    elif pattern_name == '24_hour':
                        hour = int(match.group(1))
                        minute = int(match.group(2))
                        
                        if 0 <= hour <= 23 and 0 <= minute <= 59:
                            time_obj = time(hour, minute)
                            confidence = 0.9
                    
                    elif pattern_name == 'hour_only':
                        hour = int(match.group(1))
                        
                        if 1 <= hour <= 12:
                            # Assume PM for business hours (2-5, 9-12), AM for early hours (6-8)
                            if hour == 2 or hour == 10 or (9 <= hour <= 12) or (3 <= hour <= 5):
                                # Business hours: assume PM
                                time_obj = time(hour + 12 if hour != 12 else 12, 0)
                            else:
                                # Early morning hours: assume AM
                                time_obj = time(hour if hour != 12 else 0, 0)
                            confidence = 0.7  # Lower confidence due to AM/PM assumption
                    
                    if time_obj:
                        # Create a datetime with today's date for consistency
                        today = date.today()
                        dt = datetime.combine(today, time_obj)
                        
                        matches.append(DateTimeMatch(
                            value=dt,
                            confidence=confidence,
                            start_pos=match.start(),
                            end_pos=match.end(),
                            matched_text=match.group(0),
                            pattern_type=pattern_name
                        ))
                
                except ValueError:
                    # Invalid time, skip
                    continue
        
        return matches
    
    def _extract_time_ranges(self, text: str) -> List[DateTimeMatch]:
        """Extract time range patterns (from X to Y) from text."""
        matches = []
        
        for pattern_name, pattern in self.time_range_patterns.items():
            for match in pattern.finditer(text):
                try:
                    start_time = None
                    end_time = None
                    confidence = 0.95  # High confidence for explicit time ranges
                    
                    if pattern_name == 'from_to_12hour':
                        # from 10:00 AM to 11:30 AM
                        start_hour = int(match.group(1))
                        start_minute = int(match.group(2)) if match.group(2) else 0
                        start_ampm = match.group(3).lower()
                        
                        end_hour = int(match.group(4))
                        end_minute = int(match.group(5)) if match.group(5) else 0
                        end_ampm = match.group(6).lower()
                        
                        # Convert to 24-hour format
                        if 1 <= start_hour <= 12 and 1 <= end_hour <= 12:
                            if start_ampm == 'pm' and start_hour != 12:
                                start_hour += 12
                            elif start_ampm == 'am' and start_hour == 12:
                                start_hour = 0
                                
                            if end_ampm == 'pm' and end_hour != 12:
                                end_hour += 12
                            elif end_ampm == 'am' and end_hour == 12:
                                end_hour = 0
                            
                            start_time = time(start_hour, start_minute)
                            end_time = time(end_hour, end_minute)
                    
                    elif pattern_name == 'from_to_24hour':
                        # from 10:00 to 11:30
                        start_hour = int(match.group(1))
                        start_minute = int(match.group(2))
                        end_hour = int(match.group(3))
                        end_minute = int(match.group(4))
                        
                        if (0 <= start_hour <= 23 and 0 <= start_minute <= 59 and
                            0 <= end_hour <= 23 and 0 <= end_minute <= 59):
                            start_time = time(start_hour, start_minute)
                            end_time = time(end_hour, end_minute)
                    
                    elif pattern_name == 'from_to_mixed':
                        # More flexible pattern - handles various combinations
                        start_hour = int(match.group(1))
                        start_minute = int(match.group(2)) if match.group(2) else 0
                        start_ampm = match.group(3).lower() if match.group(3) else None
                        
                        end_hour = int(match.group(4))
                        end_minute = int(match.group(5)) if match.group(5) else 0
                        end_ampm = match.group(6).lower() if match.group(6) else None
                        
                        # Apply AM/PM conversion if specified
                        if start_ampm and 1 <= start_hour <= 12:
                            if start_ampm == 'pm' and start_hour != 12:
                                start_hour += 12
                            elif start_ampm == 'am' and start_hour == 12:
                                start_hour = 0
                        
                        if end_ampm and 1 <= end_hour <= 12:
                            if end_ampm == 'pm' and end_hour != 12:
                                end_hour += 12
                            elif end_ampm == 'am' and end_hour == 12:
                                end_hour = 0
                        
                        # If no AM/PM specified, use context or assume reasonable defaults
                        if not start_ampm and not end_ampm:
                            # If both times are in 24-hour format range, use as-is
                            if 0 <= start_hour <= 23 and 0 <= end_hour <= 23:
                                pass  # Use as-is
                            # If in 12-hour range, make reasonable assumptions
                            elif 1 <= start_hour <= 12 and 1 <= end_hour <= 12:
                                # Assume business hours context
                                if start_hour >= 8 and end_hour >= 8:
                                    # Likely AM for early hours, PM for later
                                    if start_hour <= 11:
                                        pass  # Keep as AM (or early 24-hour)
                                    else:
                                        start_hour += 12 if start_hour != 12 else 0
                                        end_hour += 12 if end_hour != 12 else 0
                                confidence = 0.8  # Lower confidence due to assumption
                        
                        if (0 <= start_hour <= 23 and 0 <= start_minute <= 59 and
                            0 <= end_hour <= 23 and 0 <= end_minute <= 59):
                            start_time = time(start_hour, start_minute)
                            end_time = time(end_hour, end_minute)
                    
                    elif pattern_name == 'simple_to_12hour':
                        # 9am to 12pm (without "from")
                        start_hour = int(match.group(1))
                        start_minute = int(match.group(2)) if match.group(2) else 0
                        start_ampm = match.group(3).lower()
                        
                        end_hour = int(match.group(4))
                        end_minute = int(match.group(5)) if match.group(5) else 0
                        end_ampm = match.group(6).lower()
                        
                        # Convert to 24-hour format
                        if 1 <= start_hour <= 12 and 1 <= end_hour <= 12:
                            if start_ampm == 'pm' and start_hour != 12:
                                start_hour += 12
                            elif start_ampm == 'am' and start_hour == 12:
                                start_hour = 0
                                
                            if end_ampm == 'pm' and end_hour != 12:
                                end_hour += 12
                            elif end_ampm == 'am' and end_hour == 12:
                                end_hour = 0
                            
                            start_time = time(start_hour, start_minute)
                            end_time = time(end_hour, end_minute)
                    
                    if start_time and end_time:
                        # Validate that end time is after start time
                        today = date.today()
                        start_dt = datetime.combine(today, start_time)
                        end_dt = datetime.combine(today, end_time)
                        
                        if end_dt <= start_dt:
                            # End time might be next day, or invalid range
                            if end_dt.time() < start_dt.time():
                                # Assume end time is next day
                                end_dt = end_dt + timedelta(days=1)
                            else:
                                # Invalid range, skip
                                continue
                        
                        # Create a match for the start time (the main datetime)
                        # Store end time information in a special way that can be retrieved
                        matches.append(DateTimeMatch(
                            value=start_dt,
                            confidence=confidence,
                            start_pos=match.start(),
                            end_pos=match.end(),
                            matched_text=match.group(0),
                            pattern_type=f"time_range_{pattern_name}"
                        ))
                        
                        # Also create a special end time match that can be identified
                        matches.append(DateTimeMatch(
                            value=end_dt,
                            confidence=confidence,
                            start_pos=match.start(),
                            end_pos=match.end(),
                            matched_text=match.group(0),
                            pattern_type=f"time_range_end_{pattern_name}"
                        ))
                
                except (ValueError, IndexError):
                    # Invalid time range, skip
                    continue
        
        return matches
    
    def _combine_date_time_range_matches(self, text: str, date_matches: List[DateTimeMatch], 
                                       time_range_matches: List[DateTimeMatch]) -> List[DateTimeMatch]:
        """Combine date matches with time range matches."""
        combined = []
        
        # Group time range matches by their matched text (start and end times from same range)
        range_groups = {}
        for time_match in time_range_matches:
            key = (time_match.start_pos, time_match.end_pos, time_match.matched_text)
            if key not in range_groups:
                range_groups[key] = []
            range_groups[key].append(time_match)
        
        for date_match in date_matches:
            best_range_group = None
            min_distance = float('inf')
            
            # Find the closest time range group
            for key, range_group in range_groups.items():
                start_pos, end_pos, matched_text = key
                distance = min(abs(date_match.start_pos - start_pos), abs(date_match.start_pos - end_pos))
                if distance < 150 and distance < min_distance:  # Within 150 characters
                    min_distance = distance
                    best_range_group = range_group
            
            if best_range_group and len(best_range_group) == 2:
                # Should have start and end time matches
                start_match = None
                end_match = None
                
                for time_match in best_range_group:
                    if time_match.pattern_type.startswith('time_range_end_'):
                        end_match = time_match
                    else:
                        start_match = time_match
                
                if start_match and end_match:
                    # Combine date with start time
                    start_dt = datetime.combine(date_match.value.date(), start_match.value.time())
                    
                    # Combine date with end time
                    end_dt = datetime.combine(date_match.value.date(), end_match.value.time())
                    
                    # If end time is before start time, assume it's next day
                    if end_dt <= start_dt:
                        end_dt = end_dt + timedelta(days=1)
                    
                    # Calculate combined confidence
                    combined_confidence = (date_match.confidence + start_match.confidence) / 2
                    
                    # Determine text span
                    start_pos = min(date_match.start_pos, start_match.start_pos)
                    end_pos = max(date_match.end_pos, start_match.end_pos)
                    matched_text = text[start_pos:end_pos]
                    
                    # Create start time match
                    combined.append(DateTimeMatch(
                        value=start_dt,
                        confidence=combined_confidence,
                        start_pos=start_pos,
                        end_pos=end_pos,
                        matched_text=matched_text,
                        pattern_type=f"{date_match.pattern_type}+{start_match.pattern_type}"
                    ))
                    
                    # Create end time match
                    combined.append(DateTimeMatch(
                        value=end_dt,
                        confidence=combined_confidence,
                        start_pos=start_pos,
                        end_pos=end_pos,
                        matched_text=matched_text,
                        pattern_type=f"{date_match.pattern_type}+{end_match.pattern_type}"
                    ))
        
        return combined
    
    def _combine_date_time_matches(self, text: str, date_matches: List[DateTimeMatch], 
                                 time_matches: List[DateTimeMatch]) -> List[DateTimeMatch]:
        """Combine date and time matches that appear close together in text."""
        combined = []
        
        for date_match in date_matches:
            best_time_match = None
            min_distance = float('inf')
            
            # Find the closest time match within reasonable distance
            for time_match in time_matches:
                distance = abs(date_match.start_pos - time_match.start_pos)
                if distance < 100 and distance < min_distance:  # Within 100 characters
                    min_distance = distance
                    best_time_match = time_match
            
            if best_time_match:
                # Combine date and time
                combined_dt = datetime.combine(
                    date_match.value.date(),
                    best_time_match.value.time()
                )
                
                # Calculate combined confidence
                combined_confidence = (date_match.confidence + best_time_match.confidence) / 2
                
                # Determine text span
                start_pos = min(date_match.start_pos, best_time_match.start_pos)
                end_pos = max(date_match.end_pos, best_time_match.end_pos)
                matched_text = text[start_pos:end_pos]
                
                combined.append(DateTimeMatch(
                    value=combined_dt,
                    confidence=combined_confidence,
                    start_pos=start_pos,
                    end_pos=end_pos,
                    matched_text=matched_text,
                    pattern_type=f"{date_match.pattern_type}+{best_time_match.pattern_type}"
                ))
        
        return combined
    
    def _extract_relative_dates(self, text: str) -> List[DateTimeMatch]:
        """Extract relative date patterns from text."""
        matches = []
        now = datetime.now()
        today = now.date()
        
        for pattern_name, pattern in self.relative_date_patterns.items():
            for match in pattern.finditer(text):
                try:
                    date_obj = None
                    confidence = 0.9
                    
                    if pattern_name == 'today':
                        date_obj = today
                        confidence = 0.95
                    
                    elif pattern_name == 'tomorrow':
                        date_obj = today + timedelta(days=1)
                        confidence = 0.95
                    
                    elif pattern_name == 'yesterday':
                        date_obj = today - timedelta(days=1)
                        confidence = 0.95
                    
                    elif pattern_name == 'next_weekday':
                        weekday_name = match.group(1).lower()
                        target_weekday = self.weekday_names[weekday_name]
                        date_obj = self._get_next_weekday(today, target_weekday)
                        confidence = 0.9
                    
                    elif pattern_name == 'this_weekday':
                        weekday_name = match.group(1).lower()
                        target_weekday = self.weekday_names[weekday_name]
                        date_obj = self._get_this_weekday(today, target_weekday)
                        confidence = 0.85  # Slightly lower confidence due to ambiguity
                    
                    elif pattern_name == 'in_days':
                        days = int(match.group(1))
                        date_obj = today + timedelta(days=days)
                        confidence = 0.9
                    
                    elif pattern_name == 'in_weeks':
                        weeks = int(match.group(1))
                        date_obj = today + timedelta(weeks=weeks)
                        confidence = 0.9
                    
                    elif pattern_name == 'in_months':
                        months = int(match.group(1))
                        date_obj = self._add_months(today, months)
                        confidence = 0.85  # Lower confidence due to month length variations
                    
                    elif pattern_name == 'days_from_now':
                        days = int(match.group(1))
                        date_obj = today + timedelta(days=days)
                        confidence = 0.9
                    
                    elif pattern_name == 'weeks_from_now':
                        weeks = int(match.group(1))
                        date_obj = today + timedelta(weeks=weeks)
                        confidence = 0.9
                    
                    if date_obj:
                        matches.append(DateTimeMatch(
                            value=datetime.combine(date_obj, time(0, 0)),
                            confidence=confidence,
                            start_pos=match.start(),
                            end_pos=match.end(),
                            matched_text=match.group(0),
                            pattern_type=f"relative_{pattern_name}"
                        ))
                
                except (ValueError, KeyError):
                    # Invalid relative date, skip
                    continue
        
        return matches
    
    def extract_durations(self, text: str) -> List[DurationMatch]:
        """Extract duration patterns from text."""
        matches = []
        
        for pattern_name, pattern in self.duration_patterns.items():
            for match in pattern.finditer(text):
                try:
                    duration = None
                    confidence = 0.9
                    
                    if pattern_name == 'for_hours':
                        hours = float(match.group(1))
                        duration = timedelta(hours=hours)
                        confidence = 0.95
                    
                    elif pattern_name == 'for_minutes':
                        minutes = int(match.group(1))
                        duration = timedelta(minutes=minutes)
                        confidence = 0.95
                    
                    elif pattern_name == 'for_hours_minutes':
                        hours = int(match.group(1))
                        minutes = int(match.group(3))
                        duration = timedelta(hours=hours, minutes=minutes)
                        confidence = 0.98  # Highest confidence for most specific pattern
                    
                    elif pattern_name == 'duration_hours':
                        hours = float(match.group(1))
                        duration = timedelta(hours=hours)
                        confidence = 0.8  # Lower confidence without "for" keyword
                    
                    elif pattern_name == 'duration_minutes':
                        minutes = int(match.group(1))
                        duration = timedelta(minutes=minutes)
                        confidence = 0.8
                    
                    elif pattern_name == 'duration_colon':
                        hours = int(match.group(1))
                        minutes = int(match.group(2))
                        duration = timedelta(hours=hours, minutes=minutes)
                        confidence = 0.9
                    
                    if duration:
                        matches.append(DurationMatch(
                            duration=duration,
                            confidence=confidence,
                            start_pos=match.start(),
                            end_pos=match.end(),
                            matched_text=match.group(0),
                            pattern_type=pattern_name
                        ))
                
                except ValueError:
                    # Invalid duration, skip
                    continue
        
        # Remove overlapping matches, keeping the most specific (highest confidence)
        filtered_matches = []
        for match in sorted(matches, key=lambda x: x.confidence, reverse=True):
            # Check if this match overlaps with any already accepted match
            overlaps = False
            for accepted in filtered_matches:
                if (match.start_pos < accepted.end_pos and match.end_pos > accepted.start_pos):
                    overlaps = True
                    break
            
            if not overlaps:
                filtered_matches.append(match)
        
        # Sort by confidence (highest first)
        filtered_matches.sort(key=lambda x: x.confidence, reverse=True)
        return filtered_matches
    
    def calculate_end_time(self, start_datetime: datetime, text: str) -> Optional[datetime]:
        """
        Calculate end time based on duration information in text.
        
        Args:
            start_datetime: The start datetime of the event
            text: Text to search for duration information
            
        Returns:
            End datetime if duration found, None otherwise
        """
        durations = self.extract_durations(text)
        if durations:
            # Use the most confident duration match
            best_duration = durations[0]
            return start_datetime + best_duration.duration
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
    
    def _add_months(self, start_date: date, months: int) -> date:
        """Add months to a date, handling month boundaries correctly."""
        month = start_date.month - 1 + months
        year = start_date.year + month // 12
        month = month % 12 + 1
        day = min(start_date.day, self._days_in_month(year, month))
        return date(year, month, day)
    
    def _days_in_month(self, year: int, month: int) -> int:
        """Get the number of days in a specific month and year."""
        if month == 2:
            return 29 if self._is_leap_year(year) else 28
        elif month in [4, 6, 9, 11]:
            return 30
        else:
            return 31
    
    def _is_leap_year(self, year: int) -> bool:
        """Check if a year is a leap year."""
        return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)
    
    def parse_single_datetime(self, text: str, prefer_dd_mm: bool = False) -> Optional[datetime]:
        """
        Parse text and return the most confident datetime match.
        
        Args:
            text: Input text to parse
            prefer_dd_mm: If True, interpret ambiguous dates as DD/MM instead of MM/DD
            
        Returns:
            Most confident datetime match or None if no valid datetime found
        """
        matches = self.extract_datetime(text, prefer_dd_mm)
        return matches[0].value if matches else None
    
    def get_parsing_metadata(self, text: str, prefer_dd_mm: bool = False) -> Dict[str, Any]:
        """
        Get detailed parsing information including all matches and confidence scores.
        
        Args:
            text: Input text to parse
            prefer_dd_mm: If True, interpret ambiguous dates as DD/MM instead of MM/DD
            
        Returns:
            Dictionary containing parsing metadata
        """
        matches = self.extract_datetime(text, prefer_dd_mm)
        durations = self.extract_durations(text)
        
        return {
            'total_matches': len(matches),
            'best_match': {
                'datetime': matches[0].value.isoformat() if matches else None,
                'confidence': matches[0].confidence if matches else 0.0,
                'matched_text': matches[0].matched_text if matches else None,
                'pattern_type': matches[0].pattern_type if matches else None
            } if matches else None,
            'all_matches': [
                {
                    'datetime': match.value.isoformat(),
                    'confidence': match.confidence,
                    'matched_text': match.matched_text,
                    'pattern_type': match.pattern_type,
                    'position': (match.start_pos, match.end_pos)
                }
                for match in matches
            ],
            'durations': [
                {
                    'duration_seconds': duration.duration.total_seconds(),
                    'duration_str': str(duration.duration),
                    'confidence': duration.confidence,
                    'matched_text': duration.matched_text,
                    'pattern_type': duration.pattern_type,
                    'position': (duration.start_pos, duration.end_pos)
                }
                for duration in durations
            ],
            'parsing_settings': {
                'prefer_dd_mm': prefer_dd_mm
            }
        }