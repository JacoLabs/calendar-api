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
        """ * 3  # Triple the text to make it even larger
        
        start_time = time.time()
        result = self.parser.parse_text(large_text)
        end_time = time.time()
        
        parse_time = end_time - start_time
        
        # Should complete within acceptable time
        self.assertLess(parse_time, self.max_acceptable_time, 
                       f"Large text parsing took {parse_time:.2f}s, expected < {self.max_acceptable_time}s")
        
        # Should still produce a reasonable result
        self.assertIsNotNone(result)
        self.assertGreater(result.confidence_score, 0.0)
        
        print(f"Large text parsing time: {parse_time:.3f}s")
    
    def test_multiple_events_parsing_performance(self):
        """Test performance when parsing text with many potential events."""
        # Create text with many event-like patterns
        events_text = ""
        for i in range(50):  # 50 potential events
            day = (datetime.now() + timedelta(days=i)).strftime("%B %d")
            events_text += f"Meeting {i+1} on {day} at {10 + (i % 8)}:00am in Room {i % 10 + 1}. "
        
        start_time = time.time()
        results = self.parser.parse_multiple_events(events_text)
        end_time = time.time()
        
        parse_time = end_time - start_time
        
        # Should complete within acceptable time
        self.assertLess(parse_time, self.max_acceptable_time * 2,  # Allow more time for multiple events
                       f"Multiple events parsing took {parse_time:.2f}s")
        
        # Should find multiple events
        self.assertGreater(len(results), 1)
        
        print(f"Multiple events parsing time: {parse_time:.3f}s for {len(results)} events")
    
    def test_complex_datetime_patterns_performance(self):
        """Test performance with complex datetime patterns."""
        complex_text = """
        Schedule for next week: Monday 9:00 AM to 10:30 AM team standup, then 11:15-12:45 client call,
        followed by lunch from 1:00 PM until 2:15 PM. Tuesday starts at 8:30am with vendor meeting
        lasting 2 hours and 15 minutes, then project review from 11:00 to 12:30, afternoon session
        2:30-4:45 PM. Wednesday morning 9:15-10:45 training, midday 12:00-1:30 lunch meeting,
        evening 6:00-8:30 PM networking event. Thursday all-day workshop 9:00 AM - 5:00 PM with
        breaks at 10:30-10:45, 12:00-1:00, and 3:15-3:30. Friday wrap-up 9:30-11:00 AM,
        then 2:00-3:30 PM final review, ending with 4:00-5:30 PM celebration.
        """
        
        start_time = time.time()
        result = self.parser.parse_text(complex_text)
        end_time = time.time()
        
        parse_time = end_time - start_time
        
        # Should handle complex patterns efficiently
        self.assertLess(parse_time, self.max_acceptable_time,
                       f"Complex datetime parsing took {parse_time:.2f}s")
        
        print(f"Complex datetime parsing time: {parse_time:.3f}s")
    
    def test_repeated_parsing_performance(self):
        """Test performance with repeated parsing of the same text."""
        text = "Team meeting tomorrow at 2pm in Conference Room A for 1 hour"
        
        iterations = 100
        start_time = time.time()
        
        for _ in range(iterations):
            result = self.parser.parse_text(text)
        
        end_time = time.time()
        total_time = end_time - start_time
        avg_time = total_time / iterations
        
        # Average parse time should be very fast for simple text
        self.assertLess(avg_time, 0.1, f"Average parse time {avg_time:.4f}s too slow")
        
        print(f"Average parse time over {iterations} iterations: {avg_time:.4f}s")
    
    def test_memory_usage_with_large_text(self):
        """Test that memory usage doesn't grow excessively with large text."""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Parse several large texts
        large_text = "Meeting tomorrow at 2pm. " * 10000  # Very repetitive large text
        
        for _ in range(10):
            result = self.parser.parse_text(large_text)
        
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be reasonable (less than 100MB)
        self.assertLess(memory_increase, 100, 
                       f"Memory usage increased by {memory_increase:.1f}MB")
        
        print(f"Memory usage increase: {memory_increase:.1f}MB")


class TestWorkflowPerformance(unittest.TestCase):
    """Test performance of complete workflows."""
    
    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_storage = os.path.join(self.temp_dir, "test_events.json")
        self.app = TextToCalendarApp()
        self.app.calendar_service = CalendarService(storage_path=self.temp_storage)
        self.app.set_config(auto_preview=False, verbose_output=False)
    
    def tearDown(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_end_to_end_workflow_performance(self):
        """Test performance of complete end-to-end workflow."""
        text = "Project review meeting tomorrow at 2pm in Conference Room B for 90 minutes"
        
        start_time = time.time()
        success, event, message = self.app.run_complete_workflow(text)
        end_time = time.time()
        
        workflow_time = end_time - start_time
        
        # Complete workflow should be fast
        self.assertLess(workflow_time, 3.0, f"Workflow took {workflow_time:.2f}s")
        
        if success:
            self.assertIsNotNone(event)
        
        print(f"End-to-end workflow time: {workflow_time:.3f}s")
    
    def test_batch_processing_performance(self):
        """Test performance of batch processing multiple events."""
        texts = [
            "Meeting tomorrow at 9am",
            "Lunch next Friday at 12:30pm",
            "Conference call Monday 3pm for 1 hour",
            "Training session Tuesday 10am-12pm",
            "Client meeting Wednesday 2pm at their office",
        ] * 10  # 50 total events
        
        start_time = time.time()
        results = self.app.run_batch_workflow(texts)
        end_time = time.time()
        
        batch_time = end_time - start_time
        avg_time_per_event = batch_time / len(texts)
        
        # Batch processing should be efficient
        self.assertLess(avg_time_per_event, 1.0, 
                       f"Average time per event {avg_time_per_event:.2f}s too slow")
        
        print(f"Batch processing time: {batch_time:.3f}s for {len(texts)} events")
        print(f"Average time per event: {avg_time_per_event:.3f}s")
    
    def test_calendar_storage_performance(self):
        """Test performance of calendar storage operations."""
        events = []
        for i in range(100):
            event = Event(
                title=f"Test Event {i}",
                start_datetime=datetime.now() + timedelta(days=i),
                end_datetime=datetime.now() + timedelta(days=i, hours=1)
            )
            events.append(event)
        
        # Test creation performance
        start_time = time.time()
        with patch('builtins.print'):  # Suppress output
            for event in events:
                self.app.calendar_service.create_event(event)
        end_time = time.time()
        
        creation_time = end_time - start_time
        avg_creation_time = creation_time / len(events)
        
        # Event creation should be fast
        self.assertLess(avg_creation_time, 0.1, 
                       f"Average event creation time {avg_creation_time:.4f}s too slow")
        
        # Test retrieval performance
        start_time = time.time()
        stored_events = self.app.calendar_service.list_events()
        end_time = time.time()
        
        retrieval_time = end_time - start_time
        
        # Event retrieval should be fast
        self.assertLess(retrieval_time, 1.0, f"Event retrieval took {retrieval_time:.2f}s")
        
        self.assertEqual(len(stored_events), len(events))
        
        print(f"Created {len(events)} events in {creation_time:.3f}s")
        print(f"Retrieved {len(stored_events)} events in {retrieval_time:.3f}s")


class TestStressScenarios(unittest.TestCase):
    """Test system behavior under stress conditions."""
    
    def setUp(self):
        """Set up test environment."""
        self.parser = EventParser()
    
    def test_extremely_long_text(self):
        """Test parsing extremely long text without crashing."""
        # Create very long text (1MB+)
        base_text = "Meeting tomorrow at 2pm in Conference Room A. "
        long_text = base_text * 20000  # ~1MB of text
        
        start_time = time.time()
        try:
            result = self.parser.parse_text(long_text)
            end_time = time.time()
            
            parse_time = end_time - start_time
            
            # Should not crash and should complete in reasonable time
            self.assertLess(parse_time, 30.0, "Extremely long text parsing took too long")
            self.assertIsNotNone(result)
            
            print(f"Extremely long text ({len(long_text)} chars) parsed in {parse_time:.3f}s")
            
        except Exception as e:
            self.fail(f"Parser crashed on extremely long text: {e}")
    
    def test_many_datetime_patterns(self):
        """Test text with many datetime patterns."""
        # Create text with 100+ datetime patterns
        datetime_text = ""
        for i in range(100):
            datetime_text += f"Event {i} on {i+1}/15/2024 at {(i % 12) + 1}:00pm. "
        
        start_time = time.time()
        try:
            result = self.parser.parse_text(datetime_text)
            end_time = time.time()
            
            parse_time = end_time - start_time
            
            # Should handle many patterns without excessive slowdown
            self.assertLess(parse_time, 10.0, "Many datetime patterns parsing too slow")
            
            print(f"Text with 100 datetime patterns parsed in {parse_time:.3f}s")
            
        except Exception as e:
            self.fail(f"Parser failed with many datetime patterns: {e}")
    
    def test_unicode_and_special_characters(self):
        """Test parsing text with unicode and special characters."""
        unicode_text = """
        Réunion demain à 14h30 dans la salle de conférence. 
        会议明天下午2点在会议室A。
        Встреча завтра в 14:00 в конференц-зале.
        Meeting with special chars: @#$%^&*()_+-=[]{}|;':\",./<>?
        Event on 12/25/2024 at 2:30 PM with émojis 🎉📅⏰
        """
        
        try:
            result = self.parser.parse_text(unicode_text)
            
            # Should handle unicode gracefully
            self.assertIsNotNone(result)
            self.assertGreaterEqual(result.confidence_score, 0.0)
            
            print("Unicode text parsing successful")
            
        except Exception as e:
            self.fail(f"Parser failed with unicode text: {e}")
    
    def test_malformed_datetime_patterns(self):
        """Test parsing text with malformed datetime patterns."""
        malformed_text = """
        Meeting on 32/45/2024 at 25:70 in Room -1.
        Event at 99:99 PM on February 30th, 2024.
        Call on 13/13/13 at 0:0:0:0 AM/PM.
        Conference at ??:?? on ??/??/???? in Room ???.
        """
        
        try:
            result = self.parser.parse_text(malformed_text)
            
            # Should handle malformed patterns gracefully
            self.assertIsNotNone(result)
            # Confidence should be low due to malformed patterns
            self.assertLessEqual(result.confidence_score, 0.5)
            
            print("Malformed datetime patterns handled gracefully")
            
        except Exception as e:
            self.fail(f"Parser crashed on malformed patterns: {e}")


class TestPerformanceBenchmarks(unittest.TestCase):
    """Benchmark tests to establish performance baselines."""
    
    def setUp(self):
        """Set up test environment."""
        self.parser = EventParser()
    
    def test_simple_text_benchmark(self):
        """Benchmark simple text parsing."""
        simple_texts = [
            "Meeting tomorrow at 2pm",
            "Lunch next Friday 12:30",
            "Call Monday 9am for 30 minutes",
            "Training Tuesday 10am-12pm",
            "Conference Wednesday 3pm in Room A"
        ]
        
        times = []
        for text in simple_texts:
            start_time = time.time()
            result = self.parser.parse_text(text)
            end_time = time.time()
            times.append(end_time - start_time)
        
        avg_time = sum(times) / len(times)
        max_time = max(times)
        
        print(f"Simple text parsing benchmark:")
        print(f"  Average time: {avg_time:.4f}s")
        print(f"  Maximum time: {max_time:.4f}s")
        print(f"  Texts per second: {1/avg_time:.1f}")
        
        # Establish performance expectations
        self.assertLess(avg_time, 0.1, "Simple text parsing should be under 0.1s")
        self.assertLess(max_time, 0.2, "No simple text should take over 0.2s")
    
    def test_complex_text_benchmark(self):
        """Benchmark complex text parsing."""
        complex_texts = [
            "Annual team building workshop 'Innovation Day' next Thursday from 9am to 5pm at the Marriott Hotel, 123 Queen Street West, Toronto",
            "Project review meeting with all stakeholders on March 15, 2024 from 10:00 AM to 11:30 AM in the main boardroom to discuss Q1 results",
            "Conference call with overseas team (London, Tokyo, Sydney) tomorrow at 6:00 AM EST for 2 hours to review project timeline and deliverables",
        ]
        
        times = []
        for text in complex_texts:
            start_time = time.time()
            result = self.parser.parse_text(text)
            end_time = time.time()
            times.append(end_time - start_time)
        
        avg_time = sum(times) / len(times)
        max_time = max(times)
        
        print(f"Complex text parsing benchmark:")
        print(f"  Average time: {avg_time:.4f}s")
        print(f"  Maximum time: {max_time:.4f}s")
        
        # Complex text should still be reasonably fast
        self.assertLess(avg_time, 0.5, "Complex text parsing should be under 0.5s")
        self.assertLess(max_time, 1.0, "No complex text should take over 1.0s")


if __name__ == '__main__':
    # Run performance tests with timing information
    print("="*60)
    print("PERFORMANCE TEST SUITE")
    print("="*60)
    
    # Create test suite
    suite = unittest.TestSuite()
    
    # Add performance test classes
    for test_class in [TestParsingPerformance, TestWorkflowPerformance, 
                      TestStressScenarios, TestPerformanceBenchmarks]:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        suite.addTests(tests)
    
    # Run tests with detailed output
    runner = unittest.TextTestRunner(verbosity=2)
    start_time = time.time()
    result = runner.run(suite)
    end_time = time.time()
    
    # Print performance summary
    print(f"\n{'='*60}")
    print(f"PERFORMANCE TEST SUMMARY")
    print(f"{'='*60}")
    print(f"Total test time: {end_time - start_time:.2f}s")
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    
    if result.failures or result.errors:
        print(f"\nPERFORMANCE ISSUES DETECTED:")
        for test, traceback in result.failures + result.errors:
            print(f"- {test}")
    else:
        print(f"\n✅ All performance tests passed!")