#!/usr/bin/env python3
"""
Debug script to test quote extraction specifically.
"""

import re

def test_quotes():
    text = "Hi team, let's schedule our 'Q4 Planning Review' for next Friday at 2:30pm in the main conference room."
    
    quote_patterns = [
        re.compile(r'"([^"]+)"'),
        re.compile(r"(?<!\w)'([^']+)'(?!\w)"),  # Avoid matching contractions like "let's"
        re.compile(r'`([^`]+)`')
    ]
    
    print(f"Text: {text}")
    print()
    
    for i, pattern in enumerate(quote_patterns):
        matches = pattern.finditer(text)
        print(f"Pattern {i+1}: {pattern.pattern}")
        for match in matches:
            print(f"  Found: '{match.group(1)}' at position {match.start(1)}-{match.end(1)}")
        print()

if __name__ == "__main__":
    test_quotes()