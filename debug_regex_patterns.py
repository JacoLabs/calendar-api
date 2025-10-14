#!/usr/bin/env python3

import re

# Test the regex patterns
text = "Title: COWA Due Date: Oct 15, 2025"

# Current pattern from the code
month_words = r'january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec'
label_prefix = r'(?:due(?:\s*date)?|deadline|date)\s*[:\-]?\s*'

labeled_pattern = re.compile(
    rf'\b{label_prefix}({month_words})\.?\s+(\d{{1,2}})(?:st|nd|rd|th)?,?\s+(\d{{4}})\b',
    re.IGNORECASE
)

print(f"Text: {text}")
print(f"Pattern: {labeled_pattern.pattern}")
print(f"Match: {labeled_pattern.search(text)}")

if labeled_pattern.search(text):
    match = labeled_pattern.search(text)
    print(f"Groups: {match.groups()}")
    print(f"Full match: '{match.group(0)}'")
else:
    print("No match found")

# Test simpler patterns
simple_patterns = [
    r'due\s*date\s*:\s*oct\s+15,?\s+2025',
    r'due\s*date\s*:\s*\w+\s+\d+,?\s+\d{4}',
    r'(?:due(?:\s*date)?|deadline|date)\s*[:\-]?\s*\w+\s+\d+,?\s+\d{4}',
]

for i, pattern in enumerate(simple_patterns):
    compiled = re.compile(pattern, re.IGNORECASE)
    match = compiled.search(text)
    print(f"Pattern {i+1}: {pattern}")
    print(f"Match: {match}")
    if match:
        print(f"Full match: '{match.group(0)}'")
    print()