# test_sms_parser.py - Simple test script

import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import Database
from sms_parser import get_sms_parser

def test_parser():
    print("🧪 Testing SMS Parser...\n")
    
    # Setup
    db = Database()
    parser = get_sms_parser(db)
    
    # Test cases
    tests = [
        {
            "name": "HDFC Debit",
            "sms": "HDFC Bank: Rs. 1,500.00 debited from A/c XX1234 on 15-12-2023 at AMAZON INDIA. Avl Bal: Rs. 45,230.15",
            "expected": 1500.00
        },
        {
            "name": "ICICI Credit Card",
            "sms": "ICICI Bank: Rs. 2,750.00 spent on Credit Card XX7878 at SWIGGY on 15/12/23.",
            "expected": 2750.00
        },
        {
            "name": "UPI Payment",
            "sms": "UPI: Rs. 500.00 paid to KIRANA STORE on 15-12-2023.",
            "expected": 500.00
        },
        {
            "name": "SBI Transaction",
            "sms": "SBI: Rs. 3,200 debited from A/C XX5678 to ZOMATO on 15-12-2023.",
            "expected": 3200.00
        }
    ]
    
    passed = 0
    for test in tests:
        print(f"📱 Testing: {test['name']}")
        result = parser.parse_sms(user_id=1, message_text=test['sms'])
        
        if result["success"]:
            amount = result["parsed_data"]["amount"]
            merchant = result["parsed_data"]["merchant"]
            confidence = result["confidence"]
            
            if abs(amount - test['expected']) < 0.01:
                print(f"  ✅ PASS: Rs. {amount} at {merchant} (confidence: {confidence:.2%})")
                passed += 1
            else:
                print(f"  ❌ FAIL: Expected Rs. {test['expected']}, got Rs. {amount}")
        else:
            print(f"  ❌ FAIL: Could not parse SMS")
    
    print(f"\n📊 Results: {passed}/{len(tests)} passed ({passed/len(tests)*100:.1f}%)")
    return passed == len(tests)

if __name__ == "__main__":
    success = test_parser()
    sys.exit(0 if success else 1)