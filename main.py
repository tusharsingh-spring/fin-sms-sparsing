# main.py - SINGLE FastAPI App with ALL endpoints

from fastapi import FastAPI, HTTPException, File, UploadFile, Form
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, List
import uvicorn
import shutil
import os
from datetime import datetime, timedelta

# Import your modules
from database import db
from sms_parser import get_sms_parser

# Initialize
app = FastAPI(title="FinApp Backend", version="1.0")
sms_parser = get_sms_parser(db)

# Pydantic Models
class SMSRequest(BaseModel):
    user_id: int
    message_text: str
    sender_number: Optional[str] = None
    sender_name: Optional[str] = None

class TransactionResponse(BaseModel):
    id: int
    amount: float
    date: str
    merchant: Optional[str]
    category: Optional[str]
    source: str
    created_at: str

# ============ OCR ENDPOINTS (Your existing) ============
@app.post("/api/ocr/upload")
async def upload_receipt(
    user_id: int = Form(...),
    file: UploadFile = File(...)
):
    """Upload receipt for OCR processing"""
    try:
        # Save file temporarily
        temp_path = f"/tmp/{file.filename}"
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # TODO: Call your OCR processing
        ocr_result = {
            "amount": 1500.0,
            "date": "2023-12-15",
            "merchant": "Test Store",
            "confidence": 0.85
        }
        
        # Save to database
        image_id = db.save_receipt_image(
            user_id=user_id,
            filename=file.filename,
            file_path=temp_path,
            file_size=os.path.getsize(temp_path)
        )
        
        transaction_id = db.save_transaction(
            user_id=user_id,
            amount=ocr_result["amount"],
            date=ocr_result["date"],
            merchant=ocr_result["merchant"],
            category="Shopping",
            source="receipt_ocr",
            receipt_id=image_id
        )
        
        return {
            "success": True,
            "image_id": image_id,
            "transaction_id": transaction_id,
            "parsed_data": ocr_result
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ============ SMS ENDPOINTS (NEW) ============
@app.post("/api/sms/parse")
async def parse_sms(sms_request: SMSRequest):
    """Parse SMS message"""
    try:
        result = sms_parser.parse_sms(
            user_id=sms_request.user_id,
            message_text=sms_request.message_text,
            sender_number=sms_request.sender_number,
            sender_name=sms_request.sender_name
        )
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/sms/test")
async def test_sms_parser():
    """Test SMS parser with sample messages"""
    test_messages = [
        "HDFC Bank: Rs. 1,500.00 debited from A/c XX1234 on 15-12-2023 at AMAZON INDIA.",
        "ICICI Bank: Rs. 2,750.00 spent on Credit Card XX7878 at SWIGGY on 15/12/23.",
        "UPI: Rs. 500.00 paid to KIRANA STORE on 15-12-2023.",
    ]
    
    results = []
    for i, message in enumerate(test_messages):
        result = sms_parser.parse_sms(
            user_id=1,
            message_text=message,
            sender_number=f"BANK{i}",
            sender_name="Test Bank"
        )
        results.append(result)
    
    return {
        "tested": len(test_messages),
        "results": results
    }

# ============ TRANSACTIONS ENDPOINTS (Unified) ============
@app.get("/api/transactions/{user_id}")
async def get_transactions(user_id: int, limit: int = 100):
    """Get ALL transactions for user (OCR + SMS)"""
    try:
        transactions = db.get_user_transactions(user_id, limit)
        
        # Categorize by source
        by_source = {}
        for txn in transactions:
            source = txn["source"]
            if source not in by_source:
                by_source[source] = []
            by_source[source].append(txn)
        
        return {
            "total": len(transactions),
            "by_source": by_source,
            "transactions": transactions
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/transactions/stats/{user_id}")
async def get_transaction_stats(user_id: int):
    """Get transaction statistics"""
    try:
        transactions = db.get_user_transactions(user_id, 1000)
        
        if not transactions:
            return {"message": "No transactions found"}
        
        total_amount = sum(t["amount"] for t in transactions)
        avg_amount = total_amount / len(transactions)
        
        # Count by source
        source_counts = {}
        for txn in transactions:
            source = txn["source"]
            source_counts[source] = source_counts.get(source, 0) + 1
        
        # Recent activity
        recent_days = 7
        recent_txns = [t for t in transactions 
                      if datetime.fromisoformat(t["date"]).date() > 
                      datetime.now().date() - timedelta(days=recent_days)]
        
        return {
            "total_transactions": len(transactions),
            "total_amount": total_amount,
            "average_amount": avg_amount,
            "source_distribution": source_counts,
            f"recent_{recent_days}_days": len(recent_txns),
            "recent_amount": sum(t["amount"] for t in recent_txns)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ============ HEALTH & INFO ============
@app.get("/")
async def root():
    return {
        "message": "FinApp Backend API",
        "version": "1.0",
        "endpoints": {
            "ocr": {
                "upload": "POST /api/ocr/upload"
            },
            "sms": {
                "parse": "POST /api/sms/parse",
                "test": "GET /api/sms/test"
            },
            "transactions": {
                "get": "GET /api/transactions/{user_id}",
                "stats": "GET /api/transactions/stats/{user_id}"
            }
        }
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "database": "connected" if db.conn else "disconnected",
        "timestamp": datetime.now().isoformat()
    }

if __name__ == "__main__":
    print("🚀 Starting FinApp Backend Server...")
    print("📊 Database tables created/verified")
    print("📱 SMS Parser initialized")
    print("🌐 API Endpoints:")
    print("  - POST /api/ocr/upload")
    print("  - POST /api/sms/parse")
    print("  - GET /api/transactions/{user_id}")
    print("  - GET /health")
    
    uvicorn.run(app, host="0.0.0.0", port=8000)