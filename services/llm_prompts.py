"""
LLM prompt templates for event extraction.
Provides structured prompts for extracting calendar event information from natural language text.
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class PromptTemplate:
    """Template for LLM prompts with metadata."""
    system_prompt: str
    user_prompt_template: str
    expected_format: str
    confidence_threshold: float
    use_case: str


class LLMPromptTemplates:
    """
    Collection of prompt templates for different event extraction scenarios.
    Designed to work with various LLM providers (Ollama, OpenAI, Groq, etc.)
    """
    
    def __init__(self):
        self.templates = self._initialize_templates()
    
    def _initialize_templates(self) -> Dict[str, PromptTemplate]:
        """Initialize all prompt templates."""
        return {
            'primary_extraction': self._create_primary_extraction_template(),
            'multi_paragraph': self._create_multi_paragraph_template(),
            'ambiguous_handling': self._create_ambiguous_handling_template(),
            'fallback_extraction': self._create_fallback_extraction_template(),
            'confidence_scoring': self._create_confidence_scoring_template(),
            'incomplete_info': self._create_incomplete_info_template(),
        }
    
    def _create_primary_extraction_template(self) -> PromptTemplate:
        """Primary template for standard event extraction."""
        system_prompt = """You are an expert calendar event extraction system. Your job is to extract structured event information from natural language text.

Extract the following information when present:
- title: The event name or description
- start_datetime: Date and time when the event starts (ISO format: YYYY-MM-DDTHH:MM:SS)
- end_datetime: Date and time when the event ends (if specified or can be inferred)
- location: Where the event takes place (optional)
- description: Additional details about the event
- all_day: Whether this is an all-day event (boolean)

IMPORTANT RULES:
1. Always respond with valid JSON
2. Use null for missing information
3. For dates without year, assume current year (2025)
4. For times without date, look for date context in the text
5. If only start time is given, estimate reasonable end time based on event type
6. Provide confidence scores (0.0-1.0) for each extracted field
7. Handle typos and variations in date/time formats (9a.m, 9am, 9:00 A M)

CRITICAL ALL-DAY EVENT RULES:
8. If text contains "due date", "deadline", "expires", "ends on" with ONLY a date (no time), create an ALL-DAY event on that date
9. If text has a date but NO time context, default to ALL-DAY event rather than assuming a time
10. For all-day events, set start_datetime to the date at 00:00:00 and end_datetime to the next day at 00:00:00
11. Set all_day: true for events that should be all-day

Response format:
{
  "title": "string or null",
  "start_datetime": "ISO datetime string or null", 
  "end_datetime": "ISO datetime string or null",
  "location": "string or null",
  "description": "string or null",
  "all_day": true/false,
  "confidence": {
    "title": 0.0-1.0,
    "start_datetime": 0.0-1.0,
    "end_datetime": 0.0-1.0,
    "location": 0.0-1.0,
    "overall": 0.0-1.0
  },
  "extraction_notes": "brief explanation of extraction decisions"
}"""

        user_prompt_template = """Extract calendar event information from this text:

"{text}"

Current date context: {current_date}
Additional context: {context}"""

        return PromptTemplate(
            system_prompt=system_prompt,
            user_prompt_template=user_prompt_template,
            expected_format="json",
            confidence_threshold=0.7,
            use_case="Standard event extraction from clear text"
        )
    
    def _create_multi_paragraph_template(self) -> PromptTemplate:
        """Template for handling multi-paragraph text as single event context."""
        system_prompt = """You are an expert at extracting calendar event information from multi-paragraph text. The entire text should be treated as describing a SINGLE event, even if information is scattered across paragraphs.

Key principles:
1. Treat all paragraphs as describing ONE event
2. Combine information from different paragraphs
3. The most specific date/time information takes precedence
4. Look for the main event name/title across all paragraphs
5. Extract the primary location if multiple are mentioned

IMPORTANT: Do not create multiple events. Extract information for ONE event only.

Response format:
{
  "title": "string or null",
  "start_datetime": "ISO datetime string or null",
  "end_datetime": "ISO datetime string or null", 
  "location": "string or null",
  "description": "combined description from all paragraphs",
  "confidence": {
    "title": 0.0-1.0,
    "start_datetime": 0.0-1.0,
    "end_datetime": 0.0-1.0,
    "location": 0.0-1.0,
    "overall": 0.0-1.0
  },
  "extraction_notes": "explanation of how information was combined",
  "paragraphs_processed": "number of paragraphs analyzed"
}"""

        user_prompt_template = """Extract information for ONE calendar event from this multi-paragraph text:

"{text}"

Current date: {current_date}
Context: This text may span multiple paragraphs but describes a single event."""

        return PromptTemplate(
            system_prompt=system_prompt,
            user_prompt_template=user_prompt_template,
            expected_format="json",
            confidence_threshold=0.6,
            use_case="Multi-paragraph text describing single event"
        )
    
    def _create_ambiguous_handling_template(self) -> PromptTemplate:
        """Template for handling ambiguous or incomplete information."""
        system_prompt = """You are an expert at handling ambiguous calendar event information. When information is unclear or incomplete, provide multiple interpretations and indicate uncertainty.

For ambiguous information:
1. Provide the most likely interpretation as primary
2. List alternative interpretations in the alternatives field
3. Clearly indicate what information is missing or uncertain
4. Lower confidence scores for uncertain extractions
5. Provide helpful suggestions for clarification

Response format:
{
  "title": "most likely title or null",
  "start_datetime": "most likely start time or null",
  "end_datetime": "most likely end time or null",
  "location": "most likely location or null", 
  "description": "string or null",
  "all_day": true/false,
  "confidence": {
    "title": 0.0-1.0,
    "start_datetime": 0.0-1.0,
    "end_datetime": 0.0-1.0,
    "location": 0.0-1.0,
    "overall": 0.0-1.0
  },
  "alternatives": {
    "title": ["alternative title 1", "alternative title 2"],
    "start_datetime": ["alternative datetime 1", "alternative datetime 2"],
    "location": ["alternative location 1", "alternative location 2"]
  },
  "ambiguities": ["description of ambiguous elements"],
  "missing_info": ["list of missing critical information"],
  "clarification_needed": "what user should clarify"
}"""

        user_prompt_template = """Extract calendar event information from this potentially ambiguous text:

"{text}"

Current date: {current_date}
Note: This text may be incomplete or ambiguous. Provide alternatives and indicate uncertainties."""

        return PromptTemplate(
            system_prompt=system_prompt,
            user_prompt_template=user_prompt_template,
            expected_format="json",
            confidence_threshold=0.4,
            use_case="Ambiguous or incomplete event information"
        )
    
    def _create_fallback_extraction_template(self) -> PromptTemplate:
        """Template for fallback extraction when primary methods fail."""
        system_prompt = """You are a fallback event extraction system. Extract whatever event information you can find, even if incomplete. Focus on finding ANY useful information rather than perfect extraction.

Extraction priorities:
1. Any date or time references (even vague ones)
2. Any event names or activities mentioned
3. Any location references
4. Any duration or timing clues

Be very liberal in extraction - it's better to extract something than nothing.

Response format:
{
  "title": "any event name found or null",
  "start_datetime": "any date/time found or null",
  "end_datetime": "any end time found or null",
  "location": "any location found or null",
  "description": "original text as description",
  "confidence": {
    "title": 0.0-1.0,
    "start_datetime": 0.0-1.0,
    "end_datetime": 0.0-1.0,
    "location": 0.0-1.0,
    "overall": 0.0-1.0
  },
  "extraction_method": "fallback",
  "found_elements": ["list of any event-related elements found"],
  "suggestions": "suggestions for improving the input text"
}"""

        user_prompt_template = """Try to extract ANY calendar event information from this text:

"{text}"

Current date: {current_date}
Note: Extract whatever you can find, even if incomplete."""

        return PromptTemplate(
            system_prompt=system_prompt,
            user_prompt_template=user_prompt_template,
            expected_format="json",
            confidence_threshold=0.2,
            use_case="Fallback extraction for difficult text"
        )
    
    def _create_confidence_scoring_template(self) -> PromptTemplate:
        """Template specifically for confidence scoring and validation."""
        system_prompt = """You are an event extraction confidence assessor. Analyze extracted event information and provide detailed confidence scores and quality assessment.

Confidence scoring criteria:
- Title: 1.0 = explicit event name, 0.5 = inferred from context, 0.2 = very unclear
- DateTime: 1.0 = explicit date+time, 0.7 = explicit date only, 0.4 = relative date, 0.2 = very vague
- Location: 1.0 = specific address, 0.7 = named venue, 0.4 = general area, 0.2 = very vague
- Overall: weighted average considering importance (datetime > title > location)

Response format:
{
  "confidence_assessment": {
    "title": {
      "score": 0.0-1.0,
      "reasoning": "why this score",
      "quality": "high/medium/low"
    },
    "start_datetime": {
      "score": 0.0-1.0,
      "reasoning": "why this score", 
      "quality": "high/medium/low"
    },
    "end_datetime": {
      "score": 0.0-1.0,
      "reasoning": "why this score",
      "quality": "high/medium/low"
    },
    "location": {
      "score": 0.0-1.0,
      "reasoning": "why this score",
      "quality": "high/medium/low"
    },
    "overall": {
      "score": 0.0-1.0,
      "reasoning": "overall assessment",
      "recommendation": "accept/review/reject"
    }
  },
  "quality_issues": ["list of potential problems"],
  "improvement_suggestions": ["how to improve extraction"]
}"""

        user_prompt_template = """Assess the confidence and quality of this event extraction:

Original text: "{text}"
Extracted information: {extracted_info}

Provide detailed confidence scoring and quality assessment."""

        return PromptTemplate(
            system_prompt=system_prompt,
            user_prompt_template=user_prompt_template,
            expected_format="json",
            confidence_threshold=0.0,
            use_case="Confidence scoring and quality assessment"
        )
    
    def _create_incomplete_info_template(self) -> PromptTemplate:
        """Template for handling incomplete information with user prompts."""
        system_prompt = """You are an event extraction system that handles incomplete information by identifying what's missing and suggesting how to complete it.

When information is incomplete:
1. Extract whatever is available
2. Clearly identify what's missing
3. Suggest reasonable defaults where appropriate
4. Provide prompts for user to complete missing information
5. Indicate which fields are critical vs optional

Response format:
{
  "extracted": {
    "title": "string or null",
    "start_datetime": "ISO datetime or null",
    "end_datetime": "ISO datetime or null", 
    "location": "string or null",
    "description": "string or null"
  },
  "missing_critical": ["list of missing critical fields"],
  "missing_optional": ["list of missing optional fields"],
  "suggested_defaults": {
    "end_datetime": "suggested end time if start time exists",
    "title": "suggested title if none found"
  },
  "user_prompts": {
    "title": "What should we call this event?",
    "start_datetime": "When does this event start?",
    "location": "Where is this event taking place?"
  },
  "confidence": {
    "title": 0.0-1.0,
    "start_datetime": 0.0-1.0,
    "end_datetime": 0.0-1.0,
    "location": 0.0-1.0,
    "overall": 0.0-1.0
  },
  "can_create_event": true/false
}"""

        user_prompt_template = """Extract event information and identify what's missing:

"{text}"

Current date: {current_date}
Focus on: What information is available vs what's missing for creating a calendar event."""

        return PromptTemplate(
            system_prompt=system_prompt,
            user_prompt_template=user_prompt_template,
            expected_format="json",
            confidence_threshold=0.3,
            use_case="Incomplete information handling with user prompts"
        )
    
    def get_template(self, template_name: str) -> Optional[PromptTemplate]:
        """Get a specific prompt template by name."""
        return self.templates.get(template_name)
    
    def get_primary_template(self) -> PromptTemplate:
        """Get the primary extraction template."""
        return self.templates['primary_extraction']
    
    def get_multi_paragraph_template(self) -> PromptTemplate:
        """Get the multi-paragraph handling template."""
        return self.templates['multi_paragraph']
    
    def get_ambiguous_template(self) -> PromptTemplate:
        """Get the ambiguous information handling template."""
        return self.templates['ambiguous_handling']
    
    def get_fallback_template(self) -> PromptTemplate:
        """Get the fallback extraction template."""
        return self.templates['fallback_extraction']
    
    def get_confidence_template(self) -> PromptTemplate:
        """Get the confidence scoring template."""
        return self.templates['confidence_scoring']
    
    def get_incomplete_template(self) -> PromptTemplate:
        """Get the incomplete information template."""
        return self.templates['incomplete_info']
    
    def format_prompt(self, template_name: str, text: str, **kwargs) -> tuple[str, str]:
        """
        Format a prompt template with the given text and context.
        
        Args:
            template_name: Name of the template to use
            text: The text to extract event information from
            **kwargs: Additional context variables
            
        Returns:
            Tuple of (system_prompt, formatted_user_prompt)
        """
        template = self.get_template(template_name)
        if not template:
            raise ValueError(f"Template '{template_name}' not found")
        
        # Set default values
        context_vars = {
            'text': text,
            'current_date': kwargs.get('current_date', '2025-01-01'),
            'context': kwargs.get('context', 'No additional context'),
            **kwargs
        }
        
        # Format the user prompt
        formatted_user_prompt = template.user_prompt_template.format(**context_vars)
        
        return template.system_prompt, formatted_user_prompt
    
    def get_template_for_text_type(self, text: str, context: Optional[str] = None) -> str:
        """
        Determine the best template to use based on text characteristics.
        
        Args:
            text: The text to analyze
            context: Optional context about the text
            
        Returns:
            Template name to use
        """
        # Count paragraphs
        paragraphs = [p.strip() for p in text.split('\n') if p.strip()]
        
        # Check for ambiguity indicators (be more specific)
        strong_ambiguity_indicators = [
            'maybe', 'possibly', 'might', 'could be', 'not sure',
            'either', 'unclear', 'tbd', 'to be determined'
        ]
        
        has_strong_ambiguity = any(indicator in text.lower() for indicator in strong_ambiguity_indicators)
        
        # Check for incomplete information
        has_date = any(word in text.lower() for word in [
            'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday',
            'tomorrow', 'today', 'next', 'january', 'february', 'march', 'april',
            'may', 'june', 'july', 'august', 'september', 'october', 'november', 'december',
            '/', '-', '2024', '2025'
        ])
        
        has_time = any(word in text.lower() for word in [
            'am', 'pm', 'a.m', 'p.m', ':', 'noon', 'midnight', 'morning', 'afternoon', 'evening'
        ])
        
        # Determine best template with more specific logic
        if len(paragraphs) > 2:
            return 'multi_paragraph'
        elif has_strong_ambiguity:
            return 'ambiguous_handling'
        elif len(text.split()) < 2:  # Very short text (single word)
            return 'fallback_extraction'
        elif not has_date and not has_time and len(text.split()) < 5:
            return 'incomplete_info'
        else:
            return 'primary_extraction'
    
    def list_templates(self) -> Dict[str, str]:
        """List all available templates with their use cases."""
        return {name: template.use_case for name, template in self.templates.items()}


# Global instance for easy access
_prompt_templates = None

def get_prompt_templates() -> LLMPromptTemplates:
    """Get the global prompt templates instance."""
    global _prompt_templates
    if _prompt_templates is None:
        _prompt_templates = LLMPromptTemplates()
    return _prompt_templates