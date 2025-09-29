#!/usr/bin/env python3
"""
Test the API endpoint for due date parsing.
"""

import requests
import json

def test_api_due_date():
    """Test the API with due date examples."""
    
    # Start the API server first (assuming it's running on localhost:8000)
    api_url = "http://localhost:8000/parse"
    
    test_cases = [
        {
            'text': 'Due Date: Oct 15, 2025',
            'description': 'Simple due date'
        },
        {
            'text': 'Item ID: 37131076518125 Title: COWA Due Date: Oct 15, 2025',
            'description': 'Due date with context (screenshot example)'
        }
    ]
    
    print("Testing API Due Date Parsing")
    print("=" * 50)
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\nTest {i}: {test_case['description']}")
        print(f"Input: '{test_case['text']}'")
        
        try:
            response = requests.post(api_url, json={
                'text': test_case['text'],
                'timezone': 'UTC'
            })
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ API Response:")
                print(f"   Title: {data.get('title')}")
                print(f"   Start: {data.get('start_datetime')}")
                print(f"   End: {data.get('end_datetime')}")
                print(f"   All Day: {data.get('all_day')}")
                print(f"   Confidence: {data.get('confidence_score', 0):.2f}")
                
                # Check if it's correctly parsed as Oct 15, 2025
                if data.get('start_datetime') and '2025-10-15' in data['start_datetime']:
                    print("✅ Correct date extracted")
                else:
                    print("❌ Wrong date extracted")
                
                if data.get('all_day'):
                    print("✅ Correctly marked as all-day")
                else:
                    print("❌ Should be all-day event")
                    
            else:
                print(f"❌ API Error: {response.status_code}")
                print(f"   Response: {response.text}")
                
        except requests.exceptions.ConnectionError:
            print("❌ Could not connect to API. Make sure the server is running on localhost:8000")
            print("   Run: python api/app/main.py")
            break
        except Exception as e:
            print(f"❌ Error: {e}")
    
    print("\n" + "=" * 50)
    print("API test completed!")

if __name__ == "__main__":
    test_api_due_date()