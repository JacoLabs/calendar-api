"""
Duckling parser integration for deterministic date/time entity extraction.

This module provides a Python client for the Duckling Haskell service,
which offers robust rule-based parsing for dates, times, and other entities.
"""

import json
import time
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Tuple
import requests
from requests.exceptions import RequestException, Timeout, ConnectionError

from models.event_models import FieldResult


class DucklingExtractor:
    """
    Client for Duckling entity extraction service.
    
    Duckling is a rule-based parser developed by Facebook that provides
    robust extraction of dates, times, numbers, and other entities from text.
    This class provides a Python interface to a Duckling HTTP service.
    
    Requirements addressed:
    - 11.1: Deterministic backup parsing when regex fails
    - 11.3: Timezone validation and normalization
    - 11.4: Confidence scoring for deterministic results (0.6-0.8 range)
    """
    
    def __init__(self, 
                 duckling_url: str = "http://localhost:8000/parse",
                 timeout_seconds: int = 3,
                 default_timezone: str = "UTC"):
        """
        Initialize Duckling extractor.
        
        Args:
            duckling_url: URL of the Duckling service endpoint
            timeout_seconds: Request timeout in seconds
            default_timezone: Default timezone for parsing
        """
        self.duckling_url = duckling_url
        self.timeout_seconds = timeout_seconds
        self.default_timezone = default_timezone
        self._service_available = None
        self._last_health_check = 0
        self._health_check_interval = 300  # 5 minutes
    
    def is_service_available(self) -> bool:
        """
        Check if Duckling service is available.
        
        Returns:
            True if service is responding, False otherwise
        """
        current_time = time.time()
        
        # Use cached result if recent
        if (self._service_available is not None and 
            current_time - self._last_health_check < self._health_check_interval):
            return self._service_available
        
        try:
            # Simple health check with minimal payload
            response = requests.post(
                self.duckling_url,
                json={
                    "text": "test",
                    "dims": ["time"],
                    "locale": "en_US"
                },
                timeout=2
            )
            self._service_available = response.status_code == 200
        except (RequestException, ConnectionError, Timeout):
            self._service_available = False
        
        self._last_health_check = current_time
        return self._service_available
    
    def extract_with_duckling(self, text: str, field: str = "time") -> FieldResult:
        """
        Extract entities using Duckling parser.
        
        Args:
            text: Input text to parse
            field: Field type to extract ("time", "date", "datetime")
            
        Returns:
            FieldResult with extracted value and metadata
            
        Requirements:
        - 11.1: Provides deterministic backup when regex fails
        - 11.3: Validates timezone normalization
        - 11.4: Returns confidence in 0.6-0.8 range
        """
        start_time = time.time()
        
        # Check service availability (this may take time for the first check)
        if not self.is_service_available():
            processing_time_ms = max(1, int((time.time() - start_time) * 1000))
            return FieldResult(
                value=None,
                source="duckling",
                confidence=0.0,
                span=(0, 0),
                alternatives=[],
                processing_time_ms=processing_time_ms
            )
        
        try:
            # Map field types to Duckling dimensions
            dim_mapping = {
                "time": "time",
                "date": "time", 
                "datetime": "time",
                "start_datetime": "time",
                "end_datetime": "time",
                "duration": "duration",
                "number": "number"
            }
            
            duckling_dim = dim_mapping.get(field, "time")
            
            # Prepare request payload
            payload = {
                "text": text,
                "dims": [duckling_dim],
                "locale": "en_US",
                "tz": self.default_timezone
            }
            
            # Make request to Duckling service
            response = requests.post(
                self.duckling_url,
                json=payload,
                timeout=self.timeout_seconds
            )
            
            processing_time_ms = max(1, int((time.time() - start_time) * 1000))
            
            if response.status_code != 200:
                return FieldResult(
                    value=None,
                    source="duckling",
                    confidence=0.0,
                    span=(0, 0),
                    alternatives=[],
                    processing_time_ms=processing_time_ms
                )
            
            # Parse response
            entities = response.json()
            
            if not entities:
                return FieldResult(
                    value=None,
                    source="duckling",
                    confidence=0.0,
                    span=(0, 0),
                    alternatives=[],
                    processing_time_ms=processing_time_ms
                )
            
            # Process the best entity
            best_entity = self._select_best_entity(entities, field)
            
            if not best_entity:
                return FieldResult(
                    value=None,
                    source="duckling",
                    confidence=0.0,
                    span=(0, 0),
                    alternatives=[],
                    processing_time_ms=processing_time_ms
                )
            
            # Extract value and validate
            extracted_value = self._extract_value_from_entity(best_entity, field)
            confidence = self._calculate_confidence(best_entity, text)
            span = (best_entity.get("start", 0), best_entity.get("end", 0))
            
            # Get alternatives
            alternatives = []
            for entity in entities[1:6]:  # Up to 5 alternatives
                alt_value = self._extract_value_from_entity(entity, field)
                if alt_value and alt_value != extracted_value:
                    alternatives.append(alt_value)
            
            return FieldResult(
                value=extracted_value,
                source="duckling",
                confidence=confidence,
                span=span,
                alternatives=alternatives,
                processing_time_ms=processing_time_ms
            )
            
        except (RequestException, ConnectionError, Timeout) as e:
            processing_time_ms = max(1, int((time.time() - start_time) * 1000))
            return FieldResult(
                value=None,
                source="duckling",
                confidence=0.0,
                span=(0, 0),
                alternatives=[],
                processing_time_ms=processing_time_ms
            )
        except Exception as e:
            processing_time_ms = max(1, int((time.time() - start_time) * 1000))
            return FieldResult(
                value=None,
                source="duckling",
                confidence=0.0,
                span=(0, 0),
                alternatives=[],
                processing_time_ms=processing_time_ms
            )
    
    def _select_best_entity(self, entities: List[Dict], field: str) -> Optional[Dict]:
        """
        Select the best entity from Duckling results.
        
        Args:
            entities: List of entities from Duckling
            field: Target field type
            
        Returns:
            Best entity or None
        """
        if not entities:
            return None
        
        # Sort by confidence (if available) and span length (prefer shorter spans)
        def entity_score(entity):
            confidence = entity.get("confidence", 0.5)
            span_length = entity.get("end", 0) - entity.get("start", 0)
            # Prefer higher confidence and shorter spans
            return (confidence, -span_length)
        
        sorted_entities = sorted(entities, key=entity_score, reverse=True)
        return sorted_entities[0]
    
    def _extract_value_from_entity(self, entity: Dict, field: str) -> Any:
        """
        Extract the actual value from a Duckling entity.
        
        Args:
            entity: Duckling entity dictionary
            field: Target field type
            
        Returns:
            Extracted value or None
        """
        try:
            value_data = entity.get("value", {})
            
            if field in ["time", "date", "datetime", "start_datetime", "end_datetime"]:
                # Handle time entities
                if "value" in value_data:
                    # ISO datetime string
                    iso_string = value_data["value"]
                    return datetime.fromisoformat(iso_string.replace("Z", "+00:00"))
                elif "from" in value_data and "to" in value_data:
                    # Time range - return start time for start fields, end for end fields
                    if field == "end_datetime":
                        iso_string = value_data["to"]["value"]
                    else:
                        iso_string = value_data["from"]["value"]
                    return datetime.fromisoformat(iso_string.replace("Z", "+00:00"))
                elif "from" in value_data:
                    # Open-ended range
                    iso_string = value_data["from"]["value"]
                    return datetime.fromisoformat(iso_string.replace("Z", "+00:00"))
            
            elif field == "duration":
                # Handle duration entities
                if "minute" in value_data:
                    return value_data["minute"]
                elif "hour" in value_data:
                    return value_data["hour"] * 60
                elif "second" in value_data:
                    return value_data["second"] / 60
            
            elif field == "number":
                # Handle number entities
                return value_data.get("value")
            
            return None
            
        except (KeyError, ValueError, TypeError):
            return None
    
    def _calculate_confidence(self, entity: Dict, original_text: str) -> float:
        """
        Calculate confidence score for Duckling extraction.
        
        Args:
            entity: Duckling entity
            original_text: Original input text
            
        Returns:
            Confidence score between 0.6 and 0.8 (deterministic backup range)
            
        Requirements:
        - 11.4: Confidence scoring for Duckling results (0.6-0.8 range)
        """
        base_confidence = 0.7  # Base confidence for deterministic parsing
        
        # Factors that increase confidence
        confidence_factors = []
        
        # 1. Span coverage (how much of the text is covered)
        span_start = entity.get("start", 0)
        span_end = entity.get("end", 0)
        span_length = span_end - span_start
        text_length = len(original_text.strip())
        
        if text_length > 0:
            coverage_ratio = span_length / text_length
            # Higher coverage generally means better match
            coverage_factor = min(1.0, coverage_ratio * 2)  # Cap at 1.0
            confidence_factors.append(coverage_factor)
        
        # 2. Entity completeness (has all expected fields)
        value_data = entity.get("value", {})
        completeness_factor = 0.5
        
        if "value" in value_data:
            completeness_factor = 1.0  # Complete datetime
        elif "from" in value_data and "to" in value_data:
            completeness_factor = 0.9  # Time range
        elif "from" in value_data:
            completeness_factor = 0.7  # Open range
        
        confidence_factors.append(completeness_factor)
        
        # 3. Duckling's own confidence (if provided)
        duckling_confidence = entity.get("confidence", 0.7)
        confidence_factors.append(duckling_confidence)
        
        # Calculate weighted average with more generous scoring
        if confidence_factors:
            avg_factor = sum(confidence_factors) / len(confidence_factors)
            # Adjust base confidence by average factor, but be more generous
            final_confidence = base_confidence * (0.8 + 0.2 * avg_factor)
        else:
            final_confidence = base_confidence
        
        # Ensure confidence is within deterministic backup range (0.6-0.8)
        return max(0.6, min(0.8, final_confidence))
    
    def validate_timezone_normalization(self, datetime_result: FieldResult) -> bool:
        """
        Validate that datetime results have proper timezone information.
        
        Args:
            datetime_result: FieldResult containing datetime value
            
        Returns:
            True if timezone is properly normalized, False otherwise
            
        Requirements:
        - 11.3: Timezone validation and normalization for Duckling outputs
        """
        if not datetime_result.value or not isinstance(datetime_result.value, datetime):
            return False
        
        dt = datetime_result.value
        
        # Check if datetime has timezone info
        if dt.tzinfo is None:
            return False
        
        # Check if timezone is valid (not just a naive offset)
        try:
            # Try to get timezone name or offset
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
    
    def normalize_timezone(self, dt: datetime, target_timezone: str = None) -> datetime:
        """
        Normalize datetime to target timezone.
        
        Args:
            dt: Input datetime
            target_timezone: Target timezone (defaults to instance default)
            
        Returns:
            Normalized datetime with proper timezone
        """
        if target_timezone is None:
            target_timezone = self.default_timezone
        
        # If datetime is naive, assume it's in the default timezone
        if dt.tzinfo is None:
            if target_timezone == "UTC":
                dt = dt.replace(tzinfo=timezone.utc)
            else:
                # For simplicity, treat as UTC if no specific timezone handling
                dt = dt.replace(tzinfo=timezone.utc)
        
        # Convert to target timezone if needed
        if target_timezone == "UTC" and dt.tzinfo != timezone.utc:
            dt = dt.astimezone(timezone.utc)
        
        return dt
    
    def extract_multiple_fields(self, text: str, fields: List[str]) -> Dict[str, FieldResult]:
        """
        Extract multiple fields from text in a single request.
        
        Args:
            text: Input text
            fields: List of field names to extract
            
        Returns:
            Dictionary mapping field names to FieldResults
        """
        results = {}
        
        # Group fields by Duckling dimension for efficiency
        time_fields = [f for f in fields if f in ["time", "date", "datetime", "start_datetime", "end_datetime"]]
        duration_fields = [f for f in fields if f == "duration"]
        number_fields = [f for f in fields if f == "number"]
        
        # Extract time-related fields
        if time_fields:
            for field in time_fields:
                results[field] = self.extract_with_duckling(text, field)
        
        # Extract duration fields
        if duration_fields:
            for field in duration_fields:
                results[field] = self.extract_with_duckling(text, field)
        
        # Extract number fields
        if number_fields:
            for field in number_fields:
                results[field] = self.extract_with_duckling(text, field)
        
        return results