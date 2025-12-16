from fastapi import FastAPI
import uvicorn
import re
from datetime import datetime
from dateutil import parser

app = FastAPI()

class SimpleSMSParser:
    @staticmethod
    def parse_sms(message_text):
        result = {
            "success": False,
            "amount": None,
            "merchant": None,
            "date": None,
            "bank": None,
            "confidence": 0.0
        }
        
        # Amount extraction (FIXED)
        amount_patterns = [
            r'(?:Rs\.?|INR|₹)\s*([\d,]+\.\d{2})\b',
            r'([\d,]+\.\d{2})\s*(?:Rs|INR|₹)\b',
            r'(?:debited|paid|spent)\D*?([\d,]+\.\d{2})\b',
            r'(?:Amount|Amt)[:\s]*([\d,]+\.\d{2})\b',
        ]
        
        amount = None
        for pattern in amount_patterns:
            match = re.search(pattern, message_text, re.IGNORECASE)
            if match:
                try:
                    amount_str = match.group(1).replace(',', '')
                    amount = float(amount_str)
                    break
                except:
                    continue
        
        if not amount:
            return result
        
        result["amount"] = amount
        result["success"] = True
        
        # Date extraction
        date_patterns = [
            r'on\s+(\d{2}-\d{2}-\d{4})',
            r'on\s+(\d{1,2}/\d{1,2}/\d{4})',
            r'(\d{2}-\d{2}-\d{4})'
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, message_text)
            if match:
                try:
                    date_obj = parser.parse(match.group(1), dayfirst=True)
                    result["date"] = date_obj.date().isoformat()
                    break
                except:
                    continue
        
        if not result["date"]:
            result["date"] = datetime.now().date().isoformat()
        
        # Merchant extraction
        merchant_patterns = [
            r'at\s+([A-Z][A-Z\s&]+?)(?:\s+on|\.|,|$)',
            r'to\s+([A-Z][A-Z\s&]+?)(?:\s+on|\.|,|$)',
        ]
        
        for pattern in merchant_patterns:
            match = re.search(pattern, message_text)
            if match:
                result["merchant"] = match.group(1).strip()
                break
        
        # Bank detection
        message_lower = message_text.lower()
        if 'hdfc' in message_lower:
            result["bank"] = "HDFC"
        elif 'icici' in message_lower:
            result["bank"] = "ICICI"
        elif 'upi' in message_lower:
            result["bank"] = "UPI"
        
        # Calculate confidence
        confidence = 0.9 if result["merchant"] else 0.7
        if result["bank"]:
            confidence += 0.05
        result["confidence"] = min(confidence, 1.0)
        
        return result

@app.post("/parse")
async def parse_sms_endpoint(sms_text: str):
    return SimpleSMSParser.parse_sms(sms_text)

@app.get("/test")
async def test_parse():
    test_sms = "london Bank: Rs. 1,500.00 debited from A/c XX1234 on 15-12-2023 at AMAZON INDIA."
    return SimpleSMSParser.parse_sms(test_sms)

@app.get("/")
async def root():
    return {
        "message": "SMS Parser API",
        "endpoints": {
            "parse": "POST /parse",
            "test": "GET /test"
        }
    }

if __name__ == "__main__":
    print("🚀 Starting Simple SMS Parser API on http://localhost:9000")
    uvicorn.run(app, host="0.0.0.0", port=9000)
