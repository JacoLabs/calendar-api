"""
Startup Optimizer for Text-to-Calendar Event Parser.

This module handles application startup with performance optimizations including:
- Lazy loading initialization
- Regex pattern precompilation
- Model warm-up
- Background optimization tasks

Requirements addressed:
- 16.1: Lazy loading for heavy modules to reduce cold start time
- Regex pattern precompilation at startup
- Model warm-up on boot for reduced first-request latency
"""

import asyncio
import logging
from typing import Dict, Any, Optional
from datetime import datetime

from services.performance_optimizer import get_performance_optimizer, PerformanceMetrics

logger = logging.getLogger(__name__)


class StartupOptimizer:
    """
    Handles optimized application startup with performance enhancements.
    """
    
    def __init__(self):
        self.performance_optimizer = get_performance_optimizer()
        self.startup_metrics: Optional[PerformanceMetrics] = None
        self.startup_completed = False
        self.background_tasks = []
    
    async def initialize_application(self, 
                                   enable_warm_up: bool = True,
                                   warm_up_in_background: bool = True) -> PerformanceMetrics:
        """
        Initialize the application with performance optimizations.
        
        Args:
            enable_warm_up: Whether to warm up models
            warm_up_in_background: Whether to warm up models in background
            
        Returns:
            Performance metrics from initialization
        """
        logger.info("Starting application initialization with performance optimizations")
        start_time = datetime.now()
        
        # Get regex patterns for precompilation
        regex_patterns = self._get_regex_patterns()
        
        # Get warm-up inputs
        warm_up_inputs = self._get_warm_up_inputs() if enable_warm_up else None
        
        if warm_up_in_background and enable_warm_up:
            # Initialize without warm-up first for faster startup
            self.startup_metrics = self.performance_optimizer.initialize(
                regex_patterns=regex_patterns,
                warm_up_inputs=None  # Skip warm-up for now
            )
            
            # Start warm-up in background
            warm_up_task = asyncio.create_task(self._background_warm_up(warm_up_inputs))
            self.background_tasks.append(warm_up_task)
            
        else:
            # Initialize with immediate warm-up
            self.startup_metrics = self.performance_optimizer.initialize(
                regex_patterns=regex_patterns,
                warm_up_inputs=warm_up_inputs
            )
        
        self.startup_completed = True
        
        initialization_time = (datetime.now() - start_time).total_seconds()
        logger.info(f"Application initialization completed in {initialization_time:.3f}s")
        
        return self.startup_metrics
    
    async def _background_warm_up(self, warm_up_inputs: Dict[str, str]):
        """
        Perform model warm-up in the background.
        
        Args:
            warm_up_inputs: Test inputs for warm-up
        """
        try:
            logger.info("Starting background model warm-up")
            warm_up_results = self.performance_optimizer.model_warmup.warm_up_models(warm_up_inputs)
            
            successful_warmups = sum(1 for success in warm_up_results.values() if success)
            logger.info(f"Background warm-up completed: {successful_warmups}/{len(warm_up_results)} successful")
            
        except Exception as e:
            logger.error(f"Background warm-up failed: {e}")
    
    def _get_regex_patterns(self) -> Dict[str, str]:
        """
        Get regex patterns for precompilation.
        
        Returns:
            Dictionary of regex patterns to compile
        """
        return {
            # Enhanced date patterns
            'date_slash_us': r'\b\d{1,2}/\d{1,2}/\d{4}\b',
            'date_slash_eu': r'\b\d{1,2}/\d{1,2}/\d{4}\b',
            'date_dash': r'\b\d{1,2}-\d{1,2}-\d{4}\b',
            'date_dot': r'\b\d{1,2}\.\d{1,2}\.\d{4}\b',
            'date_iso': r'\b\d{4}-\d{1,2}-\d{1,2}\b',
            'date_written_full': r'\b(?:january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{1,2},?\s+\d{4}\b',
            'date_written_short': r'\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+\d{1,2},?\s+\d{4}\b',
            'date_ordinal': r'\b\d{1,2}(?:st|nd|rd|th)\s+(?:of\s+)?(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+\d{4}\b',
            
            # Enhanced time patterns
            'time_12hour_colon': r'\b\d{1,2}:\d{2}\s*(?:am|pm|a\.m\.?|p\.m\.?)\b',
            'time_12hour_simple': r'\b\d{1,2}\s*(?:am|pm|a\.m\.?|p\.m\.?)\b',
            'time_24hour': r'\b\d{1,2}:\d{2}\b',
            'time_range_12hour': r'\b\d{1,2}(?::\d{2})?\s*(?:am|pm|a\.m\.?|p\.m\.?)\s*[-–—to]\s*\d{1,2}(?::\d{2})?\s*(?:am|pm|a\.m\.?|p\.m\.?)\b',
            'time_range_24hour': r'\b\d{1,2}:\d{2}\s*[-–—to]\s*\d{1,2}:\d{2}\b',
            'time_special': r'\b(?:noon|midnight|midday)\b',
            
            # Relative date/time patterns
            'relative_day': r'\b(?:today|tomorrow|yesterday)\b',
            'relative_week': r'\b(?:this|next|last)\s+(?:week|monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b',
            'relative_month': r'\b(?:this|next|last)\s+month\b',
            'relative_year': r'\b(?:this|next|last)\s+year\b',
            'relative_time': r'\b(?:in\s+\d+\s+(?:minute|hour|day|week|month)s?|after\s+(?:lunch|dinner|work|school))\b',
            
            # Duration patterns
            'duration_hours': r'\b(?:for\s+)?\d+\s*(?:hour|hr)s?\b',
            'duration_minutes': r'\b(?:for\s+)?\d+\s*(?:minute|min)s?\b',
            'duration_mixed': r'\b(?:for\s+)?\d+\s*(?:hour|hr)s?\s*(?:and\s+)?\d+\s*(?:minute|min)s?\b',
            'duration_until': r'\buntil\s+(?:\d{1,2}(?::\d{2})?\s*(?:am|pm|a\.m\.?|p\.m\.?)|noon|midnight)\b',
            
            # Location patterns
            'location_at': r'\bat\s+([^,\n.!?]+?)(?:\s*[,\n.!?]|$)',
            'location_in': r'\bin\s+([^,\n.!?]+?)(?:\s*[,\n.!?]|$)',
            'location_room': r'\b(?:room|rm)\s+([a-z0-9]+)\b',
            'location_building': r'\b(?:building|bldg)\s+([a-z0-9]+)\b',
            'location_address': r'\b\d+\s+[a-z\s]+(?:street|st|avenue|ave|road|rd|drive|dr|lane|ln|boulevard|blvd)\b',
            'location_venue': r'\b(?:at|in)\s+([a-z\s]+(?:center|centre|hall|auditorium|theater|theatre|stadium|arena|park|square))\b',
            
            # Title/event patterns
            'title_meeting': r'\b(?:meeting|call|conference|session|discussion)\s+(?:with|about|on|regarding)\s+([^,\n.!?]+)',
            'title_event': r'\b(?:event|gathering|party|celebration|ceremony|workshop|seminar|training)\s*:?\s*([^,\n.!?]+)',
            'title_appointment': r'\b(?:appointment|visit|checkup)\s+(?:with|at)\s+([^,\n.!?]+)',
            'title_class': r'\b(?:class|lesson|lecture|course)\s*:?\s*([^,\n.!?]+)',
            
            # Email/document patterns
            'email_subject': r'(?:subject|re)\s*:\s*([^\n]+)',
            'email_from': r'from\s*:\s*([^\n<]+)',
            'email_to': r'to\s*:\s*([^\n<]+)',
            'email_date': r'date\s*:\s*([^\n]+)',
            
            # Due date patterns (for task/deadline detection)
            'due_date': r'due\s+(?:date\s*:?\s*)?([a-z]+\s+\d{1,2},?\s+\d{4})',
            'deadline': r'deadline\s*:?\s*([a-z]+\s+\d{1,2},?\s+\d{4})',
            'expires': r'expires?\s+(?:on\s+)?([a-z]+\s+\d{1,2},?\s+\d{4})',
            
            # Recurrence patterns
            'recurrence_daily': r'\b(?:daily|every\s+day)\b',
            'recurrence_weekly': r'\b(?:weekly|every\s+week|every\s+(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday))\b',
            'recurrence_monthly': r'\b(?:monthly|every\s+month)\b',
            'recurrence_yearly': r'\b(?:yearly|annually|every\s+year)\b',
            'recurrence_every_other': r'\bevery\s+other\s+(?:day|week|month|year|monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b',
            
            # Participant patterns
            'participants_with': r'\bwith\s+([^,\n.!?]+?)(?:\s*[,\n.!?]|$)',
            'participants_and': r'\band\s+([a-z\s]+?)(?:\s*[,\n.!?]|$)',
            'participants_email': r'\b[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}\b',
            
            # Cleanup patterns
            'cleanup_item_id': r'\bitem\s+id\s*:?\s*\d+\b',
            'cleanup_status': r'\bstatus\s*:?\s*[a-z]+\b',
            'cleanup_assignee': r'\bassignee\s*:?\s*[a-z\s]+\b',
            'cleanup_metadata': r'\b(?:created|updated|modified)\s*:?\s*[^\n]+\b',
        }
    
    def _get_warm_up_inputs(self) -> Dict[str, str]:
        """
        Get test inputs for model warm-up.
        
        Returns:
            Dictionary of test inputs for different services
        """
        return {
            'llm_service': "Meeting with John tomorrow at 2pm in Conference Room A",
            'duckling_extractor': "next Friday at 3:30 PM for 1 hour",
            'recognizers_extractor': "January 15th at noon until 1:30 PM",
            'regex_extractor': "Team standup Monday 9:00 AM - 9:30 AM",
            'title_extractor': "Weekly project review meeting",
            'location_extractor': "Meeting at Nathan Phillips Square downtown"
        }
    
    def get_startup_status(self) -> Dict[str, Any]:
        """
        Get current startup status and metrics.
        
        Returns:
            Dictionary with startup information
        """
        status = {
            'startup_completed': self.startup_completed,
            'performance_optimizer_initialized': self.performance_optimizer.is_initialized(),
            'background_tasks_count': len(self.background_tasks),
            'background_tasks_completed': sum(1 for task in self.background_tasks if task.done())
        }
        
        if self.startup_metrics:
            status['startup_metrics'] = {
                'regex_compilation_time': self.startup_metrics.regex_compilation_time,
                'warm_up_time': self.startup_metrics.warm_up_time,
                'module_load_times': self.startup_metrics.module_load_times
            }
        
        return status
    
    def get_performance_optimizer(self):
        """Get the performance optimizer instance."""
        return self.performance_optimizer
    
    async def shutdown(self):
        """Clean shutdown of startup optimizer."""
        logger.info("Shutting down startup optimizer")
        
        # Cancel background tasks
        for task in self.background_tasks:
            if not task.done():
                task.cancel()
        
        # Wait for tasks to complete or be cancelled
        if self.background_tasks:
            await asyncio.gather(*self.background_tasks, return_exceptions=True)
        
        logger.info("Startup optimizer shutdown completed")


# Global instance
_startup_optimizer = None

def get_startup_optimizer() -> StartupOptimizer:
    """Get the global startup optimizer instance."""
    global _startup_optimizer
    if _startup_optimizer is None:
        _startup_optimizer = StartupOptimizer()
    return _startup_optimizer


async def initialize_application_startup(enable_warm_up: bool = True,
                                       warm_up_in_background: bool = True) -> PerformanceMetrics:
    """
    Initialize application startup with performance optimizations.
    
    Args:
        enable_warm_up: Whether to enable model warm-up
        warm_up_in_background: Whether to perform warm-up in background
        
    Returns:
        Performance metrics from initialization
    """
    startup_optimizer = get_startup_optimizer()
    return await startup_optimizer.initialize_application(
        enable_warm_up=enable_warm_up,
        warm_up_in_background=warm_up_in_background
    )


async def shutdown_application_startup():
    """Shutdown application startup optimizer."""
    startup_optimizer = get_startup_optimizer()
    await startup_optimizer.shutdown()