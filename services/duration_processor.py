"""
Duration and all-day event processing service.

This module provides functionality for:
- Parsing duration expressions ("for 2 hours", "30 minutes")
- Converting "until" expressions ("until noon", "until 5pm")
- Detecting all-day event indicators
- Resolving conflicts between duration and explicit end times

Requirements addressed: 13.2, 13.3, 13.4, 13.6
"""

import re
from datetime import datetime, timedelta, time
from typing import Optional, Tuple, Dict, Any
from models.event_models import DurationResult


class DurationProcessor:
    """
    Processes duration and all-day event information from text.
    
    Handles various duration formats and resolves conflicts with explicit end times.
    """
    
    def __init__(self):
        """Initialize the duration processor with regex patterns."""
        # Duration patterns - "for X hours/minutes"
        self.duration_patterns = [
            # "for 2 hours", "for 30 minutes", "for 1.5 hours"
            r'for\s+(\d+(?:\.\d+)?)\s+(hours?|hrs?|h)\b',
            r'for\s+(\d+(?:\.\d+)?)\s+(minutes?|mins?|m)\b',
            # "2 hour meeting", "30 minute call" - fixed to include all minute variations
            r'(\d+(?:\.\d+)?)\s+(hour|hr|h)\s+(?:meeting|call|session|event)',
            r'(\d+(?:\.\d+)?)\s+(minutes?|mins?|minute|min|m)\s+(?:meeting|call|session|event|training)',
            # "lasting 2 hours", "takes 30 minutes"
            r'(?:lasting|takes?|runs?)\s+(\d+(?:\.\d+)?)\s+(hours?|hrs?|h)\b',
            r'(?:lasting|takes?|runs?)\s+(\d+(?:\.\d+)?)\s+(minutes?|mins?|m)\b',
            # Additional patterns for edge cases
            r'(\d+(?:\.\d+)?)\s+(hour|hr|h)\s+(?:long|duration|marathon)',
            r'(\d+(?:\.\d+)?)\s+(minutes?|mins?|minute|min|m)\s+(?:long|duration|marathon|call)',
        ]
        
        # Until time patterns - "until noon", "until 5pm"
        self.until_patterns = [
            # "until noon", "until midnight"
            r'until\s+(noon|midnight)\b',
            # "until 5pm", "until 17:00", "until 5:30 PM"
            r'until\s+(\d{1,2}):?(\d{2})?\s*(am|pm|a\.m\.|p\.m\.)\b',
            r'until\s+(\d{1,2}):(\d{2})\b',  # 24-hour format
            # "until 5", "until five"
            r'until\s+(\d{1,2})\b',
            r'until\s+(one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve)\b',
        ]
        
        # All-day indicators
        self.all_day_patterns = [
            r'\ball[\s-]?day\b',
            r'\bfull[\s-]?day\b',
            r'\bentire[\s-]?day\b',
            r'\bwhole[\s-]?day\b',
            r'\bthrough(?:out)?\s+the\s+day\b',
            r'\bfrom\s+morning\s+(?:to|until)\s+(?:evening|night)\b',
            r'\b(?:morning|afternoon|evening)\s+(?:to|until)\s+(?:afternoon|evening|night)\b',
        ]
        
        # Word to number mapping for time parsing
        self.word_to_number = {
            'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5, 'six': 6,
            'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10, 'eleven': 11, 'twelve': 12
        }
    
    def calculate_duration_end_time(self, start_datetime: datetime, text: str) -> DurationResult:
        """
        Calculate end time based on duration expressions in text.
        
        Args:
            start_datetime: The start time of the event
            text: Text containing duration information
            
        Returns:
            DurationResult with calculated duration and end time
            
        Requirements: 13.2 - "for 45 minutes" → calculate end time as start time + 45 minutes
        """
        if not start_datetime:
            return DurationResult(confidence=0.0)
        
        text_lower = text.lower()
        duration_minutes = None
        confidence = 0.0
        
        # Try to find duration patterns
        for pattern in self.duration_patterns:
            match = re.search(pattern, text_lower, re.IGNORECASE)
            if match:
                try:
                    value = float(match.group(1))
                    unit = match.group(2).lower()
                    
                    # Convert to minutes
                    if unit.startswith('h') or unit == 'hour':  # hours, hrs, h, hour
                        duration_minutes = int(value * 60)
                    elif unit.startswith('m') or 'min' in unit:  # minutes, mins, m, min, minute
                        duration_minutes = int(value)
                    
                    confidence = 0.8  # High confidence for explicit duration
                    break
                except (ValueError, IndexError):
                    continue
        
        if duration_minutes is None:
            return DurationResult(confidence=0.0)
        
        # Validate reasonable duration (5 minutes to 24 hours)
        if duration_minutes < 5 or duration_minutes > 1440:
            confidence *= 0.5  # Lower confidence for unusual durations
        
        return DurationResult(
            duration_minutes=duration_minutes,
            confidence=confidence
        )
    
    def parse_until_time(self, text: str, start_date: datetime) -> DurationResult:
        """
        Parse "until" expressions and convert to end time.
        
        Args:
            text: Text containing "until" expressions
            start_date: The start date to use for calculating end time
            
        Returns:
            DurationResult with end time override
            
        Requirements: 13.3 - "until noon" → set end time to 12:00 PM
        """
        if not start_date:
            return DurationResult(confidence=0.0)
        
        text_lower = text.lower()
        end_time_override = None
        confidence = 0.0
        
        # Try to find until patterns
        for pattern in self.until_patterns:
            match = re.search(pattern, text_lower, re.IGNORECASE)
            if match:
                try:
                    if 'noon' in match.group(0):
                        end_time_override = start_date.replace(hour=12, minute=0, second=0, microsecond=0)
                        confidence = 0.9
                        break
                    elif 'midnight' in match.group(0):
                        # Midnight of the next day
                        end_time_override = start_date.replace(hour=23, minute=59, second=59, microsecond=0)
                        confidence = 0.9
                        break
                    else:
                        # Parse time components
                        hour_str = match.group(1)
                        minute_str = match.group(2) if len(match.groups()) > 1 and match.group(2) else "00"
                        am_pm = match.group(3) if len(match.groups()) > 2 and match.group(3) else None
                        
                        # Convert hour
                        if hour_str.isdigit():
                            hour = int(hour_str)
                        elif hour_str in self.word_to_number:
                            hour = self.word_to_number[hour_str]
                            # For word numbers, assume PM for business hours (1-11)
                            if 1 <= hour <= 11:
                                hour += 12  # Convert to PM (5 -> 17)
                            elif hour == 12:
                                # 12 could be noon or midnight, assume midnight for "until twelve"
                                hour = 0  # midnight
                        else:
                            continue
                        
                        # Convert minute
                        minute = int(minute_str) if minute_str and minute_str.isdigit() else 0
                        
                        # Handle AM/PM
                        if am_pm:
                            am_pm_lower = am_pm.lower().replace('.', '')
                            if 'pm' in am_pm_lower and hour != 12:
                                hour += 12
                            elif 'am' in am_pm_lower and hour == 12:
                                hour = 0
                        
                        # Validate time
                        if 0 <= hour <= 23 and 0 <= minute <= 59:
                            end_time_override = start_date.replace(
                                hour=hour, minute=minute, second=0, microsecond=0
                            )
                            confidence = 0.8
                            break
                        
                except (ValueError, IndexError, AttributeError):
                    continue
        
        # Ensure end time is after start time
        if end_time_override and end_time_override <= start_date:
            # If end time is before or equal to start time, assume next day
            end_time_override = end_time_override + timedelta(days=1)
            confidence *= 0.7  # Lower confidence for next-day assumption
        
        return DurationResult(
            end_time_override=end_time_override,
            confidence=confidence
        )
    
    def detect_all_day_indicators(self, text: str) -> DurationResult:
        """
        Detect all-day event indicators in text.
        
        Args:
            text: Text to analyze for all-day indicators
            
        Returns:
            DurationResult with all_day flag set
            
        Requirements: 13.4 - "all-day" → create all-day event with no specific times
        """
        text_lower = text.lower()
        confidence = 0.0
        
        # Check for all-day patterns
        for pattern in self.all_day_patterns:
            if re.search(pattern, text_lower, re.IGNORECASE):
                confidence = 0.9
                break
        
        # Additional heuristics for all-day detection
        if confidence == 0.0:
            # Check for activity words that suggest all-day events
            all_day_activities = [
                'conference', 'workshop', 'retreat', 'festival', 'fair', 'exhibition',
                'vacation', 'holiday', 'trip', 'visit', 'birthday', 'anniversary'
            ]
            
            # Check if text contains all-day activity words
            has_all_day_activity = any(activity in text_lower for activity in all_day_activities)
            
            # Check if text has specific times that would contradict all-day
            has_specific_time = bool(re.search(r'\b\d{1,2}:\d{2}|\b\d{1,2}\s*(?:am|pm|a\.m\.|p\.m\.)\b', text_lower))
            
            if has_all_day_activity and not has_specific_time:
                confidence = 0.6
        
        return DurationResult(
            all_day=confidence > 0.5,
            confidence=confidence
        )
    
    def resolve_duration_conflicts(self, start_datetime: datetime, end_datetime: Optional[datetime], 
                                 duration_result: DurationResult) -> Tuple[Optional[datetime], DurationResult]:
        """
        Resolve conflicts between duration information and explicit end times.
        
        Args:
            start_datetime: The start time of the event
            end_datetime: Explicit end time if found
            duration_result: Duration information from text
            
        Returns:
            Tuple of (resolved_end_datetime, updated_duration_result)
            
        Requirements: 13.6 - When duration conflicts with explicit end time → prioritize explicit end time
        """
        if not start_datetime:
            return end_datetime, duration_result
        
        # If we have an explicit end time, prioritize it
        if end_datetime:
            # Calculate actual duration from explicit times
            actual_duration = end_datetime - start_datetime
            actual_minutes = int(actual_duration.total_seconds() / 60)
            
            # Update duration result with actual duration
            resolved_result = DurationResult(
                duration_minutes=actual_minutes,
                end_time_override=end_datetime,
                all_day=duration_result.all_day,
                confidence=max(0.9, duration_result.confidence)  # High confidence for explicit times
            )
            
            return end_datetime, resolved_result
        
        # If we have an end time override from "until" expressions
        if duration_result.end_time_override:
            calculated_duration = duration_result.end_time_override - start_datetime
            calculated_minutes = int(calculated_duration.total_seconds() / 60)
            
            resolved_result = DurationResult(
                duration_minutes=calculated_minutes,
                end_time_override=duration_result.end_time_override,
                all_day=duration_result.all_day,
                confidence=duration_result.confidence
            )
            
            return duration_result.end_time_override, resolved_result
        
        # If we have duration minutes, calculate end time
        if duration_result.duration_minutes:
            calculated_end = start_datetime + timedelta(minutes=duration_result.duration_minutes)
            
            resolved_result = DurationResult(
                duration_minutes=duration_result.duration_minutes,
                end_time_override=calculated_end,
                all_day=duration_result.all_day,
                confidence=duration_result.confidence
            )
            
            return calculated_end, resolved_result
        
        # If all-day event, set to full day
        if duration_result.all_day:
            # Set to start of day to end of day
            start_of_day = start_datetime.replace(hour=0, minute=0, second=0, microsecond=0)
            end_of_day = start_datetime.replace(hour=23, minute=59, second=59, microsecond=0)
            
            resolved_result = DurationResult(
                duration_minutes=1439,  # Almost 24 hours
                end_time_override=end_of_day,
                all_day=True,
                confidence=duration_result.confidence
            )
            
            return end_of_day, resolved_result
        
        # No duration information found
        return end_datetime, duration_result
    
    def process_duration_and_all_day(self, text: str, start_datetime: Optional[datetime], 
                                   end_datetime: Optional[datetime]) -> Tuple[Optional[datetime], DurationResult]:
        """
        Main method to process all duration and all-day information.
        
        Args:
            text: Text to analyze
            start_datetime: Start time of the event
            end_datetime: Explicit end time if found
            
        Returns:
            Tuple of (final_end_datetime, duration_result)
        """
        if not start_datetime:
            return end_datetime, DurationResult(confidence=0.0)
        
        # Check for all-day indicators first
        all_day_result = self.detect_all_day_indicators(text)
        
        # If it's an all-day event, handle it specially
        if all_day_result.all_day:
            return self.resolve_duration_conflicts(start_datetime, end_datetime, all_day_result)
        
        # Try to parse duration expressions
        duration_result = self.calculate_duration_end_time(start_datetime, text)
        
        # Try to parse "until" expressions
        until_result = self.parse_until_time(text, start_datetime)
        
        # Combine results, preferring "until" expressions over duration
        if until_result.end_time_override and until_result.confidence > 0:
            # Until expressions take priority when present
            combined_result = until_result
        elif duration_result.duration_minutes:
            combined_result = duration_result
        else:
            combined_result = DurationResult(confidence=0.0)
        
        # Resolve conflicts with explicit end time
        return self.resolve_duration_conflicts(start_datetime, end_datetime, combined_result)