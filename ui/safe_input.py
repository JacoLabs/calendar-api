"""
Safe input wrapper for handling input in both interactive and non-interactive environments.
Prevents hanging in test environments and provides robust fallbacks.
"""

import sys
import os
from typing import Optional


def is_non_interactive() -> bool:
    """
    Check if we're running in a non-interactive environment.
    
    Returns:
        True if non-interactive mode should be used
    """
    # Check environment variables
    if os.getenv('NON_INTERACTIVE') == '1':
        return True
    
    if os.getenv('PREVIEW_AUTO_ACCEPT') == '1':
        return True
    
    # Check if we're in a test environment
    if 'pytest' in sys.modules:
        return True
    
    # Check if stdin is not a TTY (e.g., piped input, CI environment)
    if not sys.stdin.isatty():
        return True
    
    return False


def safe_input(prompt: str, default: Optional[str] = None) -> str:
    """
    Safe wrapper around input() that handles non-interactive environments gracefully.
    
    Args:
        prompt: The prompt to display to the user
        default: Default value to return if input fails or in non-interactive mode
        
    Returns:
        User input string, or default value if input fails
    """
    # In non-interactive mode, return default immediately
    if is_non_interactive():
        if default is not None:
            return default
        return ""
    
    # Retry mechanism to prevent infinite loops
    max_retries = 3
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            result = input(prompt).strip()
            return result
            
        except EOFError:
            # End of file reached (e.g., Ctrl+D, piped input ended)
            if default is not None:
                return default
            return ""
            
        except KeyboardInterrupt:
            # User pressed Ctrl+C
            if default is not None:
                return default
            return ""
            
        except Exception as e:
            # Any other input error
            retry_count += 1
            if retry_count >= max_retries:
                # Log the error once, then return default
                print(f"Input error after {max_retries} attempts: {type(e).__name__}: {e}", file=sys.stderr)
                if default is not None:
                    return default
                return ""
            
            # Brief pause before retry
            import time
            time.sleep(0.1)
    
    # Fallback (should not reach here)
    if default is not None:
        return default
    return ""


def safe_input_with_validation(prompt: str, validator=None, default: Optional[str] = None, 
                              error_message: str = "Invalid input. Please try again.") -> str:
    """
    Safe input with validation function.
    
    Args:
        prompt: The prompt to display
        validator: Function that takes input string and returns True if valid
        default: Default value if input fails or validation fails repeatedly
        error_message: Message to show on validation failure
        
    Returns:
        Validated input string or default
    """
    if is_non_interactive():
        if default is not None:
            return default
        return ""
    
    max_attempts = 3
    attempt = 0
    
    while attempt < max_attempts:
        try:
            user_input = safe_input(prompt, default)
            
            # If we got a default or empty string, return it
            if not user_input and default is not None:
                return default
            
            # If no validator, return the input
            if validator is None:
                return user_input
            
            # Validate the input
            if validator(user_input):
                return user_input
            else:
                attempt += 1
                if attempt < max_attempts:
                    print(error_message)
                
        except Exception as e:
            print(f"Input validation error: {type(e).__name__}: {e}", file=sys.stderr)
            break
    
    # All attempts failed, return default
    if default is not None:
        return default
    return ""


def confirm_action(prompt: str, default_yes: bool = False) -> bool:
    """
    Safe confirmation prompt that returns a boolean.
    
    Args:
        prompt: The confirmation prompt
        default_yes: Default value if in non-interactive mode or input fails
        
    Returns:
        True if user confirms, False otherwise
    """
    if is_non_interactive():
        return default_yes
    
    full_prompt = f"{prompt} ({'Y/n' if default_yes else 'y/N'}): "
    response = safe_input(full_prompt, "y" if default_yes else "n")
    
    if not response:
        return default_yes
    
    return response.lower() in ['y', 'yes', '1', 'true']


def get_choice(prompt: str, choices: list, default_index: int = 0) -> int:
    """
    Safe choice selection from a list of options.
    
    Args:
        prompt: The prompt to display
        choices: List of choice strings
        default_index: Default choice index if in non-interactive mode
        
    Returns:
        Index of selected choice
    """
    if is_non_interactive():
        return default_index
    
    # Display choices
    print(prompt)
    for i, choice in enumerate(choices):
        print(f"  {i + 1}. {choice}")
    
    def validate_choice(input_str: str) -> bool:
        try:
            choice_num = int(input_str)
            return 1 <= choice_num <= len(choices)
        except ValueError:
            return False
    
    choice_prompt = f"Enter choice (1-{len(choices)}): "
    response = safe_input_with_validation(
        choice_prompt, 
        validate_choice, 
        str(default_index + 1),
        f"Please enter a number between 1 and {len(choices)}"
    )
    
    try:
        return int(response) - 1
    except ValueError:
        return default_index