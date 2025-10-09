"""
Deterministic backup layer for coordinating Duckling and Microsoft Recognizers-Text.

This module provides a unified interface for deterministic parsing methods,
coordinating between Duckling and Microsoft Recognizers-Text to provide
reliable fallback options when regex parsing fails.
"""

import time
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Tuple
import hashlib

from models.event_models import FieldResult
from services.duckling_extractor import DucklingExtractor
from services.recognizers_extractor import RecognizersExtractor


class DeterministicBackupLayer:
    """
    Coordinates deterministic parsing methods (Duckling and Microsoft Recognizers-Text).
    
    This class provides a unified interface for deterministic backup parsing,
    implementing intelligent coordination between multiple deterministic parsers
    to provide the best possible results when regex parsing fails.
    
    Requirements addressed:
    - 11.2: Coordinate Duckling and Recognizers for deterministic backup
    - 11.3: Timezone validation and normalization for datetime results
    - 11.5: Fallback logic when deterministic methods fail
    """
    
    def __init__(self, 
                 duckling_url: str = "http://localhost:8000/parse",
                 default_timezone: str = "UTC",
                 timeout_seconds: int = 3):
        """
        Initialize deterministic backup layer.
        
        Args:
            duckling_url: URL of the Duckling service endpoint
            default_timezone: Default timezone for parsing
            timeout_seconds: Request timeout in seconds
        """
        self.default_timezone = default_timezone
        self.timeout_seconds = timeout_seconds
        
        # Initialize extractors
        self.duckling_extractor = DucklingExtractor(
            duckling_url=duckling_url,
            timeout_seconds=timeout_seconds,
            default_timezone=default_timezone
        )
        
        self.recognizers_extractor = RecognizersExtractor(
            default_timezone=default_timezone
        )
        
        # Performance tracking
        self._performance_stats = {
            'duckling_calls': 0,
            'recognizers_calls': 0,
            'successful_extractions': 0,
            'failed_extractions': 0,
            'avg_processing_time_ms': 0.0
        }
    
    def extract_with_backup(self, text: str, field: str = "time") -> FieldResult:
        """
        Extract entities using deterministic backup methods.
        
        Coordinates between Duckling and Microsoft Recognizers-Text to provide
        the best possible deterministic extraction result.
        
        Args:
            text: Input text to parse
            field: Field type to extract ("time", "date", "datetime", etc.)
            
        Returns:
            FieldResult with best deterministic extraction result
            
        Requirements:
        - 11.2: Coordinate multiple deterministic parsers
        - 11.3: Validate timezone normalization
        - 11.5: Implement fallback logic when methods fail
        """
        start_time = time.time()
        
        try:
            # Get results from both extractors
            candidates = []
            
            # Try Duckling extraction
            if self.duckling_extractor.is_service_available():
                self._performance_stats['duckling_calls'] += 1
                duckling_result = self.duckling_extractor.extract_with_duckling(text, field)
                if duckling_result.value is not None:
                    candidates.append(duckling_result)
            
            # Try Microsoft Recognizers extraction
            if self.recognizers_extractor.is_service_available():
                self._performance_stats['recognizers_calls'] += 1
                recognizers_result = self.recognizers_extractor.extract_with_recognizers(text, field)
                if recognizers_result.value is not None:
                    candidates.append(recognizers_result)
            
            processing_time_ms = max(1, int((time.time() - start_time) * 1000))
            
            # If no candidates found, return empty result
            if not candidates:
                self._performance_stats['failed_extractions'] += 1
                return FieldResult(
                    value=None,
                    source="deterministic_backup",
                    confidence=0.0,
                    span=(0, 0),
                    alternatives=[],
                    processing_time_ms=processing_time_ms
                )
            
            # Choose the best candidate
            best_result = self.choose_best_span(candidates, text, field)
            
            # Validate timezone normalization for datetime fields
            if field in ["time", "date", "datetime", "start_datetime", "end_datetime"]:
                if not self.validate_timezone_normalization(best_result):
                    # Try to normalize the timezone
                    if isinstance(best_result.value, datetime):
                        normalized_dt = self._normalize_datetime_timezone(best_result.value)
                        best_result = FieldResult(
                            value=normalized_dt,
                            source=best_result.source,
                            confidence=best_result.confidence * 0.9,  # Slight penalty for normalization
                            span=best_result.span,
                            alternatives=best_result.alternatives,
                            processing_time_ms=best_result.processing_time_ms
                        )
            
            # Update source to indicate backup layer coordination
            best_result.source = f"deterministic_backup_{best_result.source}"
            best_result.processing_time_ms = processing_time_ms
            
            # Update performance stats
            self._performance_stats['successful_extractions'] += 1
            self._update_avg_processing_time(processing_time_ms)
            
            return best_result
            
        except Exception as e:
            processing_time_ms = max(1, int((time.time() - start_time) * 1000))
            self._performance_stats['failed_extractions'] += 1
            
            return FieldResult(
                value=None,
                source="deterministic_backup",
                confidence=0.0,
                span=(0, 0),
                alternatives=[],
                processing_time_ms=processing_time_ms
            )
    
    def choose_best_span(self, candidates: List[FieldResult], text: str, field: str) -> FieldResult:
        """
        Select the best span from multiple deterministic extraction candidates.
        
        Implements intelligent selection logic to choose the most reliable
        extraction result from multiple deterministic parsers.
        
        Args:
            candidates: List of FieldResult candidates from different extractors
            text: Original input text
            field: Target field type
            
        Returns:
            Best FieldResult candidate
            
        Requirements:
        - 11.2: Choose shortest valid span when multiple deterministic methods succeed
        """
        if not candidates:
            return FieldResult(
                value=None,
                source="deterministic_backup",
                confidence=0.0,
                span=(0, 0),
                alternatives=[],
                processing_time_ms=0
            )
        
        if len(candidates) == 1:
            return candidates[0]
        
        # Score each candidate based on multiple factors
        scored_candidates = []
        
        for candidate in candidates:
            score = self._calculate_candidate_score(candidate, text, field)
            scored_candidates.append((score, candidate))
        
        # Sort by score (highest first)
        scored_candidates.sort(key=lambda x: x[0], reverse=True)
        
        # Get the best candidate
        best_candidate = scored_candidates[0][1]
        
        # Collect alternatives from other candidates
        alternatives = []
        for _, candidate in scored_candidates[1:]:
            if candidate.value != best_candidate.value:
                alternatives.append(candidate.value)
        
        # Add alternatives from the best candidate
        alternatives.extend(best_candidate.alternatives)
        
        # Remove duplicates while preserving order
        unique_alternatives = []
        seen = set()
        for alt in alternatives:
            alt_key = str(alt)
            if alt_key not in seen:
                unique_alternatives.append(alt)
                seen.add(alt_key)
        
        # Return enhanced best candidate
        return FieldResult(
            value=best_candidate.value,
            source=best_candidate.source,
            confidence=best_candidate.confidence,
            span=best_candidate.span,
            alternatives=unique_alternatives[:5],  # Limit to 5 alternatives
            processing_time_ms=best_candidate.processing_time_ms
        )
    
    def _calculate_candidate_score(self, candidate: FieldResult, text: str, field: str) -> float:
        """
        Calculate a score for a candidate extraction result.
        
        Args:
            candidate: FieldResult to score
            text: Original input text
            field: Target field type
            
        Returns:
            Score for the candidate (higher is better)
        """
        if candidate.value is None:
            return 0.0
        
        score_factors = []
        
        # 1. Base confidence score (40% weight)
        confidence_score = candidate.confidence
        score_factors.append(('confidence', confidence_score, 0.4))
        
        # 2. Span quality score (30% weight)
        span_score = self._calculate_span_score(candidate.span, text)
        score_factors.append(('span', span_score, 0.3))
        
        # 3. Source reliability score (20% weight)
        source_score = self._calculate_source_score(candidate.source)
        score_factors.append(('source', source_score, 0.2))
        
        # 4. Value quality score (10% weight)
        value_score = self._calculate_value_score(candidate.value, field)
        score_factors.append(('value', value_score, 0.1))
        
        # Calculate weighted average
        total_score = sum(score * weight for _, score, weight in score_factors)
        
        return total_score
    
    def _calculate_span_score(self, span: Tuple[int, int], text: str) -> float:
        """
        Calculate score based on span characteristics.
        
        Args:
            span: Character span (start, end)
            text: Original text
            
        Returns:
            Span quality score (0.0 to 1.0)
        """
        start, end = span
        
        if start < 0 or end > len(text) or start >= end:
            return 0.0
        
        span_length = end - start
        text_length = len(text.strip())
        
        if text_length == 0:
            return 0.0
        
        # Prefer shorter spans (more specific)
        # But not too short (at least 2 characters for meaningful content)
        if span_length < 2:
            return 0.1
        elif span_length <= 10:
            return 1.0  # Optimal range
        elif span_length <= 20:
            return 0.8
        elif span_length <= text_length * 0.5:
            return 0.6
        else:
            return 0.3  # Very long spans are less reliable
    
    def _calculate_source_score(self, source: str) -> float:
        """
        Calculate score based on extraction source reliability.
        
        Args:
            source: Source identifier
            
        Returns:
            Source reliability score (0.0 to 1.0)
        """
        # Duckling tends to be more reliable for datetime extraction
        if 'duckling' in source.lower():
            return 1.0
        elif 'recognizers' in source.lower():
            return 0.8
        else:
            return 0.5
    
    def _calculate_value_score(self, value: Any, field: str) -> float:
        """
        Calculate score based on extracted value quality.
        
        Args:
            value: Extracted value
            field: Target field type
            
        Returns:
            Value quality score (0.0 to 1.0)
        """
        if value is None:
            return 0.0
        
        if field in ["time", "date", "datetime", "start_datetime", "end_datetime"]:
            if isinstance(value, datetime):
                # Check if datetime is reasonable
                now = datetime.now(timezone.utc)
                
                # Should be within reasonable range (past 1 year to future 2 years)
                min_date = now.replace(year=now.year - 1)
                max_date = now.replace(year=now.year + 2)
                
                if min_date <= value <= max_date:
                    return 1.0
                elif value > max_date:
                    # Future dates are less reliable but possible
                    return 0.7
                else:
                    # Very old dates are suspicious
                    return 0.3
            else:
                return 0.5  # Non-datetime value for datetime field
        
        elif field == "number":
            if isinstance(value, (int, float)):
                # Reasonable number range
                if 0 <= value <= 10000:
                    return 1.0
                else:
                    return 0.7
            else:
                return 0.5
        
        else:
            # Generic field - just check if value exists
            return 1.0 if value else 0.0
    
    def validate_timezone_normalization(self, datetime_result: FieldResult) -> bool:
        """
        Validate that datetime results have proper timezone information.
        
        Args:
            datetime_result: FieldResult containing datetime value
            
        Returns:
            True if timezone is properly normalized, False otherwise
            
        Requirements:
        - 11.3: Timezone validation and normalization for datetime results
        """
        if not datetime_result.value or not isinstance(datetime_result.value, datetime):
            return True  # Non-datetime values don't need timezone validation
        
        dt = datetime_result.value
        
        # Check if datetime has timezone info
        if dt.tzinfo is None:
            return False
        
        try:
            # Check if timezone is valid
            tz_name = dt.tzinfo.tzname(dt)
            if tz_name is None:
                return False
            
            # Ensure it's a reasonable timezone offset (-12 to +14 hours)
            offset = dt.utcoffset()
            if offset is None:
                return False
            
            offset_hours = offset.total_seconds() / 3600
            if not (-12 <= offset_hours <= 14):
                return False
            
            return True
            
        except (AttributeError, TypeError, ValueError):
            return False
    
    def _normalize_datetime_timezone(self, dt: datetime) -> datetime:
        """
        Normalize datetime to have proper timezone information.
        
        Args:
            dt: Input datetime
            
        Returns:
            Normalized datetime with proper timezone
        """
        # If datetime is naive, assume it's in the default timezone
        if dt.tzinfo is None:
            if self.default_timezone == "UTC":
                return dt.replace(tzinfo=timezone.utc)
            else:
                # For simplicity, treat as UTC if no specific timezone handling
                return dt.replace(tzinfo=timezone.utc)
        
        # If datetime has timezone but it's not UTC and we want UTC
        if self.default_timezone == "UTC" and dt.tzinfo != timezone.utc:
            return dt.astimezone(timezone.utc)
        
        return dt
    
    def extract_multiple_fields(self, text: str, fields: List[str]) -> Dict[str, FieldResult]:
        """
        Extract multiple fields from text using deterministic backup methods.
        
        Args:
            text: Input text
            fields: List of field names to extract
            
        Returns:
            Dictionary mapping field names to FieldResults
        """
        results = {}
        
        # Extract each field individually
        for field in fields:
            results[field] = self.extract_with_backup(text, field)
        
        return results
    
    def is_available(self) -> bool:
        """
        Check if any deterministic backup services are available.
        
        Returns:
            True if at least one service is available, False otherwise
        """
        return (self.duckling_extractor.is_service_available() or 
                self.recognizers_extractor.is_service_available())
    
    def get_service_status(self) -> Dict[str, bool]:
        """
        Get status of all deterministic backup services.
        
        Returns:
            Dictionary mapping service names to availability status
        """
        return {
            'duckling': self.duckling_extractor.is_service_available(),
            'recognizers': self.recognizers_extractor.is_service_available(),
            'overall': self.is_available()
        }
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """
        Get performance statistics for the backup layer.
        
        Returns:
            Dictionary with performance metrics
        """
        total_calls = self._performance_stats['duckling_calls'] + self._performance_stats['recognizers_calls']
        success_rate = 0.0
        
        if total_calls > 0:
            success_rate = self._performance_stats['successful_extractions'] / total_calls
        
        return {
            'total_calls': total_calls,
            'duckling_calls': self._performance_stats['duckling_calls'],
            'recognizers_calls': self._performance_stats['recognizers_calls'],
            'successful_extractions': self._performance_stats['successful_extractions'],
            'failed_extractions': self._performance_stats['failed_extractions'],
            'success_rate': success_rate,
            'avg_processing_time_ms': self._performance_stats['avg_processing_time_ms']
        }
    
    def _update_avg_processing_time(self, processing_time_ms: int):
        """
        Update the average processing time with a new measurement.
        
        Args:
            processing_time_ms: New processing time measurement
        """
        current_avg = self._performance_stats['avg_processing_time_ms']
        total_successful = self._performance_stats['successful_extractions']
        
        if total_successful <= 1:
            self._performance_stats['avg_processing_time_ms'] = processing_time_ms
        else:
            # Calculate running average
            new_avg = ((current_avg * (total_successful - 1)) + processing_time_ms) / total_successful
            self._performance_stats['avg_processing_time_ms'] = new_avg
    
    def reset_performance_stats(self):
        """Reset performance statistics."""
        self._performance_stats = {
            'duckling_calls': 0,
            'recognizers_calls': 0,
            'successful_extractions': 0,
            'failed_extractions': 0,
            'avg_processing_time_ms': 0.0
        }
    
    def create_fallback_result(self, text: str, field: str, processing_time_ms: int = 0) -> FieldResult:
        """
        Create a fallback result when all deterministic methods fail.
        
        Args:
            text: Original input text
            field: Target field type
            processing_time_ms: Processing time for the failed attempt
            
        Returns:
            FieldResult indicating failure with appropriate metadata
            
        Requirements:
        - 11.5: Fallback logic when deterministic methods fail
        """
        return FieldResult(
            value=None,
            source="deterministic_backup_failed",
            confidence=0.0,
            span=(0, 0),
            alternatives=[],
            processing_time_ms=processing_time_ms
        )
    
    def get_text_hash(self, text: str) -> str:
        """
        Generate a hash for text to support caching.
        
        Args:
            text: Input text
            
        Returns:
            SHA-256 hash of the normalized text
        """
        # Normalize text for consistent hashing
        normalized_text = text.strip().lower()
        return hashlib.sha256(normalized_text.encode('utf-8')).hexdigest()[:16]