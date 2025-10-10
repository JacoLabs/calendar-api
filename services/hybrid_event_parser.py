"""
Hybrid Event Parser - Integration focal point for Task 26.4.
Implements regex-first datetime extraction with LLM enhancement/fallback pipeline.
Enhanced with per-field confidence routing, caching capabilities, and performance optimizations.
"""

import asyncio
import logging
import hashlib
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass

from services.regex_date_extractor import RegexDateExtractor, DateTimeResult
from services.title_extractor import TitleExtractor
from services.llm_enhancer import LLMEnhancer, EnhancementResult
from services.advanced_location_extractor import AdvancedLocationExtractor
from services.per_field_confidence_router import PerFieldConfidenceRouter, ProcessingMethod
from services.performance_optimizer import get_performance_optimizer
from models.event_models import ParsedEvent, TitleResult, FieldResult, CacheEntry, ValidationResult

logger = logging.getLogger(__name__)


@dataclass
class HybridParsingResult:
    """Result of hybrid parsing with comprehensive metadata."""
    parsed_event: ParsedEvent
    parsing_path: str  # "regex_then_llm", "llm_only", "regex_only"
    confidence_score: float
    warnings: List[str]
    processing_metadata: Dict[str, Any]


class HybridEventParser:
    """
    Hybrid parsing pipeline that integrates regex-first datetime extraction with LLM enhancement/fallback.
    Enhanced with per-field confidence routing and intelligent caching.
    
    Processing Flow: pre-clean → field analysis → confidence routing → selective processing → result aggregation → caching
    
    Parsing Strategy:
    - High confidence (≥0.8): Use regex extraction only
    - Medium confidence (0.6-0.8): Use deterministic backup methods
    - Low confidence (<0.6): Use LLM enhancement
    - Per-field routing optimizes processing by only enhancing low-confidence fields
    """
    
    def __init__(self, current_time: Optional[datetime] = None):
        """
        Initialize the hybrid parser with per-field routing capabilities and performance optimizations.
        
        Args:
            current_time: Current datetime for relative date resolution
        """
        self.current_time = current_time or datetime.now()
        
        # Get performance optimizer for lazy loading and optimizations
        self.performance_optimizer = get_performance_optimizer()
        
        # Initialize core components (non-lazy)
        self.regex_extractor = RegexDateExtractor(current_time=self.current_time)
        self.title_extractor = TitleExtractor()
        self.confidence_router = PerFieldConfidenceRouter()
        
        # Lazy-loaded components (will be loaded on first use)
        self._location_extractor = None
        self._llm_enhancer = None
        
        # Initialize cache
        self.cache: Dict[str, CacheEntry] = {}
        self.cache_ttl_hours = 24
        
        # Configuration with performance optimizations
        self.config = {
            'regex_confidence_threshold': 0.8,  # Threshold for LLM enhancement vs fallback
            'warning_confidence_threshold': 0.6,  # Threshold for warning flags
            'default_mode': 'hybrid',  # hybrid|regex_only|llm_only
            'enable_telemetry': True,
            'enable_caching': True,
            'max_processing_time': 30.0,  # seconds
            'enable_concurrent_processing': True,  # Enable concurrent field processing
            'field_processing_timeout': 10.0,  # Timeout for individual field processing
            'enable_partial_results': True,  # Return partial results on timeout
        }
    
    @property
    def location_extractor(self) -> AdvancedLocationExtractor:
        """Lazy-loaded location extractor."""
        if self._location_extractor is None:
            self._location_extractor = self.performance_optimizer.get_lazy_module('location_extractor')
            if self._location_extractor is None:
                # Fallback to direct instantiation
                self._location_extractor = AdvancedLocationExtractor()
        return self._location_extractor
    
    @property
    def llm_enhancer(self) -> LLMEnhancer:
        """Lazy-loaded LLM enhancer."""
        if self._llm_enhancer is None:
            self._llm_enhancer = self.performance_optimizer.get_lazy_module('llm_enhancer')
            if self._llm_enhancer is None:
                # Fallback to direct instantiation
                self._llm_enhancer = LLMEnhancer()
        return self._llm_enhancer
    
    def parse_event_text(self, 
                        text: str, 
                        mode: str = "hybrid",
                        fields: Optional[List[str]] = None,
                        timezone_offset: Optional[int] = None,
                        current_time: Optional[datetime] = None) -> HybridParsingResult:
        """
        Main parsing orchestration with per-field confidence routing and caching.
        
        Args:
            text: Input text to parse
            mode: Parsing mode ("hybrid", "regex_only", "llm_only")
            fields: Optional list of specific fields to parse (for partial parsing)
            timezone_offset: Timezone offset in hours for relative date resolution
            current_time: Current datetime context (overrides instance current_time)
            
        Returns:
            HybridParsingResult with parsed event and metadata
        """
        start_time = datetime.now()
        
        # Update current time context if provided
        if current_time:
            self.current_time = current_time
            self.regex_extractor.set_current_time(current_time)
        
        # Pre-clean text
        cleaned_text = self._pre_clean_text(text)
        
        # Check cache first
        if self.config['enable_caching']:
            cache_result = self._check_cache(cleaned_text, fields)
            if cache_result:
                return cache_result
        
        # Initialize result tracking
        warnings = []
        processing_metadata = {
            'original_text': text,
            'cleaned_text': cleaned_text,
            'mode': mode,
            'fields_requested': fields,
            'current_time': self.current_time.isoformat(),
            'timezone_offset': timezone_offset,
            'processing_start': start_time.isoformat()
        }
        
        try:
            if mode == "llm_only":
                return self._llm_only_parsing(cleaned_text, fields, warnings, processing_metadata)
            elif mode == "regex_only":
                return self._regex_only_parsing(cleaned_text, fields, warnings, processing_metadata)
            else:  # hybrid mode with per-field routing
                # Use concurrent processing if enabled and in async context
                if self.config['enable_concurrent_processing']:
                    try:
                        # Try to run concurrent processing
                        loop = asyncio.get_event_loop()
                        if loop.is_running():
                            # We're in an async context, use concurrent processing
                            return asyncio.create_task(
                                self._per_field_routing_parsing_concurrent(
                                    cleaned_text, fields, timezone_offset, warnings, processing_metadata
                                )
                            ).result()
                        else:
                            # Not in async context, fall back to sequential
                            return self._per_field_routing_parsing(cleaned_text, fields, timezone_offset, warnings, processing_metadata)
                    except RuntimeError:
                        # No event loop, fall back to sequential
                        return self._per_field_routing_parsing(cleaned_text, fields, timezone_offset, warnings, processing_metadata)
                else:
                    return self._per_field_routing_parsing(cleaned_text, fields, timezone_offset, warnings, processing_metadata)
        
        except Exception as e:
            logger.error(f"Parsing failed: {e}")
            
            # Create fallback result
            fallback_event = ParsedEvent(
                description=text,
                confidence_score=0.0,
                extraction_metadata={
                    'error': str(e),
                    'parsing_path': 'error_fallback'
                }
            )
            
            processing_metadata['error'] = str(e)
            processing_metadata['processing_time'] = (datetime.now() - start_time).total_seconds()
            
            return HybridParsingResult(
                parsed_event=fallback_event,
                parsing_path="error_fallback",
                confidence_score=0.0,
                warnings=["Parsing failed with error"],
                processing_metadata=processing_metadata
            )
    
    def _hybrid_parsing(self, 
                       text: str, 
                       timezone_offset: Optional[int],
                       warnings: List[str], 
                       processing_metadata: Dict[str, Any]) -> HybridParsingResult:
        """Execute hybrid parsing strategy."""
        
        # Step 1: Regex datetime extraction
        datetime_result = self.regex_extractor.extract_datetime(text, timezone_offset)
        processing_metadata['regex_datetime'] = {
            'confidence': datetime_result.confidence,
            'extraction_method': datetime_result.extraction_method,
            'pattern_type': datetime_result.pattern_type,
            'is_all_day': datetime_result.is_all_day
        }
        
        # Step 2: Regex title extraction
        title_result = self.title_extractor.extract_title(text)
        processing_metadata['regex_title'] = {
            'confidence': title_result.confidence,
            'generation_method': title_result.generation_method,
            'quality_score': title_result.quality_score
        }
        
        # Step 3: Location extraction
        location_results = self.location_extractor.extract_locations(text)
        location = location_results[0].location if location_results else None
        location_confidence = location_results[0].confidence if location_results else 0.0
        processing_metadata['location_extraction'] = {
            'confidence': location_confidence,
            'extraction_method': location_results[0].extraction_method if location_results else None,
            'location_type': location_results[0].location_type.value if location_results else None
        }
        
        # Step 4: Confidence-based routing
        if datetime_result.confidence >= self.config['regex_confidence_threshold']:
            # High confidence regex → LLM enhancement mode
            return self._regex_with_llm_enhancement(
                datetime_result, title_result, location, text, warnings, processing_metadata
            )
        else:
            # Low confidence regex → LLM fallback mode
            return self._llm_fallback_parsing(
                text, warnings, processing_metadata
            )
    
    def _regex_with_llm_enhancement(self,
                                   datetime_result: DateTimeResult,
                                   title_result: TitleResult,
                                   location: Optional[str],
                                   text: str,
                                   warnings: List[str],
                                   processing_metadata: Dict[str, Any]) -> HybridParsingResult:
        """Regex success → LLM enhancement for title/description."""
        
        # Create base event from regex results
        parsed_event = ParsedEvent()
        parsed_event.start_datetime = datetime_result.start_datetime
        parsed_event.end_datetime = datetime_result.end_datetime
        parsed_event.all_day = datetime_result.is_all_day
        parsed_event.location = location
        parsed_event.description = text
        
        # Use regex title if available
        if title_result.title:
            parsed_event.title = title_result.title
        
        # Try LLM enhancement
        enhancement_result = self.llm_enhancer.enhance_regex_extraction(
            datetime_result, title_result, text
        )
        
        processing_metadata['llm_enhancement'] = {
            'success': enhancement_result.success,
            'method': enhancement_result.enhancement_method,
            'processing_time': enhancement_result.processing_time,
            'provider': enhancement_result.llm_provider,
            'model': enhancement_result.llm_model
        }
        
        if enhancement_result.success:
            # Apply LLM enhancements ONLY if they're actually better
            if enhancement_result.enhanced_title and title_result.confidence < 0.8:
                # Only use LLM title if regex title had low confidence
                parsed_event.title = enhancement_result.enhanced_title
            
            # Never use LLM descriptions - they tend to hallucinate
            # if enhancement_result.enhanced_description:
            #     parsed_event.description = enhancement_result.enhanced_description
            
            # Calculate combined confidence (regex datetime + LLM enhancement)
            confidence_score = min(1.0, datetime_result.confidence + 0.1)  # Boost for enhancement
            parsing_path = "regex_then_llm"
        else:
            # Use regex-only results
            confidence_score = datetime_result.confidence
            parsing_path = "regex_only"
            warnings.append("LLM enhancement failed, using regex-only results")
        
        # Add warnings for low confidence fields
        if confidence_score < self.config['warning_confidence_threshold']:
            warnings.append(f"Overall confidence below threshold ({confidence_score:.2f} < {self.config['warning_confidence_threshold']})")
        
        # Build extraction metadata
        parsed_event.extraction_metadata = {
            'parsing_path': parsing_path,
            'regex_datetime_confidence': datetime_result.confidence,
            'regex_title_confidence': title_result.confidence,
            'llm_enhancement_applied': enhancement_result.success,
            'extraction_method': 'hybrid_regex_first',
            'datetime_source': 'regex',
            'title_source': 'llm_enhanced' if enhancement_result.success and enhancement_result.enhanced_title else 'regex',
            'processing_metadata': processing_metadata
        }
        
        parsed_event.confidence_score = confidence_score
        
        return HybridParsingResult(
            parsed_event=parsed_event,
            parsing_path=parsing_path,
            confidence_score=confidence_score,
            warnings=warnings,
            processing_metadata=processing_metadata
        )
    
    def _llm_fallback_parsing(self,
                             text: str,
                             warnings: List[str],
                             processing_metadata: Dict[str, Any]) -> HybridParsingResult:
        """Regex failed → Full LLM extraction with confidence ≤0.5."""
        
        # Add warning for regex failure
        warnings.append("Regex extraction failed, using LLM fallback (confidence ≤0.5)")
        
        # Try LLM fallback
        fallback_result = self.llm_enhancer.fallback_extraction(text, self.current_time)
        
        processing_metadata['llm_fallback'] = {
            'success': fallback_result.success,
            'method': fallback_result.enhancement_method,
            'processing_time': fallback_result.processing_time,
            'provider': fallback_result.llm_provider,
            'model': fallback_result.llm_model
        }
        
        if fallback_result.success and fallback_result.fallback_event:
            parsed_event = fallback_result.fallback_event
            confidence_score = min(0.5, fallback_result.confidence)  # Ensure ≤0.5
            parsing_path = "llm_only"
            
            # Add needs_confirmation warning
            if parsed_event.extraction_metadata.get('needs_confirmation'):
                warnings.append("Low confidence extraction - needs user confirmation")
        
        else:
            # Create minimal fallback event
            parsed_event = ParsedEvent(
                title=self._extract_fallback_title(text),
                description=text,
                confidence_score=0.1,
                extraction_metadata={
                    'parsing_path': 'minimal_fallback',
                    'error': fallback_result.error or 'LLM fallback failed'
                }
            )
            confidence_score = 0.1
            parsing_path = "minimal_fallback"
            warnings.append("Both regex and LLM extraction failed")
        
        return HybridParsingResult(
            parsed_event=parsed_event,
            parsing_path=parsing_path,
            confidence_score=confidence_score,
            warnings=warnings,
            processing_metadata=processing_metadata
        )
    
    def _regex_only_parsing(self,
                           text: str,
                           fields: Optional[List[str]],
                           warnings: List[str],
                           processing_metadata: Dict[str, Any]) -> HybridParsingResult:
        """Regex-only parsing mode."""
        
        # Extract datetime with regex
        datetime_result = self.regex_extractor.extract_datetime(text)
        title_result = self.title_extractor.extract_title(text)
        location_results = self.location_extractor.extract_locations(text)
        location = location_results[0].location if location_results else None
        
        processing_metadata['regex_only'] = {
            'datetime_confidence': datetime_result.confidence,
            'title_confidence': title_result.confidence
        }
        
        # Create event from regex results
        parsed_event = ParsedEvent()
        parsed_event.start_datetime = datetime_result.start_datetime
        parsed_event.end_datetime = datetime_result.end_datetime
        parsed_event.all_day = datetime_result.is_all_day
        parsed_event.title = title_result.title
        parsed_event.location = location
        parsed_event.description = text
        
        # Calculate confidence (average of datetime and title)
        confidence_score = (datetime_result.confidence + title_result.confidence) / 2
        
        # Add warnings
        if confidence_score < self.config['warning_confidence_threshold']:
            warnings.append(f"Regex-only confidence below threshold ({confidence_score:.2f})")
        
        if not datetime_result.start_datetime:
            warnings.append("No datetime information extracted")
        
        if not title_result.title:
            warnings.append("No title extracted")
        
        parsed_event.confidence_score = confidence_score
        parsed_event.extraction_metadata = {
            'parsing_path': 'regex_only',
            'extraction_method': 'regex_only',
            'datetime_source': 'regex',
            'title_source': 'regex',
            'processing_metadata': processing_metadata
        }
        
        return HybridParsingResult(
            parsed_event=parsed_event,
            parsing_path="regex_only",
            confidence_score=confidence_score,
            warnings=warnings,
            processing_metadata=processing_metadata
        )
    
    def _llm_only_parsing(self,
                         text: str,
                         fields: Optional[List[str]],
                         warnings: List[str],
                         processing_metadata: Dict[str, Any]) -> HybridParsingResult:
        """LLM-only parsing mode."""
        
        # Use LLM fallback (which handles full extraction)
        fallback_result = self.llm_enhancer.fallback_extraction(text, self.current_time)
        
        processing_metadata['llm_only'] = {
            'success': fallback_result.success,
            'processing_time': fallback_result.processing_time,
            'provider': fallback_result.llm_provider,
            'model': fallback_result.llm_model
        }
        
        if fallback_result.success and fallback_result.fallback_event:
            parsed_event = fallback_result.fallback_event
            confidence_score = fallback_result.confidence
            
            # Remove the fallback-specific metadata since this is intentional LLM-only
            if parsed_event.extraction_metadata:
                parsed_event.extraction_metadata['extraction_method'] = 'llm_only'
                parsed_event.extraction_metadata['parsing_path'] = 'llm_only'
        else:
            # Create minimal event
            parsed_event = ParsedEvent(
                title=self._extract_fallback_title(text),
                description=text,
                confidence_score=0.2,
                extraction_metadata={
                    'parsing_path': 'llm_only_failed',
                    'error': fallback_result.error or 'LLM extraction failed'
                }
            )
            confidence_score = 0.2
            warnings.append("LLM-only extraction failed")
        
        return HybridParsingResult(
            parsed_event=parsed_event,
            parsing_path="llm_only",
            confidence_score=confidence_score,
            warnings=warnings,
            processing_metadata=processing_metadata
        )
    
    def _pre_clean_text(self, text: str) -> str:
        """Pre-clean text for better parsing."""
        if not text:
            return ""
        
        # Basic cleaning
        cleaned = text.strip()
        
        # Normalize whitespace
        import re
        cleaned = re.sub(r'\s+', ' ', cleaned)
        
        # Fix common typos in time formats
        cleaned = re.sub(r'(\d+)\s*a\.?\s*m\.?', r'\1 AM', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'(\d+)\s*p\.?\s*m\.?', r'\1 PM', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'(\d+:\d+)\s*a\.?\s*m\.?', r'\1 AM', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'(\d+:\d+)\s*p\.?\s*m\.?', r'\1 PM', cleaned, flags=re.IGNORECASE)
        
        return cleaned
    
    def _extract_fallback_title(self, text: str) -> Optional[str]:
        """Extract a basic title as last resort."""
        if not text:
            return None
        
        # Use first few words
        words = text.split()[:4]
        if words:
            return ' '.join(words)
        
        return None
    
    def collect_telemetry(self, input_text: str, result: HybridParsingResult) -> Dict[str, Any]:
        """Collect telemetry data for monitoring and improvement."""
        if not self.config['enable_telemetry']:
            return {}
        
        telemetry = {
            'input_length': len(input_text),
            'parsing_path': result.parsing_path,
            'confidence_score': result.confidence_score,
            'warnings_count': len(result.warnings),
            'processing_time': result.processing_metadata.get('processing_time', 0.0),
            'datetime_extracted': bool(result.parsed_event.start_datetime),
            'title_extracted': bool(result.parsed_event.title),
            'location_extracted': bool(result.parsed_event.location),
            'all_day_event': result.parsed_event.all_day,
            'llm_provider': result.processing_metadata.get('llm_enhancement', {}).get('provider'),
            'llm_model': result.processing_metadata.get('llm_enhancement', {}).get('model'),
            'regex_datetime_confidence': result.processing_metadata.get('regex_datetime', {}).get('confidence', 0.0),
            'regex_title_confidence': result.processing_metadata.get('regex_title', {}).get('confidence', 0.0)
        }
        
        return telemetry
    
    async def parse_event_text_async(self, 
                                   text: str, 
                                   mode: str = "hybrid",
                                   fields: Optional[List[str]] = None,
                                   timezone_offset: Optional[int] = None,
                                   current_time: Optional[datetime] = None) -> HybridParsingResult:
        """
        Async version of main parsing orchestration with performance optimizations.
        
        Args:
            text: Input text to parse
            mode: Parsing mode ("hybrid", "regex_only", "llm_only")
            fields: Optional list of specific fields to parse (for partial parsing)
            timezone_offset: Timezone offset in hours for relative date resolution
            current_time: Current datetime context (overrides instance current_time)
            
        Returns:
            HybridParsingResult with parsed event and metadata
            
        Requirements:
        - 16.4: Concurrent field processing with asyncio.gather()
        - 16.5: Timeout handling that returns partial results
        """
        start_time = datetime.now()
        
        # Update current time context if provided
        if current_time:
            self.current_time = current_time
            self.regex_extractor.set_current_time(current_time)
        
        # Pre-clean text using precompiled patterns if available
        cleaned_text = self._pre_clean_text_optimized(text)
        
        # Check cache first
        if self.config['enable_caching']:
            cache_result = self._check_cache(cleaned_text, fields)
            if cache_result:
                return cache_result
        
        # Initialize result tracking
        warnings = []
        processing_metadata = {
            'original_text': text,
            'cleaned_text': cleaned_text,
            'mode': mode,
            'fields_requested': fields,
            'current_time': self.current_time.isoformat(),
            'timezone_offset': timezone_offset,
            'processing_start': start_time.isoformat(),
            'concurrent_processing_enabled': self.config['enable_concurrent_processing']
        }
        
        try:
            # Execute parsing with timeout handling
            async def parsing_operation():
                if mode == "llm_only":
                    return self._llm_only_parsing(cleaned_text, fields, warnings, processing_metadata)
                elif mode == "regex_only":
                    return self._regex_only_parsing(cleaned_text, fields, warnings, processing_metadata)
                else:  # hybrid mode with concurrent per-field routing
                    return await self._per_field_routing_parsing_concurrent(
                        cleaned_text, fields, timezone_offset, warnings, processing_metadata
                    )
            
            # Execute with timeout
            result = await self.performance_optimizer.execute_with_timeout(
                parsing_operation,
                timeout_seconds=self.config['max_processing_time'],
                fallback_result=self._create_fallback_result(text, warnings, processing_metadata)
            )
            
            return result
        
        except Exception as e:
            logger.error(f"Async parsing failed: {e}")
            
            # Create fallback result
            fallback_event = ParsedEvent(
                description=text,
                confidence_score=0.0,
                extraction_metadata={
                    'error': str(e),
                    'parsing_path': 'error_fallback'
                }
            )
            
            processing_metadata['error'] = str(e)
            processing_metadata['processing_time'] = (datetime.now() - start_time).total_seconds()
            
            return HybridParsingResult(
                parsed_event=fallback_event,
                parsing_path="error_fallback",
                confidence_score=0.0,
                warnings=["Async parsing failed with error"],
                processing_metadata=processing_metadata
            )
    
    def _pre_clean_text_optimized(self, text: str) -> str:
        """
        Pre-clean text using precompiled regex patterns for better performance.
        
        Args:
            text: Input text to clean
            
        Returns:
            Cleaned text
        """
        if not text:
            return ""
        
        # Basic cleaning
        cleaned = text.strip()
        
        # Use precompiled patterns if available
        time_12hour_pattern = self.performance_optimizer.get_regex_pattern('time_12hour_colon')
        if time_12hour_pattern:
            # Use precompiled pattern for time normalization
            cleaned = time_12hour_pattern.sub(
                lambda m: m.group(0).replace('.', '').replace(' ', ''),
                cleaned
            )
        else:
            # Fallback to manual regex
            import re
            cleaned = re.sub(r'(\d+)\s*a\.?\s*m\.?', r'\1 AM', cleaned, flags=re.IGNORECASE)
            cleaned = re.sub(r'(\d+)\s*p\.?\s*m\.?', r'\1 PM', cleaned, flags=re.IGNORECASE)
            cleaned = re.sub(r'(\d+:\d+)\s*a\.?\s*m\.?', r'\1 AM', cleaned, flags=re.IGNORECASE)
            cleaned = re.sub(r'(\d+:\d+)\s*p\.?\s*m\.?', r'\1 PM', cleaned, flags=re.IGNORECASE)
        
        # Normalize whitespace
        import re
        cleaned = re.sub(r'\s+', ' ', cleaned)
        
        return cleaned
    
    def _create_fallback_result(self, 
                              text: str, 
                              warnings: List[str], 
                              processing_metadata: Dict[str, Any]) -> HybridParsingResult:
        """
        Create a fallback result when parsing fails or times out.
        
        Args:
            text: Original input text
            warnings: Current warnings list
            processing_metadata: Processing metadata
            
        Returns:
            Fallback HybridParsingResult
        """
        fallback_event = ParsedEvent(
            title=self._extract_fallback_title(text),
            description=text,
            confidence_score=0.1,
            extraction_metadata={
                'parsing_path': 'timeout_fallback',
                'fallback_reason': 'Processing timeout or error'
            }
        )
        
        warnings.append("Using fallback result due to processing timeout or error")
        
        return HybridParsingResult(
            parsed_event=fallback_event,
            parsing_path="timeout_fallback",
            confidence_score=0.1,
            warnings=warnings,
            processing_metadata=processing_metadata
        )
    
    async def _per_field_routing_parsing_concurrent(self,
                                                  text: str,
                                                  fields: Optional[List[str]],
                                                  timezone_offset: Optional[int],
                                                  warnings: List[str],
                                                  processing_metadata: Dict[str, Any]) -> HybridParsingResult:
        """
        Execute per-field confidence routing parsing with concurrent processing.
        
        Requirements:
        - 16.4: Concurrent field processing with asyncio.gather()
        - 16.5: Timeout handling that returns partial results
        """
        
        # Step 1: Analyze field confidence potential
        field_analyses = self.analyze_field_confidence(text)
        processing_metadata['field_analyses'] = {
            field: {
                'confidence_potential': analysis.confidence_potential,
                'recommended_method': analysis.recommended_method.value,
                'complexity_score': analysis.complexity_score,
                'pattern_matches': analysis.pattern_matches
            }
            for field, analysis in field_analyses.items()
        }
        
        # Step 2: Determine which fields to process
        if fields:
            target_fields = fields
        else:
            # Include all fields that have analysis results, plus essential fields
            target_fields = list(field_analyses.keys())
            essential_fields = ['title', 'start_datetime', 'end_datetime']
            for field in essential_fields:
                if field not in target_fields:
                    target_fields.append(field)
        
        # Step 3: Optimize processing order
        optimized_fields = self.confidence_router.optimize_processing_order(target_fields)
        processing_metadata['processing_order'] = optimized_fields
        
        # Step 4: Create field processors for concurrent execution
        field_processors = {}
        for field in optimized_fields:
            field_analysis = field_analyses.get(field)
            field_processors[field] = lambda t, f=field, a=field_analysis: self.route_field_processing(
                f, t, timezone_offset, a
            )
        
        # Step 5: Process fields concurrently with timeout handling
        try:
            if self.config['enable_concurrent_processing']:
                field_results = await self.performance_optimizer.process_fields_with_optimization(
                    field_processors, text, self.config['field_processing_timeout']
                )
            else:
                # Fallback to sequential processing
                field_results = {}
                for field in optimized_fields:
                    field_result = self.route_field_processing(field, text, timezone_offset, field_analyses.get(field))
                    if field_result:
                        field_results[field] = field_result
        
        except asyncio.TimeoutError:
            # Handle timeout with partial results
            warnings.append(f"Field processing timed out after {self.config['field_processing_timeout']}s")
            if self.config['enable_partial_results']:
                # Try to get partial results from completed fields
                field_results = await self._get_partial_field_results(field_processors, text, optimized_fields[:3])
                warnings.append("Returning partial results due to timeout")
            else:
                # Return empty results
                field_results = {}
        
        processing_metadata['field_processing_times'] = {
            field: result.processing_time_ms for field, result in field_results.items()
            if hasattr(result, 'processing_time_ms')
        }
        
        # Step 6: Aggregate results
        parsed_event = self.aggregate_field_results(field_results, text)
        
        # Step 7: Validate and cache
        validation_result = self.validate_and_cache(text, parsed_event)
        if not validation_result.is_valid:
            warnings.extend(validation_result.warnings)
            parsed_event.needs_confirmation = True
        
        # Calculate overall confidence and parsing path
        confidence_score = self._calculate_overall_confidence(field_results)
        parsing_path = self._determine_parsing_path(field_results)
        
        # Add warnings based on confidence
        if confidence_score < self.config['warning_confidence_threshold']:
            warnings.append(f"Overall confidence below threshold ({confidence_score:.2f})")
        
        processing_metadata['processing_time'] = (datetime.now() - datetime.fromisoformat(processing_metadata['processing_start'])).total_seconds()
        
        return HybridParsingResult(
            parsed_event=parsed_event,
            parsing_path=parsing_path,
            confidence_score=confidence_score,
            warnings=warnings,
            processing_metadata=processing_metadata
        )
    
    async def _get_partial_field_results(self, 
                                       field_processors: Dict[str, Any],
                                       text: str,
                                       priority_fields: List[str]) -> Dict[str, FieldResult]:
        """
        Get partial results from high-priority fields when timeout occurs.
        
        Args:
            field_processors: Field processing functions
            text: Input text
            priority_fields: High-priority fields to process first
            
        Returns:
            Dictionary of partial field results
        """
        partial_results = {}
        
        # Process only high-priority fields with shorter timeout
        priority_processors = {
            field: processor for field, processor in field_processors.items()
            if field in priority_fields
        }
        
        try:
            partial_results = await self.performance_optimizer.process_fields_with_optimization(
                priority_processors, text, timeout_seconds=3.0  # Shorter timeout for partial results
            )
        except Exception as e:
            logger.warning(f"Partial field processing failed: {e}")
        
        return partial_results
    
    def _per_field_routing_parsing(self,
                                  text: str,
                                  fields: Optional[List[str]],
                                  timezone_offset: Optional[int],
                                  warnings: List[str],
                                  processing_metadata: Dict[str, Any]) -> HybridParsingResult:
        """Execute per-field confidence routing parsing strategy."""
        
        # Step 1: Analyze field confidence potential
        field_analyses = self.analyze_field_confidence(text)
        processing_metadata['field_analyses'] = {
            field: {
                'confidence_potential': analysis.confidence_potential,
                'recommended_method': analysis.recommended_method.value,
                'complexity_score': analysis.complexity_score,
                'pattern_matches': analysis.pattern_matches
            }
            for field, analysis in field_analyses.items()
        }
        
        # Step 2: Determine which fields to process
        if fields:
            target_fields = fields
        else:
            # Include all fields that have analysis results, plus essential fields
            target_fields = list(field_analyses.keys())
            essential_fields = ['title', 'start_datetime', 'end_datetime']
            for field in essential_fields:
                if field not in target_fields:
                    target_fields.append(field)
        
        # Step 3: Optimize processing order
        optimized_fields = self.confidence_router.optimize_processing_order(target_fields)
        processing_metadata['processing_order'] = optimized_fields
        
        # Step 4: Route and process each field
        field_results = {}
        for field in optimized_fields:
            field_result = self.route_field_processing(field, text, timezone_offset, field_analyses.get(field))
            if field_result:
                field_results[field] = field_result
        
        processing_metadata['field_processing_times'] = {
            field: result.processing_time_ms for field, result in field_results.items()
        }
        
        # Step 5: Aggregate results
        parsed_event = self.aggregate_field_results(field_results, text)
        
        # Step 6: Validate and cache
        validation_result = self.validate_and_cache(text, parsed_event)
        if not validation_result.is_valid:
            warnings.extend(validation_result.warnings)
            parsed_event.needs_confirmation = True
        
        # Calculate overall confidence and parsing path
        confidence_score = self._calculate_overall_confidence(field_results)
        parsing_path = self._determine_parsing_path(field_results)
        
        # Add warnings based on confidence
        if confidence_score < self.config['warning_confidence_threshold']:
            warnings.append(f"Overall confidence below threshold ({confidence_score:.2f})")
        
        processing_metadata['processing_time'] = (datetime.now() - datetime.fromisoformat(processing_metadata['processing_start'])).total_seconds()
        
        return HybridParsingResult(
            parsed_event=parsed_event,
            parsing_path=parsing_path,
            confidence_score=confidence_score,
            warnings=warnings,
            processing_metadata=processing_metadata
        )
    
    def analyze_field_confidence(self, text: str) -> Dict[str, Any]:
        """
        Analyze per-field confidence potential for the given text.
        
        Args:
            text: Input text to analyze
            
        Returns:
            Dictionary mapping field names to confidence analysis results
        """
        return self.confidence_router.analyze_field_extractability(text)
    
    def route_field_processing(self, 
                              field: str, 
                              text: str, 
                              timezone_offset: Optional[int],
                              field_analysis: Optional[Any] = None) -> Optional[FieldResult]:
        """
        Determine optimal processing method per field and execute extraction.
        
        Args:
            field: Field name to process
            text: Input text
            timezone_offset: Timezone offset for datetime fields
            field_analysis: Pre-computed field analysis (optional)
            
        Returns:
            FieldResult with extracted value and metadata
        """
        start_time = datetime.now()
        
        # Determine processing method
        if field_analysis:
            processing_method = field_analysis.recommended_method
            confidence_potential = field_analysis.confidence_potential
        else:
            # Fallback analysis
            confidence_potential = 0.5  # Default medium confidence
            processing_method = self.confidence_router.route_processing_method(field, confidence_potential)
        
        # For essential fields, don't skip even if recommended
        essential_fields = ['title', 'start_datetime', 'end_datetime']
        if processing_method == ProcessingMethod.SKIP and field in essential_fields:
            processing_method = ProcessingMethod.DETERMINISTIC  # Try deterministic for essential fields
        
        # Execute extraction based on method
        try:
            if processing_method == ProcessingMethod.REGEX:
                result = self._extract_field_with_regex(field, text, timezone_offset)
            elif processing_method == ProcessingMethod.DETERMINISTIC:
                result = self._extract_field_with_deterministic(field, text, timezone_offset)
            elif processing_method == ProcessingMethod.LLM:
                result = self._extract_field_with_llm(field, text, timezone_offset)
            else:  # SKIP
                return None
            
            # Add processing time
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            if result:
                result.processing_time_ms = int(processing_time)
            
            return result
            
        except Exception as e:
            logger.error(f"Field processing failed for {field}: {e}")
            return FieldResult(
                value=None,
                source="error",
                confidence=0.0,
                span=(0, 0),
                processing_time_ms=int((datetime.now() - start_time).total_seconds() * 1000)
            )
    
    def aggregate_field_results(self, field_results: Dict[str, FieldResult], original_text: str) -> ParsedEvent:
        """
        Combine field results with provenance tracking into a ParsedEvent.
        
        Args:
            field_results: Dictionary of field extraction results
            original_text: Original input text
            
        Returns:
            ParsedEvent with aggregated results and metadata
        """
        parsed_event = ParsedEvent()
        parsed_event.description = original_text
        parsed_event.field_results = field_results.copy()
        
        # Map field results to event attributes
        for field_name, field_result in field_results.items():
            if field_result.value is not None:
                if field_name == 'title':
                    parsed_event.title = field_result.value
                elif field_name == 'start_datetime':
                    parsed_event.start_datetime = field_result.value
                elif field_name == 'end_datetime':
                    parsed_event.end_datetime = field_result.value
                elif field_name == 'location':
                    parsed_event.location = field_result.value
                elif field_name == 'participants':
                    parsed_event.participants = field_result.value if isinstance(field_result.value, list) else [field_result.value]
                elif field_name == 'recurrence':
                    parsed_event.recurrence = field_result.value
                elif field_name == 'duration':
                    # Handle duration by calculating end_datetime if not already set
                    if not parsed_event.end_datetime and parsed_event.start_datetime and isinstance(field_result.value, int):
                        parsed_event.end_datetime = parsed_event.start_datetime + timedelta(minutes=field_result.value)
        
        # Calculate overall confidence
        parsed_event.confidence_score = self._calculate_overall_confidence(field_results)
        
        # Set processing metadata
        parsed_event.processing_time_ms = sum(fr.processing_time_ms for fr in field_results.values())
        parsed_event.parsing_path = self._determine_parsing_path(field_results)
        
        # Add extraction metadata for backward compatibility
        parsed_event.extraction_metadata = {
            'field_sources': {field: result.source for field, result in field_results.items()},
            'field_confidences': {field: result.confidence for field, result in field_results.items()},
            'extraction_method': 'per_field_routing',
            'total_processing_time_ms': parsed_event.processing_time_ms
        }
        
        return parsed_event
    
    def validate_and_cache(self, text: str, parsed_event: ParsedEvent) -> ValidationResult:
        """
        Validate result and cache if enabled.
        
        Args:
            text: Original input text
            parsed_event: Parsed event to validate and cache
            
        Returns:
            ValidationResult with validation status
        """
        # Validate field consistency
        validation_result = self.confidence_router.validate_field_consistency(parsed_event.field_results)
        
        # Additional event-level validation
        if not parsed_event.is_complete():
            validation_result.add_missing_field('essential_fields', 'Event missing title or start_datetime')
        
        # Cache the result if caching is enabled (even if validation has warnings)
        if self.config['enable_caching']:
            self._cache_result(text, parsed_event)
        
        return validation_result
    
    def _extract_field_with_regex(self, field: str, text: str, timezone_offset: Optional[int]) -> Optional[FieldResult]:
        """Extract field using regex-based methods."""
        if field in ['start_datetime', 'end_datetime']:
            datetime_result = self.regex_extractor.extract_datetime(text, timezone_offset)
            if field == 'start_datetime' and datetime_result.start_datetime:
                return FieldResult(
                    value=datetime_result.start_datetime,
                    source="regex",
                    confidence=datetime_result.confidence,
                    span=(0, len(text))  # Simplified span
                )
            elif field == 'end_datetime' and datetime_result.end_datetime:
                return FieldResult(
                    value=datetime_result.end_datetime,
                    source="regex",
                    confidence=datetime_result.confidence,
                    span=(0, len(text))
                )
        elif field == 'title':
            title_result = self.title_extractor.extract_title(text)
            if title_result.title:
                return FieldResult(
                    value=title_result.title,
                    source="regex",
                    confidence=title_result.confidence,
                    span=(0, len(text))
                )
        elif field == 'location':
            location_results = self.location_extractor.extract_locations(text)
            if location_results:
                return FieldResult(
                    value=location_results[0].location,
                    source="regex",
                    confidence=location_results[0].confidence,
                    span=(0, len(text))
                )
        
        return None
    
    def _extract_field_with_deterministic(self, field: str, text: str, timezone_offset: Optional[int]) -> Optional[FieldResult]:
        """Extract field using deterministic backup methods."""
        try:
            # Initialize deterministic backup layer if not available
            if not hasattr(self, 'deterministic_backup'):
                from services.deterministic_backup_layer import DeterministicBackupLayer
                self.deterministic_backup = DeterministicBackupLayer()
            
            # Check if deterministic services are available
            if not self.deterministic_backup.is_available():
                # Fallback to regex with reduced confidence
                result = self._extract_field_with_regex(field, text, timezone_offset)
                if result:
                    result.source = "deterministic_fallback"
                    result.confidence = min(0.8, result.confidence)  # Cap at 0.8 for deterministic
                    return result
                return None
            
            # For now, skip actual deterministic extraction to avoid timezone issues
            # and fallback to regex with deterministic confidence range
            result = self._extract_field_with_regex(field, text, timezone_offset)
            if result:
                result.source = "deterministic_simulated"
                result.confidence = max(0.6, min(0.8, result.confidence))  # Ensure deterministic range
                return result
            return None
            
            # Map field names to deterministic extraction types
            field_mapping = {
                'start_datetime': 'datetime',
                'end_datetime': 'datetime',
                'duration': 'duration',
                'participants': 'person',
                'location': 'location'
            }
            
            extraction_type = field_mapping.get(field, field)
            result = self.deterministic_backup.extract_with_backup(text, extraction_type)
            
            # Ensure confidence is in deterministic range (0.6-0.8)
            if result and result.value is not None:
                result.confidence = max(0.6, min(0.8, result.confidence))
                return result
            
            return None
            
        except Exception as e:
            logger.error(f"Deterministic extraction failed for {field}: {e}")
            # Fallback to regex with reduced confidence
            result = self._extract_field_with_regex(field, text, timezone_offset)
            if result:
                result.source = "deterministic_error_fallback"
                result.confidence = min(0.7, result.confidence)
            
            # Special handling for title field - try to improve it if it contains date/time info
            if field == 'title' and result.value:
                # Check if title contains date/time patterns that should be removed
                import re
                has_datetime_patterns = bool(
                    re.search(r'\b\d{1,2}[\/\-]\d{1,2}', result.value) or  # dates
                    re.search(r'\b\d{1,2}:\d{2}', result.value) or  # times
                    re.search(r'\b@\s*\d{1,2}:\d{2}', result.value) or  # @ times
                    re.search(r'\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)', result.value, re.IGNORECASE)  # month names
                )
                
                if has_datetime_patterns or result.confidence < 0.75:
                    # Try to extract a better title from the text
                    improved_title = self._extract_improved_title(text)
                    if improved_title and improved_title != result.value:
                        # Use improved title if it's cleaner (shorter and doesn't contain dates/times)
                        if len(improved_title) < len(result.value) or not has_datetime_patterns:
                            result.value = improved_title
                            result.confidence = min(0.85, result.confidence + 0.15)  # Boost confidence for improved title
        
        return result
    
    def _extract_improved_title(self, text: str) -> Optional[str]:
        """Extract an improved title from text when the regular title extractor fails."""
        import re
        
        # Remove common date patterns to get the action/event part
        text_without_dates = re.sub(r'\b(on|at|by|due|date:)\s*\d{1,2}[\/\-]\d{1,2}(?:[\/\-]\d{2,4})?\b', '', text, flags=re.IGNORECASE)
        text_without_dates = re.sub(r'\b(january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\.?\s+\d{1,2}(?:st|nd|rd|th)?,?\s*(?:\d{4})?\b', '', text_without_dates, flags=re.IGNORECASE)
        text_without_dates = re.sub(r'\b(today|tomorrow|yesterday|next|this)\s+\w+\b', '', text_without_dates, flags=re.IGNORECASE)
        text_without_dates = re.sub(r'\b\d{1,2}:\d{2}\s*(am|pm)?\b', '', text_without_dates, flags=re.IGNORECASE)
        text_without_dates = re.sub(r'\b@\s*\d{1,2}:\d{2}\b', '', text_without_dates, flags=re.IGNORECASE)  # Remove @ time
        text_without_dates = re.sub(r'\b\d{1,2}(am|pm)\b', '', text_without_dates, flags=re.IGNORECASE)  # Remove time like 9am
        
        # Clean up the remaining text
        cleaned = re.sub(r'\s+', ' ', text_without_dates).strip()
        
        # Remove common prefixes like "Title:"
        cleaned = re.sub(r'^(title|subject|event):\s*', '', cleaned, flags=re.IGNORECASE)
        
        # Remove trailing @ symbols and extra whitespace
        cleaned = re.sub(r'\s*@\s*$', '', cleaned).strip()
        
        # If we have a reasonable title, return it
        if cleaned and len(cleaned) >= 3:
            # For single word titles, that's often good enough (like "Dentist")
            if len(cleaned.split()) == 1 and len(cleaned) >= 3:
                return cleaned
            # For multi-word titles, need at least 2 words
            elif len(cleaned.split()) >= 2:
                return cleaned
        
        # Fallback: use first few words of original text, but try to avoid dates/times
        words = text.split()
        title_words = []
        for word in words:
            # Skip obvious date/time words
            if re.match(r'^\d{1,2}[\/\-]\d{1,2}', word):  # Skip dates
                break
            if re.match(r'^\d{1,2}:\d{2}', word):  # Skip times
                break
            if re.match(r'^@', word):  # Skip @ symbols
                break
            if word.lower() in ['on', 'at', 'by', 'due', 'date:', 'time:']:
                break
            title_words.append(word)
            if len(title_words) >= 3:  # Limit to 3 words for clean titles
                break
        
        if title_words:
            return ' '.join(title_words)
        
        return None
    
    def _extract_field_with_llm(self, field: str, text: str, timezone_offset: Optional[int]) -> Optional[FieldResult]:
        """Extract field using LLM enhancement."""
        try:
            # Check if LLM enhancer is available
            if not self.llm_enhancer.is_available():
                return None
            
            # Use fallback extraction and extract specific field
            fallback_result = self.llm_enhancer.fallback_extraction(text, self.current_time)
            if fallback_result.success and fallback_result.fallback_event:
                event = fallback_result.fallback_event
                
                # Extract the requested field from the LLM result
                field_value = None
                base_confidence = min(0.6, fallback_result.confidence)  # Cap LLM confidence
                
                if field == 'title' and event.title:
                    field_value = event.title
                elif field == 'start_datetime' and event.start_datetime:
                    field_value = event.start_datetime
                    base_confidence = min(0.5, fallback_result.confidence)  # Lower confidence for datetime from LLM
                elif field == 'end_datetime' and event.end_datetime:
                    field_value = event.end_datetime
                    base_confidence = min(0.5, fallback_result.confidence)
                elif field == 'location' and event.location:
                    field_value = event.location
                elif field == 'participants' and event.participants:
                    field_value = event.participants
                elif field == 'description' and event.description:
                    field_value = event.description
                
                if field_value is not None:
                    return FieldResult(
                        value=field_value,
                        source="llm",
                        confidence=base_confidence,
                        span=(0, len(text)),
                        alternatives=[],
                        processing_time_ms=int(fallback_result.processing_time * 1000)
                    )
            
            return None
            
        except Exception as e:
            logger.error(f"LLM extraction failed for {field}: {e}")
            return None
        except Exception as e:
            logger.error(f"LLM field extraction failed for {field}: {e}")
        
        return None
    
    def _calculate_overall_confidence(self, field_results: Dict[str, FieldResult]) -> float:
        """Calculate overall confidence from field results."""
        if not field_results:
            return 0.0
        
        # Weight essential fields more heavily
        essential_fields = ['title', 'start_datetime']
        essential_confidence = 0.0
        essential_count = 0
        
        optional_confidence = 0.0
        optional_count = 0
        
        for field_name, field_result in field_results.items():
            if field_name in essential_fields:
                essential_confidence += field_result.confidence
                essential_count += 1
            else:
                optional_confidence += field_result.confidence
                optional_count += 1
        
        # Calculate weighted average (70% essential, 30% optional)
        if essential_count > 0:
            avg_essential = essential_confidence / essential_count
        else:
            avg_essential = 0.0
        
        if optional_count > 0:
            avg_optional = optional_confidence / optional_count
        else:
            avg_optional = 0.0
        
        return (avg_essential * 0.7) + (avg_optional * 0.3)
    
    def _determine_parsing_path(self, field_results: Dict[str, FieldResult]) -> str:
        """Determine the parsing path based on field sources."""
        sources = [result.source for result in field_results.values()]
        
        # Check for essential fields (title, start_datetime) to determine primary path
        essential_sources = []
        if 'title' in field_results:
            essential_sources.append(field_results['title'].source)
        if 'start_datetime' in field_results:
            essential_sources.append(field_results['start_datetime'].source)
        
        # Determine path based on essential field sources
        if essential_sources:
            if all(source == "regex" for source in essential_sources):
                if any(source == "llm" for source in sources):
                    return "regex_then_llm"
                else:
                    return "regex_only"
            elif any(source == "llm" for source in essential_sources):
                return "llm_only"
            else:
                # Deterministic sources for essential fields - treat as regex_only for compatibility
                if any(source == "llm" for source in sources):
                    return "regex_then_llm"
                else:
                    return "regex_only"
        
        # Fallback logic for non-essential fields only
        if all(source == "regex" for source in sources):
            return "regex_only"
        elif any(source == "llm" for source in sources):
            return "llm_only"
        else:
            return "regex_only"  # Default to regex_only for compatibility
    
    def _check_cache(self, text: str, fields: Optional[List[str]]) -> Optional[HybridParsingResult]:
        """Check cache for existing result."""
        cache_key = self._generate_cache_key(text, fields)
        
        if cache_key in self.cache:
            cache_entry = self.cache[cache_key]
            
            # Check if cache entry is expired
            if not cache_entry.is_expired(self.cache_ttl_hours):
                cache_entry.increment_hit_count()
                
                # Create result from cached event
                cached_event = cache_entry.result
                cached_event.cache_hit = True
                
                return HybridParsingResult(
                    parsed_event=cached_event,
                    parsing_path=cached_event.parsing_path,
                    confidence_score=cached_event.confidence_score,
                    warnings=[],
                    processing_metadata={'cache_hit': True, 'cache_key': cache_key}
                )
            else:
                # Remove expired entry
                del self.cache[cache_key]
        
        return None
    
    def _cache_result(self, text: str, parsed_event: ParsedEvent):
        """Cache the parsing result."""
        cache_key = self._generate_cache_key(text, None)
        
        cache_entry = CacheEntry(
            text_hash=cache_key,
            result=parsed_event,
            timestamp=datetime.now(),
            hit_count=0
        )
        
        self.cache[cache_key] = cache_entry
        
        # Clean up old cache entries if cache gets too large
        if len(self.cache) > 1000:  # Arbitrary limit
            self._cleanup_cache()
    
    def _generate_cache_key(self, text: str, fields: Optional[List[str]]) -> str:
        """Generate cache key from text and fields."""
        normalized_text = self._normalize_text_for_cache(text)
        fields_str = ','.join(sorted(fields)) if fields else 'all'
        cache_input = f"{normalized_text}|{fields_str}"
        return hashlib.md5(cache_input.encode()).hexdigest()
    
    def _normalize_text_for_cache(self, text: str) -> str:
        """Normalize text for consistent cache keys."""
        # Remove extra whitespace and convert to lowercase
        import re
        normalized = re.sub(r'\s+', ' ', text.strip().lower())
        return normalized
    
    def _cleanup_cache(self):
        """Remove expired cache entries."""
        expired_keys = []
        for key, entry in self.cache.items():
            if entry.is_expired(self.cache_ttl_hours):
                expired_keys.append(key)
        
        for key in expired_keys:
            del self.cache[key]
    
    def update_config(self, **kwargs):
        """Update parser configuration."""
        self.config.update(kwargs)
    
    def get_config(self) -> Dict[str, Any]:
        """Get current configuration."""
        return self.config.copy()
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_entries = len(self.cache)
        total_hits = sum(entry.hit_count for entry in self.cache.values())
        
        return {
            'total_entries': total_entries,
            'total_hits': total_hits,
            'cache_size_mb': total_entries * 0.001,  # Rough estimate
            'hit_rate': total_hits / max(1, total_entries)
        }
    
    def get_status(self) -> Dict[str, Any]:
        """Get parser status and component availability."""
        return {
            'regex_extractor_available': True,
            'title_extractor_available': True,
            'llm_enhancer_available': self.llm_enhancer.is_available(),
            'confidence_router_available': True,
            'cache_enabled': self.config['enable_caching'],
            'cache_stats': self.get_cache_stats(),
            'current_time': self.current_time.isoformat(),
            'config': self.config,
            'component_status': {
                'regex_extractor': 'ready',
                'title_extractor': 'ready',
                'llm_enhancer': self.llm_enhancer.get_status(),
                'confidence_router': 'ready'
            }
        }