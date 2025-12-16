import re
import json
from datetime import datetime
from dateutil import parser

class SMSParser:
    def __init__(self, db_instance):
        self.db = db_instance
        self.bank_patterns = self.load_bank_patterns()
        print("✅ SMS Parser initialized with improved patterns")
    
    def load_bank_patterns(self):
        return {
            "HDFC": {"confidence": 0.95},
            "ICICI": {"confidence": 0.93},
            "SBI": {"confidence": 0.92},
            "AXIS": {"confidence": 0.91},
            "UPI": {"confidence": 0.90},
            "PAYTM": {"confidence": 0.89},
            "PHONEPE": {"confidence": 0.89}
        }
    
    def detect_bank(self, message_text, sender_number=None):
        """Improved bank detection"""
        message_lower = message_text.lower()
        bank_confidence = 0.7
        
        # Bank keywords (case insensitive)
        if 'hdfc' in message_lower:
            return 'HDFC', 0.95
        elif 'icici' in message_lower:
            return 'ICICI', 0.93
        elif 'sbi' in message_lower or 'state bank' in message_lower:
            return 'SBI', 0.92
        elif 'axis' in message_lower:
            return 'AXIS', 0.91
        elif 'upi' in message_lower:
            return 'UPI', 0.90
        elif 'paytm' in message_lower:
            return 'PAYTM', 0.89
        elif 'phonepe' in message_lower:
            return 'PHONEPE', 0.89
        elif any(word in message_lower for word in ['debited', 'credited', 'paid', 'withdrawn', 'transaction']):
            # Generic bank transaction
            return 'UNKNOWN_BANK', 0.7
        else:
            return None, 0.5
    
    def extract_amount(self, message_text):
        """COMPLETE FIXED VERSION - extracts all amount formats"""
        print(f"🔍 Extracting amount from: {message_text[:80]}...")
        
        # ALL possible amount patterns (ordered by priority)
        patterns = [
            # Pattern 1: Rs. 1,500.00 or ₹1,500.00 or INR 1,500.00
            r'(?:Rs\.?|INR|₹)\s*([\d,]+\.\d{2})\b',
            
            # Pattern 2: 1,500.00 Rs or 1,500.00 INR
            r'([\d,]+\.\d{2})\s*(?:Rs|INR|₹)\b',
            
            # Pattern 3: debited/paid/spent 1,500.00
            r'(?:debited|paid|spent|credited)\D*?([\d,]+\.\d{2})\b',
            
            # Pattern 4: Amount: 4,500.00 or Amt: 4,500.00
            r'(?:Amount|Amt)[:\s]*([\d,]+\.\d{2})\b',
            
            # Pattern 5: Rs. 1,500 (without .00)
            r'(?:Rs\.?|INR|₹)\s*([\d,]+)\b',
            
            # Pattern 6: 1,500 Rs (without .00)
            r'([\d,]+)\s*(?:Rs|INR|₹)\b',
            
            # Pattern 7: Any number with comma and optional decimals
            r'\b([\d,]+\.?\d*)\s+(?:debited|paid|spent|credited|rs|inr)\b',
            
            # Pattern 8: Generic amount extraction as last resort
            r'\b(\d{1,3}(?:,\d{3})*\.?\d*)\b(?=\s*(?:rs|inr|₹)?\s|$)'
        ]
        
        for i, pattern in enumerate(patterns, 1):
            match = re.search(pattern, message_text, re.IGNORECASE)
            if match:
                amount_str = match.group(1)
                print(f"  Pattern {i} matched: '{amount_str}'")
                
                # Clean and convert
                try:
                    amount_clean = amount_str.replace(',', '')
                    amount = float(amount_clean)
                    print(f"  ✅ Parsed amount: {amount}")
                    
                    # Higher confidence for more specific patterns
                    confidence = 0.95 if i <= 4 else 0.85
                    return amount, confidence
                    
                except ValueError as e:
                    print(f"  ⚠️ Failed to parse '{amount_str}': {e}")
                    continue
        
        print(f"  ❌ No amount found")
        return None, 0.0
    
    def extract_date(self, message_text):
        """Extract date from SMS"""
        date_obj = None
        confidence = 0.0
        
        patterns = [
            r'on\s+(\d{2}-\d{2}-\d{4})',          # on 15-12-2023
            r'on\s+(\d{1,2}/\d{1,2}/\d{4})',      # on 15/12/2023
            r'Date[:\s]*(\d{2}-\d{2}-\d{4})',     # Date: 15-12-2023
            r'(\d{2}-\d{2}-\d{4})',               # 15-12-2023
            r'(\d{1,2}/\d{1,2}/\d{4})',           # 15/12/2023
            r'(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4})',  # 15 Dec 2023
        ]
        
        for pattern in patterns:
            match = re.search(pattern, message_text, re.IGNORECASE)
            if match:
                date_str = match.group(1)
                try:
                    date_obj = parser.parse(date_str, dayfirst=True, fuzzy=True)
                    confidence = 0.9
                    print(f"  ✅ Date found: {date_obj.date()}")
                    break
                except Exception as e:
                    print(f"  ⚠️ Failed to parse date '{date_str}': {e}")
                    continue
        
        if not date_obj:
            date_obj = datetime.now()
            confidence = 0.3
            print(f"  ⚠️ Using current date: {date_obj.date()}")
        
        return date_obj.date(), confidence
    
    def extract_merchant(self, message_text):
        """Extract merchant name"""
        merchant = None
        confidence = 0.0
        
        # Try to extract merchant from different patterns
        patterns = [
            r'at\s+([A-Z][A-Z\s&]+?)(?:\s+on|\.|,|$)',      # at AMAZON INDIA on
            r'to\s+([A-Z][A-Z\s&]+?)(?:\s+on|\.|,|$)',      # to AMAZON INDIA
            r'@\s+([A-Z][A-Z\s&]+?)(?:\s+on|\.|,|$)',       # @ AMAZON INDIA
            r'(?:Info|Merchant)[:\s]*([^\n.,]+)',           # Info: AMAZON INDIA
            r'(?:via|through)\s+([A-Z][A-Z\s&]+)',          # via AMAZON INDIA
            r'[^\w]([A-Z]{2,}[A-Z\s&]+)(?:\s+(?:on|at|\.|,|$))',  # Any all caps words
        ]
        
        for pattern in patterns:
            match = re.search(pattern, message_text)
            if match:
                merchant = match.group(1).strip()
                
                # Clean up merchant name
                merchant = re.sub(r'\s+', ' ', merchant)  # Remove extra spaces
                merchant = ' '.join(word.capitalize() for word in merchant.split())
                
                # Remove common suffixes
                suffixes = ['Pvt', 'Ltd', 'Inc', 'Corp', 'LLC']
                for suffix in suffixes:
                    if merchant.endswith(suffix):
                        merchant = merchant[:-len(suffix)].strip()
                
                confidence = 0.8
                print(f"  ✅ Merchant found: {merchant}")
                break
        
        if not merchant:
            print(f"  ⚠️ No merchant found")
        
        return merchant, confidence
    
    def extract_transaction_type(self, message_text):
        """Determine if debit or credit"""
        message_lower = message_text.lower()
        
        debit_keywords = ['debited', 'spent', 'paid', 'withdrawn', 'purchase']
        credit_keywords = ['credited', 'received', 'deposited', 'refund']
        
        if any(word in message_lower for word in debit_keywords):
            return 'DEBIT', 0.9
        elif any(word in message_lower for word in credit_keywords):
            return 'CREDIT', 0.9
        else:
            return 'UNKNOWN', 0.5
    
    def parse_sms(self, user_id, message_text, sender_number=None, sender_name=None):
        """Main parsing function - FIXED"""
        print(f"\n" + "="*60)
        print(f"📱 PARSING SMS for User {user_id}")
        print(f"Message: {message_text}")
        print("="*60)
        
        # Step 1: Detect bank
        bank_detected, bank_conf = self.detect_bank(message_text, sender_number)
        print(f"🏦 Bank: {bank_detected or 'Not detected'} (confidence: {bank_conf:.2f})")
        
        # Step 2: Extract transaction type
        txn_type, txn_type_conf = self.extract_transaction_type(message_text)
        print(f"💳 Type: {txn_type} (confidence: {txn_type_conf:.2f})")
        
        # Step 3: Extract amount (FIXED)
        amount, amount_conf = self.extract_amount(message_text)
        
        # Step 4: Extract date
        date, date_conf = self.extract_date(message_text)
        
        # Step 5: Extract merchant
        merchant, merchant_conf = self.extract_merchant(message_text)
        
        print("-"*60)
        
        # Calculate overall confidence
        confidences = []
        if amount_conf > 0:
            confidences.append(amount_conf)
        if date_conf > 0:
            confidences.append(date_conf)
        if merchant_conf > 0:
            confidences.append(merchant_conf)
        
        if confidences:
            field_avg = sum(confidences) / len(confidences)
            overall_conf = field_avg * bank_conf * txn_type_conf
        else:
            overall_conf = bank_conf * txn_type_conf * 0.5
        
        # Prepare result
        result = {
            "success": amount is not None,
            "sms_id": None,
            "transaction_id": None,
            "parsed_data": {
                "amount": amount,
                "merchant": merchant,
                "date": date.strftime("%Y-%m-%d") if date else None,
                "bank": bank_detected,
                "transaction_type": txn_type
            },
            "confidence": round(overall_conf, 3),
            "field_confidences": {
                "amount": round(amount_conf, 3),
                "date": round(date_conf, 3),
                "merchant": round(merchant_conf, 3),
                "bank": round(bank_conf, 3),
                "transaction_type": round(txn_type_conf, 3)
            }
        }
        
        # Save to database if we have amount
        if amount and self.db and hasattr(self.db, 'save_sms_message'):
            try:
                sms_id = self.db.save_sms_message(
                    user_id=user_id,
                    message_text=message_text,
                    sender_number=sender_number,
                    sender_name=sender_name,
                    is_bank_sms=(bank_detected is not None),
                    bank_detected=bank_detected
                )
                result["sms_id"] = sms_id
                
                if sms_id and overall_conf > 0.5:
                    transaction_id = self.db.save_parsed_sms_transaction(
                        user_id=user_id,
                        sms_id=sms_id,
                        amount=amount,
                        merchant=merchant or "Unknown Merchant",
                        transaction_date=date or datetime.now().date(),
                        bank_name=bank_detected or "Unknown Bank",
                        confidence=overall_conf
                    )
                    result["transaction_id"] = transaction_id
                    
            except Exception as e:
                print(f"⚠️ Database error: {e}")
        
        print(f"📊 RESULT:")
        print(f"  Success: {result['success']}")
        print(f"  Amount: ₹{amount if amount else 'N/A'}")
        print(f"  Merchant: {merchant or 'N/A'}")
        print(f"  Date: {date.strftime('%Y-%m-%d') if date else 'N/A'}")
        print(f"  Bank: {bank_detected or 'N/A'}")
        print(f"  Type: {txn_type}")
        print(f"  Confidence: {overall_conf:.2%}")
        print("="*60)
        
        return result

# Singleton instance
sms_parser_instance = None

def get_sms_parser(db):
    global sms_parser_instance
    if sms_parser_instance is None:
        sms_parser_instance = SMSParser(db)
    return sms_parser_instance
