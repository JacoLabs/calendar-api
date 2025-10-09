"""
Enhanced recurrence pattern processing for calendar events.

This module provides comprehensive recurrence pattern recognition and RRULE generation
for natural language recurrence expressions like "every other Tuesday", "monthly", etc.
"""

import re
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple
from models.event_models import RecurrenceResult


class RecurrenceProcessor:
    """
    Processes natural language recurrence patterns and converts them to RFC 5545 RRULE format.
    
    Supports:
    - Daily patterns: "daily", "every day", "each day"
    - Weekly patterns: "weekly", "every week", "every Tuesday"
    - Monthly patterns: "monthly", "every month", "first Monday of each month"
    - Interval patterns: "every other Tuesday", "every 2 weeks"
    - Custom patterns: Complex recurrence rules
    """
    
    def __init__(self):
        """Initialize the recurrence processor with pattern definitions."""
        self._weekday_map = {
            'monday': 'MO', 'mon': 'MO',
            'tuesday': 'TU', 'tue': 'TU', 'tues': 'TU',
            'wednesday': 'WE', 'wed': 'WE',
            'thursday': 'TH', 'thu': 'TH', 'thur': 'TH', 'thurs': 'TH',
            'friday': 'FR', 'fri': 'FR',
            'saturday': 'SA', 'sat': 'SA',
            'sunday': 'SU', 'sun': 'SU'
        }
        
        self._ordinal_map = {
            'first': '1', '1st': '1',
            'second': '2', '2nd': '2',
            'third': '3', '3rd': '3',
            'fourth': '4', '4th': '4',
            'fifth': '5', '5th': '5',
            'last': '-1'
        }
        
        self._interval_map = {
            'other': 2, 'two': 2, '2': 2,
            'three': 3, '3': 3,
            'four': 4, '4': 4,
            'five': 5, '5': 5,
            'six': 6, '6': 6
        }
        
        # Compile regex patterns for efficiency
        self._compile_patterns()
    
    def _compile_patterns(self):
        """Compile regex patterns for recurrence detection."""
        # Daily patterns
        self.daily_pattern = re.compile(
            r'\b(?:daily|every\s+day|each\s+day)\b',
            re.IGNORECASE
        )
        
        # Weekly patterns
        self.weekly_pattern = re.compile(
            r'\b(?:weekly|every\s+week|each\s+week)\b',
            re.IGNORECASE
        )
        
        # Monthly patterns
        self.monthly_pattern = re.compile(
            r'\b(?:monthly|every\s+month|each\s+month)\b',
            re.IGNORECASE
        )
        
        # Yearly patterns
        self.yearly_pattern = re.compile(
            r'\b(?:yearly|annually|every\s+year|each\s+year)\b',
            re.IGNORECASE
        )
        
        # Every other / interval patterns
        self.interval_pattern = re.compile(
            r'\bevery\s+(?:other|two|three|four|five|six|\d+)\s+(\w+)',
            re.IGNORECASE
        )
        
        # Specific weekday patterns
        weekdays = '|'.join(self._weekday_map.keys())
        self.weekday_pattern = re.compile(
            rf'\b(?:every\s+)?({weekdays})s?\b',
            re.IGNORECASE
        )
        
        # Ordinal patterns (first Monday, second Tuesday, etc.)
        ordinals = '|'.join(self._ordinal_map.keys())
        self.ordinal_pattern = re.compile(
            rf'\b({ordinals})\s+({weekdays})\s+(?:of\s+(?:each\s+|every\s+)?month|monthly)\b',
            re.IGNORECASE
        )
        
        # Complex interval patterns with numbers
        self.numeric_interval_pattern = re.compile(
            r'\bevery\s+(\d+)\s+(day|week|month|year)s?\b',
            re.IGNORECASE
        )
    
    def parse_recurrence_pattern(self, text: str) -> RecurrenceResult:
        """
        Parse natural language recurrence pattern and convert to RRULE.
        
        Args:
            text: Natural language text containing recurrence information
            
        Returns:
            RecurrenceResult with RRULE, confidence, and pattern type
        """
        if not text or not text.strip():
            return RecurrenceResult()
        
        text = text.strip().lower()
        
        # Try different pattern matching approaches in order of specificity
        
        # 1. Handle "every other" patterns first (most specific)
        every_other_result = self.handle_every_other_pattern(text)
        if every_other_result.rrule:
            return every_other_result
        
        # 2. Handle ordinal patterns (first Monday, second Tuesday, etc.)
        ordinal_result = self._handle_ordinal_pattern(text)
        if ordinal_result.rrule:
            return ordinal_result
        
        # 3. Handle numeric interval patterns (every 2 weeks, every 3 days)
        numeric_result = self._handle_numeric_interval_pattern(text)
        if numeric_result.rrule:
            return numeric_result
        
        # 4. Handle specific weekday patterns
        weekday_result = self._handle_weekday_pattern(text)
        if weekday_result.rrule:
            return weekday_result
        
        # 5. Handle basic frequency patterns
        basic_result = self._handle_basic_frequency_pattern(text)
        if basic_result.rrule:
            return basic_result
        
        # No pattern matched
        return RecurrenceResult(
            natural_language=text,
            confidence=0.0,
            pattern_type="none"
        )
    
    def handle_every_other_pattern(self, text: str) -> RecurrenceResult:
        """
        Handle "every other [day/week/Tuesday]" patterns.
        
        Args:
            text: Text containing "every other" pattern
            
        Returns:
            RecurrenceResult with RRULE for interval=2 pattern
        """
        if not text:
            return RecurrenceResult()
        
        original_text = text.strip()
        text = text.strip().lower()
        
        # Match "every other Tuesday" pattern
        match = re.search(r'\bevery\s+other\s+(\w+)', text, re.IGNORECASE)
        if match:
            period = match.group(1).lower()
            
            # Check if it's a weekday
            if period in self._weekday_map:
                weekday = self._weekday_map[period]
                rrule = f"FREQ=WEEKLY;INTERVAL=2;BYDAY={weekday}"
                return RecurrenceResult(
                    rrule=rrule,
                    natural_language=original_text,
                    confidence=0.9,
                    pattern_type="weekly"
                )
            
            # Check if it's a general period
            elif period in ['day', 'week', 'month', 'year']:
                freq_map = {
                    'day': 'DAILY',
                    'week': 'WEEKLY', 
                    'month': 'MONTHLY',
                    'year': 'YEARLY'
                }
                pattern_type_map = {
                    'day': 'daily',
                    'week': 'weekly', 
                    'month': 'monthly',
                    'year': 'yearly'
                }
                freq = freq_map[period]
                rrule = f"FREQ={freq};INTERVAL=2"
                return RecurrenceResult(
                    rrule=rrule,
                    natural_language=original_text,
                    confidence=0.9,
                    pattern_type=pattern_type_map[period]
                )
        
        # Match "every two [period]" pattern
        match = re.search(r'\bevery\s+(?:two|\d+)\s+(\w+)', text, re.IGNORECASE)
        if match:
            period = match.group(1).lower()
            
            # Extract interval number
            interval_match = re.search(r'\bevery\s+(two|\d+)', text, re.IGNORECASE)
            if interval_match:
                interval_text = interval_match.group(1).lower()
                interval = self._interval_map.get(interval_text, 2)
                if interval_text.isdigit():
                    interval = int(interval_text)
                
                if period in ['day', 'days']:
                    rrule = f"FREQ=DAILY;INTERVAL={interval}"
                    return RecurrenceResult(
                        rrule=rrule,
                        natural_language=original_text,
                        confidence=0.9,
                        pattern_type="daily"
                    )
                elif period in ['week', 'weeks']:
                    rrule = f"FREQ=WEEKLY;INTERVAL={interval}"
                    return RecurrenceResult(
                        rrule=rrule,
                        natural_language=original_text,
                        confidence=0.9,
                        pattern_type="weekly"
                    )
                elif period in ['month', 'months']:
                    rrule = f"FREQ=MONTHLY;INTERVAL={interval}"
                    return RecurrenceResult(
                        rrule=rrule,
                        natural_language=original_text,
                        confidence=0.9,
                        pattern_type="monthly"
                    )
                elif period in ['year', 'years']:
                    rrule = f"FREQ=YEARLY;INTERVAL={interval}"
                    return RecurrenceResult(
                        rrule=rrule,
                        natural_language=original_text,
                        confidence=0.9,
                        pattern_type="yearly"
                    )
        
        return RecurrenceResult()
    
    def _handle_ordinal_pattern(self, text: str) -> RecurrenceResult:
        """Handle ordinal patterns like 'first Monday of each month'."""
        match = self.ordinal_pattern.search(text)
        if match:
            ordinal = match.group(1).lower()
            weekday = match.group(2).lower()
            
            if ordinal in self._ordinal_map and weekday in self._weekday_map:
                ordinal_num = self._ordinal_map[ordinal]
                weekday_code = self._weekday_map[weekday]
                
                # Create RRULE for monthly recurrence with specific weekday
                rrule = f"FREQ=MONTHLY;BYDAY={ordinal_num}{weekday_code}"
                
                return RecurrenceResult(
                    rrule=rrule,
                    natural_language=text,
                    confidence=0.85,
                    pattern_type="monthly"
                )
        
        return RecurrenceResult()
    
    def _handle_numeric_interval_pattern(self, text: str) -> RecurrenceResult:
        """Handle numeric interval patterns like 'every 3 weeks'."""
        match = self.numeric_interval_pattern.search(text)
        if match:
            interval = int(match.group(1))
            period = match.group(2).lower()
            
            freq_map = {
                'day': 'DAILY',
                'week': 'WEEKLY',
                'month': 'MONTHLY', 
                'year': 'YEARLY'
            }
            
            if period in freq_map:
                freq = freq_map[period]
                rrule = f"FREQ={freq};INTERVAL={interval}"
                
                return RecurrenceResult(
                    rrule=rrule,
                    natural_language=text,
                    confidence=0.9,
                    pattern_type=period + "ly"
                )
        
        return RecurrenceResult()
    
    def _handle_weekday_pattern(self, text: str) -> RecurrenceResult:
        """Handle specific weekday patterns like 'every Tuesday'."""
        match = self.weekday_pattern.search(text)
        if match:
            weekday = match.group(1).lower()
            
            if weekday in self._weekday_map:
                weekday_code = self._weekday_map[weekday]
                rrule = f"FREQ=WEEKLY;BYDAY={weekday_code}"
                
                return RecurrenceResult(
                    rrule=rrule,
                    natural_language=text,
                    confidence=0.8,
                    pattern_type="weekly"
                )
        
        return RecurrenceResult()
    
    def _handle_basic_frequency_pattern(self, text: str) -> RecurrenceResult:
        """Handle basic frequency patterns like 'daily', 'weekly', 'monthly'."""
        if self.daily_pattern.search(text):
            return RecurrenceResult(
                rrule="FREQ=DAILY",
                natural_language=text,
                confidence=0.8,
                pattern_type="daily"
            )
        
        if self.weekly_pattern.search(text):
            return RecurrenceResult(
                rrule="FREQ=WEEKLY",
                natural_language=text,
                confidence=0.8,
                pattern_type="weekly"
            )
        
        if self.monthly_pattern.search(text):
            return RecurrenceResult(
                rrule="FREQ=MONTHLY",
                natural_language=text,
                confidence=0.8,
                pattern_type="monthly"
            )
        
        if self.yearly_pattern.search(text):
            return RecurrenceResult(
                rrule="FREQ=YEARLY",
                natural_language=text,
                confidence=0.8,
                pattern_type="yearly"
            )
        
        return RecurrenceResult()
    
    def validate_rrule_format(self, rrule: str) -> bool:
        """
        Validate RRULE format according to RFC 5545 specification.
        
        Args:
            rrule: RRULE string to validate
            
        Returns:
            True if RRULE is valid, False otherwise
        """
        if not rrule or not isinstance(rrule, str):
            return False
        
        # Basic format check - must start with FREQ=
        if not rrule.startswith('FREQ='):
            return False
        
        # Split into components
        components = rrule.split(';')
        
        # Validate each component
        valid_keys = {
            'FREQ', 'UNTIL', 'COUNT', 'INTERVAL', 'BYSECOND', 'BYMINUTE',
            'BYHOUR', 'BYDAY', 'BYMONTHDAY', 'BYYEARDAY', 'BYWEEKNO',
            'BYMONTH', 'BYSETPOS', 'WKST'
        }
        
        freq_values = {'SECONDLY', 'MINUTELY', 'HOURLY', 'DAILY', 'WEEKLY', 'MONTHLY', 'YEARLY'}
        weekday_values = {'SU', 'MO', 'TU', 'WE', 'TH', 'FR', 'SA'}
        
        freq_found = False
        
        for component in components:
            if '=' not in component:
                return False
            
            key, value = component.split('=', 1)
            
            if key not in valid_keys:
                return False
            
            # Validate specific components
            if key == 'FREQ':
                if value not in freq_values:
                    return False
                freq_found = True
            
            elif key == 'INTERVAL':
                try:
                    interval = int(value)
                    if interval < 1:
                        return False
                except ValueError:
                    return False
            
            elif key == 'COUNT':
                try:
                    count = int(value)
                    if count < 1:
                        return False
                except ValueError:
                    return False
            
            elif key == 'BYDAY':
                # Validate BYDAY format (e.g., MO, 1MO, -1FR)
                days = value.split(',')
                for day in days:
                    day = day.strip()
                    if not day:
                        return False
                    
                    # Check for ordinal prefix
                    if day[0].isdigit() or day[0] == '-':
                        # Extract ordinal and weekday
                        ordinal_match = re.match(r'^(-?\d+)([A-Z]{2})$', day)
                        if not ordinal_match:
                            return False
                        ordinal, weekday = ordinal_match.groups()
                        if weekday not in weekday_values:
                            return False
                        # Validate ordinal range (-53 to 53, excluding 0)
                        ordinal_num = int(ordinal)
                        if ordinal_num == 0 or ordinal_num < -53 or ordinal_num > 53:
                            return False
                    else:
                        # Just weekday
                        if day not in weekday_values:
                            return False
            
            elif key == 'BYMONTH':
                months = value.split(',')
                for month in months:
                    try:
                        month_num = int(month.strip())
                        if month_num < 1 or month_num > 12:
                            return False
                    except ValueError:
                        return False
            
            elif key == 'BYMONTHDAY':
                days = value.split(',')
                for day in days:
                    try:
                        day_num = int(day.strip())
                        if day_num == 0 or day_num < -31 or day_num > 31:
                            return False
                    except ValueError:
                        return False
        
        return freq_found
    
    def generate_rrule_for_pattern(self, pattern_type: str, interval: int = 1, 
                                 weekday: Optional[str] = None, 
                                 ordinal: Optional[int] = None) -> str:
        """
        Generate RRULE for specific pattern parameters.
        
        Args:
            pattern_type: Type of pattern ('daily', 'weekly', 'monthly', 'yearly')
            interval: Interval between occurrences (default 1)
            weekday: Specific weekday for weekly patterns (e.g., 'MO', 'TU')
            ordinal: Ordinal position for monthly patterns (e.g., 1 for first, -1 for last)
            
        Returns:
            RRULE string
        """
        freq_map = {
            'daily': 'DAILY',
            'weekly': 'WEEKLY',
            'monthly': 'MONTHLY',
            'yearly': 'YEARLY'
        }
        
        if pattern_type not in freq_map:
            raise ValueError(f"Invalid pattern_type: {pattern_type}")
        
        freq = freq_map[pattern_type]
        rrule_parts = [f"FREQ={freq}"]
        
        if interval > 1:
            rrule_parts.append(f"INTERVAL={interval}")
        
        if weekday:
            if ordinal:
                rrule_parts.append(f"BYDAY={ordinal}{weekday}")
            else:
                rrule_parts.append(f"BYDAY={weekday}")
        
        return ';'.join(rrule_parts)
    
    def extract_pattern_info(self, rrule: str) -> Dict[str, any]:
        """
        Extract pattern information from RRULE.
        
        Args:
            rrule: RRULE string to analyze
            
        Returns:
            Dictionary with pattern information
        """
        if not self.validate_rrule_format(rrule):
            return {}
        
        info = {}
        components = rrule.split(';')
        
        for component in components:
            key, value = component.split('=', 1)
            
            if key == 'FREQ':
                info['frequency'] = value.lower()
            elif key == 'INTERVAL':
                info['interval'] = int(value)
            elif key == 'BYDAY':
                info['weekdays'] = value.split(',')
            elif key == 'COUNT':
                info['count'] = int(value)
            elif key == 'UNTIL':
                info['until'] = value
            elif key == 'BYMONTH':
                info['months'] = [int(m) for m in value.split(',')]
            elif key == 'BYMONTHDAY':
                info['month_days'] = [int(d) for d in value.split(',')]
        
        return info
    
    def describe_rrule(self, rrule: str) -> str:
        """
        Convert RRULE back to natural language description.
        
        Args:
            rrule: RRULE string to describe
            
        Returns:
            Natural language description of the recurrence pattern
        """
        if not self.validate_rrule_format(rrule):
            return "Invalid recurrence pattern"
        
        info = self.extract_pattern_info(rrule)
        
        if not info:
            return "Unknown recurrence pattern"
        
        frequency = info.get('frequency', '')
        interval = info.get('interval', 1)
        weekdays = info.get('weekdays', [])
        
        # Reverse weekday mapping - use full names
        weekday_names = {
            'MO': 'monday', 'TU': 'tuesday', 'WE': 'wednesday', 'TH': 'thursday',
            'FR': 'friday', 'SA': 'saturday', 'SU': 'sunday'
        }
        
        if frequency == 'daily':
            if interval == 1:
                return "Daily"
            elif interval == 2:
                return "Every other day"
            else:
                return f"Every {interval} days"
        
        elif frequency == 'weekly':
            if weekdays:
                weekday_list = []
                for wd in weekdays:
                    # Handle ordinal weekdays (e.g., "1MO", "-1FR")
                    if wd[0].isdigit() or wd[0] == '-':
                        ordinal_match = re.match(r'^(-?\d+)([A-Z]{2})$', wd)
                        if ordinal_match:
                            ordinal, weekday_code = ordinal_match.groups()
                            weekday_name = weekday_names.get(weekday_code, weekday_code)
                            if ordinal == '1':
                                weekday_list.append(f"first {weekday_name}")
                            elif ordinal == '-1':
                                weekday_list.append(f"last {weekday_name}")
                            else:
                                weekday_list.append(f"{ordinal} {weekday_name}")
                    else:
                        weekday_name = weekday_names.get(wd, wd.lower())
                        weekday_list.append(weekday_name)
                
                weekday_str = ', '.join(weekday_list)
                
                if interval == 1:
                    return f"Every {weekday_str}"
                elif interval == 2:
                    return f"Every other {weekday_str}"
                else:
                    return f"Every {interval} weeks on {weekday_str}"
            else:
                if interval == 1:
                    return "Weekly"
                elif interval == 2:
                    return "Every other week"
                else:
                    return f"Every {interval} weeks"
        
        elif frequency == 'monthly':
            if interval == 1:
                return "Monthly"
            elif interval == 2:
                return "Every other month"
            else:
                return f"Every {interval} months"
        
        elif frequency == 'yearly':
            if interval == 1:
                return "Yearly"
            else:
                return f"Every {interval} years"
        
        return f"Every {interval} {frequency}" if interval > 1 else frequency.capitalize()