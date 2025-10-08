"""
Hybrid Event Parser - Integration focal point for Task 26.4.
Implements regex-first datetime extraction with LLM enhancement/fallback pipeline.
"""

import logging
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass

from services.regex_date_extractor import RegexDateExtractor, DateTimeResult
from services.title_extractor import TitleExtractor
from services.llm_enhancer import LLMEnhancer, EnhancementResult
from services.advanced_location_extractor import AdvancedLocationExtractor
from models.event_models import ParsedEvent, TitleResult

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
    
    Processing Flow: pre-clean → RegexDateExtractor → TitleExtractor → LLMEnhancer → confidence/warnings → response
    
    Parsing Strategy:
    - Regex ≥ 0.8: Use regex datetime + LLM enhancement for title/description
    - Regex < 0.8: Full LLM parsing with confidence ≤ 0.5 and warning flags
    - Mode support: hybrid|regex_only|llm_only for testing and debugging
    """
    
    def __init__(self, current_time: Optional[datetime] = None):
        """
        Initialize the hybrid parser.
        
        Args:
            current_time: Current datetime for relative date resolution
        """
        self.current_time = current_time or datetime.now()
        
        # Initialize components
        self.regex_extractor = RegexDateExtractor(current_time=self.current_time)
        self.title_extractor = TitleExtractor()
        self.location_extractor = AdvancedLocationExtractor()
        self.llm_enhancer = LLMEnhancer()
        
        # Configuration
        self.config = {
            'regex_confidence_threshold': 0.8,  # Threshold for LLM enhancement vs fallback
            'warning_confidence_threshold': 0.6,  # Threshold for warning flags
            'default_mode': 'hybrid',  # hybrid|regex_only|llm_only
            'enable_telemetry': True,
            'max_processing_time': 30.0  # seconds
        }
    
    def parse_event_text(self, 
                        text: str, 
                        mode: str = "hybrid",
                        timezone_offset: Optional[int] = None,
                        current_time: Optional[datetime] = None) -> HybridParsingResult:
        """
        Main parsing orchestration with mode support and confidence-based routing.
        
        Args:
            text: Input text to parse
            mode: Parsing mode ("hybrid", "regex_only", "llm_only")
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
        
        # Initialize result tracking
        warnings = []
        processing_metadata = {
            'original_text': text,
            'cleaned_text': cleaned_text,
            'mode': mode,
            'current_time': self.current_time.isoformat(),
            'timezone_offset': timezone_offset,
            'processing_start': start_time.isoformat()
        }
        
        try:
            if mode == "llm_only":
                return self._llm_only_parsing(cleaned_text, warnings, processing_metadata)
            elif mode == "regex_only":
                return self._regex_only_parsing(cleaned_text, warnings, processing_metadata)
            else:  # hybrid mode
                return self._hybrid_parsing(cleaned_text, timezone_offset, warnings, processing_metadata)
        
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
    
    def update_config(self, **kwargs):
        """Update parser configuration."""
        self.config.update(kwargs)
    
    def get_config(self) -> Dict[str, Any]:
        """Get current configuration."""
        return self.config.copy()
    
    def get_status(self) -> Dict[str, Any]:
        """Get parser status and component availability."""
        return {
            'regex_extractor_available': True,
            'title_extractor_available': True,
            'llm_enhancer_available': self.llm_enhancer.is_available(),
            'current_time': self.current_time.isoformat(),
            'config': self.config,
            'component_status': {
                'regex_extractor': 'ready',
                'title_extractor': 'ready',
                'llm_enhancer': self.llm_enhancer.get_status()
            }
        }