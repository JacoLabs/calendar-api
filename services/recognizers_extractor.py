"""
Microsoft Recognizers-Text integration for deterministic entity extraction.

This module provides a Python client for Microsoft Recognizers-Text library,
which offers multi-language entity recognition for dates, times, numbers, and other entities.
"""

import time
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any, Tuple
import re

try:
    from recognizers_text import Culture
    from recognizers_date_time import DateTimeRecognizer
    from recognizers_number import NumberRecognizer
    RECOGNIZERS_AVAILABLE = True
except ImportError:
    # Define mock classes when library is not available
    class Culture:
        English = "en-us"
        Spanish = "es-es"
        French = "fr-fr"
        German = "de-de"
        Italian = "it-it"
        Portuguese = "pt-pt"
        Chinese = "zh-cn"
        Japanese = "ja-jp"
        Korean = "ko-kr"
        Dutch = "nl-nl"
        Swedish = "sv-se"
        Turkish = "tr-tr"
    
    class MockModel:
        def parse(self, text):
            return []
    
    class DateTimeRecognizer:
        def get_datetime_model(self, culture):
            return MockModel()
    
    class NumberRecognizer:
        def get_number_model(self, culture, fallback=True):
            return MockModel()
    
    RECOGNIZERS_AVAILABLE = False

from models.event_models import FieldResult


class RecognizersExtractor:
    """
    Client for Microsoft Recognizers-Text entity extraction.
    
    Microsoft Recognizers-Text provides multi-language entity recognition
    for dates, times, numbers, and other structured data types.
    This class provides a unified interface for calendar event parsing.
    
    Requirements addressed:
    - 11.1: Deterministic backup parsing when regex fails
    - 11.2: Multi-language entity recognition for dates, times, numbers
    - 11.4: Confidence scoring for deterministic results (0.6-0.8 range)
    """
    
    def __init__(self, 
                 default_culture: str = Culture.English,
                 default_timezone: str = "UTC"):
        """
        Initialize Recognizers extractor.
        
        Args:
            default_culture: Default culture for recognition (e.g., Culture.English)
            default_timezone: Default timezone for parsing
        """
        self.default_culture = default_culture
        self.default_timezone = default_timezone
        self._datetime_recognizer = None
        self._number_recognizer = None
        self._service_available = RECOGNIZERS_AVAILABLE
        
        # Initialize recognizers if available
        if self._service_available:
            try:
                self._datetime_recognizer = DateTimeRecognizer()
                self._number_recognizer = NumberRecognizer()
            except Exception:
                self._service_available = False
    
    def is_service_available(self) -> bool:
        """
        Check if Microsoft Recognizers-Text is available.
        
        Returns:
            True if library is available and functional, False otherwise
        """
        return self._service_available and self._datetime_recognizer is not None
    
    def extract_with_recognizers(self, text: str, field: str = "time") -> FieldResult:
        """
        Extract entities using Microsoft Recognizers-Text.
        
        Args:
            text: Input text to parse
            field: Field type to extract ("time", "date", "datetime", "number", "duration")
            
        Returns:
            FieldResult with extracted value and metadata
            
        Requirements:
        - 11.1: Provides deterministic backup when regex fails
        - 11.2: Multi-language entity recognition
        - 11.4: Returns confidence in 0.6-0.8 range
        """
        start_time = time.time()
        
        # Check service availability
        if not self.is_service_available():
            processing_time_ms = max(1, int((time.time() - start_time) * 1000))
            return FieldResult(
                value=None,
                source="recognizers",
                confidence=0.0,
                span=(0, 0),
                alternatives=[],
                processing_time_ms=processing_time_ms
            )
        
        try:
            # Route to appropriate recognizer based on field type
            if field in ["time", "date", "datetime", "start_datetime", "end_datetime", "duration"]:
                return self._extract_datetime(text, field, start_time)
            elif field == "number":
                return self._extract_number(text, field, start_time)
            else:
                # Unsupported field type
                processing_time_ms = max(1, int((time.time() - start_time) * 1000))
                return FieldResult(
                    value=None,
                    source="recognizers",
                    confidence=0.0,
                    span=(0, 0),
                    alternatives=[],
                    processing_time_ms=processing_time_ms
                )
                
        except Exception as e:
            processing_time_ms = max(1, int((time.time() - start_time) * 1000))
            return FieldResult(
                value=None,
                source="recognizers",
                confidence=0.0,
                span=(0, 0),
                alternatives=[],
                processing_time_ms=processing_time_ms
            )
    
    def _extract_datetime(self, text: str, field: str, start_time: float) -> FieldResult:
        """
        Extract datetime entities using DateTimeRecognizer.
        
        Args:
            text: Input text
            field: Field type
            start_time: Processing start time
            
        Returns:
            FieldResult with datetime extraction
        """
        try:
            # Use DateTimeRecognizer to extract datetime entities
            model = self._datetime_recognizer.get_datetime_model(self.default_culture)
            results = model.parse(text)
            
            processing_time_ms = max(1, int((time.time() - start_time) * 1000))
            
            if not results:
                return FieldResult(
                    value=None,
                    source="recognizers",
                    confidence=0.0,
                    span=(0, 0),
                    alternatives=[],
                    processing_time_ms=processing_time_ms
                )
            
            # Select the best result
            best_result = self._select_best_datetime_result(results, field)
            
            if not best_result:
                return FieldResult(
                    value=None,
                    source="recognizers",
                    confidence=0.0,
                    span=(0, 0),
                    alternatives=[],
                    processing_time_ms=processing_time_ms
                )
            
            # Extract datetime value
            extracted_value = self._extract_datetime_value(best_result, field)
            confidence = self._calculate_datetime_confidence(best_result, text)
            span = (best_result.start, best_result.end)
            
            # Get alternatives
            alternatives = []
            for result in results[1:6]:  # Up to 5 alternatives
                if result != best_result:
                    alt_value = self._extract_datetime_value(result, field)
                    if alt_value and alt_value != extracted_value:
                        alternatives.append(alt_value)
            
            return FieldResult(
                value=extracted_value,
                source="recognizers",
                confidence=confidence,
                span=span,
                alternatives=alternatives,
                processing_time_ms=processing_time_ms
            )
            
        except Exception as e:
            processing_time_ms = max(1, int((time.time() - start_time) * 1000))
            return FieldResult(
                value=None,
                source="recognizers",
                confidence=0.0,
                span=(0, 0),
                alternatives=[],
                processing_time_ms=processing_time_ms
            )
    
    def _extract_number(self, text: str, field: str, start_time: float) -> FieldResult:
        """
        Extract number entities using NumberRecognizer.
        
        Args:
            text: Input text
            field: Field type
            start_time: Processing start time
            
        Returns:
            FieldResult with number extraction
        """
        try:
            # Use NumberRecognizer to extract number entities
            model = self._number_recognizer.get_number_model(self.default_culture, True)
            results = model.parse(text)
            
            processing_time_ms = max(1, int((time.time() - start_time) * 1000))
            
            if not results:
                return FieldResult(
                    value=None,
                    source="recognizers",
                    confidence=0.0,
                    span=(0, 0),
                    alternatives=[],
                    processing_time_ms=processing_time_ms
                )
            
            # Select the best result (first one for numbers)
            best_result = results[0]
            
            # Extract number value
            extracted_value = self._extract_number_value(best_result)
            confidence = self._calculate_number_confidence(best_result, text)
            span = (best_result.start, best_result.end)
            
            # Get alternatives
            alternatives = []
            for result in results[1:6]:  # Up to 5 alternatives
                alt_value = self._extract_number_value(result)
                if alt_value is not None and alt_value != extracted_value:
                    alternatives.append(alt_value)
            
            return FieldResult(
                value=extracted_value,
                source="recognizers",
                confidence=confidence,
                span=span,
                alternatives=alternatives,
                processing_time_ms=processing_time_ms
            )
            
        except Exception as e:
            processing_time_ms = max(1, int((time.time() - start_time) * 1000))
            return FieldResult(
                value=None,
                source="recognizers",
                confidence=0.0,
                span=(0, 0),
                alternatives=[],
                processing_time_ms=processing_time_ms
            )
    
    def _select_best_datetime_result(self, results: List[Any], field: str) -> Optional[Any]:
        """
        Select the best datetime result from Recognizers results.
        
        Args:
            results: List of recognition results
            field: Target field type
            
        Returns:
            Best result or None
        """
        if not results:
            return None
        
        # Filter results by type relevance
        relevant_results = []
        
        for result in results:
            type_name = result.type_name.lower() if hasattr(result, 'type_name') else ""
            
            # Check if result type matches field requirements
            if field in ["time", "start_datetime", "end_datetime"]:
                if any(keyword in type_name for keyword in ["time", "datetime", "date"]):
                    relevant_results.append(result)
            elif field == "date":
                if any(keyword in type_name for keyword in ["date", "datetime"]):
                    relevant_results.append(result)
            elif field == "duration":
                if any(keyword in type_name for keyword in ["duration", "timespan"]):
                    relevant_results.append(result)
            else:
                relevant_results.append(result)  # Include all for generic datetime
        
        if not relevant_results:
            relevant_results = results  # Fall back to all results
        
        # Sort by span length (prefer shorter, more specific spans) and position
        def result_score(result):
            span_length = result.end - result.start
            position = result.start
            # Prefer shorter spans and earlier positions
            return (span_length, position)
        
        sorted_results = sorted(relevant_results, key=result_score)
        return sorted_results[0]
    
    def _extract_datetime_value(self, result: Any, field: str) -> Optional[datetime]:
        """
        Extract datetime value from a Recognizers result.
        
        Args:
            result: Recognition result
            field: Target field type
            
        Returns:
            Extracted datetime or None
        """
        try:
            if not hasattr(result, 'resolution') or not result.resolution:
                return None
            
            resolution = result.resolution
            values = resolution.get('values', [])
            
            if not values:
                return None
            
            # Get the first value (most likely interpretation)
            value_data = values[0]
            
            # Handle different value types
            if 'value' in value_data:
                # Single datetime value
                datetime_str = value_data['value']
                return self._parse_datetime_string(datetime_str)
            
            elif 'start' in value_data and 'end' in value_data:
                # Time range - return start or end based on field
                if field == "end_datetime":
                    datetime_str = value_data['end']
                else:
                    datetime_str = value_data['start']
                return self._parse_datetime_string(datetime_str)
            
            elif 'start' in value_data:
                # Open-ended range
                datetime_str = value_data['start']
                return self._parse_datetime_string(datetime_str)
            
            return None
            
        except (KeyError, ValueError, TypeError, AttributeError):
            return None
    
    def _extract_number_value(self, result: Any) -> Optional[float]:
        """
        Extract number value from a Recognizers result.
        
        Args:
            result: Recognition result
            
        Returns:
            Extracted number or None
        """
        try:
            if not hasattr(result, 'resolution') or not result.resolution:
                return None
            
            resolution = result.resolution
            value = resolution.get('value')
            
            if value is not None:
                return float(value)
            
            return None
            
        except (KeyError, ValueError, TypeError, AttributeError):
            return None
    
    def _parse_datetime_string(self, datetime_str: str) -> Optional[datetime]:
        """
        Parse datetime string from Recognizers output.
        
        Args:
            datetime_str: Datetime string from Recognizers
            
        Returns:
            Parsed datetime or None
        """
        try:
            # Handle various datetime formats from Recognizers
            
            # ISO format with timezone
            if 'T' in datetime_str and ('+' in datetime_str or 'Z' in datetime_str):
                return datetime.fromisoformat(datetime_str.replace('Z', '+00:00'))
            
            # ISO format without timezone
            elif 'T' in datetime_str:
                dt = datetime.fromisoformat(datetime_str)
                # Assume UTC if no timezone
                return dt.replace(tzinfo=timezone.utc)
            
            # Date only format (YYYY-MM-DD)
            elif re.match(r'^\d{4}-\d{2}-\d{2}$', datetime_str):
                dt = datetime.strptime(datetime_str, '%Y-%m-%d')
                return dt.replace(tzinfo=timezone.utc)
            
            # Time only format (HH:MM:SS or HH:MM)
            elif re.match(r'^\d{1,2}:\d{2}(:\d{2})?$', datetime_str):
                # For time-only, use today's date
                today = datetime.now(timezone.utc).date()
                if ':' in datetime_str and datetime_str.count(':') == 2:
                    time_part = datetime.strptime(datetime_str, '%H:%M:%S').time()
                else:
                    time_part = datetime.strptime(datetime_str, '%H:%M').time()
                return datetime.combine(today, time_part, tzinfo=timezone.utc)
            
            # Try generic parsing as fallback
            else:
                # Attempt to parse with common formats
                formats = [
                    '%Y-%m-%d %H:%M:%S',
                    '%Y-%m-%d %H:%M',
                    '%m/%d/%Y %H:%M:%S',
                    '%m/%d/%Y %H:%M',
                    '%d/%m/%Y %H:%M:%S',
                    '%d/%m/%Y %H:%M'
                ]
                
                for fmt in formats:
                    try:
                        dt = datetime.strptime(datetime_str, fmt)
                        return dt.replace(tzinfo=timezone.utc)
                    except ValueError:
                        continue
            
            return None
            
        except (ValueError, TypeError):
            return None
    
    def _calculate_datetime_confidence(self, result: Any, original_text: str) -> float:
        """
        Calculate confidence score for datetime extraction.
        
        Args:
            result: Recognition result
            original_text: Original input text
            
        Returns:
            Confidence score between 0.6 and 0.8 (deterministic backup range)
            
        Requirements:
        - 11.4: Confidence scoring for Recognizers results (0.6-0.8 range)
        """
        base_confidence = 0.7  # Base confidence for deterministic parsing
        
        # Factors that influence confidence
        confidence_factors = []
        
        # 1. Span coverage (how much of the text is covered)
        span_length = result.end - result.start
        text_length = len(original_text.strip())
        
        if text_length > 0:
            coverage_ratio = span_length / text_length
            # Higher coverage generally means better match
            coverage_factor = min(1.0, coverage_ratio * 1.5)  # Cap at 1.0
            confidence_factors.append(coverage_factor)
        
        # 2. Resolution completeness
        resolution_factor = 0.5
        if hasattr(result, 'resolution') and result.resolution:
            values = result.resolution.get('values', [])
            if values:
                value_data = values[0]
                if 'value' in value_data:
                    resolution_factor = 1.0  # Complete datetime
                elif 'start' in value_data and 'end' in value_data:
                    resolution_factor = 0.9  # Time range
                elif 'start' in value_data:
                    resolution_factor = 0.7  # Open range
        
        confidence_factors.append(resolution_factor)
        
        # 3. Type specificity
        type_factor = 0.7
        if hasattr(result, 'type_name'):
            type_name = result.type_name.lower()
            if 'datetime' in type_name:
                type_factor = 1.0
            elif 'date' in type_name or 'time' in type_name:
                type_factor = 0.8
            elif 'duration' in type_name:
                type_factor = 0.7
        
        confidence_factors.append(type_factor)
        
        # Calculate weighted average
        if confidence_factors:
            avg_factor = sum(confidence_factors) / len(confidence_factors)
            # Adjust base confidence by average factor
            final_confidence = base_confidence * (0.7 + 0.3 * avg_factor)
        else:
            final_confidence = base_confidence
        
        # Ensure confidence is within deterministic backup range (0.6-0.8)
        return max(0.6, min(0.8, final_confidence))
    
    def _calculate_number_confidence(self, result: Any, original_text: str) -> float:
        """
        Calculate confidence score for number extraction.
        
        Args:
            result: Recognition result
            original_text: Original input text
            
        Returns:
            Confidence score between 0.6 and 0.8
        """
        base_confidence = 0.75  # Slightly higher for numbers (usually more reliable)
        
        # Span coverage factor
        span_length = result.end - result.start
        text_length = len(original_text.strip())
        
        coverage_factor = 1.0
        if text_length > 0:
            coverage_ratio = span_length / text_length
            coverage_factor = min(1.0, coverage_ratio * 2.0)
        
        # Resolution quality factor
        resolution_factor = 0.8
        if hasattr(result, 'resolution') and result.resolution:
            if 'value' in result.resolution:
                resolution_factor = 1.0
        
        # Calculate final confidence
        avg_factor = (coverage_factor + resolution_factor) / 2.0
        final_confidence = base_confidence * (0.8 + 0.2 * avg_factor)
        
        # Ensure confidence is within deterministic backup range (0.6-0.8)
        return max(0.6, min(0.8, final_confidence))
    
    def validate_span(self, text: str, span: Tuple[int, int]) -> bool:
        """
        Validate that a span is within text boundaries and reasonable.
        
        Args:
            text: Original text
            span: Character span (start, end)
            
        Returns:
            True if span is valid, False otherwise
        """
        start, end = span
        
        # Check boundaries
        if start < 0 or end > len(text) or start >= end:
            return False
        
        # Check that span contains meaningful content
        span_text = text[start:end].strip()
        if not span_text:
            return False
        
        # Check span length is reasonable (not too short or too long)
        span_length = end - start
        if span_length < 1 or span_length > len(text):
            return False
        
        return True
    
    def extract_multiple_fields(self, text: str, fields: List[str]) -> Dict[str, FieldResult]:
        """
        Extract multiple fields from text efficiently.
        
        Args:
            text: Input text
            fields: List of field names to extract
            
        Returns:
            Dictionary mapping field names to FieldResults
        """
        results = {}
        
        # Group fields by recognizer type for efficiency
        datetime_fields = [f for f in fields if f in ["time", "date", "datetime", "start_datetime", "end_datetime", "duration"]]
        number_fields = [f for f in fields if f == "number"]
        
        # Extract datetime fields
        if datetime_fields:
            # Run datetime recognition once and reuse results
            if self.is_service_available():
                try:
                    model = self._datetime_recognizer.get_datetime_model(self.default_culture)
                    datetime_results = model.parse(text)
                    
                    for field in datetime_fields:
                        start_time = time.time()
                        
                        # Select best result for this field
                        best_result = self._select_best_datetime_result(datetime_results, field)
                        
                        if best_result:
                            extracted_value = self._extract_datetime_value(best_result, field)
                            confidence = self._calculate_datetime_confidence(best_result, text)
                            span = (best_result.start, best_result.end)
                            
                            # Get alternatives
                            alternatives = []
                            for result in datetime_results[1:6]:
                                if result != best_result:
                                    alt_value = self._extract_datetime_value(result, field)
                                    if alt_value and alt_value != extracted_value:
                                        alternatives.append(alt_value)
                            
                            processing_time_ms = max(1, int((time.time() - start_time) * 1000))
                            
                            results[field] = FieldResult(
                                value=extracted_value,
                                source="recognizers",
                                confidence=confidence,
                                span=span,
                                alternatives=alternatives,
                                processing_time_ms=processing_time_ms
                            )
                        else:
                            processing_time_ms = max(1, int((time.time() - start_time) * 1000))
                            results[field] = FieldResult(
                                value=None,
                                source="recognizers",
                                confidence=0.0,
                                span=(0, 0),
                                alternatives=[],
                                processing_time_ms=processing_time_ms
                            )
                
                except Exception:
                    # Fall back to individual extraction
                    for field in datetime_fields:
                        results[field] = self.extract_with_recognizers(text, field)
            else:
                # Service not available
                for field in datetime_fields:
                    results[field] = FieldResult(
                        value=None,
                        source="recognizers",
                        confidence=0.0,
                        span=(0, 0),
                        alternatives=[],
                        processing_time_ms=1
                    )
        
        # Extract number fields
        for field in number_fields:
            results[field] = self.extract_with_recognizers(text, field)
        
        return results
    
    def get_supported_cultures(self) -> List[str]:
        """
        Get list of supported cultures/languages.
        
        Returns:
            List of supported culture codes
        """
        if not RECOGNIZERS_AVAILABLE:
            return []
        
        # Common cultures supported by Microsoft Recognizers
        return [
            Culture.English,
            Culture.Spanish,
            Culture.French,
            Culture.Italian,
            Culture.Portuguese,
            Culture.Chinese,
            Culture.Japanese,
            Culture.Korean,
            Culture.Dutch,
            Culture.Turkish
        ]
    
    def set_culture(self, culture: str):
        """
        Set the culture for recognition.
        
        Args:
            culture: Culture code (e.g., Culture.English)
        """
        if culture in self.get_supported_cultures():
            self.default_culture = culture