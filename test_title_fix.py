#!/usr/bin/env python3
"""
Quick test to verify title extraction fix
"""

from services.title_extractor import TitleExtractor

def test_title_extraction():
    extractor = TitleExtractor()
    
    test_cases = [
        "Item ID: 37131076518125Title: COWA!Due Date: Oct 15, 2025",
        "Title: COWA!Due Date: Oct 15, 2025",
        "Item ID: 37131076518125\nTitle: COWA!\nDue Date: Oct 15, 2025",  # Multi-line version
        "Title: COWA!\nDue Date: Oct 15, 2025",
        "Title: Meeting with Sarah!Due Date: Tomorrow",
        "Title: Project Review Due Date: Nov 1, 2025"
    ]
    
    for text in test_cases:
        result = extractor.extract_title(text)
        print(f"Text: '{text}'")
        print(f"Extracted title: '{result.title}'")
        print(f"Confidence: {result.confidence}")
        print(f"Method: {result.generation_method}")
        print("-" * 50)

if __name__ == "__main__":
    test_title_extraction()