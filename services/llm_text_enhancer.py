"""
LLM-based text enhancement service for improving email and text parsing quality.
Supports multiple LLM providers including free local models and cloud APIs.
"""

import os
import json
import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Optional imports - will gracefully handle missing dependencies
try:
    import openai
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logger.info("OpenAI not available - install with: pip install openai")

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    logger.info("Requests not available - install with: pip install requests")

try:
    from transformers import pipeline, AutoTokenizer, AutoModelForCausalLM
    import torch
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False
    logger.info("Transformers not available - install with: pip install transformers torch")


@dataclass
class TextEnhancement:
    """Result of LLM text enhancement."""
    enhanced_text: str
    confidence: float
    detected_patterns: List[str]
    original_text: str
    enhancement_type: str
    metadata: Dict[str, Any]


class LLMTextEnhancer:
    """
    LLM-based text enhancement service that improves parsing quality by:
    1. Detecting email communication patterns (school, business, personal)
    2. Restructuring text for better parsing
    3. Extracting and highlighting key event information
    4. Handling multi-line and fragmented text from Gmail selections
    
    Supports multiple LLM providers:
    - Local models via Ollama (FREE)
    - Hugging Face transformers (FREE)
    - OpenAI API (PAID)
    - Groq API (FREE tier available)
    """
    
    def __init__(self, provider: str = "auto", model: Optional[str] = None, **kwargs):
        """
        Initialize the LLM text enhancer.
        
        Args:
            provider: LLM provider ("auto", "ollama", "huggingface", "openai", "groq")
            model: Model name (provider-specific)
            **kwargs: Additional provider-specific configuration
        """
        self.provider = provider
        self.model = model
        self.client = None
        self.local_model = None
        self.config = kwargs
        
        # Auto-detect best available provider
        if provider == "auto":
            self.provider = self._detect_best_provider()
        
        # Initialize the selected provider
        self._initialize_provider()
        
        logger.info(f"LLM Text Enhancer initialized with provider: {self.provider}, model: {self.model}")
    
    def _detect_best_provider(self) -> str:
        """Detect the best available LLM provider."""
        
        # Check for Ollama (best free option)
        if self._check_ollama_available():
            return "ollama"
        
        # Check for Groq API key (fast and has free tier)
        if os.getenv('GROQ_API_KEY'):
            return "groq"
        
        # Check for OpenAI API key
        if os.getenv('OPENAI_API_KEY') and OPENAI_AVAILABLE:
            return "openai"
        
        # Check for Hugging Face transformers (local, but resource intensive)
        if TRANSFORMERS_AVAILABLE:
            return "huggingface"
        
        # Fallback to heuristics
        return "heuristic"
    
    def _check_ollama_available(self) -> bool:
        """Check if Ollama is running locally."""
        if not REQUESTS_AVAILABLE:
            return False
        
        try:
            response = requests.get("http://localhost:11434/api/tags", timeout=2)
            return response.status_code == 200
        except:
            return False
    
    def _initialize_provider(self):
        """Initialize the selected LLM provider."""
        
        if self.provider == "ollama":
            self._initialize_ollama()
        elif self.provider == "groq":
            self._initialize_groq()
        elif self.provider == "openai":
            self._initialize_openai()
        elif self.provider == "huggingface":
            self._initialize_huggingface()
        else:
            logger.info("Using heuristic fallback mode")
    
    def _initialize_ollama(self):
        """Initialize Ollama local LLM."""
        if not REQUESTS_AVAILABLE:
            logger.error("Requests library required for Ollama")
            self.provider = "heuristic"
            return
        
        # Default to a good free model for text processing
        if not self.model:
            self.model = "llama3.2:3b"  # Fast, good for text processing
        
        # Check if model is available
        try:
            response = requests.get("http://localhost:11434/api/tags", timeout=5)
            if response.status_code == 200:
                available_models = [model['name'] for model in response.json().get('models', [])]
                if self.model not in available_models:
                    logger.warning(f"Model {self.model} not found. Available: {available_models}")
                    # Try to pull the model
                    self._pull_ollama_model(self.model)
            else:
                logger.error("Ollama not available")
                self.provider = "heuristic"
        except Exception as e:
            logger.error(f"Failed to connect to Ollama: {e}")
            self.provider = "heuristic"
    
    def _initialize_groq(self):
        """Initialize Groq API."""
        api_key = os.getenv('GROQ_API_KEY')
        if not api_key:
            logger.error("GROQ_API_KEY not found")
            self.provider = "heuristic"
            return
        
        if not self.model:
            self.model = "llama-3.1-8b-instant"  # Fast and free
        
        self.config['api_key'] = api_key
        self.config['base_url'] = "https://api.groq.com/openai/v1"
    
    def _initialize_openai(self):
        """Initialize OpenAI API."""
        if not OPENAI_AVAILABLE:
            logger.error("OpenAI library not available")
            self.provider = "heuristic"
            return
        
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            logger.error("OPENAI_API_KEY not found")
            self.provider = "heuristic"
            return
        
        if not self.model:
            self.model = "gpt-3.5-turbo"
        
        try:
            self.client = OpenAI(api_key=api_key)
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI client: {e}")
            self.provider = "heuristic"
    
    def _initialize_huggingface(self):
        """Initialize Hugging Face transformers."""
        if not TRANSFORMERS_AVAILABLE:
            logger.error("Transformers library not available")
            self.provider = "heuristic"
            return
        
        if not self.model:
            # Use a small, efficient model for text processing
            self.model = "microsoft/DialoGPT-small"
        
        try:
            # Load model and tokenizer
            self.local_model = pipeline(
                "text-generation",
                model=self.model,
                tokenizer=self.model,
                device=0 if torch.cuda.is_available() else -1,
                max_length=512
            )
        except Exception as e:
            logger.error(f"Failed to load Hugging Face model: {e}")
            self.provider = "heuristic"
    
    def _pull_ollama_model(self, model_name: str):
        """Pull a model in Ollama."""
        try:
            logger.info(f"Pulling Ollama model: {model_name}")
            response = requests.post(
                "http://localhost:11434/api/pull",
                json={"name": model_name},
                timeout=300  # 5 minutes timeout for model download
            )
            if response.status_code == 200:
                logger.info(f"Successfully pulled model: {model_name}")
            else:
                logger.error(f"Failed to pull model: {response.text}")
        except Exception as e:
            logger.error(f"Error pulling model: {e}")
    
    def enhance_text_for_parsing(self, text: str, context: Optional[str] = None) -> TextEnhancement:
        """
        Enhance text using LLM to improve parsing quality.
        
        Args:
            text: Original text to enhance
            context: Optional context about the text source (email, clipboard, etc.)
            
        Returns:
            TextEnhancement object with improved text and metadata
        """
        if self.provider == "heuristic":
            return self._fallback_enhancement(text)
        
        try:
            # Detect the type of text and apply appropriate enhancement
            enhancement_type = self._detect_text_type(text)
            
            # Get the appropriate prompt for this text type
            system_prompt, user_prompt = self._get_enhancement_prompts(text, enhancement_type, context)
            
            # Call the appropriate LLM provider
            if self.provider == "ollama":
                result = self._call_ollama(system_prompt, user_prompt)
            elif self.provider == "groq":
                result = self._call_groq(system_prompt, user_prompt)
            elif self.provider == "openai":
                result = self._call_openai(system_prompt, user_prompt)
            elif self.provider == "huggingface":
                result = self._call_huggingface(system_prompt, user_prompt)
            else:
                return self._fallback_enhancement(text)
            
            return TextEnhancement(
                enhanced_text=result.get('enhanced_text', text),
                confidence=result.get('confidence', 0.8),
                detected_patterns=result.get('detected_patterns', []),
                original_text=text,
                enhancement_type=enhancement_type,
                metadata={
                    'provider': self.provider,
                    'model_used': self.model,
                    'processing_notes': result.get('notes', ''),
                    'context': context
                }
            )
            
        except Exception as e:
            logger.error(f"LLM enhancement failed: {e}")
            return self._fallback_enhancement(text)
    
    def _call_ollama(self, system_prompt: str, user_prompt: str) -> Dict[str, Any]:
        """Call Ollama local LLM."""
        full_prompt = f"{system_prompt}\n\nUser: {user_prompt}\n\nAssistant: "
        
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": self.model,
                "prompt": full_prompt,
                "stream": False,
                "options": {
                    "temperature": 0.1,
                    "num_predict": 500
                }
            },
            timeout=30
        )
        
        if response.status_code == 200:
            result_text = response.json()['response']
            # Try to parse as JSON, fallback to text processing
            try:
                return json.loads(result_text)
            except:
                # Extract information from text response
                return self._parse_text_response(result_text)
        else:
            raise Exception(f"Ollama API error: {response.status_code}")
    
    def _call_groq(self, system_prompt: str, user_prompt: str) -> Dict[str, Any]:
        """Call Groq API."""
        headers = {
            "Authorization": f"Bearer {self.config['api_key']}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.1,
            "max_tokens": 500
        }
        
        response = requests.post(
            f"{self.config['base_url']}/chat/completions",
            headers=headers,
            json=data,
            timeout=30
        )
        
        if response.status_code == 200:
            result_text = response.json()['choices'][0]['message']['content']
            try:
                return json.loads(result_text)
            except:
                return self._parse_text_response(result_text)
        else:
            raise Exception(f"Groq API error: {response.status_code}")
    
    def _call_openai(self, system_prompt: str, user_prompt: str) -> Dict[str, Any]:
        """Call OpenAI API."""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.1,
            max_tokens=500,
            response_format={"type": "json_object"}
        )
        
        return json.loads(response.choices[0].message.content)
    
    def _call_huggingface(self, system_prompt: str, user_prompt: str) -> Dict[str, Any]:
        """Call Hugging Face local model."""
        full_prompt = f"{system_prompt}\n\nUser: {user_prompt}\n\nAssistant: "
        
        result = self.local_model(
            full_prompt,
            max_length=len(full_prompt) + 200,
            num_return_sequences=1,
            temperature=0.1,
            do_sample=True,
            pad_token_id=self.local_model.tokenizer.eos_token_id
        )
        
        generated_text = result[0]['generated_text'][len(full_prompt):]
        
        try:
            return json.loads(generated_text)
        except:
            return self._parse_text_response(generated_text)
    
    def _parse_text_response(self, text: str) -> Dict[str, Any]:
        """Parse a text response when JSON parsing fails."""
        # Simple text parsing for when the model doesn't return JSON
        lines = text.strip().split('\n')
        
        enhanced_text = text
        confidence = 0.7
        patterns = []
        notes = "Text response parsed"
        
        # Look for enhanced text in the response
        for line in lines:
            if 'enhanced' in line.lower() or 'improved' in line.lower():
                # Try to extract the enhanced text
                if ':' in line:
                    enhanced_text = line.split(':', 1)[1].strip().strip('"\'')
                    break
        
        return {
            'enhanced_text': enhanced_text,
            'confidence': confidence,
            'detected_patterns': patterns,
            'notes': notes
        }
    
    def _detect_text_type(self, text: str) -> str:
        """
        Detect the type of text to determine enhancement strategy.
        
        Args:
            text: Text to analyze
            
        Returns:
            Text type string (school_email, business_email, personal_message, etc.)
        """
        text_lower = text.lower()
        
        # School/educational patterns
        school_indicators = [
            'students', 'grade', 'school', 'class', 'teacher', 'principal',
            'elementary', 'middle school', 'high school', 'kindergarten',
            'homework', 'assignment', 'field trip', 'parent', 'guardian'
        ]
        
        # Business patterns
        business_indicators = [
            'meeting', 'conference', 'call', 'presentation', 'client',
            'project', 'deadline', 'team', 'manager', 'office', 'boardroom',
            'quarterly', 'budget', 'proposal', 'stakeholder'
        ]
        
        # Personal patterns
        personal_indicators = [
            'lunch', 'dinner', 'coffee', 'birthday', 'party', 'wedding',
            'appointment', 'doctor', 'dentist', 'vacation', 'weekend'
        ]
        
        # Email-specific patterns
        email_indicators = [
            'dear', 'hi', 'hello', 'regards', 'sincerely', 'best',
            'from:', 'to:', 'subject:', 'sent:', 'cc:', 'bcc:'
        ]
        
        # Count indicators
        school_count = sum(1 for indicator in school_indicators if indicator in text_lower)
        business_count = sum(1 for indicator in business_indicators if indicator in text_lower)
        personal_count = sum(1 for indicator in personal_indicators if indicator in text_lower)
        email_count = sum(1 for indicator in email_indicators if indicator in text_lower)
        
        # Determine type based on highest count
        if school_count >= 2:
            return 'school_email' if email_count > 0 else 'school_message'
        elif business_count >= 2:
            return 'business_email' if email_count > 0 else 'business_message'
        elif personal_count >= 1:
            return 'personal_message'
        elif email_count >= 2:
            return 'generic_email'
        else:
            return 'generic_text'
    
    def _get_enhancement_prompts(self, text: str, text_type: str, context: Optional[str]) -> tuple[str, str]:
        """
        Get appropriate system and user prompts based on text type.
        
        Args:
            text: Original text
            text_type: Detected text type
            context: Optional context
            
        Returns:
            Tuple of (system_prompt, user_prompt)
        """
        base_system_prompt = """You are an expert at extracting calendar event information from various types of text. Your job is to restructure and enhance text to make it easier for a calendar parsing system to extract:

1. Event title/name
2. Date and time
3. Location
4. Duration (if mentioned)

You should:
- Restructure confusing or fragmented text into clear, parseable format
- Move the most important information (event name) to the beginning
- Ensure dates and times are clearly stated
- Preserve all original information while making it more accessible
- Handle partial text selections from emails (common with Gmail)

Always respond with valid JSON in this format:
{
  "enhanced_text": "restructured text optimized for parsing",
  "confidence": 0.85,
  "detected_patterns": ["pattern1", "pattern2"],
  "notes": "brief explanation of changes made"
}"""
        
        # Customize system prompt based on text type
        if text_type.startswith('school'):
            system_prompt = base_system_prompt + """

SPECIAL FOCUS FOR SCHOOL COMMUNICATIONS:
- School events often use formal language like "On [day] the [grade] students will [action] [event]"
- Restructure to put the event name first: "[Event Name] on [day] for [grade] students"
- Common patterns: field trips, assemblies, parent meetings, school events
- Times are often mentioned separately from the main event description"""
            
        elif text_type.startswith('business'):
            system_prompt = base_system_prompt + """

SPECIAL FOCUS FOR BUSINESS COMMUNICATIONS:
- Business meetings often have formal titles and specific times
- Look for meeting rooms, conference calls, project names
- Restructure to highlight: "[Meeting Title] on [date] at [time] in [location]"
- Handle recurring meeting patterns and corporate communication styles"""
            
        else:
            system_prompt = base_system_prompt
        
        # Create user prompt with context
        context_info = f" (Context: {context})" if context else ""
        user_prompt = f"""Please enhance this text for calendar event parsing{context_info}:

"{text}"

Focus on making the event information as clear and parseable as possible while preserving all original details."""
        
        return system_prompt, user_prompt
    
    def _fallback_enhancement(self, text: str) -> TextEnhancement:
        """
        Fallback enhancement when LLM is not available.
        Uses basic heuristics to improve text structure.
        
        Args:
            text: Original text
            
        Returns:
            TextEnhancement with basic improvements
        """
        enhanced_text = text
        detected_patterns = []
        
        # Basic improvements
        lines = text.split('\n')
        
        # Look for school event pattern: "On [day] the [grade] students will [action] [event]"
        school_pattern = r'On\s+(\w+)\s+the\s+(\w+)\s+students\s+will\s+(\w+)\s+(.+)'
        import re
        
        for i, line in enumerate(lines):
            match = re.search(school_pattern, line, re.IGNORECASE)
            if match:
                day, grade, action, event = match.groups()
                # Restructure to put event first
                enhanced_line = f"{event.strip()} on {day} for {grade} students"
                lines[i] = enhanced_line
                detected_patterns.append('school_event_restructure')
                break
        
        enhanced_text = '\n'.join(lines)
        
        # If we made changes, increase confidence
        confidence = 0.7 if detected_patterns else 0.5
        
        return TextEnhancement(
            enhanced_text=enhanced_text,
            confidence=confidence,
            detected_patterns=detected_patterns,
            original_text=text,
            enhancement_type='fallback',
            metadata={'method': 'heuristic_fallback'}
        )
    
    def is_available(self) -> bool:
        """Check if LLM enhancement is available."""
        return self.provider != "heuristic"
    
    def get_usage_stats(self) -> Dict[str, Any]:
        """Get usage statistics (for monitoring/billing)."""
        return {
            'provider': self.provider,
            'model': self.model,
            'available': self.is_available(),
            'total_requests': 0,  # Would track this in production
            'total_tokens': 0     # Would track this in production
        }


# Global instance for easy access
_llm_enhancer = None

def get_llm_enhancer() -> LLMTextEnhancer:
    """Get the global LLM enhancer instance."""
    global _llm_enhancer
    if _llm_enhancer is None:
        _llm_enhancer = LLMTextEnhancer()
    return _llm_enhancer