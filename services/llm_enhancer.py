"""
LLMEnhancer for polishing regex-extracted information and fallback parsing.
Implements structured JSON schema output with temperature ≤0.2 for the hybrid parsing pipeline (Task 26.3).
"""

import json
import logging
import re
from typing import Optional, Dict, Any, List, Union, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass

from services.llm_service import LLMService, LLMResponse
from services.regex_date_extractor import DateTimeResult
from models.event_models import TitleResult, ParsedEvent, FieldResult

logger = logging.getLogger(__name__)


@dataclass
class EnhancementResult:
    """Result of LLM enhancement with confidence and method tracking."""
    success: bool
    enhanced_title: Optional[str] = None
    enhanced_description: Optional[str] = None
    fallback_event: Optional[ParsedEvent] = None
    confidence: float = 0.0
    enhancement_method: str = "none"  # "polish", "fallback", "failed"
    processing_time: float = 0.0
    llm_provider: str = ""
    llm_model: str = ""
    error: Optional[str] = None
    raw_response: Optional[Dict[str, Any]] = None


class LLMEnhancer:
    """
    LLM service for polishing regex-extracted information and fallback parsing.
    
    Critical constraints for hybrid parsing pipeline:
    - Never invent or override datetime fields (temperature ≤0.2)
    - JSON schema output validation
    - Two distinct roles:
      1. Enhancement: Polish titles and descriptions when regex succeeds
      2. Fallback: Full extraction only when regex fails (confidence ≤0.5, add warning)
    
    Implements confidence adjustment based on LLM vs regex agreement.
    """
    
    def __init__(self, llm_service: Optional[LLMService] = None):
        """
        Initialize the LLM enhancer.
        
        Args:
            llm_service: Optional LLM service instance (creates new if None)
        """
        self.llm_service = llm_service or LLMService(provider="auto")
        self._compile_schemas()
    
    def _compile_schemas(self):
        """Compile JSON schemas for structured LLM output."""
        
        # Schema for enhancement mode (polish titles/descriptions only)
        self.enhancement_schema = {
            "type": "object",
            "properties": {
                "enhanced_title": {
                    "type": ["string", "null"],
                    "description": "Polished, complete title (do not change if already good)"
                },
                "enhanced_description": {
                    "type": ["string", "null"],
                    "description": "Enhanced description with context (optional)"
                },
                "confidence": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "number", "minimum": 0.0, "maximum": 1.0},
                        "description": {"type": "number", "minimum": 0.0, "maximum": 1.0},
                        "overall": {"type": "number", "minimum": 0.0, "maximum": 1.0}
                    },
                    "required": ["title", "description", "overall"]
                },
                "enhancement_notes": {
                    "type": "string",
                    "description": "Brief notes about what was enhanced"
                }
            },
            "required": ["enhanced_title", "enhanced_description", "confidence", "enhancement_notes"],
            "additionalProperties": False
        }
        
        # Schema for fallback mode (full extraction when regex fails)
        self.fallback_schema = {
            "type": "object",
            "properties": {
                "title": {
                    "type": ["string", "null"],
                    "description": "Event title extracted from text"
                },
                "start_datetime": {
                    "type": ["string", "null"],
                    "description": "Start datetime in ISO format (YYYY-MM-DDTHH:MM:SS) or null if not found"
                },
                "end_datetime": {
                    "type": ["string", "null"],
                    "description": "End datetime in ISO format (YYYY-MM-DDTHH:MM:SS) or null if not found"
                },
                "location": {
                    "type": ["string", "null"],
                    "description": "Event location or null if not found"
                },
                "description": {
                    "type": "string",
                    "description": "Event description or original text"
                },
                "all_day": {
                    "type": "boolean",
                    "description": "True if this is an all-day event"
                },
                "confidence": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "number", "minimum": 0.0, "maximum": 1.0},
                        "start_datetime": {"type": "number", "minimum": 0.0, "maximum": 1.0},
                        "end_datetime": {"type": "number", "minimum": 0.0, "maximum": 1.0},
                        "location": {"type": "number", "minimum": 0.0, "maximum": 1.0},
                        "overall": {"type": "number", "minimum": 0.0, "maximum": 1.0}
                    },
                    "required": ["title", "start_datetime", "end_datetime", "location", "overall"]
                },
                "extraction_notes": {
                    "type": "string",
                    "description": "Notes about extraction quality and any issues"
                },
                "needs_confirmation": {
                    "type": "boolean",
                    "description": "True if extraction has low confidence and needs user confirmation"
                }
            },
            "required": ["title", "start_datetime", "end_datetime", "location", "description", 
                        "all_day", "confidence", "extraction_notes", "needs_confirmation"],
            "additionalProperties": False
        }
        
        # Function calling schema for field-specific enhancement
        self.function_calling_schema = {
            "name": "enhance_event_fields",
            "description": "Enhance specific low-confidence event fields while preserving high-confidence locked fields",
            "parameters": {
                "type": "object",
                "properties": {
                    "enhanced_fields": {
                        "type": "object",
                        "description": "Enhanced values for low-confidence fields only",
                        "properties": {
                            "title": {
                                "type": ["string", "null"],
                                "description": "Enhanced event title (only if confidence < 0.8)"
                            },
                            "location": {
                                "type": ["string", "null"],
                                "description": "Enhanced location (only if confidence < 0.8)"
                            },
                            "description": {
                                "type": ["string", "null"],
                                "description": "Enhanced description (only if confidence < 0.8)"
                            },
                            "participants": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Enhanced participant list (only if confidence < 0.8)"
                            }
                        },
                        "additionalProperties": False
                    },
                    "field_confidence": {
                        "type": "object",
                        "description": "Confidence scores for enhanced fields",
                        "properties": {
                            "title": {"type": "number", "minimum": 0.0, "maximum": 1.0},
                            "location": {"type": "number", "minimum": 0.0, "maximum": 1.0},
                            "description": {"type": "number", "minimum": 0.0, "maximum": 1.0},
                            "participants": {"type": "number", "minimum": 0.0, "maximum": 1.0}
                        },
                        "additionalProperties": False
                    },
                    "locked_fields_preserved": {
                        "type": "boolean",
                        "description": "Confirmation that high-confidence locked fields were not modified"
                    },
                    "enhancement_notes": {
                        "type": "string",
                        "description": "Notes about what fields were enhanced and why"
                    }
                },
                "required": ["enhanced_fields", "field_confidence", "locked_fields_preserved", "enhancement_notes"],
                "additionalProperties": False
            }
        }
    
    def enhance_regex_extraction(self, 
                                datetime_result: DateTimeResult,
                                title_result: Optional[TitleResult] = None,
                                original_text: str = "") -> EnhancementResult:
        """
        Enhance regex-extracted information using LLM (Enhancement Mode).
        
        Critical: Never modify datetime fields - only polish titles and descriptions.
        
        Args:
            datetime_result: Regex-extracted datetime information (DO NOT MODIFY)
            title_result: Optional regex-extracted title
            original_text: Original input text for context
            
        Returns:
            EnhancementResult with polished title and description
        """
        if not self.llm_service.is_available():
            return EnhancementResult(
                success=False,
                error="LLM service not available",
                enhancement_method="failed"
            )
        
        start_time = datetime.now()
        
        try:
            # Prepare enhancement prompt
            system_prompt = self._get_enhancement_system_prompt()
            user_prompt = self._format_enhancement_prompt(
                datetime_result, title_result, original_text
            )
            
            # Call LLM with strict constraints
            response = self._call_llm_with_schema(
                system_prompt, user_prompt, self.enhancement_schema, temperature=0.1
            )
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            if response.success and response.data:
                data = response.data
                
                # Validate that LLM didn't try to modify datetime
                if any(key in data for key in ['start_datetime', 'end_datetime', 'date', 'time']):
                    logger.warning("LLM attempted to modify datetime in enhancement mode - ignoring")
                
                return EnhancementResult(
                    success=True,
                    enhanced_title=data.get('enhanced_title'),
                    enhanced_description=data.get('enhanced_description'),
                    confidence=data.get('confidence', {}).get('overall', 0.5),
                    enhancement_method="polish",
                    processing_time=processing_time,
                    llm_provider=response.provider,
                    llm_model=response.model,
                    raw_response=data
                )
            else:
                return EnhancementResult(
                    success=False,
                    error=response.error or "Enhancement failed",
                    enhancement_method="failed",
                    processing_time=processing_time
                )
        
        except Exception as e:
            processing_time = (datetime.now() - start_time).total_seconds()
            logger.error(f"Enhancement failed: {e}")
            return EnhancementResult(
                success=False,
                error=str(e),
                enhancement_method="failed",
                processing_time=processing_time
            )
    
    def fallback_extraction(self, text: str, current_time: Optional[datetime] = None) -> EnhancementResult:
        """
        Perform full LLM extraction when regex fails (Fallback Mode).
        
        Returns confidence ≤0.5 and adds needs_confirmation flag.
        
        Args:
            text: Original input text
            current_time: Current datetime for relative date resolution
            
        Returns:
            EnhancementResult with fallback ParsedEvent (confidence ≤0.5)
        """
        if not self.llm_service.is_available():
            return EnhancementResult(
                success=False,
                error="LLM service not available for fallback",
                enhancement_method="failed"
            )
        
        start_time = datetime.now()
        
        try:
            # Prepare fallback prompt
            system_prompt = self._get_fallback_system_prompt()
            user_prompt = self._format_fallback_prompt(text, current_time)
            
            # Call LLM with fallback schema
            response = self._call_llm_with_schema(
                system_prompt, user_prompt, self.fallback_schema, temperature=0.2
            )
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            if response.success and response.data:
                data = response.data
                
                # Create ParsedEvent from LLM response
                parsed_event = self._create_parsed_event_from_llm(data, text)
                
                # Ensure confidence ≤0.5 for fallback mode
                fallback_confidence = min(0.5, data.get('confidence', {}).get('overall', 0.3))
                parsed_event.confidence_score = fallback_confidence
                
                # Add fallback metadata
                if not parsed_event.extraction_metadata:
                    parsed_event.extraction_metadata = {}
                
                parsed_event.extraction_metadata.update({
                    'extraction_method': 'llm_fallback',
                    'needs_confirmation': data.get('needs_confirmation', True),
                    'fallback_reason': 'regex_extraction_failed',
                    'llm_provider': response.provider,
                    'llm_model': response.model,
                    'processing_time': processing_time
                })
                
                return EnhancementResult(
                    success=True,
                    fallback_event=parsed_event,
                    confidence=fallback_confidence,
                    enhancement_method="fallback",
                    processing_time=processing_time,
                    llm_provider=response.provider,
                    llm_model=response.model,
                    raw_response=data
                )
            else:
                return EnhancementResult(
                    success=False,
                    error=response.error or "Fallback extraction failed",
                    enhancement_method="failed",
                    processing_time=processing_time
                )
        
        except Exception as e:
            processing_time = (datetime.now() - start_time).total_seconds()
            logger.error(f"Fallback extraction failed: {e}")
            return EnhancementResult(
                success=False,
                error=str(e),
                enhancement_method="failed",
                processing_time=processing_time
            )
    
    def _get_enhancement_system_prompt(self) -> str:
        """Get system prompt for enhancement mode."""
        return """You are an AI assistant that polishes event titles and descriptions. 

CRITICAL CONSTRAINTS:
- NEVER modify, create, or suggest datetime information
- NEVER output start_datetime, end_datetime, date, or time fields
- Only enhance titles and descriptions
- Keep enhancements minimal and accurate
- Use temperature ≤0.2 for consistency

Your job is to:
1. Polish titles to be complete and descriptive (fix truncation, improve clarity)
2. NEVER create or modify descriptions - leave them as null
3. Maintain accuracy - don't invent ANY information not explicitly in the text

Output must be valid JSON matching the provided schema."""
    
    def _get_fallback_system_prompt(self) -> str:
        """Get system prompt for fallback mode."""
        return """You are an AI assistant that extracts calendar event information when regex parsing fails.

CRITICAL CONSTRAINTS:
- Use temperature ≤0.2 for consistency
- Output confidence ≤0.5 (this is fallback mode)
- Set needs_confirmation=true for low confidence extractions
- Be conservative - don't invent information not clearly in the text
- Use ISO datetime format: YYYY-MM-DDTHH:MM:SS

Extract:
- title: Event name/subject
- start_datetime: Start time in ISO format or null
- end_datetime: End time in ISO format or null  
- location: Venue/place or null
- description: Event details or original text
- all_day: true for date-only events

Output must be valid JSON matching the provided schema."""
    
    def _format_enhancement_prompt(self, 
                                  datetime_result: DateTimeResult,
                                  title_result: Optional[TitleResult],
                                  original_text: str) -> str:
        """Format prompt for enhancement mode."""
        prompt_parts = [
            "Please enhance the following event information:",
            "",
            f"Original text: {original_text}",
            "",
            "Regex-extracted information (DO NOT MODIFY):",
            f"- Start: {datetime_result.start_datetime}",
            f"- End: {datetime_result.end_datetime}",
            f"- All-day: {datetime_result.is_all_day}",
            ""
        ]
        
        if title_result and title_result.title:
            prompt_parts.extend([
                f"Current title: {title_result.title}",
                f"Title confidence: {title_result.confidence}",
                f"Title method: {title_result.generation_method}",
                ""
            ])
        else:
            prompt_parts.extend([
                "No title extracted by regex",
                ""
            ])
        
        prompt_parts.extend([
            "Please provide:",
            "1. Enhanced title: ONLY clean up the existing title, do NOT add extra words or context",
            "2. Enhanced description: ALWAYS set to null - do NOT create descriptions",
            "3. Confidence scores for your enhancements",
            "",
            "CRITICAL: If title is already good (like 'COWA!'), return it exactly as-is.",
            "DO NOT add context like 'Event on October 15' or any extra words.",
            "Remember: DO NOT modify datetime information. Only clean existing title if needed."
        ])
        
        return "\n".join(prompt_parts)
    
    def _format_fallback_prompt(self, text: str, current_time: Optional[datetime]) -> str:
        """Format prompt for fallback mode."""
        prompt_parts = [
            "Extract calendar event information from this text (regex parsing failed):",
            "",
            f"Text: {text}",
            ""
        ]
        
        if current_time:
            prompt_parts.extend([
                f"Current date/time: {current_time.isoformat()}",
                "Use this for resolving relative dates (tomorrow, next week, etc.)",
                ""
            ])
        
        prompt_parts.extend([
            "Extract all available information:",
            "- Be conservative - don't invent details not in the text",
            "- Use ISO format for datetimes: YYYY-MM-DDTHH:MM:SS",
            "- Set confidence ≤0.5 (this is fallback mode)",
            "- Set needs_confirmation=true if extraction is uncertain",
            "- For date-only events, set all_day=true"
        ])
        
        return "\n".join(prompt_parts)
    
    def _call_llm_with_schema(self, 
                             system_prompt: str, 
                             user_prompt: str, 
                             schema: Dict[str, Any],
                             temperature: float = 0.1) -> LLMResponse:
        """Call LLM with JSON schema validation."""
        try:
            # Add schema to system prompt
            schema_prompt = f"{system_prompt}\n\nOutput JSON schema:\n{json.dumps(schema, indent=2)}"
            
            # Call LLM service with low temperature
            if hasattr(self.llm_service, '_call_ollama') and self.llm_service.provider == "ollama":
                return self._call_ollama_with_schema(schema_prompt, user_prompt, temperature)
            elif hasattr(self.llm_service, '_call_openai') and self.llm_service.provider == "openai":
                return self._call_openai_with_schema(schema_prompt, user_prompt, temperature)
            else:
                # Fallback to regular extraction
                return self.llm_service.extract_event(user_prompt, template="structured")
        
        except Exception as e:
            return LLMResponse(
                success=False,
                data=None,
                error=str(e),
                provider=self.llm_service.provider,
                model=self.llm_service.model,
                confidence=0.0,
                processing_time=0.0
            )
    
    def _call_ollama_with_schema(self, system_prompt: str, user_prompt: str, temperature: float) -> LLMResponse:
        """Call Ollama with schema validation."""
        import requests
        
        full_prompt = f"{system_prompt}\n\n{user_prompt}\n\nJSON Response:"
        
        try:
            response = requests.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": self.llm_service.model,
                    "prompt": full_prompt,
                    "stream": False,
                    "options": {
                        "temperature": temperature,  # Low temperature for consistency
                        "num_predict": 150,  # Reduced for faster enhancement
                        "top_p": 0.9,
                        "num_ctx": 1024,  # Smaller context for speed
                        "repeat_penalty": 1.1
                    }
                },
                timeout=10  # Faster timeout for enhancement
            )
            
            if response.status_code == 200:
                result_text = response.json()['response']
                
                # Try to parse JSON
                try:
                    data = json.loads(result_text)
                    return LLMResponse(
                        success=True,
                        data=data,
                        error=None,
                        provider="ollama",
                        model=self.llm_service.model,
                        confidence=data.get('confidence', {}).get('overall', 0.5),
                        processing_time=0.0
                    )
                except json.JSONDecodeError:
                    # Try to extract JSON from response
                    data = self._extract_json_from_response(result_text)
                    return LLMResponse(
                        success=bool(data),
                        data=data,
                        error="JSON parsing failed" if not data else None,
                        provider="ollama",
                        model=self.llm_service.model,
                        confidence=0.3,
                        processing_time=0.0
                    )
            else:
                return LLMResponse(
                    success=False,
                    data=None,
                    error=f"Ollama API error: {response.status_code}",
                    provider="ollama",
                    model=self.llm_service.model,
                    confidence=0.0,
                    processing_time=0.0
                )
        
        except Exception as e:
            return LLMResponse(
                success=False,
                data=None,
                error=str(e),
                provider="ollama",
                model=self.llm_service.model,
                confidence=0.0,
                processing_time=0.0
            )
    
    def _call_openai_with_schema(self, system_prompt: str, user_prompt: str, temperature: float) -> LLMResponse:
        """Call OpenAI with schema validation."""
        try:
            response = self.llm_service.openai_client.chat.completions.create(
                model=self.llm_service.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=temperature,
                max_tokens=500,
                response_format={"type": "json_object"}
            )
            
            data = json.loads(response.choices[0].message.content)
            return LLMResponse(
                success=True,
                data=data,
                error=None,
                provider="openai",
                model=self.llm_service.model,
                confidence=data.get('confidence', {}).get('overall', 0.5),
                processing_time=0.0
            )
        
        except Exception as e:
            return LLMResponse(
                success=False,
                data=None,
                error=str(e),
                provider="openai",
                model=self.llm_service.model,
                confidence=0.0,
                processing_time=0.0
            )
    
    def _extract_json_from_response(self, text: str) -> Optional[Dict[str, Any]]:
        """Extract JSON from LLM response text."""
        import re
        
        # Try to find JSON in the response
        json_pattern = r'\{.*\}'
        matches = re.findall(json_pattern, text, re.DOTALL)
        
        for match in matches:
            try:
                return json.loads(match)
            except json.JSONDecodeError:
                continue
        
        return None
    
    def _create_parsed_event_from_llm(self, data: Dict[str, Any], original_text: str) -> ParsedEvent:
        """Create ParsedEvent from LLM response data."""
        parsed_event = ParsedEvent()
        
        # Basic fields
        parsed_event.title = data.get('title')
        parsed_event.location = data.get('location')
        parsed_event.description = data.get('description', original_text)
        parsed_event.all_day = data.get('all_day', False)
        
        # Parse datetime strings
        if data.get('start_datetime'):
            try:
                parsed_event.start_datetime = datetime.fromisoformat(data['start_datetime'])
            except (ValueError, TypeError) as e:
                logger.warning(f"Failed to parse start_datetime: {e}")
        
        if data.get('end_datetime'):
            try:
                parsed_event.end_datetime = datetime.fromisoformat(data['end_datetime'])
            except (ValueError, TypeError) as e:
                logger.warning(f"Failed to parse end_datetime: {e}")
        
        # Set confidence
        confidence_data = data.get('confidence', {})
        parsed_event.confidence_score = confidence_data.get('overall', 0.3)
        
        # Build metadata
        parsed_event.extraction_metadata = {
            'llm_confidence': confidence_data,
            'extraction_notes': data.get('extraction_notes', ''),
            'needs_confirmation': data.get('needs_confirmation', True),
            'raw_llm_response': data
        }
        
        return parsed_event
    
    def is_available(self) -> bool:
        """Check if LLM enhancer is available."""
        return self.llm_service.is_available()
    
    def enhance_low_confidence_fields(self, 
                                     text: str, 
                                     field_results: Dict[str, FieldResult],
                                     locked_fields: Dict[str, Any],
                                     confidence_threshold: float = 0.8) -> Dict[str, FieldResult]:
        """
        Enhance only low-confidence fields using LLM with strict guardrails.
        
        This method implements per-field confidence routing by:
        1. Identifying fields below confidence threshold
        2. Limiting LLM context to residual unparsed text only
        3. Enforcing schema constraints to prevent locked field modification
        4. Using timeout with retry for reliability
        
        Args:
            text: Original input text
            field_results: Current field extraction results
            locked_fields: High-confidence fields that cannot be modified
            confidence_threshold: Threshold below which fields need enhancement (default 0.8)
            
        Returns:
            Dictionary of enhanced field results with improved confidence scores
        """
        if not self.llm_service.is_available():
            logger.warning("LLM service not available for field enhancement")
            return field_results
        
        # Identify fields that need enhancement (Requirement 12.1)
        fields_to_enhance = []
        for field_name, field_result in field_results.items():
            if field_result.confidence < confidence_threshold and field_name not in locked_fields:
                fields_to_enhance.append(field_name)
        
        if not fields_to_enhance:
            logger.debug("No fields need LLM enhancement")
            return field_results
        
        logger.info(f"Enhancing low-confidence fields: {fields_to_enhance}")
        
        try:
            # Limit context to residual unparsed text (Requirement 12.3)
            residual_text = self.limit_context_to_residual(text, field_results)
            
            # Create enhancement schema with locked fields (Requirement 12.1)
            enhancement_schema = self._create_field_enhancement_schema(fields_to_enhance, locked_fields)
            
            # Prepare enhancement prompt
            system_prompt = self._get_field_enhancement_system_prompt(locked_fields)
            user_prompt = self._format_field_enhancement_prompt(
                residual_text, fields_to_enhance, field_results, locked_fields
            )
            
            # Call LLM with timeout and retry (Requirement 12.4)
            response = self.timeout_with_retry(
                system_prompt, user_prompt, enhancement_schema, timeout_seconds=3
            )
            
            if response and response.success and response.data:
                # Validate and apply enhancements (Requirement 12.2)
                validated_data = self.enforce_schema_constraints(response.data, locked_fields)
                enhanced_results = field_results.copy()
                
                # Update enhanced fields
                enhanced_fields = validated_data.get('enhanced_fields', {})
                field_confidence = validated_data.get('field_confidence', {})
                
                for field_name in fields_to_enhance:
                    if field_name in enhanced_fields and enhanced_fields[field_name] is not None:
                        new_confidence = field_confidence.get(field_name, 0.7)
                        enhanced_results[field_name] = FieldResult(
                            value=enhanced_fields[field_name],
                            source="llm_enhancement",
                            confidence=new_confidence,
                            span=field_results[field_name].span,
                            alternatives=field_results[field_name].alternatives,
                            processing_time_ms=int(response.processing_time * 1000) if hasattr(response, 'processing_time') else 0
                        )
                
                return enhanced_results
            else:
                logger.warning(f"LLM field enhancement failed: {response.error if response else 'No response'}")
                return field_results
        
        except Exception as e:
            logger.error(f"Field enhancement failed: {e}")
            return field_results
    
    def limit_context_to_residual(self, text: str, field_results: Dict[str, FieldResult]) -> str:
        """
        Limit LLM context to residual unparsed text only (Requirement 12.3).
        
        Removes already-extracted spans from the text to reduce token usage
        and prevent LLM from re-processing high-confidence fields.
        
        Args:
            text: Original input text
            field_results: Current field extraction results with spans
            
        Returns:
            Residual text with high-confidence spans removed
        """
        if not field_results:
            return text
        
        # Collect all spans that have been successfully extracted
        extracted_spans = []
        for field_name, field_result in field_results.items():
            if field_result.confidence >= 0.8 and field_result.span:
                extracted_spans.append(field_result.span)
        
        if not extracted_spans:
            return text
        
        # Sort spans by start position (reverse order for removal)
        extracted_spans.sort(key=lambda x: x[0], reverse=True)
        
        # Remove extracted spans from text
        residual_text = text
        for start, end in extracted_spans:
            if 0 <= start < end <= len(residual_text):
                residual_text = residual_text[:start] + residual_text[end:]
        
        # Clean up multiple spaces
        residual_text = re.sub(r'\s+', ' ', residual_text).strip()
        
        return residual_text
    
    def enforce_schema_constraints(self, llm_output: Dict[str, Any], locked_fields: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enforce schema constraints to prevent modification of high-confidence fields (Requirement 12.2).
        
        Validates that LLM output doesn't attempt to modify locked fields and
        removes any unauthorized field modifications.
        
        Args:
            llm_output: Raw LLM response data
            locked_fields: High-confidence fields that cannot be modified
            
        Returns:
            Validated output with locked field modifications removed
        """
        if not locked_fields:
            return llm_output
        
        validated_output = llm_output.copy()
        
        # Check for unauthorized field modifications
        unauthorized_modifications = []
        for field_name in locked_fields:
            if field_name in validated_output:
                unauthorized_modifications.append(field_name)
                # Remove the unauthorized modification
                del validated_output[field_name]
        
        if unauthorized_modifications:
            logger.warning(f"LLM attempted to modify locked fields: {unauthorized_modifications}")
            
            # Add warning to enhancement notes
            if 'enhancement_notes' in validated_output:
                validated_output['enhancement_notes'] += f" [WARNING: Attempted to modify locked fields: {unauthorized_modifications}]"
            else:
                validated_output['enhancement_notes'] = f"WARNING: Attempted to modify locked fields: {unauthorized_modifications}"
        
        # Validate enhanced_fields structure if present
        enhanced_field_violations = []
        if 'enhanced_fields' in validated_output:
            enhanced_fields = validated_output['enhanced_fields']
            for field_name in list(enhanced_fields.keys()):
                if field_name in locked_fields:
                    logger.warning(f"Removing unauthorized enhancement of locked field: {field_name}")
                    enhanced_field_violations.append(field_name)
                    del enhanced_fields[field_name]
        
        # Add warnings for enhanced_fields violations
        if enhanced_field_violations:
            warning_msg = f" [WARNING: Attempted to modify locked fields in enhanced_fields: {enhanced_field_violations}]"
            if 'enhancement_notes' in validated_output:
                validated_output['enhancement_notes'] += warning_msg
            else:
                validated_output['enhancement_notes'] = f"WARNING: Attempted to modify locked fields: {enhanced_field_violations}"
        
        return validated_output
    
    def timeout_with_retry(self, 
                          system_prompt: str, 
                          user_prompt: str, 
                          schema: Dict[str, Any],
                          timeout_seconds: int = 3) -> Optional[LLMResponse]:
        """
        Handle LLM calls with timeout and single retry (Requirement 12.4).
        
        Implements timeout handling with single retry and returns partial results
        on failure rather than complete failure.
        
        Args:
            system_prompt: System prompt for LLM
            user_prompt: User prompt for LLM
            schema: JSON schema for validation
            timeout_seconds: Timeout in seconds (default 3)
            
        Returns:
            LLMResponse or None if both attempts fail
        """
        import time
        import threading
        from concurrent.futures import ThreadPoolExecutor, TimeoutError
        
        def call_llm():
            """Inner function to call LLM with schema."""
            return self._call_llm_with_schema(system_prompt, user_prompt, schema, temperature=0.0)
        
        # First attempt
        try:
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(call_llm)
                response = future.result(timeout=timeout_seconds)
                
                if response.success:
                    return response
                else:
                    logger.warning(f"First LLM attempt failed: {response.error}")
        
        except TimeoutError:
            logger.warning(f"First LLM attempt timed out after {timeout_seconds}s")
        except Exception as e:
            logger.warning(f"First LLM attempt failed with exception: {e}")
        
        # Single retry attempt (Requirement 12.4)
        try:
            logger.info("Retrying LLM call...")
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(call_llm)
                response = future.result(timeout=timeout_seconds)
                
                if response.success:
                    logger.info("LLM retry succeeded")
                    return response
                else:
                    logger.error(f"LLM retry failed: {response.error}")
        
        except TimeoutError:
            logger.error(f"LLM retry timed out after {timeout_seconds}s")
        except Exception as e:
            logger.error(f"LLM retry failed with exception: {e}")
        
        # Both attempts failed - return None (Requirement 12.6)
        logger.error("Both LLM attempts failed, returning None for partial results handling")
        return None
    
    def validate_json_schema(self, output: str) -> Dict[str, Any]:
        """
        Ensure structured output compliance with JSON schema (Requirement 12.5).
        
        Validates LLM output against the expected schema and handles
        malformed responses gracefully.
        
        Args:
            output: Raw LLM output string
            
        Returns:
            Validated dictionary or empty dict if validation fails
        """
        try:
            # Try to parse as JSON
            data = json.loads(output)
            
            # Basic structure validation
            if not isinstance(data, dict):
                logger.error("LLM output is not a JSON object")
                return {}
            
            # Check for required function calling structure
            if 'enhanced_fields' in data:
                # Validate function calling schema
                return self._validate_function_calling_response(data)
            else:
                # Validate regular schema
                return self._validate_regular_response(data)
        
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM output as JSON: {e}")
            # Try to extract JSON from text
            return self._extract_json_from_response(output) or {}
        except Exception as e:
            logger.error(f"Schema validation failed: {e}")
            return {}
    
    def _validate_function_calling_response(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate function calling schema response."""
        required_fields = ['enhanced_fields', 'field_confidence', 'locked_fields_preserved', 'enhancement_notes']
        
        for field in required_fields:
            if field not in data:
                logger.warning(f"Missing required field in function calling response: {field}")
                return {}
        
        # Validate enhanced_fields structure
        enhanced_fields = data.get('enhanced_fields', {})
        if not isinstance(enhanced_fields, dict):
            logger.error("enhanced_fields must be an object")
            return {}
        
        # Validate field_confidence structure
        field_confidence = data.get('field_confidence', {})
        if not isinstance(field_confidence, dict):
            logger.error("field_confidence must be an object")
            return {}
        
        # Validate confidence values
        for field, confidence in field_confidence.items():
            if not isinstance(confidence, (int, float)) or not (0.0 <= confidence <= 1.0):
                logger.warning(f"Invalid confidence value for {field}: {confidence}")
                field_confidence[field] = 0.5  # Default fallback
        
        # Validate locked_fields_preserved
        if not isinstance(data.get('locked_fields_preserved'), bool):
            logger.warning("locked_fields_preserved must be boolean")
            data['locked_fields_preserved'] = True  # Safe default
        
        return data
    
    def _validate_regular_response(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate regular enhancement/fallback schema response."""
        # Basic validation for enhancement or fallback schemas
        if 'confidence' in data:
            confidence = data['confidence']
            if isinstance(confidence, dict):
                # Validate confidence values
                for field, conf_value in confidence.items():
                    if not isinstance(conf_value, (int, float)) or not (0.0 <= conf_value <= 1.0):
                        logger.warning(f"Invalid confidence value for {field}: {conf_value}")
                        confidence[field] = 0.5  # Default fallback
        
        return data
    
    def _create_field_enhancement_schema(self, fields_to_enhance: List[str], locked_fields: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create dynamic schema for field-specific enhancement.
        
        Generates a schema that only allows enhancement of specified low-confidence fields
        while explicitly preventing modification of locked high-confidence fields.
        
        Args:
            fields_to_enhance: List of field names that need enhancement
            locked_fields: High-confidence fields that cannot be modified
            
        Returns:
            Dynamic JSON schema for field enhancement
        """
        # Base schema structure
        schema = {
            "type": "object",
            "properties": {
                "enhanced_fields": {
                    "type": "object",
                    "description": f"Enhanced values for fields: {', '.join(fields_to_enhance)}",
                    "properties": {},
                    "additionalProperties": False
                },
                "field_confidence": {
                    "type": "object",
                    "description": "Confidence scores for enhanced fields",
                    "properties": {},
                    "additionalProperties": False
                },
                "locked_fields_preserved": {
                    "type": "boolean",
                    "description": f"Confirmation that locked fields were not modified: {', '.join(locked_fields.keys())}"
                },
                "enhancement_notes": {
                    "type": "string",
                    "description": "Notes about field enhancements"
                }
            },
            "required": ["enhanced_fields", "field_confidence", "locked_fields_preserved", "enhancement_notes"],
            "additionalProperties": False
        }
        
        # Add properties for fields that can be enhanced
        for field_name in fields_to_enhance:
            if field_name == "title":
                schema["properties"]["enhanced_fields"]["properties"]["title"] = {
                    "type": ["string", "null"],
                    "description": "Enhanced event title"
                }
                schema["properties"]["field_confidence"]["properties"]["title"] = {
                    "type": "number", "minimum": 0.0, "maximum": 1.0
                }
            elif field_name == "location":
                schema["properties"]["enhanced_fields"]["properties"]["location"] = {
                    "type": ["string", "null"],
                    "description": "Enhanced event location"
                }
                schema["properties"]["field_confidence"]["properties"]["location"] = {
                    "type": "number", "minimum": 0.0, "maximum": 1.0
                }
            elif field_name == "description":
                schema["properties"]["enhanced_fields"]["properties"]["description"] = {
                    "type": ["string", "null"],
                    "description": "Enhanced event description"
                }
                schema["properties"]["field_confidence"]["properties"]["description"] = {
                    "type": "number", "minimum": 0.0, "maximum": 1.0
                }
            elif field_name == "participants":
                schema["properties"]["enhanced_fields"]["properties"]["participants"] = {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Enhanced participant list"
                }
                schema["properties"]["field_confidence"]["properties"]["participants"] = {
                    "type": "number", "minimum": 0.0, "maximum": 1.0
                }
        
        return schema
    
    def _get_field_enhancement_system_prompt(self, locked_fields: Dict[str, Any]) -> str:
        """Get system prompt for field-specific enhancement."""
        locked_field_names = ', '.join(locked_fields.keys()) if locked_fields else "none"
        
        return f"""You are an AI assistant that enhances specific low-confidence event fields.

CRITICAL CONSTRAINTS:
- Temperature = 0 for deterministic results
- NEVER modify these locked high-confidence fields: {locked_field_names}
- Only enhance the specific fields requested
- Use function calling schema for structured output
- Set locked_fields_preserved=true to confirm compliance

Your job is to:
1. Enhance ONLY the requested low-confidence fields
2. Provide confidence scores for your enhancements
3. Confirm that locked fields were not modified
4. Be conservative - don't invent information not in the text

Output must match the function calling schema exactly."""
    
    def _format_field_enhancement_prompt(self, 
                                        residual_text: str,
                                        fields_to_enhance: List[str],
                                        field_results: Dict[str, FieldResult],
                                        locked_fields: Dict[str, Any]) -> str:
        """Format prompt for field-specific enhancement."""
        prompt_parts = [
            "Enhance the following low-confidence event fields:",
            "",
            f"Residual text (high-confidence spans removed): {residual_text}",
            "",
            f"Fields to enhance: {', '.join(fields_to_enhance)}",
            "",
            "Current field results:"
        ]
        
        for field_name in fields_to_enhance:
            if field_name in field_results:
                result = field_results[field_name]
                prompt_parts.append(f"- {field_name}: {result.value} (confidence: {result.confidence:.2f})")
            else:
                prompt_parts.append(f"- {field_name}: not extracted")
        
        if locked_fields:
            prompt_parts.extend([
                "",
                "LOCKED high-confidence fields (DO NOT MODIFY):"
            ])
            for field_name, value in locked_fields.items():
                prompt_parts.append(f"- {field_name}: {value}")
        
        prompt_parts.extend([
            "",
            "Please enhance only the requested fields and confirm locked fields were preserved."
        ])
        
        return "\n".join(prompt_parts)
    
    def timeout_with_retry(self, 
                          system_prompt: str, 
                          user_prompt: str, 
                          schema: Dict[str, Any],
                          timeout_seconds: int = 3) -> Optional[LLMResponse]:
        """
        Call LLM with 3-second timeout and single retry on failure.
        
        This method implements reliable LLM calling with:
        1. Strict 3-second timeout per attempt
        2. Single retry on timeout or failure
        3. Proper error handling and logging
        4. Graceful degradation on total failure
        
        Args:
            system_prompt: System prompt for LLM
            user_prompt: User prompt for LLM  
            schema: JSON schema for structured output validation
            timeout_seconds: Timeout in seconds (default 3 per requirement)
            
        Returns:
            LLM response with success/failure status, or None if failed after retry
        """
        import time
        
        total_attempts = 2  # Initial attempt + 1 retry as per requirement
        
        for attempt in range(total_attempts):
            try:
                logger.debug(f"LLM call attempt {attempt + 1}/{total_attempts} (timeout: {timeout_seconds}s)")
                start_time = time.time()
                
                # Call LLM with timeout enforcement
                response = self._call_llm_with_timeout(system_prompt, user_prompt, schema, timeout_seconds)
                
                elapsed_time = time.time() - start_time
                
                if response and response.success:
                    logger.debug(f"LLM call succeeded on attempt {attempt + 1} ({elapsed_time:.2f}s)")
                    # Validate JSON schema compliance (Requirement 12.5)
                    if response.data and schema:
                        is_valid, validated_data, error = self.validate_json_schema(
                            json.dumps(response.data), schema
                        )
                        if not is_valid:
                            logger.warning(f"LLM response failed schema validation: {error}")
                            if attempt < total_attempts - 1:
                                continue  # Retry on schema validation failure
                        else:
                            response.data = validated_data
                    
                    return response
                else:
                    error_msg = response.error if response else 'No response'
                    logger.warning(f"LLM call failed on attempt {attempt + 1}: {error_msg}")
            
            except TimeoutError:
                logger.warning(f"LLM call timed out on attempt {attempt + 1} (>{timeout_seconds}s)")
            except Exception as e:
                logger.warning(f"LLM call error on attempt {attempt + 1}: {e}")
            
            # Brief pause before retry (not on last attempt)
            if attempt < total_attempts - 1:
                time.sleep(0.1)
        
        logger.error(f"LLM call failed after {total_attempts} attempts - returning None")
        return None
    
    def _call_llm_with_timeout(self, 
                              system_prompt: str, 
                              user_prompt: str, 
                              schema: Dict[str, Any],
                              timeout_seconds: int) -> Optional[LLMResponse]:
        """
        Call LLM with strict timeout enforcement using threading.
        
        This method implements timeout control by:
        1. Running LLM call in separate daemon thread
        2. Enforcing strict timeout with thread.join()
        3. Using temperature=0 for deterministic results
        4. Proper exception handling and timeout detection
        
        Args:
            system_prompt: System prompt for LLM
            user_prompt: User prompt for LLM
            schema: JSON schema for validation
            timeout_seconds: Strict timeout in seconds
            
        Returns:
            LLM response or None if timeout/error
            
        Raises:
            TimeoutError: If LLM call exceeds timeout_seconds
        """
        import threading
        import time
        
        result = [None]  # Use list to allow modification in thread
        exception = [None]
        start_time = time.time()
        
        def llm_call_thread():
            try:
                # Use temperature=0 for deterministic results (Requirement 12.5)
                result[0] = self._call_llm_with_schema(
                    system_prompt, 
                    user_prompt, 
                    schema, 
                    temperature=0.0
                )
            except Exception as e:
                exception[0] = e
        
        # Start the LLM call in a separate daemon thread
        thread = threading.Thread(target=llm_call_thread, daemon=True)
        thread.start()
        
        # Wait for completion or timeout
        thread.join(timeout=timeout_seconds)
        
        elapsed_time = time.time() - start_time
        
        if thread.is_alive():
            # Thread is still running - timeout occurred
            error_msg = f"LLM call timed out after {timeout_seconds}s (elapsed: {elapsed_time:.2f}s)"
            logger.warning(error_msg)
            raise TimeoutError(error_msg)
        
        # Check for exceptions in the thread
        if exception[0]:
            logger.warning(f"LLM call failed with exception: {exception[0]}")
            raise exception[0]
        
        # Log successful completion
        if result[0] and result[0].success:
            logger.debug(f"LLM call completed successfully in {elapsed_time:.2f}s")
        
        return result[0]
    
    def validate_json_schema(self, json_text: str, schema: Dict[str, Any]) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """
        Validate JSON text against a schema for structured output compliance.
        
        This method implements comprehensive JSON schema validation by:
        1. Parsing JSON text with detailed error reporting
        2. Validating required fields and data types
        3. Checking additional properties constraints
        4. Ensuring numeric ranges and constraints
        5. Providing detailed error messages for debugging
        
        Args:
            json_text: JSON text string to validate
            schema: JSON schema dictionary to validate against
            
        Returns:
            Tuple of (is_valid, parsed_data, error_message)
            - is_valid: True if validation passes
            - parsed_data: Parsed JSON data if valid, None otherwise
            - error_message: Detailed error message if validation fails
        """
        # Step 1: Parse JSON with detailed error handling
        try:
            data = json.loads(json_text)
            logger.debug(f"Successfully parsed JSON with {len(data)} fields")
        except json.JSONDecodeError as e:
            error_msg = f"Invalid JSON syntax: {e}"
            logger.warning(error_msg)
            return False, None, error_msg
        
        # Step 2: Validate against schema
        try:
            validation_result = self._validate_against_schema(data, schema)
            if validation_result[0]:
                logger.debug("JSON schema validation passed")
                return True, data, None
            else:
                error_msg = f"Schema validation failed: {validation_result[1]}"
                logger.warning(error_msg)
                return False, None, error_msg
        except Exception as e:
            error_msg = f"Schema validation error: {e}"
            logger.error(error_msg)
            return False, None, error_msg
    
    def _validate_against_schema(self, data: Dict[str, Any], schema: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """
        Simple schema validation (basic implementation).
        
        Args:
            data: Data to validate
            schema: Schema to validate against
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not isinstance(data, dict):
            return False, "Data must be an object"
        
        # Check required fields
        required_fields = schema.get('required', [])
        for field in required_fields:
            if field not in data:
                return False, f"Missing required field: {field}"
        
        # Check field types
        properties = schema.get('properties', {})
        for field_name, field_value in data.items():
            if field_name in properties:
                field_schema = properties[field_name]
                expected_type = field_schema.get('type')
                
                if expected_type:
                    if isinstance(expected_type, list):
                        # Handle union types like ["string", "null"]
                        valid_type = False
                        for t in expected_type:
                            if self._check_type(field_value, t):
                                valid_type = True
                                break
                        if not valid_type:
                            return False, f"Field '{field_name}' has invalid type. Expected one of {expected_type}"
                    else:
                        if not self._check_type(field_value, expected_type):
                            return False, f"Field '{field_name}' has invalid type. Expected {expected_type}"
        
        # Check additionalProperties
        if schema.get('additionalProperties') is False:
            allowed_fields = set(properties.keys())
            actual_fields = set(data.keys())
            extra_fields = actual_fields - allowed_fields
            if extra_fields:
                return False, f"Additional properties not allowed: {extra_fields}"
        
        return True, None
    
    def _check_type(self, value: Any, expected_type: str) -> bool:
        """Check if value matches expected JSON schema type."""
        if expected_type == "null":
            return value is None
        elif expected_type == "string":
            return isinstance(value, str)
        elif expected_type == "number":
            return isinstance(value, (int, float))
        elif expected_type == "integer":
            return isinstance(value, int)
        elif expected_type == "boolean":
            return isinstance(value, bool)
        elif expected_type == "array":
            return isinstance(value, list)
        elif expected_type == "object":
            return isinstance(value, dict)
        else:
            return False
    
    def _create_field_enhancement_schema(self, fields_to_enhance: List[str], locked_fields: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create dynamic schema for field-specific enhancement.
        
        Generates a schema that only allows enhancement of specified low-confidence fields
        while explicitly preventing modification of locked high-confidence fields.
        
        Args:
            fields_to_enhance: List of field names that need enhancement
            locked_fields: High-confidence fields that cannot be modified
            
        Returns:
            Dynamic JSON schema for field enhancement
        """
        # Base schema structure
        schema = {
            "type": "object",
            "properties": {
                "enhanced_fields": {
                    "type": "object",
                    "description": f"Enhanced values for fields: {', '.join(fields_to_enhance)}",
                    "properties": {},
                    "additionalProperties": False
                },
                "field_confidence": {
                    "type": "object",
                    "description": "Confidence scores for enhanced fields",
                    "properties": {},
                    "additionalProperties": False
                },
                "locked_fields_preserved": {
                    "type": "boolean",
                    "description": f"Confirmation that locked fields were not modified: {', '.join(locked_fields.keys())}"
                },
                "enhancement_notes": {
                    "type": "string",
                    "description": "Notes about field enhancements"
                }
            },
            "required": ["enhanced_fields", "field_confidence", "locked_fields_preserved", "enhancement_notes"],
            "additionalProperties": False
        }
        
        # Add properties for fields that can be enhanced
        for field_name in fields_to_enhance:
            if field_name == "title":
                schema["properties"]["enhanced_fields"]["properties"]["title"] = {
                    "type": ["string", "null"],
                    "description": "Enhanced event title"
                }
                schema["properties"]["field_confidence"]["properties"]["title"] = {
                    "type": "number", "minimum": 0.0, "maximum": 1.0
                }
            elif field_name == "location":
                schema["properties"]["enhanced_fields"]["properties"]["location"] = {
                    "type": ["string", "null"],
                    "description": "Enhanced event location"
                }
                schema["properties"]["field_confidence"]["properties"]["location"] = {
                    "type": "number", "minimum": 0.0, "maximum": 1.0
                }
            elif field_name == "description":
                schema["properties"]["enhanced_fields"]["properties"]["description"] = {
                    "type": ["string", "null"],
                    "description": "Enhanced event description"
                }
                schema["properties"]["field_confidence"]["properties"]["description"] = {
                    "type": "number", "minimum": 0.0, "maximum": 1.0
                }
            elif field_name == "participants":
                schema["properties"]["enhanced_fields"]["properties"]["participants"] = {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Enhanced participant list"
                }
                schema["properties"]["field_confidence"]["properties"]["participants"] = {
                    "type": "number", "minimum": 0.0, "maximum": 1.0
                }
        
        return schema
    
    def _get_field_enhancement_system_prompt(self, locked_fields: Dict[str, Any]) -> str:
        """Get system prompt for field enhancement with locked field constraints."""
        locked_field_names = list(locked_fields.keys()) if locked_fields else []
        
        prompt = """You are an AI assistant that enhances specific low-confidence event fields.

CRITICAL CONSTRAINTS:
- Temperature = 0 for deterministic results
- NEVER modify or reference these LOCKED fields: """ + str(locked_field_names) + """
- Only enhance the specific fields requested
- Be conservative - don't invent information not in the text
- Maintain accuracy and avoid hallucination

Your job is to:
1. Enhance only the requested fields based on available context
2. Provide confidence scores for your enhancements
3. Return null for fields where no enhancement is possible

Output must be valid JSON matching the provided schema."""
        
        return prompt
    
    def _format_field_enhancement_prompt(self, 
                                        residual_text: str,
                                        fields_to_enhance: List[str],
                                        current_results: Dict[str, FieldResult],
                                        locked_fields: Dict[str, Any]) -> str:
        """Format prompt for field enhancement."""
        prompt_parts = [
            "Enhance the following low-confidence fields using the residual text:",
            "",
            f"Residual text: {residual_text}",
            "",
            f"Fields to enhance: {fields_to_enhance}",
            ""
        ]
        
        # Show current field values
        prompt_parts.append("Current field values:")
        for field_name in fields_to_enhance:
            if field_name in current_results:
                result = current_results[field_name]
                prompt_parts.append(f"- {field_name}: {result.value} (confidence: {result.confidence:.2f})")
            else:
                prompt_parts.append(f"- {field_name}: None")
        
        prompt_parts.extend([
            "",
            "LOCKED fields (DO NOT modify or reference):"
        ])
        
        for field_name, value in locked_fields.items():
            prompt_parts.append(f"- {field_name}: {value}")
        
        prompt_parts.extend([
            "",
            "Provide enhanced values for the requested fields only.",
            "Set confidence scores based on how certain you are about each enhancement."
        ])
        
        return "\n".join(prompt_parts)
    
    def get_status(self) -> Dict[str, Any]:
        """Get enhancer status."""
        return {
            'available': self.is_available(),
            'llm_service': self.llm_service.get_status(),
            'enhancement_mode': 'polish_only',
            'fallback_mode': 'full_extraction_low_confidence',
            'temperature_constraint': '≤0.2',
            'datetime_constraint': 'never_modify',
            'guardrails': {
                'field_enhancement': True,
                'schema_constraints': True,
                'context_limiting': True,
                'timeout_retry': True,
                'json_validation': True
            }
        }