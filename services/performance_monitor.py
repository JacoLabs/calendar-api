"""
Comprehensive Performance Monitoring Module for Text-to-Calendar Event Parser.

This module implements comprehensive performance monitoring including:
- Component latency tracking for regex, deterministic backup, and LLM processing
- Golden set maintenance with 50-100 curated test cases
- Reliability diagram generation for confidence calibration
- Performance metrics collection and reporting

Requirements addressed:
- 15.1: Component latency tracking and performance metrics collection
- 15.2: Golden set maintenance with 50-100 curated test cases
- 15.3: Reliability diagram generation for confidence calibration
"""

import json
import logging
import statistics
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Callable
import matplotlib.pyplot as plt
import numpy as np
from models.event_models import ParsedEvent, NormalizedEvent

logger = logging.getLogger(__name__)


@dataclass
class ComponentLatency:
    """Tracks latency metrics for a specific component."""
    component_name: str
    latencies: deque = field(default_factory=lambda: deque(maxlen=1000))  # Keep last 1000 measurements
    total_calls: int = 0
    total_time_ms: float = 0.0
    
    def add_measurement(self, latency_ms: float):
        """Add a latency measurement."""
        self.latencies.append(latency_ms)
        self.total_calls += 1
        self.total_time_ms += latency_ms
    
    def get_stats(self) -> Dict[str, float]:
        """Get statistical summary of latencies."""
        if not self.latencies:
            return {
                'count': 0,
                'mean': 0.0,
                'median': 0.0,
                'p95': 0.0,
                'p99': 0.0,
                'min': 0.0,
                'max': 0.0
            }
        
        latencies_list = list(self.latencies)
        return {
            'count': len(latencies_list),
            'mean': statistics.mean(latencies_list),
            'median': statistics.median(latencies_list),
            'p95': np.percentile(latencies_list, 95),
            'p99': np.percentile(latencies_list, 99),
            'min': min(latencies_list),
            'max': max(latencies_list)
        }


@dataclass
class GoldenTestCase:
    """Represents a curated test case for accuracy validation."""
    id: str
    input_text: str
    expected_title: str
    expected_start: datetime
    expected_end: datetime
    expected_location: Optional[str] = None
    expected_description: str = ""
    category: str = "general"  # "date_time", "location", "title", "complex", etc.
    difficulty: str = "medium"  # "easy", "medium", "hard"
    notes: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'id': self.id,
            'input_text': self.input_text,
            'expected_title': self.expected_title,
            'expected_start': self.expected_start.isoformat(),
            'expected_end': self.expected_end.isoformat(),
            'expected_location': self.expected_location,
            'expected_description': self.expected_description,
            'category': self.category,
            'difficulty': self.difficulty,
            'notes': self.notes
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'GoldenTestCase':
        """Create GoldenTestCase from dictionary."""
        return cls(
            id=data['id'],
            input_text=data['input_text'],
            expected_title=data['expected_title'],
            expected_start=datetime.fromisoformat(data['expected_start']),
            expected_end=datetime.fromisoformat(data['expected_end']),
            expected_location=data.get('expected_location'),
            expected_description=data.get('expected_description', ''),
            category=data.get('category', 'general'),
            difficulty=data.get('difficulty', 'medium'),
            notes=data.get('notes', '')
        )


@dataclass
class AccuracyResult:
    """Represents the result of testing against a golden test case."""
    test_case_id: str
    predicted_event: Optional[ParsedEvent]
    accuracy_score: float  # 0.0 to 1.0
    field_accuracies: Dict[str, float] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    processing_time_ms: float = 0.0
    confidence_score: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'test_case_id': self.test_case_id,
            'predicted_event': self.predicted_event.to_dict() if self.predicted_event else None,
            'accuracy_score': self.accuracy_score,
            'field_accuracies': self.field_accuracies,
            'errors': self.errors,
            'processing_time_ms': self.processing_time_ms,
            'confidence_score': self.confidence_score
        }


@dataclass
class ReliabilityPoint:
    """Represents a point in the reliability diagram."""
    confidence_bin: float  # Center of confidence bin (e.g., 0.1, 0.2, ...)
    predicted_confidence: float  # Average predicted confidence in this bin
    actual_accuracy: float  # Actual accuracy for predictions in this bin
    count: int  # Number of predictions in this bin


@dataclass
class PerformanceMetrics:
    """Comprehensive performance metrics for the parsing system."""
    timestamp: datetime = field(default_factory=datetime.now)
    
    # Component latency metrics
    component_latencies: Dict[str, Dict[str, float]] = field(default_factory=dict)
    
    # Accuracy metrics
    overall_accuracy: float = 0.0
    field_accuracies: Dict[str, float] = field(default_factory=dict)
    
    # Confidence calibration metrics
    calibration_error: float = 0.0  # Expected Calibration Error (ECE)
    reliability_points: List[ReliabilityPoint] = field(default_factory=list)
    
    # System performance metrics
    total_requests: int = 0
    successful_parses: int = 0
    failed_parses: int = 0
    cache_hit_rate: float = 0.0
    
    # Quality metrics
    average_quality_score: float = 0.0
    quality_distribution: Dict[str, int] = field(default_factory=dict)  # "high", "medium", "low"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'timestamp': self.timestamp.isoformat(),
            'component_latencies': self.component_latencies,
            'overall_accuracy': self.overall_accuracy,
            'field_accuracies': self.field_accuracies,
            'calibration_error': self.calibration_error,
            'reliability_points': [
                {
                    'confidence_bin': rp.confidence_bin,
                    'predicted_confidence': rp.predicted_confidence,
                    'actual_accuracy': rp.actual_accuracy,
                    'count': rp.count
                }
                for rp in self.reliability_points
            ],
            'total_requests': self.total_requests,
            'successful_parses': self.successful_parses,
            'failed_parses': self.failed_parses,
            'cache_hit_rate': self.cache_hit_rate,
            'average_quality_score': self.average_quality_score,
            'quality_distribution': self.quality_distribution
        }


class PerformanceMonitor:
    """
    Comprehensive performance monitoring system for text-to-calendar event parsing.
    
    Tracks component latencies, maintains golden test sets, generates reliability diagrams,
    and provides comprehensive performance metrics collection and reporting.
    
    Requirements:
    - 15.1: Component latency tracking for regex, deterministic, and LLM timing
    - 15.2: Golden set maintenance with 50-100 curated test cases
    - 15.3: Reliability diagram generation for confidence calibration
    """
    
    def __init__(self, golden_set_path: str = "tests/golden_set.json"):
        """
        Initialize the performance monitor.
        
        Args:
            golden_set_path: Path to the golden test set file
        """
        self.golden_set_path = Path(golden_set_path)
        
        # Component latency tracking
        self.component_latencies: Dict[str, ComponentLatency] = {
            'regex_extractor': ComponentLatency('regex_extractor'),
            'duckling_extractor': ComponentLatency('duckling_extractor'),
            'recognizers_extractor': ComponentLatency('recognizers_extractor'),
            'llm_enhancer': ComponentLatency('llm_enhancer'),
            'title_extractor': ComponentLatency('title_extractor'),
            'location_extractor': ComponentLatency('location_extractor'),
            'recurrence_processor': ComponentLatency('recurrence_processor'),
            'duration_processor': ComponentLatency('duration_processor'),
            'overall_parsing': ComponentLatency('overall_parsing')
        }
        
        # Golden test set
        self.golden_test_cases: List[GoldenTestCase] = []
        self.load_golden_set()
        
        # Accuracy tracking
        self.accuracy_results: deque = deque(maxlen=1000)  # Keep last 1000 results
        
        # Confidence calibration tracking
        self.confidence_predictions: List[Tuple[float, bool]] = []  # (confidence, was_correct)
        
        # System metrics
        self.request_count = 0
        self.success_count = 0
        self.failure_count = 0
        self.cache_hits = 0
        self.cache_misses = 0
        
        # Quality tracking
        self.quality_scores: deque = deque(maxlen=1000)
        
        logger.info(f"PerformanceMonitor initialized with {len(self.golden_test_cases)} golden test cases")
    
    def track_component_latency(self, component: str, duration_ms: float):
        """
        Track latency for a specific component.
        
        Args:
            component: Component name (regex, deterministic, llm, etc.)
            duration_ms: Processing duration in milliseconds
            
        Requirements: 15.1 - Component latency tracking
        """
        if component in self.component_latencies:
            self.component_latencies[component].add_measurement(duration_ms)
            logger.debug(f"Tracked {component} latency: {duration_ms:.2f}ms")
        else:
            logger.warning(f"Unknown component for latency tracking: {component}")
    
    def time_component(self, component: str):
        """
        Context manager for timing component execution.
        
        Args:
            component: Component name
            
        Usage:
            with monitor.time_component('regex_extractor'):
                # Component execution code
                pass
        """
        class ComponentTimer:
            def __init__(self, monitor: 'PerformanceMonitor', component_name: str):
                self.monitor = monitor
                self.component_name = component_name
                self.start_time = None
            
            def __enter__(self):
                self.start_time = time.time()
                return self
            
            def __exit__(self, exc_type, exc_val, exc_tb):
                if self.start_time:
                    duration_ms = (time.time() - self.start_time) * 1000
                    self.monitor.track_component_latency(self.component_name, duration_ms)
        
        return ComponentTimer(self, component)
    
    def load_golden_set(self):
        """
        Load golden test set from file or create default set.
        
        Requirements: 15.2 - Golden set maintenance with 50-100 curated test cases
        """
        try:
            if self.golden_set_path.exists():
                with open(self.golden_set_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.golden_test_cases = [
                        GoldenTestCase.from_dict(case_data)
                        for case_data in data.get('test_cases', [])
                    ]
                logger.info(f"Loaded {len(self.golden_test_cases)} golden test cases")
            else:
                logger.info("Golden set file not found, creating default test cases")
                self.create_default_golden_set()
                self.save_golden_set()
        except Exception as e:
            logger.error(f"Error loading golden set: {e}")
            self.create_default_golden_set()
    
    def create_default_golden_set(self):
        """Create a default set of golden test cases covering various scenarios."""
        default_cases = [
            # Basic date/time cases
            GoldenTestCase(
                id="basic_001",
                input_text="Meeting tomorrow at 2pm",
                expected_title="Meeting",
                expected_start=datetime(2025, 1, 2, 14, 0),
                expected_end=datetime(2025, 1, 2, 15, 0),
                category="date_time",
                difficulty="easy"
            ),
            GoldenTestCase(
                id="basic_002",
                input_text="Lunch with John next Friday from 12:30-1:30 at Cafe Downtown",
                expected_title="Lunch with John",
                expected_start=datetime(2025, 1, 10, 12, 30),
                expected_end=datetime(2025, 1, 10, 13, 30),
                expected_location="Cafe Downtown",
                category="location",
                difficulty="medium"
            ),
            GoldenTestCase(
                id="basic_003",
                input_text="Team standup every Monday at 9am",
                expected_title="Team standup",
                expected_start=datetime(2025, 1, 6, 9, 0),
                expected_end=datetime(2025, 1, 6, 10, 0),
                category="recurrence",
                difficulty="medium"
            ),
            
            # Complex formatting cases
            GoldenTestCase(
                id="complex_001",
                input_text="Indigenous Legacy Gathering\nMonday, Sep 29, 2025\n2–3pm\nNathan Phillips Square",
                expected_title="Indigenous Legacy Gathering",
                expected_start=datetime(2025, 9, 29, 14, 0),
                expected_end=datetime(2025, 9, 29, 15, 0),
                expected_location="Nathan Phillips Square",
                category="complex",
                difficulty="medium"
            ),
            GoldenTestCase(
                id="complex_002",
                input_text="Project Review Meeting\n• Date: January 15, 2025\n• Time: 10:00 AM - 11:30 AM\n• Location: Conference Room B\n• Attendees: Team leads",
                expected_title="Project Review Meeting",
                expected_start=datetime(2025, 1, 15, 10, 0),
                expected_end=datetime(2025, 1, 15, 11, 30),
                expected_location="Conference Room B",
                category="complex",
                difficulty="hard"
            ),
            
            # Typo and format variation cases
            GoldenTestCase(
                id="typo_001",
                input_text="Dentist appointment tommorow at 9a.m",
                expected_title="Dentist appointment",
                expected_start=datetime(2025, 1, 2, 9, 0),
                expected_end=datetime(2025, 1, 2, 10, 0),
                category="typo",
                difficulty="medium"
            ),
            GoldenTestCase(
                id="typo_002",
                input_text="Meeting on 01/15/2025 at 2 PM for 45 minutes",
                expected_title="Meeting",
                expected_start=datetime(2025, 1, 15, 14, 0),
                expected_end=datetime(2025, 1, 15, 14, 45),
                category="duration",
                difficulty="medium"
            ),
            
            # Relative date cases
            GoldenTestCase(
                id="relative_001",
                input_text="Doctor appointment next week Tuesday at noon",
                expected_title="Doctor appointment",
                expected_start=datetime(2025, 1, 7, 12, 0),
                expected_end=datetime(2025, 1, 7, 13, 0),
                category="relative_date",
                difficulty="medium"
            ),
            GoldenTestCase(
                id="relative_002",
                input_text="Conference call in two weeks at 3:30 PM",
                expected_title="Conference call",
                expected_start=datetime(2025, 1, 15, 15, 30),
                expected_end=datetime(2025, 1, 15, 16, 30),
                category="relative_date",
                difficulty="hard"
            ),
            
            # All-day and duration cases
            GoldenTestCase(
                id="duration_001",
                input_text="Workshop all day on March 1st",
                expected_title="Workshop",
                expected_start=datetime(2025, 3, 1, 0, 0),
                expected_end=datetime(2025, 3, 1, 23, 59),
                category="all_day",
                difficulty="easy"
            ),
            GoldenTestCase(
                id="duration_002",
                input_text="Training session from 9am until noon on Friday",
                expected_title="Training session",
                expected_start=datetime(2025, 1, 3, 9, 0),
                expected_end=datetime(2025, 1, 3, 12, 0),
                category="duration",
                difficulty="medium"
            )
        ]
        
        self.golden_test_cases = default_cases
        logger.info(f"Created {len(default_cases)} default golden test cases")
    
    def save_golden_set(self):
        """Save golden test set to file."""
        try:
            # Ensure directory exists
            self.golden_set_path.parent.mkdir(parents=True, exist_ok=True)
            
            data = {
                'version': '1.0',
                'created': datetime.now().isoformat(),
                'test_cases': [case.to_dict() for case in self.golden_test_cases]
            }
            
            with open(self.golden_set_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Saved {len(self.golden_test_cases)} golden test cases to {self.golden_set_path}")
        except Exception as e:
            logger.error(f"Error saving golden set: {e}")
    
    def add_golden_test_case(self, test_case: GoldenTestCase):
        """
        Add a new golden test case.
        
        Args:
            test_case: GoldenTestCase to add
        """
        # Check for duplicate IDs
        existing_ids = {case.id for case in self.golden_test_cases}
        if test_case.id in existing_ids:
            logger.warning(f"Golden test case with ID {test_case.id} already exists")
            return False
        
        self.golden_test_cases.append(test_case)
        self.save_golden_set()
        logger.info(f"Added golden test case: {test_case.id}")
        return True
    
    def evaluate_accuracy(self, parser_func: Callable[[str], ParsedEvent]) -> Dict[str, Any]:
        """
        Evaluate parsing accuracy against golden test set.
        
        Args:
            parser_func: Function that takes text and returns ParsedEvent
            
        Returns:
            Dictionary with accuracy metrics and detailed results
            
        Requirements: 15.2 - Golden set maintenance and accuracy evaluation
        """
        if not self.golden_test_cases:
            logger.warning("No golden test cases available for evaluation")
            return {'error': 'No golden test cases available'}
        
        results = []
        total_accuracy = 0.0
        field_accuracies = defaultdict(list)
        
        logger.info(f"Evaluating accuracy against {len(self.golden_test_cases)} golden test cases")
        
        for test_case in self.golden_test_cases:
            try:
                # Time the parsing
                start_time = time.time()
                predicted_event = parser_func(test_case.input_text)
                processing_time_ms = (time.time() - start_time) * 1000
                
                # Calculate accuracy
                accuracy_result = self._calculate_accuracy(test_case, predicted_event)
                accuracy_result.processing_time_ms = processing_time_ms
                
                results.append(accuracy_result)
                total_accuracy += accuracy_result.accuracy_score
                
                # Track field accuracies
                for field, accuracy in accuracy_result.field_accuracies.items():
                    field_accuracies[field].append(accuracy)
                
                # Track confidence calibration
                if predicted_event and predicted_event.confidence_score > 0:
                    is_correct = accuracy_result.accuracy_score > 0.7  # Consider >70% accuracy as correct
                    self.confidence_predictions.append((predicted_event.confidence_score, is_correct))
                
                logger.debug(f"Test case {test_case.id}: accuracy={accuracy_result.accuracy_score:.3f}")
                
            except Exception as e:
                logger.error(f"Error evaluating test case {test_case.id}: {e}")
                error_result = AccuracyResult(
                    test_case_id=test_case.id,
                    predicted_event=None,
                    accuracy_score=0.0,
                    errors=[str(e)]
                )
                results.append(error_result)
        
        # Calculate summary statistics
        overall_accuracy = total_accuracy / len(results) if results else 0.0
        
        field_accuracy_summary = {}
        for field, accuracies in field_accuracies.items():
            field_accuracy_summary[field] = {
                'mean': statistics.mean(accuracies),
                'median': statistics.median(accuracies),
                'min': min(accuracies),
                'max': max(accuracies),
                'count': len(accuracies)
            }
        
        # Store results for later analysis
        self.accuracy_results.extend(results)
        
        # Calculate performance stats safely
        processing_times = [r.processing_time_ms for r in results if r.processing_time_ms > 0]
        performance_stats = {}
        if processing_times:
            performance_stats = {
                'mean_processing_time_ms': statistics.mean(processing_times),
                'median_processing_time_ms': statistics.median(processing_times)
            }
        else:
            performance_stats = {
                'mean_processing_time_ms': 0.0,
                'median_processing_time_ms': 0.0
            }
        
        evaluation_summary = {
            'timestamp': datetime.now().isoformat(),
            'total_test_cases': len(self.golden_test_cases),
            'overall_accuracy': overall_accuracy,
            'field_accuracies': field_accuracy_summary,
            'results': [result.to_dict() for result in results],
            'performance_stats': performance_stats
        }
        
        logger.info(f"Accuracy evaluation complete: {overall_accuracy:.3f} overall accuracy")
        return evaluation_summary
    
    def _calculate_accuracy(self, test_case: GoldenTestCase, predicted_event: Optional[ParsedEvent]) -> AccuracyResult:
        """
        Calculate accuracy score for a single test case.
        
        Args:
            test_case: Expected results
            predicted_event: Actual prediction
            
        Returns:
            AccuracyResult with detailed accuracy breakdown
        """
        if not predicted_event:
            return AccuracyResult(
                test_case_id=test_case.id,
                predicted_event=None,
                accuracy_score=0.0,
                errors=["No prediction generated"]
            )
        
        field_accuracies = {}
        errors = []
        
        # Title accuracy
        title_accuracy = 0.0
        if predicted_event.title and test_case.expected_title:
            # Simple string similarity (could be enhanced with fuzzy matching)
            predicted_title = predicted_event.title.lower().strip()
            expected_title = test_case.expected_title.lower().strip()
            
            if predicted_title == expected_title:
                title_accuracy = 1.0
            elif expected_title in predicted_title or predicted_title in expected_title:
                title_accuracy = 0.7
            else:
                # Check for word overlap
                predicted_words = set(predicted_title.split())
                expected_words = set(expected_title.split())
                overlap = len(predicted_words & expected_words)
                total_words = len(predicted_words | expected_words)
                title_accuracy = overlap / total_words if total_words > 0 else 0.0
        
        field_accuracies['title'] = title_accuracy
        if title_accuracy < 0.5:
            errors.append(f"Title mismatch: expected '{test_case.expected_title}', got '{predicted_event.title}'")
        
        # Start datetime accuracy
        start_accuracy = 0.0
        if predicted_event.start_datetime and test_case.expected_start:
            time_diff = abs((predicted_event.start_datetime - test_case.expected_start).total_seconds())
            if time_diff == 0:
                start_accuracy = 1.0
            elif time_diff <= 300:  # Within 5 minutes
                start_accuracy = 0.9
            elif time_diff <= 3600:  # Within 1 hour
                start_accuracy = 0.7
            elif time_diff <= 86400:  # Within 1 day
                start_accuracy = 0.3
            else:
                start_accuracy = 0.0
        
        field_accuracies['start_datetime'] = start_accuracy
        if start_accuracy < 0.7:  # Changed threshold to be more lenient for errors
            errors.append(f"Start time mismatch: expected {test_case.expected_start}, got {predicted_event.start_datetime}")
        
        # End datetime accuracy
        end_accuracy = 0.0
        if predicted_event.end_datetime and test_case.expected_end:
            time_diff = abs((predicted_event.end_datetime - test_case.expected_end).total_seconds())
            if time_diff == 0:
                end_accuracy = 1.0
            elif time_diff <= 300:  # Within 5 minutes
                end_accuracy = 0.9
            elif time_diff <= 3600:  # Within 1 hour
                end_accuracy = 0.7
            elif time_diff <= 86400:  # Within 1 day
                end_accuracy = 0.3
            else:
                end_accuracy = 0.0
        
        field_accuracies['end_datetime'] = end_accuracy
        if end_accuracy < 0.7:  # Changed threshold to be more lenient for errors
            errors.append(f"End time mismatch: expected {test_case.expected_end}, got {predicted_event.end_datetime}")
        
        # Location accuracy (optional field)
        location_accuracy = 1.0  # Default to perfect if no location expected
        if test_case.expected_location:
            if predicted_event.location:
                predicted_location = predicted_event.location.lower().strip()
                expected_location = test_case.expected_location.lower().strip()
                
                if predicted_location == expected_location:
                    location_accuracy = 1.0
                elif expected_location in predicted_location or predicted_location in expected_location:
                    location_accuracy = 0.8
                else:
                    location_accuracy = 0.0
            else:
                location_accuracy = 0.0
                errors.append(f"Missing location: expected '{test_case.expected_location}'")
        elif predicted_event.location:
            # Extra location provided (not necessarily wrong)
            location_accuracy = 0.8
        
        field_accuracies['location'] = location_accuracy
        
        # Calculate overall accuracy (weighted average)
        weights = {
            'title': 0.3,
            'start_datetime': 0.4,
            'end_datetime': 0.2,
            'location': 0.1
        }
        
        overall_accuracy = sum(
            field_accuracies[field] * weights[field]
            for field in weights
            if field in field_accuracies
        )
        
        return AccuracyResult(
            test_case_id=test_case.id,
            predicted_event=predicted_event,
            accuracy_score=overall_accuracy,
            field_accuracies=field_accuracies,
            errors=errors,
            confidence_score=predicted_event.confidence_score
        )
    
    def generate_reliability_diagram(self, output_path: str = "reliability_diagram.png") -> Dict[str, Any]:
        """
        Generate reliability diagram for confidence calibration analysis.
        
        Args:
            output_path: Path to save the reliability diagram
            
        Returns:
            Dictionary with calibration metrics and reliability data
            
        Requirements: 15.3 - Reliability diagram generation for confidence calibration
        """
        if not self.confidence_predictions:
            logger.warning("No confidence predictions available for reliability diagram")
            return {'error': 'No confidence predictions available'}
        
        # Create confidence bins
        num_bins = 10
        bin_boundaries = np.linspace(0, 1, num_bins + 1)
        reliability_points = []
        
        total_predictions = len(self.confidence_predictions)
        logger.info(f"Generating reliability diagram from {total_predictions} predictions")
        
        # Calculate reliability for each bin
        for i in range(num_bins):
            bin_start = bin_boundaries[i]
            bin_end = bin_boundaries[i + 1]
            bin_center = (bin_start + bin_end) / 2
            
            # Find predictions in this bin
            bin_predictions = [
                (conf, correct) for conf, correct in self.confidence_predictions
                if bin_start <= conf < bin_end or (i == num_bins - 1 and conf == 1.0)
            ]
            
            if bin_predictions:
                confidences = [conf for conf, _ in bin_predictions]
                correctness = [correct for _, correct in bin_predictions]
                
                avg_confidence = statistics.mean(confidences)
                accuracy = sum(correctness) / len(correctness)
                count = len(bin_predictions)
                
                reliability_points.append(ReliabilityPoint(
                    confidence_bin=bin_center,
                    predicted_confidence=avg_confidence,
                    actual_accuracy=accuracy,
                    count=count
                ))
        
        # Calculate Expected Calibration Error (ECE)
        ece = 0.0
        for point in reliability_points:
            weight = point.count / total_predictions
            ece += weight * abs(point.predicted_confidence - point.actual_accuracy)
        
        # Generate the plot
        try:
            plt.figure(figsize=(10, 8))
            
            # Plot reliability curve
            if reliability_points:
                confidences = [p.predicted_confidence for p in reliability_points]
                accuracies = [p.actual_accuracy for p in reliability_points]
                counts = [p.count for p in reliability_points]
                
                # Main reliability plot
                plt.subplot(2, 2, 1)
                plt.scatter(confidences, accuracies, s=[c*10 for c in counts], alpha=0.7)
                plt.plot([0, 1], [0, 1], 'r--', label='Perfect calibration')
                plt.xlabel('Predicted Confidence')
                plt.ylabel('Actual Accuracy')
                plt.title(f'Reliability Diagram (ECE: {ece:.3f})')
                plt.legend()
                plt.grid(True, alpha=0.3)
                
                # Confidence histogram
                plt.subplot(2, 2, 2)
                all_confidences = [conf for conf, _ in self.confidence_predictions]
                plt.hist(all_confidences, bins=20, alpha=0.7, edgecolor='black')
                plt.xlabel('Predicted Confidence')
                plt.ylabel('Frequency')
                plt.title('Confidence Distribution')
                plt.grid(True, alpha=0.3)
                
                # Accuracy by confidence bin
                plt.subplot(2, 2, 3)
                bin_centers = [p.confidence_bin for p in reliability_points]
                bin_accuracies = [p.actual_accuracy for p in reliability_points]
                plt.bar(bin_centers, bin_accuracies, width=0.08, alpha=0.7)
                plt.xlabel('Confidence Bin')
                plt.ylabel('Accuracy')
                plt.title('Accuracy by Confidence Bin')
                plt.grid(True, alpha=0.3)
                
                # Sample count by bin
                plt.subplot(2, 2, 4)
                bin_counts = [p.count for p in reliability_points]
                plt.bar(bin_centers, bin_counts, width=0.08, alpha=0.7)
                plt.xlabel('Confidence Bin')
                plt.ylabel('Sample Count')
                plt.title('Sample Count by Confidence Bin')
                plt.grid(True, alpha=0.3)
            
            plt.tight_layout()
            plt.savefig(output_path, dpi=300, bbox_inches='tight')
            plt.close()
            
            logger.info(f"Reliability diagram saved to {output_path}")
            
        except Exception as e:
            logger.error(f"Error generating reliability diagram: {e}")
        
        # Return calibration metrics
        calibration_data = {
            'expected_calibration_error': ece,
            'total_predictions': total_predictions,
            'reliability_points': [
                {
                    'confidence_bin': p.confidence_bin,
                    'predicted_confidence': p.predicted_confidence,
                    'actual_accuracy': p.actual_accuracy,
                    'count': p.count
                }
                for p in reliability_points
            ],
            'diagram_path': output_path
        }
        
        return calibration_data
    
    def record_request(self, success: bool, cache_hit: bool = False, quality_score: float = None):
        """
        Record a parsing request for system metrics.
        
        Args:
            success: Whether the parsing was successful
            cache_hit: Whether the result came from cache
            quality_score: Quality score of the result (0.0 to 1.0)
        """
        self.request_count += 1
        
        if success:
            self.success_count += 1
        else:
            self.failure_count += 1
        
        if cache_hit:
            self.cache_hits += 1
        else:
            self.cache_misses += 1
        
        if quality_score is not None:
            self.quality_scores.append(quality_score)
    
    def get_performance_metrics(self) -> PerformanceMetrics:
        """
        Get comprehensive performance metrics.
        
        Returns:
            PerformanceMetrics object with current system performance data
        """
        # Component latency metrics
        component_latencies = {}
        for component_name, latency_tracker in self.component_latencies.items():
            component_latencies[component_name] = latency_tracker.get_stats()
        
        # Calculate cache hit rate
        total_cache_requests = self.cache_hits + self.cache_misses
        cache_hit_rate = self.cache_hits / total_cache_requests if total_cache_requests > 0 else 0.0
        
        # Calculate average quality score
        avg_quality = statistics.mean(self.quality_scores) if self.quality_scores else 0.0
        
        # Quality distribution
        quality_distribution = {'high': 0, 'medium': 0, 'low': 0}
        for score in self.quality_scores:
            if score >= 0.7:
                quality_distribution['high'] += 1
            elif score >= 0.4:
                quality_distribution['medium'] += 1
            else:
                quality_distribution['low'] += 1
        
        # Field accuracies from recent results
        field_accuracies = {}
        if self.accuracy_results:
            recent_results = list(self.accuracy_results)[-100:]  # Last 100 results
            field_accuracy_sums = defaultdict(list)
            
            for result in recent_results:
                for field, accuracy in result.field_accuracies.items():
                    field_accuracy_sums[field].append(accuracy)
            
            for field, accuracies in field_accuracy_sums.items():
                field_accuracies[field] = statistics.mean(accuracies)
        
        # Overall accuracy
        overall_accuracy = 0.0
        if self.accuracy_results:
            recent_results = list(self.accuracy_results)[-100:]
            overall_accuracy = statistics.mean([r.accuracy_score for r in recent_results])
        
        # Calibration error
        calibration_error = 0.0
        if len(self.confidence_predictions) >= 10:
            # Quick ECE calculation
            try:
                confidences = [conf for conf, _ in self.confidence_predictions[-100:]]
                correctness = [correct for _, correct in self.confidence_predictions[-100:]]
                
                # Simple binning for quick calculation
                bins = np.linspace(0, 1, 11)
                bin_indices = np.digitize(confidences, bins) - 1
                
                ece = 0.0
                total_count = len(confidences)
                
                for bin_idx in range(10):
                    bin_mask = bin_indices == bin_idx
                    if np.any(bin_mask):
                        bin_confidences = np.array(confidences)[bin_mask]
                        bin_correctness = np.array(correctness)[bin_mask]
                        
                        avg_confidence = np.mean(bin_confidences)
                        avg_accuracy = np.mean(bin_correctness)
                        bin_weight = len(bin_confidences) / total_count
                        
                        ece += bin_weight * abs(avg_confidence - avg_accuracy)
                
                calibration_error = ece
            except Exception as e:
                logger.warning(f"Error calculating calibration error: {e}")
        
        return PerformanceMetrics(
            component_latencies=component_latencies,
            overall_accuracy=overall_accuracy,
            field_accuracies=field_accuracies,
            calibration_error=calibration_error,
            total_requests=self.request_count,
            successful_parses=self.success_count,
            failed_parses=self.failure_count,
            cache_hit_rate=cache_hit_rate,
            average_quality_score=avg_quality,
            quality_distribution=quality_distribution
        )
    
    def generate_performance_report(self, output_path: str = "performance_report.json") -> Dict[str, Any]:
        """
        Generate comprehensive performance report.
        
        Args:
            output_path: Path to save the performance report
            
        Returns:
            Dictionary with comprehensive performance analysis
        """
        metrics = self.get_performance_metrics()
        
        # Generate reliability diagram
        reliability_data = self.generate_reliability_diagram("reliability_diagram.png")
        
        # Create comprehensive report
        report = {
            'report_timestamp': datetime.now().isoformat(),
            'system_metrics': metrics.to_dict(),
            'reliability_analysis': reliability_data,
            'golden_set_info': {
                'total_cases': len(self.golden_test_cases),
                'categories': list(set(case.category for case in self.golden_test_cases)),
                'difficulty_distribution': {
                    difficulty: sum(1 for case in self.golden_test_cases if case.difficulty == difficulty)
                    for difficulty in ['easy', 'medium', 'hard']
                }
            },
            'recommendations': self._generate_recommendations(metrics)
        }
        
        # Save report
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            logger.info(f"Performance report saved to {output_path}")
        except Exception as e:
            logger.error(f"Error saving performance report: {e}")
        
        return report
    
    def _generate_recommendations(self, metrics: PerformanceMetrics) -> List[str]:
        """Generate performance improvement recommendations based on metrics."""
        recommendations = []
        
        # Latency recommendations
        for component, stats in metrics.component_latencies.items():
            if stats['count'] > 0:
                if stats['p95'] > 5000:  # >5 seconds
                    recommendations.append(f"High latency detected in {component} (P95: {stats['p95']:.0f}ms) - consider optimization")
                elif stats['p95'] > 2000:  # >2 seconds
                    recommendations.append(f"Moderate latency in {component} (P95: {stats['p95']:.0f}ms) - monitor for trends")
        
        # Accuracy recommendations
        if metrics.overall_accuracy < 0.7:
            recommendations.append(f"Overall accuracy is low ({metrics.overall_accuracy:.2f}) - review golden set and parsing logic")
        
        for field, accuracy in metrics.field_accuracies.items():
            if accuracy < 0.6:
                recommendations.append(f"Low accuracy for {field} field ({accuracy:.2f}) - consider field-specific improvements")
        
        # Calibration recommendations
        if metrics.calibration_error > 0.1:
            recommendations.append(f"Poor confidence calibration (ECE: {metrics.calibration_error:.3f}) - review confidence scoring")
        
        # Cache recommendations
        if metrics.cache_hit_rate < 0.3:
            recommendations.append(f"Low cache hit rate ({metrics.cache_hit_rate:.2f}) - review caching strategy")
        
        # Quality recommendations
        if metrics.average_quality_score < 0.6:
            recommendations.append(f"Low average quality score ({metrics.average_quality_score:.2f}) - review quality assessment criteria")
        
        return recommendations


# Global instance
_performance_monitor = None

def get_performance_monitor() -> PerformanceMonitor:
    """Get the global performance monitor instance."""
    global _performance_monitor
    if _performance_monitor is None:
        _performance_monitor = PerformanceMonitor()
    return _performance_monitor