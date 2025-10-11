#!/usr/bin/env python3
"""
Production Performance and Accuracy Validator.

This script implements comprehensive production validation including:
- Parsing accuracy monitoring against golden set
- Component latency tracking and performance analysis
- Confidence calibration validation with real user data
- Cache hit rate monitoring and performance improvements
- Production performance dashboard and reporting

Requirements addressed:
- 15.1: Component latency tracking and performance metrics
- 15.2: Golden set accuracy monitoring in production
- 15.3: Confidence calibration validation
- 16.6: Production performance dashboard and reporting
"""

import asyncio
import json
import logging
import statistics
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import aiohttp
import psutil
import matplotlib.pyplot as plt
import numpy as np

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class ProductionMetrics:
    """Production performance metrics snapshot."""
    timestamp: datetime = field(default_factory=datetime.now)
    
    # Accuracy metrics
    golden_set_accuracy: float = 0.0
    field_accuracies: Dict[str, float] = field(default_factory=dict)
    confidence_calibration_error: float = 0.0
    
    # Performance metrics
    component_latencies: Dict[str, Dict[str, float]] = field(default_factory=dict)
    overall_latency_p50: float = 0.0
    overall_latency_p95: float = 0.0
    overall_latency_p99: float = 0.0
    
    # Cache metrics
    cache_hit_rate: float = 0.0
    cache_size: int = 0
    cache_performance_improvement: float = 0.0
    
    # System metrics
    cpu_usage: float = 0.0
    memory_usage: float = 0.0
    request_rate: float = 0.0
    error_rate: float = 0.0
    
    # Quality metrics
    high_confidence_rate: float = 0.0
    needs_confirmation_rate: float = 0.0
    warning_rate: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'timestamp': self.timestamp.isoformat(),
            'accuracy': {
                'golden_set_accuracy': self.golden_set_accuracy,
                'field_accuracies': self.field_accuracies,
                'confidence_calibration_error': self.confidence_calibration_error
            },
            'performance': {
                'component_latencies': self.component_latencies,
                'overall_latency_p50': self.overall_latency_p50,
                'overall_latency_p95': self.overall_latency_p95,
                'overall_latency_p99': self.overall_latency_p99
            },
            'cache': {
                'hit_rate': self.cache_hit_rate,
                'size': self.cache_size,
                'performance_improvement': self.cache_performance_improvement
            },
            'system': {
                'cpu_usage': self.cpu_usage,
                'memory_usage': self.memory_usage,
                'request_rate': self.request_rate,
                'error_rate': self.error_rate
            },
            'quality': {
                'high_confidence_rate': self.high_confidence_rate,
                'needs_confirmation_rate': self.needs_confirmation_rate,
                'warning_rate': self.warning_rate
            }
        }


@dataclass
class ConfidencePrediction:
    """Confidence prediction for calibration analysis."""
    predicted_confidence: float
    actual_accuracy: float
    timestamp: datetime = field(default_factory=datetime.now)
    text_length: int = 0
    parsing_method: str = "unknown"


class ProductionPerformanceValidator:
    """
    Production performance and accuracy validation system.
    
    Monitors parsing accuracy, component performance, confidence calibration,
    and cache effectiveness in production environment.
    """
    
    def __init__(
        self,
        api_base_url: str = "http://localhost:8000",
        golden_set_path: str = "tests/golden_set.json",
        metrics_history_path: str = "production_metrics_history.json",
        validation_interval: int = 300  # 5 minutes
    ):
        """
        Initialize production validator.
        
        Args:
            api_base_url: Base URL of the production API
            golden_set_path: Path to golden test set
            metrics_history_path: Path to store metrics history
            validation_interval: Validation interval in seconds
        """
        self.api_base_url = api_base_url.rstrip('/')
        self.golden_set_path = Path(golden_set_path)
        self.metrics_history_path = Path(metrics_history_path)
        self.validation_interval = validation_interval
        
        # Metrics storage
        self.metrics_history: List[ProductionMetrics] = []
        self.confidence_predictions: deque = deque(maxlen=10000)  # Keep last 10k predictions
        self.recent_requests: deque = deque(maxlen=1000)  # Keep last 1k requests for analysis
        
        # Golden test set
        self.golden_test_cases = []
        self.load_golden_set()
        
        # Performance tracking
        self.component_latencies = defaultdict(list)
        self.request_latencies = deque(maxlen=1000)
        
        logger.info(f"ProductionPerformanceValidator initialized with {len(self.golden_test_cases)} golden test cases")
    
    def load_golden_set(self):
        """Load golden test set from file."""
        try:
            if self.golden_set_path.exists():
                with open(self.golden_set_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.golden_test_cases = data.get('test_cases', [])
                logger.info(f"Loaded {len(self.golden_test_cases)} golden test cases")
            else:
                logger.warning(f"Golden set file not found: {self.golden_set_path}")
        except Exception as e:
            logger.error(f"Error loading golden set: {e}")
    
    async def validate_golden_set_accuracy(self) -> Dict[str, Any]:
        """
        Validate parsing accuracy against golden test set in production.
        
        Returns:
            Dictionary with accuracy metrics and detailed results
        """
        logger.info("Starting golden set accuracy validation")
        
        if not self.golden_test_cases:
            logger.warning("No golden test cases available for validation")
            return {'error': 'No golden test cases available'}
        
        results = []
        total_accuracy = 0.0
        field_accuracies = defaultdict(list)
        confidence_predictions = []
        
        async with aiohttp.ClientSession() as session:
            for i, test_case in enumerate(self.golden_test_cases):
                try:
                    # Make API request
                    start_time = time.time()
                    
                    payload = {
                        "text": test_case["input_text"],
                        "timezone": "UTC",
                        "locale": "en_US",
                        "use_llm_enhancement": True
                    }
                    
                    async with session.post(
                        f"{self.api_base_url}/parse",
                        json=payload,
                        timeout=aiohttp.ClientTimeout(total=30)
                    ) as response:
                        processing_time_ms = (time.time() - start_time) * 1000
                        
                        if response.status == 200:
                            result = await response.json()
                            
                            # Calculate accuracy
                            accuracy_result = self._calculate_test_case_accuracy(test_case, result)
                            accuracy_result['processing_time_ms'] = processing_time_ms
                            
                            results.append(accuracy_result)
                            total_accuracy += accuracy_result['accuracy_score']
                            
                            # Track field accuracies
                            for field, accuracy in accuracy_result['field_accuracies'].items():
                                field_accuracies[field].append(accuracy)
                            
                            # Track confidence predictions
                            confidence_score = result.get('confidence_score', 0.0)
                            is_accurate = accuracy_result['accuracy_score'] > 0.7
                            confidence_predictions.append((confidence_score, is_accurate))
                            
                            # Store for calibration analysis
                            self.confidence_predictions.append(ConfidencePrediction(
                                predicted_confidence=confidence_score,
                                actual_accuracy=accuracy_result['accuracy_score'],
                                text_length=len(test_case["input_text"]),
                                parsing_method=result.get('parsing_metadata', {}).get('parsing_path', 'unknown')
                            ))
                            
                            logger.debug(f"Test case {test_case['id']}: accuracy={accuracy_result['accuracy_score']:.3f}")
                        else:
                            logger.error(f"API error for test case {test_case['id']}: {response.status}")
                            results.append({
                                'test_case_id': test_case['id'],
                                'accuracy_score': 0.0,
                                'errors': [f"API error: {response.status}"],
                                'processing_time_ms': processing_time_ms
                            })
                
                except Exception as e:
                    logger.error(f"Error validating test case {test_case['id']}: {e}")
                    results.append({
                        'test_case_id': test_case['id'],
                        'accuracy_score': 0.0,
                        'errors': [str(e)],
                        'processing_time_ms': 0.0
                    })
                
                # Progress logging
                if (i + 1) % 10 == 0:
                    logger.info(f"Validated {i + 1}/{len(self.golden_test_cases)} test cases")
        
        # Calculate summary statistics
        overall_accuracy = total_accuracy / len(results) if results else 0.0
        
        field_accuracy_summary = {}
        for field, accuracies in field_accuracies.items():
            if accuracies:
                field_accuracy_summary[field] = {
                    'mean': statistics.mean(accuracies),
                    'median': statistics.median(accuracies),
                    'min': min(accuracies),
                    'max': max(accuracies),
                    'count': len(accuracies)
                }
        
        # Performance statistics
        processing_times = [r.get('processing_time_ms', 0) for r in results if r.get('processing_time_ms', 0) > 0]
        performance_stats = {}
        if processing_times:
            performance_stats = {
                'mean_processing_time_ms': statistics.mean(processing_times),
                'median_processing_time_ms': statistics.median(processing_times),
                'p95_processing_time_ms': np.percentile(processing_times, 95),
                'p99_processing_time_ms': np.percentile(processing_times, 99)
            }
        
        validation_summary = {
            'timestamp': datetime.now().isoformat(),
            'total_test_cases': len(self.golden_test_cases),
            'overall_accuracy': overall_accuracy,
            'field_accuracies': field_accuracy_summary,
            'performance_stats': performance_stats,
            'confidence_predictions': len(confidence_predictions),
            'results': results
        }
        
        logger.info(f"Golden set validation complete: {overall_accuracy:.3f} overall accuracy")
        return validation_summary
    
    def _calculate_test_case_accuracy(self, test_case: Dict[str, Any], api_result: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate accuracy for a single test case."""
        field_accuracies = {}
        errors = []
        
        # Title accuracy
        title_accuracy = 0.0
        predicted_title = api_result.get('title', '')
        expected_title = test_case.get('expected_title', '')
        
        if predicted_title and expected_title:
            predicted_title = predicted_title.lower().strip()
            expected_title = expected_title.lower().strip()
            
            if predicted_title == expected_title:
                title_accuracy = 1.0
            elif expected_title in predicted_title or predicted_title in expected_title:
                title_accuracy = 0.7
            else:
                # Word overlap calculation
                predicted_words = set(predicted_title.split())
                expected_words = set(expected_title.split())
                overlap = len(predicted_words & expected_words)
                total_words = len(predicted_words | expected_words)
                title_accuracy = overlap / total_words if total_words > 0 else 0.0
        
        field_accuracies['title'] = title_accuracy
        if title_accuracy < 0.5:
            errors.append(f"Title mismatch: expected '{expected_title}', got '{predicted_title}'")
        
        # Start datetime accuracy
        start_accuracy = 0.0
        predicted_start = api_result.get('start_datetime')
        expected_start = test_case.get('expected_start')
        
        if predicted_start and expected_start:
            try:
                from datetime import datetime
                if isinstance(predicted_start, str):
                    predicted_dt = datetime.fromisoformat(predicted_start.replace('Z', '+00:00'))
                else:
                    predicted_dt = predicted_start
                
                expected_dt = datetime.fromisoformat(expected_start)
                
                time_diff = abs((predicted_dt - expected_dt).total_seconds())
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
            except Exception as e:
                logger.warning(f"Error comparing start times: {e}")
                start_accuracy = 0.0
        
        field_accuracies['start_datetime'] = start_accuracy
        if start_accuracy < 0.7:
            errors.append(f"Start time mismatch: expected {expected_start}, got {predicted_start}")
        
        # End datetime accuracy
        end_accuracy = 0.0
        predicted_end = api_result.get('end_datetime')
        expected_end = test_case.get('expected_end')
        
        if predicted_end and expected_end:
            try:
                if isinstance(predicted_end, str):
                    predicted_dt = datetime.fromisoformat(predicted_end.replace('Z', '+00:00'))
                else:
                    predicted_dt = predicted_end
                
                expected_dt = datetime.fromisoformat(expected_end)
                
                time_diff = abs((predicted_dt - expected_dt).total_seconds())
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
            except Exception as e:
                logger.warning(f"Error comparing end times: {e}")
                end_accuracy = 0.0
        
        field_accuracies['end_datetime'] = end_accuracy
        if end_accuracy < 0.7:
            errors.append(f"End time mismatch: expected {expected_end}, got {predicted_end}")
        
        # Location accuracy (optional field)
        location_accuracy = 1.0  # Default to perfect if no location expected
        predicted_location = api_result.get('location', '')
        expected_location = test_case.get('expected_location', '')
        
        if expected_location:
            if predicted_location:
                predicted_location = predicted_location.lower().strip()
                expected_location = expected_location.lower().strip()
                
                if predicted_location == expected_location:
                    location_accuracy = 1.0
                elif expected_location in predicted_location or predicted_location in expected_location:
                    location_accuracy = 0.8
                else:
                    location_accuracy = 0.0
            else:
                location_accuracy = 0.0
                errors.append(f"Missing location: expected '{expected_location}'")
        elif predicted_location:
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
        
        return {
            'test_case_id': test_case['id'],
            'accuracy_score': overall_accuracy,
            'field_accuracies': field_accuracies,
            'errors': errors,
            'confidence_score': api_result.get('confidence_score', 0.0)
        }
    
    async def track_component_latency(self) -> Dict[str, Any]:
        """
        Track component latency and overall system performance.
        
        Returns:
            Dictionary with component latency metrics
        """
        logger.info("Tracking component latency")
        
        try:
            async with aiohttp.ClientSession() as session:
                # Get metrics from API
                async with session.get(
                    f"{self.api_base_url}/metrics",
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        metrics_text = await response.text()
                        # Parse Prometheus metrics (simplified)
                        component_metrics = self._parse_prometheus_metrics(metrics_text)
                        
                        # Get health check with performance data
                        async with session.get(
                            f"{self.api_base_url}/healthz",
                            timeout=aiohttp.ClientTimeout(total=10)
                        ) as health_response:
                            if health_response.status == 200:
                                health_data = await health_response.json()
                                
                                # Combine metrics
                                latency_metrics = {
                                    'timestamp': datetime.now().isoformat(),
                                    'component_metrics': component_metrics,
                                    'health_data': health_data,
                                    'system_metrics': self._get_system_metrics()
                                }
                                
                                return latency_metrics
                    
                    logger.warning(f"Failed to get metrics: {response.status}")
                    return {'error': f'Failed to get metrics: {response.status}'}
        
        except Exception as e:
            logger.error(f"Error tracking component latency: {e}")
            return {'error': str(e)}
    
    def _parse_prometheus_metrics(self, metrics_text: str) -> Dict[str, Any]:
        """Parse Prometheus metrics text (simplified parser)."""
        metrics = {}
        
        for line in metrics_text.split('\n'):
            line = line.strip()
            if line and not line.startswith('#'):
                try:
                    # Simple parsing for histogram metrics
                    if '_bucket{' in line or '_count{' in line or '_sum{' in line:
                        parts = line.split(' ')
                        if len(parts) >= 2:
                            metric_name = parts[0].split('{')[0]
                            value = float(parts[1])
                            
                            if metric_name not in metrics:
                                metrics[metric_name] = []
                            metrics[metric_name].append(value)
                except Exception:
                    continue
        
        return metrics
    
    def _get_system_metrics(self) -> Dict[str, float]:
        """Get system performance metrics."""
        try:
            return {
                'cpu_usage_percent': psutil.cpu_percent(interval=1),
                'memory_usage_percent': psutil.virtual_memory().percent,
                'disk_usage_percent': psutil.disk_usage('/').percent,
                'network_io_bytes_sent': psutil.net_io_counters().bytes_sent,
                'network_io_bytes_recv': psutil.net_io_counters().bytes_recv
            }
        except Exception as e:
            logger.warning(f"Error getting system metrics: {e}")
            return {}
    
    async def validate_confidence_calibration(self) -> Dict[str, Any]:
        """
        Validate confidence calibration with real user data.
        
        Returns:
            Dictionary with calibration metrics and reliability data
        """
        logger.info("Validating confidence calibration")
        
        if len(self.confidence_predictions) < 10:
            logger.warning("Insufficient confidence predictions for calibration analysis")
            return {'error': 'Insufficient data for calibration analysis'}
        
        # Convert predictions to lists
        confidences = [pred.predicted_confidence for pred in self.confidence_predictions]
        accuracies = [pred.actual_accuracy for pred in self.confidence_predictions]
        
        # Calculate reliability diagram
        reliability_data = self._calculate_reliability_diagram(confidences, accuracies)
        
        # Calculate Expected Calibration Error (ECE)
        ece = self._calculate_expected_calibration_error(confidences, accuracies)
        
        # Additional calibration metrics
        calibration_metrics = {
            'timestamp': datetime.now().isoformat(),
            'total_predictions': len(self.confidence_predictions),
            'expected_calibration_error': ece,
            'reliability_points': reliability_data,
            'confidence_distribution': self._get_confidence_distribution(confidences),
            'accuracy_by_confidence_bin': self._get_accuracy_by_confidence_bin(confidences, accuracies)
        }
        
        logger.info(f"Confidence calibration validation complete: ECE={ece:.3f}")
        return calibration_metrics
    
    def _calculate_reliability_diagram(self, confidences: List[float], accuracies: List[float]) -> List[Dict[str, Any]]:
        """Calculate reliability diagram points."""
        bins = np.linspace(0, 1, 11)  # 10 bins
        reliability_points = []
        
        for i in range(len(bins) - 1):
            bin_start, bin_end = bins[i], bins[i + 1]
            bin_center = (bin_start + bin_end) / 2
            
            # Find predictions in this bin
            bin_indices = [
                j for j, conf in enumerate(confidences)
                if bin_start <= conf < bin_end
            ]
            
            if bin_indices:
                bin_confidences = [confidences[j] for j in bin_indices]
                bin_accuracies = [accuracies[j] for j in bin_indices]
                
                reliability_points.append({
                    'confidence_bin': bin_center,
                    'predicted_confidence': statistics.mean(bin_confidences),
                    'actual_accuracy': statistics.mean(bin_accuracies),
                    'count': len(bin_indices)
                })
        
        return reliability_points
    
    def _calculate_expected_calibration_error(self, confidences: List[float], accuracies: List[float]) -> float:
        """Calculate Expected Calibration Error (ECE)."""
        bins = np.linspace(0, 1, 11)  # 10 bins
        total_samples = len(confidences)
        ece = 0.0
        
        for i in range(len(bins) - 1):
            bin_start, bin_end = bins[i], bins[i + 1]
            
            # Find predictions in this bin
            bin_indices = [
                j for j, conf in enumerate(confidences)
                if bin_start <= conf < bin_end
            ]
            
            if bin_indices:
                bin_confidences = [confidences[j] for j in bin_indices]
                bin_accuracies = [accuracies[j] for j in bin_indices]
                
                avg_confidence = statistics.mean(bin_confidences)
                avg_accuracy = statistics.mean(bin_accuracies)
                bin_weight = len(bin_indices) / total_samples
                
                ece += bin_weight * abs(avg_confidence - avg_accuracy)
        
        return ece
    
    def _get_confidence_distribution(self, confidences: List[float]) -> Dict[str, int]:
        """Get distribution of confidence scores."""
        distribution = {'low': 0, 'medium': 0, 'high': 0}
        
        for conf in confidences:
            if conf < 0.4:
                distribution['low'] += 1
            elif conf < 0.8:
                distribution['medium'] += 1
            else:
                distribution['high'] += 1
        
        return distribution
    
    def _get_accuracy_by_confidence_bin(self, confidences: List[float], accuracies: List[float]) -> Dict[str, float]:
        """Get average accuracy by confidence bin."""
        bins = {'low': [], 'medium': [], 'high': []}
        
        for conf, acc in zip(confidences, accuracies):
            if conf < 0.4:
                bins['low'].append(acc)
            elif conf < 0.8:
                bins['medium'].append(acc)
            else:
                bins['high'].append(acc)
        
        return {
            bin_name: statistics.mean(accuracies) if accuracies else 0.0
            for bin_name, accuracies in bins.items()
        }
    
    async def monitor_cache_performance(self) -> Dict[str, Any]:
        """
        Monitor cache hit rates and performance improvements.
        
        Returns:
            Dictionary with cache performance metrics
        """
        logger.info("Monitoring cache performance")
        
        try:
            async with aiohttp.ClientSession() as session:
                # Get cache statistics
                async with session.get(
                    f"{self.api_base_url}/cache/stats",
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        cache_stats = await response.json()
                        
                        # Add timestamp and additional analysis
                        cache_performance = {
                            'timestamp': datetime.now().isoformat(),
                            'cache_stats': cache_stats,
                            'performance_analysis': self._analyze_cache_performance(cache_stats)
                        }
                        
                        logger.info(f"Cache hit rate: {cache_stats.get('hit_rate', 0):.2%}")
                        return cache_performance
                    else:
                        logger.warning(f"Failed to get cache stats: {response.status}")
                        return {'error': f'Failed to get cache stats: {response.status}'}
        
        except Exception as e:
            logger.error(f"Error monitoring cache performance: {e}")
            return {'error': str(e)}
    
    def _analyze_cache_performance(self, cache_stats: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze cache performance and provide insights."""
        hit_rate = cache_stats.get('hit_rate', 0.0)
        total_requests = cache_stats.get('cache_hits', 0) + cache_stats.get('cache_misses', 0)
        
        analysis = {
            'performance_grade': 'unknown',
            'recommendations': [],
            'efficiency_metrics': {}
        }
        
        # Performance grading
        if hit_rate >= 0.8:
            analysis['performance_grade'] = 'excellent'
        elif hit_rate >= 0.6:
            analysis['performance_grade'] = 'good'
        elif hit_rate >= 0.4:
            analysis['performance_grade'] = 'fair'
        else:
            analysis['performance_grade'] = 'poor'
            analysis['recommendations'].append('Consider increasing cache TTL or improving cache key strategy')
        
        # Efficiency metrics
        if total_requests > 0:
            analysis['efficiency_metrics'] = {
                'requests_served_from_cache': cache_stats.get('cache_hits', 0),
                'cache_efficiency_ratio': hit_rate,
                'estimated_latency_savings_ms': cache_stats.get('cache_hits', 0) * 500,  # Estimate 500ms saved per hit
                'cache_utilization': cache_stats.get('cache_size', 0) / cache_stats.get('max_cache_size', 1000)
            }
        
        return analysis
    
    async def generate_production_dashboard_report(self) -> Dict[str, Any]:
        """
        Generate comprehensive production performance dashboard report.
        
        Returns:
            Dictionary with complete dashboard data
        """
        logger.info("Generating production dashboard report")
        
        # Collect all metrics
        dashboard_data = {
            'report_timestamp': datetime.now().isoformat(),
            'validation_interval_seconds': self.validation_interval,
            'metrics': {}
        }
        
        try:
            # Golden set accuracy validation
            logger.info("Running golden set accuracy validation...")
            accuracy_results = await self.validate_golden_set_accuracy()
            dashboard_data['metrics']['accuracy'] = accuracy_results
            
            # Component latency tracking
            logger.info("Tracking component latency...")
            latency_results = await self.track_component_latency()
            dashboard_data['metrics']['latency'] = latency_results
            
            # Confidence calibration validation
            logger.info("Validating confidence calibration...")
            calibration_results = await self.validate_confidence_calibration()
            dashboard_data['metrics']['calibration'] = calibration_results
            
            # Cache performance monitoring
            logger.info("Monitoring cache performance...")
            cache_results = await self.monitor_cache_performance()
            dashboard_data['metrics']['cache'] = cache_results
            
            # System health summary
            dashboard_data['summary'] = self._generate_health_summary(dashboard_data['metrics'])
            
            # Store metrics history
            self._store_metrics_history(dashboard_data)
            
            logger.info("Production dashboard report generated successfully")
            return dashboard_data
        
        except Exception as e:
            logger.error(f"Error generating dashboard report: {e}")
            dashboard_data['error'] = str(e)
            return dashboard_data
    
    def _generate_health_summary(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Generate overall health summary from metrics."""
        summary = {
            'overall_status': 'unknown',
            'accuracy_status': 'unknown',
            'performance_status': 'unknown',
            'cache_status': 'unknown',
            'calibration_status': 'unknown',
            'alerts': [],
            'recommendations': []
        }
        
        try:
            # Accuracy status
            accuracy_data = metrics.get('accuracy', {})
            overall_accuracy = accuracy_data.get('overall_accuracy', 0.0)
            
            if overall_accuracy >= 0.8:
                summary['accuracy_status'] = 'excellent'
            elif overall_accuracy >= 0.7:
                summary['accuracy_status'] = 'good'
            elif overall_accuracy >= 0.6:
                summary['accuracy_status'] = 'fair'
            else:
                summary['accuracy_status'] = 'poor'
                summary['alerts'].append(f'Low accuracy: {overall_accuracy:.2%}')
                summary['recommendations'].append('Review golden test set and parsing logic')
            
            # Performance status
            latency_data = metrics.get('latency', {})
            if 'performance_stats' in accuracy_data:
                p95_latency = accuracy_data['performance_stats'].get('p95_processing_time_ms', 0)
                
                if p95_latency <= 1000:  # 1 second
                    summary['performance_status'] = 'excellent'
                elif p95_latency <= 2000:  # 2 seconds
                    summary['performance_status'] = 'good'
                elif p95_latency <= 5000:  # 5 seconds
                    summary['performance_status'] = 'fair'
                else:
                    summary['performance_status'] = 'poor'
                    summary['alerts'].append(f'High latency: {p95_latency:.0f}ms p95')
                    summary['recommendations'].append('Optimize parsing components or increase resources')
            
            # Cache status
            cache_data = metrics.get('cache', {})
            cache_stats = cache_data.get('cache_stats', {})
            hit_rate = cache_stats.get('hit_rate', 0.0)
            
            if hit_rate >= 0.8:
                summary['cache_status'] = 'excellent'
            elif hit_rate >= 0.6:
                summary['cache_status'] = 'good'
            elif hit_rate >= 0.4:
                summary['cache_status'] = 'fair'
            else:
                summary['cache_status'] = 'poor'
                summary['alerts'].append(f'Low cache hit rate: {hit_rate:.2%}')
                summary['recommendations'].append('Review cache configuration and TTL settings')
            
            # Calibration status
            calibration_data = metrics.get('calibration', {})
            ece = calibration_data.get('expected_calibration_error', 1.0)
            
            if ece <= 0.1:
                summary['calibration_status'] = 'excellent'
            elif ece <= 0.2:
                summary['calibration_status'] = 'good'
            elif ece <= 0.3:
                summary['calibration_status'] = 'fair'
            else:
                summary['calibration_status'] = 'poor'
                summary['alerts'].append(f'Poor confidence calibration: ECE={ece:.3f}')
                summary['recommendations'].append('Review confidence scoring algorithm')
            
            # Overall status
            statuses = [
                summary['accuracy_status'],
                summary['performance_status'],
                summary['cache_status'],
                summary['calibration_status']
            ]
            
            if all(status in ['excellent', 'good'] for status in statuses):
                summary['overall_status'] = 'healthy'
            elif any(status == 'poor' for status in statuses):
                summary['overall_status'] = 'critical'
            else:
                summary['overall_status'] = 'warning'
        
        except Exception as e:
            logger.error(f"Error generating health summary: {e}")
            summary['error'] = str(e)
        
        return summary
    
    def _store_metrics_history(self, dashboard_data: Dict[str, Any]):
        """Store metrics history to file."""
        try:
            # Load existing history
            history = []
            if self.metrics_history_path.exists():
                with open(self.metrics_history_path, 'r', encoding='utf-8') as f:
                    history = json.load(f)
            
            # Add new data point
            history.append(dashboard_data)
            
            # Keep only last 1000 data points
            if len(history) > 1000:
                history = history[-1000:]
            
            # Save updated history
            with open(self.metrics_history_path, 'w', encoding='utf-8') as f:
                json.dump(history, f, indent=2, ensure_ascii=False)
            
            logger.debug(f"Stored metrics history: {len(history)} data points")
        
        except Exception as e:
            logger.error(f"Error storing metrics history: {e}")
    
    async def run_continuous_validation(self):
        """Run continuous production validation."""
        logger.info(f"Starting continuous validation with {self.validation_interval}s interval")
        
        while True:
            try:
                # Generate dashboard report
                dashboard_report = await self.generate_production_dashboard_report()
                
                # Log summary
                summary = dashboard_report.get('summary', {})
                overall_status = summary.get('overall_status', 'unknown')
                alerts = summary.get('alerts', [])
                
                logger.info(f"Validation cycle complete - Status: {overall_status}")
                
                if alerts:
                    logger.warning(f"Alerts: {'; '.join(alerts)}")
                
                # Wait for next validation cycle
                await asyncio.sleep(self.validation_interval)
            
            except KeyboardInterrupt:
                logger.info("Continuous validation stopped by user")
                break
            except Exception as e:
                logger.error(f"Error in continuous validation: {e}")
                await asyncio.sleep(60)  # Wait 1 minute before retrying


async def main():
    """Main function for running production validation."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Production Performance and Accuracy Validator')
    parser.add_argument('--api-url', default='http://localhost:8000', help='API base URL')
    parser.add_argument('--golden-set', default='tests/golden_set.json', help='Golden test set path')
    parser.add_argument('--interval', type=int, default=300, help='Validation interval in seconds')
    parser.add_argument('--continuous', action='store_true', help='Run continuous validation')
    parser.add_argument('--single-run', action='store_true', help='Run single validation cycle')
    
    args = parser.parse_args()
    
    # Initialize validator
    validator = ProductionPerformanceValidator(
        api_base_url=args.api_url,
        golden_set_path=args.golden_set,
        validation_interval=args.interval
    )
    
    if args.continuous:
        # Run continuous validation
        await validator.run_continuous_validation()
    elif args.single_run:
        # Run single validation cycle
        dashboard_report = await validator.generate_production_dashboard_report()
        
        # Print summary
        print("\n" + "="*80)
        print("PRODUCTION VALIDATION REPORT")
        print("="*80)
        
        summary = dashboard_report.get('summary', {})
        print(f"Overall Status: {summary.get('overall_status', 'unknown').upper()}")
        print(f"Report Time: {dashboard_report.get('report_timestamp', 'unknown')}")
        
        # Accuracy
        accuracy = dashboard_report.get('metrics', {}).get('accuracy', {})
        print(f"\nAccuracy: {accuracy.get('overall_accuracy', 0):.2%}")
        
        # Performance
        if 'performance_stats' in accuracy:
            perf = accuracy['performance_stats']
            print(f"Performance: {perf.get('p95_processing_time_ms', 0):.0f}ms p95")
        
        # Cache
        cache = dashboard_report.get('metrics', {}).get('cache', {})
        cache_stats = cache.get('cache_stats', {})
        print(f"Cache Hit Rate: {cache_stats.get('hit_rate', 0):.2%}")
        
        # Calibration
        calibration = dashboard_report.get('metrics', {}).get('calibration', {})
        print(f"Calibration ECE: {calibration.get('expected_calibration_error', 0):.3f}")
        
        # Alerts
        alerts = summary.get('alerts', [])
        if alerts:
            print(f"\nAlerts:")
            for alert in alerts:
                print(f"  - {alert}")
        
        # Recommendations
        recommendations = summary.get('recommendations', [])
        if recommendations:
            print(f"\nRecommendations:")
            for rec in recommendations:
                print(f"  - {rec}")
        
        print("="*80)
    else:
        print("Please specify --continuous or --single-run")


if __name__ == "__main__":
    asyncio.run(main())