"""
LLMEnhancer for polishing regex-extracted information and fallback parsing.
Implements structured JSON schema output with temperature ≤0.2 for the hybrid parsing pipeline (Task 26.3).
"""

import json
import logging
from typing import Optional, Dict, Any, List, Union
from datetime import datetime, timedelta
from dataclasses import dataclass

from services.llm_service import LLMService, LLMResponse
from services.regex_date_extractor import DateTimeResult
from models.event_models import TitleResult, ParsedEvent

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
    
    def get_status(self) -> Dict[str, Any]:
        """Get enhancer status."""
        return {
            'available': self.is_available(),
            'llm_service': self.llm_service.get_status(),
            'enhancement_mode': 'polish_only',
            'fallback_mode': 'full_extraction_low_confidence',
            'temperature_constraint': '≤0.2',
            'datetime_constraint': 'never_modify'
        }