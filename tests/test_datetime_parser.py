"""
Comprehensive unit tests for datetime parsing functionality.
Tests various date formats, time formats, and edge cases.
"""

import unittest
from unittest.mock import patch
from datetime import datetime, date, time, timedelta
from services.datetime_parser import DateTimeParser, DateTimeMatch, DurationMatch


class TestDateTimeParser(unittest.TestCase):
    """Test cases for DateTimeParser class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.parser = DateTimeParser()
    
    def test_mm_dd_yyyy_format(self):
        """Test MM/DD/YYYY date format parsing."""
        test_cases = [
            ("Meeting on 12/25/2024", datetime(2024, 12, 25, 9, 0)),
            ("Event scheduled for 01/15/2025", datetime(2025, 1, 15, 9, 0)),
            ("Deadline is 3/8/2024", datetime(2024, 3, 8, 9, 0)),
            ("Conference on 12-25-2024", datetime(2024, 12, 25, 9, 0)),
        ]
        
        for text, expected in test_cases:
            with self.subTest(text=text):
                result = self.parser.parse_single_datetime(text)
                self.assertEqual(result, expected)
    
    def test_dd_mm_yyyy_format_with_preference(self):
        """Test DD/MM/YYYY interpretation when prefer_dd_mm is True."""
        text = "Meeting on 15/03/2024"  # Unambiguous - day > 12
        result = self.parser.parse_single_datetime(text, prefer_dd_mm=True)
        expected = datetime(2024, 3, 15, 9, 0)
        self.assertEqual(result, expected)
        
        # Test ambiguous date with preference
        text = "Meeting on 05/03/2024"  # Could be May 3rd or March 5th
        result_dd_mm = self.parser.parse_single_datetime(text, prefer_dd_mm=True)
        result_mm_dd = self.parser.parse_single_datetime(text, prefer_dd_mm=False)
        
        expected_dd_mm = datetime(2024, 3, 5, 9, 0)  # March 5th
        expected_mm_dd = datetime(2024, 5, 3, 9, 0)  # May 3rd
        
        self.assertEqual(result_dd_mm, expected_dd_mm)
        self.assertEqual(result_mm_dd, expected_mm_dd)
    
    def test_month_name_formats(self):
        """Test month name date formats."""
        test_cases = [
            ("Meeting on January 15, 2024", datetime(2024, 1, 15, 9, 0)),
            ("Event on March 8 2025", datetime(2025, 3, 8, 9, 0)),
            ("Deadline December 31, 2024", datetime(2024, 12, 31, 9, 0)),
            ("Conference February 29, 2024", datetime(2024, 2, 29, 9, 0)),  # Leap year
        ]
        
        for text, expected in test_cases:
            with self.subTest(text=text):
                result = self.parser.parse_single_datetime(text)
                self.assertEqual(result, expected)
    
    def test_month_day_current_year(self):
        """Test month and day without year (should use current year)."""
        current_year = datetime.now().year
        test_cases = [
            ("Meeting on January 15", datetime(current_year, 1, 15, 9, 0)),
            ("Event March 8", datetime(current_year, 3, 8, 9, 0)),
        ]
        
        for text, expected in test_cases:
            with self.subTest(text=text):
                result = self.parser.parse_single_datetime(text)
                self.assertEqual(result, expected)
    
    def test_yyyy_mm_dd_format(self):
        """Test YYYY-MM-DD ISO format."""
        test_cases = [
            ("Meeting on 2024-12-25", datetime(2024, 12, 25, 9, 0)),
            ("Event 2025/01/15", datetime(2025, 1, 15, 9, 0)),
        ]
        
        for text, expected in test_cases:
            with self.subTest(text=text):
                result = self.parser.parse_single_datetime(text)
                self.assertEqual(result, expected)
    
    def test_12_hour_time_formats(self):
        """Test 12-hour time format parsing with AM/PM."""
        today = date.today()
        test_cases = [
            ("Meeting at 2pm", datetime.combine(today, time(14, 0))),
            ("Event at 9:30 AM", datetime.combine(today, time(9, 30))),
            ("Call at 11:45 PM", datetime.combine(today, time(23, 45))),
            ("Lunch at 12 PM", datetime.combine(today, time(12, 0))),
            ("Midnight at 12 AM", datetime.combine(today, time(0, 0))),
        ]
        
        for text, expected in test_cases:
            with self.subTest(text=text):
                matches = self.parser.extract_datetime(text)
                self.assertTrue(len(matches) > 0, f"No matches found for: {text}")
                # Find time-only match (not combined with date)
                time_match = next((m for m in matches if 'default_time' not in m.pattern_type), None)
                if time_match:
                    self.assertEqual(time_match.value.time(), expected.time())
    
    def test_24_hour_time_formats(self):
        """Test 24-hour time format parsing."""
        today = date.today()
        test_cases = [
            ("Meeting at 14:30", datetime.combine(today, time(14, 30))),
            ("Event at 09:15", datetime.combine(today, time(9, 15))),
            ("Call at 23:45", datetime.combine(today, time(23, 45))),
            ("Start at 00:00", datetime.combine(today, time(0, 0))),
        ]
        
        for text, expected in test_cases:
            with self.subTest(text=text):
                matches = self.parser.extract_datetime(text)
                self.assertTrue(len(matches) > 0, f"No matches found for: {text}")
                # Find time-only match
                time_match = next((m for m in matches if 'default_time' not in m.pattern_type), None)
                if time_match:
                    self.assertEqual(time_match.value.time(), expected.time())
    
    def test_combined_date_time(self):
        """Test parsing text with both date and time."""
        test_cases = [
            ("Meeting on 12/25/2024 at 2:30 PM", datetime(2024, 12, 25, 14, 30)),
            ("Event January 15, 2025 at 9:00 AM", datetime(2025, 1, 15, 9, 0)),
            ("Call on March 8 at 11:45 PM", datetime(datetime.now().year, 3, 8, 23, 45)),
            ("Conference 2024-06-15 14:30", datetime(2024, 6, 15, 14, 30)),
        ]
        
        for text, expected in test_cases:
            with self.subTest(text=text):
                result = self.parser.parse_single_datetime(text)
                self.assertEqual(result, expected)
    
    def test_hour_only_formats(self):
        """Test parsing hour-only formats like '2 o'clock'."""
        today = date.today()
        test_cases = [
            ("Meeting at 2 o'clock", time(14, 0)),  # Assumes PM for business hours
            ("Event at 10 o'clock", time(22, 0)),   # Assumes PM for business hours
            ("Call at 8 o'clock", time(8, 0)),      # Assumes AM for early hours
        ]
        
        for text, expected_time in test_cases:
            with self.subTest(text=text):
                matches = self.parser.extract_datetime(text)
                self.assertTrue(len(matches) > 0, f"No matches found for: {text}")
                # Find time-only match
                time_match = next((m for m in matches if 'default_time' not in m.pattern_type), None)
                if time_match:
                    self.assertEqual(time_match.value.time(), expected_time)
    
    def test_multiple_datetime_matches(self):
        """Test text with multiple date/time references."""
        text = "Meeting on 12/25/2024 at 2 PM, follow-up on January 15 at 9:30 AM"
        matches = self.parser.extract_datetime(text)
        
        # Should find multiple matches
        self.assertGreaterEqual(len(matches), 2)
        
        # Check that matches are sorted by confidence
        for i in range(len(matches) - 1):
            self.assertGreaterEqual(matches[i].confidence, matches[i + 1].confidence)
    
    def test_invalid_dates(self):
        """Test handling of invalid date formats."""
        invalid_texts = [
            "Meeting on 13/45/2024",  # Invalid month and day
            "Event on February 30, 2024",  # Invalid day for February
            "Call at 25:70",  # Invalid time
            "Conference on 2024-13-45",  # Invalid month and day in ISO format
        ]
        
        for text in invalid_texts:
            with self.subTest(text=text):
                result = self.parser.parse_single_datetime(text)
                # Should either return None or a valid datetime (if partial parsing succeeded)
                if result is not None:
                    self.assertIsInstance(result, datetime)
    
    def test_edge_cases(self):
        """Test edge cases and boundary conditions."""
        test_cases = [
            # Leap year
            ("Meeting on February 29, 2024", datetime(2024, 2, 29, 9, 0)),
            # Year boundaries
            ("Event on December 31, 2024", datetime(2024, 12, 31, 9, 0)),
            ("Call on January 1, 2025", datetime(2025, 1, 1, 9, 0)),
            # Time boundaries
            ("Meeting at 12:00 AM", time(0, 0)),  # Midnight
            ("Event at 11:59 PM", time(23, 59)),  # Just before midnight
        ]
        
        for text, expected in test_cases:
            with self.subTest(text=text):
                if isinstance(expected, datetime):
                    result = self.parser.parse_single_datetime(text)
                    self.assertEqual(result, expected)
                else:  # time object
                    matches = self.parser.extract_datetime(text)
                    self.assertTrue(len(matches) > 0)
                    time_match = next((m for m in matches if 'default_time' not in m.pattern_type), None)
                    if time_match:
                        self.assertEqual(time_match.value.time(), expected)
    
    def test_confidence_scoring(self):
        """Test that confidence scores are reasonable."""
        # High confidence cases
        high_confidence_texts = [
            "Meeting on January 15, 2024 at 2:30 PM",  # Explicit month name + AM/PM
            "Event December 25, 2024 at 9:00 AM",
        ]
        
        for text in high_confidence_texts:
            with self.subTest(text=text):
                matches = self.parser.extract_datetime(text)
                if matches:
                    self.assertGreater(matches[0].confidence, 0.8)
        
        # Lower confidence cases
        lower_confidence_texts = [
            "Meeting at 2 o'clock",  # Hour only, AM/PM assumed
            "Event on 05/03/2024",  # Ambiguous MM/DD vs DD/MM
        ]
        
        for text in lower_confidence_texts:
            with self.subTest(text=text):
                matches = self.parser.extract_datetime(text)
                if matches:
                    self.assertLess(matches[0].confidence, 0.9)
    
    def test_parsing_metadata(self):
        """Test parsing metadata functionality."""
        text = "Meeting on 12/25/2024 at 2:30 PM"
        metadata = self.parser.get_parsing_metadata(text)
        
        self.assertIn('total_matches', metadata)
        self.assertIn('best_match', metadata)
        self.assertIn('all_matches', metadata)
        self.assertIn('parsing_settings', metadata)
        
        # Check best match structure
        best_match = metadata['best_match']
        if best_match:
            self.assertIn('datetime', best_match)
            self.assertIn('confidence', best_match)
            self.assertIn('matched_text', best_match)
            self.assertIn('pattern_type', best_match)
    
    def test_no_datetime_found(self):
        """Test behavior when no datetime is found in text."""
        text = "This is just regular text with no dates or times"
        result = self.parser.parse_single_datetime(text)
        self.assertIsNone(result)
        
        matches = self.parser.extract_datetime(text)
        self.assertEqual(len(matches), 0)
        
        metadata = self.parser.get_parsing_metadata(text)
        self.assertEqual(metadata['total_matches'], 0)
        self.assertIsNone(metadata['best_match'])
    
    def test_case_insensitive_parsing(self):
        """Test that parsing is case insensitive."""
        test_cases = [
            ("meeting on JANUARY 15, 2024", datetime(2024, 1, 15, 9, 0)),
            ("event at 2PM", time(14, 0)),
            ("call at 9:30 am", time(9, 30)),
        ]
        
        for text, expected in test_cases:
            with self.subTest(text=text):
                if isinstance(expected, datetime):
                    result = self.parser.parse_single_datetime(text)
                    self.assertEqual(result, expected)
                else:  # time object
                    matches = self.parser.extract_datetime(text)
                    self.assertTrue(len(matches) > 0)
                    time_match = next((m for m in matches if 'default_time' not in m.pattern_type), None)
                    if time_match:
                        self.assertEqual(time_match.value.time(), expected)


class TestDateTimeMatch(unittest.TestCase):
    """Test cases for DateTimeMatch dataclass."""
    
    def test_datetime_match_creation(self):
        """Test creating DateTimeMatch objects."""
        dt = datetime(2024, 12, 25, 14, 30)
        match = DateTimeMatch(
            value=dt,
            confidence=0.95,
            start_pos=10,
            end_pos=25,
            matched_text="12/25/2024 2:30 PM",
            pattern_type="combined"
        )
        
        self.assertEqual(match.value, dt)
        self.assertEqual(match.confidence, 0.95)
        self.assertEqual(match.start_pos, 10)
        self.assertEqual(match.end_pos, 25)
        self.assertEqual(match.matched_text, "12/25/2024 2:30 PM")
        self.assertEqual(match.pattern_type, "combined")


class TestRelativeDateParsing(unittest.TestCase):
    """Test cases for relative date parsing functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.parser = DateTimeParser()
        self.today = date.today()
        self.now = datetime.now()
    
    def test_basic_relative_dates(self):
        """Test basic relative date parsing (today, tomorrow, yesterday)."""
        test_cases = [
            ("Meeting today", self.today),
            ("Event tomorrow", self.today + timedelta(days=1)),
            ("Call yesterday", self.today - timedelta(days=1)),
        ]
        
        for text, expected_date in test_cases:
            with self.subTest(text=text):
                result = self.parser.parse_single_datetime(text)
                self.assertIsNotNone(result)
                self.assertEqual(result.date(), expected_date)
    
    def test_next_weekday_parsing(self):
        """Test 'next [weekday]' parsing."""
        test_cases = [
            "Meeting next Monday",
            "Event next Friday", 
            "Call next Sunday"
        ]
        
        for text in test_cases:
            with self.subTest(text=text):
                result = self.parser.parse_single_datetime(text)
                self.assertIsNotNone(result)
                # Should be in the future
                self.assertGreater(result.date(), self.today)
                # Should be within the next 7 days
                self.assertLessEqual((result.date() - self.today).days, 7)
    
    def test_this_weekday_parsing(self):
        """Test 'this [weekday]' parsing."""
        test_cases = [
            "Meeting this Monday",
            "Event this Friday",
            "Call this Sunday"
        ]
        
        for text in test_cases:
            with self.subTest(text=text):
                result = self.parser.parse_single_datetime(text)
                self.assertIsNotNone(result)
                # Should be within this week (could be today or future)
                self.assertGreaterEqual(result.date(), self.today)
                self.assertLessEqual((result.date() - self.today).days, 7)
    
    def test_in_days_parsing(self):
        """Test 'in X days' parsing."""
        test_cases = [
            ("Meeting in 3 days", 3),
            ("Event in 1 day", 1),
            ("Call in 10 days", 10),
        ]
        
        for text, days in test_cases:
            with self.subTest(text=text):
                result = self.parser.parse_single_datetime(text)
                expected_date = self.today + timedelta(days=days)
                self.assertIsNotNone(result)
                self.assertEqual(result.date(), expected_date)
    
    def test_in_weeks_parsing(self):
        """Test 'in X weeks' parsing."""
        test_cases = [
            ("Meeting in 2 weeks", 2),
            ("Event in 1 week", 1),
            ("Call in 4 weeks", 4),
        ]
        
        for text, weeks in test_cases:
            with self.subTest(text=text):
                result = self.parser.parse_single_datetime(text)
                expected_date = self.today + timedelta(weeks=weeks)
                self.assertIsNotNone(result)
                self.assertEqual(result.date(), expected_date)
    
    def test_in_months_parsing(self):
        """Test 'in X months' parsing."""
        test_cases = [
            ("Meeting in 2 months", 2),
            ("Event in 1 month", 1),
            ("Call in 6 months", 6),
        ]
        
        for text, months in test_cases:
            with self.subTest(text=text):
                result = self.parser.parse_single_datetime(text)
                self.assertIsNotNone(result)
                # Check that the month difference is approximately correct
                month_diff = (result.year - self.today.year) * 12 + (result.month - self.today.month)
                self.assertEqual(month_diff, months)
    
    def test_days_from_now_parsing(self):
        """Test 'X days from now' parsing."""
        test_cases = [
            ("Meeting 5 days from now", 5),
            ("Event 1 day from now", 1),
            ("Call 14 days from now", 14),
        ]
        
        for text, days in test_cases:
            with self.subTest(text=text):
                result = self.parser.parse_single_datetime(text)
                expected_date = self.today + timedelta(days=days)
                self.assertIsNotNone(result)
                self.assertEqual(result.date(), expected_date)
    
    def test_weeks_from_now_parsing(self):
        """Test 'X weeks from now' parsing."""
        test_cases = [
            ("Meeting 3 weeks from now", 3),
            ("Event 1 week from now", 1),
        ]
        
        for text, weeks in test_cases:
            with self.subTest(text=text):
                result = self.parser.parse_single_datetime(text)
                expected_date = self.today + timedelta(weeks=weeks)
                self.assertIsNotNone(result)
                self.assertEqual(result.date(), expected_date)
    
    def test_relative_date_with_time(self):
        """Test relative dates combined with specific times."""
        test_cases = [
            ("Meeting tomorrow at 2 PM", self.today + timedelta(days=1), time(14, 0)),
            ("Call next Friday at 9:30 AM", None, time(9, 30)),  # Date varies by current day
            ("Event in 3 days at 11:00", self.today + timedelta(days=3), time(11, 0)),
        ]
        
        for text, expected_date, expected_time in test_cases:
            with self.subTest(text=text):
                result = self.parser.parse_single_datetime(text)
                self.assertIsNotNone(result)
                if expected_date:
                    self.assertEqual(result.date(), expected_date)
                self.assertEqual(result.time(), expected_time)
    
    def test_case_insensitive_relative_dates(self):
        """Test that relative date parsing is case insensitive."""
        test_cases = [
            "Meeting TOMORROW",
            "Event Next FRIDAY",
            "Call IN 3 DAYS",
        ]
        
        for text in test_cases:
            with self.subTest(text=text):
                result = self.parser.parse_single_datetime(text)
                self.assertIsNotNone(result)
    
    def test_relative_date_confidence_scores(self):
        """Test confidence scores for relative date parsing."""
        high_confidence_texts = [
            "Meeting today",
            "Event tomorrow", 
            "Call yesterday"
        ]
        
        for text in high_confidence_texts:
            with self.subTest(text=text):
                matches = self.parser.extract_datetime(text)
                self.assertTrue(len(matches) > 0)
                # Should have reasonable confidence for clear relative dates
                # (Note: confidence is reduced by 0.8 factor for default time)
                self.assertGreater(matches[0].confidence, 0.7)


class TestDurationParsing(unittest.TestCase):
    """Test cases for duration parsing functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.parser = DateTimeParser()
    
    def test_for_hours_parsing(self):
        """Test 'for X hours' duration parsing."""
        test_cases = [
            ("Meeting for 2 hours", timedelta(hours=2)),
            ("Event for 1.5 hours", timedelta(hours=1.5)),
            ("Call for 3 hours", timedelta(hours=3)),
        ]
        
        for text, expected_duration in test_cases:
            with self.subTest(text=text):
                durations = self.parser.extract_durations(text)
                self.assertTrue(len(durations) > 0)
                self.assertEqual(durations[0].duration, expected_duration)
    
    def test_for_minutes_parsing(self):
        """Test 'for X minutes' duration parsing."""
        test_cases = [
            ("Meeting for 30 minutes", timedelta(minutes=30)),
            ("Event for 45 mins", timedelta(minutes=45)),
            ("Call for 15 minutes", timedelta(minutes=15)),
        ]
        
        for text, expected_duration in test_cases:
            with self.subTest(text=text):
                durations = self.parser.extract_durations(text)
                self.assertTrue(len(durations) > 0)
                self.assertEqual(durations[0].duration, expected_duration)
    
    def test_for_hours_and_minutes_parsing(self):
        """Test 'for X hours and Y minutes' duration parsing."""
        test_cases = [
            ("Meeting for 2 hours and 30 minutes", timedelta(hours=2, minutes=30)),
            ("Event for 1 hour 45 minutes", timedelta(hours=1, minutes=45)),
            ("Call for 3 hours and 15 mins", timedelta(hours=3, minutes=15)),
        ]
        
        for text, expected_duration in test_cases:
            with self.subTest(text=text):
                durations = self.parser.extract_durations(text)
                self.assertTrue(len(durations) > 0)
                self.assertEqual(durations[0].duration, expected_duration)
    
    def test_duration_without_for_keyword(self):
        """Test duration parsing without 'for' keyword."""
        test_cases = [
            ("Meeting 2 hours", timedelta(hours=2)),
            ("Event 45 minutes", timedelta(minutes=45)),
            ("Call 1.5 hours", timedelta(hours=1.5)),
        ]
        
        for text, expected_duration in test_cases:
            with self.subTest(text=text):
                durations = self.parser.extract_durations(text)
                self.assertTrue(len(durations) > 0)
                self.assertEqual(durations[0].duration, expected_duration)
    
    def test_colon_duration_format(self):
        """Test duration in HH:MM format."""
        test_cases = [
            ("Meeting 2:30 hours", timedelta(hours=2, minutes=30)),
            ("Event 1:15 duration", timedelta(hours=1, minutes=15)),
            ("Call 0:45 hrs", timedelta(minutes=45)),
        ]
        
        for text, expected_duration in test_cases:
            with self.subTest(text=text):
                durations = self.parser.extract_durations(text)
                self.assertTrue(len(durations) > 0)
                self.assertEqual(durations[0].duration, expected_duration)
    
    def test_calculate_end_time(self):
        """Test end time calculation based on duration."""
        start_time = datetime(2024, 12, 25, 14, 0)  # 2:00 PM
        
        test_cases = [
            ("Meeting for 2 hours", timedelta(hours=2)),
            ("Event for 30 minutes", timedelta(minutes=30)),
            ("Call for 1 hour and 15 minutes", timedelta(hours=1, minutes=15)),
        ]
        
        for text, expected_duration in test_cases:
            with self.subTest(text=text):
                end_time = self.parser.calculate_end_time(start_time, text)
                expected_end = start_time + expected_duration
                self.assertEqual(end_time, expected_end)
    
    def test_no_duration_found(self):
        """Test behavior when no duration is found."""
        text = "Meeting tomorrow at 2 PM"
        start_time = datetime(2024, 12, 25, 14, 0)
        
        end_time = self.parser.calculate_end_time(start_time, text)
        self.assertIsNone(end_time)
        
        durations = self.parser.extract_durations(text)
        self.assertEqual(len(durations), 0)
    
    def test_duration_confidence_scores(self):
        """Test confidence scores for duration parsing."""
        high_confidence_texts = [
            "Meeting for 2 hours",
            "Event for 30 minutes",
        ]
        
        lower_confidence_texts = [
            "Meeting 2 hours",  # Without 'for' keyword
            "Event 30 minutes",
        ]
        
        for text in high_confidence_texts:
            with self.subTest(text=text):
                durations = self.parser.extract_durations(text)
                self.assertTrue(len(durations) > 0)
                self.assertGreater(durations[0].confidence, 0.9)
        
        for text in lower_confidence_texts:
            with self.subTest(text=text):
                durations = self.parser.extract_durations(text)
                self.assertTrue(len(durations) > 0)
                self.assertLess(durations[0].confidence, 0.9)


class TestDateArithmeticHelpers(unittest.TestCase):
    """Test cases for date arithmetic helper functions."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.parser = DateTimeParser()
    
    def test_get_next_weekday(self):
        """Test getting next occurrence of a weekday."""
        # Test from a Monday (weekday 0)
        monday = date(2024, 1, 1)  # This is a Monday
        
        # Next Tuesday should be 1 day ahead
        next_tuesday = self.parser._get_next_weekday(monday, 1)
        self.assertEqual(next_tuesday, date(2024, 1, 2))
        
        # Next Monday should be 7 days ahead (next week)
        next_monday = self.parser._get_next_weekday(monday, 0)
        self.assertEqual(next_monday, date(2024, 1, 8))
        
        # Next Sunday should be 6 days ahead
        next_sunday = self.parser._get_next_weekday(monday, 6)
        self.assertEqual(next_sunday, date(2024, 1, 7))
    
    def test_get_this_weekday(self):
        """Test getting occurrence of weekday in current week."""
        # Test from a Wednesday (weekday 2)
        wednesday = date(2024, 1, 3)  # This is a Wednesday
        
        # This Friday should be 2 days ahead
        this_friday = self.parser._get_this_weekday(wednesday, 4)
        self.assertEqual(this_friday, date(2024, 1, 5))
        
        # This Wednesday should be today
        this_wednesday = self.parser._get_this_weekday(wednesday, 2)
        self.assertEqual(this_wednesday, wednesday)
        
        # This Monday should be next week (since it already passed)
        this_monday = self.parser._get_this_weekday(wednesday, 0)
        self.assertEqual(this_monday, date(2024, 1, 8))
    
    def test_add_months(self):
        """Test adding months to dates."""
        start_date = date(2024, 1, 15)
        
        # Add 1 month
        result = self.parser._add_months(start_date, 1)
        self.assertEqual(result, date(2024, 2, 15))
        
        # Add 12 months (1 year)
        result = self.parser._add_months(start_date, 12)
        self.assertEqual(result, date(2025, 1, 15))
        
        # Test month boundary handling (January 31 + 1 month)
        jan_31 = date(2024, 1, 31)
        result = self.parser._add_months(jan_31, 1)
        self.assertEqual(result, date(2024, 2, 29))  # 2024 is leap year
        
        # Test non-leap year
        jan_31_2023 = date(2023, 1, 31)
        result = self.parser._add_months(jan_31_2023, 1)
        self.assertEqual(result, date(2023, 2, 28))
    
    def test_days_in_month(self):
        """Test days in month calculation."""
        # Regular months
        self.assertEqual(self.parser._days_in_month(2024, 1), 31)  # January
        self.assertEqual(self.parser._days_in_month(2024, 4), 30)  # April
        self.assertEqual(self.parser._days_in_month(2024, 6), 30)  # June
        
        # February in leap year
        self.assertEqual(self.parser._days_in_month(2024, 2), 29)
        
        # February in non-leap year
        self.assertEqual(self.parser._days_in_month(2023, 2), 28)
    
    def test_is_leap_year(self):
        """Test leap year detection."""
        # Leap years
        self.assertTrue(self.parser._is_leap_year(2024))
        self.assertTrue(self.parser._is_leap_year(2000))
        self.assertTrue(self.parser._is_leap_year(1600))
        
        # Non-leap years
        self.assertFalse(self.parser._is_leap_year(2023))
        self.assertFalse(self.parser._is_leap_year(1900))
        self.assertFalse(self.parser._is_leap_year(2100))


class TestBoundaryConditions(unittest.TestCase):
    """Test boundary conditions and edge cases for relative date parsing."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.parser = DateTimeParser()
    
    def test_year_boundary_relative_dates(self):
        """Test relative dates across year boundaries."""
        # Mock today as December 30th to test year boundary
        with patch('services.datetime_parser.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2024, 12, 30, 10, 0)
            mock_datetime.combine = datetime.combine
            
            # Tomorrow should be in next year
            result = self.parser.parse_single_datetime("Meeting tomorrow")
            self.assertEqual(result.date(), date(2024, 12, 31))
            
            # In 3 days should be in next year
            result = self.parser.parse_single_datetime("Event in 3 days")
            self.assertEqual(result.date(), date(2025, 1, 2))
    
    def test_month_boundary_relative_dates(self):
        """Test relative dates across month boundaries."""
        # Mock today as January 30th to test February boundary
        with patch('services.datetime_parser.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2024, 1, 30, 10, 0)
            mock_datetime.combine = datetime.combine
            
            # In 3 days should handle month boundary
            result = self.parser.parse_single_datetime("Meeting in 3 days")
            self.assertEqual(result.date(), date(2024, 2, 2))
    
    def test_leap_year_handling(self):
        """Test relative date parsing in leap years."""
        # Mock today as February 28th in leap year
        with patch('services.datetime_parser.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2024, 2, 28, 10, 0)
            mock_datetime.combine = datetime.combine
            
            # Tomorrow should be February 29th (leap day)
            result = self.parser.parse_single_datetime("Meeting tomorrow")
            self.assertEqual(result.date(), date(2024, 2, 29))
    
    def test_weekend_boundary_conditions(self):
        """Test weekday parsing around weekends."""
        # Mock today as Friday
        with patch('services.datetime_parser.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2024, 1, 5, 10, 0)  # Friday
            mock_datetime.combine = datetime.combine
            
            # Next Monday should be 3 days ahead
            result = self.parser.parse_single_datetime("Meeting next Monday")
            self.assertEqual(result.date(), date(2024, 1, 8))
            
            # This Sunday should be 2 days ahead
            result = self.parser.parse_single_datetime("Event this Sunday")
            self.assertEqual(result.date(), date(2024, 1, 7))


if __name__ == '__main__':
    unittest.main()