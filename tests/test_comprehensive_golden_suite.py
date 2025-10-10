"""
Comprehensive Golden Test Suite and Validation System.

This module implements comprehensive test cases covering all parsing scenarios,
regression testing for parsing accuracy improvements, test validation for confidence
thresholds and warning flags, automated accuracy evaluation against golden set,
and performance benchmarking and latency profiling.

Requirements addressed:
- 15.2: Golden set maintenance with 50-100 curated test cases
- 15.3: Reliability diagram generation for confidence calibration
- Task 16: Create golden test suite and validation
"""

import json
import logging
import statistics
import time
import unittest
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from unittest.mock import patch, MagicMock

from services.performance_monitor import PerformanceMonitor, GoldenTestCase, AccuracyResult
from services.event_parser import EventParser
from services.hybrid_event_parser import HybridEventParser
from models.event_models import ParsedEvent, FieldResult

logger = logging.getLogger(__name__)


class GoldenTestSuiteManager:
    """
    Manages comprehensive golden test suite with 50-100 curated test cases
    covering all parsing scenarios and edge cases.
    """
    
    def __init__(self, golden_set_path: str = "tests/golden_set.json"):
        """Initialize the golden test suite manager."""
        self.golden_set_path = Path(golden_set_path)
        self.performance_monitor = PerformanceMonitor(str(golden_set_path))
        self.test_categories = {
            'basic_datetime': [],
            'complex_formatting': [],
            'typos_variations': [],
            'relative_dates': [],
            'duration_allday': [],
            'location_extraction': [],
            'title_generation': [],
            'recurrence_patterns': [],
            'edge_cases': [],
            'multilingual': [],
            'confidence_thresholds': [],
            'warning_flags': []
        }
        self.load_comprehensive_test_cases()
    
    def load_comprehensive_test_cases(self):
        """Load comprehensive test cases covering all parsing scenarios."""
        # Basic DateTime Parsing (Requirements 2.1, 2.2)
        basic_datetime_cases = [
            GoldenTestCase(
                id="basic_dt_001",
                input_text="Meeting tomorrow at 2pm",
                expected_title="Meeting",
                expected_start=datetime(2025, 1, 2, 14, 0),
                expected_end=datetime(2025, 1, 2, 15, 0),
                category="basic_datetime",
                difficulty="easy",
                notes="Simple relative date with time"
            ),
            GoldenTestCase(
                id="basic_dt_002",
                input_text="Conference on March 15, 2025 at 10:30 AM",
                expected_title="Conference",
                expected_start=datetime(2025, 3, 15, 10, 30),
                expected_end=datetime(2025, 3, 15, 11, 30),
                category="basic_datetime",
                difficulty="easy",
                notes="Explicit date with AM/PM time"
            ),
            GoldenTestCase(
                id="basic_dt_003",
                input_text="Call on 12/25/2024 at 14:30",
                expected_title="Call",
                expected_start=datetime(2024, 12, 25, 14, 30),
                expected_end=datetime(2024, 12, 25, 15, 30),
                category="basic_datetime",
                difficulty="easy",
                notes="MM/DD/YYYY format with 24-hour time"
            ),
            GoldenTestCase(
                id="basic_dt_004",
                input_text="Workshop next Friday from 9:00-17:00",
                expected_title="Workshop",
                expected_start=datetime(2025, 1, 10, 9, 0),
                expected_end=datetime(2025, 1, 10, 17, 0),
                category="basic_datetime",
                difficulty="medium",
                notes="Relative date with time range"
            ),
            GoldenTestCase(
                id="basic_dt_005",
                input_text="Meeting at noon on January 1st",
                expected_title="Meeting",
                expected_start=datetime(2025, 1, 1, 12, 0),
                expected_end=datetime(2025, 1, 1, 13, 0),
                category="basic_datetime",
                difficulty="easy",
                notes="Named time (noon) with ordinal date"
            )
        ]
        
        # Complex Formatting (Requirement 6.1, 6.2, 6.3)
        complex_formatting_cases = [
            GoldenTestCase(
                id="complex_fmt_001",
                input_text="Indigenous Legacy Gathering\nMonday, Sep 29, 2025\n2–3pm\nNathan Phillips Square",
                expected_title="Indigenous Legacy Gathering",
                expected_start=datetime(2025, 9, 29, 14, 0),
                expected_end=datetime(2025, 9, 29, 15, 0),
                expected_location="Nathan Phillips Square",
                category="complex_formatting",
                difficulty="medium",
                notes="Multi-line format with en-dash time range"
            ),
            GoldenTestCase(
                id="complex_fmt_002",
                input_text="Project Review Meeting\n• Date: January 15, 2025\n• Time: 10:00 AM - 11:30 AM\n• Location: Conference Room B\n• Attendees: Team leads",
                expected_title="Project Review Meeting",
                expected_start=datetime(2025, 1, 15, 10, 0),
                expected_end=datetime(2025, 1, 15, 11, 30),
                expected_location="Conference Room B",
                category="complex_formatting",
                difficulty="hard",
                notes="Bullet point format with structured data"
            ),
            GoldenTestCase(
                id="complex_fmt_003",
                input_text="URGENT: Board Meeting\nWhen: Tomorrow 3:00 PM EST\nWhere: Executive Boardroom\nDuration: 2 hours\nRequired: All VPs",
                expected_title="Board Meeting",
                expected_start=datetime(2025, 1, 2, 15, 0),
                expected_end=datetime(2025, 1, 2, 17, 0),
                expected_location="Executive Boardroom",
                category="complex_formatting",
                difficulty="hard",
                notes="Email-style format with timezone and duration"
            ),
            GoldenTestCase(
                id="complex_fmt_004",
                input_text="Team Standup | Daily | 9:00 AM - 9:30 AM | Conference Room A | Every weekday",
                expected_title="Team Standup",
                expected_start=datetime(2025, 1, 2, 9, 0),
                expected_end=datetime(2025, 1, 2, 9, 30),
                expected_location="Conference Room A",
                category="complex_formatting",
                difficulty="medium",
                notes="Pipe-separated format with recurrence info"
            )
        ]
        
        # Typos and Variations (Requirement 6.5)
        typos_variations_cases = [
            GoldenTestCase(
                id="typo_001",
                input_text="Dentist appointment tommorow at 9a.m",
                expected_title="Dentist appointment",
                expected_start=datetime(2025, 1, 2, 9, 0),
                expected_end=datetime(2025, 1, 2, 10, 0),
                category="typos_variations",
                difficulty="medium",
                notes="Typo in 'tomorrow' and malformed time 'a.m'"
            ),
            GoldenTestCase(
                id="typo_002",
                input_text="Meting on 01/15/2025 at 2 PM for 45 minuts",
                expected_title="Meting",
                expected_start=datetime(2025, 1, 15, 14, 0),
                expected_end=datetime(2025, 1, 15, 14, 45),
                category="typos_variations",
                difficulty="medium",
                notes="Typos in 'Meeting' and 'minutes'"
            ),
            GoldenTestCase(
                id="typo_003",
                input_text="Conference cal at 3:30 P M next wendsday",
                expected_title="Conference cal",
                expected_start=datetime(2025, 1, 8, 15, 30),
                expected_end=datetime(2025, 1, 8, 16, 30),
                category="typos_variations",
                difficulty="medium",
                notes="Typos in 'call', spaced 'P M', and 'wednesday'"
            ),
            GoldenTestCase(
                id="typo_004",
                input_text="Training sesion 9:00 A M - 12:00 P M friday",
                expected_title="Training sesion",
                expected_start=datetime(2025, 1, 3, 9, 0),
                expected_end=datetime(2025, 1, 3, 12, 0),
                category="typos_variations",
                difficulty="medium",
                notes="Typo in 'session' and spaced AM/PM"
            )
        ]
        
        # Relative Dates (Requirement 2.3)
        relative_dates_cases = [
            GoldenTestCase(
                id="relative_001",
                input_text="Doctor appointment next week Tuesday at noon",
                expected_title="Doctor appointment",
                expected_start=datetime(2025, 1, 7, 12, 0),
                expected_end=datetime(2025, 1, 7, 13, 0),
                category="relative_dates",
                difficulty="medium",
                notes="Next week + specific day"
            ),
            GoldenTestCase(
                id="relative_002",
                input_text="Conference call in two weeks at 3:30 PM",
                expected_title="Conference call",
                expected_start=datetime(2025, 1, 15, 15, 30),
                expected_end=datetime(2025, 1, 15, 16, 30),
                category="relative_dates",
                difficulty="hard",
                notes="Relative week offset"
            ),
            GoldenTestCase(
                id="relative_003",
                input_text="Meeting the day after tomorrow at 10am",
                expected_title="Meeting",
                expected_start=datetime(2025, 1, 3, 10, 0),
                expected_end=datetime(2025, 1, 3, 11, 0),
                category="relative_dates",
                difficulty="medium",
                notes="Day after tomorrow phrase"
            ),
            GoldenTestCase(
                id="relative_004",
                input_text="Lunch this coming Monday at 12:30",
                expected_title="Lunch",
                expected_start=datetime(2025, 1, 6, 12, 30),
                expected_end=datetime(2025, 1, 6, 13, 30),
                category="relative_dates",
                difficulty="medium",
                notes="This coming + day of week"
            ),
            GoldenTestCase(
                id="relative_005",
                input_text="Workshop in 3 days at 2pm",
                expected_title="Workshop",
                expected_start=datetime(2025, 1, 4, 14, 0),
                expected_end=datetime(2025, 1, 4, 15, 0),
                category="relative_dates",
                difficulty="medium",
                notes="Numeric day offset"
            )
        ]
        
        # Duration and All-day Events (Requirements 2.4, 13.2, 13.3, 13.4)
        duration_allday_cases = [
            GoldenTestCase(
                id="duration_001",
                input_text="Workshop all day on March 1st",
                expected_title="Workshop",
                expected_start=datetime(2025, 3, 1, 0, 0),
                expected_end=datetime(2025, 3, 1, 23, 59),
                category="duration_allday",
                difficulty="easy",
                notes="All-day event detection"
            ),
            GoldenTestCase(
                id="duration_002",
                input_text="Training session from 9am until noon on Friday",
                expected_title="Training session",
                expected_start=datetime(2025, 1, 3, 9, 0),
                expected_end=datetime(2025, 1, 3, 12, 0),
                category="duration_allday",
                difficulty="medium",
                notes="Until time parsing"
            ),
            GoldenTestCase(
                id="duration_003",
                input_text="Meeting for 2 hours starting at 10am tomorrow",
                expected_title="Meeting",
                expected_start=datetime(2025, 1, 2, 10, 0),
                expected_end=datetime(2025, 1, 2, 12, 0),
                category="duration_allday",
                difficulty="medium",
                notes="Duration calculation from start time"
            ),
            GoldenTestCase(
                id="duration_004",
                input_text="Conference call for 45 minutes at 3pm",
                expected_title="Conference call",
                expected_start=datetime(2025, 1, 1, 15, 0),
                expected_end=datetime(2025, 1, 1, 15, 45),
                category="duration_allday",
                difficulty="medium",
                notes="Minute-based duration"
            ),
            GoldenTestCase(
                id="duration_005",
                input_text="All-day team building event on Friday",
                expected_title="All-day team building event",
                expected_start=datetime(2025, 1, 3, 0, 0),
                expected_end=datetime(2025, 1, 3, 23, 59),
                category="duration_allday",
                difficulty="easy",
                notes="All-day keyword detection"
            )
        ]
        
        # Location Extraction (Requirement 4)
        location_extraction_cases = [
            GoldenTestCase(
                id="location_001",
                input_text="Lunch with John next Friday from 12:30-1:30 at Cafe Downtown",
                expected_title="Lunch with John",
                expected_start=datetime(2025, 1, 10, 12, 30),
                expected_end=datetime(2025, 1, 10, 13, 30),
                expected_location="Cafe Downtown",
                category="location_extraction",
                difficulty="medium",
                notes="Simple location with 'at' preposition"
            ),
            GoldenTestCase(
                id="location_002",
                input_text="Meeting in Conference Room 205 tomorrow at 2pm",
                expected_title="Meeting",
                expected_start=datetime(2025, 1, 2, 14, 0),
                expected_end=datetime(2025, 1, 2, 15, 0),
                expected_location="Conference Room 205",
                category="location_extraction",
                difficulty="easy",
                notes="Room number location with 'in' preposition"
            ),
            GoldenTestCase(
                id="location_003",
                input_text="Client visit @ 123 Main Street, Toronto on Monday 10am",
                expected_title="Client visit",
                expected_start=datetime(2025, 1, 6, 10, 0),
                expected_end=datetime(2025, 1, 6, 11, 0),
                expected_location="123 Main Street, Toronto",
                category="location_extraction",
                difficulty="medium",
                notes="Full address with @ symbol"
            ),
            GoldenTestCase(
                id="location_004",
                input_text="Training session at the downtown office building",
                expected_title="Training session",
                expected_start=datetime(2025, 1, 1, 9, 0),
                expected_end=datetime(2025, 1, 1, 10, 0),
                expected_location="downtown office building",
                category="location_extraction",
                difficulty="medium",
                notes="Descriptive location"
            ),
            GoldenTestCase(
                id="location_005",
                input_text="Meet at the front entrance of City Hall at 3pm",
                expected_title="Meet",
                expected_start=datetime(2025, 1, 1, 15, 0),
                expected_end=datetime(2025, 1, 1, 16, 0),
                expected_location="front entrance of City Hall",
                category="location_extraction",
                difficulty="medium",
                notes="Directional location description"
            )
        ]
        
        # Title Generation (Requirement 5)
        title_generation_cases = [
            GoldenTestCase(
                id="title_001",
                input_text="Indigenous Legacy Gathering on Monday at 2pm",
                expected_title="Indigenous Legacy Gathering",
                expected_start=datetime(2025, 1, 6, 14, 0),
                expected_end=datetime(2025, 1, 6, 15, 0),
                category="title_generation",
                difficulty="easy",
                notes="Explicit formal title"
            ),
            GoldenTestCase(
                id="title_002",
                input_text="Lunch with Sarah and Mike tomorrow at noon",
                expected_title="Lunch with Sarah and Mike",
                expected_start=datetime(2025, 1, 2, 12, 0),
                expected_end=datetime(2025, 1, 2, 13, 0),
                category="title_generation",
                difficulty="medium",
                notes="Activity with people"
            ),
            GoldenTestCase(
                id="title_003",
                input_text="Tomorrow at 9am dentist appointment",
                expected_title="dentist appointment",
                expected_start=datetime(2025, 1, 2, 9, 0),
                expected_end=datetime(2025, 1, 2, 10, 0),
                category="title_generation",
                difficulty="medium",
                notes="Title at end of sentence"
            ),
            GoldenTestCase(
                id="title_004",
                input_text="Pick up dry cleaning after work on Friday",
                expected_title="Pick up dry cleaning",
                expected_start=datetime(2025, 1, 3, 17, 0),
                expected_end=datetime(2025, 1, 3, 18, 0),
                category="title_generation",
                difficulty="medium",
                notes="Action-based title generation"
            )
        ]
        
        # Edge Cases and Boundary Conditions
        edge_cases = [
            GoldenTestCase(
                id="edge_001",
                input_text="Meeting at midnight on New Year's Eve",
                expected_title="Meeting",
                expected_start=datetime(2024, 12, 31, 0, 0),
                expected_end=datetime(2024, 12, 31, 1, 0),
                category="edge_cases",
                difficulty="hard",
                notes="Midnight boundary case"
            ),
            GoldenTestCase(
                id="edge_002",
                input_text="Conference call spanning midnight from 11:30 PM to 12:30 AM",
                expected_title="Conference call",
                expected_start=datetime(2025, 1, 1, 23, 30),
                expected_end=datetime(2025, 1, 2, 0, 30),
                category="edge_cases",
                difficulty="hard",
                notes="Cross-midnight time span"
            ),
            GoldenTestCase(
                id="edge_003",
                input_text="Leap year meeting on February 29, 2024 at 2pm",
                expected_title="Leap year meeting",
                expected_start=datetime(2024, 2, 29, 14, 0),
                expected_end=datetime(2024, 2, 29, 15, 0),
                category="edge_cases",
                difficulty="medium",
                notes="Leap year date handling"
            ),
            GoldenTestCase(
                id="edge_004",
                input_text="Very long meeting title that goes on and on and includes many details about the project review and quarterly planning session tomorrow at 10am",
                expected_title="Very long meeting title that goes on and on and includes many details about the project review and quarterly planning session",
                expected_start=datetime(2025, 1, 2, 10, 0),
                expected_end=datetime(2025, 1, 2, 11, 0),
                category="edge_cases",
                difficulty="medium",
                notes="Very long title handling"
            )
        ]
        
        # Confidence Threshold Test Cases
        confidence_threshold_cases = [
            GoldenTestCase(
                id="conf_high_001",
                input_text="Team meeting tomorrow at 2:00 PM in Conference Room A",
                expected_title="Team meeting",
                expected_start=datetime(2025, 1, 2, 14, 0),
                expected_end=datetime(2025, 1, 2, 15, 0),
                expected_location="Conference Room A",
                category="confidence_thresholds",
                difficulty="easy",
                notes="High confidence case - clear datetime and location"
            ),
            GoldenTestCase(
                id="conf_med_001",
                input_text="Maybe lunch sometime next week with the client",
                expected_title="lunch with the client",
                expected_start=datetime(2025, 1, 6, 12, 0),
                expected_end=datetime(2025, 1, 6, 13, 0),
                category="confidence_thresholds",
                difficulty="hard",
                notes="Medium confidence - vague timing"
            ),
            GoldenTestCase(
                id="conf_low_001",
                input_text="We should probably meet up soon to discuss things",
                expected_title="meet up to discuss things",
                expected_start=datetime(2025, 1, 2, 10, 0),
                expected_end=datetime(2025, 1, 2, 11, 0),
                category="confidence_thresholds",
                difficulty="hard",
                notes="Low confidence - very vague"
            )
        ]
        
        # Warning Flags Test Cases
        warning_flags_cases = [
            GoldenTestCase(
                id="warn_001",
                input_text="Meeting on 13/25/2024 at 25:00",
                expected_title="Meeting",
                expected_start=datetime(2025, 1, 1, 10, 0),
                expected_end=datetime(2025, 1, 1, 11, 0),
                category="warning_flags",
                difficulty="hard",
                notes="Invalid date/time should trigger warnings"
            ),
            GoldenTestCase(
                id="warn_002",
                input_text="Call at 2 on 5/3",
                expected_title="Call",
                expected_start=datetime(2025, 5, 3, 14, 0),
                expected_end=datetime(2025, 5, 3, 15, 0),
                category="warning_flags",
                difficulty="medium",
                notes="Ambiguous time (AM/PM) and date format"
            )
        ]
        
        # Add more test cases to reach 50+ requirement
        additional_basic_cases = [
            GoldenTestCase(
                id="basic_dt_006",
                input_text="Staff meeting every Monday at 9:30 AM",
                expected_title="Staff meeting",
                expected_start=datetime(2025, 1, 6, 9, 30),
                expected_end=datetime(2025, 1, 6, 10, 30),
                category="basic_datetime",
                difficulty="medium",
                notes="Recurring meeting pattern"
            ),
            GoldenTestCase(
                id="basic_dt_007",
                input_text="Appointment on 2025-03-15 at 14:45",
                expected_title="Appointment",
                expected_start=datetime(2025, 3, 15, 14, 45),
                expected_end=datetime(2025, 3, 15, 15, 45),
                category="basic_datetime",
                difficulty="easy",
                notes="ISO date format"
            ),
            GoldenTestCase(
                id="basic_dt_008",
                input_text="Call this afternoon at 3",
                expected_title="Call",
                expected_start=datetime(2025, 1, 1, 15, 0),
                expected_end=datetime(2025, 1, 1, 16, 0),
                category="basic_datetime",
                difficulty="medium",
                notes="Relative time reference"
            )
        ]
        basic_datetime_cases.extend(additional_basic_cases)
        
        # Add more complex cases
        additional_complex_cases = [
            GoldenTestCase(
                id="complex_fmt_005",
                input_text="Event Details:\nTitle: Annual Conference\nDate: March 20, 2025\nTime: 9:00 AM - 5:00 PM\nVenue: Convention Center",
                expected_title="Annual Conference",
                expected_start=datetime(2025, 3, 20, 9, 0),
                expected_end=datetime(2025, 3, 20, 17, 0),
                expected_location="Convention Center",
                category="complex_formatting",
                difficulty="medium",
                notes="Structured event details format"
            ),
            GoldenTestCase(
                id="complex_fmt_006",
                input_text="REMINDER: Doctor's appointment\nScheduled for: Tomorrow 2:30 PM\nLocation: Medical Center, Suite 200\nDuration: 30 minutes",
                expected_title="Doctor's appointment",
                expected_start=datetime(2025, 1, 2, 14, 30),
                expected_end=datetime(2025, 1, 2, 15, 0),
                expected_location="Medical Center, Suite 200",
                category="complex_formatting",
                difficulty="medium",
                notes="Reminder format with duration"
            )
        ]
        complex_formatting_cases.extend(additional_complex_cases)
        
        # Add more edge cases
        additional_edge_cases = [
            GoldenTestCase(
                id="edge_005",
                input_text="Meeting on the 31st of February",
                expected_title="Meeting",
                expected_start=datetime(2025, 3, 3, 10, 0),  # Should default to valid date
                expected_end=datetime(2025, 3, 3, 11, 0),
                category="edge_cases",
                difficulty="hard",
                notes="Invalid date should be handled gracefully"
            ),
            GoldenTestCase(
                id="edge_006",
                input_text="Conference call at 25:00 hours",
                expected_title="Conference call",
                expected_start=datetime(2025, 1, 2, 1, 0),  # Should default to 1 AM next day
                expected_end=datetime(2025, 1, 2, 2, 0),
                category="edge_cases",
                difficulty="hard",
                notes="Invalid time should be handled gracefully"
            )
        ]
        edge_cases.extend(additional_edge_cases)
        
        # Add more test cases to reach 50+ requirement
        additional_misc_cases = [
            GoldenTestCase(
                id="misc_001",
                input_text="Breakfast meeting at 8 AM sharp tomorrow",
                expected_title="Breakfast meeting",
                expected_start=datetime(2025, 1, 2, 8, 0),
                expected_end=datetime(2025, 1, 2, 9, 0),
                category="basic_datetime",
                difficulty="easy",
                notes="Sharp time indicator"
            ),
            GoldenTestCase(
                id="misc_002",
                input_text="Late night coding session from 10 PM to 2 AM",
                expected_title="Late night coding session",
                expected_start=datetime(2025, 1, 1, 22, 0),
                expected_end=datetime(2025, 1, 2, 2, 0),
                category="edge_cases",
                difficulty="medium",
                notes="Cross-midnight session"
            ),
            GoldenTestCase(
                id="misc_003",
                input_text="Quick standup in 15 minutes",
                expected_title="Quick standup",
                expected_start=datetime(2025, 1, 1, 9, 15),
                expected_end=datetime(2025, 1, 1, 10, 15),
                category="relative_dates",
                difficulty="medium",
                notes="Relative time in minutes"
            )
        ]
        basic_datetime_cases.extend(additional_misc_cases)

        # Store all test cases by category
        self.test_categories = {
            'basic_datetime': basic_datetime_cases,
            'complex_formatting': complex_formatting_cases,
            'typos_variations': typos_variations_cases,
            'relative_dates': relative_dates_cases,
            'duration_allday': duration_allday_cases,
            'location_extraction': location_extraction_cases,
            'title_generation': title_generation_cases,
            'edge_cases': edge_cases,
            'confidence_thresholds': confidence_threshold_cases,
            'warning_flags': warning_flags_cases
        }
        
        # Flatten all test cases
        all_test_cases = []
        for category_cases in self.test_categories.values():
            all_test_cases.extend(category_cases)
        
        # Update performance monitor with comprehensive test cases
        self.performance_monitor.golden_test_cases = all_test_cases
        self.performance_monitor.save_golden_set()
        
        logger.info(f"Loaded {len(all_test_cases)} comprehensive test cases across {len(self.test_categories)} categories")
    
    def get_test_cases_by_category(self, category: str) -> List[GoldenTestCase]:
        """Get test cases for a specific category."""
        return self.test_categories.get(category, [])
    
    def get_all_test_cases(self) -> List[GoldenTestCase]:
        """Get all test cases."""
        all_cases = []
        for category_cases in self.test_categories.values():
            all_cases.extend(category_cases)
        return all_cases
    
    def get_test_statistics(self) -> Dict[str, Any]:
        """Get statistics about the test suite."""
        stats = {
            'total_cases': 0,
            'categories': {},
            'difficulty_distribution': defaultdict(int),
            'coverage_areas': []
        }
        
        for category, cases in self.test_categories.items():
            stats['categories'][category] = len(cases)
            stats['total_cases'] += len(cases)
            
            for case in cases:
                stats['difficulty_distribution'][case.difficulty] += 1
        
        # Coverage areas based on requirements
        stats['coverage_areas'] = [
            'Basic DateTime Parsing (Req 2.1, 2.2)',
            'Complex Text Formatting (Req 6.1, 6.2, 6.3)',
            'Typo Tolerance (Req 6.5)',
            'Relative Date Conversion (Req 2.3)',
            'Duration and All-day Events (Req 2.4, 13.2-13.4)',
            'Location Extraction (Req 4)',
            'Title Generation (Req 5)',
            'Edge Cases and Boundaries',
            'Confidence Threshold Validation',
            'Warning Flag Generation'
        ]
        
        return stats


class RegressionTestValidator:
    """
    Validates parsing accuracy improvements and detects regressions
    by comparing current performance against historical baselines.
    """
    
    def __init__(self, baseline_path: str = "tests/regression_baseline.json"):
        """Initialize regression test validator."""
        self.baseline_path = Path(baseline_path)
        self.baseline_results = self.load_baseline()
        self.current_results = {}
        
    def load_baseline(self) -> Dict[str, Any]:
        """Load baseline results from file."""
        if self.baseline_path.exists():
            try:
                with open(self.baseline_path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Could not load baseline: {e}")
        
        return {
            'version': '1.0',
            'timestamp': datetime.now().isoformat(),
            'test_results': {},
            'performance_metrics': {},
            'accuracy_thresholds': {
                'overall_accuracy': 0.85,
                'title_accuracy': 0.90,
                'datetime_accuracy': 0.95,
                'location_accuracy': 0.80
            }
        }
    
    def save_baseline(self, results: Dict[str, Any]):
        """Save current results as new baseline."""
        baseline_data = {
            'version': '1.0',
            'timestamp': datetime.now().isoformat(),
            'test_results': results.get('test_results', {}),
            'performance_metrics': results.get('performance_metrics', {}),
            'accuracy_thresholds': results.get('accuracy_thresholds', {})
        }
        
        try:
            self.baseline_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.baseline_path, 'w') as f:
                json.dump(baseline_data, f, indent=2)
            logger.info(f"Saved new baseline to {self.baseline_path}")
        except Exception as e:
            logger.error(f"Could not save baseline: {e}")
    
    def validate_regression(self, current_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate current results against baseline to detect regressions.
        
        Args:
            current_results: Current test results to validate
            
        Returns:
            Dictionary with regression analysis results
        """
        self.current_results = current_results
        
        regression_analysis = {
            'timestamp': datetime.now().isoformat(),
            'has_regression': False,
            'improvements': [],
            'regressions': [],
            'performance_changes': {},
            'accuracy_changes': {},
            'recommendations': []
        }
        
        # Compare overall accuracy
        baseline_accuracy = self.baseline_results.get('performance_metrics', {}).get('overall_accuracy', 0.0)
        current_accuracy = current_results.get('overall_accuracy', 0.0)
        
        accuracy_change = current_accuracy - baseline_accuracy
        regression_analysis['accuracy_changes']['overall'] = {
            'baseline': baseline_accuracy,
            'current': current_accuracy,
            'change': accuracy_change,
            'change_percent': (accuracy_change / baseline_accuracy * 100) if baseline_accuracy > 0 else 0
        }
        
        # Significant regression threshold (5% decrease)
        if accuracy_change < -0.05:
            regression_analysis['has_regression'] = True
            regression_analysis['regressions'].append(
                f"Overall accuracy decreased by {abs(accuracy_change):.3f} ({accuracy_change/baseline_accuracy*100:.1f}%)" if baseline_accuracy > 0 else f"Overall accuracy decreased by {abs(accuracy_change):.3f}"
            )
        elif accuracy_change > 0.02:
            regression_analysis['improvements'].append(
                f"Overall accuracy improved by {accuracy_change:.3f} ({accuracy_change/baseline_accuracy*100:.1f}%)" if baseline_accuracy > 0 else f"Overall accuracy improved by {accuracy_change:.3f}"
            )
        
        # Compare field accuracies
        baseline_fields = self.baseline_results.get('performance_metrics', {}).get('field_accuracies', {})
        current_fields = current_results.get('field_accuracies', {})
        
        for field in set(baseline_fields.keys()) | set(current_fields.keys()):
            baseline_val = baseline_fields.get(field, {}).get('mean', 0.0)
            current_val = current_fields.get(field, {}).get('mean', 0.0)
            
            field_change = current_val - baseline_val
            regression_analysis['accuracy_changes'][field] = {
                'baseline': baseline_val,
                'current': current_val,
                'change': field_change,
                'change_percent': (field_change / baseline_val * 100) if baseline_val > 0 else 0
            }
            
            if field_change < -0.05:  # 5% regression threshold
                regression_analysis['has_regression'] = True
                regression_analysis['regressions'].append(
                    f"{field} accuracy decreased by {abs(field_change):.3f}"
                )
            elif field_change > 0.02:  # 2% improvement threshold
                regression_analysis['improvements'].append(
                    f"{field} accuracy improved by {field_change:.3f}"
                )
        
        # Compare performance metrics
        baseline_perf = self.baseline_results.get('performance_metrics', {}).get('performance_stats', {})
        current_perf = current_results.get('performance_stats', {})
        
        for metric in ['mean_processing_time_ms', 'median_processing_time_ms']:
            baseline_val = baseline_perf.get(metric, 0.0)
            current_val = current_perf.get(metric, 0.0)
            
            if baseline_val > 0:
                perf_change = current_val - baseline_val
                perf_change_percent = perf_change / baseline_val * 100
                
                regression_analysis['performance_changes'][metric] = {
                    'baseline': baseline_val,
                    'current': current_val,
                    'change': perf_change,
                    'change_percent': perf_change_percent
                }
                
                # Performance regression if >20% slower
                if perf_change_percent > 20:
                    regression_analysis['has_regression'] = True
                    regression_analysis['regressions'].append(
                        f"{metric} increased by {perf_change:.1f}ms ({perf_change_percent:.1f}%)"
                    )
                elif perf_change_percent < -10:  # Performance improvement
                    regression_analysis['improvements'].append(
                        f"{metric} improved by {abs(perf_change):.1f}ms ({abs(perf_change_percent):.1f}%)"
                    )
        
        # Generate recommendations
        if regression_analysis['has_regression']:
            regression_analysis['recommendations'].extend([
                "Review recent changes that may have caused performance or accuracy regressions",
                "Run focused tests on regressed components",
                "Consider reverting recent changes if regressions are severe"
            ])
        
        if regression_analysis['improvements']:
            regression_analysis['recommendations'].append(
                "Document improvements and update baseline if changes are intentional"
            )
        
        return regression_analysis


class ConfidenceThresholdValidator:
    """
    Validates confidence thresholds and warning flags to ensure
    the system properly indicates uncertainty and potential issues.
    """
    
    def __init__(self):
        """Initialize confidence threshold validator."""
        self.confidence_thresholds = {
            'high_confidence': 0.8,
            'medium_confidence': 0.6,
            'low_confidence': 0.4,
            'needs_confirmation': 0.6
        }
        
        self.expected_warnings = {
            'ambiguous_datetime': ['ambiguous', 'unclear', 'multiple'],
            'invalid_datetime': ['invalid', 'impossible', 'malformed'],
            'missing_required': ['missing', 'required', 'incomplete'],
            'low_confidence': ['uncertain', 'confidence', 'verify']
        }
    
    def validate_confidence_calibration(self, test_results: List[AccuracyResult]) -> Dict[str, Any]:
        """
        Validate that confidence scores are well-calibrated with actual accuracy.
        
        Args:
            test_results: List of accuracy results with confidence scores
            
        Returns:
            Dictionary with calibration analysis
        """
        if not test_results:
            return {'error': 'No test results provided'}
        
        # Group results by confidence bins
        confidence_bins = defaultdict(list)
        for result in test_results:
            if result.predicted_event and result.predicted_event.confidence_score > 0:
                bin_center = round(result.predicted_event.confidence_score, 1)
                confidence_bins[bin_center].append(result)
        
        calibration_analysis = {
            'timestamp': datetime.now().isoformat(),
            'total_predictions': len(test_results),
            'confidence_bins': {},
            'calibration_error': 0.0,
            'reliability_curve': [],
            'is_well_calibrated': False,
            'recommendations': []
        }
        
        # Analyze each confidence bin
        total_weighted_error = 0.0
        total_predictions = 0
        
        for bin_center, bin_results in confidence_bins.items():
            if not bin_results:
                continue
            
            # Calculate actual accuracy for this bin
            accuracies = [r.accuracy_score for r in bin_results]
            actual_accuracy = statistics.mean(accuracies)
            predicted_confidence = bin_center
            
            # Calculate calibration error for this bin
            bin_error = abs(predicted_confidence - actual_accuracy)
            bin_weight = len(bin_results)
            
            total_weighted_error += bin_error * bin_weight
            total_predictions += bin_weight
            
            calibration_analysis['confidence_bins'][str(bin_center)] = {
                'predicted_confidence': predicted_confidence,
                'actual_accuracy': actual_accuracy,
                'count': len(bin_results),
                'calibration_error': bin_error,
                'accuracy_range': [min(accuracies), max(accuracies)]
            }
            
            calibration_analysis['reliability_curve'].append({
                'confidence': predicted_confidence,
                'accuracy': actual_accuracy,
                'count': len(bin_results)
            })
        
        # Calculate Expected Calibration Error (ECE)
        if total_predictions > 0:
            calibration_analysis['calibration_error'] = total_weighted_error / total_predictions
        
        # Determine if well-calibrated (ECE < 0.1)
        calibration_analysis['is_well_calibrated'] = calibration_analysis['calibration_error'] < 0.1
        
        # Generate recommendations
        if not calibration_analysis['is_well_calibrated']:
            calibration_analysis['recommendations'].extend([
                "Confidence scores are poorly calibrated with actual accuracy",
                "Consider adjusting confidence calculation algorithms",
                "Review confidence thresholds for different parsing methods"
            ])
        
        # Check for specific calibration issues
        for bin_center, bin_data in calibration_analysis['confidence_bins'].items():
            if bin_data['calibration_error'] > 0.15:  # Significant miscalibration
                if bin_data['predicted_confidence'] > bin_data['actual_accuracy']:
                    calibration_analysis['recommendations'].append(
                        f"Overconfident predictions in {bin_center} confidence range"
                    )
                else:
                    calibration_analysis['recommendations'].append(
                        f"Underconfident predictions in {bin_center} confidence range"
                    )
        
        return calibration_analysis
    
    def validate_warning_flags(self, test_results: List[AccuracyResult]) -> Dict[str, Any]:
        """
        Validate that appropriate warning flags are generated for problematic cases.
        
        Args:
            test_results: List of accuracy results to analyze
            
        Returns:
            Dictionary with warning flag validation results
        """
        warning_analysis = {
            'timestamp': datetime.now().isoformat(),
            'total_cases': len(test_results),
            'warning_categories': {},
            'missing_warnings': [],
            'false_warnings': [],
            'warning_accuracy': 0.0,
            'recommendations': []
        }
        
        # Analyze warning flags for each test result
        correct_warnings = 0
        total_warning_opportunities = 0
        
        for result in test_results:
            if not result.predicted_event:
                continue
            
            test_case_id = result.test_case_id
            predicted_event = result.predicted_event
            
            # Check if warnings should be present based on test case category
            should_have_warnings = self._should_have_warnings(test_case_id, result)
            actual_warnings = getattr(predicted_event, 'warnings', [])
            
            total_warning_opportunities += 1
            
            if should_have_warnings and actual_warnings:
                # Check if warnings are appropriate
                if self._are_warnings_appropriate(should_have_warnings, actual_warnings):
                    correct_warnings += 1
                else:
                    warning_analysis['false_warnings'].append({
                        'test_case': test_case_id,
                        'expected_warnings': should_have_warnings,
                        'actual_warnings': actual_warnings
                    })
            elif should_have_warnings and not actual_warnings:
                warning_analysis['missing_warnings'].append({
                    'test_case': test_case_id,
                    'expected_warnings': should_have_warnings,
                    'accuracy_score': result.accuracy_score
                })
            elif not should_have_warnings and actual_warnings:
                warning_analysis['false_warnings'].append({
                    'test_case': test_case_id,
                    'unexpected_warnings': actual_warnings
                })
            else:
                # No warnings expected or present - correct
                correct_warnings += 1
        
        # Calculate warning accuracy
        if total_warning_opportunities > 0:
            warning_analysis['warning_accuracy'] = correct_warnings / total_warning_opportunities
        
        # Categorize warning types
        for category, keywords in self.expected_warnings.items():
            warning_analysis['warning_categories'][category] = {
                'expected_count': 0,
                'actual_count': 0,
                'accuracy': 0.0
            }
        
        # Generate recommendations
        if warning_analysis['warning_accuracy'] < 0.8:
            warning_analysis['recommendations'].extend([
                "Warning flag accuracy is below 80%",
                "Review warning generation logic",
                "Improve detection of problematic parsing cases"
            ])
        
        if warning_analysis['missing_warnings']:
            warning_analysis['recommendations'].append(
                f"Missing warnings in {len(warning_analysis['missing_warnings'])} cases"
            )
        
        if warning_analysis['false_warnings']:
            warning_analysis['recommendations'].append(
                f"False warnings in {len(warning_analysis['false_warnings'])} cases"
            )
        
        return warning_analysis
    
    def _should_have_warnings(self, test_case_id: str, result: AccuracyResult) -> List[str]:
        """Determine what warnings should be present for a test case."""
        expected_warnings = []
        
        # Low accuracy should trigger warnings
        if result.accuracy_score < 0.6:
            expected_warnings.append('low_confidence')
        
        # Specific test case patterns
        if 'warn_' in test_case_id:
            expected_warnings.append('invalid_datetime')
        elif 'conf_low_' in test_case_id:
            expected_warnings.append('low_confidence')
        elif 'edge_' in test_case_id:
            expected_warnings.append('ambiguous_datetime')
        
        return expected_warnings
    
    def _are_warnings_appropriate(self, expected: List[str], actual: List[str]) -> bool:
        """Check if actual warnings match expected warning categories."""
        if not expected:
            return len(actual) == 0
        
        # Check if any expected warning category is represented
        for expected_category in expected:
            keywords = self.expected_warnings.get(expected_category, [])
            for warning in actual:
                warning_lower = warning.lower()
                if any(keyword in warning_lower for keyword in keywords):
                    return True
        
        return False


class ComprehensiveGoldenTestSuite(unittest.TestCase):
    """
    Comprehensive test suite that validates all parsing scenarios,
    regression testing, confidence thresholds, and performance benchmarks.
    """
    
    @classmethod
    def setUpClass(cls):
        """Set up test suite with comprehensive test cases."""
        cls.golden_suite_manager = GoldenTestSuiteManager()
        cls.regression_validator = RegressionTestValidator()
        cls.confidence_validator = ConfidenceThresholdValidator()
        cls.performance_monitor = cls.golden_suite_manager.performance_monitor
        
        # Initialize parsers
        cls.event_parser = EventParser()
        cls.hybrid_parser = HybridEventParser()
        
        # Test statistics
        cls.test_stats = cls.golden_suite_manager.get_test_statistics()
        
        logger.info(f"Initialized comprehensive test suite with {cls.test_stats['total_cases']} test cases")
    
    def test_comprehensive_parsing_accuracy(self):
        """Test parsing accuracy across all golden test cases."""
        print(f"\n{'='*80}")
        print("COMPREHENSIVE PARSING ACCURACY TEST")
        print(f"{'='*80}")
        
        # Test with event parser
        def parser_func(text: str) -> ParsedEvent:
            return self.event_parser.parse_text(text)
        
        evaluation_results = self.performance_monitor.evaluate_accuracy(parser_func)
        
        # Validate results
        self.assertIn('overall_accuracy', evaluation_results)
        self.assertIn('field_accuracies', evaluation_results)
        self.assertIn('results', evaluation_results)
        
        overall_accuracy = evaluation_results['overall_accuracy']
        
        print(f"Overall Accuracy: {overall_accuracy:.3f}")
        print(f"Total Test Cases: {evaluation_results['total_test_cases']}")
        
        # Print field accuracies
        if 'field_accuracies' in evaluation_results:
            print("\nField Accuracies:")
            for field, stats in evaluation_results['field_accuracies'].items():
                print(f"  {field}: {stats['mean']:.3f} (min: {stats['min']:.3f}, max: {stats['max']:.3f})")
        
        # Accuracy should meet minimum thresholds
        self.assertGreaterEqual(overall_accuracy, 0.75, 
                               f"Overall accuracy {overall_accuracy:.3f} below minimum threshold of 0.75")
        
        # Store results for regression testing
        self.evaluation_results = evaluation_results
    
    def test_category_specific_accuracy(self):
        """Test accuracy for specific parsing categories."""
        print(f"\n{'='*60}")
        print("CATEGORY-SPECIFIC ACCURACY TEST")
        print(f"{'='*60}")
        
        category_results = {}
        
        for category, test_cases in self.golden_suite_manager.test_categories.items():
            if not test_cases:
                continue
            
            print(f"\nTesting {category} ({len(test_cases)} cases):")
            
            category_accuracies = []
            for test_case in test_cases:
                try:
                    predicted_event = self.event_parser.parse_text(test_case.input_text)
                    accuracy_result = self.performance_monitor._calculate_accuracy(test_case, predicted_event)
                    category_accuracies.append(accuracy_result.accuracy_score)
                except Exception as e:
                    logger.error(f"Error testing {test_case.id}: {e}")
                    category_accuracies.append(0.0)
            
            if category_accuracies:
                avg_accuracy = statistics.mean(category_accuracies)
                min_accuracy = min(category_accuracies)
                max_accuracy = max(category_accuracies)
                
                category_results[category] = {
                    'average': avg_accuracy,
                    'min': min_accuracy,
                    'max': max_accuracy,
                    'count': len(category_accuracies)
                }
                
                print(f"  Average: {avg_accuracy:.3f}")
                print(f"  Range: {min_accuracy:.3f} - {max_accuracy:.3f}")
                
                # Category-specific thresholds
                if category in ['basic_datetime', 'title_generation']:
                    self.assertGreaterEqual(avg_accuracy, 0.85, 
                                          f"{category} accuracy {avg_accuracy:.3f} below threshold")
                elif category in ['complex_formatting', 'location_extraction']:
                    self.assertGreaterEqual(avg_accuracy, 0.70, 
                                          f"{category} accuracy {avg_accuracy:.3f} below threshold")
        
        self.category_results = category_results
    
    def test_confidence_threshold_validation(self):
        """Test confidence threshold validation and calibration."""
        print(f"\n{'='*60}")
        print("CONFIDENCE THRESHOLD VALIDATION")
        print(f"{'='*60}")
        
        # Get test results for confidence validation
        test_results = []
        confidence_test_cases = self.golden_suite_manager.get_test_cases_by_category('confidence_thresholds')
        
        for test_case in confidence_test_cases:
            try:
                predicted_event = self.event_parser.parse_text(test_case.input_text)
                accuracy_result = self.performance_monitor._calculate_accuracy(test_case, predicted_event)
                test_results.append(accuracy_result)
            except Exception as e:
                logger.error(f"Error in confidence test {test_case.id}: {e}")
        
        # Validate confidence calibration
        calibration_results = self.confidence_validator.validate_confidence_calibration(test_results)
        
        print(f"Calibration Error: {calibration_results.get('calibration_error', 0.0):.3f}")
        print(f"Well Calibrated: {calibration_results.get('is_well_calibrated', False)}")
        
        if 'confidence_bins' in calibration_results:
            print("\nConfidence Bins:")
            for bin_center, bin_data in calibration_results['confidence_bins'].items():
                print(f"  {bin_center}: predicted={bin_data['predicted_confidence']:.3f}, "
                      f"actual={bin_data['actual_accuracy']:.3f}, count={bin_data['count']}")
        
        # Calibration should be reasonable (ECE < 0.15)
        calibration_error = calibration_results.get('calibration_error', 1.0)
        self.assertLess(calibration_error, 0.15, 
                       f"Calibration error {calibration_error:.3f} too high")
        
        self.calibration_results = calibration_results
    
    def test_warning_flag_validation(self):
        """Test warning flag generation and accuracy."""
        print(f"\n{'='*60}")
        print("WARNING FLAG VALIDATION")
        print(f"{'='*60}")
        
        # Get test results for warning validation
        test_results = []
        warning_test_cases = self.golden_suite_manager.get_test_cases_by_category('warning_flags')
        
        for test_case in warning_test_cases:
            try:
                predicted_event = self.event_parser.parse_text(test_case.input_text)
                accuracy_result = self.performance_monitor._calculate_accuracy(test_case, predicted_event)
                test_results.append(accuracy_result)
            except Exception as e:
                logger.error(f"Error in warning test {test_case.id}: {e}")
        
        # Validate warning flags
        warning_results = self.confidence_validator.validate_warning_flags(test_results)
        
        print(f"Warning Accuracy: {warning_results.get('warning_accuracy', 0.0):.3f}")
        print(f"Missing Warnings: {len(warning_results.get('missing_warnings', []))}")
        print(f"False Warnings: {len(warning_results.get('false_warnings', []))}")
        
        # Warning accuracy should be reasonable
        warning_accuracy = warning_results.get('warning_accuracy', 0.0)
        self.assertGreaterEqual(warning_accuracy, 0.7, 
                               f"Warning accuracy {warning_accuracy:.3f} too low")
        
        self.warning_results = warning_results
    
    def test_performance_benchmarking(self):
        """Test performance benchmarking and latency profiling."""
        print(f"\n{'='*60}")
        print("PERFORMANCE BENCHMARKING")
        print(f"{'='*60}")
        
        # Performance test cases
        performance_cases = [
            "Simple meeting tomorrow at 2pm",
            "Complex multi-line event with location and duration from 9am to 5pm at Conference Center",
            "Very long text with multiple potential events and lots of extra information that should be filtered out during parsing"
        ]
        
        performance_results = {
            'simple_text': [],
            'complex_text': [],
            'long_text': []
        }
        
        # Test each case multiple times for statistical significance
        for i, text in enumerate(performance_cases):
            case_type = ['simple_text', 'complex_text', 'long_text'][i]
            
            for _ in range(10):  # 10 iterations per case
                start_time = time.time()
                try:
                    result = self.event_parser.parse_text(text)
                    end_time = time.time()
                    
                    duration_ms = (end_time - start_time) * 1000
                    performance_results[case_type].append(duration_ms)
                    
                    # Track in performance monitor
                    self.performance_monitor.track_component_latency('overall_parsing', duration_ms)
                    
                except Exception as e:
                    logger.error(f"Performance test error: {e}")
        
        # Analyze performance results
        for case_type, durations in performance_results.items():
            if durations:
                avg_duration = statistics.mean(durations)
                median_duration = statistics.median(durations)
                max_duration = max(durations)
                
                print(f"{case_type}:")
                print(f"  Average: {avg_duration:.2f}ms")
                print(f"  Median: {median_duration:.2f}ms")
                print(f"  Maximum: {max_duration:.2f}ms")
                
                # Performance thresholds
                if case_type == 'simple_text':
                    self.assertLess(avg_duration, 100, f"Simple text parsing too slow: {avg_duration:.2f}ms")
                elif case_type == 'complex_text':
                    self.assertLess(avg_duration, 500, f"Complex text parsing too slow: {avg_duration:.2f}ms")
                elif case_type == 'long_text':
                    self.assertLess(avg_duration, 2000, f"Long text parsing too slow: {avg_duration:.2f}ms")
        
        self.performance_results = performance_results
    
    def test_regression_validation(self):
        """Test for regressions against baseline performance."""
        print(f"\n{'='*60}")
        print("REGRESSION VALIDATION")
        print(f"{'='*60}")
        
        # Use evaluation results from comprehensive accuracy test
        if hasattr(self, 'evaluation_results'):
            regression_analysis = self.regression_validator.validate_regression(self.evaluation_results)
            
            print(f"Has Regression: {regression_analysis['has_regression']}")
            print(f"Improvements: {len(regression_analysis['improvements'])}")
            print(f"Regressions: {len(regression_analysis['regressions'])}")
            
            if regression_analysis['improvements']:
                print("\nImprovements:")
                for improvement in regression_analysis['improvements']:
                    print(f"  ✅ {improvement}")
            
            if regression_analysis['regressions']:
                print("\nRegressions:")
                for regression in regression_analysis['regressions']:
                    print(f"  ❌ {regression}")
            
            # Should not have significant regressions
            self.assertFalse(regression_analysis['has_regression'], 
                           f"Regressions detected: {regression_analysis['regressions']}")
            
            self.regression_analysis = regression_analysis
        else:
            self.skipTest("No evaluation results available for regression testing")
    
    def test_hybrid_parser_comparison(self):
        """Test hybrid parser performance compared to standard parser."""
        print(f"\n{'='*60}")
        print("HYBRID PARSER COMPARISON")
        print(f"{'='*60}")
        
        # Test subset of cases with both parsers
        test_cases = self.golden_suite_manager.get_test_cases_by_category('basic_datetime')[:5]
        
        standard_results = []
        hybrid_results = []
        
        for test_case in test_cases:
            # Standard parser
            try:
                start_time = time.time()
                standard_event = self.event_parser.parse_text(test_case.input_text)
                standard_time = (time.time() - start_time) * 1000
                
                standard_accuracy = self.performance_monitor._calculate_accuracy(test_case, standard_event)
                standard_results.append({
                    'accuracy': standard_accuracy.accuracy_score,
                    'time_ms': standard_time,
                    'confidence': standard_event.confidence_score if standard_event else 0.0
                })
            except Exception as e:
                logger.error(f"Standard parser error: {e}")
                standard_results.append({'accuracy': 0.0, 'time_ms': 0.0, 'confidence': 0.0})
            
            # Hybrid parser
            try:
                start_time = time.time()
                hybrid_event = self.hybrid_parser.parse_event_text(test_case.input_text)
                hybrid_time = (time.time() - start_time) * 1000
                
                # Convert hybrid result to ParsedEvent for comparison
                if hybrid_event and hybrid_event.parsed_event:
                    parsed_event = ParsedEvent(
                        title=hybrid_event.parsed_event.title,
                        start_datetime=hybrid_event.parsed_event.start_datetime,
                        end_datetime=hybrid_event.parsed_event.end_datetime,
                        location=hybrid_event.parsed_event.location,
                        confidence_score=hybrid_event.confidence_score
                    )
                    hybrid_accuracy = self.performance_monitor._calculate_accuracy(test_case, parsed_event)
                    hybrid_results.append({
                        'accuracy': hybrid_accuracy.accuracy_score,
                        'time_ms': hybrid_time,
                        'confidence': hybrid_event.confidence_score
                    })
                else:
                    hybrid_results.append({'accuracy': 0.0, 'time_ms': hybrid_time, 'confidence': 0.0})
            except Exception as e:
                logger.error(f"Hybrid parser error: {e}")
                hybrid_results.append({'accuracy': 0.0, 'time_ms': 0.0, 'confidence': 0.0})
        
        # Compare results
        if standard_results and hybrid_results:
            standard_avg_accuracy = statistics.mean([r['accuracy'] for r in standard_results])
            hybrid_avg_accuracy = statistics.mean([r['accuracy'] for r in hybrid_results])
            
            standard_avg_time = statistics.mean([r['time_ms'] for r in standard_results])
            hybrid_avg_time = statistics.mean([r['time_ms'] for r in hybrid_results])
            
            print(f"Standard Parser - Accuracy: {standard_avg_accuracy:.3f}, Time: {standard_avg_time:.2f}ms")
            print(f"Hybrid Parser - Accuracy: {hybrid_avg_accuracy:.3f}, Time: {hybrid_avg_time:.2f}ms")
            
            # Both parsers should perform reasonably well
            self.assertGreaterEqual(standard_avg_accuracy, 0.7, "Standard parser accuracy too low")
            self.assertGreaterEqual(hybrid_avg_accuracy, 0.7, "Hybrid parser accuracy too low")
    
    def tearDown(self):
        """Clean up after each test."""
        pass
    
    @classmethod
    def tearDownClass(cls):
        """Generate comprehensive test report."""
        print(f"\n{'='*80}")
        print("COMPREHENSIVE GOLDEN TEST SUITE REPORT")
        print(f"{'='*80}")
        
        # Generate performance report
        try:
            report = cls.performance_monitor.generate_performance_report("comprehensive_test_report.json")
            print(f"Performance report saved to: comprehensive_test_report.json")
            
            # Print summary
            if 'system_metrics' in report:
                metrics = report['system_metrics']
                print(f"\nSystem Metrics:")
                print(f"  Component Latencies: {len(metrics.get('component_latencies', {}))}")
                print(f"  Overall Accuracy: {metrics.get('overall_accuracy', 0.0):.3f}")
                print(f"  Calibration Error: {metrics.get('calibration_error', 0.0):.3f}")
            
            if 'recommendations' in report and report['recommendations']:
                print(f"\nRecommendations:")
                for rec in report['recommendations']:
                    print(f"  • {rec}")
        
        except Exception as e:
            logger.error(f"Error generating performance report: {e}")
        
        print(f"\n{'='*80}")
        print("COMPREHENSIVE TEST SUITE COMPLETED")
        print(f"{'='*80}")


if __name__ == '__main__':
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run comprehensive test suite
    unittest.main(verbosity=2)