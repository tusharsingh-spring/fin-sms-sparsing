import re

def test_amount_extraction():
    print("Testing Amount Extraction with Commas\\n")
    
    test_cases = [
        ("london Bank: Rs. 1,500.00 debited", "1,500.00"),
        ("Rs. 15,250.50 spent at SWIGGY", "15,250.50"),
        ("INR 2,000.00 paid", "2,000.00"),
        ("₹3,500.00 debited", "3,500.00"),
        ("Amount: 4,500.00 Rs", "4,500.00"),
        ("debited 5,500.00 from account", "5,500.00"),
        ("Rs. 1500.00 paid", "1500.00"),  # No comma
        ("Rs. 1,500 debited", "1,500"),   # No decimals
    ]
    
    # FIXED pattern that works
    pattern_fixed = r'(?:Rs\.?|INR|₹)\s*([\d,]+(?:\.\d{2})?)\b'
    
    for sms, expected in test_cases:
        print(f"SMS: {sms}")
        match = re.search(pattern_fixed, sms, re.IGNORECASE)
        if match:
            captured = match.group(1)
            # Convert to float
            try:
                amount_clean = captured.replace(',', '')
                amount_float = float(amount_clean)
                print(f"  ✓ Captured: {captured}")
                print(f"  ✓ As float: {amount_float}")
                if captured == expected:
                    print(f"  ✓ Matches expected: {expected}")
                else:
                    print(f"  ✗ Expected: {expected}, Got: {captured}")
            except Exception as e:
                print(f"  ✗ Error converting {captured}: {e}")
        else:
            print(f"  ✗ No match found")
        print()

test_amount_extraction()
