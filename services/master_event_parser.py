"""
MasterEventParser - Orchestration class for LLM-first event parsing strategy.

This class integrates all parsing components with LLM as the primary method,
comprehensive fallback mechanisms, and unified confidence scoring.
"""

import logging
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass

from models.event_models import ParsedEvent, ValidationResult, NormalizedEvent
from services.llm_service import LLMService, get_llm_service
from services.event_parser import EventParser
from services.format_aware_text_processor import FormatAwareTextProcessor, TextFormatResult
from services.advanced_location_extractor import AdvancedLocationExtractor, LocationResult
from services.smart_title_extractor import SmartTitleExtractor, TitleResult
from services.comprehensive_error_handler import ComprehensiveErrorHandler, ErrorHandlingResult

logger = logging.getLogger(__name__)


@dataclass
class ParsingResult:
    """
    Comprehensive result from the master parser with detailed metadata.
    """
    success: bool
    parsed_event: Optional[ParsedEvent] = None
    normalized_event: Optional[NormalizedEvent] = None
    confidence_score: float = 0.0
    parsing_method: str = ""  # "llm_primary", "llm_enhanced", "regex_fallback", "component_fallback"
    processing_time: float = 0.0
    format_result: Optional[TextFormatResult] = None
    error_handling_result: Optional[ErrorHandlingResult] = None
    validation_result: Optional[ValidationResult] = None
    metadata: Dict[str, Any] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'success': self.success,
            'parsed_event': self.parsed_event.to_dict() if self.parsed_event else None,
            'normalized_event': self.normalized_event.to_dict() if self.normalized_event else None,
            'confidence_score': self.confidence_score,
            'parsing_method': self.parsing_method,
            'processing_time': self.processing_time,
            'format_result': self.format_result.to_dict() if self.format_result else None,
            'metadata': self.metadata or {}
        }


class MasterEventParser:
    """
    Master orchestration class for LLM-first event parsing with comprehensive fallbacks.
    
    Execution Order:
    1. Text Format Processing (FormatAwareTextProcessor)
    2. LLM Primary Extraction (LLMService)
    3. Regex Fallback (EventParser) - if LLM fails or low confidence
    4. Component Enhancement (AdvancedLocationExtractor, SmartTitleExtractor)
    5. Error Handling & Validation (ComprehensiveErrorHandler)
    6. Cross-component Validation & Consistency Checking
    7. Unified Confidence Scoring & Normalization
    """
    
    def __init__(self, llm_service: Optional[LLMService] = None):
        """
        Initialize the master parser with all component services.
        
        Args:
            llm_service: Optional LLM service instance (will create default if None)
        """
        # Core services
        self.llm_service = llm_service or get_llm_service()
        self.format_processor = FormatAwareTextProcessor()
        self.regex_parser = EventParser()
        self.location_extractor = AdvancedLocationExtractor()
        self.title_extractor = SmartTitleExtractor()
        self.error_handler = ComprehensiveErrorHandler()
        
        # Configuration
        self.config = {
            'llm_first_strategy': True,
            'llm_confidence_threshold': 0.4,  # Switch to regex if LLM confidence below this
            'enable_component_enhancement': True,
            'enable_cross_validation': True,
            'enable_error_handling': True,
            'performance_optimization': True,
            'debug_logging': False,
            'max_processing_time': 30.0,  # seconds
            'unified_confidence_weights': {
                'llm_confidence': 0.4,
                'format_confidence': 0.2,
                'component_confidence': 0.2,
                'consistency_score': 0.2
            }
        }
        
        # Performance tracking
        self.performance_stats = {
            'total_parses': 0,
            'llm_successes': 0,
            'regex_fallbacks': 0,
            'component_enhancements': 0,
            'error_recoveries': 0,
            'average_processing_time': 0.0
        }
        
        logger.info("MasterEventParser initialized with LLM-first strategy")
    
    def parse_event(self, text: str, **kwargs) -> ParsingResult:
        """
        Main parsing method with LLM-first strategy and comprehensive fallbacks.
        
        Args:
            text: Input text containing event information
            **kwargs: Additional context (current_date, user_preferences, etc.)
            
        Returns:
            ParsingResult with comprehensive parsing information
        """
        start_time = datetime.now()
        
        try:
            # Step 1: Text Format Processing
            if self.config['debug_logging']:
                logger.debug(f"Starting parse for text: {text[:100]}...")
            
            format_result = self._process_text_format(text)
            processed_text = format_result.processed_text
            
            # Step 2: LLM Primary Extraction
            llm_result = None
            parsing_method = "unknown"
            
            if self.config['llm_first_strategy'] and self.llm_service.is_available():
                llm_result = self._llm_primary_extraction(processed_text, **kwargs)
                
                if llm_result and llm_result.confidence_score >= self.config['llm_confidence_threshold']:
                    parsing_method = "llm_primary"
                    if self.config['debug_logging']:
                        logger.debug(f"LLM primary extraction successful: confidence={llm_result.confidence_score}")
                else:
                    if self.config['debug_logging']:
                        logger.debug(f"LLM confidence too low or failed, falling back to regex")
                    llm_result = None
            
            # Step 3: Regex Fallback (if LLM failed or low confidence)
            regex_result = None
            if not llm_result:
                regex_result = self._regex_fallback_extraction(processed_text, **kwargs)
                if regex_result:
                    parsing_method = "regex_fallback"
                    self.performance_stats['regex_fallbacks'] += 1
                    if self.config['debug_logging']:
                        logger.debug(f"Regex fallback successful: confidence={regex_result.confidence_score}")
            
            # Select primary result
            primary_result = llm_result or regex_result
            
            if not primary_result:
                return self._handle_no_parsing_result(text, format_result, start_time)
            
            # Step 4: Component Enhancement (optional)
            enhanced_result = primary_result
            if self.config['enable_component_enhancement']:
                enhanced_result = self._enhance_with_components(
                    primary_result, processed_text, llm_result is not None
                )
                if enhanced_result != primary_result:
                    parsing_method += "_enhanced"
                    self.performance_stats['component_enhancements'] += 1
            
            # Step 5: Error Handling & Validation
            error_result = None
            if self.config['enable_error_handling']:
                error_result = self._handle_errors_and_validate(
                    enhanced_result, text, self.llm_service.is_available()
                )
                
                if error_result.success and error_result.resolved_event:
                    enhanced_result = error_result.resolved_event
                    if error_result.user_action_taken or error_result.fallback_used:
                        parsing_method += "_error_handled"
                        self.performance_stats['error_recoveries'] += 1
            
            # Step 6: Cross-component Validation & Consistency Checking
            if self.config['enable_cross_validation']:
                enhanced_result = self._cross_validate_components(enhanced_result, processed_text)
            
            # Step 7: Unified Confidence Scoring & Normalization
            final_confidence = self._calculate_unified_confidence(
                enhanced_result, format_result, llm_result, regex_result
            )
            enhanced_result.confidence_score = final_confidence
            
            # Create normalized event
            normalized_event = self._create_normalized_event(enhanced_result)
            
            # Calculate processing time
            processing_time = (datetime.now() - start_time).total_seconds()
            
            # Update performance stats
            self._update_performance_stats(processing_time, llm_result is not None)
            
            # Build comprehensive result
            result = ParsingResult(
                success=True,
                parsed_event=enhanced_result,
                normalized_event=normalized_event,
                confidence_score=final_confidence,
                parsing_method=parsing_method,
                processing_time=processing_time,
                format_result=format_result,
                error_handling_result=error_result,
                metadata=self._build_parsing_metadata(
                    enhanced_result, format_result, llm_result, regex_result, **kwargs
                )
            )
            
            if self.config['debug_logging']:
                logger.debug(f"Parse completed: method={parsing_method}, confidence={final_confidence:.2f}, time={processing_time:.2f}s")
            
            return result
            
        except Exception as e:
            processing_time = (datetime.now() - start_time).total_seconds()
            logger.error(f"Master parser failed: {e}")
            
            return ParsingResult(
                success=False,
                confidence_score=0.0,
                parsing_method="failed",
                processing_time=processing_time,
                metadata={'error': str(e), 'original_text': text}
            )
    
    def _process_text_format(self, text: str) -> TextFormatResult:
        """Process text format and normalize content."""
        try:
            return self.format_processor.process_text(text)
        except Exception as e:
            logger.warning(f"Format processing failed: {e}")
            # Return basic result
            from services.format_aware_text_processor import TextFormatResult, TextFormat
            return TextFormatResult(
                processed_text=text,
                original_text=text,
                detected_format=TextFormat.PLAIN_TEXT,
                confidence=0.5
            )
    
    def _llm_primary_extraction(self, text: str, **kwargs) -> Optional[ParsedEvent]:
        """Perform LLM-based primary extraction."""
        try:
            if not self.llm_service.is_available():
                return None
            
            # Add current date context if not provided
            if 'current_date' not in kwargs:
                kwargs['current_date'] = datetime.now().strftime('%Y-%m-%d')
            
            parsed_event = self.llm_service.llm_extract_event(text, **kwargs)
            
            if parsed_event and parsed_event.confidence_score > 0:
                self.performance_stats['llm_successes'] += 1
                return parsed_event
            
            return None
            
        except Exception as e:
            logger.warning(f"LLM extraction failed: {e}")
            return None
    
    def _regex_fallback_extraction(self, text: str, **kwargs) -> Optional[ParsedEvent]:
        """Perform regex-based fallback extraction."""
        try:
            # Use the existing EventParser for regex-based extraction
            parsed_event = self.regex_parser.parse_text(text, **kwargs)
            
            if parsed_event and parsed_event.confidence_score > 0:
                # Mark as regex fallback
                if not parsed_event.extraction_metadata:
                    parsed_event.extraction_metadata = {}
                parsed_event.extraction_metadata['extraction_method'] = 'regex_fallback'
                return parsed_event
            
            return None
            
        except Exception as e:
            logger.warning(f"Regex fallback failed: {e}")
            return None
    
    def _enhance_with_components(self, parsed_event: ParsedEvent, text: str, 
                               llm_was_primary: bool) -> ParsedEvent:
        """Enhance parsing results with specialized component extractors."""
        try:
            enhanced_event = parsed_event
            enhancements_made = []
            
            # Location enhancement (if location is missing or low confidence)
            location_confidence = self._get_field_confidence(parsed_event, 'location')
            if not parsed_event.location or location_confidence < 0.6:
                location_results = self.location_extractor.extract_locations(text)
                if location_results and location_results[0].confidence > location_confidence:
                    enhanced_event.location = location_results[0].location
                    enhancements_made.append('location')
                    
                    # Update metadata
                    if not enhanced_event.extraction_metadata:
                        enhanced_event.extraction_metadata = {}
                    enhanced_event.extraction_metadata['location_enhanced'] = True
                    enhanced_event.extraction_metadata['location_enhancement_confidence'] = location_results[0].confidence
            
            # Title enhancement (if title is missing or low confidence)
            title_confidence = self._get_field_confidence(parsed_event, 'title')
            if not parsed_event.title or title_confidence < 0.6:
                # Use SmartTitleExtractor as LLM fallback service
                if llm_was_primary:
                    # LLM was primary, use title extractor to validate/enhance
                    llm_result = {
                        'title': parsed_event.title,
                        'confidence': {'title': title_confidence}
                    }
                    title_result = self.title_extractor.extract_with_llm_fallback(text, llm_result)
                else:
                    # Regex was primary, use title extractor as enhancement
                    title_result = self.title_extractor.extract_title_fallback(text, "regex_primary")
                
                if title_result.title and title_result.confidence > title_confidence:
                    enhanced_event.title = title_result.title
                    enhancements_made.append('title')
                    
                    # Update metadata
                    if not enhanced_event.extraction_metadata:
                        enhanced_event.extraction_metadata = {}
                    enhanced_event.extraction_metadata['title_enhanced'] = True
                    enhanced_event.extraction_metadata['title_enhancement_confidence'] = title_result.confidence
            
            # Update overall metadata if enhancements were made
            if enhancements_made:
                if not enhanced_event.extraction_metadata:
                    enhanced_event.extraction_metadata = {}
                enhanced_event.extraction_metadata['component_enhancements'] = enhancements_made
                enhanced_event.extraction_metadata['enhancement_timestamp'] = datetime.now().isoformat()
            
            return enhanced_event
            
        except Exception as e:
            logger.warning(f"Component enhancement failed: {e}")
            return parsed_event
    
    def _handle_errors_and_validate(self, parsed_event: ParsedEvent, original_text: str, 
                                  llm_available: bool) -> ErrorHandlingResult:
        """Handle errors and validate the parsed event."""
        try:
            return self.error_handler.handle_parsing_errors(
                parsed_event, original_text, llm_available
            )
        except Exception as e:
            logger.warning(f"Error handling failed: {e}")
            # Return success result to continue processing
            return ErrorHandlingResult(
                success=True,
                resolved_event=parsed_event,
                error_type="error_handler_failed",
                error_message=f"Error handler failed: {e}"
            )
    
    def _cross_validate_components(self, parsed_event: ParsedEvent, text: str) -> ParsedEvent:
        """Perform cross-component validation and consistency checking."""
        try:
            # Validate field consistency
            consistency_issues = self.error_handler.validate_field_consistency(parsed_event, text)
            
            if consistency_issues:
                # Add consistency warnings to metadata
                if not parsed_event.extraction_metadata:
                    parsed_event.extraction_metadata = {}
                parsed_event.extraction_metadata['consistency_issues'] = consistency_issues
                parsed_event.extraction_metadata['consistency_check_timestamp'] = datetime.now().isoformat()
                
                # Reduce confidence slightly for consistency issues
                parsed_event.confidence_score *= 0.95
            
            return parsed_event
            
        except Exception as e:
            logger.warning(f"Cross-validation failed: {e}")
            return parsed_event
    
    def _calculate_unified_confidence(self, parsed_event: ParsedEvent, 
                                    format_result: TextFormatResult,
                                    llm_result: Optional[ParsedEvent],
                                    regex_result: Optional[ParsedEvent]) -> float:
        """Calculate unified confidence score across all extraction methods."""
        try:
            weights = self.config['unified_confidence_weights']
            
            # Base confidence from the parsing method
            base_confidence = parsed_event.confidence_score
            
            # LLM confidence component
            llm_confidence = 0.0
            if llm_result:
                llm_confidence = llm_result.confidence_score
            elif regex_result:
                # If regex was used, give it moderate confidence
                llm_confidence = 0.6
            
            # Format confidence component
            format_confidence = format_result.confidence if format_result else 0.5
            
            # Component confidence (average of enhanced fields)
            component_confidence = base_confidence
            metadata = parsed_event.extraction_metadata or {}
            if metadata.get('component_enhancements'):
                # Boost confidence if components enhanced the result
                component_confidence = min(1.0, base_confidence * 1.1)
            
            # Consistency score
            consistency_score = 1.0
            if metadata.get('consistency_issues'):
                # Reduce score based on number of issues
                num_issues = len(metadata['consistency_issues'])
                consistency_score = max(0.5, 1.0 - (num_issues * 0.1))
            
            # Calculate weighted average
            unified_confidence = (
                weights['llm_confidence'] * llm_confidence +
                weights['format_confidence'] * format_confidence +
                weights['component_confidence'] * component_confidence +
                weights['consistency_score'] * consistency_score
            )
            
            # Ensure confidence is within valid range
            return max(0.0, min(1.0, unified_confidence))
            
        except Exception as e:
            logger.warning(f"Unified confidence calculation failed: {e}")
            return parsed_event.confidence_score
    
    def _create_normalized_event(self, parsed_event: ParsedEvent) -> NormalizedEvent:
        """Create normalized event output with standardized format."""
        try:
            # Ensure we have required fields for NormalizedEvent
            if not parsed_event.title:
                raise ValueError("Cannot create NormalizedEvent: title is required")
            
            if not parsed_event.start_datetime:
                raise ValueError("Cannot create NormalizedEvent: start_datetime is required")
            
            # Use end_datetime or calculate default
            end_datetime = parsed_event.end_datetime
            if not end_datetime:
                end_datetime = parsed_event.start_datetime + timedelta(hours=1)
            
            return NormalizedEvent(
                title=parsed_event.title,
                start_datetime=parsed_event.start_datetime,
                end_datetime=end_datetime,
                location=parsed_event.location,
                description=parsed_event.description or "",
                confidence_score=parsed_event.confidence_score,
                field_confidence={
                    'title': self._get_field_confidence(parsed_event, 'title'),
                    'start_datetime': self._get_field_confidence(parsed_event, 'start_datetime'),
                    'end_datetime': self._get_field_confidence(parsed_event, 'end_datetime'),
                    'location': self._get_field_confidence(parsed_event, 'location'),
                    'description': self._get_field_confidence(parsed_event, 'description')
                },
                extraction_metadata=parsed_event.extraction_metadata or {},
                quality_score=self._calculate_quality_score(parsed_event)
            )
        except Exception as e:
            logger.warning(f"Normalization failed: {e}")
            # Return basic normalized event
            return NormalizedEvent(
                title=getattr(parsed_event, 'title', None) or "Untitled Event",
                start_datetime=getattr(parsed_event, 'start_datetime', None),
                end_datetime=getattr(parsed_event, 'end_datetime', None),
                location=getattr(parsed_event, 'location', None),
                description=getattr(parsed_event, 'description', None) or "",
                confidence_score=getattr(parsed_event, 'confidence_score', 0.0),
                field_confidence={},
                parsing_metadata={'normalization_error': str(e)},
                quality_score=0.5
            )
    
    def _get_field_confidence(self, parsed_event: ParsedEvent, field_name: str) -> float:
        """Get confidence score for a specific field."""
        metadata = parsed_event.extraction_metadata or {}
        
        # Check for field-specific confidence
        field_confidence_key = f'{field_name}_confidence'
        if field_confidence_key in metadata:
            return metadata[field_confidence_key]
        
        # Check for LLM field confidence
        llm_confidence = metadata.get('llm_confidence', {})
        if isinstance(llm_confidence, dict) and field_name in llm_confidence:
            return llm_confidence[field_name]
        
        # Check if field was enhanced
        if metadata.get(f'{field_name}_enhanced'):
            enhancement_confidence = metadata.get(f'{field_name}_enhancement_confidence', 0.7)
            return enhancement_confidence
        
        # Default to overall confidence
        return parsed_event.confidence_score
    
    def _calculate_quality_score(self, parsed_event: ParsedEvent) -> float:
        """Calculate overall quality score for the parsed event."""
        try:
            score = 0.0
            
            # Title quality (25%)
            if parsed_event.title and len(parsed_event.title.strip()) >= 3:
                score += 0.25
            
            # DateTime quality (35%)
            if parsed_event.start_datetime:
                score += 0.25
                if parsed_event.end_datetime:
                    score += 0.10
            
            # Location quality (15%)
            if parsed_event.location and len(parsed_event.location.strip()) >= 3:
                score += 0.15
            
            # Description quality (10%)
            if parsed_event.description and len(parsed_event.description.strip()) >= 10:
                score += 0.10
            
            # Confidence bonus (15%)
            confidence_bonus = parsed_event.confidence_score * 0.15
            score += confidence_bonus
            
            return min(1.0, score)
            
        except Exception as e:
            logger.warning(f"Quality score calculation failed: {e}")
            return 0.5
    
    def _build_parsing_metadata(self, parsed_event: ParsedEvent, format_result: TextFormatResult,
                              llm_result: Optional[ParsedEvent], regex_result: Optional[ParsedEvent],
                              **kwargs) -> Dict[str, Any]:
        """Build comprehensive parsing metadata."""
        metadata = {
            'master_parser_version': '1.0',
            'parsing_timestamp': datetime.now().isoformat(),
            'llm_available': self.llm_service.is_available(),
            'llm_used': llm_result is not None,
            'regex_used': regex_result is not None,
            'format_processing': {
                'detected_format': format_result.detected_format.value if format_result else 'unknown',
                'format_confidence': format_result.confidence if format_result else 0.0,
                'processing_steps': format_result.processing_steps if format_result else []
            },
            'component_services': {
                'format_processor': True,
                'llm_service': self.llm_service.is_available(),
                'regex_parser': True,
                'location_extractor': self.config['enable_component_enhancement'],
                'title_extractor': self.config['enable_component_enhancement'],
                'error_handler': self.config['enable_error_handling']
            },
            'configuration': {
                'llm_first_strategy': self.config['llm_first_strategy'],
                'llm_confidence_threshold': self.config['llm_confidence_threshold'],
                'component_enhancement': self.config['enable_component_enhancement'],
                'cross_validation': self.config['enable_cross_validation']
            },
            'performance_stats': self.performance_stats.copy(),
            'context': kwargs
        }
        
        # Merge with event-specific metadata
        if parsed_event.extraction_metadata:
            metadata['event_metadata'] = parsed_event.extraction_metadata
        
        return metadata
    
    def _handle_no_parsing_result(self, text: str, format_result: Optional[TextFormatResult], 
                                start_time: datetime) -> ParsingResult:
        """Handle case where no parsing method succeeded."""
        processing_time = (datetime.now() - start_time).total_seconds()
        
        return ParsingResult(
            success=False,
            confidence_score=0.0,
            parsing_method="no_result",
            processing_time=processing_time,
            format_result=format_result,
            metadata={
                'error': 'No parsing method succeeded',
                'original_text': text,
                'llm_available': self.llm_service.is_available(),
                'format_processed': format_result is not None
            }
        )
    
    def _update_performance_stats(self, processing_time: float, llm_used: bool):
        """Update performance statistics."""
        self.performance_stats['total_parses'] += 1
        
        # Update average processing time
        total = self.performance_stats['total_parses']
        current_avg = self.performance_stats['average_processing_time']
        self.performance_stats['average_processing_time'] = (
            (current_avg * (total - 1) + processing_time) / total
        )
    
    # ===== PUBLIC INTERFACE METHODS =====
    
    def parse_text(self, text: str, **kwargs) -> ParsedEvent:
        """
        Simple interface that returns just the ParsedEvent (for compatibility).
        
        Args:
            text: Input text containing event information
            **kwargs: Additional context
            
        Returns:
            ParsedEvent object (or empty event if parsing failed)
        """
        result = self.parse_event(text, **kwargs)
        
        if result.success and result.parsed_event:
            return result.parsed_event
        else:
            # Return empty event for compatibility
            return ParsedEvent(
                description=text,
                confidence_score=0.0,
                extraction_metadata={'master_parser_failed': True, 'error': 'No parsing result'}
            )
    
    def parse_multiple_events(self, text: str, **kwargs) -> List[ParsedEvent]:
        """
        Parse text that may contain multiple events.
        
        Args:
            text: Input text that may contain multiple events
            **kwargs: Additional context
            
        Returns:
            List of ParsedEvent objects
        """
        try:
            # First, try to detect multiple events using format processor
            format_result = self.format_processor.process_text(text)
            
            if format_result.multiple_events_detected:
                segments = self.format_processor.extract_event_segments(format_result)
                events = []
                
                for segment in segments:
                    if segment.strip():
                        parsed_event = self.parse_text(segment, **kwargs)
                        if parsed_event.confidence_score > 0.2:  # Minimum threshold
                            events.append(parsed_event)
                
                return events if events else [self.parse_text(text, **kwargs)]
            else:
                # Single event
                return [self.parse_text(text, **kwargs)]
                
        except Exception as e:
            logger.warning(f"Multiple event parsing failed: {e}")
            # Fallback to single event parsing
            return [self.parse_text(text, **kwargs)]
    
    def get_parsing_status(self) -> Dict[str, Any]:
        """Get current parsing service status and performance statistics."""
        return {
            'master_parser_ready': True,
            'llm_service_status': self.llm_service.get_status(),
            'component_services': {
                'format_processor': True,
                'regex_parser': True,
                'location_extractor': True,
                'title_extractor': True,
                'error_handler': True
            },
            'configuration': self.config.copy(),
            'performance_stats': self.performance_stats.copy()
        }
    
    def configure(self, **kwargs):
        """Update parser configuration."""
        for key, value in kwargs.items():
            if key in self.config:
                self.config[key] = value
                logger.info(f"Updated config: {key} = {value}")
            else:
                logger.warning(f"Unknown config key: {key}")
    
    def reset_performance_stats(self):
        """Reset performance statistics."""
        self.performance_stats = {
            'total_parses': 0,
            'llm_successes': 0,
            'regex_fallbacks': 0,
            'component_enhancements': 0,
            'error_recoveries': 0,
            'average_processing_time': 0.0
        }
        logger.info("Performance statistics reset")


# Global instance for easy access
_master_parser = None

def get_master_parser() -> MasterEventParser:
    """Get the global master parser instance."""
    global _master_parser
    if _master_parser is None:
        _master_parser = MasterEventParser()
    return _master_parser