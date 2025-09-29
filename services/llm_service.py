"""
LLM Service for calendar event extraction.
Provides a unified interface for LLM-based event parsing with Ollama integration.
"""

import os
import json
import logging
from typing import Optional, Dict, Any, List, Union
from datetime import datetime
from dataclasses import dataclass

from services.llm_prompts import get_prompt_templates, PromptTemplate
from models.event_models import ParsedEvent

logger = logging.getLogger(__name__)

# Optional imports - graceful handling of missing dependencies
try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    logger.warning("Requests not available - Ollama integration disabled")

try:
    import openai
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


@dataclass
class LLMResponse:
    """Response from LLM service."""
    success: bool
    data: Optional[Dict[str, Any]]
    error: Optional[str]
    provider: str
    model: str
    confidence: float
    processing_time: float


class LLMService:
    """
    LLM service for calendar event extraction with Ollama integration.
    
    Provides structured event extraction using local Ollama models with fallback
    to other providers when available. Designed for the LLM-first parsing strategy.
    """
    
    def __init__(self, provider: str = "auto", model: Optional[str] = None, **kwargs):
        """
        Initialize LLM service.
        
        Args:
            provider: LLM provider ("auto", "ollama", "openai", "groq")
            model: Model name (provider-specific)
            **kwargs: Additional configuration
        """
        self.provider = provider
        self.model = model
        self.config = kwargs
        self.prompt_templates = get_prompt_templates()
        
        # Provider clients
        self.ollama_available = False
        self.openai_client = None
        
        # Auto-detect best provider
        if provider == "auto":
            self.provider = self._detect_best_provider()
        
        # Initialize the selected provider
        self._initialize_provider()
        
        logger.info(f"LLM Service initialized: provider={self.provider}, model={self.model}")
    
    def _detect_best_provider(self) -> str:
        """Detect the best available LLM provider."""
        # Check Ollama first (preferred for local inference)
        if self._check_ollama_available():
            return "ollama"
        
        # Check OpenAI API
        if self._check_openai_available():
            return "openai"
        
        # Check Groq API
        if self._check_groq_available():
            return "groq"
        
        # Fallback to heuristic mode
        return "heuristic"
    
    def _check_ollama_available(self) -> bool:
        """Check if Ollama is running locally."""
        if not REQUESTS_AVAILABLE:
            return False
        
        try:
            response = requests.get("http://localhost:11434/api/tags", timeout=3)
            return response.status_code == 200
        except:
            return False
    
    def _check_openai_available(self) -> bool:
        """Check if OpenAI API is available."""
        return OPENAI_AVAILABLE and bool(self.config.get('openai_api_key') or 
                                        os.getenv('OPENAI_API_KEY'))
    
    def _check_groq_available(self) -> bool:
        """Check if Groq API is available."""
        return bool(self.config.get('groq_api_key') or os.getenv('GROQ_API_KEY'))
    
    def _initialize_provider(self):
        """Initialize the selected provider."""
        if self.provider == "ollama":
            self._initialize_ollama()
        elif self.provider == "openai":
            self._initialize_openai()
        elif self.provider == "groq":
            self._initialize_groq()
        else:
            logger.info("Using heuristic fallback mode")
    
    def _initialize_ollama(self):
        """Initialize Ollama provider."""
        if not REQUESTS_AVAILABLE:
            logger.error("Requests library required for Ollama")
            self.provider = "heuristic"
            return
        
        # Set default model for event extraction
        if not self.model:
            self.model = "llama3.2:3b"  # Good balance of speed and accuracy
        
        # Verify Ollama is available
        if self._check_ollama_available():
            self.ollama_available = True
            # Check if model is available
            try:
                response = requests.get("http://localhost:11434/api/tags", timeout=5)
                if response.status_code == 200:
                    available_models = [m['name'] for m in response.json().get('models', [])]
                    if self.model not in available_models:
                        logger.warning(f"Model {self.model} not found. Available: {available_models}")
                        # Try to pull the model
                        self._pull_ollama_model(self.model)
            except Exception as e:
                logger.error(f"Error checking Ollama models: {e}")
        else:
            logger.error("Ollama not available")
            self.provider = "heuristic"
    
    def _initialize_openai(self):
        """Initialize OpenAI provider."""
        if not OPENAI_AVAILABLE:
            logger.error("OpenAI library not available")
            self.provider = "heuristic"
            return
        
        api_key = self.config.get('openai_api_key') or os.getenv('OPENAI_API_KEY')
        if not api_key:
            logger.error("OpenAI API key not found")
            self.provider = "heuristic"
            return
        
        if not self.model:
            self.model = "gpt-3.5-turbo"
        
        try:
            self.openai_client = OpenAI(api_key=api_key)
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI: {e}")
            self.provider = "heuristic"
    
    def _initialize_groq(self):
        """Initialize Groq provider."""
        api_key = self.config.get('groq_api_key') or os.getenv('GROQ_API_KEY')
        if not api_key:
            logger.error("Groq API key not found")
            self.provider = "heuristic"
            return
        
        if not self.model:
            self.model = "llama-3.1-8b-instant"
        
        self.config.update({
            'groq_api_key': api_key,
            'groq_base_url': "https://api.groq.com/openai/v1"
        })
    
    def _pull_ollama_model(self, model_name: str) -> bool:
        """Pull a model in Ollama."""
        try:
            logger.info(f"Pulling Ollama model: {model_name}")
            response = requests.post(
                "http://localhost:11434/api/pull",
                json={"name": model_name},
                timeout=300
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Error pulling model: {e}")
            return False
    
    def extract_event(self, text: str, **kwargs) -> LLMResponse:
        """
        Extract calendar event information from text using LLM.
        
        Args:
            text: Input text containing event information
            **kwargs: Additional context (current_date, context, etc.)
            
        Returns:
            LLMResponse with extracted event data
        """
        start_time = datetime.now()
        
        try:
            # Determine best template for this text
            template_name = kwargs.get('template', 
                                     self.prompt_templates.get_template_for_text_type(text))
            
            # Format the prompt
            system_prompt, user_prompt = self.prompt_templates.format_prompt(
                template_name, text, **kwargs
            )
            
            # Call the appropriate provider
            if self.provider == "ollama":
                result = self._call_ollama(system_prompt, user_prompt)
            elif self.provider == "openai":
                result = self._call_openai(system_prompt, user_prompt)
            elif self.provider == "groq":
                result = self._call_groq(system_prompt, user_prompt)
            else:
                result = self._fallback_extraction(text)
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            return LLMResponse(
                success=True,
                data=result,
                error=None,
                provider=self.provider,
                model=self.model,
                confidence=result.get('confidence', {}).get('overall', 0.5),
                processing_time=max(processing_time, 0.001)  # Ensure non-zero processing time
            )
            
        except Exception as e:
            processing_time = (datetime.now() - start_time).total_seconds()
            logger.error(f"LLM extraction failed: {e}")
            
            return LLMResponse(
                success=False,
                data=None,
                error=str(e),
                provider=self.provider,
                model=self.model,
                confidence=0.0,
                processing_time=processing_time
            )
    
    def _call_ollama(self, system_prompt: str, user_prompt: str) -> Dict[str, Any]:
        """Call Ollama local LLM."""
        if not self.ollama_available:
            raise Exception("Ollama not available")
        
        # Combine prompts for Ollama
        full_prompt = f"{system_prompt}\n\n{user_prompt}\n\nResponse:"
        
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": self.model,
                "prompt": full_prompt,
                "stream": False,
                "options": {
                    "temperature": 0.1,  # Low temperature for consistent extraction
                    "num_predict": 800,  # Enough tokens for detailed response
                    "top_p": 0.9
                }
            },
            timeout=60
        )
        
        if response.status_code != 200:
            raise Exception(f"Ollama API error: {response.status_code} - {response.text}")
        
        result_text = response.json()['response']
        
        # Try to parse as JSON
        try:
            return json.loads(result_text)
        except json.JSONDecodeError:
            # Fallback: try to extract JSON from text
            return self._extract_json_from_text(result_text)
    
    def _call_openai(self, system_prompt: str, user_prompt: str) -> Dict[str, Any]:
        """Call OpenAI API."""
        if not self.openai_client:
            raise Exception("OpenAI client not initialized")
        
        response = self.openai_client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.1,
            max_tokens=800,
            response_format={"type": "json_object"}
        )
        
        return json.loads(response.choices[0].message.content)
    
    def _call_groq(self, system_prompt: str, user_prompt: str) -> Dict[str, Any]:
        """Call Groq API."""
        headers = {
            "Authorization": f"Bearer {self.config['groq_api_key']}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.1,
            "max_tokens": 800
        }
        
        response = requests.post(
            f"{self.config['groq_base_url']}/chat/completions",
            headers=headers,
            json=data,
            timeout=30
        )
        
        if response.status_code != 200:
            raise Exception(f"Groq API error: {response.status_code}")
        
        result_text = response.json()['choices'][0]['message']['content']
        
        try:
            return json.loads(result_text)
        except json.JSONDecodeError:
            return self._extract_json_from_text(result_text)
    
    def _extract_json_from_text(self, text: str) -> Dict[str, Any]:
        """Extract JSON from text response when direct parsing fails."""
        import re
        
        # Try to find JSON in the text
        json_pattern = r'\{.*\}'
        matches = re.findall(json_pattern, text, re.DOTALL)
        
        for match in matches:
            try:
                return json.loads(match)
            except json.JSONDecodeError:
                continue
        
        # Fallback: create basic structure from text
        return {
            "title": None,
            "start_datetime": None,
            "end_datetime": None,
            "location": None,
            "description": text,
            "confidence": {
                "title": 0.1,
                "start_datetime": 0.1,
                "end_datetime": 0.1,
                "location": 0.1,
                "overall": 0.1
            },
            "extraction_notes": "Failed to parse LLM response as JSON"
        }
    
    def _fallback_extraction(self, text: str) -> Dict[str, Any]:
        """Fallback extraction when LLM is not available."""
        # Basic heuristic extraction
        import re
        from datetime import datetime, timedelta
        
        # Try to find basic patterns
        title = None
        start_datetime = None
        location = None
        
        # Simple title extraction (first few words)
        words = text.split()
        if len(words) >= 2:
            title = ' '.join(words[:4])  # First 4 words as title
        elif len(words) == 1:
            title = words[0]
        
        # Enhanced date/time pattern matching
        date_patterns = [
            r'\b\d{1,2}/\d{1,2}/\d{4}\b',  # MM/DD/YYYY
            r'\b\d{1,2}-\d{1,2}-\d{4}\b',  # MM-DD-YYYY
            r'\btomorrow\b',
            r'\btoday\b',
            r'\bnext \w+\b',
            r'\bmonday\b', r'\btuesday\b', r'\bwednesday\b', r'\bthursday\b',
            r'\bfriday\b', r'\bsaturday\b', r'\bsunday\b',
            r'\d{1,2}:\d{2}\s*(?:am|pm|a\.m|p\.m)',  # Time patterns
            r'\d{1,2}\s*(?:am|pm|a\.m|p\.m)',  # Simple time
            r'\bnoon\b', r'\bmidnight\b'
        ]
        
        # Check for any date/time indicators
        has_datetime = False
        for pattern in date_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                has_datetime = True
                break
        
        if has_datetime:
            # Use current date + reasonable time as placeholder
            base_time = datetime.now().replace(hour=14, minute=0, second=0, microsecond=0)
            
            # Try to extract specific time if present
            time_match = re.search(r'(\d{1,2})(?::(\d{2}))?\s*(?:am|pm|a\.m|p\.m)', text, re.IGNORECASE)
            if time_match:
                hour = int(time_match.group(1))
                minute = int(time_match.group(2)) if time_match.group(2) else 0
                
                # Handle AM/PM
                if 'pm' in text.lower() or 'p.m' in text.lower():
                    if hour != 12:
                        hour += 12
                elif 'am' in text.lower() or 'a.m' in text.lower():
                    if hour == 12:
                        hour = 0
                
                start_datetime = base_time.replace(hour=hour, minute=minute)
            else:
                start_datetime = base_time
        
        # Enhanced location extraction
        location_indicators = ['at ', 'in ', '@ ', 'room ', 'building ', 'office ']
        for indicator in location_indicators:
            if indicator in text.lower():
                parts = text.lower().split(indicator, 1)
                if len(parts) > 1:
                    location_part = parts[1].split()[:3]  # Next few words
                    if location_part:
                        location = ' '.join(location_part).strip('.,!?')
                        break
        
        return {
            "title": title,
            "start_datetime": start_datetime.isoformat() if start_datetime else None,
            "end_datetime": (start_datetime + timedelta(hours=1)).isoformat() if start_datetime else None,
            "location": location,
            "description": text,
            "confidence": {
                "title": 0.4 if title else 0.0,
                "start_datetime": 0.4 if start_datetime else 0.0,
                "end_datetime": 0.4 if start_datetime else 0.0,
                "location": 0.4 if location else 0.0,
                "overall": 0.3 if (title and start_datetime) else 0.2
            },
            "extraction_notes": "Heuristic fallback extraction used"
        }
    
    def llm_extract_event(self, text: str, **kwargs) -> ParsedEvent:
        """
        Extract event using LLM and return ParsedEvent object.
        
        Args:
            text: Input text containing event information
            **kwargs: Additional context
            
        Returns:
            ParsedEvent object with extracted information
        """
        response = self.extract_event(text, **kwargs)
        
        if not response.success:
            # Return empty event with error info
            return ParsedEvent(
                description=text,
                confidence_score=0.0,
                extraction_metadata={
                    'error': response.error,
                    'provider': response.provider,
                    'llm_available': False
                }
            )
        
        data = response.data
        
        # Convert LLM response to ParsedEvent
        parsed_event = ParsedEvent()
        parsed_event.title = data.get('title')
        parsed_event.description = data.get('description', text)
        
        # Parse datetime strings
        if data.get('start_datetime'):
            try:
                parsed_event.start_datetime = datetime.fromisoformat(data['start_datetime'])
            except (ValueError, TypeError):
                pass
        
        if data.get('end_datetime'):
            try:
                parsed_event.end_datetime = datetime.fromisoformat(data['end_datetime'])
            except (ValueError, TypeError):
                pass
        
        parsed_event.location = data.get('location')
        
        # Set confidence score
        confidence_data = data.get('confidence', {})
        parsed_event.confidence_score = confidence_data.get('overall', response.confidence)
        
        # Build extraction metadata
        parsed_event.extraction_metadata = {
            'llm_provider': response.provider,
            'llm_model': response.model,
            'processing_time': response.processing_time,
            'llm_confidence': confidence_data,
            'extraction_notes': data.get('extraction_notes', ''),
            'template_used': kwargs.get('template', 'auto-selected'),
            'llm_available': True,
            'raw_llm_response': data
        }
        
        # Add additional LLM-specific metadata
        if 'alternatives' in data:
            parsed_event.extraction_metadata['alternatives'] = data['alternatives']
        
        if 'ambiguities' in data:
            parsed_event.extraction_metadata['ambiguities'] = data['ambiguities']
        
        if 'missing_info' in data:
            parsed_event.extraction_metadata['missing_info'] = data['missing_info']
        
        return parsed_event
    
    def is_available(self) -> bool:
        """Check if LLM service is available."""
        return self.provider != "heuristic"
    
    def get_status(self) -> Dict[str, Any]:
        """Get current service status."""
        return {
            'provider': self.provider,
            'model': self.model,
            'available': self.is_available(),
            'ollama_available': self.ollama_available,
            'openai_available': bool(self.openai_client),
            'config': {k: v for k, v in self.config.items() if 'key' not in k.lower()}
        }
    
    def test_connection(self) -> bool:
        """Test the LLM connection with a simple query."""
        try:
            test_text = "Meeting tomorrow at 2pm"
            response = self.extract_event(test_text, current_date="2025-01-01")
            return response.success
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False


# Global instance for easy access
_llm_service = None

def get_llm_service() -> LLMService:
    """Get the global LLM service instance."""
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service