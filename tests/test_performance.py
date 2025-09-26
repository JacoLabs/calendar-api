"""
Performance tests for the text-to-calendar event system.
Tests parsing performance with large text blocks and stress scenarios.
"""

import unittest
import time
import tempfile
import os
from datetime import datetime, timedelta
from unittest.mock import patch

from main import TextToCalendarApp
from services.event_parser import EventParser
from services.calendar_service import CalendarService
from models.event_models import Event


class TestParsingPerformance(unittest.TestCase):
    """Test parsing performance with various text sizes and complexities."""
    
    def setUp(self):
        """Set up test environment."""
        self.parser = EventParser()
        self.max_acceptable_time = 5.0  # 5 seconds max for any single parse
    
    def test_large_text_block_performance(self):
        """Test parsing performance with large text blocks."""
        # Create a large text block with multiple potential events
        large_text = """
        Here's my complete schedule for the next month. On Monday March 4th I have a team meeting 
        at 9am in Conference Room A. The meeting should last about 2 hours and we'll be discussing 
        the quarterly results. Then at 1pm I'm having lunch with the client at The Keg Restaurant 
        downtown. This is an important business lunch to discuss the new contract terms.
        
        Tuesday March 5th is pretty busy - I have a conference call at 8am with the overseas team 
        in London. We'll be reviewing the project timeline and deliverables. Then at 10:30am I have 
        a project review meeting in the boardroom with all stakeholders. This meeting is scheduled 
        for 90 minutes. After that, at 2pm I have a one-on-one with my manager in her office.
        
        Wednesday March 6th I have a doctor's appointment at 2:15pm at Toronto General Hospital. 
        I need to leave the office by 1:30pm to get there on time. The appointment should take 
        about 45 minutes. Before that, I have a training session from 9am to 12pm in Training Room B.
        
        Thursday March 7th is the big presentation day. The quarterly review presentation is at 3pm 
        in the main auditorium. It's called "Q4 Results and Future Planning" and all department heads 
        will be attending. I need to prepare my slides and practice the presentation beforehand.
        
        Friday March 8th I have a team building event from 1pm to 5pm at the community center on 
        Elm Street. This is a mandatory event for all team members. We'll be doing various activities 
        and team exercises. After that, there's an optional happy hour at Murphy's Pub starting at 6pm.
        
        The following week starts with a Monday morning standup at 9am sharp. Then I have back-to-back 
        meetings: client call at 10am, vendor meeting at 11:30am, and lunch meeting at 12:30pm with 
        the new hire. Tuesday has a workshop from 9am to 5pm called "Advanced Project Management 
        Techniques" in the downtown conference center.
        
        Looking ahead to the third week, I have several important deadlines. The project proposal 
        is due on Wednesday at 5pm. I need to submit it to the client portal before the deadline. 
        Thursday has a board meeting at 2pm in the executive boardroom. All senior managers must attend.
        
        The month ends with a company-wide meeting on Friday at 4pm in the main conference hall. 
        This is followed by the monthly social event at 6pm in the office cafeteria. Everyone is 
        invited to attend and there will be food and drinks provided.
        """ *